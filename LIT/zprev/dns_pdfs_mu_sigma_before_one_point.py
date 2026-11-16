"""dns_pdfs_mu_sigma.py  v01  The width sigma against the position mu (= ln of the median) of the lognormal of every digitised DNS pdf, from dns_pdfs_params.csv (dns_pdfs_params.py of the selection: one lognormal unless two reduce the misfit by 30 %).
Plot     filled symbol: the first (narrow) lognormal, mu1 = ln m1, sigma1; open triangle: the second lognormal (mu2, sigma2) of the curves that have two, joined to the first by a thin line.  Three panels: the radius (eta), the swirl in u_K and in u'.  The top axis gives the median m = exp(mu).
Output   dns_pdfs_mu_sigma.png.
Usage    python dns_pdfs_mu_sigma.py
Versions M01 m01.v01 (2026-11-15): first version.
"""
import csv
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
COLOUR = {"Tanahashi 2001": "tab:blue", "Tanahashi 2004": "tab:orange", "Das 2006": "tab:green", "Pirozzoli 2012": "tab:red", "Wang 2007": "tab:purple", "Ghira 2022": "tab:brown", "Jimenez and Wray 1998": "tab:gray",
          "Aligolzadeh 2023, PIV": "tab:olive", "Aligolzadeh 2023, DNS": "tab:cyan"}


def key(label):
    for k in COLOUR:
        if label.startswith(k):
            return k
    return "Aligolzadeh 2023, DNS" if label.startswith("Aligolzadeh 2023, DNS") else None


def main():
    rows = list(csv.DictReader(open(os.path.join(HERE, "dns_pdfs_params.csv"), encoding="utf-8")))
    panels = (("radius", "radius r_max / eta"), ("swirl / u_K", "swirl / u_K"), ("swirl / u'", "swirl / u'"))
    fig, ax = plt.subplots(1, 3, figsize=(16, 5.2))
    for a, (q, title) in zip(ax, panels):
        seen = set()
        for r in rows:
            if not r["quantity"].startswith(q):
                continue
            k = key(r["source"])
            c = COLOUR[k]
            mu1, s1 = math.log(float(r["m1"])), float(r["sigma1"])
            a.plot([mu1], [s1], "o", color=c, ms=8, label=k if k not in seen else None)
            seen.add(k)
            if r["n"] == "2":
                mu2, s2 = math.log(float(r["m2"])), float(r["sigma2"])
                a.plot([mu1, mu2], [s1, s2], "-", color=c, lw=0.8)
                a.plot([mu2], [s2], "^", mfc="none", mec=c, ms=9, mew=1.6)
        a.set_xlabel("mu = ln(median)")
        a.set_ylabel("sigma (width in ln x)")
        a.set_title(title, fontsize=10)
        a.set_ylim(0, 1.0)
        a.grid(alpha=0.25)
        top = a.secondary_xaxis("top", functions=(np.exp, np.log))
        top.set_xlabel("median m = exp(mu)")
        a.legend(fontsize=7, loc="lower right")
    fig.suptitle("Lognormal parameters of the DNS pdfs: filled circle, the first (narrow) or only lognormal; open triangle, the second, joined by a line", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "dns_pdfs_mu_sigma.png"), dpi=90)


if __name__ == "__main__":
    main()
