r"""cumulette.py -- a named dict in shared memory, seen by the hub and its processes.

    newbie:       a place to put small things that another program can read, without
                  either of you sending anything to the other. It works like a dict, and
                  what a process wrote is still there when it dies.
    student:      the Cumul of pipe/cumul.py, cut down to what the runner needs (hence
                  the little name): a fixed block cut into equal SLOTS, each starting with a readable 64-byte header. A
                  name finds its slot by hashing, then walking forward until it matches.
                  A value too big for one slot is split over the next free ones. Values
                  are JSON, stored as 8 hex digits of crc32 followed by the text: a read
                  that overlaps a write fails the crc and is tried again, so a reader
                  never acts on half a value.
    origin:       based on Cumul by Frans L Muller, which was free to use and amend. This
                  file, cumulette, is such an amendment.
    practitioner: ONE WRITER PER KEY. Nothing is locked, so a name is written by one
                  process only; any process may read any name. Which names the hub and
                  the processes use is for runbench2 and bench2 to say.

Use:
    ch = Channel('run42')                       the hub MAKES the block (10 MB default)
    ch = Channel('run42', create=False, wid=7)  a process OPENS it; wid is its own number,
                                                unique among the writers, 1 or more
    ch['p7'] = {'n': 3}    write any JSON value under a name (34 bytes at most, no space);
                           replaces what was there; Full if the slots run out
    ch['p7']               read it; KeyError if there is none
    ch.get('p7', default)  read it; the default if there is none
    del ch['p7']           remove it and every piece of it; KeyError if there is none
    ch.terminate()         the owner's last act: every other handle then fails with
                           ChannelError, and so does opening the block
    ch.close()             let go of this handle (the maker's handle also removes the name
                           on POSIX; Windows removes the block with its last handle)

A miss is "not there just now": a key being rewritten is released and placed again, so
for a few microseconds a reader can find it missing. A read that overlaps a write tries
again, at once TRIES times and then for PATIENCE (50 ms); a value that still will not
hold still raises Torn (a ChannelError, but the block is fine: its writer was rewriting
it all the time, or died in the middle of writing it). Anything that reads in a loop
should treat Torn as "no news". Terminated is the other ChannelError. The sequence field
of each header is kept at zero.

VERSION  M1 m01.v04 (2026-10-30): the file is cumulette.py, so that it is not mistaken for the
         Cumul of pipe/ and pycluster/; nothing else changed.
         M1 m01.v03 (2026-10-30): the file was cumul.py (it was rbchannel.py); the header names
         its origin (Cumul by Frans L Muller).
         M1 m01.v02 (2026-10-27): reads wait up to PATIENCE and then raise Torn; before,
         12 immediate tries raised ChannelError, which a reader could mistake for a dead
         block (three writers flat out gave one in ten runs of the suite a failure).
         M1 m01.v01 (2026-10-27): first version, cut from pipe/cumul.py. Gone:
         attachments, pickled, byte and name values, transient and hub-owned slots, the
         free cursor, stow, gather, drop, reap, load, free, view_at, version, keys, dump,
         pid, claimed, exists, widof, the write counter and the iteration and length of
         the dict. The store itself (hash walk, claim, split values, release, tombstone
         collapse, terminate, which cumul called seal) is cumul's, with the helpers as
         local functions and the value as crc-sealed JSON.
"""
import json
import os
import sys
import time
import zlib
from multiprocessing import shared_memory as shm

__all__ = ['Channel', 'ChannelError', 'Full', 'Torn']

# ---- the block: a header line of HEAD bytes before every slot, then the payload --------
HEAD = 64
FLAGW = 8                           # state, content, owner byte, then the claimant's id
LENOFF = FLAGW + 11                 # after the encoding byte and the zero sequence field
KEYOFF = LENOFF + 9
KEYW = HEAD - KEYOFF - 2            # bytes of a name; the last two bytes are ' \n'
STEP = 1                            # the probe step: the tombstone clean-up depends on it
HEADKEY = br'_\|/_'                 # slot 0's name
MINSLOT = 128
PAGE = 4096
E, T, M, W, R = b'E', b'T', b'M', b'W', b'R'    # empty, tombstone, more-of, writing, ready
MANY, ONE = b'N', b'1'              # the value is split over slots, or is in this one
OWNED = b'O'
SEED = 0x9E3779B9
SLOTS, SLOTSIZE = 2560, 4096        # 10 MB
TRIES = 12                          # reads retried at once, a writer being in the middle
PATIENCE = 0.05                     # then seconds more, 0.5 ms apart, before Torn
MISSING = object()
TERMINATED = 'has been terminated -- its owner has gone, nothing here is live'
UNTRACKED = {'track': False} if sys.version_info >= (3, 13) else {}


