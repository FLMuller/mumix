"""belin_table1_eps_re.py  v01  Table I of Belin et al. (1996): the dissipation rate against the Reynolds number.
eps is taken from lambda: eps = 15 nu u'^2 / lambda^2 (lambda is printed with three digits, so it is less affected by rounding than eta, eps ~ eta^-4).  Cell radii (p. 3): cell 2 10 cm, cell 1 3.3 cm.
Left: eps against Re.  Right: eps / (U^3 / R_disk) against Re, which is constant if the dissipation scales with the mean velocity and the disk radius.
Usage: python belin_table1_eps_re.py     writes belin_table1_eps_re.png

Versions  M01 m01.v01 (2026-11-13): first version.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = [(2, 1.6e-2, 39, 8, 4.1e4, 3000), (2, 2.1e-2, 284, 94, 2.3e5, 1520), (2, 4.6e-4, 128, 37, 4.7e6, 276), (2, 3.3e-4, 136, 52, 7e6, 320), (2, 4.4e-4, 128, 27, 5e6, 262),
        (2, 1.1e-3, 64, 13, 2e6, 680), (1, 2.7e-2, 118, 29, 16700, 1740), (1, 2.6e-4, 27.4, 6.1, 4.3e5, 187)]      # cell, nu, U, u', Re, lambda (um)
DISK = {2: 10.0, 1: 3.3}


def main():
    cell = np.array([r[0] for r in ROWS])
    nu, U, up, Re, lam = (np.array([r[i] for r in ROWS], float) for i in range(1, 6))
    eps = 15 * nu * up ** 2 / (lam * 1e-4) ** 2                                  # cm^2/s^3
    radius = np.array([DISK[c] for c in cell])
    scaled = eps / (U ** 3 / radius)
    fig, ax = plt.subplots(1, 2, figsize=(13, 5.2))
    for c, colour in ((2, "tab:blue"), (1, "tab:red")):
        sel = cell == c
        ax[0].loglog(Re[sel], eps[sel], "o", ms=9, color=colour, label="cell %d" % c)
        ax[1].loglog(Re[sel], scaled[sel], "o", ms=9, color=colour, label="cell %d" % c)
    for a, y in zip(ax, (eps, scaled)):
        for x, yy, u in zip(Re, y, U):
            a.annotate("U %g" % u, (x, yy), textcoords="offset points", xytext=(6, 4), fontsize=8)
        a.set_xlabel("Re (Table I, disk radius and angular speed)")
        a.legend(fontsize=8)
    ax[0].set_ylabel("eps = 15 nu u'^2 / lambda^2  (cm^2/s^3)")
    ax[1].set_ylabel("eps / (U^3 / R_disk)")
    ax[1].set_title("mean %.3f, spread x/÷ %.1f" % (np.exp(np.mean(np.log(scaled))), np.exp(np.std(np.log(scaled)))), fontsize=10)
    ax[0].set_title("dissipation rate of each run (labels: mean velocity U, cm/s)", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_table1_eps_re.png"), dpi=110)
    print("eps/(U^3/R): geometric mean %.3f, factor spread %.2f" % (np.exp(np.mean(np.log(scaled))), np.exp(np.std(np.log(scaled)))))


if __name__ == "__main__":
    main()
