"""fit_smoothing.py  v01  The swirl factor of Mouri and Hori (2009): chord model and the length of the hot wire, fitted together with the threshold pairs.

Question.  Mouri and Hori (2009) average the whole distribution of tubes (V0 about 2.4-3.2 u_K); Mouri et al. (2007) give the 0.1% and 1% threshold averages
of the same experiments (V0 = 5.6-14).  fit_threshold.py found that the chord model alone explains the radius of the whole distribution but not its swirl (the
model needs a factor 4.5-5.9 that grows with Re_lambda, beyond its range).  Here the hot wire's sensing length L is added: it averages the velocity over L, which
lowers the measured swirl and widens the profile, more so at high Re_lambda where L/eta grows (L/eta = 2.3 to 13 for L = 1.25 mm).

Forward model (as fit_threshold.py, units R = 1 the Gaussian width of the true tube, central swirl A0 = U0)
    1  a pool of straight-path crossings (tilt limit TILT, random offset and rotation, thinned by the encounter rate);
    2  each signal is averaged over the sensing length, a boxcar of l = L/R (R = r0 / 1.585 in eta: l = (L/eta) 1.585 / r0, so it depends on the unknown r0);
    3  the events whose smoothed amplitude is >= f A0 are kept, aligned on their zero crossing and averaged, and a Burgers profile is fitted to the mean:
       rho_r(f, l) = r_fit / r0, rho_U(f, l) = V_fit / U0.   A table of the logs on a grid of (f, l), saved in fit_smoothing_table.npz.
Inverse problem  per Re_lambda, one tube (r0, U0) and the data (r, U) at three cuts: 0.1% (f_a), 1% (f_b) of Mouri et al. (2007) and the whole distribution (f_c)
of Mouri and Hori (2009); shared by all Re_lambda: f_a > f_b > f_c and the sensing length L.  66 numbers, 22 + 4 unknowns: the residuals are the test.
Output  the fitted cuts and L (against 1.0-1.25 mm), the residuals, the tube r0, U0 for every Re_lambda and the factors the 2009 data need
(radius divisor, swirl factor) with and without the length; fit_smoothing.csv.  Nothing here changes corrections.json.
Usage: python fit_smoothing.py [--tilt 45] [--pool 20000] [--length 1.25]   (--length fixes L in mm instead of fitting it)

Versions  M01 m01.v01 (2026-11-11): first version.
"""
import argparse
import csv
import math
import os
import sys

import numpy as np
from scipy.ndimage import uniform_filter1d
from scipy.optimize import least_squares, minimize

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chord_model as cm       # noqa: E402
import fit_threshold as ft     # noqa: E402
import sourcedata as sd        # noqa: E402

TUBES = ft.TUBES
FGRID = np.array([0.04, 0.06, 0.08, 0.10, 0.14, 0.18, 0.22, 0.28, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85])
LGRID = np.array([0.0, 0.3, 0.6, 1.0, 1.5, 2.2, 3.2, 4.5, 6.5])
NU_09 = 0.141e-4                                           # m^2/s, the kinematic viscosity of the experiments (Table I, 0.141-0.143 cm^2/s)


def eta_mm(re):
    """The Kolmogorov length in mm from the dissipation of the experiment (sourcedata.EPS_M) and nu."""
    return 1e3 * (NU_09 ** 3 / sd.EPS_M[int(round(re))]) ** 0.25


def pool(n, tilt):
    A0 = cm.reference_amplitude()
    out, have = [], 0
    sin_t = math.sin(tilt)
    while have < n:
        m = 6000
        alpha = np.arcsin(cm.RNG.uniform(-sin_t, sin_t, m))
        phi = cm.RNG.uniform(0, 2 * math.pi, m)
        b = cm.RNG.uniform(-14.0, 14.0, m)
        thin = cm.RNG.uniform(0, 1, m) < np.cos(alpha)
        S = cm.signal(alpha[thin], phi[thin], b[thin]).astype(np.float32)
        keep = np.max(np.abs(S), axis=1) >= 0.02 * A0
        out.append(S[keep])
        have += int(keep.sum())
    return np.concatenate(out)[:n], A0


