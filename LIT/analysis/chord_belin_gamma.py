"""chord_belin_gamma.py  v01  Constant circulation with scatter: what the chord model with Belin's gradient cut reads, against Belin's Figs. 5 and 6.

Assumption (the user's): every tube has the same circulation Gamma, up to a lognormal scatter, so that its swirl follows from its radius:
        Gamma / nu = 8.784 r_max U_max   (Burgers: Gamma = 2 pi r_max U_max / (1 - e^-x), x = 1.2564)     ->     U_max / U_eta = Re_Gamma e^(s z) / (8.784 r_max / eta),  z ~ N(0, 1).
Parameters: Re_Gamma (the median of Gamma / nu) and s (the scatter, ln).  Radii: the Tanahashi (2001) two-lognormal r_max pdf (not fitted).
Probe and cut as chord_belin_cut.py: impact parameter uniform in +-12 R, isotropic orientation, a tube met in proportion to its radius (unless --nobias), event kept when
max |dS/ds| >= 5 sigma_gradient, sigma_gradient = U_eta / (sqrt 15 eta).  Belin's readings of a kept event:  R_m = spacing of the extrema / 3.17;  U_m = half the distance between
the extreme values of S;  Re_f = U_m R_m / nu  (Belin: 'R_f = U_max R / nu').  Drawn: R_m x 1.585 (r_max units, Fig. 5) and Re_f / Re_lambda^(1/2) (Fig. 6).
Belin's Fig. 6 (all Re_lambda collapse): read by eye from the figure (not digitised): EYE_FIG6.  Re_lambda 659 (his Fig. 1).
Usage: python chord_belin_gamma.py [--events 100000] [--scan]       --scan: grid over (Re_Gamma, s); writes chord_belin_gamma.png

Versions  M01 m01.v01 (2026-11-12): first version.
          m01.v02 (2026-11-12): --families: the second lognormal family has its own circulation (ratio to the first); the family of the kept events is reported.
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
STEP = float(cm.S_GRID[1] - cm.S_GRID[0])
SIGMA_GRADIENT = 1.0 / math.sqrt(15)
CUT = 5.0
RE_LAMBDA = 659.0
K_BURGERS = 8.784
EYE_FIG6 = np.array([[1.0, 0.012], [2.5, 0.055], [3.5, 0.082], [5.0, 0.074], [7.0, 0.066], [9.0, 0.050], [11.0, 0.040], [13.0, 0.033], [16.0, 0.027],
                     [20.0, 0.018], [25.0, 0.011], [30.0, 0.007], [35.0, 0.004], [40.0, 0.003]])       # Re_f / Re_lambda^(1/2), p(.): read by eye from Belin Fig. 6


def draw_tubes(rng, n, tilt, bias):
    """Crossings: true r_max, family (0: first lognormal, 1: second), tilt, rotation and impact parameter (as chord_population.events, with the family kept)."""
    m = 40 * n
    family = (rng.uniform(size=m) >= cp.RADIUS[0]).astype(int)
    r = np.where(family == 0, cp.RADIUS[1] * np.exp(cp.RADIUS[2] * rng.standard_normal(m)), cp.RADIUS[3] * np.exp(cp.RADIUS[4] * rng.standard_normal(m)))
    met = rng.uniform(size=m) < (r / np.percentile(r, 99.5) if bias else 1.0)
    r, family = r[met], family[met]
    sin_t = math.sin(tilt)
    alpha = np.arcsin(rng.uniform(-sin_t, sin_t, len(r)))
    thin = rng.uniform(size=len(r)) < np.cos(alpha)
    r, family, alpha = r[thin][:n], family[thin][:n], alpha[thin][:n]
    return r, family, alpha, rng.uniform(0, 2 * math.pi, len(r)), rng.uniform(-12.0, 12.0, len(r))


def readings(re_gamma, scatter, n, tilt_deg, bias, seed, ratio=1.0, intense=(0.0, 1.0), extra=(0.0, 0.5)):
    """(r_max read, Re_f read / sqrt Re_lambda, share kept, true r_max and Gamma/nu of the kept events, family of the kept events).
    ratio: Gamma of the second family / Gamma of the first (1: one circulation for all)."""
    rng = np.random.default_rng(seed)
    r, family, alpha, phi, b = draw_tubes(rng, n, math.radians(tilt_deg), bias)
    gamma = re_gamma * np.where(family == 1, ratio, 1.0) * np.exp(scatter * rng.standard_normal(len(r)))
    boost = np.where(rng.uniform(size=len(r)) < intense[0], intense[1], 1.0)         # a share intense[0] of the tubes (any radius) has intense[1] times the circulation: a second Re_c component
    gamma = gamma * boost
    u_burgers = gamma / (K_BURGERS * r)                                     # f(Gamma): the Burgers swirl of the circulation, U_eta
    re_c = gamma / K_BURGERS                                               # core Reynolds number U_burgers r_max / nu (the same for every radius at one Gamma)
    u = u_burgers + extra[0] * re_c ** extra[1]                            # U_max = f(Gamma) + a Re_c^n
    width = r / RATIO
    kept = np.zeros(len(r), bool)
    r_read, re_f = np.zeros(len(r)), np.zeros(len(r))
    for start in range(0, len(r), 3000):
        sl = slice(start, start + 3000)
        S = cm.signal(alpha[sl], phi[sl], b[sl])
        scale = u[sl] / cp.GMAX
        grad = np.max(np.abs(np.diff(S, axis=1)), axis=1) / STEP * scale / width[sl]
        kept[sl] = grad >= CUT * SIGMA_GRADIENT
        spacing = np.abs(cm.S_GRID[np.argmax(S, axis=1)] - cm.S_GRID[np.argmin(S, axis=1)]) * width[sl]
        amplitude = 0.5 * (S.max(axis=1) - S.min(axis=1)) * scale
        r_read[sl] = spacing / 2
        re_f[sl] = amplitude * (spacing / 3.17) / math.sqrt(RE_LAMBDA)
    return r_read[kept], re_f[kept], float(kept.mean()), r[kept], gamma[kept], family[kept]


def stats(x, edges):
    h, e = np.histogram(x, bins=edges, density=True)
    c = 0.5 * (e[1:] + e[:-1])
    return float(np.mean(x)), float(np.median(x)), float(c[np.argmax(h)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", type=int, default=100000)
    ap.add_argument("--tilt", type=float, default=90.0)
    ap.add_argument("--nobias", action="store_true")
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--ratios", default="1,0.3,0.1", help="Gamma(second family) / Gamma(first family), with --families")
    ap.add_argument("--intense", default="", help="w:k,w:k,...  a share w of the tubes with k times the circulation (a second Re_c component); scanned for Re_Gamma 700 and 1000")
    ap.add_argument("--refine", action="store_true", help="scan base circulation, scatter, share and factor of the intense component; plot the four best")
    ap.add_argument("--additive", action="store_true", help="U_max = Gamma / (8.784 r_max) + a Re_c^n, Re_c = Gamma / 8.784: scan Gamma and a (n = 0.5), plot the four best")
    ap.add_argument("--fit", action="store_true", help="fit Re_Gamma, a and n of U_max = Gamma/(8.784 r_max) + a Re_c^n to Belin Figs. 5 and 6 (scatter fixed by --scatter)")
    ap.add_argument("--scatter", type=float, default=0.5)
    ap.add_argument("--gamma", type=float, default=0.0, help="with --fit: fix Re_Gamma at this value (e.g. 300, the best model 8.78 alpha beta at Re_lambda 659) and fit a, n and the scatter")
    ap.add_argument("--families", action="store_true", help="scan the circulation of the second family relative to the first")
    ap.add_argument("--seed", type=int, default=3)
    args = ap.parse_args()
    rm, p_belin = fc.load()
    e5, e6 = np.linspace(0, 30, 61), np.linspace(0, 40, 41)
    area6 = np.trapezoid(EYE_FIG6[:, 1], EYE_FIG6[:, 0])
    print("Belin Fig. 5 x 1.585 (R_m < 19): mean 9.33 median 7.6 mode 5.9.   Fig. 6 by eye: area %.2f, peak at Re_f/sqrt(Re_lambda) = 3.5" % area6)
    if args.fit:
        from scipy.optimize import minimize
        centres5, centres6 = 0.5 * (e5[1:] + e5[:-1]), 0.5 * (e6[1:] + e6[:-1])
        target5 = np.interp(centres5, RATIO * rm, p_belin / RATIO, left=np.nan, right=np.nan)
        ok5 = ~np.isnan(target5)
        target5 = target5 / (np.nansum(target5) * (e5[1] - e5[0]))
        target6 = np.interp(centres6, EYE_FIG6[:, 0], EYE_FIG6[:, 1])
        target6 = target6 / (target6.sum() * (e6[1] - e6[0]))

        def run(v):
            g, a_coef, n_exp = (args.gamma, max(v[0], 0.0), min(max(v[1], 0.0), 1.5)) if args.gamma else (math.exp(v[0]), max(v[1], 0.0), min(max(v[2], 0.0), 1.5))
            s_fit = min(max(v[2], 0.05), 1.5) if args.gamma else args.scatter
            r_read, re_f, share, r_true, gam, fam = readings(g, s_fit, args.events, args.tilt, not args.nobias, args.seed, 1.0, (0.0, 1.0), (a_coef, n_exp))
            inside = r_read[r_read < RATIO * 19.75]
            h5, h6 = np.histogram(inside, e5, density=True)[0], np.histogram(re_f, e6, density=True)[0]
            m5, m6 = math.sqrt(np.mean((h5 - target5)[ok5] ** 2)), math.sqrt(np.mean((h6 - target6) ** 2))
            return m5 / target5[ok5].max() + m6 / target6.max(), h5, h6, share

        history = []

        def objective(v):
            value = run(v)[0]
            history.append((value, v.copy()))
            print("  " + (("a %5.2f  n %4.2f  scatter %4.2f" % (max(v[0], 0), min(max(v[1], 0), 1.5), min(max(v[2], 0.05), 1.5))) if args.gamma else ("Re_Gamma %7.0f  a %5.2f  n %4.2f" % (math.exp(v[0]), max(v[1], 0), min(max(v[2], 0), 1.5)))) + "  misfit %.3f" % value, flush=True)
            return value
        start = np.array([4.0, 0.7, 0.5]) if args.gamma else np.array([math.log(1200.0), 2.0, 0.5])
        res = minimize(objective, start, method="Nelder-Mead", options={"xatol": 0.03, "fatol": 0.004, "maxfev": 70, "initial_simplex": np.array([start, start + [1.5, 0, 0], start + [0, 0.3, 0], start + [0, 0, 0.2]]) if args.gamma else np.array([start, start + [0.4, 0, 0], start + [0, 1.0, 0], start + [0, 0, 0.25]])})
        best = res.x
        if args.gamma:
            print("best (Re_Gamma fixed at %g): a %.2f, n %.2f, scatter %.2f, misfit %.3f;  additive swirl a Re_c^n = %.1f U_eta" % (args.gamma, max(best[0], 0), min(max(best[1], 0), 1.5), min(max(best[2], 0.05), 1.5), res.fun, max(best[0], 0) * (args.gamma / K_BURGERS) ** min(max(best[1], 0), 1.5)))
        else:
            print("best: Re_Gamma %.0f, a %.2f, n %.2f (scatter %.1f), misfit %.3f" % (math.exp(best[0]), max(best[1], 0), min(max(best[2], 0), 1.5), args.scatter, res.fun))
        v0, h50, h60, s0 = run(np.array([0.0, 0.5, 0.5]) if args.gamma else np.array([math.log(1200.0), 0.0, 0.5]))
        v1, h51, h61, s1 = run(best)
        figf, axf = plt.subplots(1, 2, figsize=(14, 5))
        axf[0].plot(RATIO * rm, p_belin / RATIO, "ko", ms=5, label="Belin Fig. 5, R_m x 1.585")
        axf[1].plot(EYE_FIG6[:, 0], EYE_FIG6[:, 1], "ko", ms=5, label="Belin Fig. 6 (read by eye)")
        axf[0].step(centres5, h50, where="mid", color="tab:gray", lw=1.6, label="no additive term (a = 0), scatter 0.5")
        axf[1].step(centres6, h60, where="mid", color="tab:gray", lw=1.6, label="no additive term (a = 0), scatter 0.5")
        label = ("fitted: Re_Gamma %g (fixed), a %.2f, n %.2f, scatter %.2f" % (args.gamma, max(best[0], 0), min(max(best[1], 0), 1.5), min(max(best[2], 0.05), 1.5))) if args.gamma else ("fitted: Re_Gamma %.0f, a %.2f, n %.2f" % (math.exp(best[0]), max(best[1], 0), min(max(best[2], 0), 1.5)))
        axf[0].step(centres5, h51, where="mid", color="tab:red", lw=2, label=label)
        axf[1].step(centres6, h61, where="mid", color="tab:red", lw=2, label=label)
        axf[0].set_xlim(0, 30)
        axf[0].set_xlabel("r_max / eta (read by the wire)")
        axf[1].set_xlabel("Re_f / Re_lambda^(1/2)")
        for a_ in axf:
            a_.set_ylabel("pdf")
            a_.legend(fontsize=8)
        axf[0].set_title("U_max = Gamma/(8.784 r_max) + a Re_c^n, scatter %.1f, Re_lambda 659, Belin's cut" % args.scatter, fontsize=9)
        figf.tight_layout()
        figf.savefig(os.path.join(HERE, "chord_belin_gamma_fit_G%g.png" % args.gamma if args.gamma else "chord_belin_gamma_fit.png"), dpi=110)
        return
    if args.additive:
        centres5, centres6 = 0.5 * (e5[1:] + e5[:-1]), 0.5 * (e6[1:] + e6[:-1])
        target5 = np.interp(centres5, RATIO * rm, p_belin / RATIO, left=np.nan, right=np.nan)
        ok5 = ~np.isnan(target5)
        target5 = target5 / (np.nansum(target5) * (e5[1] - e5[0]))
        target6 = np.interp(centres6, EYE_FIG6[:, 0], EYE_FIG6[:, 1])
        target6 = target6 / (target6.sum() * (e6[1] - e6[0]))
        results = []
        for g in (300, 500, 800, 1200):
            for a_coef in (0.0, 0.5, 1.0, 2.0):
                for s in (0.3, 0.5):
                    r_read, re_f, share, r_true, gam, fam = readings(g, s, args.events, args.tilt, not args.nobias, args.seed, 1.0, (0.0, 1.0), (a_coef, 0.5))
                    inside = r_read[r_read < RATIO * 19.75]
                    h5, h6 = np.histogram(inside, e5, density=True)[0], np.histogram(re_f, e6, density=True)[0]
                    m5, m6 = math.sqrt(np.mean((h5 - target5)[ok5] ** 2)), math.sqrt(np.mean((h6 - target6) ** 2))
                    results.append((m5 / target5[ok5].max() + m6 / target6.max(), m5, m6, g, s, a_coef, 0.5, h5, h6))
        results.sort(key=lambda x: x[0])
        for res in results[:6]:
            print("misfit %.3f (radius %.4f, Re_f %.4f): Re_Gamma %g, scatter %.1f, a %.1f, n %.1f" % res[:7])
        figa, axa = plt.subplots(1, 2, figsize=(14, 5))
        axa[0].plot(RATIO * rm, p_belin / RATIO, "ko", ms=5, label="Belin Fig. 5, R_m x 1.585")
        axa[1].plot(EYE_FIG6[:, 0], EYE_FIG6[:, 1], "ko", ms=5, label="Belin Fig. 6 (read by eye)")
        for res, colour in zip(results[:4], ("tab:blue", "tab:green", "tab:red", "tab:purple")):
            label = "Re_Gamma %g, s %.1f, a %.1f" % (res[3], res[4], res[5])
            axa[0].step(centres5, res[7], where="mid", color=colour, lw=1.8, label=label)
            axa[1].step(centres6, res[8], where="mid", color=colour, lw=1.8, label=label)
        axa[0].set_xlim(0, 30)
        axa[0].set_xlabel("r_max / eta (read by the wire)")
        axa[1].set_xlabel("Re_f / Re_lambda^(1/2)")
        for a_ in axa:
            a_.set_ylabel("pdf")
            a_.legend(fontsize=8)
        axa[0].set_title("U_max = Gamma/(8.784 r_max) + a Re_c^0.5: the four best of 32 settings", fontsize=9)
        figa.tight_layout()
        figa.savefig(os.path.join(HERE, "chord_belin_gamma_additive.png"), dpi=110)
        return
    if args.refine:
        centres5 = 0.5 * (e5[1:] + e5[:-1])
        centres6 = 0.5 * (e6[1:] + e6[:-1])
        target5 = np.interp(centres5, RATIO * rm, p_belin / RATIO, left=np.nan, right=np.nan)
        ok5 = ~np.isnan(target5)
        target5 = target5 / (np.nansum(target5) * (e5[1] - e5[0]))
        target6 = np.interp(centres6, EYE_FIG6[:, 0], EYE_FIG6[:, 1])
        target6 = target6 / (target6.sum() * (e6[1] - e6[0]))
        results = []
        for g in (800, 1200, 1800):
            for s in (0.3, 0.5):
                for w in (0.05, 0.1, 0.2):
                    for k in (4.0, 8.0):
                        r_read, re_f, share, r_true, gam, fam = readings(g, s, args.events, args.tilt, not args.nobias, args.seed, 1.0, (w, k))
                        inside = r_read[r_read < RATIO * 19.75]
                        h5 = np.histogram(inside, e5, density=True)[0]
                        h6 = np.histogram(re_f, e6, density=True)[0]
                        m5 = math.sqrt(np.mean((h5 - target5)[ok5] ** 2))
                        m6 = math.sqrt(np.mean((h6 - target6) ** 2))
                        results.append((m5 / target5[ok5].max() + m6 / target6.max(), m5, m6, g, s, w, k, h5, h6))
        results.sort(key=lambda x: x[0])
        for res in results[:6]:
            print("misfit %.3f (radius %.4f, Re_f %.4f): base %g, scatter %.1f, share %.2f, factor x%g" % res[:7])
        figr, axr = plt.subplots(1, 2, figsize=(14, 5))
        axr[0].plot(RATIO * rm, p_belin / RATIO, "ko", ms=5, label="Belin Fig. 5, R_m x 1.585")
        axr[1].plot(EYE_FIG6[:, 0], EYE_FIG6[:, 1], "ko", ms=5, label="Belin Fig. 6 (read by eye)")
        for res, colour in zip(results[:4], ("tab:blue", "tab:green", "tab:red", "tab:purple")):
            label = "base %g, s %.1f, %d%% of tubes x%g" % (res[3], res[4], round(100 * res[5]), res[6])
            axr[0].step(centres5, res[7], where="mid", color=colour, lw=1.8, label=label)
            axr[1].step(centres6, res[8], where="mid", color=colour, lw=1.8, label=label)
        axr[0].set_xlim(0, 30)
        axr[0].set_xlabel("r_max / eta (read by the wire)")
        axr[1].set_xlabel("Re_f / Re_lambda^(1/2)")
        for a_ in axr:
            a_.set_ylabel("pdf")
            a_.legend(fontsize=8)
        axr[0].set_title("the four best of 36 settings (radius and Re_f misfit together)", fontsize=9)
        figr.tight_layout()
        figr.savefig(os.path.join(HERE, "chord_belin_gamma_refine.png"), dpi=110)
        return
    if args.intense:
        figi, axi = plt.subplots(1, 2, figsize=(14, 5))
        axi[0].plot(RATIO * rm, p_belin / RATIO, "ko", ms=5, label="Belin Fig. 5, R_m x 1.585")
        axi[1].plot(EYE_FIG6[:, 0], EYE_FIG6[:, 1], "ko", ms=5, label="Belin Fig. 6 (read by eye)")
        cases = [(500, (0.0, 1.0), "tab:gray", "base Re_Gamma 500, no intense component"), (500, (0.2, 4.0), "tab:blue", "base 500, 20% of tubes at x4 circulation"),
                 (500, (0.2, 8.0), "tab:orange", "base 500, 20% at x8"), (1000, (0.0, 1.0), "tab:green", "base 1000, no intense component")]
        for g, wk, colour, label in cases:
            r_read, re_f, share, r_true, gam, fam = readings(g, 0.4, args.events, args.tilt, not args.nobias, args.seed, 1.0, wk)
            inside = r_read[r_read < RATIO * 19.75]
            axi[0].hist(inside, e5, density=True, histtype="step", color=colour, lw=2, label=label)
            axi[1].hist(re_f, e6, density=True, histtype="step", color=colour, lw=2, label=label)
            print("%-45s radius mean %.1f median %.1f | Re_f mean %.1f median %.1f" % ((label,) + (stats(inside, e5)[0], stats(inside, e5)[1], stats(re_f, e6)[0], stats(re_f, e6)[1])))
        axi[0].set_xlim(0, 30)
        axi[0].set_xlabel("r_max / eta (read by the wire)")
        axi[1].set_xlabel("Re_f / Re_lambda^(1/2)")
        for a_ in axi:
            a_.set_ylabel("pdf")
            a_.legend(fontsize=8)
        axi[0].set_title("radius pdf, Belin's cut (5 sigma gradient), Re_lambda 659, scatter 0.4", fontsize=9)
        axi[1].set_title("worm Reynolds number pdf", fontsize=9)
        figi.tight_layout()
        figi.savefig(os.path.join(HERE, "chord_belin_gamma_intense.png"), dpi=110)
        return
    ratios = [float(v) for v in args.ratios.split(",")] if args.families else [1.0]
    grid = [(g, s, q) for g in (300, 1000, 3000, 10000, 30000) for s in (0.3, 0.6, 0.9) for q in (1.0,)] if args.scan else [(g, 0.6, q) for g in (1000, 3000) for q in ratios]
    fig, ax = plt.subplots(1, 2, figsize=(14, 5))
    ax[0].plot(RATIO * rm, p_belin / RATIO, "ko", ms=4, label="Belin Fig. 5, R_m x 1.585")
    ax[1].plot(EYE_FIG6[:, 0], EYE_FIG6[:, 1], "ko", ms=4, label="Belin Fig. 6 (read by eye)")
    colours = plt.cm.viridis(np.linspace(0, 0.9, len(grid)))
    print("Re_Gamma  s   | kept   | r_max read: mean median mode | Re_f/sqrt(Re_lambda): mean median mode | true Gamma/nu of kept, r_max")
    for (g, s, q), c in zip(grid, colours):
        r_read, re_f, share, r_true, gam, fam = readings(g, s, args.events, args.tilt, not args.nobias, args.seed, q)
        if len(r_read) < 50:
            print("%7g  %.1f | %.4f | too few events" % (g, s, share))
            continue
        inside = r_read[r_read < RATIO * 19.75]
        print("%7g  %.1f  G2/G1 %.2f | %.4f | %5.2f %5.2f %5.2f | %5.2f %5.2f %5.2f | %7.0f  %5.2f | second family %.0f%% of kept" % ((g, s, q, share) + stats(inside, e5) + stats(re_f, e6) + (np.median(gam), r_true.mean(), 100 * fam.mean())))
        if args.scan and not (s == 0.6):
            continue
        ax[0].hist(inside, e5, density=True, histtype="step", color=c, lw=1.5, label="Re_Gamma %g, s %.1f, G2/G1 %.2f" % (g, s, q))
        ax[1].hist(re_f, e6, density=True, histtype="step", color=c, lw=1.5, label="Re_Gamma %g, s %.1f, G2/G1 %.2f" % (g, s, q))
    ax[0].set_xlim(0, 30)
    ax[0].set_xlabel("r_max / eta (read)")
    ax[1].set_xlabel("Re_f / Re_lambda^(1/2)")
    for a in ax:
        a.set_ylabel("pdf")
        a.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "chord_belin_gamma.png"), dpi=110)


if __name__ == "__main__":
    main()
