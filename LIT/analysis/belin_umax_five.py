"""belin_umax_five.py  v02  The U_max pdfs of the wire-and-tube model (chord_belin_sens.py) at Re_lambda 255 and 659, for the check of the chain from the tubes to Belin's numbers.
Curves  (i)   the tubes as generated: the input population of U_max (all weights equal);
        (ii)  the tubes that hit the wire (weighted by the footprint: a tube is met in proportion to the distance within which it can still be detected) -- and (ii') the ones that are selected and read;
        (iii) U_max as the wire observes it: the half swing of the read signals, dS / 2 (what the wire measures, no angle correction);
        (iv)  U_max as Belin gets it: dS / (2 sin alpha) with the constant sin alpha = 0.14 (his eq. 8);
        (v)   U_max with the actual incidence angle of each event as sampled: dS / (2 |sin alpha|).
Panels  columns Re_lambda 255 and 659, rows U_max in cm/s and U_max / U_eta (U_eta from the Table I chain); linear axes, pdfs normalised to an area of one over the whole range
        (the area inside the plotted range, and the part beyond it, are printed).
Usage:  python belin_umax_five.py [--params 7.29 0.58 2.58 0.38] [--n 80000]      (r_max median, r_max ln-width, U_max scale in DNS units, U_max ln-width)    writes belin_umax_five.png

Versions  M01 m01.v01 (2026-11-13): first version (log axis, Re_lambda on the rows).
          m01.v02 (2026-11-13): linear axes, one Re_lambda a column, area checked.
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


def curves_of(res):
    w, rd = res["w"], res["rd"]
    sin_a = np.abs(res["sin_w"])
    return [("(i) generated (the population)", res["umax"], np.ones_like(w), "tab:gray", "-", 2.2),
            ("(ii) the tubes that hit the wire", res["umax"], w, "tab:blue", "-", 2.2),
            ("(ii') hit, selected and read", res["umax"][rd], w[rd], "tab:blue", "--", 1.6),
            ("(iii) as observed by the wire: dS / 2", res["amp"][rd], w[rd], "tab:green", "-", 2.2),
            ("(iv) Belin's rule: dS / (2 x 0.14)", res["amp"][rd] / cs.SIN_BELIN, w[rd], "tab:red", "-", 2.2),
            ("(v) the actual alpha: dS / (2 |sin alpha|)", res["amp"][rd] / sin_a[rd], w[rd], "tab:purple", "-", 2.2)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--params", type=float, nargs=4, default=[7.29, 0.58, 2.58, 0.38])
    ap.add_argument("--n", type=int, default=80000)
    args = ap.parse_args()
    v = np.log(np.array(args.params))
    fig, ax = plt.subplots(2, 2, figsize=(15, 11))
    for col, Rl in enumerate((255, 659)):
        res = cs.run(Rl, sf.config(v), args.n, 11 + (col))
        ue = res["ue"]
        for row, (unit, label, top) in enumerate(((ue, "U_max (cm/s)", 400.0), (1.0, "U_max / U_eta", 200.0))):
            a = ax[row, col]
            edges = np.linspace(0, 6 * top, 6 * 160 + 1)                                  # far beyond the plotted range, so that the area is one
            centre = 0.5 * (edges[1:] + edges[:-1])
            for name, val, wt, colour, ls, lw in curves_of(res):
                h = np.histogram(val * unit, edges, weights=wt)[0].astype(float)
                pdf = h / (h.sum() * (edges[1] - edges[0]))
                inside = centre <= top
                a.plot(centre[inside], pdf[inside], color=colour, ls=ls, lw=lw, label="%s: median %.3g" % (name, cs.wquantile(val * unit, wt, 0.5)))
                print("Re_lambda %d %-16s %-44s area in the plot %.3f, beyond %.3f, total %.3f" % (Rl, label, name, pdf[inside].sum() * (edges[1] - edges[0]), pdf[~inside].sum() * (edges[1] - edges[0]), pdf.sum() * (edges[1] - edges[0])))
            a.set_xlim(0, top)
            a.set_xlabel(label)
            a.set_ylabel("pdf (area 1)")
            a.set_title("Re_lambda %d  (U_eta %.2f cm/s, mean flow U %.0f cm/s)" % (Rl, ue, res["U"] * ue), fontsize=10)
            a.legend(fontsize=8, loc="upper right")
    fig.suptitle("U_max in the wire-and-tube model: generated, hit, observed, and with Belin's and the actual incidence angle (r_max %.2f eta/%.2f, U_max %.2f x DNS/%.2f)" % tuple(args.params), fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_umax_five.png"), dpi=90)


if __name__ == "__main__":
    main()
