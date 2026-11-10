"""Sigma iteration, small groups (n<3) take the mean sigma of the large groups of the same quantity, else of all large groups."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
import sys

sys.path.insert(0, HERE)

import math
import numpy as np
import iterate_sigma as it

OBS, GROUPS, NAMES = it.OBS, it.GROUPS, it.NAMES
N = len(OBS)


def run(free_p):
    sig = np.array([o[4] for o in OBS], float)
    par = np.array([89.7, 0.12, 0.897]) if free_p else np.array([57.0, 0.879])
    for k in range(300):
        new_par, c = it.fit(sig, free_p, par)
        r = it.logres(new_par, free_p)
        big = {g: math.sqrt(np.mean(r[i] ** 2)) for g, i in GROUPS.items() if len(i) >= 3}
        allmean = np.mean(list(big.values()))
        new = sig.copy()
        for g, idx in GROUPS.items():
            if g in big:
                new[idx] = big[g]
            else:
                same = [v for h, v in big.items() if h[1] == g[1]]
                new[idx] = max(big.values())
        ch = max(abs(new_par - par).max(), abs(new - sig).max())
        par, sig = new_par, new
        if ch < 2e-5:
            break
    return par, sig, k + 1


for free_p in (False, True):
    par, sig, its = run(free_p)
    r = it.logres(par, free_p)
    print("\n=== %s: %d iterations, params %s" % ("a,p,q" if free_p else "a,q (p=0.2)", its, np.round(par, 4)))
    for g, idx in it.GROUPS.items():
        print("  %-16s n=%2d sigma %.1f%%  own rms %.1f%%" % (NAMES[g], len(idx), sig[idx[0]] * 100, math.sqrt(np.mean(r[idx] ** 2)) * 100))
    chi = lambda p_: (lambda rr: 1e9 if rr is None else float(np.sum((rr / sig) ** 2)))(it.logres(p_, free_p))
    k = len(par); h = np.array([0.5, 0.005, 0.01]) if free_p else np.array([0.5, 0.01])
    H = np.zeros((k, k))
    for i in range(k):
        for j in range(k):
            ei = np.zeros(k); ei[i] = h[i]; ej = np.zeros(k); ej[j] = h[j]
            H[i, j] = (chi(par + ei + ej) - chi(par + ei - ej) - chi(par - ei + ej) + chi(par - ei - ej)) / (4 * h[i] * h[j])
    print("  errors", np.round(np.sqrt(np.diag(np.linalg.inv(H / 2))), 4), "chi2/N = %.2f" % (chi(par) / N))
    a, p, q = par if free_p else (par[0], 0.2, par[1])
    for Rl in (83, 332, 1934):
        m = it.f3.model(Rl, a, p, q)
        print("  Re_l %d: beta %.2f Vf %.0f%% share %.0f%% d %.1f" % (Rl, m["beta"], m["Vf"] * 100, m["share"] * 100, m["d"]))
