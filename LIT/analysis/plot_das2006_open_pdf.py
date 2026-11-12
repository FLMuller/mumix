"""plot_das2006_open_pdf.py  v01  The open symbols of Fig. 7 of Das et al. (2006) (das2006_fig7a.png, das2006_fig7b.png: high-resolution crops of panels a and b): the pdfs of the diameter D* and
of the maximum azimuthal velocity of the coherent fine eddies in channel flow (Re_tau = 180) for five wall bands; the open circles (110 < y+ < 145) and open squares (145 < y+ < 180) are the
bands away from the wall, the filled symbols the bands near it.  Each open marker is a ring with a light centre: the centres are found as the holes of the dark pixels (binary_fill_holes minus the
dark pixels, area 6-45 px) outside the legend; the points of the two open series share the same abscissae, so the holes are grouped in columns (within 3.5 px) and each group gives
P = mean of its points (the circle and the square), with the group's highest and lowest point as bounds (one point where the two markers overlap).
Axes (pixels): (a) x 216 (D* = 0) to 983 (80), y 46 (p = 0.1) to 752.5 (1e-3); (b) x 200.5 (0) to 966 (3.0), y 69.5 (p = 10) to 774.5 (1e-2).
Outliers (holes between black markers) are rejected by reject_outliers (dark fraction of the annulus around the point); the overlay shows the accepted points in green and the rejected ones in red.  Writes das2006_open_pdfs.csv, das2006_open_overlay.png.   Usage: python plot_das2006_open_pdf.py
"""
import os

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
PANELS = {"D": dict(image="das2006_fig7a.png", x0=216.0, x1=983.0, y0=46.0, y1=752.5, xmax=80.0, top_exp=-1, decades=2, legend=(600, 350)),
          "u": dict(image="das2006_fig7b.png", x0=200.5, x1=966.0, y0=69.5, y1=774.5, xmax=3.0, top_exp=1, decades=3, legend=(570, 440))}


def open_points(pn):
    """Centres (pixels) of the open markers of a panel."""
    im = np.array(Image.open(os.path.join(HERE, pn["image"])).convert("L")).astype(float)
    dark = im < 128
    holes = ndi.binary_fill_holes(dark) & ~dark
    lab, n = ndi.label(holes)
    com = ndi.center_of_mass(holes, lab, range(1, n + 1))
    area = ndi.sum(holes, lab, range(1, n + 1))
    pts = [(c[1], c[0]) for c, a in zip(com, area) if 6 <= a <= 45 and pn["x0"] + 4 < c[1] < pn["x1"] - 4 and pn["y0"] + 3 < c[0] < pn["y1"] - 3
           and not (c[1] > pn["legend"][0] and c[0] < pn["legend"][1])]
    return im, np.array(sorted(pts))


def annulus_dark(dark, cx, cy, r0=5.5, r1=8.0):
    """Fraction of dark pixels in the annulus r0..r1 around a point: low around an open marker (a thin ring and the lines), high in a gap between filled markers."""
    x0, x1, y0, y1 = int(cx - r1 - 1), int(cx + r1 + 2), int(cy - r1 - 1), int(cy + r1 + 2)
    sub = dark[y0:y1, x0:x1]
    yy, xx = np.mgrid[y0:y1, x0:x1]
    r = np.hypot(xx - cx, yy - cy)
    m = (r >= r0) & (r <= r1)
    return float(sub[m].mean())


def reject_outliers(im, pts, pn, areas=None, dark_max=0.60):
    """Open-marker candidates that are really holes between black markers are rejected: the annulus 5.5-8 px around an open marker is mostly light (a thin ring and a few lines), around a gap
    between filled markers it is mostly dark; a point with more than `dark_max` dark pixels there is rejected.  (A running median of ln p along x was tried too and removed: the two open series
    differ by up to 10% and the median merged them.)  Returns a boolean array (True = accepted)."""
    dark = im < 128
    return np.array([annulus_dark(dark, x, y) < dark_max for x, y in pts])


