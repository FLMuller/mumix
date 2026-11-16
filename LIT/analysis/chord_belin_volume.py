"""chord_belin_volume.py  v01  The chord model by brute force: a volume of straight tubes at volume fraction V_f, a wire that sweeps a straight line through it, and Belin's cut and reading applied to what it meets.
Tubes   r_max / eta from one lognormal (--rmedian, --sharp), x = Re_f / Re_lambda^(1/2) from a second (Belin's Fig. 6 lognormal, median x --median, ln-width x --narrow), independent;
        Re_c = r_max U_max / nu = 1.585 x Re_lambda^(1/2), U_max = Re_c / r_max.  Every tube has the length L (--length, 42 eta), a random centre and an isotropic axis direction.
Volume  tube number density n = V_f / (pi <r_max^2> L); the wire is the x axis.  A box of cross-section (2H)^2, H = L/2 + the reach of the tubes of the input pdfs (all but 1 in 10^4) holds the tubes that can reach the wire; the number of tubes thrown
        M corresponds to the box length X = M / (n (2H)^2), so the event rate follows (events per cm of path).  Nothing is weighted by hand: a tube is met in proportion to its width, length and orientation because
        the geometry does it.  A tube is a candidate when the point of its axis nearest to the wire lies on the tube (|t*| <= L/2: end hits are ignored, L >> R) and its distance b is within reach(): the largest distance at which the gradient of a line vortex of that circulation can still pass the cut (nothing else is dropped).
Probe   the wire is normal to the flow (along y, flow along x) and is cooled by U_eff = sqrt((U + v_x)^2 + v_z^2 + 0.2^2 v_y^2), v the swirl velocity of the tube, U = 0.588 Omega R the mean flow (Table I chain); the signal is U_eff - U;
        geometry of chord_model with the impact parameter b / R, isotropic axis; an event is kept when max |dS/ds| >= 5 U_eta / (sqrt 15 eta); the reading is made in a window of +-2 r_max
        around the steepest point (opposite-sign extrema needed); r_max read = half the spacing, amplitude = half the swing.  Tubes are thrown in batches until --target events are kept and read (50000).
Check   chord_belin_volume_check.png: b / R and the axis position t* / L of the candidates and of the events kept.  The share of tubes that can be thrown away without ever being read is printed.
Limits  tubes do not overlap or interact (V_f = 20 %: the signals of two tubes in one window would add); no wire filter; time = length / U exactly (the pattern is frozen).
Usage:  python chord_belin_volume.py [--target 50000] [--length 100] [--vf 0.2] [--rmedian 4.44 --sharp 0.55 --median 1.4384 --narrow 0.8436]    writes chord_belin_volume<tag>.png, chord_belin_volume_check<tag>.png

Versions  M01 m01.v01 (2026-11-13): first version.
          m01.v02 (2026-11-13): the wire response is the cooling speed U_eff (normal to the flow, yaw coefficient 0.2) of the whole swirl velocity plus the mean flow U, not one signed component; L = 42 eta.
"""
import argparse
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chord_model as cm                  # noqa: E402
import chord_population as cp             # noqa: E402
import belin_gamma_pdf as bg              # noqa: E402
import belin_umax_vs_relambda as bu       # noqa: E402

RATIO = cp.RATIO
GMAX = cp.GMAX
SIGMA_GRADIENT = 1.0 / math.sqrt(15)
CUT = 5.0
KYAW = 0.2                                                           # cooling by the velocity component along the wire, relative to the normal ones (Jorgensen)
DISK_RADIUS = 10.0                                                   # cm, cell 2 of Belin et al.
MEAN_FRACTION = 0.588                                                # mean local velocity U = 0.588 Omega R (Table I chain)
WINDOW = 2.0                                                         # half-width of the reading window in r_max
GRID = np.linspace(-60.0, 60.0, 1201)                                # path coordinate s / R of the signal (far passes need a long stretch)
STEP = float(GRID[1] - GRID[0])


