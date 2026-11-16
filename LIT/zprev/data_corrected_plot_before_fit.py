"""data_corrected_plot.py  v01  The tube data of the page as read, and with the model's multipliers applied to the observed (probe) data: r_max / eta, U_max / U_eta and G = Gamma / nu against Re_lambda.
Rows      top: every data point as read (fittingtool/data/tubes.csv, raw values); bottom: the DNS rows as read and the observed rows corrected with the multipliers of the Belin-fit tubes (belin_correctors*.json).
Columns   r_max / eta, U_max / U_eta, G = 8.784 r_max U_max / nu (from the two values of a row; a row without a swirl but with a listed Gamma / nu, Jimenez et al., shows the listed value; otherwise no G, see data_G_derivation.csv).
Multipliers (corrected = m x printed value; interpolated linearly in log Re_lambda, constant outside the Re_lambda range of the runs, 100-2000)
          Belin 1996: r of Belin's wire and U by his published rule (shape match, belin_correctors.json); his U is not a row of the table: it is derived from his Fig. 6, U_max / U_eta = 1.585 exp(mu) Re_lambda^(1/2) / r_max with the median exp(mu) of the lognormal fit of x and r_max = 7.608 eta of the table row;  Mouri et al. 2007 (0.1% and 1% classes, the class of a row is the one with the smaller r at the same Re_lambda: 0.1%) and 2004 (1% class): the Mouri class multipliers;
          Mouri and Hori 2009: all-tube average at 0.5 sigma (belin_correctors_all.json);  Sassa and Makita 2005: C = 2.5 (belin_correctors_sassa.json; below Re_lambda 100 the value at 100).
          Ghira et al. 2022 and 2025: radius x 1.25 and swirl x 0.67 (section 9a, from the all-tube population of Pirozzoli 2012).
          Not corrected (no multiplier yet): Mouri 2003 (a range only), Aligolzadeh 2023, the wall flows and the other DNS rows.
Usage     python data_corrected_plot.py     writes data_corrected_plot.png and data_G_derivation.csv
Versions  M01 m01.v03 (2026-11-15): linear axes (Re_lambda and G).
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
    t["Mouri09"] = (Table([(r["Re_lambda"], r["k=0.5"]["m_r"]) for r in a]), Table([(r["Re_lambda"], r["k=0.5"]["m_U"]) for r in a]))
    t["Ghira"] = (Table([(100, 1.25), (2000, 1.25)]), Table([(100, 0.67), (2000, 0.67)]))                              # the 1%-volume DNS to the whole population (section 9a): radius x 1.25, swirl x 0.67
    t["Sassa05"] = (Table([(r["Re_lambda"], r["C=2.5"]["m_r"]) for r in s]), Table([(r["Re_lambda"], r["C=2.5"]["m_U"]) for r in s]))
    return t


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
    cmap = plt.get_cmap("tab20")
    colour = {s: cmap(i % 20) for i, s in enumerate(sources)}
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
    for row in (0, 1):
        for col, label in enumerate(("r_max / eta", "U_max / U_eta", "G = Gamma / nu = 8.784 r_max U_max / nu")):
            a = ax[row, col]
            a.set_xlabel("Re_lambda")
            a.set_ylabel(label)
        ax[row, 0].set_title("every data point as read" if row == 0 else "Ghira (r x 1.25, U x 0.67) and observed data corrected; other DNS as read", fontsize=10)
    handles = [plt.Line2D([], [], color=colour[s], marker=marker[s], ls="", label=s) for s in sources]
    fig.legend(handles=handles, loc="lower center", ncol=8, fontsize=8)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(os.path.join(HERE, "data_corrected_plot.png"), dpi=90)
    with open(os.path.join(HERE, "data_G_derivation.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "src", "re_lo", "re_hi", "r_raw", "u_raw", "G_from_r_u", "gamma_listed", "route"])
        for d in out:
            both = d["r_raw"] is not None and d["u_raw"] is not None
            route = "r from the table row, U derived from Fig. 6 (not in the csv): G = 8.784 r U" if d["src"] == "Belin96" else "8.784 r U (both values)" if both else ("Gamma/nu as listed by the source (no U)" if d["gamma_listed"] else ("no G: r only" if d["r_raw"] is not None else "no G: U only"))
            w.writerow([d["id"], d["src"], d["lo"], d["hi"], d["r_raw"], d["u_raw"], "" if not both else "%.1f" % (G0 * d["r_raw"] * d["u_raw"]), d["gamma_listed"] or "", route])


if __name__ == "__main__":
    main()
