"""modelselect.py  v01  Choose the tube model with an explicit penalty on complexity, and test the choice against the corrections.

    python modelselect.py            prints the tables and writes results/modelselect.json

Why.  The fitting tool selected 'the model with the fewest parameters whose combined score is within 25 % of the best'.  That rule has no
statistical basis for the width 25 %.  Here every model of fitmodels.py is judged three ways on the same data:

    AICc   n ln(SS/n) + 2k + 2k(k+1)/(n-k-1): the Akaike criterion with the small-sample correction.  SS is the weighted sum of squared log residuals
           of the radius and the swirl together (the two quantities that are measured; the circulation follows from them).  Lower is better;
           a difference under 2 is no evidence, over 10 is decisive (Burnham and Anderson).
    BIC    n ln(SS/n) + k ln n: penalises a parameter more than AICc when n is large.
    LOSO   leave one source out: the model is fitted without a source and then predicts that source; the score is the weighted rms log
           error of all the left-out predictions, in per cent.  A parameter that only follows the noise of one source makes this worse, so the
           penalty on complexity is the data's own.  This is the criterion used for the choice.

n is counted two ways, because the points of one source are not independent: n = the number of points, and n = the number of (source, quantity)
groups (each source counts once per quantity, as the weights of fitdata already do).  The second is the honest one and is the one reported
as 'AICc(src)'.

Scenarios.  The corrections are the largest uncertainty, so the comparison is repeated for other corrections (SCENARIOS below).

Two populations.  two_population() fits the swirl of the intense tubes (the 1 % of highest vorticity, and the threshold averages of the hot wire)
and of all tubes separately, on the values as calculated from the papers (no swirl correction).

Versions  M01 m01.v01 (2026-11-12): first version.
"""
import copy
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

__all__ = ["criteria", "loso", "table", "two_population", "main", "SCENARIOS"]

DATA = os.path.join(HERE, "data", "tubes.csv")
CORR = os.path.join(HERE, "data", "corrections.json")
KINDS = ("r", "U")


def sum_squares(model, p, obs):
    """(weighted SS of the log residuals of r and U, number of points, number of (source, quantity) groups)."""
    ss, n, groups = 0.0, 0, set()
    for kind in KINDS:
        o = obs[kind]
        if not len(o["re"]):
            continue
        pred = model.predict(o["re"], p, np.array(o["tube_set"]))[kind]
        e = np.log(pred / o["val"])
        ss += float(np.sum(o["w"] * e * e))
        n += len(e)
        groups |= {(s, kind) for s in o["src"]}
    return ss, n, len(groups)


def criteria(res, obs):
    """AICc and BIC of a fit result, for n = points and n = source groups."""
    m, p = res["model"], res["params"]
    ss, n, ng = sum_squares(m, p, obs)
    k = m.nparam
    out = {}
    for tag, nn in (("pts", n), ("src", ng)):
        s2 = ss / n                                   # the mean weighted square residual (the weights average 1)
        aic = nn * math.log(s2) + 2 * k
        out["aicc_" + tag] = aic + (2 * k * (k + 1) / (nn - k - 1) if nn - k - 1 > 0 else float("inf"))
        out["bic_" + tag] = nn * math.log(s2) + k * math.log(nn)
    out.update(ss=ss, n=n, groups=ng, rms=100 * math.sqrt(ss / n))
    return out


def loso(model_key, rows):
    """Leave one source out: weighted rms log error (per cent) of the predictions of each source by the model fitted without it."""
    obs_all = fitdata.observations(rows)
    sources = sorted({s for kind in KINDS for s in obs_all[kind]["src"]})
    se, sw = 0.0, 0.0
    for left in sources:
        obs = fitdata.observations(rows, exclude=(left,))
        model = next(m for m in fitmodels.models(obs) if m.key == model_key)
        res = fitmodels.fit(model, obs)
        if not res.get("ok"):
            return float("nan")
        for kind in KINDS:
            o = obs_all[kind]
            take = np.array([s == left for s in o["src"]])
            if not take.any():
                continue
            pred = model.predict(o["re"][take], res["params"], np.array(o["tube_set"])[take])[kind]
            e = np.log(pred / o["val"][take])
            se += float(np.sum(o["w"][take] * e * e))
            sw += float(np.sum(o["w"][take]))
    return 100 * math.sqrt(se / sw)


