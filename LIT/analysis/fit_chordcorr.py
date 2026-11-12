"""fit_chordcorr.py  v01  Overall fit with the hot-wire radii chord-corrected (r_max = reported / K) and the swirl as reported.

v02: corrections by source (see the list agreed with the user): Mouri and Hori (2009, the all-tube average) radius divided by K = 1.7 (chord
length: off-axis and tilted crossings) and swirl multiplied by KU = 3; every other source as reported: DNS (3D fields), Mouri 2004 and 2007
and 2003 (a high threshold favours head-on crossings, so no correction), Belin (the peak of the chord distribution, near the true radius) and
the 3D PIV (left as reported for now).  v01: all hot-wire radii divided by K, swirl as reported.  Radius and swirl are then independent data:
    r_max/eta = b Re_lambda**m              fitted to every row with a radius
    U_max/U_eta = c Re_lambda**s            fitted to every row with a swirl (Mouri and Hori 2009 not included, as before)
each source weighted equally (weights 1/n per source).  Derived: Re_c = r U, Gamma/nu = 8.784 Re_c, gamma/gamma_eta = 4x/r**2 and the
budget V_f = (1 - S/r**4) r**2/(E U**2), d/eta = r sqrt(pi/V_f).
Usage: python fit_chordcorr.py [K [KU]]      (writes chordcorr_fit.png; defaults K = 1.7, KU = 3)
"""
import html
import math
import os
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_data_sections as bds
import plot_groups as pg
import sourcedata as sd

K = float(sys.argv[1]) if len(sys.argv) > 1 else 1.7            # chord ratio for the all-tube hot-wire average (Mouri and Hori 2009)
KU = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0           # swirl factor for the same source
HOTWIRE = ("Mouri03", "Mouri04", "Mouri07", "Mouri09")
K_RADIUS = {"Mouri09": K}                                       # all other sources: no radius correction (DNS, PIV, intense hot-wire classes, Belin)
K_SWIRL = {"Mouri09": KU}
U_EXCLUDE = ()
X = sd.x
S = 48 * X * X
E = 0.977 * 4 * X


def rows():
    out = []
    for t in bds.tube_items():
        if isinstance(t["Re"], (int, float)) and t["beta"]:
            k = K_RADIUS.get(t["src"], 1.0)
            out.append(dict(src=t["src"], Re=t["Re"], r_rep=t["beta"], r=t["beta"] / k, U=t["U"] * K_SWIRL.get(t["src"], 1.0) if t["U"] else t["U"]))
    return out


def ranges():
    """Rows whose Re_lambda is a range (Belin, Mouri 2003, Sassa): (src, lo, hi, reported radius, radius used).  Belin's hot film has a
    resolution of at most 3 eta and 5.5 is the peak of the chord distribution, so it is used as reported; the Mouri 2003 wire gets K."""
    out = []
    for t in bds.tube_items():
        if isinstance(t["Re"], str) and "ndash" in t["Re"] and t["beta"]:
            lo, hi = [float(v) for v in t["Re"].replace("&ndash;", "-").split("-")]
            k = K_RADIUS.get(t["src"], 1.0)
            out.append((t["src"], lo, hi, t["beta"], t["beta"] / k))
    return out


def powerfit(pts):
    """pts: list of (src, Re, value); weighted LSQ of ln value on ln Re, every source total weight 1. Returns amplitude, exponent, errors, rms log residual."""
    cnt = defaultdict(int)
    for s, _, _ in pts:
        cnt[s] += 1
    x = np.array([math.log(p[1]) for p in pts])
    y = np.array([math.log(p[2]) for p in pts])
    w = np.array([1.0 / cnt[p[0]] for p in pts])
    w *= len(w) / w.sum()
    A = np.vstack([np.ones_like(x), x]).T
    cov0 = np.linalg.inv(A.T @ (w[:, None] * A))
    b = cov0 @ A.T @ (w * y)
    res = y - A @ b
    cov = cov0 * float(np.sum(w * res**2)) / (len(y) - 2)
    return math.exp(b[0]), b[1], np.sqrt(np.diag(cov)), math.sqrt(float(np.mean(res**2)))


