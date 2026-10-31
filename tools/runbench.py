r"""runbench.py -- run b_ suites: the tests in parallel spokes, the benchmarks one at a time.

Use:     python runbench.py [target ...] [-name=NAME] [-nohub] [-test] [-bench] [-timeout=SECONDS]
  target   a suite file, a suite name (unit or b_unit), a folder (every b_*.py in it) or `all`.
           None: the folder test or tests of the current directory.
  -name    the report's name: letters, digits, . _ - (no path). The default is
           benchx<suites>-<folder>: the folder is the first one the suites share, or its parent
           when that is test or tests. Suites with no folder in common (only the drive) are refused.
  -nohub   one suite after another, its own printing live on the console.
  -test    the tests only: no benchmarks are run, and the report says nothing was timed.
  -bench   the benchmarks only: the tests are not run, so no failing test holds a benchmark back.
           Neither word, or both, runs the tests and then the benchmarks of the suites that passed.
  -timeout   the hang guard in seconds (default 10): the hub kills a spoke whose one test is still
           going after this long, notes that test as slow, and goes on. It is the `timeout` of runbench().
  The report is results/<name>_<date>_<time>.html: a folder beside this folder, made when
  missing. The console shows its path, and a line of totals. Exit code: 0 all passed; 1 a suite
  failed; 2 a target names nothing, or a refused name or folders.

Python:  runbench(targets=(), name='', nohub=False, test_time=1.0, timeout=10.0, budget=10.0,
                   tlong=1.0, tmax=42.0, grace=3.0, jobs=0, bench_jobs=1, pause=0.010,
                   worker_pause=None, orphan=5.0, tick=True, collect=None, server=True,
                   results=None, tests=True, benches=True) -> the number of suites that failed
  collect  a list that gets the suites' dicts (the tests, the bench, the page).
  server   True: register the results folder with the report server and start it (one only);
           False: not; a tuple (port, roots file, log file, pid file): a server of your own.
  results  the folder for the reports, instead of the one beside this folder.
  tests, benches  False leaves that part out: -test is benches=False, -bench is tests=False.

A spoke (a Worker of bench.py, started with python -c, see SPOKE) writes into the shared dict (cumulette.py), N being its number:
  hub.config.N      the hub's limits for it, and `prior`: the tests of earlier spokes
  hub.message.N     the hub's words to it (terminate)
  spoke.progress.N  where it is: phase, step, start of the step, tests done so far
  spoke.output.N    what it printed
  spoke.htm.N       its page of the suite: str of HTML, with {{machine}} left for the hub
  spoke.data.N      what it found, as dicts: info, tests, testsecs, bench, benchinfo
The hub makes the tab, names it for the suite, puts the page in it, fills {{machine}}, adds
the Summary, and pastes all into runbench.html (with runbench.css and runbench.js).

VERSION  M4 m04.v03 (2026-10-31): -test and -bench (tests=False, benches=False): one part of a run.
         M4 m04.v02 (2026-10-31): -timeout=SECONDS; the console words are read by words(). The workers
         are started here with python -c (SPOKE): bench.py has no main() to run.
         M4 m04.v01 (2026-10-30): the file is runbench.py (it was runbench3.py); the support modules
         and the page files are in primary/ and primary/html/.
         M3 m03.v02 (2026-10-29): the page carries the colours of the code roles (codelex.css(),
         from lang/python.mu and cython.mu).
         M3 m03.v01 (2026-10-28): rebuilt from zprev/runbench2.py: the report is the spokes'
         pages and the hub's Summary, as Markdown and templates; dotted channel keys; names
         and results folder by rule; the console only reports.
"""
import ast
import base64
import collections
import json
import os
import re
import struct
import subprocess
import sys
import time

# the support modules (codelex, codemark, htmlwriter, cumulette, reportserver) and the compiled
# ones (marked, mdwriter) are in primary/ below this file: use finds them there
PRIMARY = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'primary')   # the page files
from use import load, use
use('primary', 'silent')
import codelex
import reportserver as rsrv
from htmlwriter import htmappend, htmsave, htmtemplate, htmwriteln
load('marked', 'mdwriter')            # md2htm, mdwriteln: built by use into primary/pyxfiles
from cumulette import Channel, ChannelError, Torn

__all__ = ['runbench2']

BEAT = 0.25                         # seconds between the hub's heartbeats to a worker
RETRIES = 8                         # fresh workers started for one suite after timeouts
STEP_CYCLES = 568                   # as in bench2.py
REF_MHZ = 3000
QUIET = 3.0                         # longest wait for the machine to recover, per bench
BAND = 1.10                         # a probe this much slower than the best is not quiet
STARTUP = 3                         # a worker may take this many timeouts to start
START = 0.5                         # seconds a worker takes to start, off a file's budget
NOT_TIMED = 'a test failed or the suite did not run: investigate that first'
NOT_ASKED = 'run with -test: the tests only, nothing was timed'
SPOKE = ('import sys\n'                        # the program of each worker process, run with python -c:
         'tools, path, kind, name, tag = sys.argv[1:6]\n'      # its words: tools folder, suite file,
         'sys.path.insert(0, tools)\n'                         # phase (test or bench), the hub's
         'from bench import Worker\n'                          # block, and this worker's number
         'Worker(path, name, int(tag)).run(kind == "test", kind == "bench")\n')


# ---- finding the suites ---------------------------------------------------------------
def suites_in(folder, deep=False):
    """The b_*.py files of a folder, sorted; below it as well if deep."""
    found = []
    for root, dirs, files in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if not d.startswith(('.', '__')) and d != 'prev')
        found += [os.path.join(root, f) for f in sorted(files)
                  if f.startswith('b_') and f.endswith('.py')]
        if not deep:
            break
    return found


