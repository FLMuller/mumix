"""plot_pirozzoli2012_pdf.py  v01  Digitise Fig. 2 of Pirozzoli (2012) (pirozzoli2012_fig2.png, a screenshot of the figure: the pdfs of the vortex core radius r0/eta (a) and of the maximum induced
velocity v0/u_k (b); symbols: the DNS of the paper (test case D), line: Tanahashi et al. at Re_lambda = 97) as plot_das2006_pdf.py: the symbols and the line are enclosed between a top and a
bottom bound in each pixel column, P = (P_top + P_bottom)/2; columns whose lowest point is at or below twice the p of the bottom axis (1e-5) are ignored; the tick marks are masked.  P is normalised
to unit area and fitted with two lognormals (mu2 >= mu1, start a1 = 0.7; fit_tanahashi_lognormal.fit_mixture).
Axes (pixels of the png): (a) x 125 (0) to 361.5 (50), y 69 (p = 1) to 216.5 (1e-5); (b) x 419 (0) to 655 (15), same y.  The screenshot has a low resolution: about 3% of a decade per pixel.
Writes pirozzoli2012_overlay.png, pirozzoli2012_pdfs.png and pirozzoli2012_pdfs.csv.   Usage: python plot_pirozzoli2012_pdf.py
"""
import os

import numpy as np
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import fit_tanahashi_lognormal as fl

HERE = os.path.dirname(os.path.abspath(__file__))
PANELS = {"D": dict(x0=125.0, x1=361.5, y0=69.0, y1=216.5, xmax=50.0, top_exp=0, decades=5, xstart=130, xstop=355, legend=(9999, 0), inset=(0, 0, 0), tmask=76, xmin=1.0, floor=1e-5),
          "v": dict(x0=419.0, x1=655.0, y0=69.0, y1=216.5, xmax=15.0, top_exp=0, decades=5, xstart=424, xstop=597, legend=(9999, 0), inset=(0, 0, 0), tmask=76, xmin=0.2, floor=1e-5)}


def digitise(dark, pn):
    xs, top, bot = [], [], []
    for x in range(pn["xstart"], pn["xstop"]):
        ys = np.nonzero(dark[pn["tmask"]:int(pn["y1"]) - 14, x])[0] + pn["tmask"]
        if x > pn["legend"][0]:
            ys = ys[ys > pn["legend"][1]]
        if pn["inset"][0] <= x <= pn["inset"][1]:                    # the inset of the figure (a second small plot) hides the curves above its lower edge
            ys = ys[ys > pn["inset"][2]]
        if len(ys):
            xs.append(x)
            top.append(ys.min())
            bot.append(ys.max())
    xs, top, bot = np.array(xs), np.array(top, float), np.array(bot, float)
    p_of = lambda y: 10.0 ** (pn["top_exp"] - (y - pn["y0"]) / (pn["y1"] - pn["y0"]) * pn["decades"])
    ptop, pbot = p_of(top), p_of(bot)
    ok = pbot > 2.0 * pn["floor"]
    xs, top, bot, ptop, pbot = xs[ok], top[ok], bot[ok], ptop[ok], pbot[ok]
    x = (xs - pn["x0"]) / (pn["x1"] - pn["x0"]) * pn["xmax"]
    keep = x >= pn["xmin"]
    return dict(px=xs[keep], top=top[keep], bot=bot[keep], x=x[keep], ptop=ptop[keep], pbot=pbot[keep], p=((ptop + pbot) / 2)[keep])


def y_pixel(p, pn):
    return pn["y0"] + (pn["top_exp"] - np.log10(p)) / pn["decades"] * (pn["y1"] - pn["y0"])


