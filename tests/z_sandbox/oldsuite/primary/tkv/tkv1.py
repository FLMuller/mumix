"""
tkv1.py — Tree dictionary: nodes AND leaves in one merged hash store.
Python port of MATLAB tkv.m v8.1 — ALGORITHM-IDENTICAL store.
VERSION: 2.0

Faithful translation of tkv.m's MERGED open-addressing hash: ONE parallel-array
store per node holds child NODES and leaf VALUES, told apart by the uint8 istype
flag (kvGet returns value + node-flag in one probe). Same DJB2+finaliser hash and
perturbed probe as kv.m. The tree layer (dotted kvw/kvr, node autoviv, typed
registry) rides on top; attribute autovivification still uses speculative nodes
(the one Python adaptation — see below).

istype codes (tkv.m): 0 dead | 201 leaf | 202 sparse-leaf | 203 node | 204 sparse-node.
Entry indices are 1-based as in tkv.m; Python lists indexed at k-1.

Python adaptations (unchanged from v1):
  - attribute autovivification via speculative nodes (t.a.b.c = 9); a bare read
    of a missing name returns an empty speculative node — use .isEmpty().
  - registered functions are called with parens (R.val(), R.dbl(5)).
  - structs -> dict / SimpleNamespace; some MATLAB subsasgn-grow idioms dropped.
"""

from __future__ import annotations

from key2idx import key2idx

_SEED, _MOD, _M32, _TOMB, _N0, _SZT0 = 130150524, 4294967296, 0xFFFFFFFF, 0xFFFFFFFF, 32, 64
_KIND = {0: "key not found", 201: "leaf", 202: "leaf(sparse)",
         203: "tkv", 204: "tkv(sparse)"}
_METHODS = None


class Tkv1Error(Exception):              pass
class Tkv1BadRegistry(Tkv1Error):         pass
class Tkv1DuplicateName(Tkv1Error):       pass
class Tkv1ReservedName(Tkv1Error):        pass
class Tkv1ReservedParen(Tkv1Error):       pass
class Tkv1SparseDimMismatch(Tkv1Error):   pass
class Tkv1SparseKindMismatch(Tkv1Error):  pass


def _is_method_name(name):
    global _METHODS
    if _METHODS is None:
        _METHODS = {n for n in dir(tkv1) if not n.startswith("_")}
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