def find_suites(targets, cwd):
    """(paths, the places that were looked at and had nothing)."""
    here = os.path.dirname(os.path.abspath(__file__))
    near = os.path.dirname(here)
    places = [cwd, os.path.join(cwd, 'test'), os.path.join(cwd, 'tests'),
              os.path.join(near, 'test'), os.path.join(near, 'tests')]
    folders = [p for p in places[1:3] + places[3:] if os.path.isdir(p)]
    found = []
    missing = []
    for target in targets or ['']:
        if not target:
            hit = [places[1], places[2]]
            hit = [p for p in hit if os.path.isdir(p)]
            if hit:
                found += suites_in(hit[0])
            else:
                missing.append('(no target, and no test or tests folder in ' + cwd + ')')
            continue
        if target == 'all':
            if folders:
                found += suites_in(folders[0], deep=True)
            else:
                missing.append('all: no test or tests folder')
            continue
        names = ['b_' + target + '.py', 'b_' + target, target, target + '.py']
        paths = [os.path.join(place, name) for name in names for place in [''] + places]
        files = [p for p in paths if p.endswith('.py') and os.path.isfile(p)]
        dirs = [p for p in paths if os.path.isdir(p)]
        if files:
            found.append(files[0])
        elif dirs:
            found += suites_in(dirs[0])
        else:
            missing.append(target)
    unique = []
    for path in found:
        full = os.path.abspath(path)
        if full not in unique:
            unique.append(full)
    return unique, missing


# ---- small things ---------------------------------------------------------------------
def step_time(n=20000):
    """Seconds of one step of the reference loop (the same loop as bench2.py's)."""
    h = 5381
    m = 2**32
    t0 = time.perf_counter()
    for j in range(n):
        h = (h * 33 + j) % m
    return (time.perf_counter() - t0) / n


def kill_tree(proc):
    """End a worker and everything it started."""
    if proc.poll() is not None:
        return
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        proc.kill()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass


def seconds(value):
    if value < 100:
        return f'{value:.1f} s'
    return f'{int(value // 60)}m{value % 60:02.0f}s'


class Gauge:
    """What the OS counters need to be kept between two looks (Windows only)."""
    __slots__ = ('ok', 'k32', 'u64', 'Memory', 'Power', 'Disk', 'pdh', 'query', 'cores',
                 'rated', 'disk', 'value', 'counters', 'wt', 'ctypes')


