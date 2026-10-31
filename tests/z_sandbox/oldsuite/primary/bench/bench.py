# noinspection InconsistentLineSeparators
"""
bench.py — Base class for timed benchmarks with reference normalisation.
Python port of MATLAB bench.m v2.0.
VERSION: 2.0

------------------------------------------------------------------------
Architecture: tests first, benchmarks last (mirrors the MATLAB design)
------------------------------------------------------------------------
  1. test_* methods in the subclass are ordinary unittest correctness
     tests. They run first. A built-in benchContract test guarantees a
     non-empty suite even for a bench-only subclass.
  2. Benchmarks run in tearDownClass — which unittest guarantees to run
     AFTER every test — and are SKIPPED when any test failed: timing code
     that just failed its contract is meaningless.
  3. The console report always prints. HTML is written by runbench, which
     reads BenchResults back after the run:
         tc = b_foo; res = run(tc); S = tc.BenchResults

How state survives:
  MATLAB shared a containers.Map across the framework's per-test instance
  copies. Python's unittest reuses the *class* across tests, so the failure
  gate and the results live as CLASS attributes (_failed, _bench_results).
  The instance run() override flips _failed sticky-True on any failure or
  error; tearDownClass reads it.

------------------------------------------------------------------------
Subclass contract
------------------------------------------------------------------------
  1. Declare the class attributes:
       BenchName    - short id,        e.g. 'kvdot'
       BenchVersion - version string,  e.g. '2.01'
       BenchHeader  - one-line summary of what changed in this version
       Nx           - iterations per single measurement
       NRep         - number of live repetitions
  2. Bench methods — time EXACTLY Nx operations (one operation = one
     conversion / one element-op / one call) and return that elapsed time. The
     framework calls the method NRep times, so total work is a constant
     N = Nx * NRep, of which each method call is one sample. CV and outlier
     removal are computed across the NRep samples (in bench.py, NOT in the
     method). The reported figure is mean/Nx — i.e. PER operation.

     If one natural call processes M items (e.g. an M-element array), loop
     Nx // M passes so the total is still Nx operations and mean/Nx stays
     per-item — comparable to a per-item baseline:
       def bench_foo(self, Nx):
           name = 'label'; group = 'section'   # both optional
           n = max(1, Nx // M)                  # M operations per pass
           t0 = time.perf_counter()
           for _ in range(n): <pass over M items>
           return time.perf_counter() - t0, name, group
  3. Correctness tests go in ordinary test_* methods.
  4. Override setup_fixtures (a classmethod) to build shared state once.

------------------------------------------------------------------------
Usage
------------------------------------------------------------------------
    python -m unittest tests.b_str2int        # tests + console bench report
    python primary/runbench.py b_str2int "msg"  # the same + HTML results tab
"""

from __future__ import annotations

import math
import time
import unittest

# ════════════════════════════════════════════════════════════════
#   TUNABLES — every magic number in this file lives here
# ════════════════════════════════════════════════════════════════

REF_STEPS  = 50_000   # steps in one reference sample. Sized so a sample costs
                      # ~6 ms warm: long enough to swamp timer resolution, short
                      # enough that NRep samples stay cheap. Its exact value is
                      # arbitrary -- r divides by the cost of ONE step, so the
                      # count cancels. It is NOT calibrated (see ref_loop).

REF_CV_TOL = 15.0     # %. Variation of the reference ACROSS the live reps, and
                      # the only thing that still invalidates a run: it means the
                      # machine moved WHILE measuring, so every row was timed
                      # against a shifting baseline.


