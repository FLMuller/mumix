import os

HERE = os.path.dirname(os.path.abspath(__file__))
import sys

sys.path.insert(0, HERE)
import math, numpy as np
from collections import defaultdict
from scipy.optimize import differential_evolution
import fit_lfl as f
x, G, S, E = f.x, f.G, f.S, f.E
full = list(f.OBS)
used = [o for o in full if o[0] in ("Ghira", "Jimenez", "Tanahashi")]
mouri = [o for o in full if o[0] == "Mouri"]


def tube(Rl, b, s, kap):
    beta = b * Rl**s
    U = kap * (Rl / math.sqrt(15)) ** 0.5            # U_max/U_eta = kappa u'/U_eta
    R = G * beta * U / 1.0 / (2 * math.pi) * 2 * math.pi / 1.0  # placeholder replaced below
    R = 2 * math.pi * beta * U / f.KB
    Vf = (1 - S / beta**4) * beta**2 / (E * U**2)
    return dict(R=R, beta=beta, U=U, Rec=beta * U, Vf=Vf, share=1 - S / beta**4, d=beta * math.sqrt(math.pi / Vf) if Vf > 0 else float("nan"), gam=4 * x / beta**2)


def predict(o, *par):
    src, qty, Rl, val, ex = o
    m = tube(Rl, *par)
    if qty == "R1e": return m["beta"] / math.sqrt(x)
    if qty == "rmax": return m["beta"]
    if qty == "Rec": return m["Rec"]
    if qty == "d": return m["d"]
    ins = 1 - math.exp(-x * (ex / m["beta"]) ** 2)
    if qty == "Gam": return m["R"] * ins
    if qty == "Uth": return m["R"] / (2 * math.pi * ex) * ins


def logres(par, obs=used):
    return np.array([math.log(predict(o, *par) / o[3]) for o in obs])


G_ = defaultdict(list)
for i, o in enumerate(used): G_[(o[0], o[1])].append(i)
sig = np.full(len(used), 0.1)
par = np.array([4.3, 0.0, 1.0])
for it in range(1, 300):
    de = differential_evolution(lambda v: float(np.sum((logres(v) / sig) ** 2)), [(1, 12), (-0.3, 0.4), (0.2, 3)], seed=1, tol=1e-12, popsize=25, polish=True)
    r = logres(de.x)
    big = {g: max(0.03, math.sqrt(np.mean(r[i] ** 2))) for g, i in G_.items() if len(i) >= 3}
    new = sig.copy()
    for g, idx in G_.items(): new[idx] = big[g] if g in big else max(big.values())
    ch = max(abs(de.x - par).max(), abs(new - sig).max()); par, sig = de.x, new
    if ch < 1e-6: break
r = logres(par)
print("u' model: b=%.3f s=%+.4f kappa=%.3f it=%d chi2/N=%.2f" % (*par, it, float(np.sum((r / sig) ** 2)) / len(used)))
for g, idx in G_.items(): print("  %-20s sigma %.1f%% mean res %+.1f%% rms %.1f%%" % (g, sig[idx[0]] * 100, 100 * np.mean(r[idx]), 100 * math.sqrt(np.mean(r[idx] ** 2))))
print("Mouri Re_c model/lit:", [round(predict(o, *par) / o[3], 2) for o in mouri])
print("Kida:", [(o[1], o[2], round(predict(o, *par) / o[3], 2)) for o in f.KIDA])
for Rl in (83, 170, 332, 1000, 1934):
    m = tube(Rl, *par)
    print("Re_l %5d R_G %.0f beta %.2f U %.2f Rec %.1f Vf %.1f%% share %.0f%% d %.1f" % (Rl, m["R"], m["beta"], m["U"], m["Rec"], m["Vf"] * 100, m["share"] * 100, m["d"]))
