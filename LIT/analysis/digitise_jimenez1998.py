"""digitise_jimenez1998.py  v01  Reads Fig. 3(a) and 3(d) of Jimenez and Wray (1998), J. Fluid Mech. 373, 255: the pdfs of the radius R/eta and of the maximum azimuthal velocity u0/u' of the vortex filaments (worms) of forced isotropic turbulence, Re_lambda 36 ... 170.
Source   the raster images of pages 8 (panel a) and 9 (panel d) of 'Jimenez (1998).pdf' (white ink on black, 2416 x 1924 pixels).
Axes     frame lines found in the image: (a) x 0 -> 15 from column 20 to 2376, 1e0 at row 19, 628.5 px per decade (ticks 1e-1 at 647.5, 1e-2 at 1276);  (d) x 0 -> 3 from column 25 to 2381, 1e0 at row 190.5 (the frame top is 10^0.3), 573.8 px per decade (ticks 1e-1 at 761.5, 1e-2 at 1338).  The paper says the collapse of the curves of the different Re_lambda is excellent.
Method   the Re_lambda curves lie on each other (five line styles and one marker series), so no single curve is traced: in every pixel column the ink pixels inside the frame are collected (frame, ticks and the right edge column masked) and the median of log p is the central curve of the bundle
         (25 and 75 % quantiles as a band); columns with more than a quarter of a decade-run of ink (ticks, vertical lines) are skipped, and the steep rise at the left of the curves (R/eta < 1.9, u0/u' < 0.12) is left out.  Statistics from the central curve normalised to unit area over the range shown.  u0/u' is in units of the rms velocity (the paper's normalisation), not u_K.
Output   jimenez1998_pdfs_radius.csv, jimenez1998_pdfs_swirl.csv (x, p_lo, p_mid, p_hi), jimenez1998_pdfs.png, numbers printed.
Usage    python digitise_jimenez1998.py
Versions M01 m01.v01 (2026-11-15): first version.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pypdfium2 as pdfium
import pypdfium2.raw as raw

HERE = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.join(os.path.dirname(HERE), "Jimenez (1998).pdf")
# name: (page index, image index, x0 col, x1 col, x at x0, x at x1, frame top row, frame bottom row, row of the tick 1e0, pixels per decade; (a): ticks 1e-1 at row 647.5 and 1e-2 at 1276; (d): the frame top is 10^0.3, ticks 1e0 at 190.5, 1e-1 at 761.5, 1e-2 at 1338)
FIG = {"radius": (7, 0, 20, 2376, 0.0, 15.0, 22, 1904.5, 19.0, 628.5), "swirl": (8, 1, 25, 2381, 0.0, 3.0, 21, 1903.5, 190.5, 573.8)}


def ink(page_index, image_index):
    page = pdfium.PdfDocument(PDF)[page_index]
    imgs = [o for o in page.get_objects() if o.type == raw.FPDF_PAGEOBJ_IMAGE]
    return np.array(imgs[image_index].get_bitmap().to_pil().convert("L")) > 128


def bundle(b, spec):
    _, _, x0, x1, v0, v1, yt, yb, y1, per_dec = spec
    out = []
    for px in range(x0 + 30, x1 - 60):
        col = b[:, px].copy()
        col[:int(yt) + 14] = False
        col[int(yb) - 14:] = False
        ys = np.nonzero(col)[0]
        if len(ys) < 2 or len(ys) > 0.25 * (yb - yt):                           # no ink, or a column that is a tick or a vertical line of the frame
            continue
        if len(ys) < 2:
            continue
        lp = -(ys - y1) / per_dec
        out.append((v0 + (px - x0) / (x1 - x0) * (v1 - v0), *np.quantile(lp, [0.25, 0.5, 0.75])))
    out = np.array(out)
    k = 15                                                                       # a running median over 15 columns (0.1 of R/eta) removes the isolated spikes of ticks and markers
    for j in (1, 2, 3):
        pad = np.r_[np.full(k // 2, out[0, j]), out[:, j], np.full(k // 2, out[-1, j])]
        out[:, j] = np.median(np.lib.stride_tricks.sliding_window_view(pad, k), axis=1)
    return out


def stats(x, p):
    p = p / np.trapezoid(p, x)
    c = np.r_[0, np.cumsum(0.5 * (p[1:] + p[:-1]) * np.diff(x))]
    return dict(mode=float(x[np.argmax(p)]), median=float(np.interp(0.5, c, x)), mean=float(np.trapezoid(x * p, x)), q10=float(np.interp(0.1, c, x)), q90=float(np.interp(0.9, c, x)))


def main():
    fig, ax = plt.subplots(1, 2, figsize=(13, 5))
    for a, (name, spec) in zip(ax, FIG.items()):
        d = bundle(ink(spec[0], spec[1]), spec)
        d = d[d[:, 0] >= (1.9 if name == "radius" else 0.12)]                     # left of this the curves rise steeply and the bundle is no longer a single curve
        x, lo, mid, hi = d[:, 0], 10 ** d[:, 1], 10 ** d[:, 2], 10 ** d[:, 3]
        a.semilogy(x, mid, "k-", label="central curve of the bundle")
        a.fill_between(x, lo, hi, color="0.8", label="25-75% of the pixels")
        a.set_xlabel("R / eta" if name == "radius" else "u0 / u'")
        a.set_ylabel("pdf")
        a.set_title("Jimenez and Wray (1998) Fig. 3%s, digitised" % ("a" if name == "radius" else "d"), fontsize=10)
        a.legend(fontsize=8)
        a.set_ylim(1e-3, 3)
        with open(os.path.join(HERE, "jimenez1998_pdfs_%s.csv" % name), "w") as f:
            f.write("x,p_lo,p_mid,p_hi\n")
            for i in range(len(x)):
                f.write("%.4f,%.6g,%.6g,%.6g\n" % (x[i], lo[i], mid[i], hi[i]))
        s = stats(x, mid)
        print(name, "area %.3f mode %.2f median %.2f mean %.2f q10 %.2f q90 %.2f" % (np.trapezoid(mid, x), s["mode"], s["median"], s["mean"], s["q10"], s["q90"]))
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "jimenez1998_pdfs.png"), dpi=90)


if __name__ == "__main__":
    main()
