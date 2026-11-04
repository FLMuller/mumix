"""
b_xlver.py -- sandbox: the same operations on three versions of xlw, run one version at a time.

Question   How do the three builds compare on creating and saving a workbook and on opening
           it, for numbers, for mixed text and numbers, and for real Excel files?
Versions   old   the first xlw: tkv cell nodes, ElementTree reader, f-string writer (1c46628)
           py    the same with the pure-Python xlsheet codec patched in (1c46628 + xlsheet)
           grid  the grid: one kv per sheet, book tables, codec on tuples, Python loops
           new   the grid with the hot loops in Cython (this tree)
Method     The suite uses only what every version has (xlw(), newbook, write(block), save(),
           open()) and reads values through whichever reader the version has. It runs from a
           checkout of each version (git worktree), so each version imports its own modules:
               XLVER=old|py|grid|new python tools/runbench.py tests/z_sandbox/b_xlver.py
           The files that are opened are written once by the first run into XLSHARE, so every
           version opens the same bytes; XLREF is the folder of the Excel reference files.
           One op is one whole operation on 5 000 cells (500 x 10) or on the real file.
Result     AC, ms per operation, median of 3 runs (old / py / grid / new):
           create to saved, 5 000 numbers 40.3 / 35.5 / 22.4 / 11.6; mixed 35.0 / 32.5 / 19.7 /
           11.1. Opened to read, numbers 43.2 / 21.8 / 12.3 / 9.8; mixed 43.4 / 21.8 / 14.4 /
           10.9. Open only 40.0 / 17.9 / 8.5 / 5.6. Save only, numbers 22.7 / 18.4 / 12.1 / 7.0.
           The 9 015-cell Excel file: open 83.8 / 40.6 / 20.5 / 15.8, save 59.5 / 44.5 / 31.6 /
           20.2. The 250-cell file with formulas (fixed costs dominate): open 7.2 / 6.2 / 5.6 /
           5.7, save 3.7 / 3.5 / 2.8 / 2.8. Geometric mean new / old 0.31.
           Second set, 2026-11-01, AC at 144-167% speed, median of 4-5 runs, ms per operation
           (old / py / new; formulas and cell-held text now in new): create to saved, numbers
           43.5 / 39.1 / 12.0, mixed 37.1 / 33.9 / 11.6. Opened to read, numbers 48.6 / 22.9 /
           10.3, mixed 44.8 / 22.4 / 11.5. Theopylline As recieved (headers and numbers, 9 015
           cells): open 91.7 / 40.3 / 16.7, save 59.9 / 48.1 / 21.0. Theophylline Isotherm
           (experimental, 2 formulas, fixed costs dominate): open 1.90 / 1.90 / 1.96, save
           1.14 / 1.16 / 1.16. htmltags (functions, text and numbers, 104 formulas): open
           6.22 / 4.00 / 3.14, save 4.25 / 3.38 / 2.28. old and py read the cached values only
           and drop the formulas on save, new keeps them.
"""

import os
import sys


def findtools():                      # walk up to the folder that holds tools/
    from os.path import abspath, dirname, isdir, join
    here = dirname(abspath(__file__))
    while here != dirname(here) and not isdir(join(here, 'tools')):
        here = dirname(here)
    sys.path.insert(0, join(here, 'tools'))
    return here


ROOT = findtools()
sys.path.insert(0, os.path.join(ROOT, 'xlw'))
from use import load
from bench import bench

SOURCES = ['xlw']
globals().update(load('xlw', into={}))
import xlw as xlwmodule
import xlreader

MODE = os.environ.get('XLVER', 'new')
SHARE = os.environ.get('XLSHARE', os.path.join(ROOT, 'results', 'ver'))
REFERENCE = os.environ.get('XLREF', os.path.join(ROOT, 'results', 'reference'))
FIXTURES = os.environ.get('XLFIX', os.path.join(ROOT, 'tests', 'fixtures'))
OUTDIR = os.path.join(ROOT, 'results', 'b_xlver_' + MODE)

try:
    import xlsheet
except ImportError:
    xlsheet = None
GRID = xlsheet is not None and hasattr(xlsheet, 'cell_value')
if MODE == 'grid' and GRID:
    xlsheet.FUN = None                        # the grid with the Python loops


def values_of(sheet, rows, cols):
    """Read every value of a rows x cols block, whichever reader this version has."""
    if GRID:
        value = xlsheet.cell_value
        return [value(sheet, r, c) for r in range(1, rows + 1) for c in range(1, cols + 1)]
    return [sheet[r, c].kvr('val') for r in range(1, rows + 1) for c in range(1, cols + 1)]


class Patched:
    """Mode py: read and write worksheets with the pure-Python xlsheet codec of 1c46628."""

    def __enter__(me):
        me.on = MODE == 'py' and xlsheet is not None and not GRID
        if me.on:
            me.read = xlreader.read_cells
            me.write = xlwmodule.sheet_data

            def read_cells(archive, path, sheet, strings, deltas, report):
                return xlsheet.xml_to_sheet(archive.read(path), sheet, strings, deltas, report)
            xlreader.read_cells = read_cells
            xlwmodule.sheet_data = xlsheet.sheet_to_xml
        return me

    def __exit__(me, *exc):
        if me.on:
            xlreader.read_cells = me.read
            xlwmodule.sheet_data = me.write


def table(kind):
    rows = []
    for i in range(500):
        line = []
        for j in range(10):
            if kind == 'mix' and j % 3 == 0:
                line.append(f'label {j} {i % 7}')
            elif kind == 'mix' and j % 5 == 1:
                line.append(i % 2 == 0)
            else:
                line.append(i * 0.001 + j)
        rows.append(line)
    return rows


