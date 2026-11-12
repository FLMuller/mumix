"""fit5_geff.py  v01  Closure with an effective circulation constant and no circulation law.

Model: Gamma/nu = G_eff Re_c with Re_c = (r_max/eta)(U_max/U_eta), G_eff = f * 2 pi / K_B = 5.12 (f = 0.583, the factor by which the
circulations listed by Ghira 2022 and Kida 2002 lie below the Burgers value, plot_pairs.py).  Gamma is therefore not a fitted law: the
tube is described by two laws,
    r_max/eta = b Re_l**m          (b, m)
    Re_c      = c Re_l**k          (c, k),        U_max/U_eta = Re_c / (r_max/eta),
and Gamma/nu, the strain gamma/gamma_eta = 4x/beta**2 and the budget quantities V_f, share and d/eta follow from them
(budget as in fit4_floor.py).  Data: the radii of Ghira 2022 and 2025, Jimenez, Tanahashi, Aligolzadeh, and Re_c of Mouri and Hori 2009
(whole tubes) and of Ghira 2022 (intense tubes, converted r_max times converted U_max).  Weights: sigma of each (source, quantity)
group = rms of its own log residuals (floor 5%; groups with fewer than 3 points get the largest group sigma), iterated to convergence.
Variants: A all data; B whole-tube Re_c only (Mouri and Hori); C intense-tube Re_c only (Ghira).
Usage: python fit5_geff.py [burgers]      (burgers: G = 8.78 in place of the adapted 5.12; only the reported Gamma/nu changes,
                                           because the fits use r_max and Re_c, not Gamma)
"""
import math
import os
import sys
from collections import defaultdict

import numpy as np
from scipy.optimize import minimize

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_data_sections as bds
import iterate_sigma as it
import sourcedata as sd

x = sd.x
S = 48 * x * x
E = 0.977 * 4 * x
FLOOR = 0.05


def factor():
    """Equal-source geometric mean of Gamma_listed / (8.78 Re_c) for Ghira 2022 and Kida 2002; Ghira beta*U by Re_lambda."""
    per = defaultdict(list)
    betaU = {}
    for t in bds.tube_items():
        if t["src"] in ("Ghira22", "Kida02") and t["beta"] and t["U"]:
            per[t["src"]].append(math.log(t["RG"] / (sd.G * t["beta"] * t["U"])))
            if t["src"] == "Ghira22":
                betaU[t["Re"]] = t["beta"] * t["U"]
    geo = {k: math.exp(sum(v) / len(v)) for k, v in per.items()}
    return math.sqrt(geo["Ghira22"] * geo["Kida02"]), betaU


FAC, GHIRA_BETAU = factor()
GEFF = sd.G if "burgers" in sys.argv[1:] else FAC * sd.G   # "burgers": the exact Burgers 2 pi/K_B = 8.78

# observations: (group, quantity, Re_lambda, value)
OBS = []
for src, q, Re, val, _ in it.OBS:
    if (src, q) in (("Ghira22 IVS", "beta"), ("Jimenez93 IVS", "beta"), ("Tanahashi01", "beta"), ("Mouri09 all", "Rec")):
        OBS.append((src + " " + ("Re_c" if q == "Rec" else "r_max"), "Rec" if q == "Rec" else "beta", Re, val))
OBS += [("Ghira25 IVS r_max", "beta", 54, 1.12 * 4.29 / 0.97), ("Ghira25 IVS r_max", "beta", 54, 1.12 * 4.23 / 0.97),
        ("Aligolzadeh23 IVS r_max", "beta", 179, 1.12 * 5.1 / 0.95)]
OBS += [("Ghira22 IVS Re_c", "Rec", Re, bu) for Re, bu in sorted(GHIRA_BETAU.items())]


def tube(Re, par):
    b, m, c, k = par
    beta = b * Re**m
    Rec = c * Re**k
    U = Rec / beta
    Vf = (1 - S / beta**4) * beta**2 / (E * U**2)
    return dict(beta=beta, Rec=Rec, U=U, R=GEFF * Rec, gam=4 * x / beta**2, Vf=Vf, share=1 - S / beta**4,
                d=beta * math.sqrt(math.pi / Vf) if Vf > 0 else float("nan"))


