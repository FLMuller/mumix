"""chord_tanahashi_belin.py  v01  The Tanahashi (2001) radius pdf seen through the chord kernel, against the radius pdf measured by Belin et al. (1996), Fig. 5.

The route of fit_chord.py: observed density p(R_m) = integral p_true(R) g(R_m / R) / R dR, g the chord kernel of one tube (chord_kernel.py: random impact
parameter and orientation, tilt limited to alpha_max, an event kept when its peak is at least a fraction f of the same tube's central-crossing peak).  The cut is
relative to each tube, so the swirl of the tube drops out and the radius pdf does not depend on the swirl pdf.  R is the standard deviation of the Gaussian vorticity profile (R^2 its variance; r_max = 1.585 R).  Everything is drawn in r_max units: Belin's R_m is multiplied by 1.585.
Three true pdfs:  (1) the first Tanahashi lognormal alone (the model tube), (2) both lognormals (the whole pdf), (3) the lognormal fitted to Belin (fit_chord.py).
(alpha_max, f) as fitted to Belin: (45 deg, 0.7), (0 deg, 0.4), (90 deg, 0.7).
Usage: python chord_tanahashi_belin.py      writes chord_tanahashi_belin.png and prints mean, median and mode of every curve.

Versions  M01 m01.v01 (2026-11-12): first version.
          m01.v02 (2026-11-12): drawn and tabulated in r_max units (Belin x 1.585).
"""
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chord_kernel as ck   # noqa: E402
import fit_chord as fc      # noqa: E402

RATIO = fc.RMAX_PER_R
RADIUS = (0.708, 5.231, 0.288, 11.27, 0.605)          # Tanahashi 2001: weight 1, median 1 (r_max / eta), s 1, median 2, s 2


def lognormal(R, median, s):
    return np.exp(-0.5 * ((np.log(R) - math.log(median)) / s) ** 2) / (R * s * math.sqrt(2 * math.pi))


def true_pdf(which):
    """Density of the Gaussian width R on fc.RGRID."""
    R = fc.RGRID
    w1, m1, s1, m2, s2 = RADIUS
    if which == "first":
        return lognormal(R, m1 / RATIO, s1)
    if which == "both":
        return w1 * lognormal(R, m1 / RATIO, s1) + (1 - w1) * lognormal(R, m2 / RATIO, s2)
    return lognormal(R, 4.19, 0.53)                      # fit_chord: alpha_max 45 deg, f 0.7


def observed(rm, p_true, alpha_max, f):
    gg, gv = ck.kernel(alpha_max, f)
    rho = rm[:, None] / fc.RGRID[None, :]
    g = np.interp(rho, gg, gv, left=0.0, right=0.0)
    return np.trapezoid(p_true[None, :] * g / fc.RGRID[None, :], fc.RGRID, axis=1)


def stats(x, p):
    p = p / np.trapezoid(p, x)
    cdf = np.cumsum(p) * (x[1] - x[0])
    return float(np.trapezoid(x * p, x)), float(np.interp(0.5, cdf / cdf[-1], x)), float(x[np.argmax(p)])


def main():
    rm, p_belin = fc.load()
    x = np.linspace(0.3, 30, 600)
    fig, ax = plt.subplots(1, 3, figsize=(16, 4.8), sharey=True)
    print("%-34s %-14s mean  median  mode   (all in r_max / eta = 1.585 R_m)" % ("true pdf", "alpha_max, f"))
    print("%-34s %-14s %5.2f %5.2f  %5.2f" % ("Belin Fig. 5 x 1.585 (R_m < 19)", "", *[RATIO * v for v in stats(rm, p_belin)]))
    for a, (alpha, f) in zip(ax, ((45, 0.7), (0, 0.4), (90, 0.7))):
        a.plot(RATIO * rm, p_belin / RATIO, "ko", ms=4, label="Belin et al. (1996) Fig. 5, R_m x 1.585")
        for which, colour, label in (("first", "tab:blue", "Tanahashi, first lognormal only"), ("both", "tab:red", "Tanahashi, both lognormals (our model)"), ("belin", "tab:green", "lognormal fitted to Belin")):
            pt = true_pdf(which)
            a.plot(RATIO * x, observed(x, pt, alpha, f) / RATIO, color=colour, lw=1.8, label="seen through the chord kernel: " + label)
            a.plot(RATIO * fc.RGRID, pt / RATIO, color=colour, lw=1, ls=":", label="true pdf (dotted)" if which == "first" else None)
            print("%-34s %-14s %5.2f %5.2f  %5.2f" % (label, "%d deg, %.1f" % (alpha, f), *[RATIO * v for v in stats(x, observed(x, pt, alpha, f))]))
        a.set_xlim(0, 40)
        a.set_xlabel("r_max / eta")
        a.set_title("tilt <= %d deg, relative cut f = %.1f" % (alpha, f), fontsize=10)
        a.legend(fontsize=7)
    ax[0].set_ylabel("pdf")
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "chord_tanahashi_belin.png"), dpi=110)


def scan():
    """A prediction, not a fit: the Tanahashi pdf (both lognormals, nothing adjusted) through the kernel of isotropic orientation (tilt up to 90 deg) for a range of the cut f."""
    rm, p_belin = fc.load()
    x = np.linspace(0.3, 30, 600)
    pt = true_pdf("both")
    fig, ax = plt.subplots(figsize=(7.5, 5))
    ax.plot(RATIO * rm, p_belin / RATIO, "ko", ms=4, label="Belin et al. (1996) Fig. 5, R_m x 1.585")
    ax.plot(RATIO * fc.RGRID, pt / RATIO, "k:", lw=1, label="true pdf (Tanahashi 2001, both lognormals)")
    print("prediction, tilt up to 90 deg:  f   mean  median  mode   (Belin %.2f %.2f %.2f)" % tuple(RATIO * v for v in stats(rm, p_belin)))
    for f, colour in zip((0.1, 0.3, 0.5, 0.7, 0.9), plt.cm.viridis(np.linspace(0, 0.9, 5))):
        obs = observed(x, pt, 90, f)
        ax.plot(RATIO * x, obs / RATIO, color=colour, lw=1.6, label="f = %.1f" % f)
        print("                              %.1f   %5.2f %5.2f  %5.2f" % (f, *[RATIO * v for v in stats(x, obs)]))
    ax.set_xlim(0, 40)
    ax.set_xlabel("r_max / eta")
    ax.set_ylabel("pdf")
    ax.set_title("the radius pdf the probe reads from the Tanahashi tubes (isotropic, cut f relative to each tube)", fontsize=9)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "chord_tanahashi_belin_scan.png"), dpi=110)


if __name__ == "__main__":
    scan()
    main()
