"""
b_report.py -- tests and benchmarks for report, the HTML report writer, and for the report
of the micromixing model (mumix.write_report) built on it.

The page is checked with a standard XML parser (the writer promises well-formed output),
by reading its text back, and for what it must not contain (scripts, external files).
The charts come from real chart nodes through svgchart, and the end-to-end test runs the
model, writes the workbook and the report and reads both back.

Run from the project root:
    python tools/runbench.py tests/b_report.py
"""

import os
import re
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
import mumix                                      # puts tools, xlw, svgchart, htmlreport on sys.path

SOURCES = ['report']
globals().update(load('xlw', into={}))
CH = load('xlchart', into={})
RP = load('report', into={})

OUTDIR = os.path.join(ROOT, 'results', 'b_report')


def parse(text):
    return ET.fromstring(text)


def texts(element):
    return [''.join(item.itertext()).strip() for item in element]


def header_of(table):
    """The header cell texts of a table node; empty when it has no header row."""
    head = table.find('thead')
    return [] if head is None else texts(head.find('tr'))


class b_report(bench):
    BenchName = 'report'
    BenchVersion = 'M1.0.5'
    BenchHeader = ''
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        os.makedirs(OUTDIR, exist_ok=True)
        cls.headers = ['t', 'x', 'label']
        cls.units = ['s', 'm', None]
        cls.rows = [[float(i), i * 0.123456, 'row ' + str(i)] for i in range(40)]
        cls.wide = [[i * 0.0123 + j for j in range(11)] for i in range(15)]

    def book_with_charts(self, n=2):
        xl = xlw()
        xl.newbook(os.path.join(OUTDIR, 'charts'), 'Data')
        xl.write(['x', 'y']).nl()
        for i in range(5):
            xl.write([float(i), float(i * i)]).nl()
        for number in range(n):
            chart = xl.chart(f'c{number}')
            chart.title.text = [('Chart ', {}), ('A', {'baseline': -25})] if number == 0 \
                else f'Second {number}'
            CH['add_series'](chart, 'Data!$A$2:$A$6', 'Data!$B$2:$B$6', label='y')
        return xl.charts

    # ---- small pieces -----------------------------------------------------------------------
    def test_T01_numbers_as_text(self):
        sig = RP['sig']
        self.assertEqual(sig(3.14159), '3.142')
        self.assertEqual(sig(3.14159, 2), '3.1')
        self.assertEqual(sig(5), '5')
        self.assertEqual(sig(5.0), '5')
        self.assertEqual(sig(1234567.0), '1234567')
        self.assertEqual(sig(1e-7), '1e-07')
        self.assertEqual(sig(np.float64(0.5)), '0.5')
        self.assertEqual(sig(None), '')
        self.assertEqual(sig('text'), 'text')
        self.assertEqual(sig(True), 'True')

    def test_T02_sampling_keeps_the_ends_and_spreads_evenly(self):
        rows = list(range(241))
        picked = RP['sample_rows'](rows, 15)
        self.assertEqual(len(picked), 15)
        self.assertEqual((picked[0], picked[-1]), (0, 240))
        steps = np.diff(picked)
        self.assertTrue(steps.min() >= 17 and steps.max() <= 18)

    def test_T03_a_short_table_is_not_sampled(self):
        rows = list(range(10))
        self.assertEqual(RP['sample_rows'](rows, 15), rows)
        self.assertEqual(RP['sample_rows'](rows, 10), rows)
        self.assertEqual(RP['sample_rows'](rows, 1), rows)       # a guard, not a sample

    def test_T04_plain_title_joins_runs_and_handles_no_title(self):
        book = self.book_with_charts()
        charts = book.Data.kvr('priv').kvr('charts').nodes()
        self.assertEqual(RP['plain_title'](charts[0]), 'Chart A')
        self.assertEqual(RP['plain_title'](charts[1]), 'Second 1')
        xl = xlw()
        xl.newbook(os.path.join(OUTDIR, 'untitled'), 'Data')
        self.assertEqual(RP['plain_title'](xl.chart('c')), '')

    # ---- tables --------------------------------------------------------------------------------
    def test_T05_table_structure(self):
        root = parse(RP['table_html'](self.headers, self.units, self.rows[:3], caption='cap'))
        table = root.find('table')
        self.assertEqual(table.find('caption').text, 'cap')
        head = table.find('thead').find('tr')
        self.assertEqual(texts(head), ['ts', 'xm', 'label'])
        body = table.find('tbody').findall('tr')
        self.assertEqual(len(body), 3)
        self.assertEqual(texts(body[1]), ['1', '0.1235', 'row 1'])

    def test_T06_text_columns_left_numbers_right(self):
        root = parse(RP['table_html'](self.headers, self.units, self.rows[:2]))
        cells = root.find('table').find('tbody').find('tr').findall('td')
        self.assertEqual([cell.get('class') for cell in cells], ['num', 'num', 'txt'])

    def test_T07_cell_text_is_escaped(self):
        root = parse(RP['table_html'](['a<b'], None, [['<script>x</script> & "q"']]))
        cell = root.find('table').find('tbody').find('tr').find('td')
        self.assertEqual(cell.text, '<script>x</script> & "q"')
        self.assertEqual(root.find('table').find('thead').find('tr').find('th').text, 'a<b')
        self.assertIsNone(root.find('.//script'))

    def test_T08_row_classes(self):
        root = parse(RP['table_html'](['a'], None, [[1], [2], [3]],
                                      row_classes=[None, 'flag', None]))
        rows = root.find('table').find('tbody').findall('tr')
        self.assertEqual([row.get('class') for row in rows], [None, 'flag', None])

    def test_T09_an_empty_table_and_missing_units(self):
        root = parse(RP['table_html'](['a', 'b'], None, []))
        self.assertEqual(len(root.find('table').find('tbody').findall('tr')), 0)
        self.assertEqual(texts(root.find('table').find('thead').find('tr')), ['a', 'b'])

    def test_T10_facts_and_list(self):
        facts = parse(RP['facts_html']([('feed time', 3600.0, 's'), ('ratio', 0.25, '')]))
        rows = facts.find('table').find('tbody').findall('tr')
        self.assertEqual(texts(rows[0]), ['feed time', '3600 s'])
        self.assertEqual(texts(rows[1]), ['ratio', '0.25'])
        items = parse('<r>' + RP['list_html'](['a & b', '<c>']) + '</r>').find('ul')
        self.assertEqual([li.text for li in items], ['a & b', '<c>'])

    # ---- charts --------------------------------------------------------------------------------
    def test_T11_charts_of_a_book_in_sheet_order_with_titles(self):
        charts = RP['book_charts'](self.book_with_charts(3))
        self.assertEqual([item[1] for item in charts], ['c0', 'c1', 'c2'])
        self.assertEqual([item[0] for item in charts], ['Data'] * 3)
        self.assertEqual([item[2] for item in charts], ['Chart A', 'Second 1', 'Second 2'])
        for sheet, key, title, svg in charts:
            self.assertTrue(svg.startswith('<?xml'))
            parse(svg)

    def test_T12_a_book_without_charts_gives_none(self):
        xl = xlw()
        xl.newbook(os.path.join(OUTDIR, 'nocharts'), 'Data')
        xl.write([1, 2, 3])
        self.assertEqual(RP['book_charts'](xl.nocharts), [])

    def test_T13_charts_section_embeds_inline_svg_and_links_the_files(self):
        charts = RP['book_charts'](self.book_with_charts(2))
        root = parse(RP['charts_section'](charts, 'my run'))
        figures = root.findall('figure')
        self.assertEqual(len(figures), 2)
        link = figures[0].find('figcaption').find('a')
        self.assertEqual(link.get('href'), 'my%20run_c0.svg')
        svg = [child for child in figures[0] if child.tag.endswith('svg')][0]
        self.assertIn('max-width:100%', svg.get('style'))
        self.assertIsNone(svg.get('width'))

    def test_T14_charts_are_written_as_standalone_files(self):
        charts = RP['book_charts'](self.book_with_charts(2))
        paths = RP['write_charts'](OUTDIR, 'unit', charts)
        self.assertEqual([os.path.basename(path) for path in paths],
                         ['unit_c0.svg', 'unit_c1.svg'])
        for path, item in zip(paths, charts):
            with open(path, encoding='utf-8') as handle:
                self.assertEqual(handle.read(), item[3])

    # ---- the page --------------------------------------------------------------------------------
    def test_T15_page_is_well_formed_with_title_sections_and_workbook_link(self):
        text = RP['page']('Run <1> & 2', [('First', '<p>one</p>'), ('Second', '<p>two</p>')],
                          subtitle='sub', workbook='my book.xlsx', generated='2026-10-31')
        self.assertTrue(text.startswith('<!DOCTYPE html>'))
        root = parse(text)
        self.assertEqual(root.find('head').find('title').text, 'Run <1> & 2')
        main = root.find('body').find('main')
        self.assertEqual(main.find('h1').text, 'Run <1> & 2')
        self.assertEqual([h.text for h in main.iter('h2')], ['First', 'Second'])
        link = [a for a in main.iter('a')][0]
        self.assertEqual(link.get('href'), 'my%20book.xlsx')
        self.assertEqual(link.text, 'my book.xlsx')
        self.assertIn('generated 2026-10-31', text)

    def test_T16_page_without_optional_parts(self):
        root = parse(RP['page']('T', [('H', '<p>x</p>')]))
        main = root.find('body').find('main')
        self.assertEqual(len(list(main.iter('a'))), 0)
        self.assertEqual(len(list(main.iter('footer'))), 0)

    def test_T17_page_has_no_scripts_and_no_external_files(self):
        charts = RP['book_charts'](self.book_with_charts(1))
        text = RP['page']('T', [('Charts', RP['charts_section'](charts, 'u'))])
        self.assertNotIn('<script', text)
        self.assertNotIn('src=', text)
        outside = [url for url in re.findall(r'https?://[^"\s<]+', text)
                   if 'w3.org' not in url and 'purl.org' not in url
                   and 'creativecommons' not in url]
        self.assertEqual(outside, [])

    def test_T18_write_page_is_utf8(self):
        path = RP['write_page'](OUTDIR, 'unit.html', RP['page']('µ-mixing', []))
        with open(path, encoding='utf-8') as handle:
            self.assertIn('µ-mixing', handle.read())

    # ---- the mumix report -----------------------------------------------------------------------
    def test_T19_the_mumix_report_end_to_end(self):
        result = mumix.run(nout=41)
        xl, book = mumix.build_workbook(result, os.path.join(OUTDIR, 'mumix_unit.xlsx'))
        xl.save()
        path = mumix.write_report(result, book, OUTDIR, stem='mumix_unit',
                                  generated='2026-10-31')
        self.assertEqual(os.path.basename(path), 'mumix_unit.html')
        with open(path, encoding='utf-8') as handle:
            text = handle.read()
        root = parse(text)
        main = root.find('body').find('main')
        self.assertEqual([h.text for h in main.iter('h2')],
                         ['Run', 'Charts', 'Results', 'Parameters', 'Balances', 'Model notes'])
        self.assertEqual(len(main.findall('.//figure')), 3)
        self.assertIn('mumix_unit.xlsx', [a.get('href') for a in main.iter('a')])
        for name in ('concentrations', 'accumulation', 'interface'):
            self.assertTrue(os.path.isfile(os.path.join(OUTDIR, f'mumix_unit_{name}.svg')))
        self.assertTrue(os.path.isfile(os.path.join(OUTDIR, 'mumix_unit.xlsx')))

    def test_T20_the_results_table_is_a_sample_with_both_ends_and_the_model_numbers(self):
        result = mumix.run(nout=41)
        xl, book = mumix.build_workbook(result, os.path.join(OUTDIR, 'mumix_unit2.xlsx'))
        path = mumix.write_report(result, book, OUTDIR, stem='mumix_unit2')
        with open(path, encoding='utf-8') as handle:
            root = parse(handle.read())
        tables = list(root.iter('table'))
        results = [t for t in tables if t.find('caption') is not None
                   and 'output times' in ''.join(t.find('caption').itertext())][0]
        rows = results.find('tbody').findall('tr')
        self.assertEqual(len(rows), mumix.REPORT_ROWS)
        first = texts(rows[0])
        last = texts(rows[-1])
        self.assertEqual(first[0], '0')
        self.assertEqual(last[0], '3600')
        names = header_of(results)
        self.assertEqual(len(names), len(mumix.REPORT_COLUMNS))
        conversion = [n.startswith('conversion') for n in names].index(True)
        self.assertAlmostEqual(float(last[conversion]), result.derived.conversion[-1],
                               places=3)
        self.assertIn('15 of 41 output times', ''.join(results.find('caption').itertext()))

    def test_T21_parameters_are_marked_by_source_and_the_balances_are_small(self):
        result = mumix.run(nout=41)
        xl, book = mumix.build_workbook(result, os.path.join(OUTDIR, 'mumix_unit3.xlsx'))
        path = mumix.write_report(result, book, OUTDIR, stem='mumix_unit3')
        with open(path, encoding='utf-8') as handle:
            root = parse(handle.read())
        tables = list(root.iter('table'))
        params = [t for t in tables if header_of(t)[:2] == ['name', 'value']][0]
        rows = params.find('tbody').findall('tr')
        names = [texts(row)[0] for row in rows]
        self.assertEqual(names, list(mumix.PARAMETERS) + [d[0] for d in mumix.DERIVED])
        assumed = [texts(row)[0] for row in rows if row.get('class') == 'flag']
        self.assertEqual(assumed, [name for name, spec in mumix.PARAMETERS.items()
                                   if spec[3] == 'assumed'])
        balances = [t for t in tables if header_of(t)[:1] == ['balance']][0]
        for row in balances.find('tbody').findall('tr'):
            self.assertLess(float(texts(row)[1]), 1e-6)

    # ---- benchmarks -----------------------------------------------------------------------------------
    def bench_sig(self, timer):
        sig = RP['sig']
        with timer as test:
            while test.more:
                for i in test.count:
                    sig(0.000123456)
        return 'sig(0.000123456)', 'text'

    def bench_table_html_15x11(self, timer):
        build = RP['table_html']
        headers = [f'h{j}' for j in range(11)]
        rows = self.wide
        with timer as test:
            while test.more:
                for i in test.count:
                    build(headers, None, rows)
        return 'table_html, 15 rows x 11 columns', 'table'

    def bench_page_four_sections(self, timer):
        page = RP['page']
        sections = [(f'S{i}', '<p>text</p>') for i in range(4)]
        with timer as test:
            while test.more:
                for i in test.count:
                    page('T', sections, subtitle='s', workbook='w.xlsx')
        return 'page, 4 sections', 'page'
