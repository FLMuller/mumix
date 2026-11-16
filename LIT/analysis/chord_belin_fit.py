"""chord_belin_fit.py  v01  Fit the true tube radius pdf so that the chord model with Belin's gradient cut reproduces Belin's measured radius pdf (Fig. 5).

Forward model (chord_belin_cut.py): a tube of radius r_max (Gaussian width R = r_max / 1.585) and swirl U_max is crossed by the wire at a random impact parameter (uniform in
+-12 R), orientation isotropic (tilt up to --tilt, rotation uniform, thinned by the encounter rate cos alpha); the event is kept when max |dS/ds| >= 5 sigma_gradient
(sigma_gradient = U_eta / (sqrt 15 eta), Belin Fig. 1); the radius read is half the spacing of the two extrema of S.
Kernel: for each of a grid of true radii r_max the crossings are simulated once; K(x | r) is the density of the apparent radius x of the kept events and e(r) the share of
the crossings kept.  A true pdf p(r) then gives the observed pdf  p_obs(x) = N sum_r p(r) w(r) e(r) K(x | r),  w(r) = r (a tube is met in proportion to its size) or 1 (--nobias).
Swirl of a tube: 'MODEL' one value 0.769 Re^(1/3) (Re_lambda 659: 6.7 U_eta);  'INDEPENDENT' the shape of the Tanahashi (2001) swirl pdf with its mean on that value.
Fit: ln median and ln-width s of a single lognormal true pdf, to Belin's pdf below R_m = 19.75 (r_max 31) renormalised to area 1 over that range.  Also shown, nothing fitted: the
Tanahashi (2001) two-lognormal radius pdf.
Usage: python chord_belin_fit.py [--n 30000] [--tilt 90] [--nobias]    writes chord_belin_fit.png
Versions  M01 m01.v01 (2026-11-12): first version.
"""
import argparse
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import least_squares

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chord_model as cm        # noqa: E402
import chord_population as cp   # noqa: E402
import fit_chord as fc          # noqa: E402
import chord_tanahashi_belin as ctb   # noqa: E402

RATIO = cp.RATIO
STEP = float(cm.S_GRID[1] - cm.S_GRID[0])
SIGMA_GRADIENT = 1.0 / math.sqrt(15)
CUT = 5.0
RE_LAMBDA = 659.0
R_GRID = np.exp(np.linspace(math.log(1.8), math.log(70.0), 28))      # true r_max / eta
X_BINS = np.linspace(0.0, 31.3, 63)                                  # apparent r_max / eta, to R_m = 19.75


def swirl(case, rng, n):
    mean = 0.769 * RE_LAMBDA ** (1 / 3)
    if case == "MODEL":
        return np.full(n, mean)
    u = cp.lognormal2(rng, n, cp.SWIRL)
    return u * mean / (cp.lognormal2(np.random.default_rng(5), 200000, cp.SWIRL).mean())


def build_kernel(case, n, tilt_deg, seed):
    """K[i, j]: density of the apparent radius in bin j for the kept events of true radius R_GRID[i]; e[i]: share kept."""
    rng = np.random.default_rng(seed)
    K, eff = np.zeros((len(R_GRID), len(X_BINS) - 1)), np.zeros(len(R_GRID))
    sin_t = math.sin(math.radians(tilt_deg))
    for i, r in enumerate(R_GRID):
        width = r / RATIO
        alpha = np.arcsin(rng.uniform(-sin_t, sin_t, n))
        keep_geo = rng.uniform(size=n) < np.cos(alpha)
        alpha = alpha[keep_geo]
        m = len(alpha)
        phi, b = rng.uniform(0, 2 * math.pi, m), rng.uniform(-12.0, 12.0, m)
        u = swirl(case, rng, m)
        apparent, kept_count = [], 0
        for start in range(0, m, 3000):
            sl = slice(start, start + 3000)
            S = cm.signal(alpha[sl], phi[sl], b[sl])
            grad = np.max(np.abs(np.diff(S, axis=1)), axis=1) / STEP * (u[sl] / cp.GMAX) / width
            ok = grad >= CUT * SIGMA_GRADIENT
            kept_count += int(ok.sum())
            spacing = np.abs(cm.S_GRID[np.argmax(S[ok], axis=1)] - cm.S_GRID[np.argmin(S[ok], axis=1)]) * width
            apparent.append(spacing / 2)
        apparent = np.concatenate(apparent)
        eff[i] = kept_count / m
        if len(apparent) > 5:
            K[i], _ = np.histogram(apparent, bins=X_BINS, density=True)
    return K, eff


