"""belin_swirl_pdf.py  v01  The pdf of U_max / u' from Belin et al. (1996): the pdf of x = Re_f / Re_lambda^(1/2) (Fig. 6) and the pdf of the radius R_m / eta (Fig. 5).
Relation (belin_table1 notes): x = Re_f / Re_lambda^(1/2) = 0.508 (U_max / u') (R / eta), R = R_m the Gaussian width of the Burgers vortex that Belin reads; so U_max / u' = x / (0.508 R_m / eta).
Both Belin pdfs are the apparent (measured) ones.  The joint of x and R_m is not given, so three assumptions bracket it (200000 draws each):
    A  x and R_m independent                              U / u' = x / (0.508 R_m)
    B  U / u' independent of R_m (swirl does not depend on size): lognormal deconvolution, ln(U/u') = ln x - ln 0.508 - ln R_m with var ln(U/u') = var ln x - var ln R_m
    C  x and R_m perfectly rank-correlated (the larger the worm, the larger Re_f)
Fig. 6: belin_fig6_digitised.csv (digitise_belin_fig6.py), averaged in bins of 2.5 in x (the markers of the different Re_lambda collapse); Fig. 5: belin_fig5_digitised.csv.
Usage: python belin_swirl_pdf.py     writes belin_swirl_pdf.png

Versions  M01 m01.v01 (2026-11-13): first version.
"""
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RNG = np.random.default_rng(11)
CONST = 15 ** -0.25                                    # 0.508


def fig6_pdf():
    xs, ps = [], []
    with open(os.path.join(HERE, "belin_fig6_digitised.csv"), newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            x = float(r["Re_f_over_sqrt_Re_lambda"])
            if 0.0 <= x <= 41:
                xs.append(x)
                ps.append(float(r["p"]))
    xs, ps = np.array(xs), np.array(ps)
    edges = np.arange(0, 42.6, 2.5)
    centre, mean = [], []
    for a, b in zip(edges[:-1], edges[1:]):
        sel = (xs >= a) & (xs < b)
        if sel.any():
            centre.append(0.5 * (a + b))
            mean.append(ps[sel].mean())
    return np.array(centre), np.array(mean)


def draw(centre, density, n):
    """n draws of a pdf given on a grid (inverse of the cumulative integral)."""
    grid = np.linspace(centre.min(), centre.max(), 800)
    p = np.interp(grid, centre, density)
    cdf = np.cumsum(p)
    cdf = cdf / cdf[-1]
    return np.interp(RNG.uniform(size=n), cdf, grid)


def main():
    cx, px = fig6_pdf()
    d5 = np.loadtxt(os.path.join(HERE, "belin_fig5_digitised.csv"), delimiter=",", skiprows=1)
    n = 200000
    x = draw(cx, px, n)
    r = np.maximum(draw(d5[:, 0], d5[:, 1], n), 0.5)
    case_a = x / (CONST * r)
    lx, lr = np.log(np.maximum(x, 0.2)), np.log(r)
    var_u = max(lx.var() - lr.var(), 1e-4)
    case_b = np.exp(lx.mean() - np.log(CONST) - lr.mean() + np.sqrt(var_u) * RNG.standard_normal(n))
    case_c = np.sort(x)[np.argsort(np.argsort(r))] / (CONST * r)
    fig, ax = plt.subplots(figsize=(9.5, 5.8))
    bins = np.linspace(0, 12, 121)
    for y, colour, label in ((case_a, "tab:blue", "A: x and R_m independent"), (case_b, "tab:green", "B: U/u' independent of R_m (lognormal deconvolution; sd of ln = %.2f)" % np.sqrt(var_u)),
                             (case_c, "tab:red", "C: x and R_m perfectly rank-correlated")):
        ax.hist(y, bins, density=True, histtype="step", lw=2, color=colour, label=label + "  (median %.2f, mean %.2f)" % (np.median(y), y.mean()))
        print("%-40s median %.2f  mean %.2f  10%%-90%% %.2f - %.2f" % (label[:40], np.median(y), y.mean(), np.percentile(y, 10), np.percentile(y, 90)))
    ax.axvspan(0.4, 0.8, color="gray", alpha=0.2, label="the tube data of the page (0.4-0.8 u')")
    ax.axvline(2.5, color="tab:purple", ls=":", lw=1.5, label="Jimenez and Wray bound 2.5 u'")
    ax.set_xlabel("U_max / u'")
    ax.set_ylabel("pdf")
    ax.set_xlim(0, 12)
    ax.set_title("Belin et al. (1996): pdf of U_max/u' from the pdfs of Re_f/Re_lambda^0.5 and of the radius", fontsize=10)
    ax.legend(fontsize=7.5)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_swirl_pdf.png"), dpi=110)
    print("x: median %.1f, R_m: median %.2f" % (np.median(x), np.median(r)))


if __name__ == "__main__":
    main()
