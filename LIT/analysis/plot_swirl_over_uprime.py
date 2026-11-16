"""plot_swirl_over_uprime.py  v01  The swirl of the tube data as U_max / u' against Re_lambda (instead of U_max / U_eta).
Conversion: U_max / u' = (U_max / U_eta) / (u' / U_eta), with u' / U_eta = (Re_lambda / sqrt 15)^(1/2) (isotropic turbulence; it agrees with the Table I of Belin et al. 1996 to 20-30 % at high Re_lambda,
belin_table1_relambda.py).  Rows: LIT/fittingtool/data/tubes.csv with the corrections of corrections.json (the values the fits use; Mouri 2007 and 2004 and the excluded quantities are drawn open).
Curves: the best models of the page, U_max / U_eta = 0.769 Re_lambda^(1/3) (D6) and -4.61 + 1.798 ln Re_lambda (L1), converted in the same way; the Jimenez and Wray (1998) bound of 2.5 u'; and the swirl
that Belin's Fig. 6 gives at Re_lambda 659 for his mean apparent radius (r_max 9.3 eta): Gamma / (u' eta) of the peak (96) and of the mean (301) divided by 8.784 r_max.
Usage: python plot_swirl_over_uprime.py     writes plot_swirl_over_uprime.png

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
FIT = os.path.join(HERE, "..", "fittingtool")
sys.path.insert(0, FIT)
import fitdata  # noqa: E402

CONVERT = 15 ** 0.25                                           # U / u' = (U / U_eta) * 15^(1/4) / Re_lambda^(1/2)


def main():
    rows = fitdata.load(os.path.join(FIT, "data", "tubes.csv"), os.path.join(FIT, "data", "corrections.json"))
    excluded_q = fitdata.EXCLUDED_QUANTITIES
    fig, ax = plt.subplots(figsize=(10.5, 6.5))
    shown = set()
    for x in rows:
        if x["re"] is None or x["u"] is None:
            continue
        ratio = x["u"] * CONVERT / math.sqrt(x["re"])
        left_out = x["excluded"] or "U" in excluded_q.get(x["src"], {})
        colour = {"A": "tab:blue", "B": "tab:green", "C": "tab:red"}.get(x["group"], "gray")
        label = "%s (%s)" % (x["reference"], x["tube_set"]) if (x["reference"], left_out) not in shown else None
        shown.add((x["reference"], left_out))
        ax.plot(x["re"], ratio, "o", ms=6, color=colour, mfc="none" if left_out else colour, alpha=0.9, label=label)
    re = np.logspace(1.4, 3.5, 100)
    ax.plot(re, 0.769 * re ** (1 / 3) * CONVERT / np.sqrt(re), "k-", lw=2, label="best model D6: 0.769 Re^(1/3) U_eta")
    ax.plot(re, (-4.61 + 1.798 * np.log(re)) * CONVERT / np.sqrt(re), "k--", lw=2, label="best model L1: -4.61 + 1.798 ln Re U_eta")
    ax.axhline(2.5, color="tab:purple", lw=1.5, ls=":", label="Jimenez and Wray bound 2.5 u'")
    r_apparent = 9.3
    for gstar, name in ((96, "peak"), (301, "mean")):
        ax.plot([659], [gstar / (8.784 * r_apparent)], "*", ms=14, color="tab:orange", mec="k", label="Belin Fig. 6 %s, r_max 9.3 eta" % name)
    ax.set_xscale("log")
    ax.set_xlabel("Re_lambda")
    ax.set_ylabel("U_max / u'")
    ax.set_ylim(0, 4.5)
    ax.set_title("swirl of the tubes in units of the rms velocity (open: left out of the fits)", fontsize=10)
    ax.legend(fontsize=6.5, ncol=2, loc="upper right")
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "plot_swirl_over_uprime.png"), dpi=110)


if __name__ == "__main__":
    main()
