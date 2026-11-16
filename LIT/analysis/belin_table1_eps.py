"""belin_table1_eps.py  v01  Table I of Belin et al. (1996): the dissipation rate eps calculated two ways, which must agree if the table is consistent.
    from eta      eps = nu^3 / eta^4
    from lambda   eps = 15 nu u'^2 / lambda^2
(cm, s units; 1 cm^2/s^3 = 1e-4 W/kg).  Points are labelled with Re_lambda = u' lambda / nu.
Usage: python belin_table1_eps.py     writes belin_table1_eps.png and prints the values

Versions  M01 m01.v01 (2026-11-13): first version.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = [(2, 1.6e-2, 39, 8, 3000, 127), (2, 2.1e-2, 284, 94, 1520, 26), (2, 4.6e-4, 128, 37, 276, 2.9), (2, 3.3e-4, 136, 52, 320, 2), (2, 4.4e-4, 128, 27, 262, 3.4),
        (2, 1.1e-3, 64, 13, 680, 12), (1, 2.7e-2, 118, 29, 1740, 64), (1, 2.6e-4, 27.4, 6.1, 187, 5)]      # cell, nu, U, u', lambda (um), eta (um)


def main():
    nu, U, up, lam, eta = (np.array([r[i] for r in ROWS], float) for i in range(1, 6))
    lam_cm, eta_cm = lam * 1e-4, eta * 1e-4
    eps_eta = nu ** 3 / eta_cm ** 4
    eps_lam = 15 * nu * up ** 2 / lam_cm ** 2
    eps_u3 = up ** 3 / 1.0                                                      # u'^3 / L with L = 1 cm, for the order of magnitude only
    Rl = up * lam_cm / nu
    fig, ax = plt.subplots(figsize=(7, 6.2))
    lim = [1e1, 1e11]
    ax.plot(lim, lim, "k-", lw=1, label="equal")
    ax.loglog(eps_lam, eps_eta, "o", ms=9, color="tab:blue")
    for x, y, r in zip(eps_lam, eps_eta, Rl):
        ax.annotate("%.0f" % r, (x, y), textcoords="offset points", xytext=(6, 4), fontsize=8)
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_xlabel("eps from lambda: 15 nu u'^2 / lambda^2  (cm^2/s^3)")
    ax.set_ylabel("eps from eta: nu^3 / eta^4  (cm^2/s^3)")
    ax.set_title("Belin et al. (1996) Table I: the dissipation rate two ways (labels: Re_lambda)", fontsize=9)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_table1_eps.png"), dpi=110)
    print("Re_lambda   eps(eta) cm2/s3   eps(lambda) cm2/s3   eps(eta) W/kg   ratio eta/lambda")
    for r, a, b in zip(Rl, eps_eta, eps_lam):
        print("%7.0f     %10.3g        %10.3g          %9.3g     %5.2f" % (r, a, b, a * 1e-4, a / b))


if __name__ == "__main__":
    main()
