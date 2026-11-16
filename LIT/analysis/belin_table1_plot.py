"""belin_table1_plot.py  v01  Table I of Belin et al. (1996): the kinematic viscosity nu of each run against the mean velocity U, the Reynolds number Re and Re_lambda.
Shows whether the viscosity of the helium (set by temperature and pressure) is linked to the flow speed or the Reynolds number.  The Re_lambda = 879 entry is plotted at 439
(u' lambda / nu from its own row; see the discussion of the misprint).
Usage: python belin_table1_plot.py     writes belin_table1_plot.png

Versions  M01 m01.v01 (2026-11-13): first version.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import spearmanr

HERE = os.path.dirname(os.path.abspath(__file__))
# cell, nu cm^2/s, U cm/s, u' cm/s, Re, R_lambda (printed), lambda um, eta um
ROWS = [(2, 1.6e-2, 39, 8, 4.1e4, 151, 3000, 127), (2, 2.1e-2, 284, 94, 2.3e5, 674, 1520, 26), (2, 4.6e-4, 128, 37, 4.7e6, 2300, 276, 2.9),
        (2, 3.3e-4, 136, 52, 7e6, 5040, 320, 2), (2, 4.4e-4, 128, 27, 5e6, 1550, 262, 3.4), (2, 1.1e-3, 64, 13, 2e6, 822, 680, 12),
        (1, 2.7e-2, 118, 29, 16700, 188, 1740, 64), (1, 2.6e-4, 27.4, 6.1, 4.3e5, 879, 187, 5)]


def main():
    cell, nu, U, up, Re, Rl = (np.array([r[i] for r in ROWS], float) for i in (0, 1, 2, 3, 4, 5))
    Rl_fixed = Rl.copy()
    Rl_fixed[-1] = up[-1] * 187e-4 / nu[-1]                                  # u' lambda / nu = 439
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.6))
    for a, (x, label) in zip(ax, ((U, "mean velocity U (cm/s)"), (Re, "Reynolds number Re"), (Rl_fixed, "Re_lambda"))):
        for c, marker in ((1, "s"), (2, "o")):
            sel = cell == c
            a.loglog(x[sel], nu[sel], marker, ms=9, color="tab:blue" if c == 2 else "tab:red", label="cell %d" % c)
        for xi, ni, ri in zip(x, nu, Rl):
            a.annotate("%g" % ri, (xi, ni), textcoords="offset points", xytext=(6, 4), fontsize=8)
        corr = spearmanr(x, nu)[0]
        a.set_xlabel(label)
        a.set_ylabel("kinematic viscosity nu (cm^2/s)")
        a.set_title("rank correlation coefficient %.2f (8 runs)" % corr, fontsize=10)
        a.legend(fontsize=8)
    fig.suptitle("Belin et al. (1996) Table I: the viscosity of each run against U, Re and Re_lambda (labels: printed Re_lambda)", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_table1_plot.png"), dpi=110)
    for name, x in (("U", U), ("Re", Re), ("Re_lambda", Rl_fixed)):
        print("%-10s rank correlation with nu: %.2f" % (name, spearmanr(x, nu)[0]))


if __name__ == "__main__":
    main()
