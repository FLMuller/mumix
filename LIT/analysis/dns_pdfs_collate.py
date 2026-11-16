"""dns_pdfs_collate.py  v02  Every digitised radius pdf and swirl pdf of the DNS (and scanning-PIV) papers: the integral of each curve and its statistics in one table (dns_pdfs_table.md, .html, .csv), and all curves on linear axes (dns_pdfs_radius.png, dns_pdfs_swirl.png).
Radius   r = r_max / eta as the paper defines it: D/2 (Tanahashi 2001 and 2004, Das 2006, Wang 2007), r0 (Pirozzoli 2012), R_ivs (Ghira 2022, seven Re_lambda), R (Jimenez and Wray 1998), R* = R/eta (Aligolzadeh 2023, experiment and DNS, histograms).
Swirl    maximum azimuthal velocity in u_K (Tanahashi 2004, Pirozzoli 2012, Wang 2007, and Tanahashi 2001 converted with u'/u_K = (Re_lambda / sqrt 15)^(1/2) at Re_lambda 80) and in the rms velocity u' (Tanahashi 2001, Das 2006, Jimenez and Wray 1998, u0/u').
Integral the area of the curve as digitised (trapezoid rule over the range digitised; the bar sum for the histograms) is the check that the axes are right (1 for a pdf).  Every curve is then scaled to unit area, the four older ones with the rise below their first point and the tail beyond the last (summary_pdfs.normalise; Das: the straight-line tail of
         summary_pdfs), and mode, median, mean and the 10 and 90 % points are taken from it.  r_max (page): the mean radius times the conversion of the page to the radius of maximum swirl: 1.12 for the 1/e radii of the vorticity (Ghira R_ivs, Jimenez R), 1 for D/2 and r0, and none for Aligolzadeh (the R of the structure boundary).
Not drawn Ghira 2025 Fig. 15a (R_ivs/R_B, the variable of Ghira 2022 Fig. 5b) and Das 2006 Fig. 9 (the circulation pdf).
Usage    python dns_pdfs_collate.py
Versions M01 m01.v02 (2026-11-15): the integral and the table added, linear axes only.   m01.v01: first version (linear and logarithmic panels).
"""
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import summary_pdfs as sp

HERE = os.path.dirname(os.path.abspath(__file__))
RE_TAN01 = 80.0                                                                    # Re_lambda of the Tanahashi (2001) mixing layer (reviewed from his Fig. 1b)
UK_OVER_URMS = math.sqrt(math.sqrt(15.0 / RE_TAN01 ** 2))                          # u_K / u' = (15 / Re_lambda^2)^(1/4)
G_BURGERS = 1.12                                                                   # r_max = 1.12 R for the 1/e radius R of a Gaussian vorticity


def col(csv, *names):
    d = np.genfromtxt(os.path.join(HERE, csv), delimiter=",", names=True)
    return [d[n] for n in names]


def curve(label, x, p, colour, ls, lw, area, rfac=None, legend=True, rng=None):
    return dict(label=label, x=x, p=p, c=colour, ls=ls, lw=lw, area=area, rfac=rfac, legend=legend, range=rng if rng else (float(np.min(x)), float(np.max(x))))


def unit(x, p):
    o = np.argsort(x)
    x, p = x[o], p[o]
    area = float(np.trapezoid(p, x))
    return x, p / area, area


def stats(x, p):
    c = np.r_[0, np.cumsum(0.5 * (p[1:] + p[:-1]) * np.diff(x))]
    q = lambda f: float(np.interp(f * c[-1], c, x))
    return dict(mode=float(x[np.argmax(p)]), median=q(0.5), mean=float(np.trapezoid(x * p, x) / c[-1]), q10=q(0.1), q90=q(0.9))


def radius_curves():
    out = []
    for label, csv, xc, pc, xmin, rise, fac, c in sp.SIZE:
        x, p = sp.load(csv, xc, pc, xmin)
        raw_area, rng = float(np.trapezoid(p, x)), (float(x.min() * fac), float(x.max() * fac))
        if csv.startswith("das2006"):
            low = x < sp.TAIL_FROM
            xt = np.arange(sp.TAIL_FROM, 80.01, 1.0)
            x, p = np.r_[x[low], xt], np.r_[p[low], sp.TAIL_A * np.exp(sp.TAIL_K * xt)]
            p, _ = sp.normalise(x, p, rise, (sp.TAIL_A, sp.TAIL_K))
        else:
            p, _ = sp.normalise(x, p, rise)
        out.append(curve(label.replace(", mixing layer", " (mixing layer)"), x * fac, p / fac, c, "-", 2.0, raw_area, 1.0, rng=rng))
    x, p = col("wang2007_pdfs_diameter.csv", "x", "p_mid")
    x, p, a = unit(x / 2, 2 * p)
    out.append(curve("Wang 2007, mixing layer", x, p, "tab:purple", "-", 2.0, a, 1.0))
    d = np.genfromtxt(os.path.join(HERE, "ghira2022_fig5a_pdfs.csv"), delimiter=",", names=True)
    for k, re in enumerate(sorted(set(d["Re_lambda"]))):
        s = d["Re_lambda"] == re
        x, p, a = unit(d["x"][s], d["p"][s])
        out.append(curve("Ghira 2022, Re_lambda %d" % re, x, p, "tab:brown", "-", 0.9, a, G_BURGERS, legend=(k == 0)))
    x, p = col("jimenez1998_pdfs_radius.csv", "x", "p_mid")
    x, p, a = unit(x, p)
    out.append(curve("Jimenez and Wray 1998, worms", x, p, "tab:gray", "-", 2.0, a, G_BURGERS))
    d = np.genfromtxt(os.path.join(HERE, "aligolzadeh2023_fig4_pdfs.csv"), delimiter=",", names=True, dtype=None, encoding="utf-8")
    for name, label, c in (("a", "Aligolzadeh 2023, PIV experiment", "tab:olive"), ("b", "Aligolzadeh 2023, DNS sets", "tab:cyan")):
        s = d["panel"] == name
        w = d["width"][s]
        a = float(np.sum(d["p"][s] * w))                                           # the bar sum is the integral of the histogram
        x, p, _ = unit(d["x_centre"][s], d["p"][s])
        out.append(curve(label, x, p, c, "--", 1.6, a, None))
    return out


