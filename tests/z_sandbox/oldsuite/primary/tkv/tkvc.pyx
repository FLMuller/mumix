# cython: language_level=3
"""
tkvc.pyx — Cython build of tkv. Same merged open-addressing hash as tkv.py /
tkv.m, with the probe arithmetic and array indexing in C. Public API identical
to tkv (dotted kvw/kvr, node autoviv, sparse, typed registry); kept under a
DISTINCT name so it benches head-to-head against pure-Python tkv.

    from tkvc import tkvc
    t = tkvc(); t.cfg.host = 'x'; t.kvr('cfg.host')

Build:  python primary/setup.py build_ext --inplace
"""

from key2idx import key2idx

DEF SEED  = 130150524
DEF MOD   = 4294967296
DEF M32   = 0xFFFFFFFF
DEF TOMB  = 0xFFFFFFFF
DEF N0    = 32
DEF SZT0  = 64

_KIND = {0: "key not found", 201: "leaf", 202: "leaf(sparse)",
         203: "tkv", 204: "tkv(sparse)"}
_METHODS = None


class TkvcError(Exception):              pass
class TkvcBadRegistry(TkvcError):        pass
class TkvcDuplicateName(TkvcError):      pass
class TkvcReservedName(TkvcError):       pass
class TkvcReservedParen(TkvcError):      pass
class TkvcSparseDimMismatch(TkvcError):  pass
class TkvcSparseKindMismatch(TkvcError): pass


def _is_method_name(name):
    global _METHODS
    if _METHODS is None:
        _METHODS = {n for n in dir(tkvc) if not n.startswith("_")}
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


