"""belin_table1_relambda_const.py  v01  Belin et al. (1996) Table I (belin_table1.csv): Re_lambda calculated from a constant length L = u'^3 / eps per cell, against Re, with Re_lambda of the table.
eps = u'^3 / L, lambda = (15 nu u'^2 / eps)^(1/2), Re_lambda = u' lambda / nu = (15 u' L / nu)^(1/2).  L per cell: the mean of u'^3 / eps over its runs, eps from the power number (belin_table1_u3eps_const.py:
cell 2 5.74 cm, cell 1 1.02 cm).  Table: Re_lambda_used of belin_table1.csv (u' lambda / nu, the misprint 879 as 439).
Usage: python belin_table1_relambda_const.py     writes belin_table1_relambda_const.png

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
L_CELL = {2: 5.738, 1: 1.021}


def main():
    with open(os.path.join(HERE, "belin_table1.csv"), newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    cell = np.array([int(r["cell"]) for r in rows])
    nu, up, Re, Rl = (np.array([float(r[k]) for r in rows]) for k in ("nu_cm2_s", "u_prime_cm_s", "Re_used", "Re_lambda_used"))
    L = np.array([L_CELL[c] for c in cell])
    Rl_calc = np.sqrt(15 * up * L / nu)
    fig, ax = plt.subplots(figsize=(8.5, 5.8))
    for c, colour in ((2, "tab:blue"), (1, "tab:red")):
        sel = cell == c
        ax.loglog(Re[sel], Rl_calc[sel], "o", ms=9, color=colour, label="cell %d: calculated from L = %.2f cm" % (c, L_CELL[c]))
        ax.loglog(Re[sel], Rl[sel], "s", ms=9, mfc="none", mew=2, color=colour, label="cell %d: Table I (u' lambda / nu)" % c)
    for x, a_, b_ in zip(Re, Rl_calc, Rl):
        ax.plot([x, x], [a_, b_], "-", color="gray", lw=0.8)
    ax.set_xlabel("Re (Table I, corrected)")
    ax.set_ylabel("Re_lambda")
    ax.set_title("Belin et al. (1996): Re_lambda from a constant u'^3/eps length, against the table", fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_table1_relambda_const.png"), dpi=110)
    print("Re          Re_lambda table   calculated   ratio")
    for r, t, c in zip(Re, Rl, Rl_calc):
        print("%9.3g   %8.0f   %8.0f    %.2f" % (r, t, c, c / t))


if __name__ == "__main__":
    main()
