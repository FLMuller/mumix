"""belin_gamma_pdf.py  v01  The pdf of the circulation from Belin et al. (1996) Fig. 6.
Belin's variable x = Re_f / Re_lambda^(1/2), Re_f = U_max R / nu, R = r_max / 1.585 (the Gaussian width of the Burgers vortex).  With Gamma = 8.784 r_max U_max:
    Gamma / nu = 8.784 x 1.585 Re_f = 13.92 Re_f,   so   Gamma / (nu Re_lambda^(1/2)) = 13.92 x        and        Gamma / (u' eta) = 27.4 x   (isotropic: u' eta / nu = Re_lambda^(1/2) / 15^(1/4)).
The pdf of the digitised Fig. 6 (belin_fig6_digitised.csv, markers averaged in bins of 2.5 in x; binned(width) takes another width) is transformed:  p(g) = p_x(g / 13.92) / 13.92, g = Gamma / (nu Re_lambda^(1/2)).
Drawn for comparison: the circulation of Jimenez et al. (1993) Table 3 (the mean of Re_Gamma / Re_lambda^(1/2) of their worms, 16.5 to 21.1) and the best model of the page, Gamma/nu = 8.784 alpha beta
with alpha = 0.769 Re_lambda^(1/3), beta = 5, so g = 33.8 Re_lambda^(-1/6) (11.4 at Re_lambda 659, 15.7 at 100).  A lognormal is fitted to the binned pdf.
Usage: python belin_gamma_pdf.py     writes belin_gamma_pdf.png

Versions  M01 m01.v01 (2026-11-13): first version.
"""
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import least_squares

HERE = os.path.dirname(os.path.abspath(__file__))
K = 8.784 * 1.585                                         # Gamma / nu = K Re_f = 13.92 Re_f


def binned(width=2.5):
    xs, ps = [], []
    with open(os.path.join(HERE, "belin_fig6_digitised.csv"), newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            x = float(r["Re_f_over_sqrt_Re_lambda"])
            if 0.0 <= x <= 41:
                xs.append(x)
                ps.append(float(r["p"]))
    xs, ps = np.array(xs), np.array(ps)
    edges = np.arange(0, 40.0 + 1.1 * width, width)
    c, m = [], []
    for a, b in zip(edges[:-1], edges[1:]):
        sel = (xs >= a) & (xs < b)
        if sel.any():
            c.append(0.5 * (a + b))
            m.append(ps[sel].mean())
    c, m = np.array(c), np.array(m)
    return c, m / (np.trapezoid(m, c))                    # area 1 over 0 ... 40


def raw_points():
    """The digitised markers of Fig. 6: arrays x and p (belin_fig6_digitised.csv), 0 <= x <= 41."""
    xs, ps = [], []
    with open(os.path.join(HERE, "belin_fig6_digitised.csv"), newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            x = float(r["Re_f_over_sqrt_Re_lambda"])
            if 0.0 <= x <= 41:
                xs.append(x)
                ps.append(float(r["p"]))
    return np.array(xs), np.array(ps)


def lognormal_x(x, mu, s):
    """Unit-area lognormal in x (mu = ln median, s = width of ln x)."""
    return np.exp(-0.5 * ((np.log(x) - mu) / s) ** 2) / (x * s * np.sqrt(2 * np.pi))


def lognormal_fit():
    """(mu, s, rms residual) of the unit-area lognormal fitted by least squares to all the digitised markers of Fig. 6 (x > 0.3)."""
    xs, ps = raw_points()
    ok = xs > 0.3
    fit = least_squares(lambda v: lognormal_x(xs[ok], v[0], v[1]) - ps[ok], [np.log(9.0), 0.8])
    return fit.x[0], fit.x[1], float(np.sqrt(np.mean(fit.fun ** 2)))


def main():
    cx, px = binned()
    g, pg = K * cx, px / K
    mean = np.trapezoid(g * pg, g)
    cdf = np.cumsum(pg) / pg.sum()
    median = np.interp(0.5, cdf, g)
    mode = g[np.argmax(pg)]

    def lognormal(v, grid):
        mu, s = v
        return np.exp(-0.5 * ((np.log(grid) - mu) / s) ** 2) / (grid * s * np.sqrt(2 * np.pi))
    ok = g > 0
    fit = least_squares(lambda v: lognormal(v, g[ok]) - pg[ok], [np.log(100.0), 0.8])
    mu, s = fit.x
    grid = np.linspace(2, 560, 400)
    fig, ax = plt.subplots(figsize=(9.5, 5.8))
    ax.plot(g, pg, "ko", ms=6, label="Belin Fig. 6, digitised, binned (mean %.0f, median %.0f, mode %.0f)" % (mean, median, mode))
    ax.plot(grid, lognormal(fit.x, grid), "k-", lw=1.5, label="lognormal: median %.0f, ln-width %.2f" % (np.exp(mu), s))
    ax.axvspan(16.5, 21.1, color="tab:blue", alpha=0.25, label="Jimenez et al. (1993) Table 3: mean 16.5-21.1 (DNS, Re_lambda 36-170)")
    ax.axvline(33.8 * 659 ** (-1 / 6), color="tab:red", lw=2, label="best model, Re_lambda 659: 11.4")
    ax.axvline(33.8 * 100 ** (-1 / 6), color="tab:red", lw=2, ls="--", label="best model, Re_lambda 100: 15.7")
    top = ax.secondary_xaxis("top", functions=(lambda v: v * 15 ** 0.25, lambda v: v / 15 ** 0.25))
    top.set_xlabel("Gamma / (u' eta) = 1.968 x Gamma / (nu Re_lambda^(1/2))")
    ax.set_xlabel("Gamma / (nu Re_lambda^(1/2)) = 13.92 x")
    ax.set_ylabel("pdf")
    ax.set_xlim(0, 560)
    ax.set_title("pdf of the circulation of the worms of Belin et al. (1996), from his Fig. 6", fontsize=10, pad=34)
    ax.legend(fontsize=7.5)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_gamma_pdf.png"), dpi=110)
    print("Gamma/(nu sqrt Re_lambda): mean %.0f, median %.0f, mode %.0f; lognormal median %.0f, s %.2f" % (mean, median, mode, np.exp(mu), s))
    print("same in Gamma/(u' eta): mean %.0f, median %.0f, mode %.0f" % (mean * 15 ** 0.25, median * 15 ** 0.25, mode * 15 ** 0.25))


if __name__ == "__main__":
    main()
