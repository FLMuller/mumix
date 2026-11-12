"""plot_tanahashi2004_pdf.py  v01  Digitise Fig. 5 of Tanahashi, Kang, Miyamoto, Shiokawa and Miyauchi (2004) (tanahashi2004_fig5.png: the pdfs of the diameter D/eta and of the
maximum azimuthal velocity v_theta,max/u_k of the coherent fine-scale eddies in a turbulent channel flow, Re_tau = 800, nine bands of the wall distance y+), as plot_tanahashi_pdf.py
did for Fig. 7 of Tanahashi et al. (2001): the nine curves of a panel are enclosed between a top and a bottom bound in each pixel column, P = (P_top + P_bottom)/2; the columns whose
lowest point is at or below twice the p of the bottom axis are ignored; the legends, the insets and the tick marks are masked.  P is normalised to unit area and fitted in the linear
domain with two lognormals (widths <= 0.7), as fit_tanahashi_lognormal.py; the weights by number and by volume (D^2) and by <v^2> are printed.
Axes (pixels of the png): left panel x 331.5 (D/eta = 0) to 603.5 (70), y 47.5 (p = 1) to 423.5 (1e-3); right panel x 714.5 (0) to 986.5 (10), y 47.5 (p = 10) to 423.5 (1e-3).
Writes tanahashi2004_overlay.png, tanahashi2004_pdfs.png and tanahashi2004_pdfs.csv.   Usage: python plot_tanahashi2004_pdf.py
"""
import os

import numpy as np
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import fit_tanahashi_lognormal as fl

HERE = os.path.dirname(os.path.abspath(__file__))
PANELS = {"D": dict(x0=331.5, x1=603.5, y0=47.5, y1=423.5, xmax=70.0, top_exp=0, decades=3, xstart=338, xstop=601, legend=(450, 252), inset=(374, 474, 182), tmask=150, xmin=4.0, floor=1e-3),
          "v": dict(x0=714.5, x1=986.5, y0=47.5, y1=423.5, xmax=10.0, top_exp=1, decades=4, xstart=720, xstop=984, legend=(836, 252), inset=(752, 842, 182), tmask=150, xmin=0.0, floor=1e-3)}


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
    rgb = np.array(Image.open(os.path.join(HERE, "tanahashi2004_fig5.png")).convert("RGB"))
    dark = np.array(Image.open(os.path.join(HERE, "tanahashi2004_fig5.png")).convert("L")).astype(float) < 110
    res = {k: digitise(dark, pn) for k, pn in PANELS.items()}
    fig, ax = plt.subplots(figsize=(13, 6.5))
    ax.imshow(rgb[:445, :])
    for k, r in res.items():
        pn = PANELS[k]
        ax.plot(r["px"], r["top"], c="tab:blue", lw=1.0, label="top bound" if k == "D" else None)
        ax.plot(r["px"], r["bot"], c="tab:red", lw=1.0, label="bottom bound" if k == "D" else None)
        ax.plot(r["px"], y_pixel(r["p"], pn), c="tab:green", lw=1.6, label="P = (P_top + P_bottom)/2" if k == "D" else None)
    ax.set_xlim(300, 1010)
    ax.set_ylim(440, 30)
    ax.legend(loc="upper center", fontsize=9, ncol=3, bbox_to_anchor=(0.5, 1.07))
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "tanahashi2004_overlay.png"), dpi=130)
    plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    cols = {}
    for col, (k, name, unit, lin_max, floor) in enumerate((("D", r"$D^*=D/\eta$ (diameter)", r"$D^*$", 40, 1e-3), ("v", r"$v_{\theta,max}/u_K$ (maximum azimuthal velocity)", r"$v_{\theta,max}/u_K$", 10.0, 1e-3))):
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
            mix[0], 1 - mix[0], np.exp(mix[1]), np.exp(mix[3]), mix[2], mix[4], n1 / (n1 + n2), n2 / (n1 + n2), "D" if k == "D" else "v", v1 / (v1 + v2), v2 / (v1 + v2),
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
    fig.suptitle("Tanahashi et al. (2004) Fig. 5 (channel, Re_tau = 800, all wall bands): P = (P_top + P_bottom)/2 fitted with two lognormals (linear domain, widths <= 0.7)", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "tanahashi2004_pdfs.png"), dpi=110)
    n = max(len(res["D"]["x"]), len(res["v"]["x"]))
    pad = lambda a: np.pad(a, (0, n - len(a)), constant_values=np.nan)
    np.savetxt(os.path.join(HERE, "tanahashi2004_pdfs.csv"), np.column_stack([pad(res["D"]["x"]), pad(res["D"]["ptop"]), pad(res["D"]["pbot"]), pad(res["D"]["p"]),
                                                                              pad(res["v"]["x"]), pad(res["v"]["ptop"]), pad(res["v"]["pbot"]), pad(res["v"]["p"])]),
               delimiter=",", header="D_over_eta,pD_top,pD_bottom,pD,v_over_uk,pv_top,pv_bottom,pv", comments="")


if __name__ == "__main__":
    main()
