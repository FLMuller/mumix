"""belin_table1_relambda.py  v01  Table I of Belin et al. (1996): Re_lambda recomputed from the other columns, against the printed Re_lambda.
Three routes (nu in cm^2/s, u' in cm/s, lambda and eta in um):
    a  Re_lambda = u' lambda / nu
    b  Re_lambda = sqrt(15) (u' eta / nu)^2        (isotropy: u' / U_eta = (Re_lambda / sqrt 15)^(1/2), U_eta = nu / eta)
    c  Re_lambda = (lambda / eta)^2 / sqrt(15)     (isotropy: lambda / eta = 15^(1/4) Re_lambda^(1/2))
Usage: python belin_table1_relambda.py     writes belin_table1_relambda.png and prints the numbers

Versions  M01 m01.v01 (2026-11-13): first version.
"""
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = [(2, 1.6e-2, 39, 8, 4.1e4, 151, 3000, 127), (2, 2.1e-2, 284, 94, 2.3e5, 674, 1520, 26), (2, 4.6e-4, 128, 37, 4.7e6, 2300, 276, 2.9),
        (2, 3.3e-4, 136, 52, 7e6, 5040, 320, 2), (2, 4.4e-4, 128, 27, 5e6, 1550, 262, 3.4), (2, 1.1e-3, 64, 13, 2e6, 822, 680, 12),
        (1, 2.7e-2, 118, 29, 16700, 188, 1740, 64), (1, 2.6e-4, 27.4, 6.1, 4.3e5, 879, 187, 5)]


def main():
    printed = np.array([r[5] for r in ROWS], float)
    nu, up, lam, eta = (np.array([r[i] for r in ROWS], float) for i in (1, 3, 6, 7))
    lam_cm, eta_cm = lam * 1e-4, eta * 1e-4
    route_a = up * lam_cm / nu
    route_b = math.sqrt(15) * (up * eta_cm / nu) ** 2
    route_c = (lam / eta) ** 2 / math.sqrt(15)
    fig, ax = plt.subplots(figsize=(7, 6.2))
    lim = [60, 12000]
    ax.plot(lim, lim, "k-", lw=1, label="equal to the printed value")
    for y, marker, colour, label in ((route_a, "o", "tab:blue", "a: u' lambda / nu"), (route_b, "s", "tab:red", "b: sqrt(15) (u' eta / nu)^2"), (route_c, "^", "tab:green", "c: (lambda / eta)^2 / sqrt(15)")):
        ax.loglog(printed, y, marker, ms=9, color=colour, mfc="none", mew=2, label=label)
    for p, a_ in zip(printed, route_a):
        ax.annotate("%g" % p, (p, a_), textcoords="offset points", xytext=(6, -12), fontsize=8)
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_xlabel("Re_lambda printed in Table I")
    ax.set_ylabel("Re_lambda calculated from the other columns")
    ax.set_title("Belin et al. (1996) Table I: is Re_lambda consistent with u', lambda, eta, nu?", fontsize=9)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_table1_relambda.png"), dpi=110)
    print("printed   a (u' lam/nu)   b (isotropic, eta)   c (lam/eta)")
    for p, a_, b_, c_ in zip(printed, route_a, route_b, route_c):
        print("%6g   %8.0f   %8.0f   %8.0f" % (p, a_, b_, c_))


if __name__ == "__main__":
    main()
