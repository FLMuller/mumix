"""
b_xlreader.py -- tests for xlreader: cells, styles and XY charts read into the xlw tree.

Three kinds of evidence, in rising strength:
  * round trips of workbooks xlw wrote itself (cell values and styles come back);
  * what the reader makes of files from elsewhere: the MATLAB xlw outputs and an
    Excel-authored workbook in tests/fixtures, and the four charts in workbooks saved by
    Excel 16 (results/reference, skipped when absent, never copied into the repository);
  * the fixpoint on those Excel charts: read the Excel chart, write it with xlchart, read
    that again, and nothing that was read the first time may be lost or changed. This
    shows the reader and the writer are inverses on real Excel output, and the written
    chart is also checked against the schema element order.

Run from the project root:
    python tools/runbench.py tests/b_xlreader.py
"""

import hashlib
import os
import re
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
from use import load
from bench import bench

SOURCES = ['xlreader', 'xlchart', 'xlw']
globals().update(load('xlw', into={}))
CH = load('xlchart', into={})
RD = load('xlreader', into={})
import xlreader                                  # for its helper functions (draw_color)
from xlstore import KV, TKV                      # to tell a record from a node
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chartcheck import order_errors
from gridcheck import Cell, at, ncells, cell_table, formula_table

OUTDIR = os.path.join(ROOT, 'results', 'b_xlreader')
FIXTURES = os.path.join(ROOT, 'tests', 'fixtures')
REFERENCE = os.path.join(ROOT, 'results', 'reference')
CRYSTAL = 'SB Solubility vs temperature.xlsx'
XRD = 'Theopylline As recieved.xlsx'


# ---------------------------------------------------------------- comparison helpers ----
def dump(thing):
    """A tkv node, a kv record, a list or a scalar as plain nested data (for comparing)."""
    if isinstance(thing, TKV):
        out = {key: dump(value) for key, value in thing.entries()}
        for name, child in zip(thing.names(), thing.nodes()):
            out[name + '/'] = dump(child)
        return out
    if isinstance(thing, KV):
        return {key: dump(value) for key, value in zip(thing.keys(), thing.vals())}
    if isinstance(thing, (list, tuple)):
        return [dump(item) for item in thing]
    if isinstance(thing, dict):
        return {key: dump(value) for key, value in thing.items()}
    return thing


def contains(big, small, path=''):
    """Everything in `small` must be in `big` with the same value (floats to 1e-9);
    `big` may have more. Returns the differences as strings."""
    problems = []
    if isinstance(small, dict):
        if not isinstance(big, dict):
            return [f'{path}: {big!r} is not a record']
        for key, value in small.items():
            if key not in big:
                problems.append(f'{path}/{key} is missing')
            else:
                problems += contains(big[key], value, f'{path}/{key}')
    elif isinstance(small, list):
        if not isinstance(big, list) or len(big) != len(small):
            return [f'{path}: {big!r} differs from {small!r}']
        for index, value in enumerate(small):
            problems += contains(big[index], value, f'{path}[{index}]')
    elif isinstance(small, float) or isinstance(big, float):
        try:
            if abs(float(big) - float(small)) > 1e-9 * max(1.0, abs(float(small))):
                problems.append(f'{path}: {big!r} differs from {small!r}')
        except (TypeError, ValueError):
            problems.append(f'{path}: {big!r} differs from {small!r}')
    elif big != small:
        problems.append(f'{path}: {big!r} differs from {small!r}')
    return problems


def sha(path):
    with open(path, 'rb') as handle:
        return hashlib.sha256(handle.read()).hexdigest()


