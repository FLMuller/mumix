r"""bench.py -- run ONE b_ suite: its tests, then its benchmarks, and say how it went.

    newbie:       a b_ suite proves a unit (test_* methods) and times it (bench_* methods).
                  This file runs one suite in one process. runbench.py starts it, usually
                  many at once, and reads what it reports. A suite is run only by runbench.py.
    student:      the engine that used to hide in the base class's tearDownClass. It loads
                  the suite file, runs the tests, and if they all passed times every
                  bench_* against a flat reference loop (r = cost per operation / cost of
                  one reference step, so a faster or slower machine cancels out).
    practitioner: a suite needs only unittest.TestCase, a setup_fixtures classmethod,
                  test_* methods and bench_* methods of one form, bench_x(self, timer):
                  set up once, then `with timer as test: while test.more: for i in
                  test.count: OP`, and return 'label', 'group'. The engine decides how
                  many ops and for how long (see Timer): a suite declares no Nx and no
                  NRep. Nothing in the suite is changed or imported by this file except
                  the suite itself.

Use:
  runbench.py starts one process for each phase of a suite (the tests, then the benchmarks):
      Worker(path, channel, tag).run(want_test, want_bench)
  The worker talks to the hub through the shared block `channel` as writer `tag`, and takes
  its limits from the hub's dict hub.config.<tag>.

  A suite may inherit `bench`:
      from bench import bench
      class b_unit(bench):  BenchName = ...; bench_*(self, timer), test_*

What it keeps on the channel (one writer per key; N is this process's tag):
    p<N>  this process's state, rewritten at every step: suite, phase (import, tests,
          bench, end), the step it is in and when it began (tstart) and how long it may
          take (limit), the test records so far, 'live' while the timed benchmarks run,
          and at the end the whole result ('end').
    o<N>  what the suite printed: the last 16 KB of lines, with a count of those dropped.
    h<N>  written by the hub: limits (timeout, test_time, pause, budget, skip, live,
          orphan) and its heartbeat.
    m<N>  written by the hub: {'cmd': 'terminate'} asks this process to stop at the next
          boundary. A hub whose heartbeat is older than `orphan` seconds is taken as gone.

The limits (all from the runner's def): test_time 1 s for any ONE test: a kernel timer
stops a slow one (in the middle of its own code if that is running Python), "time too
high" is noted against it, and the run goes ON with the next test; one that cannot be
interrupted (a sleep, a long C call) is noted when it returns. An ERROR stops: the first
test that fails ends the file's tests (the rest are skipped, and say why) and no
benchmark is timed; a bench that raises is caught, reported with its traceback, and the
benchmarks stop there. timeout 10 s is the hang guard behind all that: the hub kills a
worker whose one test is still going and notes the test as slow. Pause 10 ms after every
test and every bench call (outside the timing), budget 10 s for the whole file: what the
import and the tests have used comes off it, and the benchmark phase gets the rest
(never under 2 s).

HOW LONG A BENCH RUNS. Each bench has the time left of the file's budget shared out among
the benches still to run, at most TIER_SLOW + 0.25 s of wall time (never under 0.3 s), and
at most MAX_OPS ops (see Timer for the blocks and the tier). A bench that cannot make its
ops in its time is flagged slow and reported from what it did: the cost of a call is the
time over the calls done. Two limits cover the long calls: a call that takes more than
`tlong` (1 s) is measured once, as it is, and one that takes more than `tmax` (42 s) is
stopped by the kernel timer (see Alarm), its row saying how long a call took at least.
The hub's kill (the step's limit, a little after tmax) is behind the timer for a call
that will not end.

The machine line (power, clock in GHz, speed, PC CPU, memory, disk) is not measured here:
the hub reads it around the timed run, which this process marks with p<N>['live'] = True
and False. This process reports what only it knows: the reference step (perinner), the
CPU seconds it used in that run (cpu) and that run's wall seconds (live_wall).

The warm-up is the probe blocks of each Timer, thrown away; the method's return gives the
bench its label and group.

HOW A TIME IS REPORTED. Every timed BLOCK is CALIBRATED: the reference loop is measured
(calibrate: 2000 hashes, the fastest of 10 takes, about 3 ms) when the Timer begins and
after each block, outside the timing, and the mean of the two either side of a block is
the seconds per step during it. The block's r is (its seconds per op, less the loop's own
cost, see overhead) over that step, so each sample says what the operation cost in
reference steps at the machine's speed AT THAT MOMENT, whoever else was running. The
reported r is the mean of the blocks' r, after the usual outlier rule; +/- is their stdev
in percent and se the standard error of the mean; the reported cost is r times the mean
reference step of the run (time / #hashes * #reference hashes, as it were). This is what
lets benchmarks run side by side. It cannot correct for work that is not like the
reference: the reference is pure integer arithmetic, so code bound by memory or caches
still reads a little differently when the machine is shared, and a process kept waiting
for a core (more workers than cores) is not corrected at all.

VERSION  M3 m03.v03 (2026-10-31): the Code tabs come from the class attribute `sources` (module
         names) and use.locate: only the code that ran. SOURCES, declared_sources and find_source are gone.
         M3 m03.v02 (2026-10-31): no main() and no plain(): a suite is run only by runbench.py, which
         starts the Worker itself. Worker is in __all__.
         M3 m03.v01 (2026-10-30): the file is bench.py (it was bench3.py), the class bench, and the
         support modules and page files are in primary/.
         M2 m02.v02 (2026-10-29): the unit page has a Code tab for the suite and one for each file
         the suite names in SOURCES (read from the suite's text), or a red tab that says what
         is missing and what it costs.
         M2 m02.v01 (2026-10-28): rebuilt around the Timer. A bench is bench_x(self,
         timer): no Nx, no NRep, no ceiling. The ops are timed in blocks, the clock read
         once per block, at most 1000 ops a bench, in at most 0.3 s (1 s for slower ones),
         each bench with a share of the file's budget; the stdev and standard error come
         from the blocks; a slow bench is reported from what it did; a call over tlong
         (1 s) is measured once, up to tmax (42 s). The engine up to here is kept as
         bench_nx.py.
         M1 m01.v04 (2026-10-28): a test over test_time is stopped by the timer and noted
         slow, the run goes on; an error stops (a failing test ends the file's tests, a
         raising bench ends the benchmarks); no total test budget. Rebuilt from scratch
         after the file was lost; the design is the one of v03.
         M1 m01.v03 (2026-10-27): no pre-scaling: run at the declared Nx and stop at the
         budget with a kernel timer (Alarm), reporting the share of the work done; every
         timed call calibrated.
         M1 m01.v02 (2026-10-27): no machine meter here (the hub reads it); the ceiling.
         M1 m01.v01 (2026-10-27): first version, written from scratch, with
         bench.py's design as the inspiration: the reference loop, the outlier rule and the
         r figure are the same; the gate, the driver and the report are not.
"""
import _thread
import html
import importlib.util
import itertools
import math
import os
import re
import sys
import time
import traceback
import unittest