def table(rows, keys=None, with_loso=True):
    """One dict a model: key, name, k, rms, AICc and BIC (source count), their differences from the best, LOSO, sensible."""
    obs = fitdata.observations(rows)
    out = []
    for model in fitmodels.models(obs):
        if model.info or (keys and model.key not in keys):
            continue
        res = fitmodels.fit(model, obs)
        if not res.get("ok"):
            continue
        c = criteria(res, obs)
        out.append(dict(key=model.key, name=model.name, k=model.nparam, params=[float(v) for v in res["params"]], names=list(model.names),
                        rms=c["rms"], aicc=c["aicc_src"], bic=c["bic_src"], aicc_pts=c["aicc_pts"], n=c["n"], groups=c["groups"],
                        loso=loso(model.key, rows) if with_loso else float("nan"), sensible=fitmodels.sensible(res),
                        vf300=float(res["bud"]["vf"][2]), rms_r=100 * res["scores"]["rms_r"], rms_U=100 * res["scores"]["rms_U"]))
    for name in ("aicc", "bic", "aicc_pts"):
        best = min(x[name] for x in out)
        for x in out:
            x["d_" + name] = x[name] - best
    return out


def load(changes=None, excluded=None, quantities=None):
    """The rows under a scenario: changes {source: {r_divisor, u_factor} or None} applied to the corrections of the file."""
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
    ("as used: Mouri-Hori r/1.75, U x 3; Ghira U x 0.6", {}),
    ("Mouri-Hori U x 2.5", {"Mouri09": {"u_factor": 2.5}}),
    ("Mouri-Hori U x 2", {"Mouri09": {"u_factor": 2.0}}),
    ("Ghira as listed (x 1), Mouri-Hori U x 3", {"Ghira22": {"u_factor": 1.0}, "Ghira25": {"u_factor": 1.0}}),
    ("Ghira as listed (x 1), Mouri-Hori U x 5", {"Ghira22": {"u_factor": 1.0}, "Ghira25": {"u_factor": 1.0}, "Mouri09": {"u_factor": 5.0}}),
    ("Mouri-Hori r/1.6", {"Mouri09": {"r_divisor": 1.6}}),
    ("Mouri-Hori r/1.9", {"Mouri09": {"r_divisor": 1.9}}),
]
MAIN = ("D1", "D2", "D3", "D4", "D6", "D8", "L1", "L2", "L3", "C1", "K5")


def show(rows_table, title):
    print("\n" + title)
    print("  %-4s %-2s %7s %7s %7s %7s %7s  %s" % ("key", "k", "rms %", "LOSO %", "dAICc", "dBIC", "V_f300", "name"))
    for x in sorted(rows_table, key=lambda x: x["loso"] if not math.isnan(x["loso"]) else x["rms"]):
        print("  %-4s %-2d %7.2f %7.2f %7.1f %7.1f %7.3f  %s%s" % (x["key"], x["k"], x["rms"], x["loso"], x["d_aicc"], x["d_bic"], x["vf300"], x["name"][:60],
                                                                 "" if x["sensible"] else "  [not sensible]"))


