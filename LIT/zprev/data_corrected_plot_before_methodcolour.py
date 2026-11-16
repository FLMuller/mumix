"""data_corrected_plot.py  v01  The tube data of the page as read, and with the model's multipliers applied to the observed (probe) data: r_max / eta, U_max / U_eta and G = Gamma / nu against Re_lambda.
Rows      top: every data point as read (fittingtool/data/tubes.csv, raw values); bottom: the DNS rows as read and the observed rows corrected with the multipliers of the Belin-fit tubes (belin_correctors*.json).
Columns   r_max / eta, U_max / U_eta, G = 8.784 r_max U_max / nu (from the two values of a row; a row without a swirl but with a listed Gamma / nu, Jimenez et al., shows the listed value; otherwise no G, see data_G_derivation.csv).
Multipliers (corrected = m x printed value; interpolated linearly in log Re_lambda, constant outside the Re_lambda range of the runs, 100-2000)
          Belin 1996: r of Belin's wire and U by his published rule (shape match, belin_correctors.json); his U is not a row of the table: it is derived from his Fig. 6, U_max / U_eta = 1.585 exp(mu) Re_lambda^(1/2) / r_max with the median exp(mu) of the lognormal fit of x and r_max = 7.608 eta of the table row;  Mouri et al. 2007 (0.1% and 1% classes, the class of a row is the one with the smaller r at the same Re_lambda: 0.1%) and 2004 (1% class): the Mouri class multipliers;
          Mouri and Hori 2009: all-tube average at 0.33 sigma (belin_correctors_all.json);  Sassa and Makita 2005: C = 2.5 (belin_correctors_sassa.json; below Re_lambda 100 the value at 100).
          Ghira et al. 2022 and 2025: radius x 1.25 and swirl x 0.67 (section 9a, from the all-tube population of Pirozzoli 2012).
          Not corrected (no multiplier yet): Mouri 2003 (a range only), Aligolzadeh 2023, the wall flows and the other DNS rows.
Usage     python data_corrected_plot.py     writes data_corrected_plot.png and data_G_derivation.csv
Versions  M01 m01.v11 (2026-11-16): the dots of Mouri and Hori 2009 are grey.
          M01 m01.v10 (2026-11-16): dashed red: the straight line of r and U = a Re^0.5 fitted without Mouri and Hori 2009; dashed grey: the same with it.
          M01 m01.v09 (2026-11-16): Mouri and Hori 2009 at k = 0.33 sigma.
          M01 m01.v08 (2026-11-16): the solid red lines are removed; the dashed U line is the exponent 0.5 again (1/3 in the first v08 run).
          M01 m01.v07 (2026-11-16): Wang et al. (2007) is in the fit again; the last row of Sassa and Makita (2005), Re_lambda 2391, is out.
          M01 m01.v06 (2026-11-16): Mouri and Hori 2009 at k = 0.33 sigma; the fits minimise SOS = sqrt(sum((calc/exp - 1)^2)) + sqrt(sum((calc - exp)^2) / mean(exp)), every point with the same weight (fit_trends, domain='sos').
          M01 m01.v05 (2026-11-16): Mouri and Hori 2009 at k = 0.2 sigma (0.5 in v04, 0.3 in v05); the main fit excludes the one Wang et al. (2007) row; linear-domain fits (fit_trends, domain='linear').
          M01 m01.v04 (2026-11-15): trends of r and U fitted to the dots of the bottom row (fit_trends) and drawn in red; data_corrected_fits.json.
          M01 m01.v03 (2026-11-15): linear axes (Re_lambda and G).
          M01 m01.v02 (2026-11-15): Ghira et al. (2022, 2025) corrected with radius x 1.25 and swirl x 0.67 in the bottom row.
          M01 m01.v01 (2026-11-14): first version.
"""
import csv
import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "fittingtool"))
import fitdata                        # noqa: E402
sys.path.insert(0, HERE)
import belin_gamma_pdf as bg          # noqa: E402

DATA = os.path.join(os.path.dirname(HERE), "fittingtool", "data", "tubes.csv")
G0 = fitdata.G0


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


