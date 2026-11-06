"""
b_kv.py - tests + benchmark for kv, the contract of xlw/kv.pyx.   (kv only, no comparisons)
Carried from code.py/sandbox/tests/b_kv.py: the benchmark rows converted to the timer form
(one op per iteration, no Nx or NRep). A sparse key is the text "[5 3]" (it was "(5 3)"),
and it is text starting with "[" that is reserved; T93-T95 are new.

WHAT kv IS
  A small hash map: open addressing, perturbed probing, tombstone deletes. Keys are
  stored as bytes and hashed with Python's own hash(). Two kinds of key share one table:
    leaf    "name"        any text; kind 201;  d.name  d["name"]  d.kvr("name")
    sparse  (r, c, ...)   numbers or text, stored as the text "[r c]"; kind 202.
                          Every sparse key in one store has the same dimension.
  Text that starts with "[" cannot be created as a leaf (it would look sparse).
  A value can be anything; None means "delete". Entries sit in insertion order in
  parallel arrays, so keys(), vals() and indici() are one contiguous scan.

HOW THIS SUITE IS LAID OUT
  Benches   one row per key action a caller pays for, grouped by syntax:
            method, function, attribute, item, sparse, chained, mutate, enum, query.
  Tests     T01-T08 constructor, clear, chaining      T09-T15 kvr / kvw
            T16-T23 dot syntax                        T24-T34 iskey, remove, delete
            T35-T43 keys, vals, ordering              T44-T48 chained indexing
            T49-T54 growth, resize, tombstones        T55-T85 items, sparse keys, errors
            T86-T92 enumeration and kind
  The tests run FIRST. The benches run LAST and are skipped if any test failed.

Run from the project root:
    python tools/runbench.py tests/b_kv.py           # tests, then benchmarks
"""

import sys


def findtools():
    # Walk up from this file to the build root (the folder holding tools/) and put
    # tools/ (use.py, bench.py, runbench.py) on sys.path. Defined BEFORE it is called.
    from os.path import abspath, dirname, isdir, join as pjoin
    s = dirname(abspath(__file__))
    while s != dirname(s) and not isdir(pjoin(s, "tools")):
        s = dirname(s)
    sys.path.insert(0, pjoin(s, "tools"))


findtools()
from use import load


from bench import bench
SOURCES = ['kv']                      # the module this suite proves and times
load('kv')  # kv, kvr, kvw, KvError, KvSparseDimMismatch, KvReservedBracket


