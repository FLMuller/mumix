"""modelselect.py  v02  Choose the tube model with an explicit penalty on complexity, on the data of Fig. 1b of the paper, with the weighted sum of squares of its last appendix.

    python modelselect.py            prints the tables and writes results/modelselect.json

Data.     analysis/data_corrected_dots.csv, written by analysis/data_corrected_plot.py: the dots of the bottom row of Fig. 1b (a single Re_lambda): Ghira et al. and the observed rows with the multipliers computed from the models of the probes,
          the other simulations as read.  Left out of every fit: the rows of Sassa and Makita at Re_lambda 820 (a shear flow) and 2391 (OUTLIER_IDS).  The main scenario leaves out the all-tube average of Mouri and Hori (2009) as well; the second scenario has it (threshold k = 0.33).

Measure.  For each quantity (r_max/eta, U_max/U_eta) with values e_i, mean ebar, and model values c_i:
              S = b sum (1 - c_i/e_i)^2 + sum (c_i - e_i)^2 / ebar^2,    b = (1 - ebar^2/e_max^2) / (ebar^2/e_min^2 - 1)
          (the appendix of the paper derives b: the relative error balanced between the smallest and the largest value).  Every point has the same weight; the S of the quantities add.  A model is fitted by minimising the S of the quantities it is fitted to
          (model.kinds); all models are judged on r and U.  s = sqrt(S / (N - p)), N the number of values of r and U, p the number of parameters: the standard error of the fit, dimensionless (reported in per cent as rms).

Criteria  AICc  N' ln(S/N) + 2p + 2p(p+1)/(N' - p - 1): the Akaike criterion with the small-sample correction; N' = the number of (source, quantity) groups ('AICc', the points of one source are not independent) or the number of points ('AICc pts').
          BIC   N' ln(S/N) + p ln N'.
          LOSO  leave one source out: the model is fitted without a source (b and the mean from the data that remain) and predicts it; the score is sqrt(sum of the S contributions of all left-out predictions, with the b and the mean of the whole data / N),
                in per cent.  A parameter that only follows the noise of one source makes this worse.  This is the criterion used for the choice, with the fewest parameters among the best.

Scenarios SCENARIOS below: with and without Mouri and Hori, the other thresholds of its all-tube average, the factors of Ghira et al., the two rows of Sassa and Makita.
Two populations: two_population() fits the swirl of the intense tubes and of all tubes separately, on the values as calculated from the papers, with the same measure.

Versions  M01 m01.v02 (2026-11-16): rebuilt on the data of Fig. 1b with the weighted sum of squares (linear domain, equal weight per point); the log-domain version with a weight per source is in zprev/modelselect_before_sos.py.
          M01 m01.v01 (2026-11-12): first version.
"""
import copy
import csv
import json
import math
import os
import sys

import numpy as np
from scipy.optimize import least_squares

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fitdata       # noqa: E402
import fitmodels     # noqa: E402

__all__ = ["balance", "fit", "criteria", "loso", "table", "two_population", "main", "SCENARIOS", "dots", "load", "OUTLIER_IDS"]

DATA = os.path.join(HERE, "data", "tubes.csv")
CORR = os.path.join(HERE, "data", "corrections.json")
DOTS = os.path.join(os.path.dirname(HERE), "analysis", "data_corrected_dots.csv")
KINDS = ("r", "U")
OUTLIER_IDS = (41, 67)                                  # Sassa and Makita (2005): the shear flow at Re_lambda 820 and the row at 2391


def number(text):
    return float(text) if text not in ("", None) else None


