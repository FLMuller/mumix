"""
kv.py — pure-Python kv with the option-B design (kvc2's ideas, no compilation).

Portable: a .py file has no cpXY-win ABI tag, so the SAME file runs on 3.13,
3.14, any CPython — unlike the kvc*.pyd, which must be rebuilt per interpreter.

Same open-addressing store as kv, but with kvc2's three wins, all of which are
free in pure Python:
  * keys stored as BYTES; the key compare is `==`, which in CPython is a C-level
    length check + memcmp on the bytes buffers (memcmp IS the built-in here).
  * hash is Python's hash(bytes) (siphash in C, cached on the object), not the
    per-character DJB2 loop kv/kvc run in Python — that loop was the real cost.
  * _key2idx is in-source and emits bytes directly (no str round-trip).
The parallel TYPE array is kept, so leaf/sparse enumeration is a contiguous scan
(the thing a dict cannot do).

NOTE: hash differs from kv.m, so probe ORDER is not algorithm-identical — kv is
the portable speed variant; kv / kvc keep the faithful DJB2 algorithm.
"""

N0   = 32                     # initial entry-buffer length
SZT0 = 64                     # initial index-table length (power of two)
TOMB = -1                     # _idx slot sentinels: 0 empty, -1 tomb, k>=1 entry k-1
M64  = 0xFFFFFFFFFFFFFFFF     # mask hash to 64-bit unsigned (matches the kvc2 cast)

__all__ = ["kv", "kvr", "kvw", "KvError", "KvSparseDimMismatch", "KvReservedParen"]


class KvError(Exception):            pass
class KvSparseDimMismatch(KvError): pass
class KvReservedParen(KvError):     pass


def _numb(x):
    # number -> bytes directly (one C format step; no str object, no encode).
    if isinstance(x, int):
        return b"%d" % x
    return b"%.15g" % x


def _key2idx(key):
    # -> (canonical bytes, nD).  Bytes throughout (store/hash/compare are bytes).
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