class Meter:
    """Reads the PC's counters: power, memory, CPU, the disk's busy time and the clock of
    the fastest core. snap() is one look; figures(a, b, ...) is the machine line between
    two. The clock is the "% Processor Performance" counter (what Task Manager shows: it
    sees turbo and caps) times the rated clock; the disk is the driver's idle time over
    the interval, for the volume the run is on. A look that fails gives None, never an
    error: a meter must not stop a run."""

    def __init__(me):
        me.priv = gauge = Gauge()
        gauge.ok = False
        if os.name != 'nt':
            return
        try:
            import ctypes
            import ctypes.wintypes as wt
            gauge.ctypes = ctypes
            gauge.wt = wt
            u64 = ctypes.c_ulonglong
            gauge.u64 = u64
            k32 = ctypes.WinDLL('kernel32', use_last_error=True)
            gauge.k32 = k32

            class Memory(ctypes.Structure):
                _fields_ = [('length', wt.DWORD), ('load', wt.DWORD)] + [
                    (f'f{i}', u64) for i in range(7)]

            class Power(ctypes.Structure):
                _fields_ = [('ac', ctypes.c_ubyte), ('flag', ctypes.c_ubyte),
                            ('pct', ctypes.c_ubyte), ('saver', ctypes.c_ubyte),
                            ('life', wt.DWORD), ('full', wt.DWORD)]

            class Disk(ctypes.Structure):
                _fields_ = [('read', ctypes.c_longlong), ('written', ctypes.c_longlong),
                            ('readTime', ctypes.c_longlong),
                            ('writeTime', ctypes.c_longlong), ('idle', ctypes.c_longlong),
                            ('readCount', wt.DWORD), ('writeCount', wt.DWORD),
                            ('queue', wt.DWORD), ('split', wt.DWORD),
                            ('clock', ctypes.c_longlong), ('device', wt.DWORD),
                            ('manager', wt.WCHAR * 8)]

            class Core(ctypes.Structure):
                _fields_ = [(name, wt.ULONG) for name in (
                    'number', 'maxMhz', 'currentMhz', 'limitMhz', 'maxIdle', 'idle')]

            gauge.Memory = Memory
            gauge.Power = Power
            gauge.Disk = Disk
            k32.GetSystemTimes.argtypes = [ctypes.POINTER(u64)] * 3
            k32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(Memory)]
            k32.GetSystemPowerStatus.argtypes = [ctypes.POINTER(Power)]
            k32.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p,
                                        wt.DWORD, wt.DWORD, wt.HANDLE]
            k32.CreateFileW.restype = wt.HANDLE
            k32.DeviceIoControl.argtypes = [wt.HANDLE, wt.DWORD, ctypes.c_void_p, wt.DWORD,
                                            ctypes.c_void_p, wt.DWORD,
                                            ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
            gauge.cores = os.cpu_count() or 1
            info = (Core * gauge.cores)()
            powrprof = ctypes.WinDLL('powrprof')
            if powrprof.CallNtPowerInformation(11, None, 0, ctypes.byref(info),
                                               ctypes.sizeof(info)) != 0:
                raise OSError('no processor information')
            gauge.rated = max(core.maxMhz for core in info)
            drive = os.path.splitdrive(os.getcwd())[0] or 'C:'
            handle = k32.CreateFileW(chr(92) * 2 + '.' + chr(92) + drive, 0, 3, None, 3, 0,
                                     None)
            gauge.disk = None if handle in (None, ctypes.c_void_p(-1).value) else handle
            me.open_clock()
            gauge.ok = True
            me.snap()                           # the first look only primes the counters
        except Exception:
            gauge.ok = False

    def open_clock(me):
        """One PDH counter of % Processor Performance for each core."""
        gauge = me.priv
        ctypes = gauge.ctypes
        wt = gauge.wt
        pdh = ctypes.WinDLL('pdh')
        handle = ctypes.c_void_p

        class Number(ctypes.Union):
            _fields_ = [('whole', ctypes.c_long), ('real', ctypes.c_double),
                        ('large', ctypes.c_longlong)]

        class Value(ctypes.Structure):
            _fields_ = [('status', wt.DWORD), ('number', Number)]

        pdh.PdhOpenQueryW.argtypes = [wt.LPCWSTR, ctypes.c_void_p, ctypes.POINTER(handle)]
        pdh.PdhAddEnglishCounterW.argtypes = [handle, wt.LPCWSTR, ctypes.c_void_p,
                                              ctypes.POINTER(handle)]
        pdh.PdhCollectQueryData.argtypes = [handle]
        pdh.PdhGetFormattedCounterValue.argtypes = [handle, wt.DWORD,
                                                    ctypes.POINTER(wt.DWORD),
                                                    ctypes.POINTER(Value)]
        gauge.query = handle()
        if pdh.PdhOpenQueryW(None, None, ctypes.byref(gauge.query)) != 0:
            raise OSError('no performance counters')
        counters = []
        for core in range(gauge.cores):
            one = handle()
            path = chr(92) + f'Processor Information(0,{core})' + chr(92) + (
                '% Processor Performance')
            if pdh.PdhAddEnglishCounterW(gauge.query, path, None, ctypes.byref(one)) != 0:
                raise OSError('no counter ' + path)
            counters.append(one)
        gauge.pdh = pdh
        gauge.counters = counters
        gauge.value = Value

    def snap(me):
        """(wall, PC idle, PC total, memory %, power, disk idle, disk clock, core MHz)."""
        gauge = me.priv
        wall = time.perf_counter()
        if not gauge.ok and not hasattr(gauge, 'counters'):
            return (wall,) + (None,) * 7
        try:
            ctypes = gauge.ctypes
            wt = gauge.wt
            k32 = gauge.k32
            idle = gauge.u64()
            kern = gauge.u64()
            user = gauge.u64()
            k32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kern), ctypes.byref(user))
            memory = gauge.Memory()
            memory.length = ctypes.sizeof(memory)
            k32.GlobalMemoryStatusEx(ctypes.byref(memory))
            power = gauge.Power()
            k32.GetSystemPowerStatus(ctypes.byref(power))
            disk_idle = disk_clock = None
            if gauge.disk:
                perf = gauge.Disk()
                got = wt.DWORD()
                if k32.DeviceIoControl(gauge.disk, 0x70020, None, 0, ctypes.byref(perf),
                                       ctypes.sizeof(perf), ctypes.byref(got), None):
                    disk_idle = perf.idle
                    disk_clock = perf.clock
            gauge.pdh.PdhCollectQueryData(gauge.query)
            best = 0.0
            for counter in gauge.counters:
                value = gauge.value()
                if gauge.pdh.PdhGetFormattedCounterValue(counter, 0x8200, None,
                                                         ctypes.byref(value)) == 0:
                    best = max(best, value.number.real)
            return (wall, idle.value, kern.value + user.value, memory.load,
                    {1: 'AC', 0: 'BATTERY'}.get(power.ac, '?'), disk_idle, disk_clock,
                    gauge.rated * best / 100 or None)
        except Exception:
            return (wall,) + (None,) * 7

    def figures(me, first, last, perinner, cpu, wall):
        """The machine line's numbers between two looks. perinner is the worker's seconds
        per reference step: speed is a step at 3 GHz over this one, so above 100% is turbo.
        cpu and wall are the worker's own CPU and wall seconds over the same run."""
        out = {'power': last[4], 'mem': last[3], 'mhz': last[7], 'speed': None,
               'pc_cpu': None, 'disk': None, 'py_share': None}
        if first[2] is not None and last[2] is not None and last[2] > first[2]:
            out['pc_cpu'] = 100 * (1 - (last[1] - first[1]) / (last[2] - first[2]))
        if first[6] is not None and last[6] is not None and last[6] > first[6]:
            out['disk'] = max(0.0, 100 * (1 - (last[5] - first[5]) / (last[6] - first[6])))
        if perinner:
            out['speed'] = 100 * (STEP_CYCLES / REF_MHZ * 1e-6) / perinner
        if wall:
            out['py_share'] = min(100.0, 100 * cpu / wall)
        return out


def tick_file(path):
    """Add one to the progress field of the BenchVersion = "M<mark>.<manual>.<progress>" of
    a b_ class in a suite file and return (old, new), or None if there is no such line. The
    line is found by parsing the file, not by searching its text, so a BenchVersion in a
    docstring or in a string the suite writes out is not mistaken for it. The file is read
    and written as bytes and only the digits change, line endings included. Each run
    presumes a change, so each report maps to a version of its own; mark and manual are
    only ever changed by hand."""
    with open(path, 'rb') as f:
        raw = f.read()
    try:
        tree = ast.parse(raw)
    except (SyntaxError, ValueError):
        return None
    value = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name.startswith('b_'):
            for stmt in node.body:
                if (isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Constant)
                        and isinstance(stmt.value.value, str)
                        and any(isinstance(t, ast.Name) and t.id == 'BenchVersion'
                                for t in stmt.targets)):
                    value = stmt.value
                    break
    if value is None or value.lineno != value.end_lineno:
        return None
    starts = [0]
    for row in raw.split(b'\n')[:-1]:
        starts.append(starts[-1] + len(row) + 1)
    first = starts[value.lineno - 1] + value.col_offset
    last = starts[value.end_lineno - 1] + value.end_col_offset
    old = value.value
    numbers = [int(n) for n in re.findall(r'\d+', old)[:3]]
    numbers += [0] * (3 - len(numbers))
    new = f'M{numbers[0]}.{numbers[1]}.{numbers[2] + 1}'
    quote = raw[first:first + 1]
    with open(path, 'wb') as f:
        f.write(raw[:first] + quote + new.encode('ascii') + quote + raw[last:])
    return old, new


