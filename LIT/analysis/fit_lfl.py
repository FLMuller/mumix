"""Like-for-like fit of (a, p, q): every observation is compared with the model Burgers profile evaluated
the way its source defines the quantity (no conversion factors).

Model: r_max = beta eta, U_max = beta**q U_eta, total R_G = Gamma/nu = a Re_l**p = 8.78 beta**(1+q),
Burgers swirl U(r)/U_eta = R_G/(2 pi r/eta) * (1 - exp(-x (r/r_max)**2)),  R_B = r_max/sqrt(x) = 1/e radius of the vorticity.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
import sys

sys.path.insert(0, HERE)

import math
from collections import defaultdict

import numpy as np
from scipy.optimize import differential_evolution, minimize

x = 1.2564312086261697
KB = 1 - math.exp(-x)
G = 2 * math.pi / KB
S = 48 * x * x
E = 0.977 * 4 * x
RB_OVER_RMAX = 1 / math.sqrt(x)

# ---- literature observations: (source, quantity, Re_lambda, value, extra) ------------------------
OBS = []
Re_g = [90, 148, 191, 242, 314, 292, 399]
c_g = [14.36, 13.01, 12.19, 11.32, 10.92, 11.34, 10.35]       # Re_Gamma / sqrt(Re_lambda)
R_ivs = [4.28, 4.23, 4.10, 4.06, 3.98, 3.98, 3.90]            # R_ivs / eta
for Re, c, r in zip(Re_g, c_g, R_ivs):
    OBS.append(("Ghira", "R1e", Re, r, None))
for Re, c, r in zip(Re_g, c_g, R_ivs):
    OBS.append(("Ghira", "Gam", Re, c * math.sqrt(Re), r))   # Gamma inside R_ivs, extra = R_ivs/eta
for Re, r in zip([35.8, 62.8, 94.5, 168.1], [4.22, 4.16, 4.16, 3.85]):
    OBS.append(("Jimenez", "R1e", Re, r, None))
OBS.append(("Tanahashi", "rmax", 200, 4.5, None))
Re_m = [332, 488, 716, 945, 1080, 1304, 719, 1098, 1416, 1693, 1934]
Re0 = [20.5, 20.2, 21.2, 25.1, 25.3, 23.8, 20.8, 22.8, 25.4, 25.4, 28.0]
for Re, r0 in zip(Re_m, Re0):
    OBS.append(("Mouri", "Rec", Re, r0, None))
USED = list(OBS)
# Kida et al. (2002), Table 2: not used in the fit (red rows)
KIDA = [("Kida", "rmax", 83, 5.2, None), ("Kida", "rmax", 170, 5.4, None),
        ("Kida", "Uth", 83, 3.1, 5.2), ("Kida", "Uth", 170, 3.3, 5.4),
        ("Kida", "Gam", 83, 110.0, 5.2), ("Kida", "Gam", 170, 123.0, 5.4),
        ("Kida", "d", 83, 15.6, None), ("Kida", "d", 170, 17.2, None)]
ALL = USED + KIDA


def tube(Rl, a, p, q):
    R = a * Rl**p
    beta = (R / G) ** (1 / (1 + q))
    Vf = (1 - S / beta**4) * beta ** (2 - 2 * q) / E
    return dict(R=R, beta=beta, U=beta**q, gam=4 * x / beta**2, Vf=Vf, share=1 - S / beta**4,
                d=beta * math.sqrt(math.pi / Vf) if Vf > 0 else float("nan"), Rec=beta ** (1 + q))


def predict(obs, a, p, q):
    src, qty, Rl, val, extra = obs
    m = tube(Rl, a, p, q)
    if not m["Vf"] > 0:
        return float("nan")
    if qty == "R1e":
        return m["beta"] * RB_OVER_RMAX
    if qty == "rmax":
        return m["beta"]
    if qty == "Rec":
        return m["Rec"]
    if qty == "d":
        return m["d"]
    inside = 1 - math.exp(-x * (extra / m["beta"]) ** 2)          # circulation fraction inside radius `extra`
    if qty == "Gam":
        return m["R"] * inside
    if qty == "Uth":
        return m["R"] / (2 * math.pi * extra) * inside
    raise KeyError(qty)


GROUPS = defaultdict(list)
for i, o in enumerate(USED):
    GROUPS[(o[0], o[1])].append(i)


def logres(par, obs=USED):
    out = np.array([math.log(predict(o, *par) / o[3]) for o in obs])
    return out


def chi2(par, sig):
    r = logres(par)
    return 1e9 if not np.all(np.isfinite(r)) else float(np.sum((r / sig) ** 2))


def fit(sig, start):
    best = None
    for st in (start, np.array([80.0, 0.14, 0.9]), np.array([120.0, 0.05, 1.0])):
        r = minimize(lambda v: chi2(v, sig), st, method="Nelder-Mead", options=dict(xatol=1e-7, fatol=1e-11, maxiter=8000))
        if best is None or r.fun < best.fun:
            best = r
    return best.x


def iterate(start=(80.0, 0.14, 0.9)):
    sig = np.full(len(USED), 0.15)
    par = np.array(start)
    for it in range(1, 400):
        new_par = fit(sig, par)
        r = logres(new_par)
        big = {g: math.sqrt(np.mean(r[i] ** 2)) for g, i in GROUPS.items() if len(i) >= 3}
        new = sig.copy()
        for g, idx in GROUPS.items():
            new[idx] = big[g] if g in big else max(big.values())
        change = max(abs(new_par - par).max(), abs(new - sig).max())
        par, sig = new_par, new
        if change < 1e-7:
            break
    return par, sig, it


def errors(par, sig):
    h = np.array([0.5, 0.005, 0.01])
    H = np.zeros((3, 3))
    for i in range(3):
        for j in range(3):
            ei = np.zeros(3); ei[i] = h[i]
            ej = np.zeros(3); ej[j] = h[j]
            H[i, j] = (chi2(par + ei + ej, sig) - chi2(par + ei - ej, sig) - chi2(par - ei + ej, sig) + chi2(par - ei - ej, sig)) / (4 * h[i] * h[j])
    cov = np.linalg.inv(H / 2)
    err = np.sqrt(np.diag(cov))
    return err, cov / np.outer(err, err)


if __name__ == "__main__":
    par, sig, its = iterate()
    err, corr = errors(par, sig)
    r = logres(par)
    N = len(USED)
    print("N=%d iterations %d  a=%.2f p=%.4f q=%.4f  chi2/N=%.3f  errors %s" % (N, its, *par, float(np.sum((r / sig) ** 2)) / N, np.round(err, 4)))
    print("corr", np.round(corr, 2).tolist())
    names = {}
    for g, idx in GROUPS.items():
        print("  %-18s n=%2d sigma %.1f%%  rms %.1f%%  mean log-res %+.1f%%" % (g, len(idx), sig[idx[0]] * 100, 100 * math.sqrt(np.mean(r[idx] ** 2)), 100 * np.mean(r[idx])))
    # global check
    de = differential_evolution(lambda v: chi2(v, sig), [(5, 300), (-0.2, 0.8), (0.3, 1.8)], seed=2, tol=1e-12, popsize=30, polish=True)
    print("DE check: %s chi2 %.4f vs %.4f" % (np.round(de.x, 4), de.fun, chi2(par, sig)))
    print("\nKida (not used): model / literature")
    for o in KIDA:
        print("  %-5s %-5s Re_l %3d lit %7.2f model %7.2f ratio %.2f" % (o[0], o[1], o[2], o[3], predict(o, *par), predict(o, *par) / o[3]))
    for Rl in (83, 332, 1934):
        m = tube(Rl, *par)
        print("Re_l %d: R_G %.0f beta %.2f U %.2f Vf %.0f%% share %.0f%% d %.1f" % (Rl, m["R"], m["beta"], m["U"], m["Vf"] * 100, m["share"] * 100, m["d"]))
