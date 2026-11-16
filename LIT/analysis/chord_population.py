"""chord_population.py  v01  What a hot-wire probe reads from a POPULATION of tubes (radius and swirl from the DNS pdfs), for different cuts.

Question.  chord_model.py crosses one tube size with a straight probe.  A real record has tubes of every size and strength, and the detection
is a cut on the absolute signal, so a cut also picks the strong (and the large) tubes.  What are the factors (apparent / true) of radius and swirl,
cut by cut, for the lognormal pdfs of Tanahashi et al. (2001)?

Model
    tubes    radius r_max/eta from the two-lognormal fit of the radius pdf (Tanahashi 2001, mixing layer: weight 0.708, median 5.23, s 0.288 and
             median 11.27, s 0.605); swirl U_max/U_eta from the two-lognormal fit of the swirl pdf (U_max/u_rms; weight 0.415, median 0.500, s 0.619;
             median 0.900, s 0.407), u_rms = (Re_lambda/sqrt15)^(1/2) U_eta (Re_lambda 80).  Cases: INDEPENDENT (radius and swirl drawn separately),
             FIXED_SWIRL (every tube has the median swirl: only the radius varies), CORRELATED (the swirl ranks like the radius).
    probe    as chord_model: impact parameter uniform in +-B_MAX R (so a tube of radius R is met in proportion to R), tilt density cos alpha,
             rotation uniform, thinned by the encounter rate cos alpha; the probe senses one velocity component.
    signal   S(s) in physical units: the unit-tube signal of chord_model (R = 1) with s -> s/R and amplitude U_max / 0.4512.
    cut      keep the strongest fraction q of the events by peak |S|: q = 1 (all), 0.5, 0.1, 0.01, 0.001.
    reading  (a) Belin: radius = spacing of the two extrema / 3.17 (mean, median, mode);
             (b) Mouri: the kept events are aligned on their zero crossing and averaged; a Burgers profile is fitted to the mean: r_fit, U_fit.
    factors  radius factor = r_fit / (true mean r_max/eta of the whole population) and / (mean of the first lognormal: the model tube);
             swirl factor = (true mean U_max/U_eta) / U_fit  (the number the measurement must be MULTIPLIED by).
Usage: python chord_population.py [--events 120000] [--seed 1]
Output: the table, and chord_population.csv.

Versions  M01 m01.v01 (2026-11-12): first version.
          m01.v02 (2026-11-12): radii are r_max (the radius of peak swirl): Belin's spacing/3.17 and the fitted Burgers width were Gaussian widths R = r_max/1.585 and had been compared with r_max.
"""
import argparse
import csv
import math
import os
import sys

import numpy as np
from scipy.optimize import least_squares

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chord_model as cm   # noqa: E402

__all__ = ["population", "run_case", "main"]

GMAX = (1 - math.exp(-cm.X0)) / cm.RMAX                 # 0.4512: peak of (1 - exp(-x^2/2))/x
RATIO = cm.RMAX                                         # r_max = 1.585 R
B_MAX = 12.0
BIAS = True                                             # a tube is met in proportion to its radius (False: every tube equally likely)
GRID = np.linspace(-80, 80, 641)                        # physical s / eta for the mean profile
RADIUS = (0.708, 5.231, 0.288, 11.27, 0.605)            # weight 1, median 1, s 1, median 2, s 2  (r_max / eta)
SWIRL = (0.415, 0.500, 0.619, 0.9006, 0.407)            # U_max / u_rms
RE_LAMBDA = 80.0
U_RMS = (RE_LAMBDA / math.sqrt(15)) ** 0.5              # u_rms / U_eta
COPULA_RHO = 0.43                                       # rank correlation of ln r and ln U (see case COPULA)
CUTS = (1.0, 0.5, 0.1, 0.01, 0.001)
C_SASSA = (1.5, 2.0, 2.5, 3.0, 3.5)                    # Sassa & Makita (2005) eq. 2: keep events with dw/dt >= C rms(dw/dt); they use C = 2.5 (their Fig. 2 scans 1-3.5)
RMS_GRADIENT = math.sqrt(2 / 15)                        # rms of a transverse gradient dw/dx in units of U_eta/eta: <(dw/dx)^2> = 2 eps / (15 nu)


def lognormal2(rng, n, p):
    """n draws of the two-lognormal pdf p = (w1, m1, s1, m2, s2)."""
    first = rng.uniform(size=n) < p[0]
    z = rng.standard_normal(n)
    return np.where(first, p[1] * np.exp(p[2] * z), p[3] * np.exp(p[4] * z))


