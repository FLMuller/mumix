"""
b_xlsheet.py -- tests and benchmarks for xlsheet: the cell grid, the book tables and the
worksheet XML codec.

What it proves
    The grid and the tables (kinds, text and style indices, escaped texts, the style cache),
    the writer's output (golden files in tests/golden, kept as bytes), and the reader: the fast
    scan agrees cell for cell with the general ElementTree path (read_with_elementtree, kept in
    xlsheet as the reference) on crafted cases and on every fixture and Excel workbook, falls
    back by the rules (a formula or inline string widens the expression, an unusual cell is a
    fragment, a prefixed namespace reads the whole part), and a workbook opens and saves to a
    copy that reads back the same. tests/golden/old holds what the first xlw (tkv cell nodes)
    wrote for the corpus; the new reader must read that back to the cells the corpus holds.

To rewrite the golden files (only when the output format is meant to change):
    python -c "import sys; sys.path.insert(0, 'tests'); import b_xlsheet; b_xlsheet.write_goldens()"

Run from the project root:
    python tools/runbench.py tests/b_xlsheet.py
"""

import io
import math
import os
import re
import shutil
import sys
import zipfile
import xml.etree.ElementTree as ET


def findtools():                      # walk up to the folder that holds tools/
    from os.path import abspath, dirname, isdir, join
    here = dirname(abspath(__file__))
    while here != dirname(here) and not isdir(join(here, 'tools')):
        here = dirname(here)
    sys.path.insert(0, join(here, 'tools'))
    return here


ROOT = findtools()
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from use import load
from bench import bench
import mumix                                      # puts tools, xlw on sys.path

SOURCES = ['xlsheet']
load('xlw')
import xlw as xlwmodule
import xlreader
import xlsheet
from chartcheck import package_errors
from gridcheck import at, ncells, cell_table, formula_table

OUTDIR = os.path.join(ROOT, 'results', 'b_xlsheet')
GOLDEN = os.path.join(ROOT, 'tests', 'golden')
FIXTURES = os.path.join(ROOT, 'tests', 'fixtures')
REFERENCE = os.path.join(ROOT, 'results', 'reference')
PARTS = ('xl/worksheets/sheet1.xml', 'xl/worksheets/sheet2.xml', 'xl/worksheets/sheet3.xml',
         'xl/worksheets/sheet4.xml', 'xl/worksheets/sheet5.xml', 'xl/styles.xml',
         'xl/sharedStrings.xml')


# ---------------------------------------------------------------------- the corpus -------
def build_corpus(folder):
    """One book 'corpus' with five sheets, built deterministically; returns the xlw."""
    xl = xlw()
    xl.newbook(os.path.join(folder, 'corpus'), 'plain', 'mixed', 'styled', 'sparse', 'wide')
    book = xl.corpus
    plain = book.plain
    for i in range(20):
        plain.write([i, i * 0.5, -i * 1.25, i * 1e-7, i * 1e21, 0.1 * i + 0.2, 3.0, i / 7.0])
        plain.writeln()
    mixed = book.mixed
    for row in (['plain text', 'a & b <c> "d" \'e\'', 'micro µ and ∑', '  spaced  '],
                [True, False, '', None],
                [0, 12345678901234567890, float('nan'), float('inf')],
                ['plain text', 'plain text', 'again', 'again'],
                ['[A] in A', '[B]', '[odd', '(paren)']):
        mixed.write([row])
        mixed.writeln()
    styled = book.styled
    styled.write('title', 'bold', True, 'fill', 'FFFF00').writeln()
    styled.write(1.5, 'Heading1').write(2.5, 'numfmt', '0.00%').write(3.5, 'italic', True)
    styled.writeln()
    styled.write('shared', 'color', 'C00000').write('shared').write('shared', 'bold', True)
    styled.writeln()
    styled.write(42, 'halign', 'center', 'wrap', True, 'indent', 2)
    styled.border([(2, 1), (2, 2)], 'n:medium,s:double', 'color', 'FF0000')
    sparse = book.sparse
    for row, col, value in ((1, 1, 'a'), (5, 3, 2.5), (5, 27, 'far'), (100, 1, 7), (100, 52, 8)):
        xlsheet.put_cell(sparse, row, col, value, {})
    wide = book.wide
    for row in range(3):
        wide.write([['x' * (3 * col % 90) for col in range(1, 31)]])
        wide.writeln()
    return xl


def corpus_parts(folder):
    """{part name: text} of the corpus book as the writer makes it now."""
    xl = build_corpus(folder)
    return dict(xlwmodule.build_parts(xl.corpus))


def write_goldens():
    os.makedirs(GOLDEN, exist_ok=True)
    os.makedirs(OUTDIR, exist_ok=True)
    parts = corpus_parts(OUTDIR)
    for name in PARTS:
        with open(os.path.join(GOLDEN, name.replace('/', '_')), 'w', encoding='utf-8',
                  newline='') as handle:
            handle.write(parts[name])


def golden(name, folder=GOLDEN):
    with open(os.path.join(folder, name.replace('/', '_')), encoding='utf-8',
              newline='') as handle:
        return handle.read()


HEAD = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="'
        'http://schemas.openxmlformats.org/spreadsheetml/2006/main">')


def sheetxml(body, head='', tail='', empty=False):
    """A worksheet part as bytes around a <sheetData> body."""
    middle = '<sheetData/>' if empty else '<sheetData>' + body + '</sheetData>'
    return (HEAD + head + middle + tail + '</worksheet>').encode('utf-8')


