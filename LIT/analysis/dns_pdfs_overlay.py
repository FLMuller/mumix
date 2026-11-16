"""dns_pdfs_overlay.py  v01  One picture per reference: the original figure (cut out of the paper) with the digitised curves drawn over it, to see by eye whether the digitisation follows the figure.
Sources  the screenshots or crops that each digitising script read (Tanahashi 2001 Fig. 7, Tanahashi 2004 Fig. 5, Das 2006 Fig. 7a/b, Pirozzoli 2012 Fig. 2), the raster images of the pdf pages (Wang 2007 Figs. 6, 7; Jimenez and Wray 1998 Fig. 3a, d) and the pdf pages
         rendered (Ghira 2022 Fig. 5a, b; Aligolzadeh 2023 Fig. 4a, b: vector figures).  The digitised curves are read back from the csv files of the digitising scripts and mapped to pixels with the same axis calibration as the scripts.
Drawn    green: the curve used (the mean of the top and bottom bounds or the central curve); blue and red: the top and bottom bounds or the 25 and 75 % curves (where the csv has them); Ghira: the seven digitised paths over the figure; Aligolzadeh: the bar tops.
Output   dns_overlay_<ref>.png for tanahashi2001, tanahashi2004, das2006, pirozzoli2012, wang2007, ghira2022, jimenez1998, aligolzadeh2023.
Usage    python dns_pdfs_overlay.py
Versions M01 m01.v01 (2026-11-15): first version.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pypdfium2 as pdfium
import pypdfium2.raw as raw
from PIL import Image
from scipy import ndimage as ndi

import digitise_aligolzadeh2023 as dal
import digitise_ghira2022 as dgh
import digitise_jimenez1998 as dji
import digitise_wang2007 as dwa

HERE = os.path.dirname(os.path.abspath(__file__))
LIT = os.path.dirname(HERE)
S = 4.0                                                                           # render scale of the pdf pages (pixels per point)


def csv(name):
    return np.genfromtxt(os.path.join(HERE, name), delimiter=",", names=True, dtype=None, encoding="utf-8")


def rgb(name):
    return np.array(Image.open(os.path.join(HERE, name)).convert("RGB"))


def to_px(pn, x, p):
    """Pixel position of data (x, p) in a raster panel pn (x0, x1, y0, y1 pixels, xmax, top_exp, decades)."""
    return pn["x0"] + np.asarray(x) / pn["xmax"] * (pn["x1"] - pn["x0"]), pn["y0"] + (pn["top_exp"] - np.log10(np.asarray(p))) / pn["decades"] * (pn["y1"] - pn["y0"])


def panel(ax, img, box, curves, title, gray=False):
    """Show img[y0:y1, x0:x1] (box) and draw the curves (list of (px, py, colour, linewidth, label)) with the offset removed."""
    x0, x1, y0, y1 = [int(v) for v in box]
    x0, y0 = max(x0, 0), max(y0, 0)                                              # a negative start would wrap around in the slice
    x1, y1 = min(x1, img.shape[1]), min(y1, img.shape[0])
    ax.imshow(img[y0:y1, x0:x1], cmap="gray" if gray else None, extent=(x0, x1, y1, y0), interpolation="antialiased")
    for px, py, c, lw, lab in curves:
        ax.plot(px, py, color=c, lw=lw, label=lab, alpha=0.9)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y1, y0)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(title, fontsize=9)
    if any(c[4] for c in curves):
        ax.legend(fontsize=7, loc="upper right")


def margin(pn, l=70, r=25, t=25, b=45):
    return pn["x0"] - l, pn["x1"] + r, pn["y0"] - t, pn["y1"] + b


def raster_ref(name, image, panels, data, title, cols):
    """Tanahashi 2001 and 2004, Pirozzoli 2012: panels dict key -> pn; data: csv; cols: key -> (x column, p, top, bottom)."""
    img = rgb(image)
    d = csv(data)
    fig, ax = plt.subplots(1, len(panels), figsize=(7.2 * len(panels), 5.6))
    for a, (key, pn) in zip(np.atleast_1d(ax), panels.items()):
        xc, pc, tc, bc = cols[key]
        cur = []
        if tc:
            cur.append((*to_px(pn, d[xc], d[tc]), "tab:blue", 0.9, "top bound"))
            cur.append((*to_px(pn, d[xc], d[bc]), "tab:red", 0.9, "bottom bound"))
        cur.append((*to_px(pn, d[xc], d[pc]), "tab:green", 1.6, "curve used"))
        panel(a, img, margin(pn), cur, "%s, %s" % (title, key))
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "dns_overlay_%s.png" % name), dpi=90)
    plt.close(fig)


def finite(x, p):
    k = np.isfinite(x) & np.isfinite(p) & (p > 0)
    return x[k], p[k]


def main():
    T01 = {"D": dict(x0=124.5, x1=461.5, y0=31.5, y1=282.5, xmax=100.0, top_exp=0, decades=4), "v": dict(x0=572.5, x1=909.5, y0=31.5, y1=282.5, xmax=3.0, top_exp=1, decades=4)}
    T04 = {"D": dict(x0=331.5, x1=603.5, y0=47.5, y1=423.5, xmax=70.0, top_exp=0, decades=3), "v": dict(x0=714.5, x1=986.5, y0=47.5, y1=423.5, xmax=10.0, top_exp=1, decades=4)}
    PI = {"D": dict(x0=125.0, x1=361.5, y0=69.0, y1=216.5, xmax=50.0, top_exp=0, decades=5), "v": dict(x0=419.0, x1=655.0, y0=69.0, y1=216.5, xmax=15.0, top_exp=0, decades=5)}
    raster_ref("tanahashi2001", "tanahashi2001_fig7.png", T01, "tanahashi2001_pdfs.csv", "Tanahashi 2001 Fig. 7", {"D": ("D_star", "pD", "pD_top", "pD_bottom"), "v": ("v_star", "pv", "pv_top", "pv_bottom")})
    raster_ref("tanahashi2004", "tanahashi2004_fig5.png", T04, "tanahashi2004_pdfs.csv", "Tanahashi 2004 Fig. 5", {"D": ("D_over_eta", "pD", "pD_top", "pD_bottom"), "v": ("v_over_uk", "pv", "pv_top", "pv_bottom")})
    raster_ref("pirozzoli2012", "pirozzoli2012_fig2.png", PI, "pirozzoli2012_pdfs.csv", "Pirozzoli 2012 Fig. 2", {"D": ("r0_over_eta", "pr", "pr_top", "pr_bottom"), "v": ("v0_over_uk", "pv", "pv_top", "pv_bottom")})

    # Das 2006 Fig. 7: two crops
    DA = {"D": ("das2006_fig7a.png", dict(x0=216.0, x1=983.0, y0=46.0, y1=752.5, xmax=80.0, top_exp=-1, decades=2), ("D_star", "pD", "pD_top", "pD_bottom")),
          "u": ("das2006_fig7b.png", dict(x0=200.5, x1=966.0, y0=69.5, y1=774.5, xmax=3.0, top_exp=1, decades=3), ("u_star", "pv", "pv_top", "pv_bottom"))}
    d = csv("das2006_open_pdfs.csv")
    fig, ax = plt.subplots(1, 2, figsize=(14.4, 6))
    for a, (key, (image, pn, (xc, pc, tc, bc))) in zip(ax, DA.items()):
        x, p = finite(d[xc], d[pc])
        xt, pt = finite(d[xc], d[tc])
        xb, pb = finite(d[xc], d[bc])
        panel(a, rgb(image), margin(pn, 90, 30, 40, 60), [(*to_px(pn, xt, pt), "tab:blue", 0.9, "top bound"), (*to_px(pn, xb, pb), "tab:red", 0.9, "bottom bound"), (*to_px(pn, x, p), "tab:green", 1.6, "curve used (open symbols)")],
              "Das 2006 Fig. 7%s, %s" % ("a" if key == "D" else "b", key))
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "dns_overlay_das2006.png"), dpi=90)
    plt.close(fig)

    # Wang 2007: two raster images of page 7, white ink on black
    pdf = pdfium.PdfDocument(dwa.PDF)[6]
    imgs = [np.array(o.get_bitmap().to_pil().convert("L")) for o in pdf.get_objects() if type(o).__name__ == "PdfImage"]
    fig, ax = plt.subplots(1, 2, figsize=(14.4, 5.6))
    for a, (name, spec) in zip(ax, dwa.FIG.items()):
        idx, x0, x1, v0, v1, yt, yb, dec, _ = spec
        per_dec = (yb - yt) / dec
        c = csv("wang2007_pdfs_%s.csv" % name)
        px = x0 + (c["x"] - v0) / (v1 - v0) * (x1 - x0)
        y = lambda p: yt - np.log10(p) * per_dec
        panel(a, imgs[idx], (x0 - 150, x1 + 30, yt - 30, yb + 90), [(px, y(c["p_lo"]), "tab:blue", 0.9, "25% of the pixels"), (px, y(c["p_hi"]), "tab:red", 0.9, "75% of the pixels"), (px, y(c["p_mid"]), "tab:green", 1.6, "central curve")],
              "Wang 2007 Fig. %d, %s" % (6 if name == "diameter" else 7, name), gray=True)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "dns_overlay_wang2007.png"), dpi=90)
    plt.close(fig)

    # Jimenez and Wray 1998: the two raster panels, white ink on black
    fig, ax = plt.subplots(1, 2, figsize=(14.4, 5.6))
    for a, (name, spec) in zip(ax, dji.FIG.items()):
        _, _, x0, x1, v0, v1, yt, yb, y1, per_dec = spec
        c = csv("jimenez1998_pdfs_%s.csv" % name)
        px = x0 + (c["x"] - v0) / (v1 - v0) * (x1 - x0)
        y = lambda p: y1 - np.log10(p) * per_dec
        panel(a, ndi.grey_dilation(dji.ink(spec[0], spec[1]).astype(np.uint8) * 255, size=(5, 5)), (x0 - 40, x1 + 40, yt - 30, yb + 40), [(px, y(c["p_lo"]), "tab:blue", 0.9, "25% of the pixels"), (px, y(c["p_hi"]), "tab:red", 0.9, "75% of the pixels"), (px, y(c["p_mid"]), "tab:green", 1.6, "central curve")],
              "Jimenez and Wray 1998 Fig. 3%s" % ("a" if name == "radius" else "d"), gray=True)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "dns_overlay_jimenez1998.png"), dpi=90)
    plt.close(fig)

    # Ghira 2022 Fig. 5: pdf page 10 rendered, the vector paths read back
    page = pdfium.PdfDocument(dgh.PDF)[9]
    big = np.array(page.render(scale=S).to_pil().convert("RGB"))
    H = page.get_size()[1]
    allp = dgh.paths(page)
    frames = sorted(b for b, col, pts, o in allp if col == (0, 0, 0) and len(pts) == 5 and b[2] - b[0] > 100 and b[3] - b[1] > 100 and b[1] > 480)
    fig, ax = plt.subplots(1, 2, figsize=(14.4, 5.6))
    for a, name, fr in zip(ax, "ab", frames):
        spec = dict(dgh.PANEL[name], frame=fr)
        l, b, r, t = fr
        cur = []
        d = csv("ghira2022_fig5%s_pdfs.csv" % name)
        for k, re in enumerate(sorted(set(d["Re_lambda"]))):
            s = d["Re_lambda"] == re
            X = l + d["x"][s] / (spec["x"][1] - spec["x"][0]) * (r - l)
            Y = t - (np.log10(spec["ytop"]) - np.log10(d["p"][s])) / spec["dec"] * (t - b)
            cur.append((X * S, (H - Y) * S, "tab:green", 0.9, "digitised paths, Re_lambda 90-399" if k == 0 else None))
        panel(a, big, (l * S - 150, r * S + 40, (H - t) * S - 60, (H - b) * S + 140), cur, "Ghira 2022 Fig. 5%s" % name)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "dns_overlay_ghira2022.png"), dpi=90)
    plt.close(fig)

    # Aligolzadeh 2023 Fig. 4: pdf page 9 rendered, bar tops from the csv
    page = pdfium.PdfDocument(dal.PDF)[8]
    big = np.array(page.render(scale=S).to_pil().convert("RGB"))
    H = page.get_size()[1]
    frames = sorted(o.get_bounds() for o in page.get_objects() if o.type == raw.FPDF_PAGEOBJ_PATH and raw.FPDFPath_CountSegments(o.raw) == 5 and o.get_bounds()[2] - o.get_bounds()[0] > 100 and o.get_bounds()[3] - o.get_bounds()[1] > 100)
    d = csv("aligolzadeh2023_fig4_pdfs.csv")
    fig, ax = plt.subplots(1, 2, figsize=(14.4, 5.6))
    for a, name, fr in zip(ax, "ab", frames):
        l, b, r, t = fr
        s = d["panel"] == name
        xc, w, p = d["x_centre"][s], d["width"][s], d["p"][s]
        X = np.ravel(np.c_[xc - w / 2, xc + w / 2])
        P = np.ravel(np.c_[p, p])
        px = (l + X / dal.XMAX * (r - l)) * S
        py = (H - (b + P / dal.YMAX * (t - b))) * S
        panel(a, big, (l * S - 150, r * S + 40, (H - t) * S - 60, (H - b) * S + 140), [(px, py, "tab:green", 1.2, "bar tops, digitised")], "Aligolzadeh 2023 Fig. 4%s" % name)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "dns_overlay_aligolzadeh2023.png"), dpi=90)
    plt.close(fig)


if __name__ == "__main__":
    main()
