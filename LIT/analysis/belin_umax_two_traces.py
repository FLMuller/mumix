"""belin_umax_two_traces.py  v01  The U_max pdf (cm/s) from Belin et al. (1996) Fig. 6 at the two Re_lambda of the traces of his Fig. 2 (659 and 2850), with the U_max of each event.
As belin_umax_vs_relambda.py: U_max = 1.585 x Re_lambda^(1/2) nu / r_max with x from the lognormal fit of Fig. 6 and nu, eta from the Table I chain at that Re_lambda; r_max = 5 eta and 9.3 eta.
Events (half the swing read from the figure): a 27.5 cm/s, b 72.5 cm/s.  Dots: the digitised markers of Fig. 6 transformed with the same factors.
Usage: python belin_umax_two_traces.py     writes belin_umax_two_traces.png

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
import belin_gamma_pdf as bg             # noqa: E402
import belin_umax_vs_relambda as bu      # noqa: E402


def main():
    mu, s, _ = bg.lognormal_fit()
    xs, ps = bg.raw_points()
    grid = np.linspace(0.05, 100, 2000)
    pdf = bg.lognormal_x(grid, mu, s)
    fig, ax = plt.subplots(1, 2, figsize=(14, 5.4))
    for a, (Rl, event, label) in zip(ax, ((659, 27.5, "a"), (2850, 72.5, "b"))):
        c = bu.chain_at(Rl)
        for beta, colour in ((5.0, "tab:blue"), (9.3, "tab:green")):
            f = 1.585 * math.sqrt(Rl) * c["nu"] / (beta * c["eta"])           # U_max (cm/s) = f x
            a.plot(f * grid, pdf / f, "-", lw=2, color=colour, label="r_max = %g eta: median %.0f cm/s" % (beta, f * math.exp(mu)))
            a.plot(f * xs, ps / f, "o", ms=3, color=colour, alpha=0.6)
        a.axvline(event, color="k", lw=2, ls="--", label="Fig. 2%s event: U_max = %.1f cm/s" % (label, event))
        a.axvline(0.769 * Rl ** (1 / 3) * c["U_eta"], color="tab:red", lw=2, ls=":", label="our model: %.1f cm/s" % (0.769 * Rl ** (1 / 3) * c["U_eta"]))
        a.set_xlim(0, 450 if Rl == 2850 else 330)
        a.set_xlabel("U_max (cm/s)")
        a.set_ylabel("pdf")
        a.set_title("Re_lambda = %d (nu %.2g cm^2/s, eta %.1f um, U_eta %.2f cm/s from the chain)" % (Rl, c["nu"], c["eta"] * 1e4, c["U_eta"]), fontsize=9)
        a.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_umax_two_traces.png"), dpi=105)


if __name__ == "__main__":
    main()
