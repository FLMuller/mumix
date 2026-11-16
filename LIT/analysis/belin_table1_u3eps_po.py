"""belin_table1_u3eps_po.py  v01  Belin et al. (1996) Table I (belin_table1.csv): the length u'^3 / eps against Re, with eps from the power number, eps = Po N^3 D^5 / V (Po constant per cell:
cell 2 0.270, cell 1 1.010, belin_table1_po_const.py), N = Re nu / (2 pi R^2), D = 2 R, V = pi R^2 H.  For comparison the same length with eps from lambda (15 nu u'^2 / lambda^2) is drawn as open symbols.
Usage: python belin_table1_u3eps_po.py     writes belin_table1_u3eps_po.png

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
CELL = {2: (10.0, 13.1, 0.2697), 1: (3.3, 5.5, 1.0101)}                      # radius, height (cm), Po


def main():
    with open(os.path.join(HERE, "belin_table1.csv"), newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    cell = np.array([int(r["cell"]) for r in rows])
    nu, up, Re, lam = (np.array([float(r[k]) for r in rows]) for k in ("nu_cm2_s", "u_prime_cm_s", "Re_used", "lambda_um"))
    R = np.array([CELL[c][0] for c in cell])
    H = np.array([CELL[c][1] for c in cell])
    Po = np.array([CELL[c][2] for c in cell])
    N = Re * nu / (2 * math.pi * R ** 2)
    eps_po = Po * N ** 3 * (2 * R) ** 5 / (math.pi * R ** 2 * H)
    eps_lam = 15 * nu * up ** 2 / (lam * 1e-4) ** 2
    L_po, L_lam = up ** 3 / eps_po, up ** 3 / eps_lam
    fig, ax = plt.subplots(figsize=(8.3, 5.8))
    for c, colour in ((2, "tab:blue"), (1, "tab:red")):
        sel = cell == c
        ax.loglog(Re[sel], L_po[sel], "o", ms=9, color=colour, label="cell %d: eps from Po (disk radius %.1f cm, dotted)" % (c, CELL[c][0]))
        ax.loglog(Re[sel], L_lam[sel], "o", ms=9, mfc="none", color=colour, label="cell %d: eps from lambda" % c)
        ax.axhline(CELL[c][0], color=colour, lw=0.8, ls=":")
    ax.set_xlabel("Re (Table I, corrected)")
    ax.set_ylabel("u'^3 / eps  (cm)")
    ax.set_title("Belin et al. (1996) Table I: the length u'^3/eps, eps from the power number", fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_table1_u3eps_po.png"), dpi=110)
    c2 = cell == 2
    print("u'^3/eps from Po, cell 2 (cm):", np.round(L_po[c2], 2), " mean %.2f cm = %.2f R, spread x/÷ %.2f" % (L_po[c2].mean(), L_po[c2].mean() / 10, np.exp(np.std(np.log(L_po[c2])))))
    print("u'^3/eps from lambda, cell 2 (cm):", np.round(L_lam[c2], 2), " spread x/÷ %.2f" % np.exp(np.std(np.log(L_lam[c2]))))
    print("cell 1 from Po (cm):", np.round(L_po[~c2], 2))
    print("Re:", Re[c2])


if __name__ == "__main__":
    main()
