"""belin_table1_pairs.py  v01  Table I of Belin et al. (1996): every column against every other, with Re_lambda calculated as u' lambda / nu (route a; the printed 879 becomes 439).
Lower triangle: log-log scatter of the 8 runs (red: cell 1, blue: cell 2).  Upper triangle: the rank correlation coefficient of the pair.
Usage: python belin_table1_pairs.py     writes belin_table1_pairs.png and prints the rank correlations

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
    Rl = up * lam * 1e-4 / nu                                                    # route a
    columns = [("nu (cm^2/s)", nu), ("U (cm/s)", U), ("u' (cm/s)", up), ("Re", Re), ("Re_lambda = u' lambda / nu", Rl), ("lambda (um)", lam), ("eta (um)", eta)]
    n = len(columns)
    fig, ax = plt.subplots(n, n, figsize=(15, 14))
    for i in range(n):
        for j in range(n):
            a = ax[i, j]
            if i == j:
                a.text(0.5, 0.5, columns[i][0], ha="center", va="center", fontsize=10, transform=a.transAxes)
                a.set_xticks([])
                a.set_yticks([])
            elif i > j:
                for c, colour in ((1, "tab:red"), (2, "tab:blue")):
                    sel = cell == c
                    a.loglog(columns[j][1][sel], columns[i][1][sel], "o", ms=5, color=colour)
                a.tick_params(labelsize=6)
            else:
                corr = spearmanr(columns[j][1], columns[i][1])[0]
                a.text(0.5, 0.5, "%.2f" % corr, ha="center", va="center", fontsize=14, transform=a.transAxes, color="k" if abs(corr) < 0.6 else "tab:red", weight="bold" if abs(corr) >= 0.6 else "normal")
                a.set_xticks([])
                a.set_yticks([])
    fig.suptitle("Belin et al. (1996) Table I, 8 runs: lower triangle log-log scatter, upper triangle rank correlation coefficient (red: |value| >= 0.6)", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_table1_pairs.png"), dpi=100)
    names = [c[0].split(" ")[0] for c in columns]
    print("rank correlation coefficients")
    for i in range(n):
        print("%-10s" % names[i] + "".join("%6.2f" % spearmanr(columns[i][1], columns[j][1])[0] for j in range(n)))
    print("columns:", names)


if __name__ == "__main__":
    main()
