"""
runbench.py — Update bench class identity, run tests + benchmarks, write HTML.
Python port of MATLAB runbench.m v2.0.
VERSION: 2.0

Signature matches MATLAB runbench(className, version, changes):
    runbench('b_str2int', 1, 'plop')          # explicit version, message
    runbench('b_str2int', [], 'plop')         # auto-increment version (None/[] ok)
    runbench('b_str2int', 'hashfix', 'plop')  # text version -> label after number
    runbench('b_str2int')                      # auto-increment, no message

CLI (from the project root), same order — class, version, changes:
    python primary/runbench.py b_str2int 1 "plop"
    python primary/runbench.py b_str2int "" "auto-increment, with message"

The version always increases by at least 0.001 over the value in the test
file (leading number parsed; any text suffix ignored for comparison). A
larger numeric jump (e.g. 2.000) is honoured as given. A non-numeric token
becomes a label appended after the auto-incremented number.

Flow (mirrors runbench.m):
  1. Patch BenchVersion / BenchName / BenchHeader in the test file.
  2. Import the class fresh, run it with unittest — tests run first; the
     benchmark runs in tearDownClass and is skipped if any test failed.
  3. Read the class's BenchResults + the captured per-test outcomes; append a
     tab with BOTH to results/<class>.html (shell from bench_template.html).
"""

from __future__ import annotations

import importlib
import math
import os
import re
import sys
import time
import unittest

HERE      = os.path.dirname(os.path.abspath(__file__))
ROOT      = os.path.dirname(HERE)
TESTS_DIR = os.path.join(ROOT, "tests")
RES_DIR   = os.path.join(ROOT, "results")
TEMPLATE  = os.path.join(HERE, "bench_template.html")

BENCH_TOKENS = {"b", "bench", "bm", "bt", "t", "test"}


# ════════════════════════════════════════════════════════════════
# Per-test outcome capture
# ════════════════════════════════════════════════════════════════
class _CaptureResult(unittest.TextTestResult):
    """Records (name, status, duration, report) for each test, in run order."""
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.records = []
        self._t0 = None

    def startTest(self, test):
        self._t0 = time.perf_counter()
        super().startTest(test)

    def _dur(self):
        return time.perf_counter() - (self._t0 or time.perf_counter())

    def addSuccess(self, test):
        super().addSuccess(test)
        self.records.append([test._testMethodName, "pass", self._dur(), ""])

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.records.append([test._testMethodName, "FAIL", self._dur(),
                             self._exc_info_to_string(err, test)])

    def addError(self, test, err):
        super().addError(test, err)
        self.records.append([test._testMethodName, "FAIL", self._dur(),
                             self._exc_info_to_string(err, test)])

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.records.append([test._testMethodName, "incomplete", self._dur(), reason])


def run(testclass):
    """Run a bench subclass under unittest; return the _CaptureResult."""
    suite  = unittest.TestLoader().loadTestsFromTestCase(testclass)
    runner = unittest.TextTestRunner(resultclass=_CaptureResult, verbosity=0,
                                     stream=open(os.devnull, "w"))
    return runner.run(suite)


# ════════════════════════════════════════════════════════════════
# Version patching
# ════════════════════════════════════════════════════════════════
def _patch_const(txt, name, value):
    value = value.replace("\\", "\\\\")
    pat = r"(" + name + r"\s*=\s*([\"']))(?:(?!\2).)*(\2)"
    return re.sub(pat, lambda m: m.group(1) + value + m.group(3), txt, count=1)


def _resolve_version(txt, version):
    cur = 1.0
    m = re.search(r"BenchVersion\s*=\s*['\"]([^'\"]*)['\"]", txt)
    if m:
        try:
            cur = float(re.match(r"\s*([0-9.]+)", m.group(1)).group(1))
        except (AttributeError, ValueError):
            pass
    label, new_ver = "", float("nan")
    if version is not None:
        try:
            new_ver = float(version)
        except (TypeError, ValueError):
            label = str(version)
    min_next = cur + 0.001
    if math.isnan(new_ver) or new_ver < min_next - 1e-9:
        new_ver = min_next
    ver_str = f"{new_ver:.3f}"
    if label:
        ver_str += " " + label
    return cur, ver_str