def table(path, n, tilt):
    """log rho_r, log rho_U on FGRID x LGRID (None where too few events), cached in path."""
    if os.path.exists(path):
        z = np.load(path)
        if abs(float(z["tilt"]) - tilt) < 1e-9 and int(z["pool"]) == n:
            return z["lr"], z["lu"]
    S0, A0 = pool(n, tilt)
    lr = np.full((len(FGRID), len(LGRID)), np.nan)
    lu = np.full_like(lr, np.nan)
    step = cm.S_GRID[1] - cm.S_GRID[0]
    for j, ell in enumerate(LGRID):
        width = max(1, int(round(ell / step)) | 1)
        S = uniform_filter1d(S0, size=width, axis=1, mode="constant") if width > 1 else S0
        amp = np.max(np.abs(S), axis=1)
        for i, f in enumerate(FGRID):
            sel = np.nonzero(amp >= f * A0)[0]
            if len(sel) < 60:
                continue
            total, count = np.zeros_like(ft.GRID), 0
            for k in sel:
                p = ft.aligned_profile(S[k].astype(float))
                if p is not None:
                    total += p
                    count += 1
            if count < 60:
                continue
            mean = total / count
            res = least_squares(lambda q: ft.burgers(ft.GRID, q[0], q[1]) - mean, [math.sqrt(1 + ell * ell / 6), A0 / 2], bounds=([0.2, 0.001], [25.0, 5 * A0]))
            lr[i, j], lu[i, j] = math.log(res.x[0]), math.log(res.x[1] / A0)
        print("  l = %.1f done" % ell, flush=True)
    np.savez(path, lr=lr, lu=lu, tilt=tilt, pool=n)
    return lr, lu


def interpolator(grid):
    """Bilinear interpolation of a table on (FGRID, LGRID); NaN cells are filled from the nearest valid cell in f."""
    g = grid.copy()
    for j in range(g.shape[1]):
        good = ~np.isnan(g[:, j])
        if good.any() and not good.all():
            g[:, j] = np.interp(FGRID, FGRID[good], g[good, j])
    def at(f, ell):
        f = min(max(f, FGRID[0]), FGRID[-1])
        ell = min(max(ell, LGRID[0]), LGRID[-1])
        i = min(int(np.searchsorted(FGRID, f)) - 1, len(FGRID) - 2) if f > FGRID[0] else 0
        j = min(int(np.searchsorted(LGRID, ell)) - 1, len(LGRID) - 2) if ell > LGRID[0] else 0
        tf = (f - FGRID[i]) / (FGRID[i + 1] - FGRID[i])
        tl = (ell - LGRID[j]) / (LGRID[j + 1] - LGRID[j])
        return ((1 - tf) * (1 - tl) * g[i, j] + tf * (1 - tl) * g[i + 1, j] + (1 - tf) * tl * g[i, j + 1] + tf * tl * g[i + 1, j + 1])
    return at


def load_data():
    pairs, _ = ft.load_pairs()
    nine = {}
    with open(TUBES, newline="", encoding="utf-8") as f:
        for rec in csv.DictReader(f):
            if rec["src"] == "Mouri09":
                nine[float(rec["re_lo"])] = (float(rec["r_raw"]), float(rec["u_raw"]))
    return [(re, ra, rb, nine[re]) for re, ra, rb in pairs]


def inner(theta, run, rho_r, rho_u, L):
    """For one Re_lambda: best tube (r0, U0) for the cuts and length in theta; returns (sum of squared log residuals, r0, U0, residual list)."""
    fa, fb, fc = theta[:3]
    mm = theta[3] if L is None else L
    re, ra, rb, rc = run
    obs = [(ra, fa), (rb, fb), (rc, fc)]
    leta = mm / eta_mm(re)
    best = None
    for r0 in np.exp(np.linspace(math.log(2.5), math.log(9.0), 90)):
        ell = leta * cm.RMAX / r0
        lr = [rho_r(f, ell) for _, f in obs]
        lu = [rho_u(f, ell) for _, f in obs]
        res_r = [math.log(o[0]) - math.log(r0) - x for (o, _), x in zip(obs, lr)]
        lu0 = np.mean([math.log(o[1]) - x for (o, _), x in zip(obs, lu)])
        res_u = [math.log(o[1]) - lu0 - x for (o, _), x in zip(obs, lu)]
        sse = sum(v * v for v in res_r) + sum(v * v for v in res_u)
        if best is None or sse < best[0]:
            best = (sse, r0, math.exp(lu0), res_r + res_u)
    return best


