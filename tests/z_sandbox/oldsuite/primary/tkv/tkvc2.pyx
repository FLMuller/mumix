# cython: language_level=3
"""
tkvc2.pyx — Experimental fast tkv (option B). The tree / node / registry layer
of tkv, sitting on the SAME store experiment as kvc2:

  * segment keys stored as BYTES; comparison is memcmp (C), not str compare.
  * hash is Python's hash(bytes) (siphash in C), not the per-char DJB2 loop.
  * index / hash / istype tables are RAW C ARRAYS (malloc); the probe touches no
    Python objects until a hash hits, then one list slot (key, memcmp) + value.
  * _key2idx is inlined and emits bytes directly (no str round-trip, no _numstr).

The merged istype partition is kept (201 leaf / 202 sparse-leaf / 203 node /
204 sparse-node) so node/leaf enumeration is a contiguous C scan — the thing a
dict cannot do. NOTE: the hash differs from tkv.m, so the probe ORDER is not
algorithm-identical — tkvc2 is the speed experiment; tkv / tkvc remain the
faithful DJB2 versions.

    from tkvc2 import tkvc2
    t = tkvc2(); t.cfg.host = 'x'; t.kvr('cfg.host')

Build:  python primary/setup.py build_ext --inplace
"""

from cpython.bytes cimport PyBytes_AS_STRING, PyBytes_GET_SIZE
from libc.stdlib cimport malloc, free, realloc
from libc.string cimport memcmp, memset

DEF TOMB = 0xFFFFFFFF
DEF N0   = 32
DEF SZT0 = 64

_KIND = {0: "key not found", 201: "leaf", 202: "leaf(sparse)",
         203: "tkv", 204: "tkv(sparse)"}
_METHODS = None


class Tkvc2Error(Exception):              pass
class Tkvc2BadRegistry(Tkvc2Error):       pass
class Tkvc2DuplicateName(Tkvc2Error):     pass
class Tkvc2ReservedName(Tkvc2Error):      pass
class Tkvc2ReservedParen(Tkvc2Error):     pass
class Tkvc2SparseDimMismatch(Tkvc2Error): pass
class Tkvc2SparseKindMismatch(Tkvc2Error):pass


def _is_method_name(bytes name):
    # method/property names as a BYTES set (segments are bytes in this store).
    global _METHODS
    if _METHODS is None:
        _METHODS = {n.encode("utf-8") for n in dir(tkvc2) if not n.startswith("_")}
    return name in _METHODS


def _type_after(registry, t):
    if not registry:
        return ""
    seq = registry.get("sequence", [])
    try:
        i = seq.index(t)
    except ValueError:
        return ""
    return seq[i + 1] if i + 1 < len(seq) else ""


cdef inline bytes _numb(x):
    # number -> bytes directly (one C format step; no str object, no encode).
    if isinstance(x, int):
        return b"%d" % x
    return b"%.15g" % x


cdef tuple _key2idx(key):
    # -> (canonical bytes, nD).  Mirrors key2idx.py but builds BYTES throughout.
    cdef list comps, parts
    cdef bytes bc
    if isinstance(key, str):
        return (<str>key).encode("utf-8"), 0          # user str -> bytes (unavoidable)
    if isinstance(key, bool):
        return (b"True" if key else b"False"), 0
    if isinstance(key, (int, float)):
        return b"(" + _numb(key) + b")", 1
    if isinstance(key, (list, tuple)):
        comps = list(key)
        if len(comps) == 1:
            e = comps[0]
            if isinstance(e, (list, tuple)):
                comps = list(e)
            elif isinstance(e, str):
                return e.encode("utf-8"), 0
            else:
                return b"(" + _numb(e) + b")", 1
        parts = []
        for c in comps:
            if isinstance(c, str):
                bc = (<str>c).encode("utf-8")
                if b" " in bc:
                    bc = b"'" + bc + b"'"
            else:
                bc = _numb(c)                         # numbers never contain a space
            parts.append(bc)
        return b"(" + b" ".join(parts) + b")", len(parts)
    return str(key).encode("utf-8"), 0


