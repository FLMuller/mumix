"""
b_svgchart.py -- tests and benchmarks for svgchart, the SVG drawing of an xlw chart node.

Two layers. The pure functions (Excel's automatic axis, number formats, colours, spline,
trendline fits) are checked against numbers worked out by hand. The drawing is checked
through the matplotlib Figure that chart_figure() returns: axis limits, scale, which axis
crosses where, the secondary axis, legend, trendline, error bars, labels, and that the SVG
is well formed with its text kept as text. Pictures for looking at go to results/b_svgchart.
The charts Excel itself saved (results/reference, skipped when absent) are drawn as well.

Run from the project root:
    python tools/runbench.py tests/b_svgchart.py
"""

import math
import os
import sys
import xml.etree.ElementTree as ET

import numpy as np


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
import mumix                                      # puts tools, xlw, svgchart on sys.path

SOURCES = ['svgchart', 'xlchart']
globals().update(load('xlw', into={}))
CH = load('xlchart', into={})
SC = load('svgchart', into={})
from xlw import book_values

OUTDIR = os.path.join(ROOT, 'results', 'b_svgchart')
REFERENCE = os.path.join(ROOT, 'results', 'reference')
XT = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
YT = [0.2, 1.1, 1.9, 3.2, 3.9, 5.1]


