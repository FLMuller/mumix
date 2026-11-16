"""belin_table1_po_ab.py  v01  Belin et al. (1996) Table I, misprints corrected: the power number Po on linear axes against Re, with Po = A / Re + b fitted (least squares, linear in 1 / Re).
Po as in belin_table1_po_fit.py.  Fits: all 8 runs and the 6 runs of cell 2; the errors are the standard errors of A and b from the covariance of the fit.
Usage: python belin_table1_po_ab.py     writes belin_table1_po_ab.png

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


def fit(re, po, label, colour, ax, grid):
    (A, b), cov = np.polyfit(1.0 / re, po, 1, cov=True)
    resid = po - (A / re + b)
    ax.plot(grid / 1e6, A / grid + b, "-", color=colour, lw=1.4, label="%s: Po = (%.3g +- %.2g) / Re + (%.3f +- %.3f), rms residual %.2f" % (label, A, math.sqrt(cov[0, 0]), b, math.sqrt(cov[1, 1]), math.sqrt(np.mean(resid ** 2))))
    print("%-7s Po = %.4g / Re + %.4f   (standard errors %.3g, %.4f; rms residual %.3f; %d runs)" % (label, A, b, math.sqrt(cov[0, 0]), math.sqrt(cov[1, 1]), math.sqrt(np.mean(resid ** 2)), len(re)))


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
    fig, ax = plt.subplots(figsize=(8.5, 5.8))
    for c, colour in ((2, "tab:blue"), (1, "tab:red")):
        ax.plot(Re[cell == c] / 1e6, Po[cell == c], "o", ms=9, color=colour, label="cell %d" % c)
    grid = np.linspace(1.2e4, 7.2e6, 400)
    fit(Re, Po, "all 8", "k", ax, grid)
    fit(Re[cell == 2], Po[cell == 2], "cell 2", "tab:blue", ax, grid)
    ax.set_xlabel("Re / 10^6 (Table I, corrected)")
    ax.set_ylabel("Po = eps V / (N^3 D^5)")
    ax.set_title("Belin et al. (1996): power number against Re, Po = A / Re + b", fontsize=10)
    ax.set_xlim(0, 7.4)
    ax.set_ylim(0, 1.6)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_table1_po_ab.png"), dpi=110)


if __name__ == "__main__":
    main()
