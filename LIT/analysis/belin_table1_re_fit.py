"""belin_table1_re_fit.py  v01  Table I of Belin et al. (1996): Re against U/nu, with the line Re = L U/nu fitted (least squares in log Re, slope 1) to each cell, the outlier left out.
Outlier: the cell 2 run with Re = 2e6 (nu 1.1e-3, U 64), whose Re/(U/nu) is twice that of the other cell 2 runs.  A free-slope fit of log Re on log (U/nu) for all runs without it is also given.
Usage: python belin_table1_re_fit.py     writes belin_table1_re_fit.png and prints the fitted values

Versions  M01 m01.v01 (2026-11-13): first version.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = [(2, 1.6e-2, 39, 4.1e4), (2, 2.1e-2, 284, 2.3e5), (2, 4.6e-4, 128, 4.7e6), (2, 3.3e-4, 136, 7e6), (2, 4.4e-4, 128, 5e6), (2, 1.1e-3, 64, 2e6),
        (1, 2.7e-2, 118, 16700), (1, 2.6e-4, 27.4, 4.3e5)]                  # cell, nu (cm^2/s), U (cm/s), Re
OUTLIER = 5                                                                 # index of the Re = 2e6 run


def main():
    cell = np.array([r[0] for r in ROWS])
    nu, U, Re = (np.array([r[i] for r in ROWS], float) for i in (1, 2, 3))
    x = U / nu
    keep = np.ones(len(ROWS), bool)
    keep[OUTLIER] = False
    fig, ax = plt.subplots(figsize=(7.5, 6))
    grid = np.logspace(1.5, 6.0, 50)
    for c, colour in ((2, "tab:blue"), (1, "tab:red")):
        sel = (cell == c) & keep
        length = float(np.exp(np.mean(np.log(Re[sel] / x[sel]))))               # slope fixed at 1: log L is the mean of log (Re / x)
        spread = float(np.std(np.log(Re[sel] / x[sel])))
        ax.loglog(x[sel], Re[sel], "o", ms=9, color=colour, label="cell %d: L = %.1f cm (scatter %.0f%%)" % (c, length, 100 * spread))
        ax.loglog(grid, length * grid, "-", color=colour, lw=1.3)
        print("cell %d: L = %.2f cm, scatter of ln(Re / (U/nu)) %.3f, %d runs" % (c, length, spread, sel.sum()))
    ax.loglog(x[~keep], Re[~keep], "x", ms=11, mew=2, color="k", label="left out (Re twice L = 17 cm)")
    slope, intercept = np.polyfit(np.log(x[keep]), np.log(Re[keep]), 1)
    ax.loglog(grid, np.exp(intercept) * grid ** slope, "--", color="gray", label="free slope, all runs but the outlier: Re = %.2f (U/nu)^%.2f" % (np.exp(intercept), slope))
    print("free slope (7 runs): Re = %.3f (U/nu)^%.3f" % (np.exp(intercept), slope))
    ax.set_xlabel("U / nu  (1/cm)")
    ax.set_ylabel("Re (Table I)")
    ax.set_title("Belin et al. (1996) Table I: Re = L U / nu", fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_table1_re_fit.png"), dpi=110)


if __name__ == "__main__":
    main()