class ChannelError(Exception):
    """Anything this module refuses to do."""


class Full(ChannelError):
    """No room. The block cannot grow: shared memory is fixed when it is made."""


class Torn(ChannelError):
    """A value that would not hold still long enough to read: its writer kept rewriting it,
    or died in the middle of the write. The block itself is fine."""


class Priv:
    """What a Channel keeps for itself."""
    __slots__ = ('blk', 'mm', 'slots', 'slotsize', 'seed', 'claim', 'cache', 'created')


def line(st, kind, n, key):
    """One 64-byte slot header, fixed width so a probe reads known offsets."""
    return ((st + kind + OWNED).ljust(FLAGW) + b'  ' + b'%08d' % 0 + b' ' + b'%08d' % n
            + b' ' + key.ljust(KEYW))[:HEAD - 2] + b' \n'


EMPTY = line(E, ONE, 0, b'')
TOMB = line(T, ONE, 0, b'')
DEAD = line(W, ONE, 0, b'')


def keybytes(key):
    """A name as bytes, or ChannelError if the header cannot hold it."""
    raw = key if isinstance(key, bytes) else str(key).encode('utf-8')
    if not raw or b' ' in raw or b'\n' in raw or len(raw) > KEYW:
        raise ChannelError(f'{key!r} is not a name: 1 to {KEYW} bytes, no space or '
                           f'newline')
    return raw


def walk(me, key, placing=False):
    """(index, found) for a name: from its hash, forward, until it matches or an empty slot
    ends the probe. Placing: the first empty or tombstoned slot on the way. A continuation
    (M) is skipped, so a piece is never taken for a head. STEP 1 visits every slot once."""
    priv = me.priv
    mm = priv.mm
    size = priv.slotsize
    n = priv.slots
    home = zlib.crc32(key, priv.seed) % n
    first_tomb = -1
    for step in range(n):
        i = (home + step * STEP) % n
        o = i * size
        st = mm[o:o + 1]
        if st == E:
            if not placing:
                return -1, False
            return (first_tomb if first_tomb >= 0 else i), False
        if st == T:
            if first_tomb < 0:
                first_tomb = i
            continue
        if st == M:
            continue
        if mm[o + KEYOFF:o + KEYOFF + KEYW].rstrip() == key:
            return i, True
    if not placing:
        return -1, False
    if first_tomb >= 0:
        return first_tomb, False
    if mm[0:1] == W:
        raise ChannelError(f'{me.name!r} {TERMINATED}')
    raise Full(f'{me.name}: all {n} slots are taken')


def clear(me, i):
    """Give one slot back. A tombstone is kept only where a probe still runs THROUGH
    slot i: walk on to the next empty slot, where every probe stops anyway, and rehash
    each live name on the way. A name sitting on its own home slot was never displaced,
    so nothing reaches it through here. Without the clean-up a block that has churned
    fills with tombstones and every miss walks them all (cumul measured 256 probes at
    12% live, 1.3 with it). When no probe needs the slot it goes empty, and the
    tombstones just behind it with it."""
    priv = me.priv
    mm = priv.mm
    size = priv.slotsize
    n = priv.slots
    needed = True
    for step in range(1, n):
        j = (i + step) % n
        if j == 0:
            continue                # the header is never empty: a probe walks on past it
        o = j * size
        st = mm[o:o + 1]
        if st == E:
            needed = False
            break
        if st in (T, M):
            continue
        k = mm[o + KEYOFF:o + KEYOFF + KEYW].rstrip()
        if k and not 0 < (zlib.crc32(k, priv.seed) % n - i) % n <= step:
            break                   # that name's chain runs through slot i
    if needed:
        mm[i * size:i * size + HEAD] = TOMB
        return
    mm[i * size:i * size + HEAD] = EMPTY
    j = (i - STEP) % n
    while j != 0 and mm[j * size:j * size + 1] == T:
        mm[j * size:j * size + HEAD] = EMPTY
        j = (j - STEP) % n


