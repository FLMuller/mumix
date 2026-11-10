import os

HERE = os.path.dirname(os.path.abspath(__file__))
import sys

sys.path.insert(0, HERE)
import math, numpy as np
from collections import defaultdict
import fit_lfl as f
from scipy.optimize import differential_evolution

full = list(f.OBS)
used = [o for o in full if o[0] in ("Ghira", "Jimenez", "Tanahashi")]
mouri = [o for o in full if o[0] == "Mouri"]
f.USED[:] = used
f.GROUPS.clear()
for i, o in enumerate(used):
    f.GROUPS[(o[0], o[1])].append(i)
N = len(used)
for floor in (0.0, 0.03, 0.05):
    sig = np.full(N, 0.15); par = np.array([148.0, 0.12, 1.27])
    for it in range(1, 400):
        new_par = f.fit(sig, par)
        r = f.logres(new_par)
        big = {g: max(floor, math.sqrt(np.mean(r[i] ** 2))) for g, i in f.GROUPS.items() if len(i) >= 3}
        new = sig.copy()
        for g, idx in f.GROUPS.items():
            new[idx] = big[g] if g in big else max(big.values())
        ch = max(abs(new_par - par).max(), abs(new - sig).max())
        par, sig = new_par, new
        if ch < 1e-7: break
    err, corr = f.errors(par, sig)
    r = f.logres(par)
    print("\nfloor %.0f%%: N=%d it=%d a=%.1f p=%+.3f q=%.3f chi2/N=%.2f err %s corr %s" % (floor * 100, N, it, *par, float(np.sum((r / sig) ** 2)) / N, np.round(err, 3), np.round([corr[0, 1], corr[0, 2], corr[1, 2]], 2)))
    for g, idx in f.GROUPS.items():
        print("   %-20s n=%2d sigma %.1f%%  mean res %+.1f%%" % (g, len(idx), sig[idx[0]] * 100, 100 * np.mean(r[idx])))
    de = differential_evolution(lambda v: f.chi2(v, sig), [(5, 600), (-0.3, 0.8), (0.3, 1.8)], seed=1, tol=1e-12, popsize=30, polish=True)
    print("   DE global: %s chi2 %.3f vs %.3f" % (np.round(de.x, 3), de.fun, f.chi2(par, sig)))
    if floor == 0.03:
        keep = (par, sig)
par, sig = keep
print("\n=== chosen: floor 3% ===", np.round(par, 3))
for o in used:
    pass
rel = lambda o: f.predict(o, *par) / o[3]
print("RMSE per quantity (absolute, % of lit mean):")
by = defaultdict(list)
for o in used: by[o[1]].append(o)
for q_, L in by.items():
    lit = np.array([o[3] for o in L]); mod = np.array([f.predict(o, *par) for o in L])
    print("  %-5s n=%2d lit %.2f..%.2f mean %.2f model mean %.2f rmse %.2f (%.1f%%)" % (q_, len(L), lit.min(), lit.max(), lit.mean(), mod.mean(), math.sqrt(np.mean((mod - lit) ** 2)), 100 * math.sqrt(np.mean((mod - lit) ** 2)) / lit.mean()))
print("\nnot used: model/lit")
for o in mouri + f.KIDA:
    print("  %-7s %-5s Re_l %5.0f lit %7.2f model %7.2f  ratio %.2f" % (o[0], o[1], o[2], o[3], f.predict(o, *par), f.predict(o, *par) / o[3]))
print("\nmodel table")
for Rl in (36, 83, 170, 274, 332, 1000, 1934, 2170):
    m = f.tube(Rl, *par)
    print("Re_l %5d R_G %6.0f beta %.2f Rec %5.1f U %.2f gam/gam_eta %.2f Vf %4.1f%% share %.0f%% d %.1f" % (Rl, m["R"], m["beta"], m["Rec"], m["U"], m["gam"], m["Vf"] * 100, m["share"] * 100, m["d"]))