def core_masks():
    """One affinity mask per PHYSICAL core, each holding the core's logical processors
    (both threads of a hyper-threaded core), from the OS. [] where that cannot be read."""
    if os.name != 'nt':
        return []
    try:
        import ctypes
        import ctypes.wintypes as wt
        k32 = ctypes.WinDLL('kernel32', use_last_error=True)
        size = wt.DWORD(0)
        k32.GetLogicalProcessorInformation(None, ctypes.byref(size))   # sets the size
        buf = ctypes.create_string_buffer(size.value)
        if not k32.GetLogicalProcessorInformation(buf, ctypes.byref(size)):
            return []
        masks = []
        for offset in range(0, size.value, 32):         # one 32-byte record per entry
            mask, relation = struct.unpack_from('<QI', buf, offset)
            if relation == 0:                           # RelationProcessorCore
                masks.append(mask)
        return masks
    except Exception:
        return []


def set_affinity(pid, mask):
    """Pin a process (pid 0: this one) to the logical processors in mask. Returns the mask
    it had, or None if it could not be changed (Windows only)."""
    try:
        import ctypes
        import ctypes.wintypes as wt
        k32 = ctypes.WinDLL('kernel32', use_last_error=True)
        k32.OpenProcess.restype = wt.HANDLE
        k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
        k32.GetProcessAffinityMask.argtypes = [wt.HANDLE, ctypes.POINTER(ctypes.c_size_t),
                                               ctypes.POINTER(ctypes.c_size_t)]
        k32.SetProcessAffinityMask.argtypes = [wt.HANDLE, ctypes.c_size_t]
        handle = k32.OpenProcess(0x0200 | 0x0400, False, pid or os.getpid())
        if not handle:
            return None
        old = ctypes.c_size_t()
        system = ctypes.c_size_t()
        k32.GetProcessAffinityMask(handle, ctypes.byref(old), ctypes.byref(system))
        done = k32.SetProcessAffinityMask(handle, mask)
        k32.CloseHandle(handle)
        return old.value if done else None
    except Exception:
        return None


# ---- the hub --------------------------------------------------------------------------
class Job:
    """One worker process for one phase of one suite."""
    __slots__ = ('suite', 'phase', 'tag', 'proc', 'begin', 'p', 'hub', 'shown', 'snap0',
                 'snap1', 'slot')


class Priv:
    """What a Hub keeps for itself."""
    __slots__ = ('ch', 'cfg', 'tag', 'active', 'best', 'quiet_note', 'meter', 'cores',
                 'own')


