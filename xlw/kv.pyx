# cython: language_level=3
"""
kv.pyx -- kv: an open-addressing hash map for text keys and sparse [r, c, ...] keys.
Promoted from the sandbox variant kvc2 (its timing is in the history, commit e98424b); the
canonical sparse key is written [5 3] (kvc2 wrote (5 3)).

Algorithm
    Open addressing with a parallel TYPE array, so leaf and sparse enumeration is a
    contiguous scan, which a dict cannot do. Keys are stored as BYTES and compared with
    memcmp (C). The hash is Python's hash(bytes) (siphash in C), not the per-character
    DJB2 loop. The index, hash and type tables are RAW C ARRAYS (malloc), so the probe
    touches no Python object until a hash hits; then one list slot holds the key
    (memcmp) and one the value. key2idx is inlined and emits bytes directly.
    The hash differs from kv.m, so the probe ORDER is not that of kv.m. The observable
    behaviour is the same: the parity tests assert behaviour, not probe order.
    A sparse key d[5, 3] is stored, and shown by indici() and the repr, as the text
    "[5 3]": a list, as in Python. That text is also an address: d["[5 3]"] reads and
    overwrites the cell, so a key from indici() always round-trips. For the same reason a
    NEW text key that starts with "[" is refused (KvReservedBracket); a text key that
    starts with "(" is an ordinary leaf. Text that starts with "[" (a header such as
    "[A] in A") cannot be a kv key; as a value, or behind a one-letter prefix, it is fine.
    Position access. Entries sit in write order in the parallel arrays; d.at(idx) is the key
    at position idx (the position is the slot number, the first entry written is 0), so a
    store of unique texts is a numbered list: d.kvw(text, len(d)) and d.at(n) is the text.
    A removal leaves a dead slot, and a resize normally compacts the live entries, which
    renumbers them. The first call of at() PINS the store: from then on a resize never
    compacts, so a position that was handed out stays valid (dead slots stay dead; keys(),
    vals() and indici() skip them). A pinned store that churns would grow without bound, so
    a new entry is refused with KvPositionOverflow when BOTH hold: more than 10 slots per
    live entry, and the dead slots hold more than 10 x 4096 bytes (counted as 64 bytes
    each). clear() unpins. Do not use at() on a store that deletes keys often.

Use
    from kv import kv, kvr, kvw
    d = kv(); d.x = 5; d[2, 3] = 99; d.kvr('x'); d.indici()      # ['[2 3]']
    d.at(0)                                                       # 'x'

Versions
    M03  m03.v01  2026-10-31  at(idx): the key at a position, which pins the store against
                              compaction; KvPositionOverflow on excessive churn.
    M02  m02.v01  2026-10-31  the sparse key is written [r c] in place of (r c), and
                              KvReservedParen is KvReservedBracket. The delimiter costs
                              nothing (measured). Tried and dropped: a
                              marker byte 0xFF in place of the delimiter; no text could
                              collide, but "[5 3]" then no longer addressed the cell, so
                              keys from indici() did not round-trip, and indici() was 2.3x
                              slower.
    M01  m01.v01  2026-10-31  promoted from kvc2.pyx: kvc2 -> kv, Kvc2* -> Kv*, and an
                              __all__ list added. Algorithm and code untouched.
"""

from cpython.bytes cimport PyBytes_AS_STRING, PyBytes_GET_SIZE
from libc.stdlib cimport malloc, free, realloc
from libc.string cimport memcmp, memset

DEF TOMB = 0xFFFFFFFF
DEF N0   = 32
DEF SZT0 = 64
DEF DEADRATIO = 10                   # a pinned store may hold this many slots per live entry ...
DEF DEADMEM   = 40960                # ... or, below this many bytes of dead slots (10 x 4096)
DEF DEADSLOT  = 64                   # bytes counted for one dead slot

__all__ = ["kv", "kvr", "kvw", "KvError", "KvSparseDimMismatch", "KvReservedBracket",
           "KvPositionOverflow"]


class KvError(Exception):            pass
class KvSparseDimMismatch(KvError): pass
class KvReservedBracket(KvError):   pass
class KvPositionOverflow(KvError):  pass


cdef inline bytes _numb(x):
    # number -> bytes directly (one C format step; no str object, no encode).
    if isinstance(x, int):
        return b"%d" % x
    return b"%.15g" % x


