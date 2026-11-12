"""fit_chord.py  v01  Fit the chord model to the size distribution measured by Belin et al. (1996), Fig. 5.

Data: belin_fig5_digitised.csv (digitise_belin.py), renormalised to unit area, R_m/eta < 19.
Model: the radius read by the probe R_m is the true radius R of a tube times the chord ratio rho = R_m/R, whose density g(rho | alpha_max, f)
comes from the 3D crossing model (chord_kernel.py: random impact parameter and orientation, tilt limited to alpha_max, event kept when its
peak is at least a fraction f of the central-crossing peak).  The true radii follow a lognormal, ln R ~ N(ln R0, s^2), R in units of eta
(R is the Gaussian width, r_max = 1.585 R).  Observed density
        p(R_m) = integral p_true(R) g(R_m/R) / R dR .
Parameters fitted: R0, s and f for each tilt limit alpha_max; also a fit with no chord effect (rho = 1) for comparison.
Usage: python fit_chord.py      (writes belin_fit.png and belin_kernel.png)
"""
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
import chord_kernel as ck

RMAX_PER_R = math.sqrt(2 * 1.2564312086261697)           # r_max = 1.585 R
RGRID = np.exp(np.linspace(math.log(0.6), math.log(40), 260))


def load():
    d = np.loadtxt(os.path.join(HERE, "belin_fig5_digitised.csv"), delimiter=",", skiprows=1)
    d = d[d[:, 0] < 19.0]
    area = np.trapezoid(d[:, 1], d[:, 0])
    return d[:, 0], d[:, 1] / area


def observed(rm, R0, s, g_grid, g_val):
    """p(R_m) for a lognormal true-radius density and the chord kernel (grid, values)."""
    p_true = np.exp(-0.5 * ((np.log(RGRID) - math.log(R0)) / s) ** 2) / (RGRID * s * math.sqrt(2 * math.pi))
    rho = rm[:, None] / RGRID[None, :]
    g = np.interp(rho, g_grid, g_val, left=0.0, right=0.0) if g_val is not None else None
    return np.trapezoid(p_true[None, :] * g / RGRID[None, :], RGRID, axis=1)


def delta_kernel(rm, R0, s):
    """No chord effect: the observed density is the lognormal itself."""
    return np.exp(-0.5 * ((np.log(rm) - math.log(R0)) / s) ** 2) / (rm * s * math.sqrt(2 * math.pi))


def fit_one(rm, p, alpha_max):
    def resid(v):
        R0, s, f = math.exp(v[0]), v[1], v[2]
        gg, gv = ck.kernel(alpha_max, f)
        return observed(rm, R0, s, gg, gv) - p
    best = None
    for f0 in (0.2, 0.4, 0.7):
        for R0 in (2.5, 3.5):
            r = least_squares(resid, [math.log(R0), 0.3, f0], bounds=([math.log(0.8), 0.03, 0.03], [math.log(8), 1.2, 0.98]))
            if best is None or r.cost < best.cost:
                best = r
    return best


def main():
    rm, p = load()
    results = {}
    for alpha_max in (0, 30, 45, 60, 90):
        r = fit_one(rm, p, alpha_max)
        R0, s, f = math.exp(r.x[0]), r.x[1], r.x[2]
        rms = math.sqrt(2 * r.cost / len(rm))
        results[alpha_max] = (R0, s, f, rms, r)
        mean_true = R0 * math.exp(s * s / 2)
        print("alpha_max %2d deg: R0 = %.2f eta (true median r_max = %.2f)  s = %.2f  f = %.2f   rms misfit %.4f   (true mean r_max = %.2f)"
              % (alpha_max, R0, RMAX_PER_R * R0, s, f, rms, RMAX_PER_R * mean_true))
    r0 = least_squares(lambda v: delta_kernel(rm, math.exp(v[0]), v[1]) - p, [math.log(4), 0.5])
    print("no chord effect (rho = 1): R0 = %.2f eta  s = %.2f   rms misfit %.4f" % (math.exp(r0.x[0]), r0.x[1], math.sqrt(2 * r0.cost / len(rm))))
    best = min(results, key=lambda a: results[a][3])
    R0, s, f, rms, _ = results[best]
    # figure 1: data and fits
    fig, ax = plt.subplots(figsize=(10, 6.5))
    ax.plot(rm, p, "k.", ms=7, label="Belin Fig. 5 (digitised, area 1)")
    x = np.linspace(0.5, 19, 400)
    for a, col in zip((0, 45, 90), ("#1b4f72", "#e67e22", "#c0392b")):
        R0a, sa, fa, rmsa, _ = results[a]
        gg, gv = ck.kernel(a, fa)
        ax.plot(x, observed(x, R0a, sa, gg, gv), c=col, lw=1.8, label="chord model, tilt <= %d deg: R0=%.2f, s=%.2f, f=%.2f (rms %.4f)" % (a, R0a, sa, fa, rmsa))
    ax.plot(x, delta_kernel(x, math.exp(r0.x[0]), r0.x[1]), "g--", lw=1.4, label="lognormal, no chord effect (rms %.4f)" % math.sqrt(2 * r0.cost / len(rm)))
    gg, gv = ck.kernel(best, f)
    pt = np.exp(-0.5 * ((np.log(x) - math.log(R0)) / s) ** 2) / (x * s * math.sqrt(2 * math.pi))
    ax.plot(x, pt, c="0.5", ls=":", lw=1.4, label="true radius pdf of the best fit (tilt <= %d deg)" % best)
    ax.set_xlabel(r"radius read by the probe $R_m/\eta$")
    ax.set_ylabel(r"$p(R_m/\eta)$")
    ax.set_xlim(0, 19)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    ax.set_title("Chord model fitted to the measured size distribution of Belin et al. (1996)")
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_fit.png"), dpi=110)
    # figure 2: smooth kernels for identical tubes
    fig2, axes = plt.subplots(1, 3, figsize=(16, 5), sharey=True)
    for axk, a in zip(axes, (0, 45, 90)):
        for fv, col in zip((0.8, 0.5, 0.3, 0.2, 0.1), ("#1b4f72", "#2e86c1", "#e67e22", "#c0392b", "#7d3c98")):
            gg, gv = ck.kernel(a, fv)
            mean = np.sum(gg * gv) * 0.01
            cum = np.cumsum(gv) * 0.01
            axk.plot(gg, gv, c=col, lw=1.6, label="f=%.1f: mean %.2f, median %.2f" % (fv, mean, float(np.interp(0.5, cum, gg))))
        axk.set_xlim(0.8, 6)
        axk.set_title("tilt limit %d deg" % a)
        axk.set_xlabel(r"$\rho=R_m/R$ (chord radius over true radius)")
        axk.legend(fontsize=8)
        axk.grid(alpha=0.25)
    axes[0].set_ylabel(r"$g(\rho)$ for identical tubes")
    fig2.suptitle("Distribution of the chord radius for identical tubes, smoothed (impact parameter and orientation integrated)")
    fig2.tight_layout()
    fig2.savefig(os.path.join(HERE, "belin_kernel.png"), dpi=110)


if __name__ == "__main__":
    main()