class Hub:
    """Starts, watches and ends the workers. One per run."""

    def __init__(me, cfg):
        me.priv = priv = Priv()
        priv.cfg = cfg
        priv.ch = Channel(f'rb2_{os.getpid()}_{int(time.time()) % 100000}')
        priv.tag = 0
        priv.active = []
        priv.best = min(step_time() for _ in range(5))
        priv.quiet_note = False
        priv.meter = Meter()
        priv.cores = core_masks()
        priv.own = None                 # this process's affinity, to put back at the end

    # ---- phases ------------------------------------------------------------------------
    def phase(me, kind, suites, limit):
        """Run `kind` ('test' or 'bench') for each suite, `limit` workers at once. A bench
        is started after the machine has recovered. With `limit` over 1 for benchmarks and
        no more than the physical cores less one, each worker gets a core of its own (both
        its threads) and the hub keeps the last core. With more than that nobody is
        pinned: the workers share the machine, and each call's calibration says how much
        of it they got."""
        priv = me.priv
        cfg = priv.cfg
        if kind == 'test':
            suites = sorted(suites, key=lambda s: -s['prev'])
        pinned = kind == 'bench' and 1 < limit < len(priv.cores)
        if pinned:
            priv.own = set_affinity(0, priv.cores[-1])
        pending = collections.deque(suites)
        while pending or priv.active:
            while pending and len(priv.active) < limit:
                if kind == 'bench' and not priv.active:
                    me.quiet()                  # only when alone: others make it noisy
                job = me.launch(pending.popleft(), kind)
                job.slot = None
                if pinned:
                    taken = {other.slot for other in priv.active}
                    job.slot = next(i for i in range(limit) if i not in taken)
                    set_affinity(job.proc.pid, priv.cores[job.slot])
                priv.active.append(job)
            for job in list(me.priv.active):
                verdict = me.poll(job)
                if verdict:
                    me.priv.active.remove(job)
                    if verdict == 'again':
                        pending.appendleft(job.suite)
            time.sleep(cfg['pause'])

    def quiet(me):
        """Wait (QUIET s at most) until a reference probe is back to the best seen. If it
        never is, the machine has a new normal: take it, and say so once."""
        priv = me.priv
        calm = 0
        t0 = time.time()
        probe = priv.best
        while time.time() - t0 < QUIET:
            probe = min(step_time() for _ in range(3))
            priv.best = min(priv.best, probe)
            calm = calm + 1 if probe <= priv.best * BAND else 0
            if calm >= 2:
                return
            time.sleep(0.05)
        if not priv.quiet_note:
            priv.quiet_note = True
            print(f'  note: the machine did not return to its first speed in {QUIET:g} s '
                  f'({100 * priv.best / probe:.0f}% of it); timing on from here')
        priv.best = probe

    # ---- one worker --------------------------------------------------------------------
    def launch(me, suite, kind):
        priv = me.priv
        cfg = priv.cfg
        priv.tag += 1
        job = Job()
        job.suite = suite
        job.phase = kind
        job.tag = priv.tag
        job.p = {}
        job.shown = 0
        job.snap0 = None
        job.snap1 = None
        budget = cfg['budget'] - (suite['test_wall'] + START if kind == 'bench' else 0.0)
        job.hub = {'timeout': cfg['timeout'], 'pause': cfg['worker_pause'],
                   'budget': max(2.0, budget), 'skip': list(suite['skip']),
                   'live': cfg['live'], 'orphan': cfg['orphan'],
                   'tlong': cfg['tlong'], 'tmax': cfg['tmax'],
                   'test_time': cfg['test_time'],
                   'prior': {'records': suite['records'], 'secs': suite['test_secs']},
                   'beat': time.time(), 'hub': os.getpid()}
        priv.ch[f'hub.config.{job.tag}'] = job.hub
        priv.ch[f'hub.message.{job.tag}'] = {'seq': 0, 'cmd': ''}
        args = [cfg['python'], '-c', SPOKE, HERE, suite['path'], kind, priv.ch.name, str(job.tag)]
        out = None if cfg['live'] else subprocess.DEVNULL
        job.begin = time.time()
        job.proc = subprocess.Popen(args, cwd=suite['cwd'], stdin=subprocess.DEVNULL,
                                    stdout=out, stderr=out)
        return job

    def poll(me, job):
        """None while it runs; 'done' or 'again' once it is over."""
        priv = me.priv
        cfg = priv.cfg
        p = me.peek(f'spoke.progress.{job.tag}')
        if p:
            job.p = p
        now = time.time()
        if now - job.hub['beat'] >= BEAT:
            job.hub['beat'] = now
            priv.ch[f'hub.config.{job.tag}'] = job.hub
        live = job.p.get('live')        # the worker is inside its timed run: read the PC
        if live and job.snap0 is None:
            job.snap0 = priv.meter.snap()
        elif not live and job.snap0 is not None and job.snap1 is None:
            job.snap1 = priv.meter.snap()
        if job.proc.poll() is not None:
            return me.finish(job)
        started = job.p.get('tstart')
        limit = job.p.get('limit')
        if started and limit and now - started > limit:
            return me.overran(job, f'{job.p.get("step")}: no end after {limit:g} s')
        if not job.p and now - job.begin > cfg['timeout'] * STARTUP:
            return me.overran(job, 'the worker never reported')
        return None

    def peek(me, key):
        """A worker's key, or None if it is not there or would not hold still. A worker
        that was killed in the middle of writing one leaves it torn for good: the hub goes
        on with what it last had."""
        try:
            return me.priv.ch.get(key)
        except Torn:
            return None

    def output(me, job):
        """The lines the worker printed that survive on the channel, as text."""
        got = me.peek(f'spoke.output.{job.tag}') or {}
        lines = [f'{text}' for stream, text in got.get('lines', [])]
        if got.get('dropped'):
            lines.insert(0, f'... {got["dropped"]} earlier lines dropped')
        return lines

    def reap(me, job):
        """Delete the spoke's keys."""
        for kind in ('spoke.progress', 'spoke.output', 'spoke.htm', 'spoke.data', 'hub.config',
                     'hub.message'):
            try:
                del me.priv.ch[f'{kind}.{job.tag}']
            except Exception:           # a key torn by a kill, or already gone: let it be
                pass

    def finish(me, job):
        """The spoke has exited: take its page and data, or find out why it left none."""
        suite = job.suite
        final = me.peek(f'spoke.progress.{job.tag}') or job.p
        data = me.peek(f'spoke.data.{job.tag}')
        htm = me.peek(f'spoke.htm.{job.tag}')
        lines = me.output(job)
        code = job.proc.returncode
        wall = time.time() - job.begin
        me.reap(job)
        suite['wall_' + job.phase] += wall
        if job.phase == 'test':
            suite['test_wall'] += wall
        if data is None or htm is None:
            step = final.get('step')
            why = f'the spoke died (exit code {code & 0xFFFFFFFF:#x})'
            if job.phase == 'test':
                recs = final.get('recs', [])
                suite['records'] += recs
                suite['skip'] += [r[0] for r in recs]
                if step and final.get('phase') == 'tests':
                    began = final.get('tstart') or job.begin
                    text = why + ' in this test\n' + '\n'.join(lines[-20:])
                    suite['records'].append([step, 'FAIL', round(time.time() - began, 3),
                                             text])
                    suite['skip'].append(step)
            suite['crash'] = (f'{why} {"in " + step if step else "before reporting"}\n'
                              + '\n'.join(lines[-30:]))
            suite['htm'] = None
            return 'done'
        info = data['info']
        suite['version'] = info.get('version') or suite['version']
        suite['header'] = info.get('header') or suite['header']
        if info.get('crash'):
            suite['crash'] = info['crash']
        if 'tests' in data:
            suite['records'] += [[name, t['status'], t['secs'], t['text']]
                                 for name, t in data['tests'].items()]
            suite['test_secs'] += data['testsecs']
        if 'benchinfo' in data:
            bench = dict(data['benchinfo'])
            bench['rows'] = [dict(row, label=label) for label, row in data['bench'].items()]
            suite['bench'] = bench
            suite['bench_wall'] = wall
            if bench['rows'] and job.snap0 is not None:
                if job.snap1 is None:
                    job.snap1 = me.priv.meter.snap()
                bench['machine'] = me.priv.meter.figures(
                    job.snap0, job.snap1, bench['perinner'], bench['cpu'],
                    bench['live_wall'])
        suite['htm'] = htm
        return 'done'

    def overran(me, job, why):
        """A test or bench call ran past its timeout: kill the worker and its children.
        A test: it fails, and the rest of the suite runs on in a new worker."""
        suite = job.suite
        suite['htm'] = None
        step = job.p.get('step') or 'start'
        lines = me.output(job)
        kill_tree(job.proc)
        me.reap(job)
        wall = time.time() - job.begin
        suite['wall_' + job.phase] += wall
        recs = job.p.get('recs', [])
        if job.phase == 'test':
            suite['test_wall'] += wall
            suite['records'] += recs
            suite['skip'] += [r[0] for r in recs]
            if step not in ('import', 'start'):
                limit = job.p.get('limit') or me.priv.cfg['timeout']
                suite['records'].append([step, 'slow', limit,
                                         f'time too high: killed after {limit:g} s\n'
                                         + '\n'.join(lines[-20:])])
                suite['skip'].append(step)
                suite['tries'] += 1
                if suite['tries'] <= RETRIES:
                    return 'again'
                suite['crash'] = f'gave up after {RETRIES} workers were killed'
                return 'done'
        if job.phase == 'bench':
            suite['bench'] = {'skipped': f'killed: {why}', 'killed': True}
        else:
            suite['crash'] = f'TIMEOUT: {why}\n' + '\n'.join(lines[-20:])
        return 'done'

    # ---- the end -----------------------------------------------------------------------
    def stop_all(me):
        """Ask every live worker to stop, give them `grace`, then kill what is left."""
        priv = me.priv
        for job in priv.active:
            try:
                priv.ch[f'hub.message.{job.tag}'] = {'seq': 1, 'cmd': 'terminate'}
            except ChannelError:
                pass
        t0 = time.time()
        while priv.active and time.time() - t0 < priv.cfg['grace']:
            if all(job.proc.poll() is not None for job in priv.active):
                break
            time.sleep(priv.cfg['pause'])
        for job in priv.active:
            kill_tree(job.proc)

    def close(me):
        if me.priv.own:
            set_affinity(0, me.priv.own)        # the hub was pinned for a parallel bench
        me.priv.ch.terminate()
        me.priv.ch.close()