def population(rng, n, case):
    """Radius r_max/eta and swirl U_max/U_eta of n tubes."""
    r = lognormal2(rng, n, RADIUS)
    if case == "MODEL":                                  # our best model (D6): every tube has U_max/U_eta = 0.769 Re^(1/3), whatever its radius
        u = np.full(n, 0.769 * RE_LAMBDA ** (1 / 3))
    elif case == "FIXED_SWIRL":
        u = np.full(n, 0.7522 * U_RMS)
    elif case == "JOINT":                                # swirl given radius from the isolines of Ghira et al. (2022) Fig. 9b, Re_lambda 90 (ghira2022_fig9b_re90.csv): median U ~ R^0.31, spread of ln U 0.227; anchored at the Tanahashi median swirl 3.41 at r = 5.45; the isolines end at R about 9, so U is held at its R = 9 value for larger tubes
        u = 3.41 * (np.minimum(r, 9.0) / 5.45) ** 0.31 * np.exp(0.227 * rng.standard_normal(n))
    elif case == "COPULA":                               # both Tanahashi marginals kept (broad swirl pdf included); the dependence of Ghira et al. (2022) Fig. 9b enters as a rank correlation
        z1 = rng.standard_normal(n)                      # rho = b s_R / sqrt(b^2 s_R^2 + s_c^2): slope b = 0.31, s_R = 0.35 (their radii, ln), s_c = 0.227 -> 0.43
        z2 = COPULA_RHO * z1 + math.sqrt(1 - COPULA_RHO ** 2) * rng.standard_normal(n)
        r = np.sort(r)[np.argsort(np.argsort(z1))]
        u = np.sort(lognormal2(rng, n, SWIRL) * U_RMS)[np.argsort(np.argsort(z2))]
    elif case == "ANTICORRELATED":                       # the largest tubes carry the weakest swirl (rank-matched, both marginal pdfs kept): the other end of the range from CORRELATED
        u = np.sort(lognormal2(rng, n, SWIRL) * U_RMS)[::-1][np.argsort(np.argsort(r))]
    elif case == "CORRELATED":
        u = np.sort(lognormal2(rng, n, SWIRL) * U_RMS)[np.argsort(np.argsort(r))]
    else:
        u = lognormal2(rng, n, SWIRL) * U_RMS
    return r, u


def burgers(s, radius, peak):
    x = np.where(np.abs(s) < 1e-9, 1e-9, s) / radius
    return peak * (1 - np.exp(-x * x / 2)) / x / GMAX


def aligned(S, grid_unit):
    """Unit-tube signal row -> (centred s in units of R, signal) with the larger extremum positive at s > 0; None if no zero crossing between the extrema."""
    i1 = int(np.argmax(np.abs(S)))
    S = S * (1.0 if S[i1] > 0 else -1.0)
    i2 = int(np.argmin(S)) if i1 == int(np.argmax(S)) else int(np.argmax(S))
    lo, hi = sorted((i1, i2))
    crossing = np.nonzero(np.diff(np.sign(S[lo:hi + 1])))[0]
    if len(crossing) == 0:
        return None
    k = lo + crossing[0]
    centre = grid_unit[k] - S[k] * (grid_unit[k + 1] - grid_unit[k]) / (S[k + 1] - S[k])
    x = grid_unit - centre
    if grid_unit[int(np.argmax(S))] < centre:
        x, S = -x[::-1], S[::-1]
    return x, S


def events(rng, n, case, tilt):
    """n kept-by-geometry crossings: dict of arrays r (true), u (true), peak (physical |S| max), spacing (physical), and the unit signals."""
    r, u = population(rng, 40 * n, case)
    met = rng.uniform(size=len(r)) < (r / np.percentile(r, 99.5) if BIAS else 1.0)                      # a tube of radius R is met in proportion to R (impact range ~ R)
    r, u = r[met], u[met]
    sin_t = math.sin(tilt)
    alpha = np.arcsin(rng.uniform(-sin_t, sin_t, len(r)))
    thin = rng.uniform(size=len(r)) < np.cos(alpha)
    r, u, alpha = r[thin][:n], u[thin][:n], alpha[thin][:n]
    phi = rng.uniform(0, 2 * math.pi, len(r))
    b = rng.uniform(-B_MAX, B_MAX, len(r))
    return r, u, alpha, phi, b


