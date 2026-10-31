"""
kv1.py — Standalone hash map with attribute- and item-access syntax.
Python port of MATLAB kv.m v7.0 — ALGORITHM-IDENTICAL.
VERSION: 2.0

This is a faithful translation of kv.m's open-addressing hash table, NOT a
wrapper over Python's dict. One parallel-array store (idx / hash / cles / data /
type), a modified-DJB2 hash with a bitwise finaliser, and a CPython-style
perturbed probe with tombstones — exactly as kv.m. Pure-Python probing is slower
than the C dict; the point here is algorithmic fidelity, not raw speed.

Store layout (kv.m verbatim):
    _idx    index table, len szT: 0=empty, 0xFFFFFFFF=tombstone, k>0 = entry k
    _hash   cached uint32 hashes,    len nbuf   (entry k at _hash[k-1])
    _cles   key strings,             len nbuf
    _data   values,                  len nbuf
    _type   uint8 flags: 0=dead, 201=leaf, 202=sparse-leaf
    _nUsed _nfill _szT _mask _nbuf _sparseD   bookkeeping
Entry indices are 1-based (as in kv.m); Python lists are indexed at k-1.

Public contract (unchanged from the dict version, so the tests still hold):
  attribute / item / kvr-kvw access, canonical sparse keys via key2idx,
  reserved parens, dim gate, leaf/sparse partition, miss -> None, [] -> None
  deletes, reference semantics.
"""

from __future__ import annotations

from key2idx import key2idx

_SEED  = 130150524        # kv.m hash seed
_MOD   = 4294967296       # 2**32
_M32   = 0xFFFFFFFF       # uint32 mask
_TOMB  = 0xFFFFFFFF       # tombstone marker in the index table
_N0    = 32               # initial buffer (power of two)
_SZT0  = 64               # initial index table = 2*N0 (power of two)


class Kv1Error(Exception):           pass
class Kv1SparseDimMismatch(Kv1Error): pass
class Kv1ReservedParen(Kv1Error):     pass