# Points of the open series that are hidden behind black markers, marked by hand on a copy of the figure (das2006_fig7a_dots.png: a green dot for the open circles (110 < y+ < 145), a red dot
# for the open squares (145 < y+ < 180)); pixel centres in that copy, whose axes are x 207.5 (D* = 0) to 974.5 (80) and y 57 (p = 0.1) to 763.5 (1e-3).  They replace the interpolated values.
DOTS_CROP = dict(x0=207.5, x1=974.5, y0=57.0, y1=763.5, xmax=80.0, top_exp=-1, decades=2)
MANUAL_D = [("circle", 467.1, 364.5), ("circle", 475.3, 371.6), ("circle", 480.4, 382.5), ("circle", 489.2, 391.6), ("circle", 495.7, 401.2),
            ("square", 363.5, 196.5), ("square", 373.4, 206.3), ("square", 380.5, 220.5), ("square", 384.5, 234.5), ("square", 392.4, 246.6),
            ("square", 699.5, 548.5), ("square", 709.5, 562.5), ("square", 714.6, 574.2), ("square", 717.5, 586.5), ("square", 723.4, 599.4), ("square", 732.5, 619.5)]


def manual_points():
    """The hand-marked points as (series, D*, p)."""
    c = DOTS_CROP
    return [(name, (x - c["x0"]) / (c["x1"] - c["x0"]) * c["xmax"], 10.0 ** (c["top_exp"] - (y - c["y0"]) / (c["y1"] - c["y0"]) * c["decades"])) for name, x, y in MANUAL_D]


def p_of(y, pn):
    return 10.0 ** (pn["top_exp"] - (y - pn["y0"]) / (pn["y1"] - pn["y0"]) * pn["decades"])


def marker_grid(xs, lo=6.0, hi=9.5):
    """The markers sit on a regular grid in x (the bins of the pdf): spacing h and phase from the x of the accepted points, by maximising the length of the mean phase vector."""
    best = (0.0, None, None)
    for h in np.arange(lo, hi, 0.005):
        ph = 2 * np.pi * xs / h
        r = np.hypot(np.cos(ph).mean(), np.sin(ph).mean())
        if r > best[0]:
            best = (r, h, (np.arctan2(np.sin(ph).mean(), np.cos(ph).mean()) / (2 * np.pi)) * h)
    return best[1], best[2], best[0]


def track_two(found, gate=0.35):
    """Follow the two open series (the circle and the square bands) along the grid (used for the diameter panel; in the swirl panel the two series nearly coincide and the mean of the markers found is used).  found[k] is the list of ln p of the accepted open markers at grid position k (0, 1 or 2 values, rarely more).
    Start at the first position with two markers (the upper and the lower series); then at each position the markers are assigned to the series by the nearest predicted value (the last value of
    the series plus its last slope): two markers go to the two series (the pairing with the smaller total distance), one marker goes to the nearer series if it is within `gate` of its prediction
    and the other series is missing there.  Returns two arrays of ln p (nan where a series is missing)."""
    n = len(found)
    tr = np.full((2, n), np.nan)
    k0 = next(k for k in range(n) if len(found[k]) >= 2)
    v = sorted(found[k0])[-2:]
    tr[0, k0], tr[1, k0] = v[1], v[0]
    def predict(t, k):
        idx = np.nonzero(~np.isnan(tr[t, :k]))[0]
        if len(idx) == 0:
            return np.nan
        if len(idx) >= 2 and k - idx[-1] <= 3:
            slope = (tr[t, idx[-1]] - tr[t, idx[-2]]) / (idx[-1] - idx[-2])
            return tr[t, idx[-1]] + slope * (k - idx[-1])
        return tr[t, idx[-1]]
    for k in list(range(k0 + 1, n)) + []:
        c = list(found[k])
        pa, pb = predict(0, k), predict(1, k)
        if len(c) == 0:
            continue
        if len(c) >= 2:
            c = sorted(c)
            lo, hi = c[0], c[-1]
            d_keep = abs(hi - pa) + abs(lo - pb)
            d_swap = abs(lo - pa) + abs(hi - pb)
            if d_keep <= d_swap:
                tr[0, k], tr[1, k] = hi, lo
            else:
                tr[0, k], tr[1, k] = lo, hi
        else:
            da, db = abs(c[0] - pa), abs(c[0] - pb)
            if min(da, db) <= gate:
                tr[0 if da <= db else 1, k] = c[0]
    return tr


