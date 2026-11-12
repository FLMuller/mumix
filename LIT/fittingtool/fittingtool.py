"""fittingtool.py  v01  Fit the tube closure models to the literature data and write the report.

Use
    python fittingtool.py [--data FILE] [--corrections FILE] [--exclude SRC,SRC] [--results DIR] [--tolerance 1.15] [--no-report]

    reads   data/tubes.csv (the data, made by exportdata.py) and data/corrections.json (the corrections applied to the values of the papers)
    fits    every model of fitmodels.py (the circulation, direct power-law, closure and two-set families) to the corrected data
    writes  results/fit_YYYY.MM.DD_HH;MM.html (one document: Summary, Data, Corrections, R and U, Compare, a tab for each model, Legacy, Notes),
            results/index.html (a file tree of the reports) and results/latest.json (parameters and scores of the run)
    prints  one line for each model and the selected model; then shows the report through the report server (contactRS, if mumix/tools/reportserver.py is
            found above this folder and answers; --no-open leaves that out).

The tool needs numpy, scipy and matplotlib; it reads nothing outside its folder.  Run it from any folder: python path/to/fittingtool.py.

Versions  M01 m01.v02 (2026-11-11): the report is shown through the report server at the end of a run (--no-open to skip); models D6-D8, L1-L5, K5.
          M01 m01.v01 (2026-11-11): first version (models D1-D5, C1-C3, K3, K4, T6, legacy n; report and index).
"""
import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fitdata       # noqa: E402
import fitmodels     # noqa: E402
import fitreport     # noqa: E402

__all__ = ["run", "main"]


def fit_all(rows, exclude=()):
    """Fit every model to the rows; returns (obs, results, selected key, reasons)."""
    obs = fitdata.observations(rows, exclude=exclude)
    results = [fitmodels.fit(m, obs) for m in fitmodels.models(obs)]
    selected, reasons = fitmodels.select(results)
    return obs, results, selected, reasons


def variants(data_path, corrections, excluded):
    """The same fits under other choices of correction: a list of dicts (label, selected, scores and parameters of the main models)."""
    import copy
    def with_changes(**changes):
        c = copy.deepcopy(corrections)
        for src, val in changes.items():
            if val is None:
                c.pop(src, None)
            else:
                c.setdefault(src, {}).update(val)
        return c
    plan = [("as used (the Corrections tab)", corrections, ()),
            ("no corrections at all", {}, ()),
            ("Mouri and Hori (2009) left out", corrections, ("Mouri09",)),
            ("Mouri and Hori radius / 1.17 (the high amplitude cut chord ratio)", with_changes(Mouri09={"r_divisor": 1.17}), ()),
            ("Mouri and Hori radius / 1.7 (the value on the page, v46)", with_changes(Mouri09={"r_divisor": 1.7}), ()),
            ("Mouri and Hori swirl x 5 (the comparison with the threshold pairs)", with_changes(Mouri09={"u_factor": 5.0}), ()),
            ("Mouri and Hori swirl as calculated (no x 3)", with_changes(Mouri09={"u_factor": 1.0}), ()),
            ("Ghira (2022) swirl as calculated (no x 0.6)", with_changes(Ghira22=None), ()),
            ("Ghira (2022) left out", corrections, ("Ghira22",)),
            ("Mouri 2004 and 2007 included, as calculated", corrections, ())]
    out = []
    for label, corr, exclude in plan:
        keep = {} if label.startswith(("no corrections", "Mouri 2004 and 2007 included")) else excluded
        rows = fitdata.load(data_path, corr=corr, excluded=keep)
        obs, results, selected, reasons = fit_all(rows, exclude)
        by = {r["model"].key: r for r in results if r["ok"]}
        out.append(dict(label=label, selected=selected, by=by))
    return out


def run(data_path, corr_path, exclude=(), tolerance=None, with_variants=True):
    """Fit all models; returns the context dict of the report."""
    if tolerance:
        fitmodels.TOLERANCE = tolerance
    rows = fitdata.load(data_path, corr_path)
    obs, results, selected, reasons = fit_all(rows, exclude)
    with open(corr_path, encoding="utf-8") as f:
        corr_file = json.load(f)
    corrections, excluded = corr_file["corrections"], corr_file.get("excluded", {})
    res_all = [x["re"] for x in rows if x["re"] is not None]
    summary = ", ".join("%s: radius / %g, swirl x %g" % (k, v.get("r_divisor", 1.0), v.get("u_factor", 1.0)) for k, v in corrections.items()) or "none"
    return dict(rows=rows, obs=obs, results=results, selected=selected, reasons=reasons, legacy=fitmodels.legacy_n(rows), corrections=corrections,
                excluded=excluded, tolerance=fitmodels.TOLERANCE, stamp=time.strftime("%Y-%m-%d %H:%M"), corr_summary=summary,
                variants=variants(data_path, corrections, excluded) if with_variants else [],
                re_range="%g&ndash;%g" % (min(res_all), max(res_all)), files=dict(data=os.path.basename(data_path), corrections=os.path.basename(corr_path)))


