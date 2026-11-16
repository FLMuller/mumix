"""belin_rumax_pdf.py  v01  The pdf of r_max U_max / (u' eta) from Belin et al. (1996) Fig. 6, against the same quantity of our tube data.
Chain (belin_gamma_pdf.py): Gamma / (u' eta) = 27.4 x, x = Re_f / Re_lambda^(1/2);  Gamma = 8.784 r_max U_max, hence
    y = r_max U_max / (u' eta) = Gamma / (8.784 u' eta) = 3.12 x          p(y) = p_x(y / 3.12) / 3.12.
Its Re_lambda free: in Kolmogorov units r_max U_max / (nu) = alpha beta = Re_c = y Re_lambda^(1/2) / 15^(1/4), so Re_c / Re_lambda^(1/2) = y / 1.968 (top axis).
Our data: the corrected rows of LIT/fittingtool/data/tubes.csv with a radius, a swirl and a single Re_lambda:  y = r_max/eta * (U_max / U_eta) * 15^(1/4) / Re_lambda^(1/2) (the quantities of the page, converted
with the isotropic u' / U_eta = (Re_lambda / sqrt 15)^(1/2)); histogram, area 1.
Usage: python belin_rumax_pdf.py     writes belin_rumax_pdf.png

Versions  M01 m01.v01 (2026-11-13): first version.
"""
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FIT = os.path.join(HERE, "..", "fittingtool")
sys.path.insert(0, FIT)
sys.path.insert(0, HERE)
import fitdata           # noqa: E402
import belin_gamma_pdf   # noqa: E402

C15 = 15 ** 0.25


def main():
    cx, px = belin_gamma_pdf.binned()
    scale = 8.784 * 1.585 * C15 / 8.784                    # y = 3.12 x ... (27.4 / 8.784)
    scale = 27.4 / 8.784
    y, py = scale * cx, px / scale
    mean = np.trapezoid(y * py, y)
    cdf = np.cumsum(py) / py.sum()
    median, mode = np.interp(0.5, cdf, y), y[np.argmax(py)]
    rows = fitdata.load(os.path.join(FIT, "data", "tubes.csv"), os.path.join(FIT, "data", "corrections.json"))
    data = np.array([x["r"] * x["u"] * C15 / math.sqrt(x["re"]) for x in rows if x["re"] is not None and x["r"] is not None and x["u"] is not None])
    fig, ax = plt.subplots(figsize=(9.5, 5.8))
    ax.plot(y, py, "ko-", ms=6, lw=1, label="Belin Fig. 6 (mode %.0f, median %.0f, mean %.0f)" % (mode, median, mean))
    lo, hi = np.percentile(data, [10, 90])
    ax.axvspan(lo, hi, color="tab:red", alpha=0.25, label="our tube data, corrected: 10-90 %% range %.1f-%.1f, median %.1f (n = %d; the pdf is too narrow to draw on this scale)" % (lo, hi, np.median(data), len(data)))
    ax.plot(data, np.full(len(data), -0.0007), "|", color="tab:red", ms=12, mew=1.5)
    top = ax.secondary_xaxis("top", functions=(lambda v: v / C15, lambda v: v * C15))
    top.set_xlabel("Re_c / Re_lambda^(1/2) = alpha beta / Re_lambda^(1/2)")
    ax.set_xlabel("r_max U_max / (u' eta)")
    ax.set_ylabel("pdf")
    ax.set_xlim(0, 125)
    ax.set_ylim(-0.002, None)
    ax.set_title("pdf of r_max U_max/(u' eta): Belin's circulation against our data", fontsize=10, pad=34)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_rumax_pdf.png"), dpi=110)
    print("Belin: y = r_max U_max/(u' eta): mode %.1f, median %.1f, mean %.1f;  our data: median %.2f, mean %.2f (n = %d), 10-90%% %.2f-%.2f" % (mode, median, mean, np.median(data), data.mean(), len(data), *np.percentile(data, [10, 90])))
    print("ratio Belin median / data median: %.1f" % (median / np.median(data)))


if __name__ == "__main__":
    main()
