"""belin_range_numbers.py  v01  The tubes of the fit to Belin et al. (1996) taken as the ground truth, over a range of Re_lambda: the true r_max and U_max (mode and mean of the generated population) and the same quantities as the probes observe them.
Population  chord_belin_sens.py with the fitted inputs: r_max lognormal (median 7.29 eta, ln-width 0.58), U_max = 2.58 x 0.769 Re_lambda^(1/3) U_eta x lognormal (0.38).  The mode and the mean are of the distribution itself, no median.
Probes      (a) Belin's wire: the events that pass his gradient cut and can be read; r = half the spacing of the extrema, U = dS / (2 x 0.14) (his rule), as in belin_results.py.
            (b) a crossed wire with Mouri's selection (Mouri et al. 2007): events whose increment of the transverse velocity over the sampling interval dx_s (boxcar of 1 mm) is above the threshold that holds 1% (k = 3.6 sigma) or 0.1% (k = 6.4 sigma) of the increments;
                each event is observed on its own trace: r = half the distance between the extrema of the smoothed signal within +-10 R (R = r_max / 1.585, the core size of the tube itself) of the steepest increment, U = half the peak-to-peak value.  dx_s / eta and probe / eta follow Mouri's table (log Re_lambda interpolation, constant outside 332-1934).
            Weights are the footprint weights of the importance sampling, as everywhere in the model.  The model has no background turbulence, and the Re_lambda above 718 are extrapolations of the Belin tubes.
Output      belin_range_numbers.json, belin_range_numbers.png
Usage       python belin_range_numbers.py [--n 40000]
Versions    M01 m01.v02 (2026-11-13): the window of the extrema is +-10 R of each tube (was a fixed 12 eta, which put a spike of events at the window edge).
"""
import argparse
import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chord_belin_volume as cbv      # noqa: E402
import chord_belin_sens_fit as sf     # noqa: E402
import chord_mouri as cm              # noqa: E402
import belin_results as br            # noqa: E402

RE_RANGE = (100, 150, 250, 400, 650, 1000, 1500, 2000)
K1, K01 = 3.6, 6.4                    # thresholds of the 1% and 0.1% classes, in standard deviations of the increment (Mouri et al. 2007, Table II: 3.5-3.7, 6.0-6.7)
WIN = 10.0                            # in units of R = r_max / 1.585 of each tube: the extrema are looked for within +-10 R of the steepest increment
LOGRE = np.log([m[0] for m in cm.MOURI])
SEP = [m[2] / m[1] for m in cm.MOURI]
PROBE = [0.1 / m[1] for m in cm.MOURI]


def mouri_setup(Rl):
    return float(np.interp(np.log(Rl), LOGRE, SEP)), float(np.interp(np.log(Rl), LOGRE, PROBE))


def mouri_events(Rl, cfg, n, seed=31):
    """Per-event observation of the Mouri classes: weights, true r and U, observed r and U, and the peak increment in sigma."""
    rng = np.random.default_rng(seed)
    sep, probe = mouri_setup(Rl)
    r = np.exp(math.log(cfg["r_median"]) + cfg["r_sigma"] * rng.standard_normal(n))
    umax = 0.769 * Rl ** (1 / 3) * cfg["umax_scale"] * np.exp(cfg["u_sigma"] * rng.standard_normal(n))
    width = r / cbv.RATIO
    old = cbv.CUT
    cbv.CUT = K1 * cm.SIGMA_GT / cbv.SIGMA_GRADIENT
    reach = cbv.reach(r, umax)
    cbv.CUT = old
    b = rng.uniform(-reach, reach)
    sa = rng.uniform(-1, 1, n)
    phi = rng.uniform(0, 2 * math.pi, n)
    w = np.sqrt(1 - sa ** 2) * reach
    step = cbv.STEP * width
    r_obs, u_obs, peak = np.zeros(n), np.zeros(n), np.zeros(n)
    for start in range(0, n, 1000):
        sl = slice(start, start + 1000)
        v = cbv.signal(np.arcsin(sa[sl]), phi[sl], b[sl] / width[sl]) * (umax[sl] / cbv.GMAX)[:, None, None]
        S = v[:, :, 1]
        Ssm = cm.box_smooth(S, np.maximum(np.round(0.5 * probe / step[sl]).astype(int), 0))
        d = np.maximum(np.round(sep / step[sl]).astype(int), 1)
        inc = np.abs(cm.increment(Ssm, d))
        x0 = np.argmax(inc, axis=1)
        peak[sl] = inc[np.arange(len(x0)), x0] / (cm.SIGMA_GT * sep)
        xs = (cbv.GRID[None, :] - cbv.GRID[x0][:, None]) * width[sl][:, None]
        inside = np.abs(xs) <= WIN * width[sl][:, None]
        ih, il = np.argmax(np.where(inside, Ssm, -np.inf), axis=1), np.argmin(np.where(inside, Ssm, np.inf), axis=1)
        rows = np.arange(len(ih))
        r_obs[sl] = 0.5 * np.abs(xs[rows, ih] - xs[rows, il])
        u_obs[sl] = 0.5 * (Ssm[rows, ih] - Ssm[rows, il])
    return dict(w=w, r=r, umax=umax, r_obs=r_obs, u_obs=np.abs(u_obs), peak=peak, sep=sep, probe=probe)