cdef tuple _key2idx(key):
    # -> (canonical bytes, nD).  Mirrors key2idx.py but builds BYTES throughout
    # (the store/hash/memcmp are all bytes — no str round-trip).
    cdef list comps, parts
    cdef bytes bc
    if isinstance(key, str):
        return (<str>key).encode("utf-8"), 0          # user str -> bytes (unavoidable)
    if isinstance(key, bool):
        return (b"True" if key else b"False"), 0
    if isinstance(key, (int, float)):
        return b"[" + _numb(key) + b"]", 1
    if isinstance(key, (list, tuple)):
        comps = list(key)
        if len(comps) == 1:
            e = comps[0]
            if isinstance(e, (list, tuple)):
                comps = list(e)
            elif isinstance(e, str):
                return e.encode("utf-8"), 0
            else:
                return b"[" + _numb(e) + b"]", 1
        parts = []
        for c in comps:
            if isinstance(c, str):
                bc = (<str>c).encode("utf-8")
                if b" " in bc:
                    bc = b"'" + bc + b"'"
            else:
                bc = _numb(c)                         # numbers never contain a space
            parts.append(bc)
        return b"[" + b" ".join(parts) + b"]", len(parts)
    return str(key).encode("utf-8"), 0


cdef class kv:
    cdef unsigned int*       _idx        # index table (szT): 0 empty, TOMB tomb, k entry
    cdef unsigned long long* _hash       # cached hashes (nbuf)
    cdef unsigned char*      _type       # 201 leaf / 202 sparse-leaf (nbuf)
    cdef list _cles, _data               # bytes keys / object values (nbuf-long)
    cdef unsigned long long _mask
    cdef Py_ssize_t _szT, _nbuf, _nUsed, _nfill, _sparseD, _fslot
    cdef bint _pinned                    # at() was used: resizes keep every slot where it is

    def __cinit__(self):
        self._idx = NULL; self._hash = NULL; self._type = NULL
        self._setup()

    def __dealloc__(self):
        free(self._idx); free(self._hash); free(self._type)

    cdef _setup(self):
        free(self._idx); free(self._hash); free(self._type)
        self._szT  = SZT0
        self._mask = SZT0 - 1
        self._nbuf = N0
        self._idx  = <unsigned int*>malloc(SZT0 * sizeof(unsigned int))
        self._hash = <unsigned long long*>malloc(N0 * sizeof(unsigned long long))
        self._type = <unsigned char*>malloc(N0)
        memset(self._idx, 0, SZT0 * sizeof(unsigned int))
        memset(self._type, 0, N0)
        self._cles = [None] * N0
        self._data = [None] * N0
        self._nUsed = 0
        self._nfill = 0
        self._sparseD = 0
        self._pinned = 0

    def clear(self):
        self._setup()
        return self

    # ── probe primitives ────────────────────────────────────────────────
    cdef _get(self, bytes bkey):
        cdef const char* qp = PyBytes_AS_STRING(bkey)
        cdef Py_ssize_t qn = PyBytes_GET_SIZE(bkey)
        cdef unsigned long long h = <unsigned long long>hash(bkey), perturb = h
        cdef Py_ssize_t slot = <Py_ssize_t>(h & self._mask)
        cdef unsigned int ei
        cdef object sk
        while True:
            ei = self._idx[slot]
            if ei == 0:
                return None
            if ei < TOMB and self._hash[ei - 1] == h:
                sk = self._cles[ei - 1]
                if PyBytes_GET_SIZE(sk) == qn and memcmp(PyBytes_AS_STRING(sk), qp, qn) == 0:
                    return self._data[ei - 1]
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
                    return self._type[ei - 1]
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
                self._type[ei - 1] = 0
                self._nUsed -= 1
            self._data[ei - 1] = val
            return
        elif val is None:
            return
        qp = PyBytes_AS_STRING(bkey)
        if ty < 202 and PyBytes_GET_SIZE(bkey) > 0 and qp[0] == 91:   # '['
            raise KvReservedBracket("bracketed keys are reserved; index with d[r, c]")
        if (self._pinned and self._nfill > DEADRATIO * self._nUsed
                and (self._nfill - self._nUsed) * DEADSLOT > DEADMEM):
            raise KvPositionOverflow(
                "excessive churn, dont use kv.at when frequently deleting keys")
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
        self._hash[ei - 1] = h
        self._type[ei - 1] = ty
        self._cles[ei - 1] = bkey
        self._data[ei - 1] = val
        self._idx[slot]    = <unsigned int>ei

    cdef _remove(self, bytes bkey):
        cdef unsigned long long h = <unsigned long long>hash(bkey)
        cdef Py_ssize_t ei = self._find(bkey, h)
        if ei == 0:
            return
        self._idx[self._fslot] = TOMB
        self._type[ei - 1]     = 0
        self._data[ei - 1]     = None
        self._nUsed -= 1

    cdef _grow(self):
        cdef Py_ssize_t newbuf = self._nbuf * 2, ext = self._nbuf
        self._hash = <unsigned long long*>realloc(self._hash, newbuf * sizeof(unsigned long long))
        self._type = <unsigned char*>realloc(self._type, newbuf)
        self._cles += [None] * ext
        self._data += [None] * ext
        self._nbuf = newbuf

    cdef _resize(self):
        cdef Py_ssize_t n = self._nfill if self._pinned else self._nUsed
        cdef Py_ssize_t new_szt = self._szT, k, i, s
        while new_szt < 4 * n:
            new_szt *= 2
        cdef unsigned long long new_mask = new_szt - 1, hk, perturb
        cdef unsigned int* new_idx
        if self._pinned:
            # positions were handed out: grow the probe table over the live entries and
            # leave every slot, dead ones included, where it is
            new_idx = <unsigned int*>malloc(new_szt * sizeof(unsigned int))
            memset(new_idx, 0, new_szt * sizeof(unsigned int))
            for k in range(n):
                if self._type[k] == 0:
                    continue
                hk = self._hash[k]
                perturb = hk
                s = <Py_ssize_t>(hk & new_mask)
                while new_idx[s] != 0:
                    perturb >>= 5
                    s = <Py_ssize_t>(((5 * <unsigned long long>s + 1) + perturb) & new_mask)
                new_idx[s] = <unsigned int>(k + 1)
            free(self._idx)
            self._idx = new_idx
            self._szT = new_szt
            self._mask = new_mask
            return
        cdef list live = [i for i in range(self._nfill) if self._type[i] > 0]
        cdef list nc = [self._cles[i] for i in live]
        cdef list nd = [self._data[i] for i in live]
        # compact the C arrays in place (live indices increasing, target <= source)
        for k in range(n):
            i = live[k]
            self._hash[k] = self._hash[i]
            self._type[k] = self._type[i]
        # rebuild the index table
        new_idx = <unsigned int*>malloc(new_szt * sizeof(unsigned int))
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

    # ── public API ──────────────────────────────────────────────────────
    def kvw(self, key, val):
        cdef bytes bkey
        cdef int nD, ty
        bkey, nD = _key2idx(key)
        if nD > 0:
            if self._sparseD == 0:
                self._sparseD = nD
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
        cdef bytes bkey = _key2idx(key)[0]
        return self._find(bkey, <unsigned long long>hash(bkey)) > 0

    def remove(self, key):
        self._remove(_key2idx(key)[0])

    def isEmpty(self):
        return self._nUsed == 0

    def kind(self, key):
        return self._typeof(_key2idx(key)[0])

    def at(me, Py_ssize_t idx):
        me._pinned = 1
        if idx < 0 or idx >= me._nfill or me._type[idx] == 0:
            raise IndexError(idx)
        return me._cles[idx].decode("utf-8")

    def numEntries(self):
        cdef Py_ssize_t i, c = 0
        for i in range(self._nfill):
            if 0 < self._type[i] < 202:
                c += 1
        return c

    def keys(self):
        cdef Py_ssize_t i
        return [self._cles[i].decode("utf-8") for i in range(self._nfill)
                if 0 < self._type[i] < 202]

    def vals(self):
        cdef Py_ssize_t i
        return [self._data[i] for i in range(self._nfill) if 0 < self._type[i] < 202]

    def indici(self):
        cdef Py_ssize_t i
        return [self._cles[i].decode("utf-8") for i in range(self._nfill)
                if self._type[i] == 202]

    def icount(self):
        cdef Py_ssize_t i, c = 0
        for i in range(self._nfill):
            if self._type[i] == 202:
                c += 1
        return c

    def idim(self):
        return self._sparseD

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return self._get(name.encode("utf-8"))

    def __setattr__(self, name, val):
        if isinstance(name, str) and name.startswith("_"):
            raise AttributeError(name)
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
        cdef Py_ssize_t i
        leaves, sparse = [], []
        for i in range(self._nfill):
            t = self._type[i]
            if 0 < t < 202:
                leaves.append((self._cles[i].decode(), self._data[i]))
            elif t == 202:
                sparse.append((self._cles[i].decode(), self._data[i]))
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