cdef class tkvc2:
    cdef unsigned int*       _idx        # index table (szT): 0 empty, TOMB tomb, k entry
    cdef unsigned long long* _hash       # cached hashes (nbuf)
    cdef unsigned char*      _istype     # 201/202/203/204 (nbuf)
    cdef list _cles, _data               # bytes keys / object values (nbuf-long)
    cdef unsigned long long _mask
    cdef Py_ssize_t _szT, _nbuf, _nUsed, _nfill, _sparseD, _sparseKind, _fslot
    cdef object _registry, _parent
    cdef str _type, _nextType, _name
    cdef bint _speculative

    def __cinit__(self):
        self._idx = NULL; self._hash = NULL; self._istype = NULL
        self._setup()
        self._registry = None
        self._type = ""
        self._nextType = ""
        self._parent = None
        self._name = ""
        self._speculative = False

    def __init__(self, types=None, **handlers):
        if types is None:
            return
        self._init_typed(types, handlers)

    def __dealloc__(self):
        free(self._idx); free(self._hash); free(self._istype)

    cdef _setup(self):
        free(self._idx); free(self._hash); free(self._istype)
        self._szT  = SZT0
        self._mask = SZT0 - 1
        self._nbuf = N0
        self._idx    = <unsigned int*>malloc(SZT0 * sizeof(unsigned int))
        self._hash   = <unsigned long long*>malloc(N0 * sizeof(unsigned long long))
        self._istype = <unsigned char*>malloc(N0)
        memset(self._idx, 0, SZT0 * sizeof(unsigned int))
        memset(self._istype, 0, N0)
        self._cles = [None] * N0
        self._data = [None] * N0
        self._nUsed = 0
        self._nfill = 0
        self._sparseD = 0
        self._sparseKind = 0

    @staticmethod
    cdef tkvc2 _child(tkvc2 parent, bytes name):
        cdef tkvc2 nd = tkvc2.__new__(tkvc2)     # __cinit__ mallocs the store
        nd._registry = parent._registry
        nd._type = parent._nextType
        nd._nextType = _type_after(parent._registry, parent._nextType)
        nd._parent = parent
        nd._name = name.decode("utf-8")
        nd._speculative = False
        return nd

    cdef _init_typed(self, types, handlers):
        types = [types] if isinstance(types, str) else list(types)
        if len(set(types)) != len(types):
            return
        reg = {"sequence": types}
        for nm, fn in handlers.items():
            if nm == "sequence":
                raise Tkvc2BadRegistry('"sequence" is a reserved registry key.')
            if not callable(fn):
                raise Tkvc2BadRegistry(f'Handler "{nm}" must be callable.')
            reg[nm] = fn
        self._registry = reg
        self._type = types[0]
        self._nextType = _type_after(reg, types[0])

    def clear(self):
        self._setup()
        return self

    # ── merged-hash store (option B: bytes + hash() + memcmp + C arrays) ──
    cdef tuple _get(self, bytes bkey):
        cdef const char* qp = PyBytes_AS_STRING(bkey)
        cdef Py_ssize_t qn = PyBytes_GET_SIZE(bkey)
        cdef unsigned long long h = <unsigned long long>hash(bkey), perturb = h
        cdef Py_ssize_t slot = <Py_ssize_t>(h & self._mask)
        cdef unsigned int ei
        cdef object sk
        while True:
            ei = self._idx[slot]
            if ei == 0:
                return (None, False)
            if ei < TOMB and self._hash[ei - 1] == h:
                sk = self._cles[ei - 1]
                if PyBytes_GET_SIZE(sk) == qn and memcmp(PyBytes_AS_STRING(sk), qp, qn) == 0:
                    return (self._data[ei - 1], self._istype[ei - 1] >= 203)
            perturb >>= 5
            slot = <Py_ssize_t>(((5 * <unsigned long long>slot + 1) + perturb) & self._mask)

    cdef int _typeof(self, bytes bkey):
        cdef const char* qp = PyBytes_AS_STRING(bkey)
        cdef Py_ssize_t qn = PyBytes_GET_SIZE(bkey)
        cdef unsigned long long h = <unsigned long long>hash(bkey), perturb = h
        cdef Py_ssize_t slot = <Py_ssize_t>(h & self._mask)
        cdef unsigned int ei
        cdef object sk
        while True:
            ei = self._idx[slot]
            if ei == 0:
                return 0
            if ei < TOMB and self._hash[ei - 1] == h:
                sk = self._cles[ei - 1]
                if PyBytes_GET_SIZE(sk) == qn and memcmp(PyBytes_AS_STRING(sk), qp, qn) == 0:
                    return self._istype[ei - 1]
            perturb >>= 5
            slot = <Py_ssize_t>(((5 * <unsigned long long>slot + 1) + perturb) & self._mask)

    cdef Py_ssize_t _find(self, bytes bkey, unsigned long long h):
        cdef const char* qp = PyBytes_AS_STRING(bkey)
        cdef Py_ssize_t qn = PyBytes_GET_SIZE(bkey)
        cdef unsigned long long perturb = h
        cdef Py_ssize_t slot = <Py_ssize_t>(h & self._mask), first_dummy = -1
        cdef unsigned int ei
        cdef object sk
        while True:
            ei = self._idx[slot]
            if ei == 0:
                self._fslot = first_dummy if first_dummy >= 0 else slot
                return 0
            elif ei == TOMB:
                if first_dummy < 0:
                    first_dummy = slot
            else:
                if self._hash[ei - 1] == h:
                    sk = self._cles[ei - 1]
                    if PyBytes_GET_SIZE(sk) == qn and memcmp(PyBytes_AS_STRING(sk), qp, qn) == 0:
                        self._fslot = slot
                        return <Py_ssize_t>ei
            perturb >>= 5
            slot = <Py_ssize_t>(((5 * <unsigned long long>slot + 1) + perturb) & self._mask)

    cdef _set(self, bytes bkey, val, int ty):
        cdef unsigned long long h = <unsigned long long>hash(bkey)
        cdef Py_ssize_t ei = self._find(bkey, h), slot = self._fslot, nf
        cdef const char* qp
        if ei > 0:
            if val is None:
                self._idx[slot] = TOMB
                self._istype[ei - 1] = 0
                self._nUsed -= 1
            self._data[ei - 1] = val
            return
        elif val is None:
            return
        qp = PyBytes_AS_STRING(bkey)
        if ty != 202 and ty != 204 and PyBytes_GET_SIZE(bkey) > 0 and qp[0] == 40:   # '('
            raise Tkvc2ReservedParen("parenthesised keys are reserved; index with t[r, c]")
        nf = self._nfill
        if 3 * (nf + 1) > 2 * self._szT:
            self._resize()
            self._find(bkey, h)
            slot = self._fslot
            nf = self._nfill
        ei = nf + 1
        self._nfill = ei
        self._nUsed += 1
        if ei > self._nbuf:
            self._grow()
        self._hash[ei - 1]   = h
        self._istype[ei - 1] = ty
        self._cles[ei - 1]   = bkey
        self._data[ei - 1]   = val
        self._idx[slot]      = <unsigned int>ei

    cdef _remove(self, bytes bkey):
        cdef unsigned long long h = <unsigned long long>hash(bkey)
        cdef Py_ssize_t ei = self._find(bkey, h)
        if ei == 0:
            return
        self._idx[self._fslot] = TOMB
        self._istype[ei - 1]   = 0
        self._data[ei - 1]     = None
        self._nUsed -= 1

    cdef _grow(self):
        cdef Py_ssize_t newbuf = self._nbuf * 2, ext = self._nbuf
        self._hash   = <unsigned long long*>realloc(self._hash, newbuf * sizeof(unsigned long long))
        self._istype = <unsigned char*>realloc(self._istype, newbuf)
        self._cles += [None] * ext
        self._data += [None] * ext
        self._nbuf = newbuf

    cdef _resize(self):
        cdef Py_ssize_t n = self._nUsed, new_szt = self._szT, k, i, s
        while new_szt < 4 * n:
            new_szt *= 2
        cdef unsigned long long new_mask = new_szt - 1, hk, perturb
        cdef list live = [i for i in range(self._nfill) if self._istype[i] > 0]
        cdef list nc = [self._cles[i] for i in live]
        cdef list nd = [self._data[i] for i in live]
        # compact the C arrays in place (live indices increasing, target <= source)
        for k in range(n):
            i = live[k]
            self._hash[k]   = self._hash[i]
            self._istype[k] = self._istype[i]
        cdef unsigned int* new_idx = <unsigned int*>malloc(new_szt * sizeof(unsigned int))
        memset(new_idx, 0, new_szt * sizeof(unsigned int))
        for k in range(n):
            hk = self._hash[k]
            perturb = hk
            s = <Py_ssize_t>(hk & new_mask)
            while new_idx[s] != 0:
                perturb >>= 5
                s = <Py_ssize_t>(((5 * <unsigned long long>s + 1) + perturb) & new_mask)
            new_idx[s] = <unsigned int>(k + 1)
        free(self._idx)
        self._idx = new_idx
        self._cles = nc + [None] * (self._nbuf - n)
        self._data = nd + [None] * (self._nbuf - n)
        self._nfill = n
        self._szT   = new_szt
        self._mask  = new_mask

    # ── tree write layer ────────────────────────────────────────────────
    cdef _sparse_gate(self, int kind, int nD):
        if self._sparseD == 0:
            self._sparseD = nD
        elif self._sparseD != nD:
            raise Tkvc2SparseDimMismatch(
                f"Sparse container is {self._sparseD}-D; got {nD}-D key.")
        if self._sparseKind == 0:
            self._sparseKind = kind
        elif self._sparseKind != kind:
            raise Tkvc2SparseKindMismatch("sparse kind mismatch")

    cdef tkvc2 _add_node(self, bytes ck, int nD, bint speculative):
        cdef int ty
        if _is_method_name(ck):
            raise Tkvc2ReservedName(f'name "{ck.decode()}" is a tkvc2 method/property')
        if nD > 0:
            self._sparse_gate(204, nD)
            ty = 204
        else:
            ty = 203
        cdef tkvc2 child = tkvc2._child(self, ck)
        if self._registry is not None and self._nextType == "":
            child._registry = None
        child._speculative = speculative
        self._set(ck, child, ty)
        return child

    cdef _leaf_set(self, bytes ck, val, int nD):
        cdef int ty
        if self._typeof(ck) >= 203:
            raise Tkvc2DuplicateName(f'name "{ck.decode()}" is already a node')
        if nD > 0:
            self._sparse_gate(202, nD)
            ty = 202
        else:
            ty = 201
        self._set(ck, val, ty)

    cdef _leaf_write(self, bytes ck, val, int nD):
        cdef tkvc2 v
        if val is None:
            self._remove(ck)
            return
        res = self._get(ck)
        if res[0] is not None and res[1]:
            v = <tkvc2?>res[0]
            if v._speculative:
                self._remove(ck)
            else:
                raise Tkvc2DuplicateName(f'name "{ck.decode()}" is already a node')
        self._leaf_set(ck, val, nD)

    cdef _confirm(self):
        cdef tkvc2 node = self
        while node is not None:
            if node._speculative:
                node._speculative = False
            node = <tkvc2?>node._parent if node._parent is not None else None

    # single-segment read (bytes seg); registry lookup decodes only on miss.
    cdef _leaf_kvr(self, bytes seg, tuple args):
        cdef bint spec
        res = self._get(seg)
        v = res[0]
        if v is not None:
            spec = (<tkvc2?>v)._speculative if res[1] else False
            if not spec:
                if args and res[1]:
                    return (<tkvc2?>v).kvr(*args)
                return v
        cdef str sname = seg.decode("utf-8")
        if self._registry and sname != "sequence" and sname in self._registry:
            return self._registry[sname](self, *args)
        return None

    # ── path API ─────────────────────────────────────────────────────────
    def kvw(self, path, val):
        cdef bytes cpath, seg
        cdef int nD
        cpath, nD = _key2idx(path)
        if b"." not in cpath:
            self._leaf_write(cpath, val, nD)
            return
        cdef tkvc2 cur = self
        cdef list segs = cpath.split(b".")
        for seg in segs[:-1]:
            res = cur._get(seg)
            if res[0] is None:
                cur = cur._add_node(seg, 0, False)
            elif not res[1]:
                raise Tkvc2DuplicateName(f'path segment "{seg.decode()}" is already a leaf')
            else:
                cur = <tkvc2?>res[0]
        cur._leaf_write(segs[-1], val, 0)

    def kvr(self, path, *args):
        cdef bytes cpath, seg
        if isinstance(path, str) and "." not in path:
            return self._leaf_kvr((<str>path).encode("utf-8"), args)
        cpath = _key2idx(path)[0]
        if b"." not in cpath:
            return self._leaf_kvr(cpath, args)
        cdef tkvc2 cur = self
        cdef list segs = cpath.split(b".")
        for seg in segs[:-1]:
            res = cur._get(seg)
            if res[0] is None or not res[1]:
                return None
            cur = <tkvc2?>res[0]
        return cur._leaf_kvr(segs[-1], args)

    def insert(self, *args):
        ck, nD = _key2idx(list(args[:-1]) if len(args) > 2 else args[0])
        self._leaf_write(ck, args[-1], nD)
        return self

    def node(self, path, *extra):
        ck, nD = _key2idx([path, *extra]) if extra else _key2idx(path)
        res = self._get(ck)
        if res[0] is None:
            return self._add_node(ck, nD, False)
        if not res[1]:
            raise Tkvc2DuplicateName(f'node name "{ck.decode()}" already exists as leaf')
        return res[0]

    def remove(self, key):
        self._remove(_key2idx(key)[0])

    # ── scans ────────────────────────────────────────────────────────────
    cdef list _live_nodes(self):
        cdef list out = []
        cdef Py_ssize_t i
        for i in range(self._nfill):
            if self._istype[i] >= 203 and not (<tkvc2?>self._data[i])._speculative:
                out.append((self._cles[i], self._data[i]))
        return out

    def count(self):   return len(self._live_nodes())
    def names(self):   return [k.decode("utf-8") for k, _ in self._live_nodes()]
    def nodes(self):   return [v for _, v in self._live_nodes()]
    def hasNodes(self): return len(self._live_nodes()) > 0

    def isnode(self, name):
        res = self._get(_key2idx(name)[0])
        if res[0] is None or not res[1]:
            return False
        return not (<tkvc2?>res[0])._speculative

    def keys(self):
        cdef Py_ssize_t i
        return [self._cles[i].decode("utf-8") for i in range(self._nfill)
                if 0 < self._istype[i] < 202]

    def vals(self):
        cdef Py_ssize_t i
        return [self._data[i] for i in range(self._nfill) if 0 < self._istype[i] < 202]

    def numEntries(self):
        cdef Py_ssize_t i, c = 0
        for i in range(self._nfill):
            if 0 < self._istype[i] < 202:
                c += 1
        return c

    def entries(self):
        cdef Py_ssize_t i
        return [[self._cles[i].decode("utf-8"), self._data[i]]
                for i in range(self._nfill) if 0 < self._istype[i] < 202]

    def iskey(self, key):
        cdef bytes ck = _key2idx(key)[0]
        if ck[:1] == b"(":
            return False
        res = self._get(ck)
        return res[0] is not None and not res[1]

    def indici(self):
        cdef Py_ssize_t i
        return [self._cles[i].decode("utf-8") for i in range(self._nfill)
                if self._istype[i] == 202 or self._istype[i] == 204]

    def icount(self):
        cdef Py_ssize_t i, c = 0
        for i in range(self._nfill):
            if self._istype[i] == 202 or self._istype[i] == 204:
                c += 1
        return c

    def idim(self):        return self._sparseD
    def indexisnode(self): return self._sparseKind == 204

    def kind(self, key):
        cdef bytes ck = _key2idx(key)[0]
        res = self._get(ck)
        if res[0] is None:
            return _KIND[0]
        if res[1]:                                       # node -> cast is safe
            if (<tkvc2?>res[0])._speculative:
                return _KIND[0]
        return _KIND.get(self._typeof(ck), "leaf")

    def parent(self): return self._parent
    def name(self):   return self._name
    def type(self):   return self._type

    def isEmpty(self):
        return self.count() == 0 and self.numEntries() == 0 and self.icount() == 0

    # ── attribute access ─────────────────────────────────────────────────
    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        res = self._get(name.encode("utf-8"))
        if res[0] is not None:
            return res[0]
        if self._registry and name != "sequence" and name in self._registry:
            fn = self._registry[name]
            return lambda *a: fn(self, *a)
        return self._add_node(name.encode("utf-8"), 0, True)

    def __setattr__(self, name, val):
        if isinstance(name, str) and name.startswith("_"):
            raise AttributeError(name)
        if _is_method_name(name.encode("utf-8")):
            raise Tkvc2ReservedName(f'name "{name}" is a tkvc2 method/property')
        if self._registry and name != "sequence" and name in self._registry:
            raise Tkvc2ReservedName(f'name "{name}" is a registered function')
        self._confirm()
        self._leaf_write(name.encode("utf-8"), val, 0)

    def __getitem__(self, key):
        cdef bytes ck
        cdef int nD
        ck, nD = _key2idx(key)
        res = self._get(ck)
        if res[0] is not None:
            return res[0]
        if nD > 0:
            return self._add_node(ck, nD, True)
        return None

    def __setitem__(self, key, val):
        cdef bytes ck
        cdef int nD
        ck, nD = _key2idx(key)
        self._confirm()
        self._leaf_write(ck, val, nD)

    def __delitem__(self, key):
        self.remove(key)

    def __contains__(self, key):
        return self.iskey(key)

    def string(self):
        return repr(self)

    def __repr__(self):
        cdef Py_ssize_t i
        cdef int t
        parts = []
        for i in range(self._nfill):
            t = self._istype[i]
            if t >= 203:
                if (<tkvc2?>self._data[i])._speculative:
                    continue
                parts.append(f"{self._cles[i].decode()}:{self._data[i]!r}")
            elif t > 0:
                parts.append(f"{self._cles[i].decode()}:{_leafstr(self._data[i])}")
        return "{" + " ".join(parts) + "}"


def _leafstr(v):
    if v is None:
        return "''"
    if isinstance(v, tkvc2):
        return "#tkv"
    if isinstance(v, (list, tuple)):
        return "[" + ",".join(map(str, v)) + "]"
    return str(v)


def kvr(d, path, *args):
    return d.kvr(path, *args)


def kvw(d, path, val):
    d.kvw(path, val)
    return d