class b_xlreader(bench):
    BenchName = 'xlreader'
    BenchVersion = 'M1.0.12'
    BenchHeader = ''
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        os.makedirs(OUTDIR, exist_ok=True)
        xl = xlw()
        xl.newbook(os.path.join(OUTDIR, 'orig'), 'Data', 'My Sheet')
        sheet = xl.orig.Data
        sheet.write(['label', 'value', 'flag']).nl()
        sheet.write(['alpha', 3.14159, True]).nl()
        sheet.write(['beta', 1234567.5, False]).nl()
        sheet.write('styled', 'bold', True, 'fill', 'FFFF00', 'color', 'C00000', 'sz', 14,
                    'font', 'Cambria').write(0.00012, 'numfmt', '0.00E+00')
        sheet.write(42, 'halign', 'center', 'wrap', True, 'indent', 2, 'rotation', -30)
        sheet.write('x', 'italic', True, 'underline', True, 'strikethrough', True,
                    'shrink', True, 'valign', 'bottom').nl()
        sheet.write(7, 'numfmt', '0.00%').nl()
        sheet.write('quote & <b> "q"').write('(paren)').nl()
        sheet.border([(7, 1), (7, 2)], 'n:medium,s:double', 'color', 'FF0000')
        xl.orig.My_Sheet.write('second sheet')
        xl.orig.My_Sheet.gridlines(False)
        chart = xl.orig.Data.chart('conc')
        chart.title.text = 'Concentration'
        chart.xaxis.title.text = [('T (', {}), ('o', {'baseline': 30}), ('C)', {})]
        chart.yaxis.title.text = 'conc'
        chart.yaxis.log = 10
        chart.xaxis.min = 0
        chart.xaxis.max = 5
        chart.legend.pos = 'b'
        first = CH['add_series'](chart, 'Data!$B$2:$B$3', 'Data!$B$2:$B$3', label='A',
                                 marker=dict(symbol='diamond', size=7))
        CH['add_series'](chart, 'Data!$B$2:$B$3', 'Data!$B$2:$B$3', labelref='Data!$A$1',
                         axis=2, line=dict(color='C00000', dash='dash'), smooth=True)
        first.trend.fit = 'linear'
        first.trend.rsq = True
        first.yerr.value = 0.5
        xl.save()
        cls.original = xl
        cls.reader = xlw()
        cls.book = cls.reader.open(os.path.join(OUTDIR, 'orig.xlsx'))

    def excel(self, name):
        path = os.path.join(REFERENCE, name)
        if not os.path.isfile(path):
            self.skipTest('no reference workbook in results/reference')
        return path

    def charts_of(self, book):
        found = []
        for key in book.kvr('priv').kvr('sheetkeys'):
            charts = book.kvr(key).kvr('priv').kvr('charts')
            if charts is not None:
                found += charts.nodes()
        return found

    def excel_chart_parts(self):
        found = []
        for name in (CRYSTAL, XRD):
            path = self.excel(name)
            archive = zipfile.ZipFile(path)
            for part in sorted(archive.namelist()):
                if re.fullmatch(r'xl/charts/chart\d+\.xml', part):
                    found.append((name, part, archive.read(part)))
        return found

    # ---- our own workbooks ----------------------------------------------------------
    def test_T01_book_name_sheets_and_the_safe_output_file(self):
        bpriv = self.book.kvr('priv')
        self.assertEqual(self.book.name(), 'orig_xlw')
        self.assertEqual(bpriv.kvr('sheets'), ['Data', 'My Sheet'])
        self.assertTrue(bpriv.kvr('fname').endswith('orig_xlw.xlsx'))

    def test_T02_every_cell_value_and_style_round_trips(self):
        original = cell_table(self.original.orig.Data)
        read = cell_table(self.book.Data)
        self.assertEqual(sorted(original), sorted(read))
        for key in original:
            self.assertEqual(read[key], original[key], f'cell {key}')

    def test_T03_value_types(self):
        data = self.book.Data
        self.assertEqual(at(data, 2, 1).kvr('val'), 'alpha')
        self.assertAlmostEqual(at(data, 2, 2).kvr('val'), 3.14159, places=12)
        self.assertIs(at(data, 2, 3).kvr('val'), True)
        self.assertIs(at(data, 3, 3).kvr('val'), False)
        self.assertEqual(at(data, 6, 1).kvr('val'), 'quote & <b> "q"')
        self.assertEqual(at(data, 6, 2).kvr('val'), '(paren)')

    def test_T04_style_properties(self):
        cell = at(self.book.Data, 4, 1)
        self.assertTrue(cell.kvr('bold'))
        self.assertEqual(cell.kvr('fill'), 'FFFF00')
        self.assertEqual(cell.kvr('color'), 'C00000')
        self.assertEqual(cell.kvr('sz'), 14)
        self.assertEqual(cell.kvr('font'), 'Cambria')
        self.assertEqual(at(self.book.Data, 4, 2).kvr('numfmt'), '0.00E+00')
        centred = at(self.book.Data, 4, 3)
        self.assertEqual(centred.kvr('halign'), 'center')
        self.assertTrue(centred.kvr('wrap'))
        self.assertEqual(centred.kvr('indent'), 2)
        self.assertEqual(centred.kvr('rotation'), -30)

    def test_T05_border_and_its_colour(self):
        cell = at(self.book.Data, 7, 1)
        edges = {edge: (style, color) for edge, style, color in cell.kvr('border')}
        self.assertEqual(edges['n'], ('medium', 'FF0000'))
        self.assertEqual(edges['s'], ('double', 'FF0000'))
        self.assertEqual(cell.kvr('bcolor'), 'FF0000')

    def test_T06_blank_styled_cell_is_blank(self):
        self.assertEqual(at(self.book.Data, 7, 2).kvr('val'), None)

    def test_T07_second_sheet_and_grid_lines(self):
        sheet = self.book.My_Sheet
        self.assertEqual(at(sheet, 1, 1).kvr('val'), 'second sheet')
        self.assertFalse(sheet.kvr('showGrid'))
        self.assertTrue(self.book.Data.kvr('showGrid'))

    def test_T08_reading_never_overwrites_the_source(self):
        source = os.path.join(OUTDIR, 'orig.xlsx')
        before = sha(source)
        reader = xlw()
        book = reader.open(source)
        book.save()
        self.assertEqual(sha(source), before)
        self.assertTrue(os.path.isfile(os.path.join(OUTDIR, 'orig_xlw.xlsx')))

    def test_T09_read_save_read_gives_the_same_cells(self):
        reader = xlw()
        first = reader.open(os.path.join(OUTDIR, 'orig.xlsx'), name='pass1')
        first.save()
        second = xlw().open(os.path.join(OUTDIR, 'pass1_xlw.xlsx'), name='pass2')
        self.assertEqual(cell_table(second.Data), cell_table(first.Data))

    def test_T10_the_reader_reports_nothing_for_a_workbook_xlw_wrote(self):
        self.assertEqual(self.book.kvr('priv').kvr('unmapped'), [])

    # ---- our own chart --------------------------------------------------------------
    def test_T11_chart_series_axes_and_titles(self):
        chart = self.charts_of(self.book)[0]
        series = chart.kvr('series').nodes()
        self.assertEqual(len(series), 2)
        self.assertEqual(series[0].kvr('label'), 'A')
        self.assertEqual(series[0].kvr('x'), 'Data!$B$2:$B$3')
        self.assertEqual(series[0].kvr('marker').kvr('symbol'), 'diamond')
        self.assertEqual(series[0].kvr('marker').kvr('size'), 7)
        self.assertEqual(series[1].kvr('labelref'), 'Data!$A$1')
        self.assertEqual(series[1].kvr('axis'), 2)
        self.assertTrue(series[1].kvr('smooth'))
        self.assertEqual(series[1].kvr('line').kvr('color'), 'C00000')
        self.assertEqual(series[1].kvr('line').kvr('dash'), 'dash')
        self.assertEqual(chart.title.kvr('text'), 'Concentration')
        runs = chart.xaxis.title.kvr('text')
        self.assertEqual([piece for piece, props in runs], ['T (', 'o', 'C)'])
        self.assertEqual(runs[1][1]['baseline'], 30)
        self.assertEqual(chart.yaxis.kvr('log'), 10)
        self.assertEqual(chart.xaxis.kvr('min'), 0)
        self.assertEqual(chart.xaxis.kvr('max'), 5)
        self.assertEqual(chart.legend.kvr('pos'), 'b')

    def test_T12_trendline_and_error_bars(self):
        series = self.charts_of(self.book)[0].kvr('series').nodes()[0]
        self.assertEqual(series.trend.kvr('fit'), 'linear')
        self.assertTrue(series.trend.kvr('rsq'))
        self.assertEqual(series.yerr.kvr('value'), 0.5)
        self.assertEqual(series.yerr.kvr('mode'), 'fixed')

    def test_T13_secondary_axis_nodes_exist_and_x2_is_hidden(self):
        chart = self.charts_of(self.book)[0]
        self.assertTrue(chart.isnode('y2axis'))
        self.assertFalse(chart.x2axis.kvr('visible'))

    def test_T14_our_chart_reaches_a_fixpoint(self):
        chart = self.charts_of(self.book)[0]
        scratch = xlw()
        scratch.newbook(os.path.join(OUTDIR, 'scratch'), 'S')
        again = RD['read_chart_xml'](CH['chart_part'](chart).encode('utf-8'),
                                     scratch.scratch.S, 'again')
        before = dump(chart)
        before.pop('anchor')              # the anchor belongs to the drawing, not the chart
        self.assertEqual(contains(dump(again), before), [])
        self.assertEqual(contains(before, dump(again)), [])

    # ---- files from elsewhere ----------------------------------------------------------
    def test_T15_the_matlab_written_files_read(self):
        data = xlw().open(os.path.join(FIXTURES, 'data.xlsx'))
        self.assertEqual(data.kvr('priv').kvr('sheets'), ['S1', 'Two'])
        self.assertEqual(at(data.S1, 1, 1).kvr('val'), 'one-A1')
        self.assertEqual(at(data.Two, 1, 1).kvr('val'), 'two-A1')
        grid = xlw().open(os.path.join(FIXTURES, 'bench.xlsx'))
        self.assertEqual(ncells(grid.S1), 144)
        self.assertEqual(at(grid.S1, 1, 1).kvr('numfmt'), '0')
        small = xlw().open(os.path.join(FIXTURES, 'scale_10.xlsx'))
        self.assertEqual(ncells(small.S1), 100)

    def test_T16_an_excel_authored_workbook_reads_with_fonts_and_a_report(self):
        book = xlw().open(os.path.join(FIXTURES, 'htmltags.xlsx'))
        bpriv = book.kvr('priv')
        self.assertEqual(bpriv.kvr('sheets'), ['Sheet1', 'Sheet2'])
        cell = at(book.Sheet1, 1, 1)
        self.assertEqual(cell.kvr('font'), 'JetBrains Mono')
        self.assertEqual(cell.kvr('sz'), 10.5)
        self.assertEqual(cell.kvr('color'), '067D17')
        self.assertEqual(cell.kvr('valign'), 'center')
        self.assertEqual(cell.kvr('val'), None)                 # styled, no value
        report = ' | '.join(bpriv.kvr('unmapped'))
        self.assertNotIn('formula', report)                     # the formulas are read now
        self.assertIn('sortState', report)
        self.assertEqual(len(formula_table(book.Sheet1)) + len(formula_table(book.Sheet2)), 104)

    def test_T17_extension_noise_is_not_reported(self):
        book = xlw().open(self.excel(CRYSTAL))
        report = ' | '.join(book.kvr('priv').kvr('unmapped'))
        for noise in ('AlternateContent', 'extLst', 'userShapes', 'printSettings',
                      'chartStyle', 'colors'):
            self.assertNotIn(noise, report)
        self.assertIn('pictures', report)
        self.assertNotIn('formula', report)
        self.assertEqual(len(formula_table(book.kvr(book.kvr('priv').kvr('sheetkeys')[0]))), 61)

    def test_T18_the_excel_workbooks_have_the_expected_cells_and_charts(self):
        crystal = xlw().open(self.excel(CRYSTAL))
        self.assertEqual(len(self.charts_of(crystal)), 3)
        self.assertEqual(len(crystal.kvr('priv').kvr('sheets')), 1)
        xrd = xlw().open(self.excel(XRD))
        self.assertEqual(len(self.charts_of(xrd)), 1)
        sheet = xrd.Sheet1
        self.assertEqual(ncells(sheet), 9015)

    # ---- the Excel charts, read ----------------------------------------------------------
    def crystal_chart(self, first_x):
        """The Crystal16 chart whose first series has this x range."""
        book = xlw().open(self.excel(CRYSTAL))
        for chart in self.charts_of(book):
            if chart.kvr('series').nodes()[0].kvr('x') == first_x:
                return chart
        self.fail('chart not found')

    def test_T19_crystal_two_series_chart(self):
        chart = self.crystal_chart('BLOCK_A_2_2__2_8!$K$2:$K$5')
        first, second = chart.kvr('series').nodes()
        self.assertEqual(first.kvr('x'), 'BLOCK_A_2_2__2_8!$K$2:$K$5')
        self.assertEqual(first.kvr('y'), 'BLOCK_A_2_2__2_8!$M$2:$M$5')
        self.assertEqual(first.kvr('marker').kvr('symbol'), 'diamond')
        self.assertEqual(first.kvr('marker').kvr('size'), 6)
        self.assertFalse(first.kvr('smooth'))
        self.assertEqual(second.kvr('label'), 'Equation 1 Fit')
        self.assertEqual(second.kvr('marker').kvr('symbol'), 'none')
        self.assertTrue(second.kvr('smooth'))
        self.assertIsNone(chart.kvr('title'))

    def test_T20_crystal_axis_titles_and_legend(self):
        chart = self.crystal_chart('BLOCK_A_2_2__2_8!$K$2:$K$5')
        runs = chart.xaxis.title.kvr('text')
        self.assertEqual([piece for piece, props in runs],
                         ['Temperature (', 'o', 'C)'])
        self.assertEqual(runs[1][1]['baseline'], 30)
        self.assertEqual(chart.yaxis.title.kvr('text'), 'Concentration (mg/ml)')
        self.assertEqual(chart.legend.kvr('pos'), 'r')
        self.assertTrue(chart.legend.kvr('overlay'))
        self.assertAlmostEqual(chart.legend.kvr('layout').kvr('x'), 0.60555297, places=6)
        self.assertEqual(chart.xaxis.kvr('tickmajor'), 'out')

    def test_T21_crystal_trendline_chart(self):
        book = xlw().open(self.excel(CRYSTAL))
        found = [chart for chart in self.charts_of(book)
                 if chart.kvr('series').nodes()[0].isnode('trend')]
        self.assertEqual(len(found), 1)
        series = found[0].kvr('series').nodes()[0]
        self.assertEqual(series.trend.kvr('fit'), 'linear')
        self.assertTrue(series.trend.kvr('rsq'))
        self.assertTrue(series.trend.kvr('eq'))
        self.assertEqual(series.kvr('marker').kvr('symbol'), 'circle')
        self.assertTrue(series.kvr('line').kvr('none'))
        self.assertEqual(series.trend.kvr('line').kvr('dash'), 'sysDot')
        self.assertTrue(found[0].isnode('title'))
        self.assertIsNone(found[0].xaxis.kvr('gridminor'))
        self.assertIsNotNone(found[0].xaxis.kvr('gridmajor'))
        self.assertFalse(found[0].xaxis.kvr('gridmajor').kvr('none'))

    def test_T22_xrd_chart_is_smooth_without_markers(self):
        book = xlw().open(self.excel(XRD))
        chart = self.charts_of(book)[0]
        series = chart.kvr('series').nodes()[0]
        self.assertEqual(chart.kvr('style'), 'smoothMarker')
        self.assertTrue(series.kvr('smooth'))
        self.assertEqual(series.kvr('marker').kvr('symbol'), 'none')
        self.assertTrue(series.kvr('x').startswith('Sheet1!$'))
        self.assertIsNone(chart.kvr('title'))

    def test_T23_primary_axes_without_gridlines_are_recorded_as_none(self):
        book = xlw().open(self.excel(XRD))
        chart = self.charts_of(book)[0]
        for axis in (chart.xaxis, chart.yaxis):
            grid = axis.kvr('gridmajor')
            if grid is not None:
                self.assertTrue(grid.kvr('none') or grid.kvr('color'))

    # ---- the fixpoint: Excel chart -> read -> write -> read ------------------------------
    def test_T24_every_excel_chart_survives_read_write_read(self):
        parts = self.excel_chart_parts()
        scratch = xlw()
        scratch.newbook(os.path.join(OUTDIR, 'fix'), 'S')
        sheet = scratch.fix.S
        for name, part, data in parts:
            first = RD['read_chart_xml'](data, sheet, 'first')
            xml = CH['chart_part'](first)
            second = RD['read_chart_xml'](xml.encode('utf-8'), sheet, 'second')
            self.assertEqual(contains(dump(second), dump(first)), [], f'{name} {part}')
            self.assertEqual(order_errors(ET.fromstring(xml)), [], f'{name} {part}')
            sheet.kvr('priv').kvr('charts').remove('first')
            sheet.kvr('priv').kvr('charts').remove('second')

    def test_T25_an_excel_chart_written_into_a_workbook_is_a_valid_package(self):
        book_xl = xlw()
        book = book_xl.open(self.excel(CRYSTAL), name='roundtrip')
        out = os.path.join(OUTDIR, 'roundtrip_xlw.xlsx')
        book.kvr('priv').kvw('fname', out)
        book_xl.save()
        archive = zipfile.ZipFile(out)
        charts = [name for name in archive.namelist() if re.fullmatch(r'xl/charts/chart\d+\.xml', name)]
        self.assertEqual(len(charts), 3)
        for name in archive.namelist():
            ET.fromstring(archive.read(name))
        for name in charts:
            self.assertEqual(order_errors(ET.fromstring(archive.read(name))), [])
        again = xlw().open(out, name='again')
        self.assertEqual(len(self.charts_of(again)), 3)
        self.assertEqual(len(cell_table(again.BLOCK_A_2_2__2_8)),
                         len(cell_table(book.BLOCK_A_2_2__2_8)))

    # ---- helper functions -----------------------------------------------------------------
    def test_T26_colour_strings_from_drawingml(self):
        root = ET.fromstring(
            '<a:solidFill xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<a:schemeClr val="tx1"><a:lumMod val="65000"/><a:lumOff val="35000"/>'
            '</a:schemeClr></a:solidFill>')
        self.assertEqual(xlreader.draw_color(root), ('theme:tx1:65000:35000', None))
        srgb = ET.fromstring(
            '<a:solidFill xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<a:srgbClr val="4472c4"><a:alpha val="50000"/></a:srgbClr></a:solidFill>')
        self.assertEqual(xlreader.draw_color(srgb), ('4472C4', 50.0))
        system = ET.fromstring(
            '<a:solidFill xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<a:sysClr val="windowText" lastClr="000000"/></a:solidFill>')
        self.assertEqual(xlreader.draw_color(system), ('sys:windowText:000000', None))

    def test_T27_a_workbook_that_is_not_there_is_an_error(self):
        with self.assertRaises(FileNotFoundError):
            xlw().open(os.path.join(OUTDIR, 'does_not_exist.xlsx'))

    def test_T28_a_file_that_is_not_a_workbook_is_an_error(self):
        path = os.path.join(OUTDIR, 'not_a_workbook.xlsx')
        with open(path, 'w') as handle:
            handle.write('plain text')
        with self.assertRaises(zipfile.BadZipFile):
            xlw().open(path)

    # ---- benchmarks: the helpers that run once per chart element --------------------------
    def bench_draw_color(self, timer):
        element = ET.fromstring(
            '<a:solidFill xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<a:schemeClr val="tx1"><a:lumMod val="65000"/><a:lumOff val="35000"/>'
            '</a:schemeClr></a:solidFill>')
        draw = xlreader.draw_color
        with timer as test:
            while test.more:
                for i in test.count:
                    draw(element)
        return 'draw_color (theme colour, two modifiers)', 'helpers'

    def bench_line_record(self, timer):
        element = ET.fromstring(
            '<a:ln xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'w="9525" cap="flat"><a:solidFill><a:schemeClr val="tx1"><a:lumMod val="15000"/>'
            '<a:lumOff val="85000"/></a:schemeClr></a:solidFill><a:prstDash val="dash"/>'
            '<a:round/></a:ln>')
        make = xlreader.line_record
        with timer as test:
            while test.more:
                for i in test.count:
                    make(element)
        return 'line_record (width, cap, colour, dash)', 'helpers'
