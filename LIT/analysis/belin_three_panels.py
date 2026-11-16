"""belin_three_panels.py  v01  Belin et al. (1996) Fig. 6 in three steps, for Re_lambda = 255, 718 and 2313.
1  the original pdf of x = Re_f / Re_lambda^(1/2): all digitised markers and the lognormal fitted to them (belin_gamma_pdf.lognormal_fit)
2  the same transformed to r_max U_max (cm^2/s) = 1.585 x Re_lambda^(1/2) nu, nu from the Table I correlations of cell 2 (belin_rumax_physical.chain) at the Re that gives this Re_lambda
3  the same with r_max = 5 eta (eta from the chain): U_max (cm/s) = r_max U_max / (5 eta)
Lines: the lognormal, transformed;  dots: the digitised markers, transformed with the same factor.
Usage: python belin_three_panels.py     writes belin_three_panels.png

Versions  M01 m01.v01 (2026-11-13): first version.
"""
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import brentq

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import belin_gamma_pdf as bg        # noqa: E402
import belin_rumax_physical as brp  # noqa: E402

BETA = 5.0


def main():
    mu, s_ln, rms = bg.lognormal_fit()
    xs, ps = bg.raw_points()
    grid = np.linspace(0.05, 80, 1500)
    pdf = bg.lognormal_x(grid, mu, s_ln)
    fig, ax = plt.subplots(1, 3, figsize=(17, 5.4))
    ax[0].plot(xs, ps, "ko", ms=4, label="Belin Fig. 6, all digitised markers")
    ax[0].plot(grid, pdf, "r-", lw=2, label="lognormal: median %.1f, ln-width %.2f" % (np.exp(mu), s_ln))
    ax[0].set_xlim(0, 45)
    ax[0].set_xlabel("x = Re_f / Re_lambda^(1/2)")
    for Rl, colour in ((255, "tab:blue"), (718, "tab:green"), (2313, "tab:red")):
        Re = brentq(lambda r: brp.chain(math.exp(r))["Re_lambda"] - Rl, math.log(1e3), math.log(1e9))
        c = brp.chain(math.exp(Re))
        f_rumax = 1.585 * math.sqrt(Rl) * c["nu"]                         # r_max U_max (cm^2/s) = f_rumax x
        f_u = f_rumax / (BETA * c["eta"])                                  # U_max (cm/s) = f_u x
        for a, f, unit in ((ax[1], f_rumax, "cm^2/s"), (ax[2], f_u, "cm/s")):
            a.plot(f * grid, pdf / f, "-", lw=2, color=colour, label="Re_lambda %d (Re %.2g): median %.3g %s" % (Rl, c["Re"], f * np.exp(mu), unit))
            a.plot(f * xs, ps / f, "o", ms=3, color=colour, alpha=0.6)
    ax[1].set_xlabel("r_max U_max  (cm^2/s)")
    ax[1].set_xscale("log")
    ax[2].set_xlabel("U_max  (cm/s), r_max = 5 eta")
    for a in ax:
        a.set_ylabel("pdf")
        a.legend(fontsize=8)
    ax[0].set_title("1: Fig. 6 and its lognormal fit", fontsize=10)
    ax[1].set_title("2: transformed to r_max U_max", fontsize=10)
    ax[2].set_title("3: and to U_max with r_max = 5 eta", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_three_panels.png"), dpi=105)


if __name__ == "__main__":
    main()