def save_json(path, ctx):
    out = dict(stamp=ctx["stamp"], selected=ctx["selected"], corrections=ctx["corrections"], models={})
    for r in ctx["results"]:
        m = r["model"]
        if r.get("ok"):
            out["models"][m.key] = dict(name=m.name, family=m.family, nparam=m.nparam, equations=m.equations, names=m.names, params=[float(v) for v in r["params"]],
                                        errors=[float(v) for v in r["errors"]], scores=r["scores"], re_check=[float(v) for v in r["re_check"]],
                                        r=[float(v) for v in r["pred"]["r"]], U=[float(v) for v in r["pred"]["U"]], G=[float(v) for v in r["pred"]["G"]],
                                        vf=[float(v) for v in r["bud"]["vf"]], d=[float(v) for v in r["bud"]["d"]], info=m.info)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)


def open_report(path):
    """Show the report through the report server (mumix/tools/reportserver.py, looked for in the folders above this one): contactRS('load', '[doc]', ...), the
    layout the server gives a doc, with its status bar.  Returns the address, or None with the reason printed when there is no server module or it refuses.
    Without the server the report is the same file: open it from the file manager."""
    folder = HERE
    tools = None
    while True:
        if os.path.isfile(os.path.join(folder, "tools", "reportserver.py")):
            tools = os.path.join(folder, "tools")
            break
        parent = os.path.dirname(folder)
        if parent == folder:
            break
        folder = parent
    if tools is None:
        print("report server: not found above this folder; open the report file directly")
        return None
    sys.path.insert(0, tools)
    sys.path.insert(0, os.path.join(tools, "rs_primary"))
    try:
        import reportserver
        from rs3util import pathof
        rel = pathof(os.path.abspath(path))
        if rel is None:
            print("report server: %s is outside the home of the report server; open the file directly" % os.path.basename(path))
            return None
        got = reportserver.contactRS("load", "[doc]", {"doc": ["doc", rel]}, os.path.basename(path))
        print("report server: opened", got.get("url", rel))
        return got.get("url")
    except Exception as error:                      # no server, refused, no answer: the report file itself is still there
        print("report server: not opened (%s); open the report file directly" % error)
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fit the tube closure models and write the report.")
    ap.add_argument("--data", default=os.path.join(HERE, "data", "tubes.csv"))
    ap.add_argument("--corrections", default=os.path.join(HERE, "data", "corrections.json"))
    ap.add_argument("--exclude", default="", help="sources left out of the fits, e.g. Mouri09")
    ap.add_argument("--results", default=os.path.join(HERE, "results"))
    ap.add_argument("--tolerance", type=float, default=None, help="selection tolerance on the combined score (default 1.25)")
    ap.add_argument("--no-report", action="store_true")
    ap.add_argument("--no-open", action="store_true", help="do not show the report through the report server at the end of the run")
    a = ap.parse_args(argv)
    ctx = run(a.data, a.corrections, tuple(s for s in a.exclude.split(",") if s), a.tolerance)
    for r in ctx["results"]:
        m = r["model"]
        if not r["ok"]:
            print("%-3s FAILED %s" % (m.key, r["message"]))
            continue
        sc = r["scores"]
        print("%-3s %-66s p=%d  rms r %.1f%% U %.1f%% G %.1f%%  combined %.1f%%  V_f(300) %.3f" % (m.key, m.name[:66], m.nparam, 100 * sc["rms_r"], 100 * sc["rms_U"], 100 * sc["rms_G"],
                                                                                                    100 * sc["combined"], r["bud"]["vf"][2]))
    print("selected:", ctx["selected"])
    if not a.no_report:
        os.makedirs(a.results, exist_ok=True)
        path = fitreport.write_report(a.results, ctx)
        save_json(os.path.join(a.results, "latest.json"), ctx)
        index = fitreport.write_index(a.results)
        print("report:", path)
        print("index :", index)
        if not a.no_open:
            open_report(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
