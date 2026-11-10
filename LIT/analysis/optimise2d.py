"""2-D optimisation of the tube model constants (a, q) against the literature observations.

chi2(a, q) is evaluated on a grid, minimised globally with differential evolution, and the
parameter errors come from the curvature of chi2 at the minimum (Hessian).  Two objectives:
  A  kinematics and spacing   (Ghira 2022, Mouri 2009, Kida 2002, Tanahashi 2001, Jimenez 1993)
  B  A plus the volume fraction / vortex share of the vorticity region above the rms value
     (Jimenez 1993: 25 % of the volume, 80 % of the dissipation; Hosokawa 1989: 20 %, 75 %)
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

import math
import sys

import numpy as np
from scipy.optimize import differential_evolution, minimize

sys.path.insert(0, HERE)
import fit_aq as fa

# ---- extra observation sets -----------------------------------------------------------------
# Jimenez et al. 1993, Table 3: 1/e radius R/eta; r_max = 1.12 R
J93 = [("Jimenez93 IVS", "beta", Re, 1.12 * R, 0.12) for Re, R in ((35.8, 4.22), (62.8, 4.16), (94.5, 4.16), (168.1, 3.85))]
# volume fraction and vortex share of the region above the rms vorticity (definition-dependent: wide sigma)
SHARE = [("Jimenez93 >rms", "Vf", 130, 0.25, 0.30), ("Jimenez93 >rms", "share", 130, 0.80, 0.12),
         ("Hosokawa89 low thr", "Vf", 100, 0.20, 0.30), ("Hosokawa89 low thr", "share", 100, 0.75, 0.12)]


def model(Rl, a, q):
    m = fa.model(Rl, a, q)
    m["share"] = 1 - fa.S / m["beta"] ** 4
    return m


def residuals(p, obs):
    a, q = p
    out = []
    for s, quantity, Re, val, sig in obs:
        m = model(Re, a, q)
        if not (m["Vf"] > 0):
            return np.full(len(obs), 30.0)
        out.append(math.log(m[quantity] / val) / sig)
    return np.array(out)


def chi2(p, obs):
    return float(np.sum(residuals(p, obs) ** 2))


def hessian_errors(p, obs, h=(0.5, 0.01)):
    """Numerical Hessian of chi2/2 -> covariance (a, q)."""
    p = np.array(p, float)
    H = np.zeros((2, 2))
    f0 = chi2(p, obs)
    for i in range(2):
        for j in range(2):
            ei = np.zeros(2); ei[i] = h[i]
            ej = np.zeros(2); ej[j] = h[j]
            H[i, j] = (chi2(p + ei + ej, obs) - chi2(p + ei - ej, obs) - chi2(p - ei + ej, obs) + chi2(p - ei - ej, obs)) / (4 * h[i] * h[j])
    cov = np.linalg.inv(H / 2) * 1.0          # delta chi2 = 1  <->  1 sigma
    return cov


def run(label, obs):
    de = differential_evolution(lambda p: chi2(p, obs), [(30, 90), (0.3, 1.8)], seed=1, tol=1e-10, polish=True)
    a, q = de.x
    cov = hessian_errors(de.x, obs)
    sa, sq = math.sqrt(cov[0, 0]), math.sqrt(cov[1, 1])
    rho = cov[0, 1] / (sa * sq)
    n = len(obs)
    print("\n== %s: %d observations" % (label, n))
    print("global minimum a=%.2f q=%.3f  chi2=%.2f (rms %.2f sigma)" % (a, q, de.fun, math.sqrt(de.fun / n)))
    print("1-sigma (delta chi2 = 1): sigma_a=%.2f sigma_q=%.3f correlation %.2f" % (sa, sq, rho))
    # joint confidence region extents (68 %: dchi2 = 2.30, 95 %: 6.18)
    A = np.linspace(40, 75, 141)
    Q = np.linspace(0.5, 1.4, 181)
    grid = np.array([[chi2((aa, qq), obs) for aa in A] for qq in Q])
    for lvl, name in ((2.30, "68%"), (6.18, "95%")):
        mask = grid <= de.fun + lvl
        print("%s region: a %.1f-%.1f, q %.2f-%.2f" % (name, A[mask.any(axis=0)].min(), A[mask.any(axis=0)].max(), Q[mask.any(axis=1)].min(), Q[mask.any(axis=1)].max()))
    return de.x, de.fun, A, Q, grid


if __name__ == "__main__":
    base = fa.obs + J93
    xa, fA, A, Q, gA = run("A kinematics + spacing", base)
    xb, fB, _, _, gB = run("B = A + volume fraction and share", base + SHARE)
    print("\nchi2 table for objective A (rows q, columns a); minimum marked *")
    asel = [48, 52, 56, 60, 64]
    print("q\\a  " + "  ".join("%6.0f" % a for a in asel))
    for qq in (0.60, 0.70, 0.80, 0.85, 0.90, 0.95, 1.00, 1.10, 1.20):
        row = []
        for aa in asel:
            v = chi2((aa, qq), base)
            row.append("%6.1f" % v)
        print("%.2f %s" % (qq, "  ".join(row)))
    print("\nat the objective-A optimum, objective-B chi2 = %.1f; at the B optimum, A chi2 = %.1f" % (chi2(xa, base + SHARE), chi2(xb, base)))
    for name, p in (("A", xa), ("B", xb), ("current a=56.5,q=0.90", (56.5, 0.90))):
        print("\nmodel at", name, "a=%.1f q=%.3f" % tuple(p))
        for Rl in (83, 100, 170, 330, 1934):
            m = model(Rl, *p)
            print("  Re_l %5d: beta %.2f U %.2f Vf %.0f%% share %.0f%% d/eta %.1f" % (Rl, m["beta"], m["U"], m["Vf"] * 100, m["share"] * 100, m["d"]))
