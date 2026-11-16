"""dns_pdfs_vs_re.py  v01  mu and sigma of the lognormal chosen for each DNS pdf (one point per pdf, dns_pdfs_mu_sigma.chosen_point) against Re_lambda.
Re_lambda Ghira et al. 2022: 90 ... 399 (their Table); Tanahashi et al. 2001: 80 (read from their Fig. 1b, assumed); Wang et al. 2007: 115 (read from their Fig. 1a, the flat end of the curve); Pirozzoli 2012: 251.4, the case E of his Table 1 (the open circles of his Fig. 2 are case E; the caption says case D, 98.6);
         Aligolzadeh et al. 2023: 179 (the von Karman experiment) and 418 (the DNS of the Johns Hopkins database); Jimenez and Wray 1998: the curves of the runs at Re_lambda 37, 62, 95, 168 are pooled (the paper says they collapse): a bar from 37 to 168 with the marker at the geometric mean.
         Not placed: Tanahashi et al. 2004 (channel, Re_tau 800) and Das et al. 2006 (channel, Re_tau 180): no isotropic Re_lambda.
Colour    marker face: V_f, the fraction of the volume of the flow occupied by the vortices that the method keeps (a threshold on the vorticity screens out a subset; see vortex_volume_fraction), log scale 1e-4 to 2e-2; white where the paper states none; edge: the source.
Plot     columns: radius (eta), swirl in u_K, swirl in u'; top row the median m = exp(mu) (in eta, u_K or u'), bottom row sigma; markers as dns_pdfs_mu_sigma (circle: one lognormal; filled triangle: the first of two, a1 >= 0.5; open triangle: the second).  The dashed line: the median of the Ghira et al. radius, 5.78 Re^-0.073.
Output   dns_pdfs_vs_re.png, and the slopes of mu and sigma on ln Re_lambda printed.
Usage    python dns_pdfs_vs_re.py
Versions M01 m01.v05 (2026-11-15): the face colour is V_f, the volume fraction of the flow occupied by the vortices kept by the method (stated by Ghira, Aligolzadeh, Jimenez and Wray), in place of the share of the tube volume of the chosen lognormal.
         M01 m01.v04 (2026-11-15): the face of every marker is coloured by the share of the tube volume that the chosen lognormal covers (the edge keeps the source colour).
         M01 m01.v03 (2026-11-15): the median m = exp(mu) in the top row in place of mu.
         M01 m01.v02 (2026-11-15): linear Re_lambda axis (0-450).
         M01 m01.v01 (2026-11-15): first version (logarithmic Re_lambda axis).
"""
import csv
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm
from matplotlib.lines import Line2D

import dns_pdfs_mu_sigma as ms

HERE = os.path.dirname(os.path.abspath(__file__))
CMAP = plt.get_cmap("viridis")
NORM = LogNorm(1e-4, 2e-2)
RE_OF = {"Tanahashi 2001": (80.0, 80.0), "Wang 2007": (115.0, 115.0), "Pirozzoli 2012": (251.4, 251.4), "Aligolzadeh 2023, PIV": (179.0, 179.0), "Aligolzadeh 2023, DNS": (418.0, 418.0), "Jimenez and Wray 1998": (37.0, 168.0)}


def re_range(source):
    if source.startswith("Ghira 2022"):
        v = float(source.split("lambda")[-1])
        return v, v
    for k, v in RE_OF.items():
        if source.startswith(k):
            return v
    return None


def vortex_volume_fraction(source, re_geo):
    """V_f: the fraction of the volume of the flow that the vortices kept by the method occupy, as the paper states it; None where the paper gives none (an eduction without a vorticity threshold).
    Ghira et al. 2022: 1 % of the volume with the highest vorticity (by construction); Aligolzadeh et al. 2023: 1.4 % of the measured volume (the experiment; none is stated for the DNS);
    Jimenez and Wray 1998: V = 4.16 Re_lambda^-2 (their Fig. 8b, the volume with omega > 0.5 omega_f), taken at the geometric mean of Re_lambda 37 and 168."""
    if source.startswith("Ghira 2022"):
        return 0.01
    if source.startswith("Aligolzadeh 2023, PIV"):
        return 0.014
    if source.startswith("Jimenez and Wray"):
        return 4.16 / re_geo ** 2
    return None