def dots(drop=(), mh_k="0.33", ghira=None, keep_ids=()):
    """The rows of the dots of Fig. 1b as rows for fitdata.observations (every value as the fits use it).
    drop: sources left out;  mh_k: the threshold of the all-tube average of Mouri and Hori ('0.25', '0.33', '0.5', '1');  ghira: None (the factors of the figure) or (radius factor, swirl factor) applied to the values as listed;  keep_ids: rows of OUTLIER_IDS to keep."""
    rows = []
    with open(DOTS, newline="", encoding="utf-8") as f:
        for rec in csv.DictReader(f):
            row = dict(id=int(rec["id"]), src=rec["src"], reference=rec["reference"], group=rec["group"], tube_set=rec["tube_set"], method=rec["method"], re=number(rec["re"]))
            r, u = number(rec["r"]), number(rec["u"])
            r_raw, u_raw = number(rec["r_raw"]), number(rec["u_raw"])
            if rec["src"] == "Mouri09" and mh_k != "0.33":
                r = None if r_raw is None else r_raw * number(rec["m_r_k" + mh_k])
                u = None if u_raw is None else u_raw * number(rec["m_u_k" + mh_k])
            if rec["src"].startswith("Ghira") and ghira is not None:
                r = None if r_raw is None else r_raw * ghira[0]
                u = None if u_raw is None else u_raw * ghira[1]
            row.update(r=r, u=u, r_raw=r_raw, u_raw=u_raw, re_lo=row["re"], re_hi=row["re"], gamma_listed=None, d_over_eta=None, g=(fitdata.G0 * r * u if r is not None and u is not None else None),
                       excluded=(rec["src"] in drop) or (int(rec["id"]) in OUTLIER_IDS and int(rec["id"]) not in keep_ids))
            rows.append(row)
    fitdata.EXCLUDED_QUANTITIES = {}
    return rows


def balance(e):
    """The factor b of the relative term: (1 - mean^2/max^2) / (mean^2/min^2 - 1) of the values e (appendix of the paper)."""
    m = float(np.mean(e))
    return (1.0 - m * m / float(np.max(e)) ** 2) / (m * m / float(np.min(e)) ** 2 - 1.0)


def stats(obs):
    """b and the mean of each quantity of the data."""
    return {k: (balance(obs[k]["val"]), float(np.mean(obs[k]["val"]))) for k in ("r", "U", "G") if len(obs[k]["val"]) > 1}


def contribution(calc, e, b, m):
    """The part of S of the values e fitted by calc: b sum (1 - calc/e)^2 + sum (calc - e)^2 / m^2, with the b and the mean m of the whole data of the quantity."""
    return float(b * np.sum((1.0 - calc / e) ** 2) + np.sum((calc - e) ** 2) / (m * m))


def residuals(model, p, obs, st):
    out = []
    for kind in model.kinds:
        d = obs[kind]
        if not len(d["re"]):
            continue
        b, m = st[kind]
        pred = model.predict(d["re"], p, d["tube_set"])[kind]
        out.append(math.sqrt(b) * (1.0 - pred / d["val"]))
        out.append((pred - d["val"]) / m)
    return np.concatenate(out)


def fit(model, obs):
    """Fit one model by minimising S of the quantities it is fitted to.  Returns the result dict of fitmodels.fit (params, budget at RE_CHECK, ok), with S of r and U on the data."""
    st = stats(obs)
    best = None
    for start in model.starts:
        lo, hi = model.bounds
        try:
            res = least_squares(lambda p: residuals(model, p, obs, st), start, bounds=(lo, hi), max_nfev=4000, x_scale="jac")
        except (ValueError, FloatingPointError):
            continue
        if best is None or res.cost < best.cost:
            best = res
    if best is None:
        return dict(model=model, ok=False, message="no start converged")
    p = best.x
    re = np.array(fitmodels.RE_CHECK, float)
    pr = model.predict(re, p, np.array(["intense"] * len(re)))
    return dict(model=model, ok=True, params=p, re_check=re, pred=pr, bud=fitmodels.budget(pr["r"], pr["U"]), message="")


def sum_squares(model, p, obs):
    """(S of r and U together, of r, of U, number of values, number of (source, quantity) groups) of the model on the data."""
    st = stats(obs)
    tot, part, n, groups = 0.0, {}, 0, set()
    for kind in KINDS:
        d = obs[kind]
        if not len(d["re"]):
            continue
        pred = model.predict(d["re"], p, np.array(d["tube_set"]))[kind]
        part[kind] = contribution(pred, d["val"], *st[kind])
        tot += part[kind]
        n += len(d["re"])
        groups |= {(s, kind) for s in d["src"]}
    return tot, part, n, len(groups)


