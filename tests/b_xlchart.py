"""
b_xlchart.py -- tests and benchmarks for xlchart, the XY chart definition and its XML.

The central check is element ORDER, because Excel refuses or repairs a chart whose
elements are out of order and does not say why. The child sequences of the ECMA-376 schema
are in chartcheck.py, typed in independently of the code under test. The same validator is also run over the charts Excel itself wrote
(results/reference, skipped when those files are absent): if it accepts those, the
tables are right.

Run from the project root:
    python tools/runbench.py tests/b_xlchart.py
"""

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

SOURCES = ['xlchart', 'xlw']
globals().update(load('xlw', into={}))
CH = load('xlchart', into={})

OUTDIR = os.path.join(ROOT, 'results', 'b_xlchart')
REFERENCE = os.path.join(ROOT, 'results', 'reference')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chartcheck import ORDER, local, order_errors, package_errors


def chart_root(chart, values=None):
    return ET.fromstring(CH['chart_part'](chart, values))


class b_xlchart(bench):
    BenchName = 'xlchart'
    BenchVersion = 'M1.0.6'
    BenchHeader = ''
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        os.makedirs(OUTDIR, exist_ok=True)
        cls.rich = cls.build()

    @classmethod
    def build(cls):
        xl = xlw()
        xl.newbook(os.path.join(OUTDIR, 'rich'), 'Data')
        xl.write(['t', 'A', 'B']).nl()
        for i in range(11):
            xl.write([i * 0.1, 1.0 - i * 0.08, 100 + i * 7.0]).nl()
        chart = xl.chart('conc')
        chart.title.text = 'Concentration vs time'
        chart.xaxis.title.text = [('time (s', {}), (')', {})]
        chart.yaxis.title.text = 'conc'
        chart.legend.pos = 'r'
        first = CH['add_series'](chart, 'Data!$A$2:$A$12', 'Data!$B$2:$B$12', label='A',
                                 marker=dict(symbol='diamond', size=6))
        CH['add_series'](chart, 'Data!$A$2:$A$12', 'Data!$C$2:$C$12',
                         labelref='Data!$C$1', axis=2,
                         line=dict(color='C00000', dash='dash'))
        first.trend.fit = 'linear'
        first.trend.rsq = True
        first.trend.eq = True
        first.yerr.value = 0.05
        chart.y2axis.title.text = 'B'
        chart.xaxis.min = 0
        chart.xaxis.max = 1
        return xl, chart

    def plain(self, **chart_settings):
        """A fresh writer with data in A1:C6 and one chart with one series."""
        xl = xlw()
        xl.newbook(os.path.join(OUTDIR, 'plain'), 'Data')
        xl.write([[1, 2, 3], [2, 4, 8], [3, 6, 27], [4, 8, 64], [5, 10, 125]])
        chart = xl.chart('c1')
        CH['add_series'](chart, 'Data!$A$1:$A$5', 'Data!$B$1:$B$5', label='B')
        return xl, chart

    # ---- building ----------------------------------------------------------------
    def test_T01_new_chart_is_a_node_under_the_sheet_private_tree(self):
        xl, chart = self.plain()
        charts = xl.plain.Data.kvr('priv').kvr('charts')
        self.assertEqual(charts.names(), ['c1'])
        self.assertIs(charts.kvr('c1'), chart)

    def test_T02_chart_names_are_made_safe_and_default_to_a_number(self):
        xl = xlw()
        xl.newbook(os.path.join(OUTDIR, 'chartnames'), 'S')
        first = xl.chart()
        second = xl.chart('my chart')
        self.assertEqual(first.name(), 'chart1')
        self.assertEqual(second.name(), 'my_chart')

    def test_T03_series_keep_their_order_and_leaves(self):
        xl, chart = self.plain()
        CH['add_series'](chart, [1, 2, 3], [4, 5, 6], smooth=True)
        names = chart.kvr('series').names()
        self.assertEqual(names, ['s1', 's2'])
        self.assertEqual(chart.series.s2.kvr('y'), [4, 5, 6])
        self.assertTrue(chart.series.s2.kvr('smooth'))

    def test_T04_series_options_given_as_dicts_become_records(self):
        xl, chart = self.plain()
        node = CH['add_series'](chart, 'Data!$A$1:$A$5', 'Data!$C$1:$C$5',
                                line=dict(color='FF0000', width=3))
        self.assertEqual(node.kvr('line').kvr('color'), 'FF0000')
        self.assertEqual(node.kvr('line').kvr('width'), 3)

    def test_T05_rec_leaves_out_none(self):
        record = CH['rec'](name='Calibri', height=None, bold=False)
        self.assertEqual(sorted(record.keys()), ['bold', 'name'])

    def test_T06_place_sets_the_anchor(self):
        xl, chart = self.plain()
        CH['place'](chart, 4, 2, ncols=6, nrows=10)
        self.assertEqual(CH['anchor_of'](chart), (4, 0, 2, 0, 10, 0, 12, 0))

    def test_T07_default_anchor_is_beside_the_data_and_below_earlier_charts(self):
        xl, chart = self.plain()
        self.assertEqual(CH['anchor_of'](chart, 3, 0)[0], 4)
        self.assertEqual(CH['anchor_of'](chart, 3, 1)[2], 21)

    def test_T08_ref_and_parse_ref(self):
        ref = CH['ref']
        parse = CH['parse_ref']
        self.assertEqual(ref('Data', 2, 1, 100, 1), 'Data!$A$2:$A$100')
        self.assertEqual(ref('Data', 3, 28), 'Data!$AB$3')
        self.assertEqual(ref("It's here", 1, 2, 4, 2), "'It''s here'!$B$1:$B$4")
        self.assertEqual(parse('Data!$A$2:$A$100'), ('Data', 2, 1, 100, 1))
        self.assertEqual(parse("'It''s here'!$B$1:$B$4"), ("It's here", 1, 2, 4, 2))
        self.assertEqual(parse('Data!$AB$3'), ('Data', 3, 28, 3, 28))
        self.assertIsNone(parse('not a ref'))
        self.assertIsNone(parse([1, 2]))

    # ---- the XML: structure and order -------------------------------------------------
    def test_T09_minimal_chart_is_valid_and_complete(self):
        xl, chart = self.plain()
        root = chart_root(chart)
        self.assertEqual(order_errors(root), [])
        names = [local(item.tag) for item in root.iter()]
        self.assertEqual(names.count('valAx'), 2)
        self.assertEqual(names.count('axId'), 4)            # two in the chart, two axes
        self.assertEqual(names.count('catAx'), 0)
        self.assertEqual(root.find('.//{*}autoTitleDeleted').get('val'), '1')

    def test_T10_rich_chart_is_valid(self):
        xl, chart = self.rich
        self.assertEqual(order_errors(chart_root(chart)), [])

    def test_T11_two_axis_chart_has_two_groups_and_four_axes(self):
        xl, chart = self.rich
        root = chart_root(chart)
        names = [local(item.tag) for item in root.iter()]
        self.assertEqual(names.count('scatterChart'), 2)
        self.assertEqual(names.count('valAx'), 4)
        axes = root.findall('.//{*}valAx')
        positions = [axis.find('{*}axPos').get('val') for axis in axes]
        self.assertEqual(positions, ['b', 'l', 'b', 'r'])
        self.assertEqual(axes[2].find('{*}delete').get('val'), '1')   # secondary x hidden
        self.assertEqual(axes[3].find('{*}crosses').get('val'), 'max')

    def test_T12_axis_ids_are_unique_and_the_cross_axes_pair_up(self):
        xl, chart = self.rich
        axes = chart_root(chart).findall('.//{*}valAx')
        ids = [axis.find('{*}axId').get('val') for axis in axes]
        self.assertEqual(len(set(ids)), 4)
        for first, second in ((0, 1), (2, 3)):
            self.assertEqual(axes[first].find('{*}crossAx').get('val'), ids[second])
            self.assertEqual(axes[second].find('{*}crossAx').get('val'), ids[first])

    def test_T13_scaling_order_is_logbase_orientation_max_min(self):
        xl, chart = self.plain()
        chart.yaxis.log = 10
        chart.yaxis.min = 1
        chart.yaxis.max = 1000
        chart.yaxis.reverse = True
        root = chart_root(chart)
        scaling = root.findall('.//{*}valAx')[1].find('{*}scaling')
        self.assertEqual([local(item.tag) for item in scaling],
                         ['logBase', 'orientation', 'max', 'min'])
        self.assertEqual(scaling.find('{*}orientation').get('val'), 'maxMin')
        self.assertEqual(order_errors(root), [])

    def test_T14_crossing_is_written_into_the_other_axis(self):
        xl, chart = self.plain()
        chart.yaxis.crossesat = 5                 # the X axis crosses at Y = 5
        chart.xaxis.crosses = 'max'               # the Y axis crosses at the X maximum
        axes = chart_root(chart).findall('.//{*}valAx')
        self.assertEqual(axes[0].find('{*}crossesAt').get('val'), '5')
        self.assertIsNone(axes[0].find('{*}crosses'))
        self.assertEqual(axes[1].find('{*}crosses').get('val'), 'max')

    def test_T15_units_ticks_labels_and_number_format(self):
        xl, chart = self.plain()
        chart.xaxis.major = 0.5
        chart.xaxis.minor = 0.1
        chart.xaxis.tickmajor = 'cross'
        chart.xaxis.ticklabels = 'low'
        chart.xaxis.numfmt = '0.00'
        axis = chart_root(chart).findall('.//{*}valAx')[0]
        self.assertEqual(axis.find('{*}majorUnit').get('val'), '0.5')
        self.assertEqual(axis.find('{*}minorUnit').get('val'), '0.1')
        self.assertEqual(axis.find('{*}majorTickMark').get('val'), 'cross')
        self.assertEqual(axis.find('{*}tickLblPos').get('val'), 'low')
        self.assertEqual(axis.find('{*}numFmt').get('formatCode'), '0.00')
        self.assertEqual(axis.find('{*}numFmt').get('sourceLinked'), '0')

    def test_T16_gridlines_default_off_and_switch(self):
        xl, chart = self.plain()
        chart.yaxis.gridmajor = CH['rec'](none=True)
        chart.xaxis.gridminor = CH['rec'](color='EEEEEE')
        axes = chart_root(chart).findall('.//{*}valAx')
        self.assertIsNotNone(axes[0].find('{*}majorGridlines'))
        self.assertIsNone(axes[1].find('{*}majorGridlines'))
        self.assertIsNotNone(axes[0].find('{*}minorGridlines'))

    def test_T17_title_with_runs_and_superscript(self):
        xl, chart = self.plain()
        chart.xaxis.title.text = [('T (', {}), ('o', {'baseline': 30}), ('C)', {})]
        title = chart_root(chart).findall('.//{*}valAx')[0].find('{*}title')
        runs = title.findall('.//{*}r')
        self.assertEqual([run.find('{*}t').text for run in runs], ['T (', 'o', 'C)'])
        self.assertEqual(runs[1].find('{*}rPr').get('baseline'), '30000')

    def test_T18_y_title_is_rotated_and_x_title_is_not(self):
        xl, chart = self.plain()
        chart.xaxis.title.text = 'x'
        chart.yaxis.title.text = 'y'
        axes = chart_root(chart).findall('.//{*}valAx')
        self.assertEqual(axes[0].find('.//{*}rich/{*}bodyPr').get('rot'), '0')
        self.assertEqual(axes[1].find('.//{*}rich/{*}bodyPr').get('rot'), '-5400000')

    def test_T19_chart_title_present_turns_the_auto_title_flag_off(self):
        xl, chart = self.plain()
        chart.title.text = 'T'
        root = chart_root(chart)
        self.assertEqual(root.find('.//{*}autoTitleDeleted').get('val'), '0')
        self.assertEqual(root.find('.//{*}chart/{*}title//{*}t').text, 'T')

    def test_T20_series_name_literal_and_from_a_cell(self):
        xl, chart = self.rich
        series = chart_root(chart).findall('.//{*}ser')
        self.assertEqual(series[0].find('{*}tx/{*}v').text, 'A')
        self.assertEqual(series[1].find('{*}tx/{*}strRef/{*}f').text, 'Data!$C$1')

    def test_T21_data_cache_holds_the_cell_values(self):
        xl, chart = self.rich
        values = None
        import xlw as xlwmodule
        book = xl.rich
        values = xlwmodule.book_values(book)
        root = chart_root(chart, values)
        cache = root.find('.//{*}ser/{*}yVal/{*}numRef/{*}numCache')
        self.assertEqual(cache.find('{*}ptCount').get('val'), '11')
        points = cache.findall('{*}pt')
        self.assertEqual(len(points), 11)
        self.assertAlmostEqual(float(points[1].find('{*}v').text), 0.92)

    def test_T22_blank_and_text_cells_leave_no_point(self):
        xl, chart = self.plain()
        root = chart_root(chart, lambda ref: [1.0, None, 'text', float('nan'), 5.0])
        cache = root.find('.//{*}ser/{*}xVal/{*}numRef/{*}numCache')
        self.assertEqual(cache.find('{*}ptCount').get('val'), '5')
        self.assertEqual([pt.get('idx') for pt in cache.findall('{*}pt')], ['0', '4'])

    def test_T23_literal_data_is_numlit(self):
        xl = xlw()
        xl.newbook(os.path.join(OUTDIR, 'lit'), 'S')
        chart = xl.chart('c')
        CH['add_series'](chart, [1, 2, 3], [4.5, 5.5, 6.5])
        root = chart_root(chart)
        self.assertIsNotNone(root.find('.//{*}xVal/{*}numLit'))
        self.assertEqual(order_errors(root), [])

    def test_T24_palette_cycles_and_marker_none_has_no_size(self):
        xl, chart = self.plain()
        CH['add_series'](chart, [1], [2], marker=dict(symbol='none'))
        series = chart_root(chart).findall('.//{*}ser')
        self.assertEqual(series[0].find('.//{*}ln//{*}srgbClr').get('val'), '4472C4')
        self.assertEqual(series[1].find('.//{*}ln//{*}srgbClr').get('val'), 'ED7D31')
        marker = series[1].find('{*}marker')
        self.assertEqual([local(item.tag) for item in marker], ['symbol'])

    def test_T25_chart_style_controls_default_lines_markers_and_smoothing(self):
        xl, chart = self.plain()
        chart.style = 'marker'
        series = chart_root(chart).find('.//{*}ser')
        self.assertIsNotNone(series.find('{*}spPr/{*}ln/{*}noFill'))
        chart.style = 'smooth'
        series = chart_root(chart).find('.//{*}ser')
        self.assertEqual(series.find('{*}smooth').get('val'), '1')
        self.assertEqual(series.find('{*}marker/{*}symbol').get('val'), 'none')

    def test_T26_trendline_children_in_order(self):
        xl, chart = self.plain()
        node = chart.series.s1
        node.trend.fit = 'poly'
        node.trend.order = 3
        node.trend.forward = 2
        node.trend.intercept = 0
        node.trend.rsq = True
        node.trend.label = 'cubic'
        node.trend.numfmt = '0.000'
        root = chart_root(chart)
        trend = root.find('.//{*}trendline')
        self.assertEqual([local(item.tag) for item in trend],
                         ['name', 'spPr', 'trendlineType', 'order', 'forward', 'intercept',
                          'dispRSqr', 'dispEq', 'trendlineLbl'])
        self.assertEqual(order_errors(root), [])

    def test_T27_error_bars_fixed_percentage_and_custom(self):
        xl, chart = self.plain()
        node = chart.series.s1
        node.xerr.value = 0.5
        node.xerr.dir = 'plus'
        node.yerr.mode = 'custom'
        node.yerr.plus = 'Data!$C$1:$C$5'
        node.yerr.minus = [1, 1, 1, 1, 1]
        root = chart_root(chart)
        bars = root.findall('.//{*}errBars')
        self.assertEqual(len(bars), 2)
        self.assertEqual(bars[0].find('{*}errDir').get('val'), 'x')
        self.assertEqual(bars[0].find('{*}errBarType').get('val'), 'plus')
        self.assertEqual(bars[0].find('{*}errValType').get('val'), 'fixedVal')
        self.assertEqual(bars[1].find('{*}errValType').get('val'), 'cust')
        self.assertIsNotNone(bars[1].find('{*}plus/{*}numRef'))
        self.assertIsNotNone(bars[1].find('{*}minus/{*}numLit'))
        self.assertEqual(order_errors(root), [])

    def test_T28_data_labels(self):
        xl, chart = self.plain()
        node = chart.series.s1
        node.labels.showy = True
        node.labels.pos = 't'
        node.labels.numfmt = '0.0'
        root = chart_root(chart)
        labels = root.find('.//{*}ser/{*}dLbls')
        self.assertEqual(labels.find('{*}showVal').get('val'), '1')
        self.assertEqual(labels.find('{*}dLblPos').get('val'), 't')
        self.assertEqual(order_errors(root), [])

    def test_T29_legend_position_hide_and_layout(self):
        xl, chart = self.build()                  # its own chart: this test changes it
        chart.legend.pos = 'b'
        chart.legend.hide = [2]
        chart.legend.layout = CH['rec'](x=0.1, y=0.2, w=0.3, h=0.1)
        root = chart_root(chart)
        legend = root.find('.//{*}legend')
        self.assertEqual(legend.find('{*}legendPos').get('val'), 'b')
        self.assertEqual(legend.find('{*}legendEntry/{*}idx').get('val'), '1')
        self.assertEqual(legend.find('.//{*}manualLayout/{*}x').get('val'), '0.1')
        self.assertEqual(order_errors(root), [])

    def test_T30_text_is_escaped_and_control_characters_removed(self):
        xl, chart = self.plain()
        chart.title.text = 'a < b & "c" \x00\x1f'
        root = chart_root(chart)
        self.assertEqual(root.find('.//{*}chart/{*}title//{*}t').text, 'a < b & "c" ')

    def test_T31_colours_theme_and_system_forms(self):
        xl, chart = self.plain()
        chart.series.s1['line'] = CH['rec'](color='theme:tx1:65000:35000', width=1)
        chart.xaxis['line'] = CH['rec'](color='sys:windowText:000000')
        root = chart_root(chart)
        scheme = root.find('.//{*}ser/{*}spPr//{*}schemeClr')
        self.assertEqual(scheme.get('val'), 'tx1')
        self.assertEqual(scheme.find('{*}lumMod').get('val'), '65000')
        self.assertEqual(scheme.find('{*}lumOff').get('val'), '35000')
        self.assertIsNotNone(root.find('.//{*}valAx/{*}spPr//{*}sysClr'))
        self.assertEqual(order_errors(root), [])

    def test_T32_chart_and_plot_area_fills(self):
        xl, chart = self.plain()
        chart.plotarea['fill'] = CH['rec'](color='F2F2F2')
        chart.chartarea['fill'] = CH['rec'](none=True)
        root = chart_root(chart)
        self.assertEqual(root.find('.//{*}plotArea/{*}spPr//{*}srgbClr').get('val'), 'F2F2F2')
        self.assertIsNotNone(root.find('{*}spPr/{*}noFill'))

    # ---- in the workbook ----------------------------------------------------------------
    def test_T33_workbook_with_a_chart_is_a_consistent_package(self):
        xl, chart = self.rich
        xl.save()
        fname = xl.rich.kvr('priv').kvr('fname')
        self.assertEqual(package_errors(fname), [])
        names = zipfile.ZipFile(fname).namelist()
        for part in ('xl/charts/chart1.xml', 'xl/drawings/drawing1.xml',
                     'xl/drawings/_rels/drawing1.xml.rels',
                     'xl/worksheets/_rels/sheet1.xml.rels'):
            self.assertIn(part, names)

    def test_T34_every_part_of_a_chart_workbook_is_well_formed(self):
        xl, chart = self.rich
        xl.save()
        archive = zipfile.ZipFile(xl.rich.kvr('priv').kvr('fname'))
        for name in archive.namelist():
            ET.fromstring(archive.read(name))

    def test_T35_the_drawing_anchors_the_chart_beside_the_data(self):
        xl, chart = self.rich
        xl.save()
        archive = zipfile.ZipFile(xl.rich.kvr('priv').kvr('fname'))
        drawing = ET.fromstring(archive.read('xl/drawings/drawing1.xml'))
        self.assertEqual(order_errors(drawing), [])
        col = drawing.find('.//{*}from/{*}col').text
        self.assertEqual(col, '4')                      # data ends in column C (3): gap

    def test_T36_sheet_xml_declares_the_drawing(self):
        xl, chart = self.rich
        xl.save()
        archive = zipfile.ZipFile(xl.rich.kvr('priv').kvr('fname'))
        sheet = archive.read('xl/worksheets/sheet1.xml').decode()
        self.assertIn('xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/'
                      'relationships"', sheet)
        self.assertTrue(sheet.rstrip().endswith('<drawing r:id="rId1"/></worksheet>'))
        self.assertLess(sheet.index('</sheetData>'), sheet.index('<drawing'))

    def test_T37_two_charts_on_one_sheet_and_charts_on_two_sheets(self):
        xl = xlw()
        xl.newbook(os.path.join(OUTDIR, 'many'), 'One', 'Two')
        sheet1 = xl.many.One
        sheet2 = xl.many.Two
        sheet1.write([[1, 2], [3, 4]])
        for sheet, count in ((sheet1, 2), (sheet2, 1)):
            for n in range(count):
                chart = sheet.chart(f'c{n}')
                CH['add_series'](chart, 'One!$A$1:$A$2', 'One!$B$1:$B$2')
        xl.save()
        fname = xl.many.kvr('priv').kvr('fname')
        self.assertEqual(package_errors(fname), [])
        archive = zipfile.ZipFile(fname)
        names = archive.namelist()
        for part in ('xl/charts/chart1.xml', 'xl/charts/chart2.xml', 'xl/charts/chart3.xml',
                     'xl/drawings/drawing1.xml', 'xl/drawings/drawing2.xml'):
            self.assertIn(part, names)
        first = ET.fromstring(archive.read('xl/drawings/drawing1.xml'))
        self.assertEqual(len(first.findall('{*}twoCellAnchor')), 2)

    def test_T38_a_book_without_charts_has_no_chart_parts(self):
        xl = xlw()
        xl.newbook(os.path.join(OUTDIR, 'none'), 'S')
        xl.write('x')
        xl.save()
        names = zipfile.ZipFile(os.path.join(OUTDIR, 'none.xlsx')).namelist()
        self.assertFalse([name for name in names if 'chart' in name or 'drawing' in name])

    def test_T39_chart_on_a_quoted_sheet_name(self):
        xl = xlw()
        xl.newbook(os.path.join(OUTDIR, 'quoted'), 'My Data')
        xl.write([[1, 2], [3, 4], [5, 6]])
        chart = xl.chart('c')
        CH['add_series'](chart, CH['ref']('My Data', 1, 1, 3, 1),
                         CH['ref']('My Data', 1, 2, 3, 2))
        xl.save()
        archive = zipfile.ZipFile(os.path.join(OUTDIR, 'quoted.xlsx'))
        root = ET.fromstring(archive.read('xl/charts/chart1.xml'))
        formula = root.find('.//{*}xVal//{*}f').text
        self.assertEqual(formula, "'My Data'!$A$1:$A$3")
        cache = root.find('.//{*}xVal//{*}numCache')
        self.assertEqual(len(cache.findall('{*}pt')), 3)         # found through the quote

    # ---- against the charts Excel wrote --------------------------------------------------
    def reference_charts(self):
        found = []
        for name in ('SB Solubility vs temperature.xlsx', 'Theopylline As recieved.xlsx'):
            path = os.path.join(REFERENCE, name)
            if os.path.isfile(path):
                archive = zipfile.ZipFile(path)
                for part in sorted(archive.namelist()):
                    if re.fullmatch(r'xl/charts/chart\d+\.xml', part):
                        found.append((name, part, archive.read(part)))
        return found

    def test_T40_the_order_tables_accept_every_chart_excel_wrote(self):
        charts = self.reference_charts()
        if not charts:
            self.skipTest('no reference workbooks in results/reference')
        for name, part, data in charts:
            self.assertEqual(order_errors(ET.fromstring(data)), [], f'{name} {part}')

    def test_T41_the_order_tables_reject_a_wrongly_ordered_chart(self):
        xl, chart = self.plain()
        text = CH['chart_part'](chart)
        wrong = text.replace('<c:plotVisOnly val="1"/><c:dispBlanksAs val="gap"/>',
                             '<c:dispBlanksAs val="gap"/><c:plotVisOnly val="1"/>')
        self.assertNotEqual(text, wrong)
        self.assertTrue(order_errors(ET.fromstring(wrong)))

    # ---- benchmarks --------------------------------------------------------------------------
    def bench_chart_part_two_series(self, timer):
        chart = self.rich[1]
        part = CH['chart_part']
        with timer as test:
            while test.more:
                for i in test.count:
                    part(chart)
        return 'chart_part, 2 series, trendline, error bars', 'xml'

    def bench_chart_part_plain(self, timer):
        chart = self.plain()[1]
        part = CH['chart_part']
        with timer as test:
            while test.more:
                for i in test.count:
                    part(chart)
        return 'chart_part, 1 series', 'xml'
