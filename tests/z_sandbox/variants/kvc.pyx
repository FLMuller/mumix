# cython: language_level=3, boundscheck=False, wraparound=False
"""
kvc.pyx — Cython build of kv. Same open-addressing algorithm as kv.py / kv.m,
but the probe arithmetic and array indexing run as C. Public API is byte-
identical to kv (attribute / item / kvr-kvw, sparse keys, reserved parens, dim
gate), so kvc is a drop-in — kept under a DISTINCT name so it benches head-to-
head against the pure-Python kv (lab-notebook style).

    from kvc import kvc
    d = kvc(); d.x = 5; d[2, 3] = 99; d.kvr('x')

Build:  python primary/setup.py build_ext --inplace
"""

from key2idx import key2idx

DEF SEED  = 130150524
DEF MOD   = 4294967296
DEF M32   = 0xFFFFFFFF
DEF TOMB  = 0xFFFFFFFF
DEF N0    = 32
DEF SZT0  = 64


class KvcError(Exception):           pass
class KvcSparseDimMismatch(KvcError): pass
class KvcReservedParen(KvcError):     pass


cdef class kvc:
    cdef list _idx, _hash, _cles, _data, _type
    cdef unsigned long long _mask
    cdef Py_ssize_t _szT, _nbuf, _nUsed, _nfill, _sparseD, _fslot

    def __init__(self):
        self.clear()

    def clear(self):
        self._szT     = SZT0
        self._mask    = SZT0 - 1
        self._idx     = [0] * SZT0
        self._hash    = [0] * N0
        self._type    = [0] * N0
        self._nbuf    = N0
        self._nUsed   = 0
        self._nfill   = 0
        self._cles    = [None] * N0
        self._data    = [None] * N0
        self._sparseD = 0

    # ── hash: modified DJB2 + bitwise finaliser (kv.m verbatim) ────────
    cdef unsigned long long _hashkey(self, str ckey):
        cdef unsigned long long h = SEED
        cdef Py_UCS4 ch
        for ch in ckey:                       # Cython code-point iteration
            h = (h * 33 + <unsigned long long>ch) % MOD
        h ^= (h << 17) & M32
        return h

    # ── read-only probe (kvGet) ────────────────────────────────────────
    cdef _get(self, str ckey):
        cdef unsigned long long h = self._hashkey(ckey), perturb = h
        cdef Py_ssize_t slot = <Py_ssize_t>(h & self._mask)
        cdef unsigned long long ei
        cdef list idx = self._idx, hsh = self._hash, cles = self._cles
        while True:
            ei = idx[slot]
            if ei == 0:
                return None
            if ei < TOMB and <unsigned long long>hsh[ei - 1] == h and cles[ei - 1] == ckey:
                return self._data[ei - 1]
            perturb >>= 5
            slot = <Py_ssize_t>(((5 * <unsigned long long>slot + 1) + perturb) & self._mask)

    # ── probe with tombstone bookkeeping (kvFind) ──────────────────────
    cdef Py_ssize_t _find_slot(self, str ckey, unsigned long long h):
        # returns ei (0 if absent); writes the insertion slot to self._fslot
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

    cdef int _typeof(self, str ckey):
        cdef unsigned long long h = self._hashkey(ckey), perturb = h, ei
        cdef Py_ssize_t slot = <Py_ssize_t>(h & self._mask)
        cdef list idx = self._idx, hsh = self._hash, cles = self._cles
        while True:
            ei = idx[slot]
            if ei == 0:
                return 0
            if ei < TOMB and <unsigned long long>hsh[ei - 1] == h and cles[ei - 1] == ckey:
                return self._type[ei - 1]
            perturb >>= 5
            slot = <Py_ssize_t>(((5 * <unsigned long long>slot + 1) + perturb) & self._mask)

    # ── write gate (kvSet) ──────────────────────────────────────────────
    cdef _set(self, str ckey, val, int ty):
        cdef unsigned long long h = self._hashkey(ckey)
        cdef Py_ssize_t ei = self._find_slot(ckey, h)
        cdef Py_ssize_t slot = self._fslot
        cdef bint b = val is None
        cdef Py_ssize_t nf
        if ei > 0:
            if b:
                self._idx[slot] = TOMB
                self._type[ei - 1] = 0
                self._nUsed -= 1
            self._data[ei - 1] = val
            return
        elif b:
            return
        if ty < 202 and len(ckey) > 0 and ckey[0] == u"(":
            raise KvcReservedParen("parenthesised keys are reserved; index with d[r, c]")
        nf = self._nfill
        if 3 * (nf + 1) > 2 * self._szT:
            self._resize()
            self._find_slot(ckey, h)
            slot = self._fslot
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
        self._idx[slot] = ei

    cdef _remove(self, str ckey):
        cdef unsigned long long h = self._hashkey(ckey)
        cdef Py_ssize_t ei = self._find_slot(ckey, h)
        if ei == 0:
            return
        self._idx[self._fslot] = TOMB
        self._data[ei - 1] = None
        self._type[ei - 1] = 0
        self._nUsed -= 1

    cdef _grow(self):
        cdef Py_ssize_t newbuf = self._nbuf * 2, ext = self._nbuf
        self._hash += [0] * ext
        self._cles += [None] * ext
        self._data += [None] * ext
        self._type += [0] * ext
        self._nbuf = newbuf

    cdef _resize(self):
        cdef Py_ssize_t n = self._nUsed, new_szt = self._szT
        while new_szt < 4 * n:
            new_szt *= 2
        cdef unsigned long long new_mask = new_szt - 1
        cdef list live = [i for i in range(self._nfill) if self._type[i] > 0]
        cdef list nh = [self._hash[i] for i in live]
        cdef list nc = [self._cles[i] for i in live]
        cdef list nd = [self._data[i] for i in live]
        cdef list nt = [self._type[i] for i in live]
        cdef list ni = [0] * new_szt
        cdef Py_ssize_t k, s
        cdef unsigned long long hk, perturb
        for k in range(n):
            hk = nh[k]
            perturb = hk
            s = <Py_ssize_t>(hk & new_mask)
            while ni[s] != 0:
                perturb >>= 5
                s = <Py_ssize_t>(((5 * <unsigned long long>s + 1) + perturb) & new_mask)
            ni[s] = k + 1
        self._hash[:n] = nh
        self._cles[:n] = nc
        self._data[:n] = nd
        self._type[:n] = nt
        self._idx  = ni
        self._nfill = n
        self._szT   = new_szt
        self._mask  = new_mask

    # ── public API ──────────────────────────────────────────────────────
    def kvw(self, key, val):
        cdef object ckey
        cdef int nD, ty
        ckey, nD = key2idx(key)
        if nD > 0:
            if self._sparseD == 0:
                self._sparseD = nD
            elif self._sparseD != nD:
                raise KvcSparseDimMismatch(
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

    def iskey(self, key):
        return self._find_slot(key2idx(key)[0], self._hashkey(key2idx(key)[0])) > 0

    def remove(self, key):
        self._remove(key2idx(key)[0])

    def isEmpty(self):
        return self._nUsed == 0

    def kind(self, key):
        return self._typeof(key2idx(key)[0])

    def numEntries(self):
        cdef Py_ssize_t i, c = 0, nf = self._nfill
        cdef list t = self._type
        for i in range(nf):
            if 0 < <int>t[i] < 202:
                c += 1
        return c

    def keys(self):
        cdef Py_ssize_t i, nf = self._nfill
        cdef list t = self._type, cl = self._cles
        return [cl[i] for i in range(nf) if 0 < <int>t[i] < 202]

    def vals(self):
        cdef Py_ssize_t i, nf = self._nfill
        cdef list t = self._type, d = self._data
        return [d[i] for i in range(nf) if 0 < <int>t[i] < 202]

    def indici(self):
        cdef Py_ssize_t i, nf = self._nfill
        cdef list t = self._type, cl = self._cles
        return [cl[i] for i in range(nf) if <int>t[i] == 202]

    def icount(self):
        cdef Py_ssize_t i, c = 0, nf = self._nfill
        cdef list t = self._type
        for i in range(nf):
            if <int>t[i] == 202:
                c += 1
        return c

    def idim(self):
        return self._sparseD

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return self._get(name)

    def __setattr__(self, name, val):
        if isinstance(name, str) and name.startswith("_"):
            raise AttributeError(name)        # internals are cdef, not settable here
        self.kvw(name, val)

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

    def __repr__(self):
        cdef Py_ssize_t i, nf = self._nfill
        cdef list t = self._type, cl = self._cles, d = self._data
        leaves = [(cl[i], d[i]) for i in range(nf) if 0 < <int>t[i] < 202]
        sparse = [(cl[i], d[i]) for i in range(nf) if <int>t[i] == 202]
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
