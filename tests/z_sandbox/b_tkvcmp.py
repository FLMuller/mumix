r"""b_tkvcmp.py -- quick timing: which tkv variant reads and writes fastest?  (sandbox)

QUESTION
    Which tkv variant should be promoted to be the xlw writer's document tree?

VARIANTS  (unmodified copies in variants/, module -> class)
    tkvpy  tkvpy.py   pure Python, bytes keys, hash(bytes)              (option B)
    tkv1   tkv1.py    pure Python, faithful DJB2 hash
    tkvc   tkvc.pyx   Cython, faithful DJB2 hash
    tkvc2  tkvc2.pyx  Cython, option B, raw C arrays for the probe tables
    tkvc3  tkvc3.pyx  Cython, option B, one slot-returning probe

HOW IT RUNS
    The same operations are timed on every variant. Groups: read (depth 1 and 4, dotted
    chain, item, sparse), write (depth 1 and 4, sparse), build (one cell: a sparse (r,c)
    node with three leaves added to a fresh sheet, which is how the writer fills one),
    cell entries() (the writer's one-call read of a cell) and enum (nodes of a 100-cell
    sheet, keys).
    ONE OP PER ITERATION: the harness takes the loop body as one op and sizes its run for
    ops of microseconds. A first version built 100 cells per iteration (0.3 to 2 ms); the
    rows of four variants were dropped from the report without a note, so every row is
    now one op, and anything to set up goes in the untimed step before the loop.
    The tests run first and only check that the fixtures hold what the rows read.

HYPOTHESIS
    tkvc2 and tkvc3 read about equally, at roughly 0.2 us for depth 1 (port log: tkvc2
    0.23 us, tkvc 0.48 us, pure Python 1.28 us); tkvc3 is faster on writes and on the
    cell build, which is the path the writer pays for.

RESULT   (5 runs, AC power, 4.4 GHz, speed about 166%; median of the mean us per op)
    tkvc2 and tkvc3 are a tie on every row (each row's run-to-run range includes 1.0).
    Both are 2-4.5x faster than tkvc, 3-5x than tkvpy and 5-7x than tkv1.
    Geometric mean of (time / best in group): tkvc2 1.20, tkvc3 1.20, tkvc 2.15,
    tkvpy 3.42, tkv1 5.24. Read depth 1 0.20 us, depth 4 0.8 us, write depth 1 0.5 us,
    one cell (node + 3 leaves) 2.4 us. tkvc3 shows no write or build advantage.
    Cost of option B: entries() 0.33-0.37 us against 0.19 us for tkvc, and keys() 5.2
    against 1.4 us, because the byte keys are decoded to str.
    Writer view: one cell built and read back once on save costs 2.8 us (tkvc2, tkvc3),
    5.2 us (tkvc), 11.7 us (tkvpy), 16.3 us (tkv1); 100,000 cells = 0.3, 0.5, 1.2, 1.6 s.
    The tkv layer is a small part of a save at any of these speeds.
    Noise: a row is measured over at most 1000 ops, so single rows move 10-30% between
    runs; differences under about 15% are not resolved.

Run from the project root. runbench runs the tests first and the benchmarks only if none
failed; add -test or -bench only to run one half:
    python tools/runbench.py tests/z_sandbox/b_tkvcmp.py
"""

import sys


def findtools():                      # walk up to the folder that holds tools/
    from os.path import abspath, dirname, isdir, join
    here = dirname(abspath(__file__))
    while here != dirname(here) and not isdir(join(here, 'tools')):
        here = dirname(here)
    sys.path.insert(0, join(here, 'tools'))


findtools()
from bench import bench
from use import use, load

use('variants', 'silent')

SOURCES = ['tkvpy', 'tkv1', 'tkvc', 'tkvc2', 'tkvc3']  # the modules this suite times
CLASSES = {'tkvpy': 'tkv', 'tkv1': 'tkv1', 'tkvc': 'tkvc', 'tkvc2': 'tkvc2', 'tkvc3': 'tkvc3'}
BOUND = {module: load(module, into={}) for module in SOURCES}


