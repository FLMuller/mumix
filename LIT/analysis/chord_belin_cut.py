"""chord_belin_cut.py  v01  The radius pdf of Belin et al. (1996) from the chord model with Belin's own detection: the velocity increment over 2 eta in the extreme tails.

Belin (1996, Sect. 3, Fig. 1): the pdf of the velocity increments over r = 2 eta is, in the dissipative range, the pdf of the velocity gradient; the events kept are those in its
extreme tails, where the pdf (standard deviation 1) is below 1e-3: |gradient| >= 5 sigma (his Fig. 1 crosses 1e-3 at s = +-5); the tail area is 2.6e-3.  Here the gradient dS/ds of the
sensed signal is used directly (s = path length = int U dt), with sigma = sqrt(eps / 15 nu) = U_eta / (sqrt 15 eta) = 0.258 U_eta / eta, the longitudinal value.
The radius he reads is the spacing of the two extrema of the signal / 3.17 (the Gaussian width R); here the same spacing / 2 is drawn, which is r_max (his R x 1.585).

Model (chord_model.py geometry, chord_population.py population)
    tubes      radius r_max / eta and swirl U_max / U_eta from the Tanahashi (2001) pdfs (two lognormals each); swirl drawn independently of the radius ('INDEPENDENT'),
               or the same for every tube ('MODEL': 0.769 Re^(1/3), the best model).  The swirl scale is that of the best model at the Re_lambda of the experiment, U_max / U_eta = 0.769 Re_lambda^(1/3) (Belin Fig. 1: 659, so 6.7), the Tanahashi pdf giving only the shape.
               (A first version used the Re_lambda = 80 swirl for this Re_lambda = 659 record: no tube reached the cut.)
    crossings  impact parameter uniform in +-12 R (a tube of radius R is met in proportion to R unless --nobias), tilt up to --tilt degrees, rotation uniform.
    selection  an event is kept when max |dS/ds| >= 5 sigma_gradient.  The cut is absolute, so strong tubes pass more easily (the relative cut f of chord_tanahashi_belin.py
               has no such effect).
Usage: python chord_belin_cut.py [--events 200000] [--tilt 90] [--nobias]    writes chord_belin_cut.png

Versions  M01 m01.v01 (2026-11-12): first version.
          m01.v02 (2026-11-12): the cut is on the velocity gradient itself (5 sigma_gradient), not on an increment over a rounded number of grid steps; swirl at the Re_lambda of the record.
"""
import argparse
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chord_model as cm        # noqa: E402
import chord_population as cp   # noqa: E402
import fit_chord as fc          # noqa: E402

RATIO = cp.RATIO
SIGMA_GRADIENT = 1.0 / math.sqrt(15)                   # rms of the longitudinal velocity gradient, sqrt(eps / 15 nu) = U_eta / (sqrt 15 eta)
CUT_SIGMAS = 5.0
STEP = float(cm.S_GRID[1] - cm.S_GRID[0])


def kept_radii(case, n, tilt_deg, bias, seed, re_lambda, cut_sigmas=CUT_SIGMAS):
    """(apparent r_max / eta of the kept events, true r_max, true U of the kept events, fraction kept)."""
    cp.BIAS = bias
    rng = np.random.default_rng(seed)
    r, u, alpha, phi, b = cp.events(rng, n, case, math.radians(tilt_deg))
    if case != 'MODEL':                                                    # keep the shape of the Tanahashi swirl pdf, put its mean on the best model at this Re_lambda
        u = u * 0.769 * re_lambda ** (1 / 3) / cp.population(np.random.default_rng(seed + 11), 300000, case)[1].mean()
    else:
        u = np.full(len(r), 0.769 * re_lambda ** (1 / 3))
    width = r / RATIO                                                      # Gaussian width R of each tube, in eta
    threshold = cut_sigmas * SIGMA_GRADIENT                                # U_eta / eta
    kept, spacing = np.zeros(len(r), bool), np.zeros(len(r))
    chunk = 3000
    for start in range(0, len(r), chunk):
        sl = slice(start, start + chunk)
        S = cm.signal(alpha[sl], phi[sl], b[sl])
        scale = u[sl] / cp.GMAX
        gradient = np.max(np.abs(np.diff(S, axis=1)), axis=1) / STEP * scale / width[sl]     # largest |dS/ds| of the event, s in eta
        kept[sl] = gradient >= threshold
        spacing[sl] = np.abs(cm.S_GRID[np.argmax(S, axis=1)] - cm.S_GRID[np.argmin(S, axis=1)]) * width[sl]
    return spacing[kept] / 2, r[kept], u[kept], float(kept.mean())


def stats(x, bins):
    h, e = np.histogram(x, bins=bins, density=True)
    c = 0.5 * (e[1:] + e[:-1])
    return float(np.mean(x)), float(np.median(x)), float(c[np.argmax(h)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", type=int, default=200000)
    ap.add_argument("--tilt", type=float, default=90.0)
    ap.add_argument("--nobias", action="store_true")
    ap.add_argument("--seed", type=int, default=2)
    ap.add_argument("--re", type=float, default=659.0, help="Re_lambda of the experiment (Belin Fig. 1: 659)")
    args = ap.parse_args()
    rm, p_belin = fc.load()
    bins = np.linspace(0, 30, 61)
    fig, ax = plt.subplots(figsize=(8, 5.2))
    ax.plot(RATIO * rm, p_belin / RATIO, "ko", ms=4, label="Belin et al. (1996) Fig. 5, R_m x 1.585")
    print("Belin Fig. 5 x 1.585 (R_m < 19):   mean %.2f  median %.2f  mode %.2f" % tuple(RATIO * v for v in (np.sum(rm * p_belin) / np.sum(p_belin), np.interp(0.5, np.cumsum(p_belin) / np.sum(p_belin), rm), rm[np.argmax(p_belin)])))
    for case, colour in (("INDEPENDENT", "tab:red"), ("MODEL", "tab:blue")):
        rad, rtrue, utrue, frac = kept_radii(case, args.events, args.tilt, not args.nobias, args.seed, args.re)
        inside = rad[rad < RATIO * 19.75]                                    # the range of Belin's figure
        m, md, mo = stats(inside, bins)
        print("%-12s kept %.3f%% of crossings (%d): apparent r_max mean %.2f median %.2f mode %.2f (below 19.75 R_m);  true of kept: r_max mean %.2f, U mean %.2f"
              % (case, 100 * frac, len(rad), m, md, mo, rtrue.mean(), utrue.mean()))
        ax.hist(inside, bins, density=True, histtype="step", color=colour, lw=1.8, label="chord model, Belin's cut (gradient > 5 sigma), swirl: " + case)
    ax.set_xlim(0, 30)
    ax.set_xlabel("r_max / eta")
    ax.set_ylabel("pdf")
    ax.set_title("tilt <= %g deg, tubes met %s" % (args.tilt, "equally" if args.nobias else "in proportion to size"), fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "chord_belin_cut.png"), dpi=110)


if __name__ == "__main__":
    main()