def total(theta, data, rho_r, rho_u, L):
    fa, fb, fc = theta[:3]
    pen = 0.0
    if not (fa > fb > fc > 0.0):
        pen = 10.0 + 50 * max(0.0, fb - fa) + 50 * max(0.0, fc - fb)
    return sum(inner(theta, run, rho_r, rho_u, L)[0] for run in data) + pen


def fit(data, rho_r, rho_u, L, start):
    best = None
    for s in start:
        r = minimize(total, s, args=(data, rho_r, rho_u, L), method="Nelder-Mead", options=dict(xatol=1e-3, fatol=1e-6, maxiter=500))
        if best is None or r.fun < best.fun:
            best = r
    return best


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tilt", type=float, default=45.0)
    ap.add_argument("--pool", type=int, default=20000)
    ap.add_argument("--length", type=float, default=None, help="fix the sensing length in mm")
    a = ap.parse_args(argv)
    path = os.path.join(HERE, "fit_smoothing_table.npz")
    print("table of the chord model with the wire length (tilt %g, pool %d); cached in %s" % (a.tilt, a.pool, os.path.basename(path)))
    lr, lu = table(path, a.pool, math.radians(a.tilt))
    rho_r, rho_u = interpolator(lr), interpolator(lu)
    data = load_data()
    results = {}
    for label, L in (("L fitted", None), ("L = 1.25 mm", 1.25), ("L = 1.0 mm", 1.0), ("no wire length (L = 0)", 0.0)):
        if a.length is not None and L is None:
            continue
        starts = [[0.7, 0.4, 0.15, 1.2], [0.8, 0.5, 0.2, 0.8], [0.6, 0.3, 0.1, 1.8]] if L is None else [[0.7, 0.4, 0.15, 0], [0.8, 0.5, 0.2, 0], [0.6, 0.3, 0.1, 0]]
        r = fit(data, rho_r, rho_u, L, starts)
        th = r.x
        sse = sum(inner(th, run, rho_r, rho_u, L)[0] for run in data)
        results[label] = (th, sse, L)
        print("\n%s: f(0.1%%) = %.2f, f(1%%) = %.2f, f(whole) = %.2f%s; rms log residual %.3f over %d numbers"
              % (label, th[0], th[1], th[2], ", L = %.2f mm" % th[3] if L is None else "", math.sqrt(sse / (6 * len(data))), 6 * len(data)))
    th, sse, L = results["L fitted" if "L fitted" in results else "L = 1.25 mm"]
    print("\nper Re_lambda (%s):  L/eta   tube r0, U0   2009 raw r, U   radius divisor  swirl factor   residual rms" % ("L fitted" if L is None else "L fixed"))
    rows = []
    for run in data:
        sse_i, r0, u0, res = inner(th, run, rho_r, rho_u, L)
        mm = th[3] if L is None else L
        print("%6.0f   %5.1f   %5.2f %6.2f     %5.2f %5.2f     %5.2f       %5.2f       %.3f" % (run[0], mm / eta_mm(run[0]), r0, u0, run[3][0], run[3][1],
                                                                                          run[3][0] / r0, u0 / run[3][1], math.sqrt(sse_i / 6)))
        rows.append([run[0], mm / eta_mm(run[0]), r0, u0, run[3][0], run[3][1], run[3][0] / r0, u0 / run[3][1]])
    with open(os.path.join(HERE, "fit_smoothing.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["re_lambda", "L_over_eta", "r0", "U0", "r_2009", "U_2009", "r_divisor", "u_factor"])
        w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
