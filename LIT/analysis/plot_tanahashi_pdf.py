"""plot_tanahashi_pdf.py  v02  Digitise Fig. 7 of Tanahashi, Iwase and Miyauchi (2001) (tanahashi2001_fig7.png: the pdfs of the diameter D* and of the maximum azimuthal
velocity v*_theta,m of the coherent fine-scale eddies, mixing layer Re_omega,0 = 500), plot the result over the original figure, and plot the pdfs with their statistics.

Method (v02): the four times of the figure overlap, so for every pixel column of a panel the dark pixels (curves and markers) are enclosed between a top bound (the highest p) and
a bottom bound (the lowest p); P = (P_top + P_bottom)/2 is the curve used.  The legend boxes, the long tick marks at the top and bottom of the axes (the top 80 and bottom 14 pixel rows) and the last columns are masked.
Axes boxes (pixels of the png): left panel x 124.5 (D*=0) to 461.5 (100), y 31.5 (p=1) to 282.5 (1e-4); right panel x 572.5 (0) to 909.5 (3.0), y 31.5 (p=10) to 282.5 (1e-3).
A column whose lowest point is at or below twice the p of the bottom axis (2e-4 in the left panel, 2e-3 in the right) is a line that drops to zero in the noisy tail and is ignored.
Writes tanahashi2001_overlay.png (the original with top, bottom and P over it), tanahashi2001_pdfs.png and tanahashi2001_pdfs.csv.
Usage: python plot_tanahashi_pdf.py

Versions  M01 m01.v03 (2026-11-11): columns whose lowest point is <= 2 x the axis floor are ignored.  m01.v02: top and bottom bounds and their mean in place of the median of the dark pixels.  m01.v01: first version.
"""
import os

import numpy as np
from PIL import Image
from scipy.integrate import cumulative_trapezoid
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
TOP_MASK = 80          # pixel rows above this (p > about 0.2 of the left panel, 1.5 of the right) hold only the long tick marks, no curve
BOTTOM_MASK = 14       # the tick marks at the bottom spine
PANELS = {"D": dict(x0=124.5, x1=461.5, y0=31.5, y1=282.5, xmax=100.0, top_exp=0, decades=4, xstart=134, xstop=455, legend=(340, 125)),
          "v": dict(x0=572.5, x1=909.5, y0=31.5, y1=282.5, xmax=3.0, top_exp=1, decades=4, xstart=582, xstop=903, legend=(780, 125))}


def column_bounds(dark, pn):
    """Per pixel column: pixel y of the top and of the bottom of the dark pixels inside the axes (legend and the axes edges masked)."""
    xs, top, bot = [], [], []
    for x in range(pn["xstart"], pn["xstop"]):
        ys = np.nonzero(dark[TOP_MASK:int(pn["y1"]) - BOTTOM_MASK, x])[0] + TOP_MASK         # the tick marks of the axes reach into the panel: top and bottom rows are masked
        if x > pn["legend"][0]:
            ys = ys[ys > pn["legend"][1]]
        if len(ys):
            xs.append(x)
            top.append(ys.min())
            bot.append(ys.max())
    return np.array(xs), np.array(top, float), np.array(bot, float)


def p_of(y, pn):
    return 10.0 ** (pn["top_exp"] - (y - pn["y0"]) / (pn["y1"] - pn["y0"]) * pn["decades"])


def digitise(dark, key):
    pn = PANELS[key]
    xs, top, bot = column_bounds(dark, pn)
    ptop, pbot = p_of(top, pn), p_of(bot, pn)
    floor = 10.0 ** (pn["top_exp"] - pn["decades"])               # the p at the bottom axis of the panel
    ok = pbot > 2.0 * floor                                       # a curve that drops to the bottom axis in this column is a line to zero, not data: the column is ignored
    xs, top, bot, ptop, pbot = xs[ok], top[ok], bot[ok], ptop[ok], pbot[ok]
    pmean = (ptop + pbot) / 2.0
    xv = (xs - pn["x0"]) / (pn["x1"] - pn["x0"]) * pn["xmax"]
    return dict(x=xv, px=xs, top=top, bot=bot, ptop=ptop, pbot=pbot, p=pmean, pn=pn)


def stats(x, p):
    area = np.trapezoid(p, x)
    pn = p / area
    cum = cumulative_trapezoid(pn, x, initial=0)
    q = lambda f: x[np.searchsorted(cum, f * cum[-1])]
    return dict(area=area, mode=x[np.argmax(p)], median=q(0.5), mean=np.trapezoid(pn * x, x), q10=q(0.1), q25=q(0.25), q75=q(0.75), q90=q(0.9))