def criteria(res, obs):
    """AICc and BIC of a fit, for N' = groups and N' = points, and the standard error s (per cent)."""
    m, p = res["model"], res["params"]
    ss, part, n, ng = sum_squares(m, p, obs)
    k = m.nparam
    out = {}
    for tag, nn in (("pts", n), ("src", ng)):
        aic = nn * math.log(ss / n) + 2 * k
        out["aicc_" + tag] = aic + (2 * k * (k + 1) / (nn - k - 1) if nn - k - 1 > 0 else float("inf"))
        out["bic_" + tag] = nn * math.log(ss / n) + k * math.log(nn)
    out.update(ss=ss, n=n, groups=ng, rms=100 * math.sqrt(ss / max(n - k, 1)),
               rms_r=100 * math.sqrt(part.get("r", 0.0) / max(len(obs["r"]["re"]), 1)), rms_U=100 * math.sqrt(part.get("U", 0.0) / max(len(obs["U"]["re"]), 1)))
    return out


def loso(model_key, rows):
    """Leave one source out: the standard error (per cent) of the predictions of each source by the model fitted without it, measured with the b and the means of the whole data."""
    obs_all = fitdata.observations(rows)
    st_all = stats(obs_all)
    sources = sorted({s for kind in KINDS for s in obs_all[kind]["src"]})
    total, n = 0.0, 0
    for left in sources:
        obs = fitdata.observations(rows, exclude=(left,))
        model = next(m for m in fitmodels.models(obs) if m.key == model_key)
        res = fit(model, obs)
        if not res.get("ok"):
            return float("nan")
        for kind in KINDS:
            d = obs_all[kind]
            take = np.array([s == left for s in d["src"]])
            if not take.any():
                continue
            pred = model.predict(d["re"][take], res["params"], np.array(d["tube_set"])[take])[kind]
            total += contribution(pred, d["val"][take], *st_all[kind])
            n += int(take.sum())
    return 100 * math.sqrt(total / n)


def table(rows, keys=None, with_loso=True):
    """One dict a model: key, name, k, rms (the standard error s, per cent), AICc and BIC (source count), their differences from the best, LOSO, sensible."""
    obs = fitdata.observations(rows)
    out = []
    for model in fitmodels.models(obs):
        if model.info or (keys and model.key not in keys):
            continue
        res = fit(model, obs)
        if not res.get("ok"):
            continue
        c = criteria(res, obs)
        out.append(dict(key=model.key, name=model.name, k=model.nparam, params=[float(v) for v in res["params"]], names=list(model.names),
                        rms=c["rms"], aicc=c["aicc_src"], bic=c["bic_src"], aicc_pts=c["aicc_pts"], n=c["n"], groups=c["groups"],
                        loso=loso(model.key, rows) if with_loso else float("nan"), sensible=fitmodels.sensible(res),
                        vf300=float(res["bud"]["vf"][2]), rms_r=c["rms_r"], rms_U=c["rms_U"]))
    for name in ("aicc", "bic", "aicc_pts"):
        best = min(x[name] for x in out)
        for x in out:
            x["d_" + name] = x[name] - best
    return out


def load(changes=None, excluded=None, quantities=None):
    """The rows under the constant factors of the corrections file (the corrections as adopted before the model multipliers of Fig. 1b; shown in the tabs of the recording book)."""
    with open(CORR, encoding="utf-8") as f:
        data = json.load(f)
    corr = copy.deepcopy(data.get("corrections", {}))
    for src, val in (changes or {}).items():
        if val is None:
            corr.pop(src, None)
        else:
            corr.setdefault(src, {}).update(val)
    rows = fitdata.load(DATA, CORR, corr=corr, excluded=data.get("excluded", {}) if excluded is None else excluded)
    fitdata.EXCLUDED_QUANTITIES = data.get("excluded_quantities", {}) if quantities is None else quantities
    return rows