def grid_curve(pn, im, pts, win=2.5, ywin=6, tracking=True, gate=0.35, manual=()):
    """The open-symbol curve on the marker grid, with the two open series followed separately.  At each grid abscissa the accepted open markers within +-win px are assigned to the two series
    (track_two); where a series has no marker (it runs behind a black marker) its ln p is interpolated between the found points of that series, and the black marker near the expected position
    (+-ywin px in y, +-win px in x) refines it: the mean y of the dark pixels there.  P is the mean of the two series.  Returns x_k (data units), P, the two series, flags (0 found, 1 interpolated,
    2 refined on black pixels; per series), the grid spacing and the phase strength."""
    dark = im < 128
    h, phase, strength = marker_grid(pts[:, 0])
    ks = np.arange(int(np.ceil((pts[:, 0].min() - phase) / h)), int(np.floor((pts[:, 0].max() - phase) / h)) + 1)
    xk = phase + ks * h
    lnp = np.log(p_of(pts[:, 1], pn))
    found = [list(lnp[np.abs(pts[:, 0] - x) <= win]) for x in xk]
    if tracking:
        tr = track_two(found, gate)
    else:                                                       # one curve: the mean of the markers found at each grid position (both series together)
        m = np.array([np.mean(f) if len(f) else np.nan for f in found])
        tr = np.vstack([m, m])
    flag = np.zeros((2, len(xk)), int)
    xdata = (xk - pn["x0"]) / (pn["x1"] - pn["x0"]) * pn["xmax"]
    for name, dx, dp in manual:                                    # hand-marked points: put each on the series (upper or lower) whose value there is nearer, and on the nearest grid position
        k = int(np.argmin(np.abs(xdata - dx)))
        if abs(xdata[k] - dx) > 0.6 * h / (pn["x1"] - pn["x0"]) * pn["xmax"]:
            continue
        est = []
        for t in range(2):
            okt = ~np.isnan(tr[t])
            est.append(np.interp(xk[k], xk[okt], tr[t][okt]))
        t = int(np.argmin([abs(np.log(dp) - e) for e in est]))
        tr[t, k] = np.log(dp)
        flag[t, k] = 3
    for t in range(2):
        ok = ~np.isnan(tr[t])
        tr[t] = np.interp(xk, xk[ok], tr[t][ok])
        for i in np.nonzero(~ok)[0]:
            flag[t, i] = 1
            y_exp = pn["y0"] + (pn["top_exp"] - tr[t, i] / np.log(10)) / pn["decades"] * (pn["y1"] - pn["y0"])
            x0, x1, y0, y1 = int(round(xk[i] - win)), int(round(xk[i] + win)) + 1, int(round(y_exp - ywin)), int(round(y_exp + ywin)) + 1
            ys = np.nonzero(dark[y0:y1, x0:x1])[0] + y0
            if len(ys) >= 3:
                tr[t, i] = np.log(p_of(ys.mean(), pn))
                flag[t, i] = 2
    P = 0.5 * (np.exp(tr[0]) + np.exp(tr[1]))
    return (xk - pn["x0"]) / (pn["x1"] - pn["x0"]) * pn["xmax"], P, np.exp(tr), flag, h, strength