# ════════════════════════════════════════════════════════════════
# HTML writer
# ════════════════════════════════════════════════════════════════
def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _extract_region(txt, a, b):
    i, j = txt.find(a), txt.find(b)
    if i != -1 and j != -1 and j > i + len(a):
        return txt[i + len(a):j]
    return ""


def _bench_table_html(S):
    if S.get("skipped", True):
        h = ('<p style="color:#c22222;font-weight:bold">Benchmarks skipped &mdash; '
             'one or more tests failed.</p>\n')
        if "error" in S:
            h += f'<p class="meta">{_esc(S["error"])}</p>\n'
        return h
    has_g = any(g for g in S["groups"])
    h = '<p class="hdr"><b>Benchmarks</b></p>\n<table><thead><tr>'
    if has_g:
        h += "<th>Group</th>"
    h += (f'<th>Method</th><th>r</th><th>mean {S["uLabel"]}</th>'
          f'<th>+/-%</th></tr></thead><tbody>\n')
    if has_g:
        h += (f'<tr class="refrow"><td>reference</td><td>t_ref</td><td>1</td>'
              f'<td>{S["refMeanStr"]}</td><td>{S["refCVStr"]}</td></tr>\n')
    else:
        h += (f'<tr class="refrow"><td>t_ref</td><td>1</td>'
              f'<td>{S["refMeanStr"]}</td><td>{S["refCVStr"]}</td></tr>\n')
    prev_g = None
    for i, row in enumerate(S["rows"]):
        if has_g:
            g = S["groups"][i]
            gl = _esc(g) if g != prev_g else ""
            prev_g = g
            h += (f'<tr><td>{gl}</td><td>{_esc(row[0])}</td><td>{row[1]}</td>'
                  f'<td>{row[2]}</td><td>{row[3]}</td></tr>\n')
        else:
            h += (f'<tr><td>{_esc(row[0])}</td><td>{row[1]}</td>'
                  f'<td>{row[2]}</td><td>{row[3]}</td></tr>\n')
    h += "</tbody></table>\n"
    return h


def _fmt_dur(d):
    # Adaptive unit so sub-millisecond unit tests read as e.g. "31 µs" rather
    # than a wall of "0.000 s". (MATLAB printed seconds; tests are usually <1 ms.)
    if d >= 1.0:    return f"{d:.3f} s"
    if d >= 1e-3:   return f"{d * 1e3:.2f} ms"
    return f"{d * 1e6:.0f} µs"


def _test_table_html(records):
    h = ('<p class="hdr"><b>Tests</b></p>\n<table><thead><tr>'
         '<th>Test</th><th>Result</th><th>Duration</th></tr></thead><tbody>\n')
    colour = {"pass": "#2a7a2a", "FAIL": "#c22222", "incomplete": "#b8860b"}
    for name, status, dur, report in records:
        st = (f'<span style="color:{colour[status]};font-weight:bold">'
              f'{status.lower() if status != "FAIL" else status}</span>')
        h += f"<tr><td>{_esc(name)}</td><td>{st}</td><td>{_fmt_dur(dur)}</td></tr>\n"
        if status == "FAIL" and report:
            h += ('<tr><td colspan="3" style="text-align:left"><details>'
                  f'<summary>diagnostics</summary><pre>{_esc(report)}</pre>'
                  "</details></td></tr>\n")
    h += "</tbody></table>\n"
    return h