class Table:
    """Multiplier against Re_lambda from a list of (Re_lambda, value), linear in log Re_lambda, constant outside."""

    def __init__(self, points):
        pts = sorted(points)
        self.x = np.log([p[0] for p in pts])
        self.y = np.array([p[1] for p in pts])

    def __call__(self, re):
        return float(np.interp(math.log(re), self.x, self.y))


def tables():
    c = load("belin_correctors.json")
    a = load("belin_correctors_all.json")
    s = load("belin_correctors_sassa.json")
    t = {}
    for name in ("Mouri 1%", "Mouri 0.1%"):
        t[name] = (Table([(r["Re_lambda"], r["r"][name]["shape"]) for r in c]), Table([(r["Re_lambda"], r["U"][name]["shape"]) for r in c]))
    t["Belin"] = (Table([(r["Re_lambda"], r["r"]["Belin's wire"]["shape"]) for r in c]), Table([(r["Re_lambda"], r["U"]["Belin's wire, published rule dS/(2 x 0.14)"]["shape"]) for r in c]))
    t["Mouri09"] = (Table([(r["Re_lambda"], r["k=0.33"]["m_r"]) for r in a]), Table([(r["Re_lambda"], r["k=0.33"]["m_U"]) for r in a]))
    t["Ghira"] = (Table([(100, 1.25), (2000, 1.25)]), Table([(100, 0.67), (2000, 0.67)]))                              # the 1%-volume DNS to the whole population (section 9a): radius x 1.25, swirl x 0.67
    t["Sassa05"] = (Table([(r["Re_lambda"], r["C=2.5"]["m_r"]) for r in s]), Table([(r["Re_lambda"], r["C=2.5"]["m_U"]) for r in s]))
    return t


def sos(calc, exp):
    """The sum of squares of the fits: sqrt(sum((calc/exp - 1)^2)) + sqrt(sum((calc - exp)^2) / mean(exp)): the relative and the absolute misfit of the points."""
    return float(np.sqrt(np.sum((calc / exp - 1.0) ** 2)) + np.sqrt(np.sum((calc - exp) ** 2) / np.mean(exp)))