def md(v, w, hi, nbin=120):
    """Mode (the maximum of the weighted histogram, 120 bins from 0 to hi) and mean."""
    h = np.histogram(v, np.linspace(0, hi, nbin + 1), weights=w)[0]
    k = int(np.argmax(h))
    return dict(mode=float(0.5 * (2 * k + 1) * hi / nbin), mean=float(np.sum(v * w) / np.sum(w)))


def fmt(q):
    return "none" if q is None else "r %.2f/%.2f U %.1f/%.1f" % (q["r"]["mode"], q["r"]["mean"], q["U_over_Ueta"]["mode"], q["U_over_Ueta"]["mean"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40000)
    ap.add_argument("--params", type=float, nargs=4, default=[7.29, 0.58, 2.58, 0.38])
    args = ap.parse_args()
    cfg = sf.config(np.log(np.array(args.params)))
    out = []
    for Rl in RE_RANGE:
        nb, res = br.numbers(Rl, cfg, args.n)
        row = dict(Re_lambda=Rl, U_eta_cm_s=res["ue"], true=dict(r=nb["r_population"], U_over_Ueta=nb["U_population"]),
                   belin_probe=dict(r=nb["r_read"], U_over_Ueta=nb["U_belin"], share_of_hits_read=nb["share_read_of_selected"]))
        ev = mouri_events(Rl, cfg, args.n)
        for name, k in (("mouri_1pc", K1), ("mouri_01pc", K01)):
            m = ev["peak"] >= k
            if m.sum() < 50:
                row[name] = None
                continue
            row[name] = dict(r=md(ev["r_obs"][m], ev["w"][m], 40), U_over_Ueta=md(ev["u_obs"][m], ev["w"][m], 120), true_r=md(ev["r"][m], ev["w"][m], 40),
                             true_U_over_Ueta=md(ev["umax"][m], ev["w"][m], 120), events=int(m.sum()), share_of_weight=float(ev["w"][m].sum() / ev["w"].sum()))
        row["mouri_sep_eta"], row["mouri_probe_eta"] = ev["sep"], ev["probe"]
        out.append(row)
        print("Re_lambda %d: true r %.2f/%.2f U %.1f/%.1f | Belin r %.2f/%.2f U %.1f/%.1f | 1%%: %s | 0.1%%: %s" % (
            Rl, row["true"]["r"]["mode"], row["true"]["r"]["mean"], row["true"]["U_over_Ueta"]["mode"], row["true"]["U_over_Ueta"]["mean"],
            row["belin_probe"]["r"]["mode"], row["belin_probe"]["r"]["mean"], row["belin_probe"]["U_over_Ueta"]["mode"], row["belin_probe"]["U_over_Ueta"]["mean"],
            fmt(row["mouri_1pc"]), fmt(row["mouri_01pc"])), flush=True)
    with open(os.path.join(HERE, "belin_range_numbers.json"), "w") as f:
        json.dump(out, f, indent=1)
    fig, ax = plt.subplots(2, 2, figsize=(12, 9), sharex=True)
    series = [("true population", lambda r: r["true"], "k", "-"), ("Belin's wire (his reading)", lambda r: r["belin_probe"], "tab:red", "-"),
              ("Mouri 1% class, per event", lambda r: r["mouri_1pc"], "tab:blue", "--"), ("Mouri 0.1% class, per event", lambda r: r["mouri_01pc"], "tab:green", "--")]
    for col, key, ylabel in ((0, "r", "r_max / eta"), (1, "U_over_Ueta", "U_max / U_eta")):
        for row_i, stat in enumerate(("mode", "mean")):
            a = ax[row_i, col]
            for name, get, colour, ls in series:
                pts = [(r["Re_lambda"], get(r)[key][stat]) for r in out if get(r) is not None]
                a.plot(*zip(*pts), "o" + ls, color=colour, label=name)
            a.axvspan(100, 718, color="0.93", zorder=0)
            a.set_xscale("log")
            a.set_ylabel("%s: %s of the distribution" % (ylabel, stat))
            a.set_xlabel("Re_lambda")
            a.legend(fontsize=7)
    fig.suptitle("Tubes of the Belin fit as the ground truth, and as each probe observes them (grey band: the range of Belin's data)", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_range_numbers.png"), dpi=90)


if __name__ == "__main__":
    main()