class kv:
    def __init__(self):
        self.clear()

    def clear(self):
        # object.__setattr__ throughout: our __setattr__ routes non-underscore
        # names to kvw(), so internals must bypass it.
        s = object.__setattr__
        s(self, "_szT", SZT0)
        s(self, "_mask", SZT0 - 1)
        s(self, "_idx", [0] * SZT0)
        s(self, "_hash", [0] * N0)
        s(self, "_type", [0] * N0)
        s(self, "_nbuf", N0)
        s(self, "_nUsed", 0)
        s(self, "_nfill", 0)
        s(self, "_cles", [None] * N0)    # bytes keys (hash/compare)
        s(self, "_skeys", [None] * N0)   # str keys (decode once at insert; enum is decode-free)
        s(self, "_data", [None] * N0)
        s(self, "_sparseD", 0)
        s(self, "_fslot", 0)
        return self

    # ── probe (read) ─────────────────────────────────────────────────────
    def _get(self, bkey):
        h = hash(bkey) & M64
        idx, hsh, cles, mask = self._idx, self._hash, self._cles, self._mask
        slot, perturb = h & mask, h
        while True:
            ei = idx[slot]
            if ei == 0:
                return None
            if ei != TOMB and hsh[ei - 1] == h and cles[ei - 1] == bkey:
                return self._data[ei - 1]
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
                return self._type[ei - 1]
            perturb >>= 5
            slot = (5 * slot + 1 + perturb) & mask

    # ── probe with tombstone bookkeeping (write/remove) ──────────────────
    def _find(self, bkey, h):
        # returns ei (0 if absent); writes the insertion slot to self._fslot.
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
                self._type[ei - 1] = 0
                object.__setattr__(self, "_nUsed", self._nUsed - 1)
            self._data[ei - 1] = val
            return
        elif val is None:
            return
        if ty < 202 and len(bkey) > 0 and bkey[0] == 40:    # b"("[0] == 40
            raise KvReservedParen("parenthesised keys are reserved; index with d[r, c]")
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
        self._hash[ei - 1] = h
        self._cles[ei - 1] = bkey
        self._skeys[ei - 1] = bkey.decode("utf-8")    # the one decode, at insert
        self._data[ei - 1] = val
        self._type[ei - 1] = ty
        self._idx[slot] = ei

    def _remove(self, bkey):
        h = hash(bkey) & M64
        ei = self._find(bkey, h)
        if ei == 0:
            return
        self._idx[self._fslot] = TOMB
        self._data[ei - 1] = None
        self._type[ei - 1] = 0
        object.__setattr__(self, "_nUsed", self._nUsed - 1)

    def _grow(self):
        ext = self._nbuf
        self._hash.extend([0] * ext)
        self._cles.extend([None] * ext)
        self._skeys.extend([None] * ext)
        self._data.extend([None] * ext)
        self._type.extend([0] * ext)
        object.__setattr__(self, "_nbuf", self._nbuf + ext)

    def _resize(self):
        n = self._nUsed
        new_szt = self._szT
        while new_szt < 4 * n:
            new_szt *= 2
        new_mask = new_szt - 1
        live = [i for i in range(self._nfill) if self._type[i] > 0]
        nh = [self._hash[i] for i in live]
        nc = [self._cles[i] for i in live]
        ns = [self._skeys[i] for i in live]
        nd = [self._data[i] for i in live]
        nt = [self._type[i] for i in live]
        ni = [0] * new_szt
        for k in range(n):
            hk = nh[k]
            perturb = hk
            s = hk & new_mask
            while ni[s] != 0:
                perturb >>= 5
                s = (5 * s + 1 + perturb) & new_mask
            ni[s] = k + 1
        self._hash[:n] = nh
        self._cles[:n] = nc
        self._skeys[:n] = ns
        self._data[:n] = nd
        self._type[:n] = nt
        object.__setattr__(self, "_idx", ni)
        object.__setattr__(self, "_nfill", n)
        object.__setattr__(self, "_szT", new_szt)
        object.__setattr__(self, "_mask", new_mask)

    # ── public API ──────────────────────────────────────────────────────
    def kvw(self, key, val):
        bkey, nD = _key2idx(key)
        if nD > 0:
            if self._sparseD == 0:
                object.__setattr__(self, "_sparseD", nD)
            elif self._sparseD != nD:
                raise KvSparseDimMismatch(
                    f"Sparse container is {self._sparseD}-D; got {nD}-D key.")
            ty = 202
        else:
            ty = 201
        self._set(bkey, val, ty)
        return self

    def kvr(self, key):
        return self._get(_key2idx(key)[0])

    def insert(self, *args):
        return self.kvw(list(args[:-1]) if len(args) > 2 else args[0], args[-1])

    def iskey(self, key):
        bkey = _key2idx(key)[0]
        return self._find(bkey, hash(bkey) & M64) > 0

    def remove(self, key):
        self._remove(_key2idx(key)[0])

    def isEmpty(self):
        return self._nUsed == 0

    def kind(self, key):
        return self._typeof(_key2idx(key)[0])

    def numEntries(self):
        t = self._type
        return sum(1 for i in range(self._nfill) if 0 < t[i] < 202)

    def keys(self):
        t, sk = self._type, self._skeys
        return [sk[i] for i in range(self._nfill) if 0 < t[i] < 202]

    def vals(self):
        t, d = self._type, self._data
        return [d[i] for i in range(self._nfill) if 0 < t[i] < 202]

    def indici(self):
        t, sk = self._type, self._skeys
        return [sk[i] for i in range(self._nfill) if t[i] == 202]

    def icount(self):
        t = self._type
        return sum(1 for i in range(self._nfill) if t[i] == 202)

    def idim(self):
        return self._sparseD

    def __getattr__(self, name):
        # only fired when normal lookup misses; internals exist so never reach here
        if name.startswith("_"):
            raise AttributeError(name)
        return self._get(name.encode("utf-8"))

    def __setattr__(self, name, val):
        if name.startswith("_"):
            object.__setattr__(self, name, val)
        else:
            self.kvw(name, val)

    def __getitem__(self, key):
        return self._get(_key2idx(key)[0])

    def __setitem__(self, key, val):
        self.kvw(key, val)

    def __delitem__(self, key):
        self.remove(key)

    def __contains__(self, key):
        return self.iskey(key)

    def __len__(self):
        return self._nUsed

    def __repr__(self):
        t, sk, d = self._type, self._skeys, self._data
        leaves = [(sk[i], d[i]) for i in range(self._nfill) if 0 < t[i] < 202]
        sparse = [(sk[i], d[i]) for i in range(self._nfill) if t[i] == 202]
        s = "{" + " ".join(f"{k}:{_render(v)}" for k, v in leaves)
        if sparse:
            s += " [" + " ".join(f"{k}:{_render(v)}" for k, v in sparse) + "]"
        return s + "}"


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
