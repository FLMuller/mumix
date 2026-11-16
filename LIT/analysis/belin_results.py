"""belin_results.py  v01  The results of the wire-and-tube model fitted to Belin et al. (1996): the figures of the paper and of the Belin tab, and the numbers (belin_model_numbers.json) that the texts quote.
Model   chord_belin_sens.py with the inputs of chord_belin_sens_fit.py (--phases): r_max lognormal, U_max = S x 0.769 Re_lambda^(1/3) U_eta x lognormal, independent; the incidence angle of every crossing from u'/U; Belin's gradient cut.
Figures belin_model_fig.png        2 rows (Re_lambda 255, 659) x 4 columns: r_max pdf, x = Re_f / Re_lambda^(1/2) pdf, U_max in cm/s (five curves), U_max / U_eta (five curves);
        belin_model_fig659.png     the same at Re_lambda 659 only (2 x 2), for the paper.
Numbers per Re_lambda (151, 255, 359, 507, 659, 718): the generated tubes (the population): median, mean and mode of r_max and of U_max; the same for the events that are read (as read: r_max = half the extrema spacing;
        U_max with Belin's rule dS / (2 x 0.14) and with the actual alpha), and the ratios that correct Belin's numbers: population / as read.
Usage:  python belin_results.py [--params 7.29 0.58 2.58 0.38] [--n 80000]

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
import chord_belin_fit_inputs as fi   # noqa: E402
import belin_gamma_pdf as bg          # noqa: E402
import belin_umax_five as b5          # noqa: E402

RE_LIST = (151, 255, 359, 507, 659, 718)


def wmean(v, w):
    return float(np.sum(v * w) / np.sum(w))


def wmode(v, w, hi):
    edges = np.linspace(0, hi, 121)
    h = np.histogram(v, edges, weights=w)[0]
    return float(0.5 * (edges[np.argmax(h)] + edges[np.argmax(h) + 1]))


def stats(v, w, hi):
    return dict(median=cs.wquantile(v, w, 0.5), mean=wmean(v, w), mode=wmode(v, w, hi))


def numbers(Rl, cfg, n):
    res = cs.run(Rl, cfg, n, 11)
    w, rd, ue = res["w"], res["rd"], res["ue"]
    one = np.ones_like(w)
    sin_a = np.abs(res["sin_w"])
    out = dict(Re_lambda=Rl, U_eta_cm_s=ue, U_cm_s=res["U"] * ue, sigma_sin_alpha=float(res["sigma_alpha"]), share_selected=float(w[res["kept"]].sum() / w.sum()), share_read_of_selected=float(w[rd].sum() / w[res["kept"]].sum()),
               r_population=stats(res["r"], one, 40), r_hit=stats(res["r"], w, 40), r_read=stats(res["r_read"][rd], w[rd], 40), r_read_true=stats(res["r"][rd], w[rd], 40),
               U_population=stats(res["umax"], one, 120), U_read_true=stats(res["umax"][rd], w[rd], 120),
               U_observed=stats(res["amp"][rd], w[rd], 120), U_belin=stats(res["amp"][rd] / cs.SIN_BELIN, w[rd], 400), U_actual_alpha=stats(res["amp"][rd] / sin_a[rd], w[rd], 400),
               sin_alpha_read=stats(sin_a[rd], w[rd], 1.0))
    out["r_correction_mean"] = out["r_population"]["mean"] / out["r_read"]["mean"]
    out["r_correction_median"] = out["r_population"]["median"] / out["r_read"]["median"]
    out["r_correction_mode"] = out["r_population"]["mode"] / out["r_read"]["mode"]
    out["r_correction_intense_median"] = out["r_read_true"]["median"] / out["r_read"]["median"]
    out["r_correction_intense_mean"] = out["r_read_true"]["mean"] / out["r_read"]["mean"]
    out["U_correction_intense_median"] = out["U_read_true"]["median"] / out["U_belin"]["median"]
    out["U_correction_belin_mean"] = out["U_population"]["mean"] / out["U_belin"]["mean"]
    out["U_correction_belin_median"] = out["U_population"]["median"] / out["U_belin"]["median"]
    out["U_correction_actual_mean"] = out["U_population"]["mean"] / out["U_actual_alpha"]["mean"]
    return out, res


def figure(rows, params, path):
    t5, t6, ok = fi.targets()
    c5, c6 = 0.5 * (fi.R5[1:] + fi.R5[:-1]), 0.5 * (fi.X6[1:] + fi.X6[:-1])
    ncol = 4
    fig, ax = plt.subplots(len(rows), ncol, figsize=(5.2 * ncol, 4.8 * len(rows)))
    ax = np.atleast_2d(ax)
    for row, (Rl, res) in enumerate(rows):
        w, rd, ue = res["w"], res["rd"], res["ue"]
        one = np.ones_like(w)
        a = ax[row, 0]
        rb = np.linspace(0, 30, 61)
        mid = 0.5 * (rb[1:] + rb[:-1])
        for name, val, wt, colour, ls, lw in (("generated (population)", res["r"], one, "tab:gray", "-", 2.2), ("hit the wire", res["r"], w, "tab:blue", "-", 2.0), ("hit, selected, read: true r_max", res["r"][rd], w[rd], "tab:blue", "--", 1.5)):
            h = np.histogram(val, np.linspace(0, 120, 481), weights=wt)[0].astype(float)
            h = np.histogram(val, rb, weights=wt)[0] / (h.sum() * (rb[1] - rb[0]))
            a.plot(mid, h, color=colour, ls=ls, lw=lw, label=name)
        a.plot(c5, sf.cs.pdf(res["r_read"][rd], w[rd], fi.R5), color="tab:red", lw=2.5, label="as read by the wire (spacing / 2)")
        a.plot(c5, t5, "ko", ms=3, label="Belin Fig. 5")
        a.set_xlabel("r_max / eta")
        a.set_title("Re_lambda %d: r_max" % Rl, fontsize=10)
        a = ax[row, 1]
        xb = np.linspace(0, 40, 41)
        xm = 0.5 * (xb[1:] + xb[:-1])
        xtrue = res["r"] * res["umax"] / (1.585 * math.sqrt(Rl))
        for name, val, wt, colour, ls, lw in (("generated (population)", xtrue, one, "tab:gray", "-", 2.2), ("hit the wire", xtrue, w, "tab:blue", "-", 2.0)):
            h = np.histogram(val, np.linspace(0, 400, 801), weights=wt)[0].astype(float)
            h = np.histogram(val, xb, weights=wt)[0] / (h.sum() * (xb[1] - xb[0]))
            a.plot(xm, h, color=colour, ls=ls, lw=lw, label=name)
        a.plot(c6, sf.cs.pdf(res["x_belin"][rd], w[rd], fi.X6), color="tab:red", lw=2.5, label="as read, Belin's rule")
        a.plot(c6[ok], t6[ok], "ko", ms=3, label="Belin Fig. 6")
        a.set_xlabel("x = Re_f / Re_lambda^(1/2)  (r_max U_max / (1.585 nu Re_lambda^(1/2)))")
        a.set_title("Re_lambda %d: the product r_max U_max" % Rl, fontsize=10)
        for k, (unit, label, top) in enumerate(((ue, "U_max (cm/s)", 400.0), (1.0, "U_max / U_eta", 200.0))):
            a = ax[row, 2 + k]
            edges = np.linspace(0, 6 * top, 6 * 160 + 1)
            centre = 0.5 * (edges[1:] + edges[:-1])
            for name, val, wt, colour, ls, lw in b5.curves_of(res):
                h = np.histogram(val * unit, edges, weights=wt)[0].astype(float)
                pdf = h / (h.sum() * (edges[1] - edges[0]))
                a.plot(centre[centre <= top], pdf[centre <= top], color=colour, ls=ls, lw=lw, label=name)
            a.set_xlim(0, top)
            a.set_xlabel(label)
            a.set_title("Re_lambda %d: %s" % (Rl, label), fontsize=10)
        for k in range(ncol):
            ax[row, k].set_ylabel("pdf (area 1)")
            ax[row, k].legend(fontsize=7, loc="upper right")
    fig.suptitle("wire-and-tube model fitted to Belin et al. (1996): r_max %.2f eta (ln-width %.2f), U_max %.2f x DNS (ln-width %.2f)" % tuple(params), fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=90)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", type=float, nargs=4, default=[7.29, 0.58, 2.58, 0.38])
    ap.add_argument("--n", type=int, default=80000)
    args = ap.parse_args()
    cfg = sf.config(np.log(np.array(args.params)))
    allnum, keep = [], {}
    for Rl in RE_LIST:
        num, res = numbers(Rl, cfg, args.n)
        allnum.append(num)
        keep[Rl] = res
        print("   intense (selected and read) tubes: true r_max median %.2f mean %.2f | as read median %.2f mean %.2f | factor median %.2f mean %.2f | U_max/U_eta true median %.1f, Belin median %.1f (factor %.2f), observed median %.1f" %
              (num["r_read_true"]["median"], num["r_read_true"]["mean"], num["r_read"]["median"], num["r_read"]["mean"], num["r_correction_intense_median"], num["r_correction_intense_mean"], num["U_read_true"]["median"], num["U_belin"]["median"], num["U_correction_intense_median"], num["U_observed"]["median"]))
        print("Re_lambda %d: r_max population mean %.2f median %.2f | as read mean %.2f median %.2f mode %.2f | correction (population / read) mean %.2f median %.2f mode %.2f | U_max/U_eta population mean %.1f, Belin %.1f, actual alpha %.1f (corrections %.2f, %.2f)" %
              (Rl, num["r_population"]["mean"], num["r_population"]["median"], num["r_read"]["mean"], num["r_read"]["median"], num["r_read"]["mode"], num["r_correction_mean"], num["r_correction_median"], num["r_correction_mode"],
               num["U_population"]["mean"] / num["U_eta_cm_s"] * num["U_eta_cm_s"], num["U_belin"]["mean"], num["U_actual_alpha"]["mean"], num["U_correction_belin_mean"], num["U_correction_actual_mean"]))
    with open(os.path.join(HERE, "belin_model_numbers.json"), "w") as f:
        json.dump(dict(params=args.params, rows=allnum), f, indent=1)
    figure([(255, keep[255]), (659, keep[659])], args.params, os.path.join(HERE, "belin_model_fig.png"))
    figure([(659, keep[659])], args.params, os.path.join(HERE, "belin_model_fig659.png"))


if __name__ == "__main__":
    main()
