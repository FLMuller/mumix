"""belin_mouri_dists.py  v01  The distributions of r_max and U_max/U_eta of the tubes of the Belin fit (ground truth): as generated, as they hit the probe, and as the sensors of Belin and of Mouri measure them.
Curves   real: the generated population (area 1); hit the probe: the same weighted by the footprint of each tube (the flux through the probe line, importance sampling of chord_belin_sens.py);
         Belin's wire: the events that pass his gradient cut and can be read, r = half the spacing of the extrema, U = dS / (2 x 0.14) (his rule), also dS / (2 sin alpha) with the actual alpha of each event, dS / (2 sin alpha*) with the one constant sin alpha* that best matches the real distribution (belin_sin_alpha_equiv.py), and the raw dS / 2; Mouri's crossed wire: the events of the 1% (3.6 sigma) and 0.1% (6.4 sigma) classes, r and U read on each event (belin_range_numbers.py).
Rows     Re_lambda 255 and 659.  Linear axes, every curve has area 1 over the range shown (what falls beyond is omitted).
Usage    python belin_mouri_dists.py [--n 40000]    writes belin_mouri_dists.png
Versions M01 m01.v04 (2026-11-13): U panel also shows dS/(2 sin alpha) with the actual alpha, with the constant sin alpha* that best matches the real distribution, and the raw dS/2.
"""
import argparse
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chord_belin_sens as cs         # noqa: E402
import chord_belin_sens_fit as sf     # noqa: E402
import belin_range_numbers as rn      # noqa: E402
import belin_sin_alpha_equiv as sae   # noqa: E402


def dens(v, w, edges):
    h = np.histogram(v, edges, weights=w)[0].astype(float)
    return h / (h.sum() * (edges[1] - edges[0]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40000)
    ap.add_argument("--params", type=float, nargs=4, default=[7.29, 0.58, 2.58, 0.38])
    args = ap.parse_args()
    cfg = sf.config(np.log(np.array(args.params)))
    fig, ax = plt.subplots(2, 2, figsize=(13, 9))
    for row, Rl in enumerate((255, 659)):
        res = cs.run(Rl, cfg, args.n, 11)
        ev = rn.mouri_events(Rl, cfg, args.n)
        w, rd = res["w"], res["rd"]
        one = np.ones_like(w)
        for col, (label, top, nb) in enumerate((("r_max / eta", 30.0, 60), ("U_max / U_eta", 120.0, 60))):
            edges = np.linspace(0, top, nb + 1)
            mid = 0.5 * (edges[1:] + edges[:-1])
            a = ax[row, col]
            if col == 0:
                true, belin, mouri = res["r"], res["r_read"][rd], ev["r_obs"]
            else:
                true, belin, mouri = res["umax"], res["amp"][rd] / cs.SIN_BELIN, ev["u_obs"]
            a.plot(mid, dens(true, one, edges), color="k", lw=2.4, label="real distribution (generated tubes)")
            a.plot(mid, dens(true, w, edges), color="tab:gray", lw=2.0, ls="--", label="hit the probe (weighted by footprint)")
            a.plot(mid, dens(belin, w[rd], edges), color="tab:red", lw=2.2, label="Belin's wire: events read, his rule (constant sin alpha = 0.14)")
            if col == 1:
                a.plot(mid, dens(res["amp"][rd] / np.abs(res["sin_w"][rd]), w[rd], edges), color="tab:orange", lw=2.2, label="Belin's wire: dS / (2 sin alpha), the actual alpha of each event")
                sstar = sae.best(res["amp"][rd], w[rd], res["umax"], one, np.linspace(0, 120, 241))
                a.plot(mid, dens(res["amp"][rd] / sstar, w[rd], edges), color="tab:purple", lw=2.2, ls="-.", label="Belin's wire: dS / (2 x %.2f), the constant sin alpha that best matches the real distribution" % sstar)
                a.plot(mid, dens(res["amp"][rd], w[rd], edges), color="tab:brown", lw=1.5, ls=":", label="Belin's wire: dS / 2, as the wire sees it (no conversion)")
            c1, c01 = ev["peak"] >= rn.K1, ev["peak"] >= rn.K01
            a.plot(mid, dens(mouri[c1], ev["w"][c1], edges), color="tab:blue", lw=2.0, label="Mouri's crossed wire: 1% class, per event")
            a.plot(mid, dens(mouri[c01], ev["w"][c01], edges), color="tab:green", lw=2.0, label="Mouri's crossed wire: 0.1% class, per event")
            a.set_xlim(0, top)
            a.set_xlabel(label)
            a.set_ylabel("pdf (area 1)")
            a.set_title("Re_lambda %d: %s" % (Rl, label), fontsize=10)
            a.legend(fontsize=7)
    fig.suptitle("Tubes of the Belin fit (ground truth): as generated, as they hit the probe, and as the two sensors measure them", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_mouri_dists.png"), dpi=90)


if __name__ == "__main__":
    main()
