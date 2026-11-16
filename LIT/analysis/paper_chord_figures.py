"""paper_chord_figures.py  v01  The comparison figure of the paper's section on the wire-and-tube model: the tubes behind Belin's records, as found by the model fitted to Figs. 5 and 6 (belin_results.py), against the distributions of the DNS.
Panels  (a) r_max / eta: the tubes generated for Re_lambda 659 (population) and the intense tubes (selected and read), against the two-lognormal pdf of Tanahashi et al. (2001) (chord_population.RADIUS);
        (b) U_max / u': the same tubes, with u'/U_eta = (Re_lambda / sqrt 15)^(1/2), against the swirl pdf of Tanahashi et al. (2001) (chord_population.SWIRL, in units of u'_rms).
Output  paper_chord_compare.png and paper_chord_numbers.json (medians and means that the text quotes).
Usage:  python paper_chord_figures.py [--params 7.29 0.58 2.58 0.38]

Versions  M01 m01.v01 (2026-11-13): first version.
"""
import argparse
import json
import math
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
import chord_population as cp         # noqa: E402


def lognormal_pdf(x, median, sigma):
    return np.exp(-0.5 * (np.log(x / median) / sigma) ** 2) / (x * sigma * math.sqrt(2 * math.pi))


def mixture(x, p):
    w, m1, s1, m2, s2 = p
    return w * lognormal_pdf(x, m1, s1) + (1 - w) * lognormal_pdf(x, m2, s2)


def mixture_stats(p, hi):
    x = np.linspace(1e-3, hi, 200000)
    f = mixture(x, p)
    c = np.cumsum(f) * (x[1] - x[0])
    return dict(median=float(np.interp(0.5, c / c[-1], x)), mean=float(np.sum(x * f) / np.sum(f)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", type=float, nargs=4, default=[7.29, 0.58, 2.58, 0.38])
    ap.add_argument("--n", type=int, default=80000)
    args = ap.parse_args()
    Rl = 659
    res = cs.run(Rl, sf.config(np.log(np.array(args.params))), args.n, 11)
    w, rd = res["w"], res["rd"]
    one = np.ones_like(w)
    fig, ax = plt.subplots(1, 2, figsize=(13, 5.2))
    rb = np.linspace(0, 40, 161)
    a = ax[0]
    for name, val, wt, colour, ls in (("Belin tubes: generated (all tubes)", res["r"], one, "tab:gray", "-"), ("Belin tubes: intense (selected and read)", res["r"][rd], w[rd], "tab:blue", "--")):
        h = np.histogram(val, np.linspace(0, 150, 600), weights=wt)[0].astype(float)
        h = np.histogram(val, rb, weights=wt)[0] / (h.sum() * (rb[1] - rb[0]))
        a.plot(0.5 * (rb[1:] + rb[:-1]), h, color=colour, ls=ls, lw=2.2, label="%s: median %.2f, mean %.2f" % (name, cs.wquantile(val, wt, 0.5), float(np.sum(val * wt) / np.sum(wt))))
    xr = np.linspace(0.05, 40, 800)
    tr = mixture_stats(cp.RADIUS, 200)
    a.plot(xr, mixture(xr, cp.RADIUS), color="tab:orange", lw=2.2, label="Tanahashi et al. (2001), DNS: median %.2f, mean %.2f" % (tr["median"], tr["mean"]))
    a.set_xlabel("r_max / eta")
    a.set_ylabel("pdf (area 1)")
    a.set_xlim(0, 30)
    a.legend(fontsize=8)
    a.set_title("(a) radius of maximum swirl", fontsize=10)
    up = math.sqrt(Rl / math.sqrt(15))                                         # u'/U_eta
    sb = np.linspace(0, 6, 241)
    a = ax[1]
    for name, val, wt, colour, ls in (("Belin tubes: generated (all tubes)", res["umax"] / up, one, "tab:gray", "-"), ("Belin tubes: intense (selected and read)", res["umax"][rd] / up, w[rd], "tab:blue", "--")):
        h = np.histogram(val, np.linspace(0, 30, 1201), weights=wt)[0].astype(float)
        h = np.histogram(val, sb, weights=wt)[0] / (h.sum() * (sb[1] - sb[0]))
        a.plot(0.5 * (sb[1:] + sb[:-1]), h, color=colour, ls=ls, lw=2.2, label="%s: median %.2f, mean %.2f" % (name, cs.wquantile(val, wt, 0.5), float(np.sum(val * wt) / np.sum(wt))))
    xs = np.linspace(0.01, 6, 800)
    ts = mixture_stats(cp.SWIRL, 30)
    a.plot(xs, mixture(xs, cp.SWIRL), color="tab:orange", lw=2.2, label="Tanahashi et al. (2001), DNS: median %.2f, mean %.2f" % (ts["median"], ts["mean"]))
    a.set_xlabel("U_max / u'")
    a.set_ylabel("pdf (area 1)")
    a.set_xlim(0, 4)
    a.legend(fontsize=8)
    a.set_title("(b) swirl, Re_lambda %d for the Belin tubes (u'/U_eta = %.1f)" % (Rl, up), fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "paper_chord_compare.png"), dpi=100)
    out = dict(Re_lambda=Rl, up_over_Ueta=up, r_population=dict(median=cs.wquantile(res["r"], one, 0.5), mean=float(np.mean(res["r"]))), r_intense=dict(median=cs.wquantile(res["r"][rd], w[rd], 0.5), mean=float(np.sum(res["r"][rd] * w[rd]) / np.sum(w[rd]))),
               r_tanahashi=tr, u_population=dict(median=cs.wquantile(res["umax"] / up, one, 0.5), mean=float(np.mean(res["umax"] / up))),
               u_intense=dict(median=cs.wquantile(res["umax"][rd] / up, w[rd], 0.5), mean=float(np.sum(res["umax"][rd] / up * w[rd]) / np.sum(w[rd]))), u_tanahashi=ts)
    with open(os.path.join(HERE, "paper_chord_numbers.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
