"""digitise_belin_fig6.py  v01  Digitise Fig. 6 of Belin et al. (1996): the pdf of the worm Reynolds number Re_f / Re_lambda^(1/2), seven marker types (one for each Re_lambda).

Page 9 of ../Belin (1996).pdf is rendered at 6x.  The frame of the plot is found (x 0 ... 40, p 0 ... 0.1 are its left/right and bottom/top edges) and removed with the tick marks.
Markers:
    filled (circle, up triangle, down triangle)   binary opening removes the thin strokes; what is left are the filled blobs; a blob that is several markers merged is split into
                                                  round(area / area of one marker) pieces by k-means; centre = centre of the bounding box (the centroid for a merged piece)
    hollow (circle, square)                       holes filled, filled blobs taken away, opening; circle or square from the fill ratio of the bounding box
    crosses (+, x)                                what is left after taking away the blobs is matched with a '+' and an 'x' template (correlation, non-maximum suppression)
Output: belin_fig6_digitised.csv (type, Re_f/Re_lambda^0.5, p) and belin_fig6_overlay.png (the found points on the image).  A marker hidden under another one is not found: the
count per type is printed so that it can be compared with the figure.
Usage: python digitise_belin_fig6.py

Versions  M01 m01.v01 (2026-11-12): first version.
"""
import csv
import os

import numpy as np
import pypdfium2 as pdfium
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy.cluster.vq import kmeans2
from scipy.signal import fftconvolve

HERE = os.path.dirname(os.path.abspath(__file__))
SCALE = 6
FRAME = dict(left=1172.5, right=2193.5, top=376.0, bottom=1133.5)       # pixels of the page rendered at SCALE (found from the long dark lines)
CROP = (900, 250, 2500, 1300)                                              # x0, y0, x1, y1 of the crop that is shown
RADIUS_OPEN = 6


def disk(r):
    y, x = np.ogrid[-r:r + 1, -r:r + 1]
    return (x * x + y * y) <= r * r


def to_data(x_pix, y_pix):
    return (40.0 * (x_pix - FRAME["left"]) / (FRAME["right"] - FRAME["left"]), 0.1 * (FRAME["bottom"] - y_pix) / (FRAME["bottom"] - FRAME["top"]))


def split_blobs(mask, one_area):
    """Centres of the blobs of a mask; a merged blob is divided by k-means into round(area / one_area) pieces."""
    lab, n = ndi.label(mask)
    out = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        pieces = max(1, int(round(len(xs) / one_area)))
        if pieces == 1:
            out.append(((xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2, len(xs), (xs.max() - xs.min() + 1), (ys.max() - ys.min() + 1), ys.mean(), False))
        else:
            pts = np.column_stack([xs, ys]).astype(float)
            centres, labels = kmeans2(pts, pieces, minit="++", seed=1)
            for k in range(pieces):
                if np.any(labels == k):
                    out.append((centres[k][0], centres[k][1], int((labels == k).sum()), 0, 0, centres[k][1], True))
    return out


def cross_template(kind, size=21, width=3):
    t = np.zeros((size, size))
    c = size // 2
    if kind == "+":
        t[c - width // 2:c + width // 2 + 1, :] = 1
        t[:, c - width // 2:c + width // 2 + 1] = 1
    else:
        for i in range(size):
            t[max(0, i - width // 2):i + width // 2 + 1, i] = 1
            t[max(0, size - 1 - i - width // 2):size - i + width // 2, i] = 1
    return t


def peaks(score, threshold, distance):
    found = []
    work = score.copy()
    while True:
        k = np.argmax(work)
        y, x = np.unravel_index(k, work.shape)
        if work[y, x] < threshold:
            break
        found.append((x, y, work[y, x]))
        work[max(0, y - distance):y + distance + 1, max(0, x - distance):x + distance + 1] = 0
    return found


def main():
    page = pdfium.PdfDocument(os.path.join(HERE, "..", "Belin (1996).pdf"))[8].render(scale=SCALE).to_pil().convert("L")
    a = np.array(page)
    mask = a < 140
    for r in (FRAME["top"], FRAME["bottom"]):                                # frame lines away (a margin of 4 pixels)
        mask[int(r) - 4:int(r) + 5, :] = False
    for c in (FRAME["left"], FRAME["right"]):
        mask[:, int(c) - 4:int(c) + 5] = False
    region = np.zeros_like(mask)
    region[int(FRAME["top"]) - 30:int(FRAME["bottom"]) + 30, int(FRAME["left"]) - 30:int(FRAME["right"]) + 30] = True
    mask &= region
    # the labels and the caption are outside the region; the ticks are thin and are removed by the opening
    filled = ndi.binary_opening(mask, structure=disk(RADIUS_OPEN))
    solid = split_blobs(filled, one_area=330)
    filled_dilated = ndi.binary_dilation(filled, structure=disk(3))
    holes = ndi.binary_fill_holes(mask) & ~filled_dilated
    hollow_mask = ndi.binary_opening(holes, structure=disk(RADIUS_OPEN))
    hollow = split_blobs(hollow_mask, one_area=330)
    residue = mask & ~ndi.binary_dilation(filled | hollow_mask, structure=disk(5))
    residue = ndi.binary_opening(residue, structure=np.ones((2, 2), bool))
    found = []
    for x, y, area, w, h, ycen, merged in solid:
        if merged:
            kind = "filled (merged)"
        else:
            kind = "filled circle" if abs(w - h) < 4 and area > 0.7 * w * h else ("up triangle" if ycen > y else "down triangle")
        found.append((kind, x, y))
    for x, y, area, w, h, ycen, merged in hollow:
        kind = "hollow (merged)" if merged else ("square" if area > 0.9 * 0 + 0 and False else "hollow")
        found.append((kind, x, y))
    for kind in ("+", "x"):
        t = cross_template(kind)
        score = fftconvolve(residue.astype(float), t[::-1, ::-1], mode="same")
        for x, y, s in peaks(score, 0.62 * t.sum(), 11):
            if region[int(y), int(x)]:
                found.append((kind, x, y))
    rows = []
    for kind, x, y in found:
        xd, pd = to_data(x, y)
        if -1.5 <= xd <= 41.5 and -0.01 <= pd <= 0.101:
            rows.append((kind, xd, pd, x, y))
    with open(os.path.join(HERE, "belin_fig6_digitised.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["marker", "Re_f_over_sqrt_Re_lambda", "p"])
        for kind, xd, pd, x, y in sorted(rows, key=lambda r: r[1]):
            w.writerow([kind, "%.3f" % xd, "%.5f" % pd])
    counts = {}
    for r in rows:
        counts[r[0]] = counts.get(r[0], 0) + 1
    print("markers found:", counts, " total", len(rows))
    img = page.convert("RGB").crop(CROP)
    d = ImageDraw.Draw(img)
    colours = {"filled circle": (220, 0, 0), "up triangle": (0, 150, 0), "down triangle": (0, 90, 220), "filled (merged)": (200, 0, 200), "hollow": (255, 130, 0),
               "hollow (merged)": (255, 130, 0), "+": (0, 170, 170), "x": (150, 90, 0)}
    for kind, xd, pd, x, y in rows:
        cx, cy = x - CROP[0], y - CROP[1]
        d.ellipse([cx - 16, cy - 16, cx + 16, cy + 16], outline=colours.get(kind, (0, 0, 0)), width=3)
    img.save(os.path.join(HERE, "belin_fig6_overlay.png"))


if __name__ == "__main__":
    main()
