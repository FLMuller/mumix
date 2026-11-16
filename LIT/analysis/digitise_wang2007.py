"""digitise_wang2007.py  v01  Digitises Fig. 6 (pdf of the diameter D/eta) and Fig. 7 (pdf of the maximum azimuthal velocity <u_theta>_m / u_k) of Wang, Tanahashi and Miyauchi (2007), Int. J. Heat Fluid Flow 28, 1280:
coherent fine scale eddies of the spatially developing mixing layer (Re_omega,0 = 700), ten bins of x/Lambda from 10-12 to 28-30, one curve each (markers on lines, log y axis, white on black in the raster image).
Source   the raster images of page 7 of 'Wang (2007).pdf' (2520 x 1712 and 2520 x 1735 pixels).  Axes: x from the ticks (Fig. 6: 0 at 298 px, 100 at 2464; Fig. 7: 0 at 301, 10 at 2485); y log, decades from the frame (Fig. 6: 1e0 at the top frame, 1e-4 at the bottom, 363 px per decade;
         Fig. 7: 1e0 at the top, 1e-3 at the bottom, 487.7 px per decade).
Method   the ten curves lie on each other, so no single curve is traced: in every pixel column of the plot the white pixels of the curves and markers are collected (legend, frame and ticks masked) and their 25, 50 and 75 % quantiles in log p give a low, central and high curve
         of the bundle (the spread is mostly the scatter of the markers; the central curve is the collapsed pdf).  Statistics are taken from the central curve, normalised to unit area over the range shown; r_max = D / 2.
Output   wang2007_pdfs.csv (D/eta or u/u_k, p_lo, p_mid, p_hi), wang2007_pdfs.png (check), numbers printed.
Usage    python digitise_wang2007.py
Versions M01 m01.v01 (2026-11-14): first version.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pypdfium2 as pdfium

HERE = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.join(os.path.dirname(HERE), "Wang (2007).pdf")

# name: (index of the image on the page, x0 px, x1 px, x value at x0, x value at x1, y top px (1e0), y bottom px, decades, legend mask (x0, x1, y0, y1))
FIG = {"diameter": (0, 298, 2464, 0.0, 100.0, 58, 1511, 4, (960, 2330, 100, 560)),
       "swirl": (1, 301, 2485, 0.0, 10.0, 60, 1524, 3, (400, 1780, 1050, 1470))}


def load_images():
    page = pdfium.PdfDocument(PDF)[6]
    imgs = [o for o in page.get_objects() if type(o).__name__ == "PdfImage"]
    return [np.array(o.get_bitmap().to_pil()) > 128 for o in imgs]


def bundle(b, spec):
    """x values and the 25, 50, 75 % quantiles of log10 p of the white pixels of every column."""
    _, x0, x1, v0, v1, yt, yb, dec, (lx0, lx1, ly0, ly1) = spec
    per_dec = (yb - yt) / dec
    out = []
    for px in range(x0 + 12, x1 - 40):
        col = b[:, px].copy()
        col[:yt + 55] = False                                             # frame and the long ticks of the x axis
        col[yb - 55:] = False
        if lx0 <= px <= lx1:
            col[ly0:ly1] = False                                          # legend
        ys = np.nonzero(col)[0]
        if len(ys) < 3:
            continue
        lp = -(ys - yt) / per_dec
        out.append((v0 + (px - x0) / (x1 - x0) * (v1 - v0), *np.quantile(lp, [0.25, 0.5, 0.75])))
    return np.array(out)


def stats(x, p):
    p = p / np.trapezoid(p, x)
    c = np.cumsum(0.5 * (p[1:] + p[:-1]) * np.diff(x))
    c = np.r_[0, c]
    return dict(mode=float(x[np.argmax(p)]), median=float(np.interp(0.5, c, x)), mean=float(np.trapezoid(x * p, x)), q10=float(np.interp(0.1, c, x)), q90=float(np.interp(0.9, c, x)))


def main():
    imgs = load_images()
    fig, ax = plt.subplots(1, 2, figsize=(13, 5))
    rows = {}
    for a, (name, spec) in zip(ax, FIG.items()):
        d = bundle(imgs[spec[0]], spec)
        x, lo, mid, hi = d[:, 0], 10 ** d[:, 1], 10 ** d[:, 2], 10 ** d[:, 3]
        a.semilogy(x, mid, "k-", label="central curve of the ten")
        a.fill_between(x, lo, hi, color="0.8", label="25-75% of the pixels")
        a.set_xlabel("D / eta" if name == "diameter" else "<u_theta>_m / u_k")
        a.set_ylabel("p")
        a.set_title("Wang et al. (2007) Fig. %d, digitised" % (6 if name == "diameter" else 7), fontsize=10)
        a.legend(fontsize=8)
        rows[name] = (x, lo, mid, hi)
        st = stats(x, mid)
        area = np.trapezoid(mid, x)
        print(name, "area of the digitised p over the range shown: %.3f; mode %.2f median %.2f mean %.2f q10 %.2f q90 %.2f" % (area, st["mode"], st["median"], st["mean"], st["q10"], st["q90"]))
        if name == "diameter":
            print("   as r_max = D/2: mode %.2f median %.2f mean %.2f q10 %.2f q90 %.2f" % (st["mode"] / 2, st["median"] / 2, st["mean"] / 2, st["q10"] / 2, st["q90"] / 2))
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "wang2007_pdfs.png"), dpi=90)
    for name, (x, lo, mid, hi) in rows.items():
        with open(os.path.join(HERE, "wang2007_pdfs_%s.csv" % name), "w") as f:
            f.write("x,p_lo,p_mid,p_hi\n")
            for i in range(len(x)):
                f.write("%.4f,%.6g,%.6g,%.6g\n" % (x[i], lo[i], mid[i], hi[i]))


if __name__ == "__main__":
    main()
