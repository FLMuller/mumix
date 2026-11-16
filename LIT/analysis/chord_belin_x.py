"""chord_belin_x.py  v01  The chord model with the swirl distribution of Belin's Fig. 6: what the wire reads at Re_lambda 659 and 2850, against Belin's Figs. 5 and 6.
Tubes   radius r_max / eta = beta from the Tanahashi (2001) two-lognormal pdf (chord_population.RADIUS); a tube is met in proportion to its radius.
Swirl   every tube gets its own x = Re_f / Re_lambda^(1/2) from the lognormal fitted to Belin's Fig. 6 (median 9.74, ln-width 0.889), made narrower by 20 % (ln-width x 0.8) and with the median raised by 10 %
        (median x 1.10).  Then Re_c = r_max U_max / nu = 1.585 x Re_lambda^(1/2),  alpha = U_max / U_eta = Re_c / beta  (x and beta independent).
Probe   as chord_belin_cut.py: impact parameter uniform in +-12 R, isotropic orientation, an event kept when max |dS/ds| >= 5 U_eta / (sqrt 15 eta); the signal of a tube is U_max / 0.4512 times the unit signal of chord_model.
Read    r_max read = half the spacing of the extrema (eta), R_m = spacing / 3.17; U_m = half the swing (U_eta);  x_read = (U_m / U_eta) (R_m / eta) / Re_lambda^(1/2)  (Belin: Re_f = U_m R_m / nu).
Output  Fig. 5 and Fig. 6 of Belin (belin_fig5_digitised.csv, belin_fig6_digitised.csv) against the model reading; U_max in cm/s of the tubes and of the events (U_eta from the Table I chain).
Usage: python chord_belin_x.py [--events 150000] [--median 1.10] [--narrow 0.8]     writes chord_belin_x.png

Versions  M01 m01.v01 (2026-11-13): first version.
          m01.v12 (2026-11-13): the separate OUT panels are removed; the measured pdfs (model reading and Belin's data) are in the IN panels. Panels: r_max, r_max U_max, U_max.
          m01.v11 (2026-11-13): --bmax (impact parameter limit, in R).
          m01.v10 (2026-11-13): panels r_max IN, r_max U_max IN, r_max OUT, r_max U_max OUT, U_max; each IN panel shows the population, the crossed tubes and the tubes after the cut, each OUT panel the reading and Belin's data.
          m01.v09 (2026-11-13): the reading is made inside a window of +-2 r_max around the steepest point of the signal (the core), not over the whole +-14R stretch; an event without an opposite-sign extremum inside it is not read.
          m01.v08 (2026-11-13): the sampled radius is size-weighted (a tube is met in proportion to its radius: the crossed tubes follow r p(r)); the fifth panel shows the population, the crossed tubes and those after the cut.
          m01.v07 (2026-11-13): a fifth panel: the input pdf of r_max as sampled and after the cut.
          m01.v06 (2026-11-13): a fourth panel: the U_max distribution that follows from the two inputs (all tubes, the tubes of the events kept, and as read).
          m01.v05 (2026-11-13): the third panel is the r_max U_max pdf as the wire reads it (against Fig. 6 transformed) instead of U_max, which needs an assumed r_max.
          m01.v04 (2026-11-13): the draws are inverse-CDF samples of the pdfs (inverse_cdf): r_max U_max from the cumulative curve of the lognormal of Fig. 6, r_max from the cumulative curve of its own pdf, then U_max = product / r_max;
                                the sampled r_max U_max histogram is drawn on the input panel as a check.
          m01.v03 (2026-11-13): the x-read panel is removed (Fig. 6 is the input, not a test); panels: input r_max U_max pdf, radius read, U_max.
          m01.v02 (2026-11-13): --sharp w: one sharp tube size r_max = 5 eta (ln-width w) instead of the Tanahashi pdf.
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
import chord_model as cm                  # noqa: E402
import chord_population as cp             # noqa: E402
import belin_gamma_pdf as bg              # noqa: E402
import belin_umax_vs_relambda as bu       # noqa: E402

RATIO = cp.RATIO
STEP = float(cm.S_GRID[1] - cm.S_GRID[0])
SIGMA_GRADIENT = 1.0 / math.sqrt(15)
CUT = 5.0
BMAX = 12.0                                                         # impact parameter uniform in +-BMAX R (Belin, p. 6: a crossing at b = 2R is rejected, so about 2)
WINDOW = 2.0                                                       # half-width of the reading window in r_max, around the steepest point of the signal


def inverse_cdf(grid, pdf):
    """Sampler of a pdf given on a grid: u uniform in (0, 1) -> F^-1(u), F the cumulative integral of the pdf (linear interpolation of the cumulative curve)."""
    cdf = np.concatenate([[0.0], np.cumsum(0.5 * (pdf[1:] + pdf[:-1]) * np.diff(grid))])
    cdf = cdf / cdf[-1]
    return lambda u: np.interp(u, cdf, grid)


def simulate(Rl, n, mu, s, seed, sharp=0.0, rmedian=5.0, bias=True):
    """Crossings with the swirl and the radius drawn by inverse-CDF sampling: the product r_max U_max / nu = Re_c = 1.585 x Re_lambda^(1/2) from the cumulative curve of the lognormal pdf of x (Fig. 6, as used),
    r_max / eta from the cumulative curve of its own pdf (a single lognormal around 5 eta with ln-width `sharp`; sharp = 0: the Tanahashi radii of chord_population), then U_max / U_eta = Re_c / r_max."""
    rng = np.random.default_rng(seed)
    cp.BIAS = True
    r, _, alpha, phi, b = cp.events(rng, n, "INDEPENDENT", math.radians(90.0))               # geometry (offset, orientation); r only if sharp = 0
    m = len(r)
    if BMAX != cp.B_MAX:
        b = rng.uniform(-BMAX, BMAX, m)
    xg = np.logspace(-2.5, 3.0, 8000)
    x = inverse_cdf(xg, bg.lognormal_x(xg, mu, s))(rng.uniform(size=m))
    Re_c = 1.585 * x * math.sqrt(Rl)
    if sharp > 0:
        rg = np.linspace(0.3, 40.0, 12000)
        pdf_r = bg.lognormal_x(rg, math.log(rmedian), sharp)
        r_pop = inverse_cdf(rg, pdf_r)(rng.uniform(size=m))                      # the population of tubes (as is)
        r = inverse_cdf(rg, rg * pdf_r)(rng.uniform(size=m)) if bias else r_pop   # the tubes that are crossed: a tube is met in proportion to its radius, p(r) -> r p(r)
    umax = Re_c / r                                                           # U_max / U_eta
    width = r / RATIO
    kept, spacing, amp, readable = np.zeros(len(r), bool), np.zeros(len(r)), np.zeros(len(r)), np.zeros(len(r), bool)
    for start in range(0, len(r), 3000):
        sl = slice(start, start + 3000)
        S = cm.signal(alpha[sl], phi[sl], b[sl])
        scale = umax[sl] / cp.GMAX
        diff = np.abs(np.diff(S, axis=1))
        grad = np.max(diff, axis=1) / STEP * scale / width[sl]
        kept[sl] = grad >= CUT * SIGMA_GRADIENT
        # reading: only the core around the steepest point of the signal, +- WINDOW r_max (= WINDOW 1.585 R); an event whose window has no opposite-sign extremum is not read
        centre = cm.S_GRID[np.argmax(diff, axis=1)] + 0.5 * STEP
        inside = np.abs(cm.S_GRID[None, :] - centre[:, None]) <= WINDOW * RATIO
        Sw_hi, Sw_lo = np.where(inside, S, -np.inf), np.where(inside, S, np.inf)
        i_hi, i_lo = np.argmax(Sw_hi, axis=1), np.argmin(Sw_lo, axis=1)
        s_hi, s_lo = S[np.arange(len(i_hi)), i_hi], S[np.arange(len(i_lo)), i_lo]
        readable[sl] = (s_hi > 0) & (s_lo < 0)
        spacing[sl] = np.abs(cm.S_GRID[i_hi] - cm.S_GRID[i_lo]) * width[sl]
        amp[sl] = 0.5 * (s_hi - s_lo) * scale
    kept_all = kept
    kept = kept & readable
    r_read = spacing[kept] / 2
    R_m = spacing[kept] / 3.17
    x_read = amp[kept] * R_m / math.sqrt(Rl)
    return dict(r_pop=r_pop if sharp > 0 else r, Re_c=Re_c, Re_c_kept=Re_c[kept], share=float(kept.mean()), share_cut=float(kept_all.mean()), r_read=r_read, x_read=x_read, U_read=amp[kept], U_true=umax, U_true_kept=umax[kept], r=r, r_kept=r[kept])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", type=int, default=150000)
    ap.add_argument("--median", type=float, default=1.10)
    ap.add_argument("--narrow", type=float, default=0.8)
    ap.add_argument("--rmedian", type=float, default=5.0, help="median of the single lognormal r_max / eta (with --sharp: its ln-width)")
    ap.add_argument("--bmax", type=float, default=12.0, help="impact parameter uniform in +-bmax R")
    ap.add_argument("--sharp", type=float, default=0.0, help="ln-width of a single sharp radius pdf around r_max = 5 eta (0: the Tanahashi pdf)")
    args = ap.parse_args()
    global BMAX
    BMAX = args.bmax
    mu0, s0, _ = bg.lognormal_fit()
    mu, s = mu0 + math.log(args.median), s0 * args.narrow
    print("x lognormal: Belin median %.2f ln-width %.3f -> used median %.2f ln-width %.3f" % (math.exp(mu0), s0, math.exp(mu), s))
    d5 = np.loadtxt(os.path.join(HERE, "belin_fig5_digitised.csv"), delimiter=",", skiprows=1)
    xs, ps = bg.raw_points()
    fig, ax = plt.subplots(2, 3, figsize=(17, 13))
    for row, (Rl, event) in enumerate(((659, 27.5), (2850, 72.5))):
        res = simulate(Rl, args.events, mu, s, 5 + row, args.sharp, args.rmedian)
        c = bu.chain_at(Rl)
        ue = c["U_eta"]
        print("Re_lambda %d: %.1f %% of the crossings pass the cut, %.1f %% are read (core window); r_max read: median %.1f eta (Belin Fig. 5: 7.6); U_eta %.2f cm/s" % (Rl, 100 * res["share_cut"], 100 * res["share"], np.median(res["r_read"]), ue))
        print("   U_max of the tubes: median %.0f cm/s (kept ones %.0f); U_max read: median %.0f cm/s, 10-90 %% %.0f-%.0f; Fig. 2 event %.1f cm/s" % (np.median(res["U_true"]) * ue, np.median(res["U_true_kept"]) * ue, np.median(res["U_read"]) * ue, *(np.percentile(res["U_read"], [10, 90]) * ue), event))
        f = 1.585 * math.sqrt(Rl) * c["nu"]                                       # r_max U_max (cm^2/s) = f x
        edges = np.logspace(math.log10(f * 0.3), math.log10(f * 60), 80)
        rb = np.linspace(0, 30, 121)
        p_read = 1.585 * res["x_read"] * math.sqrt(Rl) * c["nu"]
        grid = np.linspace(0.05, 120, 3000)
        a = ax[row, 0]                                                            # r_max in: the population, the tubes crossed (size-weighted) and the tubes that pass the cut
        a.hist(res["r_pop"], rb, density=True, histtype="step", lw=2, color="tab:gray", label="in, as is (population): median %.2f eta" % np.median(res["r_pop"]))
        a.hist(res["r"], rb, density=True, histtype="step", lw=2, color="tab:blue", label="crossed (met in proportion to r_max): median %.2f eta" % np.median(res["r"]))
        a.hist(res["r_kept"], rb, density=True, histtype="step", lw=2, color="tab:green", ls="--", label="after the cut: median %.2f eta" % np.median(res["r_kept"]))
        a.hist(res["r_read"], rb, density=True, histtype="step", lw=2.5, color="tab:red", label="out, as measured (red of the OUT panel): median %.2f eta" % np.median(res["r_read"]))
        a.plot(RATIO * d5[:, 0], d5[:, 1] / RATIO / np.trapezoid(d5[:, 1] / RATIO, RATIO * d5[:, 0]), "ko", ms=3, label="Belin Fig. 5 (measured)")
        a.set_xlim(0, 20)
        a.set_xlabel("r_max / eta (true, and as read)")
        a.set_title("Re_lambda %d: r_max, in and out" % Rl, fontsize=10)
        a = ax[row, 1]                                                            # r_max U_max in: the lognormal, the sampled tubes (all crossed), and those after the cut
        a.plot(f * grid, bg.lognormal_x(grid, mu, s) / f, "-", lw=2, color="tab:gray", label="in, as is (lognormal used): median %.3g cm^2/s, ln-width %.2f" % (f * math.exp(mu), s))
        a.hist(res["Re_c"] * c["nu"], edges, density=True, histtype="step", lw=2, color="tab:blue", label="sampled, crossed: median %.3g" % np.median(res["Re_c"] * c["nu"]))
        a.hist(res["Re_c_kept"] * c["nu"], edges, density=True, histtype="step", lw=2, color="tab:green", ls="--", label="after the cut: median %.3g" % np.median(res["Re_c_kept"] * c["nu"]))
        a.hist(p_read, edges, density=True, histtype="step", lw=2.5, color="tab:red", label="out, as measured (red of the OUT panel): median %.3g" % np.median(p_read))
        a.plot(f * xs, ps / f, "ko", ms=3, label="Belin Fig. 6 (measured), transformed")
        a.set_xscale("log")
        a.set_xlim(f * 0.3, f * 60)
        a.set_xlabel("r_max U_max (cm^2/s) (true, and as read)")
        a.set_title("Re_lambda %d: r_max U_max, in and out (nu %.2g cm^2/s)" % (Rl, c["nu"]), fontsize=10)
        a = ax[row, 2]                                                            # the velocity distribution that follows from the two inputs
        bins = np.linspace(0, 700, 141)
        a.hist(res["U_true"] * ue, bins, density=True, histtype="step", lw=2, color="tab:blue", label="U_max of the crossed tubes: median %.0f cm/s" % (np.median(res["U_true"]) * ue))
        a.hist(res["U_true_kept"] * ue, bins, density=True, histtype="step", lw=1.5, ls="--", color="tab:green", label="after the cut: median %.0f cm/s" % (np.median(res["U_true_kept"]) * ue))
        a.hist(res["U_read"] * ue, bins, density=True, histtype="step", lw=2, color="tab:red", label="as the wire reads it (half swing): median %.0f cm/s" % (np.median(res["U_read"]) * ue))
        a.axvline(event, color="k", ls="--", lw=2, label="Fig. 2 event: %.1f cm/s" % event)
        a.axvline(0.769 * Rl ** (1 / 3) * ue, color="gray", ls=":", lw=2, label="our model: %.1f cm/s" % (0.769 * Rl ** (1 / 3) * ue))
        a.set_xlim(0, 450)
        a.set_xlabel("U_max (cm/s)")
        a.set_title("Re_lambda %d: U_max (U_eta %.2f cm/s)" % (Rl, ue), fontsize=10)
        for k in range(3):
            ax[row, k].set_ylabel("pdf")
            ax[row, k].legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.14), frameon=False)          # below the axes, so that no curve is covered
    fig.suptitle("chord model with Belin's swirl distribution (x lognormal: median %.1f, ln-width %.2f; %s; Belin's 5 sigma gradient cut)" % (math.exp(mu), s, "Tanahashi radii" if args.sharp <= 0 else "r_max lognormal: median %.1f eta, ln-width %.2f" % (args.rmedian, args.sharp)), fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "chord_belin_x.png" if args.sharp <= 0 and args.median == 1.10 else ("chord_belin_x_sharp.png" if args.median == 1.10 else "chord_belin_x_exact.png")), dpi=100)


if __name__ == "__main__":
    main()
