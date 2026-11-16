"""chord_belin_fit_inputs.py  v01  Fit the two input distributions of the chord model until the read (outlet) distributions match Belin et al. (1996).
Inputs  (1) the true radius: one lognormal, median m_r (eta) and ln-width s_r;  (2) the product x = Re_f / Re_lambda^(1/2) (r_max U_max / nu = 1.585 x Re_lambda^(1/2)): one lognormal, median m_x and ln-width s_x.
        Both sampled by inverse CDF (chord_belin_x.simulate), Belin's 5 sigma gradient cut, Re_lambda 659 and 2850.
Outlets the radius read (r_max = half the extrema spacing) against Fig. 5 (belin_fig5_digitised.csv, r_max = 1.585 R_m, below 30 eta) and the product read (x_read) against Fig. 6 (all markers, binned in x, 0-40);
        4 histograms (two Re_lambda); each compared as density over its range; misfit = sum of rms differences relative to the peak of the target.
Method  Nelder-Mead on (ln m_r, ln s_r, ln m_x, ln s_x), common random numbers (fixed seeds, EVENTS crossings per Re_lambda).
Usage: python chord_belin_fit_inputs.py [--events 25000]      prints each step and the best parameters; the figure of the best is made by chord_belin_x.py (command printed at the end)

Versions  M01 m01.v01 (2026-11-13): first version.
          m01.v02 (2026-11-13): --start; the radius is size-weighted (chord_belin_x.simulate bias).
"""
import argparse
import math
import os
import sys

import numpy as np
from scipy.optimize import minimize

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import belin_gamma_pdf as bg    # noqa: E402
import chord_belin_x as cbx     # noqa: E402

R5 = np.linspace(0, 30, 61)
X6 = np.linspace(0, 40, 21)


def targets():
    d5 = np.loadtxt(os.path.join(HERE, "belin_fig5_digitised.csv"), delimiter=",", skiprows=1)
    r = cbx.RATIO * d5[:, 0]
    c5 = 0.5 * (R5[1:] + R5[:-1])
    t5 = np.interp(c5, r, d5[:, 1] / cbx.RATIO, left=0.0, right=0.0)
    t5 = t5 / (t5.sum() * 0.5)
    xs, ps = bg.raw_points()
    t6 = np.array([ps[(xs >= a) & (xs < b)].mean() if ((xs >= a) & (xs < b)).any() else np.nan for a, b in zip(X6[:-1], X6[1:])])
    ok = ~np.isnan(t6)
    t6 = t6 / (np.nansum(t6) * 2.0)
    return t5, t6, ok


def outlets(params, events):
    m_r, s_r, m_x, s_x = params
    out = []
    for row, Rl in enumerate((659, 2850)):
        res = cbx.simulate(Rl, events, math.log(m_x), s_x, 5 + row, s_r, m_r)
        h5 = np.histogram(res["r_read"], R5)[0].astype(float)
        h5 = h5 / (h5.sum() * 0.5)
        h6 = np.histogram(res["x_read"], X6)[0].astype(float)
        h6 = h6 / (h6.sum() * 2.0)
        out.append((h5, h6, res))
    return out


def misfit(params, events, t5, t6, ok):
    total = 0.0
    for h5, h6, _ in outlets(params, events):
        total += math.sqrt(np.mean((h5 - t5) ** 2)) / t5.max() + math.sqrt(np.mean((h6 - t6)[ok] ** 2)) / np.nanmax(t6)
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", type=int, default=25000)
    ap.add_argument("--bmax", type=float, default=12.0, help="impact parameter limit in R (chord_belin_x.BMAX)")
    ap.add_argument("--start", type=float, nargs=4, default=None, metavar=("R_MEDIAN", "R_WIDTH", "X_MEDIAN", "X_WIDTH"), help="start of the search (default: radius 3.0 / 0.6, x of the Fig. 6 fit)")
    args = ap.parse_args()
    cbx.BMAX = args.bmax
    t5, t6, ok = targets()
    mu0, s0, _ = bg.lognormal_fit()
    start = np.array([math.log(3.0), math.log(0.6), mu0, math.log(s0)]) if args.start is None else np.log(np.array(args.start))

    def objective(v):
        value = misfit((math.exp(v[0]), math.exp(v[1]), math.exp(v[2]), math.exp(v[3])), args.events, t5, t6, ok)
        print("  r median %.2f ln-width %.2f | x median %.2f ln-width %.2f | misfit %.4f" % (math.exp(v[0]), math.exp(v[1]), math.exp(v[2]), math.exp(v[3]), value), flush=True)
        return value
    res = minimize(objective, start, method="Nelder-Mead", options={"maxfev": 90, "xatol": 0.02, "fatol": 0.003, "initial_simplex": np.array([start, start + [0.3, 0, 0, 0], start + [0, 0.3, 0, 0], start + [0, 0, 0.2, 0], start + [0, 0, 0, 0.2]])})
    m_r, s_r, m_x, s_x = (math.exp(v) for v in res.x)
    print("best: r_max median %.2f eta, ln-width %.2f; x median %.2f, ln-width %.2f; misfit %.4f" % (m_r, s_r, m_x, s_x, res.fun))
    print("figure: python chord_belin_x.py --rmedian %.3f --sharp %.3f --median %.4f --narrow %.4f" % (m_r, s_r, m_x / math.exp(mu0), s_x / s0))


if __name__ == "__main__":
    main()