def swirl_curves():
    uk, urms = [], []
    for label, csv, xc, pc, xmin, rise, c in sp.SWIRL_UK:
        x, p = sp.load(csv, xc, pc, xmin)
        raw_area = float(np.trapezoid(p, x))
        p, _ = sp.normalise(x, p, rise)
        uk.append(curve(label.replace(", channel Re_tau 800", " (channel)"), x, p, c, "-", 2.0, raw_area))
    x, p = col("wang2007_pdfs_swirl.csv", "x", "p_mid")
    x, p, a = unit(x, p)
    uk.append(curve("Wang 2007, mixing layer", x, p, "tab:purple", "-", 2.0, a))
    for label, csv, xc, pc, xmin, rise, c in sp.SWIRL_URMS:
        x, p = sp.load(csv, xc, pc, xmin)
        raw_area = float(np.trapezoid(p, x))
        p, _ = sp.normalise(x, p, rise)
        lab = label.replace(", channel Re_tau 180, open symbols", " (channel)").replace(", mixing layer", " (mixing layer)")
        urms.append(curve(lab, x, p, c, "-", 2.0, raw_area))
        if csv.startswith("tanahashi2001"):                                            # to u_K: x(u_K) = x(u') / (u_K / u'), p scaled by the inverse
            uk.append(curve(lab + ", Re_lambda 80 assumed", x / UK_OVER_URMS, p * UK_OVER_URMS, c, ":", 1.8, raw_area))
    x, p = col("jimenez1998_pdfs_swirl.csv", "x", "p_mid")
    x, p, a = unit(x, p)
    urms.append(curve("Jimenez and Wray 1998, worms", x, p, "tab:gray", "-", 2.0, a))
    return uk, urms


def draw(ax, curves, xlabel, xmax):
    for cv in curves:
        ax.plot(cv["x"], cv["p"], color=cv["c"], ls=cv["ls"], lw=cv["lw"], label=("Ghira 2022, R_ivs, seven Re_lambda 90-399" if cv["label"].startswith("Ghira") else cv["label"]) if cv["legend"] else None)
    ax.set_xlim(0, xmax)
    ax.set_ylim(bottom=0)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("pdf, unit area")
    ax.legend(fontsize=8)


def main():
    rc = radius_curves()
    uk, urms = swirl_curves()
    fig, ax = plt.subplots(figsize=(10, 6))
    draw(ax, rc, "r_max / eta  (as the paper defines the radius)", 30)
    ax.set_title("Radius pdfs of the DNS and PIV papers, linear axes", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "dns_pdfs_radius.png"), dpi=90)
    fig, ax = plt.subplots(1, 2, figsize=(14, 5.5))
    draw(ax[0], uk, "maximum azimuthal velocity / u_K", 10)
    draw(ax[1], urms, "maximum azimuthal velocity / u' (rms velocity)", 3)
    fig.suptitle("Swirl pdfs of the DNS papers, linear axes: left in Kolmogorov velocity, right in rms velocity", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "dns_pdfs_swirl.png"), dpi=90)
    rows = []
    for quantity, curves in (("radius r/eta", rc), ("swirl / u_K", uk), ("swirl / u'", urms)):
        for cv in curves:
            s = stats(cv["x"], cv["p"])
            rm = None if cv.get("rfac") is None else cv["rfac"] * s["mean"]
            rows.append((cv["label"], quantity, cv["range"], cv["area"], s, rm))
    head = ["source", "quantity", "range digitised", "area as digitised", "mode", "median", "mean", "10 %", "90 %", "mean r_max (page)"]
    body = [[lab, q, "%.2g-%.3g" % rng, "%.3f" % a, "%.2f" % s["mode"], "%.2f" % s["median"], "%.2f" % s["mean"], "%.2f" % s["q10"], "%.2f" % s["q90"], "-" if rm is None else "%.2f" % rm] for lab, q, rng, a, s, rm in rows]
    with open(os.path.join(HERE, "dns_pdfs_table.md"), "w", encoding="utf-8") as f:
        f.write("| " + " | ".join(head) + " |\n|" + "---|" * len(head) + "\n")
        for r in body:
            f.write("| " + " | ".join(r) + " |\n")
    with open(os.path.join(HERE, "dns_pdfs_table.csv"), "w", encoding="utf-8") as f:
        f.write(",".join('"%s"' % h for h in head) + "\n")
        for r in body:
            f.write(",".join('"%s"' % v for v in r) + "\n")
    print("| " + " | ".join(head) + " |")
    for r in body:
        print("| " + " | ".join(r) + " |")


if __name__ == "__main__":
    main()
