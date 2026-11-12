"""chord_kernel.py  v01  Table and kernel of the chord model (see chord_model.py for the geometry).

table(): for a grid of tilt alpha in [0, 90 deg], rotation phi in [0, pi) and impact parameter b in [0, B_MAX] (units of the Gaussian width R of
the tube) the spacing of the two extrema of the signal in units of 2 r_max (= the ratio R_m/R, Belin's R_m = spacing/3.17) and the peak
amplitude as a fraction of a central crossing at alpha = 0, phi = 90 deg.  The extremum positions are refined by a parabola through the
three grid points around each extremum.  Cached in chord_table.npz.

kernel(alpha_max, f): the smoothed probability density g(rho) of the ratio rho = R_m/R for identical tubes, over the events whose tilt is
at most alpha_max and whose amplitude is at least f (the fraction of the central-crossing amplitude).  Event density: b uniform, tilt
density cos(alpha) (isotropic orientation) times the encounter rate cos(alpha), rotation phi uniform.
Usage: python chord_kernel.py      (builds the table)
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chord_model as cm

CACHE = os.path.join(HERE, "chord_table.npz")
ALPHAS = np.radians(np.linspace(0, 90, 19))          # 5 degree steps
PHIS = np.linspace(0, math.pi, 17)[:-1]
BS = np.arange(0.0, 12.0001, 0.05)


def _extremum(S, grid):
    """Parabolic refinement of the positions of the maximum and the minimum of each row of S."""
    pos = []
    for sign in (1, -1):
        v = sign * S
        i = np.clip(np.argmax(v, axis=1), 1, S.shape[1] - 2)
        y0, y1, y2 = v[np.arange(len(v)), i - 1], v[np.arange(len(v)), i], v[np.arange(len(v)), i + 1]
        den = y0 - 2 * y1 + y2
        d = np.where(np.abs(den) > 1e-15, 0.5 * (y0 - y2) / den, 0.0)
        pos.append(grid[i] + np.clip(d, -1, 1) * (grid[1] - grid[0]))
    return pos


def build():
    A0 = cm.reference_amplitude()
    n_a, n_p, n_b = len(ALPHAS), len(PHIS), len(BS)
    ratio = np.zeros((n_a, n_p, n_b))
    amp = np.zeros((n_a, n_p, n_b))
    for ia, al in enumerate(ALPHAS):
        for ip, ph in enumerate(PHIS):
            S = cm.signal(np.full(n_b, al), np.full(n_b, ph), BS)
            xmax, xmin = _extremum(S, cm.S_GRID)
            ratio[ia, ip] = np.abs(xmax - xmin) / cm.SPACING0
            amp[ia, ip] = np.max(np.abs(S), axis=1) / A0
    np.savez(CACHE, ratio=ratio, amp=amp)
    return ratio, amp


def table():
    if os.path.exists(CACHE):
        z = np.load(CACHE)
        return z["ratio"], z["amp"]
    return build()


def kernel(alpha_max_deg, f, grid=None, smooth=0.04):
    """Smoothed density of rho = R_m/R on grid (default 0 ... 12 in steps of 0.01) for the events with tilt <= alpha_max and amplitude >= f."""
    ratio, amp = table()
    if grid is None:
        grid = np.arange(0.0, 12.0, 0.01)
    ok = (ALPHAS[:, None, None] <= math.radians(alpha_max_deg) + 1e-9) & (amp >= f)
    w = np.broadcast_to((np.cos(ALPHAS) ** 2)[:, None, None], ratio.shape) * ok
    h, edges = np.histogram(ratio.ravel(), bins=np.append(grid, grid[-1] + 0.01), weights=w.ravel())
    if h.sum() <= 0:
        return grid, np.zeros_like(grid)
    k = np.exp(-0.5 * (np.arange(-4 * int(smooth / 0.01), 4 * int(smooth / 0.01) + 1) * 0.01 / smooth) ** 2)
    h = np.convolve(h, k / k.sum(), mode="same")
    return grid, h / (h.sum() * 0.01)


if __name__ == "__main__":
    r, a = build()
    print("table built", r.shape)
