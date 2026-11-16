"""dns_pdfs_four.py  v01  The digitised pdfs of four DNS/PIV sets (Tanahashi et al. 2001, Wang et al. 2007, Aligolzadeh et al. 2023 experiment, Pirozzoli 2012) on linear axes: one plot for the radius r_max/eta (all four), one for the swirl in u_K (Tanahashi, Wang, Pirozzoli; Aligolzadeh has none).
Solid    the digitised pdf scaled to unit area (dns_pdfs_collate: radius_curves, swirl_curves).  Dashed: the first lognormal of its fit (dns_pdfs_params.csv), weighted by its share a1 of the area (a1 = 1 where one lognormal was chosen), the curve whose (mu, sigma) is plotted in Fig. D3.
Tanahashi 2001 swirl is in u_K with Re_lambda = 80 assumed (u'/u_K = 4.55).
Output   dns_pdfs_four_R.png, dns_pdfs_four_U.png.
Usage    python dns_pdfs_four.py
Versions M01 m01.v01 (2026-11-15): first version.
"""
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import dns_pdfs_collate as dc
import dns_pdfs_mu_sigma as ms
import fit_tanahashi_lognormal as fl

HERE = os.path.dirname(os.path.abspath(__file__))
FOUR = ("Tanahashi 2001", "Wang 2007", "Aligolzadeh 2023, PIV", "Pirozzoli 2012")


def first_lognormal(params, label, quantity):
    for r in params:
        if r["quantity"].startswith(quantity) and r["source"].startswith(label):
            return float(r["a1"]), float(r["m1"]), float(r["sigma1"])
    return None


def draw(curves, quantity, params, xlabel, xmax, title, name):
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for cv in curves:
        k = ms.key(cv["label"])
        if k not in FOUR:
            continue
        c = ms.COLOUR[k]
        ax.plot(cv["x"], cv["p"], color=c, lw=2, label=k)
        f = first_lognormal(params, k if not k.startswith("Aligolzadeh") else "Aligolzadeh 2023, PIV", quantity)
        if f:
            a1, m1, s1 = f
            xs = np.linspace(0.02, xmax, 800)
            ax.plot(xs, a1 * fl.lognormal(xs, np.log(m1), s1), color=c, lw=1.3, ls="--")
    ax.plot([], [], "k--", lw=1.3, label="first lognormal, weighted by its share a1 of the area")
    ax.set_xlim(0, xmax)
    ax.set_ylim(bottom=0)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("pdf, unit area")
    ax.set_title(title, fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, name), dpi=90)


def main():
    params = list(csv.DictReader(open(os.path.join(HERE, "dns_pdfs_params.csv"), encoding="utf-8")))
    rc = dc.radius_curves()
    uk, _ = dc.swirl_curves()
    draw(rc, "radius", params, "r_max / eta  (as the paper defines the radius)", 20, "Radius pdfs: Tanahashi 2001, Wang 2007, Aligolzadeh 2023 (PIV), Pirozzoli 2012", "dns_pdfs_four_R.png")
    draw(uk, "swirl / u_K", params, "maximum azimuthal velocity / u_K", 10, "Swirl pdfs in u_K: Tanahashi 2001 (Re_lambda 80 assumed), Wang 2007, Pirozzoli 2012", "dns_pdfs_four_U.png")


if __name__ == "__main__":
    main()
