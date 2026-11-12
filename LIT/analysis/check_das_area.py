"""check_das_area.py  v01  Is the digitised Das et al. (2006) Fig. 7 pdf a pdf?  Integrates the top bound, the bottom bound and their mean P in linear p and linear x, and adds the mass that the digitised
range leaves out (the rise below the first column, the tail beyond the last one: exponential extrapolation of the last decade); overlays the curves on the original figure.
Reads das2006_pdfs.csv (plot_das2006_pdf.py).  Writes das2006_area_check.png.   Usage: python check_das_area.py
"""
import os

import numpy as np
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
PANELS = {"D": dict(x0=221.0, x1=436.0, y0=12.0, y1=209.0, xmax=80.0, top_exp=-1, decades=2, cols=("D_star", "pD_top", "pD_bottom", "pD")),
          "u": dict(x0=214.0, x1=428.0, y0=271.0, y1=468.0, xmax=3.0, top_exp=1, decades=3, cols=("u_star", "pv_top", "pv_bottom", "pv"))}


def tail_mass(x, p, n=8):
    """Mass beyond the last point, from the exponential decay of the last n points (p ~ p_end exp(-k (x - x_end)): mass p_end / k); 0 if the curve is not decreasing."""
    lp = np.log(p[-n:])
    k = -np.polyfit(x[-n:], lp, 1)[0]
    return p[-1] / k if k > 0 else 0.0


def main():
    d = np.genfromtxt(os.path.join(HERE, "das2006_pdfs.csv"), delimiter=",", names=True)
    rgb = np.array(Image.open(os.path.join(HERE, "das2006_fig7.png")).convert("RGB"))
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.imshow(rgb[:560, :])
    print("integrals in linear p and linear x over the digitised range, and the mass outside it")
    for key, pn in PANELS.items():
        x, top, bot, p = (d[c] for c in pn["cols"])
        ok = np.isfinite(x)
        x, top, bot, p = x[ok], top[ok], bot[ok], p[ok]
        a_top, a_bot, a_p = (np.trapezoid(v, x) for v in (top, bot, p))
        left = 0.5 * p[0] * (x[0] - (2.0 if key == "D" else 0.0))               # a linear rise from zero (D* = 2, u* = 0) to the first point
        right = tail_mass(x, p)
        print("  %s  x %.2f-%.2f: top bound %.3f, bottom bound %.3f, mean P %.3f; outside the range: rise %.3f, tail %.3f; mean P with both: %.3f" % (
            key, x.min(), x.max(), a_top, a_bot, a_p, left, right, a_p + left + right))
        px = pn["x0"] + x / pn["xmax"] * (pn["x1"] - pn["x0"])
        py = lambda v: pn["y0"] + (pn["top_exp"] - np.log10(v)) / pn["decades"] * (pn["y1"] - pn["y0"])
        ax.plot(px, py(top), c="tab:blue", lw=0.8)
        ax.plot(px, py(bot), c="tab:red", lw=0.8)
        ax.plot(px, py(p), c="tab:green", lw=1.5)
    ax.set_xlim(150, 470)
    ax.set_ylim(480, 0)
    ax.axis("off")
    ax.set_title("Das et al. (2006) Fig. 7: top bound (blue), bottom bound (red) and P (green) over the original figure", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "das2006_area_check.png"), dpi=130)


if __name__ == "__main__":
    main()
