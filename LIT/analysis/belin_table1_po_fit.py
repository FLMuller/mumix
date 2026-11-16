"""belin_table1_po_fit.py  v01  Belin et al. (1996) Table I, misprints corrected (belin_table1.csv): the power number Po = eps V / (N^3 D^5) against Re, with a straight line in log-log.
eps = 15 nu u'^2 / lambda^2;  N = Re nu / (2 pi R^2) (Re is based on the disk radius and angular speed);  D = 2 R, V = pi R^2 H;  cell 2: R 10 cm, H 13.1 cm;  cell 1: R 3.3 cm, H 5.5 cm.
Two fits: all 8 runs, and the 6 runs of cell 2 (same geometry).
Usage: python belin_table1_po_fit.py     writes belin_table1_po_fit.png

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
    coef, cov = np.polyfit(np.log10(re), np.log10(po), 1, cov=True)
    resid = np.log10(po) - np.polyval(coef, np.log10(re))
    ax.loglog(grid, 10 ** coef[1] * grid ** coef[0], "-", color=colour, lw=1.3, label="%s: Po = %.3g Re^%.2f (exponent +- %.2f, scatter x/÷ %.2f, %d runs)" % (label, 10 ** coef[1], coef[0], math.sqrt(cov[0, 0]), 10 ** np.std(resid), len(re)))
    print("%-8s Po = %.4g Re^%.3f  (standard error of the exponent %.3f, rms scatter x/÷ %.2f, %d runs)" % (label, 10 ** coef[1], coef[0], math.sqrt(cov[0, 0]), 10 ** np.std(resid), len(re)))


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
    fig, ax = plt.subplots(figsize=(8, 5.8))
    for c, colour in ((2, "tab:blue"), (1, "tab:red")):
        ax.loglog(Re[cell == c], Po[cell == c], "o", ms=9, color=colour, label="cell %d" % c)
    grid = np.logspace(4.1, 6.95, 50)
    fit(Re, Po, "all 8", "k", ax, grid)
    fit(Re[cell == 2], Po[cell == 2], "cell 2", "tab:blue", ax, grid)
    ax.set_xlabel("Re (Table I, corrected)")
    ax.set_ylabel("Po = eps V / (N^3 D^5)")
    ax.set_title("Belin et al. (1996): power number against Re", fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_table1_po_fit.png"), dpi=110)
    for r, c, p in zip(Re, cell, Po):
        print("cell %d Re %.3g Po %.3f" % (c, r, p))


if __name__ == "__main__":
    main()