def readable(table):
    """A cell table without what the file cannot carry: non-finite numbers are blank cells
    and a blank cell without a style is absent."""
    out = {}
    for key, (value, style) in table.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            value = float(value)
            if not math.isfinite(value):
                value = None
        if value is None and not style:
            continue
        out[key] = (value, style)
    return out


def differences(first, second):
    """What differs between two cell tables: floats are compared to 1e-14 (a file keeps 15
    significant digits), everything else must be equal. [] when they agree."""
    found = []
    for key in sorted(set(first) | set(second)):
        if key not in first or key not in second:
            found.append((key, 'only in one'))
            continue
        a, b = first[key], second[key]
        if isinstance(a[0], float) and isinstance(b[0], float):
            same = math.isclose(a[0], b[0], rel_tol=1e-14, abs_tol=0.0) or a[0] == b[0]
        else:
            same = a[0] == b[0]
        if not same or a[1] != b[1]:
            found.append((key, a, b))
    return found


class Spy:
    """Counts, while a test runs, the parts read whole by the ElementTree fallback and the
    unusual cells read as fragments."""

    def __init__(me):
        me.whole = 0
        me.fragments = 0
        me.original_whole = xlsheet.read_with_elementtree
        me.original_parse = xlsheet.parse_fragments

    def __enter__(me):
        def whole(*args):
            me.whole += 1
            return me.original_whole(*args)

        def parse(gap):
            found = me.original_parse(gap)
            me.fragments += len(found)
            return found
        xlsheet.read_with_elementtree = whole
        xlsheet.parse_fragments = parse
        return me

    def __exit__(me, *exc):
        xlsheet.read_with_elementtree = me.original_whole
        xlsheet.parse_fragments = me.original_parse


class NoFun:
    """While active the Python loops of xlsheet run instead of the Cython ones."""

    def __enter__(me):
        me.saved = xlsheet.FUN
        xlsheet.FUN = None
        return me

    def __exit__(me, *exc):
        xlsheet.FUN = me.saved


EDGE_VALUES = [0, 1, -1, 0.1, 1e-9, 1e21, 12345678901234567890, float('nan'), float('inf'),
               -0.0, True, False, None, '', 'a', '[x', '\x01y', '\u00e9', 3.0, 1e15, 123456.789,
               0.05, 99999.99, 1e7, 9999999.5, 0.01, 100000.0, -5e-5, 2.5e-300]


