"""digitise_mouri_fig3.py  v01  Digitises Fig. 3 of Mouri, Hori and Kawashima (2007), Phys. Fluids 19, 055101: the pdf of the absolute spanwise-velocity increment / its standard deviation, Re_lambda 719 (duct), 1304 (boundary layer), 1934 (duct).
Source   the raster image of page 5 of 'Mouri (2007).pdf' (white curves on black, 795 x 1052 pixels).  x axis: 0 and 10 are the frame lines; y axis: log, one decade = the 82 px spacing of the ticks; the curves are shifted by 10^3 each (719 by 10^6, 1304 by 10^3, 1934 not shifted).
Method   column by column the white run nearest to the previous point is followed (continuity), starting at x = 0.5; the dotted Gaussian and the vertical bars and flags of the 1% and 0.1% marks are skipped (runs taller than 9 px are bridged by interpolation).  The vertical offset of each curve is then fixed by int P dx = 1.
Output   mouri_fig3_digitised.csv (x, P for each Re_lambda) and mouri_fig3_check.png (the trace over the image).
Usage    python digitise_mouri_fig3.py
Versions M01 m01.v01 (2026-11-13): first version.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pypdfium2 as pdfium

HERE = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.join(os.path.dirname(HERE), "Mouri (2007).pdf")
X0, X10 = 40.5, 781.5                                         # pixel columns of x = 0 and 10
DECADE = 82.0                                                 # pixels per decade
SHIFT = {719: 6, 1304: 3, 1934: 0}                            # the curves are shifted by 10^3 each
START = {719: 60, 1304: 308, 1934: 553}                       # an approximate y pixel of each curve near x = 0.5 (read from the image)
KEEP = 9                                                      # runs taller than this are bars or flags


def load():
    page = pdfium.PdfDocument(PDF)[4]
    img = [o for o in page.get_objects() if type(o).__name__ == "PdfImage"][0]
    return np.array(img.get_bitmap().to_pil()) > 128


def runs(col):
    idx = np.nonzero(col)[0]
    if len(idx) == 0:
        return []
    cut = np.nonzero(np.diff(idx) > 1)[0]
    starts = np.r_[idx[0], idx[cut + 1]]
    ends = np.r_[idx[cut], idx[-1]]
    return [(s, e) for s, e in zip(starts, ends)]


def trace(b, y_start, xs_px):
    ys, last, slope = [], float(y_start), 0.0
    for x in xs_px:
        rs = [r for r in runs(b[:, x]) if r[1] - r[0] <= KEEP and 4 < (r[0] + r[1]) / 2 < 925]
        pred = last + slope
        if rs:
            best = min(rs, key=lambda r: abs((r[0] + r[1]) / 2 - pred))
            c = (best[0] + best[1]) / 2
            if abs(c - pred) < 7:
                slope = 0.7 * slope + 0.3 * (c - last)
                last = c
                ys.append(c)
                continue
        ys.append(np.nan)
        last = pred
    return np.array(ys)


def main():
    b = load()
    xs_px = np.arange(int(X0 + 0.5 * 74.1), int(X10) - 3)
    xv = (xs_px - X0) / (X10 - X0) * 10
    fig, ax = plt.subplots(1, 2, figsize=(14, 8))
    ax[0].imshow(b, cmap="gray")
    rows = []
    out = {}
    for Rl, ys0 in START.items():
        y = trace(b, ys0, xs_px)
        ok = ~np.isnan(y)
        y = np.interp(xv, xv[ok], y[ok])
        ax[0].plot(xs_px, y, "r-", lw=0.8)
        logp = -(y - 0) / DECADE                                          # up to a constant: the offset follows from the normalisation
        p = 10 ** logp
        area = np.trapezoid(p, xv)                                         # x from 0.5; add the part below 0.5 as the first value times 0.5
        area += 0.5 * p[0]
        out[Rl] = (xv, p / area)
        print(Rl, "gaps filled:", int((~ok).sum()), "of", len(ok))
    for Rl, (xv_, p) in out.items():
        ax[1].semilogy(xv_, p, label="Re_lambda = %d" % Rl)
    ax[1].legend()
    ax[1].set_xlabel("|velocity increment| / standard deviation")
    ax[1].set_ylabel("pdf, normalised int P dx = 1 (digitised)")
    fig.savefig(os.path.join(HERE, "mouri_fig3_check.png"), dpi=80)
    with open(os.path.join(HERE, "mouri_fig3_digitised.csv"), "w") as f:
        f.write("x,P_719,P_1304,P_1934\n")
        for i, x in enumerate(xv):
            f.write("%.4f,%.6g,%.6g,%.6g\n" % (x, out[719][1][i], out[1304][1][i], out[1934][1][i]))


if __name__ == "__main__":
    main()