def observed(p_true_on_grid, K, eff, bias):
    w = R_GRID if bias else np.ones_like(R_GRID)
    dr = np.gradient(R_GRID)
    p = (p_true_on_grid * w * eff * dr)[:, None] * K
    out = p.sum(0)
    return out / (out.sum() * (X_BINS[1] - X_BINS[0]))


def lognormal_r(median, s):
    return np.exp(-0.5 * ((np.log(R_GRID) - math.log(median)) / s) ** 2) / (R_GRID * s * math.sqrt(2 * math.pi))


def tanahashi_r():
    w1, m1, s1, m2, s2 = cp.RADIUS
    return w1 * lognormal_r(m1, s1) + (1 - w1) * lognormal_r(m2, s2)


def belin_binned():
    rm, p = fc.load()
    x = RATIO * rm
    centres = 0.5 * (X_BINS[1:] + X_BINS[:-1])
    pb = np.interp(centres, x, p / RATIO, left=np.nan, right=np.nan)
    pb[centres > x.max()] = np.nan
    ok = ~np.isnan(pb)
    pb = pb / (np.nansum(pb) * (X_BINS[1] - X_BINS[0]))
    return centres, pb, ok


def stats(centres, p):
    p = np.nan_to_num(p)
    p = p / p.sum()
    cdf = np.cumsum(p)
    return float(np.sum(centres * p)), float(np.interp(0.5, cdf, centres)), float(centres[np.argmax(p)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30000)
    ap.add_argument("--tilt", type=float, default=90.0)
    ap.add_argument("--nobias", action="store_true")
    ap.add_argument("--seed", type=int, default=4)
    args = ap.parse_args()
    bias = not args.nobias
    centres, pb, ok = belin_binned()
    print("Belin Fig. 5 x 1.585: mean %.2f median %.2f mode %.2f" % stats(centres, pb))
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=False)
    for case, colour in (("MODEL", "tab:blue"), ("INDEPENDENT", "tab:red")):
        K, eff = build_kernel(case, args.n, args.tilt, args.seed)
        print("%s: share of crossings kept by the 5 sigma gradient cut, r_max = 2.5 / 5 / 10 / 20 / 40:" % case, np.round(np.interp([2.5, 5, 10, 20, 40], R_GRID, eff), 4))

        def resid(v):
            return (observed(lognormal_r(math.exp(v[0]), v[1]), K, eff, bias) - pb)[ok]
        best = min((least_squares(resid, [math.log(m0), s0], bounds=([math.log(1.5), 0.05], [math.log(40), 1.5])) for m0 in (4, 8, 15) for s0 in (0.3, 0.6)), key=lambda r: r.cost)
        median, s = math.exp(best.x[0]), best.x[1]
        fit = observed(lognormal_r(median, s), K, eff, bias)
        tan = observed(tanahashi_r(), K, eff, bias)
        print("   best single lognormal: median r_max %.2f eta, s %.2f (mean %.2f), rms misfit %.4f;  fitted apparent mean %.2f median %.2f mode %.2f" %
              ((median, s, median * math.exp(s * s / 2), math.sqrt(2 * best.cost / ok.sum())) + stats(centres, fit)))
        print("   Tanahashi two lognormals, nothing fitted: rms misfit %.4f;  apparent mean %.2f median %.2f mode %.2f" %
              ((math.sqrt(np.mean(((tan - pb)[ok]) ** 2)),) + stats(centres, tan)))
        ax = axes[0] if case == "MODEL" else axes[1]
        ax.plot(centres[ok], pb[ok], "ko", ms=4, label="Belin Fig. 5, R_m x 1.585")
        ax.plot(centres, fit, color=colour, lw=2, label="chord model with the fitted lognormal (median %.1f, s %.2f)" % (median, s))
        ax.plot(centres, tan, color="tab:green", lw=1.8, label="chord model with the Tanahashi pdf (not fitted)")
        ax.plot(R_GRID, lognormal_r(median, s) / np.trapezoid(lognormal_r(median, s), R_GRID) * 0.25, color=colour, ls=":", lw=1, label="fitted true pdf (dotted, scaled)")
        ax.plot(R_GRID, tanahashi_r() / np.trapezoid(tanahashi_r(), R_GRID) * 0.25, color="tab:green", ls=":", lw=1, label="Tanahashi true pdf (dotted, scaled)")
        ax.set_xlim(0, 40)
        ax.set_xlabel("r_max / eta")
        ax.set_ylabel("pdf")
        ax.set_title("swirl: %s, Re_lambda %g, tubes met %s, tilt <= %g deg" % (case, RE_LAMBDA, "in proportion to size" if bias else "equally", args.tilt), fontsize=9)
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "chord_belin_fit.png" if bias else "chord_belin_fit_equalchance.png"), dpi=110)


if __name__ == "__main__":
    main()