def main():
    rows = list(csv.DictReader(open(os.path.join(HERE, "dns_pdfs_params.csv"), encoding="utf-8")))
    panels = (("radius", "radius r_max / eta"), ("swirl / u_K", "swirl / u_K"), ("swirl / u'", "swirl / u'"))
    fig, ax = plt.subplots(2, 3, figsize=(16, 9))
    pts = {q: [] for q, _ in panels}
    shares = []
    placed = set()
    for col, (q, title) in enumerate(panels):
        seen = set()
        for r in rows:
            if not r["quantity"].startswith(q):
                continue
            rr = re_range(r["source"])
            if rr is None:
                continue
            k = ms.key(r["source"])
            c = ms.COLOUR[k]
            mu, s, kind = ms.chosen_point(r)
            x = math.sqrt(rr[0] * rr[1])
            pts[q].append((x, mu, s, k))
            vf = vortex_volume_fraction(r["source"], x)
            placed.add(k)
            shares.append((r["source"], r["quantity"], vf))
            face = "white" if vf is None else CMAP(NORM(vf))
            for row, y in ((0, math.exp(mu)), (1, s)):
                a = ax[row, col]
                if rr[0] != rr[1]:
                    a.plot([rr[0], rr[1]], [y, y], "-", color=c, lw=2, alpha=0.6)
                a.plot([x], [y], "o" if kind == "one" else "^", ms=11, mfc=face, mec=c, mew=2.2, zorder=3)
            seen.add(k)
        for row, lab in ((0, "median m = exp(mu)"), (1, "sigma (width in ln x)")):
            a = ax[row, col]
            a.set_xlim(0, 450)
            a.set_xlabel("Re_lambda")
            a.set_ylabel(lab)
            a.grid(alpha=0.25, which="both")
            if row == 1:
                a.set_ylim(0, 1.0)
        ax[0, col].set_title(title, fontsize=10)
    re = np.linspace(37.0, 450.0, 100)
    ax[0, 0].plot(re, 5.78 * re ** -0.073, "k--", lw=1, label="Ghira et al. median 5.78 Re^-0.073")
    srcs = [Line2D([], [], marker="s", mfc="white", mec=c, mew=2.2, ls="", ms=9, label=k) for k, c in ms.COLOUR.items() if k in placed]
    kinds = [Line2D([], [], marker="o", mfc="0.85", mec="0.3", mew=1.5, ls="", ms=10, label="one lognormal chosen"), Line2D([], [], marker="^", mfc="0.85", mec="0.3", mew=1.5, ls="", ms=10, label="two chosen: the first (a1 >= 0.5) or the second (a1 < 0.5)"),
             Line2D([], [], color="0.4", lw=2, alpha=0.6, label="pooled over a range of Re_lambda"), Line2D([], [], color="k", ls="--", lw=1, label="Ghira et al. median 5.78 Re^-0.073"), Line2D([], [], marker="o", mfc="white", mec="0.3", mew=1.5, ls="", ms=10, label="V_f not stated (no vorticity threshold)")]
    fig.legend(handles=srcs + kinds, loc="lower center", ncol=4, fontsize=8)
    sm = plt.cm.ScalarMappable(cmap=CMAP, norm=NORM)
    cax = fig.add_axes([0.945, 0.25, 0.012, 0.6])
    cb = fig.colorbar(sm, cax=cax)
    cb.set_label("V_f: fraction of the flow volume occupied by the vortices kept by the method")
    fig.suptitle("median and sigma of the lognormal chosen for each DNS pdf against Re_lambda (Tanahashi 2004 and Das, channels, have no Re_lambda)", fontsize=11)
    fig.subplots_adjust(left=0.05, right=0.92, bottom=0.2, top=0.92, wspace=0.28, hspace=0.3)
    fig.savefig(os.path.join(HERE, "dns_pdfs_vs_re.png"), dpi=90)
    for src, q, v in shares:
        print("  V_f %-48s %-12s %s" % (src, q, "not stated" if v is None else "%.2e" % v))
    for q in pts:
        for name, sel in (("all", lambda k: True), ("without Ghira", lambda k: k != "Ghira 2022")):
            p = [t for t in pts[q] if sel(t[3])]
            if len(p) >= 3:
                x = np.log([t[0] for t in p])
                mu, s = np.array([t[1] for t in p]), np.array([t[2] for t in p])
                bm, am = np.polyfit(x, mu, 1)
                bs, as_ = np.polyfit(x, s, 1)
                print("%-12s %-14s n=%2d  mu = %.2f %+.3f ln Re (r %+.2f)   sigma = %.2f %+.3f ln Re (r %+.2f)" % (q, name, len(p), am, bm, np.corrcoef(x, mu)[0, 1], as_, bs, np.corrcoef(x, s)[0, 1]))
            else:
                print("%-12s %-14s n=%2d  too few" % (q, name, len(p)))


if __name__ == "__main__":
    main()