def main():
    rgb = np.array(Image.open(os.path.join(HERE, "pirozzoli2012_fig2.png")).convert("RGB"))
    dark = np.array(Image.open(os.path.join(HERE, "pirozzoli2012_fig2.png")).convert("L")).astype(float) < 150
    res = {k: digitise(dark, pn) for k, pn in PANELS.items()}
    fig, ax = plt.subplots(figsize=(13, 6.5))
    ax.imshow(rgb[:240, :])
    for k, r in res.items():
        pn = PANELS[k]
        ax.plot(r["px"], r["top"], c="tab:blue", lw=1.0, label="top bound" if k == "D" else None)
        ax.plot(r["px"], r["bot"], c="tab:red", lw=1.0, label="bottom bound" if k == "D" else None)
        ax.plot(r["px"], y_pixel(r["p"], pn), c="tab:green", lw=1.6, label="P = (P_top + P_bottom)/2" if k == "D" else None)
    ax.set_xlim(60, 700)
    ax.set_ylim(235, 55)
    ax.legend(loc="upper center", fontsize=9, ncol=3, bbox_to_anchor=(0.5, 1.07))
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "pirozzoli2012_overlay.png"), dpi=130)
    plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    cols = {}
    for col, (k, name, unit, lin_max, floor) in enumerate((("D", r"$r_0/\eta$ (vortex core radius)", r"$r_0/\eta$", 25, 1e-5), ("v", r"$v_0/u_K$ (maximum induced velocity)", r"$v_0/u_K$", 15.0, 1e-5))):
        r = res[k]
        x, top, bot, p = r["x"], r["ptop"], r["pbot"], r["p"]
        area = np.trapezoid(p, x)
        top, bot, p = top / area, bot / area, p / area
        cum = np.cumsum(np.r_[0, 0.5 * (p[1:] + p[:-1]) * np.diff(x)])
        q = lambda f: x[np.searchsorted(cum, f * cum[-1])]
        mean = np.trapezoid(p * x, x)
        fl.SRATIO = 2.0 if k == "D" else 0.0          # sigma1 << sigma2 for the sizes, free for the swirl
        mix = fl.fit_mixture(x, top, bot, p, 0.7, "lin")
        xs = np.exp(np.linspace(np.log(x.min()), np.log(x.max()), 600))
        c1, c2 = mix[0] * fl.lognormal(xs, mix[1], mix[2]), (1 - mix[0]) * fl.lognormal(xs, mix[3], mix[4])
        n1, n2 = np.trapezoid(c1, xs), np.trapezoid(c2, xs)
        w = 2 if k == "D" else 2
        v1, v2 = np.trapezoid(c1 * xs ** w, xs), np.trapezoid(c2 * xs ** w, xs)
        print("%s: area of the digitised pdf %.3f; mode %.3g median %.3g mean %.3g quartiles %.3g-%.3g 10-90%% %.3g-%.3g rms %.3g" % (
            k, area, x[np.argmax(p)], q(0.5), mean, q(0.25), q(0.75), q(0.1), q(0.9), np.sqrt(np.trapezoid(p * x ** 2, x))))
        print("   two lognormals: weights %.2f %.2f; medians %.3g %.3g; s %.2f %.2f; by number %.2f %.2f; by %s^2 %.2f %.2f; rms residual %.3f of the peak" % (
            mix[0], 1 - mix[0], np.exp(mix[1]), np.exp(mix[3]), mix[2], mix[4], n1 / (n1 + n2), n2 / (n1 + n2), "r" if k == "D" else "v", v1 / (v1 + v2), v2 / (v1 + v2),
            np.sqrt(np.mean((fl.mixture(x, mix) - p) ** 2)) / p.max()))
        for row, logy in enumerate((False, True)):
            a = axes[row][col]
            a.fill_between(x, bot, top, color="0.85")
            a.plot(xs, c1, c="tab:blue", lw=1.0, ls=":", label="component 1: weight %.2f, median %.3g, s = %.2f" % (mix[0], np.exp(mix[1]), mix[2]))
            a.plot(xs, c2, c="tab:orange", lw=1.0, ls=":", label="component 2: weight %.2f, median %.3g, s = %.2f" % (1 - mix[0], np.exp(mix[3]), mix[4]))
            a.plot(xs, c1 + c2, c="tab:red", lw=1.8, label="two lognormals")
            a.plot(x, p, c="k", lw=1.2, label="digitised P")
            a.set_xlim(0, lin_max if not logy else PANELS[k]["xmax"])
            if logy:
                a.set_yscale("log")
                a.set_ylim(floor * (1 if k == "D" else 1), None)
            a.set_xlabel(unit)
            a.set_ylabel("pdf" + (" (log)" if logy else ""))
            a.grid(alpha=0.25, which="both")
            a.legend(fontsize=7.5)
            if row == 0:
                a.set_title(name, fontsize=10)
        cols[k] = (x, p)
    fig.suptitle("Pirozzoli (2012) Fig. 2 (DNS test case D and the Tanahashi curve at Re_lambda = 97): P = (P_top + P_bottom)/2 fitted with two lognormals (linear domain, widths <= 0.7)", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "pirozzoli2012_pdfs.png"), dpi=110)
    n = max(len(res["D"]["x"]), len(res["v"]["x"]))
    pad = lambda a: np.pad(a, (0, n - len(a)), constant_values=np.nan)
    np.savetxt(os.path.join(HERE, "pirozzoli2012_pdfs.csv"), np.column_stack([pad(res["D"]["x"]), pad(res["D"]["ptop"]), pad(res["D"]["pbot"]), pad(res["D"]["p"]),
                                                                              pad(res["v"]["x"]), pad(res["v"]["ptop"]), pad(res["v"]["pbot"]), pad(res["v"]["p"])]),
               delimiter=",", header="r0_over_eta,pr_top,pr_bottom,pr,v0_over_uk,pv_top,pv_bottom,pv", comments="")


if __name__ == "__main__":
    main()
