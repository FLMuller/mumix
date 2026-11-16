"""belin_table1_calc_vs_table.py  v01  Belin et al. (1996) Table I (belin_table1.csv): Re_lambda and the Taylor scale lambda calculated from a constant length L = u'^3 / eps per cell, each against the table value.
eps = u'^3 / L (L: cell 2 5.738 cm, cell 1 1.021 cm), lambda = (15 nu u'^2 / eps)^(1/2) = (15 nu L / u')^(1/2), Re_lambda = u' lambda / nu.  The black line is equality, the dashed lines are +-40 %.
Usage: python belin_table1_calc_vs_table.py     writes belin_table1_calc_vs_table_lin.png (linear axes)

Versions  M01 m01.v01 (2026-11-13): first version (log-log).
          m01.v02 (2026-11-13): linear axes.
"""
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
L_CELL = {2: 5.738, 1: 1.021}


def main():
    with open(os.path.join(HERE, "belin_table1.csv"), newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    cell = np.array([int(r["cell"]) for r in rows])
    nu, up, Re, Rl, lam = (np.array([float(r[k]) for r in rows]) for k in ("nu_cm2_s", "u_prime_cm_s", "Re_used", "Re_lambda_used", "lambda_um"))
    L = np.array([L_CELL[c] for c in cell])
    lam_calc = np.sqrt(15 * nu * L / up) * 1e4                                  # um
    Rl_calc = np.sqrt(15 * up * L / nu)
    fig, ax = plt.subplots(1, 2, figsize=(13, 5.8))
    for a, table, calc, label, lim in ((ax[0], Rl, Rl_calc, "Re_lambda", [0, 5500]), (ax[1], lam, lam_calc, "lambda (um)", [0, 4500])):
        a.plot(lim, lim, "k-", lw=1)
        a.plot(lim, [0.6 * v for v in lim], "k--", lw=0.8)
        a.plot(lim, [1.4 * v for v in lim], "k--", lw=0.8)
        for c, colour in ((2, "tab:blue"), (1, "tab:red")):
            sel = cell == c
            a.plot(table[sel], calc[sel], "o", ms=9, color=colour, label="cell %d (L = %.2f cm)" % (c, L_CELL[c]))
        for x, y, r in zip(table, calc, Re):
            a.annotate("Re %.2g" % r, (x, y), textcoords="offset points", xytext=(6, -11), fontsize=7)
        a.set_xlim(lim)
        a.set_ylim(lim)
        a.set_xlabel("%s, Table I" % label)
        a.set_ylabel("%s, calculated from the constant length" % label)
        a.legend(fontsize=8)
    fig.suptitle("Belin et al. (1996) Table I: Re_lambda and lambda from eps = u'^3/L, against the table (dashed: +-40 %)", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_table1_calc_vs_table_lin.png"), dpi=110)
    print("lambda table (um):", lam, "\nlambda calculated (um):", np.round(lam_calc), "\nratio:", np.round(lam_calc / lam, 2))
    print("Re_lambda ratio:", np.round(Rl_calc / Rl, 2))


if __name__ == "__main__":
    main()
