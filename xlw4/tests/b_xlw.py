"""
b_xlw.py -- tests and benchmarks for xlw4, the pure-Python .xlsx writer and reader.

The tests hold the interface of xlw (xlw.py of the old package) and what the rebuild changed:
the verbs, the styles, the file written, the file read back, the charts, and the tree. A file is
read back with a small stdlib reader written here (zipfile + ElementTree), independent of xlw4,
so a symmetric mistake in the writer and the reader of the package cannot hide. The benchmarks
time the verbs a caller pays for and the whole-book rows (build, save, open) of 10 000 and
100 000 cells, which are the figures to compare with xlw's.

Run from the project root:
    python tools/runbench.py xlw4/tests
"""

import os
import sys
import xml.etree.ElementTree as ET
import zipfile
from os.path import abspath, dirname, isdir, join


def findtools():                      # walk up to the folder that holds tools/, and put xlw4 on the path
    here = dirname(abspath(__file__))
    while here != dirname(here) and not isdir(join(here, 'tools')):
        here = dirname(here)
    sys.path.insert(0, join(here, 'tools'))
    sys.path.insert(0, dirname(dirname(abspath(__file__))))
    return here


ROOT = findtools()
from bench import bench

SOURCES = ['xlw', 'xlbook', 'xlcells', 'xlerrors', 'xlformat', 'xlpack', 'xlscatter', 'xltext', 'xltree']
from xlw import xlw, XlwError, XlwNoBook, XlwNoSheet, XlwBadArg, book_values, build_parts
from xltext import column, parse_xml, safe_name, tag, xml_text
Node = type(xlw().root.kvr('priv'))          # the plain tree node, as the tree of xlw4 holds it

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
NSR = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
OUTDIR = os.path.join(ROOT, 'results', 'b_xlw4')
FIXTURES = os.path.join(ROOT, 'tests', 'fixtures')


def readsheet(filename, sheet_name):
    """{(row, col): value} of one sheet, read with the standard library only."""
    with zipfile.ZipFile(filename) as archive:
        workbook = ET.fromstring(archive.read('xl/workbook.xml'))
        rels = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        target = {rel.get('Id'): rel.get('Target') for rel in rels}
        rid = [sheet.get(NSR + 'id') for sheet in workbook.iter(NS + 'sheet')
               if sheet.get('name') == sheet_name][0]
        strings = [''.join(t.text or '' for t in item.iter(NS + 't'))
                   for item in ET.fromstring(archive.read('xl/sharedStrings.xml')).iter(NS + 'si')]
        cells = {}
        for cell in ET.fromstring(archive.read('xl/' + target[rid])).iter(NS + 'c'):
            letters = ''.join(ch for ch in cell.get('r') if ch.isalpha())
            col = 0
            for ch in letters:
                col = col * 26 + ord(ch) - 64
            row = int(cell.get('r')[len(letters):])
            value = cell.find(NS + 'v')
            if value is None:
                cells[row, col] = None
            elif cell.get('t') == 's':
                cells[row, col] = strings[int(value.text)]
            elif cell.get('t') == 'b':
                cells[row, col] = value.text == '1'
            else:
                cells[row, col] = float(value.text)
        return cells


class Array:
    """What a numpy array offers xlw4: tolist()."""
    def __init__(me, rows):
        me.rows = rows

    def tolist(me):
        return me.rows


class Scalar:
    """What a numpy number offers xlw4: item() (and tolist())."""
    def __init__(me, value):
        me.value = value

    def item(me):
        return me.value

    def tolist(me):
        return me.value


def partext(filename, part):
    with zipfile.ZipFile(filename) as archive:
        return archive.read(part).decode('utf-8')


