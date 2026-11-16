"""chord_mouri.py  v01  The methods of Mouri et al. (2007, 2009) and Sassa and Makita (2005) applied to the tube population found from Belin's records (chord_belin_sens.py, belin_results.py): do the three one-dimensional detection methods
read the tubes that Belin's wire reads?  A test of the population, and of the corrections of the page (Mouri and Hori 2009: radius / 1.75, swirl x 3).
Signal   a crossed wire gives the transverse velocity v (the spanwise v of Mouri, the vertical w of Sassa), linear in the swirl, along the path of the mean flow: S(s) = v_y of the Burgers tube (isotropic axis, offset b), the path
         along e_x; the signal is smoothed by the probe (a boxcar of the length of the probe: 1 mm for Mouri, about eta for Sassa).
Methods  Mouri et al. (2007): the increment v(x + d/2) - v(x - d/2) over the sampling interval d = dx_s; events where |increment| >= k sigma, sigma = sqrt(2/15) (U_eta/eta) d the rms increment (k = 3.5: the top 1%; 6.3-6.7: the top 0.1%, their
         Table II); the signals of the events are aligned on the increment, the sign made equal, averaged, and the mean profile is fitted by the Burgers vortex around its peaks (R0, V0).
         Mouri and Hori (2009): all tubes: the increment over d0 = 6 eta, events above a low threshold (the background; k = 1.5, 2, 3 are tried); the same averaging and fit.
         Sassa and Makita (2005): events where dw/dt >= C rms(dw/dt) (C = 2.5, Fig. 2 scans 1.5-3.5); the average of the signals; diameter = interval of the two peaks of the mean trace, V = the peak.
Tubes    the population of the fit to Belin: r_max lognormal (median 7.29 eta, ln-width 0.58), U_max = 2.58 x 0.769 Re_lambda^(1/3) U_eta x lognormal 0.38; weights (the footprint) as in chord_belin_sens.py; no background turbulence.
Output   chord_mouri<tag>.json (chord_mouri_plot.py makes the figure): R0/eta and V0/u_K as the three methods read them, against the values of the papers, and against the true tubes of the events.
Usage:   python chord_mouri.py [--n 30000]

Versions  M01 m01.v01 (2026-11-13): first version.
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
from scipy.optimize import least_squares

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chord_belin_volume as cbv      # noqa: E402
import chord_belin_sens as cs         # noqa: E402
import chord_belin_sens_fit as sf     # noqa: E402

SIGMA_GT = math.sqrt(2.0 / 15.0)                                     # rms of the transverse gradient, U_eta / eta
XB, KB = 1.2564312, 0.71531                                          # Burgers: x = 1.2564, K_B = 1 - exp(-x)
XGRID = np.arange(-60.0, 60.01, 0.5)                                 # common position grid of the mean profiles, eta

# (Re_lambda, eta cm, dx_s cm, dx0 / eta, k for 0.1 %, k for 1 %, paper: R0/eta all, V0/uK all, R0 0.1 %, V0 0.1 %, R0 1 %, V0 1 %)   Mouri and Hori (2009) Tables 1-2, Mouri et al. (2007) Table II
MOURI = [(332, 0.0539, 0.0378, 6.30, 6.45, 3.61, 8.45, 2.43, 5.18, 7.60, 6.53, 5.61),
         (719, 0.0288, 0.0355, 6.16, 6.69, 3.66, 8.56, 2.43, 5.21, 8.67, 6.50, 6.11),
         (1098, 0.0177, 0.0255, 5.76, 6.50, 3.62, 8.91, 2.56, 5.64, 10.0, 6.61, 6.83),
         (1934, 0.00955, 0.0212, 6.66, 6.01, 3.52, 8.81, 3.18, 6.20, 14.0, 7.03, 9.17)]


def burgers_profile(x, r0, v0):
    a = np.maximum(np.abs(x) / r0, 1e-9)
    return np.sign(x) * v0 * (1 - np.exp(-XB * a ** 2)) / (KB * a)


def box_smooth(S, half):
    """Boxcar average of each row over 2 half + 1 points (half an integer array, one per row)."""
    n, m = S.shape
    cum = np.concatenate([np.zeros((n, 1)), np.cumsum(S, axis=1)], axis=1)
    j = np.arange(m)[None, :]
    lo, hi = np.clip(j - half[:, None], 0, m), np.clip(j + half[:, None] + 1, 0, m)
    return (np.take_along_axis(cum, hi, axis=1) - np.take_along_axis(cum, lo, axis=1)) / np.maximum(hi - lo, 1)


def increment(S, shift):
    """S(j + ceil(d/2)) - S(j - floor(d/2)) with d = shift, an integer per row."""
    n, m = S.shape
    j = np.arange(m)[None, :]
    a = np.clip(j + ((shift + 1) // 2)[:, None], 0, m - 1)
    b = np.clip(j - (shift // 2)[:, None], 0, m - 1)
    return np.take_along_axis(S, a, axis=1) - np.take_along_axis(S, b, axis=1)


def read_profile(sumprof, sumw):
    """R0, V0 of the mean profile: Burgers fit around the peaks (|x| <= 2 x_peak) and the peak reading (Sassa): half the peak separation and the peak height."""
    P = sumprof / max(sumw, 1e-30)
    A = 0.5 * (P - P[::-1])                                                      # the antisymmetric part
    pos = XGRID > 0
    k = np.argmax(A[pos])
    xp, vp = XGRID[pos][k], A[pos][k]
    sel = np.abs(XGRID) <= max(2.0 * xp, 4.0)
    fit = least_squares(lambda q: burgers_profile(XGRID[sel], q[0], q[1]) - A[sel], [xp, vp], bounds=([0.5, 0.0], [80.0, 500.0]))
    return dict(R0=float(fit.x[0]), V0=float(fit.x[1]), r_peak=float(xp), v_peak=float(vp))


def run(Rl, cfg, n, specs, probe, seed=21):
    """The conditional mean profiles of the specs for the tubes of the model at Re_lambda; specs: list of (name, separation eta, threshold in sigma, is_all)."""
    rng = np.random.default_rng(seed)
    c = cs.bu.chain_at(Rl)
    r = np.exp(math.log(cfg["r_median"]) + cfg["r_sigma"] * rng.standard_normal(n))
    umax = 0.769 * Rl ** (1 / 3) * cfg["umax_scale"] * np.exp(cfg["u_sigma"] * rng.standard_normal(n))
    width = r / cbv.RATIO
    gmin = min(s[2] for s in specs) * SIGMA_GT
    old = cbv.CUT
    cbv.CUT = gmin / cbv.SIGMA_GRADIENT                                         # reach(): gradient threshold gmin (U_eta / eta)
    reach = cbv.reach(r, umax)
    cbv.CUT = old
    b = rng.uniform(-reach, reach)
    sa = rng.uniform(-1, 1, n)
    phi = rng.uniform(0, 2 * math.pi, n)
    w = np.sqrt(1 - sa ** 2) * reach
    step = cbv.STEP * width                                                      # eta per grid point of each tube
    acc = {s[0]: [np.zeros(len(XGRID)), 0.0, 0.0, 0.0, 0.0] for s in specs}     # profile sum, weight, sum w r, sum w U, count
    for start in range(0, n, 1000):
        sl = slice(start, start + 1000)
        v = cbv.signal(np.arcsin(sa[sl]), phi[sl], b[sl] / width[sl]) * (umax[sl] / cbv.GMAX)[:, None, None]
        S = v[:, :, 1]                                                           # the transverse component, U_eta
        half = np.maximum(np.round(0.5 * probe / step[sl]).astype(int), 0)
        Ssm = box_smooth(S, half)
        for name, sep, thr, is_all in specs:
            d = np.maximum(np.round(sep / step[sl]).astype(int), 1)
            inc = increment(Ssm, d)
            absinc = np.abs(inc)
            x0 = np.argmax(absinc, axis=1)
            peak = absinc[np.arange(len(x0)), x0]
            ok = peak >= thr * SIGMA_GT * sep
            a = acc[name]
            for i in np.nonzero(ok)[0]:
                sgn = np.sign(inc[i, x0[i]])
                xs = (cbv.GRID - cbv.GRID[x0[i]]) * width[sl][i] * 1.0
                a[0] += w[sl][i] * np.interp(XGRID, xs, sgn * Ssm[i], left=0.0, right=0.0)
                a[1] += w[sl][i]
                a[2] += w[sl][i] * r[sl][i]
                a[3] += w[sl][i] * umax[sl][i]
                a[4] += 1
    out = {}
    for name, sep, thr, is_all in specs:
        a = acc[name]
        if a[4] < 100:
            continue
        rd = read_profile(a[0], a[1])
        rd.update(true_r=a[2] / a[1], true_U=a[3] / a[1], count=int(a[4]), uK=1.0)
        out[name] = rd
    out["population"] = dict(true_r=float(np.mean(r)), true_U=float(np.mean(umax)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30000)
    ap.add_argument("--params", type=float, nargs=4, default=[7.29, 0.58, 2.58, 0.38])
    ap.add_argument("--tag", default="", help="suffix of the json file name")
    args = ap.parse_args()
    cfg = sf.config(np.log(np.array(args.params)))
    result = dict(mouri=[], sassa=[])
    for Rl, eta_cm, dxs_cm, dx0, k01, k1, r_all, v_all, r01, v01, r1, v1 in MOURI:
        probe = 0.1 / eta_cm                                                      # 1 mm in eta
        sep_s = dxs_cm / eta_cm
        specs = [("0.1%", sep_s, k01, False), ("1%", sep_s, k1, False), ("all k=1.5", dx0, 1.5, True), ("all k=2", dx0, 2.0, True), ("all k=3", dx0, 3.0, True)]
        res = run(Rl, cfg, args.n, specs, probe)
        res.update(Re_lambda=Rl, probe_eta=probe, sep_eta=sep_s, paper=dict(r_all=r_all, v_all=v_all, r01=r01, v01=v01, r1=r1, v1=v1))
        result["mouri"].append(res)
        print("Re_lambda %d (probe %.1f eta, increment %.2f eta): population mean r_max %.2f, U_max %.1f" % (Rl, probe, sep_s, res["population"]["true_r"], res["population"]["true_U"]))
        for name, _, _, _ in specs:
            if name in res:
                q = res[name]
                pr, pv = {"0.1%": (r01, v01), "1%": (r1, v1)}.get(name, (r_all, v_all))
                print("   %-10s R0 %.2f (paper %.2f)  V0/uK %.2f (paper %.2f) | peak reading r %.2f, v %.2f | true r %.2f, U %.1f | events %d" % (name, q["R0"], pr, q["V0"], pv, q["r_peak"], q["v_peak"], q["true_r"], q["true_U"], q["count"]), flush=True)
    for Rl in (19, 300, 820, 2391):
        specs = [("C=%.1f" % C, 0.5, C, False) for C in (1.5, 2.0, 2.5, 3.0, 3.5)]
        res = run(Rl, cfg, args.n, specs, 1.0)
        res["Re_lambda"] = Rl
        result["sassa"].append(res)
        print("Sassa, Re_lambda %d (probe 1 eta): population mean r_max %.2f, U_max %.1f" % (Rl, res["population"]["true_r"], res["population"]["true_U"]))
        for name, _, _, _ in specs:
            if name in res:
                q = res[name]
                print("   %-8s diameter D/eta %.1f (r_peak x 2), V peak %.2f uK | Burgers R0 %.2f V0 %.2f | true r %.2f U %.1f | events %d" % (name, 2 * q["r_peak"], q["v_peak"], q["R0"], q["V0"], q["true_r"], q["true_U"], q["count"]), flush=True)
    with open(os.path.join(HERE, "chord_mouri%s.json" % args.tag), "w") as f:
        json.dump(result, f, indent=1)


if __name__ == "__main__":
    main()
