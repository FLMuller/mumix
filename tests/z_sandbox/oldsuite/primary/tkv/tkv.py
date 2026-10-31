"""
tkv.py — pure-Python tkv with the option-B design (tkvc2's ideas, no compile).

Portable: a .py file has no cpXY-win ABI tag, so it runs on any CPython — unlike
tkvc*.pyd. Tree / node / registry layer on the kv store:
  * segment keys stored as BYTES; compare is `==` (C memcmp in CPython).
  * hash is Python's hash(bytes), not the per-char DJB2 loop.
  * _key2idx in-source, bytes throughout.
The merged TYPE partition (201 leaf / 202 sparse-leaf / 203 node / 204 sparse-
node) is kept so node/leaf enumeration is a contiguous scan.

NOTE: hash differs from tkv.m, so probe ORDER is not algorithm-identical — tkv
is the portable speed variant; tkv / tkvc keep the faithful DJB2 algorithm.

    from tkv import tkv
    t = tkv(); t.cfg.host = 'x'; t.kvr('cfg.host')
"""

N0   = 32
SZT0 = 64
TOMB = -1
M64  = 0xFFFFFFFFFFFFFFFF

_KIND = {0: "key not found", 201: "leaf", 202: "leaf(sparse)",
         203: "tkv", 204: "tkv(sparse)"}
_METHODS = None

__all__ = ["tkv", "kvr", "kvw", "TkvError", "TkvBadRegistry", "TkvDuplicateName",
           "TkvReservedName", "TkvReservedParen", "TkvSparseDimMismatch",
           "TkvSparseKindMismatch"]


class TkvError(Exception):              pass
class TkvBadRegistry(TkvError):       pass
class TkvDuplicateName(TkvError):     pass
class TkvReservedName(TkvError):      pass
class TkvReservedParen(TkvError):     pass
class TkvSparseDimMismatch(TkvError): pass
class TkvSparseKindMismatch(TkvError):pass


def _is_method_name(name):              # name is bytes
    global _METHODS
    if _METHODS is None:
        _METHODS = {n.encode("utf-8") for n in dir(tkv) if not n.startswith("_")}
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


def _numb(x):
    if isinstance(x, int):
        return b"%d" % x
    return b"%.15g" % x


def _key2idx(key):
    if isinstance(key, str):
        return key.encode("utf-8"), 0
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
                bc = c.encode("utf-8")
                if b" " in bc:
                    bc = b"'" + bc + b"'"
            else:
                bc = _numb(c)
            parts.append(bc)
        return b"(" + b" ".join(parts) + b")", len(parts)
    return str(key).encode("utf-8"), 0


