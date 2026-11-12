"""chord_model.py  v01  What a straight probe path reads from a Burgers tube: extrema spacing, amplitude and the selected chord distribution.

Tube: straight axis through the origin with unit direction a, Gaussian vorticity omega = omega0 exp(-rho^2/2R^2) (R = 1), azimuthal swirl
v_theta(rho) = omega0 R^2/rho (1 - exp(-rho^2/2R^2)), peak at r_max = sqrt(2x) R = 1.585 R (x = 1.2564).
Probe path: the line p(s) = s e_x + b n, with e_x the path direction (frozen flow), n = (e_x x a)/|e_x x a| the common perpendicular of
path and axis and b the impact parameter (the distance between the two lines).  Velocity at p:  v = v_theta(rho)/rho * (a x p),
rho^2 = |p|^2 - (p.a)^2 = b^2 + sin(gamma)^2 (s - s_c)^2, gamma the angle between path and axis.  The probe senses the component
along e_y, so the signal is
    S(s) = v_theta(rho(s))/rho(s) * e_y . (a x p(s)).
Orientation: a = (sin alpha, cos alpha cos phi, cos alpha sin phi); alpha is the tilt of the axis out of the plane normal to the
path (alpha = 0: axis normal to the path), phi the rotation about the path direction (phi = 90 deg puts the axis along e_z, the
most sensitive case).  Event density: b uniform, orientation isotropic (density cos(alpha)) times the encounter rate |e_x x a| =
cos(alpha); with --uniform the tilt is taken uniform in alpha instead (density 1).
Selection: an event is kept when max|S| >= f A0, A0 the peak swirl of a central crossing at alpha = 0, phi = 90 deg.
Measured size: Belin reads the spacing of the two extrema of S, Delta s, and R_m = Delta s / 3.17, so a central crossing of a normal
tube gives R_m = R.  Output: mean, median and mode of R_m/R over the kept events, for each tilt limit and amplitude cut.
Usage: python chord_model.py
"""
import math
import sys

import numpy as np

X0 = 1.2564312086261697
RMAX = math.sqrt(2 * X0)
SPACING0 = 2 * RMAX                       # = 3.17 R: spacing of a central crossing
S_GRID = np.linspace(-14, 14, 561)
RNG = np.random.default_rng(1)


def signal(alpha, phi, b):
    """Arrays (N,) of orientation and impact parameter -> signal (N, len(S_GRID))."""
    ca, sa, cphi, sphi = np.cos(alpha), np.sin(alpha), np.cos(phi), np.sin(phi)
    a = np.stack([sa, ca * cphi, ca * sphi], axis=1)                        # (N, 3)
    ex = np.array([1.0, 0.0, 0.0])
    cross = np.cross(np.broadcast_to(ex, a.shape), a)                       # e_x x a, length cos(alpha)
    n = cross / np.linalg.norm(cross, axis=1)[:, None]
    s = S_GRID[None, :, None]
    p = s * ex[None, None, :] + (b[:, None, None] * n[:, None, :])          # (N, M, 3)
    axp = np.cross(np.broadcast_to(a[:, None, :], p.shape), p)             # a x p
    rho2 = np.sum(p * p, axis=2) - np.sum(p * a[:, None, :], axis=2) ** 2
    rho2 = np.maximum(rho2, 1e-12)
    vth_over_rho = (1 - np.exp(-rho2 / 2)) / rho2                           # v_theta/rho with omega0 = R = 1
    return vth_over_rho * axp[:, :, 1]


def reference_amplitude():
    s = signal(np.array([0.0]), np.array([math.pi / 2]), np.array([0.0]))
    return float(np.max(np.abs(s)))


def events(n, alpha_max, f, uniform_tilt, b_max=12.0):
    """n candidate crossings; returns R_m/R of the kept ones."""
    A0 = reference_amplitude()
    out = []
    while sum(len(o) for o in out) < n:
        m = 6000
        if uniform_tilt:
            alpha = RNG.uniform(-alpha_max, alpha_max, m)
            w = np.ones(m)
        else:                                                                # density cos(alpha) on [-alpha_max, alpha_max]
            u = RNG.uniform(-math.sin(alpha_max), math.sin(alpha_max), m)
            alpha = np.arcsin(u)
            w = np.ones(m)
        phi = RNG.uniform(0, 2 * math.pi, m)
        b = RNG.uniform(-b_max, b_max, m)
        keep_rate = np.cos(alpha)                                            # encounter rate |e_x x a|
        thin = RNG.uniform(0, 1, m) < keep_rate * w
        alpha, phi, b = alpha[thin], phi[thin], b[thin]
        S = signal(alpha, phi, b)
        amp = np.max(np.abs(S), axis=1)
        ok = amp >= f * A0
        if not ok.any():
            continue
        S = S[ok]
        spacing = np.abs(S_GRID[np.argmax(S, axis=1)] - S_GRID[np.argmin(S, axis=1)])
        out.append(spacing / SPACING0)
    return np.concatenate(out)[:n]


def summarise(r):
    hist, edges = np.histogram(r, bins=np.linspace(0, 4, 81))
    mode = 0.5 * (edges[np.argmax(hist)] + edges[np.argmax(hist) + 1])
    return float(np.mean(r)), float(np.median(r)), float(mode)


def main():
    uniform_tilt = "--uniform" in sys.argv
    print("tilt weighting: %s; R_m/R = (extrema spacing)/(3.17 R) of the kept events" % ("uniform in alpha" if uniform_tilt else "isotropic"))
    print("Belin's distribution (read from Fig. 5) relative to a true r_max/eta = 5 (R = 3.15): mean 6.0/3.15 = 1.90, median 5.0/3.15 = 1.59, mode 3.5/3.15 = 1.11")
    print("alpha_max  cut f | mean  median  mode")
    for alpha_deg in (0, 45, 90):
        for f in (0.8, 0.5, 0.3, 0.2, 0.1):
            if alpha_deg == 0 and f < 0.3:
                pass
            r = events(8000, math.radians(alpha_deg), f, uniform_tilt)
            m, md, mo = summarise(r)
            print("   %3d      %.1f  | %.2f  %.2f  %.2f" % (alpha_deg, f, m, md, mo))


if __name__ == "__main__":
    main()