def groups(pts, tol=3.5):
    out, cur = [], [pts[0]]
    for q in pts[1:]:
        if q[0] - np.mean([c[0] for c in cur]) <= tol:
            cur.append(q)
        else:
            out.append(np.array(cur))
            cur = [q]
    out.append(np.array(cur))
    return out


def main():
    fig, axes = plt.subplots(1, 2, figsize=(14, 7))
    table = {}
    for ax, (key, pn) in zip(axes, PANELS.items()):
        im, pts_all = open_points(pn)
        good = reject_outliers(im, pts_all, pn)
        pts = pts_all[good]
        print("%s: %d candidate holes, %d rejected as outliers" % (key, len(pts_all), int((~good).sum())))
        xg, pg, series, flag, h, strength = grid_curve(pn, im, pts, tracking=True, gate=0.18 if key == "D" else 0.35, manual=manual_points() if key == "D" else ())        # the two open series are followed separately in both panels (a wider gate for the swirl panel, where the curves are steeper in ln p)
        x, p, top, bot, n = xg, pg, series.max(axis=0), series.min(axis=0), flag.max(axis=0)
        table[key] = (x, top, bot, p, n)
        print("%s: grid spacing %.2f px (phase strength %.2f), %d grid points; per series: found %d and %d, interpolated and refined on black pixels %d and %d, interpolated only %d and %d; hand-marked %d and %d" % (
            key, h, strength, len(xg), int((flag[0] == 0).sum()), int((flag[1] == 0).sum()), int((flag[0] == 2).sum()), int((flag[1] == 2).sum()), int((flag[0] == 1).sum()), int((flag[1] == 1).sum()), int((flag[0] == 3).sum()), int((flag[1] == 3).sum())))
        ax.imshow(im, cmap="gray")
        ax.scatter(pts[:, 0], pts[:, 1], s=18, facecolors="none", edgecolors="lime", lw=0.8)
        ax.scatter(pts_all[~good][:, 0], pts_all[~good][:, 1], s=26, facecolors="none", edgecolors="r", lw=1.0)
        px = pn["x0"] + x / pn["xmax"] * (pn["x1"] - pn["x0"])
        py_of = lambda v: pn["y0"] + (pn["top_exp"] - np.log10(v)) / pn["decades"] * (pn["y1"] - pn["y0"])
        for t, colour in ((0, "tab:green"), (1, "tab:cyan")):
            ax.plot(px, py_of(series[t]), c=colour, lw=0.8)
            ax.scatter(px[flag[t] == 0], py_of(series[t])[flag[t] == 0], s=9, c=colour)
            ax.scatter(px[flag[t] == 2], py_of(series[t])[flag[t] == 2], s=16, c="tab:blue", marker="s")
            ax.scatter(px[flag[t] == 1], py_of(series[t])[flag[t] == 1], s=16, c="tab:orange", marker="^")
            ax.scatter(px[flag[t] == 3], py_of(series[t])[flag[t] == 3], s=40, c="magenta", marker="*")
        ax.plot(px, py_of(p), c="magenta", lw=1.0, ls="--")
        ax.set_xlim(pn["x0"] - 20, pn["x1"] + 20)
        ax.set_ylim(pn["y1"] + 20, pn["y0"] - 20)
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "das2006_open_overlay.png"), dpi=110)
    plt.close(fig)
    nmax = max(len(table["D"][0]), len(table["u"][0]))
    pad = lambda a: np.pad(a.astype(float), (0, nmax - len(a)), constant_values=np.nan)
    np.savetxt(os.path.join(HERE, "das2006_open_pdfs.csv"), np.column_stack([pad(table["D"][0]), pad(table["D"][1]), pad(table["D"][2]), pad(table["D"][3]),
                                                                          pad(table["u"][0]), pad(table["u"][1]), pad(table["u"][2]), pad(table["u"][3])]),
               delimiter=",", header="D_star,pD_top,pD_bottom,pD,u_star,pv_top,pv_bottom,pv", comments="")


if __name__ == "__main__":
    main()