class b_xlver(bench):
    BenchName = 'xlver'
    BenchVersion = 'M1.0.16'
    BenchHeader = ''
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        os.makedirs(OUTDIR, exist_ok=True)
        os.makedirs(SHARE, exist_ok=True)
        cls.tables = {'num': table('num'), 'mix': table('mix')}
        cls.shared = {}
        cls.built = {}
        for kind in ('num', 'mix'):
            path = os.path.join(SHARE, f'{kind}5k.xlsx')
            if not os.path.isfile(path):
                xl = xlw()
                xl.newbook(path, 'Data')
                xl.write(cls.tables[kind])
                xl.save()
            cls.shared[kind] = path
            xl = xlw()
            xl.newbook(os.path.join(OUTDIR, f'built_{kind}'), 'Data')
            xl.write(cls.tables[kind])
            cls.built[kind] = xl
        cls.real = {}
        for key, folder, name in (('xrd', REFERENCE, 'Theopylline As recieved.xlsx'),
                                  ('isotherm', REFERENCE, 'Theophylline Isotherm.xlsx'),
                                  ('html', FIXTURES, 'htmltags.xlsx')):
            source = os.path.join(folder, name)
            if os.path.isfile(source):
                with Patched():
                    xl = xlw()
                    xl.open(source, 'real_' + key)
                    cls.real[key] = (source, xl)

    def test_T1_the_shared_files_read_back_what_was_written(self):
        for kind in ('num', 'mix'):
            with Patched():
                xl = xlw()
                book = xl.open(self.shared[kind])
                values = values_of(book.Data, 500, 10)
            if kind == 'num':
                self.assertAlmostEqual(values[1], 1.0, places=9)
                self.assertAlmostEqual(values[-1], 499 * 0.001 + 9, places=9)
            else:
                self.assertEqual(values[0], 'label 0 0')
                self.assertIs(values[1], True)

    def test_T2_a_saved_workbook_has_the_cells(self):
        with Patched():
            xl = self.built['mix']
            xl.save()
            book = xlw().open(os.path.join(OUTDIR, 'built_mix.xlsx'))
            values = values_of(book.Data, 500, 10)
        self.assertEqual(values[0], 'label 0 0')
        self.assertIs(values[1], True)

    # ---- one op = one whole operation on 5 000 cells --------------------------------------
    def create_to_saved(self, timer, kind):
        data = self.tables[kind]
        path = os.path.join(OUTDIR, f'c2s_{kind}')
        with Patched():
            with timer as test:
                while test.more:
                    for i in test.count:
                        xl = xlw()
                        xl.newbook(path, 'Data')
                        xl.write(data)
                        xl.save()

    def opened_to_read(self, timer, kind):
        path = self.shared[kind]
        with Patched():
            with timer as test:
                while test.more:
                    for i in test.count:
                        book = xlw().open(path)
                        values_of(book.Data, 500, 10)

    def open_only(self, timer, kind):
        path = self.shared[kind]
        with Patched():
            with timer as test:
                while test.more:
                    for i in test.count:
                        xlw().open(path)

    def save_only(self, timer, kind):
        xl = self.built[kind]
        with Patched():
            with timer as test:
                while test.more:
                    for i in test.count:
                        xl.save()

    def bench_01_create_to_saved_numbers(self, timer):
        self.create_to_saved(timer, 'num')
        return 'create to saved, 5 000 numbers', 'whole book'

    def bench_02_create_to_saved_mixed(self, timer):
        self.create_to_saved(timer, 'mix')
        return 'create to saved, 5 000 mixed', 'whole book'

    def bench_03_opened_to_read_numbers(self, timer):
        self.opened_to_read(timer, 'num')
        return 'opened to read, 5 000 numbers', 'whole book'

    def bench_04_opened_to_read_mixed(self, timer):
        self.opened_to_read(timer, 'mix')
        return 'opened to read, 5 000 mixed', 'whole book'

    def bench_05_open_only_numbers(self, timer):
        self.open_only(timer, 'num')
        return 'open only, 5 000 numbers', 'whole book'

    def bench_06_save_only_numbers(self, timer):
        self.save_only(timer, 'num')
        return 'save only, 5 000 numbers', 'whole book'

    def bench_07_save_only_mixed(self, timer):
        self.save_only(timer, 'mix')
        return 'save only, 5 000 mixed', 'whole book'

    def real_open(self, timer, key):
        if key not in self.real:
            self.skipTest('no reference workbook')
        source = self.real[key][0]
        with Patched():
            with timer as test:
                while test.more:
                    for i in test.count:
                        xlw().open(source, 'real_' + key)

    def real_save(self, timer, key):
        if key not in self.real:
            self.skipTest('no reference workbook')
        xl = self.real[key][1]
        with Patched():
            with timer as test:
                while test.more:
                    for i in test.count:
                        xl.save()

    def bench_08_open_real_xrd(self, timer):
        self.real_open(timer, 'xrd')
        return 'open Theopylline As recieved (headers and numbers, 9 015 cells)', 'real file'

    def bench_09_save_real_xrd(self, timer):
        self.real_save(timer, 'xrd')
        return 'save Theopylline As recieved', 'real file'

    def bench_10_open_isotherm(self, timer):
        self.real_open(timer, 'isotherm')
        return 'open Theophylline Isotherm (experimental data, 2 formulas)', 'real file'

    def bench_11_save_isotherm(self, timer):
        self.real_save(timer, 'isotherm')
        return 'save Theophylline Isotherm', 'real file'

    def bench_12_open_htmltags(self, timer):
        self.real_open(timer, 'html')
        return 'open htmltags (functions, text and numbers; 104 formulas)', 'real file'

    def bench_13_save_htmltags(self, timer):
        self.real_save(timer, 'html')
        return 'save htmltags', 'real file'