def run_case(case, n_events, seed, tilt_deg=90.0):
    """List of rows (cut, kept, belin mean/median/mode factors, r_fit, U_fit, true means) for one case."""
    rng = np.random.default_rng(seed)
    tilt = math.radians(tilt_deg)
    r, u, alpha, phi, b = events(rng, n_events, case, tilt)
    rho = r / RATIO                                                      # Gaussian width R of each tube in eta
    peaks, spacings, slopes, unit = np.zeros(len(r)), np.zeros(len(r)), np.zeros(len(r)), []
    chunk = 3000
    for start in range(0, len(r), chunk):
        sl = slice(start, start + chunk)
        S = cm.signal(alpha[sl], phi[sl], b[sl])
        scale = u[sl] / GMAX
        peaks[sl] = np.max(np.abs(S), axis=1) * scale
        slopes[sl] = np.max(np.abs(np.diff(S, axis=1)), axis=1) / (cm.S_GRID[1] - cm.S_GRID[0]) * scale / rho[sl]      # largest |dS/ds|, in U_eta/eta
        spacings[sl] = np.abs(cm.S_GRID[np.argmax(S, axis=1)] - cm.S_GRID[np.argmin(S, axis=1)]) * rho[sl]
        unit.append(S.astype(np.float32))
    unit = np.concatenate(unit)
    first = RADIUS[1] * math.exp(RADIUS[2] ** 2 / 2)
    pr, pu = population(np.random.default_rng(seed + 7), 400000, case)
    true_r, true_u = float(np.mean(pr)), float(np.mean(pu))        # the pdf's own means (every tube counted once)
    order = np.argsort(-peaks)
    rows = []
    for q in CUTS + tuple(-c for c in C_SASSA):          # q > 0: the strongest fraction q by peak |S|; q < 0: Sassa's dw/dt cut with C = -q
        if q > 0:
            keep = order[:max(150, int(q * len(r)))]
        else:
            keep = np.nonzero(slopes >= -q * RMS_GRADIENT)[0]
            if len(keep) < 40:
                continue
        fraction = len(keep) / len(r)
        if len(keep) > 6000:
            keep = rng.choice(keep, 6000, replace=False)                 # the mean profile of 6000 events is stable; saves time
        belin = spacings[keep] / 2                                     # radius to the peak swirl, r_max = half the extrema spacing (Belin's spacing / 3.17 is the Gaussian width R = r_max / 1.585)
        hist, edges = np.histogram(belin, bins=np.linspace(0, 40, 161))
        mode = 0.5 * (edges[np.argmax(hist)] + edges[np.argmax(hist) + 1])
        total, count = np.zeros_like(GRID), 0
        for i in keep:
            a = aligned(unit[i].astype(float), cm.S_GRID)
            if a is None:
                continue
            x, S = a
            total += np.interp(GRID, x * rho[i], S * u[i] / GMAX, left=0.0, right=0.0)
            count += 1
        mean = total / max(count, 1)
        fit = least_squares(lambda p: burgers(GRID, p[0], p[1]) - mean, [3.0, true_u / 2], bounds=([0.2, 0.05], [50.0, 60.0]))
        r_fit, u_fit = fit.x[0] * RATIO, fit.x[1]          # the fitted width R -> r_max = 1.585 R, to compare with the tube radius r_max / eta
        rows.append(dict(case=case, q=q, fraction=fraction, kept=len(keep), true_r=true_r, true_u=true_u, first_r=first,
                         belin_mean=float(np.mean(belin)), belin_median=float(np.median(belin)), belin_mode=mode,
                         r_fit=r_fit, u_fit=u_fit, mean_true_r_kept=float(np.mean(r[keep])), mean_true_u_kept=float(np.mean(u[keep])), belin_values=belin, peak_values=peaks[keep], true_r_values=r[keep]))
    return rows


