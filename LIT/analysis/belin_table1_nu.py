"""belin_table1_nu.py  v01  Table I of Belin et al. (1996): the kinematic viscosity nu of each run against every other column (Re_lambda calculated as u' lambda / nu; the printed 879 becomes 439).
Red: cell 1, blue: cell 2; each point is labelled with its calculated Re_lambda.  The title of each panel gives the rank correlation coefficient (8 runs).
Usage: python belin_table1_nu.py     writes belin_table1_nu.png

Versions  M01 m01.v01 (2026-11-13): first version.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import spearmanr

HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = [(2, 1.6e-2, 39, 8, 4.1e4, 3000, 127), (2, 2.1e-2, 284, 94, 2.3e5, 1520, 26), (2, 4.6e-4, 128, 37, 4.7e6, 276, 2.9),
        (2, 3.3e-4, 136, 52, 7e6, 320, 2), (2, 4.4e-4, 128, 27, 5e6, 262, 3.4), (2, 1.1e-3, 64, 13, 2e6, 680, 12),
        (1, 2.7e-2, 118, 29, 16700, 1740, 64), (1, 2.6e-4, 27.4, 6.1, 4.3e5, 187, 5)]       # cell, nu, U, u', Re, lambda (um), eta (um)


def main():
    cell = np.array([r[0] for r in ROWS])
    nu, U, up, Re, lam, eta = (np.array([r[i] for r in ROWS], float) for i in range(1, 7))
    Rl = up * lam * 1e-4 / nu
    panels = [("U (cm/s)", U), ("u' (cm/s)", up), ("Re", Re), ("Re_lambda = u' lambda / nu", Rl), ("lambda (um)", lam), ("eta (um)", eta)]
    fig, ax = plt.subplots(2, 3, figsize=(15, 8.5))
    for a, (label, x) in zip(ax.flat, panels):
        for c, colour in ((1, "tab:red"), (2, "tab:blue")):
            sel = cell == c
            a.loglog(x[sel], nu[sel], "o", ms=9, color=colour, label="cell %d" % c)
        for xi, ni, ri in zip(x, nu, Rl):
            a.annotate("%.0f" % ri, (xi, ni), textcoords="offset points", xytext=(6, 4), fontsize=8)
        a.set_xlabel(label)
        a.set_ylabel("nu (cm^2/s)")
        a.set_title("rank correlation coefficient %.2f" % spearmanr(x, nu)[0], fontsize=10)
        a.legend(fontsize=8)
    fig.suptitle("Belin et al. (1996) Table I: kinematic viscosity of the helium against the other columns (labels: Re_lambda)", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_table1_nu.png"), dpi=105)


if __name__ == "__main__":
    main()
