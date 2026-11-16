"""belin_table1_power.py  v01  Table I of Belin et al. (1996): the power number implied by eps = Po N^3 D^5 / V.
eps from lambda (15 nu u'^2 / lambda^2).  N = Omega / 2 pi with Omega = Re nu / R_disk^2 (Re of Table I is based on the disk radius and angular speed, p. 3).  Disk radius R = cell radius
(cell 2: 10 cm, height 13.1 cm; cell 1: 3.3 cm, height 5.5 cm), D = 2 R, V = pi R^2 H.  Po = eps V / (N^3 D^5) for each run, against Re.  The Re = 2e6 run (outlier of Re = L U / nu) is marked.
Usage: python belin_table1_power.py     writes belin_table1_power.png

Versions  M01 m01.v01 (2026-11-13): first version.
"""
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = [(2, 1.6e-2, 39, 8, 4.1e4, 3000), (2, 2.1e-2, 284, 94, 2.3e5, 1520), (2, 4.6e-4, 128, 37, 4.7e6, 276), (2, 3.3e-4, 136, 52, 7e6, 320), (2, 4.4e-4, 128, 27, 5e6, 262),
        (2, 1.1e-3, 64, 13, 2e6, 680), (1, 2.7e-2, 118, 29, 16700, 1740), (1, 2.6e-4, 27.4, 6.1, 4.3e5, 187)]      # cell, nu, U, u', Re, lambda (um)
CELL = {2: (10.0, 13.1), 1: (3.3, 5.5)}                                                                  # radius, height (cm)


def main():
    cell = np.array([r[0] for r in ROWS])
    nu, U, up, Re, lam = (np.array([r[i] for r in ROWS], float) for i in range(1, 6))
    eps = 15 * nu * up ** 2 / (lam * 1e-4) ** 2
    radius = np.array([CELL[c][0] for c in cell])
    height = np.array([CELL[c][1] for c in cell])
    volume = math.pi * radius ** 2 * height
    diameter = 2 * radius
    omega = Re * nu / radius ** 2
    N = omega / (2 * math.pi)
    Po = eps * volume / (N ** 3 * diameter ** 5)
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    for c, colour in ((2, "tab:blue"), (1, "tab:red")):
        sel = cell == c
        ax.loglog(Re[sel], Po[sel], "o", ms=9, color=colour, label="cell %d (R %.1f cm, V %.0f cm^3)" % (c, CELL[c][0], volume[sel][0]))
    ax.loglog(Re[5], Po[5], "x", ms=13, mew=2, color="k", label="Re = 2e6 run (outlier in Re = L U / nu)")
    for x, y, n in zip(Re, Po, N):
        ax.annotate("N %.1f Hz" % n, (x, y), textcoords="offset points", xytext=(6, 4), fontsize=8)
    ax.set_xlabel("Re (Table I)")
    ax.set_ylabel("Po = eps V / (N^3 D^5)")
    ax.set_title("Belin et al. (1996): power number implied by Table I", fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_table1_power.png"), dpi=110)
    for r, c, p, n in zip(Re, cell, Po, N):
        print("cell %d  Re %.3g  N %.2f Hz  Po %.3f" % (c, r, n, p))


if __name__ == "__main__":
    main()
