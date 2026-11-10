"""Iterate the weights: sigma for each (source, quantity) group = rms of that group's own log residuals.

Start from the assumed sigmas, fit the parameters, set every group's sigma to the rms of its residuals
at that fit, refit, and repeat until the parameters and sigmas stop changing.  A group with few points can
be fitted exactly (sigma -> 0, weight -> infinity), so a floor SIGMA_MIN is applied.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

import math
import sys
from collections import defaultdict

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, HERE)
import fit3d as f3

OBS = f3.OBS
GROUPS = defaultdict(list)
for i, (s, qn, Re, val, sig) in enumerate(OBS):
    GROUPS[(s, qn)].append(i)
NAMES = {("Ghira22 IVS", "R"): "Ghira R_G", ("Ghira22 IVS", "beta"): "Ghira r_max", ("Jimenez93 IVS", "beta"): "Jimenez r_max",
         ("Mouri09 all", "Rec"): "Mouri Re_c", ("Kida02 all", "U"): "Kida swirl", ("Kida02 all", "d"): "Kida spacing",
         ("Tanahashi01", "beta"): "Tanahashi r_max"}


def logres(par, free_p):
    a, p, q = par if free_p else (par[0], 0.2, par[1])
    out = np.empty(len(OBS))
    for i, (s, qn, Re, val, sig) in enumerate(OBS):
        m = f3.model(Re, a, p, q)
        if not (m["Vf"] > 0):
            return None
        out[i] = math.log(m[qn] / val)
    return out


def fit(sig, free_p, start):
    def f(par):
        r = logres(par, free_p)
        return 1e9 if r is None else float(np.sum((r / sig) ** 2))
    best = None
    for st in (start,):
        r = minimize(f, st, method="Nelder-Mead", options=dict(xatol=1e-6, fatol=1e-10, maxiter=6000))
        best = r if best is None or r.fun < best.fun else best
    return best.x, best.fun


def iterate(free_p, floor, verbose=True):
    sig = np.array([o[4] for o in OBS], float)
    par = np.array([89.7, 0.12, 0.897]) if free_p else np.array([57.0, 0.879])
    hist = []
    for it in range(1, 201):
        par_new, c = fit(sig, free_p, par)
        r = logres(par_new, free_p)
        sig_new = sig.copy()
        for (s, qn), idx in GROUPS.items():
            sig_new[idx] = max(floor, math.sqrt(np.mean(r[idx] ** 2)))
        change = max(abs(par_new - par).max() / 1.0, abs(sig_new - sig).max())
        par, sig = par_new, sig_new
        hist.append((it, par.copy(), c / len(OBS)))
        if change < 2e-5:
            break
    return par, sig, hist, it


if __name__ == "__main__":
    n = len(OBS)
    for free_p in (False, True):
        for floor in (0.0, 0.03, 0.05):
            if free_p is False and floor == 0.0:
                pass
            par, sig, hist, its = iterate(free_p, floor)
            r = logres(par, free_p)
            print("\n=== %s, floor %.0f%%: converged after %d iterations" % ("a,p,q free" if free_p else "a,q (p=0.2)", floor * 100, its))
            print("parameters:", np.round(par, 4))
            print("first iterations:", "; ".join("%d: %s" % (h[0], np.round(h[1], 3)) for h in hist[:4]))
            for (s, qn), idx in GROUPS.items():
                print("  %-16s n=%2d sigma %.1f%% (assumed %.0f%%)  rms residual %.1f%%" % (NAMES[(s, qn)], len(idx), sig[idx[0]] * 100, OBS[idx[0]][4] * 100, math.sqrt(np.mean(r[idx] ** 2)) * 100))
            # parameter errors from the curvature with the final sigmas
            def chi2(p_):
                rr = logres(p_, free_p)
                return 1e9 if rr is None else float(np.sum((rr / sig) ** 2))
            k = len(par)
            h = np.array([0.5, 0.005, 0.01]) if free_p else np.array([0.5, 0.01])
            H = np.zeros((k, k))
            for i in range(k):
                for j in range(k):
                    ei = np.zeros(k); ei[i] = h[i]
                    ej = np.zeros(k); ej[j] = h[j]
                    H[i, j] = (chi2(par + ei + ej) - chi2(par + ei - ej) - chi2(par - ei + ej) + chi2(par - ei - ej)) / (4 * h[i] * h[j])
            cov = np.linalg.inv(H / 2)
            print("  1-sigma errors:", np.round(np.sqrt(np.diag(cov)), 4), " chi2/N = %.2f (1.0 by construction when no group is at the floor)" % (chi2(par) / n))
            m = f3.model
            if free_p:
                a, p, q = par
            else:
                a, q = par; p = 0.2
            print("  model: " + "; ".join("Re_l %d: beta %.2f Vf %.0f%% share %.0f%% d %.1f" % (Rl, m(Rl, a, p, q)["beta"], m(Rl, a, p, q)["Vf"] * 100, m(Rl, a, p, q)["share"] * 100, m(Rl, a, p, q)["d"]) for Rl in (83, 332, 1934)))