class bench(unittest.TestCase):
    # -- subclass must supply these (class attributes) --------------------
    BenchName    = ""      # short name,    e.g. 'kvdot'
    BenchVersion = "1.0"   # version,       e.g. '2.01'
    BenchHeader  = ""      # one-line summary of changes for this version
    Nx           = 1000    # iterations per single measurement
    NRep         = 7       # number of live repetitions

    # -- shared across all per-test runs (the failure gate + results) -----
    _failed         = False
    _bench_results  = None

    # ------------------------------------------------------------------ #
    # Fixtures
    # ------------------------------------------------------------------ #
    @classmethod
    def setUpClass(cls):
        # Clear stale gate/results from a previous run on the same class.
        cls._failed = False
        cls._bench_results = None
        cls.setup_fixtures()

    @classmethod
    def setup_fixtures(cls):
        # subclass hook — override to build shared state once (as class attrs)
        pass

    @property
    def BenchResults(self):
        return type(self)._bench_results

    # ------------------------------------------------------------------ #
    # Failure gate
    #   unittest reuses the class across tests but a fresh instance per
    #   test, so we cannot store the gate on self. run() inspects the
    #   shared TestResult after the test and flips the class flag.
    # ------------------------------------------------------------------ #
    def run(self, result=None):
        result = super().run(result)
        if result is not None and (result.failures or result.errors):
            type(self)._failed = True
        return result

    # ------------------------------------------------------------------ #
    # Built-in contract test — also guarantees a non-empty suite so the
    # teardown runs even for subclasses with no tests of their own.
    # ------------------------------------------------------------------ #
    def test_benchContract(self):
        # The base class is itself a TestCase and gets collected wherever it
        # is imported (`from bench import bench`). It has no benchmarks of its
        # own — skip rather than fail.
        if type(self) is bench:
            self.skipTest("bench base class — not a concrete benchmark")
        bm = discover_bench_methods(type(self))
        self.assertTrue(
            bm,
            "no bench methods found — declare them as bench_* methods",
        )

    # ------------------------------------------------------------------ #
    # Benchmark driver — tearDownClass runs after ALL tests
    # ------------------------------------------------------------------ #
    @classmethod
    def tearDownClass(cls):
        # Four phases, in order:  DISCOVER -> RUN -> REDUCE -> PRINT.
        # Each phase is one line here; the work lives in the file-scope helpers
        # below, which take plain data in and hand plain data back.
        if cls is bench:
            return                    # the abstract base owns no benchmarks

        S = {
            "name":    cls.BenchName,
            "version": cls.BenchVersion,
            "header":  cls.BenchHeader,
            "ts":      time.strftime("%Y-%m-%d %H:%M:%S"),
            "Nx":      cls.Nx,
            "NRep":    cls.NRep,
            "skipped": True,
        }
        cls._bench_results = S         # set once; every exit path below returns it

        if cls._failed:
            print("\n bench: benchmarks SKIPPED — one or more tests failed.\n")
            return

        names = discover_bench_methods(cls)                     # 1. DISCOVER
        if not names:
            return                     # the contract test already reported this

        try:
            # Fixture holder WITHOUT running TestCase.__init__: fixtures live as
            # class attributes, so ordinary lookup resolves on a bare instance.
            holder = cls.__new__(cls)
            labels, groups = warm_up(cls, holder, names)
            tRef, times    = measure(cls, holder, names)        # 2. RUN
            build_results(S, labels, groups, tRef, times,       # 3. REDUCE
                          cls.Nx, cls.NRep)
            report(S)                                           # 4. PRINT
        except Exception as ME:        # noqa: BLE001 — report, never crash the suite
            print(f"\n bench: benchmark run FAILED — {ME}\n")
            S["skipped"] = True        # build_results may have cleared it mid-way
            S["error"]   = str(ME)

# ════════════════════════════════════════════════════════════════
# Module-level helpers — pure data in / data out, no class dispatch
# ════════════════════════════════════════════════════════════════

def warm_up(cls, holder, names):
    """Run every bench once and harvest the label + group each one reports.

    Two jobs in one pass. The timings are DISCARDED: a first call measures
    imports, allocation and cold caches, not the operation. And a bench may
    return (t, label, group), so this is also where the report's row names come
    from -- falling back to the method name with 'bench_' stripped.
    Returns (labels, groups), both parallel to `names`.
    """
    labels = [""] * len(names)
    groups = [""] * len(names)
    for i, m in enumerate(names):
        out = getattr(cls, m)(holder, cls.Nx)
        if isinstance(out, tuple):
            if len(out) >= 3 and out[2]:
                groups[i] = out[2]
            if len(out) >= 2 and out[1]:
                labels[i] = out[1]
        if not labels[i]:
            labels[i] = m.replace("bench_", "")
    return labels, groups


def measure(cls, holder, names):
    """The live measurement: NRep sweeps of every bench.

    Each sweep is preceded by one reference sample, so machine speed is tracked
    ALONGSIDE the benchmarks rather than assumed constant -- that is what lets
    r stay comparable when the clock moves. No calibration is involved: ref_loop
    is flat, so one step is a fixed unit of work on any machine.
    Returns (tRef per rep, times[method][rep]).
    """
    tRef  = [0.0] * cls.NRep
    times = [[0.0] * cls.NRep for _ in names]
    for rep in range(cls.NRep):
        tRef[rep] = ref_loop()
        for i, m in enumerate(names):
            out = getattr(cls, m)(holder, cls.Nx)
            times[i][rep] = out[0] if isinstance(out, tuple) else out
    return tRef, times