def fit_trends(out, exclude=(), domain="sos", exclude_ids=()):
    """Trends of r_max/eta and U_max/U_eta with Re_lambda fitted to the dots of the bottom row (the values as plotted there: Ghira and the observed rows corrected, the other DNS as read); the lines (rows with a range of Re_lambda: Belin, Mouri 2003, the range of Sassa) are not used.
    Least squares in the LINEAR domain, SS = sum w (y - model)^2 (domain="log": of ln y, the version of m01.v04); each source has the same weight in each quantity (the weights 1/n of its points, scaled to sum to the number of points).
    r: a constant, a power law or a straight line;  U: a power law with a free exponent, the exponents 1/3 and 1/2, and a straight line.  rms_pct = 100 sqrt(SS/n) / mean(y) (linear); rms_log_pct = 100 sqrt(mean w ln(y/model)^2).  The best of the constant and power laws is chosen by AICc."""
    from scipy.optimize import least_squares, minimize
    pts = {"r": [], "U": []}
    for d in out:
        if d["lo"] is None or d["lo"] != d["hi"] or d["src"] in exclude or d["id"] in exclude_ids:
            continue
        corr = d["corrected"] and (not d["method"].startswith("DNS") or d["src"].startswith("Ghira"))
        for key, raw, lo in (("r", d["r_raw"], d.get("r_lo")), ("U", d["u_raw"], d.get("u_lo"))):
            v = (lo if corr else raw)
            if v is not None and v > 0:
                pts[key].append((d["lo"], v, d["src"]))
    shapes = {"constant": (lambda q, re: q[0] + 0 * re, 1), "power": (lambda q, re: q[0] * re ** q[1], 2), "straight line": (lambda q, re: q[0] + q[1] * re, 2),
              "power, exponent 1/3": (lambda q, re: q[0] * re ** (1 / 3), 1), "power, exponent 1/2": (lambda q, re: q[0] * re ** 0.5, 1)}
    fits = {}
    for key, names in (("r", ("constant", "power", "straight line")), ("U", ("power", "power, exponent 1/3", "power, exponent 1/2", "straight line"))):
        data = pts[key]
        re, y, src = np.array([p[0] for p in data]), np.array([p[1] for p in data]), [p[2] for p in data]
        w = np.array([1.0 / src.count(s) for s in src])
        w *= len(w) / w.sum()
        if domain == "sos":
            w = np.ones(len(y))                                                      # every point has the same weight
        n = len(y)
        res = {}
        for name in names:
            f, k = shapes[name]
            q0 = [float(np.mean(y)), 0.0] if name in ("power", "straight line") else [float(np.mean(y))]
            if name == "power":
                q0 = [float(np.mean(y)), 0.3]
            elif name == "straight line":
                q0 = [float(np.mean(y)), 0.0]
            if domain == "linear":
                fun = lambda q: np.sqrt(w) * (y - f(q, re))
            else:
                fun = lambda q: np.sqrt(w) * (np.log(y) - np.log(np.maximum(f(q, re), 1e-9)))
            starts = [q0] if name != "power" else [[float(np.mean(y)) / float(np.mean(re)) ** b0, b0] for b0 in (-0.2, 0.0, 0.2, 0.4, 0.6)]
            q = min((least_squares(fun, st) for st in starts), key=lambda r_: r_.cost).x
            if domain == "sos":                                                       # SOS = sqrt(sum((calc/exp - 1)^2)) + sqrt(sum((calc - exp)^2) / mean(exp)), minimised from the linear least-squares solution
                S = lambda qq: sos(f(qq, re), y)
                q = least_squares(lambda qq: np.sqrt(w) * (y - f(qq, re)), q).x
                q = minimize(S, q, method="Nelder-Mead", options=dict(xatol=1e-9, fatol=1e-12, maxiter=20000, maxfev=20000)).x
            model = f(q, re)
            rss = sos(model, y) ** 2 if domain == "sos" else (float(np.sum(w * (y - model) ** 2)) if domain == "linear" else float(np.sum(w * (np.log(y) - np.log(model)) ** 2)))
            aic = n * math.log(rss / n) + 2 * k + 2 * k * (k + 1) / max(n - k - 1, 1)
            e = (float(q[0]), float(q[1]) if k == 2 else {"constant": 0.0, "power, exponent 1/3": 1 / 3, "power, exponent 1/2": 0.5}[name])
            res[name] = dict(a=e[0], b=e[1], k=k, rms_pct=100 * math.sqrt(float(np.sum(w * (y - model) ** 2)) / n) / float(np.mean(y)), rms_log_pct=100 * math.sqrt(float(np.sum(w * (np.log(y) - np.log(model)) ** 2)) / n), aicc=aic, aicc_domain=domain, rss=rss, line=name == "straight line")
        best = min((m for m in res if not res[m].get("line")), key=lambda m: res[m]["aicc"])
        bm = res[best]
        resid = np.log(y) - np.log(shapes[best][0]([bm["a"], bm["b"]], re))
        by = {}
        for s in sorted(set(src)):
            sel = [i for i, qq in enumerate(src) if qq == s]
            by[s] = dict(n=len(sel), mean_ln=float(np.mean(resid[sel])), sd_ln=float(np.std(resid[sel])))
        fits[key] = dict(n=n, n_sources=len(set(src)), models=res, best=best, by_source=by, re_range=[float(re.min()), float(re.max())], domain=domain)
    return fits


