"""fit_das2006_open.py  v01  Two-lognormal fits to the pdfs of the open symbols of Das et al. (2006), Fig. 7 (the bands 110 < y+ < 180, away from the wall):
reads das2006_open_pdfs.csv (plot_das2006_open_pdf.py), scales P to a total area of 1 (the range plus the rise below the first point and the tail beyond the last one, as check_das_area.py),
and fits a sum of two lognormals (fit_tanahashi_lognormal.fit_mixture: mu2 >= mu1, start a1 = 0.7; the diameter with sigma2 >= SRATIO sigma1; the swirl without a width constraint; settings
at the top of main()).  The diameter tail above D* = 18 is a straight line in ln p through the points marked by hand on the figure (TAIL_FROM, TAIL_A, TAIL_K).  Writes das2006_open_pdfs.png.   Usage: python fit_das2006_open.py
"""
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import fit_tanahashi_lognormal as fl

HERE = os.path.dirname(os.path.abspath(__file__))
# the tail of the diameter pdf above D* = TAIL_FROM is a straight line in ln p (an exponential), fitted to eight points that were marked by hand on the original figure
# (das2006_fig7a_orange.png: p = 0.1053 exp(-0.0682 D*), rms 0.057 in ln p); below it the digitised open symbols are used
TAIL_FROM = 18.0
TAIL_LINE = os.environ.get("DAS_TAIL_LINE", "1") == "1"     # False: use the digitised open symbols over the whole range (no straight-line tail)
TAIL_A, TAIL_K = 0.1053, -0.0682


def main():
    d = np.genfromtxt(os.path.join(HERE, "das2006_open_pdfs.csv"), delimiter=",", names=True)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for col, (k, cx, ct, cb, cp, name, unit, xmin, lin_max, floor) in enumerate((
            ("D", "D_star", "pD_top", "pD_bottom", "pD", r"$D^*$ (diameter, in $\eta$), open symbols", r"$D^*$", 3.0, 60, 1e-3),
            ("u", "u_star", "pv_top", "pv_bottom", "pv", r"$u^*_{\theta,max}$ (in $u'_{rms}$), open symbols", r"$u^*_{\theta,max}$", 0.0, 3.0, 1e-2))):
        x, top, bot, p = (d[c] for c in (cx, ct, cb, cp))
        ok = np.isfinite(x) & (x >= xmin)
        x, top, bot, p = x[ok], top[ok], bot[ok], p[ok]
        if k == "D" and TAIL_LINE:                           # digitised points below TAIL_FROM, the straight line from there to D* = 80
            low = x < TAIL_FROM
            xt = np.arange(TAIL_FROM, 80.01, 1.0)
            pt = TAIL_A * np.exp(TAIL_K * xt)
            x = np.r_[x[low], xt]
            p = np.r_[p[low], pt]
            top = np.r_[top[low], pt]
            bot = np.r_[bot[low], pt]
        area = np.trapezoid(p, x)
        left = 0.5 * p[0] * (x[0] - (2.0 if k == "D" else 0.0))
        slope = -np.polyfit(x[-8:], np.log(p[-8:]), 1)[0] if not (k == "D" and TAIL_LINE) else -TAIL_K
        right = p[-1] / slope if slope > 0 else 0.0
        total = area + left + right
        top, bot, p = top / total, bot / total, p / total
        fl.AREA_MATCH = False
        fl.SRATIO = 2.0 if k == "D" else 0.0
        fl.A_FIXED = None
        fl.S1_FIXED = None
        fl.MU1_FIXED = None
        fl.ORDER = "median"
        mix = fl.fit_mixture(x, top, bot, p, 0.7 if k == "D" else 3.0, "lin")
        xs = np.exp(np.linspace(np.log(x.min()), np.log(x.max()), 600))
        c1, c2 = mix[0] * fl.lognormal(xs, mix[1], mix[2]), (1 - mix[0]) * fl.lognormal(xs, mix[3], mix[4])
        cum = np.cumsum(np.r_[0, 0.5 * (p[1:] + p[:-1]) * np.diff(x)])
        qf = lambda f: x[np.searchsorted(cum, f * cum[-1])]
        print("%s: area of the digitised pdf %.3f, with the rise %.3f and the tail %.3f: total %.3f; mode %.3g median %.3g mean %.3g 10-90%% %.3g-%.3g" % (
            k, area, left, right, total, x[np.argmax(p)], qf(0.5), np.trapezoid(p * x, x) / cum[-1], qf(0.1), qf(0.9)))
        v1, v2 = np.trapezoid(c1 * xs ** 2, xs), np.trapezoid(c2 * xs ** 2, xs)
        print("   two lognormals: weights %.2f %.2f; medians %.3g %.3g; s %.2f %.2f; by %s^2 %.2f %.2f; rms residual %.3f of the peak; integrals over the range: P %.3f, fit %.3f" % (
            mix[0], 1 - mix[0], np.exp(mix[1]), np.exp(mix[3]), mix[2], mix[4], k, v1 / (v1 + v2), v2 / (v1 + v2),
            np.sqrt(np.mean((fl.mixture(x, mix) - p) ** 2)) / p.max(), np.trapezoid(p, x), np.trapezoid(fl.mixture(x, mix), x)))
        for row, logy in enumerate((False, True)):
            a = axes[row][col]
            a.fill_between(x, bot, top, color="0.85")
            a.plot(xs, c1, c="tab:blue", lw=1.0, ls=":", label="component 1: weight %.2f, median %.3g, s = %.2f" % (mix[0], np.exp(mix[1]), mix[2]))
            a.plot(xs, c2, c="tab:orange", lw=1.0, ls=":", label="component 2: weight %.2f, median %.3g, s = %.2f" % (1 - mix[0], np.exp(mix[3]), mix[4]))
            a.plot(xs, c1 + c2, c="tab:red", lw=1.8, label="two lognormals")
            a.plot(x, p, c="k", lw=1.2, label="digitised P (open symbols; D* > 18: straight line), total area 1")
            a.set_xlim(0, lin_max if not logy else (80 if k == "D" else 3.0))
            if logy:
                a.set_yscale("log")
                a.set_ylim(floor, None)
            a.set_xlabel(unit)
            a.set_ylabel("pdf" + (" (log)" if logy else ""))
            a.grid(alpha=0.25, which="both")
            a.legend(fontsize=7.5)
            if row == 0:
                a.set_title(name, fontsize=10)
    fig.suptitle("Das et al. (2006) Fig. 7, open symbols (110 < y+ < 180): fit with two lognormals", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "das2006_open_pdfs.png"), dpi=110)


if __name__ == "__main__":
    main()
