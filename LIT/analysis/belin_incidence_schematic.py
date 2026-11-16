"""belin_incidence_schematic.py  v02  Schematic of the incidence angle alpha of Belin et al. (1996, Fig. 3, eqs. 2-8) in the frame of the wire: the wire is fixed, the mean flow and the tube move past it.
Panel A  lab frame, plane (x, y) of the wire: the wire is the black bar along y; the mean flow U is along x (normal to the wire = the direction the wire senses); the tube (axis out of the page) is carried by the
         instantaneous flow W = U + w, w a large-scale fluctuation along the wire; alpha = the angle between W (the direction the tube travels) and x (the mean flow = the wire normal).
Panel B  the sensed signal at the wire, S(t) = v_x(wire) for a tube whose centre passes through the wire (b = 0): antisymmetric, amplitude sin(alpha) U_max, extrema 3.17 R apart.
Panel C  the velocity triangle: mean flow U, fluctuation w along the wire, resultant W, angle alpha; the size of sin(alpha) in Belin's analysis and in the model.
Usage: python belin_incidence_schematic.py     writes belin_incidence_schematic.png
Versions  M01 m01.v01 (2026-11-13): first version (wire moving through a tube at rest).
          m01.v02 (2026-11-13): the wire is fixed; the mean flow and the tube travel past it; alpha is defined as the angle between the tube's velocity W and the mean flow direction x (the wire normal).
"""
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RMAX = 1.585                                                       # r_max / R


def vtheta(r):
    """Burgers swirl velocity / (omega0 R) at r / R."""
    return (1 - np.exp(-r ** 2 / 2)) / r


def tube(a, centre, alpha=0.35, dashed=False):
    a.add_patch(plt.Circle(centre, RMAX, fill=True, color="tab:red", alpha=alpha * 0.6, lw=0))
    a.add_patch(plt.Circle(centre, RMAX, fill=False, color="tab:red", lw=1.4, ls="--" if dashed else "-", alpha=min(1.0, alpha * 2.2)))
    a.plot(*centre, "o", color="tab:red", ms=4, alpha=min(1.0, alpha * 2.5))
    for ang in np.linspace(0, 2 * math.pi, 7)[:-1] + 0.4:                       # the swirl, counter-clockwise
        p = np.array(centre) + RMAX * np.array([math.cos(ang), math.sin(ang)])
        t = np.array([-math.sin(ang), math.cos(ang)]) * 0.8
        a.annotate("", xy=p + t, xytext=p, arrowprops=dict(arrowstyle="->", color="tab:red", alpha=min(1.0, alpha * 2.0), lw=1.1))


