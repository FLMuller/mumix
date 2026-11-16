"""digitise_aligolzadeh2023.py  v01  Reads Fig. 4 of Aligolzadeh, Dore, Elsinga and Fleury (2023), J. Fluid Mech. 973, A5: the histograms of the normalised radius R* = R/eta of the vortex structures, (a) the scanning-PIV experiment (von Karman water tank) and (b) the DNS sets.
Source   the vector paths of page 9 of 'Aligolzadeh (2023).pdf': each histogram is one stepped outline of 245 path points; the frame is the 5-point path of each panel (x 0 -> 15, y 0 -> 0.25).
Method   the horizontal runs of the outline are the bar tops (x left, x right, height); the bin height is the plotted p.d.f.(R*) (a density; the bars are drawn with a small gap, the bin width is the pitch).  Mode, median and mean are taken from the bars (bin centres).
         The area of the plotted curve (sum of the heights x the bin width) is printed as a check; the page uses these as the whole-structure radius pdf (r_max taken as the mean R*).
Output   aligolzadeh2023_fig4_pdfs.csv (panel, x_centre, width, p), aligolzadeh2023_fig4.png, numbers printed.
Usage    python digitise_aligolzadeh2023.py
Versions M01 m01.v01 (2026-11-15): first version.
"""
import ctypes
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pypdfium2 as pdfium
import pypdfium2.raw as raw

HERE = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.join(os.path.dirname(HERE), "Aligolzadeh (2023).pdf")
XMAX, YMAX = 15.0, 0.25


def outline(o):
    out = []
    for k in range(raw.FPDFPath_CountSegments(o.raw)):
        x, y = ctypes.c_float(), ctypes.c_float()
        raw.FPDFPathSegment_GetPoint(raw.FPDFPath_GetPathSegment(o.raw, k), x, y)
        out.append((x.value, y.value))
    m = o.get_matrix()
    a = np.array(out)
    return m.a * a[:, 0] + m.c * a[:, 1] + m.e, m.b * a[:, 0] + m.d * a[:, 1] + m.f


def main():
    page = pdfium.PdfDocument(PDF)[8]
    frames, curves = [], []
    for o in page.get_objects():
        if o.type != raw.FPDF_PAGEOBJ_PATH:
            continue
        n = raw.FPDFPath_CountSegments(o.raw)
        b = o.get_bounds()
        if n == 5 and b[2] - b[0] > 100 and b[3] - b[1] > 100:
            frames.append(b)
        if n == 245:
            curves.append((b, o))
    frames.sort()
    curves.sort(key=lambda c: c[0][0])
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
    with open(os.path.join(HERE, "aligolzadeh2023_fig4_pdfs.csv"), "w") as f:
        f.write("panel,x_centre,width,p\n")
        for a, name, fr, (bb, o) in zip(ax, "ab", frames, curves):
            l, b, r, t = fr
            X, Y = outline(o)
            x = (X - l) / (r - l) * XMAX
            y = (Y - b) / (t - b) * YMAX
            bars = {}
            for i in range(len(x) - 1):
                if abs(Y[i] - Y[i + 1]) < 2e-3 and abs(X[i] - X[i + 1]) > 0.5 and (Y[i] - b) > 0.2:       # horizontal run = a bar top
                    xl, xr = sorted((x[i], x[i + 1]))
                    bars[round(xl, 3)] = (xl, xr, y[i])
            B = np.array(sorted(bars.values()))
            xc, p = 0.5 * (B[:, 0] + B[:, 1]), B[:, 2]
            pitch = float(np.median(np.diff(B[:, 0])))                                # the drawn bars leave a small gap: the bin width is the pitch
            w = np.full(len(xc), pitch)
            area = float(np.sum(p) * pitch)                                          # p is a density: the area is the sum of the heights times the bin width
            c = np.cumsum(p) / np.sum(p)
            mean = float(np.sum(xc * p) / np.sum(p))
            print("Fig. 4%s: %d bars, width %.3f, area %.3f, mode %.2f median %.2f mean %.2f q10 %.2f q90 %.2f" % (
                name, len(xc), float(np.median(w)), area, xc[np.argmax(p)], np.interp(0.5, c, xc), mean, np.interp(0.1, c, xc), np.interp(0.9, c, xc)))
            for i in range(len(xc)):
                f.write("%s,%.4f,%.4f,%.6g\n" % (name, xc[i], w[i], p[i]))
            a.step(xc, p, where="mid")
            a.set_xlabel("R* = R / eta")
            a.set_ylabel("p.d.f. (R*)")
            a.set_title("Aligolzadeh et al. (2023) Fig. 4%s, from the vector paths" % name, fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "aligolzadeh2023_fig4.png"), dpi=90)


if __name__ == "__main__":
    main()
