"""belin_table1_po_const.py  v01  Belin et al. (1996) Table I, misprints corrected: the power number Po = eps V / (N^3 D^5) taken as a constant (the least-squares constant is the mean), per cell.
Po as in belin_table1_po_fit.py.  Error: the standard error of the mean (standard deviation / sqrt(n)).  The shaded band is the mean +- the standard deviation of the runs.
Usage: python belin_table1_po_const.py     writes belin_table1_po_const.png

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
CELL = {2: (10.0, 13.1), 1: (3.3, 5.5)}


def main():
    with open(os.path.join(HERE, "belin_table1.csv"), newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    cell = np.array([int(r["cell"]) for r in rows])
    nu, up, Re, lam = (np.array([float(r[k]) for r in rows]) for k in ("nu_cm2_s", "u_prime_cm_s", "Re_used", "lambda_um"))
    eps = 15 * nu * up ** 2 / (lam * 1e-4) ** 2
    R = np.array([CELL[c][0] for c in cell])
    H = np.array([CELL[c][1] for c in cell])
    N = Re * nu / (2 * math.pi * R ** 2)
    Po = eps * math.pi * R ** 2 * H / (N ** 3 * (2 * R) ** 5)
    fig, ax = plt.subplots(figsize=(8.5, 5.6))
    for c, colour in ((2, "tab:blue"), (1, "tab:red")):
        sel = cell == c
        mean, sd = Po[sel].mean(), Po[sel].std(ddof=1)
        ax.plot(Re[sel] / 1e6, Po[sel], "o", ms=9, color=colour)
        ax.axhline(mean, color=colour, lw=1.4, label="cell %d: Po = %.3f +- %.3f (standard error), standard deviation %.3f, %d runs" % (c, mean, sd / math.sqrt(sel.sum()), sd, sel.sum()))
        ax.axhspan(mean - sd, mean + sd, color=colour, alpha=0.12)
        print("cell %d: Po = %.4f, standard error %.4f, standard deviation %.4f, geometric mean %.4f, %d runs" % (c, mean, sd / math.sqrt(sel.sum()), sd, math.exp(np.mean(np.log(Po[sel]))), sel.sum()))
    ax.set_xlabel("Re / 10^6 (Table I, corrected)")
    ax.set_ylabel("Po = eps V / (N^3 D^5)")
    ax.set_xlim(0, 7.4)
    ax.set_ylim(0, 1.7)
    ax.set_title("Belin et al. (1996): power number as a constant per cell", fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_table1_po_const.png"), dpi=110)


if __name__ == "__main__":
    main()
