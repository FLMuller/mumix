import os

HERE = os.path.dirname(os.path.abspath(__file__))
import sys

sys.path.insert(0, HERE)
import math, numpy as np
from scipy.optimize import differential_evolution
import fit_lfl as f
def run(obs, sigma=0.10, label=""):
    f.USED[:] = obs
    sig = np.full(len(obs), sigma)
    best = None
    for seed in range(4):
        de = differential_evolution(lambda v: f.chi2(v, sig), [(5, 600), (-0.3, 0.8), (0.3, 1.8)], seed=seed, tol=1e-12, popsize=30, polish=True)
        if best is None or de.fun < best.fun: best = de
    r = f.logres(best.x)
    print("%-34s a=%.1f p=%+.3f q=%.3f  chi2/N=%.2f (sigma 10%%)" % (label, *best.x, best.fun / len(obs)))
    return best.x
full = list(f.OBS)
sets = {
 "all 30, equal sigma": full,
 "intense only (Ghira, Jimenez, Tanah.)": [o for o in full if o[0] in ("Ghira", "Jimenez", "Tanahashi")],
 "Ghira only": [o for o in full if o[0] == "Ghira"],
 "all but Ghira Gamma": [o for o in full if not (o[0] == "Ghira" and o[1] == "Gam")],
 "radii + Mouri Re_c": [o for o in full if o[1] in ("R1e", "rmax", "Rec")],
}
for k, v in sets.items():
    par = run(v, label=k)
    # how the other data compare at this fit
    rows = []
    for o in full + f.KIDA:
        if o in v: continue
        rows.append("%s %s %.2f" % (o[0][:4], o[1], f.predict(o, *par) / o[3]))
    print("    unused-data model/lit:", "; ".join(rows[:12]))
