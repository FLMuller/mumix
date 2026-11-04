"""
b_xlw.py -- tests and benchmarks for xlw, the tkv-backed .xlsx writer.

Ported from code.m/xlw/tests/b_xlw.m (63 tests) and extended for what the Python port
changed: the default style is always xf 0, number formats outside Excel's built-in set
are custom ids (xlw.m mapped them to Excel's currency ids), control characters are
stripped, a duplicate sheet name is refused.

The files are read back with a small stdlib reader written here (zipfile + ElementTree),
independent of xlw and of xlreader, so a symmetric mistake in writer and reader cannot
hide. Round trips through xlreader are tested in b_xlreader.

Run from the project root:
    python tools/runbench.py tests/b_xlw.py
"""

import os
import sys
import tempfile
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
from use import load
from bench import bench

SOURCES = ['xlw', 'xlstyle', 'xlparts']
globals().update(load('xlw', into={}))          # xlw, XlwError, XlwNoBook, ...
import xlsheet
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gridcheck import Cell, at, ncells, cell_table
BOUND = load('xlstyle', into={})                # the style helpers the tests probe

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
NSR = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
OUTDIR = os.path.join(ROOT, 'results', 'b_xlw')


def readsheet(filename, sheet_name):
    """{(row, col): value} of one sheet, read with the standard library only."""
    with zipfile.ZipFile(filename) as archive:
        workbook = ET.fromstring(archive.read('xl/workbook.xml'))
        rels = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        target = {rel.get('Id'): rel.get('Target') for rel in rels}
        rid = None
        for sheet in workbook.iter(NS + 'sheet'):
            if sheet.get('name') == sheet_name:
                rid = sheet.get(NSR + 'id')
        path = 'xl/' + target[rid]
        strings = []
        sst = ET.fromstring(archive.read('xl/sharedStrings.xml'))
        for item in sst.iter(NS + 'si'):
            strings.append(''.join(t.text or '' for t in item.iter(NS + 't')))
        cells = {}
        for cell in ET.fromstring(archive.read(path)).iter(NS + 'c'):
            ref = cell.get('r')
            letters = ''.join(ch for ch in ref if ch.isalpha())
            col = 0
            for ch in letters:
                col = col * 26 + ord(ch) - 64
            row = int(ref[len(letters):])
            value = cell.find(NS + 'v')
            if value is None:
                cells[(row, col)] = None
            elif cell.get('t') == 's':
                cells[(row, col)] = strings[int(value.text)]
            elif cell.get('t') == 'b':
                cells[(row, col)] = value.text == '1'
            else:
                cells[(row, col)] = float(value.text)
        return cells


def partext(filename, part):
    with zipfile.ZipFile(filename) as archive:
        return archive.read(part).decode('utf-8')


