"""Four-parameter closure: R_G = a Re_l**p (total circulation), U_max/U_eta = beta**q * Re_l**s, beta from R_G = 8.78 beta U."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

import math, sys
import numpy as np
from collections import defaultdict
from scipy.optimize import differential_evolution, minimize
sys.path.insert(0, HERE)
import iterate_sigma as it
x = 1.2564312086261697; KB = 1 - math.exp(-x); G = 2 * math.pi / KB; S = 48 * x * x; E = 0.977 * 4 * x
ALL = list(it.OBS)
USED = [o for o in ALL if o[0] != "Kida02 all"]
KIDA = [o for o in ALL if o[0] == "Kida02 all"]
USED += [("Ghira25 IVS", "beta", 54, 1.12 * 4.29 / 0.97, 0.12), ("Ghira25 IVS", "beta", 54, 1.12 * 4.23 / 0.97, 0.12)]
N = len(USED)
NAMES = {("Ghira22 IVS", "R"): "Ghira R_G", ("Ghira22 IVS", "beta"): "Ghira r_max", ("Jimenez93 IVS", "beta"): "Jimenez r_max", ("Mouri09 all", "Rec"): "Mouri Re_c",
         ("Tanahashi01", "beta"): "Tanahashi r_max", ("Ghira25 IVS", "beta"): "Ghira25 r_max"}
GROUPS = defaultdict(list)
for i, o in enumerate(USED): GROUPS[(o[0], o[1])].append(i)


def tube(Rl, a, p, q, s):
    R = a * Rl**p
    beta = (R / (G * Rl**s)) ** (1 / (1 + q))
    U = beta**q * Rl**s
    Vf = (1 - S / beta**4) * beta**2 / (E * U**2)
    return dict(R=R, beta=beta, U=U, Rec=R / G, gam=4 * x / beta**2, Vf=Vf, share=1 - S / beta**4, d=beta * math.sqrt(math.pi / Vf) if Vf > 0 else float("nan"))


def logres(par):
    return np.array([math.log(tube(o[2], *par)[o[1]] / o[3]) for o in USED])


def chi(par, sig):
    r = logres(par)
    return 1e9 if not np.all(np.isfinite(r)) else float(np.sum((r / sig) ** 2))


sig = np.full(N, 0.15); par = np.array([91.5, 0.12, 0.9, 0.0])
for k in range(400):
    best = None
    for st in (par, np.array([91.5, 0.12, 0.9, 0.0]), np.array([100, 0.1, 1.2, 0.2])):
        r_ = minimize(lambda v: chi(v, sig), st, method="Nelder-Mead", options=dict(xatol=1e-7, fatol=1e-11, maxiter=12000))
        if best is None or r_.fun < best.fun: best = r_
    newp = best.x
    r = logres(newp)
    big = {g: math.sqrt(np.mean(r[i] ** 2)) for g, i in GROUPS.items() if len(i) >= 3}
    new = sig.copy()
    for g, idx in GROUPS.items(): new[idx] = big[g] if g in big else max(big.values())
    ch = max(abs(newp - par).max(), abs(new - sig).max()); par, sig = newp, new
    if ch < 1e-7: break
print("4-param: a=%.2f p=%.4f q=%.4f s=%.4f  chi2/N=%.3f chi2=%.2f (iterations %d)" % (*par, chi(par, sig) / N, chi(par, sig), k + 1))
for seed in range(3):
    de = differential_evolution(lambda v: chi(v, sig), [(5, 600), (-0.3, 0.8), (0.1, 2.5), (-0.6, 0.9)], seed=seed, tol=1e-12, popsize=40, polish=True)
    print("  DE seed %d: %s chi2 %.3f" % (seed, np.round(de.x, 4), de.fun))
h = np.array([0.5, 0.005, 0.01, 0.005]); H = np.zeros((4, 4))
for i in range(4):
    for j in range(4):
        ei = np.zeros(4); ei[i] = h[i]; ej = np.zeros(4); ej[j] = h[j]
        H[i, j] = (chi(par + ei + ej, sig) - chi(par + ei - ej, sig) - chi(par - ei + ej, sig) + chi(par - ei - ej, sig)) / (4 * h[i] * h[j])
cov = np.linalg.inv(H / 2); err = np.sqrt(np.diag(cov)); corr = cov / np.outer(err, err)
print("errors", np.round(err, 4)); print("corr\n", np.round(corr, 2))
r = logres(par)
for g, idx in GROUPS.items():
    print(" ", NAMES[g], "sigma %.1f%%" % (sig[idx[0]] * 100), " ".join("%g:%+.0f" % (USED[i][2], 100 * (math.exp(r[i]) - 1)) for i in sorted(idx, key=lambda j: USED[j][2])))
for g, idx in GROUPS.items():
    if len(idx) > 3:
        print("  trend %-16s %+.3f" % (NAMES[g], np.polyfit(np.log([USED[i][2] for i in idx]), r[idx], 1)[0]))
by = defaultdict(list)
for o in USED: by[o[1]].append(o)
for q_, L in by.items():
    lit = np.array([o[3] for o in L]); mod = np.array([tube(o[2], *par)[q_] for o in L]); rm = math.sqrt(np.mean((mod - lit) ** 2))
    print("  RMSE %-5s n=%2d lit mean %.2f model mean %.2f rmse %.2f (%.1f%%)" % (q_, len(L), lit.mean(), mod.mean(), rm, 100 * rm / lit.mean()))
print("overall rms rel %.1f%%, max %.1f%%" % (100 * math.sqrt(np.mean((np.exp(r) - 1) ** 2)), 100 * np.abs(np.exp(r) - 1).max()))
print("\nmodel:")
for Rl in (36, 54, 83, 170, 274, 332, 1000, 1934, 2170):
    m = tube(Rl, *par)
    print("  Re_l %5d R_G %4.0f beta %.2f Rec %5.1f Umax %.2f gam/gam_eta %.2f Vf %4.1f%% share %.0f%% d %.1f" % (Rl, m["R"], m["beta"], m["Rec"], m["U"], m["gam"], m["Vf"] * 100, m["share"] * 100, m["d"]))
print("\nKida (not used):")
for o in KIDA:
    mm = tube(o[2], *par)[o[1]]; print("  %-5s Re_l %3d lit %6.2f model %6.2f ratio %.2f" % (o[1], o[2], o[3], mm, mm / o[3]))
