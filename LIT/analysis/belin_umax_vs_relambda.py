"""belin_umax_vs_relambda.py  v01  U_max (cm/s) against Re_lambda: the two events of Belin et al. (1996) Fig. 2, the U_max pdf converted from his Fig. 6, our model and our data.
Fig. 2 events (read by eye): a, Re_lambda 659, the velocity swings between about 58 and 113 cm/s: U_max = half the swing = 27.5 cm/s; b, Re_lambda 2850, between about 110 and 255 cm/s: U_max = 72.5 cm/s.
Fig. 6 converted (belin_umax_fixed_r.py): U_max = 1.585 x Re_lambda^(1/2) nu / r_max, x from the lognormal fit, nu and U_eta = nu/eta from the chain of the Table I correlations (cell 2) at each Re_lambda;
median and 10-90 % band for r_max = 5 eta and for r_max = 9.3 eta (the mean apparent radius of Belin's Fig. 5).  Model: U_max = 0.769 Re_lambda^(1/3) U_eta (cm/s with the chain's U_eta).
Our data: U_max/U_eta of the corrected rows of tubes.csv times the chain's U_eta at their Re_lambda.
Usage: python belin_umax_vs_relambda.py     writes belin_umax_vs_relambda.png

Versions  M01 m01.v01 (2026-11-13): first version.
"""
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm

HERE = os.path.dirname(os.path.abspath(__file__))
FIT = os.path.join(HERE, "..", "fittingtool")
sys.path.insert(0, HERE)
sys.path.insert(0, FIT)
import belin_gamma_pdf as bg        # noqa: E402
import belin_rumax_physical as brp  # noqa: E402
import fitdata                      # noqa: E402


def chain_at(Rl):
    Re = brentq(lambda r: brp.chain(math.exp(r))["Re_lambda"] - Rl, math.log(1e2), math.log(1e10))
    return brp.chain(math.exp(Re))


def main():
    mu, s, _ = bg.lognormal_fit()
    rl = np.logspace(1.4, 3.5, 40)
    ch = [chain_at(r) for r in rl]
    u_eta = np.array([c["U_eta"] for c in ch])
    nu = np.array([c["nu"] for c in ch])
    eta = np.array([c["eta"] for c in ch])
    fig, ax = plt.subplots(figsize=(10.5, 6.5))
    for beta, colour in ((5.0, "tab:blue"), (9.3, "tab:green")):
        base = 1.585 * np.sqrt(rl) * nu / (beta * eta)                    # U_max = base x   (cm/s)
        med = base * math.exp(mu)
        lo, hi = base * math.exp(mu + norm.ppf(0.1) * s), base * math.exp(mu + norm.ppf(0.9) * s)
        ax.fill_between(rl, lo, hi, color=colour, alpha=0.2)
        ax.plot(rl, med, "-", color=colour, lw=2, label="Fig. 6 converted, r_max = %g eta: median and 10-90 %%" % beta)
    ax.plot(rl, 0.769 * rl ** (1 / 3) * u_eta, "k--", lw=2, label="our model, U_max = 0.769 Re_lambda^(1/3) U_eta")
    rows = fitdata.load(os.path.join(FIT, "data", "tubes.csv"), os.path.join(FIT, "data", "corrections.json"))
    pts = [(x["re"], x["u"] * chain_at(x["re"])["U_eta"]) for x in rows if x["re"] is not None and x["u"] is not None and 30 < x["re"] < 3000]
    ax.plot([p[0] for p in pts], [p[1] for p in pts], "o", color="tab:red", ms=5, alpha=0.7, label="our tube data (corrected), U_eta from the chain")
    ax.plot([659], [27.5], "*", ms=18, color="k", mfc="gold", label="Belin Fig. 2a event (Re_lambda 659)")
    ax.plot([2850], [72.5], "*", ms=18, color="k", mfc="orange", label="Belin Fig. 2b event (Re_lambda 2850)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Re_lambda")
    ax.set_ylabel("U_max (cm/s)")
    ax.set_title("U_max against Re_lambda: Belin's events, his Fig. 6 converted, our model and data (U_eta from the Table I chain)", fontsize=9)
    ax.legend(fontsize=7.5)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_umax_vs_relambda.png"), dpi=110)
    for Rl in (659, 2850):
        c = chain_at(Rl)
        print("Re_lambda %d: U_eta %.2f cm/s; Fig. 6 median U_max r=5 eta: %.0f, r=9.3 eta: %.0f; model %.1f cm/s" % (Rl, c["U_eta"], 1.585 * math.sqrt(Rl) * c["nu"] / (5 * c["eta"]) * math.exp(mu), 1.585 * math.sqrt(Rl) * c["nu"] / (9.3 * c["eta"]) * math.exp(mu), 0.769 * Rl ** (1 / 3) * c["U_eta"]))


if __name__ == "__main__":
    main()
