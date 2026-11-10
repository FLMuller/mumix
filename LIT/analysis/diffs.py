import os

HERE = os.path.dirname(os.path.abspath(__file__))
import sys

sys.path.insert(0, HERE)
import math, numpy as np
import iterate_sigma as it
from collections import defaultdict
fits = {"a,q (p=0.2): a=53.00 q=0.859": (False, np.array([52.9984, 0.8591])), "a,p,q: a=81.05 p=0.137 q=0.891": (True, np.array([81.0534, 0.1366, 0.8913]))}
cat = {"R": "R_G=G/nu", "beta": "r_max/eta", "Rec": "Re_c", "U": "U_max/U_eta", "d": "d/eta"}
for name, (fp, par) in fits.items():
    r = it.logres(par, fp)
    diff = np.exp(r) - 1  # (model-lit)/lit
    print("\n==", name)
    print("%-16s %2s %10s %10s %10s" % ("source, quantity", "n", "mean diff", "mean |d|", "rms"))
    for g, idx in it.GROUPS.items():
        d = diff[idx]
        print("%-16s %2d %+9.1f%% %9.1f%% %9.1f%%" % (it.NAMES[g], len(idx), d.mean() * 100, np.abs(d).mean() * 100, np.sqrt(np.mean(d**2)) * 100))
    print("-- by category (all sources pooled)")
    bycat = defaultdict(list)
    for g, idx in it.GROUPS.items(): bycat[g[1]] += list(idx)
    for c, idx in bycat.items():
        d = diff[idx]
        print("%-16s %2d %+9.1f%% %9.1f%% %9.1f%%" % (cat[c], len(idx), d.mean() * 100, np.abs(d).mean() * 100, np.sqrt(np.mean(d**2)) * 100))
    d = diff
    print("%-16s %2d %+9.1f%% %9.1f%% %9.1f%%" % ("all", len(d), d.mean() * 100, np.abs(d).mean() * 100, np.sqrt(np.mean(d**2)) * 100))
