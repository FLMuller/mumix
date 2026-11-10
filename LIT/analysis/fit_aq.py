"""Fit the prefactor a and swirl exponent q of the tube model to literature observations (p_lambda = 0.2 fixed).

Model (Re_l = Taylor-scale Reynolds number):
    R_G  = a * Re_l**0.2                 circulation Reynolds number Gamma/nu
    beta = (R_G / G)**(1/(1+q))          core radius r_max / eta, G = 2 pi/(1 - exp(-x)) = 8.78
    U    = beta**q                       peak swirl / U_eta
    gam  = 4 x / beta**2                 strain / gamma_eta
    Vf   = (1 - S/beta**4) * beta**(2-2q) / E     core volume fraction to r_max
    d    = beta * sqrt(pi / Vf)          mean tube spacing / eta
Each observation i gives a residual ln(model/obs)/sigma; the fit minimises the sum of squares.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
import sys

sys.path.insert(0, HERE)

import math

import numpy as np
from scipy.optimize import minimize

x = 1.2564312
k = 1 - math.exp(-x)
G = 2 * math.pi / k
S = 48 * x * x
E = 0.977 * 4 * x


def model(Rl, a, q):
    R = a * Rl**0.2
    beta = (R / G) ** (1 / (1 + q))
    Vf = (1 - S / beta**4) * beta ** (2 - 2 * q) / E
    return dict(R=R, beta=beta, U=beta**q, gam=4 * x / beta**2, Vf=Vf,
                d=beta * math.sqrt(math.pi / Vf) if Vf > 0 else float("nan"), Rec=beta ** (1 + q))


# ---- observations: (set, quantity, Re_lambda, value, sigma) ---------------------------
Re_g = [90, 148, 191, 242, 314, 292, 399]
c_g = [14.36, 13.01, 12.19, 11.32, 10.92, 11.34, 10.35]
Rr = [4.28, 4.23, 4.10, 4.06, 3.98, 3.98, 3.90]
RB = [.96, .98, .97, .98, .98, .98, .97]
obs = []
for Re, c, r, rb in zip(Re_g, c_g, Rr, RB):
    obs.append(("Ghira22 IVS", "R", Re, c * math.sqrt(Re), 0.15))                 # Gamma/nu
    obs.append(("Ghira22 IVS", "beta", Re, 1.12 * r / rb, 0.12))                  # r_max = 1.12 R_B
Re_m = [332, 488, 716, 945, 1080, 1304, 719, 1098, 1416, 1693, 1934]
Re0 = [20.5, 20.2, 21.2, 25.1, 25.3, 23.8, 20.8, 22.8, 25.4, 25.4, 28.0]
for Re, r0 in zip(Re_m, Re0):
    obs.append(("Mouri09 all", "Rec", Re, r0, 0.25))                              # biased: R0 high, V0 low
obs += [("Kida02 all", "U", 83, 3.1 * 1.175, 0.15), ("Kida02 all", "U", 170, 3.3 * 1.175, 0.15),  # core-boundary swirl -> peak
        ("Kida02 all", "d", 83, 15.6, 0.15), ("Kida02 all", "d", 170, 17.2, 0.15),
        ("Tanahashi01", "beta", 200, 4.5, 0.15)]


def residuals(params, subset=None):
    a, q = params
    res = []
    for s, quantity, Re, val, sig in obs:
        if subset and s not in subset:
            continue
        m = model(Re, a, q)
        if not (m["Vf"] > 0):
            return np.full(len(obs), 10.0)
        res.append(math.log(m[quantity] / val) / sig)
    return np.array(res)


def fit(subset=None, start=(56.4, 0.81)):
    f = lambda p: float(np.sum(residuals(p, subset) ** 2))
    best = minimize(f, start, method="Nelder-Mead", options=dict(xatol=1e-4, fatol=1e-6, maxiter=4000))
    return best.x, best.fun, len(residuals(best.x, subset))


if __name__ == "__main__":
    for name, sub in (("all data", None),
                      ("Ghira22 IVS only", {"Ghira22 IVS"}),
                      ("all-tube data only (Mouri, Kida)", {"Mouri09 all", "Kida02 all"}),
                      ("without Mouri", {"Ghira22 IVS", "Kida02 all", "Tanahashi01"})):
        (a, q), cost, n = fit(sub)
        print("%-34s a=%.1f q=%.2f  chi2=%.1f for %d points (rms residual %.2f sigma)" % (name, a, q, cost, n, math.sqrt(cost / n)))
    base = np.sum(residuals((56.4, 0.81)) ** 2)
    print("baseline a=56.4 q=0.81 chi2=%.1f" % base)
    # per-source fit quality at the all-data optimum
    (a, q), cost, n = fit(None)
    print("\nper-observation residuals (model/obs) at a=%.1f q=%.2f" % (a, q))
    for s, quantity, Re, val, sig in obs:
        m = model(Re, a, q)[quantity]
        print("%-14s %-5s Re_l=%4d obs %.3g model %.3g ratio %.2f" % (s, quantity, Re, val, m, m / val))
    # profile of chi2 over q (a re-fitted for each q)
    print("\nchi2 profile")
    for qq in (0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2):
        f = lambda a_: float(np.sum(residuals((a_[0], qq)) ** 2))
        b = minimize(f, [a], method="Nelder-Mead")
        print("q=%.1f  best a=%.1f  chi2=%.1f" % (qq, b.x[0], b.fun))