def can_bench(suite):
    """Time a suite only if it loaded and no test failed: a failure is investigated first,
    and timing code that fails its tests proves nothing."""
    if suite['crash']:
        return False
    return not any(r[1] == 'FAIL' for r in suite['records'])


HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(PRIMARY, 'html', 'runbench.html')
CSS = os.path.join(PRIMARY, 'html', 'runbench.css')
JS = os.path.join(PRIMARY, 'html', 'runbench.js')
LETTERS = [chr(97 + i) for i in range(26)] + [a + b for a in map(chr, range(97, 123))
                                              for b in map(chr, range(97, 123))]


def isbroken(suite):
    """True if the suite failed: a test, a load, a killed or raising bench."""
    bench = suite['bench'] or {}
    return bool(any(r[1] == 'FAIL' for r in suite['records']) or suite['crash']
                or bench.get('killed') or bench.get('errors'))


def literal(value):
    """A value as a JavaScript literal for the page (a closing tag cannot end the script)."""
    return json.dumps(value).replace('</', '<\\/')


def can_bench(suite):
    """Time a suite only if it loaded and no test failed: a failure is investigated first,
    and timing code that fails its tests proves nothing."""
    if suite['crash']:
        return False
    return not any(r[1] == 'FAIL' for r in suite['records'])


def report_name(paths, name):
    """The report's stem: name if given, else benchx<suites>-<first shared folder>."""
    if name:
        if not re.fullmatch(r'[A-Za-z0-9._-]+', name):
            print('runbench: -name is letters, digits and . _ - (no path)')
            raise SystemExit(2)
        return name
    folders = [os.path.dirname(p) for p in paths]
    try:
        common = os.path.commonpath(folders)
    except ValueError:                              # another drive
        common = ''
    if os.path.splitdrive(common)[1].strip('\\/') == '':
        print('runbench: the suites share no folder before the drive: ' + ', '.join(paths[:3]))
        raise SystemExit(2)
    last = os.path.basename(common)
    if last.lower() in ('test', 'tests'):
        last = os.path.basename(os.path.dirname(common))
    return f'benchx{len(paths)}-{last}'


def results_folder(results):
    """The folder of the reports: beside this folder, made when it is missing."""
    folder = results or os.path.join(os.path.dirname(HERE), 'results')
    os.makedirs(folder, exist_ok=True)
    return folder


def machine_htm(machine):
    """The machine meter's figures as a flex of items (HTML), or nothing."""
    if not machine:
        return b''
    items = [f'power {machine.get("power") or "?"}']
    if machine.get('mhz'):
        items.append(f'clock {machine["mhz"] / 1000:.1f} GHz')
    if machine.get('speed') is not None:
        items.append(f'speed {machine["speed"]:.0f}%' + (' THROTTLED' if machine['speed'] < 80
                                                          else ''))
    for key, label in (('pc_cpu', 'PC CPU'), ('mem', 'Mem'), ('disk', 'Disk')):
        if machine.get(key) is not None:
            items.append(f'{label} {machine[key]:.0f}%')
    if machine.get('py_share') is not None:
        items.append(f'Python {machine["py_share"]:.0f}% of its core')
    md = mdwriteln(None, '_\\flex:machine/_')
    mdwriteln(md, '|', items)
    mdwriteln(md, '_\\|/_')
    return bytes(md2htm(md)).split(b'-->\n', 1)[1]


def fallback_md(suite):
    """A suite whose spoke left no page: a note and what the hub has."""
    md = mdwriteln(None, '**' + str(suite['version']) + '**', suite['header'])
    if suite['crash']:
        mdwriteln(md, '### Did not finish\n\n```\n' + suite['crash'] + '\n```')
    records = suite['records']
    if records:
        mdwriteln(md, '| test | result | seconds |\n|:--|:--|--:|')
        mdwriteln(md, '|', [('{.bad}' if r[1] == 'FAIL' else '{.slow}' if r[1] == 'slow' else '')
                            + r[0].replace('|', '\\|') for r in records],
                  '|', [r[1] for r in records], '|', [r[2] for r in records], '|')
    return md


