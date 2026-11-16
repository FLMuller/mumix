"""belin_rumax_physical.py  v01  The pdf of r_max U_max from Belin et al. (1996) Fig. 6 for each Re_lambda of his curves, with nu, eps, eta, u' from the three correlations of Table I (cell 2).
Chain for a given Re (belin_table1_*.py): nu = 280 Re^-0.865 cm^2/s;  Omega = Re nu / R^2, N = Omega / 2 pi (R = 10 cm);  eps = Po N^3 D^5 / V (Po = 0.2697, D = 20 cm, V = 4115 cm^3);
eta = (nu^3 / eps)^(1/4);  u' = (eps L)^(1/3), L = 5.738 cm;  lambda = u' (15 nu / eps)^(1/2);  Re_lambda = u' lambda / nu = (15 u' L / nu)^(1/2).
The chain is inverted numerically: the Re that gives each Re_lambda of Fig. 6 (255, 359, 507, 718, 940, 1342, 2313).
Then Re_f = x Re_lambda^(1/2) (x of Fig. 6), Re_c = r_max U_max / nu = 1.585 Re_f (Gamma = 8.784 r_max U_max, r_max = 1.585 R) and  r_max U_max = Re_c nu  (cm^2/s).
Left: pdf of Re_c = r_max U_max / nu (the same quantity in Kolmogorov units, alpha beta); right: pdf of r_max U_max in cm^2/s.  Dashed: the best model of the page, alpha beta = 0.769 Re_lambda^(1/3) x 5.
Usage: python belin_rumax_physical.py     writes belin_rumax_physical.png

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
import belin_gamma_pdf   # noqa: E402

R, H, PO, L = 10.0, 13.1, 0.2697, 5.738
D, V = 2 * R, math.pi * R * R * H


def chain(Re):
    nu = 280 * Re ** -0.865
    omega = Re * nu / R ** 2
    N = omega / (2 * math.pi)
    eps = PO * N ** 3 * D ** 5 / V
    eta = (nu ** 3 / eps) ** 0.25
    up = (eps * L) ** (1 / 3)
    lam = up * math.sqrt(15 * nu / eps)
    return dict(Re=Re, nu=nu, eps=eps, eta=eta, U_eta=nu / eta, up=up, lam=lam, Re_lambda=up * lam / nu, N=N)


def main():
    cx, px = belin_gamma_pdf.binned()
    fig, ax = plt.subplots(1, 2, figsize=(14, 5.8))
    colours = plt.cm.viridis(np.linspace(0, 0.9, 7))
    for Rl, colour in zip((255, 359, 507, 718, 940, 1342, 2313), colours):
        Re = brentq(lambda r: chain(math.exp(r))["Re_lambda"] - Rl, math.log(1e3), math.log(1e9))
        c = chain(math.exp(Re))
        a_c = 1.585 * math.sqrt(Rl)                              # Re_c = a_c x
        y_c, p_c = a_c * cx, px / a_c
        y_p, p_p = y_c * c["nu"], p_c / c["nu"]
        cdf = np.cumsum(p_p) / p_p.sum()
        ax[0].plot(y_c, p_c, "o-", ms=3, lw=1.2, color=colour, label="Re_lambda %d" % Rl)
        ax[1].plot(y_p, p_p, "o-", ms=3, lw=1.2, color=colour, label="Re_lambda %d (Re %.2g, nu %.2g cm2/s, eta %.1f um, u' %.0f cm/s)" % (Rl, c["Re"], c["nu"], c["eta"] * 1e4, c["up"]))
        ax[0].axvline(0.769 * Rl ** (1 / 3) * 5, color=colour, ls="--", lw=1)
        print("Re_lambda %4d: Re %.3g, nu %.3g, eps %.3g, eta %.2f um, U_eta %.3f cm/s, u' %.1f cm/s, u'/U_eta %.1f, lambda %.0f um | Re_c median %.0f (model %.0f); r_max U_max median %.3g cm2/s"
              % (Rl, c["Re"], c["nu"], c["eps"], c["eta"] * 1e4, c["U_eta"], c["up"], c["up"] / c["U_eta"], c["lam"] * 1e4, np.interp(0.5, cdf, y_c), 0.769 * Rl ** (1 / 3) * 5, np.interp(0.5, cdf, y_p)))
    ax[0].set_xlabel("Re_c = r_max U_max / nu")
    ax[1].set_xlabel("r_max U_max  (cm^2/s)")
    ax[0].set_xlim(0, 2500)
    ax[1].set_xscale("log")
    ax[1].set_xlim(0.02, 30)
    for a in ax:
        a.set_ylabel("pdf")
        a.legend(fontsize=6.5)
    ax[0].set_title("pdf of r_max U_max / nu (dashed: our model, one per Re_lambda)", fontsize=10)
    ax[1].set_title("pdf of r_max U_max in cm^2/s, nu from the correlations (cell 2)", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_rumax_physical.png"), dpi=110)


if __name__ == "__main__":
    main()