# ------------------------------------------------------------------------------------------------ two populations
def two_population():
    """The swirl as calculated from the papers (no swirl correction), fitted as two populations.
    Intense tubes (the 1 % of highest vorticity in DNS; the 0.1 % threshold of the hot wire): U = kappa u'/U_eta = kappa (Re/sqrt 15)^(1/2), and U = c Re^s.
    All tubes (Kida et al.; Mouri and Hori with an unknown chord factor f): U = a Re^s, f fitted or fixed.
    Returns a dict of the fits."""
    with open(CORR, encoding="utf-8") as f:
        data = json.load(f)
    rows = fitdata.load(DATA, CORR, corr={}, excluded={})                 # nothing corrected, nothing excluded
    def pick(sources, extra=lambda x: True):
        sel = [x for x in rows if x["src"] in sources and x["re"] is not None and x["u_raw"] is not None and extra(x)]
        cnt = {}
        for x in sel:
            cnt[x["src"]] = cnt.get(x["src"], 0) + 1
        w = np.array([1.0 / cnt[x["src"]] for x in sel])
        return np.array([x["re"] for x in sel]), np.array([x["u_raw"] for x in sel]), w * len(w) / w.sum(), [x["src"] for x in sel]
    out = {}
    # the intense population: Ghira 2022, 2025 (DNS), Mouri 2007 at the 0.1 % threshold (the stronger of each pair)
    def strongest(x):
        if x["src"] != "Mouri07":
            return True
        same = [y["u_raw"] for y in rows if y["src"] == "Mouri07" and y["re"] == x["re"]]
        return x["u_raw"] == max(same)
    re, u, w, src = pick(("Ghira22", "Ghira25", "Mouri07"), strongest)
    up = np.sqrt(re / math.sqrt(15))
    kappa = math.exp(np.sum(w * np.log(u / up)) / np.sum(w))
    e1 = np.log(kappa * up / u)
    A = np.vstack([np.ones_like(re), np.log(re)]).T
    b = np.linalg.lstsq(A * np.sqrt(w)[:, None], np.log(u) * np.sqrt(w), rcond=None)[0]
    e2 = A @ b - np.log(u)
    out["intense"] = dict(n=len(re), sources=sorted(set(src)), kappa=kappa, rms_kappa=100 * math.sqrt(np.sum(w * e1 * e1) / np.sum(w)),
                          c=math.exp(b[0]), s=float(b[1]), rms_power=100 * math.sqrt(np.sum(w * e2 * e2) / np.sum(w)),
                          by_source={s: 100 * float(np.mean([e for e, t in zip(e1, src) if t == s])) for s in sorted(set(src))})
    # all tubes: Kida (DNS, low-pressure vortices), Mouri and Hori 2009 times an unknown chord factor f
    re_k, u_k, w_k, _ = pick(("Kida02",))
    re_m, u_m, w_m, _ = pick(("Mouri09",))
    def resid(p, f=None):
        a, s = p[0], p[1]
        ff = p[2] if f is None else f
        return np.r_[np.log(a * re_k**s / u_k) / math.sqrt(len(re_k)), np.log(a * re_m**s / (ff * u_m)) / math.sqrt(len(re_m))]
    free = least_squares(resid, [2.0, 0.15, 2.0], bounds=([0.1, -0.5, 0.5], [50, 1.0, 10]))
    out["all_free"] = dict(a=float(free.x[0]), s=float(free.x[1]), f=float(free.x[2]), rms=100 * math.sqrt(float(np.mean(free.fun**2)) ))
    for f in (1.0, 1.5, 2.0, 2.5, 3.0):
        fit = least_squares(lambda p: resid(p, f), [2.0, 0.15], bounds=([0.1, -0.5], [50, 1.0]))
        out["all_f%.1f" % f] = dict(a=float(fit.x[0]), s=float(fit.x[1]), f=f, rms=100 * math.sqrt(float(np.mean(fit.fun**2))))
    # the internal exponent of each source alone
    for name, (rr, uu) in (("Mouri09", (re_m, u_m)), ("Kida02", (re_k, u_k))):
        b = np.polyfit(np.log(rr), np.log(uu), 1)
        out["slope_" + name] = float(b[0])
    return out


def main():
    result = {"scenarios": [], "two_population": two_population()}
    for label, changes in SCENARIOS:
        rows = load(changes)
        t = table(rows, MAIN, with_loso=True)
        show(t, "Scenario: " + label)
        result["scenarios"].append(dict(label=label, changes=changes, models=t))
    tp = result["two_population"]
    print("\nTwo populations (values as calculated from the papers, no swirl correction)")
    print("  intense: U = %.3f u'/U_eta, rms %.1f %% | U = %.3f Re^%.3f, rms %.1f %% | n = %d, sources %s; mean log error by source (%%): %s" % (
        tp["intense"]["kappa"], tp["intense"]["rms_kappa"], tp["intense"]["c"], tp["intense"]["s"], tp["intense"]["rms_power"], tp["intense"]["n"],
        ", ".join(tp["intense"]["sources"]), {k: round(v, 1) for k, v in tp["intense"]["by_source"].items()}))
    for key in sorted(k for k in tp if k.startswith("all_")):
        v = tp[key]
        print("  all tubes (%s): U = %.3f Re^%.3f with Mouri-Hori x %.2f, rms %.1f %%" % (key, v["a"], v["s"], v["f"], v["rms"]))
    print("  exponent within Mouri and Hori alone %.3f; within Kida alone %.3f" % (tp["slope_Mouri09"], tp["slope_Kida02"]))
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    with open(os.path.join(HERE, "results", "modelselect.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