class b_xlsheet(bench):
    BenchName = 'xlsheet'
    BenchVersion = 'M1.0.10'
    BenchHeader = ''
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        os.makedirs(OUTDIR, exist_ok=True)
        cls.parts = corpus_parts(OUTDIR)

    def sheet(self, name='S'):
        """A fresh writer with one sheet; returns (xl, sheet)."""
        xl = xlw()
        xl.newbook(os.path.join(OUTDIR, 'unit'), name)
        return xl, xl.unit.kvr(name)

    # ---- the grid and the tables ------------------------------------------------------------
    def test_T01_a_number_a_text_a_boolean_and_a_blank_are_four_kinds(self):
        xl, sheet = self.sheet()
        sheet.write([[1.5, 'a', True, '']])
        kinds = [item[2][0] for item in xlsheet.cell_list(sheet)]
        self.assertEqual(kinds, [xlsheet.NUM, xlsheet.TXT, xlsheet.BOOL, xlsheet.BLANK])
        self.assertEqual([xlsheet.cell_value(sheet, 1, c) for c in (1, 2, 3, 4)],
                         [1.5, 'a', True, None])

    def test_T02_a_text_is_stored_once_in_the_book_and_the_cells_hold_its_position(self):
        xl, sheet = self.sheet()
        sheet.write([['x', 'y', 'x', 'x']])
        tables = xlsheet.tables_of(sheet)
        self.assertEqual(xlsheet.text_list(tables), ['x', 'y'])
        self.assertEqual([item[2][1] for item in xlsheet.cell_list(sheet)], [0, 1, 0, 0])

    def test_T03_text_that_starts_with_a_bracket_or_a_control_character_round_trips(self):
        xl, sheet = self.sheet()
        texts = ['[A] in A', '[', '\x01odd', '(paren)', '', 'plain']
        sheet.write([texts])
        tables = xlsheet.tables_of(sheet)
        self.assertEqual([xlsheet.cell_value(sheet, 1, c + 1) for c in range(6)],
                         [t if t else None for t in texts])
        self.assertEqual(xlsheet.text_list(tables), [t for t in texts if t])

    def test_T04_a_repeated_style_is_one_entry_in_the_style_table(self):
        xl, sheet = self.sheet()
        for i in range(50):
            sheet.write(1.5, 'bold', True).write('t', 'bold', True)
        tables = xlsheet.tables_of(sheet)
        self.assertEqual(len(tables.xfs), 3)               # default, bold number, bold text
        self.assertEqual(xlsheet.text_list(tables), ['t'])
        self.assertEqual(tables.xfs[0], {})

    def test_T05_unhashable_style_settings_still_work(self):
        tables = xlsheet.new_tables()
        first = xlsheet.style_id(tables, {'border': [('n', 'thin', '000000')]})
        second = xlsheet.style_id(tables, {'border': [('n', 'thin', '000000')]})
        self.assertEqual((first, second), (1, 1))
        self.assertEqual(xlsheet.style_id(tables, {}), 0)

    def test_T06_numbers_get_an_automatic_format_unless_they_have_one(self):
        xl, sheet = self.sheet()
        sheet.write(42).write(0.125).write(2.5, 'numfmt', '0.00%').write(1e-9)
        self.assertEqual([xlsheet.cell_style(sheet, 1, c).get('numfmt') for c in (1, 2, 3, 4)],
                         ['0', '0.###', '0.00%', '0.##E+00'])

    def test_T07_a_numpy_value_is_stored_as_a_python_number(self):
        import numpy as np
        xl, sheet = self.sheet()
        sheet.write(np.float64(2.5)).write(np.int64(7))
        values = [xlsheet.cell_value(sheet, 1, c) for c in (1, 2)]
        self.assertEqual(values, [2.5, 7])
        self.assertEqual([type(v) for v in values], [float, int])

    def test_T08_a_cell_is_found_by_row_and_column_and_an_absent_one_is_none(self):
        xl, sheet = self.sheet()
        sheet.write([[1, 2], [3, 4]])
        self.assertEqual(xlsheet.cell_value(sheet, 2, 2), 4)
        self.assertIsNone(xlsheet.cell_value(sheet, 9, 9))
        self.assertIsNone(at(sheet, 9, 9))
        self.assertEqual(ncells(sheet), 4)

    # ---- the writer: golden files -------------------------------------------------------------
    def test_T09_golden_files_exist_for_every_part(self):
        for name in PARTS:
            self.assertTrue(os.path.isfile(os.path.join(GOLDEN, name.replace('/', '_'))), name)

    def test_T10_the_writer_matches_the_golden_files(self):
        for name in PARTS:
            self.assertEqual(self.parts[name], golden(name), name)

    def test_T11_the_corpus_is_deterministic(self):
        again = corpus_parts(OUTDIR)
        for name in PARTS:
            self.assertEqual(again[name], self.parts[name], name)

    def test_T12_what_the_first_xlw_wrote_reads_back_to_the_corpus(self):
        """Old sheet, style and string parts (tests/golden/old) in a package made by the
        new writer must read to the cells the corpus holds."""
        folder = os.path.join(OUTDIR, 'oldparts')
        os.makedirs(folder, exist_ok=True)
        xl = build_corpus(folder)
        package = os.path.join(folder, 'oldstyle.xlsx')
        with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, text in xlwmodule.build_parts(xl.corpus):
                if name in PARTS:
                    text = golden(name, os.path.join(GOLDEN, 'old'))
                archive.writestr(name, text.encode('utf-8'))
        reader = xlw()
        book = reader.open(package)
        for key in ('plain', 'mixed', 'styled', 'sparse', 'wide'):
            held = readable(cell_table(xl.corpus.kvr(key)))
            if key == 'mixed':                      # the old files predate the bracket row
                held = {where: cell for where, cell in held.items() if where[0] < 5}
            self.assertEqual(differences(readable(cell_table(book.kvr(key))), held), [], key)

    def test_T13_the_corpus_saves_a_valid_package_that_reads_back_to_itself(self):
        xl = build_corpus(OUTDIR)
        xl.save()
        path = os.path.join(OUTDIR, 'corpus.xlsx')
        self.assertEqual(package_errors(path), [])
        reader = xlw()
        book = reader.open(path)
        for key in ('plain', 'mixed', 'styled', 'sparse', 'wide'):
            self.assertEqual(differences(readable(cell_table(book.kvr(key))),
                                         readable(cell_table(xl.corpus.kvr(key)))), [], key)

    # ---- the reader: the fast scan agrees with the general path -----------------------------
    def both(self, data, strings=(), deltas=({},)):
        """Read `data` with the general ElementTree path (the reference) and with
        xml_to_sheet into fresh sheets; returns (reference, scan), each as (cell table, grid,
        report items, (whole part fallbacks, fragments))."""
        out = []
        for which in (0, 1):
            xl = xlw()
            xl.newbook(os.path.join(OUTDIR, f'both{which}'), 'S')
            sheet = getattr(xl, f'both{which}').S
            remap = xlsheet.fill_tables(xlsheet.tables_of(sheet), list(strings), list(deltas))
            report = xlreader.Collector()
            calls = (0, 0)
            if which == 0:
                grid = xlsheet.read_with_elementtree(data, sheet, report, remap)
            else:
                with Spy() as spy:
                    grid = xlsheet.xml_to_sheet(data, sheet, report, remap)
                calls = (spy.whole, spy.fragments)
            out.append((cell_table(sheet), grid, list(report.items), calls,
                        formula_table(sheet)))
        return out

    def agree(self, data, whole, fragments=0, strings=(), deltas=({},)):
        """Reference and scan must read the same; `whole` parts must have gone to the
        general path and `fragments` unusual cells must have been read one by one."""
        old, new = self.both(data, strings, deltas)
        self.assertEqual(new[:3], old[:3])
        self.assertEqual(new[4], old[4])                    # the same formulas
        self.assertEqual(new[3], (whole, fragments), '(whole part fallbacks, fragments)')
        return new

    def test_T14_numbers_strings_and_blanks(self):
        body = ('<row r="1"><c r="A1" s="0"><v>1.5</v></c><c r="B1" t="s"><v>0</v></c>'
                '<c r="C1"/><c r="D1" s="0"/></row><row r="3"><c r="A3"><v>-2e-7</v></c></row>')
        new = self.agree(sheetxml(body), 0, strings=['hello'])
        self.assertEqual(new[0][(1, 1)][0], 1.5)
        self.assertEqual(new[0][(1, 2)][0], 'hello')
        self.assertEqual(new[0][(3, 1)][0], -2e-7)
        self.assertNotIn((1, 3), new[0])

    def test_T15_booleans_and_text_cells(self):
        body = ('<c r="A1" t="b"><v>true</v></c><c r="B1" t="b"><v>0</v></c>'
                '<c r="C1" t="str"><v>plain</v></c><c r="D1" t="e"><v>#DIV/0!</v></c>')
        new = self.agree(sheetxml(body), 0)
        self.assertIs(new[0][(1, 1)][0], True)
        self.assertIs(new[0][(1, 2)][0], False)
        self.assertEqual(new[0][(1, 4)][0], '#DIV/0!')

    def test_T16_entities_and_character_references_in_text(self):
        body = '<c r="A1" t="str"><v>a &amp; b &lt;c&gt; &#233; &quot;q&quot;</v></c>'
        new = self.agree(sheetxml(body), 0)
        self.assertEqual(new[0][(1, 1)][0], 'a & b <c> é "q"')

    def test_T17_an_empty_v_is_a_blank_cell(self):
        new = self.agree(sheetxml('<c r="A1"><v></v></c><c r="B1" t="s"/>'), 0)
        self.assertEqual(new[0], {})

    def test_T18_column_letters_and_far_cells(self):
        body = '<c r="Z1"><v>1</v></c><c r="AA1"><v>2</v></c><c r="XFD1048576"><v>3</v></c>'
        new = self.agree(sheetxml(body), 0)
        self.assertEqual(sorted(new[0]), [(1, 26), (1, 27), (1048576, 16384)])

    def test_T19_styles_by_index_and_an_index_out_of_range(self):
        deltas = [{}, {'bold': True, 'numfmt': '0.00'}]
        body = ('<c r="A1" s="1"><v>1</v></c><c r="B1" s="9"><v>2</v></c>'
                '<c r="C1" s="1"/>')
        new = self.agree(sheetxml(body), 0, deltas=deltas)
        self.assertEqual(new[0][(1, 1)][1], (('bold', 'True'), ('numfmt', "'0.00'")))
        self.assertEqual(new[0][(1, 2)][1], ())
        self.assertIsNone(new[0][(1, 3)][0])                     # a blank cell that has a style
        self.assertEqual(new[0][(1, 3)][1], (('bold', 'True'), ('numfmt', "'0.00'")))

    def test_T20_an_empty_sheetdata(self):
        new = self.agree(sheetxml('', empty=True), 0)
        self.assertEqual(new[0], {})
        new = self.agree(sheetxml(''), 0)
        self.assertEqual(new[0], {})

    def test_T21_grid_flag_and_unread_elements(self):
        head = ('<sheetViews><sheetView showGridLines="0" workbookViewId="0"/></sheetViews>'
                '<weirdHead/>')
        tail = ('<pageMargins left="1" right="1" top="1" bottom="1" header="0" footer="0"/>'
                '<weirdTail/>')
        new = self.agree(sheetxml('<c r="A1"><v>1</v></c>', head, tail), 0)
        self.assertFalse(new[1])
        self.assertEqual(new[2], ['worksheet element weirdHead was not read',
                                  'worksheet element weirdTail was not read'])

    def test_T22_a_formula_cell_is_read_by_the_scan(self):
        new = self.agree(sheetxml('<c r="A1"><f>SUM(B1:B2)</f><v>3</v></c>'), 0)
        self.assertEqual(new[0][(1, 1)][0], 3.0)             # the cached value
        self.assertEqual(new[4], {(1, 1): ('<f>SUM(B1:B2)</f>', 3.0, '')})
        self.assertEqual(new[2], [])

    def test_T23_simple_inline_strings_are_read_by_the_scan(self):
        body = ('<c r="A1" t="inlineStr"><is><t>hi</t></is></c>'
                '<c r="B1" t="inlineStr"><is><t xml:space="preserve"> x &amp; y </t></is></c>'
                '<c r="C1" t="inlineStr"><is><t></t></is></c>')
        new = self.agree(sheetxml(body), 0)
        self.assertEqual(new[0][(1, 1)][0], 'hi')
        self.assertEqual(new[0][(1, 2)][0], ' x & y ')
        self.assertNotIn((1, 3), new[0])                         # an empty text is a blank cell

    def test_T24_rich_text_runs_are_one_fragment_each(self):
        body = ('<c r="A1"><v>1</v></c>'
                '<c r="B1" t="inlineStr"><is><r><t>a</t></r><r><t>b</t></r></is></c>'
                '<c r="C1"><v>2</v></c>')
        new = self.agree(sheetxml(body), 0, 1)
        self.assertEqual(new[0][(1, 2)][0], 'ab')

    def test_T25_other_attribute_order_and_extra_attributes_are_fragments(self):
        new = self.agree(sheetxml('<c r="A1" t="s" s="0"><v>0</v></c>'), 0, 1, strings=['x'])
        self.assertEqual(new[0][(1, 1)][0], 'x')
        new = self.agree(sheetxml('<c r="A1" s="0" cm="1"><v>4</v></c>'), 0, 1)
        self.assertEqual(new[0][(1, 1)][0], 4.0)

    def test_T26_prefixed_namespace_is_read_whole(self):
        data = ('<?xml version="1.0"?><x:worksheet xmlns:x="http://schemas.openxmlformats.org/'
                'spreadsheetml/2006/main"><x:sheetData><x:row r="1"><x:c r="A1"><x:v>7</x:v>'
                '</x:c></x:row></x:sheetData></x:worksheet>').encode()
        new = self.agree(data, 1)
        self.assertEqual(new[0][(1, 1)][0], 7.0)

    def test_T27_an_unknown_cell_type_is_read_as_a_number(self):
        new = self.agree(sheetxml('<c r="A1" t="d"><v>45000</v></c>'), 0)
        self.assertEqual(new[0][(1, 1)][0], 45000.0)

    def test_T28_a_part_that_is_not_well_formed_raises_in_both_readers(self):
        data = sheetxml('<c r="A1"><v>1</v></c><c r="B1" cm="1"><v>1</c>')
        for read in (xlsheet.read_with_elementtree, xlsheet.xml_to_sheet):
            xl = xlw()
            xl.newbook(os.path.join(OUTDIR, 'bad'), 'S')
            sheet = xl.bad.S
            remap = xlsheet.fill_tables(xlsheet.tables_of(sheet), [], [{}])
            with self.assertRaises(ET.ParseError):
                read(data, sheet, xlreader.Collector(), remap)

    def test_T29_unusual_cells_between_usual_ones_keep_their_place(self):
        body = ''
        for row in range(1, 7):
            body += (f'<row r="{row}"><c r="A{row}"><v>{row}</v></c>'
                     f'<c r="B{row}" t="s" s="0"><v>0</v></c>'
                     f'<c r="C{row}" cm="1"><v>{row * 2}</v></c>'
                     f'<c r="D{row}"><f>A{row}</f><v>{row}</v></c></row>')
        new = self.agree(sheetxml(body), 0, 12, strings=['s'])
        self.assertEqual(new[0][(6, 3)][0], 12.0)
        self.assertEqual(new[0][(6, 2)][0], 's')

    def test_T30_a_sheet_of_formulas_numbers_and_text_never_falls_back(self):
        body = ''
        for row in range(1, 41):
            body += (f'<row r="{row}"><c r="A{row}" t="s"><v>0</v></c>'
                     f'<c r="B{row}"><v>{row * 0.5}</v></c>'
                     f'<c r="C{row}"><f>B{row}*2</f><v>{row}</v></c>'
                     f'<c r="D{row}" t="str"><f>A{row}&amp;"!"</f><v>s&amp;{row}</v></c>'
                     f'<c r="E{row}"><f t="shared" si="0"/><v>{row}</v></c></row>')
        new = self.agree(sheetxml(body), 0, strings=['text'])
        self.assertEqual(new[2], [])
        self.assertEqual(new[0][(2, 4)][0], 's&2')
        self.assertEqual(new[4][(2, 3)], ('<f>B2*2</f>', 2.0, ''))
        self.assertEqual(new[4][(2, 4)], ('<f>A2&amp;"!"</f>', 's&2', 'str'))      # kept as written
        self.assertEqual(new[4][(2, 5)], ('<f t="shared" si="0"/>', 2.0, ''))     # a shared formula
        self.assertEqual(len(new[4]), 120)

    def test_T31_a_text_listed_twice_in_a_file_is_mapped_to_the_first(self):
        tables = xlsheet.new_tables()
        remap = xlsheet.fill_tables(tables, ['a', 'b', 'a', 'c'], [{}])
        self.assertEqual(remap, [0, 1, 0, 2])
        self.assertEqual(xlsheet.text_list(tables), ['a', 'b', 'c'])
        data = sheetxml('<c r="A1" t="s"><v>2</v></c><c r="B1" t="s"><v>3</v></c>')
        xl, sheet = self.sheet()
        remap = xlsheet.fill_tables(xlsheet.tables_of(sheet), ['a', 'b', 'a', 'c'], [{}])
        xlsheet.xml_to_sheet(data, sheet, xlreader.Collector(), remap)
        self.assertEqual([xlsheet.cell_value(sheet, 1, c) for c in (1, 2)], ['a', 'c'])

    def files(self):
        """Every workbook the codec should read the same both ways."""
        found = []
        for folder in (FIXTURES, REFERENCE, OUTDIR):
            if os.path.isdir(folder):
                for name in sorted(os.listdir(folder)):
                    if name.lower().endswith('.xlsx'):
                        found.append(os.path.join(folder, name))
        return found

    def test_T32_every_workbook_reads_the_same_with_the_scan_as_with_the_reference(self):
        build_corpus(OUTDIR).save()
        files = self.files()
        self.assertGreater(len(files), 6)
        fast = 0
        total = 0
        for path in files:
            with zipfile.ZipFile(path) as archive:
                strings = xlreader.read_strings(archive)
                deltas = xlreader.read_styles(archive, xlreader.Collector())
                for part in archive.namelist():
                    if re.fullmatch(r'xl/worksheets/sheet\d+\.xml', part):
                        old, new = self.both(archive.read(part), strings, deltas)
                        self.assertEqual(new[:3], old[:3], f'{path} {part}')
                        total += 1
                        fast += 1 if new[3] == (0, 0) else 0
        self.assertGreater(total, 8)
        self.assertGreater(fast, 5)                  # the writer's own files use the scan

    def test_T33_files_the_writer_made_never_fall_back(self):
        path = os.path.join(OUTDIR, 'corpus.xlsx')
        build_corpus(OUTDIR).save()
        with zipfile.ZipFile(path) as archive:
            strings = xlreader.read_strings(archive)
            deltas = xlreader.read_styles(archive, xlreader.Collector())
            for number in range(1, 6):
                data = archive.read(f'xl/worksheets/sheet{number}.xml')
                self.assertEqual(self.both(data, strings, deltas)[1][3], (0, 0), number)

    def test_T34_every_workbook_opens_saves_and_reads_back_the_same(self):
        sources = [os.path.join(folder, name)
                   for folder in (REFERENCE, FIXTURES) if os.path.isdir(folder)
                   for name in sorted(os.listdir(folder)) if name.lower().endswith('.xlsx')]
        self.assertGreater(len(sources), 6)
        lines = []
        folder = os.path.join(OUTDIR, 'copies')
        os.makedirs(folder, exist_ok=True)
        for source in sources:
            local = os.path.join(folder, os.path.basename(source))
            shutil.copyfile(source, local)
            xl = xlw()
            book = xl.open(local)
            xl.save()
            copy = book.kvr('priv').kvr('fname')
            again = xlw().open(copy)
            cells = 0
            for key in book.kvr('priv').kvr('sheetkeys'):
                self.assertEqual(differences(cell_table(again.kvr(key)),
                                             cell_table(book.kvr(key))), [],
                                 f'{os.path.basename(source)} {key}')
                cells += ncells(book.kvr(key))
            self.assertEqual(package_errors(copy), [], os.path.basename(source))
            lines.append(f'{os.path.basename(source)}: {cells} cells: copy reads back the same')
        with open(os.path.join(OUTDIR, 'compare.txt'), 'w', encoding='utf-8') as handle:
            handle.write('\n'.join(lines) + '\n')

    # ---- the Cython loops and the Python loops are the same ---------------------------------
    def test_T35_the_cython_loops_are_loaded(self):
        self.assertIsNotNone(xlsheet.FUN, 'xlsheetfun did not build: these tests run Python only')
        self.assertEqual(sorted(xlsheet.FUN.__all__), ['emit_grid', 'scan_cells', 'write_rows'])

    def test_T36_writing_a_block_gives_the_same_grid_in_both(self):
        import numpy as np
        values = EDGE_VALUES + [np.float64(2.5), np.int64(7), np.bool_(True)]
        lists = []
        for fun in (True, False):
            xl, sheet = self.sheet()
            if fun:
                sheet.write([values, list(reversed(values))])
            else:
                with NoFun():
                    sheet.write([values, list(reversed(values))])
            tables = xlsheet.tables_of(sheet)
            lists.append((repr(xlsheet.cell_list(sheet)), tables.xfs, xlsheet.text_list(tables)))
        self.assertEqual(lists[0], lists[1])

    def test_T37_a_single_value_and_a_styled_block_are_the_same_in_both(self):
        results = []
        for fun in (True, False):
            xl, sheet = self.sheet()
            def run():
                sheet.write(1.5).write('x').write([[2, 3]]).writeln()
                sheet.write(7, 'bold', True).write([[0.25, 'y']], 'italic', True)
            if fun:
                run()
            else:
                with NoFun():
                    run()
            tables = xlsheet.tables_of(sheet)
            results.append((repr(xlsheet.cell_list(sheet)), tables.xfs, xlsheet.text_list(tables)))
        self.assertEqual(results[0], results[1])

    def test_T38_scan_cells_reads_the_plain_form_and_refuses_the_rest_writing_nothing(self):
        xl, sheet = self.sheet()
        tables = xlsheet.tables_of(sheet)
        xlsheet.fill_tables(tables, ['a', 'b'], [{}, {'bold': True}])
        cells = sheet.kvr('cells')
        scan = xlsheet.FUN.scan_cells
        plain = (b'<row r="1" spans="1:3"><c r="A1"><v>1.5</v></c><c r="B1" s="1" t="s"><v>1</v></c>'
                 b'<c r="C1" t="b"><v>true</v></c><c r="D1" s="1"/></row>')
        self.assertEqual(scan(plain, cells, tables.xfs, None), 4)
        self.assertEqual([xlsheet.cell_value(sheet, 1, c) for c in (1, 2, 3, 4)],
                         [1.5, 'b', True, None])
        self.assertEqual(xlsheet.cell_style(sheet, 1, 4), {'bold': True})
        for body in (b'<c r="A1"><f>1</f><v>1</v></c>', b'<c r="A1" t="str"><v>x</v></c>',
                     b'<c r="A1" t="s" s="0"><v>0</v></c>', b'<c r="A1" cm="1"><v>1</v></c>',
                     b'\n<c r="A1"><v>1</v></c>', b'<c r="A1"><v>1</v></c><x/>',
                     b'<c r="A1"><v>1</c>', b'<c r="a1"><v>1</v></c>'):
            other, osheet = self.sheet()
            otables = xlsheet.tables_of(osheet)
            xlsheet.fill_tables(otables, [], [{}])
            self.assertEqual(scan(body, osheet.kvr('cells'), otables.xfs, None), -1, body)
            self.assertEqual(ncells(osheet), 0, body)

    TEXT_CELLS = ('<c r="A1" t="inlineStr"><is><t>plain</t></is></c>'
                  '<c r="B1" t="inlineStr"><is><t xml:space="preserve"> pad </t></is></c>'
                  '<c r="C1" t="inlineStr"><is><t>[open</t></is></c>'
                  '<c r="D1" t="inlineStr"><is><t>café µ</t></is></c>'
                  '<c r="E1" t="inlineStr"><is><t>a &amp; b &lt;c&gt; &#233;</t></is></c>'
                  '<c r="F1" t="str"><v>result</v></c>'
                  '<c r="G1" t="e"><v>#N/A</v></c>'
                  '<c r="A2" t="inlineStr"><is><t>plain</t></is></c>'
                  '<c r="B2" s="1" t="inlineStr"><is><t>styled</t></is></c>'
                  '<c r="C2" t="inlineStr"><is><t></t></is></c>')

    def test_T46_text_held_in_the_cell_is_read_by_the_scan_and_agrees_with_the_reference(self):
        new = self.agree(sheetxml(self.TEXT_CELLS), 0, 0, deltas=({}, {'bold': True}))
        self.assertEqual([new[0][(1, c)][0] for c in range(1, 8)],
                         ['plain', ' pad ', '[open', 'café µ', 'a & b <c> é',
                          'result', '#N/A'])
        self.assertEqual(new[0][(2, 2)], ('styled', (('bold', 'True'),)))
        xl, sheet = self.sheet()
        tables = xlsheet.tables_of(sheet)
        xlsheet.fill_tables(tables, [], [{}, {'bold': True}])
        count = xlsheet.FUN.scan_cells(
            sheetxml(self.TEXT_CELLS).split(b'<sheetData>')[1].split(b'</sheetData>')[0],
            sheet.kvr('cells'), tables.xfs, None, tables.texts,
            lambda raw: xlsheet.text_id(tables, xlsheet.text_value(raw)))
        self.assertEqual(count, 10, 'the Cython scan took the whole body')

    def test_T47_the_texts_get_the_same_positions_as_the_python_path_gives(self):
        data = sheetxml(self.TEXT_CELLS)
        lists = []
        for fun in (xlsheet.FUN, None):
            xl, sheet = self.sheet()
            tables = xlsheet.tables_of(sheet)
            xlsheet.fill_tables(tables, ['first'], [{}, {'bold': True}])
            saved = xlsheet.FUN
            xlsheet.FUN = fun
            try:
                xlsheet.xml_to_sheet(data, sheet, xlreader.Collector(), None)
            finally:
                xlsheet.FUN = saved
            lists.append(xlsheet.text_list(tables))
        self.assertEqual(lists[0], lists[1])
        self.assertEqual(lists[0][:3], ['first', 'plain', ' pad '])

    def test_T48_text_forms_the_scan_does_not_take_go_to_the_general_path_intact(self):
        refused = [('<c r="A1" t="inlineStr"><is><r><t>a</t></r><r><t>b</t></r></is></c>', 1),
                   ('<c r="A1" t="inlineStr"><is><t>a</t><t>b</t></is></c>', 0),
                   ('<c r="A1" t="inlineStr"><is><t/></is></c>', 1),
                   ('<c r="A1" t="inlineStr"><v>x</v></c>', None)]     # not a form Excel writes
        for body, fragments in refused:
            xl, sheet = self.sheet()
            tables = xlsheet.tables_of(sheet)
            xlsheet.fill_tables(tables, [], [{}])
            found = xlsheet.FUN.scan_cells(body.encode(), sheet.kvr('cells'), tables.xfs,
                                              None, tables.texts, lambda raw: 0)
            self.assertEqual(found, -1, body)
            self.assertEqual(ncells(sheet), 0, body)
            self.assertEqual(len(tables.texts), 0, body)
            if fragments is not None:
                self.agree(sheetxml(body), 0, fragments)

    def test_T39_a_number_that_float_refuses_raises_as_it_does_in_python(self):
        xl, sheet = self.sheet()
        tables = xlsheet.tables_of(sheet)
        xlsheet.fill_tables(tables, [], [{}])
        with self.assertRaises(ValueError):
            xlsheet.FUN.scan_cells(b'<c r="A1"><v>1.5x</v></c>', sheet.kvr('cells'),
                                      tables.xfs, None)

    def test_T40_the_scan_reads_every_workbook_the_same_with_either_loop(self):
        build_corpus(OUTDIR).save()
        total = 0
        for path in self.files():
            with zipfile.ZipFile(path) as archive:
                strings = xlreader.read_strings(archive)
                deltas = xlreader.read_styles(archive, xlreader.Collector())
                for part in archive.namelist():
                    if not re.fullmatch(r'xl/worksheets/sheet\d+\.xml', part):
                        continue
                    data = archive.read(part)
                    tables_out = []
                    for fun in (True, False):
                        xl, sheet = self.sheet()
                        remap = xlsheet.fill_tables(xlsheet.tables_of(sheet), list(strings),
                                                    list(deltas))
                        report = xlreader.Collector()
                        if fun:
                            grid = xlsheet.xml_to_sheet(data, sheet, report, remap)
                        else:
                            with NoFun():
                                grid = xlsheet.xml_to_sheet(data, sheet, report, remap)
                        tables_out.append((cell_table(sheet), grid, list(report.items)))
                    self.assertEqual(tables_out[0], tables_out[1], f'{path} {part}')
                    total += 1
        self.assertGreater(total, 8)

    def test_T41_the_xml_of_every_sheet_is_the_same_with_either_loop(self):
        build_corpus(OUTDIR).save()
        total = 0
        for path in self.files():
            xl = xlw()
            book = xl.open(path, 'parity')
            texts = xlsheet.text_list(xlsheet.tables_of(book.kvr(book.kvr('priv').kvr('sheetkeys')[0])))
            for key in book.kvr('priv').kvr('sheetkeys'):
                sheet = book.kvr(key)
                fast = xlsheet.sheet_to_xml(sheet, texts)
                with NoFun():
                    slow = xlsheet.sheet_to_xml(sheet, texts)
                self.assertEqual(fast, slow, f'{path} {key}')
                total += 1
        self.assertGreater(total, 8)

    def test_T42_cells_written_out_of_order_come_out_in_row_order_with_either_loop(self):
        xl, sheet = self.sheet()
        for row, col, value in ((5, 3, 'e'), (1, 2, 1.5), (5, 1, 'd'), (1, 1, True), (3, 30, 2)):
            xlsheet.put_cell(sheet, row, col, value, {})
        fast = xlsheet.sheet_to_xml(sheet)
        with NoFun():
            slow = xlsheet.sheet_to_xml(sheet)
        self.assertEqual(fast, slow)
        self.assertLess(fast[0].index('r="A1"'), fast[0].index('r="B1"'))
        self.assertLess(fast[0].index('r="B1"'), fast[0].index('r="AD3"'))
        self.assertLess(fast[0].index('r="AD3"'), fast[0].index('r="A5"'))
        self.assertEqual(fast[2], 30)

    # ---- formulas ------------------------------------------------------------------------------
    def test_T43_a_formula_is_written_and_read_back_with_and_without_a_cached_value(self):
        xl, sheet = self.sheet()
        xl.write([[1, 2]])
        xl.formula('=SUM(A1:B1)', cached=3.0)
        xl.formula('A1&"x"', cached='1x')
        xl.formula('=A1>0', cached=True)
        xl.formula('=A1+B1')
        xl.formula('=B1*2', 'bold', True, cached=4.0)
        self.assertEqual([xlsheet.cell_formula(sheet, 1, c) for c in (3, 4, 5, 6, 7)],
                         ['SUM(A1:B1)', 'A1&"x"', 'A1>0', 'A1+B1', 'B1*2'])
        self.assertEqual([xlsheet.cell_value(sheet, 1, c) for c in (3, 4, 5, 6, 7)],
                         [3.0, '1x', True, None, 4.0])
        self.assertEqual(xlsheet.cell_style(sheet, 1, 7), {'bold': True})
        xl.save()
        again = xlw().open(os.path.join(OUTDIR, 'unit.xlsx'))
        back = again.kvr('S')
        self.assertEqual(formula_table(back), formula_table(sheet))
        self.assertEqual([xlsheet.cell_value(back, 1, c) for c in (3, 4, 5, 6, 7)],
                         [3.0, '1x', True, None, 4.0])

    def test_T44_a_workbook_with_an_uncached_formula_is_calculated_on_load(self):
        xl, sheet = self.sheet()
        xl.write(1).formula('=A1*2')
        xl.save()
        with zipfile.ZipFile(os.path.join(OUTDIR, 'unit.xlsx')) as archive:
            self.assertIn('fullCalcOnLoad="1"', archive.read('xl/workbook.xml').decode())
            self.assertIn('<f>A1*2</f></c>', archive.read('xl/worksheets/sheet1.xml').decode())
        xl, sheet = self.sheet()
        xl.write(1).formula('=A1*2', cached=2)
        xl.save()
        with zipfile.ZipFile(os.path.join(OUTDIR, 'unit.xlsx')) as archive:
            self.assertNotIn('fullCalcOnLoad', archive.read('xl/workbook.xml').decode())

    def test_T45_the_formulas_of_every_workbook_survive_open_and_save(self):
        folder = os.path.join(OUTDIR, 'formulas')
        os.makedirs(folder, exist_ok=True)
        counted = {}
        sources = [path for path in self.files() if 'formulas' not in path
                   and not os.path.basename(path).endswith('_xlw.xlsx')]
        for source in sources:
            local = os.path.join(folder, os.path.basename(source))
            shutil.copyfile(source, local)
            xl = xlw()
            book = xl.open(local)
            xl.save()
            again = xlw().open(book.kvr('priv').kvr('fname'))
            total = 0
            for key in book.kvr('priv').kvr('sheetkeys'):
                first = formula_table(book.kvr(key))
                second = formula_table(again.kvr(key))
                self.assertEqual(sorted(second), sorted(first))
                for place in first:
                    self.assertEqual(second[place][0], first[place][0])      # the markup, exactly
                    self.assertEqual(second[place][2], first[place][2])
                    one, two = first[place][1], second[place][1]
                    if isinstance(one, float):
                        self.assertAlmostEqual(two, one, delta=abs(one) * 1e-9)   # ### number precision
                    else:
                        self.assertEqual(two, one)
                total += len(first)
            counted[os.path.basename(source)] = total
        self.assertEqual(counted.get('htmltags.xlsx'), 104)
        self.assertEqual(counted.get('SB Solubility vs temperature.xlsx'), 61)

    def bench_corpus_build_and_parts(self, timer):
        with timer as test:
            while test.more:
                for i in test.count:
                    corpus_parts(OUTDIR)
        return 'corpus: build and make all parts', 'whole'