cdef class tkvc:
    cdef list _idx, _hash, _cles, _data, _istype
    cdef unsigned long long _mask
    cdef Py_ssize_t _szT, _nbuf, _nUsed, _nfill, _sparseD, _sparseKind, _fslot
    cdef object _registry, _parent
    cdef str _type, _nextType, _name
    cdef bint _speculative

    def __init__(self, types=None, **handlers):
        self._init_store()
        self._registry = None
        self._type = ""
        self._nextType = ""
        self._parent = None
        self._name = ""
        self._speculative = False
        if types is None:
            return
        self._init_typed(types, handlers)

    cdef _init_store(self):
        self._szT     = SZT0
        self._mask    = SZT0 - 1
        self._idx     = [0] * SZT0
        self._hash    = [0] * N0
        self._istype  = [0] * N0
        self._nbuf    = N0
        self._nUsed   = 0
        self._nfill   = 0
        self._cles    = [None] * N0
        self._data    = [None] * N0
        self._sparseD = 0
        self._sparseKind = 0

    @staticmethod
    cdef tkvc _child(tkvc parent, str name):
        cdef tkvc nd = tkvc.__new__(tkvc)
        nd._init_store()
        nd._registry = parent._registry
        nd._type = parent._nextType
        nd._nextType = _type_after(parent._registry, parent._nextType)
        nd._parent = parent
        nd._name = name
        nd._speculative = False
        return nd

    cdef _init_typed(self, types, handlers):
        types = [types] if isinstance(types, str) else list(types)
        if len(set(types)) != len(types):
            return
        reg = {"sequence": types}
        for nm, fn in handlers.items():
            if nm == "sequence":
                raise TkvcBadRegistry('"sequence" is a reserved registry key.')
            if not callable(fn):
                raise TkvcBadRegistry(f'Handler "{nm}" must be callable.')
            reg[nm] = fn
        self._registry = reg
        self._type = types[0]
        self._nextType = _type_after(reg, types[0])

    def clear(self):
        self._init_store()
        return self

    # ── merged-hash internals ──────────────────────────────────────────
    cdef unsigned long long _hashkey(self, str ckey):
        cdef unsigned long long h = SEED
        cdef Py_UCS4 ch
        for ch in ckey:
            h = (h * 33 + <unsigned long long>ch) % MOD
        h ^= (h << 17) & M32
        return h

    cdef tuple _get(self, str ckey):
        cdef unsigned long long h = self._hashkey(ckey), perturb = h
        cdef Py_ssize_t slot = <Py_ssize_t>(h & self._mask)
        cdef unsigned long long ei
        cdef list idx = self._idx, hsh = self._hash, cles = self._cles
        while True:
            ei = idx[slot]
            if ei == 0:
                return (None, False)
            if ei < TOMB and <unsigned long long>hsh[ei - 1] == h and cles[ei - 1] == ckey:
                return (self._data[ei - 1], <int>self._istype[ei - 1] >= 203)
            perturb >>= 5
            slot = <Py_ssize_t>(((5 * <unsigned long long>slot + 1) + perturb) & self._mask)

    cdef int _typeof(self, str ckey):
        cdef unsigned long long h = self._hashkey(ckey), perturb = h, ei
        cdef Py_ssize_t slot = <Py_ssize_t>(h & self._mask)
        cdef list idx = self._idx, hsh = self._hash, cles = self._cles
        while True:
            ei = idx[slot]
            if ei == 0:
                return 0
            if ei < TOMB and <unsigned long long>hsh[ei - 1] == h and cles[ei - 1] == ckey:
                return self._istype[ei - 1]
            perturb >>= 5
            slot = <Py_ssize_t>(((5 * <unsigned long long>slot + 1) + perturb) & self._mask)

    cdef Py_ssize_t _find(self, str ckey, unsigned long long h):
        cdef unsigned long long perturb = h, ei
        cdef Py_ssize_t slot = <Py_ssize_t>(h & self._mask), first_dummy = -1
        cdef list idx = self._idx, hsh = self._hash, cles = self._cles
        while True:
            ei = idx[slot]
            if ei == 0:
                self._fslot = first_dummy if first_dummy >= 0 else slot
                return 0
            elif ei == TOMB:
                if first_dummy < 0:
                    first_dummy = slot
            else:
                if <unsigned long long>hsh[ei - 1] == h and cles[ei - 1] == ckey:
                    self._fslot = slot
                    return <Py_ssize_t>ei
            perturb >>= 5
            slot = <Py_ssize_t>(((5 * <unsigned long long>slot + 1) + perturb) & self._mask)

    cdef _set(self, str ckey, val, int ty):
        cdef unsigned long long h = self._hashkey(ckey)
        cdef Py_ssize_t ei = self._find(ckey, h), slot = self._fslot, nf
        cdef bint b = val is None
        if ei > 0:
            if b:
                self._idx[slot] = TOMB
                self._istype[ei - 1] = 0
                self._nUsed -= 1
            self._data[ei - 1] = val
            return
        elif b:
            return
        if len(ckey) > 0 and ckey[0] == u"(" and ty != 202 and ty != 204:
            raise TkvcReservedParen("parenthesised keys are reserved; index with t[r, c]")
        nf = self._nfill
        if 3 * (nf + 1) > 2 * self._szT:
            self._resize()
            self._find(ckey, h)
            slot = self._fslot
            nf = self._nfill
        ei = nf + 1
        self._nfill = ei
        self._nUsed += 1
        if ei > self._nbuf:
            self._grow()
        self._hash[ei - 1]   = h
        self._cles[ei - 1]   = ckey
        self._data[ei - 1]   = val
        self._istype[ei - 1] = ty
        self._idx[slot]      = ei

    cdef _remove(self, str ckey):
        cdef unsigned long long h = self._hashkey(ckey)
        cdef Py_ssize_t ei = self._find(ckey, h)
        if ei == 0:
            return
        self._idx[self._fslot] = TOMB
        self._data[ei - 1]     = None
        self._istype[ei - 1]   = 0
        self._nUsed -= 1

    cdef _grow(self):
        cdef Py_ssize_t ext = self._nbuf
        self._hash   += [0] * ext
        self._cles   += [None] * ext
        self._data   += [None] * ext
        self._istype += [0] * ext
        self._nbuf   += ext

    cdef _resize(self):
        cdef Py_ssize_t n = self._nUsed, new_szt = self._szT, k, s
        while new_szt < 4 * n:
            new_szt *= 2
        cdef unsigned long long new_mask = new_szt - 1, hk, perturb
        cdef list live = [i for i in range(self._nfill) if self._istype[i] > 0]
        cdef list nh = [self._hash[i] for i in live]
        cdef list nc = [self._cles[i] for i in live]
        cdef list nd = [self._data[i] for i in live]
        cdef list nt = [self._istype[i] for i in live]
        cdef list ni = [0] * new_szt
        for k in range(n):
            hk = nh[k]
            perturb = hk
            s = <Py_ssize_t>(hk & new_mask)
            while ni[s] != 0:
                perturb >>= 5
                s = <Py_ssize_t>(((5 * <unsigned long long>s + 1) + perturb) & new_mask)
            ni[s] = k + 1
        self._hash[:n]   = nh
        self._cles[:n]   = nc
        self._data[:n]   = nd
        self._istype[:n] = nt
        self._idx   = ni
        self._nfill = n
        self._szT   = new_szt
        self._mask  = new_mask

    # ── tree write layer ────────────────────────────────────────────────
    cdef _sparse_gate(self, int kind, int nD):
        if self._sparseD == 0:
            self._sparseD = nD
        elif self._sparseD != nD:
            raise TkvcSparseDimMismatch(
                f"Sparse container is {self._sparseD}-D; got {nD}-D key.")
        if self._sparseKind == 0:
            self._sparseKind = kind
        elif self._sparseKind != kind:
            raise TkvcSparseKindMismatch("sparse kind mismatch")

    cdef tkvc _add_node(self, str ck, int nD, bint speculative):
        cdef int ty
        if _is_method_name(ck):
            raise TkvcReservedName(f'name "{ck}" is a tkvc method/property')
        if nD > 0:
            self._sparse_gate(204, nD)
            ty = 204
        else:
            ty = 203
        cdef tkvc child = tkvc._child(self, ck)
        if self._registry is not None and self._nextType == "":
            child._registry = None
        child._speculative = speculative
        self._set(ck, child, ty)
        return child

    cdef _leaf_set(self, str ck, val, int nD):
        cdef int ty
        if self._typeof(ck) >= 203:
            raise TkvcDuplicateName(f'name "{ck}" is already a node')
        if nD > 0:
            self._sparse_gate(202, nD)
            ty = 202
        else:
            ty = 201
        self._set(ck, val, ty)

    cdef _leaf_write(self, str ck, val, int nD):
        cdef tkvc v
        cdef bint isn
        if val is None:
            self._remove(ck)
            return
        res = self._get(ck)
        if res[0] is not None and res[1]:
            v = <tkvc?>res[0]
            if v._speculative:
                self._remove(ck)
            else:
                raise TkvcDuplicateName(f'name "{ck}" is already a node')
        self._leaf_set(ck, val, nD)

    cdef _confirm(self):
        cdef tkvc node = self
        while node is not None:
            if node._speculative:
                node._speculative = False
            node = <tkvc?>node._parent if node._parent is not None else None

    # ── path API ─────────────────────────────────────────────────────────
    def kvw(self, path, val):
        cdef str cpath
        cdef int nD
        cpath, nD = key2idx(path)
        if "." not in cpath:
            self._leaf_write(cpath, val, nD)
            return
        cdef tkvc cur = self
        cdef list segs = cpath.split(".")
        for seg in segs[:-1]:
            res = cur._get(seg)
            if res[0] is None:
                cur = cur._add_node(seg, 0, False)
            elif not res[1]:
                raise TkvcDuplicateName(f'path segment "{seg}" is already a leaf')
            else:
                cur = <tkvc?>res[0]
        cur._leaf_write(segs[-1], val, 0)

    def kvr(self, path, *args):
        cdef bint spec
        if isinstance(path, str) and "." not in path:
            res = self._get(path)
            v = res[0]
            if v is not None:
                spec = (<tkvc?>v)._speculative if res[1] else False   # cast only when node
                if not spec:
                    if args and res[1]:
                        return v.kvr(*args)
                    return v
            if self._registry and path != "sequence" and path in self._registry:
                return self._registry[path](self, *args)
            return None
        cpath = key2idx(path)[0]
        if "." not in cpath:
            return self.kvr(cpath, *args)
        cdef tkvc cur = self
        cdef list segs = cpath.split(".")
        for seg in segs[:-1]:
            res = cur._get(seg)
            if res[0] is None or not res[1]:
                return None
            cur = <tkvc?>res[0]
        return cur.kvr(segs[-1], *args)

    def insert(self, *args):
        ck, nD = key2idx(list(args[:-1]) if len(args) > 2 else args[0])
        self._leaf_write(ck, args[-1], nD)
        return self

    def node(self, path, *extra):
        ck, nD = key2idx([path, *extra]) if extra else key2idx(path)
        res = self._get(ck)
        if res[0] is None:
            return self._add_node(ck, nD, False)
        if not res[1]:
            raise TkvcDuplicateName(f'node name "{ck}" already exists as leaf')
        return res[0]

    def remove(self, key):
        self._remove(key2idx(key)[0])

    # ── scans ────────────────────────────────────────────────────────────
    cdef list _live_nodes(self):
        cdef list out = [], it = self._istype, cl = self._cles, da = self._data
        cdef Py_ssize_t i
        for i in range(self._nfill):
            if <int>it[i] >= 203 and not (<tkvc?>da[i])._speculative:
                out.append((cl[i], da[i]))
        return out

    def count(self):   return len(self._live_nodes())
    def names(self):   return [k for k, _ in self._live_nodes()]
    def nodes(self):   return [v for _, v in self._live_nodes()]
    def hasNodes(self): return len(self._live_nodes()) > 0

    def isnode(self, name):
        res = self._get(key2idx(name)[0])
        if res[0] is None or not res[1]:
            return False
        return not (<tkvc?>res[0])._speculative          # cast safe: res[1] true

    def keys(self):
        cdef list it = self._istype, cl = self._cles
        cdef Py_ssize_t i
        return [cl[i] for i in range(self._nfill) if 0 < <int>it[i] < 202]

    def vals(self):
        cdef list it = self._istype, da = self._data
        cdef Py_ssize_t i
        return [da[i] for i in range(self._nfill) if 0 < <int>it[i] < 202]

    def numEntries(self):
        cdef list it = self._istype
        cdef Py_ssize_t i, c = 0
        for i in range(self._nfill):
            if 0 < <int>it[i] < 202:
                c += 1
        return c

    def entries(self):
        cdef list it = self._istype, cl = self._cles, da = self._data
        cdef Py_ssize_t i
        return [[cl[i], da[i]] for i in range(self._nfill) if 0 < <int>it[i] < 202]

    def iskey(self, key):
        ck = key2idx(key)[0]
        if ck[:1] == "(":
            return False
        res = self._get(ck)
        return res[0] is not None and not res[1]

    def indici(self):
        cdef list it = self._istype, cl = self._cles
        cdef Py_ssize_t i
        return [cl[i] for i in range(self._nfill) if <int>it[i] == 202 or <int>it[i] == 204]

    def icount(self):
        cdef list it = self._istype
        cdef Py_ssize_t i, c = 0
        for i in range(self._nfill):
            if <int>it[i] == 202 or <int>it[i] == 204:
                c += 1
        return c

    def idim(self):       return self._sparseD
    def indexisnode(self): return self._sparseKind == 204

    def kind(self, key):
        ck = key2idx(key)[0]
        res = self._get(ck)
        if res[0] is None:
            return _KIND[0]
        if res[1]:                                       # node -> cast is safe
            if (<tkvc?>res[0])._speculative:
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
        res = self._get(name)
        if res[0] is not None:
            return res[0]
        if self._registry and name != "sequence" and name in self._registry:
            fn = self._registry[name]
            return lambda *a: fn(self, *a)
        return self._add_node(name, 0, True)

    def __setattr__(self, name, val):
        if isinstance(name, str) and name.startswith("_"):
            raise AttributeError(name)
        if _is_method_name(name):
            raise TkvcReservedName(f'name "{name}" is a tkvc method/property')
        if self._registry and name != "sequence" and name in self._registry:
            raise TkvcReservedName(f'name "{name}" is a registered function')
        self._confirm()
        self._leaf_write(name, val, 0)

    def __getitem__(self, key):
        ck, nD = key2idx(key)
        res = self._get(ck)
        if res[0] is not None:
            return res[0]
        if nD > 0:
            return self._add_node(ck, nD, True)
        return None

    def __setitem__(self, key, val):
        ck, nD = key2idx(key)
        self._confirm()
        self._leaf_write(ck, val, nD)

    def __delitem__(self, key):
        self.remove(key)

    def __contains__(self, key):
        return self.iskey(key)

    def string(self):
        return repr(self)

    def __repr__(self):
        cdef list it = self._istype, cl = self._cles, da = self._data
        cdef Py_ssize_t i
        parts = []
        for i in range(self._nfill):
            if <int>it[i] >= 203:
                if (<tkvc?>da[i])._speculative:
                    continue
                parts.append(f"{cl[i]}:{da[i]!r}")
            elif <int>it[i] > 0:
                parts.append(f"{cl[i]}:{_leafstr(da[i])}")
        return "{" + " ".join(parts) + "}"


def _leafstr(v):
    if v is None:
        return "''"
    if isinstance(v, tkvc):
        return "#tkv"
    if isinstance(v, (list, tuple)):
        return "[" + ",".join(map(str, v)) + "]"
    return str(v)


def kvr(d, path, *args):
    return d.kvr(path, *args)


def kvw(d, path, val):
    d.kvw(path, val)
    return d