def main():
    fig, ax = plt.subplots(1, 3, figsize=(19, 6.6), gridspec_kw=dict(width_ratios=[1.45, 0.95, 0.85]))
    a = ax[0]
    al = math.radians(22)                                          # exaggerated; Belin's estimate is 8 degrees
    e = np.array([math.cos(al), math.sin(al)])
    for y in (-4.6, 4.6):                                          # the mean flow: blue arrows along x
        for x in np.linspace(-9, 6, 4):
            a.annotate("", xy=(x + 2.2, y), xytext=(x, y), arrowprops=dict(arrowstyle="-|>", color="tab:blue", lw=2.5))
    a.text(-9.4, 5.25, "mean flow U: along x, normal to the wire, the direction the wire senses", color="tab:blue", fontsize=10, va="bottom")
    a.plot([0, 0], [-0.9, 0.9], color="k", lw=7, solid_capstyle="butt", zorder=5)
    a.text(1.0, -1.0, "wire (fixed),\nalong y", fontsize=10, va="top")
    tube(a, (-7.0 * e[0], -7.0 * e[1]), alpha=0.35)
    tube(a, (0.0, 0.0), alpha=0.18, dashed=True)
    tube(a, (7.0 * e[0], 7.0 * e[1]), alpha=0.35)
    start = -7.0 * e
    a.plot([start[0] - 1.4 * e[0], 9.4 * e[0]], [start[1] - 1.4 * e[1], 9.4 * e[1]], "k:", lw=1)
    a.annotate("", xy=start + 4.6 * e + 0.0 * e, xytext=start + 1.9 * e, arrowprops=dict(arrowstyle="-|>", color="k", lw=3.2))
    a.text(-9.3, 1.9, "tube velocity W\n(carried by the flow U + w)", fontsize=10, ha="left", va="center")
    a.plot([start[0], start[0] + 6.0], [start[1], start[1]], color="tab:blue", lw=1.4, ls=":")
    th = np.linspace(0, al, 30)
    a.plot(start[0] + 4.0 * np.cos(th), start[1] + 4.0 * np.sin(th), color="k", lw=1.5)
    a.text(start[0] + 4.3, start[1] + 0.7, "alpha", fontsize=14)
    a.text(start[0], start[1] - 2.0, "t < 0", fontsize=10, color="tab:red", ha="center", va="top")
    a.text(0.0, 2.1, "t = 0 (b = 0)", fontsize=10, color="tab:red", ha="center")
    a.text(7.0 * e[0], 7.0 * e[1] - 2.3, "t > 0", fontsize=10, color="tab:red", ha="center")
    a.text(-9.4, -5.6, "the sensed part at the wire is the x component of the swirl v:\n  tube upstream (t < 0): v at the wire points (-sin a, cos a), x part < 0\n  tube downstream (t > 0): v points (sin a, -cos a), x part > 0   ->  S-shape of amplitude sin(alpha) U_max", fontsize=9, va="top")
    a.set_xlim(-9.6, 10.4)
    a.set_ylim(-8.0, 6.0)
    a.set_aspect("equal")
    a.axis("off")
    a.set_title("A  lab frame, plane (x, y): wire fixed; the tube (axis out of the page) travels past it\nalpha is drawn at 22 deg; Belin's estimate is 8 deg", fontsize=10)
    a = ax[1]
    xi = np.linspace(-7, 7, 800)
    for sin_a, colour in ((0.0, "gray"), (0.14, "tab:blue"), (0.3, "tab:green"), (0.6, "tab:red")):
        r = np.maximum(np.abs(xi), 1e-6)
        S = np.sign(xi) * vtheta(r) * sin_a / vtheta(RMAX)
        a.plot(xi, S, color=colour, lw=2.2, label="sin alpha = %.2f" % sin_a)
    a.axhline(0, color="k", lw=0.6)
    a.annotate("", xy=(-RMAX, -0.66), xytext=(RMAX, -0.66), arrowprops=dict(arrowstyle="<->", color="k"))
    a.text(0, -0.76, "3.17 R apart", ha="center", fontsize=9)
    a.annotate("", xy=(-RMAX - 0.4, 0.3), xytext=(-RMAX - 0.4, -0.3), arrowprops=dict(arrowstyle="<->", color="tab:green"))
    a.text(-6.8, 0.5, "peak to peak (green curve)\ndS = 2 sin(alpha) U_max", color="tab:green", fontsize=9, va="center", ha="left")
    a.set_xlabel("distance of the tube centre from the wire along its path  (= W t / R)")
    a.set_ylabel("signal of the fixed wire S / U_max")
    a.set_title("B  what the wire reads (b = 0): S = v_x at the wire", fontsize=10)
    a.legend(fontsize=9, loc="lower right")
    a.set_ylim(-0.85, 0.85)
    a.set_xlim(-7, 7)
    a = ax[2]
    a.annotate("", xy=(3.0, 0), xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", color="tab:blue", lw=3))
    a.annotate("", xy=(3.0, 1.0), xytext=(3.0, 0), arrowprops=dict(arrowstyle="-|>", color="tab:orange", lw=3))
    a.annotate("", xy=(3.0, 1.0), xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", color="k", lw=3))
    a.text(1.5, -0.25, "mean flow U along x\n(the wire normal: cools it fully)", color="tab:blue", ha="center", fontsize=9, va="top")
    a.text(3.15, 0.5, "w: large-scale\nfluctuation along\nthe wire (cools little)", color="tab:orange", fontsize=9, va="center")
    a.text(1.25, 0.6, "W = U + w: the velocity of the tube", fontsize=9, ha="center", va="bottom", rotation=18)
    th = np.linspace(0, math.atan(1.0 / 3.0), 30)
    a.plot(1.1 * np.cos(th), 1.1 * np.sin(th), color="k")
    a.text(1.25, 0.1, "alpha", fontsize=11)
    a.text(-0.3, -1.3, "alpha = the angle between the tube's velocity W\nand the wire-normal direction x (= the mean flow)\n\ntan(alpha) = w / U,  rms(w) = u'\n\nsin(alpha) is random with sigma ~ u'/U\n(Re_lambda 659: u' 26, U 90 cm/s: 0.29)\n\nBelin: estimates 8 deg from the signal and\nreads U_max = dS / (2 sin alpha)\nwith the constant sin alpha = 0.14", fontsize=9, va="top")
    a.set_xlim(-0.4, 5.9)
    a.set_ylim(-6.5, 1.8)
    a.set_aspect("equal")
    a.axis("off")
    a.set_title("C  the velocity triangle (lab frame)", fontsize=10)
    fig.suptitle("The incidence angle alpha: no angle, no S-shaped signal; a small angle gives amplitude sin(alpha) U_max", fontsize=12)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_incidence_schematic.png"), dpi=100)


if __name__ == "__main__":
    main()