def signal(alpha, phi, b):
    """The unit velocity vector (N, M, 3) of a Burgers tube along the path, on the long grid GRID: the maths of chord_model.signal (path p = s e_x + b n, tube axis a), but the whole vector v_theta/rho (a x p) is returned, not only
    its e_y component, because the wire is cooled by all of it; b in R, flow along e_x."""
    ca, sa = np.cos(alpha), np.sin(alpha)
    a = np.stack([sa, ca * np.cos(phi), ca * np.sin(phi)], axis=1)
    ex = np.array([1.0, 0.0, 0.0])
    cross = np.cross(np.broadcast_to(ex, a.shape), a)
    n = cross / np.linalg.norm(cross, axis=1)[:, None]
    p = GRID[None, :, None] * ex[None, None, :] + b[:, None, None] * n[:, None, :]
    axp = np.cross(np.broadcast_to(a[:, None, :], p.shape), p)
    rho2 = np.maximum(np.sum(p * p, axis=2) - np.sum(p * a[:, None, :], axis=2) ** 2, 1e-12)
    return ((1 - np.exp(-rho2 / 2)) / rho2)[:, :, None] * axp


def reach(r, umax):
    """Largest distance (eta) at which a tube can still pass the cut: the velocity gradient of a line vortex of circulation Gamma = 8.784 r_max U_max is at most Gamma / (2 pi b^2) outside the core,
    so b <= sqrt(Gamma / (2 pi G_cut)), G_cut = 5 U_eta / (sqrt 15 eta); never less than 2 R (the core).  A tube further away than this cannot be detected whatever its orientation."""
    return np.maximum(np.sqrt(8.784 * r * umax / (2 * math.pi * CUT * SIGMA_GRADIENT)), 2.0 * r / RATIO)


def lognormal(rng, n, median, width):
    return np.exp(math.log(median) + width * rng.standard_normal(n))


def read_signals(alpha, phi, b_over_R, umax, width, U):
    """The wire (normal to the flow e_x, along e_y) is cooled by U_eff = sqrt((U + v_x)^2 + v_z^2 + KYAW^2 v_y^2), v the swirl velocity of the tube (U_eta), U the mean flow (U_eta); the signal is U_eff - U.
    Returns kept (gradient cut), readable, r_max read (eta), amplitude read (U_eta, half the swing); b is in R."""
    m = len(alpha)
    kept, spacing, amp, readable = np.zeros(m, bool), np.zeros(m), np.zeros(m), np.zeros(m, bool)
    for start in range(0, m, 1000):
        sl = slice(start, start + 1000)
        v = signal(alpha[sl], phi[sl], b_over_R[sl]) * (umax[sl] / GMAX)[:, None, None]
        S = np.sqrt((U + v[:, :, 0]) ** 2 + v[:, :, 2] ** 2 + (KYAW * v[:, :, 1]) ** 2) - U
        diff = np.abs(np.diff(S, axis=1))
        kept[sl] = np.max(diff, axis=1) / STEP / width[sl] >= CUT * SIGMA_GRADIENT
        centre = GRID[np.argmax(diff, axis=1)] + 0.5 * STEP
        inside = np.abs(GRID[None, :] - centre[:, None]) <= WINDOW * RATIO
        i_hi, i_lo = np.argmax(np.where(inside, S, -np.inf), axis=1), np.argmin(np.where(inside, S, np.inf), axis=1)
        s_hi, s_lo = S[np.arange(len(i_hi)), i_hi], S[np.arange(len(i_lo)), i_lo]
        readable[sl] = (s_hi > 0) & (s_lo < 0)
        spacing[sl] = np.abs(GRID[i_hi] - GRID[i_lo]) * width[sl]
        amp[sl] = 0.5 * (s_hi - s_lo)
    return kept, readable, spacing / 2, amp