def fit(obs):
    n = len(obs)
    groups = defaultdict(list)
    for i, o in enumerate(obs):
        groups[o[0]].append(i)

    def logres(par):
        return np.array([math.log(tube(o[2], par)[o[1]] / o[3]) for o in obs])

    def chi(par, sig):
        r = logres(par)
        return 1e9 if not np.all(np.isfinite(r)) else float(np.sum((r / sig) ** 2))

    sig = np.full(n, 0.15)
    par = np.array([4.8, 0.02, 20.0, 0.1])
    for _ in range(400):
        best = None
        for st in (par, np.array([4.8, 0.02, 20.0, 0.1]), np.array([4.5, 0.05, 10.0, 0.2])):
            r_ = minimize(lambda v: chi(v, sig), st, method="Nelder-Mead", options=dict(xatol=1e-8, fatol=1e-12, maxiter=20000))
            if best is None or r_.fun < best.fun:
                best = r_
        newp = best.x
        r = logres(newp)
        big = {g: max(FLOOR, math.sqrt(np.mean(r[i] ** 2))) for g, i in groups.items() if len(i) >= 3}
        new = sig.copy()
        for g, idx in groups.items():
            new[idx] = big[g] if g in big else (max(big.values()) if big else 0.15)
        ch = max(abs(newp - par).max(), abs(new - sig).max())
        par, sig = newp, new
        if ch < 1e-8:
            break
    h = np.array([0.02, 0.002, 0.05, 0.002])
    H = np.zeros((4, 4))
    for i in range(4):
        for j in range(4):
            ei = np.zeros(4)
            ei[i] = h[i]
            ej = np.zeros(4)
            ej[j] = h[j]
            H[i, j] = (chi(par + ei + ej, sig) - chi(par + ei - ej, sig) - chi(par - ei + ej, sig) + chi(par - ei - ej, sig)) / (4 * h[i] * h[j])
    try:
        err = np.sqrt(np.diag(np.linalg.inv(H / 2)))
    except np.linalg.LinAlgError:
        err = np.full(4, float("nan"))
    r = logres(par)
    return par, err, sig, r, groups, chi(par, sig)


def report(title, obs):
    par, err, sig, r, groups, c2 = fit(obs)
    n = len(obs)
    print("\n=== %s  (N=%d)" % (title, n))
    print("beta = %.3f Re^%.4f (+-%.3f, %.4f);  Re_c = %.3f Re^%.4f (+-%.3f, %.4f);  chi2/N = %.3f" % (par[0], par[1], err[0], err[1], par[2], par[3], err[2], err[3], c2 / n))
    for g, idx in groups.items():
        print("  %-24s n=%2d sigma %5.1f%%  %s" % (g, len(idx), sig[idx[0]] * 100,
              " ".join("%g:%+.0f" % (obs[i][2], 100 * (math.exp(r[i]) - 1)) for i in sorted(idx, key=lambda j: obs[j][2]))))
    for q in ("beta", "Rec"):
        idx = [i for i, o in enumerate(obs) if o[1] == q]
        lit = np.array([obs[i][3] for i in idx])
        mod = np.array([tube(obs[i][2], par)[q] for i in idx])
        print("  RMSE %-4s n=%2d data mean %.2f model mean %.2f rmse %.2f (%.1f%%)" % (q, len(idx), lit.mean(), mod.mean(), math.sqrt(np.mean((mod - lit) ** 2)), 100 * math.sqrt(np.mean((mod - lit) ** 2)) / lit.mean()))
    print("  Re_l    beta  Re_c  Umax  Gamma/nu gam/gam_eta  Vf    share  d/eta")
    for Re in (36, 83, 332, 1000, 1934):
        m = tube(Re, par)
        print("  %5d  %5.2f %5.1f %5.2f %7.0f   %.3f   %4.1f%%  %3.0f%%  %5.1f" % (Re, m["beta"], m["Rec"], m["U"], m["R"], m["gam"], 100 * m["Vf"], 100 * m["share"], m["d"]))
    return par


if __name__ == "__main__":
    print("G = %.3f (adapted factor f = %.3f)" % (GEFF, FAC))
    report("A: all data", OBS)
    report("B: whole-tube Re_c only (Mouri and Hori) + all radii", [o for o in OBS if o[0] != "Ghira22 IVS Re_c"])
    report("C: intense-tube Re_c only (Ghira) + all radii", [o for o in OBS if o[0] != "Mouri09 all Re_c"])
