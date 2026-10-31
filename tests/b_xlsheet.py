"""
b_xlsheet.py -- tests and benchmarks for xlsheet, the worksheet XML codec (tkv <-> XML).

The contract, written before the module was: the corpus below (plain numbers, mixed text
and booleans, styles, sparse cells, wide sheets, characters that need escaping) was written
by the original xlw.sheet_data and its parts are kept as golden files in tests/golden. The
new emitter must reproduce them byte for byte, and the new scanner must read every file
the writer and Excel make into the same cells as the original xlreader.read_cells.

To rewrite the golden files (only when the output format is meant to change):
    python -c "import sys; sys.path.insert(0, 'tests'); import b_xlsheet; b_xlsheet.write_goldens()"

Run from the project root:
    python tools/runbench.py tests/b_xlsheet.py
"""

import os
import sys
import zipfile


def findtools():                      # walk up to the folder that holds tools/
    from os.path import abspath, dirname, isdir, join
    here = dirname(abspath(__file__))
    while here != dirname(here) and not isdir(join(here, 'tools')):
        here = dirname(here)
    sys.path.insert(0, join(here, 'tools'))
    return here


ROOT = findtools()
sys.path.insert(0, ROOT)
from use import load
from bench import bench
import mumix                                      # puts tools, xlw on sys.path

SOURCES = ['xlsheet']
globals().update(load('xlw', into={}))
import io
import re
import shutil
import xml.etree.ElementTree as ET
import xlw as xlwmodule
import xlreader
import xlsheet

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
                ['plain text', 'plain text', 'again', 'again']):
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
        xlwmodule.set_cell(sparse, row, col, value, xlwmodule.NO_STYLE)
    wide = book.wide
    for row in range(3):
        wide.write([['x' * (3 * col % 90) for col in range(1, 31)]])
        wide.writeln()
    return xl


def corpus_parts(folder):
    """{part name: text} of the corpus book as the writer makes it now."""
    xl = build_corpus(folder)
    parts = xlwmodule.build_parts(xl.corpus)
    return {name: parts.kvr(name) for name in PARTS}


def write_goldens():
    os.makedirs(GOLDEN, exist_ok=True)
    os.makedirs(OUTDIR, exist_ok=True)
    for name, text in corpus_parts(OUTDIR).items():
        with open(os.path.join(GOLDEN, name.replace('/', '_')), 'w', encoding='utf-8',
                  newline='') as handle:
            handle.write(text)


def golden(name):
    with open(os.path.join(GOLDEN, name.replace('/', '_')), encoding='utf-8',
              newline='') as handle:
        return handle.read()


HEAD = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="'
        'http://schemas.openxmlformats.org/spreadsheetml/2006/main">')


def sheetxml(body, head='', tail='', empty=False):
    """A worksheet part as bytes around a <sheetData> body."""
    middle = '<sheetData/>' if empty else '<sheetData>' + body + '</sheetData>'
    return (HEAD + head + middle + tail + '</worksheet>').encode('utf-8')


def cell_table(sheet):
    """{(row, col): (value, ((property, repr(setting)), ...))} of a sheet node."""
    table = {}
    for name, cell in zip(sheet.names(), sheet.nodes()):
        if name[:1] != '(':
            continue
        parts = name[1:-1].split()
        value = None
        style = []
        for key, setting in cell.entries():
            if key == 'val':
                value = setting
            else:
                style.append((key, repr(setting)))
        table[(int(parts[0]), int(parts[1]))] = (value, tuple(sorted(style)))
    return table


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


class NewCodec:
    """While active, xlw reads worksheets with xlsheet.xml_to_sheet and writes them with
    xlsheet.sheet_to_xml; leaving restores the original functions."""

    def __enter__(me):
        me.read = xlreader.read_cells
        me.write = xlwmodule.sheet_data

        def read_cells(archive, path, sheet, strings, deltas, report):
            return xlsheet.xml_to_sheet(archive.read(path), sheet, strings, deltas, report)
        xlreader.read_cells = read_cells
        xlwmodule.sheet_data = xlsheet.sheet_to_xml
        return me

    def __exit__(me, *exc):
        xlreader.read_cells = me.read
        xlwmodule.sheet_data = me.write