# the support modules (codelex, htmlwriter, cumulette) and the compiled
# ones (marked, mdwriter) are in primary/ below this file: use finds them there
PRIMARY = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'primary')   # the page files
from use import load, locate, use
use('primary')
from htmlwriter import htmappend, htmtemplate, htmwriteln
load('marked', 'mdwriter')            # md2htm, mdwriteln: built by use into primary/pyxfiles
from cumulette import Channel, ChannelError, Torn

__all__ = ['bench', 'Worker']

CAL_STEPS = 2000                    # reference steps in one take of a calibration
CAL_TAKES = 10                      # takes; the fastest is the speed (see calibrate)
REF_CV_TOL = 25.0                   # %, a reference moving more than this spoils a run
ORPHAN = 5.0                        # seconds of hub silence after which it is gone
RING = 16384                        # bytes of output lines kept
FLUSH = 0.05                        # least seconds between two writes of the output
REPORT = 4000                       # characters of one failure's traceback kept
MAX_OPS = 1000                      # most ops timed of one bench
TIER_FAST = 0.3                     # timed seconds a bench may use if MAX_OPS fit in them
TIER_SLOW = 1.0                     # ... else this many, and the ops are cut to fit
MAX_BLOCK = 100                     # most ops between two reads of the clock
PROBE_SECS = 5e-6                   # a probe block this long reads well (tick: 100 ns)
NOISY = 5.0                         # %, a standard error over this is flagged noisy
DEFAULTS = {'timeout': 10.0, 'pause': 0.010, 'budget': 10.0, 'skip': [], 'live': True,
            'orphan': ORPHAN, 'test_time': 1.0, 'tlong': 1.0, 'tmax': 42.0}


class Stop(Exception):
    """The hub asked this process to stop, or has gone."""


class Abandon(BaseException):
    """The timer fired: the time is up. A BaseException, so that a bench or a test that
    catches Exception does not swallow it."""


class Alarm:
    """A kernel timer that ends the benchmarks, or a slow test, when its time is up.

    On Windows it is a timer-queue timer. When it fires the OS runs a callback, which asks
    the main thread to raise Abandon (PyThreadState_SetAsyncExc); the main thread raises
    it at its next bytecode, in the middle of a bench's own loop if that is where it is.
    That is aimed only while a call is running (`inside`): between calls the timer just
    sets `fired`, and the next call looks at it before it starts. A call stuck in C code,
    or in time.sleep, ends when that returns; the hub's kill (the step's `limit`) is
    behind that. Without the OS timer there is only the look before each call."""

    def __init__(me):
        me.main = _thread.get_ident()
        me.timer = None
        me.inside = False
        me.fired = False
        me.deadline = None
        me.ctypes = None
        me.keep = None
        if os.name != 'nt':
            return
        try:
            import ctypes
            me.k32 = ctypes.WinDLL('kernel32', use_last_error=True)
            callback = ctypes.WINFUNCTYPE(None, ctypes.c_void_p, ctypes.c_ubyte)
            me.k32.CreateTimerQueueTimer.argtypes = [
                ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p, callback,
                ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
            me.k32.DeleteTimerQueueTimer.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                                     ctypes.c_void_p]
            me.keep = callback(me.fire)             # kept alive as long as the timer is
            me.ctypes = ctypes
        except Exception:
            me.ctypes = None

    def fire(me, parameter, timed_out):
        """The OS calls this, on a thread of its own, when the time is up."""
        me.fired = True
        if me.inside:
            me.ctypes.pythonapi.PyThreadState_SetAsyncExc(
                me.ctypes.c_ulong(me.main), me.ctypes.py_object(Abandon))

    def arm(me, seconds):
        """Set the timer to `seconds` from now, replacing one that is set."""
        me.stop()
        me.fired = False
        me.deadline = time.perf_counter() + seconds
        if me.ctypes:
            handle = me.ctypes.c_void_p()
            if me.k32.CreateTimerQueueTimer(me.ctypes.byref(handle), None, me.keep, None,
                                            int(seconds * 1000) + 1, 0, 0x8):
                me.timer = handle

    def stop(me):
        if me.timer is not None:
            me.k32.DeleteTimerQueueTimer(None, me.timer, me.ctypes.c_void_p(-1))  # waits
            me.timer = None

    def clear(me):
        """Drop an Abandon that was asked for but has not been raised yet."""
        if me.ctypes:
            me.ctypes.pythonapi.PyThreadState_SetAsyncExc(me.ctypes.c_ulong(me.main), None)

    def cancel(me):
        """Switch the timer off for good. A timer that fires just as the work ends has an
        Abandon on its way: it is aimed at the main thread and can land on any bytecode,
        this method's own calls included, so it is cleared before and after the wait for
        the OS callback, and one that lands anyway is let go. Nothing comes out of here."""
        me.inside = False
        for _ in range(3):
            try:
                me.clear()
                me.stop()
                me.clear()
            except Abandon:
                continue
            break

    def look(me):
        """Raise Abandon if the time is already up (the look before each call)."""
        if me.fired or (me.deadline is not None and time.perf_counter() > me.deadline):
            raise Abandon()