class kv1:

    # ── construction / reset ──────────────────────────────────────────
    def __init__(self):
        self.clear()

    def clear(self):
        """Reset to empty — re-seeds the index table and parallel buffers."""
        self._szT     = _SZT0
        self._mask    = _SZT0 - 1
        self._idx     = [0] * _SZT0
        self._hash    = [0] * _N0
        self._type    = [0] * _N0
        self._nbuf    = _N0
        self._nUsed   = 0
        self._nfill   = 0
        self._cles    = [None] * _N0
        self._data    = [None] * _N0
        self._sparseD = 0

    # ── the hash: modified DJB2 + bitwise finaliser (kv.m verbatim) ────
    def _hashkey(self, ckey):
        h = _SEED
        for c in ckey:
            h = (h * 33 + ord(c)) % _MOD
        h ^= (h << 17) & _M32       # bitxor(h, bitshift(h,17)) on uint32
        return h

    # ── probe: read-only fast path (kvGet) — [] / None on miss ─────────
    def _get(self, ckey):
        h = self._hashkey(ckey)
        idx, hsh, cles, mask = self._idx, self._hash, self._cles, self._mask
        perturb = h
        slot = h & mask
        while True:
            ei = idx[slot]
            if ei == 0:
                return None
            if ei < _TOMB and hsh[ei - 1] == h and cles[ei - 1] == ckey:
                return self._data[ei - 1]
            perturb >>= 5
            slot = ((5 * slot + 1) + perturb) & mask

    # ── probe with tombstone bookkeeping (kvFind): (ei, slot, h) ───────
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
                if first_dummy >= 0:
                    slot = first_dummy
                return ei, slot, h
            elif ei == _TOMB:
                if first_dummy < 0:
                    first_dummy = slot
            else:
                if hsh[ei - 1] == h and cles[ei - 1] == ckey:
                    return ei, slot, h
            perturb >>= 5
            slot = ((5 * slot + 1) + perturb) & mask

    # ── type-flag probe (kvType): 201/202, or 0 if absent ──────────────
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
                return self._type[ei - 1]
            perturb >>= 5
            slot = ((5 * slot + 1) + perturb) & mask

    # ── the write gate (kvSet): insert / overwrite / delete ────────────
    def _set(self, ckey, val, ty):
        h = self._hashkey(ckey)
        idx, hsh, cles, mask = self._idx, self._hash, self._cles, self._mask
        perturb = h
        slot = h & mask
        first_dummy = -1
        while True:                                  # inline probe (kv.m hot path)
            ei = idx[slot]
            if ei == 0:
                if first_dummy >= 0:
                    slot = first_dummy
                break
            elif ei == _TOMB:
                if first_dummy < 0:
                    first_dummy = slot
            else:
                if hsh[ei - 1] == h and cles[ei - 1] == ckey:
                    break
            perturb >>= 5
            slot = ((5 * slot + 1) + perturb) & mask

        b = val is None                              # empty sentinel -> delete
        if ei > 0:                                   # key already present
            if b:
                idx[slot] = _TOMB
                self._type[ei - 1] = 0
                self._nUsed -= 1
            self._data[ei - 1] = val                 # overwrite keeps type
            return
        elif b:
            return                                   # delete of a missing key

        # Reserved parens: a NEW '(' key may only be made by an index form.
        if ty < 202 and ckey[:1] == "(":
            raise Kv1ReservedParen(
                "parenthesised keys are reserved; index with d[r, c]")

        nf = self._nfill
        if 3 * (nf + 1) > 2 * self._szT:
            self._resize()
            _, slot, _ = self._find(ckey, h)         # idx rebuilt — re-probe
            nf = self._nfill
        ei = nf + 1
        self._nfill = ei
        self._nUsed += 1
        if ei > self._nbuf:
            self._grow()
        self._hash[ei - 1] = h
        self._cles[ei - 1] = ckey
        self._data[ei - 1] = val
        self._type[ei - 1] = ty
        self._idx[slot]    = ei

    def _remove(self, ckey):
        ei, slot, _ = self._find(ckey)
        if ei == 0:
            return
        self._idx[slot]    = _TOMB
        self._data[ei - 1] = None
        self._type[ei - 1] = 0
        self._nUsed -= 1

    def _grow(self):
        newbuf = self._nbuf * 2
        ext = newbuf - self._nbuf
        self._hash += [0] * ext
        self._cles += [None] * ext
        self._data += [None] * ext
        self._type += [0] * ext
        self._nbuf = newbuf

    def _resize(self):
        n = self._nUsed
        new_szt = self._szT
        while new_szt < 4 * n:
            new_szt *= 2
        new_mask = new_szt - 1
        live = [i for i in range(self._nfill) if self._type[i] > 0]   # drop tombs
        nh   = [self._hash[i] for i in live]
        nc   = [self._cles[i] for i in live]
        nd   = [self._data[i] for i in live]
        nt   = [self._type[i] for i in live]
        ni = [0] * new_szt
        for k in range(n):                            # rehash into the new table
            hk = nh[k]
            perturb = hk
            s = hk & new_mask
            while ni[s] != 0:
                perturb >>= 5
                s = ((5 * s + 1) + perturb) & new_mask
            ni[s] = k + 1
        self._hash[:n] = nh
        self._cles[:n] = nc
        self._data[:n] = nd
        self._type[:n] = nt
        self._idx  = ni
        self._nfill = n
        self._szT   = new_szt
        self._mask  = new_mask

    # ── public write gate: classify + dim-gate, then _set ──────────────
    def kvw(self, key, val):
        ckey, nD = key2idx(key)
        if nD > 0:
            if self._sparseD == 0:
                self._sparseD = nD
            elif self._sparseD != nD:
                raise Kv1SparseDimMismatch(
                    f"Sparse container is {self._sparseD}-D; got {nD}-D key.")
            ty = 202
        else:
            ty = 201
        self._set(ckey, val, ty)
        return self

    def kvr(self, key):
        return self._get(key2idx(key)[0])

    def insert(self, *args):
        return self.kvw(list(args[:-1]) if len(args) > 2 else args[0], args[-1])

    # ── queries ───────────────────────────────────────────────────────
    def iskey(self, key):
        ei, _, _ = self._find(key2idx(key)[0])
        return ei > 0

    def remove(self, key):
        self._remove(key2idx(key)[0])

    def isEmpty(self):
        return self._nUsed == 0

    def kind(self, key):
        return self._typeof(key2idx(key)[0])

    # ── leaf partition (0 < type < 202), in fill order ─────────────────
    def numEntries(self):
        t = self._type
        return sum(1 for i in range(self._nfill) if 0 < t[i] < 202)

    def keys(self):
        t, c = self._type, self._cles
        return [c[i] for i in range(self._nfill) if 0 < t[i] < 202]

    def vals(self):
        t, d = self._type, self._data
        return [d[i] for i in range(self._nfill) if 0 < t[i] < 202]

    # ── sparse partition (type == 202) ────────────────────────────────
    def indici(self):
        t, c = self._type, self._cles
        return [c[i] for i in range(self._nfill) if t[i] == 202]

    def icount(self):
        t = self._type
        return sum(1 for i in range(self._nfill) if t[i] == 202)

    def idim(self):
        return self._sparseD

    # ── attribute access = data keys (fires only for non-members) ─────
    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)               # internal / dunder, not a key
        return self._get(name)                       # miss -> None

    def __setattr__(self, name, val):
        if name.startswith("_"):
            object.__setattr__(self, name, val)      # internal hash state
        else:
            self.kvw(name, val)                      # data key -> write gate

    # ── item access = raw store doorway (any text / sparse keys) ──────
    def __getitem__(self, key):
        return self._get(key2idx(key)[0])

    def __setitem__(self, key, val):
        self.kvw(key, val)

    def __delitem__(self, key):
        self.remove(key)

    def __contains__(self, key):
        return self.iskey(key)

    def __len__(self):
        return self._nUsed

    # ── display (cold path) ───────────────────────────────────────────
    def __repr__(self):
        t, c, d, nf = self._type, self._cles, self._data, self._nfill
        leaves = [(c[i], d[i]) for i in range(nf) if 0 < t[i] < 202]
        sparse = [(c[i], d[i]) for i in range(nf) if t[i] == 202]
        s = "{" + " ".join(f"{k}:{_render(v)}" for k, v in leaves)
        if sparse:
            s += " [" + " ".join(f"{k}:{_render(v)}" for k, v in sparse) + "]"
        return s + "}"


# ════════════════════════════════════════════════════════════════
# Module-level fast-path functions (MATLAB's kvr(d,k) / kvw(d,k,v) form)
# ════════════════════════════════════════════════════════════════
def kvr(d, key):
    return d.kvr(key)


def kvw(d, key, val):
    return d.kvw(key, val)


def _render(v):
    if v is None:
        return "''"
    if isinstance(v, (list, tuple)):
        return "[" + ",".join(_render(x) for x in v) + "]"
    return str(v)
