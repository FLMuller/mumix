import os

HERE = os.path.dirname(os.path.abspath(__file__))
import math, sys
import numpy as np
from scipy.optimize import differential_evolution
sys.path.insert(0, HERE)
import iterate_sigma as it
f3 = it.f3
ALL = list(it.OBS)
USED = [o for o in ALL if o[0] != "Kida02 all"]
KIDA = [o for o in ALL if o[0] == "Kida02 all"]
NEW = [("Ghira25 IVS", "beta", 54, 1.12 * 4.29 / 0.97, 0.12), ("Ghira25 IVS", "beta", 54, 1.12 * 4.23 / 0.97, 0.12)]
USED += NEW
it.OBS = USED
it.GROUPS = {}
for i, o in enumerate(USED): it.GROUPS.setdefault((o[0], o[1]), []).append(i)
it.NAMES[("Ghira25 IVS", "beta")] = "Ghira25 r_max"
N = len(USED)
sig = np.array([o[4] for o in USED], float); par = np.array([81.0, 0.137, 0.89])
for k in range(300):
    new_par, _ = it.fit(sig, True, par)
    r = it.logres(new_par, True)
    big = {g: math.sqrt(np.mean(r[i] ** 2)) for g, i in it.GROUPS.items() if len(i) >= 3}
    new = sig.copy()
    for g, idx in it.GROUPS.items(): new[idx] = big[g] if g in big else max(big.values())
    ch = max(abs(new_par - par).max(), abs(new - sig).max()); par, sig = new_par, new
    if ch < 1e-7: break
chi = lambda v: (lambda rr: 1e9 if rr is None else float(np.sum((rr / sig) ** 2)))(it.logres(v, True))
print("local: a=%.2f p=%.4f q=%.4f chi2/N=%.3f (iterations %d)" % (*par, chi(par) / N, k + 1))
best = None
for seed in range(5):
    de = differential_evolution(chi, [(5, 400), (-0.3, 0.8), (0.3, 1.8)], seed=seed, tol=1e-12, popsize=30, polish=True)
    print("  DE seed %d: a=%.2f p=%.4f q=%.4f chi2=%.3f" % (seed, *de.x, de.fun))
r = it.logres(par, True)
print("\nresiduals by Re_lambda (model/lit - 1, %):")
for g, idx in it.GROUPS.items():
    print(" ", it.NAMES[g], "sigma %.1f%%" % (sig[idx[0]] * 100))
    print("    ", "  ".join("%g:%+.0f" % (USED[i][2], 100 * (math.exp(r[i]) - 1)) for i in sorted(idx, key=lambda j: USED[j][2])))
# trend of the residual against Re_lambda per group (slope of log-residual vs log Re_l)
for g, idx in it.GROUPS.items():
    if len(idx) > 3:
        x_ = np.log([USED[i][2] for i in idx]); y_ = r[idx]
        s = np.polyfit(x_, y_, 1)[0]
        print("  trend %-20s d(ln res)/d(ln Re_l) = %+.3f" % (it.NAMES[g], s))
print("\nmodel:")
for Rl in (54, 83, 170, 274, 332, 1000, 1934, 2170):
    m = f3.model(Rl, *par)
    print("  Re_l %5d R_G %4.0f beta %.2f Rec %5.1f Umax %.2f gam/gam_eta %.2f Vf %4.1f%% share %.0f%% d %.1f" % (Rl, m["R"], m["beta"], m["Rec"], m["U"], m["gam"], m["Vf"] * 100, m["share"] * 100, m["d"]))
print("\nnot used (Kida): model/lit")
for o in KIDA:
    print("  %-5s Re_l %3d lit %6.2f model %6.2f ratio %.2f" % (o[1], o[2], o[3], f3.model(o[2], *par)[o[1]], f3.model(o[2], *par)[o[1]] / o[3]))
