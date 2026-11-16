"""belin_table1_fit.py  v01  Belin et al. (1996) Table I, with the two misprints corrected (belin_table1.csv): the dissipation rate eps and the viscosity nu against Re, each with a straight line in log-log.
eps = 15 nu u'^2 / lambda^2 (cm^2/s^3).  Fit: log10 y = a + b log10 Re by least squares over the 8 runs; the standard error of b is from the covariance of the fit.
Usage: python belin_table1_fit.py     writes belin_table1_fit.png and prints the fits

Versions  M01 m01.v01 (2026-11-13): first version.
"""
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    with open(os.path.join(HERE, "belin_table1.csv"), newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    cell = np.array([int(r["cell"]) for r in rows])
    nu, up, Re, lam = (np.array([float(r[k]) for r in rows]) for k in ("nu_cm2_s", "u_prime_cm_s", "Re_used", "lambda_um"))
    eps = 15 * nu * up ** 2 / (lam * 1e-4) ** 2
    fig, ax = plt.subplots(1, 2, figsize=(13, 5.2))
    grid = np.logspace(4.4, 7, 50)
    for a, y, label in ((ax[0], eps, "eps (cm^2/s^3)"), (ax[1], nu, "nu (cm^2/s)")):
        for c, colour in ((2, "tab:blue"), (1, "tab:red")):
            a.loglog(Re[cell == c], y[cell == c], "o", ms=9, color=colour, label="cell %d" % c)
        coef, cov = np.polyfit(np.log10(Re), np.log10(y), 1, cov=True)
        slope, intercept, err = coef[0], coef[1], np.sqrt(cov[0, 0])
        resid = np.log10(y) - (intercept + slope * np.log10(Re))
        a.loglog(grid, 10 ** intercept * grid ** slope, "k-", lw=1.3, label="%s = %.3g Re^%.2f  (exponent +- %.2f, scatter x/÷ %.1f)" % (label.split(" ")[0], 10 ** intercept, slope, err, 10 ** np.std(resid)))
        a.set_xlabel("Re (Table I, corrected)")
        a.set_ylabel(label)
        a.legend(fontsize=8)
        print("%-4s = %.4g Re^%.3f  (standard error of the exponent %.3f, rms scatter x/÷ %.2f, 8 runs)" % (label.split(" ")[0], 10 ** intercept, slope, err, 10 ** np.std(resid)))
    fig.suptitle("Belin et al. (1996) Table I: dissipation rate and viscosity against Re", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_table1_fit.png"), dpi=110)


if __name__ == "__main__":
    main()
