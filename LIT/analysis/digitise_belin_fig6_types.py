"""digitise_belin_fig6_types.py  v01  Belin et al. (1996) Fig. 6: the seven marker types separated (one per Re_lambda: filled circle 359, + 255, x 940, open circle 1342, open square 507, filled down triangle 2313, filled up triangle 718).
Page 9 of ../Belin (1996).pdf at 6x (as digitise_belin_fig6.py).  Each type is found by matched filtering the dark-pixel image with a signed template (+1 on the strokes of the marker, -1 where the marker must be empty:
the inside of a hollow marker, the gaps of a cross), then non-maximum suppression.  Markers hidden under others are missed; the count per type is printed (about 14 are expected for each Re_lambda).
Output: belin_fig6_types.csv (type, Re_lambda, x, p) and belin_fig6_types_overlay.png.
Usage: python digitise_belin_fig6_types.py

Versions  M01 m01.v01 (2026-11-13): first version.
"""
import csv
import os

import numpy as np
import pypdfium2 as pdfium
from PIL import Image, ImageDraw
from scipy.signal import fftconvolve

HERE = os.path.dirname(os.path.abspath(__file__))
SCALE = 6
FRAME = dict(left=1172.5, right=2193.5, top=376.0, bottom=1133.5)
CROP = (900, 250, 2500, 1300)
SIZE = 23                                                                   # marker size in pixels
RE_LAMBDA = {"filled circle": 359, "+": 255, "x": 940, "open circle": 1342, "open square": 507, "down triangle": 2313, "up triangle": 718}
COLOURS = {"filled circle": (220, 0, 0), "+": (0, 160, 160), "x": (150, 90, 0), "open circle": (255, 130, 0), "open square": (200, 0, 200), "down triangle": (0, 90, 220), "up triangle": (0, 150, 0)}


def grid(n):
    c = n // 2
    y, x = np.mgrid[-c:c + 1, -c:c + 1]
    return x, y, c


def template(kind, n=SIZE, t=3):
    """Signed template: +1 on the marker, -1 where it must be empty, 0 elsewhere."""
    x, y, c = grid(n)
    r = np.sqrt(x * x + y * y)
    tpl = np.zeros((n, n))
    if kind == "filled circle":
        tpl[r <= c] = 1
    elif kind == "open circle":
        tpl[(r <= c) & (r >= c - t)] = 1
        tpl[r < c - t - 1] = -1
    elif kind == "open square":
        edge = (np.abs(x) >= c - t) | (np.abs(y) >= c - t)
        tpl[edge] = 1
        tpl[(np.abs(x) < c - t - 1) & (np.abs(y) < c - t - 1)] = -1
    elif kind == "up triangle":                                              # apex up: the half-width grows with y
        tpl[(np.abs(x) <= (y + c) / 2.0) & (y >= -c) & (y <= c)] = 1
    elif kind == "down triangle":
        tpl[(np.abs(x) <= (c - y) / 2.0) & (y >= -c) & (y <= c)] = 1
    elif kind == "+":
        tpl[(np.abs(y) <= t // 2) | (np.abs(x) <= t // 2)] = 1
        tpl[(np.abs(x) > t) & (np.abs(y) > t)] = -0.3
    elif kind == "x":
        tpl[(np.abs(np.abs(x) - np.abs(y)) <= t // 2 + 1)] = 1
        tpl[(np.abs(x) <= 1) | (np.abs(y) <= 1)] = np.where(((np.abs(x) <= 1) | (np.abs(y) <= 1)) & (np.abs(x) + np.abs(y) > 5), -0.3, 1)[(np.abs(x) <= 1) | (np.abs(y) <= 1)]
    return tpl


def peaks(score, threshold, distance):
    found, work = [], score.copy()
    while True:
        k = np.argmax(work)
        y, x = np.unravel_index(k, work.shape)
        if work[y, x] < threshold:
            break
        found.append((x, y, work[y, x]))
        work[max(0, y - distance):y + distance + 1, max(0, x - distance):x + distance + 1] = -1e9
    return found


def main():
    page = pdfium.PdfDocument(os.path.join(HERE, "..", "Belin (1996).pdf"))[8].render(scale=SCALE).to_pil().convert("L")
    a = np.array(page)
    dark = (a < 140).astype(float)
    for r in (FRAME["top"], FRAME["bottom"]):
        dark[int(r) - 4:int(r) + 5, :] = 0
    for c in (FRAME["left"], FRAME["right"]):
        dark[:, int(c) - 4:int(c) + 5] = 0
    region = np.zeros_like(dark, bool)
    region[int(FRAME["top"]) - 30:int(FRAME["bottom"]) + 30, int(FRAME["left"]) - 30:int(FRAME["right"]) + 30] = True
    dark *= region
    found = []
    for kind in RE_LAMBDA:
        tpl = template(kind)
        positive = (tpl > 0).sum()
        score = fftconvolve(dark, tpl[::-1, ::-1], mode="same") / positive
        for x, y, s in peaks(score, 0.80 if kind in ("filled circle", "down triangle", "up triangle") else 0.70, 12):
            if region[int(y), int(x)]:
                found.append((kind, x, y, s))
    # a marker found as two types (overlapping templates): keep the best score within 9 pixels
    found.sort(key=lambda r: -r[3])
    kept = []
    for f in found:
        if all((f[1] - k[1]) ** 2 + (f[2] - k[2]) ** 2 > 81 for k in kept):
            kept.append(f)
    rows = []
    for kind, x, y, s in kept:
        xd = 40.0 * (x - FRAME["left"]) / (FRAME["right"] - FRAME["left"])
        pd = 0.1 * (FRAME["bottom"] - y) / (FRAME["bottom"] - FRAME["top"])
        if -1.5 <= xd <= 41.5 and -0.01 <= pd <= 0.101:
            rows.append((kind, RE_LAMBDA[kind], xd, pd, x, y))
    with open(os.path.join(HERE, "belin_fig6_types.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["marker", "Re_lambda", "Re_f_over_sqrt_Re_lambda", "p"])
        for kind, rl, xd, pd, x, y in sorted(rows, key=lambda r: (r[1], r[2])):
            w.writerow([kind, rl, "%.3f" % xd, "%.5f" % pd])
    counts = {k: sum(1 for r in rows if r[0] == k) for k in RE_LAMBDA}
    print("markers per type:", counts, "total", len(rows))
    img = page.convert("RGB").crop(CROP)
    d = ImageDraw.Draw(img)
    for kind, rl, xd, pd, x, y in rows:
        cx, cy = x - CROP[0], y - CROP[1]
        d.ellipse([cx - 17, cy - 17, cx + 17, cy + 17], outline=COLOURS[kind], width=3)
    img.save(os.path.join(HERE, "belin_fig6_types_overlay.png"))


if __name__ == "__main__":
    main()