# ---- numbers ---------------------------------------------------------------------------
def ref_loop(n=CAL_STEPS):
    """Seconds for n steps of h = (h*33 + j) % 2**32: pure integer work, no memory, flat
    (a nested loop pays its set-up on every outer pass and the unit then drifts)."""
    h = 5381
    m = 2**32
    t0 = time.perf_counter()
    for j in range(n):
        h = (h * 33 + j) % m
    return time.perf_counter() - t0


def calibrate():
    """Seconds per reference step, now: the FASTEST of CAL_TAKES takes of CAL_STEPS steps.
    Interruptions only ever slow a take down, so the minimum is the speed the core really
    had, and it is steady where one take is not. Measured on the development machine, among
    memory-heavy work: one take of 2000 steps scattered by 25%, the fastest of ten by 3%;
    and it followed a real change, 115 ns a step alone and 270 ns with five busy processes.
    Costs about 3 ms."""
    return min(ref_loop(CAL_STEPS) for _ in range(CAL_TAKES)) / CAL_STEPS


def median(values):
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def mean(values):
    return sum(values) / len(values)


def std(values):
    if len(values) < 2:
        return 0.0
    mu = mean(values)
    return math.sqrt(sum((x - mu)**2 for x in values) / (len(values) - 1))


def rm_outliers(values):
    """(kept, number dropped). The floor of a timing is the true cost and anything above is
    cost plus an interruption, so the spread is estimated from the lower half only and
    whatever lies more than 3 sigma above that mean is dropped."""
    med = median(values)
    low = [x for x in values if x <= med]
    mu = mean(low)
    sigma = math.sqrt(sum((x - mu)**2 for x in low) / len(low)) if len(low) > 1 else 0.0
    kept = [x for x in values if x <= mu + 3 * sigma]
    return kept, len(values) - len(kept)