class b_svgchart(bench):
    BenchName = 'svgchart'
    BenchVersion = 'M1.0.6'
    BenchHeader = ''
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        os.makedirs(OUTDIR, exist_ok=True)

    def chart(self, **settings):
        """(chart node, values function) with data in Data!A1:C7 and one chart; settings
        are 'axis.leaf' names set on the chart, for example xaxis__min=0."""
        xl = xlw()
        xl.newbook(os.path.join(OUTDIR, 'unit'), 'Data')
        xl.write(['x', 'y', 'z']).nl()
        for i in range(len(XT)):
            xl.write([XT[i], YT[i], 10.0 ** (i - 3)]).nl()
        chart = xl.chart('c')
        for name, value in settings.items():
            node, _, leaf = name.partition('__')
            if leaf:
                setattr(getattr(chart, node), leaf, value)
            else:
                setattr(chart, node, value)
        return chart, book_values(xl.unit), xl

    def series(self, chart, y='Data!$B$2:$B$7', **options):
        return CH['add_series'](chart, 'Data!$A$2:$A$7', y, **options)

    def figure(self, chart, values):
        return SC['chart_figure'](chart, values)

    def svg(self, chart, values, name=None, **kwargs):
        text = SC['chart_svg'](chart, values, **kwargs)
        if name:
            with open(os.path.join(OUTDIR, name + '.svg'), 'w', encoding='utf-8') as handle:
                handle.write(text)
        return text

    # ---- excel_scale and nice_step ----------------------------------------------------------
    def test_T01_nice_step_is_1_2_5_times_a_power_of_ten(self):
        nice = SC['nice_step']
        self.assertEqual(nice(100), 10)
        self.assertEqual(nice(105), 20)
        self.assertEqual(nice(0.105), 0.02)
        self.assertEqual(nice(55), 10)
        self.assertEqual(nice(3), 0.5)                   # 6 intervals; 0.2 would give 15

    def test_T02_automatic_scale_of_data_from_zero(self):
        scale = SC['excel_scale']
        self.assertEqual(scale(0, 100), (0, 120, 20))
        low, high, major = scale(0, 1)
        self.assertEqual((low, round(high, 9), round(major, 9)), (0, 1.2, 0.2))

    def test_T03_zero_is_forced_unless_the_data_are_far_from_it(self):
        scale = SC['excel_scale']
        self.assertEqual(scale(10, 100)[0], 0)           # lower limit 5.5 < 5/6 of 105
        low, high, major = scale(95, 100)                # lower limit 94.75 > 5/6 of 100.25
        self.assertEqual((low, high, major), (94, 101, 1))

    def test_T04_negative_data(self):
        self.assertEqual(SC['excel_scale'](-5, 5), (-6, 6, 2))

    def test_T05_log_scale_encloses_the_data_in_powers_of_the_base(self):
        scale = SC['excel_scale']
        self.assertEqual(scale(3e-6, 1.3e-3, 10), (1e-6, 1e-2, 10.0))
        self.assertEqual(scale(0.0164, 0.0166, 10), (0.01, 0.1, 10.0))
        self.assertEqual(scale(1, 1000, 10), (1.0, 1000.0, 10.0))

    def test_T06_a_flat_series_still_gets_an_axis(self):
        low, high, major = SC['excel_scale'](5, 5)
        self.assertLess(low, 5)
        self.assertGreater(high, 5)

    # ---- numbers and colours ----------------------------------------------------------------
    def test_T07_number_formats(self):
        fmt = SC['format_number']
        self.assertEqual(fmt(0.5), '0.5')
        self.assertEqual(fmt(0), '0')
        self.assertEqual(fmt(1e-5), '1E-05')
        self.assertEqual(fmt(1234.5), '1234.5')
        self.assertEqual(fmt(3.14159, '0.00'), '3.14')
        self.assertEqual(fmt(1234567, '#,##0'), '1,234,567')
        self.assertEqual(fmt(1234.5, '#,##0.00'), '1,234.50')
        self.assertEqual(fmt(0.256, '0%'), '26%')
        self.assertEqual(fmt(0.256, '0.0%'), '25.6%')
        self.assertEqual(fmt(12345, '0.00E+00'), '1.23E+04')
        self.assertEqual(fmt(0.00012, '0.00E+00'), '1.20E-04')

    def test_T08_colours(self):
        color = SC['resolve_color']
        self.assertEqual(color('ff0000'), '#FF0000')
        self.assertEqual(color('theme:tx1'), '#000000')
        self.assertEqual(color('theme:accent1'), '#4472C4')
        self.assertEqual(color('theme:tx1:50000:50000'), '#808080')
        self.assertEqual(color('sys:windowText'), '#000000')
        self.assertEqual(color('sys:windowText:112233'), '#112233')
        self.assertEqual(color(None, 'C00000'), '#C00000')

    # ---- spline and fits --------------------------------------------------------------------------
    def test_T09_the_spline_passes_through_the_points(self):
        x = np.array([0.0, 1.0, 2.5, 4.0, 5.0])
        y = np.array([1.0, 3.0, 2.0, 5.0, 4.0])
        sx, sy = SC['catmull_rom'](x, y, per=10)
        self.assertEqual(len(sx), 4 * 10 + 1)
        for i in range(len(x)):
            self.assertAlmostEqual(sx[i * 10], x[i], places=12)
            self.assertAlmostEqual(sy[i * 10], y[i], places=12)

    def test_T10_two_points_are_returned_as_they_are(self):
        sx, sy = SC['catmull_rom']([0.0, 1.0], [2.0, 3.0])
        self.assertEqual(list(sx), [0.0, 1.0])

    def test_T11_linear_and_polynomial_fits(self):
        x = np.arange(6.0)
        function, coefficients, r2, text = SC['trend_fit']('linear', x, 2 * x + 1)
        self.assertAlmostEqual(coefficients[0], 2.0, places=10)
        self.assertAlmostEqual(coefficients[1], 1.0, places=10)
        self.assertAlmostEqual(r2, 1.0, places=10)
        self.assertTrue(text.startswith('y = 2x'))
        function, coefficients, r2, text = SC['trend_fit']('poly', x, x**2 - x, order=2)
        self.assertAlmostEqual(float(function(np.array([6.0]))[0]), 30.0, places=8)

    def test_T12_exponential_logarithmic_and_power_fits(self):
        x = np.arange(1.0, 7.0)
        function, c, r2, text = SC['trend_fit']('exp', x, 3 * np.exp(0.5 * x))
        self.assertAlmostEqual(c[0], 3.0, places=8)
        self.assertAlmostEqual(c[1], 0.5, places=8)
        function, c, r2, text = SC['trend_fit']('log', x, 2 * np.log(x) + 1)
        self.assertAlmostEqual(c[0], 2.0, places=8)
        function, c, r2, text = SC['trend_fit']('power', x, 4 * x**1.5)
        self.assertAlmostEqual(c[0], 4.0, places=8)
        self.assertAlmostEqual(c[1], 1.5, places=8)

    def test_T13_moving_average(self):
        function, average, r2, text = SC['trend_fit']('movingAvg', np.arange(5.0),
                                                      np.array([1.0, 3.0, 5.0, 7.0, 9.0]),
                                                      period=2)
        self.assertIsNone(function)
        self.assertEqual(list(average), [2.0, 4.0, 6.0, 8.0])

    def test_T14_an_unknown_fit_is_refused(self):
        with self.assertRaises(ValueError):
            SC['trend_fit']('cubic-ish', np.arange(3.0), np.arange(3.0))

    def test_T15_title_runs_become_sub_and_superscripts(self):
        text = SC['mathtext']([('c', {}), ('A', {'baseline': -25}), ('2', {'baseline': 30})])
        self.assertIn('_{', text)
        self.assertIn('^{', text)
        self.assertEqual(SC['mathtext']('a $ b'), r'a \$ b')

    # ---- the drawing ---------------------------------------------------------------------------------
    def test_T16_data_limits_follow_excels_rule_when_nothing_is_fixed(self):
        chart, values, xl = self.chart()
        self.series(chart, label='y')
        figure = self.figure(chart, values)
        ax = figure.axes[0]
        self.assertEqual(ax.get_xlim(), (0.0, 6.0))                # 0..5: major 1, max 5.25 -> 6
        low, high, major = SC['excel_scale'](min(YT), max(YT))
        self.assertEqual(ax.get_ylim(), (low, high))

    def test_T17_fixed_limits_and_major_unit_win(self):
        chart, values, xl = self.chart(xaxis__min=1, xaxis__max=4, xaxis__major=0.5,
                                       yaxis__min=-1, yaxis__max=9)
        self.series(chart, label='y')
        ax = self.figure(chart, values).axes[0]
        self.assertEqual(ax.get_xlim(), (1.0, 4.0))
        self.assertEqual(ax.get_ylim(), (-1.0, 9.0))
        ticks = [t for t in ax.get_xticks() if 1.0 <= t <= 4.0]
        self.assertEqual(ticks, [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0])

    def test_T18_reversed_axis(self):
        chart, values, xl = self.chart(yaxis__reverse=True, yaxis__min=0, yaxis__max=6)
        self.series(chart, label='y')
        ax = self.figure(chart, values).axes[0]
        self.assertEqual(ax.get_ylim(), (6.0, 0.0))

    def test_T19_log_axis(self):
        chart, values, xl = self.chart(yaxis__log=10)
        self.series(chart, y='Data!$C$2:$C$7', label='z')
        ax = self.figure(chart, values).axes[0]
        self.assertEqual(ax.get_yscale(), 'log')
        low, high = ax.get_ylim()
        self.assertAlmostEqual(math.log10(low), -3.0)
        self.assertAlmostEqual(math.log10(high), 2.0)

    def test_T20_the_x_axis_crosses_at_zero_when_the_data_straddle_it(self):
        chart, values, xl = self.chart(yaxis__min=-2, yaxis__max=6)
        self.series(chart, label='y')
        ax = self.figure(chart, values).axes[0]
        self.assertEqual(ax.spines['bottom'].get_position(), ('data', 0.0))

    def test_T21_crossing_at_a_value_at_the_minimum_and_at_the_maximum(self):
        chart, values, xl = self.chart(yaxis__min=-2, yaxis__max=6, yaxis__crossesat=3.0)
        self.series(chart, label='y')
        ax = self.figure(chart, values).axes[0]
        self.assertEqual(ax.spines['bottom'].get_position(), ('data', 3.0))
        chart, values, xl = self.chart(yaxis__min=-2, yaxis__max=6, yaxis__crosses='min')
        self.series(chart, label='y')
        self.assertEqual(self.figure(chart, values).axes[0].spines['bottom'].get_position(),
                         ('data', -2.0))
        chart, values, xl = self.chart(yaxis__min=-2, yaxis__max=6, yaxis__crosses='max')
        self.series(chart, label='y')
        self.assertEqual(self.figure(chart, values).axes[0].spines['bottom'].get_position(),
                         ('data', 6.0))

    def test_T22_autozero_on_a_log_axis_is_the_value_one_or_the_nearest_end(self):
        info = type('Info', (), {})()
        info.low, info.high, info.log = 1e-6, 1e-2, 10.0
        self.assertEqual(SC['crossing_value'](info, None), 1e-2)       # 1 lies above the range
        info.low, info.high = 1e-3, 1e3
        self.assertEqual(SC['crossing_value'](info, None), 1.0)        # 1 is inside
        info.low, info.high = 10.0, 1e3
        self.assertEqual(SC['crossing_value'](info, None), 10.0)       # 1 lies below the range

    def test_T23_secondary_axis_is_a_second_matplotlib_axes_with_its_own_scale(self):
        chart, values, xl = self.chart(y2axis__log=10)
        self.series(chart, label='y')
        self.series(chart, y='Data!$C$2:$C$7', label='z', axis=2)
        figure = self.figure(chart, values)
        self.assertEqual(len(figure.axes), 2)
        self.assertEqual(figure.axes[0].get_yscale(), 'linear')
        self.assertEqual(figure.axes[1].get_yscale(), 'log')
        self.assertEqual(figure.axes[1].get_xlim(), figure.axes[0].get_xlim())

    def test_T24_one_line_per_series_with_the_palette_and_the_given_style(self):
        chart, values, xl = self.chart()
        self.series(chart, label='a')
        self.series(chart, y='Data!$C$2:$C$7', label='b',
                    line=dict(color='C00000', width=3.0, dash='dash'),
                    marker=dict(symbol='square', size=8))
        ax = self.figure(chart, values).axes[0]
        lines = [line for line in ax.lines if len(line.get_xdata()) == len(XT)]
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0].get_color().upper(), '#4472C4')
        self.assertEqual(lines[1].get_color().upper(), '#C00000')
        self.assertEqual(lines[1].get_linewidth(), 3.0)
        self.assertEqual(lines[1].get_marker(), 's')
        self.assertEqual(lines[1].get_markersize(), 8)

    def test_T25_marker_style_has_no_line_unless_asked(self):
        chart, values, xl = self.chart(style='marker')
        self.series(chart, label='a')
        line = [item for item in self.figure(chart, values).axes[0].lines
                if len(item.get_xdata()) == len(XT)][0]
        self.assertEqual(line.get_linestyle(), 'None')
        self.assertEqual(line.get_marker(), 'o')

    def test_T26_smooth_series_is_drawn_through_extra_points(self):
        chart, values, xl = self.chart()
        self.series(chart, label='a', smooth=True)
        ax = self.figure(chart, values).axes[0]
        self.assertEqual(max(len(line.get_xdata()) for line in ax.lines),
                         (len(XT) - 1) * 12 + 1)

    def test_T27_missing_cells_are_dropped_not_drawn_as_zero(self):
        chart, values, xl = self.chart()
        node = self.series(chart, label='a')
        node['y'] = [1.0, None, 3.0, float('nan'), 5.0, 6.0]
        line = [item for item in self.figure(chart, values).axes[0].lines][0]
        self.assertEqual(list(line.get_xdata()), [0.0, 2.0, 4.0, 5.0])

    def test_T28_legend_lists_named_series_and_honours_hide(self):
        chart, values, xl = self.chart()
        chart.legend.pos = 'b'
        self.series(chart, label='alpha')
        self.series(chart, y='Data!$C$2:$C$7', label='beta')
        self.series(chart, label='gamma')
        figure = self.figure(chart, values)
        texts = [t.get_text() for t in figure.legends[0].get_texts()]
        self.assertEqual(texts, ['alpha', 'beta', 'gamma'])
        chart.legend.hide = [2]
        figure = self.figure(chart, values)
        self.assertEqual([t.get_text() for t in figure.legends[0].get_texts()],
                         ['alpha', 'gamma'])

    def test_T29_no_legend_node_no_legend(self):
        chart, values, xl = self.chart()
        self.series(chart, label='alpha')
        figure = self.figure(chart, values)
        self.assertEqual(figure.legends, [])
        self.assertIsNone(figure.axes[0].get_legend())

    def test_T30_series_name_from_a_cell(self):
        chart, values, xl = self.chart()
        chart.legend.pos = 'r'
        self.series(chart, labelref='Data!$B$1')
        figure = self.figure(chart, values)
        self.assertEqual([t.get_text() for t in figure.legends[0].get_texts()], ['y'])

    def test_T31_trendline_adds_a_line_and_the_equation_text(self):
        chart, values, xl = self.chart()
        node = self.series(chart, label='a')
        node.trend.fit = 'linear'
        node.trend.eq = True
        node.trend.rsq = True
        ax = self.figure(chart, values).axes[0]
        self.assertEqual(len(ax.lines), 2)
        self.assertEqual(len(ax.texts), 1)
        self.assertIn('R² = ', ax.texts[0].get_text())
        self.assertIn('y = ', ax.texts[0].get_text())

    def test_T32_trendline_forward_extends_the_line(self):
        chart, values, xl = self.chart()
        node = self.series(chart, label='a')
        node.trend.fit = 'linear'
        node.trend.forward = 2
        trend = self.figure(chart, values).axes[0].lines[1]
        self.assertAlmostEqual(trend.get_xdata().max(), 7.0)

    def test_T33_error_bars_are_drawn_for_every_mode(self):
        for mode, extra in (('fixed', dict(value=0.5)), ('percentage', dict(value=10)),
                            ('stddev', {}), ('stderr', {})):
            chart, values, xl = self.chart()
            node = self.series(chart, label='a')
            node.yerr.mode = mode
            for key, value in extra.items():
                setattr(node.yerr, key, value)
            ax = self.figure(chart, values).axes[0]
            self.assertEqual(len(ax.containers), 1, mode)

    def test_T34_custom_error_bars_use_the_cell_values(self):
        chart, values, xl = self.chart()
        node = self.series(chart, label='a')
        node.yerr.mode = 'custom'
        node.yerr.plus = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        node.yerr.minus = [0.0] * 6
        container = self.figure(chart, values).axes[0].containers[0]
        segments = container.lines[2][0].get_segments()
        top = [segment[1][1] - segment[0][1] for segment in segments]
        self.assertEqual([round(v, 9) for v in top], [0.1, 0.2, 0.3, 0.4, 0.5, 0.6])

    def test_T35_data_labels(self):
        chart, values, xl = self.chart()
        node = self.series(chart, label='a')
        node.labels.showy = True
        node.labels.numfmt = '0.0'
        ax = self.figure(chart, values).axes[0]
        self.assertEqual([t.get_text() for t in ax.texts], ['0.2', '1.1', '1.9', '3.2', '3.9',
                                                           '5.1'])

    def test_T36_axis_titles_and_chart_title_reach_the_svg_as_text(self):
        chart, values, xl = self.chart()
        chart.title.text = 'Chart <title> & more'
        chart.xaxis.title.text = 'time (s)'
        chart.yaxis.title.text = 'conc'
        self.series(chart, label='alpha')
        chart.legend.pos = 'r'
        text = self.svg(chart, values, 'titles')
        ET.fromstring(text)                                          # well formed
        for piece in ('time (s)', 'conc', 'alpha', 'Chart &lt;title&gt; &amp; more'):
            self.assertIn(piece, text)

    def test_T37_svg_text_is_text_and_inline_svg_scales(self):
        chart, values, xl = self.chart()
        self.series(chart, label='a')
        text = self.svg(chart, values)
        self.assertTrue(text.lstrip().startswith('<?xml'))
        self.assertIn('<text', text)                     # fonts are not converted to paths
        inline = self.svg(chart, values, inline=True)
        self.assertTrue(inline.startswith('<svg'))
        head = inline[:inline.index('>')]
        self.assertIn('max-width:100%', head)
        self.assertNotIn(' width="', head)
        ET.fromstring(inline)

    def test_T37b_same_chart_same_bytes_and_no_outside_references(self):
        chart, values, xl = self.chart()
        self.series(chart, label='a')
        first = self.svg(chart, values)
        self.assertEqual(first, self.svg(chart, values))           # no timestamp inside
        self.assertNotIn('matplotlib.org', first)
        inline = SC['inline_svg'](first)
        self.assertEqual(inline, self.svg(chart, values, inline=True))

    def test_T38_gridlines_default_major_off_when_none_minor_when_asked(self):
        chart, values, xl = self.chart()
        self.series(chart, label='a')
        ax = self.figure(chart, values).axes[0]
        self.assertTrue(ax.xaxis.get_gridlines()[0].get_visible())
        chart.xaxis.gridmajor = CH['rec'](none=True)
        chart.yaxis.gridminor = CH['rec'](color='EEEEEE', width=0.5)
        chart.yaxis.minor = 0.25
        ax = self.figure(chart, values).axes[0]
        self.assertFalse(ax.xaxis.get_gridlines()[0].get_visible())
        self.assertTrue(any(abs(loc - 0.25) < 1e-9 for loc in ax.yaxis.get_minorticklocs()))
        self.assertTrue(any(tick.gridline.get_visible()
                            for tick in ax.yaxis.get_minor_ticks()))

    def test_T39_a_chart_with_no_series_still_draws(self):
        chart, values, xl = self.chart()
        chart.title.text = 'empty'
        figure = self.figure(chart, values)
        self.assertEqual(len(figure.axes), 1)
        ET.fromstring(self.svg(chart, values))

    def test_T40_a_hidden_axis_is_not_drawn(self):
        chart, values, xl = self.chart(yaxis__visible=False)
        self.series(chart, label='a')
        ax = self.figure(chart, values).axes[0]
        self.assertFalse(ax.yaxis.get_visible())
        self.assertTrue(ax.xaxis.get_visible())

    def test_T41_the_mumix_charts_draw_with_the_axes_at_the_bottom(self):
        result = mumix.run(nout=41)
        out, book = mumix.build_workbook(result, os.path.join(OUTDIR, 'mumix_unit'))
        values = book_values(book)
        charts = book.Results.kvr('priv').kvr('charts')
        self.assertEqual(len(charts.nodes()), 3)
        for chart in charts.nodes():
            figure = self.figure(chart, values)
            ax = figure.axes[0]
            low = ax.get_ylim()[0]
            position = ax.spines['bottom'].get_position()
            self.assertEqual(position[0], 'data')
            self.assertAlmostEqual(position[1], low, places=12)          # not floating mid-plot
            ET.fromstring(SC['chart_svg'](chart, values))

    # ---- the charts Excel saved -------------------------------------------------------------------
    def test_T42_charts_read_from_the_excel_workbooks_draw_and_keep_their_fixed_limits(self):
        names = ('SB Solubility vs temperature.xlsx', 'Theopylline As recieved.xlsx',
                 'Theophylline Isotherm.xlsx')
        found = 0
        for name in names:
            path = os.path.join(REFERENCE, name)
            if not os.path.isfile(path):
                continue
            reader = xlw()
            book = reader.open(path)
            values = book_values(book)
            for key in book.kvr('priv').kvr('sheetkeys'):
                charts = book.kvr(key).kvr('priv').kvr('charts')
                if charts is None:
                    continue
                for chart_name, chart in zip(charts.names(), charts.nodes()):
                    figure = self.figure(chart, values)
                    ax = figure.axes[0]
                    for axis, limits in (('xaxis', ax.get_xlim()), ('yaxis', ax.get_ylim())):
                        node = chart.kvr(axis)
                        low = None if node is None else node.kvr('min')
                        high = None if node is None else node.kvr('max')
                        if low is not None and not (node.kvr('reverse')):
                            self.assertAlmostEqual(limits[0], low, msg=f'{name} {axis} min')
                        if high is not None and not (node.kvr('reverse')):
                            self.assertAlmostEqual(limits[1], high, msg=f'{name} {axis} max')
                    text = SC['chart_svg'](chart, values)
                    ET.fromstring(text)
                    stem = os.path.splitext(name)[0].replace(' ', '_')
                    with open(os.path.join(OUTDIR, f'{stem}_{chart_name}.svg'), 'w',
                              encoding='utf-8') as handle:
                        handle.write(text)
                    found += 1
        if not found:
            self.skipTest('no reference workbook in results/reference')

    # ---- benchmarks -----------------------------------------------------------------------------------
    def bench_excel_scale(self, timer):
        scale = SC['excel_scale']
        with timer as test:
            while test.more:
                for i in test.count:
                    scale(0.0013, 97.5)
        return 'excel_scale(0.0013, 97.5)', 'scale'

    def bench_format_number(self, timer):
        fmt = SC['format_number']
        with timer as test:
            while test.more:
                for i in test.count:
                    fmt(1234.5678, '#,##0.00')
        return "format_number(1234.5678, '#,##0.00')", 'format'

    def bench_chart_svg_one_series(self, timer):
        chart, values, xl = self.chart()
        self.series(chart, label='a')
        chart.legend.pos = 'r'
        draw = SC['chart_svg']
        with timer as test:
            while test.more:
                for i in test.count:
                    draw(chart, values)
        return 'chart_svg, 1 series, 6 points', 'draw'
