"""das2006_open_on_dots.py  Draw the open-symbol curve of the diameter pdf (plot_das2006_open_pdf.grid_curve, with the hand-marked points) on the copy of Fig. 7a that carries the hand-marked dots
(das2006_fig7a_dots.png): the upper series (green line), the lower series (cyan), their mean P (magenta, dashed), the points by status (green dot found, blue square refined on black pixels, orange
triangle interpolated, magenta star hand-marked) and the straight-line tail (orange, D* >= 18).  Writes das2006_open_on_dots.png.   Usage: python das2006_open_on_dots.py
"""
import os

import numpy as np
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import plot_das2006_open_pdf as po

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    pn = po.PANELS["D"]
    im, pts_all = po.open_points(pn)
    good = po.reject_outliers(im, pts_all, pn)
    x, P, series, flag, h, strength = po.grid_curve(pn, im, pts_all[good], tracking=True, gate=0.18, manual=po.manual_points())
    c = po.DOTS_CROP
    to_px = lambda d: c["x0"] + d / c["xmax"] * (c["x1"] - c["x0"])
    to_py = lambda p: c["y0"] + (c["top_exp"] - np.log10(p)) / c["decades"] * (c["y1"] - c["y0"])
    img = np.array(Image.open(os.path.join(HERE, "das2006_fig7a_dots.png")).convert("RGB"))
    fig, ax = plt.subplots(figsize=(11, 9.5))
    ax.imshow(img)
    for t, colour in ((0, "lime"), (1, "cyan")):
        ax.plot(to_px(x), to_py(series[t]), c=colour, lw=0.9, alpha=0.9)
        for f, mk, col, sz in ((0, "o", colour, 8), (2, "s", "blue", 18), (1, "^", "orange", 18), (3, "*", "magenta", 70)):
            sel = flag[t] == f
            ax.scatter(to_px(x[sel]), to_py(series[t][sel]), s=sz, c=col, marker=mk, edgecolors="k" if f else "none", linewidths=0.4, zorder=5)
    ax.plot(to_px(x), to_py(P), c="magenta", lw=1.2, ls="--", label="mean of the two series")
    xt = np.linspace(18, 80, 100)
    ax.plot(to_px(xt), to_py(0.1053 * np.exp(-0.0682 * xt)), c="orangered", lw=1.2, ls="-.", label="straight line p = 0.1053 exp(-0.0682 D*), D* >= 18")
    ax.set_xlim(190, 990)
    ax.set_ylim(780, 40)
    ax.axis("off")
    ax.legend(loc="upper right", bbox_to_anchor=(0.99, 0.55), fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "das2006_open_on_dots.png"), dpi=110)
    print("grid points %d; found %d + %d, refined %d + %d, interpolated %d + %d, hand-marked %d + %d" % (
        len(x), (flag[0] == 0).sum(), (flag[1] == 0).sum(), (flag[0] == 2).sum(), (flag[1] == 2).sum(), (flag[0] == 1).sum(), (flag[1] == 1).sum(), (flag[0] == 3).sum(), (flag[1] == 3).sum()))
    ms = po.manual_points()
    for name, d, p in ms:
        k = int(np.argmin(np.abs(x - d)))
        near = [("upper", series[0][k]), ("lower", series[1][k])]
        print("  dot %-6s D* %.1f p %.4f -> grid D* %.1f (offset %.2f); series there: upper %.4f, lower %.4f; flags %d %d" % (name, d, p, x[k], x[k] - d, near[0][1], near[1][1], flag[0][k], flag[1][k]))


if __name__ == "__main__":
    main()
