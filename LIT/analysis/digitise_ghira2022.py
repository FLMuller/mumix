"""digitise_ghira2022.py  v01  Reads Fig. 5 of Ghira, Elsinga and da Silva (2022), Phys. Rev. Fluids 7, 104605: the pdfs of the local radius R_ivs of the intense vorticity structures, (a) over R_ivs/eta and (b) over R_ivs/R_B, seven simulations (Re_lambda 90 ... 399).
Source   the vector paths of page 10 of 'Ghira (2022).pdf' (pypdfium2 raw path segments): the points are the plotted points, no raster reading error.
Axes     from the frame paths: (a) x 0 -> 14 over the frame width, y log 1e-4 (bottom) -> 1e0 (top); (b) x 0 -> 4, y 1e-4 -> 1e1.
Method   one path per simulation, colour matched to the legend of the figure; each curve is normalised to unit area over the range shown and its mode, median and mean are taken from the points (log y, so the curve is the plotted one).
         r_max = 1.12 R_ivs / (R_ivs/R_B) is the page's conversion for the mean row; here only the radius pdf of (a) is converted (r = 1.12 R_ivs).
Output   ghira2022_fig5a_pdfs.csv (Re_lambda, x, p), ghira2022_fig5b_pdfs.csv, ghira2022_fig5.png, numbers printed.
Usage    python digitise_ghira2022.py
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
PDF = os.path.join(os.path.dirname(HERE), "Ghira (2022).pdf")
RE = {(0, 114, 189): 90, (217, 83, 25): 148, (237, 177, 32): 191, (126, 47, 142): 242, (119, 172, 48): 314, (77, 190, 238): 292, (0, 0, 0): 399}
# panel: (frame x range px-free, frame bounds (left, bottom, right, top) in page points, x0, x1, decades below the top value, top value)
PANEL = {"a": dict(frame=(75.8, 516.4, 238.9, 641.4), x=(0.0, 14.0), ytop=1e0, dec=4),
         "b": dict(frame=None, x=(0.0, 4.0), ytop=1e1, dec=5)}


def paths(page):
    """Every path of the page as (bounds, stroke colour, list of (x, y) points)."""
    out = []
    for o in page.get_objects():
        if o.type != raw.FPDF_PAGEOBJ_PATH:
            continue
        pts = []
        for k in range(raw.FPDFPath_CountSegments(o.raw)):
            seg = raw.FPDFPath_GetPathSegment(o.raw, k)
            x, y = ctypes.c_float(), ctypes.c_float()
            raw.FPDFPathSegment_GetPoint(seg, x, y)
            pts.append((x.value, y.value))
        c = [ctypes.c_uint() for _ in range(4)]
        raw.FPDFPageObj_GetStrokeColor(o.raw, *c)
        out.append((o.get_bounds(), tuple(v.value for v in c[:3]), pts, o))
    return out


def stats(x, p):
    p = p / np.trapezoid(p, x)
    c = np.r_[0, np.cumsum(0.5 * (p[1:] + p[:-1]) * np.diff(x))]
    return dict(mode=float(x[np.argmax(p)]), median=float(np.interp(0.5, c, x)), mean=float(np.trapezoid(x * p, x)), q10=float(np.interp(0.1, c, x)), q90=float(np.interp(0.9, c, x)))


def curves(allp, frame, spec):
    """Curves of one panel: the paths inside the frame whose stroke colour is one of the legend colours and that are wider than 60 pt."""
    l, b, r, t = frame
    res = {}
    for bounds, col, pts, o in allp:
        if col in RE and l - 3 < bounds[0] and bounds[2] < r + 6 and b - 3 < bounds[1] and bounds[3] < t + 3 and bounds[2] - bounds[0] > 60 and len(pts) > 40:
            xy = np.array(pts)
            # the path points are in the object's own space: map them to the page with the object's matrix
            m = o.get_matrix()
            X = m.a * xy[:, 0] + m.c * xy[:, 1] + m.e
            Y = m.b * xy[:, 0] + m.d * xy[:, 1] + m.f
            x = spec["x"][0] + (X - l) / (r - l) * (spec["x"][1] - spec["x"][0])
            lp = np.log10(spec["ytop"]) - (t - Y) / (t - b) * spec["dec"]
            res[RE[col]] = (x, 10 ** lp)
    return res


def main():
    page = pdfium.PdfDocument(PDF)[9]
    allp = paths(page)
    # frame of panel b: the 5-segment black frame path to the right of 5a
    frames = [bnd for bnd, col, pts, o in allp if col == (0, 0, 0) and len(pts) == 5 and bnd[2] - bnd[0] > 100 and bnd[3] - bnd[1] > 100 and bnd[1] > 480]
    frames.sort()
    PANEL["a"]["frame"], PANEL["b"]["frame"] = frames[0], frames[1]
    fig, ax = plt.subplots(1, 2, figsize=(13, 5))
    for a, name in zip(ax, "ab"):
        res = curves(allp, PANEL[name]["frame"], PANEL[name])
        with open(os.path.join(HERE, "ghira2022_fig5%s_pdfs.csv" % name), "w") as f:
            f.write("Re_lambda,x,p\n")
            for re in sorted(res):
                x, p = res[re]
                for i in range(len(x)):
                    f.write("%d,%.5f,%.6g\n" % (re, x[i], p[i]))
        for re in sorted(res):
            x, p = res[re]
            o = np.argsort(x)
            x, p = x[o], p[o]
            area = np.trapezoid(p, x)
            s = stats(x, p)
            a.semilogy(x, p, label="Re_lambda = %d" % re)
            print("Fig. 5%s Re_lambda %3d: area %.3f mode %.3f median %.3f mean %.3f q10 %.3f q90 %.3f" % (name, re, area, s["mode"], s["median"], s["mean"], s["q10"], s["q90"]))
        a.set_xlabel("R_ivs / eta" if name == "a" else "R_ivs / R_B")
        a.set_ylabel("pdf")
        a.set_title("Ghira et al. (2022) Fig. 5%s, from the vector paths" % name, fontsize=10)
        a.legend(fontsize=8)
        a.set_ylim(1e-4, 1.3 if name == "a" else 3)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "ghira2022_fig5.png"), dpi=90)


if __name__ == "__main__":
    main()
