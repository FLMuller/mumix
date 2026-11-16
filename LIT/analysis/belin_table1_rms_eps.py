"""belin_table1_rms_eps.py  v01  Belin et al. (1996) Table I (belin_table1.csv): the rms velocity u' against the dissipation rate eps = 15 nu u'^2 / lambda^2.
If eps = C u'^3 / L with a length L that does not change between runs, u' is proportional to eps^(1/3).  Left: u' against eps with the fitted power law and the slope 1/3 through the geometric mean.
Right: the length u'^3 / eps (C = 1) of each run against Re.
Usage: python belin_table1_rms_eps.py     writes belin_table1_rms_eps.png

Versions  M01 m01.v01 (2026-11-13): first version.
"""
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DISK = {2: 10.0, 1: 3.3}


def main():
    with open(os.path.join(HERE, "belin_table1.csv"), newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    cell = np.array([int(r["cell"]) for r in rows])
    nu, up, Re, lam = (np.array([float(r[k]) for r in rows]) for k in ("nu_cm2_s", "u_prime_cm_s", "Re_used", "lambda_um"))
    eps = 15 * nu * up ** 2 / (lam * 1e-4) ** 2
    L = up ** 3 / eps
    fig, ax = plt.subplots(1, 2, figsize=(13, 5.3))
    for c, colour in ((2, "tab:blue"), (1, "tab:red")):
        sel = cell == c
        ax[0].loglog(eps[sel], up[sel], "o", ms=9, color=colour, label="cell %d" % c)
        ax[1].loglog(Re[sel], L[sel], "o", ms=9, color=colour, label="cell %d (disk radius %.1f cm)" % (c, DISK[c]))
        ax[1].axhline(DISK[c], color=colour, lw=0.8, ls=":")
    coef, cov = np.polyfit(np.log10(eps), np.log10(up), 1, cov=True)
    grid = np.logspace(1.8, 5.4, 50)
    ax[0].loglog(grid, 10 ** coef[1] * grid ** coef[0], "k-", label="fit: u' = %.3g eps^%.2f (exponent +- %.2f)" % (10 ** coef[1], coef[0], np.sqrt(cov[0, 0])))
    k = 10 ** np.mean(np.log10(up) - np.log10(eps) / 3)
    ax[0].loglog(grid, k * grid ** (1 / 3), "k--", label="slope 1/3 through the geometric mean: u' = %.3g eps^(1/3)" % k)
    ax[0].set_xlabel("eps = 15 nu u'^2 / lambda^2  (cm^2/s^3)")
    ax[0].set_ylabel("u' (cm/s)")
    ax[0].legend(fontsize=8)
    ax[1].set_xlabel("Re (Table I, corrected)")
    ax[1].set_ylabel("u'^3 / eps  (cm)")
    ax[1].legend(fontsize=8)
    ax[1].set_title("length u'^3/eps of each run (dotted: disk radius)", fontsize=10)
    fig.suptitle("Belin et al. (1996) Table I: rms velocity against dissipation rate", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_table1_rms_eps.png"), dpi=110)
    print("u' = %.4g eps^%.3f (standard error of the exponent %.3f)" % (10 ** coef[1], coef[0], np.sqrt(cov[0, 0])))
    print("u'^3/eps (cm):", np.round(L, 2), " ratio to disk radius:", np.round(L / np.array([DISK[c] for c in cell]), 2))


if __name__ == "__main__":
    main()