def summary_md(rows, stamp, wall, machine, broken):
    """The Summary tab's Markdown: figures, machine, a table of the suites, notes."""
    suites = [s for s, total, notes in rows]
    records = [r for s in suites for r in s['records']]
    md = mdwriteln(None, '_\\tab:Summary' + (' {bad}' if broken else '') + '/_')
    mdwriteln(md, '_\\flex:figures {cards}/_')
    mdwriteln(md, '|', [f'**{len(suites)}** suites', f'**{len(records)}** tests',
                        f'**{len(broken)}** failed',
                        f'**{sum(r[1] == "slow" for r in records)}** slow tests',
                        f'**{sum(r[1] == "skip" for r in records)}** skipped',
                        f'**{seconds(wall)}** wall'])
    mdwriteln(md, '_\\|/_\n\n## Machine\n')
    mdwriteln(md, '_\\flex:run/_')
    mdwriteln(md, '|', [f'python {sys.version.split()[0]}', f'run {stamp}', f'wall {seconds(wall)}'])
    mdwriteln(md, '_\\|/_\n\n## Suites\n')
    marks = []
    for suite, total, notes in rows:
        flags = [x['flag'] for x in (suite['bench'] or {}).get('rows', []) if x['flag']]
        marks.append('{.bad}' if isbroken(suite) else '{.slow}' if flags or any(
            r[1] == 'slow' for r in suite['records']) else '')
    mdwriteln(md, '| suite | version | tests | fail | slow | skip | test s | bench s | total s '
                  '| bench slow | notes |')
    mdwriteln(md, '|:--|:--|--:|--:|--:|--:|--:|--:|--:|--:|:--|')
    mdwriteln(md, '|', [m + f'[{s["name"]}](#tab_{s["name"]})' for m, (s, t, n) in zip(marks, rows)],
              '|', [s['version'] for s, t, n in rows],
              '|', [len(s['records']) for s, t, n in rows],
              '|', [sum(r[1] == 'FAIL' for r in s['records']) for s, t, n in rows],
              '|', [sum(r[1] == 'slow' for r in s['records']) for s, t, n in rows],
              '|', [sum(r[1] == 'skip' for r in s['records']) for s, t, n in rows],
              '|', [s['test_wall'] for s, t, n in rows], '|', [s['wall_bench'] for s, t, n in rows],
              '|', [t for s, t, n in rows],
              '|', [sum(x['flag'] not in ('', 'noisy')
                        for x in (s['bench'] or {}).get('rows', [])) for s, t, n in rows],
              '|', ['; '.join(n).replace('|', '\\|') for s, t, n in rows], '|')
    mdwriteln(md, '\n### Reading this report\n')
    mdwriteln(md, '- **fail**: a test failed, the suite would not load, or a bench raised or was '
                  'killed. A failed suite is not timed: it has to be investigated first.')
    mdwriteln(md, '- **slow**: a test went over its time limit and was stopped or noted; the run '
                  'went on. **bench slow**: a benchmark was cut short, or a call was long.')
    mdwriteln(md, '- **r** is the cost in reference steps, so a faster or slower machine cancels '
                  'out; **se %** is the standard error of the mean over the timed blocks.')
    mdwriteln(md, '- A column with more than one value has a star (sort: ascending, descending, '
                  'then the original order) and a hamburger (filter; right click for the guide).')
    mdwriteln(md, '- **Find** in the footer searches every tab; the list beside it holds the '
                  'earlier runs, each in its own colour.')
    return md


def write_report(rows, results, stem, stamp, wall, machine, server):
    """The page of the run, written to a new file in results. Returns its path."""
    suites = [s for s, total, notes in rows]
    broken = [s['name'] for s in suites if isbroken(s)]
    htm = md2htm(summary_md(rows, stamp, wall, machine, broken))
    for suite in suites:
        unit = suite['htm']
        if unit is None:                                    # the spoke left none
            page = bytes(md2htm(fallback_md(suite))).split(b'-->\n', 1)[1]
        else:
            page = unit.encode('utf-8').replace(
                b'{{machine}}', machine_htm((suite['bench'] or {}).get('machine')))
        name = suite['name'].replace('&', '&amp;').replace('"', '&quot;')
        htmwriteln(htm, f'<div class="mk mk-tab{" bad" if isbroken(suite) else ""}" '
                        f'data-name="{name}">')
        htmappend(htm, page)
        htmwriteln(htm, '</div>')
    bat, port = '', 0
    if server:
        try:
            bat, port = rsrv.prepare(results, server[1]), server[0]
        except OSError as error:
            print(f'report server: could not prepare {results} ({error})')
    now = time.time()
    local = time.localtime(now)
    base = f'{stem}_{time.strftime("%Y.%m.%d_%H;%M", local)}'
    names = [base, base + time.strftime('.%S', local)]
    names += [names[1] + letters for letters in LETTERS]
    for name in names:
        filename = name + '.html'
        mine = re.compile(re.escape(stem) + r'_(\d{4}\.\d\d\.\d\d_\d\d;\d\d[\d.]*[a-z]{0,2})\.html$')
        earlier = [{'file': f, 'when': m.group(1)} for f in os.listdir(results)
                   for m in [mine.match(f)] if m and f != filename]
        earlier.sort(key=lambda x: x['when'], reverse=True)
        token = base64.urlsafe_b64encode(f'{filename}|{int(now)}'.encode()).decode().rstrip('=')
        page = htmtemplate(TEMPLATE, htm, TITLE=f'runbench {stamp}', STEM=literal(stem),
                           RUNS=literal(earlier), NAME=literal(filename), TOKEN=literal(token),
                           PORT=port, BAT=literal(bat), css=CSS, js=JS,
                           rolecss=codelex.css())
        try:
            return htmsave(page, os.path.join(results, filename))
        except FileExistsError:
            continue
    raise FileExistsError(f'runbench: no free name for {stem}')


