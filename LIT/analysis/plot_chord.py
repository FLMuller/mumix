"""plot_chord.py  v01  Probability density of the radius read by a point probe from many identical Burgers tubes.

Uses chord_model.py: identical tubes (true r_max/eta = 5, Gaussian width R = 5/1.585 = 3.15 eta) cross a point probe at random impact
parameter and orientation (tilt limited to alpha_max, isotropic otherwise); an event is kept when its signal peak is at least f times
the peak of a central crossing; the radius read is R_m = (spacing of the two extrema)/3.17 (Belin's rule).  One panel per tilt limit,
one curve per amplitude cut f, density of R_m in units of eta.  The points are Belin's measured distribution (Fig. 5, read by eye).
Usage: python plot_chord.py      (writes chord_pdf.png next to this file)
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
import chord_model as cm

R_TRUE = 5.0 / cm.RMAX                    # Gaussian width of the true tube in eta (3.15)
BELIN_R = [1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10, 10.5, 11, 11.5, 12, 12.5, 13, 13.5, 14, 14.5, 15, 16, 17, 18, 19, 20]
BELIN_P = [.005, .03, .08, .13, .17, .19, .175, .16, .15, .14, .12, .105, .09, .08, .07, .062, .055, .05, .045, .04, .036, .032, .028, .024, .02, .017, .014, .011, .009, .006, .004, .002, .001, .0005]


def main():
    cuts = (0.8, 0.5, 0.3, 0.2)
    tilts = (0, 45, 90)
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.5), sharey=True)
    bins = np.linspace(0, 24, 97)
    centres = 0.5 * (bins[:-1] + bins[1:])
    for ax, tilt in zip(axes, tilts):
        for f, col in zip(cuts, ("#1b4f72", "#2e86c1", "#e67e22", "#c0392b")):
            ratio = cm.events(6000, math.radians(tilt), f, False)
            h, _ = np.histogram(ratio * R_TRUE, bins=bins, density=True)
            m, md, mo = cm.summarise(ratio)
            ax.plot(centres, h, c=col, lw=1.6, label="f=%.1f: mean %.1f, median %.1f, mode %.1f" % (f, m * R_TRUE, md * R_TRUE, mo * R_TRUE))
        ax.plot(BELIN_R, BELIN_P, "k.", ms=6, label="Belin (1996), measured")
        ax.axvline(R_TRUE, c="0.5", ls=":", lw=1)
        ax.set_xlim(0, 20)
        ax.set_xlabel(r"radius read by the probe $R_m/\eta$")
        ax.set_title("tilt limit %d deg%s" % (tilt, " (axis normal to the path)" if tilt == 0 else " (isotropic)" if tilt == 90 else ""), fontsize=10)
        ax.legend(fontsize=7)
        ax.grid(alpha=0.25)
    axes[0].set_ylabel(r"probability density $p(R_m/\eta)$")
    fig.suptitle("Identical tubes (true R = %.2f eta, dotted) read by a point probe: distribution of the chord radius, by tilt limit and amplitude cut f" % R_TRUE)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(os.path.join(HERE, "chord_pdf.png"), dpi=110)


if __name__ == "__main__":
    main()