def main():
    rows = fitdata.load(DATA)
    mult = tables()
    pair = {}
    for x in rows:                                                                  # the class of a Mouri 2007 row: at one Re_lambda the smaller r is the 0.1% class
        if x["src"] == "Mouri07":
            pair.setdefault(x["re"], []).append(x)
    cls = {}
    for re, rs in pair.items():
        rs = sorted(rs, key=lambda x: x["r_raw"])
        cls[rs[0]["id"]], cls[rs[-1]["id"]] = "Mouri 0.1%", "Mouri 1%"
    out = []                                                                        # per row: raw r, u, corrected r, u, source of the multiplier
    for x in rows:
        key = {"Mouri07": cls.get(x["id"]), "Mouri04": "Mouri 1%", "Belin96": "Belin", "Mouri09": "Mouri09", "Sassa05": "Sassa05", "Ghira22": "Ghira", "Ghira25": "Ghira"}.get(x["src"])
        f = dict(r=lambda re: 1.0, u=lambda re: 1.0)
        if key:
            f = dict(r=mult[key][0], u=mult[key][1] if mult[key][1] else (lambda re: 1.0))
        lo, hi = x["re_lo"], x["re_hi"]
        mid = math.sqrt(lo * hi) if lo is not None else None
        d = dict(src=x["src"], tube_set=x["tube_set"], method=x["method"], lo=lo, hi=hi, r_raw=x["r_raw"], u_raw=x["u_raw"], gamma_listed=x["gamma_listed"], corrected=bool(key), key=key, id=x["id"])
        if lo is not None:
            d["r_lo"], d["r_hi"] = (None if x["r_raw"] is None else x["r_raw"] * f["r"](lo)), (None if x["r_raw"] is None else x["r_raw"] * f["r"](hi))
            d["u_lo"], d["u_hi"] = (None if x["u_raw"] is None else x["u_raw"] * f["u"](lo)), (None if x["u_raw"] is None else x["u_raw"] * f["u"](hi))
        out.append(d)
    mu, _, _ = bg.lognormal_fit()                                                    # Belin's Fig. 6: the lognormal of x = Re_f / Re_lambda^(1/2), median exp(mu)
    rb = [d for d in out if d["src"] == "Belin96"][0]["r_raw"]                        # Belin's r_max / eta of the table (7.608)
    rl = np.exp(np.linspace(math.log(151), math.log(718), 30))
    belin = dict(re=rl, r_raw=np.full(len(rl), rb), u_raw=1.585 * math.exp(mu) * np.sqrt(rl) / rb)    # U_max / U_eta = 1.585 x Re_lambda^(1/2) / r_max (Re_f = U_max R / nu, R = r_max / 1.585, nu = eta U_eta)
    belin["r_cor"] = belin["r_raw"] * np.array([mult["Belin"][0](x) for x in rl])
    belin["u_cor"] = belin["u_raw"] * np.array([mult["Belin"][1](x) for x in rl])
    sources = sorted({d["src"] for d in out})
    OUTLIER_IDS = (67,)                                                              # the last row of Sassa and Makita (2005), Re_lambda 2391
    fits = fit_trends(out, exclude_ids=OUTLIER_IDS)                                 # all the dots but the last one of Sassa and Makita
    fits["without_Mouri09"] = fit_trends(out, exclude=("Mouri09",), exclude_ids=OUTLIER_IDS)
    fits["without_left_out"] = fit_trends(out, exclude=("Mouri03", "Mouri04", "Mouri07", "DaSilva11", "Sassa05", "Ishihara13"))      # the rows that the selection of the paper leaves out of the swirl fit
    cmap = plt.get_cmap("tab20")
    colour = {s: cmap(i % 20) for i, s in enumerate(sources)}
    colour["Mouri09"] = "0.55"                                                      # grey, as the fit with Mouri and Hori 2009
    marks = "osD^v<>pPhXd*o"
    marker = {s: marks[i % len(marks)] for i, s in enumerate(sources)}
    observed = lambda d: not d["method"].startswith("DNS")
    fig, ax = plt.subplots(2, 3, figsize=(17, 10))
    for row in (0, 1):
        for d in out:
            if d["lo"] is None:
                continue
            show_corr = row == 1 and d["corrected"] and (observed(d) or d["src"].startswith("Ghira"))
            r_a, r_b = (d["r_lo"], d["r_hi"]) if show_corr else (d["r_raw"], d["r_raw"])
            u_a, u_b = (d["u_lo"], d["u_hi"]) if show_corr else (d["u_raw"], d["u_raw"])
            if row == 1 and observed(d) and not d["corrected"]:
                pass                                                              # observed, no multiplier yet: shown as read, open symbol
            g_a = G0 * r_a * u_a if r_a is not None and u_a is not None else None
            g_b = G0 * r_b * u_b if r_b is not None and u_b is not None else None
            if g_a is None and d["gamma_listed"] and r_a is not None and u_a is None:      # no swirl in the source: its listed Gamma / nu
                g_a = g_b = d["gamma_listed"]
            for col, (va, vb) in enumerate(((r_a, r_b), (u_a, u_b), (g_a, g_b))):
                if va is None:
                    continue
                a = ax[row, col]
                open_symbol = row == 1 and observed(d) and not d["corrected"]
                kw = dict(color=colour[d["src"]], marker=marker[d["src"]], ms=6, mfc="none" if open_symbol else colour[d["src"]], ls="")
                if d["lo"] == d["hi"]:
                    a.plot([d["lo"]], [va], **kw)
                else:
                    a.plot([d["lo"], d["hi"]], [va, vb], color=colour[d["src"]], lw=2.5, alpha=0.7)
    for row in (0, 1):
        r_b, u_b = (belin["r_raw"], belin["u_raw"]) if row == 0 else (belin["r_cor"], belin["u_cor"])
        ax[row, 1].plot(rl, u_b, color=colour["Belin96"], lw=2.5, alpha=0.7)
        ax[row, 2].plot(rl, G0 * r_b * u_b, color=colour["Belin96"], lw=2.5, alpha=0.7)
    re_line = np.exp(np.linspace(math.log(30), math.log(2000), 100)) if False else np.linspace(30, 2000, 200)
    lines = {}                                                                       # (straight line of r, U = a Re^0.5) of the fit with and without Mouri and Hori 2009
    for tag, f_ in (("with", fits), ("without", fits["without_Mouri09"])):
        fl_, fw_ = f_["r"]["models"]["straight line"], f_["U"]["models"]["power, exponent 1/2"]
        lines[tag] = (fl_, fw_, fl_["a"] + fl_["b"] * re_line, fw_["a"] * re_line ** 0.5, f_["r"]["n"], f_["U"]["n"])
    for tag, colr, z in (("with", "0.55", 4), ("without", "r", 5)):
        fl_, fw_, r_d, u_d = lines[tag][:4]
        ax[1, 0].plot(re_line, r_d, "--", color=colr, lw=1.8, zorder=z)
        ax[1, 1].plot(re_line, u_d, "--", color=colr, lw=1.8, zorder=z)
        ax[1, 2].plot(re_line, G0 * r_d * u_d, "--", color=colr, lw=1.8, zorder=z)
    for row in (0, 1):
        for col, label in enumerate(("r_max / eta", "U_max / U_eta", "G = Gamma / nu = 8.784 r_max U_max / nu")):
            a = ax[row, col]
            a.set_xlabel("Re_lambda")
            a.set_ylabel(label)
        ax[row, 0].set_title("every data point as read" if row == 0 else "Ghira (r x 1.25, U x 0.67) and observed data corrected; other DNS as read", fontsize=10)
    handles = [plt.Line2D([], [], color=colour[s], marker=marker[s], ls="", label=s) for s in sources]
    for tag, colr, txt in (("without", "r", "without Mouri-Hori 2009"), ("with", "0.55", "with Mouri-Hori 2009")):
        fl_, fw_, _, _, nr, nu = lines[tag]
        handles.append(plt.Line2D([], [], color=colr, lw=1.8, ls="--", label="%s: r = %.2f %+.4f Re (%d points); U = %.3f Re^0.5 (%d points)" % (txt, fl_["a"], fl_["b"], nr, fw_["a"], nu)))
    fig.legend(handles=handles, loc="lower center", ncol=6, fontsize=8)
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    fig.savefig(os.path.join(HERE, "data_corrected_plot.png"), dpi=90)
    with open(os.path.join(HERE, "data_corrected_fits.json"), "w", encoding="utf-8") as f:
        json.dump(fits, f, indent=1)
    with open(os.path.join(HERE, "data_G_derivation.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "src", "re_lo", "re_hi", "r_raw", "u_raw", "G_from_r_u", "gamma_listed", "route"])
        for d in out:
            both = d["r_raw"] is not None and d["u_raw"] is not None
            route = "r from the table row, U derived from Fig. 6 (not in the csv): G = 8.784 r U" if d["src"] == "Belin96" else "8.784 r U (both values)" if both else ("Gamma/nu as listed by the source (no U)" if d["gamma_listed"] else ("no G: r only" if d["r_raw"] is not None else "no G: U only"))
            w.writerow([d["id"], d["src"], d["lo"], d["hi"], d["r_raw"], d["u_raw"], "" if not both else "%.1f" % (G0 * d["r_raw"] * d["u_raw"]), d["gamma_listed"] or "", route])


if __name__ == "__main__":
    main()
