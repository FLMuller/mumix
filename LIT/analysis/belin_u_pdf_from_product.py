"""belin_u_pdf_from_product.py  v01  The U_max pdf worked out from the r_max U_max pdf and a pdf of r_max, both by inverse-CDF sampling (no constant r_max).
r_max U_max / nu = Re_c = 1.585 x Re_lambda^(1/2), x from the cumulative curve of the lognormal fitted to Belin's Fig. 6 (median 9.74, ln-width 0.889, unchanged);  r_max / eta from the cumulative curve of one of
three pdfs:  (a) sharp, one lognormal at 5 eta with ln-width 0.03;  (b) the first Tanahashi (2001) lognormal (median 5.23, ln-width 0.288);  (c) both Tanahashi lognormals (chord_population.RADIUS).
U_max (cm/s) = Re_c U_eta / (r_max / eta), U_eta from the Table I chain at the Re_lambda (659, 2850).  x and r_max are drawn independently.
Usage: python belin_u_pdf_from_product.py     writes belin_u_pdf_from_product.png

Versions  M01 m01.v01 (2026-11-13): first version.
"""
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import belin_gamma_pdf as bg            # noqa: E402
import belin_umax_vs_relambda as bu     # noqa: E402
import chord_population as cp           # noqa: E402
import chord_belin_x as cbx             # noqa: E402

N = 400000


def radius_pdf(kind, grid):
    ln = lambda m, s: bg.lognormal_x(grid, math.log(m), s)
    if kind == "a":
        return ln(5.0, 0.03)
    w1, m1, s1, m2, s2 = cp.RADIUS
    if kind == "b":
        return ln(m1, s1)
    return w1 * ln(m1, s1) + (1 - w1) * ln(m2, s2)


def main():
    mu, s, _ = bg.lognormal_fit()
    rng = np.random.default_rng(3)
    xg = np.logspace(-2.5, 3.0, 8000)
    rg = np.linspace(1.0, 60.0, 12000)
    fig, ax = plt.subplots(1, 2, figsize=(14, 5.6))
    for a, (Rl, event) in zip(ax, ((659, 27.5), (2850, 72.5))):
        c = bu.chain_at(Rl)
        x = cbx.inverse_cdf(xg, bg.lognormal_x(xg, mu, s))(rng.uniform(size=N))
        Re_c = 1.585 * x * math.sqrt(Rl)
        for kind, colour, label in (("a", "tab:blue", "r_max = 5 eta, sharp (ln-width 0.03)"), ("b", "tab:green", "r_max: first Tanahashi lognormal (median 5.2, ln-width 0.29)"), ("c", "tab:red", "r_max: both Tanahashi lognormals")):
            r = cbx.inverse_cdf(rg, radius_pdf(kind, rg))(rng.uniform(size=N))
            U = Re_c * c["U_eta"] / r
            a.hist(U, np.linspace(0, 700, 141), density=True, histtype="step", lw=2, color=colour, label="%s: median %.0f cm/s" % (label, np.median(U)))
            print("Re_lambda %d, %s: median U_max %.0f cm/s, 10-90 %% %.0f-%.0f" % (Rl, kind, np.median(U), *np.percentile(U, [10, 90])))
        a.axvline(event, color="k", ls="--", lw=2, label="Fig. 2 event: %.1f cm/s" % event)
        a.axvline(0.769 * Rl ** (1 / 3) * c["U_eta"], color="gray", ls=":", lw=2, label="our model: %.1f cm/s" % (0.769 * Rl ** (1 / 3) * c["U_eta"]))
        a.set_xlim(0, 450)
        a.set_xlabel("U_max (cm/s)")
        a.set_ylabel("pdf")
        a.set_title("Re_lambda %d (U_eta %.2f cm/s)" % (Rl, c["U_eta"]), fontsize=10)
        a.legend(fontsize=7.5)
    fig.suptitle("U_max pdf = (r_max U_max pdf of Belin's Fig. 6) / (r_max pdf), both sampled", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_u_pdf_from_product.png"), dpi=105)


if __name__ == "__main__":
    main()