class b_xlw(bench):
    BenchName = 'xlw'
    BenchVersion = 'M1.0.12'
    BenchHeader = ''
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        os.makedirs(OUTDIR, exist_ok=True)
        cls.size = 12
        xl = xlw()
        xl.newbook(cls.path('bench'), 'S1')
        sheet = xl.bench.S1
        for row in range(cls.size):
            for col in range(cls.size):
                if (row + col + 2) % 5 == 0:
                    sheet.write(row * 100.0 + col + 0.5, 'Heading1')
                else:
                    sheet.write(row * 100.0 + col + 0.5)
            sheet.writeln()
        cls.xl = xl
        cls.sheet = sheet
        cls.rows = [r for r in range(1, cls.size + 1) for c in range(1, cls.size + 1)]
        cls.cols = [c for r in range(1, cls.size + 1) for c in range(1, cls.size + 1)]
        cls.scratch = xlw()
        cls.scratch.newbook(cls.path('scratch'), 'W')
        cls.scratch_sheet = cls.scratch.scratch.W
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

    def make(self):
        """A fresh writer with book 'data' (file results/b_xlw/data.xlsx), sheet 'S1'."""
        xl = xlw()
        xl.newbook(self.path('data'), 'S1')
        return xl

    # ---- newbook ------------------------------------------------------------------
    def test_T01_newbook_returns_a_book_node(self):
        book = xlw().newbook(self.path('b1'))
        self.assertEqual(book.type(), 'book')

    def test_T02_newbook_parent_is_root(self):
        book = xlw().newbook(self.path('b2'))
        self.assertEqual(book.parent().type(), 'root')

    def test_T03_extension_is_added(self):
        book = xlw().newbook(self.path('noext'))
        self.assertTrue(book.kvr('priv').kvr('fname').endswith('.xlsx'))

    def test_T04_no_double_extension(self):
        book = xlw().newbook(self.path('already.xlsx'))
        self.assertFalse(book.kvr('priv').kvr('fname').endswith('.xlsx.xlsx'))

    def test_T05_book_name_is_made_safe(self):
        xl = xlw()
        xl.newbook(self.path('my book'))
        self.assertEqual(xl.my_book.type(), 'book')

    def test_T06_two_books_last_is_active(self):
        xl = xlw()
        xl.newbook(self.path('one'))
        book2 = xl.newbook(self.path('two'))
        xl.newsheet('S1')
        self.assertIsNotNone(book2.kvr('priv').kvr('cursor'))
        self.assertIsNone(xl.one.kvr('priv').kvr('cursor'))

    # ---- newsheet -----------------------------------------------------------------
    def test_T07_newsheet_returns_a_sheet(self):
        sheet = self.make().data.S1
        self.assertEqual(sheet.type(), 'sheet')

    def test_T08_sheet_parent_is_book(self):
        xl = self.make()
        self.assertIs(xl.data.S1.parent(), xl.data)

    def test_T09_cursor_starts_at_1_1(self):
        self.assertEqual(self.make().data.S1.kvr('priv').kvr('cursor'), [1, 1])

    def test_T10_gridlines_start_on(self):
        self.assertTrue(self.make().data.S1.kvr('showGrid'))

    def test_T11_sheet_names_are_recorded_in_order(self):
        xl = self.make()
        xl.newsheet('Beta')
        self.assertEqual(xl.data.kvr('priv').kvr('sheets'), ['S1', 'Beta'])

    def test_T12_duplicate_sheet_is_refused(self):
        with self.assertRaises(XlwBadArg):
            self.make().newsheet('S1')

    def test_T13_newsheet_without_a_name_is_refused(self):
        with self.assertRaises(XlwBadArg):
            self.make().newsheet()

    # ---- write --------------------------------------------------------------------
    def test_T14_write_string(self):
        xl = self.make()
        xl.write('hello')
        self.assertEqual(at(xl.data.S1, 1, 1).kvr('val'), 'hello')

    def test_T15_write_numeric(self):
        xl = self.make()
        xl.write(3.14)
        self.assertEqual(at(xl.data.S1, 1, 1).kvr('val'), 3.14)

    def test_T16_write_logical(self):
        xl = self.make()
        xl.write(True)
        self.assertIs(at(xl.data.S1, 1, 1).kvr('val'), True)

    def test_T17_write_advances_the_cursor(self):
        sheet = self.make().data.S1
        sheet.write('a')
        sheet.write('b')
        sheet.write('c')
        self.assertEqual(sheet.kvr('priv').kvr('cursor')[1], 4)

    def test_T18_write_chains(self):
        sheet = self.make().data.S1
        sheet.write('a').write('b').write('c')
        self.assertEqual(at(sheet, 1, 1).kvr('val'), 'a')
        self.assertEqual(at(sheet, 1, 3).kvr('val'), 'c')

    def test_T19_write_returns_the_sheet(self):
        sheet = self.make().data.S1
        self.assertIs(sheet.write('x'), sheet)

    def test_T20_write_block_of_lists(self):
        sheet = self.make().data.S1
        sheet.write([[1, 2, 3], [4, 5, 6]])
        self.assertEqual(at(sheet, 1, 1).kvr('val'), 1)
        self.assertEqual(at(sheet, 1, 3).kvr('val'), 3)
        self.assertEqual(at(sheet, 2, 1).kvr('val'), 4)
        self.assertEqual(at(sheet, 2, 3).kvr('val'), 6)

    def test_T21_write_mixed_block(self):
        sheet = self.make().data.S1
        sheet.write([['alpha', 1], ['beta', 2]])
        self.assertEqual(at(sheet, 1, 1).kvr('val'), 'alpha')
        self.assertEqual(at(sheet, 2, 2).kvr('val'), 2)

    def test_T22_write_flat_list_is_one_row(self):
        sheet = self.make().data.S1
        sheet.write([True, False, True])
        self.assertIs(at(sheet, 1, 2).kvr('val'), False)
        self.assertEqual(sheet.kvr('priv').kvr('cursor'), [1, 4])

    def test_T23_write_numpy_array(self):
        import numpy
        sheet = self.make().data.S1
        sheet.write(numpy.array([[1.5, 2.5], [3.5, 4.5]]))
        self.assertEqual(at(sheet, 2, 2).kvr('val'), 4.5)
        self.assertIsInstance(at(sheet, 2, 2).kvr('val'), float)
        sheet.writeln()
        sheet.write(numpy.float64(7.25))
        self.assertEqual(at(sheet, 2, 1).kvr('val'), 7.25)

    def test_T24_write_none_makes_a_blank_cell(self):
        sheet = self.make().data.S1
        sheet.write(None)
        self.assertIsNone(at(sheet, 1, 1).kvr('val'))                # an empty text is a blank cell

    def test_T25_write_dict_is_refused(self):
        with self.assertRaises(XlwBadArg):
            self.make().write({'a': 1})

    def test_T26_keyword_style_on_the_class_method(self):
        xl = self.make()
        xl.write('x', bold=True, fill='yellow')
        cell = at(xl.data.S1, 1, 1)
        self.assertTrue(cell.kvr('bold'))
        self.assertEqual(cell.kvr('fill'), 'FFFF00')

    # ---- writeln / nl --------------------------------------------------------------
    def test_T27_writeln_starts_a_new_row(self):
        sheet = self.make().data.S1
        sheet.write('a')
        sheet.write('b')
        sheet.writeln()
        self.assertEqual(sheet.kvr('priv').kvr('cursor'), [2, 1])

    def test_T28_writeln_with_a_value(self):
        sheet = self.make().data.S1
        sheet.writeln('hello')
        self.assertEqual(sheet.kvr('priv').kvr('cursor'), [2, 1])
        self.assertEqual(at(sheet, 1, 1).kvr('val'), 'hello')

    def test_T29_writeln_chains(self):
        sheet = self.make().data.S1
        sheet.writeln('r1').writeln('r2').writeln('r3')
        self.assertEqual(at(sheet, 1, 1).kvr('val'), 'r1')
        self.assertEqual(at(sheet, 3, 1).kvr('val'), 'r3')

    def test_T30_nl_is_a_newline(self):
        xl = self.make()
        xl.write('a').nl()
        self.assertEqual(xl.data.S1.kvr('priv').kvr('cursor'), [2, 1])

    # ---- move / gridlines ------------------------------------------------------------
    def test_T31_move_directions(self):
        xl = self.make()
        cursor = xl.data.S1.kvr('priv')
        xl.move('down', 3)
        self.assertEqual(cursor.kvr('cursor')[0], 4)
        xl.move('right', 2)
        self.assertEqual(cursor.kvr('cursor')[1], 3)
        xl.move('up', 1)
        self.assertEqual(cursor.kvr('cursor')[0], 3)
        xl.move('left', 1)
        self.assertEqual(cursor.kvr('cursor')[1], 2)
        xl.move('cr')
        self.assertEqual(cursor.kvr('cursor')[1], 1)
        xl.move('home')
        self.assertEqual(cursor.kvr('cursor'), [1, 1])

    def test_T32_move_unknown_direction_is_refused(self):
        with self.assertRaises(XlwBadArg):
            self.make().move('sideways')

    def test_T33_move_btm_is_one_past_the_last_row(self):
        xl = self.make()
        xl.write('a').nl().write('b').nl().write('c').nl()
        xl.move('btm')
        self.assertEqual(xl.data.S1.kvr('priv').kvr('cursor'), [4, 1])

    def test_T34_gridlines_off(self):
        xl = self.make()
        xl.gridlines(False)
        self.assertFalse(xl.data.S1.kvr('showGrid'))

    # ---- styles -------------------------------------------------------------------
    def test_T35_named_style_is_applied(self):
        xl = self.make()
        xl.data.S1.write('x', 'Heading1')
        cell = at(xl.data.S1, 1, 1)
        self.assertEqual(cell.kvr('sz'), 15)
        self.assertTrue(cell.kvr('bold'))

    def test_T36_override_wins_and_the_base_survives(self):
        xl = self.make()
        xl.data.S1.write('x', 'Heading1', 'sz', 20)
        cell = at(xl.data.S1, 1, 1)
        self.assertEqual(cell.kvr('sz'), 20)
        self.assertTrue(cell.kvr('bold'))

    def test_T37_new_style_is_stored_and_used(self):
        xl = self.make()
        xl.newstyle('myHdr', 'bold', True, 'sz', 16, 'fill', 'FF0000')
        xl.data.S1.write('x', 'myHdr')
        cell = at(xl.data.S1, 1, 1)
        self.assertEqual(cell.kvr('sz'), 16)
        self.assertTrue(cell.kvr('bold'))
        self.assertEqual(cell.kvr('fill'), 'FF0000')

    def test_T38_integers_get_the_format_0(self):
        xl = self.make()
        xl.write(42).write(7)
        self.assertEqual(at(xl.data.S1, 1, 2).kvr('numfmt'), '0')

    def test_T39_auto_numfmt_ranges(self):
        auto = BOUND['auto_numfmt']
        self.assertEqual(auto(0.0), '')
        self.assertEqual(auto(float('nan')), '')
        self.assertEqual(auto(1234.0), '0')
        self.assertEqual(auto(3.14159), '0.##')
        self.assertEqual(auto(12345.678), '0')
        self.assertEqual(auto(0.0012), '0.##E+00')
        self.assertEqual(auto(1234567.89), '0.##E+00')

    def test_T40_underline_strike_rotation_indent_leaves(self):
        sheet = self.make().data.S1
        sheet.write('x', 'underline', True)
        sheet.write('y', 'strikethrough', True)
        sheet.write('z', 'rotation', 45)
        sheet.write('w', 'indent', 2)
        self.assertTrue(at(sheet, 1, 1).kvr('underline'))
        self.assertTrue(at(sheet, 1, 2).kvr('strikethrough'))
        self.assertEqual(at(sheet, 1, 3).kvr('rotation'), 45)
        self.assertEqual(at(sheet, 1, 4).kvr('indent'), 2)

    def test_T41_style_properties_reach_styles_xml(self):
        xl = self.make()
        xl.write('u', 'underline', True)
        xl.write('k', 'strikethrough', True)
        xl.write(7, 'rotation', -30)               # clockwise -> 120
        xl.write('i', 'indent', 3)
        xl.save()
        styles = partext(xl.data.kvr('priv').kvr('fname'), 'xl/styles.xml')
        self.assertIn('<u/>', styles)
        self.assertIn('<strike/>', styles)
        self.assertIn('textRotation="120"', styles)
        self.assertIn('indent="3"', styles)

    def test_T42_border_string_becomes_four_edges(self):
        xl = self.make()
        xl.data.S1.write('x', 'border', 'nesw:thin')
        border = at(xl.data.S1, 1, 1).kvr('border')
        self.assertEqual(len(border), 4)
        self.assertEqual(border[0][1], 'thin')

    def test_T43_border_reaches_styles_xml_and_the_file_reads_back(self):
        xl = self.make()
        xl.data.S1.write('a', 'border', 'n:medium,s:double', 'bcolor', 'FF0000')
        xl.save()
        fname = xl.data.kvr('priv').kvr('fname')
        self.assertEqual(readsheet(fname, 'S1')[(1, 1)], 'a')
        styles = partext(fname, 'xl/styles.xml')
        self.assertIn('<top style="medium"', styles)
        self.assertIn('<bottom style="double"', styles)
        self.assertIn('FFFF0000', styles)
        self.assertIn('applyBorder="1"', styles)

    def test_T44_loaded_style_good(self):
        xl = self.make()
        xl.data.S1.write('x', 'Good')
        cell = at(xl.data.S1, 1, 1)
        self.assertEqual(cell.kvr('fill'), 'C6EFCE')
        self.assertEqual(cell.kvr('color'), '006100')

    def test_T45_loaded_style_with_a_border(self):
        xl = self.make()
        xl.data.S1.write('x', 'Input')
        cell = at(xl.data.S1, 1, 1)
        self.assertEqual(cell.kvr('fill'), 'FFCC99')
        self.assertEqual(len(cell.kvr('border')), 4)

    def test_T46_heading_alias_from_the_file(self):
        xl = self.make()
        xl.data.S1.write('x', 'Heading1')
        self.assertEqual(at(xl.data.S1, 1, 1).kvr('sz'), 15)

    def test_T47_colour_named(self):
        xl = self.make()
        xl.data.S1.write('x', 'color', 'red')
        self.assertEqual(at(xl.data.S1, 1, 1).kvr('color'), 'FF0000')

    def test_T48_colour_rgb_triple(self):
        xl = self.make()
        xl.data.S1.write('x', 'fill', [255, 204, 153])
        self.assertEqual(at(xl.data.S1, 1, 1).kvr('fill'), 'FFCC99')

    def test_T49_colour_forms(self):
        color2hex = BOUND['color2hex']
        self.assertEqual(color2hex('#ff0080'), 'FF0080')
        self.assertEqual(color2hex('f08'), 'FF0088')
        self.assertEqual(color2hex((1, 0.5, 0)), 'FF8000')
        self.assertEqual(color2hex(''), '')
        self.assertEqual(color2hex(None), '')

    def test_T50_plain_cell_uses_xf_zero_and_xf_zero_is_the_default(self):
        xl = self.make()
        xl.write('plain', 'bold', True).write('x')
        xl.save()
        fname = xl.data.kvr('priv').kvr('fname')
        sheet = partext(fname, 'xl/worksheets/sheet1.xml')
        self.assertIn('<c r="A1" s="1"', sheet)    # styled first: the default is still xf 0
        self.assertIn('<c r="B1" s="0"', sheet)
        styles = ET.fromstring(partext(fname, 'xl/styles.xml'))
        xfs = styles.find(NS + 'cellXfs').findall(NS + 'xf')
        self.assertEqual(xfs[0].get('fontId'), '0')
        self.assertEqual(xfs[0].get('fillId'), '0')
        self.assertEqual(xfs[0].get('borderId'), '0')
        self.assertEqual(xfs[0].get('numFmtId'), '0')

    def test_T51_custom_number_formats_are_not_excel_currency_ids(self):
        xl = self.make()
        xl.write(0.0012).write(2.5).write(3, 'numfmt', '0.00%')
        xl.save()
        styles = partext(xl.data.kvr('priv').kvr('fname'), 'xl/styles.xml')
        root = ET.fromstring(styles)
        custom = {fmt.get('formatCode'): int(fmt.get('numFmtId'))
                  for fmt in root.iter(NS + 'numFmt')}
        self.assertGreaterEqual(custom['0.##E+00'], 164)      # xlw.m mapped this to 8
        self.assertGreaterEqual(custom['0.##'], 164)
        ids = [int(xf.get('numFmtId')) for xf in root.find(NS + 'cellXfs')]
        self.assertIn(10, ids)                                # '0.00%' is Excel's id 10

    # ---- border() verb --------------------------------------------------------------
    def test_T52_border_verb_creates_value_less_cells(self):
        sheet = self.make().data.S1
        sheet.border([(1, 1), (1, 2)], 'nesw:thin')
        cell = at(sheet, 1, 1)
        self.assertEqual(sheet.kvr('cells').kvr((1, 1))[0], xlsheet.BLANK)
        self.assertIsNone(cell.kvr('val'))
        self.assertEqual(len(cell.kvr('border')), 4)

    def test_T53_value_less_cell_emits_no_value_but_keeps_its_border(self):
        xl = self.make()
        sheet = xl.data.S1
        sheet.write('real').writeln()
        sheet.border([(2, 1)], 'all:medium', 'color', '0000FF')
        xl.save()
        fname = xl.data.kvr('priv').kvr('fname')
        cells = readsheet(fname, 'S1')
        self.assertEqual(cells[(1, 1)], 'real')
        self.assertIsNone(cells[(2, 1)])
        styles = partext(fname, 'xl/styles.xml')
        self.assertIn('<top style="medium"', styles)
        self.assertIn('FF0000FF', styles)

    def test_T54_border_verb_keeps_an_existing_value(self):
        sheet = self.make().data.S1
        sheet.write('keep')
        sheet.border([(1, 1)], 'nesw:thin')
        self.assertEqual(at(sheet, 1, 1).kvr('val'), 'keep')
        self.assertEqual(len(at(sheet, 1, 1).kvr('border')), 4)

    # ---- reads -----------------------------------------------------------------------
    def test_T55_a_cell_reads_back_its_value(self):
        cell = at(self.sheet, 3, 4)
        self.assertEqual(cell.kvr('val'), 2 * 100.0 + 3 + 0.5)

    def test_T56_kvr_with_a_coordinate_pair(self):
        cell = at(self.sheet, 5, 6)
        self.assertEqual(cell.kvr('val'), 4 * 100.0 + 5 + 0.5)

    def test_T57_kvr_of_an_absent_cell_is_none(self):
        self.assertIsNone(at(self.sheet, 99, 99))

    def test_T58_dot_walk_resolves_the_sheet(self):
        self.assertIs(self.xl.bench.S1, self.sheet)

    # ---- fluent dispatch ---------------------------------------------------------------
    def test_T60_node_dispatch_with_style_pairs(self):
        xl = self.make()
        xl.data.S1.write('disp', 'bold', True)
        self.assertEqual(at(xl.data.S1, 1, 1).kvr('val'), 'disp')
        self.assertTrue(at(xl.data.S1, 1, 1).kvr('bold'))

    def test_T61_chain_across_verbs(self):
        xl = self.make()
        xl.data.S1.write('a').write('b').writeln().write('c')
        self.assertEqual(at(xl.data.S1, 1, 1).kvr('val'), 'a')
        self.assertEqual(at(xl.data.S1, 2, 1).kvr('val'), 'c')

    # ---- activate ----------------------------------------------------------------------
    def test_T62_activate_by_name(self):
        xl = xlw()
        book1 = xl.newbook(self.path('act1'))
        xl.newbook(self.path('act2'))
        xl.activate('act1')
        xl.newsheet('S1')
        self.assertIsNotNone(book1.kvr('priv').kvr('cursor'))

    def test_T63_activate_cascades_from_a_node(self):
        xl = xlw()
        book1 = xl.newbook(self.path('cas1'))
        xl.newsheet('S1')
        xl.newbook(self.path('cas2'))
        xl.cas1.S1.activate()
        xl.newsheet('S2')
        self.assertEqual(len(book1.kvr('priv').kvr('sheets')), 2)

    def test_T64_activate_unknown_book_is_refused(self):
        with self.assertRaises(XlwNoBook):
            xlw().activate('nothing')

    # ---- routing ------------------------------------------------------------------------
    def test_T65_book_by_attribute(self):
        xl = xlw()
        book = xl.newbook(self.path('route'))
        self.assertIs(xl.route, book)

    def test_T66_unknown_book_attribute_is_refused(self):
        with self.assertRaises(XlwNoBook):
            xlw().nosuchbook

    def test_T67_methods_win_over_book_names(self):
        xl = xlw()
        with self.assertRaises(TypeError):
            xl.newbook()                          # a bad call of a real method

    # ---- save ---------------------------------------------------------------------------
    def test_T68_save_creates_all_parts(self):
        xl = self.make()
        xl.write('Name').write(42).writeln()
        xl.save()
        fname = xl.data.kvr('priv').kvr('fname')
        self.assertTrue(os.path.isfile(fname))
        names = zipfile.ZipFile(fname).namelist()
        for part in ('[Content_Types].xml', '_rels/.rels', 'xl/workbook.xml',
                     'xl/_rels/workbook.xml.rels', 'xl/styles.xml',
                     'xl/sharedStrings.xml', 'xl/worksheets/sheet1.xml'):
            self.assertIn(part, names)

    def test_T69_every_part_is_well_formed_xml(self):
        xl = self.make()
        xl.write('a', 'bold', True).write(1.5).write(True).write(None).writeln()
        xl.border([(2, 2)], 'all:thin')
        xl.save()
        archive = zipfile.ZipFile(xl.data.kvr('priv').kvr('fname'))
        for name in archive.namelist():
            ET.fromstring(archive.read(name))

    def test_T70_round_trip(self):
        xl = self.make()
        xl.write('Label').write(3.14159).writeln()
        xl.write('quote & <tag> "q" \'a\'').write(1234567.89)
        xl.save()
        cells = readsheet(xl.data.kvr('priv').kvr('fname'), 'S1')
        self.assertEqual(cells[(1, 1)], 'Label')
        self.assertAlmostEqual(cells[(1, 2)], 3.14159, places=9)
        self.assertEqual(cells[(2, 1)], 'quote & <tag> "q" \'a\'')
        self.assertAlmostEqual(cells[(2, 2)], 1234567.89, places=4)

    def test_T71_multi_sheet(self):
        xl = self.make()
        xl.write('one-A1')
        xl.newsheet('Two')
        xl.write('two-A1')
        xl.save()
        fname = xl.data.kvr('priv').kvr('fname')
        self.assertEqual(readsheet(fname, 'S1')[(1, 1)], 'one-A1')
        self.assertEqual(readsheet(fname, 'Two')[(1, 1)], 'two-A1')

    def test_T72_save_with_no_sheet_is_refused(self):
        book = xlw().newbook(self.path('nosheetbk'))
        with self.assertRaises(XlwNoSheet):
            book.save()

    def test_T73_save_all(self):
        xl = xlw()
        xl.newbook(self.path('all1'), 'S1')
        xl.write('a')
        xl.newbook(self.path('all2'), 'S1')
        xl.write('b')
        xl.save('all')
        self.assertTrue(os.path.isfile(self.path('all1.xlsx')))
        self.assertTrue(os.path.isfile(self.path('all2.xlsx')))

    def test_T74_save_by_name(self):
        xl = xlw()
        xl.newbook(self.path('byname'), 'S1')
        xl.write('a')
        xl.newbook(self.path('other'), 'S1')       # the active one is 'other'
        xl.save('byname')
        self.assertTrue(os.path.isfile(self.path('byname.xlsx')))

    def test_T75_shared_strings_are_deduplicated(self):
        xl = self.make()
        xl.write('same').write('same').write('other').write('same')
        xl.save()
        sst = ET.fromstring(partext(xl.data.kvr('priv').kvr('fname'),
                                    'xl/sharedStrings.xml'))
        self.assertEqual(len(sst.findall(NS + 'si')), 2)

    def test_T76_text_that_starts_with_a_bracket(self):
        xl = self.make()
        xl.write('(a b)').write('(1 2)').write('.x')
        xl.save()
        cells = readsheet(xl.data.kvr('priv').kvr('fname'), 'S1')
        self.assertEqual(cells[(1, 1)], '(a b)')
        self.assertEqual(cells[(1, 2)], '(1 2)')

    def test_T77_control_characters_are_stripped(self):
        xl = self.make()
        xl.write('a\x00b\x0bc\x1fd')
        xl.save()
        cells = readsheet(xl.data.kvr('priv').kvr('fname'), 'S1')
        self.assertEqual(cells[(1, 1)], 'abcd')

    def test_T78_non_finite_numbers_are_blank_cells(self):
        xl = self.make()
        xl.write(float('nan')).write(float('inf')).write(1.0)
        xl.save()
        cells = readsheet(xl.data.kvr('priv').kvr('fname'), 'S1')
        self.assertIsNone(cells[(1, 1)])
        self.assertIsNone(cells[(1, 2)])
        self.assertEqual(cells[(1, 3)], 1.0)

    def test_T79_numbers_keep_full_precision(self):
        xl = self.make()
        xl.write(0.1 + 0.2).write(123456789012345.0).write(-1e-300)
        xl.save()
        cells = readsheet(xl.data.kvr('priv').kvr('fname'), 'S1')
        self.assertAlmostEqual(cells[(1, 1)], 0.30000000000000004, places=15)
        self.assertEqual(cells[(1, 2)], 123456789012345.0)
        self.assertEqual(cells[(1, 3)], -1e-300)

    def test_T80_gridlines_off_reaches_the_sheet_xml(self):
        xl = self.make()
        xl.gridlines(False)
        xl.write('x')
        xl.save()
        sheet = partext(xl.data.kvr('priv').kvr('fname'), 'xl/worksheets/sheet1.xml')
        self.assertIn('showGridLines="0"', sheet)

    def test_T81_columns_are_autofitted(self):
        xl = self.make()
        xl.write('a').write('a much longer text value')
        xl.save()
        sheet = partext(xl.data.kvr('priv').kvr('fname'), 'xl/worksheets/sheet1.xml')
        self.assertIn('<col min="1" max="1" width="4"', sheet)      # clamped up to 4
        self.assertIn('<col min="2" max="2" width="26"', sheet)     # 24 chars + 2

    def test_T82_rows_and_cells_are_in_order_whatever_the_write_order(self):
        xl = self.make()
        sheet = xl.data.S1
        sheet.move('down', 4)
        sheet.write('r5')
        sheet.move('home')
        sheet.write('r1')
        xl.save()
        text = partext(xl.data.kvr('priv').kvr('fname'), 'xl/worksheets/sheet1.xml')
        self.assertLess(text.index('r="1"'), text.index('r="5"'))

    def test_T83_a_larger_sheet_saves_and_reads_back(self):
        xl = self.make()
        rows = [[r * 1000 + c for c in range(40)] for r in range(100)]
        xl.write(rows)
        xl.save()
        cells = readsheet(xl.data.kvr('priv').kvr('fname'), 'S1')
        self.assertEqual(len(cells), 4000)
        self.assertEqual(cells[(100, 40)], 99 * 1000 + 39)

    def test_T84_style_dedup_gives_one_xf_per_distinct_style(self):
        xl = self.make()
        for _ in range(5):
            xl.write('x', 'bold', True)
        for _ in range(5):
            xl.write('y', 'italic', True)
        xl.save()
        styles = ET.fromstring(partext(xl.data.kvr('priv').kvr('fname'),
                                       'xl/styles.xml'))
        self.assertEqual(len(styles.find(NS + 'cellXfs')), 3)         # default + 2

    def test_T85_workbook_lists_the_sheets_in_order_and_escapes_names(self):
        xl = xlw()
        xl.newbook(self.path('esc'), 'A&B', 'C<D')
        xl.write('x')
        xl.save()
        names = [sheet.get('name') for sheet in ET.fromstring(
            partext(self.path('esc.xlsx'), 'xl/workbook.xml')).iter(NS + 'sheet')]
        self.assertEqual(names, ['A&B', 'C<D'])

    def test_T86_xlstyle_helpers(self):
        safe = BOUND['safe_name']
        self.assertEqual(safe('my book'), 'my_book')
        self.assertEqual(safe('1abc'), 's_1abc')
        self.assertEqual(safe(''), 's_')
        border = BOUND['normalise_border']
        self.assertEqual(border(''), ())
        self.assertEqual(len(border('all:medium')), 4)
        self.assertEqual(border('n:thin,s:double', 'FF0000')[1], ('s', 'double', 'FF0000'))
        self.assertEqual(border(border('nesw')), border('nesw'))      # idempotent

    # ---- benchmarks ----------------------------------------------------------------------
    def bench_item_read(self, timer):
        grid = self.sheet.kvr('cells')
        rows = self.rows
        cols = self.cols
        size = len(rows)
        with timer as test:
            while test.more:
                for i in test.count:
                    grid.kvr((rows[i % size], cols[i % size]))
        return 'cells.kvr((r, c))', 'read'

    def bench_cell_value(self, timer):
        sheet = self.sheet
        rows = self.rows
        cols = self.cols
        size = len(rows)
        value = xlsheet.cell_value
        with timer as test:
            while test.more:
                for i in test.count:
                    value(sheet, rows[i % size], cols[i % size])
        return 'cell_value(sheet, r, c)', 'read'

    def bench_write_cursor(self, timer):
        with timer as test:
            while test.more:
                xl = xlw()
                xl.newbook(self.path('benchw'), 'W')
                for i in test.count:
                    xl.write(1.5)
        return 'xl.write(1.5)', 'write'

    def bench_write_node_dispatch(self, timer):
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

    # Whole-book rows: one op is one book (10 000 or 100 000 plain numeric cells, 10
    # columns), so the cost per cell is the mean divided by the cell count.
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
