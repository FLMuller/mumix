"""belin_rumax_table1.py  v01  r_max U_max / (u' eta) from Belin et al. (1996) Fig. 6, with u' eta calculated from the correlation of Table I instead of the isotropic formula.
Step 1  u' eta / nu against Re_lambda from the 8 runs of Table I (belin_table1.csv, misprints corrected): power law  u' eta / nu = a Re_lambda^b, fitted in log-log (isotropic turbulence: 0.508 Re_lambda^(1/2)).
Step 2  Re_f = x Re_lambda^(1/2) (x of Fig. 6), Re_c = r_max U_max / nu = 1.585 Re_f, hence  r_max U_max / (u' eta) = Re_c / (u' eta / nu) = 1.585 x Re_lambda^(1/2) / (a Re_lambda^b),
        drawn for Re_lambda = 255, 659 and 2313 (the range of Fig. 6).  Our data: r_max/eta * U_max/u' of the corrected rows of tubes.csv, with u'/U_eta from the same correlation.
Usage: python belin_rumax_table1.py     writes belin_rumax_table1.png

Versions  M01 m01.v01 (2026-11-13): first version.
"""
import csv
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FIT = os.path.join(HERE, "..", "fittingtool")
sys.path.insert(0, FIT)
sys.path.insert(0, HERE)
import fitdata           # noqa: E402
import belin_gamma_pdf   # noqa: E402


def main():
    with open(os.path.join(HERE, "belin_table1.csv"), newline="", encoding="utf-8") as f:
        t1 = list(csv.DictReader(f))
    nu, up, eta, Rl = (np.array([float(r[k]) for r in t1]) for k in ("nu_cm2_s", "u_prime_cm_s", "eta_um", "Re_lambda_used"))
    ratio = up * eta * 1e-4 / nu                                                 # u' eta / nu
    (b, ln_a) = np.polyfit(np.log(Rl), np.log(ratio), 1)
    a = math.exp(ln_a)
    iso = 15 ** -0.25
    print("u' eta / nu = %.3f Re_lambda^%.3f  (isotropic: %.3f Re_lambda^0.5)" % (a, b, iso))
    for re in (255, 659, 2313):
        print("  Re_lambda %5d: fit %.1f, isotropic %.1f" % (re, a * re ** b, iso * re ** 0.5))
    cx, px = belin_gamma_pdf.binned()
    fig, ax = plt.subplots(1, 2, figsize=(14, 5.6))
    grid = np.logspace(2, 3.8, 50)
    ax[0].loglog(Rl, ratio, "o", ms=9, color="tab:blue", label="Table I runs")
    ax[0].loglog(grid, a * grid ** b, "b-", label="fit: %.3f Re_lambda^%.2f" % (a, b))
    ax[0].loglog(grid, iso * grid ** 0.5, "k--", label="isotropic: 0.508 Re_lambda^0.5")
    ax[0].set_xlabel("Re_lambda (Table I, corrected)")
    ax[0].set_ylabel("u' eta / nu")
    ax[0].legend(fontsize=8)
    rows = fitdata.load(os.path.join(FIT, "data", "tubes.csv"), os.path.join(FIT, "data", "corrections.json"))
    colours = {255: "tab:blue", 659: "tab:green", 2313: "tab:red"}
    for re, colour in colours.items():
        scale = 1.585 * re ** 0.5 / (a * re ** b)                                # r_max U_max / (u' eta) = scale x
        y, py = scale * cx, px / scale
        cdf = np.cumsum(py) / py.sum()
        ax[1].plot(y, py, "o-", color=colour, ms=5, lw=1, label="Re_lambda %d (median %.0f, mean %.0f)" % (re, np.interp(0.5, cdf, y), np.trapezoid(y * py, y)))
        print("Re_lambda %d: scale %.2f; r_max U_max/(u' eta): median %.1f, mean %.1f" % (re, scale, np.interp(0.5, cdf, y), np.trapezoid(y * py, y)))
    rowsd = [(x["re"], x["r"], x["u"]) for x in rows if x["re"] is not None and x["r"] is not None and x["u"] is not None]
    yd = np.array([r * u / (a * re ** b) for re, r, u in rowsd])                  # r_max U_max / (u' eta) = (r_max U_max / nu) / (u' eta / nu)
    lo, hi = np.percentile(yd, [10, 90])
    ax[1].axvspan(lo, hi, color="gray", alpha=0.3, label="our tube data, corrected: 10-90 %% range %.1f-%.1f, median %.1f (n = %d)" % (lo, hi, np.median(yd), len(yd)))
    ax[1].set_xlabel("r_max U_max / (u' eta)")
    ax[1].set_ylabel("pdf")
    ax[1].set_xlim(0, 150)
    ax[1].legend(fontsize=7.5)
    ax[1].set_title("pdf of r_max U_max/(u' eta) from Belin's Fig. 6", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_rumax_table1.png"), dpi=110)
    print("our data: median %.2f, 10-90%% %.2f-%.2f" % (np.median(yd), lo, hi))


if __name__ == "__main__":
    main()
