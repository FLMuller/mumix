"""belin_threshold_series.py  v01  How the threshold of the detection changes what a wire reads, with the wire-and-tube model fitted to Belin et al. as the surrogate: the events above a threshold of the velocity derivative, in units of its standard deviation
(Belin: 5 sigma, area 2.6e-3; Mouri et al.: 3.5 sigma = the top 1%, 6-6.7 sigma = the top 0.1%, read from their Fig. 2), against the true tubes of the same events.
Output  per Reynolds number and threshold: the radius as read (half the extrema spacing) over the true radius of the same events, and the swirl observed (the half swing dS/2), Belin's rule (dS / (2 x 0.14)) and the swirl with the actual alpha over the true swirl;
        belin_threshold_series.png (ratios against the threshold, one line a Re_lambda) and belin_threshold_series.json.
Limits  the wire is the one of Belin et al. (resolution 0.2-3 eta, no smoothing of the signal) and the cut acts on the peak velocity gradient, whereas Mouri et al. cut on velocity increments over a separation and smooth the signal;
        so the ratios are a surrogate for the other two estimates, not their correction.  Re_lambda above 700 is outside the range of the worms of Belin et al.
Usage:  python belin_threshold_series.py [--params 7.29 0.58 2.58 0.38] [--n 40000]

Versions  M01 m01.v01 (2026-11-13): first version.
"""
import argparse
import json
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

CUTS = (3.0, 3.5, 5.0, 6.7, 8.0)
RE_LIST = (105, 255, 659, 1000)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", type=float, nargs=4, default=[7.29, 0.58, 2.58, 0.38])
    ap.add_argument("--n", type=int, default=40000)
    args = ap.parse_args()
    cfg = sf.config(np.log(np.array(args.params)))
    out = []
    for Rl in RE_LIST:
        for cut in CUTS:
            cs.cbv.CUT = cut
            res = cs.run(Rl, cfg, args.n, 11)
            w, rd, k = res["w"], res["rd"], res["kept"]
            if rd.sum() < 200:
                continue
            sin_a = np.abs(res["sin_w"])
            q = lambda v, ww: cs.wquantile(v, ww, 0.5)                                    # noqa: E731
            row = dict(Re_lambda=Rl, cut_sigma=cut, share_selected=float(w[k].sum() / w.sum()), r_read=q(res["r_read"][rd], w[rd]), r_true=q(res["r"][rd], w[rd]), r_population=q(res["r"], np.ones_like(w)),
                       U_true=q(res["umax"][rd], w[rd]), U_observed=q(res["amp"][rd], w[rd]), U_belin=q(res["amp"][rd] / cs.SIN_BELIN, w[rd]), U_actual=q(res["amp"][rd] / sin_a[rd], w[rd]), U_population=q(res["umax"], np.ones_like(w)))
            out.append(row)
            print("Re_lambda %4d cut %.1f sigma: selected %.3f of the crossings; r read/true %.2f (true %.2f, population %.2f); U observed/true %.2f, Belin/true %.2f, actual alpha/true %.2f; true/population U %.2f" %
                  (Rl, cut, row["share_selected"], row["r_read"] / row["r_true"], row["r_true"], row["r_population"], row["U_observed"] / row["U_true"], row["U_belin"] / row["U_true"], row["U_actual"] / row["U_true"], row["U_true"] / row["U_population"]), flush=True)
    cs.cbv.CUT = 5.0
    with open(os.path.join(HERE, "belin_threshold_series.json"), "w") as f:
        json.dump(out, f, indent=1)
    fig, ax = plt.subplots(1, 3, figsize=(17, 5.2))
    for Rl in RE_LIST:
        rows = [r for r in out if r["Re_lambda"] == Rl]
        c = [r["cut_sigma"] for r in rows]
        ax[0].plot(c, [r["r_read"] / r["r_true"] for r in rows], "o-", label="Re_lambda %d" % Rl)
        ax[1].plot(c, [r["U_observed"] / r["U_true"] for r in rows], "o-", label="Re_lambda %d" % Rl)
        ax[2].plot(c, [r["U_true"] / r["U_population"] for r in rows], "o-", label="Re_lambda %d" % Rl)
    ax[0].set_ylabel("r_max read / true r_max of the same events")
    ax[1].set_ylabel("U_max observed (dS/2) / true U_max of the same events")
    ax[2].set_ylabel("true U_max of the selected events / U_max of all tubes")
    for a in ax:
        a.axvline(3.5, color="gray", ls=":")
        a.axvline(5.0, color="k", ls=":")
        a.axvline(6.7, color="gray", ls=":")
        a.set_xlabel("threshold of the velocity gradient (standard deviations; 3.5: top 1%, 5: Belin, 6.7: top 0.1%)")
        a.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_threshold_series.png"), dpi=90)


if __name__ == "__main__":
    main()
