"""dns_pdfs_mu_sigma_all.py  v01  sigma against mu (= ln of the median) for EVERY row of the DNS pdf fits (dns_pdfs_fits.csv), whichever fit was chosen.
Plot     big filled circle: the single lognormal of the row (mu, sigma);  triangle: the component of the sum of two that holds at least half of the area (filled, the first, a1 >= 0.5; open, the second).  Colour: the source.  Three panels: the radius (eta), the swirl in u_K and in u'.
         The top axis gives the median m = exp(mu).  Rows of the same source (Ghira, seven Re_lambda) share a colour.
Output   dns_pdfs_mu_sigma_all.png.
Usage    python dns_pdfs_mu_sigma_all.py
Versions M01 m01.v03 (2026-11-15): one triangle a row, the component with at least half of the area (a1 >= 0.5: the first, filled; else the second, open); no lines.
         M01 m01.v02 (2026-11-15): the first component (filled triangle) and its line are left out where its weight a1 < 0.5.
         M01 m01.v01 (2026-11-15): first version (dns_pdfs_mu_sigma.py shows only the fit chosen for each row).
"""
import csv
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

import dns_pdfs_mu_sigma as ms

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    rows = list(csv.DictReader(open(os.path.join(HERE, "dns_pdfs_fits.csv"), encoding="utf-8")))
    panels = (("radius", "radius r_max / eta"), ("swirl / u_K", "swirl / u_K"), ("swirl / u'", "swirl / u'"))
    fig, ax = plt.subplots(1, 3, figsize=(17, 5.6))
    for a, (q, title) in zip(ax, panels):
        seen = set()
        for r in rows:
            if not r["quantity"].startswith(q):
                continue
            k = ms.key(r["source"])
            c = ms.COLOUR[k]
            mu, s = math.log(float(r["1 LN median"])), float(r["1 LN s"])
            a.plot([mu], [s], "o", color=c, ms=9, label=k if k not in seen else None)
            seen.add(k)
            mu1, s1, mu2, s2 = math.log(float(r["2 LN median1"])), float(r["2 LN s1"]), math.log(float(r["2 LN median2"])), float(r["2 LN s2"])
            a1 = float(r["2 LN a1"])
            if a1 >= 0.5:                                                                   # one triangle a row: the component that holds at least half of the area
                a.plot([mu1], [s1], "^", color=c, ms=7)
            else:
                a.plot([mu2], [s2], "^", mfc="none", mec=c, ms=7, mew=1.4)
        a.set_xlabel("mu = ln(median)")
        a.set_ylabel("sigma (width in ln x)")
        a.set_title(title, fontsize=10)
        a.set_ylim(0, 1.0)
        a.grid(alpha=0.25)
        a.secondary_xaxis("top", functions=(np.exp, np.log)).set_xlabel("median m = exp(mu)")
    key = [Line2D([], [], marker="o", color="0.3", ls="", ms=9, label="one lognormal fitted to the whole pdf (mu, sigma)"),
           Line2D([], [], marker="^", color="0.3", ls="", ms=7, label="two lognormals: the first, where it holds at least half (a1 >= 0.5)"),
           Line2D([], [], marker="^", mfc="none", mec="0.3", ls="", ms=7, mew=1.3, label="two lognormals: the second, where the first holds less than half (a1 < 0.5)")]
    h, _ = ax[0].get_legend_handles_labels()                                       # the nine sources (all of them are in the radius panel)
    fig.legend(handles=h + key, loc="lower center", ncol=4, fontsize=8)
    fig.suptitle("Lognormal parameters of every row: the one-lognormal fit (circle) and the dominant component of the two-lognormal fit (triangle)", fontsize=10.5)
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    fig.savefig(os.path.join(HERE, "dns_pdfs_mu_sigma_all.png"), dpi=90)


if __name__ == "__main__":
    main()
