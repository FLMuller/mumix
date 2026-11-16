"""dns_pdfs_mu_sigma.py  v01  The width sigma against the position mu (= ln of the median) of the lognormal of every digitised DNS pdf, from dns_pdfs_params.csv (dns_pdfs_params.py of the selection: one lognormal unless two reduce the misfit by 30 %).
Plot     one point per pdf, from the fit chosen by dns_pdfs_params (one lognormal unless two reduce the rms misfit to below 0.7 of it): circle, the single lognormal; filled triangle, the first lognormal of two when it holds at least half of the area (a1 >= 0.5); open triangle, the second when the first holds less.  Three panels: the radius (eta), the swirl in u_K and in u'.  The top axis gives the median m = exp(mu).
Output   dns_pdfs_mu_sigma.png.
Usage    python dns_pdfs_mu_sigma.py
Versions M01 m01.v02 (2026-11-15): ONE point per pdf: the lognormal chosen for it (one, or the dominant component of two); the earlier version drew both components of a chosen pair.
         M01 m01.v01 (2026-11-15): first version.
"""
import csv
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
COLOUR = {"Tanahashi 2001": "tab:blue", "Tanahashi 2004": "tab:orange", "Das 2006": "tab:green", "Pirozzoli 2012": "tab:red", "Wang 2007": "tab:purple", "Ghira 2022": "tab:brown", "Jimenez and Wray 1998": "tab:gray",
          "Aligolzadeh 2023, PIV": "tab:olive", "Aligolzadeh 2023, DNS": "tab:cyan"}


def key(label):
    for k in COLOUR:
        if label.startswith(k):
            return k
    return "Aligolzadeh 2023, DNS" if label.startswith("Aligolzadeh 2023, DNS") else None


def chosen_point(r):
    """The one point of a row: (mu, sigma, kind) of the fit that the selection chose (dns_pdfs_params.csv): the single lognormal (n = 1), or the dominant component of the two (the first where a1 >= 0.5, else the second)."""
    if r["n"] == "1":
        return math.log(float(r["m1"])), float(r["sigma1"]), "one"
    if float(r["a1"]) >= 0.5:
        return math.log(float(r["m1"])), float(r["sigma1"]), "first"
    return math.log(float(r["m2"])), float(r["sigma2"]), "second"


def main():
    rows = list(csv.DictReader(open(os.path.join(HERE, "dns_pdfs_params.csv"), encoding="utf-8")))
    panels = (("radius", "radius r_max / eta"), ("swirl / u_K", "swirl / u_K"), ("swirl / u'", "swirl / u'"))
    fig, ax = plt.subplots(1, 3, figsize=(16, 5.6))
    for a, (q, title) in zip(ax, panels):
        seen = set()
        for r in rows:
            if not r["quantity"].startswith(q):
                continue
            k = key(r["source"])
            c = COLOUR[k]
            mu, s, kind = chosen_point(r)
            lab = k if k not in seen else None
            seen.add(k)
            if kind == "one":
                a.plot([mu], [s], "o", color=c, ms=9, label=lab)
            elif kind == "first":
                a.plot([mu], [s], "^", color=c, ms=9, label=lab)
            else:
                a.plot([mu], [s], "^", mfc="none", mec=c, ms=9, mew=1.6, label=lab)
        a.set_xlabel("mu = ln(median)")
        a.set_ylabel("sigma (width in ln x)")
        a.set_title(title, fontsize=10)
        a.set_ylim(0, 1.0)
        a.grid(alpha=0.25)
        a.secondary_xaxis("top", functions=(np.exp, np.log)).set_xlabel("median m = exp(mu)")
    h, _ = ax[0].get_legend_handles_labels()
    kinds = [Line2D([], [], marker="o", color="0.3", ls="", ms=9, label="one lognormal chosen (a1 = 1)"),
             Line2D([], [], marker="^", color="0.3", ls="", ms=9, label="two chosen: the first, a1 >= 0.5"),
             Line2D([], [], marker="^", mfc="none", mec="0.3", ls="", ms=9, mew=1.6, label="two chosen: the second, a1 < 0.5")]
    fig.legend(handles=h + kinds, loc="lower center", ncol=4, fontsize=8)
    fig.suptitle("One point per pdf: mu and sigma of the lognormal chosen for it (the dominant one where two were chosen)", fontsize=11)
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    fig.savefig(os.path.join(HERE, "dns_pdfs_mu_sigma.png"), dpi=90)


if __name__ == "__main__":
    main()