class Timer:
    """The clock of one bench, passed to bench_x(self, timer) as its only argument:

        def bench_x(self, timer):
            ...set-up, once...
            with timer as test:
                while test.more:            # another block of ops?
                    ...prepare...           # each block, not timed; optional
                    for i in test.count:    # this block's ops, timed from the first
                        OP                  # step to the last
            return 'label', 'group'

    The ops are timed in BLOCKS and the clock is read once per block, so its cost (about
    100 ns a read) is spread over the block. The first blocks are probes of 1, 2, 4 ...
    ops, up to MAX_BLOCK or until one is long enough to read (PROBE_SECS): they are
    thrown away and give the cost c of an op. Then `planned = min(cap, tier / c)` ops are
    timed, where the tier is TIER_FAST s if all `cap` ops fit in it and TIER_SLOW s if
    not, in blocks of planned // 20 ops (at most MAX_BLOCK): about 20 or more of them, to
    give a spread. The plan is made again after every block. A bench ends at its ops, at
    its tier, at the wall-clock `deadline` the engine set, or by Abandon (kernel timer);
    `why` says which. A first call over `tlong` ends it there: that one call is the
    measurement (why = 'long').
    Every block is calibrated (see the module header).

    Why this shape, measured here on 2026-10-28: the loop itself costs 6 to 10 ns an op
    (overhead takes it off); a clock read around every op would cost 100 ns and bias a 20
    ns op by 100%; a generator that yields every op costs 23 ns an op, one that yields a
    range per block 10 ns; with 1000 ops the standard error was 1 to 4%, and 10000 ops
    made it 1 to 2% for ten times the time. What more ops cannot fix is the machine's own
    drift, which the calibration is for.

    An op that consumes state must restore it (or `prepare` renew it): the probe blocks
    run ops too, and a bench runs up to cap + the probes of them."""

    def __init__(me, worker=None, deadline=None, cap=MAX_OPS, tlong=TIER_SLOW):
        me.worker = worker              # None: no calibration and no hub (see overhead)
        me.deadline = deadline          # perf_counter time by which the bench must end
        me.cap = cap
        me.tlong = tlong                # a call over this many seconds is measured once
        me.warm = []                    # probe blocks (ops, seconds): thrown away
        me.blocks = []                  # timed blocks (ops, seconds)
        me.speed = []                   # the reference step around each timed block
        me.last = 0.0                   # the reference step measured last
        me.done = 0                     # ops timed
        me.timed = 0.0                  # seconds timed
        me.planned = cap
        me.n = 1                        # ops of the block under way
        me.t0 = 0.0
        me.probing = True
        me.used = True                  # the last block was run (count was iterated)
        me.why = ''                     # cap, time, deadline or stopped
        me.lower = 0.0                  # seconds a stopped bench had run: a call took more

    def __enter__(me):
        if me.worker is not None:
            me.last = calibrate()
        return me

    def __exit__(me, kind, value, trace):
        return False                    # whatever was raised goes on

    @property
    def more(me):
        """True while there is another block to time; it plans that block (me.n ops)."""
        if not me.used:
            raise RuntimeError('test.count was not iterated: write `for i in test.count:` '
                               'inside `while test.more:`')
        if me.worker is not None and me.worker.heard():
            raise Stop()
        if me.probing and me.warm and me.warm[0][1] / me.warm[0][0] >= me.tlong:
            me.why = 'long'             # the first call is over tlong: measured once
            return False
        if me.deadline is not None and time.perf_counter() >= me.deadline:
            me.why = 'deadline'
            return False
        if me.probing:
            last = me.warm[-1] if me.warm else None
            if last is None or (last[1] < PROBE_SECS and last[0] < MAX_BLOCK):
                me.n = min(MAX_BLOCK, 2 * last[0]) if last else 1
                me.used = False
                return True
            me.probing = False
        cost = me.timed / me.done if me.done else me.warm[-1][1] / me.warm[-1][0]
        cost = max(cost, 1e-10)
        tier = TIER_FAST if me.cap * cost <= TIER_FAST else TIER_SLOW
        me.planned = max(1, min(me.cap, int(tier / cost)))
        if me.done >= me.planned or me.timed >= tier:
            me.why = 'cap' if me.planned == me.cap and me.done >= me.planned else 'time'
            return False
        me.n = max(1, min(MAX_BLOCK, me.planned // 20, me.planned - me.done))
        me.used = False
        return True

    @property
    def count(me):
        """This block's ops: the clock runs from the first step to the last."""
        return itertools.chain(me.begin(), range(me.n), me.finish())

    def begin(me):
        me.used = True
        me.t0 = time.perf_counter()
        return
        yield

    def finish(me):
        took = time.perf_counter() - me.t0
        step = calibrate() if me.worker is not None else 0.0
        if me.probing:
            me.warm.append((me.n, took))
        else:
            me.blocks.append((me.n, took))
            me.speed.append((me.last + step) / 2)
            me.done += me.n
            me.timed += took
        me.last = step
        return
        yield


def overhead():
    """Seconds one op costs through a Timer with an empty body, the loop's own cost, which
    is taken off every bench: the best of 3 runs of 20000 ops (about 0.2 ms each)."""
    best = math.inf
    for _ in range(3):
        timer = Timer(cap=20000)
        while timer.more:
            for _ in timer.count:
                pass
        best = min(best, timer.timed / timer.done)
    return best


def discover(cls):
    """The bench_* methods of a class in definition order, base classes first."""
    seen = set()
    found = []
    for klass in reversed(cls.__mro__):
        for name in klass.__dict__:
            if name.startswith('bench_') and name not in seen:
                seen.add(name)
                found.append(name)
    return found


def load(me):
    """Import the suite file the way `python b_unit.py` would see it, and return its b_
    classes. Their tearDownClass is the old bench's benchmark driver (or nothing): it is
    switched off, because this engine drives."""
    priv = me.priv
    sys.argv[0] = priv.path
    sys.path.insert(0, os.path.dirname(priv.path))
    spec = importlib.util.spec_from_file_location(priv.name, priv.path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[priv.name] = module
    spec.loader.exec_module(module)
    classes = [obj for key, obj in vars(module).items()
               if key.startswith('b_') and isinstance(obj, type)
               and issubclass(obj, unittest.TestCase) and obj.__module__ == priv.name]
    if not classes:
        raise ImportError(f'{priv.path} has no b_ class that is a unittest.TestCase')
    for cls in classes:
        cls.tearDownClass = classmethod(lambda c: None)
    return classes


class Priv:
    """What a Worker keeps for itself."""
    __slots__ = ('ch', 'tag', 'cfg', 'name', 'path', 'p', 'lines', 'size', 'dropped',
                 'count', 'changed', 'flushed', 'checked', 'hubbeat', 'dead')


class Lines:
    """A file-like object that gives what is written to the worker's output."""
    encoding = 'utf-8'

    def __init__(me, worker, stream):
        me.worker = worker
        me.stream = stream
        me.partial = ''

    def write(me, text):
        me.partial += text
        if '\n' in me.partial:
            *whole, me.partial = me.partial.split('\n')
            for one in whole:
                me.worker.say(one, me.stream)
        return len(text)

    def flush(me):
        if me.partial:
            me.worker.say(me.partial, me.stream)
            me.partial = ''
        me.worker.flush(True)

    def isatty(me):
        return False


class Recorder(unittest.TestResult):
    """Notes each test: name, status, seconds, report. Status is pass, FAIL, slow or skip.

    SLOW is a test that did not finish inside `limit` seconds (1 s): a kernel timer stops
    it, in the middle of its own code if that is running Python, and it is noted ("time too
    high"); one that cannot be interrupted (a sleep, a long C call) is noted when it
    returns. The run goes on after a slow test. It stops at the first FAIL: the tests after
    it are marked skipped, and `failed` names the test."""

    def __init__(me, worker, prefix, limit):
        super().__init__()
        me.worker = worker
        me.prefix = prefix
        me.limit = limit
        me.alarm = Alarm()
        me.failed = None
        me.records = []
        me.name = None
        me.status = 'pass'
        me.report = ''
        me.t0 = 0.0

    def startTest(me, test):
        super().startTest(test)
        me.name = me.prefix.get(type(test), '') + str(
            getattr(test, '_testMethodName', None) or test)
        me.status = 'pass'
        me.report = ''
        me.worker.step('tests', me.name, len(me.records))
        me.t0 = time.perf_counter()
        me.alarm.arm(me.limit)
        me.alarm.inside = True

    def addSuccess(me, test):
        me.alarm.cancel()                   # the test is over: the timer goes first
        super().addSuccess(test)

    def addFailure(me, test, err):
        me.alarm.cancel()
        super().addFailure(test, err)
        me.status = 'FAIL'
        me.report = clip(me.failures[-1][1])

    def addError(me, test, err):
        me.alarm.cancel()
        if issubclass(err[0], Abandon):     # the timer stopped it: slow, not an error
            me.status = 'slow'
            took = time.perf_counter() - me.t0
            me.report = (f'time too high: stopped after {took:.1f} s, the limit is '
                         f'{me.limit:g} s')
            return
        super().addError(test, err)
        text = clip(me.errors[-1][1])
        if me.name is None:                 # setUpClass failed: no test was started
            me.records.append([str(test), 'FAIL', 0.0, text])
            me.failed = me.failed or str(test)
            return
        me.status = 'FAIL'
        me.report = text

    def addSkip(me, test, reason):
        me.alarm.cancel()
        super().addSkip(test, reason)
        me.status = 'skip'
        me.report = str(reason)

    def addUnexpectedSuccess(me, test):
        me.alarm.cancel()
        super().addUnexpectedSuccess(test)
        me.status = 'FAIL'
        me.report = 'unexpected success'

    def stopTest(me, test):
        me.alarm.cancel()
        seconds = time.perf_counter() - me.t0
        super().stopTest(test)
        if me.status == 'pass' and seconds > me.limit:
            me.status = 'slow'              # not interruptible: noted when it ended
            me.report = f'time too high: took {seconds:.1f} s, the limit is {me.limit:g} s'
        if me.name is not None:
            me.records.append([me.name, me.status, round(seconds, 6), me.report])
            if me.status == 'FAIL':
                me.failed = me.failed or me.name
            me.name = None
        me.worker.done(me.records)
        time.sleep(me.worker.priv.cfg['pause'])
        if me.failed or me.worker.heard():
            me.shouldStop = True            # on an error the run stops; on slow it goes on


def clip(text):
    """A traceback cut to REPORT characters, keeping the end, where the error is."""
    return text if len(text) <= REPORT else '...' + text[-REPORT:]


class Worker:
    """One process's run of one suite. See the module header."""

    def __init__(me, path, channel=None, tag=0):
        me.priv = priv = Priv()
        priv.path = os.path.abspath(path)
        priv.name = os.path.splitext(os.path.basename(path))[0]
        priv.cfg = dict(DEFAULTS)
        priv.p = {'suite': priv.name, 'phase': 'start', 'step': None, 'tstart': None,
                  'limit': None, 'done': 0, 'total': 0, 'recs': []}
        priv.lines = []
        priv.size = 0
        priv.dropped = 0
        priv.count = 0
        priv.changed = False
        priv.flushed = 0.0
        priv.checked = 0.0
        priv.hubbeat = None
        priv.dead = False
        priv.tag = tag
        priv.ch = None
        if channel:
            priv.ch = Channel(channel, create=False, wid=tag)
            priv.cfg.update(priv.ch.get(f'hub.config.{tag}') or {})
            if not priv.cfg['live']:
                sys.stdout = Lines(me, 'o')
                sys.stderr = Lines(me, 'e')

    # ---- the channel -------------------------------------------------------------------
    def progress(me, **fields):
        """Merge fields into this process's dict and write p<N>."""
        priv = me.priv
        priv.p.update(fields)
        if priv.ch and not priv.dead:
            try:
                priv.ch[f'spoke.progress.{priv.tag}'] = priv.p
            except ChannelError:
                priv.dead = True

    def step(me, phase, name, done, limit=None):
        """A test or bench call is about to begin: the hub times it from here."""
        me.progress(phase=phase, step=name, tstart=time.time(), done=done,
                    limit=me.priv.cfg['timeout'] if limit is None else limit)

    def done(me, records):
        me.progress(tstart=None, step=None, done=len(records), recs=records)

    def say(me, text, stream='o'):
        """Add a line to the output ring; the oldest go when it is over RING bytes."""
        priv = me.priv
        priv.lines.append([stream, text])
        priv.size += len(text) + 8
        priv.count += 1
        while priv.size > RING and priv.lines:
            gone = priv.lines.pop(0)
            priv.size -= len(gone[1]) + 8
            priv.dropped += 1
        priv.changed = True
        me.flush(False)

    def flush(me, force):
        priv = me.priv
        if not (priv.ch and priv.changed and not priv.dead):
            return
        now = time.time()
        if force or now - priv.flushed >= FLUSH:
            try:
                priv.ch[f'spoke.output.{priv.tag}'] = {'n': priv.count, 'dropped': priv.dropped,
                                           'lines': priv.lines}
            except ChannelError:
                priv.dead = True
            priv.changed = False
            priv.flushed = now

    def heard(me):
        """True when this process should stop: the hub said so, has gone, or has ended."""
        priv = me.priv
        if not priv.ch:
            return False
        if priv.dead:
            return True
        try:
            message = priv.ch.get(f'hub.message.{priv.tag}')
            if message and message.get('cmd') == 'terminate':
                return True
            now = time.time()
            if now - priv.checked >= min(1.0, priv.cfg['orphan'] / 4):
                priv.checked = now
                hub = priv.ch.get(f'hub.config.{priv.tag}')
                if hub:
                    priv.hubbeat = hub['beat']
            return priv.hubbeat is not None and now - priv.hubbeat > priv.cfg['orphan']
        except Torn:                        # the hub was rewriting it: no news this time
            return False
        except ChannelError:                # the block is terminated
            priv.dead = True
            return True

    # ---- the run -----------------------------------------------------------------------
    def run(me, want_test, want_bench):
        """Run what was asked and return the result dict, which is also left on the
        channel as p<N>['end'] for the hub."""
        priv = me.priv
        start = time.perf_counter()
        result = {'suite': priv.name, 'pid': os.getpid(), 'python': sys.version.split()[0],
                  'path': priv.path}
        try:
            me.progress(phase='import', step='import', tstart=time.time(),
                        limit=priv.cfg['timeout'] * 3, pid=os.getpid())
            classes = load(me)
            me.progress(tstart=None, step=None)
            first = classes[0]
            result['sources'] = source_names(classes)
            result['version'] = str(getattr(first, 'BenchVersion', ''))
            result['header'] = str(getattr(first, 'BenchHeader', ''))
            if want_test:
                result['tests'] = me.run_tests(classes)
            failed = want_test and any(r[1] == 'FAIL' for r in result['tests']['records'])
            if want_bench and failed:
                result['bench'] = {'skipped': 'a test failed'}
            elif want_bench and not me.heard():
                result['bench'] = me.run_benches(classes, want_test, start)
        except Stop:
            result['stopped'] = True
        except BaseException:
            result['crash'] = traceback.format_exc()[-3000:]
        result['secs'] = round(time.perf_counter() - start, 3)
        me.finish(result)
        return result

    def run_tests(me, classes):
        priv = me.priv
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        prefix = {}
        scheduled = []
        total = 0
        for cls in classes:
            if len(classes) > 1:
                prefix[cls] = cls.__name__ + '.'
            for name in loader.getTestCaseNames(cls):
                if name not in priv.cfg['skip']:
                    suite.addTest(cls(name))
                    scheduled.append(prefix.get(cls, '') + name)
                    total += 1
        me.progress(phase='tests', total=total, done=0, recs=[])
        recorder = Recorder(me, prefix, float(priv.cfg['test_time']))
        start = time.perf_counter()
        suite.run(recorder)
        if recorder.failed:                 # an error stops the run: the rest are not run
            ran = {r[0] for r in recorder.records}
            for name in scheduled:
                if name not in ran:
                    recorder.records.append([name, 'skip', 0.0,
                                             f'stopped: {recorder.failed} failed'])
        return {'records': recorder.records, 'total': total,
                'secs': round(sum(r[2] for r in recorder.records if r[1] != 'skip'), 3),
                'wall': round(time.perf_counter() - start, 3),
                'stopped': recorder.shouldStop}

    def time_one(me, cls, holder, name, index, allowance, alarm):
        """Run one bench method with a Timer of its own, for at most `allowance` seconds of
        wall time: (the timer, what the method returned, the traceback if it raised). A
        kernel timer, a little after the allowance, ends a bench stuck inside one call
        (Abandon: the timer then says `stopped` and how long the bench had run); the hub's
        kill, a little after that, is behind it."""
        priv = me.priv
        code = getattr(cls, name).__code__
        if code.co_argcount != 2 or code.co_varnames[1] == 'Nx':
            return Timer(), None, (f'{name} is not of the form bench_x(self, timer): the '
                                   f'old bench_x(self, Nx) has to be converted')
        cfg = priv.cfg
        timer = Timer(me, time.perf_counter() + allowance, tlong=float(cfg['tlong']))
        started = time.perf_counter()
        me.step('bench', name, index, float(cfg['tmax']) + 3.0)
        alarm.arm(float(cfg['tmax']) + 0.5)
        alarm.inside = True
        out, error = None, ''
        try:
            out = getattr(cls, name)(holder, timer)
        except Stop:
            raise
        except Abandon:
            timer.why = 'stopped'
            timer.lower = time.perf_counter() - started
        except Exception:
            error = clip(traceback.format_exc())
        finally:
            alarm.cancel()
        me.progress(tstart=None, step=None, done=index + 1)
        time.sleep(priv.cfg['pause'])
        if me.heard():
            raise Stop()
        return timer, out, error

    def run_benches(me, classes, tests_ran, start):
        """Time every bench_* of every class; the rows of all go in one result."""
        me.progress(phase='bench', total=0, done=0)
        results = [bench_one(me, cls, tests_ran, start, len(classes) > 1)
                   for cls in classes]
        merged = results[0]
        for more in results[1:]:
            merged['rows'] += more['rows']
        return merged

    def finish(me, result):
        """Leave the result on the channel, flush the output, and let go."""
        priv = me.priv
        for stream in (sys.stdout, sys.stderr):
            if isinstance(stream, Lines):
                stream.flush()
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        me.flush(True)
        shown = result                          # the page shows the tests of earlier spokes too
        prior = priv.cfg.get('prior')
        if prior and prior.get('records'):
            own = result.get('tests') or {'records': [], 'secs': 0.0}
            shown = dict(result, tests={'records': prior['records'] + own['records'],
                                        'secs': prior['secs'] + own['secs']})
        if priv.ch and not priv.dead:
            try:
                priv.ch[f'spoke.htm.{priv.tag}'] = bytes(unithtm(shown)).decode('utf-8')
                priv.ch[f'spoke.data.{priv.tag}'] = unitdata(result)
            except ChannelError:
                priv.dead = True
        me.progress(phase='end', step=None, tstart=None, recs=[])
        if priv.ch:
            priv.ch.close()


def bench_one(me, cls, tests_ran, start, prefixed):
    """Time the benches of one class. Each bench method gets a Timer of its own (see
    Timer) and a share of the time left in the file's budget, so every bench is timed
    even when the first ones are slow: min(TIER_SLOW + 0.25 s, what is left over the
    benches to go), never under 0.3 s. `start` is when the worker began: import, tests and
    fixtures have used part of the budget. A bench that raises is caught and reported, and
    the benches stop there.

    The rows come from the blocks: r is the mean of the blocks' r after the outlier rule,
    cv their stdev in percent, se the standard error. A bench with no timed block but a
    probe block is reported from that probe (the time over the calls done); one stopped
    before any call ended is reported with the least a call cost."""
    priv = me.priv
    cfg = priv.cfg
    names = discover(cls)
    if not names:
        return {'rows': [], 'skipped': 'no bench methods'}
    if not tests_ran:
        cls.setUpClass()
    budget = max(2.0, cfg['budget'] - (time.perf_counter() - start))
    holder = cls.__new__(cls)
    begin = time.perf_counter()
    loop = overhead()
    timers = []
    labels = []
    groups = []
    errors = []                         # [label, traceback] of the bench that raised
    alarm = Alarm()
    me.progress(live=True)              # the hub reads the machine from here ...
    live = (time.process_time(), time.perf_counter())
    try:
        for i, name in enumerate(names):
            share = (budget - (time.perf_counter() - begin)) / (len(names) - i)
            timer, out, error = me.time_one(cls, holder, name, i,
                                            min(TIER_SLOW + 0.25, max(0.3, share)), alarm)
            timers.append(timer)
            label = name.replace('bench_', '')
            group = ''
            if isinstance(out, str):
                label = out or label
            elif isinstance(out, tuple) and out:
                if isinstance(out[0], (int, float)):
                    error = (f"{name} returned a time: the old form returns (seconds, "
                             f"label, group), now return 'label', 'group'")
                label = str(out[0]) if out[0] else label
                group = str(out[1]) if len(out) > 1 and out[1] else ''
            if not (error or timer.warm or timer.blocks or timer.lower):
                error = (f'{name} never ran its timer: use `with timer as test:`, '
                         f'`while test.more:`, `for i in test.count:`')
            labels.append(label)
            groups.append(group)
            if error:
                errors.append([label, error])
                break
    finally:
        alarm.cancel()
        me.progress(live=False)         # ... to here
    secs = time.perf_counter() - begin
    if errors:
        return {'rows': [], 'errors': errors,
                'skipped': f'bench {errors[0][0]} raised: the benchmarks stopped there'}
    cpu = time.process_time() - live[0]
    live_wall = time.perf_counter() - live[1]
    steps = [step for t in timers for step in (t.speed or [t.last])]
    steps_kept, steps_out = rm_outliers(steps)
    perinner = mean(steps_kept)                 # a reference step at the usual speed
    ref_cv = std(steps_kept) / perinner * 100 if perinner else 0.0
    rows = []
    for i, timer in enumerate(timers):
        if timer.blocks:
            ratios = [max(took / n - loop, 0.0) / step
                      for (n, took), step in zip(timer.blocks, timer.speed)]
            ops, timed = timer.done, timer.timed
        elif timer.warm:                        # too slow for a timed block: the probe
            n, took = timer.warm[-1]
            ratios = [max(took / n - loop, 0.0) / (timer.last or perinner)]
            ops, timed = n, took
        else:                                   # not one call ended: the least it cost
            ratios = [timer.lower / perinner]
            ops, timed = 0, timer.lower
        kept, dropped = rm_outliers(ratios)
        ratio = mean(kept)
        cv = std(kept) / ratio * 100 if ratio else 0.0
        se = cv / math.sqrt(len(kept))
        if not ops:
            flag = f'stopped: a call took over {timer.lower:.1f} s'
        elif timer.why == 'stopped':
            flag = f'stopped at {ops} ops'
        elif timer.why == 'long':
            flag = f'long: one call, {timed:.1f} s'
        elif not timer.blocks:
            flag = f'slow: {ops} call, not timed in blocks'
        elif timer.why == 'deadline':
            flag = f'cut short at {ops} ops'
        elif ops < timer.cap:
            flag = f'slow: {ops} ops'
        elif se > NOISY or not ratio:
            flag = 'noisy'
        else:
            flag = ''
        rows.append({'label': (cls.__name__ + ': ' if prefixed else '') + labels[i],
                     'group': groups[i], 'cost': ratio * perinner, 'r': ratio, 'cv': cv,
                     'se': se, 'out': dropped, 'ops': ops, 'blocks': len(timer.blocks),
                     'secs': timed, 'flag': flag})
    return {'rows': rows, 'cap': MAX_OPS, 'loop': loop, 'perinner': perinner,
            'ref_cv': ref_cv, 'ref_out': steps_out, 'valid': ref_cv <= REF_CV_TOL,
            'cpu': cpu, 'live_wall': live_wall, 'secs': round(secs, 3),
            'budget': round(budget, 2)}


class bench(unittest.TestCase):
    """A base class for a b_ suite. It is optional: the engine runs any TestCase with
    bench_* methods. Declare the attributes and write test_* and bench_*; runbench.py
    runs the file."""
    BenchName = ''
    BenchVersion = 'M1.0.0'
    BenchHeader = ''
    sources = []                    # module names of the code under test: the report shows the file use loads

    @classmethod
    def setUpClass(cls):
        cls.setup_fixtures()

    @classmethod
    def setup_fixtures(cls):
        """Build shared state once, as class attributes."""

    def test_benchContract(self):
        if type(self) is bench:
            self.skipTest('the base class owns no benchmarks')
        self.assertTrue(discover(type(self)), 'no bench methods: declare bench_* methods')


# ---- the unit's page --------------------------------------------------------------------
TEMPLATE = os.path.join(PRIMARY, 'html', 'bench.html')


def unit_of(rows):
    """(multiplier, name) for the costs of a table, from their median."""
    costs = sorted(r['cost'] for r in rows) or [0.0]
    middle = costs[len(costs) // 2]
    return (1.0, 's') if middle >= 0.7 else (1e3, 'ms') if middle >= 0.0007 else (1e6, 'us')


def unitdata(result):
    """The plain data of a run, for the hub: info, tests and bench as dicts of dicts."""
    tests = result.get('tests') or {}
    bench = result.get('bench') or {}
    keys = ('suite', 'version', 'header', 'pid', 'python', 'secs', 'crash', 'stopped')
    data = {'info': {k: result.get(k) for k in keys}}
    if 'tests' in result:                       # a key only for what this run did
        data['tests'] = {name: {'status': status, 'secs': secs, 'text': text}
                         for name, status, secs, text in tests.get('records', [])}
        data['testsecs'] = tests.get('secs', 0.0)
    if 'bench' in result:
        data['bench'] = {row['label']: {k: v for k, v in row.items() if k != 'label'}
                         for row in bench.get('rows', [])}
        data['benchinfo'] = {k: v for k, v in bench.items() if k != 'rows'}
    return data


def unitmd(result):
    """The Markdown of a run, in sections: the first line, speed, tests (see marker.md)."""
    tests = result.get('tests') or {}
    records = tests.get('records', [])
    bench = result.get('bench') or {}
    rows = bench.get('rows', [])
    bar = lambda text: str(text).replace('|', '\\|')
    md = mdwriteln(None, f'**{result.get("version", "")}**', result.get('header', ''),
                   '| tests', len(records), 'in', tests.get('secs', 0.0), 's')
    if rows:
        mdwriteln(md, '| up to', bench['cap'], 'ops each,', bench['secs'], 's, the loop',
                  bench['loop'] * 1e9, 'ns an op')
    mdwriteln(md, '_\\section:speed/_')
    if rows:
        scale, unit = unit_of(rows)
        slow = ['{.slow}' if r['flag'] and r['flag'] != 'noisy' else '' for r in rows]
        mdwriteln(md, '| group | method | r | mean', unit, '| +/-% | se % | ops | secs | note |')
        mdwriteln(md, '|:--|:--|--:|--:|--:|--:|--:|--:|:--|')
        mdwriteln(md, '|', [s + bar(r['group']) for s, r in zip(slow, rows)],
                  '|', [bar(r['label']) for r in rows], '|', [r['r'] for r in rows],
                  '|', [r['cost'] * scale for r in rows], '|', [r['cv'] for r in rows],
                  '|', [r['se'] for r in rows], '|', [r['ops'] for r in rows],
                  '|', [r['secs'] for r in rows], '|', [bar(r['flag']) for r in rows], '|')
    elif bench:
        mdwriteln(md, '**Not timed:**', bench.get('skipped'))
    else:
        mdwriteln(md, '*No benchmark was run.*')
    for label, trace in bench.get('errors', []):
        mdwriteln(md, '\n### BENCH FAILED', label, '\n\n```\n' + trace + '\n```')
    mdwriteln(md, '_\\section:tests/_')
    if records:
        note = [bar(x.splitlines()[0]) if x and s in ('slow', 'skip') else ''
                for n, s, t, x in records]
        mark = ['{.bad}' if s == 'FAIL' else '{.slow}' if s == 'slow' else ''
                for n, s, t, x in records]
        mdwriteln(md, '| test | result | seconds | note |')
        mdwriteln(md, '|:--|:--|--:|:--|')
        mdwriteln(md, '|', [m + bar(n) for m, (n, s, t, x) in zip(mark, records)],
                  '|', [r[1] for r in records], '|', [r[2] for r in records], '|', note, '|')
    for name, status, secs, trace in records:
        if status == 'FAIL':
            mdwriteln(md, '\n### FAIL', name, '\n\n```\n' + trace + '\n```')
    if result.get('crash'):
        mdwriteln(md, '\n### Did not run\n\n```\n' + result['crash'] + '\n```')
    return md


NOTE_SOURCES = """<p><b>No sources are declared in this suite, so the report shows only the test code.</b></p>
<p>The report puts the code under test beside the test, one Code tab for each module, so you can follow a
failing test into the source and write a comment on the line. Only the suite's author knows which
modules those are. Add, in the class of <code>{name}</code>:</p>
<pre>sources = ['unit']     # module names; the file shown is the one use loads: the .pyx, else the .py</pre>
<p>Without it you get this suite's own Code tab and nothing of the unit: no source code is shown.</p>"""
NOTE_MISSING = """<p><b>{names}: not found.</b> <code>sources</code> in <code>{name}</code> names the module;
the search of <code>use</code> from the suite's folder ({here}) found no file for it. Until it is found there
is no code tab for it.</p>"""


def source_names(classes):
    """The module names the suite's classes declare in `sources`, once each, in order."""
    names = []
    for cls in classes:
        value = getattr(cls, 'sources', None) or []
        for name in [value] if isinstance(value, str) else value:
            if str(name) not in names:
                names.append(str(name))
    return names


def home_of():
    """The folder the report server's ./ paths start at (rs3util.HOME): the parent of the repository that holds this file."""
    here = os.path.dirname(os.path.abspath(__file__))
    while not os.path.isdir(os.path.join(here, '.git')) and os.path.dirname(here) != here:
        here = os.path.dirname(here)
    return os.path.dirname(here)


def server_path(path):
    """The ./ path the report server knows a file by, or None when the file is not under home_of()."""
    try:
        rel = os.path.relpath(os.path.abspath(path), home_of())
    except ValueError:                          # another drive
        return None
    return None if rel.startswith('..') else './' + rel.replace(os.sep, '/')


def source_panel(path):
    """The html of a source tab: a layout container, {{layout=[mt,[cd;eb]],PATH}}, that the report server makes the methods,
    code and comment panes of that file in (rs3pages.unfold). The file the server cannot name gets a note instead."""
    named = server_path(path)
    if named is None:
        return ('<div class="note"><p>' + html.escape(str(path)) + ' is not under the folder the report server reads '
                'from, so it has no code tab.</p></div>'), True
    return '{{layout=[mt,[cd;eb]],' + named + '}}', False


def note_panel(text):
    return '<div class="note">' + text + '</div>', True


def sourcetabs(suite, names=()):
    """[(label, panel html, bad)]: the source tabs of a unit: the suite itself, then the file use would load for each
    module in `names` (see locate: the code that ran), each labelled with its file name less .py or .pyx (the extension
    stays where two files would share a label). A suite that declares no module, or a module that is not found, gets a
    red tab that says so."""
    out = []
    name = os.path.basename(suite)
    here = os.path.dirname(os.path.abspath(suite))
    found = {}
    lost = []
    for module in names:
        path = locate(module, here)
        if path is None:
            lost.append(module)
        else:
            found[module] = str(path)
    stems = [os.path.splitext(n)[0] for n in [name] + [os.path.basename(p) for p in found.values()]]
    label = lambda n: (os.path.splitext(n)[0] if stems.count(os.path.splitext(n)[0]) == 1
                       else n)
    out.append((label(name),) + source_panel(suite))
    if not names:
        out.append(('No sources',) + note_panel(NOTE_SOURCES.format(name=html.escape(name))))
    for path in found.values():
        out.append((label(os.path.basename(path)),) + source_panel(path))
    if lost:
        out.append(('Missing sources',) + note_panel(NOTE_MISSING.format(
            names=html.escape(', '.join(lost)), name=html.escape(name), here=html.escape(here))))
    return out


def unithtm(result):
    """The unit's page: its Markdown, converted and pasted into bench.html, which gives it the tab bar (Speed, Tests, the
    sources) and the script that shows one panel at a time. The id of a unit's tabs and panels starts with its group, so
    several units share a page. The place for the machine is left as {{machine}} for the hub to fill."""
    htm = md2htm(unitmd(result))
    group = 'u' + re.sub(r'\W', '_', os.path.splitext(os.path.basename(str(result.get('path') or 'unit')))[0])
    bench = result.get('bench') or {}
    failing = any(r[1] == 'FAIL' for r in (result.get('tests') or {}).get('records', []))
    tabs = [('Speed', bool(bench.get('killed') or bench.get('errors')), None),
            ('Tests', bool(failing or result.get('crash')), None)]
    try:
        tabs += [(label, bad, panel) for label, panel, bad in sourcetabs(result['path'], result.get('sources') or [])]
    except (KeyError, OSError):                 # no source to show
        tabs.append(('No sources', True, note_panel('<p>no source</p>')[0]))
    buttons = ''.join(f'<button class="btab{" on" if i == 0 else ""}{" bad" if bad else ""}" data-group="{group}" '
                      f'data-tab="{group}{i}">{html.escape(label)}</button>' for i, (label, bad, panel) in enumerate(tabs))
    panels = ''.join(f'<div class="bpanel{" bad" if bad else ""}" data-group="{group}" id="{group}{i}" hidden>' + chr(10) + f'{panel}' + chr(10) + '</div>' + chr(10)
                     for i, (label, bad, panel) in enumerate(tabs) if panel is not None)
    htmwriteln(htm, '<!--SECTION codetabs-->')
    htmappend(htm, panels.encode('utf-8'))
    return htmtemplate(TEMPLATE, htm, MACHINE='{{machine}}', TABBAR=buttons, GROUP=group)
