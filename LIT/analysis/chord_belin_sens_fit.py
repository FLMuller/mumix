"""chord_belin_sens_fit.py  v01  Fit the tube inputs of the wire-and-tube model (chord_belin_sens.py) to Belin's Fig. 5 and Fig. 6 with the incidence angle taken from the flow (sigma of sin(alpha) = u' / U of the chain, no free angle).
Inputs  r_max: lognormal (median m_r, ln-width s_r); U_max = S x 0.769 Re_lambda^(1/3) U_eta x lognormal(0, s_u): the DNS scaling of the swirl times a scale S, spread s_u (independent of r_max).  Fitted: ln m_r, ln s_r, ln S, ln s_u.
Outlets the r_max read against Fig. 5 and x read (Belin's rule dS / (2 * 0.14), R_m = spacing / 3.17) against Fig. 6, at Re_lambda 255 and 659 (Belin's worms are below Re_lambda 700); misfit as chord_belin_fit_inputs.py.
Output  the best parameters; belin_sens_fit.png: r_max, x and U_max pdfs of the best.
Usage:  python chord_belin_sens_fit.py [--n 15000] [--maxfev 70]

Versions  M01 m01.v01 (2026-11-13): first version.
"""
import argparse
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import minimize

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chord_belin_sens as cs         # noqa: E402
import chord_belin_fit_inputs as fi   # noqa: E402
import belin_gamma_pdf as bg          # noqa: E402

RELAMBDA = (255, 659)
SIGMA_ALPHA = None                                                   # std of sin(alpha); None: u'/U of the chain (--sigma-alpha sets it)


def config(v):
    cfg = dict(cs.BASE)
    cfg.update(inputs="dns", sigma_alpha=SIGMA_ALPHA, r_median=math.exp(v[0]), r_sigma=math.exp(v[1]), umax_scale=math.exp(v[2]), u_sigma=math.exp(v[3]))
    return cfg


