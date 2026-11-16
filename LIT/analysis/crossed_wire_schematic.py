"""crossed_wire_schematic.py  v02  Sketch of the crossed (X) hot wire of Mouri et al. and Sassa and Makita passing a vortex tube, and why the difference of its two wire signals is the spanwise velocity v.
Left         top view in the plane of the mean flow (x) and the spanwise direction (y): a tube with its axis normal to the page (the simplest case, the path through its centre), its swirl, the crossed wire (two wires at +45 and -45 degrees to the flow, at right angles)
             placed where the tube's swirl is purely spanwise, and the tube carried along x past the fixed probe.  The wire is drawn larger than it is.
Right top    the spanwise velocity v along the path (Burgers vortex): the S-shaped trace the probe records as the tube goes by.
Right bottom the cooling of each wire (the velocity normal to it) and their sum and difference.
Usage        python crossed_wire_schematic.py     writes crossed_wire_schematic.png
Versions     M01 m01.v02 (2026-11-13): the tube and its trace added.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
XB, KB = 1.2564312, 0.71531                    # Burgers: peak of (1 - exp(-x a^2)) / a at a = 1 (r_max): the profile in units of r_max and of the peak velocity


def burgers(x):
    a = np.maximum(np.abs(x), 1e-9)
    return np.sign(x) * (1 - np.exp(-XB * a ** 2)) / (KB * a)


def main():
    fig = plt.figure(figsize=(14, 6.4))
    grid = fig.add_gridspec(2, 2, width_ratios=[1.25, 1], height_ratios=[1, 0.9])
    a = fig.add_subplot(grid[:, 0])
    a.set_aspect("equal")
    a.set_xlim(-2.6, 3.4)
    a.set_ylim(-2.3, 2.3)
    a.axis("off")
    a.add_patch(plt.Circle((0, 0), 1.0, fc="#fde9d9", ec="tab:orange", lw=2, ls="--"))
    a.add_patch(plt.Circle((0, 0), 0.25, fc="#fbd0a8", ec="none"))
    for th in np.deg2rad([40, 130, 220, 310]):                                     # swirl: counter-clockwise arrows around the axis
        for rr in (0.7,):
            p0 = rr * np.array([np.cos(th), np.sin(th)])
            tangent = np.array([-np.sin(th), np.cos(th)])
            a.annotate("", xy=p0 + 0.28 * tangent, xytext=p0 - 0.28 * tangent, arrowprops=dict(arrowstyle="-|>", color="tab:orange", lw=2))
    a.plot([0], [0], "o", color="tab:orange", ms=5)
    a.text(0, 1.12, "vortex tube: axis normal to the page,\nradius r_max (dashed), swirl v_theta", color="tab:orange", fontsize=9, ha="center")
    a.plot([-2.5, 3.2], [0, 0], ":", color="0.5")
    a.annotate("", xy=(-1.4, -0.55), xytext=(-2.4, -0.55), arrowprops=dict(arrowstyle="-|>", color="tab:blue", lw=2.5))
    a.text(-2.5, -0.85, "the mean flow carries the tube\npast the fixed probe", color="tab:blue", fontsize=9)
    a.annotate("", xy=(3.0, -2.05), xytext=(-2.4, -2.05), arrowprops=dict(arrowstyle="-|>", color="tab:blue", lw=2.5))
    a.text(-2.4, -2.25, "mean flow U (x)", color="tab:blue", fontsize=10)
    a.annotate("", xy=(-2.4, 2.1), xytext=(-2.4, 1.1), arrowprops=dict(arrowstyle="-|>", color="k", lw=1.5))
    a.text(-2.3, 1.65, "y", fontsize=10)
    px = 1.75                                                                       # the probe, outside the core on the +x side: the swirl there is purely spanwise
    a.plot([px - 0.45, px + 0.45], [-0.45, 0.45], color="k", lw=4, solid_capstyle="round")
    a.plot([px - 0.45, px + 0.45], [0.45, -0.45], color="k", lw=4, solid_capstyle="round")
    a.text(px + 0.5, 0.5, "wire 1 (+45 deg)", fontsize=9, va="bottom")
    a.text(px + 0.5, -0.5, "wire 2 (-45 deg)", fontsize=9, va="top")
    a.annotate("", xy=(px, 1.45), xytext=(px, 0.05), arrowprops=dict(arrowstyle="-|>", color="tab:purple", lw=2.5))
    a.text(px + 0.1, 1.2, "v: spanwise\nvelocity of the swirl", color="tab:purple", fontsize=9)
    a.text(px, -1.0, "crossed wire\n(fixed in the lab)", fontsize=9, ha="center", va="top")
    a.set_title("crossed wire and tube, seen from above (path through the centre)", fontsize=10)
    t = fig.add_subplot(grid[0, 1])
    x = np.linspace(-4, 4, 400)
    t.plot(x, burgers(x), color="tab:purple", lw=2)
    t.axhline(0, color="0.6", lw=0.8)
    t.axvline(1, color="0.7", ls=":")
    t.axvline(-1, color="0.7", ls=":")
    t.plot([1.75], [burgers(1.75)], "ko", ms=6)
    t.text(1.85, burgers(1.75) + 0.12, "probe position of the sketch", fontsize=8)
    t.set_xlabel("distance along the path / r_max")
    t.set_ylabel("v / peak velocity")
    t.set_title("the trace the probe records as the tube passes: antisymmetric, peaks at +/- r_max", fontsize=9)
    b = fig.add_subplot(grid[1, 1])
    b.axis("off")
    b.set_xlim(0, 1)
    b.set_ylim(0, 1)
    lines = [(0.90, "each wire is cooled by the velocity normal to it (flow along the wire neglected)", 9, "k"),
             (0.70, r"wire 1:   $E_1 = (U + u - v)/\sqrt{2}$", 12, "tab:red"),
             (0.52, r"wire 2:   $E_2 = (U + u + v)/\sqrt{2}$", 12, "tab:green"),
             (0.30, r"sum  $E_1 + E_2 = \sqrt{2}\,(U + u)$:  streamwise velocity", 12, "k"),
             (0.12, r"difference  $E_2 - E_1 = \sqrt{2}\,v$:  spanwise velocity (the tube's swirl)", 12, "tab:purple")]
    for y, text, fs, colour in lines:
        b.text(0.0, y, text, fontsize=fs, color=colour)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "crossed_wire_schematic.png"), dpi=100)


if __name__ == "__main__":
    main()