class b_tkvcmp(bench):
    BenchName = 'tkvcmp'
    BenchVersion = 'M1.0.6'
    BenchHeader = ''
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        cls.size = 100
        cls.paths1 = [f"key{i:04d}" for i in range(cls.size)]
        cls.paths4 = ["n1.n2.n3." + key for key in cls.paths1]
        cls.cellrows = [i // 100 + 1 for i in range(2000)]     # 2000 distinct (r,c) cells
        cls.cellcols = [i % 100 + 1 for i in range(2000)]
        cls.sparsekeys = [(i, i + 1) for i in range(cls.size)]
        cls.make = {}
        cls.store = {}
        cls.sheets = {}
        cls.cells = {}
        for module in SOURCES:
            make = BOUND[module][CLASSES[module]]
            store = make()
            for i in range(cls.size):
                store.kvw(cls.paths1[i], i)
                store.kvw(cls.paths4[i], i)
                store[cls.sparsekeys[i]] = i
            store.alpha.beta.gamma.zeta1 = 88
            sheet = store.node('sheet')
            cells = []
            for row in range(1, 11):
                for col in range(1, 11):
                    cell = sheet.node(row, col)
                    cell.kvw('val', row * col)
                    cell.kvw('bold', 1)
                    cell.kvw('fill', 'FFFF00')
                    cells.append(cell)
            cls.make[module] = make
            cls.store[module] = store
            cls.sheets[module] = sheet
            cls.cells[module] = cells

    def test_T1_read_back(self):
        for module in SOURCES:
            store = self.store[module]
            self.assertEqual(store.kvr(self.paths1[7]), 7, module)
            self.assertEqual(store.kvr(self.paths4[7]), 7, module)
            self.assertEqual(store.alpha.beta.gamma.zeta1, 88, module)
            self.assertEqual(store[self.sparsekeys[7]], 7, module)

    def test_T2_cells(self):
        for module in SOURCES:
            cells = self.cells[module]
            self.assertEqual(len(cells), 100, module)
            self.assertEqual(len(self.sheets[module].nodes()), 100, module)
            self.assertEqual(len(cells[0].entries()), 3, module)
            self.assertEqual(cells[0].kvr('fill'), 'FFFF00', module)

    def bench_tkvpy_kvr1(self, timer):
        store, paths1, size = self.store['tkvpy'], self.paths1, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvr(paths1[i % size])
        return 'tkvpy', 'read   t.kvr(d=1)'

    def bench_tkvpy_kvr4(self, timer):
        store, paths4, size = self.store['tkvpy'], self.paths4, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvr(paths4[i % size])
        return 'tkvpy', 'read   t.kvr(d=4)'

    def bench_tkvpy_dot4(self, timer):
        store = self.store['tkvpy']
        with timer as test:
            while test.more:
                for i in test.count:
                    store.alpha.beta.gamma.zeta1
        return 'tkvpy', 'read   t.a.b.c.d'

    def bench_tkvpy_item(self, timer):
        store, paths1, size = self.store['tkvpy'], self.paths1, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[paths1[i % size]]
        return 'tkvpy', 'read   t[k]'

    def bench_tkvpy_sparser(self, timer):
        store, sparse, size = self.store['tkvpy'], self.sparsekeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[sparse[i % size]]
        return 'tkvpy', 'read   t[r,c]'

    def bench_tkvpy_kvw1(self, timer):
        store, paths1, size = self.store['tkvpy'], self.paths1, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvw(paths1[i % size], i)
        return 'tkvpy', 'write  t.kvw(d=1)'

    def bench_tkvpy_kvw4(self, timer):
        store, paths4, size = self.store['tkvpy'], self.paths4, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvw(paths4[i % size], i)
        return 'tkvpy', 'write  t.kvw(d=4)'

    def bench_tkvpy_sparsew(self, timer):
        store, sparse, size = self.store['tkvpy'], self.sparsekeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[sparse[i % size]] = i
        return 'tkvpy', 'write  t[r,c]=v'

    def bench_tkvpy_cells(self, timer):
        cellrows, cellcols, make = self.cellrows, self.cellcols, self.make['tkvpy']
        with timer as test:
            while test.more:
                store = make()
                sheet = store.node('sheet')
                for i in test.count:
                    cell = sheet.node(cellrows[i], cellcols[i])
                    cell.kvw('val', i)
                    cell.kvw('bold', 1)
                    cell.kvw('fill', 'FFFF00')
        return 'tkvpy', 'build  1 cell (node + 3 leaves)'

    def bench_tkvpy_entries(self, timer):
        cells, size = self.cells['tkvpy'], self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    cells[i % size].entries()
        return 'tkvpy', 'read   cell.entries()'

    def bench_tkvpy_nodes(self, timer):
        sheet = self.sheets['tkvpy']
        with timer as test:
            while test.more:
                for i in test.count:
                    sheet.nodes()
        return 'tkvpy', 'enum   sheet.nodes() of 100'

    def bench_tkvpy_keys(self, timer):
        store = self.store['tkvpy']
        with timer as test:
            while test.more:
                for i in test.count:
                    store.keys()
        return 'tkvpy', 'enum   t.keys()'

    def bench_tkv1_kvr1(self, timer):
        store, paths1, size = self.store['tkv1'], self.paths1, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvr(paths1[i % size])
        return 'tkv1', 'read   t.kvr(d=1)'

    def bench_tkv1_kvr4(self, timer):
        store, paths4, size = self.store['tkv1'], self.paths4, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvr(paths4[i % size])
        return 'tkv1', 'read   t.kvr(d=4)'

    def bench_tkv1_dot4(self, timer):
        store = self.store['tkv1']
        with timer as test:
            while test.more:
                for i in test.count:
                    store.alpha.beta.gamma.zeta1
        return 'tkv1', 'read   t.a.b.c.d'

    def bench_tkv1_item(self, timer):
        store, paths1, size = self.store['tkv1'], self.paths1, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[paths1[i % size]]
        return 'tkv1', 'read   t[k]'

    def bench_tkv1_sparser(self, timer):
        store, sparse, size = self.store['tkv1'], self.sparsekeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[sparse[i % size]]
        return 'tkv1', 'read   t[r,c]'

    def bench_tkv1_kvw1(self, timer):
        store, paths1, size = self.store['tkv1'], self.paths1, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvw(paths1[i % size], i)
        return 'tkv1', 'write  t.kvw(d=1)'

    def bench_tkv1_kvw4(self, timer):
        store, paths4, size = self.store['tkv1'], self.paths4, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvw(paths4[i % size], i)
        return 'tkv1', 'write  t.kvw(d=4)'

    def bench_tkv1_sparsew(self, timer):
        store, sparse, size = self.store['tkv1'], self.sparsekeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[sparse[i % size]] = i
        return 'tkv1', 'write  t[r,c]=v'

    def bench_tkv1_cells(self, timer):
        cellrows, cellcols, make = self.cellrows, self.cellcols, self.make['tkv1']
        with timer as test:
            while test.more:
                store = make()
                sheet = store.node('sheet')
                for i in test.count:
                    cell = sheet.node(cellrows[i], cellcols[i])
                    cell.kvw('val', i)
                    cell.kvw('bold', 1)
                    cell.kvw('fill', 'FFFF00')
        return 'tkv1', 'build  1 cell (node + 3 leaves)'

    def bench_tkv1_entries(self, timer):
        cells, size = self.cells['tkv1'], self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    cells[i % size].entries()
        return 'tkv1', 'read   cell.entries()'

    def bench_tkv1_nodes(self, timer):
        sheet = self.sheets['tkv1']
        with timer as test:
            while test.more:
                for i in test.count:
                    sheet.nodes()
        return 'tkv1', 'enum   sheet.nodes() of 100'

    def bench_tkv1_keys(self, timer):
        store = self.store['tkv1']
        with timer as test:
            while test.more:
                for i in test.count:
                    store.keys()
        return 'tkv1', 'enum   t.keys()'

    def bench_tkvc_kvr1(self, timer):
        store, paths1, size = self.store['tkvc'], self.paths1, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvr(paths1[i % size])
        return 'tkvc', 'read   t.kvr(d=1)'

    def bench_tkvc_kvr4(self, timer):
        store, paths4, size = self.store['tkvc'], self.paths4, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvr(paths4[i % size])
        return 'tkvc', 'read   t.kvr(d=4)'

    def bench_tkvc_dot4(self, timer):
        store = self.store['tkvc']
        with timer as test:
            while test.more:
                for i in test.count:
                    store.alpha.beta.gamma.zeta1
        return 'tkvc', 'read   t.a.b.c.d'

    def bench_tkvc_item(self, timer):
        store, paths1, size = self.store['tkvc'], self.paths1, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[paths1[i % size]]
        return 'tkvc', 'read   t[k]'

    def bench_tkvc_sparser(self, timer):
        store, sparse, size = self.store['tkvc'], self.sparsekeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[sparse[i % size]]
        return 'tkvc', 'read   t[r,c]'

    def bench_tkvc_kvw1(self, timer):
        store, paths1, size = self.store['tkvc'], self.paths1, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvw(paths1[i % size], i)
        return 'tkvc', 'write  t.kvw(d=1)'

    def bench_tkvc_kvw4(self, timer):
        store, paths4, size = self.store['tkvc'], self.paths4, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvw(paths4[i % size], i)
        return 'tkvc', 'write  t.kvw(d=4)'

    def bench_tkvc_sparsew(self, timer):
        store, sparse, size = self.store['tkvc'], self.sparsekeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[sparse[i % size]] = i
        return 'tkvc', 'write  t[r,c]=v'

    def bench_tkvc_cells(self, timer):
        cellrows, cellcols, make = self.cellrows, self.cellcols, self.make['tkvc']
        with timer as test:
            while test.more:
                store = make()
                sheet = store.node('sheet')
                for i in test.count:
                    cell = sheet.node(cellrows[i], cellcols[i])
                    cell.kvw('val', i)
                    cell.kvw('bold', 1)
                    cell.kvw('fill', 'FFFF00')
        return 'tkvc', 'build  1 cell (node + 3 leaves)'

    def bench_tkvc_entries(self, timer):
        cells, size = self.cells['tkvc'], self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    cells[i % size].entries()
        return 'tkvc', 'read   cell.entries()'

    def bench_tkvc_nodes(self, timer):
        sheet = self.sheets['tkvc']
        with timer as test:
            while test.more:
                for i in test.count:
                    sheet.nodes()
        return 'tkvc', 'enum   sheet.nodes() of 100'

    def bench_tkvc_keys(self, timer):
        store = self.store['tkvc']
        with timer as test:
            while test.more:
                for i in test.count:
                    store.keys()
        return 'tkvc', 'enum   t.keys()'

    def bench_tkvc2_kvr1(self, timer):
        store, paths1, size = self.store['tkvc2'], self.paths1, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvr(paths1[i % size])
        return 'tkvc2', 'read   t.kvr(d=1)'

    def bench_tkvc2_kvr4(self, timer):
        store, paths4, size = self.store['tkvc2'], self.paths4, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvr(paths4[i % size])
        return 'tkvc2', 'read   t.kvr(d=4)'

    def bench_tkvc2_dot4(self, timer):
        store = self.store['tkvc2']
        with timer as test:
            while test.more:
                for i in test.count:
                    store.alpha.beta.gamma.zeta1
        return 'tkvc2', 'read   t.a.b.c.d'

    def bench_tkvc2_item(self, timer):
        store, paths1, size = self.store['tkvc2'], self.paths1, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[paths1[i % size]]
        return 'tkvc2', 'read   t[k]'

    def bench_tkvc2_sparser(self, timer):
        store, sparse, size = self.store['tkvc2'], self.sparsekeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[sparse[i % size]]
        return 'tkvc2', 'read   t[r,c]'

    def bench_tkvc2_kvw1(self, timer):
        store, paths1, size = self.store['tkvc2'], self.paths1, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvw(paths1[i % size], i)
        return 'tkvc2', 'write  t.kvw(d=1)'

    def bench_tkvc2_kvw4(self, timer):
        store, paths4, size = self.store['tkvc2'], self.paths4, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvw(paths4[i % size], i)
        return 'tkvc2', 'write  t.kvw(d=4)'

    def bench_tkvc2_sparsew(self, timer):
        store, sparse, size = self.store['tkvc2'], self.sparsekeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[sparse[i % size]] = i
        return 'tkvc2', 'write  t[r,c]=v'

    def bench_tkvc2_cells(self, timer):
        cellrows, cellcols, make = self.cellrows, self.cellcols, self.make['tkvc2']
        with timer as test:
            while test.more:
                store = make()
                sheet = store.node('sheet')
                for i in test.count:
                    cell = sheet.node(cellrows[i], cellcols[i])
                    cell.kvw('val', i)
                    cell.kvw('bold', 1)
                    cell.kvw('fill', 'FFFF00')
        return 'tkvc2', 'build  1 cell (node + 3 leaves)'

    def bench_tkvc2_entries(self, timer):
        cells, size = self.cells['tkvc2'], self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    cells[i % size].entries()
        return 'tkvc2', 'read   cell.entries()'

    def bench_tkvc2_nodes(self, timer):
        sheet = self.sheets['tkvc2']
        with timer as test:
            while test.more:
                for i in test.count:
                    sheet.nodes()
        return 'tkvc2', 'enum   sheet.nodes() of 100'

    def bench_tkvc2_keys(self, timer):
        store = self.store['tkvc2']
        with timer as test:
            while test.more:
                for i in test.count:
                    store.keys()
        return 'tkvc2', 'enum   t.keys()'

    def bench_tkvc3_kvr1(self, timer):
        store, paths1, size = self.store['tkvc3'], self.paths1, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvr(paths1[i % size])
        return 'tkvc3', 'read   t.kvr(d=1)'

    def bench_tkvc3_kvr4(self, timer):
        store, paths4, size = self.store['tkvc3'], self.paths4, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvr(paths4[i % size])
        return 'tkvc3', 'read   t.kvr(d=4)'

    def bench_tkvc3_dot4(self, timer):
        store = self.store['tkvc3']
        with timer as test:
            while test.more:
                for i in test.count:
                    store.alpha.beta.gamma.zeta1
        return 'tkvc3', 'read   t.a.b.c.d'

    def bench_tkvc3_item(self, timer):
        store, paths1, size = self.store['tkvc3'], self.paths1, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[paths1[i % size]]
        return 'tkvc3', 'read   t[k]'

    def bench_tkvc3_sparser(self, timer):
        store, sparse, size = self.store['tkvc3'], self.sparsekeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[sparse[i % size]]
        return 'tkvc3', 'read   t[r,c]'

    def bench_tkvc3_kvw1(self, timer):
        store, paths1, size = self.store['tkvc3'], self.paths1, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvw(paths1[i % size], i)
        return 'tkvc3', 'write  t.kvw(d=1)'

    def bench_tkvc3_kvw4(self, timer):
        store, paths4, size = self.store['tkvc3'], self.paths4, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvw(paths4[i % size], i)
        return 'tkvc3', 'write  t.kvw(d=4)'

    def bench_tkvc3_sparsew(self, timer):
        store, sparse, size = self.store['tkvc3'], self.sparsekeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[sparse[i % size]] = i
        return 'tkvc3', 'write  t[r,c]=v'

    def bench_tkvc3_cells(self, timer):
        cellrows, cellcols, make = self.cellrows, self.cellcols, self.make['tkvc3']
        with timer as test:
            while test.more:
                store = make()
                sheet = store.node('sheet')
                for i in test.count:
                    cell = sheet.node(cellrows[i], cellcols[i])
                    cell.kvw('val', i)
                    cell.kvw('bold', 1)
                    cell.kvw('fill', 'FFFF00')
        return 'tkvc3', 'build  1 cell (node + 3 leaves)'

    def bench_tkvc3_entries(self, timer):
        cells, size = self.cells['tkvc3'], self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    cells[i % size].entries()
        return 'tkvc3', 'read   cell.entries()'

    def bench_tkvc3_nodes(self, timer):
        sheet = self.sheets['tkvc3']
        with timer as test:
            while test.more:
                for i in test.count:
                    sheet.nodes()
        return 'tkvc3', 'enum   sheet.nodes() of 100'

    def bench_tkvc3_keys(self, timer):
        store = self.store['tkvc3']
        with timer as test:
            while test.more:
                for i in test.count:
                    store.keys()
        return 'tkvc3', 'enum   t.keys()'
