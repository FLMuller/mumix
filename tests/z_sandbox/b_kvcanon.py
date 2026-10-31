"""
b_kvcanon.py -- sandbox: does the delimiter of the canonical sparse key matter?  (kv, kv2)

Question   kv stores d[5, 3] as the text "(5 3)"; kv2 stores it as "[5 3]". Does the choice of
           delimiter change the speed of reading, writing or listing sparse keys?
Variants   kv   xlw/kv.pyx    "(5 3)"   text starting with ( is reserved
           kv2  xlw/kv2.pyx   "[5 3]"   text starting with [ is reserved
History    A first kv2 stored the key as 0xFF + "5 3" (and a kvlast variant as "5 3" + 0xFF),
           so that no text could collide. Get, set and insert were no faster, indici() was
           2.3x slower (the display form had to be rebuilt per key), and "(5 3)" no longer
           addressed the cell, so a key from indici() did not round-trip. Both were dropped.
Method     Same operations on both, one op per iteration: sparse read, sparse write
           (existing), one-dimensional read, insert of a new sparse key into a fresh store,
           indici() over 100 keys, and a text read as the control.
Result     AC power, us per op (kv / kv2): sparse read 0.41 / 0.42; sparse write 0.47 / 0.50;
           one-dimensional read 0.19 / 0.21; insert a new sparse key 0.55 / 0.55; indici()
           over 100 keys 5.6 / 5.4; text read (control) 0.19 / 0.19. All level within the
           5-10% noise of a row: the delimiter costs nothing.

Run from the project root:
    python tools/runbench.py tests/z_sandbox/b_kvcanon.py
"""

import sys


def findtools():                      # walk up to the folder that holds tools/
    from os.path import abspath, dirname, isdir, join
    here = dirname(abspath(__file__))
    while here != dirname(here) and not isdir(join(here, 'tools')):
        here = dirname(here)
    sys.path.insert(0, join(here, 'tools'))
    return here


ROOT = findtools()
from bench import bench
from use import use, load

use('xlw', 'silent')

SOURCES = ['kv', 'kv2']
CLASSES = {'kv': 'kv', 'kv2': 'kv2'}
BOUND = {module: load(module, into={}) for module in SOURCES}


class b_kvcanon(bench):
    BenchName = 'kvcanon'
    BenchVersion = 'M1.0.2'
    BenchHeader = ''
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        cls.size = 100
        cls.sparse = [(i, i + 1) for i in range(cls.size)]
        cls.newkeys = [(i, i + 7) for i in range(2000)]
        cls.leaf = [f'key{i:04d}' for i in range(cls.size)]
        cls.make = {name: BOUND[name][CLASSES[name]] for name in SOURCES}
        cls.sparsestore = {}
        cls.onedstore = {}
        cls.textstore = {}
        for name in SOURCES:
            make = cls.make[name]
            sparse = make()
            oned = make()
            text = make()
            for i in range(cls.size):
                sparse[cls.sparse[i]] = i
                oned[i] = i
                text.kvw(cls.leaf[i], i)
            cls.sparsestore[name] = sparse
            cls.onedstore[name] = oned
            cls.textstore[name] = text

    def test_T1_every_variant_holds_the_same_values(self):
        for name in SOURCES:
            for i in range(self.size):
                self.assertEqual(self.sparsestore[name][self.sparse[i]], i, name)
                self.assertEqual(self.onedstore[name][i], i, name)
                self.assertEqual(self.textstore[name].kvr(self.leaf[i]), i, name)

    def test_T2_indici_shows_the_delimiter_of_the_variant(self):
        shown = {'kv': '(3 4)', 'kv2': '[3 4]'}
        for name in SOURCES:
            self.assertEqual(self.sparsestore[name].indici()[3], shown[name], name)

    def test_T3_a_key_from_indici_addresses_the_cell(self):
        for name in SOURCES:
            store = self.sparsestore[name]
            key = store.indici()[3]
            self.assertEqual(store.kvr(key), store[self.sparse[3]], name)

    def bench_kv_sparse_read(self, timer):
        d = self.sparsestore['kv']
        keys = self.sparse
        with timer as test:
            while test.more:
                for i in test.count:
                    d[keys[i % 100]]
        return 'kv', 'sparse read d[r, c]'

    def bench_kv_sparse_write(self, timer):
        d = self.sparsestore['kv']
        keys = self.sparse
        with timer as test:
            while test.more:
                for i in test.count:
                    d[keys[i % 100]] = i
        return 'kv', 'sparse write d[r, c] = v'

    def bench_kv_oned_read(self, timer):
        d = self.onedstore['kv']
        with timer as test:
            while test.more:
                for i in test.count:
                    d[i % 100]
        return 'kv', 'one-dimensional read d[k]'

    def bench_kv_sparse_insert(self, timer):
        make = self.make['kv']
        keys = self.newkeys
        with timer as test:
            while test.more:
                d = make()
                for i in test.count:
                    d[keys[i % 2000]] = 1
        return 'kv', 'insert a new sparse key'

    def bench_kv_indici(self, timer):
        d = self.sparsestore['kv']
        with timer as test:
            while test.more:
                for i in test.count:
                    d.indici()
        return 'kv', 'indici() over 100 sparse keys'

    def bench_kv_text_read(self, timer):
        d = self.textstore['kv']
        keys = self.leaf
        with timer as test:
            while test.more:
                for i in test.count:
                    d.kvr(keys[i % 100])
        return 'kv', 'text read d.kvr(k) (control)'

    def bench_kv2_sparse_read(self, timer):
        d = self.sparsestore['kv2']
        keys = self.sparse
        with timer as test:
            while test.more:
                for i in test.count:
                    d[keys[i % 100]]
        return 'kv2', 'sparse read d[r, c]'

    def bench_kv2_sparse_write(self, timer):
        d = self.sparsestore['kv2']
        keys = self.sparse
        with timer as test:
            while test.more:
                for i in test.count:
                    d[keys[i % 100]] = i
        return 'kv2', 'sparse write d[r, c] = v'

    def bench_kv2_oned_read(self, timer):
        d = self.onedstore['kv2']
        with timer as test:
            while test.more:
                for i in test.count:
                    d[i % 100]
        return 'kv2', 'one-dimensional read d[k]'

    def bench_kv2_sparse_insert(self, timer):
        make = self.make['kv2']
        keys = self.newkeys
        with timer as test:
            while test.more:
                d = make()
                for i in test.count:
                    d[keys[i % 2000]] = 1
        return 'kv2', 'insert a new sparse key'

    def bench_kv2_indici(self, timer):
        d = self.sparsestore['kv2']
        with timer as test:
            while test.more:
                for i in test.count:
                    d.indici()
        return 'kv2', 'indici() over 100 sparse keys'

    def bench_kv2_text_read(self, timer):
        d = self.textstore['kv2']
        keys = self.leaf
        with timer as test:
            while test.more:
                for i in test.count:
                    d.kvr(keys[i % 100])
        return 'kv2', 'text read d.kvr(k) (control)'