def open_and_copy(source, folder):
    """Copy `source` into folder, open it with xlw and save the book beside it; returns the
    path of the saved copy (<name>_xlw.xlsx) and the number of cells read."""
    os.makedirs(folder, exist_ok=True)
    local = os.path.join(folder, os.path.basename(source))
    shutil.copyfile(source, local)
    xl = xlw()
    book = xl.open(local)
    cells = 0
    for key in book.kvr('priv').kvr('sheetkeys'):
        cells += len(xlsheet.sheet_cells(book.kvr(key)))
    xl.save()
    return book.kvr('priv').kvr('fname'), cells


def zip_parts(path):
    """{part name: bytes} of an xlsx."""
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


class b_xlsheet(bench):
    BenchName = 'xlsheet'
    BenchVersion = 'M1.0.1'
    BenchHeader = ''
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        os.makedirs(OUTDIR, exist_ok=True)
        cls.parts = corpus_parts(OUTDIR)

    # ---- phase 1: the golden files are the current writer, and are stable ------------------
    def test_T01_golden_files_exist_for_every_part(self):
        for name in PARTS:
            self.assertTrue(os.path.isfile(os.path.join(GOLDEN, name.replace('/', '_'))), name)

    def test_T02_the_current_writer_matches_the_golden_files(self):
        for name in PARTS:
            self.assertEqual(self.parts[name], golden(name), name)

    def test_T03_the_corpus_is_deterministic(self):
        again = corpus_parts(OUTDIR)
        for name in PARTS:
            self.assertEqual(again[name], self.parts[name], name)

    # ---- phase 2a: the emitter is the old sheet_data, byte for byte -------------------------
    def test_T04_emitter_matches_the_old_sheet_data_and_tables(self):
        xl = build_corpus(OUTDIR)
        book = xl.corpus
        old = xlwmodule.SaveState()
        new = xlwmodule.SaveState()
        for key in book.kvr('priv').kvr('sheetkeys'):
            sheet = book.kvr(key)
            self.assertEqual(xlsheet.sheet_to_xml(sheet, new),
                             xlwmodule.sheet_data(sheet, old), key)
        self.assertEqual(new.styles, old.styles)
        self.assertEqual(new.strings, old.strings)
        self.assertEqual(sorted(new.xf_index.keys()), sorted(old.xf_index.keys()))
        for key in old.xf_index.keys():
            self.assertEqual(new.xf_index.kvr(key), old.xf_index.kvr(key), key)

    def test_T05_constants_agree_with_the_old_modules(self):
        self.assertEqual(xlsheet.BLANK, xlwmodule.BLANK)
        self.assertEqual(xlsheet.SHEET_KNOWN, xlreader.SHEET_KNOWN)
        self.assertEqual(xlsheet.NS_MAIN, xlreader.NS_MAIN)

    def test_T06_a_repeated_style_is_charged_once(self):
        xl = xlw()
        xl.newbook(os.path.join(OUTDIR, 'cache'), 'S')
        sheet = xl.cache.S
        for i in range(50):
            sheet.write(1.5, 'bold', True).write('t', 'bold', True)
        state = xlwmodule.SaveState()
        xlsheet.sheet_to_xml(sheet, state)
        self.assertEqual(len(state.styles), 3)             # default, bold number, bold text
        self.assertEqual(state.strings, ['t'])

    def test_T07_unhashable_style_settings_still_work(self):
        xl = xlw()
        xl.newbook(os.path.join(OUTDIR, 'unhash'), 'S')
        sheet = xl.unhash.S
        node = sheet.node(1, 1)
        node['val'] = 1.0
        node['border'] = [('n', 'thin', '000000')]         # a list: not hashable
        state = xlwmodule.SaveState()
        old = xlwmodule.SaveState()
        self.assertEqual(xlsheet.sheet_to_xml(sheet, state), xlwmodule.sheet_data(sheet, old))

    # ---- phase 2b: the scanner reads what the old read_cells reads ------------------------
    def both(self, data, strings=(), deltas=({},)):
        """Read `data` with the old read_cells and the new xml_to_sheet into fresh sheets;
        returns (old, new) as (cell table, grid, report items, fallback calls)."""
        out = []
        for which in (0, 1):
            xl = xlw()
            xl.newbook(os.path.join(OUTDIR, f'both{which}'), 'S')
            sheet = getattr(xl, f'both{which}').S
            report = xlreader.Collector()
            calls = (0, 0)
            if which == 0:
                archive = zipfile.ZipFile(io.BytesIO(self.zipped(data)))
                grid = xlreader.read_cells(archive, 'p.xml', sheet, list(strings),
                                           list(deltas), report)
            else:
                with Spy() as spy:
                    grid = xlsheet.xml_to_sheet(data, sheet, list(strings), list(deltas),
                                                report)
                calls = (spy.whole, spy.fragments)
            out.append((cell_table(sheet), grid, list(report.items), calls))
        return out

    def zipped(self, data):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('p.xml', data)
        return buffer.getvalue()

    def agree(self, data, whole, fragments=0, strings=(), deltas=({},)):
        """Old and new must read the same; `whole` parts must have gone to the general
        path and `fragments` unusual cells must have been read one by one."""
        old, new = self.both(data, strings, deltas)
        self.assertEqual(new[:3], old[:3])
        self.assertEqual(new[3], (whole, fragments), '(whole part fallbacks, fragments)')
        return new

    def test_T08_numbers_strings_and_blanks(self):
        body = ('<row r="1"><c r="A1" s="0"><v>1.5</v></c><c r="B1" t="s"><v>0</v></c>'
                '<c r="C1"/><c r="D1" s="0"/></row><row r="3"><c r="A3"><v>-2e-7</v></c></row>')
        new = self.agree(sheetxml(body), 0, strings=['hello'])
        self.assertEqual(new[0][(1, 1)][0], 1.5)
        self.assertEqual(new[0][(1, 2)][0], 'hello')
        self.assertEqual(new[0][(3, 1)][0], -2e-7)

    def test_T09_booleans_and_text_cells(self):
        body = ('<c r="A1" t="b"><v>true</v></c><c r="B1" t="b"><v>0</v></c>'
                '<c r="C1" t="str"><v>plain</v></c><c r="D1" t="e"><v>#DIV/0!</v></c>')
        new = self.agree(sheetxml(body), 0)
        self.assertIs(new[0][(1, 1)][0], True)
        self.assertIs(new[0][(1, 2)][0], False)
        self.assertEqual(new[0][(1, 4)][0], '#DIV/0!')

    def test_T10_entities_and_character_references_in_text(self):
        body = '<c r="A1" t="str"><v>a &amp; b &lt;c&gt; &#233; &quot;q&quot;</v></c>'
        new = self.agree(sheetxml(body), 0)
        self.assertEqual(new[0][(1, 1)][0], 'a & b <c> é "q"')

    def test_T11_an_empty_v_is_a_blank_cell(self):
        new = self.agree(sheetxml('<c r="A1"><v></v></c><c r="B1" t="s"/>'), 0)
        self.assertEqual(new[0], {})

    def test_T12_column_letters_and_far_cells(self):
        body = '<c r="Z1"><v>1</v></c><c r="AA1"><v>2</v></c><c r="XFD1048576"><v>3</v></c>'
        new = self.agree(sheetxml(body), 0)
        self.assertEqual(sorted(new[0]), [(1, 26), (1, 27), (1048576, 16384)])

    def test_T13_styles_by_index_and_an_index_out_of_range(self):
        deltas = [{}, {'bold': True, 'numfmt': '0.00'}]
        body = ('<c r="A1" s="1"><v>1</v></c><c r="B1" s="9"><v>2</v></c>'
                '<c r="C1" s="1"/>')
        new = self.agree(sheetxml(body), 0, deltas=deltas)
        self.assertEqual(new[0][(1, 1)][1], (('bold', 'True'), ('numfmt', "'0.00'")))
        self.assertEqual(new[0][(1, 2)][1], ())
        self.assertEqual(new[0][(1, 3)][0], xlsheet.BLANK)

    def test_T14_an_empty_sheetdata(self):
        new = self.agree(sheetxml('', empty=True), 0)
        self.assertEqual(new[0], {})
        new = self.agree(sheetxml(''), 0)
        self.assertEqual(new[0], {})

    def test_T15_grid_flag_and_unread_elements(self):
        head = ('<sheetViews><sheetView showGridLines="0" workbookViewId="0"/></sheetViews>'
                '<weirdHead/>')
        tail = ('<pageMargins left="1" right="1" top="1" bottom="1" header="0" footer="0"/>'
                '<weirdTail/>')
        new = self.agree(sheetxml('<c r="A1"><v>1</v></c>', head, tail), 0)
        self.assertFalse(new[1])
        self.assertEqual(new[2], ['worksheet element weirdHead was not read',
                                  'worksheet element weirdTail was not read'])

    def test_T16_a_formula_cell_is_read_by_the_scan(self):
        new = self.agree(sheetxml('<c r="A1"><f>SUM(B1:B2)</f><v>3</v></c>'), 0)
        self.assertEqual(new[0][(1, 1)][0], 3.0)
        self.assertEqual(new[2], ['1 formula cells: the cached values were read, not '
                                  'the formulas'])

    def test_T17_simple_inline_strings_are_read_by_the_scan(self):
        body = ('<c r="A1" t="inlineStr"><is><t>hi</t></is></c>'
                '<c r="B1" t="inlineStr"><is><t xml:space="preserve"> x &amp; y </t></is></c>'
                '<c r="C1" t="inlineStr"><is><t></t></is></c>')
        new = self.agree(sheetxml(body), 0)
        self.assertEqual(new[0][(1, 1)][0], 'hi')
        self.assertEqual(new[0][(1, 2)][0], ' x & y ')
        self.assertEqual(new[0][(1, 3)][0], '')

    def test_T17b_rich_text_runs_are_one_fragment_each(self):
        body = ('<c r="A1"><v>1</v></c>'
                '<c r="B1" t="inlineStr"><is><r><t>a</t></r><r><t>b</t></r></is></c>'
                '<c r="C1"><v>2</v></c>')
        new = self.agree(sheetxml(body), 0, 1)
        self.assertEqual(new[0][(1, 2)][0], 'ab')

    def test_T18_other_attribute_order_and_extra_attributes_are_fragments(self):
        new = self.agree(sheetxml('<c r="A1" t="s" s="0"><v>0</v></c>'), 0, 1,
                         strings=['x'])
        self.assertEqual(new[0][(1, 1)][0], 'x')
        new = self.agree(sheetxml('<c r="A1" s="0" cm="1"><v>4</v></c>'), 0, 1)
        self.assertEqual(new[0][(1, 1)][0], 4.0)

    def test_T19_fallback_prefixed_namespace(self):
        data = ('<?xml version="1.0"?><x:worksheet xmlns:x="http://schemas.openxmlformats.org/'
                'spreadsheetml/2006/main"><x:sheetData><x:row r="1"><x:c r="A1"><x:v>7</x:v>'
                '</x:c></x:row></x:sheetData></x:worksheet>').encode()
        new = self.agree(data, 1)
        self.assertEqual(new[0][(1, 1)][0], 7.0)

    def test_T20_an_unknown_cell_type_is_read_as_a_number(self):
        new = self.agree(sheetxml('<c r="A1" t="d"><v>45000</v></c>'), 0)
        self.assertEqual(new[0][(1, 1)][0], 45000.0)

    def test_T21_a_part_that_is_not_well_formed_raises_in_both_readers(self):
        data = sheetxml('<c r="A1"><v>1</v></c><c r="B1" cm="1"><v>1</c>')
        archive = zipfile.ZipFile(io.BytesIO(self.zipped(data)))
        xl = xlw()
        xl.newbook(os.path.join(OUTDIR, 'bad'), 'S')
        with self.assertRaises(ET.ParseError):
            xlreader.read_cells(archive, 'p.xml', xl.bad.S, [], [{}], xlreader.Collector())
        xl = xlw()
        xl.newbook(os.path.join(OUTDIR, 'bad2'), 'S')
        with self.assertRaises(ET.ParseError):
            xlsheet.xml_to_sheet(data, xl.bad2.S, [], [{}], xlreader.Collector())

    def test_T21b_unusual_cells_between_usual_ones_keep_their_place(self):
        body = ''
        for row in range(1, 7):
            body += (f'<row r="{row}"><c r="A{row}"><v>{row}</v></c>'
                     f'<c r="B{row}" t="s" s="0"><v>0</v></c>'
                     f'<c r="C{row}" cm="1"><v>{row * 2}</v></c>'
                     f'<c r="D{row}"><f>A{row}</f><v>{row}</v></c></row>')
        new = self.agree(sheetxml(body), 0, 12, strings=['s'])      # B (t before s) and C
        self.assertEqual(new[0][(6, 3)][0], 12.0)
        self.assertEqual(new[0][(6, 2)][0], 's')

    def test_T21c_a_sheet_of_formulas_numbers_and_text_never_falls_back(self):
        body = ''
        for row in range(1, 41):
            body += (f'<row r="{row}"><c r="A{row}" t="s"><v>0</v></c>'
                     f'<c r="B{row}"><v>{row * 0.5}</v></c>'
                     f'<c r="C{row}"><f>B{row}*2</f><v>{row}</v></c>'
                     f'<c r="D{row}" t="str"><f>A{row}&amp;"!"</f><v>s&amp;{row}</v></c>'
                     f'<c r="E{row}"><f t="shared" si="0"/><v>{row}</v></c></row>')
        new = self.agree(sheetxml(body), 0, strings=['text'])
        self.assertEqual(new[2], ['120 formula cells: the cached values were read, not '
                                  'the formulas'])
        self.assertEqual(new[0][(2, 4)][0], 's&2')

    def files(self):
        """Every workbook the codec should read the same both ways."""
        found = []
        for folder in (FIXTURES, REFERENCE, OUTDIR):
            if os.path.isdir(folder):
                for name in sorted(os.listdir(folder)):
                    if name.lower().endswith('.xlsx'):
                        found.append(os.path.join(folder, name))
        return found

    def test_T22_every_workbook_reads_the_same_with_the_scanner(self):
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
                        data = archive.read(part)
                        old, new = self.both(data, strings, deltas)
                        self.assertEqual(new[:3], old[:3], f'{path} {part}')
                        total += 1
                        fast += 1 if new[3] == (0, 0) else 0
        self.assertGreater(total, 8)
        self.assertGreater(fast, 5)                  # the writer's own files use the scan

    def test_T23_files_the_writer_made_never_fall_back(self):
        path = os.path.join(OUTDIR, 'corpus.xlsx')
        build_corpus(OUTDIR).save()
        with zipfile.ZipFile(path) as archive:
            strings = xlreader.read_strings(archive)
            deltas = xlreader.read_styles(archive, xlreader.Collector())
            for number in range(1, 6):
                data = archive.read(f'xl/worksheets/sheet{number}.xml')
                self.assertEqual(self.both(data, strings, deltas)[1][3], (0, 0), number)

    # ---- the old and the new codec open each file and write it to a copy ------------------
    def test_T24_old_and_new_open_and_save_every_workbook_to_identical_copies(self):
        sources = [os.path.join(folder, name)
                   for folder in (REFERENCE, FIXTURES) if os.path.isdir(folder)
                   for name in sorted(os.listdir(folder)) if name.lower().endswith('.xlsx')]
        self.assertGreater(len(sources), 6)
        lines = []
        for source in sources:
            old_copy, old_cells = open_and_copy(source, os.path.join(OUTDIR, 'copy_old'))
            with NewCodec():
                new_copy, new_cells = open_and_copy(source, os.path.join(OUTDIR, 'copy_new'))
            old_parts = zip_parts(old_copy)
            new_parts = zip_parts(new_copy)
            name = os.path.basename(source)
            self.assertEqual(sorted(new_parts), sorted(old_parts), name)
            differing = [part for part in old_parts if old_parts[part] != new_parts[part]]
            self.assertEqual(differing, [], name)
            self.assertEqual(new_cells, old_cells, name)
            lines.append(f'{name}: {old_cells} cells, {len(old_parts)} parts, '
                         f'{sum(len(v) for v in old_parts.values())} bytes: identical')
        with open(os.path.join(OUTDIR, 'compare.txt'), 'w', encoding='utf-8') as handle:
            handle.write('\n'.join(lines) + '\n')

    def bench_corpus_build_and_parts(self, timer):
        with timer as test:
            while test.more:
                for i in test.count:
                    corpus_parts(OUTDIR)
        return 'corpus: build and make all parts', 'phase 1'
