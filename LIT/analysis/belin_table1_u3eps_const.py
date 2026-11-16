"""belin_table1_u3eps_const.py  v01  Belin et al. (1996) Table I: the length L = u'^3 / eps taken as a constant per cell (eps from the power number, belin_table1_u3eps_po.py).
The constant is the mean of the runs of a cell (the least-squares constant); the standard error of the mean is the standard deviation / sqrt(n).  The shaded band is the mean +- the standard deviation.
Also printed: the dissipation rate eps = u'^3 / L that this constant predicts for each run, against the eps from the power number.
Usage: python belin_table1_u3eps_const.py     writes belin_table1_u3eps_const.png

Versions  M01 m01.v01 (2026-11-13): first version.
"""
import csv
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CELL = {2: (10.0, 13.1, 0.2697), 1: (3.3, 5.5, 1.0101)}


def main():
    with open(os.path.join(HERE, "belin_table1.csv"), newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    cell = np.array([int(r["cell"]) for r in rows])
    nu, up, Re = (np.array([float(r[k]) for r in rows]) for k in ("nu_cm2_s", "u_prime_cm_s", "Re_used"))
    R = np.array([CELL[c][0] for c in cell])
    H = np.array([CELL[c][1] for c in cell])
    Po = np.array([CELL[c][2] for c in cell])
    N = Re * nu / (2 * math.pi * R ** 2)
    eps = Po * N ** 3 * (2 * R) ** 5 / (math.pi * R ** 2 * H)
    L = up ** 3 / eps
    fig, ax = plt.subplots(figsize=(8.5, 5.6))
    for c, colour in ((2, "tab:blue"), (1, "tab:red")):
        sel = cell == c
        mean, sd = L[sel].mean(), L[sel].std(ddof=1)
        ax.plot(Re[sel] / 1e6, L[sel], "o", ms=9, color=colour)
        ax.axhline(mean, color=colour, lw=1.4, label="cell %d: u'^3/eps = %.2f +- %.2f cm (standard error), standard deviation %.2f, %d runs; disk radius %.1f cm" % (c, mean, sd / math.sqrt(sel.sum()), sd, sel.sum(), CELL[c][0]))
        ax.axhspan(mean - sd, mean + sd, color=colour, alpha=0.12)
        eps_pred = up[sel] ** 3 / mean
        print("cell %d: u'^3/eps = %.3f cm (standard error %.3f, sd %.3f, %d runs); eps predicted / eps from Po: %s" % (c, mean, sd / math.sqrt(sel.sum()), sd, sel.sum(), np.round(eps_pred / eps[sel], 2)))
    ax.set_xlabel("Re / 10^6 (Table I, corrected)")
    ax.set_ylabel("u'^3 / eps  (cm)")
    ax.set_title("Belin et al. (1996): u'^3/eps as a constant per cell (eps from the power number)", fontsize=10)
    ax.legend(fontsize=7.5)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_table1_u3eps_const.png"), dpi=110)


if __name__ == "__main__":
    main()