class b_xlw(bench):
    BenchName = 'xlw4'
    BenchVersion = 'M1.0.16'
    BenchHeader = ''
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        os.makedirs(OUTDIR, exist_ok=True)
        cls.size = 12
        xl = xlw()
        xl.newbook(cls.path('bench'), 'S1')
        for row in range(cls.size):
            for col in range(cls.size):
                xl.write(row * 100.0 + col + 0.5, 'Heading1') if (row + col) % 5 == 3 else \
                    xl.write(row * 100.0 + col + 0.5)
            xl.writeln()
        cls.sheet = xl.bench.S1
        cls.coords = [(r, c) for r in range(1, cls.size + 1) for c in range(1, cls.size + 1)]
        cls.table_10k = [[i * 0.001 + j for j in range(10)] for i in range(1000)]
        cls.table_100k = [[i * 0.001 + j for j in range(10)] for i in range(10000)]
        for name, table in (('speed10k', cls.table_10k), ('speed100k', cls.table_100k)):
            whole = xlw()
            whole.newbook(cls.path(name), 'Data')
            whole.write(table)
            whole.save()
            setattr(cls, name, whole)

    @classmethod
    def path(cls, name):
        return os.path.join(OUTDIR, name)

    def make(self, name='data'):
        """A fresh writer with book `name` (file results/b_xlw4/<name>.xlsx) and sheet 'S1'."""
        xl = xlw()
        xl.newbook(self.path(name), 'S1')
        return xl

    def saved(self, xl):
        """Save the active book and return its file name."""
        xl.save()
        return xl.root.kvr('priv').kvr('cursor').kvr('priv').kvr('fname')

    # ---- books and sheets --------------------------------------------------------------
    def test_T01_newbook_returns_a_book_node(self):
        book = xlw().newbook(self.path('b1'))
        self.assertEqual(book.type(), 'book')
        self.assertEqual(book.kvr('priv').kvr('sheets'), [])

    def test_T02_book_parent_is_root_and_sheet_parent_is_book(self):
        xl = self.make()
        self.assertEqual(xl.data.parent().type(), 'root')
        self.assertIs(xl.data.S1.parent(), xl.data)
        self.assertEqual(xl.data.S1.type(), 'sheet')

    def test_T03_extension_is_added_once_and_the_name_is_made_safe(self):
        xl = xlw()
        self.assertTrue(xl.newbook(self.path('x1')).kvr('priv').kvr('fname').endswith('x1.xlsx'))
        self.assertTrue(xl.newbook(self.path('x2.xlsx')).kvr('priv').kvr('fname').endswith('x2.xlsx'))
        self.assertFalse(xl.newbook(self.path('x2.xlsx')).kvr('priv').kvr('fname').endswith('.xlsx.xlsx'))
        book = xl.newbook(self.path('my book-1'))
        self.assertIs(xl.my_book_1, book)

    def test_T04_two_books_last_is_active_and_activate_by_name_or_node(self):
        xl = xlw()
        first = xl.newbook(self.path('a1'), 'A')
        xl.newbook(self.path('a2'), 'B')
        xl.write('in b')
        self.assertEqual(xl.a2.B.cell(1, 1), 'in b')
        xl.activate('a1').write('in a')
        self.assertEqual(first.A.cell(1, 1), 'in a')
        xl.activate(xl.a2).write('again')
        self.assertEqual(xl.a2.B.cell(1, 2), 'again')

    def test_T05_activate_cascades_from_a_sheet(self):
        xl = xlw()
        xl.newbook(self.path('c1'), 'S1', 'S2')
        xl.newbook(self.path('c2'), 'T1')
        xl.c1.S2.activate()
        xl.write('x')
        self.assertEqual(xl.c1.S2.cell(1, 1), 'x')

    def test_T06_newsheet_returns_the_sheet_and_records_names_in_order(self):
        xl = self.make()
        sheet = xl.newsheet('Beta')
        self.assertEqual(sheet.type(), 'sheet')
        self.assertEqual(xl.data.kvr('priv').kvr('sheets'), ['S1', 'Beta'])
        self.assertEqual(xl.data.kvr('priv').kvr('sheetkeys'), ['S1', 'Beta'])
        self.assertEqual(sheet.kvr('priv').kvr('cursor'), [1, 1])
        self.assertTrue(sheet.kvr('showGrid'))

    def test_T07_newsheet_refusals(self):
        xl = self.make()
        with self.assertRaises(XlwBadArg):
            xl.newsheet('S1')
        with self.assertRaises(XlwBadArg):
            xl.newsheet()
        with self.assertRaises(XlwBadArg):
            xl.newsheet('write')
        with self.assertRaises(XlwBadArg):
            xl.newsheet('priv')

    def test_T08_a_book_by_attribute_and_unknown_names(self):
        xl = xlw()
        book = xl.newbook(self.path('route'))
        self.assertIs(xl.route, book)
        with self.assertRaises(XlwNoBook):
            xl.nosuchbook
        with self.assertRaises(XlwNoBook):
            xlw().activate('nothing')
        with self.assertRaises(XlwBadArg):
            xl.activate(xl.root)

    def test_T09_a_verb_without_a_book_is_refused_and_a_bad_call_is_a_type_error(self):
        with self.assertRaises(XlwNoBook):
            xlw().write('x')
        with self.assertRaises(TypeError):
            xlw().newbook()

    def test_T10_sheet_one_is_made_when_a_book_has_none(self):
        xl = xlw()
        book = xl.newbook(self.path('auto'))
        xl.write('x')
        self.assertEqual(book.kvr('priv').kvr('sheets'), ['Sheet1'])
        self.assertEqual(book.Sheet1.cell(1, 1), 'x')

    def test_T11_the_error_family(self):
        for kind in (XlwNoBook, XlwNoSheet, XlwBadArg):
            self.assertTrue(issubclass(kind, XlwError))

    # ---- write -----------------------------------------------------------------------------
    def test_T12_write_values_and_cursor(self):
        sheet = self.make().data.S1
        sheet.write('hello').write(3.14).write(True).write(None).write('')
        self.assertEqual([sheet.cell(1, c) for c in range(1, 6)], ['hello', 3.14, True, None, None])
        self.assertIs(sheet.cell(1, 3), True)
        self.assertEqual(sheet.kvr('priv').kvr('cursor'), [1, 6])
        self.assertIs(sheet.write('x'), sheet)

    def test_T13_write_blocks(self):
        sheet = self.make().data.S1
        sheet.write([[1, 2, 3], [4, 5, 6]])
        self.assertEqual([sheet.cell(2, c) for c in (1, 2, 3)], [4, 5, 6])
        self.assertEqual(sheet.kvr('priv').kvr('cursor'), [1, 4])
        sheet.writeln().write([True, False, True])
        self.assertIs(sheet.cell(2, 2), False)
        self.assertEqual(sheet.kvr('priv').kvr('cursor'), [2, 4])
        sheet.write([])
        self.assertEqual(sheet.kvr('priv').kvr('cursor'), [2, 4])

    def test_T14_write_array_likes(self):
        """Anything with tolist() is a block and anything with item() is a scalar: what numpy
        arrays and numpy numbers have (tried with real numpy in tests/z_sandbox/equiv_xlw_xlw4.py)."""
        sheet = self.make().data.S1
        sheet.write(Array([[1.5, 2.5], [3.5, 4.5]]))
        self.assertEqual(sheet.cell(2, 2), 4.5)
        sheet.writeln().write(Scalar(7.25)).write(Scalar(3)).write(Scalar(True))
        self.assertEqual([sheet.cell(2, c) for c in (1, 2, 3)], [7.25, 3, True])
        self.assertIsInstance(sheet.cell(2, 1), float)

    def test_T15_write_refusals(self):
        xl = self.make()
        with self.assertRaises(XlwBadArg):
            xl.write({'a': 1})
        with self.assertRaises(XlwBadArg):
            xl.write()

    def test_T16_writeln_nl_blankRow(self):
        sheet = self.make().data.S1
        sheet.write('a').writeln()
        self.assertEqual(sheet.kvr('priv').kvr('cursor'), [2, 1])
        sheet.writeln('b').nl().blankRow().write('c')
        self.assertEqual(sheet.cell(2, 1), 'b')
        self.assertEqual(sheet.kvr('priv').kvr('cursor'), [5, 2])
        self.assertEqual(sheet.cell(5, 1), 'c')

    def test_T17_move(self):
        sheet = self.make().data.S1
        sheet.write('x').write('y').move('down', 2).move('right').move('up', 9).move('left', 9)
        self.assertEqual(sheet.kvr('priv').kvr('cursor'), [1, 1])
        sheet.move('down', 3).move('right', 4)
        self.assertEqual(sheet.kvr('priv').kvr('cursor'), [4, 5])
        sheet.move('cr')
        self.assertEqual(sheet.kvr('priv').kvr('cursor'), [4, 1])
        sheet.move('home')
        self.assertEqual(sheet.kvr('priv').kvr('cursor'), [1, 1])
        sheet.write('a').writeln().write('b').move('btm')
        self.assertEqual(sheet.kvr('priv').kvr('cursor'), [3, 1])
        with self.assertRaises(XlwBadArg):
            sheet.move('sideways')

    def test_T18_move_btm_on_an_empty_sheet_is_row_one(self):
        sheet = self.make().data.S1
        self.assertEqual(sheet.move('btm').kvr('priv').kvr('cursor'), [1, 1])

    def test_T19_gridlines(self):
        sheet = self.make().data.S1
        self.assertIs(sheet.gridlines(False), sheet)
        self.assertIs(sheet.kvr('showGrid'), False)
        sheet.gridlines(True)
        self.assertIs(sheet.kvr('showGrid'), True)

    def test_T20_verbs_called_on_every_kind_of_node_reach_the_sheet(self):
        xl = self.make()
        xl.data.write('from book')
        xl.root.write('from root')
        xl.data.S1.write('from sheet')
        self.assertEqual([xl.data.S1.cell(1, c) for c in (1, 2, 3)], ['from book', 'from root', 'from sheet'])
        xl.data.S1.newsheet('Other')
        self.assertEqual(xl.data.kvr('priv').kvr('sheets'), ['S1', 'Other'])
        xl.data.S1.newstyle('viaSheet', 'bold', True)
        self.assertTrue(xl.data.kvr('priv').kvr('styles')['viaSheet']['bold'])

    def test_T21_chain_across_xlw_verbs(self):
        xl = self.make()
        out = xl.write('a').write('b').writeln().write('c').move('right').write('e')
        self.assertIs(out, xl)
        self.assertEqual(xl.data.S1.cell(2, 3), 'e')

    # ---- styles --------------------------------------------------------------------------
    def test_T22_named_style_and_override(self):
        sheet = self.make().data.S1
        sheet.write('x', 'Heading1').write('y', 'Heading1', 'sz', 20)
        self.assertEqual(sheet.cell(1, 1, 'style'), {'sz': 15, 'bold': True})
        self.assertEqual(sheet.cell(1, 2, 'style'), {'sz': 20, 'bold': True})

    def test_T23_new_style_is_stored_and_used(self):
        xl = self.make()
        xl.newstyle('myHdr', 'bold', True, 'sz', 16, 'fill', 'FF0000')
        xl.data.S1.write('x', 'myHdr')
        self.assertEqual(xl.data.S1.cell(1, 1, 'style'), {'sz': 16, 'bold': True, 'fill': 'FF0000'})
        xl.data.newstyle('book only', 'italic', True)
        xl.write('y', 'book_only')
        self.assertTrue(xl.data.S1.cell(1, 2, 'style')['italic'])
        xl.newbook(self.path('other'), 'S1')
        xl.write('z', 'book_only')
        self.assertEqual(xl.other.S1.cell(1, 1, 'style'), {})

    def test_T24_new_style_on_a_named_base(self):
        xl = self.make()
        xl.newstyle('bigGood', 'Good', 'sz', 20)
        xl.write('x', 'bigGood')
        self.assertEqual(xl.data.S1.cell(1, 1, 'style'), {'sz': 20, 'fill': 'C6EFCE', 'color': '006100'})

    def test_T25_keyword_style(self):
        xl = self.make()
        xl.write('x', bold=True, fill='yellow')
        self.assertEqual(xl.data.S1.cell(1, 1, 'style'), {'bold': True, 'fill': 'FFFF00'})

    def test_T26_numbers_get_a_format_that_shows_their_significant_figures(self):
        sheet = self.make().data.S1
        for value in (42, 1234.0, 3.14159, 12345.678, 0.0012, 1234567.89, 0.0, 0.5, 25.5):
            sheet.write(value)
        formats = [sheet.cell(1, c, 'style').get('numfmt', '') for c in range(1, 10)]
        self.assertEqual(formats, ['0', '0', '0.##', '0', '0.##E+00', '0.##E+00', '', '0.###', '0.#'])
        sheet.writeln().write(3.14159, 'numfmt', '0.0000')
        self.assertEqual(sheet.cell(2, 1, 'style')['numfmt'], '0.0000')

    def test_T27_property_forms(self):
        sheet = self.make().data.S1
        sheet.write('a', 'underline', True).write('b', 'strikethrough', True)
        sheet.write('c', 'rotation', 45).write('d', 'indent', 2).write('e', 'halign', 'center')
        self.assertTrue(sheet.cell(1, 1, 'style')['underline'])
        self.assertTrue(sheet.cell(1, 2, 'style')['strikethrough'])
        self.assertEqual(sheet.cell(1, 3, 'style')['rotation'], 45)
        self.assertEqual(sheet.cell(1, 4, 'style')['indent'], 2)
        self.assertEqual(sheet.cell(1, 5, 'style')['halign'], 'center')
        self.assertEqual(sheet.cell(1, 1, 'style').get('valign'), None)

    def test_T28_colour_forms(self):
        sheet = self.make().data.S1
        for spec in ('red', '#ff0080', 'f08', (1, 0.5, 0), [255, 204, 153], 'ff0000'):
            sheet.write('x', 'color', spec)
        self.assertEqual([sheet.cell(1, c, 'style')['color'] for c in range(1, 7)],
                         ['FF0000', 'FF0080', 'FF0088', 'FF8000', 'FFCC99', 'FF0000'])
        self.assertEqual(sheet.cell(1, 1, 'style'), {'color': 'FF0000'})

    def test_T29_border_forms(self):
        sheet = self.make().data.S1
        sheet.write('a', 'border', 'all:thin').write('b', 'border', 'n:medium,s:double', 'bcolor', 'FF0000')
        self.assertEqual(sheet.cell(1, 1, 'style')['border'],
                         (('n', 'thin', '000000'), ('s', 'thin', '000000'), ('e', 'thin', '000000'),
                          ('w', 'thin', '000000')))
        self.assertEqual(sheet.cell(1, 2, 'style')['border'],
                         (('n', 'medium', 'FF0000'), ('s', 'double', 'FF0000')))

    def test_T30_border_verb_keeps_values_and_makes_blank_cells(self):
        sheet = self.make().data.S1
        sheet.write('keep', 'bold', True)
        self.assertIs(sheet.border([(1, 1), (3, 3)], 'all:thin', 'color', 'blue'), sheet)
        self.assertEqual(sheet.cell(1, 1), 'keep')
        style = sheet.cell(1, 1, 'style')
        self.assertTrue(style['bold'])
        self.assertEqual(len(style['border']), 4)
        self.assertEqual(style['bcolor'], '0000FF')
        self.assertIsNone(sheet.cell(3, 3))
        self.assertEqual(len(sheet.cell(3, 3, 'style')['border']), 4)
        sheet.border([(5, 5)], 'n:thin')
        self.assertNotIn('bcolor', sheet.cell(5, 5, 'style'))

    def test_T31_cell_reader_refuses_an_unknown_question(self):
        with self.assertRaises(XlwBadArg):
            self.make().data.S1.cell(1, 1, 'colour')

    # ---- formulas ---------------------------------------------------------------------------
    def test_T32_formula_cells(self):
        xl = self.make()
        xl.write(1.5).write(2.5).formula('=SUM(A1:B1)', cached=4.0).formula('A1&"x"', cached='1.5x')
        sheet = xl.data.S1
        self.assertEqual(sheet.cell(1, 3), 4.0)
        self.assertEqual(sheet.cell(1, 3, 'formula'), 'SUM(A1:B1)')
        self.assertEqual(sheet.cell(1, 4), '1.5x')
        self.assertIsNone(sheet.cell(1, 1, 'formula'))
        self.assertEqual(sheet.kvr('priv').kvr('cursor'), [1, 5])

    def test_T33_formula_without_a_cached_value_asks_for_a_calculation(self):
        xl = self.make()
        xl.write(1).formula('=A1*2', 'bold', True)
        fname = self.saved(xl)
        self.assertIn('fullCalcOnLoad="1"', partext(fname, 'xl/workbook.xml'))
        self.assertIn('<f>A1*2</f></c>', partext(fname, 'xl/worksheets/sheet1.xml'))
        xl2 = self.make('data2')
        xl2.write(1).formula('=A1*2', cached=2)
        self.assertNotIn('fullCalcOnLoad', partext(self.saved(xl2), 'xl/workbook.xml'))

    # ---- the file written ---------------------------------------------------------------
    def test_T34_save_creates_all_parts_and_each_is_well_formed(self):
        xl = self.make()
        xl.write('Name').write(42).writeln().write(True)
        fname = self.saved(xl)
        with zipfile.ZipFile(fname) as archive:
            names = archive.namelist()
            for name in names:
                ET.fromstring(archive.read(name))
        for part in ('[Content_Types].xml', '_rels/.rels', 'xl/workbook.xml', 'xl/_rels/workbook.xml.rels',
                     'xl/styles.xml', 'xl/sharedStrings.xml', 'xl/worksheets/sheet1.xml'):
            self.assertIn(part, names)
        self.assertEqual(readsheet(fname, 'S1'), {(1, 1): 'Name', (1, 2): 42.0, (2, 1): True})

    def test_T35_save_refusals_and_forms(self):
        xl = xlw()
        xl.newbook(self.path('empty'))
        with self.assertRaises(XlwNoSheet):
            xl.save()
        with self.assertRaises(XlwNoBook):
            xlw().save()
        one = self.make('s1')
        one.write(1)
        two = xlw()
        two.newbook(self.path('s2'), 'A').write(2)
        two.newbook(self.path('s3'), 'A').write(3)
        two.save('all')
        two.save('s2')
        two.save([two.s2, 's3'])
        two.save(two.s3)
        for name, value in (('s2', 2.0), ('s3', 3.0)):
            self.assertEqual(readsheet(self.path(name) + '.xlsx', 'A')[(1, 1)], value)

    def test_T36_multi_sheet_workbook_lists_the_sheets_in_order_and_escapes_names(self):
        xl = self.make()
        xl.newsheet('Alpha & <Beta>')
        xl.write('in second')
        fname = self.saved(xl)
        names = [sheet.get('name') for sheet in ET.fromstring(partext(fname, 'xl/workbook.xml')).iter(NS + 'sheet')]
        self.assertEqual(names, ['S1', 'Alpha & <Beta>'])
        self.assertEqual(readsheet(fname, 'Alpha & <Beta>')[(1, 1)], 'in second')

    def test_T37_shared_strings_are_deduplicated_and_odd_text_survives(self):
        xl = self.make()
        for text in ('a', 'b', 'a', 'a', '[x]', '\x01raw', 'a\x00b', 'tab\there'):
            xl.write(text)
        fname = self.saved(xl)
        count = partext(fname, 'xl/sharedStrings.xml').count('<si>')
        self.assertEqual(count, 6)
        cells = readsheet(fname, 'S1')
        self.assertEqual([cells[1, c] for c in range(1, 9)], ['a', 'b', 'a', 'a', '[x]', 'raw', 'ab', 'tab\there'])

    def test_T38_non_finite_numbers_are_blank_and_precision_is_kept(self):
        xl = self.make()
        xl.write(float('nan')).write(float('inf')).write(1 / 3).write(1e-300).write(123456789012345.0)
        cells = readsheet(self.saved(xl), 'S1')
        self.assertIsNone(cells[1, 1])
        self.assertIsNone(cells[1, 2])
        self.assertEqual(cells[1, 3], 1 / 3)
        self.assertEqual(cells[1, 4], 1e-300)
        self.assertEqual(cells[1, 5], 123456789012345.0)

    def test_T39_gridlines_and_column_widths_reach_the_sheet_xml(self):
        xl = self.make()
        xl.write('x').write('a much longer piece of text here').gridlines(False)
        fname = self.saved(xl)
        text = partext(fname, 'xl/worksheets/sheet1.xml')
        self.assertIn('showGridLines="0"', text)
        self.assertIn('<col min="1" max="1" width="', text)
        widths = [int(float(col.get('width'))) for col in ET.fromstring(text).iter(NS + 'col')]
        self.assertEqual(widths[0], 4)
        self.assertGreater(widths[1], 30)

    def test_T40_rows_and_cells_are_in_order_whatever_the_write_order(self):
        xl = self.make()
        xl.write('c')
        xl.move('home').move('down', 4).write('late')
        xl.move('home').move('right', 4).write('early')
        refs = [cell.get('r') for cell in ET.fromstring(
            partext(self.saved(xl), 'xl/worksheets/sheet1.xml')).iter(NS + 'c')]
        self.assertEqual(refs, ['A1', 'E1', 'A5'])

    def test_T41_style_dedup_gives_one_xf_per_distinct_style_and_xf_zero_is_the_default(self):
        xl = self.make()
        xl.write('plain', 'bold', True).write('x').write('y', 'bold', True)
        for _ in range(20):
            xl.write('z', 'bold', True, 'italic', True)
        fname = self.saved(xl)
        styles = ET.fromstring(partext(fname, 'xl/styles.xml'))
        xfs = styles.find(NS + 'cellXfs').findall(NS + 'xf')
        self.assertEqual(len(xfs), 3)
        self.assertEqual([xfs[0].get(key) for key in ('fontId', 'fillId', 'borderId', 'numFmtId')], ['0'] * 4)
        sheet = partext(fname, 'xl/worksheets/sheet1.xml')
        self.assertIn('<c r="A1" s="1"', sheet)
        self.assertIn('<c r="B1" s="0"', sheet)

    def test_T42_style_properties_reach_styles_xml(self):
        xl = self.make()
        xl.write('u', 'underline', True).write('k', 'strikethrough', True).write(7, 'rotation', -30)
        xl.write('i', 'indent', 3).write('w', 'wrap', True, 'halign', 'center', 'valign', 'bottom')
        xl.write('b', 'border', 'n:medium,s:double', 'bcolor', 'FF0000').write('f', 'fill', 'C6EFCE', 'font', 'Cambria')
        styles = partext(self.saved(xl), 'xl/styles.xml')
        for text in ('<u/>', '<strike/>', 'textRotation="120"', 'indent="3"', 'wrapText="1"',
                     'horizontal="center"', 'vertical="bottom"', '<top style="medium"', '<bottom style="double"',
                     'FFFF0000', 'applyBorder="1"', '<name val="Cambria"/>', 'FFC6EFCE',
                     '<border><left/><right/><top style="medium"><color rgb="FFFF0000"/></top>'):   # left right top bottom
            self.assertIn(text, styles)

    def test_T43_custom_number_formats_have_ids_from_164_and_builtin_ones_keep_theirs(self):
        xl = self.make()
        xl.write(0.0012).write(2.5).write(3, 'numfmt', '0.00%').write(4, 'numfmt', '#,##0.00').write(5, 'numfmt', 'yy')
        root = ET.fromstring(partext(self.saved(xl), 'xl/styles.xml'))
        custom = {fmt.get('formatCode'): int(fmt.get('numFmtId')) for fmt in root.iter(NS + 'numFmt')}
        self.assertEqual(sorted(custom.values()), list(range(164, 164 + len(custom))))
        self.assertIn('0.##E+00', custom)
        self.assertIn('yy', custom)
        self.assertNotIn('0.00%', custom)
        ids = {xf.get('numFmtId') for xf in root.find(NS + 'cellXfs')}
        self.assertTrue({'10', '4'} <= ids)

    def test_T44_a_larger_sheet_saves_and_reads_back(self):
        xl = self.make()
        table = [[row * 10.0 + col for col in range(8)] for row in range(200)]
        xl.write(table)
        cells = readsheet(self.saved(xl), 'S1')
        self.assertEqual(len(cells), 1600)
        self.assertEqual(cells[200, 8], 1997.0)

    def test_T45_build_parts_lists_what_save_writes(self):
        xl = self.make()
        xl.write('a').write(1.5)
        fname = self.saved(xl)
        parts = build_parts(xl.data)
        with zipfile.ZipFile(fname) as archive:
            self.assertEqual([name for name, _ in parts], archive.namelist())
            self.assertEqual(parts[-1][1].encode('utf-8'),
                             archive.read(parts[-1][0])[archive.read(parts[-1][0]).index(b'?>') + 2:])

    # ---- the file read back --------------------------------------------------------------
    def roundtrip(self, xl):
        """Save the active book, read the file with xlw4 and return the new book."""
        fname = self.saved(xl)
        return xlw().open(fname)

    def test_T46_open_gives_the_same_cells_styles_and_formulas(self):
        xl = self.make()
        xl.write('title', 'Heading1').write(3.25).write(True).write(None).writeln()
        xl.write([[1, 2.5], ['a', 'b']]).formula('=SUM(A2:B2)', cached=3.5).write('x', 'border', 'all:thin', 'fill', 'red')
        xl.newsheet('Second').write('other sheet')
        book = self.roundtrip(xl)
        for name in ('S1', 'Second'):
            old, new = xl.data.kvr(name), book.kvr(name)
            kept = [key for key in sorted(old.kvr('cells').cells) if old.cell(*key) is not None or old.cell(*key, 'style')]
            self.assertEqual(kept, sorted(new.kvr('cells').cells))      # an unstyled blank cell is not read
            for row, col in kept:
                self.assertEqual(old.cell(row, col), new.cell(row, col))
                self.assertEqual(old.cell(row, col, 'formula'), new.cell(row, col, 'formula'))
                self.assertEqual({k: v for k, v in old.cell(row, col, 'style').items() if k != 'valign'},
                                 {k: v for k, v in new.cell(row, col, 'style').items() if k != 'valign'})
        self.assertEqual(book.kvr('priv').kvr('sheets'), ['S1', 'Second'])
        self.assertEqual(book.kvr('priv').kvr('unmapped'), [])

    def test_T47_open_saves_beside_the_source_never_over_it(self):
        xl = self.make('src')
        xl.write(1)
        fname = self.saved(xl)
        book = xlw().open(fname)
        self.assertTrue(book.kvr('priv').kvr('fname').endswith('src_xlw.xlsx'))
        named = xlw().open(fname, 'renamed')
        self.assertTrue(named.kvr('priv').kvr('fname').endswith('renamed_xlw.xlsx'))
        book.save()
        self.assertTrue(os.path.isfile(self.path('src_xlw') + '.xlsx'))

    def test_T48_read_class_method_returns_an_xlw_with_the_book_active(self):
        xl = self.make('readme')
        xl.write('seen')
        fname = self.saved(xl)
        again = xlw().read(fname)
        self.assertEqual(again.readme_xlw.S1.cell(1, 1), 'seen')
        again.move('btm').write('more')
        self.assertEqual(again.readme_xlw.S1.cell(2, 1), 'more')

    def test_T49_a_file_made_by_excel_is_read(self):
        for name in sorted(os.listdir(FIXTURES)):
            if not name.endswith('.xlsx'):
                continue
            book = xlw().open(os.path.join(FIXTURES, name), 'fx')
            sheets = book.kvr('priv').kvr('sheets')
            self.assertGreaterEqual(len(sheets), 1, name)
            self.assertGreater(sum(len(book.kvr(key).kvr('cells').cells) for key in book.kvr('priv').kvr('sheetkeys')), 0, name)

    def test_T50_open_notes_what_it_cannot_read(self):
        xl = self.make('notes')
        xl.write(1)
        fname = self.saved(xl)
        with zipfile.ZipFile(fname) as source:
            parts = {name: source.read(name) for name in source.namelist()}
        parts['xl/worksheets/sheet1.xml'] = parts['xl/worksheets/sheet1.xml'].replace(
            b'</worksheet>', b'<oddElement/></worksheet>')
        parts['xl/pivotTables/pivotTable1.xml'] = b'<x/>'
        odd = self.path('odd') + '.xlsx'
        with zipfile.ZipFile(odd, 'w') as target:
            for name, data in parts.items():
                target.writestr(name, data)
        notes = xlw().open(odd).kvr('priv').kvr('unmapped')
        self.assertIn('worksheet element oddElement was not read', notes)
        self.assertIn('pivot tables were not read', notes)

    def test_T51_cells_of_unusual_form_are_read_by_the_general_route(self):
        xl = self.make('unusual')
        xl.write(1).write('x')
        fname = self.saved(xl)
        with zipfile.ZipFile(fname) as source:
            parts = {name: source.read(name) for name in source.namelist()}
        sheet = parts['xl/worksheets/sheet1.xml'].decode('utf-8')
        sheet = sheet.replace('</row>', '<c r="C1" t="inlineStr"><is><r><t>rich </t></r><r><t>text</t></r></is></c>'
                              '<c r="D1" t="str"><v>a &amp; b</v></c><c r="E1" t="b"><v>1</v></c></row>')
        parts['xl/worksheets/sheet1.xml'] = sheet.encode('utf-8')
        odd = self.path('unusual2') + '.xlsx'
        with zipfile.ZipFile(odd, 'w') as target:
            for name, data in parts.items():
                target.writestr(name, data)
        book = xlw().open(odd)
        self.assertEqual([book.S1.cell(1, c) for c in range(1, 6)], [1.0, 'x', 'rich text', 'a & b', True])

    def test_T52_book_values_reads_a_range_row_major(self):
        xl = self.make()
        xl.write([[1, 'a'], [2, None], [3, 4.5]])
        values = book_values(xl.data)
        self.assertEqual(values('S1!$A$1:$B$3'), [1, 'a', 2, None, 3, 4.5])
        self.assertEqual(values('S1!$B$3'), [4.5])
        self.assertEqual(values('Nope!$A$1'), [])
        self.assertEqual(values('not a reference'), [])

    # ---- charts ----------------------------------------------------------------------------
    def chart_book(self):
        """A book with data and one chart that uses most of the definition."""
        xl = self.make('charty')
        xl.write(['t', 'a', 'b']).writeln()
        xl.write([[0.0, 1.0, 10.0], [1.0, 2.0, 20.0], [2.0, 3.0, 40.0]])
        chart = xl.chart('conc')
        chart.title.text = 'Concentration'
        chart.xaxis.title.text = 'time (s)'
        chart.yaxis.log = 10
        chart.yaxis.min = 1
        chart.yaxis.crossesat = 5
        chart.legend.pos = 'r'
        chart.add_series(chart.ref('S1', 2, 1, 4, 1), chart.ref('S1', 2, 2, 4, 2), label='A',
                         line=dict(color='C00000', width=2), marker=dict(symbol='square', size=7))
        second = chart.add_series(chart.ref('S1', 2, 1, 4, 1), [10, 20, 40], labelref='S1!$C$1', axis=2, smooth=True)
        second.trend.fit = 'poly'
        second.trend.order = 3
        second.trend.rsq = True
        second.yerr.mode = 'fixed'
        second.yerr.value = 2
        second.labels.showy = True
        chart.place(4, 1, ncols=8, nrows=15)
        return xl, chart

    def test_T53_chart_nodes_follow_chartdef(self):
        xl = self.make()
        chart = xl.chart('c one')
        self.assertEqual(chart.type(), 'chart')
        self.assertIsNone(chart.kvr('title'))
        chart.title.text = 'T'
        self.assertEqual(chart.kvr('title.text'), 'T')
        self.assertEqual(xl.data.S1.kvr('priv').kvr('charts').kvr('c_one'), chart)
        self.assertEqual(xl.chart().name, 'chart2')
        self.assertEqual(chart.kvr('series').count(), 0)

    def test_T54_ref_and_parse_ref(self):
        chart = self.make().chart()
        self.assertEqual(chart.ref('Data', 2, 1, 100, 1), 'Data!$A$2:$A$100')
        self.assertEqual(chart.ref('My Sheet', 1, 28), "'My Sheet'!$AB$1")
        self.assertEqual(chart.ref("it's", 1, 1, 2, 2), "'it''s'!$A$1:$B$2")
        self.assertEqual(chart.parse_ref("'My Sheet'!$B$2:$B$9"), ('My Sheet', 2, 2, 9, 2))
        self.assertEqual(chart.parse_ref("'it''s'!A1"), ("it's", 1, 1, 1, 1))
        self.assertIsNone(chart.parse_ref('A1'))
        self.assertIsNone(chart.parse_ref(5))

    def test_T55_add_series_place_and_records(self):
        chart = self.make().chart()
        node = chart.add_series('S1!$A$1:$A$3', [1, 2, 3], label='L', line={'color': 'FF0000'}, axis=2)
        self.assertEqual(node.kvr('line').kvr('color'), 'FF0000')
        self.assertEqual(node.kvr('axis'), 2)
        self.assertEqual(chart.kvr('series').count(), 1)
        chart.place(3, 2)
        self.assertEqual(chart.corner(), (3, 0, 2, 0, 12, 0, 20, 0))
        self.assertEqual(chart.rec(a=1, b=None).keys(), ['a'])

    def test_T56_unplaced_charts_go_beside_the_data_and_below_each_other(self):
        chart = self.make().chart()
        self.assertEqual(chart.corner(5, 0), (6, 0, 1, 0, 15, 0, 19, 0))
        self.assertEqual(chart.corner(5, 1), (6, 0, 21, 0, 15, 0, 39, 0))

    def test_T57_chart_parts_are_written_in_the_order_excel_demands(self):
        xl, _ = self.chart_book()
        fname = self.saved(xl)
        with zipfile.ZipFile(fname) as archive:
            names = archive.namelist()
            for name in ('xl/charts/chart1.xml', 'xl/drawings/drawing1.xml', 'xl/worksheets/_rels/sheet1.xml.rels',
                         'xl/drawings/_rels/drawing1.xml.rels'):
                self.assertIn(name, names)
        text = partext(fname, 'xl/charts/chart1.xml')
        root = ET.fromstring(text)
        c = '{http://schemas.openxmlformats.org/drawingml/2006/chart}'
        chart = root.find(c + 'chart')
        self.assertEqual([child.tag[len(c):] for child in chart], ['title', 'autoTitleDeleted', 'plotArea', 'legend',
                                                                  'plotVisOnly', 'dispBlanksAs'])
        plot = chart.find(c + 'plotArea')
        self.assertEqual([child.tag[len(c):] for child in plot],
                         ['layout', 'scatterChart', 'scatterChart', 'valAx', 'valAx', 'valAx', 'valAx', 'spPr'])
        series = [ser for ser in plot.iter(c + 'ser')]
        self.assertEqual([ser.find(c + 'idx').get('val') for ser in series], ['0', '1'])
        self.assertEqual([child.tag[len(c):] for child in series[1]],
                         ['idx', 'order', 'tx', 'spPr', 'marker', 'dLbls', 'trendline', 'errBars', 'xVal', 'yVal', 'smooth'])
        self.assertIn('<c:pt idx="2"><c:v>3</c:v></c:pt>', text)
        self.assertIn('<c:crossesAt val="5"/>', text)
        self.assertIn('<c:logBase val="10"/>', text)

    def test_T58_a_chart_reads_back_as_the_same_definition(self):
        xl, chart = self.chart_book()
        again = self.roundtrip(xl).S1.kvr('priv').kvr('charts').nodes()[0]
        self.assertEqual(again.kvr('title.text'), 'Concentration')
        self.assertEqual(again.kvr('xaxis.title.text'), 'time (s)')
        self.assertEqual(again.kvr('yaxis.log'), 10)
        self.assertEqual(again.kvr('yaxis.min'), 1)
        self.assertEqual(again.kvr('yaxis.crossesat'), 5)
        self.assertEqual(again.kvr('legend.pos'), 'r')
        self.assertEqual(again.kvr('anchor.col'), 4)
        self.assertEqual(again.kvr('anchor.row2'), 16)
        first, second = again.kvr('series').nodes()
        self.assertEqual((first.kvr('x'), first.kvr('y'), first.kvr('label')), ('S1!$A$2:$A$4', 'S1!$B$2:$B$4', 'A'))
        self.assertEqual((first.kvr('line.color'), first.kvr('line.width')), ('C00000', 2.0))
        self.assertEqual((first.kvr('marker.symbol'), first.kvr('marker.size')), ('square', 7))
        self.assertEqual(second.kvr('y'), [10.0, 20.0, 40.0])
        self.assertEqual(second.kvr('labelref'), 'S1!$C$1')
        self.assertEqual(second.kvr('axis'), 2)
        self.assertTrue(second.kvr('smooth'))
        self.assertEqual((second.kvr('trend.fit'), second.kvr('trend.order')), ('poly', 3))
        self.assertTrue(second.kvr('trend.rsq'))
        self.assertEqual((second.kvr('yerr.mode'), second.kvr('yerr.value')), ('fixed', 2.0))
        self.assertTrue(second.kvr('labels.showy'))

    def test_T59_the_chart_written_by_a_read_chart_is_the_same_text(self):
        xl, _ = self.chart_book()
        fname = self.saved(xl)
        again = xlw().open(fname)
        again.save()
        first = partext(fname, 'xl/charts/chart1.xml')
        second = partext(again.kvr('priv').kvr('fname'), 'xl/charts/chart1.xml')
        self.assertEqual(first, second)

    def test_T60_chart_styles_and_defaults(self):
        xl = self.make()
        for style in ('marker', 'smooth', 'line', 'none'):
            chart = xl.chart()
            chart.style = style
            chart.add_series([1, 2], [3, 4])
        text = [partext(self.saved(xl), f'xl/charts/chart{n}.xml') for n in (1, 2, 3, 4)]
        self.assertIn('<a:ln w="28575"><a:noFill/></a:ln>', text[0])
        self.assertIn('<c:smooth val="1"/>', text[1])
        self.assertIn('<c:symbol val="none"/>', text[2])
        self.assertIn('<c:scatterStyle val="none"/>', text[3])
        self.assertIn('<c:autoTitleDeleted val="1"/>', text[0])

    def test_T61_chart_less_book_has_no_drawing_parts(self):
        with zipfile.ZipFile(self.saved(self.make().write(1))) as archive:
            self.assertFalse([name for name in archive.namelist() if 'chart' in name or 'drawing' in name])

    def test_T62_two_sheets_with_charts_number_parts_through_the_book(self):
        xl = self.make()
        xl.chart().add_series([1], [2])
        xl.newsheet('S2')
        xl.chart().add_series([1], [2])
        xl.chart().add_series([1], [3])
        with zipfile.ZipFile(self.saved(xl)) as archive:
            names = archive.namelist()
        for name in ('xl/charts/chart3.xml', 'xl/drawings/drawing2.xml', 'xl/worksheets/_rels/sheet2.xml.rels'):
            self.assertIn(name, names)

    def test_T63_chart_text_runs_secondary_axes_and_theme_colours_round_trip(self):
        xl = self.make()
        chart = xl.chart('rich')
        chart.title.text = [('H', {}), ('2', {'baseline': -25}), ('O', {'bold': True, 'height': 12})]
        chart.title.font = chart.rec(name='Cambria', height=16, color='theme:tx1:65000:35000')
        chart.x2axis.visible = True
        chart.y2axis.gridmajor = chart.rec(color='EEEEEE', width=0.5)
        chart.chartarea.fill = chart.rec(color='sys:window:FFFFFF')
        chart.add_series([1, 2], [3, 4])
        chart.add_series([1, 2], [5, 6], axis=2)
        again = self.roundtrip(xl).S1.kvr('priv').kvr('charts').nodes()[0]
        self.assertEqual(again.kvr('title.text'), [('H', {}), ('2', {'baseline': -25.0}),
                                                   ('O', {'bold': True, 'height': 12.0})])
        self.assertEqual(again.kvr('title.font.color'), 'theme:tx1:65000:35000')
        self.assertEqual(again.kvr('title.font.name'), 'Cambria')
        self.assertTrue(again.kvr('x2axis.visible'))
        self.assertEqual(again.kvr('y2axis.gridmajor.color'), 'EEEEEE')
        self.assertEqual(again.kvr('chartarea.fill.color'), 'sys:window:FFFFFF')

    def test_T64_a_chart_with_formulas_data_reads_the_cached_values(self):
        xl = self.make()
        xl.write(1.0).writeln().formula('=A1*2', cached=2.0)
        chart = xl.chart()
        chart.add_series(chart.ref('S1', 1, 1, 2, 1), chart.ref('S1', 1, 1, 2, 1))
        text = partext(self.saved(xl), 'xl/charts/chart1.xml')
        self.assertIn('<c:pt idx="1"><c:v>2</c:v></c:pt>', text)

    # ---- the tree and the text helpers --------------------------------------------------
    def test_T65_node_leaves_children_and_paths(self):
        node = Node('thing')
        node.kvw('a.b.c', 5)
        self.assertEqual(node.kvr('a.b.c'), 5)
        self.assertEqual(node.a.b.c, 5)
        self.assertEqual(node['a.b.c'], 5)
        node['x'] = 1
        self.assertEqual(node.keys(), ['x'])
        self.assertEqual((node.count(), len(node.keys())), (1, 1))
        self.assertEqual(node.kvr('nothing', 'dflt'), 'dflt')
        node.kvw('x', None)
        self.assertIsNone(node.kvr('x'))
        self.assertIn('a:{b:{c:5}}', repr(node))

    def test_T66_reading_a_missing_node_builds_nothing_and_writing_below_it_builds_it(self):
        node = Node()
        self.assertIsNone(node.kvr('title'))
        node.title.text
        self.assertEqual(node.count(), 0)
        self.assertIsNone(node.kvr('title.text'))
        node.title.text = 'T'
        self.assertEqual(node.count(), 1)
        self.assertEqual(node.nodes()[0].name, 'title')
        child = Node()
        self.assertIs(node.add('kid', child), child)
        self.assertIs(child.parent(), node)

    def test_T67_a_leaf_cannot_have_a_method_name(self):
        node = Node()
        with self.assertRaises(AttributeError):
            node.count = 3
        with self.assertRaises(AttributeError):
            node._hidden
        node.kvw('count', 3)
        self.assertEqual(node.kvr('count'), 3)

    def test_T68_xml_helpers(self):
        self.assertEqual(tag('c:idx', val=3), '<c:idx val="3"/>')
        self.assertEqual(tag('a', 'x', 'y', k=None, b=True, f=0.5), '<a b="1" f="0.5">xy</a>')
        self.assertEqual(tag('c', **{'r:id': 'rId1'}), '<c r:id="rId1"/>')
        self.assertEqual(tag('c', name='n'), '<c name="n"/>')
        self.assertEqual(xml_text('a<b&"c"\x00\x1f'), 'a&lt;b&amp;&quot;c&quot;')
        self.assertEqual([xml_text(x) for x in (11.0, 0.1, 1e20, 7, True)], ['11', '0.1', '1e+20', '7', '1'])
        self.assertEqual(parse_xml(b'<a xmlns="u" xmlns:r="v"><b r:id="x"/></a>')[0].get('id'), 'x')
        self.assertEqual(safe_name('my sheet-1'), 'my_sheet_1')
        self.assertEqual(safe_name('1abc'), 's_1abc')
        self.assertEqual([column(n) for n in (1, 26, 27, 52, 703)], ['A', 'Z', 'AA', 'AZ', 'AAA'])
        self.assertEqual([column(x) for x in ('A', 'AB', b'AZ')], [1, 28, 52])

    # ---- benchmarks ---------------------------------------------------------------------
    def bench_cell_value(self, timer):
        sheet, coords = self.sheet, self.coords
        size = len(coords)
        with timer as test:
            while test.more:
                for i in test.count:
                    sheet.cell(*coords[i % size])
        return 'sheet.cell(r, c)', 'read'

    def bench_write_cursor(self, timer):
        with timer as test:
            while test.more:
                xl = xlw()
                xl.newbook(self.path('benchw'), 'W')
                for i in test.count:
                    xl.write(1.5)
        return 'xl.write(1.5)', 'write'

    def bench_write_node(self, timer):
        with timer as test:
            while test.more:
                xl = xlw()
                xl.newbook(self.path('benchw'), 'W')
                sheet = xl.benchw.W
                for i in test.count:
                    sheet.write(1.5)
        return 'sheet.write(1.5)', 'write'

    def bench_write_styled(self, timer):
        with timer as test:
            while test.more:
                xl = xlw()
                xl.newbook(self.path('benchw'), 'W')
                sheet = xl.benchw.W
                for i in test.count:
                    sheet.write(1.5, 'Heading1')
        return "sheet.write(1.5, 'Heading1')", 'write'

    def bench_build_10k(self, timer):
        table = self.table_10k
        with timer as test:
            while test.more:
                for i in test.count:
                    xl = xlw()
                    xl.newbook(self.path('benchb'), 'W')
                    xl.write(table)
        return 'build 10 000 cells: xl.write(block)', 'whole book'

    def bench_save_10k(self, timer):
        xl = self.speed10k
        with timer as test:
            while test.more:
                for i in test.count:
                    xl.save()
        return 'save 10 000 cells to disk', 'whole book'

    def bench_open_10k(self, timer):
        filename = self.path('speed10k') + '.xlsx'
        with timer as test:
            while test.more:
                for i in test.count:
                    xlw().open(filename)
        return 'open 10 000 cells', 'whole book'

    def bench_save_100k(self, timer):
        xl = self.speed100k
        with timer as test:
            while test.more:
                for i in test.count:
                    xl.save()
        return 'save 100 000 cells to disk', 'whole book'

    def bench_open_100k(self, timer):
        filename = self.path('speed100k') + '.xlsx'
        with timer as test:
            while test.more:
                for i in test.count:
                    xlw().open(filename)
        return 'open 100 000 cells', 'whole book'

    def bench_chart_save(self, timer):
        xl, _ = self.chart_book()
        with timer as test:
            while test.more:
                for i in test.count:
                    xl.save()
        return 'save a book with a 2-series chart', 'chart'