def _write_html(S, records, class_name):
    if not os.path.isdir(RES_DIR):
        os.makedirs(RES_DIR)
    fname = os.path.join(RES_DIR, class_name + ".html")

    old_btns, old_panels = "", ""
    if os.path.isfile(fname):
        with open(fname, encoding="utf-8") as f:
            old = f.read()
        if "bench-shell v3" in old:
            old_btns   = _extract_region(old, "<!-- BTNS:BEGIN -->",   "<!-- TAB_BTNS -->")
            old_panels = _extract_region(old, "<!-- PANELS:BEGIN -->", "<!-- TAB_PANELS -->")
        else:
            legacy = fname.replace(".html", "_legacy_" + time.strftime("%Y%m%d_%H%M%S") + ".html")
            os.rename(fname, legacy)
            print(f" runbench: old-format results moved to {legacy}")

    old_btns   = old_btns.replace('class="tbtn active"',   'class="tbtn"')
    old_panels = old_panels.replace('class="tpanel active"', 'class="tpanel"')

    tab_id  = "tab_" + time.strftime("%Y%m%d_%H%M%S")
    tab_lbl = f"{S['name']} v{S['version']}  {S['ts'][11:16]}"

    btn = (f'  <button class="tbtn active" id="btn_{tab_id}" '
           f'onclick="selTab(\'{tab_id}\')">{tab_lbl}'
           f'<span class="tclose" title="hide tab" '
           f'onclick="event.stopPropagation();closeTab(\'{tab_id}\')">&#10005;</span>'
           f'</button>\n')

    if S.get("skipped", True):
        meta = f"Nx={S['Nx']} &nbsp; NRep={S['NRep']}"
    else:
        meta = (f"Nx={S['Nx']} &nbsp; NRep={S['NRep']} &nbsp; "
                f"t<sub>ref</sub>={S['tRefIter']:.4g} {S['uLabel']}/iter")

    p  = f'<div class="tpanel active" id="{tab_id}">\n'
    p += f'<p class="hdr"><em>{_esc(S["header"])}</em></p>\n'
    p += f'<p class="meta">{meta}</p>\n'
    p += '<div class="cols">\n<div class="colL">\n'
    p += _bench_table_html(S)
    p += '</div>\n<div class="colR">\n'
    p += _test_table_html(records)
    p += "</div>\n</div>\n</div>\n"

    with open(TEMPLATE, encoding="utf-8") as f:
        tpl = f.read()
    txt = tpl.replace("{{BENCH_NAME}}", S["name"])
    txt = txt.replace("<!-- TAB_BTNS -->",   old_btns   + btn + "<!-- TAB_BTNS -->")
    txt = txt.replace("<!-- TAB_PANELS -->", old_panels + p   + "<!-- TAB_PANELS -->")

    with open(fname, "w", encoding="utf-8") as f:
        f.write(txt)
    return fname


# ════════════════════════════════════════════════════════════════
# Driver
# ════════════════════════════════════════════════════════════════
def runbench(class_name, version=None, changes=""):
    # MATLAB parity: runbench(className, version, changes). An empty version
    # ([] in MATLAB, None or [] here) means "auto-increment by 0.001".
    if isinstance(version, list) and not version:
        version = None
    # Discover support folders via use.py (root marker), like the test files —
    # so importing the test module's `from use import use` resolves.
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    from use import use
    use("silent")

    src = os.path.join(TESTS_DIR, class_name )
    if not os.path.isfile(src):
        src=src+".py"
        if not os.path.isfile(src):
            raise FileNotFoundError(f"test file not found: {src}")

    # derive BenchName from class_name (drop bench tokens)
    parts = [p for p in class_name.split("_") if p.lower() not in BENCH_TOKENS]
    name = "_".join(parts).strip("_") or class_name

    with open(src, encoding="utf-8") as f:
        txt = f.read()
    cur, ver_str = _resolve_version(txt, version)
    print(f" runbench: {class_name}  cur={cur:.3f} -> new={ver_str}  name='{name}'")

    txt = _patch_const(txt, "BenchVersion", ver_str)
    txt = _patch_const(txt, "BenchName",    name)
    txt = _patch_const(txt, "BenchHeader",  changes)
    with open(src, "w", encoding="utf-8") as f:
        f.write(txt)

    # import fresh (reload if already imported)
    mod = importlib.import_module(class_name)
    importlib.reload(mod)
    testclass = getattr(mod, class_name)

    res = run(testclass)
    S = testclass._bench_results
    if S is None:
        print(f" runbench: {class_name} stored no benchmark results — HTML not written.")
    else:
        fname = _write_html(S, res.records, class_name)
        print(f" HTML: {fname}\n")
    return res


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python primary/runbench.py <b_class> [version] [changes]")
        sys.exit(1)
    cls = sys.argv[1]
    ver = sys.argv[2] if len(sys.argv) > 2 else None      # '' -> auto-increment
    msg = sys.argv[3] if len(sys.argv) > 3 else ""
    runbench(cls, ver, msg)
