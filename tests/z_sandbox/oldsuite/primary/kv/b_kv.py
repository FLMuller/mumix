"""
b_kv.py — Tests + benchmark for kv (Python port of b_kv.m v2.1).

Tests run first; benchmarks run in tearDownClass, skipped on failure.
Baseline = Python dict (the C-level hash kv is built on).

Adaptations from MATLAB:
  d.numEntries        -> d.numEntries()        (method, not Dependent prop)
  kvr(d,k) == []      -> is None
  d.arr(3)            -> d.arr[2]              (Python 0-based, native index)
  struct('x',7)       -> {'x': 7}             (read d['st']['x'])
  d{r,c} / d{"k"}     -> d[r, c] / d["k"]
  delete []           -> = None

Run:
    python -m unittest tests.b_kv
    python primary/runbench.py b_kv "msg"
"""

from use import load                     # run from the project root (cwd on path)
load('primary', '+subs')                 # binds bench, kv, kv1, kvr/kvw, Kv*, kvc/kvc2/kvc3 (kv now in primary/kv)

import time
from types import SimpleNamespace


class b_kv(bench):
    BenchName    = "kv"
    BenchVersion = "M1.16.2"
    BenchHeader  = "test all"
    Nx           = 20000
    NRep         = 10

    @classmethod
    def setup_fixtures(cls):
        cls.N = 100
        cls.kkeys = [f"key{i:04d}" for i in range(cls.N)]
        cls.skeys = [(i, i + 1) for i in range(cls.N)]
        cls.dd = kv()
        cls.dict = {}
        cls.ss = SimpleNamespace()                 # struct baseline (no machinery)
        for i in range(cls.N):
            cls.dd.kvw(cls.kkeys[i], float(i))
            cls.dd[cls.skeys[i][0], cls.skeys[i][1]] = float(i)   # sparse leaves
            cls.dict[cls.kkeys[i]] = float(i)
            setattr(cls.ss, cls.kkeys[i], float(i))
        cls.dd.arr = [10, 20, 30, 40, 50]          # chain-into-array target
        cls.dd.st  = {"x": 7}                       # chain-into-struct target

        cls.cc = kvc() if kvc else None            # parallel Cython kvc fixture
        cls.c2 = kvc2() if kvc2 else None          # parallel Cython kvc2 fixture
        cls.c3 = kvc3() if kvc3 else None          # parallel Cython kvc3 fixture
        cls.k1 = kv1()                             # faithful DJB2 (was kv)
        cls.ee = kv()                              # pristine kv for enum (dd gets churned by mutate)
        for store in (cls.cc, cls.c2, cls.c3, cls.k1, cls.ee):
            if store is not None:
                for i in range(cls.N):
                    store.kvw(cls.kkeys[i], float(i))
                    store[cls.skeys[i][0], cls.skeys[i][1]] = float(i)

    # ════════════════════════════════════════════════════════════════
    # Bench methods — full b_kv.m matrix. One op per iteration, loop Nx.
    # ════════════════════════════════════════════════════════════════

    # ── kv method form ────────────────────────────────────────────────
    def bench_kvr(self, Nx):
        d, keys, N = self.dd, self.kkeys, self.N
        t0 = time.perf_counter()
        for i in range(Nx): d.kvr(keys[i % N])
        return time.perf_counter() - t0, "d.kvr(k)", "kv method"

    def bench_kvw(self, Nx):
        d, keys, N = self.dd, self.kkeys, self.N
        t0 = time.perf_counter()
        for i in range(Nx): d.kvw(keys[i % N], i)
        return time.perf_counter() - t0, "d.kvw(k,v)", "kv method"

    def bench_iskey(self, Nx):
        d, keys, N = self.dd, self.kkeys, self.N
        t0 = time.perf_counter()
        for i in range(Nx): d.iskey(keys[i % N])
        return time.perf_counter() - t0, "d.iskey(k)", "kv method"

    # ── kvc (Cython build) — same algorithm, C-level probe ────────────
    def bench_c_kvr(self, Nx):
        d, keys, N = self.cc, self.kkeys, self.N
        if d is None: return 0.0, "kvc (not built)", "kvc cython"
        t0 = time.perf_counter()
        for i in range(Nx): d.kvr(keys[i % N])
        return time.perf_counter() - t0, "c.kvr(k)", "kvc cython"

    def bench_c_kvw(self, Nx):
        d, keys, N = self.cc, self.kkeys, self.N
        if d is None: return 0.0, "kvc (not built)", "kvc cython"
        t0 = time.perf_counter()
        for i in range(Nx): d.kvw(keys[i % N], i)
        return time.perf_counter() - t0, "c.kvw(k,v)", "kvc cython"

    def bench_c_sparse(self, Nx):
        d, s, N = self.cc, self.skeys, self.N
        if d is None: return 0.0, "kvc (not built)", "kvc cython"
        t0 = time.perf_counter()
        for i in range(Nx): d[s[i % N]]
        return time.perf_counter() - t0, "c[r,c]", "kvc cython"

    # ── kvc2 (Cython, bytes + hash() + memcmp) ────────────────────────
    def bench_c2_kvr(self, Nx):
        d, keys, N = self.c2, self.kkeys, self.N
        if d is None: return 0.0, "kvc2 (not built)", "kvc2 cython"
        t0 = time.perf_counter()
        for i in range(Nx): d.kvr(keys[i % N])
        return time.perf_counter() - t0, "c2.kvr(k)", "kvc2 cython"

    def bench_c2_kvw(self, Nx):
        d, keys, N = self.c2, self.kkeys, self.N
        if d is None: return 0.0, "kvc2 (not built)", "kvc2 cython"
        t0 = time.perf_counter()
        for i in range(Nx): d.kvw(keys[i % N], i)
        return time.perf_counter() - t0, "c2.kvw(k,v)", "kvc2 cython"

    def bench_c2_sparse(self, Nx):
        d, s, N = self.c2, self.skeys, self.N
        if d is None: return 0.0, "kvc2 (not built)", "kvc2 cython"
        t0 = time.perf_counter()
        for i in range(Nx): d[s[i % N]]
        return time.perf_counter() - t0, "c2[r,c]", "kvc2 cython"

    # ── kvc3 (kvc2 + single slot-returning probe, no _fslot) ──────────
    def bench_c3_kvr(self, Nx):
        d, keys, N = self.c3, self.kkeys, self.N
        if d is None: return 0.0, "kvc3 (not built)", "kvc3 cython"
        t0 = time.perf_counter()
        for i in range(Nx): d.kvr(keys[i % N])
        return time.perf_counter() - t0, "c3.kvr(k)", "kvc3 cython"

    def bench_c3_kvw(self, Nx):
        d, keys, N = self.c3, self.kkeys, self.N
        if d is None: return 0.0, "kvc3 (not built)", "kvc3 cython"
        t0 = time.perf_counter()
        for i in range(Nx): d.kvw(keys[i % N], i)
        return time.perf_counter() - t0, "c3.kvw(k,v)", "kvc3 cython"

    def bench_c3_sparse(self, Nx):
        d, s, N = self.c3, self.skeys, self.N
        if d is None: return 0.0, "kvc3 (not built)", "kvc3 cython"
        t0 = time.perf_counter()
        for i in range(Nx): d[s[i % N]]
        return time.perf_counter() - t0, "c3[r,c]", "kvc3 cython"

    # ── kv1 (faithful DJB2, pure-Python; was the original kv) ──
    def bench_k1_kvr(self, Nx):
        d, keys, N = self.k1, self.kkeys, self.N
        t0 = time.perf_counter()
        for i in range(Nx): d.kvr(keys[i % N])
        return time.perf_counter() - t0, "k1.kvr(k)", "kv1 faithful"

    def bench_k1_kvw(self, Nx):
        d, keys, N = self.k1, self.kkeys, self.N
        t0 = time.perf_counter()
        for i in range(Nx): d.kvw(keys[i % N], i)
        return time.perf_counter() - t0, "k1.kvw(k,v)", "kv1 faithful"

    def bench_k1_sparse(self, Nx):
        d, s, N = self.k1, self.skeys, self.N
        t0 = time.perf_counter()
        for i in range(Nx): d[s[i % N]]
        return time.perf_counter() - t0, "k1[r,c]", "kv1 faithful"

    # ── kv function form (module kvr/kvw) ─────────────────────────────
    def bench_fnKvr(self, Nx):
        d, keys, N = self.dd, self.kkeys, self.N
        t0 = time.perf_counter()
        for i in range(Nx): kvr(d, keys[i % N])
        return time.perf_counter() - t0, "kvr(d,k)", "kv function"

    def bench_fnKvw(self, Nx):
        d, keys, N = self.dd, self.kkeys, self.N
        t0 = time.perf_counter()
        for i in range(Nx): kvw(d, keys[i % N], i)
        return time.perf_counter() - t0, "kvw(d,k,v)", "kv function"

    # ── attribute (dot) syntax ────────────────────────────────────────
    def bench_dotRead(self, Nx):
        d, keys, N = self.dd, self.kkeys, self.N
        t0 = time.perf_counter()
        for i in range(Nx): getattr(d, keys[i % N])
        return time.perf_counter() - t0, "d.key", "attribute"

    def bench_dotWrite(self, Nx):
        d, keys, N = self.dd, self.kkeys, self.N
        t0 = time.perf_counter()
        for i in range(Nx): setattr(d, keys[i % N], i)
        return time.perf_counter() - t0, "d.key=v", "attribute"

    # ── item (brace) syntax: text + sparse ────────────────────────────
    def bench_braceTextRead(self, Nx):
        d, keys, N = self.dd, self.kkeys, self.N
        t0 = time.perf_counter()
        for i in range(Nx): d[keys[i % N]]
        return time.perf_counter() - t0, "d[k]", "item"

    def bench_braceTextWrite(self, Nx):
        d, keys, N = self.dd, self.kkeys, self.N
        t0 = time.perf_counter()
        for i in range(Nx): d[keys[i % N]] = i
        return time.perf_counter() - t0, "d[k]=v", "item"

    def bench_braceSparseRead(self, Nx):
        d, s, N = self.dd, self.skeys, self.N
        t0 = time.perf_counter()
        for i in range(Nx): d[s[i % N]]
        return time.perf_counter() - t0, "d[r,c]", "sparse"

    def bench_braceSparseWrite(self, Nx):
        d, s, N = self.dd, self.skeys, self.N
        t0 = time.perf_counter()
        for i in range(Nx): d[s[i % N]] = i
        return time.perf_counter() - t0, "d[r,c]=v", "sparse"

    # ── chained reads ─────────────────────────────────────────────────
    def bench_chainArrayRead(self, Nx):
        d = self.dd
        t0 = time.perf_counter()
        for _ in range(Nx): d.arr[2]
        return time.perf_counter() - t0, "d.arr[2]", "chained"

    def bench_chainStructRead(self, Nx):
        d = self.dd
        t0 = time.perf_counter()
        for _ in range(Nx): d.st["x"]
        return time.perf_counter() - t0, "d.st['x']", "chained"

    # ── mutate: remove + re-add (net-neutral on the fixture) ──────────
    def bench_removeReadd(self, Nx):
        d, keys, N = self.dd, self.kkeys, self.N
        t0 = time.perf_counter()
        for i in range(Nx):
            k = keys[i % N]; d.remove(k); d.kvw(k, i)
        return time.perf_counter() - t0, "remove+kvw", "mutate"

    # ── dict baseline ─────────────────────────────────────────────────
    def bench_dictGet(self, Nx):
        d, keys, N = self.dict, self.kkeys, self.N
        t0 = time.perf_counter()
        for i in range(Nx): d.get(keys[i % N])
        return time.perf_counter() - t0, "dict.get(k)", "dict baseline"

    def bench_dictSet(self, Nx):
        d, keys, N = self.dict, self.kkeys, self.N
        t0 = time.perf_counter()
        for i in range(Nx): d[keys[i % N]] = i
        return time.perf_counter() - t0, "dict[k]=v", "dict baseline"

    def bench_dictIn(self, Nx):
        d, keys, N = self.dict, self.kkeys, self.N
        t0 = time.perf_counter()
        for i in range(Nx): keys[i % N] in d
        return time.perf_counter() - t0, "k in dict", "dict baseline"

    # ── struct baseline (SimpleNamespace = the no-machinery floor) ────
    def bench_structGet(self, Nx):
        s, keys, N = self.ss, self.kkeys, self.N
        t0 = time.perf_counter()
        for i in range(Nx): getattr(s, keys[i % N])
        return time.perf_counter() - t0, "s.key", "struct baseline"

    def bench_structSet(self, Nx):
        s, keys, N = self.ss, self.kkeys, self.N
        t0 = time.perf_counter()
        for i in range(Nx): setattr(s, keys[i % N], i)
        return time.perf_counter() - t0, "s.key=v", "struct baseline"

    def bench_structHas(self, Nx):
        s, keys, N = self.ss, self.kkeys, self.N
        t0 = time.perf_counter()
        for i in range(Nx): hasattr(s, keys[i % N])
        return time.perf_counter() - t0, "hasattr(s,k)", "struct baseline"

    # ── enumeration (whole-store scans) ───────────────────────────────
    def bench_numEntries(self, Nx):
        d = self.ee                                # pristine (dd is churned by mutate)
        t0 = time.perf_counter()
        for _ in range(Nx): d.numEntries()
        return time.perf_counter() - t0, "d.numEntries", "enum"

    def bench_keys(self, Nx):
        d = self.ee
        t0 = time.perf_counter()
        for _ in range(Nx): d.keys()
        return time.perf_counter() - t0, "d.keys", "enum"

    def bench_vals(self, Nx):
        d = self.ee
        t0 = time.perf_counter()
        for _ in range(Nx): d.vals()
        return time.perf_counter() - t0, "d.vals", "enum"

    def bench_indici(self, Nx):
        d = self.ee
        t0 = time.perf_counter()
        for _ in range(Nx): d.indici()
        return time.perf_counter() - t0, "d.indici", "enum"

    def bench_icount(self, Nx):
        d = self.ee
        t0 = time.perf_counter()
        for _ in range(Nx): d.icount()
        return time.perf_counter() - t0, "d.icount", "enum"

    # ── enum on kv1 (faithful) — does option-B's bytes store enumerate slower? ──
    def bench_k1_numEntries(self, Nx):
        d = self.k1
        t0 = time.perf_counter()
        for _ in range(Nx): d.numEntries()
        return time.perf_counter() - t0, "d.numEntries", "enum (kv1)"

    def bench_k1_keys(self, Nx):
        d = self.k1
        t0 = time.perf_counter()
        for _ in range(Nx): d.keys()
        return time.perf_counter() - t0, "d.keys", "enum (kv1)"

    def bench_k1_vals(self, Nx):
        d = self.k1
        t0 = time.perf_counter()
        for _ in range(Nx): d.vals()
        return time.perf_counter() - t0, "d.vals", "enum (kv1)"

    def bench_k1_indici(self, Nx):
        d = self.k1
        t0 = time.perf_counter()
        for _ in range(Nx): d.indici()
        return time.perf_counter() - t0, "d.indici", "enum (kv1)"

    def bench_k1_icount(self, Nx):
        d = self.k1
        t0 = time.perf_counter()
        for _ in range(Nx): d.icount()
        return time.perf_counter() - t0, "d.icount", "enum (kv1)"

    # ── scalar queries ────────────────────────────────────────────────
    def bench_idim(self, Nx):
        d = self.dd
        t0 = time.perf_counter()
        for _ in range(Nx): d.idim()
        return time.perf_counter() - t0, "d.idim", "query"

    def bench_kind(self, Nx):
        d, keys, N = self.dd, self.kkeys, self.N
        t0 = time.perf_counter()
        for i in range(Nx): d.kind(keys[i % N])
        return time.perf_counter() - t0, "d.kind(k)", "query"

    def bench_isEmpty(self, Nx):
        d = self.dd
        t0 = time.perf_counter()
        for _ in range(Nx): d.isEmpty()
        return time.perf_counter() - t0, "d.isEmpty", "query"

    # ════════════════════════════════════════════════════════════════
    # constructor
    # ════════════════════════════════════════════════════════════════
    def test_ctor_empty_numEntries_zero(self):
        self.assertEqual(kv().numEntries(), 0)

    def test_ctor_keys_empty(self):
        self.assertEqual(kv().keys(), [])

    def test_ctor_two_instances_independent(self):
        a, b = kv(), kv()
        a.kvw("x", 1)
        self.assertFalse(b.iskey("x"))

    def test_kvc_parity(self):
        if kvc is None:
            self.skipTest("kvc not built (run: use.load('primary'))")
        a, c = kv(), kvc()
        for o in (a, c):
            o.x = 5; o["a key"] = 42; o[2, 3] = 99; o["g", 2] = 7
            o.kvw("k", 1); o.kvw("k", 9); o["d"] = 1; o.remove("d")
        self.assertEqual(c.kvr("x"), a.kvr("x"))
        self.assertEqual(c["a key"], a["a key"])
        self.assertEqual(c[2, 3], a[2, 3])
        self.assertEqual(c.numEntries(), a.numEntries())
        self.assertEqual(c.icount(), a.icount())
        self.assertEqual(sorted(c.keys()), sorted(a.keys()))
        self.assertEqual(c.kind([2, 3]), a.kind([2, 3]))
        with self.assertRaises(Exception):
            c["(8 9)"] = 1                 # reserved-paren create errors, like kv

    def test_kvc3_parity(self):
        if kvc3 is None:
            self.skipTest("kvc3 not built (run: use.load('primary'))")
        a, c = kv(), kvc3()
        for o in (a, c):
            o.x = 5; o["a key"] = 42; o[2, 3] = 99; o["g", 2] = 7
            o.kvw("k", 1); o.kvw("k", 9); o["d"] = 1; o.remove("d")
        self.assertEqual(c.kvr("x"), a.kvr("x"))
        self.assertEqual(c["a key"], a["a key"])
        self.assertEqual(c[2, 3], a[2, 3])
        self.assertEqual(c.numEntries(), a.numEntries())
        self.assertEqual(c.icount(), a.icount())
        self.assertEqual(sorted(c.keys()), sorted(a.keys()))
        self.assertEqual(c.kind([2, 3]), a.kind([2, 3]))
        with self.assertRaises(Exception):
            c["(8 9)"] = 1

    def test_ctor_reference_semantics(self):
        a = kv(); a.kvw("x", 1)
        b = a                        # handle: same map
        b.kvw("y", 2)
        self.assertEqual(a.kvr("y"), 2)

    # ════════════════════════════════════════════════════════════════
    # kvr / kvw
    # ════════════════════════════════════════════════════════════════
    def test_kvw_stores_and_kvr_reads(self):
        d = kv(); d.kvw("alpha", 42)
        self.assertEqual(d.kvr("alpha"), 42)

    def test_kvr_missing_returns_none(self):
        self.assertIsNone(kv().kvr("absent"))

    def test_kvw_overwrite(self):
        d = kv(); d.kvw("k", 1); d.kvw("k", 99)
        self.assertEqual(d.kvr("k"), 99)
        self.assertEqual(d.numEntries(), 1)

    def test_kvw_multiple_keys(self):
        d = kv(); d.kvw("a", 1); d.kvw("b", 2); d.kvw("c", 3)
        self.assertEqual([d.kvr(k) for k in "abc"], [1, 2, 3])

    def test_module_kvr_kvw(self):
        d = kv(); kvw(d, "msg", "hello")
        self.assertEqual(kvr(d, "msg"), "hello")

    def test_kvw_heterogeneous_values(self):
        d = kv()
        d.kvw("scalar", 7); d.kvw("arr", [1, 2, 3])
        d.kvw("str", "hello"); d.kvw("st", {"x": 1})
        self.assertEqual(d.kvr("scalar"), 7)
        self.assertEqual(d.kvr("arr"), [1, 2, 3])
        self.assertEqual(d.kvr("str"), "hello")
        self.assertEqual(d.kvr("st")["x"], 1)

    # ════════════════════════════════════════════════════════════════
    # attribute (dot) read / write
    # ════════════════════════════════════════════════════════════════
    def test_dot_read_returns_value(self):
        d = kv(); d.kvw("alpha", 42)
        self.assertEqual(d.alpha, 42)

    def test_dot_read_missing_returns_none(self):
        self.assertIsNone(kv().absent)

    def test_dot_write_stores_value(self):
        d = kv(); d.mykey = 42
        self.assertEqual(d.kvr("mykey"), 42)

    def test_dot_write_overwrite(self):
        d = kv(); d.k = 1; d.k = 99
        self.assertEqual(d.kvr("k"), 99)
        self.assertEqual(d.numEntries(), 1)

    def test_dot_multiple_keys(self):
        d = kv(); d.p = 10; d.q = 20; d.r = 30
        self.assertEqual((d.p, d.q, d.r), (10, 20, 30))

    # ════════════════════════════════════════════════════════════════
    # methods: iskey, remove, isEmpty
    # ════════════════════════════════════════════════════════════════
    def test_iskey_works(self):
        d = kv(); d.kvw("z", 9)
        self.assertTrue(d.iskey("z"))
        self.assertFalse(d.iskey("missing"))

    def test_remove_works(self):
        d = kv(); d.kvw("r", 5); d.remove("r")
        self.assertFalse(d.iskey("r"))

    def test_remove_decrements_numEntries(self):
        d = kv(); d.kvw("a", 1); d.kvw("b", 2); d.remove("a")
        self.assertEqual(d.numEntries(), 1)

    def test_remove_absent_noop(self):
        d = kv(); d.kvw("k", 1); d.remove("nope")
        self.assertEqual(d.numEntries(), 1)

    def test_remove_then_reinsert(self):
        d = kv(); d.kvw("k", 1); d.remove("k"); d.kvw("k", 99)
        self.assertEqual(d.kvr("k"), 99)

    def test_isEmpty_works(self):
        d = kv()
        self.assertTrue(d.isEmpty())
        d.kvw("k", 1)
        self.assertFalse(d.isEmpty())

    def test_delete_via_none(self):
        d = kv(); d.kvw("k", 1); d["k"] = None
        self.assertFalse(d.iskey("k"))

    # ════════════════════════════════════════════════════════════════
    # property path
    # ════════════════════════════════════════════════════════════════
    def test_keys_correct(self):
        d = kv(); d.kvw("x", 1); d.kvw("y", 2)
        self.assertEqual(sorted(d.keys()), ["x", "y"])

    def test_keys_excludes_removed(self):
        d = kv(); d.kvw("keep", 1); d.kvw("drop", 2); d.remove("drop")
        self.assertNotIn("drop", d.keys())
        self.assertIn("keep", d.keys())

    def test_vals_correct(self):
        d = kv(); d.kvw("p", 42)
        self.assertEqual(d.vals(), [42])

    def test_vals_length_matches_numEntries(self):
        d = kv(); d.kvw("a", 10); d.kvw("b", 20); d.kvw("c", 30)
        self.assertEqual(len(d.vals()), 3)

    def test_numEntries_zero_after_all_removed(self):
        d = kv(); d.kvw("a", 1); d.kvw("b", 2); d.remove("a"); d.remove("b")
        self.assertEqual(d.numEntries(), 0)

    # ════════════════════════════════════════════════════════════════
    # chained indexing (native Python on the returned object)
    # ════════════════════════════════════════════════════════════════
    def test_indexed_read_returns_element(self):
        d = kv(); d.kvw("arr", [10, 20, 30, 40, 50])
        self.assertEqual(d.arr[2], 30)

    def test_indexed_write_modifies_element(self):
        d = kv(); d.kvw("arr", [1, 2, 3, 4, 5])
        d.arr[4] = 77                               # mutate stored list by ref
        self.assertEqual(d.kvr("arr"), [1, 2, 3, 4, 77])

    def test_struct_field_read(self):
        d = kv(); d.kvw("st", {"x": 99})
        self.assertEqual(d.st["x"], 99)

    def test_stored_fn_called(self):
        d = kv(); d.kvw("fn", lambda x: x * 2)
        self.assertEqual(d.fn(5), 10)

    def test_cell_key_index(self):
        d = kv(); d.kvw("c", ["a", "b", "c"])
        self.assertEqual(d.c[1], "b")

    # ════════════════════════════════════════════════════════════════
    # resize / rehash (dict handles automatically)
    # ════════════════════════════════════════════════════════════════
    def test_resize_roundtrip_100(self):
        d = kv()
        for i in range(1, 101):
            d.kvw(f"k{i}", i * 2)
        self.assertTrue(all(d.kvr(f"k{i}") == i * 2 for i in range(1, 101)))

    def test_resize_numEntries_correct(self):
        d = kv()
        for i in range(200):
            d.kvw(f"g{i}", i)
        self.assertEqual(d.numEntries(), 200)

    def test_resize_after_delete(self):
        d = kv()
        for i in range(1, 51):
            d.kvw(f"k{i}", i)
        for i in range(1, 51, 2):
            d.remove(f"k{i}")
        self.assertTrue(all(d.kvr(f"k{i}") == i for i in range(2, 51, 2)))

    # ════════════════════════════════════════════════════════════════
    # items and sparse slots
    # ════════════════════════════════════════════════════════════════
    def test_item_string_roundtrip(self):
        d = kv(); d["k"] = 5
        self.assertEqual(d["k"], 5)

    def test_item_string_delete(self):
        d = kv(); d["k"] = 5; d["k"] = None
        self.assertFalse(d.iskey("k"))

    def test_item_missing_returns_none(self):
        self.assertIsNone(kv()["nope"])

    def test_item_reaches_method_named_keys(self):
        d = kv(); d["iskey"] = 42
        self.assertEqual(d["iskey"], 42)
        self.assertTrue(d.iskey("iskey"))           # method still works

    def test_sparse_rc_roundtrip(self):
        d = kv(); d[10, 20] = 3.14
        self.assertEqual(d[10, 20], 3.14)

    def test_sparse_vector_form_equivalent(self):
        d = kv(); d[[4, 5]] = 7
        self.assertEqual(d[4, 5], 7)

    def test_sparse_3d_vector_roundtrip(self):
        d = kv(); d[[1, 2, 3]] = 99
        self.assertEqual(d[1, 2, 3], 99)

    def test_pair_text_number(self):
        d = kv(); d["group", 2] = 7
        self.assertEqual(d["group", 2], 7)          # tuple   -> '(group 2)'
        self.assertEqual(d[["group", "2"]], 7)      # list    -> '(group 2)'
        self.assertEqual(kvr(d, "(group 2)"), 7)    # canonical text
        self.assertIsNone(d["group 2"])             # space-string -> literal miss

    def test_multi_subscript_is_sparse(self):
        d = kv(); d["a", "b", "c"] = 5
        self.assertEqual(kvr(d, "(a b c)"), 5)
        self.assertEqual(d["a", "b", "c"], 5)
        self.assertEqual(d.idim(), 3)

    def test_sparse_absent_returns_none(self):
        self.assertIsNone(kv()[99, 99])

    def test_dim_mismatch_error(self):
        d = kv(); d[1, 2] = 1
        with self.assertRaises(KvSparseDimMismatch):
            d[1, 2, 3] = 2

    def test_reserved_paren_create_errors(self):
        with self.assertRaises(KvReservedParen):
            kv()["(8 9)"] = 1

    def test_reserved_paren_overwrite_ok(self):
        d = kv(); d[6, 9] = 1
        ix = d.indici()[0]                          # "(6 9)"
        d[ix] = 42                                  # literal-paren overwrite
        self.assertEqual(d[6, 9], 42)
        self.assertEqual(d.kind([6, 9]), 202)       # still sparse

    def test_literal_paren_read_miss(self):
        self.assertIsNone(kv()["(8 9 10)"])

    def test_sdims_zero_then_two(self):
        d = kv()
        self.assertEqual(d.idim(), 0)
        d[3, 7] = 1
        self.assertEqual(d.idim(), 2)

    def test_kvw_numeric_key_is_sparse(self):
        d = kv(); kvw(d, [1, 2], 5)
        self.assertEqual(d[1, 2], 5)
        self.assertEqual(d.idim(), 2)

    def test_kvr_numeric_key_is_sparse(self):
        d = kv(); d[3, 4] = 8
        self.assertEqual(kvr(d, [3, 4]), 8)

    def test_kvw_numeric_dim_mismatch(self):
        d = kv(); kvw(d, [1, 2], 1)
        with self.assertRaises(KvSparseDimMismatch):
            kvw(d, [1, 2, 3], 2)

    def test_chained_assign_into_value(self):
        d = kv(); d["arr"] = [1, 2, 3]
        d["arr"][1] = 9                             # chained mutate by ref
        self.assertEqual(d.kvr("arr"), [1, 9, 3])

    # ════════════════════════════════════════════════════════════════
    # enumeration / kind coverage
    # ════════════════════════════════════════════════════════════════
    def test_indici_lists_sparse_keys(self):
        d = kv(); d[3, 7] = 1; d[4, 8] = 2
        self.assertEqual(sorted(d.indici()), ["(3 7)", "(4 8)"])

    def test_indici_empty_no_sparse(self):
        d = kv(); d.leaf = 1
        self.assertEqual(d.indici(), [])

    def test_icount_counts_sparse(self):
        d = kv(); d[3, 7] = 1; d[4, 8] = 2; d.leaf = 3
        self.assertEqual(d.icount(), 2)

    def test_kind_flags(self):
        d = kv(); d.lf = 1; d[3, 7] = 2
        self.assertEqual(d.kind("lf"), 201)
        self.assertEqual(d.kind([3, 7]), 202)
        self.assertEqual(d.kind("nope"), 0)

    def test_single_numeric_is_1d_sparse(self):
        d = kv(); d[5] = 7
        self.assertEqual(d[5], 7)
        self.assertEqual(d.idim(), 1)

    def test_char_comma_key_is_leaf(self):
        d = kv(); d["1,2"] = 5
        self.assertEqual(d["1,2"], 5)
        self.assertEqual(d.idim(), 0)               # plain leaf, not sparse


if __name__ == "__main__":
    import unittest
    unittest.main()
