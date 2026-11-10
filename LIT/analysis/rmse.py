import os

HERE = os.path.dirname(os.path.abspath(__file__))
import sys

sys.path.insert(0, HERE)
import math, numpy as np
import iterate_sigma as it
from collections import defaultdict
f3 = it.f3
fits = {"a,q (p=0.2): a=53.00 q=0.859": (53.0, 0.2, 0.8591), "a,p,q: a=81.05 p=0.137 q=0.891": (81.0534, 0.1366, 0.8913)}
cat = {"R": "R_G", "beta": "r_max/eta", "Rec": "Re_c", "U": "U_max/U_eta", "d": "d/eta"}
for name, par in fits.items():
    print("\n==", name)
    print("%-16s %2s %9s %9s %8s %8s" % ("source, quantity", "n", "mean lit", "rmse", "bias", "rmse/mean"))
    def rows(idx):
        m = np.array([f3.model(it.OBS[i][2], *par)[it.OBS[i][1]] for i in idx]); o = np.array([it.OBS[i][3] for i in idx])
        return m, o
    def show(label, idx):
        m, o = rows(idx); e = m - o
        print("%-16s %2d %9.2f %9.2f %+8.2f %7.1f%%" % (label, len(idx), o.mean(), math.sqrt(np.sum(e**2) / len(idx)), e.mean(), 100 * math.sqrt(np.mean(e**2)) / o.mean()))
    for g, idx in it.GROUPS.items(): show(it.NAMES[g], idx)
    print("-- pooled by category")
    bc = defaultdict(list)
    for g, idx in it.GROUPS.items(): bc[g[1]] += list(idx)
    for c, idx in bc.items(): show(cat[c], idx)