def simulate(Rl, args, mu, s, seed):
    """Throw tubes in batches until args.target events are kept and read; returns the arrays of the candidates, the kept and the read, and the counts of the volume."""
    rng = np.random.default_rng(seed)
    L = args.length
    c = bu.chain_at(Rl)
    U = MEAN_FRACTION * c["Re"] * c["nu"] / DISK_RADIUS / c["U_eta"]                     # mean local velocity in U_eta (U = 0.588 Omega R, Omega R = Re nu / R_disk)
    probe = rng.standard_normal((2, 2000000))                                       # reach of the tubes of the input pdfs: H holds all but 1 in 10^4
    rp = args.rmedian * np.exp(args.sharp * probe[0])
    H = L / 2 + float(np.percentile(reach(rp, 1.585 * math.sqrt(Rl) * np.exp(mu + s * probe[1]) / rp), 99.99))
    density = args.vf / (math.pi * args.rmedian ** 2 * math.exp(2 * args.sharp ** 2) * L)        # tubes / eta^3: V_f / (pi <r_max^2> L)
    thrown = 0
    cand = dict(r=[], rc=[], umax=[], b=[], t=[], kept=[], read=[], r_read=[], amp=[])
    n_read = 0
    while n_read < args.target:
        m = 400000
        r = lognormal(rng, m, args.rmedian, args.sharp)
        x = lognormal(rng, m, math.exp(mu), s)
        Re_c = 1.585 * x * math.sqrt(Rl)
        cy, cz = rng.uniform(-H, H, (2, m))
        sa = rng.uniform(-1, 1, m)                                                  # isotropic direction: the x component uniform in (-1, 1), the rest uniform in the angle
        ph = rng.uniform(0, 2 * math.pi, m)
        ca = np.sqrt(1 - sa ** 2)
        ay, az = ca * np.cos(ph), ca * np.sin(ph)
        norm = np.maximum(ca, 1e-12)
        t_star = -(cy * ay + cz * az) / np.maximum(ay ** 2 + az ** 2, 1e-12)        # axis point nearest to the wire (the x axis)
        b = (-cy * az + cz * ay) / norm                                              # signed distance of the two lines, eta (along n = e_x x a / |e_x x a|)
        width = r / RATIO
        ok = (np.abs(t_star) <= L / 2) & (np.abs(b) <= reach(r, Re_c / r))             # the only tubes dropped: the axis point nearest the wire is off the tube, or the tube is too far to pass the cut
        thrown += m
        idx = np.nonzero(ok)[0]
        alpha, phi = np.arcsin(sa[idx]), ph[idx]
        umax = Re_c[idx] / r[idx]
        kept, readable, r_read, amp = read_signals(alpha, phi, -b[idx] / width[idx], umax, width[idx], U)
        cand["r"].append(r[idx]); cand["rc"].append(Re_c[idx]); cand["umax"].append(umax); cand["b"].append(np.abs(b[idx]) / width[idx]); cand["t"].append(t_star[idx] / L)
        cand["kept"].append(kept); cand["read"].append(kept & readable); cand["r_read"].append(r_read); cand["amp"].append(amp)
        n_read += int((kept & readable).sum())
    out = {k: np.concatenate(v) for k, v in cand.items()}
    out["pop_r"] = lognormal(rng, 200000, args.rmedian, args.sharp)
    out["thrown"], out["density"], out["H"], out["U"] = thrown, density, H, U
    volume = thrown / density
    out["X"] = volume / (2 * H) ** 2                                                  # length of the box, eta: the wire path through the thrown volume
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=50000)
    ap.add_argument("--length", type=float, default=42.0, help="tube length L / eta")
    ap.add_argument("--vf", type=float, default=0.2, help="volume fraction of the tubes (core r_max)")
    ap.add_argument("--rmedian", type=float, default=4.44)
    ap.add_argument("--sharp", type=float, default=0.55)
    ap.add_argument("--median", type=float, default=1.4384)
    ap.add_argument("--narrow", type=float, default=0.8436)
    ap.add_argument("--tag", default="", help="suffix of the two output file names")
    args = ap.parse_args()
    mu0, s0, _ = bg.lognormal_fit()
    mu, s = mu0 + math.log(args.median), s0 * args.narrow
    print("x lognormal: Belin median %.2f ln-width %.3f -> used median %.2f ln-width %.3f; r_max median %.2f eta ln-width %.2f; L %.0f eta, V_f %.2f" % (math.exp(mu0), s0, math.exp(mu), s, args.rmedian, args.sharp, args.length, args.vf))
    d5 = np.loadtxt(os.path.join(HERE, "belin_fig5_digitised.csv"), delimiter=",", skiprows=1)
    xs, ps = bg.raw_points()
    fig, ax = plt.subplots(2, 3, figsize=(17, 13))
    figc, axc = plt.subplots(2, 2, figsize=(12, 9))
    for row, (Rl, event) in enumerate(((659, 27.5), (2850, 72.5))):
        res = simulate(Rl, args, mu, s, 7 + row)
        c = bu.chain_at(Rl)
        ue = c["U_eta"]
        k, rd = res["kept"], res["read"]
        print("Re_lambda %d: %d tubes thrown (box %.0f x %.0f x %.0f eta, n = %.2e / eta^3, mean spacing %.0f eta); %d candidates (%.2f %% of those thrown), %d kept (%.1f %%), %d read" %
              (Rl, res["thrown"], res["X"], 2 * res["H"], 2 * res["H"], res["density"], res["density"] ** (-1 / 3), len(res["r"]), 100 * len(res["r"]) / res["thrown"], k.sum(), 100 * k.mean(), rd.sum()))
        print("   mean flow U %.0f cm/s (Omega R %.0f cm/s), wire normal to the flow, yaw coefficient %.1f" % (res["U"] * ue, res["U"] * ue / MEAN_FRACTION, KYAW))
        print("   events per cm of path (cm = %.0f eta): %.3g; largest |b|/R of the events read %.1f, 99th percentile %.1f (path grid +-%.0f R); share of the read events with |t*| > 0.45 L: %.3f" %
              (1 / c["eta"], rd.sum() / (res["X"] * c["eta"]), res["b"][rd].max(), np.percentile(res["b"][rd], 99), GRID[-1], np.mean(np.abs(res["t"][rd]) > 0.45)))
        print("   r_max: population median %.2f, crossed %.2f, kept %.2f, read %.2f eta (Belin Fig. 5: 7.6);  U_max (cm/s): crossed %.0f, kept %.0f, read %.0f (10-90 %%: %.0f-%.0f); Fig. 2 event %.1f" %
              (np.median(res["pop_r"]), np.median(res["r"]), np.median(res["r"][k]), np.median(res["r_read"][rd]), np.median(res["umax"]) * ue, np.median(res["umax"][k]) * ue, np.median(res["amp"][rd]) * ue,
               *(np.percentile(res["amp"][rd], [10, 90]) * ue), event))
        f = 1.585 * math.sqrt(Rl) * c["nu"]
        edges = np.logspace(math.log10(f * 0.3), math.log10(f * 60), 80)
        rb = np.linspace(0, 30, 121)
        R_m = 2 * res["r_read"][rd] / 3.17
        p_read = 1.585 * res["amp"][rd] * R_m * c["nu"]                               # r_max U_max read = 1.585 amp R_m nu (amp in U_eta, R_m in eta, U_eta eta = nu)
        grid = np.linspace(0.05, 120, 3000)
        a = ax[row, 0]
        a.hist(res["pop_r"], rb, density=True, histtype="step", lw=2, color="tab:gray", label="in, as is (population): median %.2f eta" % np.median(res["pop_r"]))
        a.hist(res["r"], rb, density=True, histtype="step", lw=2, color="tab:blue", label="crossed (met by the geometry): median %.2f eta" % np.median(res["r"]))
        a.hist(res["r"][k], rb, density=True, histtype="step", lw=2, color="tab:green", ls="--", label="after the cut: median %.2f eta" % np.median(res["r"][k]))
        a.hist(res["r_read"][rd], rb, density=True, histtype="step", lw=2.5, color="tab:red", label="out, as measured: median %.2f eta" % np.median(res["r_read"][rd]))
        a.plot(RATIO * d5[:, 0], d5[:, 1] / RATIO / np.trapezoid(d5[:, 1] / RATIO, RATIO * d5[:, 0]), "ko", ms=3, label="Belin Fig. 5 (measured)")
        a.set_xlim(0, 20)
        a.set_xlabel("r_max / eta (true, and as read)")
        a.set_title("Re_lambda %d: r_max, in and out" % Rl, fontsize=10)
        a = ax[row, 1]
        a.plot(f * grid, bg.lognormal_x(grid, mu, s) / f, "-", lw=2, color="tab:gray", label="in, as is (lognormal): median %.3g cm^2/s, ln-width %.2f" % (f * math.exp(mu), s))
        a.hist(res["rc"] * c["nu"], edges, density=True, histtype="step", lw=2, color="tab:blue", label="crossed: median %.3g" % np.median(res["rc"] * c["nu"]))
        a.hist(res["rc"][k] * c["nu"], edges, density=True, histtype="step", lw=2, color="tab:green", ls="--", label="after the cut: median %.3g" % np.median(res["rc"][k] * c["nu"]))
        a.hist(p_read, edges, density=True, histtype="step", lw=2.5, color="tab:red", label="out, as measured: median %.3g" % np.median(p_read))
        a.plot(f * xs, ps / f, "ko", ms=3, label="Belin Fig. 6 (measured), transformed")
        a.set_xscale("log")
        a.set_xlim(f * 0.3, f * 60)
        a.set_xlabel("r_max U_max (cm^2/s) (true, and as read)")
        a.set_title("Re_lambda %d: r_max U_max, in and out (nu %.2g cm^2/s)" % (Rl, c["nu"]), fontsize=10)
        a = ax[row, 2]
        bins = np.linspace(0, 700, 141)
        a.hist(res["umax"] * ue, bins, density=True, histtype="step", lw=2, color="tab:blue", label="U_max of the crossed tubes: median %.0f cm/s" % (np.median(res["umax"]) * ue))
        a.hist(res["umax"][k] * ue, bins, density=True, histtype="step", lw=1.5, ls="--", color="tab:green", label="after the cut: median %.0f cm/s" % (np.median(res["umax"][k]) * ue))
        a.hist(res["amp"][rd] * ue, bins, density=True, histtype="step", lw=2, color="tab:red", label="as the wire reads it (half swing): median %.0f cm/s" % (np.median(res["amp"][rd]) * ue))
        a.axvline(event, color="k", ls="--", lw=2, label="Fig. 2 event: %.1f cm/s" % event)
        a.axvline(0.769 * Rl ** (1 / 3) * ue, color="gray", ls=":", lw=2, label="our model: %.1f cm/s" % (0.769 * Rl ** (1 / 3) * ue))
        a.set_xlim(0, 450)
        a.set_xlabel("U_max (cm/s)")
        a.set_title("Re_lambda %d: U_max (U_eta %.2f cm/s)" % (Rl, ue), fontsize=10)
        for j in range(3):
            ax[row, j].set_ylabel("pdf")
            ax[row, j].legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.14), frameon=False)
        bb = np.linspace(0, float(np.percentile(res["b"], 99.9)), 61)
        a = axc[row, 0]
        a.hist(res["b"], bb, histtype="step", lw=2, color="tab:blue", label="candidates (|t*| <= L/2)")
        a.hist(res["b"][k], bb, histtype="step", lw=2, color="tab:green", ls="--", label="kept by the cut")
        a.hist(res["b"][rd], bb, histtype="step", lw=2, color="tab:red", label="read")
        a.set_yscale("log")
        a.set_xlabel("|b| / R")
        a.set_ylabel("count")
        a.set_title("Re_lambda %d: impact parameter" % Rl, fontsize=10)
        a.legend(fontsize=8)
        a = axc[row, 1]
        tb = np.linspace(-0.5, 0.5, 51)
        a.hist(res["t"], tb, histtype="step", lw=2, color="tab:blue", label="candidates")
        a.hist(res["t"][rd], tb, histtype="step", lw=2, color="tab:red", label="read")
        a.set_xlabel("t* / L (position of the closest approach along the tube)")
        a.set_ylabel("count")
        a.set_title("Re_lambda %d" % Rl, fontsize=10)
        a.legend(fontsize=8)
    fig.suptitle("volume model: L %.0f eta, V_f %.2f; r_max lognormal median %.2f eta ln-width %.2f; x lognormal median %.1f ln-width %.2f; 5 sigma gradient cut" % (args.length, args.vf, args.rmedian, args.sharp, math.exp(mu), s), fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "chord_belin_volume%s.png" % args.tag), dpi=100)
    figc.tight_layout()
    figc.savefig(os.path.join(HERE, "chord_belin_volume_check%s.png" % args.tag), dpi=100)


if __name__ == "__main__":
    main()