class tkv1:

    # ── construction ──────────────────────────────────────────────────
    def __init__(self, types=None, **handlers):
        self._init_store()
        object.__setattr__(self, "_registry", None)
        object.__setattr__(self, "_type", "")
        object.__setattr__(self, "_nextType", "")
        object.__setattr__(self, "_parent", None)
        object.__setattr__(self, "_name", "")
        object.__setattr__(self, "_speculative", False)
        if types is None:
            return
        self._init_typed(types, handlers)

    def _init_store(self):
        # the merged open-addressing hash (tkv.m clear)
        object.__setattr__(self, "_szT",    _SZT0)
        object.__setattr__(self, "_mask",   _SZT0 - 1)
        object.__setattr__(self, "_idx",    [0] * _SZT0)
        object.__setattr__(self, "_hash",   [0] * _N0)
        object.__setattr__(self, "_istype", [0] * _N0)
        object.__setattr__(self, "_nbuf",   _N0)
        object.__setattr__(self, "_nUsed",  0)
        object.__setattr__(self, "_nfill",  0)
        object.__setattr__(self, "_cles",   [None] * _N0)
        object.__setattr__(self, "_data",   [None] * _N0)
        object.__setattr__(self, "_sparseD", 0)
        object.__setattr__(self, "_sparseKind", 0)

    @classmethod
    def _child(cls, parent, name):
        nd = cls.__new__(cls)
        nd._init_store()
        object.__setattr__(nd, "_registry", parent._registry)
        object.__setattr__(nd, "_type", parent._nextType)
        object.__setattr__(nd, "_nextType", _type_after(parent._registry, parent._nextType))
        object.__setattr__(nd, "_parent", parent)
        object.__setattr__(nd, "_name", name)
        object.__setattr__(nd, "_speculative", False)
        return nd

    def _init_typed(self, types, handlers):
        types = [types] if isinstance(types, str) else list(types)
        if len(set(types)) != len(types):
            return                                   # duplicate types -> untyped
        reg = {"sequence": types}
        for nm, fn in handlers.items():
            if nm == "sequence":
                raise Tkv1BadRegistry('"sequence" is a reserved registry key.')
            if not callable(fn):
                raise Tkv1BadRegistry(f'Handler "{nm}" must be callable.')
            reg[nm] = fn
        object.__setattr__(self, "_registry", reg)
        object.__setattr__(self, "_type", types[0])
        object.__setattr__(self, "_nextType", _type_after(reg, types[0]))

    def clear(self):
        self._init_store()
        return self

    # ════════════════════════════════════════════════════════════════
    # Merged-hash internals (tkv.m verbatim): kvGet returns value + node flag
    # ════════════════════════════════════════════════════════════════
    def _hashkey(self, ckey):
        h = _SEED
        for c in ckey:
            h = (h * 33 + ord(c)) % _MOD
        h ^= (h << 17) & _M32
        return h

    def _get(self, ckey):
        # returns (value, isnode); (None, False) on miss. isnode = istype >= 203.
        h = self._hashkey(ckey)
        idx, hsh, cles, mask = self._idx, self._hash, self._cles, self._mask
        perturb = h
        slot = h & mask
        while True:
            ei = idx[slot]
            if ei == 0:
                return None, False
            if ei < _TOMB and hsh[ei - 1] == h and cles[ei - 1] == ckey:
                return self._data[ei - 1], self._istype[ei - 1] >= 203
            perturb >>= 5
            slot = ((5 * slot + 1) + perturb) & mask

    def _typeof(self, ckey):
        h = self._hashkey(ckey)
        idx, hsh, cles, mask = self._idx, self._hash, self._cles, self._mask
        perturb = h
        slot = h & mask
        while True:
            ei = idx[slot]
            if ei == 0:
                return 0
            if ei < _TOMB and hsh[ei - 1] == h and cles[ei - 1] == ckey:
                return self._istype[ei - 1]
            perturb >>= 5
            slot = ((5 * slot + 1) + perturb) & mask

    def _find(self, ckey, h=None):
        if h is None:
            h = self._hashkey(ckey)
        idx, hsh, cles, mask = self._idx, self._hash, self._cles, self._mask
        perturb = h
        slot = h & mask
        first_dummy = -1
        while True:
            ei = idx[slot]
            if ei == 0:
                return ei, (first_dummy if first_dummy >= 0 else slot), h
            elif ei == _TOMB:
                if first_dummy < 0:
                    first_dummy = slot
            else:
                if hsh[ei - 1] == h and cles[ei - 1] == ckey:
                    return ei, slot, h
            perturb >>= 5
            slot = ((5 * slot + 1) + perturb) & mask

    def _set(self, ckey, val, ty):
        ei, slot, h = self._find(ckey)
        b = val is None
        if ei > 0:
            if b:
                self._idx[slot] = _TOMB
                self._istype[ei - 1] = 0
                self._nUsed -= 1
            self._data[ei - 1] = val                 # overwrite: istype invariant
            return
        elif b:
            return
        if ckey[:1] == "(" and ty not in (202, 204):
            raise Tkv1ReservedParen("parenthesised keys are reserved; index with t[r, c]")
        nf = self._nfill
        if 3 * (nf + 1) > 2 * self._szT:
            self._resize()
            _, slot, _ = self._find(ckey, h)
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

    def _remove(self, ckey):
        ei, slot, _ = self._find(ckey)
        if ei == 0:
            return
        self._idx[slot]      = _TOMB
        self._data[ei - 1]   = None
        self._istype[ei - 1] = 0
        self._nUsed -= 1

    def _grow(self):
        ext = self._nbuf
        self._hash   += [0] * ext
        self._cles   += [None] * ext
        self._data   += [None] * ext
        self._istype += [0] * ext
        self._nbuf   += ext

    def _resize(self):
        n = self._nUsed
        new_szt = self._szT
        while new_szt < 4 * n:
            new_szt *= 2
        new_mask = new_szt - 1
        live = [i for i in range(self._nfill) if self._istype[i] > 0]
        nh = [self._hash[i] for i in live]
        nc = [self._cles[i] for i in live]
        nd = [self._data[i] for i in live]
        nt = [self._istype[i] for i in live]
        ni = [0] * new_szt
        for k in range(n):
            hk = nh[k]
            perturb = hk
            s = hk & new_mask
            while ni[s] != 0:
                perturb >>= 5
                s = ((5 * s + 1) + perturb) & new_mask
            ni[s] = k + 1
        self._hash[:n]   = nh
        self._cles[:n]   = nc
        self._data[:n]   = nd
        self._istype[:n] = nt
        self._idx   = ni
        self._nfill = n
        self._szT   = new_szt
        self._mask  = new_mask

    # ════════════════════════════════════════════════════════════════
    # Tree write layer
    # ════════════════════════════════════════════════════════════════
    def _sparse_gate(self, kind, nD):
        if self._sparseD == 0:
            object.__setattr__(self, "_sparseD", nD)
        elif self._sparseD != nD:
            raise Tkv1SparseDimMismatch(
                f"Sparse container is {self._sparseD}-D; got {nD}-D key.")
        if self._sparseKind == 0:
            object.__setattr__(self, "_sparseKind", kind)
        elif self._sparseKind != kind:
            raise Tkv1SparseKindMismatch(
                "Sparse container holds %s; cannot add a sparse %s." % (
                    "NODE" if self._sparseKind == 204 else "LEAF",
                    "NODE" if kind == 204 else "LEAF"))

    def _add_node(self, ck, nD, speculative=False):
        if _is_method_name(ck):
            raise Tkv1ReservedName(f'name "{ck}" is a tkv method/property')
        if nD > 0:
            self._sparse_gate(204, nD)
            ty = 204
        else:
            ty = 203
        child = tkv1._child(self, ck)
        if self._registry is not None and self._nextType == "":
            object.__setattr__(child, "_registry", None)
        object.__setattr__(child, "_speculative", speculative)
        self._set(ck, child, ty)                     # _set guards reserved parens
        return child

    def _leaf_set(self, ck, val, nD):
        if self._typeof(ck) >= 203:
            raise Tkv1DuplicateName(f'name "{ck}" is already a node')
        if nD > 0:
            self._sparse_gate(202, nD)
            ty = 202
        else:
            ty = 201
        self._set(ck, val, ty)                       # overwrite keeps istype

    def _leaf_write(self, ck, val, nD):
        if val is None:
            self._remove(ck)
            return
        v, isn = self._get(ck)
        if v is not None and isn:
            if v._speculative:
                self._remove(ck)                     # replace speculative node
            else:
                raise Tkv1DuplicateName(f'name "{ck}" is already a node')
        self._leaf_set(ck, val, nD)

    def _confirm(self):
        node = self
        while node is not None:
            if node._speculative:
                object.__setattr__(node, "_speculative", False)
            node = node._parent

    # ── function-form path API ────────────────────────────────────────
    def kvw(self, path, val):
        cpath, nD = key2idx(path)
        if "." not in cpath:
            self._leaf_write(cpath, val, nD)
            return
        segs = cpath.split(".")
        cur = self
        for seg in segs[:-1]:
            nd, isn = cur._get(seg)
            if nd is None:
                nd = cur._add_node(seg, 0)
            elif not isn:
                raise Tkv1DuplicateName(f'path segment "{seg}" is already a leaf')
            cur = nd
        cur._leaf_write(segs[-1], val, 0)

    def kvr(self, path, *args):
        if isinstance(path, str) and "." not in path:
            v, isn = self._get(path)
            if v is not None and not (isn and v._speculative):
                if args and isn:
                    return v.kvr(*args)
                return v
            if self._registry and path != "sequence" and path in self._registry:
                return self._registry[path](self, *args)
            return None
        cpath, _ = key2idx(path)
        if "." not in cpath:
            return self.kvr(cpath, *args)
        segs = cpath.split(".")
        cur = self
        for seg in segs[:-1]:
            v, isn = cur._get(seg)
            if v is None or not isn:
                return None
            cur = v
        return cur.kvr(segs[-1], *args)

    def insert(self, *args):
        ck, nD = key2idx(list(args[:-1]) if len(args) > 2 else args[0])
        self._leaf_write(ck, args[-1], nD)
        return self

    def node(self, path, *extra):
        ck, nD = key2idx([path, *extra]) if extra else key2idx(path)
        v, isn = self._get(ck)
        if v is None:
            return self._add_node(ck, nD)
        if not isn:
            raise Tkv1DuplicateName(f'node name "{ck}" already exists as leaf')
        return v

    def remove(self, key):
        self._remove(key2idx(key)[0])

    # ── store scans (live; speculative nodes filtered) ────────────────
    def _live_nodes(self):
        out = []
        it, cl, da = self._istype, self._cles, self._data
        for i in range(self._nfill):
            if it[i] >= 203 and not da[i]._speculative:
                out.append((cl[i], da[i]))
        return out

    def count(self):
        return len(self._live_nodes())

    def names(self):
        return [k for k, _ in self._live_nodes()]

    def nodes(self):
        return [v for _, v in self._live_nodes()]

    def hasNodes(self):
        return bool(self._live_nodes())

    def isnode(self, name):
        v, isn = self._get(key2idx(name)[0])
        return v is not None and isn and not v._speculative

    def keys(self):
        it, cl = self._istype, self._cles
        return [cl[i] for i in range(self._nfill) if 0 < it[i] < 202]

    def vals(self):
        it, da = self._istype, self._data
        return [da[i] for i in range(self._nfill) if 0 < it[i] < 202]

    def numEntries(self):
        it = self._istype
        return sum(1 for i in range(self._nfill) if 0 < it[i] < 202)

    def entries(self):
        it, cl, da = self._istype, self._cles, self._data
        return [[cl[i], da[i]] for i in range(self._nfill) if 0 < it[i] < 202]

    def iskey(self, key):
        ck = key2idx(key)[0]
        if ck[:1] == "(":
            return False
        v, isn = self._get(ck)
        return v is not None and not isn

    def indici(self):
        it, cl = self._istype, self._cles
        return [cl[i] for i in range(self._nfill) if it[i] in (202, 204)]

    def icount(self):
        it = self._istype
        return sum(1 for i in range(self._nfill) if it[i] in (202, 204))

    def idim(self):
        return self._sparseD

    def indexisnode(self):
        return self._sparseKind == 204

    def kind(self, key):
        ck = key2idx(key)[0]
        v, isn = self._get(ck)
        if v is None or (isn and v._speculative):
            return _KIND[0]
        return _KIND.get(self._typeof(ck), f"leaf({self._typeof(ck)})")

    # ── identity ──────────────────────────────────────────────────────
    def parent(self): return self._parent
    def name(self):   return self._name
    def type(self):   return self._type

    def isEmpty(self):
        return self.count() == 0 and self.numEntries() == 0 and self.icount() == 0

    # ── attribute access = tree walk / autoviv ────────────────────────
    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        v, isn = self._get(name)
        if v is not None:
            return v
        reg = object.__getattribute__(self, "_registry")
        if reg and name != "sequence" and name in reg:
            fn = reg[name]
            return lambda *a: fn(self, *a)
        return self._add_node(name, 0, speculative=True)

    def __setattr__(self, name, val):
        if name.startswith("_"):
            object.__setattr__(self, name, val)
            return
        if _is_method_name(name):
            raise Tkv1ReservedName(f'name "{name}" is a tkv method/property')
        reg = object.__getattribute__(self, "_registry")
        if reg and name != "sequence" and name in reg:
            raise Tkv1ReservedName(f'name "{name}" is a registered function')
        self._confirm()
        self._leaf_write(name, val, 0)

    # ── item access = raw store doorway ───────────────────────────────
    def __getitem__(self, key):
        ck, nD = key2idx(key)
        v, _ = self._get(ck)
        if v is not None:
            return v
        if nD > 0:
            return self._add_node(ck, nD, speculative=True)
        return None

    def __setitem__(self, key, val):
        ck, nD = key2idx(key)
        self._confirm()
        self._leaf_write(ck, val, nD)

    def __delitem__(self, key):
        self.remove(key)

    def __contains__(self, key):
        return self.iskey(key)

    # ── display ───────────────────────────────────────────────────────
    def string(self):
        return repr(self)

    def __repr__(self):
        it, cl, da = self._istype, self._cles, self._data
        parts = []
        for i in range(self._nfill):
            if it[i] >= 203:
                if da[i]._speculative:
                    continue
                parts.append(f"{cl[i]}:{da[i]!r}")
            elif 0 < it[i]:
                parts.append(f"{cl[i]}:{_leafstr(da[i])}")
        return "{" + " ".join(parts) + "}"


def _leafstr(v):
    if v is None:
        return "''"
    if isinstance(v, tkv1):
        return "#tkv"
    if isinstance(v, (list, tuple)):
        return "[" + ",".join(map(str, v)) + "]"
    return str(v)


def kvr(d, path, *args):
    return d.kvr(path, *args)


def kvw(d, path, val):
    d.kvw(path, val)
    return d