class b_kv(bench):
    # -- identity and tuning ------------------------------------------------
    BenchName    = "kv"                   # runbench overwrites from the class name
    BenchVersion = "M1.0.20"               # set ONCE; runbench auto-ticks the 3rd field
    BenchHeader  = ""                     # runbench fills this from the CLI message
    sources      = SOURCES
    NKeys        = 100                    # leaf keys and sparse keys in each bench store

    @classmethod
    def setup_fixtures(cls):
        # dd: the busy store the benches read, write and churn.
        # ee: the same contents, never mutated, so the enumeration timings stay clean.
        cls.leafkeys = [f"key{i:04d}" for i in range(cls.NKeys)]
        cls.sparsekeys = [(i, i + 1) for i in range(cls.NKeys)]
        cls.dd = kv()
        cls.ee = kv()
        for store in (cls.dd, cls.ee):
            for i in range(cls.NKeys):
                store.kvw(cls.leafkeys[i], float(i))
                store[cls.sparsekeys[i]] = float(i)
            store.arr = [10, 20, 30, 40, 50]  # target for the chained list read
            store.st = {"x": 7}               # target for the chained dict read

    # ====================================================================
    # Bench - one op per iteration; return (label, group). The harness chooses the count.
    # ====================================================================

    # -- method form -------------------------------------------------------
    def bench_kvr(self, timer):
        d = self.dd
        keys = self.leafkeys
        n = self.NKeys
        with timer as test:
            while test.more:
                for i in test.count:
                    d.kvr(keys[i % n])
        return "d.kvr(k)", "method"

    def bench_kvw(self, timer):
        d = self.dd
        keys = self.leafkeys
        n = self.NKeys
        with timer as test:
            while test.more:
                for i in test.count:
                    d.kvw(keys[i % n], i)
        return "d.kvw(k,v)", "method"

    def bench_iskey(self, timer):
        d = self.dd
        keys = self.leafkeys
        n = self.NKeys
        with timer as test:
            while test.more:
                for i in test.count:
                    d.iskey(keys[i % n])
        return "d.iskey(k)", "method"

    # -- function form (module-level kvr / kvw) ------------------------------
    def bench_fnKvr(self, timer):
        d = self.dd
        keys = self.leafkeys
        n = self.NKeys
        with timer as test:
            while test.more:
                for i in test.count:
                    kvr(d, keys[i % n])
        return "kvr(d,k)", "function"

    def bench_fnKvw(self, timer):
        d = self.dd
        keys = self.leafkeys
        n = self.NKeys
        with timer as test:
            while test.more:
                for i in test.count:
                    kvw(d, keys[i % n], i)
        return "kvw(d,k,v)", "function"

    # -- attribute (dot) syntax -----------------------------------------------
    def bench_dotRead(self, timer):
        d = self.dd
        keys = self.leafkeys
        n = self.NKeys
        with timer as test:
            while test.more:
                for i in test.count:
                    getattr(d, keys[i % n])
        return "d.key", "attribute"

    def bench_dotWrite(self, timer):
        d = self.dd
        keys = self.leafkeys
        n = self.NKeys
        with timer as test:
            while test.more:
                for i in test.count:
                    setattr(d, keys[i % n], i)
        return "d.key=v", "attribute"

    # -- item (square-bracket) syntax on text keys ------------------------------
    def bench_itemRead(self, timer):
        d = self.dd
        keys = self.leafkeys
        n = self.NKeys
        with timer as test:
            while test.more:
                for i in test.count:
                    d[keys[i % n]]
        return "d[k]", "item"

    def bench_itemWrite(self, timer):
        d = self.dd
        keys = self.leafkeys
        n = self.NKeys
        with timer as test:
            while test.more:
                for i in test.count:
                    d[keys[i % n]] = i
        return "d[k]=v", "item"

    # -- sparse keys ------------------------------------------------------------
    def bench_sparseRead(self, timer):
        d = self.dd
        keys = self.sparsekeys
        n = self.NKeys
        with timer as test:
            while test.more:
                for i in test.count:
                    d[keys[i % n]]
        return "d[r,c]", "sparse"

    def bench_sparseWrite(self, timer):
        d = self.dd
        keys = self.sparsekeys
        n = self.NKeys
        with timer as test:
            while test.more:
                for i in test.count:
                    d[keys[i % n]] = i
        return "d[r,c]=v", "sparse"

    # -- chained reads (kv lookup, then native indexing on the stored value) -------
    def bench_chainListRead(self, timer):
        d = self.dd
        with timer as test:
            while test.more:
                for _ in test.count:
                    d.arr[2]
        return "d.arr[2]", "chained"

    def bench_chainDictRead(self, timer):
        d = self.dd
        with timer as test:
            while test.more:
                for _ in test.count:
                    d.st["x"]
        return "d.st['x']", "chained"

    # -- mutate: remove then re-add (net-neutral on the fixture) -----------------
    def bench_removeReadd(self, timer):
        d = self.dd
        keys = self.leafkeys
        n = self.NKeys
        with timer as test:
            while test.more:
                for i in test.count:
                    k = keys[i % n]
                    d.remove(k)
                    d.kvw(k, i)
        return "remove+kvw", "mutate"

    # -- enumeration: whole-store scans of the untouched store ------------------
    def bench_numEntries(self, timer):
        d = self.ee
        with timer as test:
            while test.more:
                for _ in test.count:
                    d.numEntries()
        return "d.numEntries", "enum"

    def bench_keys(self, timer):
        d = self.ee
        with timer as test:
            while test.more:
                for _ in test.count:
                    d.keys()
        return "d.keys", "enum"

    def bench_vals(self, timer):
        d = self.ee
        with timer as test:
            while test.more:
                for _ in test.count:
                    d.vals()
        return "d.vals", "enum"

    def bench_indici(self, timer):
        d = self.ee
        with timer as test:
            while test.more:
                for _ in test.count:
                    d.indici()
        return "d.indici", "enum"

    def bench_at(self, timer):
        d = self.ee
        with timer as test:
            while test.more:
                for i in test.count:
                    d.at(i % 200)
        return "d.at(i)", "query"

    def bench_icount(self, timer):
        d = self.ee
        with timer as test:
            while test.more:
                for _ in test.count:
                    d.icount()
        return "d.icount", "enum"

    # -- scalar queries -----------------------------------------------------------
    def bench_idim(self, timer):
        d = self.dd
        with timer as test:
            while test.more:
                for _ in test.count:
                    d.idim()
        return "d.idim", "query"

    def bench_kind(self, timer):
        d = self.dd
        keys = self.leafkeys
        n = self.NKeys
        with timer as test:
            while test.more:
                for i in test.count:
                    d.kind(keys[i % n])
        return "d.kind(k)", "query"

    def bench_isEmpty(self, timer):
        d = self.dd
        with timer as test:
            while test.more:
                for _ in test.count:
                    d.isEmpty()
        return "d.isEmpty", "query"

    # ====================================================================
    # T01-T08  constructor, clear, chaining
    # ====================================================================
    def test_T01_ctor_empty_numEntries_zero(self):
        self.assertEqual(kv().numEntries(), 0)

    def test_T02_ctor_enumerations_empty(self):
        d = kv()
        self.assertEqual(d.keys(), [])
        self.assertEqual(d.vals(), [])
        self.assertEqual(d.indici(), [])
        self.assertEqual(d.icount(), 0)
        self.assertEqual(d.idim(), 0)
        self.assertEqual(len(d), 0)
        self.assertTrue(d.isEmpty())

    def test_T03_ctor_two_instances_independent(self):
        a = kv()
        b = kv()
        a.kvw("x", 1)
        self.assertFalse(b.iskey("x"))

    def test_T04_ctor_reference_semantics(self):
        a = kv()
        a.kvw("x", 1)
        b = a                                # a handle: both names are the same map
        b.kvw("y", 2)
        self.assertEqual(a.kvr("y"), 2)

    def test_T05_clear_empties_the_store(self):
        d = kv()
        d.kvw("a", 1)
        d[3, 4] = 2
        d.clear()
        self.assertTrue(d.isEmpty())
        self.assertEqual(d.keys(), [])
        self.assertEqual(d.indici(), [])
        self.assertIsNone(d.kvr("a"))

    def test_T06_clear_resets_sparse_dimension(self):
        d = kv()
        d[1, 2] = 1
        d.clear()
        self.assertEqual(d.idim(), 0)
        d[1, 2, 3] = 5                       # a different dimension is allowed again
        self.assertEqual(d.idim(), 3)

    def test_T07_clear_returns_self_and_store_is_reusable(self):
        d = kv()
        for i in range(100):                 # let the tables grow before clearing
            d.kvw(f"k{i}", i)
        self.assertIs(d.clear(), d)
        d.kvw("again", 7)
        self.assertEqual(d.kvr("again"), 7)
        self.assertEqual(d.numEntries(), 1)

    def test_T08_kvw_returns_self_for_chaining(self):
        d = kv()
        self.assertIs(d.kvw("a", 1), d)
        d.kvw("b", 2).kvw("c", 3)
        self.assertEqual(d.numEntries(), 3)

    # ====================================================================
    # T09-T15  kvr / kvw
    # ====================================================================
    def test_T09_kvw_stores_and_kvr_reads(self):
        d = kv()
        d.kvw("alpha", 42)
        self.assertEqual(d.kvr("alpha"), 42)

    def test_T10_kvr_missing_returns_none(self):
        self.assertIsNone(kv().kvr("absent"))

    def test_T11_kvw_overwrite(self):
        d = kv()
        d.kvw("k", 1)
        d.kvw("k", 99)
        self.assertEqual(d.kvr("k"), 99)
        self.assertEqual(d.numEntries(), 1)

    def test_T12_kvw_multiple_keys(self):
        d = kv()
        d.kvw("a", 1)
        d.kvw("b", 2)
        d.kvw("c", 3)
        self.assertEqual([d.kvr(k) for k in "abc"], [1, 2, 3])

    def test_T13_module_kvr_kvw(self):
        d = kv()
        kvw(d, "msg", "hello")
        self.assertEqual(kvr(d, "msg"), "hello")

    def test_T14_kvw_heterogeneous_values(self):
        d = kv()
        d.kvw("scalar", 7)
        d.kvw("arr", [1, 2, 3])
        d.kvw("str", "hello")
        d.kvw("st", {"x": 1})
        self.assertEqual(d.kvr("scalar"), 7)
        self.assertEqual(d.kvr("arr"), [1, 2, 3])
        self.assertEqual(d.kvr("str"), "hello")
        self.assertEqual(d.kvr("st")["x"], 1)

    def test_T15_falsy_values_are_stored_not_missing(self):
        d = kv()
        d.kvw("zero", 0)
        d.kvw("empty", "")
        d.kvw("no", False)
        self.assertEqual(d.kvr("zero"), 0)
        self.assertEqual(d.kvr("empty"), "")
        self.assertIs(d.kvr("no"), False)
        self.assertEqual(d.numEntries(), 3)  # only None means "absent" or "delete"

    # ====================================================================
    # T16-T23  attribute (dot) read and write
    # ====================================================================
    def test_T16_dot_read_returns_value(self):
        d = kv()
        d.kvw("alpha", 42)
        self.assertEqual(d.alpha, 42)

    def test_T17_dot_read_missing_returns_none(self):
        self.assertIsNone(kv().absent)

    def test_T18_dot_write_stores_value(self):
        d = kv()
        d.mykey = 42
        self.assertEqual(d.kvr("mykey"), 42)

    def test_T19_dot_write_overwrite(self):
        d = kv()
        d.k = 1
        d.k = 99
        self.assertEqual(d.kvr("k"), 99)
        self.assertEqual(d.numEntries(), 1)

    def test_T20_dot_multiple_keys(self):
        d = kv()
        d.p = 10
        d.q = 20
        d.r = 30
        self.assertEqual((d.p, d.q, d.r), (10, 20, 30))

    def test_T21_dot_write_none_deletes(self):
        d = kv()
        d.k = 1
        d.k = None
        self.assertFalse(d.iskey("k"))

    def test_T22_underscore_name_cannot_be_set(self):
        # The pure-Python kv stored d._note as an ordinary attribute. This kv is a cdef
        # class with no instance dict (adding one slows every attribute lookup), so it
        # refuses. Either way a name starting "_" never becomes a key.
        d = kv()
        with self.assertRaises(AttributeError):
            d._note = 5
        self.assertFalse(d.iskey("_note"))
        self.assertEqual(d.numEntries(), 0)

    def test_T23_underscore_miss_raises_attribute_error(self):
        with self.assertRaises(AttributeError):
            kv()._nothing

    # ====================================================================
    # T24-T34  iskey, remove, isEmpty, delete by None
    # ====================================================================
    def test_T24_iskey_works(self):
        d = kv()
        d.kvw("z", 9)
        self.assertTrue(d.iskey("z"))
        self.assertFalse(d.iskey("missing"))

    def test_T25_remove_works(self):
        d = kv()
        d.kvw("r", 5)
        d.remove("r")
        self.assertFalse(d.iskey("r"))

    def test_T26_remove_decrements_numEntries(self):
        d = kv()
        d.kvw("a", 1)
        d.kvw("b", 2)
        d.remove("a")
        self.assertEqual(d.numEntries(), 1)

    def test_T27_remove_absent_noop(self):
        d = kv()
        d.kvw("k", 1)
        d.remove("nope")
        self.assertEqual(d.numEntries(), 1)

    def test_T28_remove_then_reinsert(self):
        d = kv()
        d.kvw("k", 1)
        d.remove("k")
        d.kvw("k", 99)
        self.assertEqual(d.kvr("k"), 99)

    def test_T29_isEmpty_works(self):
        d = kv()
        self.assertTrue(d.isEmpty())
        d.kvw("k", 1)
        self.assertFalse(d.isEmpty())

    def test_T30_delete_via_none(self):
        d = kv()
        d.kvw("k", 1)
        d["k"] = None
        self.assertFalse(d.iskey("k"))

    def test_T31_none_on_absent_key_creates_nothing(self):
        d = kv()
        d["ghost"] = None
        self.assertFalse(d.iskey("ghost"))
        self.assertTrue(d.isEmpty())

    def test_T32_remove_sparse_key(self):
        d = kv()
        d[1, 2] = 5
        d.remove([1, 2])
        self.assertFalse(d.iskey([1, 2]))
        self.assertEqual(d.kind([1, 2]), 0)
        self.assertEqual(d.icount(), 0)

    def test_T33_sparse_delete_via_none(self):
        d = kv()
        d[3, 4] = 1
        d[3, 4] = None
        self.assertIsNone(d[3, 4])
        self.assertEqual(d.icount(), 0)
        self.assertEqual(len(d), 0)

    def test_T34_removed_key_is_not_found_by_dot_or_item(self):
        d = kv()
        d.kvw("gone", 1)
        d.remove("gone")
        self.assertIsNone(d.gone)
        self.assertIsNone(d["gone"])

    # ====================================================================
    # T35-T43  keys, vals, numEntries, ordering
    # ====================================================================
    def test_T35_keys_correct(self):
        d = kv()
        d.kvw("x", 1)
        d.kvw("y", 2)
        self.assertEqual(sorted(d.keys()), ["x", "y"])

    def test_T36_keys_excludes_removed(self):
        d = kv()
        d.kvw("keep", 1)
        d.kvw("drop", 2)
        d.remove("drop")
        self.assertNotIn("drop", d.keys())
        self.assertIn("keep", d.keys())

    def test_T37_vals_correct(self):
        d = kv()
        d.kvw("p", 42)
        self.assertEqual(d.vals(), [42])

    def test_T38_vals_length_matches_numEntries(self):
        d = kv()
        d.kvw("a", 10)
        d.kvw("b", 20)
        d.kvw("c", 30)
        self.assertEqual(len(d.vals()), 3)

    def test_T39_numEntries_zero_after_all_removed(self):
        d = kv()
        d.kvw("a", 1)
        d.kvw("b", 2)
        d.remove("a")
        d.remove("b")
        self.assertEqual(d.numEntries(), 0)

    def test_T40_keys_and_vals_exclude_sparse(self):
        d = kv()
        d.kvw("a", 1)
        d.kvw("b", 2)
        d[1, 2] = 9
        self.assertEqual(d.keys(), ["a", "b"])
        self.assertEqual(d.vals(), [1, 2])

    def test_T41_enumeration_is_in_insertion_order(self):
        d = kv()
        for k in ("z", "a", "m"):
            d.kvw(k, ord(k))
        self.assertEqual(d.keys(), ["z", "a", "m"])
        self.assertEqual(d.vals(), [ord("z"), ord("a"), ord("m")])

    def test_T42_order_survives_removal_and_resize(self):
        d = kv()
        names = [f"k{i:03d}" for i in range(100)]    # 100 entries force a table resize
        for name in names:
            d.kvw(name, 0)
        d.remove("k005")
        names.remove("k005")
        self.assertEqual(d.keys(), names)
        d.kvw("k005", 1)                     # a re-inserted key joins the end
        names.append("k005")
        self.assertEqual(d.keys(), names)

    def test_T43_keys_are_text_including_unicode(self):
        d = kv()
        d.kvw("plain", 1)
        d.kvw("caf\u00e9", 2)
        d.kvw("\u65e5\u672c", 3)
        self.assertEqual(d.keys(), ["plain", "caf\u00e9", "\u65e5\u672c"])
        self.assertTrue(all(isinstance(k, str) for k in d.keys()))
        self.assertEqual(d.kvr("caf\u00e9"), 2)
        self.assertEqual(d["\u65e5\u672c"], 3)

    # ====================================================================
    # T44-T48  chained indexing (native Python on the stored value)
    # ====================================================================
    def test_T44_indexed_read_returns_element(self):
        d = kv()
        d.kvw("arr", [10, 20, 30, 40, 50])
        self.assertEqual(d.arr[2], 30)

    def test_T45_indexed_write_modifies_element(self):
        d = kv()
        d.kvw("arr", [1, 2, 3, 4, 5])
        d.arr[4] = 77                        # mutates the stored list by reference
        self.assertEqual(d.kvr("arr"), [1, 2, 3, 4, 77])

    def test_T46_dict_field_read(self):
        d = kv()
        d.kvw("st", {"x": 99})
        self.assertEqual(d.st["x"], 99)

    def test_T47_stored_function_called(self):
        d = kv()
        d.kvw("fn", lambda x: x * 2)
        self.assertEqual(d.fn(5), 10)

    def test_T48_list_of_text_index(self):
        d = kv()
        d.kvw("c", ["a", "b", "c"])
        self.assertEqual(d.c[1], "b")

    # ====================================================================
    # T49-T54  growth, resize, tombstones
    # ====================================================================
    def test_T49_resize_roundtrip_100(self):
        d = kv()
        for i in range(1, 101):
            d.kvw(f"k{i}", i * 2)
        self.assertTrue(all(d.kvr(f"k{i}") == i * 2 for i in range(1, 101)))

    def test_T50_resize_numEntries_correct(self):
        d = kv()
        for i in range(200):
            d.kvw(f"g{i}", i)
        self.assertEqual(d.numEntries(), 200)

    def test_T51_resize_after_delete(self):
        d = kv()
        for i in range(1, 51):
            d.kvw(f"k{i}", i)
        for i in range(1, 51, 2):
            d.remove(f"k{i}")
        self.assertTrue(all(d.kvr(f"k{i}") == i for i in range(2, 51, 2)))

    def test_T52_growth_boundaries(self):
        # 32 entries fill the first buffer, the 33rd grows it, the 43rd resizes the table.
        for count in (1, 31, 32, 33, 42, 43, 44, 100):
            with self.subTest(count=count):
                d = kv()
                for i in range(count):
                    d.kvw(f"k{i}", i)
                got = [d.kvr(f"k{i}") for i in range(count)]
                self.assertEqual(d.numEntries(), count)
                self.assertEqual(got, list(range(count)))

    def test_T53_tombstone_churn_keeps_values_correct(self):
        d = kv()
        for i in range(10):
            d.kvw(f"k{i}", i)
        for rep in range(500):
            d.remove("k3")
            d.kvw("k3", rep)
        others = [i for i in range(10) if i != 3]
        self.assertEqual(d.kvr("k3"), 499)
        self.assertEqual(d.numEntries(), 10)
        self.assertEqual([d.kvr(f"k{i}") for i in others], others)

    def test_T54_resize_keeps_leaves_and_sparse(self):
        d = kv()
        for i in range(60):
            d.kvw(f"leaf{i}", i)
            d[i, i + 1] = i * 10
        self.assertEqual(d.numEntries(), 60)
        self.assertEqual(d.icount(), 60)
        self.assertTrue(all(d.kvr(f"leaf{i}") == i for i in range(60)))
        self.assertTrue(all(d[i, i + 1] == i * 10 for i in range(60)))

    # ====================================================================
    # T55-T85  items, sparse keys, key forms, errors
    # ====================================================================
    def test_T55_item_string_roundtrip(self):
        d = kv()
        d["k"] = 5
        self.assertEqual(d["k"], 5)

    def test_T56_item_string_delete(self):
        d = kv()
        d["k"] = 5
        d["k"] = None
        self.assertFalse(d.iskey("k"))

    def test_T57_item_missing_returns_none(self):
        self.assertIsNone(kv()["nope"])

    def test_T58_item_reaches_method_named_key(self):
        d = kv()
        d["iskey"] = 42
        self.assertEqual(d["iskey"], 42)
        self.assertTrue(d.iskey("iskey"))    # the method still works

    def test_T59_sparse_rc_roundtrip(self):
        d = kv()
        d[10, 20] = 3.14
        self.assertEqual(d[10, 20], 3.14)

    def test_T60_sparse_vector_form_equivalent(self):
        d = kv()
        d[[4, 5]] = 7
        self.assertEqual(d[4, 5], 7)

    def test_T61_sparse_3d_vector_roundtrip(self):
        d = kv()
        d[[1, 2, 3]] = 99
        self.assertEqual(d[1, 2, 3], 99)

    def test_T62_pair_text_number(self):
        d = kv()
        d["group", 2] = 7
        self.assertEqual(d["group", 2], 7)          # tuple -> "[group 2]"
        self.assertEqual(d[["group", "2"]], 7)      # list  -> "[group 2]"
        self.assertEqual(kvr(d, "[group 2]"), 7)    # the canonical text itself
        self.assertIsNone(d["group 2"])             # a space-string is a different key

    def test_T63_multi_subscript_is_sparse(self):
        d = kv()
        d["a", "b", "c"] = 5
        self.assertEqual(kvr(d, "[a b c]"), 5)
        self.assertEqual(d["a", "b", "c"], 5)
        self.assertEqual(d.idim(), 3)

    def test_T64_sparse_absent_returns_none(self):
        self.assertIsNone(kv()[99, 99])

    def test_T65_dim_mismatch_error(self):
        d = kv()
        d[1, 2] = 1
        with self.assertRaises(KvSparseDimMismatch):
            d[1, 2, 3] = 2

    def test_T66_reserved_bracket_create_errors(self):
        with self.assertRaises(KvReservedBracket):
            kv()["[8 9]"] = 1

    def test_T67_reserved_bracket_overwrite_ok(self):
        d = kv()
        d[6, 9] = 1
        ix = d.indici()[0]                          # "[6 9]"
        d[ix] = 42                                  # a literal-bracket overwrite
        self.assertEqual(d[6, 9], 42)
        self.assertEqual(d.kind([6, 9]), 202)       # still sparse

    def test_T68_literal_bracket_read_miss(self):
        self.assertIsNone(kv()["[8 9 10]"])

    def test_T69_idim_zero_then_two(self):
        d = kv()
        self.assertEqual(d.idim(), 0)
        d[3, 7] = 1
        self.assertEqual(d.idim(), 2)

    def test_T70_kvw_numeric_key_is_sparse(self):
        d = kv()
        kvw(d, [1, 2], 5)
        self.assertEqual(d[1, 2], 5)
        self.assertEqual(d.idim(), 2)

    def test_T71_kvr_numeric_key_is_sparse(self):
        d = kv()
        d[3, 4] = 8
        self.assertEqual(kvr(d, [3, 4]), 8)

    def test_T72_kvw_numeric_dim_mismatch(self):
        d = kv()
        kvw(d, [1, 2], 1)
        with self.assertRaises(KvSparseDimMismatch):
            kvw(d, [1, 2, 3], 2)

    def test_T73_chained_assign_into_value(self):
        d = kv()
        d["arr"] = [1, 2, 3]
        d["arr"][1] = 9                             # mutates the stored list by reference
        self.assertEqual(d.kvr("arr"), [1, 9, 3])

    def test_T74_dim_mismatch_names_both_dims_and_changes_nothing(self):
        d = kv()
        d[1, 2] = 1
        with self.assertRaises(KvSparseDimMismatch) as caught:
            d[1, 2, 3] = 2
        self.assertIn("2-D", str(caught.exception))
        self.assertIn("3-D", str(caught.exception))
        self.assertEqual(d.idim(), 2)
        self.assertEqual(len(d), 1)

    def test_T75_errors_share_the_kv_base_class(self):
        self.assertTrue(issubclass(KvSparseDimMismatch, KvError))
        self.assertTrue(issubclass(KvReservedBracket, KvError))
        with self.assertRaises(KvError):
            kv()["[1 2]"] = 1

    def test_T76_numbers_share_one_canonical_form(self):
        d = kv()
        d[2.0] = "two"                              # 2.0 and 2 both become "[2]"
        self.assertEqual(d[2], "two")
        self.assertEqual(d.indici(), ["[2]"])
        d[2.5] = "half"
        self.assertEqual(sorted(d.indici()), ["[2.5]", "[2]"])      # "." sorts before "]"

    def test_T77_text_part_with_space_is_quoted(self):
        d = kv()
        d["a b", 2] = 5
        self.assertEqual(d.indici(), ["['a b' 2]"])
        self.assertEqual(d["a b", 2], 5)
        self.assertEqual(d.idim(), 2)

    def test_T78_single_element_list_forms(self):
        text = kv()
        text[["name"]] = 1                          # one text item is just a leaf key
        self.assertEqual(text["name"], 1)
        self.assertEqual(text.idim(), 0)
        nested = kv()
        nested[[[4, 5]]] = 2                        # one nested list is unwrapped
        self.assertEqual(nested[4, 5], 2)
        number = kv()
        number[[6]] = 3                             # one number is a 1-D sparse key
        self.assertEqual(number[6], 3)
        self.assertEqual(number.idim(), 1)

    def test_T79_bool_key_is_a_text_leaf(self):
        d = kv()
        d[True] = 1
        self.assertEqual(d["True"], 1)
        self.assertEqual(d.idim(), 0)
        self.assertEqual(d.kind(False), 0)

    def test_T80_digit_text_is_a_leaf_not_a_sparse_key(self):
        d = kv()
        d["5"] = 1
        self.assertEqual(d.idim(), 0)
        self.assertEqual(d["5"], 1)
        self.assertIsNone(d[5])                     # the number 5 is the key "[5]"

    def test_T81_in_operator_matches_iskey(self):
        d = kv()
        d.kvw("a", 1)
        d[1, 2] = 2
        self.assertIn("a", d)
        self.assertIn((1, 2), d)
        self.assertIn([1, 2], d)
        self.assertNotIn("b", d)
        self.assertNotIn((9, 9), d)

    def test_T82_del_removes_leaf_and_sparse_keys(self):
        d = kv()
        d.kvw("a", 1)
        d[1, 2] = 2
        del d["a"]
        del d[1, 2]
        self.assertTrue(d.isEmpty())

    def test_T83_len_counts_leaf_and_sparse_entries(self):
        d = kv()
        d.kvw("a", 1)
        d[1, 2] = 2
        self.assertEqual(len(d), 2)
        self.assertEqual(d.numEntries(), 1)         # numEntries counts leaves only
        d.remove("a")
        self.assertEqual(len(d), 1)

    def test_T84_insert_takes_key_parts_then_value(self):
        d = kv()
        self.assertIs(d.insert("name", 5), d)
        d.insert("g", 2, 7)                         # the last argument is the value
        self.assertEqual(d.kvr("name"), 5)
        self.assertEqual(d["g", 2], 7)
        self.assertEqual(d.idim(), 2)

    def test_T85_repr_lists_leaves_then_sparse(self):
        d = kv()
        self.assertEqual(repr(d), "{}")
        d.kvw("a", 1)
        d.kvw("b", [1, [2, 3]])
        self.assertEqual(repr(d), "{a:1 b:[1,[2,3]]}")
        d[3, 4] = 5
        self.assertEqual(repr(d), "{a:1 b:[1,[2,3]] [[3 4]:5]}")

    # ====================================================================
    # T86-T92  enumeration and kind
    # ====================================================================
    def test_T86_indici_lists_sparse_keys(self):
        d = kv()
        d[3, 7] = 1
        d[4, 8] = 2
        self.assertEqual(sorted(d.indici()), ["[3 7]", "[4 8]"])

    def test_T87_indici_empty_no_sparse(self):
        d = kv()
        d.leaf = 1
        self.assertEqual(d.indici(), [])

    def test_T88_icount_counts_sparse(self):
        d = kv()
        d[3, 7] = 1
        d[4, 8] = 2
        d.leaf = 3
        self.assertEqual(d.icount(), 2)

    def test_T89_kind_flags(self):
        d = kv()
        d.lf = 1
        d[3, 7] = 2
        self.assertEqual(d.kind("lf"), 201)
        self.assertEqual(d.kind([3, 7]), 202)
        self.assertEqual(d.kind("nope"), 0)

    def test_T90_single_numeric_is_1d_sparse(self):
        d = kv()
        d[5] = 7
        self.assertEqual(d[5], 7)
        self.assertEqual(d.idim(), 1)

    def test_T91_char_comma_key_is_leaf(self):
        d = kv()
        d["1,2"] = 5
        self.assertEqual(d["1,2"], 5)
        self.assertEqual(d.idim(), 0)               # a plain leaf, not sparse

    def test_T92_indici_excludes_removed(self):
        d = kv()
        d[3, 7] = 1
        d[4, 8] = 2
        d.remove([3, 7])
        self.assertEqual(d.indici(), ["[4 8]"])
        self.assertEqual(d.icount(), 1)


    # ---- brackets are the sparse form, parentheses are ordinary text ---------------
    def test_T93_parenthesised_text_is_an_ordinary_leaf(self):
        d = kv()
        for text in ("(paren)", "(5 3)", "(", ")", "(a b"):
            d[text] = text
        for text in ("(paren)", "(5 3)", "(", ")", "(a b"):
            self.assertEqual(d[text], text)
            self.assertEqual(d.kind(text), 201)
        self.assertEqual(d.idim(), 0)

    def test_T94_a_new_bracketed_text_key_is_refused_whatever_its_content(self):
        for text in ("[paren]", "[5 3]", "[", "[A] in A"):
            with self.assertRaises(KvReservedBracket):
                kv()[text] = 1

    def test_T95_a_key_from_indici_addresses_the_cell(self):
        d = kv()
        d[5, 3] = 7
        d[8, 1] = 4
        keys = d.indici()
        self.assertEqual(keys, ["[5 3]", "[8 1]"])
        self.assertEqual([d[key] for key in keys], [7, 4])
        self.assertEqual([d.kvr(key) for key in keys], [7, 4])
        d[keys[0]] = 70
        self.assertEqual(d[5, 3], 70)
        self.assertEqual(repr(d), "{ [[5 3]:70 [8 1]:4]}")         # no leaves: the empty part, then the list


    # ---- position access: at(), the pin, and the churn limit ---------------------------------
    def test_T96_at_numbers_the_entries_in_write_order(self):
        d = kv()
        texts = ["b", "a", "(c)", "y", "text"]
        for number, text in enumerate(texts):
            d.kvw(text, number)
        for number, text in enumerate(texts):
            self.assertEqual(d.at(number), text)
            self.assertEqual(d.at(d.kvr(text)), text)

    def test_T97_at_outside_the_entries_raises_index_error(self):
        d = kv()
        d.x = 1
        for idx in (-1, 1, 99):
            with self.assertRaises(IndexError):
                d.at(idx)

    def test_T98_a_removed_entry_has_no_key_and_its_neighbours_stay(self):
        d = kv()
        for text in ("a", "b", "c"):
            d.kvw(text, 1)
        d.at(0)                                     # pin
        d.remove("b")
        with self.assertRaises(IndexError):
            d.at(1)
        self.assertEqual((d.at(0), d.at(2)), ("a", "c"))

    def test_T99_leaves_and_sparse_keys_share_one_numbering_shown_as_written(self):
        d = kv()
        d.name = "x"
        d[5, 3] = 7
        d.other = 1
        self.assertEqual([d.at(i) for i in range(3)], ["name", "[5 3]", "other"])

    def test_T100_a_store_of_unique_texts_is_a_numbered_list(self):
        d = kv()
        texts = [f"text {i}" for i in range(300)] + ["(paren)", "micro \u00b5"]
        for text in texts:
            d.kvw(text, len(d))                     # the position is the value
        for number, text in enumerate(texts):
            self.assertEqual(d.kvr(text), number)
            self.assertEqual(d.at(number), text)

    def test_T101_an_unpinned_store_renumbers_on_a_resize(self):
        d = kv()
        for i in range(40):
            d.kvw(f"k{i}", i)
        d.remove("k0")
        for i in range(40, 100):                    # growth and resizes: the gap is dropped
            d.kvw(f"k{i}", i)
        self.assertEqual(d.at(0), "k1")             # k1 moved down into position 0

    def test_T102_a_pinned_store_keeps_every_position_across_resizes(self):
        d = kv()
        for i in range(40):
            d.kvw(f"k{i}", i)
        self.assertEqual(d.at(0), "k0")             # this pins the store
        d.remove("k0")
        for i in range(40, 100):
            d.kvw(f"k{i}", i)
        with self.assertRaises(IndexError):
            d.at(0)                                 # the gap stayed
        self.assertEqual([d.at(i) for i in (1, 39, 40, 99)], ["k1", "k39", "k40", "k99"])
        self.assertEqual(d.kvr("k99"), 99)
        self.assertEqual(len(d.keys()), 99)
        self.assertEqual(d.keys()[0], "k1")         # keys() skips the dead slot

    def test_T103_excessive_churn_on_a_pinned_store_is_refused_with_the_advice(self):
        d = kv()
        for i in range(10):
            d.kvw(f"k{i}", i)
        d.at(0)
        cycles = 0
        with self.assertRaises(KvPositionOverflow) as caught:
            while cycles < 5000:
                d.remove("k3")
                d.kvw("k3", cycles)
                cycles += 1
        self.assertIn("excessive churn, dont use kv.at when frequently deleting keys",
                      str(caught.exception))
        self.assertGreater(cycles, 600)             # 640 dead slots of 64 bytes pass 10 x 4096
        self.assertLess(cycles, 700)
        self.assertEqual(len(d), 9)                 # k3 was removed and not written again
        self.assertEqual(d.kvr("k4"), 4)

    def test_T104_both_limits_must_hold(self):
        a = kv()                                    # a high ratio but few dead slots
        for i in range(10):
            a.kvw(f"k{i}", i)
        a.at(0)
        for cycle in range(300):
            a.remove("k3")
            a.kvw("k3", cycle)
        self.assertEqual(a.kvr("k3"), 299)
        b = kv()                                    # many dead slots but a low ratio
        for i in range(2000):
            b.kvw(f"k{i}", i)
        b.at(0)
        for i in range(700):
            b.remove(f"k{i}")
        b.kvw("again", 1)                           # 700 dead (44.8 KB) but 2000 < 10 x 1300
        self.assertEqual(b.kvr("again"), 1)

    def test_T105_an_unpinned_store_never_raises_and_clear_unpins(self):
        d = kv()
        for i in range(10):
            d.kvw(f"k{i}", i)
        for cycle in range(2000):
            d.remove("k3")
            d.kvw("k3", cycle)
        self.assertEqual(d.kvr("k3"), 1999)
        d.at(0)
        d.clear()
        for i in range(10):
            d.kvw(f"k{i}", i)
        for cycle in range(2000):
            d.remove("k3")
            d.kvw("k3", cycle)
        self.assertEqual(d.kvr("k3"), 1999)

    # ---- byte keys -------------------------------------------------------------------------
    def test_T106_a_bytes_key_and_the_same_str_key_are_one_key(self):
        d = kv()
        d.kvw(b"abc", 1)
        self.assertEqual(d.kvr("abc"), 1)
        d.kvw("abc", 2)
        self.assertEqual(d.kvr(b"abc"), 2)
        self.assertEqual(len(d.keys()), 1)

    def test_T107_a_bytes_key_comes_back_as_a_str(self):
        d = kv()
        d.kvw("café".encode("utf-8"), 7)
        self.assertEqual(d.keys(), ["café"])
        self.assertEqual(d.at(0), "café")
        self.assertIs(type(d.at(0)), str)
        self.assertEqual(d.kvr("café"), 7)

    def test_T108_iskey_remove_and_kind_take_bytes(self):
        d = kv()
        d.kvw(b"k", 1)
        self.assertTrue(d.iskey(b"k"))
        self.assertEqual(d.kind(b"k"), d.kind("k"))
        d.remove(b"k")
        self.assertFalse(d.iskey("k"))

    def test_T109_a_bytes_key_is_never_sparse_and_a_new_bracket_one_is_refused(self):
        d = kv()
        d.kvw(b"x", 1)
        d.kvw([2, 3], 9)                            # the sparse dimension is still free
        self.assertEqual(d.indici(), ["[2 3]"])
        with self.assertRaises(KvReservedBracket):
            d.kvw(b"[5 3]", 1)
        self.assertEqual(d.kvr(b"[2 3]"), 9)        # an existing sparse key is addressed

    def test_T110_the_empty_bytes_key_is_the_empty_str_key(self):
        d = kv()
        d.kvw(b"", 4)
        self.assertEqual(d.kvr(""), 4)


if __name__ == "__main__":
    import os
    from runbench import runbench
    name = os.path.splitext(os.path.basename(__file__))[0]   # "b_kv"
    msg  = sys.argv[1] if len(sys.argv) > 1 else "no changes provided"
    runbench(name, msg)