class tkv:
    def __init__(self, types=None, **handlers):
        self._init_store()
        s = object.__setattr__
        s(self, "_registry", None)
        s(self, "_type", "")
        s(self, "_nextType", "")
        s(self, "_parent", None)
        s(self, "_name", "")
        s(self, "_speculative", False)
        if types is None:
            return
        self._init_typed(types, handlers)

    def _init_store(self):
        s = object.__setattr__
        s(self, "_szT", SZT0)
        s(self, "_mask", SZT0 - 1)
        s(self, "_idx", [0] * SZT0)
        s(self, "_hash", [0] * N0)
        s(self, "_istype", [0] * N0)
        s(self, "_nbuf", N0)
        s(self, "_nUsed", 0)
        s(self, "_nfill", 0)
        s(self, "_cles", [None] * N0)    # bytes keys (hash/compare)
        s(self, "_skeys", [None] * N0)   # str keys (decode once at insert; enum is decode-free)
        s(self, "_data", [None] * N0)
        s(self, "_sparseD", 0)
        s(self, "_sparseKind", 0)
        s(self, "_fslot", 0)

    @staticmethod
    def _child(parent, name):
        nd = tkv.__new__(tkv)
        nd._init_store()
        s = object.__setattr__
        s(nd, "_registry", parent._registry)
        s(nd, "_type", parent._nextType)
        s(nd, "_nextType", _type_after(parent._registry, parent._nextType))
        s(nd, "_parent", parent)
        s(nd, "_name", name.decode("utf-8"))
        s(nd, "_speculative", False)
        return nd

    def _init_typed(self, types, handlers):
        types = [types] if isinstance(types, str) else list(types)
        if len(set(types)) != len(types):
            return
        reg = {"sequence": types}
        for nm, fn in handlers.items():
            if nm == "sequence":
                raise TkvBadRegistry('"sequence" is a reserved registry key.')
            if not callable(fn):
                raise TkvBadRegistry(f'Handler "{nm}" must be callable.')
            reg[nm] = fn
        s = object.__setattr__
        s(self, "_registry", reg)
        s(self, "_type", types[0])
        s(self, "_nextType", _type_after(reg, types[0]))

    def clear(self):
        self._init_store()
        return self

    # ── merged-hash store ────────────────────────────────────────────────
    def _get(self, bkey):
        h = hash(bkey) & M64
        idx, hsh, cles, mask = self._idx, self._hash, self._cles, self._mask
        slot, perturb = h & mask, h
        while True:
            ei = idx[slot]
            if ei == 0:
                return (None, False)
            if ei != TOMB and hsh[ei - 1] == h and cles[ei - 1] == bkey:
                return (self._data[ei - 1], self._istype[ei - 1] >= 203)
            perturb >>= 5
            slot = (5 * slot + 1 + perturb) & mask

    def _typeof(self, bkey):
        h = hash(bkey) & M64
        idx, hsh, cles, mask = self._idx, self._hash, self._cles, self._mask
        slot, perturb = h & mask, h
        while True:
            ei = idx[slot]
            if ei == 0:
                return 0
            if ei != TOMB and hsh[ei - 1] == h and cles[ei - 1] == bkey:
                return self._istype[ei - 1]
            perturb >>= 5
            slot = (5 * slot + 1 + perturb) & mask

    def _find(self, bkey, h):
        idx, hsh, cles, mask = self._idx, self._hash, self._cles, self._mask
        slot, perturb, first_dummy = h & mask, h, -1
        while True:
            ei = idx[slot]
            if ei == 0:
                object.__setattr__(self, "_fslot",
                                   first_dummy if first_dummy >= 0 else slot)
                return 0
            elif ei == TOMB:
                if first_dummy < 0:
                    first_dummy = slot
            else:
                if hsh[ei - 1] == h and cles[ei - 1] == bkey:
                    object.__setattr__(self, "_fslot", slot)
                    return ei
            perturb >>= 5
            slot = (5 * slot + 1 + perturb) & mask

    def _set(self, bkey, val, ty):
        h = hash(bkey) & M64
        ei = self._find(bkey, h)
        slot = self._fslot
        if ei > 0:
            if val is None:
                self._idx[slot] = TOMB
                self._istype[ei - 1] = 0
                object.__setattr__(self, "_nUsed", self._nUsed - 1)
            self._data[ei - 1] = val
            return
        elif val is None:
            return
        if len(bkey) > 0 and bkey[0] == 40 and ty != 202 and ty != 204:
            raise TkvReservedParen("parenthesised keys are reserved; index with t[r, c]")
        nf = self._nfill
        if 3 * (nf + 1) > 2 * self._szT:
            self._resize()
            self._find(bkey, h)
            slot = self._fslot
            nf = self._nfill
        ei = nf + 1
        object.__setattr__(self, "_nfill", ei)
        object.__setattr__(self, "_nUsed", self._nUsed + 1)
        if ei > self._nbuf:
            self._grow()
        self._hash[ei - 1]   = h
        self._cles[ei - 1]   = bkey
        self._skeys[ei - 1]  = bkey.decode("utf-8")    # the one decode, at insert
        self._data[ei - 1]   = val
        self._istype[ei - 1] = ty
        self._idx[slot]      = ei

    def _remove(self, bkey):
        h = hash(bkey) & M64
        ei = self._find(bkey, h)
        if ei == 0:
            return
        self._idx[self._fslot] = TOMB
        self._data[ei - 1]     = None
        self._istype[ei - 1]   = 0
        object.__setattr__(self, "_nUsed", self._nUsed - 1)

    def _grow(self):
        ext = self._nbuf
        self._hash.extend([0] * ext)
        self._cles.extend([None] * ext)
        self._skeys.extend([None] * ext)
        self._data.extend([None] * ext)
        self._istype.extend([0] * ext)
        object.__setattr__(self, "_nbuf", self._nbuf + ext)

    def _resize(self):
        n = self._nUsed
        new_szt = self._szT
        while new_szt < 4 * n:
            new_szt *= 2
        new_mask = new_szt - 1
        live = [i for i in range(self._nfill) if self._istype[i] > 0]
        nh = [self._hash[i] for i in live]
        nc = [self._cles[i] for i in live]
        ns = [self._skeys[i] for i in live]
        nd = [self._data[i] for i in live]
        nt = [self._istype[i] for i in live]
        ni = [0] * new_szt
        for k in range(n):
            hk = nh[k]
            perturb = hk
            s = hk & new_mask
            while ni[s] != 0:
                perturb >>= 5
                s = (5 * s + 1 + perturb) & new_mask
            ni[s] = k + 1
        self._hash[:n]   = nh
        self._cles[:n]   = nc
        self._skeys[:n]  = ns
        self._data[:n]   = nd
        self._istype[:n] = nt
        object.__setattr__(self, "_idx", ni)
        object.__setattr__(self, "_nfill", n)
        object.__setattr__(self, "_szT", new_szt)
        object.__setattr__(self, "_mask", new_mask)

    # ── tree write layer ─────────────────────────────────────────────────
    def _sparse_gate(self, kind, nD):
        if self._sparseD == 0:
            object.__setattr__(self, "_sparseD", nD)
        elif self._sparseD != nD:
            raise TkvSparseDimMismatch(
                f"Sparse container is {self._sparseD}-D; got {nD}-D key.")
        if self._sparseKind == 0:
            object.__setattr__(self, "_sparseKind", kind)
        elif self._sparseKind != kind:
            raise TkvSparseKindMismatch("sparse kind mismatch")

    def _add_node(self, ck, nD, speculative):
        if _is_method_name(ck):
            raise TkvReservedName(f'name "{ck.decode()}" is a tkv method/property')
        if nD > 0:
            self._sparse_gate(204, nD)
            ty = 204
        else:
            ty = 203
        child = tkv._child(self, ck)
        if self._registry is not None and self._nextType == "":
            object.__setattr__(child, "_registry", None)
        object.__setattr__(child, "_speculative", speculative)
        self._set(ck, child, ty)
        return child

    def _leaf_set(self, ck, val, nD):
        if self._typeof(ck) >= 203:
            raise TkvDuplicateName(f'name "{ck.decode()}" is already a node')
        if nD > 0:
            self._sparse_gate(202, nD)
            ty = 202
        else:
            ty = 201
        self._set(ck, val, ty)

    def _leaf_write(self, ck, val, nD):
        if val is None:
            self._remove(ck)
            return
        v, isn = self._get(ck)
        if v is not None and isn:
            if v._speculative:
                self._remove(ck)
            else:
                raise TkvDuplicateName(f'name "{ck.decode()}" is already a node')
        self._leaf_set(ck, val, nD)

    def _confirm(self):
        node = self
        while node is not None:
            if node._speculative:
                object.__setattr__(node, "_speculative", False)
            node = node._parent

    def _leaf_kvr(self, seg, args):
        v, isn = self._get(seg)
        if v is not None:
            spec = v._speculative if isn else False
            if not spec:
                if args and isn:
                    return v.kvr(*args)
                return v
        sname = seg.decode("utf-8")
        if self._registry and sname != "sequence" and sname in self._registry:
            return self._registry[sname](self, *args)
        return None

    # ── path API ─────────────────────────────────────────────────────────
    def kvw(self, path, val):
        cpath, nD = _key2idx(path)
        if b"." not in cpath:
            self._leaf_write(cpath, val, nD)
            return
        cur = self
        segs = cpath.split(b".")
        for seg in segs[:-1]:
            v, isn = cur._get(seg)
            if v is None:
                cur = cur._add_node(seg, 0, False)
            elif not isn:
                raise TkvDuplicateName(f'path segment "{seg.decode()}" is already a leaf')
            else:
                cur = v
        cur._leaf_write(segs[-1], val, 0)

    def kvr(self, path, *args):
        if isinstance(path, str) and "." not in path:
            return self._leaf_kvr(path.encode("utf-8"), args)
        cpath = _key2idx(path)[0]
        if b"." not in cpath:
            return self._leaf_kvr(cpath, args)
        cur = self
        segs = cpath.split(b".")
        for seg in segs[:-1]:
            v, isn = cur._get(seg)
            if v is None or not isn:
                return None
            cur = v
        return cur._leaf_kvr(segs[-1], args)

    def insert(self, *args):
        ck, nD = _key2idx(list(args[:-1]) if len(args) > 2 else args[0])
        self._leaf_write(ck, args[-1], nD)
        return self

    def node(self, path, *extra):
        ck, nD = _key2idx([path, *extra]) if extra else _key2idx(path)
        v, isn = self._get(ck)
        if v is None:
            return self._add_node(ck, nD, False)
        if not isn:
            raise TkvDuplicateName(f'node name "{ck.decode()}" already exists as leaf')
        return v

    def remove(self, key):
        self._remove(_key2idx(key)[0])

    # ── scans ────────────────────────────────────────────────────────────
    def _live_nodes(self):
        it, sk, da = self._istype, self._skeys, self._data
        out = []
        for i in range(self._nfill):
            if it[i] >= 203 and not da[i]._speculative:
                out.append((sk[i], da[i]))
        return out

    def count(self):    return len(self._live_nodes())
    def names(self):    return [k for k, _ in self._live_nodes()]
    def nodes(self):    return [v for _, v in self._live_nodes()]
    def hasNodes(self): return len(self._live_nodes()) > 0

    def isnode(self, name):
        v, isn = self._get(_key2idx(name)[0])
        if v is None or not isn:
            return False
        return not v._speculative

    def keys(self):
        it, sk = self._istype, self._skeys
        return [sk[i] for i in range(self._nfill) if 0 < it[i] < 202]

    def vals(self):
        it, da = self._istype, self._data
        return [da[i] for i in range(self._nfill) if 0 < it[i] < 202]

    def numEntries(self):
        it = self._istype
        return sum(1 for i in range(self._nfill) if 0 < it[i] < 202)

    def entries(self):
        it, sk, da = self._istype, self._skeys, self._data
        return [[sk[i], da[i]] for i in range(self._nfill) if 0 < it[i] < 202]

    def iskey(self, key):
        ck = _key2idx(key)[0]
        if ck[:1] == b"(":
            return False
        v, isn = self._get(ck)
        return v is not None and not isn

    def indici(self):
        it, sk = self._istype, self._skeys
        return [sk[i] for i in range(self._nfill)
                if it[i] == 202 or it[i] == 204]

    def icount(self):
        it = self._istype
        return sum(1 for i in range(self._nfill) if it[i] == 202 or it[i] == 204)

    def idim(self):        return self._sparseD
    def indexisnode(self): return self._sparseKind == 204

    def kind(self, key):
        ck = _key2idx(key)[0]
        v, isn = self._get(ck)
        if v is None:
            return _KIND[0]
        if isn and v._speculative:
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
        v, _isn = self._get(name.encode("utf-8"))
        if v is not None:
            return v
        if self._registry and name != "sequence" and name in self._registry:
            fn = self._registry[name]
            return lambda *a: fn(self, *a)
        return self._add_node(name.encode("utf-8"), 0, True)

    def __setattr__(self, name, val):
        if name.startswith("_"):
            object.__setattr__(self, name, val)
            return
        if _is_method_name(name.encode("utf-8")):
            raise TkvReservedName(f'name "{name}" is a tkv method/property')
        if self._registry and name != "sequence" and name in self._registry:
            raise TkvReservedName(f'name "{name}" is a registered function')
        self._confirm()
        self._leaf_write(name.encode("utf-8"), val, 0)

    def __getitem__(self, key):
        ck, nD = _key2idx(key)
        v, _isn = self._get(ck)
        if v is not None:
            return v
        if nD > 0:
            return self._add_node(ck, nD, True)
        return None

    def __setitem__(self, key, val):
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
        it, sk, da = self._istype, self._skeys, self._data
        parts = []
        for i in range(self._nfill):
            if it[i] >= 203:
                if da[i]._speculative:
                    continue
                parts.append(f"{sk[i]}:{da[i]!r}")
            elif it[i] > 0:
                parts.append(f"{sk[i]}:{_leafstr(da[i])}")
        return "{" + " ".join(parts) + "}"


def _leafstr(v):
    if v is None:
        return "''"
    if isinstance(v, tkv):
        return "#tkv"
    if isinstance(v, (list, tuple)):
        return "[" + ",".join(map(str, v)) + "]"
    return str(v)


def kvr(d, path, *args):
    return d.kvr(path, *args)


def kvw(d, path, val):
    d.kvw(path, val)
    return d
