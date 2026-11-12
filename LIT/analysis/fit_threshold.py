"""fit_threshold.py  v01  What the threshold averages of Mouri et al. (2004, 2007) say about the true tube, from the chord model.

Question.  Mouri's R and V are the fit of a Burgers profile to the mean of all events above an amplitude cut (the highest 0.1% or 1% of the
increments).  A straight probe cuts a tube at random offset and tilt (chord_model.py), so a stricter cut keeps nearer-central cuts: smaller
radius, larger swirl.  Is the 0.1% / 1% pair of one run two cuts of the same tube, and what tube does it give?

Forward model (units: Gaussian width R = 1 of the true tube, peak swirl A0 = U0 of a central, normal crossing, r0 = 1.585 R)
    1  Draw crossings: impact parameter uniform, tilt (density cos alpha, |alpha| <= TILT), rotation phi uniform, thinned by the encounter rate
       (as chord_model.events).  The signal S(s) is the probed velocity component along the path.
    2  Keep the events with max|S| >= f A0 (the cut f).  Align every kept event on the zero crossing between its two extrema, sign and
       direction chosen so that its larger extremum is positive and lies at s > 0, and average the profiles.
    3  Fit the Burgers profile V (1 - exp(-s^2 / 2 Rf^2)) / (s / Rf) / 0.4512 to the mean (least squares).  The master curves are
       rho_r(f) = r_fit / r0 = Rf and rho_U(f) = V_fit / A0.
Inverse problem.  The data of a run are (r_a, U_a) at the 0.1% cut and (r_b, U_b) at the 1% cut.  With one tube (r0, U0) per run and the
two cuts fA > fB the same for every run (the cut as a fraction of the central swirl: U0 is about 0.6-0.8 of the r.m.s. velocity at all Re,
so this is a modest assumption), the log of each datum is  log r0 + log rho_r(f).  The per-run (r0, U0) drop out of the ratios
r_b/r_a and U_b/U_a, which depend only on (fA, fB): the two shared numbers are fitted to the 11 ratios of each quantity, and r0, U0 follow
for every run.  Mouri et al. (2004) (1% only) is corrected with fB.

Output  the master table, the fitted cuts with the residuals of the ratios (the test of the model), and the corrected tubes: r0, U0,
Re_c = r0 U0 against the raw values, and the factors (r divisor, swirl factor) that the 0.1% rows would need.  Writes fit_threshold.csv.
Nothing here changes corrections.json: the results wait to be agreed.
Usage: python fit_threshold.py [--tilt 45] [--events 3000]

Versions  M01 m01.v01 (2026-11-11): first version.
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

TUBES = os.path.join(HERE, "..", "fittingtool", "data", "tubes.csv")
GMAX = (1 - math.exp(-cm.X0)) / cm.RMAX            # peak of (1 - exp(-x^2/2)) / x, 0.4512
GRID = np.linspace(-14, 14, 561)
CUTS = np.round(np.arange(0.10, 0.91, 0.05), 2)
RNG = cm.RNG


def aligned_profile(S):
    """The profile of one event on the grid GRID: centred on the zero crossing between its two extrema, the larger extremum positive at s > 0."""
    i1 = int(np.argmax(np.abs(S)))
    sign = 1.0 if S[i1] > 0 else -1.0
    S = S * sign
    i2 = int(np.argmin(S)) if i1 == int(np.argmax(S)) else int(np.argmax(S))
    lo, hi = sorted((i1, i2))
    seg = S[lo:hi + 1]
    crossing = np.nonzero(np.diff(np.sign(seg)))[0]
    if len(crossing) == 0:
        return None
    k = lo + crossing[0]
    centre = cm.S_GRID[k] - S[k] * (cm.S_GRID[k + 1] - cm.S_GRID[k]) / (S[k + 1] - S[k])
    x = cm.S_GRID - centre
    if cm.S_GRID[i1] < centre:                       # larger extremum on the negative side: mirror
        x, S = -x[::-1], S[::-1]                     # mirror s -> -s: the peak (positive) moves to s > 0
    return np.interp(GRID, x, S, left=0.0, right=0.0)


def burgers(s, radius, peak):
    x = np.where(np.abs(s) < 1e-9, 1e-9, s) / radius
    return peak * (1 - np.exp(-x * x / 2)) / x / GMAX


SEPARATION = None        # None: an event is selected by its peak signal; a number (in units of R): by the largest velocity increment over that separation


def selection_amplitude(S):
    """The quantity the threshold acts on, per event: the peak |S| (SEPARATION None), or the largest |S(s + d) - S(s)| (d = SEPARATION R), which is what an
    increment-based detection (Mouri et al.: the highest 0.1% and 1% of the absolute velocity increments) sees; for a small d it is d times the largest slope."""
    if SEPARATION is None:
        return np.max(np.abs(S), axis=1)
    k = max(1, int(round(SEPARATION / (cm.S_GRID[1] - cm.S_GRID[0]))))
    return np.max(np.abs(S[:, k:] - S[:, :-k]), axis=1)


def master(cut, n, tilt):
    """rho_r, rho_U of the mean profile of n events kept at the cut (a fraction of the central crossing's selection amplitude); rho_U is relative to the central swirl A0."""
    A0 = cm.reference_amplitude()
    Asel = float(selection_amplitude(cm.signal(np.array([0.0]), np.array([math.pi / 2]), np.array([0.0])))[0])
    total, count, tried = np.zeros_like(GRID), 0, 0
    sin_t = math.sin(tilt)
    while count < n and tried < 400:
        tried += 1
        m = 6000
        alpha = np.arcsin(RNG.uniform(-sin_t, sin_t, m))
        phi = RNG.uniform(0, 2 * math.pi, m)
        b = RNG.uniform(-12.0, 12.0, m)
        thin = RNG.uniform(0, 1, m) < np.cos(alpha)
        alpha, phi, b = alpha[thin], phi[thin], b[thin]
        S = cm.signal(alpha, phi, b)
        ok = selection_amplitude(S) >= cut * Asel
        for row in S[ok]:
            p = aligned_profile(row)
            if p is not None:
                total += p
                count += 1
    if count < 50:
        return None
    mean = total / count
    res = least_squares(lambda q: burgers(GRID, q[0], q[1]) - mean, [1.0, A0], bounds=([0.2, 0.01], [6.0, 5 * A0]))
    return res.x[0], res.x[1] / A0, count


def load_pairs():
    pairs, single = {}, []
    with open(TUBES, newline="", encoding="utf-8") as f:
        for rec in csv.DictReader(f):
            if rec["src"] == "Mouri07" and rec["u_raw"]:
                pairs.setdefault(float(rec["re_lo"]), []).append((float(rec["r_raw"]), float(rec["u_raw"])))
            elif rec["src"] == "Mouri04" and rec["u_raw"]:
                single.append((float(rec["re_lo"]), float(rec["r_raw"]), float(rec["u_raw"])))
    out = []
    for re, v in sorted(pairs.items()):
        v.sort()                                       # the smaller radius is the stricter (0.1%) cut
        out.append((re, v[0], v[1]))
    return out, single


def draw(table, pairs, single, rows, fa, fb, lr, lu, tilt_deg):
    """fit_threshold.png: raw and corrected r and U against Re_lambda, and the pairs on the master curve of the chord model."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 3, figsize=(16, 4.8))
    re = np.array([p[0] for p in pairs])
    ra, ua = np.array([p[1][0] for p in pairs]), np.array([p[1][1] for p in pairs])
    rb, ub = np.array([p[2][0] for p in pairs]), np.array([p[2][1] for p in pairs])
    r0, u0 = np.array([x[5] for x in rows]), np.array([x[6] for x in rows])
    re4 = np.array([x[0] for x in single])
    r4, u4 = np.array([x[1] for x in single]), np.array([x[2] for x in single])
    rf, uf = math.exp(lr(fb)), math.exp(lu(fb))
    for k, (name, a_, b_, t_, v4, t4, d6) in enumerate((("r_max / eta", ra, rb, r0, r4, r4 / rf, None),
                                                      ("U_max / U_eta", ua, ub, u0, u4, u4 / uf, 0.81 * re ** (1 / 3)))):
        x = ax[k]
        x.scatter(re, a_, marker="^", s=40, facecolors="none", edgecolors="tab:red", label="Mouri 2007, 0.1% (raw)")
        x.scatter(re, b_, marker="v", s=40, facecolors="none", edgecolors="tab:blue", label="Mouri 2007, 1% (raw)")
        x.scatter(re4, v4, marker="s", s=34, facecolors="none", edgecolors="tab:green", label="Mouri 2004, 1% (raw)")
        x.scatter(re, t_, marker="o", s=44, c="k", label="true tube from the pair (tilt <= %g deg)" % tilt_deg)
        x.scatter(re4, t4, marker="s", s=34, c="tab:green", label="Mouri 2004 corrected with the 1% cut")
        if d6 is not None:
            x.plot(np.sort(re), 0.81 * np.sort(re) ** (1 / 3), c="0.5", ls="--", label="fit D6: 0.81 Re^(1/3)")
        x.set_xscale("log"); x.set_xlabel("Re_lambda"); x.set_ylabel(name); x.grid(alpha=0.3, which="both")
    ax[0].legend(fontsize=7, loc="upper left")
    # the pairs on the master curve of the chord model
    fgrid = table[:, 0]
    ax[2].plot(np.exp([lr(f) for f in fgrid]), np.exp([lu(f) for f in fgrid]), c="k", lw=1.6, label="chord model, one tube (the cut f runs along it)")
    for f in (0.3, 0.5, 0.7, 0.9):
        ax[2].annotate("f=%.1f" % f, (math.exp(lr(f)), math.exp(lu(f))), fontsize=7, xytext=(4, -9), textcoords="offset points")
    ax[2].scatter(ra / r0, ua / u0, marker="^", s=40, c="tab:red", alpha=0.8, label="0.1% rows / true tube")
    ax[2].scatter(rb / r0, ub / u0, marker="v", s=40, c="tab:blue", alpha=0.8, label="1% rows / true tube")
    ax[2].axvline(math.exp(lr(fa)), c="tab:red", lw=0.6, ls=":"); ax[2].axvline(math.exp(lr(fb)), c="tab:blue", lw=0.6, ls=":")
    ax[2].set_xlabel("r_measured / r0"); ax[2].set_ylabel("U_measured / U0"); ax[2].grid(alpha=0.3); ax[2].legend(fontsize=7)
    fig.suptitle("Mouri et al. (2007, 2004) threshold averages and the chord model (tilt limit %g deg): cuts f = %.2f (0.1%%) and %.2f (1%%)" % (tilt_deg, fa, fb), fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "fit_threshold.png"), dpi=110)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tilt", type=float, default=45.0, help="tilt limit of the axis out of the plane normal to the path, degrees")
    ap.add_argument("--events", type=int, default=3000)
    ap.add_argument("--sep", type=float, default=None, help="select by the velocity increment over this separation (units of R) instead of the peak signal")
    a = ap.parse_args(argv)
    tilt = math.radians(a.tilt)
    global SEPARATION
    SEPARATION = a.sep
    table = []
    print("master curves (tilt limit %g deg, %d events per cut)" % (a.tilt, a.events))
    print("  cut f    r_fit/r0   U_fit/U0   r*U product")
    for cut in CUTS:
        got = master(cut, a.events, tilt)
        if got is None:
            print("  %.2f     (too few events)" % cut)
            continue
        table.append((cut, got[0], got[1]))
        print("  %.2f     %.3f      %.3f      %.3f" % (cut, got[0], got[1], got[0] * got[1]))
    table = np.array(table)
    lr = lambda f: np.interp(f, table[:, 0], np.log(table[:, 1]))
    lu = lambda f: np.interp(f, table[:, 0], np.log(table[:, 2]))
    pairs, single = load_pairs()
    ratio_r = np.array([math.log(b[0] / a_[0]) for _, a_, b in pairs])
    ratio_u = np.array([math.log(b[1] / a_[1]) for _, a_, b in pairs])

    def resid(q):
        fa, fb = q
        return np.concatenate([ratio_r - (lr(fb) - lr(fa)), ratio_u - (lu(fb) - lu(fa))])
    best = None
    for fa0 in np.linspace(0.3, 0.9, 7):
        for fb0 in np.linspace(0.1, 0.8, 8):
            if fb0 >= fa0:
                continue
            r = least_squares(resid, [fa0, fb0], bounds=([table[0, 0], table[0, 0]], [table[-1, 0], table[-1, 0]]))
            if best is None or r.cost < best.cost:
                best = r
    fa, fb = best.x
    rms = math.sqrt(2 * best.cost / len(ratio_r) / 2)
    print("\nfitted cuts: 0.1%% -> f = %.2f, 1%% -> f = %.2f of the central swirl; rms residual of the log ratios %.3f (the ratios themselves: r %.3f..%.3f, U %.3f..%.3f in log)"
          % (fa, fb, rms, ratio_r.min(), ratio_r.max(), ratio_u.min(), ratio_u.max()))
    print("model ratios r_b/r_a = %.3f, U_b/U_a = %.3f; data mean %.3f, %.3f" % (math.exp(lr(fb) - lr(fa)), math.exp(lu(fb) - lu(fa)),
                                                                              math.exp(ratio_r.mean()), math.exp(ratio_u.mean())))
    print("\nrun Re_l    raw 0.1%%: r, U, rU      true tube: r0, U0, r0U0      r divisor, swirl factor (0.1%%)    from the 1%% row: r0, U0")
    rows = []
    for (re, ra, rb) in pairs:
        r0 = math.exp(0.5 * (math.log(ra[0]) - lr(fa) + math.log(rb[0]) - lr(fb)))
        u0 = math.exp(0.5 * (math.log(ra[1]) - lu(fa) + math.log(rb[1]) - lu(fb)))
        r0a, u0a = ra[0] / math.exp(lr(fa)), ra[1] / math.exp(lu(fa))
        r0b, u0b = rb[0] / math.exp(lr(fb)), rb[1] / math.exp(lu(fb))
        print("%6.0f   %5.2f %5.2f %6.1f      %5.2f %5.2f %6.1f      %5.2f %5.2f      %5.2f %5.2f / %5.2f %5.2f"
              % (re, ra[0], ra[1], ra[0] * ra[1], r0, u0, r0 * u0, ra[0] / r0, u0 / ra[1], r0a, u0a, r0b, u0b))
        rows.append([re, ra[0], ra[1], rb[0], rb[1], r0, u0, r0 * u0, ra[0] / r0, u0 / ra[1]])
    print("\nMouri et al. (2004), 1%% only, corrected with the 1%% cut (f = %.2f):" % fb)
    for re, r, u in single:
        print("%6.0f   raw r %.2f U %.2f   true r0 %.2f U0 %.2f   (r divisor %.2f, swirl factor %.2f)"
              % (re, r, u, r / math.exp(lr(fb)), u / math.exp(lu(fb)), math.exp(lr(fb)), 1 / math.exp(lu(fb))))
    draw(table, pairs, single, rows, fa, fb, lr, lu, a.tilt)
    with open(os.path.join(HERE, "fit_threshold.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["re_lambda", "r_a", "U_a", "r_b", "U_b", "r0", "U0", "Re_c0", "r_divisor_a", "u_factor_a"])
        w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
