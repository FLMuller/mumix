r"""b_kvcmp.py -- quick timing: which kv variant reads and writes fastest?  (sandbox)

QUESTION
    Which kv variant should be promoted to be the xlw writer's kv store?

VARIANTS  (unmodified copies in variants/, module -> class)
    kvpy  kvpy.py   pure Python, bytes keys, hash(bytes)                (option B)
    kv1   kv1.py    pure Python, faithful DJB2 hash
    kvc   kvc.pyx   Cython, faithful DJB2 hash
    kvc2  kvc2.pyx  Cython, option B, raw C arrays for the probe tables
    kvc3  kvc3.pyx  Cython, option B, one slot-returning probe

HOW IT RUNS
    The same operations are timed on every variant, so the rows of one group are a fair
    comparison. Groups: read, write, mutate, build (one new key into a fresh store, growth
    included) and enum. A plain dict is timed beside the reads and the write as the floor.
    ONE OP PER ITERATION: the harness takes the loop body as one op and sizes its run for
    ops of microseconds. A first version built 100 keys per iteration; for the slower
    variants such rows were dropped from the report without a note, so every row is now
    one op, and anything to set up goes in the untimed step before the loop.
    The tests run first and only check that the fixtures hold what the rows read.

HYPOTHESIS
    kvc2 and kvc3 read about equally and several times faster than kvc and kv1; kvc3
    writes and builds faster than kvc2 (its stated aim); kvpy sits between kv1 and kvc.

RESULT   (5 runs, AC power, 4.4 GHz, speed about 169%; median of the mean us per op)
    Half right. kvc2 and kvc3 lead everywhere that matters: reads 0.1-0.4 us, writes
    0.2-0.6 us, about 3-5x faster than kvc, 3.5-6x than kvpy and 7-12x than kv1.
    Geometric mean of (time / best in group): kvc2 1.14, kvc3 1.23, kvc 2.64, kvpy 4.26,
    kv1 6.86.
    kvc2 against kvc3: a tie on every row except d.kvr(k) and d[k], where kvc2 is about
    15% faster (clear of the run-to-run range). kvc3 shows NO write or build advantage
    (insert new key 0.246 vs 0.251 us), so its stated aim is not supported here.
    Cost of option B: keys() is 4x slower than kvc (5.6 vs 1.4 us), because the byte keys
    are decoded to str; vals() is no slower.
    Noise: a row is measured over at most 1000 ops, so single rows move 10-30% between
    runs; differences under about 15% are not resolved.

Run from the project root. runbench runs the tests first and the benchmarks only if none
failed; add -test or -bench only to run one half:
    python tools/runbench.py tests/z_sandbox/b_kvcmp.py
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

SOURCES = ['kvpy', 'kv1', 'kvc', 'kvc2', 'kvc3']       # the modules this suite times
CLASSES = {'kvpy': 'kv', 'kv1': 'kv1', 'kvc': 'kvc', 'kvc2': 'kvc2', 'kvc3': 'kvc3'}
BOUND = {module: load(module, into={}) for module in SOURCES}


class b_kvcmp(bench):
    BenchName = 'kvcmp'
    BenchVersion = 'M1.0.6'
    BenchHeader = ''
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        cls.size = 100
        cls.leafkeys = [f"key{i:04d}" for i in range(cls.size)]
        cls.newkeys = [f"new{i:05d}" for i in range(2000)]     # never in a store: pure inserts
        cls.sparsekeys = [(i, i + 1) for i in range(cls.size)]
        cls.make = {}
        cls.store = {}
        for module in SOURCES:
            make = BOUND[module][CLASSES[module]]
            store = make()
            for i in range(cls.size):
                store.kvw(cls.leafkeys[i], float(i))
                store[cls.sparsekeys[i]] = float(i)
            cls.make[module] = make
            cls.store[module] = store
        cls.dict = {key: float(i) for i, key in enumerate(cls.leafkeys)}

    def test_T1_read_back(self):
        for module in SOURCES:
            store = self.store[module]
            key = self.leafkeys[7]
            self.assertEqual(store.kvr(key), 7.0, module)
            self.assertEqual(getattr(store, key), 7.0, module)
            self.assertEqual(store[key], 7.0, module)
            self.assertEqual(store[self.sparsekeys[7]], 7.0, module)

    def test_T2_write_and_remove(self):
        for module in SOURCES:
            store = self.make[module]()
            store.kvw('x', 1)
            store['y'] = 2
            store[3, 4] = 5
            self.assertEqual((store.kvr('x'), store['y'], store[3, 4]), (1, 2, 5), module)
            store.remove('x')
            self.assertFalse(store.iskey('x'), module)
            self.assertEqual(len(store.keys()), 1, module)

    def bench_kvpy_kvr(self, timer):
        store, keys, size = self.store['kvpy'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvr(keys[i % size])
        return 'kvpy', 'read   d.kvr(k)'

    def bench_kvpy_dotr(self, timer):
        store, keys, size = self.store['kvpy'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    getattr(store, keys[i % size])
        return 'kvpy', 'read   d.key'

    def bench_kvpy_itemr(self, timer):
        store, keys, size = self.store['kvpy'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[keys[i % size]]
        return 'kvpy', 'read   d[k]'

    def bench_kvpy_sparser(self, timer):
        store, sparse, size = self.store['kvpy'], self.sparsekeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[sparse[i % size]]
        return 'kvpy', 'read   d[r,c]'

    def bench_kvpy_kvw(self, timer):
        store, keys, size = self.store['kvpy'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvw(keys[i % size], i)
        return 'kvpy', 'write  d.kvw(k,v)'

    def bench_kvpy_dotw(self, timer):
        store, keys, size = self.store['kvpy'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    setattr(store, keys[i % size], i)
        return 'kvpy', 'write  d.key=v'

    def bench_kvpy_itemw(self, timer):
        store, keys, size = self.store['kvpy'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[keys[i % size]] = i
        return 'kvpy', 'write  d[k]=v'

    def bench_kvpy_sparsew(self, timer):
        store, sparse, size = self.store['kvpy'], self.sparsekeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[sparse[i % size]] = i
        return 'kvpy', 'write  d[r,c]=v'

    def bench_kvpy_remove(self, timer):
        store, keys, size = self.store['kvpy'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    key = keys[i % size]
                    store.remove(key)
                    store.kvw(key, i)
        return 'kvpy', 'mutate remove+kvw'

    def bench_kvpy_build(self, timer):
        make, newkeys = self.make['kvpy'], self.newkeys
        with timer as test:
            while test.more:
                store = make()
                for i in test.count:
                    store.kvw(newkeys[i], i)
        return 'kvpy', 'build  insert new key'

    def bench_kvpy_keys(self, timer):
        store = self.store['kvpy']
        with timer as test:
            while test.more:
                for i in test.count:
                    store.keys()
        return 'kvpy', 'enum   d.keys()'

    def bench_kvpy_vals(self, timer):
        store = self.store['kvpy']
        with timer as test:
            while test.more:
                for i in test.count:
                    store.vals()
        return 'kvpy', 'enum   d.vals()'

    def bench_kv1_kvr(self, timer):
        store, keys, size = self.store['kv1'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvr(keys[i % size])
        return 'kv1', 'read   d.kvr(k)'

    def bench_kv1_dotr(self, timer):
        store, keys, size = self.store['kv1'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    getattr(store, keys[i % size])
        return 'kv1', 'read   d.key'

    def bench_kv1_itemr(self, timer):
        store, keys, size = self.store['kv1'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[keys[i % size]]
        return 'kv1', 'read   d[k]'

    def bench_kv1_sparser(self, timer):
        store, sparse, size = self.store['kv1'], self.sparsekeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[sparse[i % size]]
        return 'kv1', 'read   d[r,c]'

    def bench_kv1_kvw(self, timer):
        store, keys, size = self.store['kv1'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvw(keys[i % size], i)
        return 'kv1', 'write  d.kvw(k,v)'

    def bench_kv1_dotw(self, timer):
        store, keys, size = self.store['kv1'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    setattr(store, keys[i % size], i)
        return 'kv1', 'write  d.key=v'

    def bench_kv1_itemw(self, timer):
        store, keys, size = self.store['kv1'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[keys[i % size]] = i
        return 'kv1', 'write  d[k]=v'

    def bench_kv1_sparsew(self, timer):
        store, sparse, size = self.store['kv1'], self.sparsekeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[sparse[i % size]] = i
        return 'kv1', 'write  d[r,c]=v'

    def bench_kv1_remove(self, timer):
        store, keys, size = self.store['kv1'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    key = keys[i % size]
                    store.remove(key)
                    store.kvw(key, i)
        return 'kv1', 'mutate remove+kvw'

    def bench_kv1_build(self, timer):
        make, newkeys = self.make['kv1'], self.newkeys
        with timer as test:
            while test.more:
                store = make()
                for i in test.count:
                    store.kvw(newkeys[i], i)
        return 'kv1', 'build  insert new key'

    def bench_kv1_keys(self, timer):
        store = self.store['kv1']
        with timer as test:
            while test.more:
                for i in test.count:
                    store.keys()
        return 'kv1', 'enum   d.keys()'

    def bench_kv1_vals(self, timer):
        store = self.store['kv1']
        with timer as test:
            while test.more:
                for i in test.count:
                    store.vals()
        return 'kv1', 'enum   d.vals()'

    def bench_kvc_kvr(self, timer):
        store, keys, size = self.store['kvc'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvr(keys[i % size])
        return 'kvc', 'read   d.kvr(k)'

    def bench_kvc_dotr(self, timer):
        store, keys, size = self.store['kvc'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    getattr(store, keys[i % size])
        return 'kvc', 'read   d.key'

    def bench_kvc_itemr(self, timer):
        store, keys, size = self.store['kvc'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[keys[i % size]]
        return 'kvc', 'read   d[k]'

    def bench_kvc_sparser(self, timer):
        store, sparse, size = self.store['kvc'], self.sparsekeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[sparse[i % size]]
        return 'kvc', 'read   d[r,c]'

    def bench_kvc_kvw(self, timer):
        store, keys, size = self.store['kvc'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvw(keys[i % size], i)
        return 'kvc', 'write  d.kvw(k,v)'

    def bench_kvc_dotw(self, timer):
        store, keys, size = self.store['kvc'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    setattr(store, keys[i % size], i)
        return 'kvc', 'write  d.key=v'

    def bench_kvc_itemw(self, timer):
        store, keys, size = self.store['kvc'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[keys[i % size]] = i
        return 'kvc', 'write  d[k]=v'

    def bench_kvc_sparsew(self, timer):
        store, sparse, size = self.store['kvc'], self.sparsekeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[sparse[i % size]] = i
        return 'kvc', 'write  d[r,c]=v'

    def bench_kvc_remove(self, timer):
        store, keys, size = self.store['kvc'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    key = keys[i % size]
                    store.remove(key)
                    store.kvw(key, i)
        return 'kvc', 'mutate remove+kvw'

    def bench_kvc_build(self, timer):
        make, newkeys = self.make['kvc'], self.newkeys
        with timer as test:
            while test.more:
                store = make()
                for i in test.count:
                    store.kvw(newkeys[i], i)
        return 'kvc', 'build  insert new key'

    def bench_kvc_keys(self, timer):
        store = self.store['kvc']
        with timer as test:
            while test.more:
                for i in test.count:
                    store.keys()
        return 'kvc', 'enum   d.keys()'

    def bench_kvc_vals(self, timer):
        store = self.store['kvc']
        with timer as test:
            while test.more:
                for i in test.count:
                    store.vals()
        return 'kvc', 'enum   d.vals()'

    def bench_kvc2_kvr(self, timer):
        store, keys, size = self.store['kvc2'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvr(keys[i % size])
        return 'kvc2', 'read   d.kvr(k)'

    def bench_kvc2_dotr(self, timer):
        store, keys, size = self.store['kvc2'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    getattr(store, keys[i % size])
        return 'kvc2', 'read   d.key'

    def bench_kvc2_itemr(self, timer):
        store, keys, size = self.store['kvc2'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[keys[i % size]]
        return 'kvc2', 'read   d[k]'

    def bench_kvc2_sparser(self, timer):
        store, sparse, size = self.store['kvc2'], self.sparsekeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[sparse[i % size]]
        return 'kvc2', 'read   d[r,c]'

    def bench_kvc2_kvw(self, timer):
        store, keys, size = self.store['kvc2'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvw(keys[i % size], i)
        return 'kvc2', 'write  d.kvw(k,v)'

    def bench_kvc2_dotw(self, timer):
        store, keys, size = self.store['kvc2'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    setattr(store, keys[i % size], i)
        return 'kvc2', 'write  d.key=v'

    def bench_kvc2_itemw(self, timer):
        store, keys, size = self.store['kvc2'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[keys[i % size]] = i
        return 'kvc2', 'write  d[k]=v'

    def bench_kvc2_sparsew(self, timer):
        store, sparse, size = self.store['kvc2'], self.sparsekeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[sparse[i % size]] = i
        return 'kvc2', 'write  d[r,c]=v'

    def bench_kvc2_remove(self, timer):
        store, keys, size = self.store['kvc2'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    key = keys[i % size]
                    store.remove(key)
                    store.kvw(key, i)
        return 'kvc2', 'mutate remove+kvw'

    def bench_kvc2_build(self, timer):
        make, newkeys = self.make['kvc2'], self.newkeys
        with timer as test:
            while test.more:
                store = make()
                for i in test.count:
                    store.kvw(newkeys[i], i)
        return 'kvc2', 'build  insert new key'

    def bench_kvc2_keys(self, timer):
        store = self.store['kvc2']
        with timer as test:
            while test.more:
                for i in test.count:
                    store.keys()
        return 'kvc2', 'enum   d.keys()'

    def bench_kvc2_vals(self, timer):
        store = self.store['kvc2']
        with timer as test:
            while test.more:
                for i in test.count:
                    store.vals()
        return 'kvc2', 'enum   d.vals()'

    def bench_kvc3_kvr(self, timer):
        store, keys, size = self.store['kvc3'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvr(keys[i % size])
        return 'kvc3', 'read   d.kvr(k)'

    def bench_kvc3_dotr(self, timer):
        store, keys, size = self.store['kvc3'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    getattr(store, keys[i % size])
        return 'kvc3', 'read   d.key'

    def bench_kvc3_itemr(self, timer):
        store, keys, size = self.store['kvc3'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[keys[i % size]]
        return 'kvc3', 'read   d[k]'

    def bench_kvc3_sparser(self, timer):
        store, sparse, size = self.store['kvc3'], self.sparsekeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[sparse[i % size]]
        return 'kvc3', 'read   d[r,c]'

    def bench_kvc3_kvw(self, timer):
        store, keys, size = self.store['kvc3'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store.kvw(keys[i % size], i)
        return 'kvc3', 'write  d.kvw(k,v)'

    def bench_kvc3_dotw(self, timer):
        store, keys, size = self.store['kvc3'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    setattr(store, keys[i % size], i)
        return 'kvc3', 'write  d.key=v'

    def bench_kvc3_itemw(self, timer):
        store, keys, size = self.store['kvc3'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[keys[i % size]] = i
        return 'kvc3', 'write  d[k]=v'

    def bench_kvc3_sparsew(self, timer):
        store, sparse, size = self.store['kvc3'], self.sparsekeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    store[sparse[i % size]] = i
        return 'kvc3', 'write  d[r,c]=v'

    def bench_kvc3_remove(self, timer):
        store, keys, size = self.store['kvc3'], self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    key = keys[i % size]
                    store.remove(key)
                    store.kvw(key, i)
        return 'kvc3', 'mutate remove+kvw'

    def bench_kvc3_build(self, timer):
        make, newkeys = self.make['kvc3'], self.newkeys
        with timer as test:
            while test.more:
                store = make()
                for i in test.count:
                    store.kvw(newkeys[i], i)
        return 'kvc3', 'build  insert new key'

    def bench_kvc3_keys(self, timer):
        store = self.store['kvc3']
        with timer as test:
            while test.more:
                for i in test.count:
                    store.keys()
        return 'kvc3', 'enum   d.keys()'

    def bench_kvc3_vals(self, timer):
        store = self.store['kvc3']
        with timer as test:
            while test.more:
                for i in test.count:
                    store.vals()
        return 'kvc3', 'enum   d.vals()'

    def bench_dict_get(self, timer):
        table, keys, size = self.dict, self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    table.get(keys[i % size])
        return 'dict', 'read   d.kvr(k)'

    def bench_dict_item(self, timer):
        table, keys, size = self.dict, self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    table[keys[i % size]]
        return 'dict', 'read   d[k]'

    def bench_dict_set(self, timer):
        table, keys, size = self.dict, self.leafkeys, self.size
        with timer as test:
            while test.more:
                for i in test.count:
                    table[keys[i % size]] = i
        return 'dict', 'write  d.kvw(k,v)'