SCENARIOS = [
    ("Fig. 1b data without Mouri-Hori 2009 (Sassa 820 and 2391 out)", dict(drop=("Mouri09",))),
    ("Fig. 1b data with Mouri-Hori 2009 at k = 0.33", dict()),
    ("with Mouri-Hori at k = 0.25", dict(mh_k="0.25")),
    ("with Mouri-Hori at k = 0.5", dict(mh_k="0.5")),
    ("with Mouri-Hori at k = 1", dict(mh_k="1")),
    ("without Mouri-Hori, Ghira as listed (radius x 1, swirl x 1)", dict(drop=("Mouri09",), ghira=(1.0, 1.0))),
    ("without Mouri-Hori, Ghira radius as listed, swirl x 0.67", dict(drop=("Mouri09",), ghira=(1.0, 0.67))),
    ("without Mouri-Hori, Ghira radius x 1.85, swirl x 0.6 (the whole-pdf mean as the target)", dict(drop=("Mouri09",), ghira=(1.85, 0.6))),
    ("without Mouri-Hori, the two rows of Sassa-Makita kept", dict(drop=("Mouri09",), keep_ids=OUTLIER_IDS)),
]
MAIN = ("D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "L1", "L2", "L3", "C1", "K5")


def show(rows_table, title):
    print("\n" + title)
    print("  %-4s %-2s %7s %7s %7s %7s %7s  %s" % ("key", "k", "s %", "LOSO %", "dAICc", "dBIC", "V_f300", "name"))
    for x in sorted(rows_table, key=lambda x: x["loso"] if not math.isnan(x["loso"]) else x["rms"]):
        print("  %-4s %-2d %7.2f %7.2f %7.1f %7.1f %7.3f  %s%s" % (x["key"], x["k"], x["rms"], x["loso"], x["d_aicc"], x["d_bic"], x["vf300"], x["name"][:60],
                                                                 "" if x["sensible"] else "  [not sensible]"))


# ------------------------------------------------------------------------------------------------ two populations
def sos_fit(shape, starts, bounds, re, e):
    """Minimise S of the values e (one quantity) by the model shape(p, Re): returns (p, the standard error s of the fit in per cent, N)."""
    b, m = balance(e), float(np.mean(e))
    fun = lambda p: np.r_[math.sqrt(b) * (1.0 - shape(p, re) / e), (shape(p, re) - e) / m]
    best = None
    for st in starts:
        res = least_squares(fun, st, bounds=bounds, max_nfev=4000, x_scale="jac")
        if best is None or res.cost < best.cost:
            best = res
    n = len(e)
    return best.x, 100 * math.sqrt(2 * best.cost / max(n - len(best.x), 1)), n


def two_population():
    """The swirl as calculated from the papers (no swirl correction), fitted as two populations, with the measure S (the same for every point of a group).
    Intense tubes (the 1 % of highest vorticity in DNS; the 0.1 % threshold of the hot wire): U = kappa u'/U_eta = kappa (Re/sqrt 15)^(1/2), and U = c Re^s.
    All tubes (Kida et al.; Mouri and Hori with an unknown chord factor f): U = a Re^s, f fitted or fixed.
    Returns a dict of the fits."""
    rows = fitdata.load(DATA, CORR, corr={}, excluded={})                 # nothing corrected, nothing excluded

    def pick(sources, extra=lambda x: True):
        sel = [x for x in rows if x["src"] in sources and x["re"] is not None and x["u_raw"] is not None and extra(x)]
        return np.array([x["re"] for x in sel]), np.array([x["u_raw"] for x in sel]), [x["src"] for x in sel]
    out = {}

    def strongest(x):                                                          # of each pair of Mouri et al. (2007) the stronger (0.1 % threshold)
        if x["src"] != "Mouri07":
            return True
        same = [y["u_raw"] for y in rows if y["src"] == "Mouri07" and y["re"] == x["re"]]
        return x["u_raw"] == max(same)
    re, u, src = pick(("Ghira22", "Ghira25", "Mouri07"), strongest)
    up = lambda r: np.sqrt(r / math.sqrt(15))
    pk, sk, n = sos_fit(lambda p, r: p[0] * up(r), [[1.0]], ([1e-3], [50]), re, u)
    pp, sp, _ = sos_fit(lambda p, r: p[0] * r ** p[1], [[0.5, 0.4], [2.0, 0.2]], ([1e-3, -1], [50, 2]), re, u)
    by = {s: 100 * float(np.mean([a / b - 1 for a, b, t in zip(pk[0] * up(re), u, src) if t == s])) for s in sorted(set(src))}
    out["intense"] = dict(n=n, sources=sorted(set(src)), kappa=float(pk[0]), rms_kappa=sk, c=float(pp[0]), s=float(pp[1]), rms_power=sp, by_source=by)
    re_k, u_k, _ = pick(("Kida02",))
    re_m, u_m, _ = pick(("Mouri09",))

    def fit_all(f=None):
        n_k = len(re_k)
        def shape_data(p):
            ff = p[2] if f is None else f
            return np.r_[u_k, ff * u_m]                                           # the values as the common law must meet them (Mouri and Hori times the chord factor)
        re_all = np.r_[re_k, re_m]

        def fun(p):
            e = shape_data(p)
            c = p[0] * re_all ** p[1]
            b, m = balance(e), float(np.mean(e))
            return np.r_[math.sqrt(b) * (1.0 - c / e), (c - e) / m]
        starts = [[2.0, 0.15, 2.0]] if f is None else [[2.0, 0.15]]
        bounds = ([0.1, -0.5, 0.5], [50, 1.0, 10]) if f is None else ([0.1, -0.5], [50, 1.0])
        best = None
        for st in starts:
            res = least_squares(fun, st, bounds=bounds, max_nfev=4000, x_scale="jac")
            if best is None or res.cost < best.cost:
                best = res
        return best
    free = fit_all()
    nn = len(re_k) + len(re_m)
    out["all_free"] = dict(a=float(free.x[0]), s=float(free.x[1]), f=float(free.x[2]), rms=100 * math.sqrt(2 * free.cost / max(nn - 3, 1)))
    for f in (1.0, 1.5, 2.0, 2.5, 3.0):
        fixed = fit_all(f)
        out["all_f%.1f" % f] = dict(a=float(fixed.x[0]), s=float(fixed.x[1]), f=f, rms=100 * math.sqrt(2 * fixed.cost / max(nn - 2, 1)))
    for name, (rr, uu) in (("Mouri09", (re_m, u_m)), ("Kida02", (re_k, u_k))):                                   # the internal exponent of each source alone
        p, _, _ = sos_fit(lambda q, r: q[0] * r ** q[1], [[1.0, 0.3], [0.3, 0.6]], ([1e-3, -1], [100, 2]), rr, uu)
        out["slope_" + name] = float(p[1])
    return out


def main():
    result = {"scenarios": [], "two_population": two_population()}
    for label, kw in SCENARIOS:
        rows = dots(**kw)
        t = table(rows, MAIN, with_loso=True)
        show(t, "Scenario: " + label)
        result["scenarios"].append(dict(label=label, changes={k: (list(v) if isinstance(v, tuple) else v) for k, v in kw.items()}, models=t))
    tp = result["two_population"]
    print("\nTwo populations (values as calculated from the papers, no swirl correction)")
    print("  intense: U = %.3f u'/U_eta, s %.1f %% | U = %.3f Re^%.3f, s %.1f %% | n = %d, sources %s; mean error by source (%%): %s" % (
        tp["intense"]["kappa"], tp["intense"]["rms_kappa"], tp["intense"]["c"], tp["intense"]["s"], tp["intense"]["rms_power"], tp["intense"]["n"],
        ", ".join(tp["intense"]["sources"]), {k: round(v, 1) for k, v in tp["intense"]["by_source"].items()}))
    for key in sorted(k for k in tp if k.startswith("all_")):
        v = tp[key]
        print("  all tubes (%s): U = %.3f Re^%.3f with Mouri-Hori x %.2f, s %.1f %%" % (key, v["a"], v["s"], v["f"], v["rms"]))
    print("  exponent within Mouri and Hori alone %.3f; within Kida alone %.3f" % (tp["slope_Mouri09"], tp["slope_Kida02"]))
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    with open(os.path.join(HERE, "results", "modelselect.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