def release_chain(me, head):
    """Free a value and every piece of it. Counts bytes instead of trusting adjacency:
    the pieces need not be adjacent, and a walk that stopped at the first gap leaked the
    rest."""
    priv = me.priv
    mm = priv.mm
    size = priv.slotsize
    n = priv.slots
    o = head * size
    key = mm[o + KEYOFF:o + KEYOFF + KEYW].rstrip()
    many = mm[o + 1:o + 2] == MANY
    total = int(mm[o + LENOFF:o + LENOFF + 8])      # before the slot is cleared
    clear(me, head)
    if not many:
        return
    got = min(total, size - HEAD)
    i = (head + STEP) % n
    for _ in range(n):
        if got >= total:
            return
        p = i * size
        if mm[p:p + 1] == M and mm[p + KEYOFF:p + KEYOFF + KEYW].rstrip() == key:
            got += int(mm[p + LENOFF:p + LENOFF + 8])
            clear(me, i)
        i = (i + STEP) % n


class Channel:
    """A named dict in shared memory. See the module header."""

    def __init__(me, name, slots=SLOTS, slotsize=SLOTSIZE, create=True, wid=0):
        """create=False OPENS ONLY: a process that reaches the block first, or misspells
        the name, must fail instead of starting an empty block of its own and running on
        believing it had joined the hub."""
        me.name = name
        me.priv = priv = Priv()
        priv.cache = {}
        priv.claim = (b'%04d' % int(wid)).ljust(FLAGW)
        priv.seed = SEED
        try:
            blk = shm.SharedMemory(name, create=False, **UNTRACKED)
            priv.created = False
        except FileNotFoundError:
            if not create:
                raise ChannelError(f'{name!r} does not exist: the hub makes it') from None
            if slots < 3:
                raise ChannelError('a block needs 3 slots: the header, an entry, and an '
                                   'empty one to stop a walk')
            slotsize = max(MINSLOT, int(slotsize))
            size = ((slots * slotsize) // PAGE + 1) * PAGE
            blk = shm.SharedMemory(name, create=True, size=size)
            priv.created = True
        mm = getattr(blk, '_mmap', None)        # slicing it copies bytes in one C step
        if mm is None:
            raise ChannelError('this Python has no SharedMemory._mmap, which is needed')
        priv.blk = blk
        priv.mm = mm
        if priv.created:
            priv.slots = slots
            priv.slotsize = size // slots       # spend the whole block
            for i in range(slots):
                mm[i * priv.slotsize:i * priv.slotsize + HEAD] = EMPTY
            body = (f'v=1 slots={slots} size={priv.slotsize} seed={SEED:08X} '
                    f'pid={os.getpid()}').encode('ascii')
            mm[HEAD:HEAD + len(body)] = body
            mm[0:HEAD] = line(R, ONE, len(body), HEADKEY)
            return
        head = mm[0:HEAD]
        if head[KEYOFF:KEYOFF + len(HEADKEY)] != HEADKEY:
            raise ChannelError(f'{name!r} is not a channel (slot 0 is {head[:40]!r})')
        if head[0:1] == W:
            raise ChannelError(f'{name!r} {TERMINATED}')
        fields = dict(part.split('=', 1) for part in
                      mm[HEAD:HEAD + int(head[LENOFF:LENOFF + 8])].decode('ascii').split()
                      if '=' in part)
        priv.slots = int(fields['slots'])
        priv.slotsize = int(fields['size'])
        priv.seed = int(fields['seed'], 16)

    def get(me, key, default=None):
        """The value under a name, or `default`. Lock-free: a read that overlaps a write is
        caught by the crc, or by a header or piece not yet in place, and tried again."""
        priv = me.priv
        mm = priv.mm
        size = priv.slotsize
        n = priv.slots
        room = size - HEAD
        k = keybytes(key)
        spins = 0
        give_up = None
        while True:
            i = priv.cache.get(k, -1)
            if (i < 0
                    or mm[i * size:i * size + 1] != R
                    or mm[i * size + KEYOFF:i * size + KEYOFF + KEYW].rstrip() != k):
                i, found = walk(me, k)          # the cached slot is checked: it may have
                if not found:                   # been released and reused since
                    if mm[0:1] == W:            # a miss on a dead block is not a miss
                        raise ChannelError(f'{me.name!r} {TERMINATED}')
                    return default
                priv.cache[k] = i
            o = i * size
            if mm[o:o + 1] == R:
                try:
                    total = int(mm[o + LENOFF:o + LENOFF + 8])
                    parts = [mm[o + HEAD:o + HEAD + min(total, room)]]
                    got = len(parts[0])
                    j = (i + STEP) % n
                    for walked in range(n if mm[o + 1:o + 2] == MANY else 0):
                        if got >= total:
                            break
                        p = j * size
                        if (mm[p:p + 1] == M
                                and mm[p + KEYOFF:p + KEYOFF + KEYW].rstrip() == k):
                            piece = int(mm[p + LENOFF:p + LENOFF + 8])
                            parts.append(mm[p + HEAD:p + HEAD + piece])
                            got += piece
                        j = (j + STEP) % n
                    text = b''.join(parts)
                    if got >= total and text[:8] == b'%08x' % zlib.crc32(text[8:]):
                        return json.loads(text[8:])
                except ValueError:              # a header caught half written
                    pass
            spins += 1                          # a writer is in the middle of it: wait
            if spins <= TRIES:
                time.sleep(0)                   # first just let it finish
                continue
            if give_up is None:
                give_up = time.perf_counter() + PATIENCE
            elif time.perf_counter() > give_up:
                raise Torn(f'{me.name}: {key!r} would not hold still for {PATIENCE:g} s: '
                           f'its writer is rewriting it all the time, or died writing it')
            time.sleep(0.0005)

    def __getitem__(me, key):
        value = me.get(key, MISSING)
        if value is MISSING:
            raise KeyError(key)
        return value

    def __setitem__(me, key, value):
        """Write a value under a name, replacing what was there: the old value is released
        and the name placed again. A split value takes free slots walking forward from its
        head, so a read finds the pieces next to it. Every piece after the head is
        CLAIMED before it is filled: WRITE, THEN LOOK. Writers stamp the slot with their
        own id, the last stamp stands, and the one that reads its own id back owns it,
        twice, because across processes the other stamp may not have landed at the first
        look. Then payload before state and the head last, so nothing looks at the
        chain until it is whole."""
        priv = me.priv
        mm = priv.mm
        size = priv.slotsize
        n = priv.slots
        room = size - HEAD
        k = keybytes(key)
        body = json.dumps(value, separators=(',', ':')).encode('utf-8')
        body = b'%08x' % zlib.crc32(body) + body
        need = max(1, -(-len(body) // room))
        head, found = walk(me, k, True)
        if found:
            release_chain(me, head)
            head, found = walk(me, k, True)
        indexes = [head]
        for step in range(1, n):
            if len(indexes) == need:
                break
            i = (head + step * STEP) % n
            if i == 0:
                continue                        # never the block's own header
            o = i * size
            if mm[o:o + 1] in (E, T):
                mm[o:o + FLAGW] = priv.claim
                if mm[o:o + FLAGW] == priv.claim:
                    time.sleep(0)               # let a competing stamp land
                    if mm[o:o + FLAGW] == priv.claim:
                        indexes.append(i)
        if len(indexes) < need:
            for i in indexes[1:]:
                clear(me, i)                    # give back what was taken
            raise Full(f'{me.name}: {need} slots wanted after {head}, {len(indexes)} free')
        kind = ONE if need == 1 else MANY
        for j, i in enumerate(indexes):
            o = i * size
            part = body[j * room:(j + 1) * room]
            mm[o:o + HEAD] = line(W, kind, len(body) if j == 0 else len(part), k)
            mm[o + HEAD:o + HEAD + len(part)] = part
        for i in reversed(indexes):
            mm[i * size:i * size + 1] = R if i == head else M
        priv.cache[k] = head

    def __delitem__(me, key):
        k = keybytes(key)
        me.priv.cache.pop(k, None)
        i, found = walk(me, k)
        if not found:
            raise KeyError(key)
        release_chain(me, i)

    def terminate(me):
        """Make every slot untouchable: THE BLOCK IS DEAD, NOT EMPTY. E would mean free and
        T reusable, so a straggler that outlived the hub would allocate into memory nobody
        owns and drift on; W is the one state that means do not touch, so it fails at its
        first access instead. The header keeps its key and geometry, so a reopen says
        terminated, not corrupt."""
        priv = me.priv
        for i in range(1, priv.slots):
            priv.mm[i * priv.slotsize:i * priv.slotsize + HEAD] = DEAD
        priv.cache.clear()
        priv.mm[0:1] = W

    def close(me):
        """Let go of this handle."""
        priv = me.priv
        priv.cache.clear()
        try:
            priv.blk.close()
            if priv.created:
                priv.blk.unlink()
        except Exception:
            pass