def finish_run(suites, results, stem, budget, wall, server):
    """The history of each suite, the report, the server, and the number that failed."""
    stamp = time.strftime('%Y-%m-%d %H:%M:%S')
    failed = 0
    rows = []
    machine = None
    for suite in suites:
        bench = suite['bench'] or {}
        broken = isbroken(suite)
        failed += broken
        total = suite['wall_test'] + suite['wall_bench']
        notes = []
        if suite['crash']:
            notes.append('DID NOT RUN' if not suite['records'] else 'CRASH')
        bad = sum(r[1] == 'FAIL' for r in suite['records'])
        if bad:
            notes.append(f'{bad} FAILED')
        if bench.get('killed'):
            notes.append('BENCH KILLED')
        if bench.get('errors'):
            notes.append(f'{len(bench["errors"])} BENCH FAILED')
        slow = sum(r[1] == 'slow' for r in suite['records'])
        if slow:
            notes.append(f'{slow} slow')
        skipped = sum(r[1] == 'skip' for r in suite['records'])
        if skipped:
            notes.append(f'{skipped} skipped')
        flags = [row['flag'] for row in bench.get('rows', []) if row['flag']]
        cut = sum(flag != 'noisy' for flag in flags)
        if cut:
            notes.append(f'{cut} bench slow')
        if len(flags) > cut:
            notes.append(f'{len(flags) - cut} noisy')
        if total > budget * 1.15:
            worst = sorted(suite['records'], key=lambda r: -r[2])[:2]
            notes.append('over budget: tests ' + seconds(suite['test_wall']) + ' ['
                         + ', '.join(f'{r[0]} {r[2]:.1f}s' for r in worst) + ']')
        rows.append((suite, total, notes))
        if bench.get('machine'):
            machine = bench['machine']
        line = {k: v for k, v in suite.items() if k not in ('output', 'skip', 'prev', 'htm')}
        line['when'] = stamp
        with open(os.path.join(results, suite['name'] + '.jsonl'), 'a', encoding='utf-8') as f:
            f.write(json.dumps(line) + '\n')
    path = write_report(rows, results, stem, stamp, wall, machine, server)
    if server:
        try:
            rsrv.start(*server)
        except Exception as error:                  # the server is a convenience: never fail
            print(f'report server: could not start ({error!r})')
    with open(os.path.join(results, 'last_run.json'), 'w', encoding='utf-8') as f:
        json.dump({'when': stamp, 'wall': wall, 'failed': failed, 'report': path,
                   'suites': [{'name': s['name'], 'tests': len(s['records']),
                               'wall_test': s['wall_test'], 'wall_bench': s['wall_bench'],
                               'notes': n} for s, t, n in rows]}, f, indent=1)
    print(f'{len(suites)} suites, {sum(len(s["records"]) for s in suites)} tests, '
          f'{failed} failed, {seconds(wall)}')
    print('report: ' + path)
    return failed


def runbench(targets=(), name='', nohub=False, test_time=1.0, timeout=10.0, budget=10.0,
              tlong=1.0, tmax=42.0, grace=3.0, jobs=0, bench_jobs=1, pause=0.010,
              worker_pause=None, orphan=5.0, tick=True, collect=None, server=True,
              results=None, tests=True, benches=True):
    """Run the suites named by `targets`. Returns the number that failed (see the module
    header); a target that names nothing exits with 2."""
    paths, missing = find_suites(list(targets), os.getcwd())
    if missing or not paths:
        print('runbench: nothing named: ' + (', '.join(missing) or '(no suites found)'))
        raise SystemExit(2)
    stem = report_name(paths, name)
    folder = results_folder(results)
    inplace = nohub or len(paths) == 1
    cfg = {'timeout': float(timeout), 'budget': float(budget), 'tlong': float(tlong),
           'tmax': float(tmax), 'test_time': float(test_time), 'grace': float(grace),
           'pause': float(pause),
           'worker_pause': float(pause if worker_pause is None else worker_pause),
           'orphan': float(orphan), 'live': inplace, 'python': sys.executable,
           }
    workers = max(1, jobs or os.cpu_count() or 1)
    suites = []
    for path in paths:
        name_of = os.path.splitext(os.path.basename(path))[0]
        suites.append({'path': path, 'name': name_of, 'cwd': os.path.dirname(os.path.dirname(path)),
                       'skip': [], 'tries': 0, 'records': [], 'test_secs': 0.0,
                       'test_wall': 0.0, 'wall_test': 0.0, 'wall_bench': 0.0,
                       'bench': None, 'crash': None, 'htm': None, 'version': '', 'header': '',
                       'prev': last_wall(folder, name_of)})
    if tick:
        for suite in suites:
            suite['ticked'] = tick_file(suite['path'])
    hub = Hub(cfg)
    began = time.time()
    try:
        if inplace:
            for suite in suites:
                if tests:
                    hub.phase('test', [suite], 1)
                if not benches:
                    suite['bench'] = {'skipped': NOT_ASKED}
                elif can_bench(suite):
                    hub.phase('bench', [suite], 1)
                else:
                    suite['bench'] = {'skipped': NOT_TIMED}
        else:
            if tests:
                hub.phase('test', suites, workers)
            todo = [s for s in suites if benches and can_bench(s)]
            for suite in suites:
                if suite not in todo:
                    suite['bench'] = {'skipped': NOT_TIMED if benches else NOT_ASKED}
            hub.phase('bench', todo, max(1, int(bench_jobs)))
    except KeyboardInterrupt:
        print('\nrunbench: interrupted, stopping the spokes')
    finally:
        hub.stop_all()
        hub.close()
    if collect is not None:
        collect.extend(suites)
    srv = (rsrv.PORT,) + rsrv.files() if server is True else (tuple(server) if server else None)
    return finish_run(suites, folder, stem, budget, time.time() - began, srv)


def last_wall(folder, name):
    """Seconds the tests of this suite took last time, from its .jsonl; 0 if never run.
    The slowest suites are started first, so the parallel phase has no long tail."""
    try:
        with open(os.path.join(folder, name + '.jsonl'), encoding='utf-8') as f:
            return json.loads(f.readlines()[-1]).get('wall_test', 0.0)
    except (OSError, ValueError, IndexError):
        return 0.0


def words(argv):
    """The console words as (targets, the arguments of runbench()). A word it does not know,
    or a -timeout that is not a number above 0, prints the Use lines and exits with 2."""
    args = {}
    targets = []
    only = set()                                    # -test, -bench: one part; both is the whole
    for word in argv:
        if word == '-nohub':
            args['nohub'] = True
        elif word in ('-test', '-bench'):
            only.add(word)
        elif word.startswith('-name='):
            args['name'] = word[6:]
        elif word.startswith('-timeout='):
            try:
                args['timeout'] = float(word[9:])
            except ValueError:
                args['timeout'] = 0.0
            if args['timeout'] <= 0:
                print('runbench: -timeout is a number of seconds above 0')
                raise SystemExit(2)
        elif word.startswith('-'):
            print(__doc__.split('Python:')[0])
            raise SystemExit(2)
        else:
            targets.append(word)
    if only == {'-test'}:
        args['benches'] = False
    elif only == {'-bench'}:
        args['tests'] = False
    return targets, args


def main(argv):
    """Turn the console words into the arguments of runbench() and run."""
    targets, args = words(argv)
    raise SystemExit(1 if runbench(targets, **args) else 0)


if __name__ == '__main__':
    main(sys.argv[1:])
