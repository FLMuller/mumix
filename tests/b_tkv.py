"""
b_tkv.py -- tests and benchmarks for tkv (the contract of the promoted xlw/tkv.pyx).

Carried from code.py/primary/tkv/b_tkv.py (a Python port of b_tkv.m): the 84 behaviour
tests unchanged, and the base benchmark rows converted to one op per iteration. The
variant rows and variant parity tests (tkvc, tkvc2, tkvc3, tkv1) are left out: the
variants are compared in tests/z_sandbox/b_tkvcmp.py.

Documented adaptations from MATLAB (see the tkv.pyx header):
  - read-miss via attribute returns an empty speculative node -> use .isEmpty()
  - registered fns are called with parens: R.val(), R.dbl(5)
  - structs use types.SimpleNamespace (so leaf.field chaining works by ref)
  - untyped sparse chaining d[r,c].v=.. yields a tkv node (not a MATLAB struct)
  - dropped: MATLAB-only idioms (array-grow d.arr(3)=5, numeric-dot d.([r c]),
    multi-output deal, odd/numeric handler-name registry errors)

Run from the project root:
    python tools/runbench.py tests/b_tkv.py
"""

import sys


def findtools():                      # walk up to the folder that holds tools/
    from os.path import abspath, dirname, isdir, join
    here = dirname(abspath(__file__))
    while here != dirname(here) and not isdir(join(here, 'tools')):
        here = dirname(here)
    sys.path.insert(0, join(here, 'tools'))


findtools()
from use import load
from bench import bench

SOURCES = ['tkv']                       # the module this suite proves and times
globals().update(load('tkv', into={}))  # tkv, kvr, kvw and the Tkv* error classes

from types import SimpleNamespace


