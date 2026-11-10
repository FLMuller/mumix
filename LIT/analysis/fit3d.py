"""Three-parameter fit (a, p, q) of the tube model: R_G = a Re_l**p, U_max = beta**q U_eta."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

import math
import sys

import numpy as np
from scipy.optimize import differential_evolution, minimize

sys.path.insert(0, HERE)
import fit_aq as fa
import optimise2d as o

OBS = fa.obs + o.J93
N = len(OBS)
x, S, E, G = fa.x, fa.S, fa.E, fa.G


def model(Rl, a, p, q):
    R = a * Rl**p
    beta = (R / G) ** (1 / (1 + q))
    Vf = (1 - S / beta**4) * beta ** (2 - 2 * q) / E
    return dict(R=R, beta=beta, U=beta**q, gam=4 * x / beta**2, Vf=Vf, share=1 - S / beta**4,
                d=beta * math.sqrt(math.pi / Vf) if Vf > 0 else float("nan"), Rec=beta ** (1 + q))


def residuals(par, obs=OBS):
    a, p, q = par
    out = []
    for s, quantity, Re, val, sig in obs:
        m = model(Re, a, p, q)
        if not (m["Vf"] > 0):
            return np.full(len(obs), 30.0)
        out.append(math.log(m[quantity] / val) / sig)
    return np.array(out)


def chi2(par, obs=OBS):
    return float(np.sum(residuals(par, obs) ** 2))


def hessian(par, h):
    par = np.array(par, float)
    n = len(par)
    H = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            ei = np.zeros(n); ei[i] = h[i]
            ej = np.zeros(n); ej[j] = h[j]
            H[i, j] = (chi2(par + ei + ej) - chi2(par + ei - ej) - chi2(par - ei + ej) + chi2(par - ei - ej)) / (4 * h[i] * h[j])
    return H


if __name__ == "__main__":
    # 2-D reference (p fixed at 0.2)
    r2 = minimize(lambda v: chi2((v[0], 0.2, v[1])), (57.0, 0.88), method="Nelder-Mead", options=dict(xatol=1e-5, fatol=1e-9))
    print("p fixed 0.2 : a=%.2f q=%.3f chi2/N=%.4f" % (r2.x[0], r2.x[1], r2.fun / N))
    de = differential_evolution(chi2, [(5, 200), (-0.2, 0.8), (0.3, 1.8)], seed=3, tol=1e-12, popsize=30, polish=True)
    a, p, q = de.x
    print("p free      : a=%.2f p=%.3f q=%.3f chi2/N=%.4f" % (a, p, q, de.fun / N))
    H = hessian(de.x, (0.5, 0.005, 0.01))
    cov = np.linalg.inv(H / 2)
    sig = np.sqrt(np.diag(cov))
    corr = cov / np.outer(sig, sig)
    print("1-sigma: a +-%.2f  p +-%.3f  q +-%.3f" % tuple(sig))
    print("correlation matrix (a,p,q):\n", corr.round(2))
    print("improvement over p=0.2: delta chi2 = %.2f (1 extra parameter; 1 sigma at 1, 95%% at 3.84)" % (r2.fun - de.fun))
    # profile over p
    print("\nprofile over p (a, q refitted):  p | a | q | chi2/N | delta chi2")
    for pp in (0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50):
        r = minimize(lambda v: chi2((v[0], pp, v[1])), (57.0, 0.88), method="Nelder-Mead", options=dict(xatol=1e-5, fatol=1e-9, maxiter=4000))
        # re-start from a scaled guess so that R at Re_l=200 stays ~170
        a0 = 170 / 200**pp
        r_b = minimize(lambda v: chi2((v[0], pp, v[1])), (a0, 0.88), method="Nelder-Mead", options=dict(xatol=1e-5, fatol=1e-9, maxiter=4000))
        rr = r_b if r_b.fun < r.fun else r
        print("  %.2f | %6.1f | %.3f | %.3f | %+.2f" % (pp, rr.x[0], rr.x[1], rr.fun / N, rr.fun - de.fun))
    # 68 / 95 % joint region of p by profile: delta chi2 = 1 and 3.84 (one parameter of interest)
    ps = np.linspace(-0.1, 0.7, 161)
    prof = []
    for pp in ps:
        best = 1e9
        for a0 in (170 / 200**pp, 57.0):
            r = minimize(lambda v: chi2((v[0], pp, v[1])), (a0, 0.88), method="Nelder-Mead", options=dict(xatol=1e-4, fatol=1e-8, maxiter=3000))
            best = min(best, r.fun)
        prof.append(best)
    prof = np.array(prof)
    for lvl, name in ((1.0, "68%"), (3.84, "95%")):
        m = prof <= de.fun + lvl
        print("p %s interval: %.3f - %.3f" % (name, ps[m].min(), ps[m].max()))
    # predictions
    print("\nmodel at the 3-parameter optimum vs 2-parameter (a=57.0, p=0.2, q=0.879):")
    for Rl in (36, 83, 170, 332, 1000, 1934, 2170):
        m3 = model(Rl, a, p, q)
        m2 = model(Rl, 57.02, 0.2, 0.879)
        print("  Re_l %5d: R_G %.0f/%.0f beta %.2f/%.2f U %.2f/%.2f Vf %.0f%%/%.0f%% share %.0f%%/%.0f%% d %.1f/%.1f" % (
            Rl, m3["R"], m2["R"], m3["beta"], m2["beta"], m3["U"], m2["U"], m3["Vf"] * 100, m2["Vf"] * 100, m3["share"] * 100, m2["share"] * 100, m3["d"], m2["d"]))
    # per-source chi2/N at the optimum
    res = residuals(de.x)
    print("\nper source chi2/N:")
    for src in sorted({o_[0] for o_ in OBS}):
        idx = [i for i, o_ in enumerate(OBS) if o_[0] == src]
        print("  %-14s n=%2d  %.2f" % (src, len(idx), np.mean(res[idx] ** 2)))