def y_pixel(p, pn):
    return pn["y0"] + (pn["top_exp"] - np.log10(p)) / pn["decades"] * (pn["y1"] - pn["y0"])


def main():
    img = Image.open(os.path.join(HERE, "tanahashi2001_fig7.png")).convert("L")
    gray = np.array(img).astype(float)
    dark = gray < 120
    res = {k: digitise(dark, k) for k in PANELS}
    # 1. overlay on the original figure
    fig, ax = plt.subplots(figsize=(13, 6.5))
    ax.imshow(np.array(Image.open(os.path.join(HERE, "tanahashi2001_fig7.png")).convert("RGB"))[:300, :])
    for k, r in res.items():
        pn = r["pn"]
        ax.plot(r["px"], r["top"], c="tab:blue", lw=1.0, label="top bound" if k == "D" else None)
        ax.plot(r["px"], r["bot"], c="tab:red", lw=1.0, label="bottom bound" if k == "D" else None)
        ax.plot(r["px"], y_pixel(r["p"], pn), c="tab:green", lw=1.6, label="P = (P_top + P_bottom)/2" if k == "D" else None)
    ax.set_xlim(90, 930)
    ax.set_ylim(305, 15)
    ax.legend(loc="upper center", fontsize=9, ncol=3, bbox_to_anchor=(0.5, 1.07))
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "tanahashi2001_overlay.png"), dpi=130)
    plt.close(fig)
    # 2. the pdfs and their statistics (on the same axes as v01)
    out = {}
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for col, (k, name, unit, lin_max) in enumerate((("D", r"$D^*=D/\eta$ (diameter)", r"$D^*$", 60), ("v", r"$v^*_{\theta,m}=v_{\theta,m}/u'_{rms}$ (maximum azimuthal velocity)", r"$v^*_{\theta,m}$", 3.0))):
        r = res[k]
        keep = r["x"] >= (4.0 if k == "D" else 0.0)
        x, p, ptop, pbot = r["x"][keep], r["p"][keep], r["ptop"][keep], r["pbot"][keep]
        s = stats(x, p)
        out[k] = s
        for row, logy in enumerate((False, True)):
            a = axes[row][col]
            a.fill_between(x, pbot / s["area"], ptop / s["area"], color="0.8", label="between the bounds")
            a.plot(x, p / s["area"], c="k", lw=1.4, label="P = mean of the bounds, normalised")
            for key, colour in (("mode", "tab:red"), ("median", "tab:blue"), ("mean", "tab:green")):
                a.axvline(s[key], c=colour, ls="--", lw=1.2, label="%s %.3g" % (key, s[key]))
            a.set_xlim(0, lin_max if not logy else (100 if k == "D" else 3.0))
            if logy:
                a.set_yscale("log")
                a.set_ylim(1e-4 if k == "D" else 1e-3, None)
            a.set_xlabel(unit)
            a.set_ylabel("pdf" + (" (log)" if logy else ""))
            a.grid(alpha=0.25, which="both")
            a.legend(fontsize=8)
            if row == 0:
                a.set_title(name, fontsize=10)
    fig.suptitle("Tanahashi, Iwase and Miyauchi (2001), Fig. 7: pdfs of the coherent fine-scale eddies (mixing layer, Re_omega,0 = 500), P = (P_top + P_bottom)/2", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "tanahashi2001_pdfs.png"), dpi=110)
    n = max(len(res["D"]["x"]), len(res["v"]["x"]))
    pad = lambda a: np.pad(a, (0, n - len(a)), constant_values=np.nan)
    np.savetxt(os.path.join(HERE, "tanahashi2001_pdfs.csv"), np.column_stack([pad(res["D"]["x"]), pad(res["D"]["ptop"]), pad(res["D"]["pbot"]), pad(res["D"]["p"]),
                                                                              pad(res["v"]["x"]), pad(res["v"]["ptop"]), pad(res["v"]["pbot"]), pad(res["v"]["p"])]),
               delimiter=",", header="D_star,pD_top,pD_bottom,pD,v_star,pv_top,pv_bottom,pv", comments="")
    for k, s in out.items():
        print("%s: mode %.3g median %.3g mean %.3g quartiles %.3g-%.3g 10-90%% %.3g-%.3g (area %.3f)" % (k, s["mode"], s["median"], s["mean"], s["q25"], s["q75"], s["q10"], s["q90"], s["area"]))


if __name__ == "__main__":
    main()
