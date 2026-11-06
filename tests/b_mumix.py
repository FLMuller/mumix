"""
b_mumix.py -- tests and benchmarks for mumix, the phenomenological micromixing model.

The tests check the mathematics of the document one piece at a time (the linear-mixture
integrals, the thresholds and fractions), then the model as a whole: the balances must close
to the solver tolerance, and a few physical limits must hold (no reaction, no product; a
faster reaction, less accumulation; the volume of B settles where the exchange rate balances
the feed). The last group tests the workbook the model writes.

Run from the project root:
    python tools/runbench.py tests/b_mumix.py
"""

import math
import os
import random
import sys
import zipfile
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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from use import load
from bench import bench
from chartcheck import order_errors, package_errors

SOURCES = ['mumix']
import mumix
import xlsheet
from xlstore import TKV

OUTDIR = os.path.join(ROOT, 'results', 'b_mumix')
NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'


class b_mumix(bench):
    BenchName = 'mumix'
    BenchVersion = 'M1.0.13'
    BenchHeader = ''
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        os.makedirs(OUTDIR, exist_ok=True)
        cls.result = mumix.run()
        cls.p = mumix.parameters()
        cls.state = mumix.initial(cls.p)

    def derivative(self, p=None, **changes):
        """ddt of the initial state (with the given state changes) as a dict."""
        p = p or self.p
        state = dict(self.state)
        state.update(changes)
        v = mumix.FIELDS(state)
        v.t = 0.0
        ddt = mumix.FIELDS({name: 0.0 for name in state})
        mumix.rates(v, p, ddt)
        return ddt

    # ---- the mathematics of the document ----------------------------------------------------
    def test_T01_segment_mean_is_the_integral_of_the_linear_mixture(self):
        self.assertAlmostEqual(mumix.segment_mean(2.0, 6.0, 0.0, 1.0), 4.0)      # (2 + 6) / 2
        self.assertAlmostEqual(mumix.segment_mean(2.0, 6.0, 0.25, 0.75), 2.0)    # mean 4 * 0.5
        self.assertEqual(mumix.segment_mean(2.0, 6.0, 0.3, 0.3), 0.0)
        steps = 20000                                                            # numeric check
        xs = np.linspace(0.2, 0.9, steps)
        numeric = np.trapezoid((1 - xs) * 3.0 + xs * 11.0, xs)
        self.assertAlmostEqual(mumix.segment_mean(3.0, 11.0, 0.2, 0.9), numeric, places=8)

    def test_T02_the_three_ranges_sum_to_half_the_two_concentrations(self):
        generator = random.Random(1)
        for _ in range(50):
            cA = generator.uniform(0, 100)
            cB = generator.uniform(0, 1000)
            xr = generator.uniform(0, 0.5)
            xB = generator.uniform(xr, 1)
            total = (mumix.segment_mean(cA, cB, 0, xr) + mumix.segment_mean(cA, cB, xr, xB)
                     + mumix.segment_mean(cA, cB, xB, 1))
            self.assertAlmostEqual(total, 0.5 * (cA + cB), places=9)

    def test_T03_thresholds_from_the_document(self):
        xB, xr = mumix.thresholds(0.0, 1000.0, 900.0, 1.0)
        self.assertAlmostEqual(xB, 0.9)                      # (Blmt - BA) / (BB - BA)
        self.assertAlmostEqual(xr, 0.001)                    # dCr / (BB - BA)
        xB, xr = mumix.thresholds(100.0, 1000.0, 550.0, 9.0)
        self.assertAlmostEqual(xB, 0.5)
        self.assertAlmostEqual(xr, 0.01)

    def test_T04_fractions_sum_to_one_and_the_ordering_holds(self):
        generator = random.Random(2)
        for _ in range(200):
            cBA = generator.uniform(0, 800)
            cBB = generator.uniform(cBA, 1500)
            Blmt = generator.uniform(-100, 1600)
            dCr = generator.uniform(0, 500)
            xB, xr = mumix.thresholds(cBA, cBB, Blmt, dCr)
            self.assertTrue(0.0 <= xr <= xB <= 1.0)
            self.assertAlmostEqual(xr + (xB - xr) + (1 - xB), 1.0)

    def test_T05_xr_is_clamped_to_xB_when_the_ordering_fails(self):
        xB, xr = mumix.thresholds(0.0, 1000.0, 0.5, 400.0)        # dCr much larger than Blmt
        self.assertAlmostEqual(xB, 0.0005)
        self.assertEqual(xr, xB)                                  # fA = 0, nothing negative

    def test_T06_blmt_outside_the_range_gives_all_or_nothing(self):
        self.assertEqual(mumix.thresholds(0.0, 1000.0, 2000.0, 1.0)[0], 1.0)   # no B eddies
        self.assertEqual(mumix.thresholds(100.0, 1000.0, 10.0, 0.0)[0], 0.0)   # all B eddies

    def test_T07_equal_concentrations_are_all_bulk(self):
        self.assertEqual(mumix.thresholds(500.0, 500.0, 900.0, 1.0), (1.0, 1.0))
        self.assertEqual(mumix.thresholds(500.0, 400.0, 900.0, 1.0), (1.0, 1.0))

    def test_T08_kolmogorov_scales(self):
        length, time = mumix.kolmogorov(0.16)                     # the 50 um, 2.5 ms of the text
        self.assertAlmostEqual(length, 50e-6, delta=0.05e-6)
        self.assertAlmostEqual(time, 2.5e-3, delta=1e-6)
        faster = mumix.kolmogorov(1.0)
        self.assertLess(faster[0], length)
        self.assertLess(faster[1], time)

    # ---- parameters and the equations ---------------------------------------------------------------
    def test_T09_parameters_and_derived_values(self):
        p = mumix.parameters()
        self.assertAlmostEqual(p.Vfeed, p.V0 * p.Ao / p.Bo)             # overall A:B = 1:1
        self.assertAlmostEqual(p.Qf * p.tf, p.Vfeed)
        self.assertAlmostEqual(p.Veddy, math.pi / 4 * p.dmu**2 * p.lammu)
        self.assertAlmostEqual(p.Nvol * p.Veddy, p.fill)                # space filling
        self.assertAlmostEqual(p.dAmu, 0.5 * (math.pi - 1) * p.dmu * p.lammu)
        self.assertAlmostEqual(p.dAr, -p.dmu * p.lammu)
        self.assertEqual(len(p.tspan), p.nout)
        self.assertAlmostEqual(p.tspan[-1], p.tf)

    def test_T10_overrides_and_unknown_names(self):
        p = mumix.parameters(kAB=5.0, tf=100.0)
        self.assertEqual(p.kAB, 5.0)
        self.assertAlmostEqual(p.Qf, p.Vfeed / 100.0)
        with self.assertRaises(KeyError):
            mumix.parameters(not_a_parameter=1)

    def test_T11_every_parameter_has_a_unit_meaning_and_a_source(self):
        for name, (value, unit, meaning, source) in mumix.PARAMETERS.items():
            self.assertTrue(unit and meaning, name)
            self.assertIn(source, ('document', 'assumed'), name)
        sources = {entry[3] for entry in mumix.PARAMETERS.values()}
        self.assertEqual(sources, {'document', 'assumed'})

    def test_T12_initial_state(self):
        state = mumix.initial(self.p)
        self.assertEqual(state['VA'], self.p.V0)
        self.assertAlmostEqual(state['nAA'], self.p.Ao * self.p.V0)
        self.assertEqual(state['nBA'], 0.0)
        self.assertAlmostEqual(state['nBB'], self.p.Bo * self.p.VB0)

    def test_T13_the_rates_are_finite_at_the_start_and_for_an_empty_B(self):
        for ddt in (self.derivative(), self.derivative(VB=0.0, nBB=0.0, nAB=0.0)):
            for name, value in ddt.items():
                self.assertTrue(math.isfinite(value), name)

    def test_T14_the_exchange_conserves_each_species_and_the_volume(self):
        no_reaction = mumix.parameters(kAB=0.0)
        no_reaction.Qf = 0.0
        ddt = self.derivative(p=no_reaction, VB=5e-9, nBB=1000 * 5e-9, nAB=2e-9, nBA=3e-8)
        self.assertAlmostEqual(ddt.VA + ddt.VB, 0.0, places=18)
        self.assertAlmostEqual(ddt.nAA + ddt.nAB, 0.0, places=15)
        self.assertAlmostEqual(ddt.nBA + ddt.nBB, 0.0, places=15)
        self.assertEqual(ddt.nP, 0.0)

    def test_T15_the_feed_adds_volume_and_moles_of_B_only(self):
        with_feed = self.derivative()
        no_feed = mumix.parameters()
        no_feed.Qf = 0.0
        without = self.derivative(p=no_feed)
        self.assertAlmostEqual(with_feed.VB - without.VB, self.p.Qf, places=20)
        self.assertAlmostEqual(with_feed.nBB - without.nBB, self.p.Qf * self.p.Bo, places=15)
        self.assertEqual(with_feed.nAA, without.nAA)
        self.assertEqual(with_feed.VA, without.VA)

    def test_T16_area_grows_while_fr_is_small_and_is_capped(self):
        growing = self.derivative()
        self.assertGreater(growing.Ai, 0.0)
        amax = min((self.state['VA'] + self.state['VB']) / (2 * self.p.dmu),
                   2 * self.state['VB'] / self.p.dmu)
        capped = self.derivative(Ai=2 * amax)
        self.assertLess(capped.Ai, 0.0)                 # above the cap it relaxes back

    def test_T16b_area_has_a_floor_so_it_can_never_collapse_to_zero(self):
        for area in (0.0, 1e-30, -1e-9):
            ddt = self.derivative(Ai=area)
            self.assertTrue(math.isfinite(ddt.Ai))
            self.assertGreater(ddt.Ai, 0.0)             # pushed back up to at least Amin
        amin = mumix.SPHERE * self.state['VB']**(2.0 / 3.0)
        self.assertAlmostEqual(amin, 4.836 * self.state['VB']**(2.0 / 3.0), delta=0.001 * amin)

    def test_T17_the_area_shrinks_when_most_eddies_return_to_bulk(self):
        p = mumix.parameters(dCr=950.0, Blmt=980.0)           # fr = 0.95 > 0.52
        ddt = self.derivative(p=p, Ai=1e-5)                   # between the floor and the cap
        self.assertLess(ddt.Ai, 0.0)
        calm = self.derivative(Ai=1e-5)                       # fr = 0.001: grows instead
        self.assertGreater(calm.Ai, 0.0)
        critical = p.dAmu / (p.dAmu + p.dmu * p.lammu)
        self.assertAlmostEqual(critical, 0.5170, places=3)

    def test_T18_mesomixing_adds_area_growth_when_switched_on(self):
        p = mumix.parameters(Nmezo=1e6)
        base = self.derivative(Ai=1e-9, VB=1e-6, nBB=1e-3)
        more = self.derivative(p=p, Ai=1e-9, VB=1e-6, nBB=1e-3)
        self.assertGreater(more.Ai, base.Ai)

    # ---- the whole model ----------------------------------------------------------------------------
    def test_T19_the_balances_close(self):
        for name, residual in self.result.balances.items():
            self.assertLess(float(np.max(np.abs(residual))), 1e-9, name)

    def test_T20_the_solution_is_finite_and_non_negative(self):
        tables = self.result.tables
        for name in ('VA', 'VB', 'Ai', 'nAA', 'nBA', 'nAB', 'nBB', 'nP'):
            values = tables[name]
            self.assertTrue(np.all(np.isfinite(values)), name)
            self.assertGreater(values.min(), -1e-12, name)

    def test_T21_the_run_finishes_and_covers_the_feed_time(self):
        stats = self.result.problem.stats()
        self.assertTrue(stats['ok'])
        self.assertEqual(self.result.t[0], 0.0)
        self.assertAlmostEqual(self.result.t[-1], self.p.tf)
        self.assertEqual(len(self.result.t), self.p.nout)

    def test_T22_product_equals_the_A_consumed_and_conversion_reaches_one(self):
        derived = self.result.derived
        tables = self.result.tables
        consumed = self.p.Ao * self.p.V0 - (tables.nAA + tables.nAB)
        np.testing.assert_allclose(tables.nP, consumed, rtol=1e-9, atol=1e-12)
        self.assertTrue(np.all(np.diff(derived.conversion) > -1e-9))      # never decreases
        self.assertGreater(derived.conversion[-1], 0.998)

    def test_T23_the_volume_of_B_settles_at_feed_rate_times_a_few_eddy_lifetimes(self):
        tables = self.result.tables
        expected = self.p.Qf * self.p.taumu / 1.6                  # from K = 4 VB / tau at the cap
        middle = tables.VB[len(tables.VB) // 2]
        self.assertAlmostEqual(middle / expected, 1.0, delta=0.05)

    def test_T24_the_volume_of_A_grows_by_the_feed(self):
        tables = self.result.tables
        total = tables.VA[-1] + tables.VB[-1]
        self.assertAlmostEqual(total, self.p.V0 + self.p.VB0 + self.p.Vfeed, places=12)
        self.assertGreater(tables.VA[-1], tables.VA[0])

    def test_T25_accumulation_is_very_low_for_most_of_the_feed(self):
        beta = self.result.derived.beta
        self.assertLess(beta[len(beta) // 2], 1e-4)                # the document's expectation
        self.assertGreater(beta[-1], beta[len(beta) // 2])         # rises as A is exhausted

    def test_T26_without_a_reaction_there_is_no_product_and_B_accumulates(self):
        result = mumix.run(kAB=0.0, nout=21)
        self.assertEqual(float(result.tables.nP.max()), 0.0)
        for name, residual in result.balances.items():
            self.assertLess(float(np.max(np.abs(residual))), 1e-9, name)
        self.assertGreater(result.derived.cBA[-1], 5.0)            # B is no longer consumed

    def test_T27_a_faster_reaction_accumulates_less_B(self):
        slow = mumix.run(kAB=1.0, nout=21)
        fast = mumix.run(kAB=10.0, nout=21)
        middle = 10
        ratio = fast.derived.beta[middle] / slow.derived.beta[middle]
        self.assertLess(ratio, 0.2)                                 # beta ~ 1 / kAB
        self.assertGreater(ratio, 0.05)

    def test_T28_a_slower_feed_holds_proportionally_less_B(self):
        long_feed = mumix.run(tf=36000.0, nout=11)
        expected = long_feed.p.Qf * long_feed.p.taumu / 1.6
        self.assertAlmostEqual(long_feed.tables.VB[5] / expected, 1.0, delta=0.05)
        self.assertLess(long_feed.tables.VB[5], self.result.tables.VB[120] / 5)
        self.assertGreater(float(long_feed.tables.Ai.min()), 0.0)     # never collapses
        for name, residual in long_feed.balances.items():
            self.assertLess(float(np.max(np.abs(residual))), 1e-9, name)
        self.assertGreater(long_feed.derived.conversion[-1], 0.998)

    # ---- the workbook ---------------------------------------------------------------------------------
    def workbook(self):
        path = os.path.join(OUTDIR, 'mumix.xlsx')
        mumix.write_xlsx(self.result, path)
        return path

    def test_T29_the_workbook_is_a_consistent_package_with_three_charts(self):
        path = self.workbook()
        self.assertEqual(package_errors(path), [])
        archive = zipfile.ZipFile(path)
        charts = [n for n in archive.namelist() if n.startswith('xl/charts/chart')]
        self.assertEqual(len(charts), 3)
        for name in archive.namelist():
            root = ET.fromstring(archive.read(name))
            if name in charts:
                self.assertEqual(order_errors(root), [], name)

    def test_T30_the_charts_use_a_secondary_axis_and_a_log_axis(self):
        archive = zipfile.ZipFile(self.workbook())
        first = ET.fromstring(archive.read('xl/charts/chart1.xml'))
        self.assertEqual(len(first.findall('.//{*}scatterChart')), 2)
        second = ET.fromstring(archive.read('xl/charts/chart2.xml'))
        self.assertIsNotNone(second.find('.//{*}valAx/{*}scaling/{*}logBase'))
        third = ET.fromstring(archive.read('xl/charts/chart3.xml'))
        self.assertEqual(len(third.findall('.//{*}logBase')), 2)

    def test_T31_results_sheet_has_headers_units_and_all_rows(self):
        xl, book = mumix.build_workbook(self.result, os.path.join(OUTDIR, 'built.xlsx'))
        headers, units, rows = mumix.result_table(self.result)
        sheet = book.Results
        self.assertEqual([xlsheet.cell_value(sheet, 1, c + 1) for c in range(len(headers))], headers)
        self.assertEqual([xlsheet.cell_value(sheet, 2, c + 1) for c in range(len(units))], units)
        self.assertEqual(sheet.kvr('cells').icount(), (len(rows) + 2) * len(headers))
        self.assertEqual(xlsheet.cell_value(sheet, 3, 1), 0.0)
        self.assertAlmostEqual(xlsheet.cell_value(sheet, 2 + len(rows), 1), self.p.tf)

    def test_T32_cell_values_match_the_result(self):
        xl, book = mumix.build_workbook(self.result, os.path.join(OUTDIR, 'built.xlsx'))
        headers, units, rows = mumix.result_table(self.result)
        column = headers.index('[A] in A') + 1
        for i in (0, 60, 120, len(rows) - 1):
            self.assertAlmostEqual(xlsheet.cell_value(book.Results, 3 + i, column),
                                   float(self.result.derived.cAA[i]), places=12)

    def test_T33_parameters_sheet_lists_every_parameter_with_its_source(self):
        xl, book = mumix.build_workbook(self.result, os.path.join(OUTDIR, 'built.xlsx'))
        sheet = book.Parameters
        names = {}
        for row in range(2, 2 + len(mumix.PARAMETERS)):
            names[xlsheet.cell_value(sheet, row, 1)] = (xlsheet.cell_value(sheet, row, 2), xlsheet.cell_value(sheet, row, 5))
        self.assertEqual(set(names), set(mumix.PARAMETERS))
        self.assertEqual(names['Bo'], (1000.0, 'document'))
        self.assertEqual(names['kAB'][1], 'assumed')
        derived_rows = [xlsheet.cell_value(sheet, row, 5) for row in range(1, 40)]
        self.assertIn('derived', derived_rows)

    def test_T34_the_workbook_reads_back_with_nothing_unmapped(self):
        import xlw
        book = xlw.xlw().open(self.workbook(), name='mumix_back')
        self.assertEqual(book.kvr('priv').kvr('sheets'), ['Results', 'Parameters'])
        self.assertEqual(book.kvr('priv').kvr('unmapped'), [])
        self.assertEqual(len(book.Results.kvr('priv').kvr('charts').nodes()), 3)

    # ---- benchmarks -----------------------------------------------------------------------------------
    def bench_rates(self, timer):
        p = self.p
        v = mumix.FIELDS(self.state)
        v.t = 0.0
        ddt = mumix.FIELDS({name: 0.0 for name in self.state})
        rates = mumix.rates
        with timer as test:
            while test.more:
                for i in test.count:
                    rates(v, p, ddt)
        return 'rates(v, p, ddt)', 'model'

    def bench_thresholds(self, timer):
        thresholds = mumix.thresholds
        with timer as test:
            while test.more:
                for i in test.count:
                    thresholds(0.3, 1000.0, 900.0, 1.0)
        return 'thresholds', 'model'

    def bench_segment_mean(self, timer):
        segment = mumix.segment_mean
        with timer as test:
            while test.more:
                for i in test.count:
                    segment(3.0, 11.0, 0.2, 0.9)
        return 'segment_mean', 'model'