def ref_loop(n=REF_STEPS):
    # Reference loop — djb2-like multiply-add (pure int, no memory).
    # h = (h*33 + j) % 2**32: same compute pattern as a hash inner loop.
    # One step is the UNIT r is quoted in, so its cost must be a constant.
    #
    # DELIBERATELY FLAT. This used to be nested:
    #     for _ in range(Nx):
    #         for j in range(Ninner):
    # which paid a range() construction and loop setup on every OUTER
    # iteration -- a fixed cost amortised over Ninner steps, making the
    # measured cost per step  a + b/Ninner  instead of a constant:
    #
    #     Ninner    1     2     4     8    16    32    64
    #     ns/step 686   554   519   450   416   413   418     (1.76x -> 1.06x)
    #
    # And Ninner was calibrated to hold t_ref near 1 us, so a SLOWER machine
    # got a SMALLER Ninner and therefore a MORE inflated unit. The reference
    # then appeared to slow more than the machine actually had, and dragged r
    # down ~30% on battery -- an artefact of the harness's own loop shape,
    # mistaken for a property of machines. Flat, the same sweep is 14% noise
    # with no trend, and no calibration is needed at all.
    h = 5381
    M = 2 ** 32
    t0 = time.perf_counter()
    for j in range(n):
        h = (h * 33 + j) % M
    t = time.perf_counter() - t0
    if h < 0:            # keep h live (defensive; CPython won't elide, but explicit)
        t += 0
    return t


def rm_outliers(t):
    # Timing distributions are NOT normal: the floor is the true operation
    # time; anything above it is true time + interruption delay. Estimate
    # mean+sigma from the bottom half (<= median), then discard anything
    # more than 3 sigma above that mean. Ignores the contaminated right tail.
    med = median(t)
    bot = [x for x in t if x <= med]
    mu  = sum(bot) / len(bot)
    sig = math.sqrt(sum((x - mu) ** 2 for x in bot) / len(bot)) if len(bot) > 1 else 0.0
    fence = mu + 3 * sig
    clean = [x for x in t if x <= fence]
    return clean, len(t) - len(clean)


def median(v):
    s = sorted(v)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def mean(v):
    return sum(v) / len(v)


def std(v):
    if len(v) < 2:
        return 0.0
    m = mean(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))


def fmt_r(r):
    # Ratio r with an SI suffix when >= 1000.
    if   r >= 1e9: return f"{r/1e9:.3g}G"
    elif r >= 1e6: return f"{r/1e6:.3g}M"
    elif r >= 1e3: return f"{r/1e3:.3g}k"
    return f"{r:.4g}"


def build_results(S, labels, groups, tRef, times, Nx, NRep):
    # Reduce raw rep times to the display-ready results dict. Preformatted
    # strings so the console report and runbench's HTML show identical numbers
    # from one source.
    S["skipped"] = False
    S["refSteps"] = REF_STEPS
    S["labels"]  = labels
    S["groups"]  = groups
    nM = len(labels)

    # perInner: seconds for ONE step of the flat reference loop. A fixed
    # quantum of work whose TIME varies with machine speed -- which is exactly
    # what r must divide by. (The old code divided by t_ref, an OUTER-loop
    # iteration that calibration pinned at ~1 us, so it barely moved when the
    # machine did and r degenerated into "mean us" under another name.)
    tRefClean, nRefOut = rm_outliers(tRef)
    perInner = mean(tRefClean) / REF_STEPS

    # display unit from the median per-iteration method time
    per_iter = sorted(mean(times[i]) / Nx for i in range(nM))
    tMed = median(per_iter)
    if   tMed >= 700e-3: uScale, S["uLabel"] = 1.0,  "s"
    elif tMed >= 700e-6: uScale, S["uLabel"] = 1e3,  "ms"
    else:                uScale, S["uLabel"] = 1e6,  "us"
    # Outlier-CLEANED, so the header agrees with both the reference row in the
    # table (refMeanStr) and the validity check below. This used to be the raw
    # mean, which meant the headline t_ref, the t_ref row, and the drift test
    # could each report a different number for the same quantity.
    S["tRefIter"] = perInner * uScale

    refCV  = std([x / REF_STEPS for x in tRefClean]) / perInner * 100 if perInner else 0.0
    refOut = f"[-{nRefOut}]" if nRefOut else ""
    # The reference ROW must show the unit r is measured in -- one inner step,
    # not a whole pass of REF_STEPS -- otherwise its own r would read
    # REF_STEPS rather than 1, and every other row would look REF_STEPS times
    # too fast against it. The same per-step figure is reported in the header
    # and the HTML meta line, where it doubles as the machine-speed stamp.
    S["refMeanStr"] = f"{perInner * uScale:.4g}"
    S["refCVStr"]   = f"{refCV:.1f}%{refOut}"
    S["perInner"]   = perInner * uScale

    rows = []
    for i in range(nM):
        txClean, nOut = rm_outliers(times[i])
        mTx = mean(txClean) / Nx
        r   = mTx / perInner if perInner else float("inf")
        cv  = std([x / Nx for x in txClean]) / mTx * 100 if mTx else 0.0
        outStr = f"[-{nOut}]" if nOut else ""
        rows.append([
            labels[i],
            fmt_r(r),
            f"{mTx * uScale:.4g}",
            f"{cv:.1f}%{outStr}",
        ])
    S["rows"] = rows

    # -- run validity -----------------------------------------------------
    # r divides by perInner, which is measured from tRef DURING the live reps,
    # so it self-corrects for machine speed. What still invalidates a run is
    # the machine moving WHILE measuring: refCV is the reference's own
    # variation across the reps, and if that is high then every row was timed
    # against a shifting baseline.
    S["refCV"]     = refCV
    S["tRefValid"] = refCV <= REF_CV_TOL
    return S