def misfit(v, n, t5, t6, ok, use=("r", "x")):
    """Sum over the Reynolds numbers of the rms differences relative to the peak of the target: the r_max pdf (Fig. 5) if 'r' is in use, the x pdf (Fig. 6) if 'x' is."""
    total = 0.0
    for row, Rl in enumerate(RELAMBDA):
        res = cs.run(Rl, config(v), n, 11 + row)
        rd, w = res["rd"], res["w"]
        if rd.sum() < 50:
            return 10.0
        h5, h6 = cs.pdf(res["r_read"][rd], w[rd], fi.R5), cs.pdf(res["x_belin"][rd], w[rd], fi.X6)
        total += ("r" in use) * math.sqrt(np.mean((h5 - t5) ** 2)) / t5.max() + ("x" in use) * math.sqrt(np.mean((h6 - t6)[ok] ** 2)) / np.nanmax(t6)
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=15000)
    ap.add_argument("--maxfev", type=int, default=70)
    ap.add_argument("--start", type=float, nargs=4, default=[5.0, 0.5, 4.0, 0.7])
    ap.add_argument("--phases", action="store_true", help="fit in phases: r_max on Fig. 5, then the swirl on Fig. 6, then all four on both")
    ap.add_argument("--sigma-alpha", type=float, default=None, help="std of sin(alpha), the same at every Re_lambda (default: u'/U of the chain)")
    ap.add_argument("--tag", default="", help="suffix of the figure file name")
    args = ap.parse_args()
    global SIGMA_ALPHA
    SIGMA_ALPHA = args.sigma_alpha
    t5, t6, ok = fi.targets()
    start = np.log(np.array(args.start))

    steps = (0.3, 0.3, 0.4, 0.3)
    stages = [((0, 1, 2, 3), ("r", "x"), args.maxfev)] if not args.phases else [((0, 1), ("r",), 40), ((2, 3), ("x",), 40), ((0, 1, 2, 3), ("r", "x"), args.maxfev)]
    best = start.copy()
    for free, use, maxfev in stages:
        def objective(u, free=free, use=use):
            v = best.copy()
            v[list(free)] = u
            value = misfit(v, args.n, t5, t6, ok, use)
            print("  [%s] r median %.2f ln-width %.2f | U_max scale %.2f x DNS, ln-width %.2f | misfit %.4f" % ("".join(use), *(math.exp(q) for q in v), value), flush=True)
            return value
        x0 = best[list(free)]
        simplex = np.array([x0] + [x0 + np.eye(len(free))[j] * steps[free[j]] for j in range(len(free))])
        res = minimize(objective, x0, method="Nelder-Mead", options={"maxfev": maxfev, "xatol": 0.02, "fatol": 0.003, "initial_simplex": simplex})
        best[list(free)] = res.x
        print("stage %s fitted on %s: r median %.2f ln-width %.2f | U_max scale %.2f ln-width %.2f | misfit %.4f" % (free, "".join(use), *(math.exp(q) for q in best), res.fun), flush=True)
    res.x = best
    res.fun = misfit(best, args.n, t5, t6, ok)
    print("best: r_max median %.2f eta, ln-width %.2f; U_max = %.2f x DNS (0.769 Re^(1/3) U_eta), ln-width %.2f; misfit %.4f" % (*(math.exp(u) for u in res.x), res.fun), flush=True)
    xs, ps = bg.raw_points()
    d5 = np.loadtxt(os.path.join(HERE, "belin_fig5_digitised.csv"), delimiter=",", skiprows=1)
    c5, c6 = 0.5 * (fi.R5[1:] + fi.R5[:-1]), 0.5 * (fi.X6[1:] + fi.X6[:-1])
    fig, ax = plt.subplots(len(RELAMBDA), 3, figsize=(17, 6.3 * len(RELAMBDA)))
    for row, Rl in enumerate(RELAMBDA):
        out = cs.run(Rl, config(res.x), 6 * args.n, 11 + row)
        rd, k, w = out["rd"], out["kept"], out["w"]
        ue, U = out["ue"], out["U"]
        print("Re_lambda %d: sigma(sin alpha) %.2f, U %.0f cm/s, selected %.1f %%, read %.1f %% of those; U_max of tubes: all %.0f, selected %.0f, read ones %.0f cm/s; read amplitude median %.0f cm/s" %
              (Rl, out["sigma_alpha"], U * ue, 100 * w[k].sum() / w.sum(), 100 * w[rd].sum() / w[k].sum(), cs.wquantile(out["umax"], w, 0.5) * ue, cs.wquantile(out["umax"][k], w[k], 0.5) * ue,
               cs.wquantile(out["umax"][rd], w[rd], 0.5) * ue, cs.wquantile(out["amp"][rd], w[rd], 0.5) * ue))
        a = ax[row, 0]
        rb = np.linspace(0, 30, 61)
        a.plot(0.5 * (rb[1:] + rb[:-1]), cs.pdf(out["r"], w, rb), color="tab:blue", lw=2, label="tubes crossed (volume-weighted)")
        a.plot(0.5 * (rb[1:] + rb[:-1]), cs.pdf(out["r"][k], w[k], rb), color="tab:green", lw=2, ls="--", label="selected (cut)")
        a.plot(c5, cs.pdf(out["r_read"][rd], w[rd], fi.R5), color="tab:red", lw=2.5, label="read")
        a.plot(c5, t5, "ko", ms=3, label="Belin Fig. 5")
        a.set_xlabel("r_max / eta")
        a.set_title("Re_lambda %d: r_max" % Rl, fontsize=10)
        a = ax[row, 1]
        a.plot(c6, cs.pdf(out["x_belin"][rd], w[rd], fi.X6), color="tab:red", lw=2.5, label="read, Belin's rule")
        a.plot(c6[ok], t6[ok], "ko", ms=3, label="Belin Fig. 6")
        a.set_xlabel("x = Re_f / Re_lambda^(1/2)")
        a.set_title("Re_lambda %d: x" % Rl, fontsize=10)
        a = ax[row, 2]
        ub = np.linspace(0, 400, 101)
        a.plot(0.5 * (ub[1:] + ub[:-1]), cs.pdf(out["umax"] * ue, w, ub), color="tab:blue", lw=2, label="U_max of the tubes crossed")
        a.plot(0.5 * (ub[1:] + ub[:-1]), cs.pdf(out["umax"][k] * ue, w[k], ub), color="tab:green", lw=2, ls="--", label="selected")
        a.plot(0.5 * (ub[1:] + ub[:-1]), cs.pdf(out["amp"][rd] * ue, w[rd], ub), color="tab:red", lw=2.5, label="read amplitude (half swing)")
        a.axvline(U * ue / cs.cbv.MEAN_FRACTION, color="k", ls=":", label="Omega R")
        a.set_xlabel("U_max (cm/s)")
        a.set_title("Re_lambda %d: U_max (U_eta %.2f cm/s, U %.0f cm/s)" % (Rl, ue, U * ue), fontsize=10)
        for k_ in range(3):
            ax[row, k_].set_ylabel("pdf")
            ax[row, k_].legend(fontsize=8)
    fig.suptitle("wire-and-tube model, incidence angle from u'/U, fitted: r_max median %.2f eta (ln-width %.2f); U_max %.2f x DNS (ln-width %.2f)" % tuple(math.exp(u) for u in res.x), fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_sens_fit%s.png" % args.tag), dpi=90)


if __name__ == "__main__":
    main()
