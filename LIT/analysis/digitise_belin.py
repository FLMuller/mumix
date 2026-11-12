"""digitise_belin.py  v01  Read the measured size distribution out of Fig. 5 of Belin et al. (1996) and overlay it on the original image.

belin_fig5.png is the figure as supplied (the clean version).  Calibration from the frame and tick marks: the frame spans columns 110.8
(R/eta = 0) to 513 (R/eta = 20) and rows 353 (p = 0) to 78 (p = 0.25).  The markers of the six Reynolds numbers collapse onto one curve, so
for each 0.5-wide bin of R/eta the median and the quartiles of the y position of all dark pixels inside the frame are taken (the thin full
line of the numerics adds only a few pixels per column to the several tens of the marker cloud).  Output: belin_fig5_digitised.csv and
belin_overlay.png (the original image in data coordinates with the digitised curve on top, to check it by eye).
The thin full line of the numerics (Belin's DNS curve seen through the probe) is read as well: in each column the dark pixel farthest from the
marker cloud, where the line separates from the cloud (more than 0.012 away), interpolated through the stretches inside the cloud; output
belin_fig5_numerics.csv, overlaid in belin_overlay.png as a blue curve.
Usage: python digitise_belin.py
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.image as mi
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
X0, X1 = 110.8, 513.0           # pixel columns of R/eta = 0 and 20
Y0, Y1 = 353.0, 78.0            # pixel rows of p = 0 and 0.25


def px_to_x(c):
    return (np.asarray(c) - X0) / (X1 - X0) * 20.0


def px_to_y(r):
    return (Y0 - np.asarray(r)) / (Y0 - Y1) * 0.25


def digitise(bin_width=0.5):
    img = mi.imread(os.path.join(HERE, "belin_fig5.png"))
    g = img[..., :3].mean(axis=2)
    dark = (g < 0.5) & (img[..., 3] > 0.5 if img.shape[2] == 4 else True)
    rows, cols = np.nonzero(dark)
    keep = (cols > X0 + 4) & (cols < X1 - 4) & (rows > Y1 + 4) & (rows < Y0 - 3)       # inside the frame, clear of the tick marks
    rows, cols = rows[keep], cols[keep]
    x, y = px_to_x(cols), px_to_y(rows)
    centres = np.arange(0.75, 20.0, bin_width)
    out = []
    for c in centres:
        m = np.abs(x - c) <= bin_width / 2
        if m.sum() >= 6:
            out.append((c, float(np.median(y[m])), float(np.percentile(y[m], 25)), float(np.percentile(y[m], 75))))
    return np.array(out), img


def digitise_line(d, img, bin_width=0.25, min_gap=0.012):
    g = img[..., :3].mean(axis=2)
    dark = (g < 0.5) & (img[..., 3] > 0.5 if img.shape[2] == 4 else True)
    rows, cols = np.nonzero(dark)
    keep = (cols > X0 + 4) & (cols < X1 - 4) & (rows > Y1 + 4) & (rows < Y0 - 3)
    x, y = px_to_x(cols[keep]), px_to_y(rows[keep])
    cloud = np.interp(np.arange(0.5, 20, bin_width), d[:, 0], d[:, 1])
    xs, ys = [], []
    for c, yc in zip(np.arange(0.5, 20, bin_width), cloud):
        m = np.abs(x - c) <= bin_width / 2
        if m.sum() == 0:
            continue
        far = y[m][np.argmax(np.abs(y[m] - yc))]
        if abs(far - yc) > min_gap:
            xs.append(c)
            ys.append(far)
    xs, ys = np.array(xs), np.array(ys)
    good = (ys < 0.215) & ~((ys < 0.006) & (xs < 14)) & (xs < 14)           # frame ticks and the right-hand edge are not the line
    return xs[good], ys[good]


def main():
    d, img = digitise()
    np.savetxt(os.path.join(HERE, "belin_fig5_digitised.csv"), d, delimiter=",", header="R_over_eta,p_median,p_q25,p_q75", comments="")
    H, W = img.shape[:2]
    extent = [px_to_x(0), px_to_x(W), float(px_to_y(H)), float(px_to_y(0))]
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.imshow(img, extent=extent, aspect="auto", origin="upper")
    d = d[d[:, 0] < 19.0]
    ax.fill_between(d[:, 0], d[:, 2], d[:, 3], color="r", alpha=0.25, label="quartiles of the pixels")
    ax.plot(d[:, 0], d[:, 1], "r.-", lw=1, ms=6, label="digitised (median)")
    lx, ly = digitise_line(d, img)
    np.savetxt(os.path.join(HERE, "belin_fig5_numerics.csv"), np.column_stack([lx, ly]), delimiter=",", header="R_over_eta,p", comments="")
    ax.plot(lx, ly, "b.", ms=5, label="numerics line, where it separates from the markers")
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 0.25)
    ax.legend()
    ax.set_title("Belin et al. (1996) Fig. 5 with the digitised curve overlaid (data coordinates)")
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_overlay.png"), dpi=110)
    print("points:", len(d), " peak %.3f at R/eta = %.2f" % (d[:, 1].max(), d[np.argmax(d[:, 1]), 0]))
    print("integral %.3f" % np.trapezoid(d[:, 1], d[:, 0]))


if __name__ == "__main__":
    main()
