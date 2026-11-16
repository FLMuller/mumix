"""belin_umax_fixed_r.py  v01  The pdf of U_max from Belin et al. (1996) Fig. 6 with a constant r_max = 5 eta, for each Re_lambda of his curves.
Chain as belin_rumax_physical.py (the three correlations of Table I, cell 2, inverted to the Re of each Re_lambda): nu, eta, U_eta = nu / eta, u'.
r_max U_max / nu = Re_c = 1.585 x Re_lambda^(1/2)   ->   with r_max = BETA eta:   alpha = U_max / U_eta = Re_c / BETA,   U_max = alpha U_eta (cm/s),   U_max / u' = alpha / (u' / U_eta).
Panels: U_max in cm/s, alpha = U_max / U_eta, U_max / u'.  Dashed: the best model alpha = 0.769 Re_lambda^(1/3) (and its U_max/u'); dotted: Jimenez and Wray bound 2.5 u'.
Usage: python belin_umax_fixed_r.py [--beta 5]     writes belin_umax_fixed_r.png

Versions  M01 m01.v01 (2026-11-13): first version.
          m01.v03 (2026-11-13): the digitised markers are drawn too, transformed with the same scale as the lines.
          m01.v02 (2026-11-13): the pdf of x is the lognormal fitted to all the markers of Fig. 6 (default); --bin w uses bins of width w.
"""
import argparse
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
import belin_gamma_pdf    # noqa: E402
import belin_rumax_physical as brp   # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--beta", type=float, default=5.0)
    ap.add_argument("--bin", type=float, default=0.0, help="bin width in x of Fig. 6; 0: use the lognormal fitted to all the markers (belin_gamma_pdf.lognormal_fit)")
    args = ap.parse_args()
    beta = args.beta
    if args.bin > 0:
        cx, px = belin_gamma_pdf.binned(args.bin)
    else:
        mu, s_ln, rms = belin_gamma_pdf.lognormal_fit()
        cx = np.linspace(0.05, 200.0, 4000)
        px = belin_gamma_pdf.lognormal_x(cx, mu, s_ln)
        print("lognormal fit to Fig. 6: median %.2f, ln-width %.3f, rms residual %.4f" % (np.exp(mu), s_ln, rms))
    raw_x, raw_p = belin_gamma_pdf.raw_points()
    fig, ax = plt.subplots(1, 3, figsize=(18, 5.6))
    colours = plt.cm.viridis(np.linspace(0, 0.9, 7))
    for Rl, colour in zip((255, 359, 507, 718, 940, 1342, 2313), colours):
        Re = brentq(lambda r: brp.chain(math.exp(r))["Re_lambda"] - Rl, math.log(1e3), math.log(1e9))
        c = brp.chain(math.exp(Re))
        a_alpha = 1.585 * math.sqrt(Rl) / beta                       # alpha = a_alpha x
        ratio = c["up"] / c["U_eta"]                                  # u' / U_eta from the chain
        scales = ((c["U_eta"] * a_alpha, "U_max (cm/s)"), (a_alpha, "alpha"), (a_alpha / ratio, "U_max/u'"))
        for a, (s, _) in zip(ax, scales):
            a.plot(s * cx, px / s, "-", lw=1.6, color=colour, label="Re_lambda %d" % Rl)
            a.plot(s * raw_x, raw_p / s, "o", ms=2.5, color=colour, alpha=0.55)                 # the digitised markers, transformed with the same scale
        cdf = np.cumsum(px) / px.sum()
        xm = np.interp(0.5, cdf, cx)
        print("Re_lambda %4d: u'/U_eta %.1f, U_eta %.2f cm/s | median x %.1f -> alpha %.1f (model %.1f), U_max %.1f cm/s, U_max/u' %.2f (model %.2f)"
              % (Rl, ratio, c["U_eta"], xm, a_alpha * xm, 0.769 * Rl ** (1 / 3), c["U_eta"] * a_alpha * xm, a_alpha * xm / ratio, 0.769 * Rl ** (1 / 3) / ratio))
        ax[1].axvline(0.769 * Rl ** (1 / 3), color=colour, ls="--", lw=1)
        ax[2].axvline(0.769 * Rl ** (1 / 3) / ratio, color=colour, ls="--", lw=1)
    ax[2].axvline(2.5, color="tab:purple", ls=":", lw=1.5, label="Jimenez and Wray bound 2.5 u'")
    for a, xl in zip(ax, ("U_max (cm/s)", "alpha = U_max / U_eta", "U_max / u'")):
        a.set_xlabel(xl)
        a.set_ylabel("pdf")
        a.legend(fontsize=7)
    ax[0].set_xlim(0, 700)
    ax[1].set_xlim(0, 120)
    ax[2].set_xlim(0, 6)
    fig.suptitle("U_max pdf from Belin's Fig. 6 (%s) with r_max = %g eta at every Re_lambda (dashed: our best model)" % ("bins of %g in x" % args.bin if args.bin > 0 else "lognormal fit", beta), fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_umax_fixed_r.png"), dpi=105)


if __name__ == "__main__":
    main()