def plot(rows):
    """chord_population.png: what the wire reads against what is there.  Rows: radius, swirl.  Columns: the cuts on the strongest fraction of events, Sassa's dw/dt cuts.
    Black: the DNS pdf of the tubes (every tube once; the swirl of the best model is one value).  Grey dashed: the tubes the wire crosses.  Coloured: the per-event reading
    (radius = extrema spacing / 3.17; swirl = the peak of the signal).  Dotted verticals: the Burgers fit to the mean profile of the kept events."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    case = rows[0]["case"]
    sel = [w for w in rows if w["case"] == case]
    name = "chord_population.png" if case == "MODEL" else "chord_population_%s.png" % case.lower()
    rng = np.random.default_rng(3)
    pop_r, pop_u = population(rng, 400000, case)
    fig, ax = plt.subplots(2, 2, figsize=(14, 8.5))
    groups = (("strongest fraction of events by peak |S| (Mouri, Belin type cuts)", [w for w in sel if w["q"] > 0], lambda w: "strongest %g %%" % (100 * w["q"])),
              ("Sassa & Makita dw/dt >= C rms (C = 2.5 in the paper)", [w for w in sel if w["q"] < 0], lambda w: "C = %g (%.1f %% of events)" % (-w["q"], 100 * w["fraction"])))
    for col, (title, group, label) in enumerate(groups):
        colours = plt.cm.viridis(np.linspace(0, 0.9, len(group)))
        for row, (key, vals, bins, xlabel, true_mean, true_first) in enumerate((
                ("r", "belin_values", np.linspace(0, 40, 101), "r_max / eta", float(np.mean(pop_r)), group[0]["first_r"]),
                ("u", "peak_values", np.linspace(0, 14, 113), "U_max / U_eta", float(np.mean(pop_u)), float(np.mean(pop_u))))):
            a = ax[row, col]
            if key == "r":
                a.hist(pop_r, bins, density=True, histtype="stepfilled", color="0.85", edgecolor="k", lw=1.6, label="tube pdf of the DNS")
                a.hist(group[0]["true_r_values"], bins, density=True, histtype="step", color="0.35", lw=1.5, ls="--", label="tubes the wire crosses (size-weighted)")
                a.axvline(true_first, color="r", ls=":", lw=2, label="model tube, first lognormal mean %.2f" % true_first)
            elif case == "MODEL":
                a.axvline(true_mean, color="k", lw=2.5, label="swirl of every tube (best model) %.2f" % true_mean)
            else:
                a.hist(pop_u, bins, density=True, histtype="stepfilled", color="0.85", edgecolor="k", lw=1.6, label="swirl pdf of the DNS (Tanahashi 2001), mean %.2f" % true_mean)
                a.axvline(0.769 * RE_LAMBDA ** (1 / 3), color="r", ls=":", lw=2, label="best model D6: %.2f" % (0.769 * RE_LAMBDA ** (1 / 3)))
            for w, c in zip(group, colours):
                a.hist(w[vals], bins, density=True, histtype="step", color=c, lw=1.5, label=label(w))
                a.axvline(w["r_fit"] if key == "r" else w["u_fit"], color=c, ls=":", lw=1.2)
            a.set_xlabel(xlabel)
            a.set_ylabel("pdf")
            if row == 0:
                a.set_title(title, fontsize=10)
            a.legend(fontsize=7)
    fig.suptitle("Chord model fed with the DNS tube population (Tanahashi 2001 pdfs, Re_lambda 80): %s swirl" % case, fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, name.replace(".png", "_equalchance.png") if not BIAS else name), dpi=110)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", type=int, default=120000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--plot", action="store_true")
    ap.add_argument("--nobias", action="store_true")
    ap.add_argument("--tilt", type=float, default=90.0)
    ap.add_argument("--cases", default="INDEPENDENT")
    args = ap.parse_args()
    global BIAS
    BIAS = not args.nobias
    allrows = []
    for case in args.cases.split(","):
        rows = run_case(case, args.events, args.seed, args.tilt)
        allrows += rows
        print("\n%s  (true population: mean r_max/eta %.2f, first lognormal mean %.2f, mean U_max/U_eta %.2f; Re_lambda %g, tilt <= %g deg, %d crossings)"
              % (case, rows[0]["true_r"], rows[0]["first_r"], rows[0]["true_u"], RE_LAMBDA, args.tilt, args.events))
        print("  cut        kept  frac | kept-tube true mean r, U | Belin r: mean median mode | fit r, U | r_fit/true r   r_fit/first   swirl factor (true U / U_fit)")
        print("   (cut q: strongest fraction by |S|; cut C: Sassa dw/dt >= C rms)")
        for w in rows:
            print("  %-9s %5d %5.3f |  %5.2f  %5.2f      | %5.2f  %5.2f  %5.2f | %5.2f  %5.2f |  %5.2f        %5.2f        %5.2f"
                  % (("q=%g" % w["q"]) if w["q"] > 0 else ("C=%g" % -w["q"]), w["kept"], w["fraction"], w["mean_true_r_kept"], w["mean_true_u_kept"], w["belin_mean"], w["belin_median"], w["belin_mode"], w["r_fit"], w["u_fit"],
                     w["r_fit"] / w["true_r"], w["r_fit"] / w["first_r"], w["true_u"] / w["u_fit"]))
    with open(os.path.join(HERE, "chord_population.csv"), "w", newline="", encoding="utf-8") as f:
        names = [k for k in allrows[0] if not k.endswith("_values")]
        out = csv.DictWriter(f, fieldnames=names, extrasaction="ignore")
        out.writeheader()
        out.writerows(allrows)
    if args.plot:
        for case in args.cases.split(","):
            plot([w for w in allrows if w["case"] == case])


if __name__ == "__main__":
    main()