def cen(s, w):
    pad = max(0, w - len(s))
    lpad = pad // 2
    return " " * lpad + s + " " * (pad - lpad)


def report(S):
    # Console table from the preformatted results dict.
    rows = S["rows"]
    nM   = len(rows)
    W    = (8, 9, 7)                                   # widths: r, mean, cv
    Wm   = max(len(r[0]) for r in rows) + 3

    grp_order = []
    for g in S["groups"]:
        if g not in grp_order:
            grp_order.append(g)
    has_groups = not (len(grp_order) == 1 and grp_order[0] == "")
    Wg = (max([len(g) for g in grp_order] + [len("reference")]) + 2) if has_groups else 0

    if has_groups:
        sepW = 1 + Wg + 1 + Wm + 2 + W[0] + 2 + W[1] + 2 + W[2]
        def line(g, m, a, b, c): return f" {g:<{Wg}} {m:<{Wm}}  {a}  {b}  {c}"
    else:
        sepW = 1 + Wm + 2 + W[0] + 2 + W[1] + 2 + W[2]
        def line(m, a, b, c): return f" {m:<{Wm}}  {a}  {b}  {c}"

    sep = "-" * sepW
    meanHdr = "mean " + S["uLabel"]

    print(f"\n{sep}")
    print(f" {S['name']}  v{S['version']}   {S['ts']}")
    print(f" {S['header']}")
    print(f" Nx={S['Nx']}  NRep={S['NRep']}  refSteps={S['refSteps']}  "
          f"t_ref={S['tRefIter']:.4g} {S['uLabel']}/step")
    if not S.get("tRefValid", True):
        print(f" *** RUN SUSPECT: the reference moved while measuring"
              f" (refCV {S.get('refCV', 0):.1f}%).")
        print(f" *** Every row was timed against a shifting baseline. Re-run on a"
              f" quiet machine, or compare variants WITHIN this run only.")
    print(sep)
    if has_groups:
        print(line("Group", "Method", cen("r", W[0]), cen(meanHdr, W[1]), cen("+/-%", W[2])))
        print(f" {sep}")
        print(line("reference", "t_ref", cen("1", W[0]),
                   cen(S["refMeanStr"], W[1]), cen(S["refCVStr"], W[2])))
    else:
        print(line("Method", cen("r", W[0]), cen(meanHdr, W[1]), cen("+/-%", W[2])))
        print(f" {sep}")
        print(line("t_ref", cen("1", W[0]),
                   cen(S["refMeanStr"], W[1]), cen(S["refCVStr"], W[2])))
    print()

    row_count = 0
    for gi, g in enumerate(grp_order):
        idx = [i for i in range(nM) if S["groups"][i] == g]
        for ii, i in enumerate(idx):
            if has_groups:
                gl = g if ii == 0 else ""
                print(line(gl, rows[i][0], cen(rows[i][1], W[0]),
                           cen(rows[i][2], W[1]), cen(rows[i][3], W[2])))
            else:
                print(line(rows[i][0], cen(rows[i][1], W[0]),
                           cen(rows[i][2], W[1]), cen(rows[i][3], W[2])))
                row_count += 1
                if row_count % 5 == 0 and row_count < nM:
                    print()
        if has_groups and gi < len(grp_order) - 1:
            print()
    print()


def discover_bench_methods(cls):
    """Every bench_* method on cls, in source (definition) order.

    Python records methods in definition order in __dict__; walking the MRO
    base-first means an override keeps its subclass position. File scope rather
    than a classmethod: it needs nothing from the instance and never dispatches.
    """
    seen, out = set(), []
    for klass in reversed(cls.__mro__):
        for nm in klass.__dict__:
            if nm.startswith("bench_") and nm not in seen:
                seen.add(nm)
                out.append(nm)
    return out