def main():
    R = rows()
    rfit = powerfit([(t["src"], t["Re"], t["r"]) for t in R])
    ufit = powerfit([(t["src"], t["Re"], t["U"]) for t in R if t["U"] and t["src"] not in U_EXCLUDE])
    print("Mouri and Hori (2009): radius / %.2f, swirl x %.2f; all other sources as reported" % (K, KU))
    print("radius: r_max/eta = %.3f Re^%.4f  (se of ln b %.3f, m %.4f)  rms residual %.1f%%  (N = %d)" % (rfit[0], rfit[1], rfit[2][0], rfit[2][1], 100 * rfit[3], len([1 for t in R])))
    print("swirl : U_max/U_eta = %.3f Re^%.4f  (se of ln c %.3f, s %.4f)  rms residual %.1f%%  (N = %d)"
          % (ufit[0], ufit[1], ufit[2][0], ufit[2][1], 100 * ufit[3], len([1 for t in R if t["U"] and t["src"] not in U_EXCLUDE])))
    by = defaultdict(list)
    for t in R:
        by[t["src"]].append(t)
    print("mean deviation (data/curve - 1) by source: radius, swirl")
    for s, v in by.items():
        dr = np.mean([t["r"] / (rfit[0] * t["Re"] ** rfit[1]) - 1 for t in v])
        du = [t["U"] / (ufit[0] * t["Re"] ** ufit[1]) - 1 for t in v if t["U"]]
        print("  %-24s radius %+4.0f%% (reported radius %.2f -> %.2f)   swirl %s" % (pg.SHORT[s], 100 * dr, np.mean([t["r_rep"] for t in v]), np.mean([t["r"] for t in v]),
              "%+4.0f%%" % (100 * np.mean(du)) if du else "-"))

    def tube(Re):
        r = rfit[0] * Re ** rfit[1]
        U = ufit[0] * Re ** ufit[1]
        Vf = (1 - S / r**4) * r**2 / (E * U**2)
        return dict(r=r, U=U, Rec=r * U, G=sd.G * r * U, g=4 * X / r**2, Vf=100 * Vf, d=r * math.sqrt(math.pi / Vf) if Vf > 0 else float("nan"))
    for Re in (90, 332, 1000, 1934):
        m = tube(Re)
        print("  Re_l %4d  r_max %.2f  U_max %.2f  Re_c %.1f  Gamma/nu %.0f  gamma/gamma_eta %.3f  V_f %.1f%%  d/eta %.1f" % (Re, m["r"], m["U"], m["Rec"], m["G"], m["g"], m["Vf"], m["d"]))

    RANGES = ranges()
    srcs = [s["key"] for s in sd.SOURCES if any(t["src"] == s["key"] for t in R) or any(q[0] == s["key"] for q in RANGES)]
    mark = {}
    for g in "ABC":
        for i, s in enumerate([s for s in srcs if pg.GROUP[s] == g]):
            mark[s] = pg.MARKERS[i % len(pg.MARKERS)]
    res = [30 * (2200 / 30) ** (i / 80) for i in range(81)]
    fig, axes = plt.subplots(2, 3, figsize=(17, 9))
    panels = [("r", r"$r_{max}/\eta$: as used (solid); reported value where corrected (open)"), ("U", r"$U_{max}/U_\eta$ as reported"),
              ("Rec", r"$Re_c=r_{max}U_{max}/\nu$"), ("G", r"$\Gamma/\nu=8.78\,Re_c$"), ("Vf", r"$V_f$ (%, derived)"), ("d", r"$d/\eta$ (derived)")]
    for ax, (key, label) in zip(axes.ravel(), panels):
        ax.plot(res, [tube(Re)[key] for Re in res], c="k", lw=1.8)
        for t in R:
            col = pg.COLOUR[pg.GROUP[t["src"]]]
            if key == "r":
                ax.scatter(t["Re"], t["r"], marker=mark[t["src"]], s=34, c=col, alpha=0.85, edgecolors="none")
                if t["src"] in K_RADIUS:
                    ax.scatter(t["Re"], t["r_rep"], marker=mark[t["src"]], s=34, facecolors="none", edgecolors=col, alpha=0.6)
            elif key == "U" and t["U"]:
                ax.scatter(t["Re"], t["U"], marker=mark[t["src"]], s=34, c=col, alpha=0.85, edgecolors="none")
            elif key == "Rec" and t["U"]:
                ax.scatter(t["Re"], t["r"] * t["U"], marker=mark[t["src"]], s=34, c=col, alpha=0.85, edgecolors="none")
            elif key == "G" and t["U"]:
                ax.scatter(t["Re"], sd.G * t["r"] * t["U"], marker=mark[t["src"]], s=34, c=col, alpha=0.85, edgecolors="none")
        if key == "r":
            for src, lo, hi, rep_r, use_r in RANGES:
                col = pg.COLOUR[pg.GROUP[src]]
                ax.plot([lo, hi], [use_r, use_r], c=col, lw=2.5, alpha=0.85, solid_capstyle="butt")
                ax.scatter([math.sqrt(lo * hi)], [use_r], marker=mark[src], s=50, c=col, edgecolors="k", linewidths=0.8)
                if src in K_RADIUS:
                    ax.plot([lo, hi], [rep_r, rep_r], c=col, lw=1.2, ls=":", alpha=0.7)
        ax.set_xscale("log")
        if key in ("Rec", "G", "Vf"):
            ax.set_yscale("log")
        ax.set_xlabel(r"$Re_\lambda$")
        ax.set_title(label, fontsize=9)
        ax.grid(alpha=0.25, which="both")
    axes[1][1].axhspan(20, 35, color="0.8", alpha=0.5)
    axes[1][1].axhline(1.0, c="0.4", ls=":", lw=1)
    axes[1][1].set_ylim(0.3, 100)
    handles = [Line2D([], [], c="k", lw=1.8, label="fit: r=%.2f Re^%.3f, U=%.2f Re^%.3f" % (rfit[0], rfit[1], ufit[0], ufit[1]))]
    for g in "ABC":
        handles.append(Line2D([], [], ls="", label=pg.GNAME[g], marker="s", mfc=pg.COLOUR[g], mec=pg.COLOUR[g], ms=0))
        for s in [s for s in srcs if pg.GROUP[s] == g]:
            handles.append(Line2D([], [], marker=mark[s], ls="", mfc=pg.COLOUR[g], mec=pg.COLOUR[g], ms=7, label="   " + pg.SHORT[s]))
    fig.text(0.01, 0.01, "Horizontal bars in the radius panel: sources that give a range of Re_lambda (Belin 1996 as reported, Mouri 2003 as reported, Sassa and Makita).", fontsize=8)
    fig.suptitle("Fit with Mouri and Hori (2009) radius divided by %.1f and swirl multiplied by %.1f, all other sources as reported" % (K, KU))
    fig.tight_layout(rect=(0, 0, 0.75, 0.95))
    leg = fig.legend(handles=handles, loc="center left", bbox_to_anchor=(0.755, 0.5), fontsize=8.5, title="Methodology and reference", frameon=True)
    for txt in leg.get_texts():
        if txt.get_text() in pg.GNAME.values():
            txt.set_fontweight("bold")
    fig.savefig(os.path.join(HERE, "chordcorr_fit.png"), dpi=110)


if __name__ == "__main__":
    main()