class b_tkv(bench):
    BenchName    = "tkv"
    BenchVersion = "M1.0.3"
    BenchHeader  = ""
    sources      = SOURCES

    @classmethod
    def setup_fixtures(cls):
        cls.N = 100
        cls.pkeys = [f"key{i:04d}" for i in range(cls.N)]
        cls.skeys = [(i, i + 1) for i in range(cls.N)]
        cls.paths2 = ["n1." + k for k in cls.pkeys]
        cls.paths3 = ["n1.n2." + k for k in cls.pkeys]
        cls.paths4 = ["n1.n2.n3." + k for k in cls.pkeys]
        t = tkv()
        for i in range(cls.N):
            t.kvw(cls.pkeys[i], i)
            t.kvw(cls.paths2[i], i)
            t.kvw(cls.paths3[i], i)
            t.kvw(cls.paths4[i], i)
            t[cls.skeys[i][0], cls.skeys[i][1]] = i
        t.alpha1 = 99
        t.alpha.beta1 = 999
        t.alpha.beta.gamma1 = 88
        t.alpha.beta.gamma.zeta1 = 88
        t.st = SimpleNamespace(x=1)
        cls.tt = t
        cls.rfn = tkv("only", sum2=lambda d, a, b: a + b)


    # ==============================================================
    # Bench methods - one op per iteration; return (label, group).
    # ==============================================================
    def bench_read1(self, timer):
        d, p, N = self.tt, self.pkeys, self.N
        with timer as test:
            while test.more:
                for i in test.count:
                    d.kvr(p[i % N])
        return "kvr d=1", "read (tkv)"

    def bench_read4(self, timer):
        d, p, N = self.tt, self.paths4, self.N
        with timer as test:
            while test.more:
                for i in test.count:
                    d.kvr(p[i % N])
        return "kvr d=4", "read"

    def bench_dotread4(self, timer):
        d = self.tt
        with timer as test:
            while test.more:
                for _ in test.count:
                    d.alpha.beta.gamma.zeta1
        return "t.a.b.c.d", "read"

    def bench_braceTextRead(self, timer):
        d, p, N = self.tt, self.pkeys, self.N
        with timer as test:
            while test.more:
                for i in test.count:
                    d[p[i % N]]
        return 't["k"]', "read"

    def bench_braceSparseRead(self, timer):
        d, s, N = self.tt, self.skeys, self.N
        with timer as test:
            while test.more:
                for i in test.count:
                    d[s[i % N]]
        return "t[r,c]", "read"

    def bench_write1(self, timer):
        d, p, N = self.tt, self.pkeys, self.N
        with timer as test:
            while test.more:
                for i in test.count:
                    d.kvw(p[i % N], i)
        return "kvw d=1", "write"

    def bench_write4(self, timer):
        d, p, N = self.tt, self.paths4, self.N
        with timer as test:
            while test.more:
                for i in test.count:
                    d.kvw(p[i % N], i)
        return "kvw d=4", "write"

    def bench_braceSparseWrite(self, timer):
        d, s, N = self.tt, self.skeys, self.N
        with timer as test:
            while test.more:
                for i in test.count:
                    d[s[i % N]] = i
        return "t[r,c]=", "write"

    def bench_iskey(self, timer):
        d, p, N = self.tt, self.pkeys, self.N
        with timer as test:
            while test.more:
                for i in test.count:
                    d.iskey(p[i % N])
        return "iskey", "query"

    def bench_isnode(self, timer):
        d = self.tt
        with timer as test:
            while test.more:
                for _ in test.count:
                    d.isnode("n1")
        return "isnode", "query"

    def bench_regfn_kvr(self, timer):
        d = self.rfn
        with timer as test:
            while test.more:
                for _ in test.count:
                    d.kvr("sum2", 2, 3)
        return "regfn kvr", "read"

    def bench_count(self, timer):
        d = self.tt
        with timer as test:
            while test.more:
                for _ in test.count:
                    d.count()
        return "count", "enum"

    def bench_keys(self, timer):
        d = self.tt
        with timer as test:
            while test.more:
                for _ in test.count:
                    d.keys()
        return "keys", "enum"

    def bench_entries(self, timer):
        d = self.tt
        with timer as test:
            while test.more:
                for _ in test.count:
                    d.entries()
        return "entries", "enum"


    # ════════════════════════════════════════════════════════════════
    # constructor / typing
    # ════════════════════════════════════════════════════════════════
    def test_ctor_untyped_empty(self):
        d = tkv()
        self.assertEqual(d.count(), 0)
        self.assertEqual(d.numEntries(), 0)

    def test_ctor_typed_root_type(self):
        self.assertEqual(tkv(["root", "book", "page"]).type(), "root")

    def test_ctor_dup_types_untyped(self):
        self.assertEqual(tkv(["a", "a"]).type(), "")

    def test_ctor_reserved_sequence_error(self):
        with self.assertRaises(TkvBadRegistry):
            tkv("t", sequence=lambda x: x)

    def test_ctor_non_fn_handler_error(self):
        with self.assertRaises(TkvBadRegistry):
            tkv("t", h="notfn")

    def test_typed_child_type_advances(self):
        d = tkv(["root", "book", "page"])
        d.b.p.x = 1
        self.assertEqual(d.b.type(), "book")
        self.assertEqual(d.b.p.type(), "page")

    def test_typed_sequence_overflow_untyped(self):
        d = tkv(["root", "cell"])
        d.c.a.b = 9
        self.assertIsInstance(d.c.a, tkv)
        self.assertEqual(d.c.a.type(), "")
        self.assertEqual(d.c.a.b, 9)

    # ════════════════════════════════════════════════════════════════
    # attribute assign / read
    # ════════════════════════════════════════════════════════════════
    def test_da_leaf_set(self):
        d = tkv(); d.x = 42
        self.assertEqual(d.kvr("x"), 42)

    def test_da_leaf_overwrite(self):
        d = tkv(); d.x = 1; d.x = 2
        self.assertEqual(d.x, 2)

    def test_da_leaf_delete(self):
        d = tkv(); d.x = 1; d.x = None
        self.assertFalse(d.iskey("x"))

    def test_da_node_delete(self):
        d = tkv(); d.nd.x = 1; d.nd = None
        self.assertEqual(d.count(), 0)

    def test_da_value_on_node_errors(self):
        d = tkv(); d.nd.x = 1
        with self.assertRaises(TkvDuplicateName):
            d.nd = 5

    def test_da_reserved_registered_errors(self):
        R = tkv("root", fn=lambda nd: 1)
        with self.assertRaises(TkvReservedName):
            R.fn = 5

    def test_da_underscore_name_cannot_be_set(self):
        # Same rule as kv (b_kv T22): a cdef class holds no extra attributes, and an
        # instance dict would slow every lookup, so d._note = 5 raises. Either way a name
        # starting "_" never becomes a key.
        d = tkv()
        with self.assertRaises(AttributeError):
            d._note = 5
        self.assertFalse(d.iskey("_note"))
        self.assertEqual(d.numEntries(), 0)

    def test_da_autoviv_chain(self):
        d = tkv(); d.a.b.c = 9
        self.assertIsInstance(d.a, tkv)
        self.assertIsInstance(d.a.b, tkv)
        self.assertEqual(d.a.b.c, 9)

    def test_da_leaf_chain_struct_field(self):
        d = tkv(); d.st = SimpleNamespace(x=1); d.st.y = 2
        self.assertEqual(d.st.y, 2)

    def test_da_node_baton(self):
        d = tkv(); d.a.b = 1; d.a.c = 2
        self.assertEqual(d.a.b, 1)
        self.assertEqual(d.a.c, 2)

    def test_da_sibling_reuse_deep(self):
        d = tkv(); d.a.b.c = 1; d.a.b.dd = 2
        self.assertEqual(d.a.b.c, 1)
        self.assertEqual(d.a.b.dd, 2)

    # ════════════════════════════════════════════════════════════════
    # attribute read branches
    # ════════════════════════════════════════════════════════════════
    def test_dr_node_read(self):
        d = tkv(); d.nd.x = 1
        self.assertIsInstance(d.nd, tkv)

    def test_dr_leaf_read(self):
        d = tkv(); d.x = "hi"
        self.assertEqual(d.x, "hi")

    def test_dr_miss_untyped_empty(self):
        self.assertTrue(tkv().nope.isEmpty())

    def test_dr_node_chain(self):
        d = tkv(); d.a.b.c = 5
        self.assertEqual(d.a.b.c, 5)

    def test_dr_leaf_chain_array(self):
        d = tkv(); d.arr = [10, 20, 30]
        self.assertEqual(d.arr[1], 20)

    def test_dr_leaf_chain_struct(self):
        d = tkv(); d.st = SimpleNamespace(x=7)
        self.assertEqual(d.st.x, 7)

    def test_dr_chain_miss_empty(self):
        self.assertTrue(tkv().no.such.thing.isEmpty())

    # ════════════════════════════════════════════════════════════════
    # registered functions (called with parens)
    # ════════════════════════════════════════════════════════════════
    def test_rf_zero_args_dot(self):
        R = tkv("root", val=lambda nd: 42)
        self.assertEqual(R.val(), 42)

    def test_rf_one_arg_dot(self):
        R = tkv("root", dbl=lambda nd, a: a * 2)
        self.assertEqual(R.dbl(5), 10)

    def test_rf_zero_args_kvr(self):
        R = tkv("root", val=lambda nd: 42)
        self.assertEqual(kvr(R, "val"), 42)

    def test_rf_args_kvr(self):
        R = tkv("root", sum4=lambda nd, a, b, c, e: a + b + c + e)
        self.assertEqual(kvr(R, "sum4", 1, 2, 3, 4), 10)

    def test_rf_baton_on_child(self):
        R = tkv(["root", "book"], tag=lambda nd: "tag:" + nd.name())
        R.b.x = 1
        self.assertEqual(R.b.tag(), "tag:b")

    def test_rf_result_is_chained(self):
        R = tkv("root", mk=lambda nd: SimpleNamespace(y=99))
        self.assertEqual(R.mk().y, 99)

    # ════════════════════════════════════════════════════════════════
    # item access / sparse
    # ════════════════════════════════════════════════════════════════
    def test_ba_leaf_set_read(self):
        d = tkv(); d["k"] = 5
        self.assertEqual(d["k"], 5)

    def test_ba_leaf_delete(self):
        d = tkv(); d["k"] = 5; d["k"] = None
        self.assertFalse(d.iskey("k"))

    def test_ba_node_collision_guard(self):
        d = tkv(); d.nd.x = 1
        with self.assertRaises(TkvDuplicateName):
            d["nd"] = 5

    def test_br_node_fallback(self):
        d = tkv(); d.nd.x = 1
        self.assertIsInstance(d["nd"], tkv)

    def test_br_missing_empty(self):
        self.assertIsNone(tkv()["nope"])

    def test_ba_sparse_rc_roundtrip(self):
        d = tkv(); d[10, 20] = 3.14
        self.assertEqual(d[10, 20], 3.14)

    def test_ba_sparse_vector_form(self):
        d = tkv(); d[[4, 5]] = 7
        self.assertEqual(d[4, 5], 7)

    def test_ba_sparse_chained_value(self):
        d = tkv(); d["arr"] = [1, 2, 3]; d["arr"][1] = 9
        self.assertEqual(kvr(d, "arr"), [1, 9, 3])

    def test_ba_sparse_zero_allowed(self):
        d = tkv(); d[0, 1] = 5
        self.assertEqual(d[0, 1], 5)

    def test_ba_dim_mismatch_enforced(self):
        d = tkv(); d[1, 2] = 1
        with self.assertRaises(TkvSparseDimMismatch):
            d[1, 2, 3] = 2

    def test_ba_typed_sparse_is_node(self):
        A = tkv(["root", "sheet", "cell"])
        A.s[1, 2].v = "plop"
        nd = A.s[1, 2]
        self.assertIsInstance(nd, tkv)
        self.assertEqual(nd.type(), "cell")
        self.assertEqual(A.s[1, 2].v, "plop")

    def test_ba_untyped_sparse_chains_to_node(self):
        # Python adaptation: untyped sparse chaining yields a tkv node, not a struct
        d = tkv(); d[1, 2].v = 7
        self.assertIsInstance(d[1, 2], tkv)
        self.assertEqual(d[1, 2].v, 7)

    # ════════════════════════════════════════════════════════════════
    # reserved parens
    # ════════════════════════════════════════════════════════════════
    def test_rp_literal_leaf_create_errors(self):
        with self.assertRaises(TkvReservedParen):
            tkv()["(8 9)"] = 1

    def test_rp_literal_node_create_errors(self):
        with self.assertRaises(TkvReservedParen):
            tkv().node("(8 9)")

    def test_rp_literal_overwrite_keeps_sparse(self):
        d = tkv(); d[6, 9] = 1
        d[d.indici()[0]] = 42
        self.assertEqual(d[6, 9], 42)
        self.assertEqual(d.kind([6, 9]), "leaf(sparse)")

    def test_rp_newnode_raw_index_is_sparse_node(self):
        d = tkv(["root", "cell"])
        n = d.node([1, 2])
        self.assertEqual(d.kind([1, 2]), "tkv(sparse)")
        self.assertIsInstance(n, tkv)

    def test_rp_literal_read_miss_is_empty(self):
        self.assertIsNone(tkv()["(8 9 10)"])

    # ════════════════════════════════════════════════════════════════
    # node API
    # ════════════════════════════════════════════════════════════════
    def test_count_counts_nodes(self):
        d = tkv(); d.a.x = 1; d.b.y = 1; d.leaf = 1
        self.assertEqual(d.count(), 2)

    def test_names_lists_nodes(self):
        d = tkv(); d.n1.x = 1; d.n2.y = 1
        self.assertEqual(sorted(d.names()), ["n1", "n2"])

    def test_nodes_returns_handles(self):
        d = tkv(); d.nd.x = 1
        self.assertIsInstance(d.nodes()[0], tkv)

    def test_isnode_true_for_node(self):
        d = tkv(); d.nd.x = 1
        self.assertTrue(d.isnode("nd"))
        self.assertFalse(d.isnode("missing"))

    def test_isnode_sparse_node(self):
        A = tkv(["root", "cell"]); A[1, 2].v = 1
        self.assertTrue(A.isnode([1, 2]))
        self.assertEqual(A.icount(), 1)
        self.assertTrue(A.indexisnode())
        self.assertEqual(A.kind([1, 2]), "tkv(sparse)")
        self.assertEqual(A.indici(), ["(1 2)"])
        self.assertEqual(A[1, 2].v, 1)

    def test_node_creates_and_returns(self):
        d = tkv(); n = d.node("k")
        self.assertIsInstance(n, tkv)
        self.assertTrue(d.isnode("k"))

    def test_node_duplicate_idempotent(self):
        d = tkv()
        self.assertIs(d.node("k"), d.node("k"))

    def test_node_on_leaf_errors(self):
        d = tkv(); d.x = 1
        with self.assertRaises(TkvDuplicateName):
            d.node("x")

    def test_node_reserved_method_errors(self):
        with self.assertRaises(TkvReservedName):
            tkv().node("count")

    def test_hasNodes_false_then_true(self):
        d = tkv(); d.x = 1
        self.assertFalse(d.hasNodes())
        d.nd.y = 1
        self.assertTrue(d.hasNodes())

    # ════════════════════════════════════════════════════════════════
    # leaf API
    # ════════════════════════════════════════════════════════════════
    def test_keys_lists_leaves(self):
        d = tkv(); d.a = 1; d.b = 2; d.nd.x = 1
        self.assertEqual(sorted(d.keys()), ["a", "b"])

    def test_vals_lists_values(self):
        d = tkv(); d.a = 10; d.b = 20
        self.assertEqual(sorted(d.vals()), [10, 20])

    def test_numEntries_counts_leaves(self):
        d = tkv(); d.a = 1; d.b = 1; d.nd.x = 1
        self.assertEqual(d.numEntries(), 2)

    def test_iskey_true_for_leaf(self):
        d = tkv(); d.lf = 1; d.nd.x = 1
        self.assertTrue(d.iskey("lf"))
        self.assertFalse(d.iskey("nd"))

    def test_entries_returns_pairs(self):
        d = tkv(); d.x = 10
        e = d.entries()
        self.assertEqual(e, [["x", 10]])

    def test_entries_empty(self):
        self.assertEqual(tkv().entries(), [])

    # ════════════════════════════════════════════════════════════════
    # identity / lifecycle
    # ════════════════════════════════════════════════════════════════
    def test_parent_of_child(self):
        d = tkv(); d.a.b = 1
        self.assertIs(d.a.parent(), d)

    def test_name_of_child(self):
        d = tkv(); d.a.b = 1
        self.assertEqual(d.a.name(), "a")

    def test_type_untyped_empty(self):
        self.assertEqual(tkv().type(), "")

    def test_clear_resets_all(self):
        d = tkv(); d.a = 1; d.nd.x = 2; d.clear()
        self.assertEqual(d.count(), 0)

    def test_remove_leaf(self):
        d = tkv(); d.x = 1; d.remove("x")
        self.assertFalse(d.iskey("x"))

    def test_remove_node(self):
        d = tkv(); d.nd.x = 1; d.remove("nd")
        self.assertFalse(d.isnode("nd"))

    def test_string_is_scalar(self):
        self.assertIsInstance(tkv().string(), str)

    def test_repr_runs(self):
        d = tkv(); d.x = 1; d.nd.y = 2
        self.assertIsInstance(repr(d), str)

    # ════════════════════════════════════════════════════════════════
    # kvr / kvw paths depth 1..4
    # ════════════════════════════════════════════════════════════════
    def test_path_depth1(self):
        d = tkv(); kvw(d, "a", 1)
        self.assertEqual(kvr(d, "a"), 1)

    def test_path_depth4(self):
        d = tkv(); kvw(d, "a.b.c.d", 4)
        self.assertEqual(kvr(d, "a.b.c.d"), 4)

    def test_path_missing_empty(self):
        self.assertIsNone(kvr(tkv(), "no.such.path"))

    def test_path_delete(self):
        d = tkv(); kvw(d, "a.b", 3); kvw(d, "a.b", None)
        self.assertIsNone(kvr(d, "a.b"))

    def test_path_node_fallback(self):
        d = tkv(); kvw(d, "a.b.c", 1)
        self.assertIsInstance(kvr(d, "a.b"), tkv)

    def test_path_leaf_on_node_errors(self):
        d = tkv(); kvw(d, "a.b.c", 1)
        with self.assertRaises(TkvDuplicateName):
            kvw(d, "a.b", 5)

    def test_kvr_numeric_key(self):
        d = tkv(); d[3, 7] = 9
        self.assertEqual(kvr(d, [3, 7]), 9)

    def test_kvw_numeric_key(self):
        d = tkv(); kvw(d, [3, 7], 9)
        self.assertEqual(d[3, 7], 9)

    def test_cov_kvr_node_continuation(self):
        d = tkv(); d.a.x = 5
        self.assertEqual(kvr(d, "a", "x"), 5)

    def test_cov_kvw_through_leaf_errors(self):
        d = tkv(); d.lf = 1
        with self.assertRaises(TkvDuplicateName):
            kvw(d, "lf.x", 2)

    def test_cov_regfn_paren_chain(self):
        R = tkv("t", mk=lambda d, a: SimpleNamespace(y=a))
        self.assertEqual(R.mk(5).y, 5)

    def test_cov_tombstone_probe(self):
        d = tkv()
        for i in range(40): kvw(d, f"k{i:03d}", i)
        for i in range(20): d.remove(f"k{i:03d}")
        for i in range(20): kvw(d, f"m{i:03d}", i)
        self.assertEqual(kvr(d, "m010"), 10)
        self.assertEqual(kvr(d, "k030"), 30)

    def test_cov_resize_correct(self):
        d = tkv()
        for i in range(600): kvw(d, f"s{i:04d}", i)
        self.assertEqual(kvr(d, "s0300"), 300)
        self.assertEqual(d.numEntries(), 600)


if __name__ == "__main__":
    import unittest
    unittest.main()
