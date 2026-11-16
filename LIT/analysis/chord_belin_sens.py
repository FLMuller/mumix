"""chord_belin_sens.py  v01  Sensitivity study of the wire-and-tube model: which physical parameter decides how many weak tubes give a readable, selected event, and what Belin's reading of them returns.
Why     Belin et al. (1996, eqs. 2-8): the hot wire is cooled by the velocity normal to it; the tube moves past it at a small angle alpha to that normal direction (large-scale fluctuations of the flow), so the swirl shows as an
        S-shaped signal whose amplitude is dS = 2 sin(alpha) U_max (eq. 7b).  Belin then reads U_max = dS / (2 sin alpha) with the constant sin alpha = 0.14, R = 0.31 U dt, and plots x = Re_f / Re_lambda^(1/2), Re_f = U_max R / nu.
Model   straight tubes (Burgers core, circulation Gamma = 8.784 r_max U_max, isotropic axis); the wire passes in a straight line along e_x at the mean speed U (U = 0.588 Omega R, Table I chain); the wire axis e_w = (sin a_w, cos a_w, 0), a_w the
        incidence angle (sin a_w Gaussian with the std sigma_alpha, None: u' / U of the chain; 0 = none); cooling U_eff = sqrt(|u|^2 - (1 - k^2) (u.e_w)^2), u = U e_x + v, k = 0.2 (yaw); signal S = U_eff - U_eff(no tube).
Sampling importance sampling of the volume: the distance of closest approach b is uniform in +-reach(r, U_max) (the largest distance at which the tube can still pass Belin's 5 sigma gradient cut: line vortex, Gamma / (2 pi b^2) = cut),
        the weight of a tube is cos(tilt) x reach: the footprint of a tube of any length L in the plane normal to the flow (L cancels).  No tube that can be selected is dropped; this is the brute-force volume of chord_belin_volume.py without the wasted draws.
Output  per variant (weighted): the share of the selected events that can be read, the read r_max, the read amplitude (cm/s) and x read with Belin's rule (dS / (2 * 0.14)); the pdfs against Fig. 5 and Fig. 6; belin_sensitivity.png.
Usage:  python chord_belin_sens.py [--n 6000]

Versions  M01 m01.v01 (2026-11-13): first version.
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
import chord_belin_volume as cbv          # noqa: E402
import chord_belin_fit_inputs as fi       # noqa: E402
import belin_gamma_pdf as bg              # noqa: E402
import belin_umax_vs_relambda as bu       # noqa: E402

SIN_BELIN = 0.14                                                    # Belin's constant sin(alpha) in U_max = dS / (2 sin alpha)
BASE = dict(inputs="dns", sigma_alpha=0.3, kyaw=0.2, ufac=1.0, umax_scale=1.0, window=2.0, r_median=5.0, r_sigma=0.4, u_sigma=0.4, x_median=14.01, x_sigma=0.75, rr_median=4.44, rr_sigma=0.55)


def wquantile(v, w, q):
    o = np.argsort(v)
    c = np.cumsum(w[o])
    return float(np.interp(q * c[-1], c, v[o]))


def run(Rl, cfg, n, seed=11):
    """n selected-or-not crossings drawn by importance sampling; returns the arrays and weights."""
    rng = np.random.default_rng(seed)
    c = bu.chain_at(Rl)
    ue = c["U_eta"]
    U = cfg["ufac"] * cbv.MEAN_FRACTION * c["Re"] * c["nu"] / cbv.DISK_RADIUS / ue
    if cfg["inputs"] == "dns":                                                    # our DNS-based tubes: r_max about 5 eta, U_max = 0.769 Re_lambda^(1/3) U_eta
        r = np.exp(math.log(cfg["r_median"]) + cfg["r_sigma"] * rng.standard_normal(n))
        umax = 0.769 * Rl ** (1 / 3) * cfg["umax_scale"] * np.exp(cfg["u_sigma"] * rng.standard_normal(n))
    else:                                                                         # the Belin-fitted inputs: r_max and x = Re_f / Re_lambda^(1/2) lognormal
        r = np.exp(math.log(cfg["rr_median"]) + cfg["rr_sigma"] * rng.standard_normal(n))
        umax = 1.585 * math.sqrt(Rl) * cfg["umax_scale"] * np.exp(math.log(cfg["x_median"]) + cfg["x_sigma"] * rng.standard_normal(n)) / r
    width = r / cbv.RATIO
    reach = cbv.reach(r, umax)
    b = rng.uniform(-reach, reach)
    sa = rng.uniform(-1, 1, n)
    phi = rng.uniform(0, 2 * math.pi, n)
    weight = np.sqrt(1 - sa ** 2) * reach                                         # footprint: cos(tilt) x reach (L cancels)
    sigma_alpha = c["up"] / (U * ue) if cfg["sigma_alpha"] is None else cfg["sigma_alpha"]            # None: the physical spread, rms of one transverse fluctuation over the mean flow, u' / U
    sin_w = np.clip(sigma_alpha * rng.standard_normal(n), -0.999, 0.999)
    ew = np.stack([sin_w, np.sqrt(1 - sin_w ** 2), np.zeros(n)], axis=1)
    k2 = cfg["kyaw"] ** 2
    kept, readable, spacing, amp = np.zeros(n, bool), np.zeros(n, bool), np.zeros(n), np.zeros(n)
    cbv.WINDOW = cfg["window"]
    for start in range(0, n, 1000):
        sl = slice(start, start + 1000)
        v = cbv.signal(np.arcsin(sa[sl]), phi[sl], b[sl] / width[sl]) * (umax[sl] / cbv.GMAX)[:, None, None]
        u = v.copy()
        u[:, :, 0] += U
        uw = np.einsum("nmi,ni->nm", u, ew[sl])
        S = np.sqrt(np.maximum(np.sum(u * u, axis=2) - (1 - k2) * uw ** 2, 0)) - np.sqrt(U ** 2 * (1 - (1 - k2) * sin_w[sl] ** 2))[:, None]
        diff = np.abs(np.diff(S, axis=1))
        kept[sl] = np.max(diff, axis=1) / cbv.STEP / width[sl] >= cbv.CUT * cbv.SIGMA_GRADIENT
        centre = cbv.GRID[np.argmax(diff, axis=1)] + 0.5 * cbv.STEP
        inside = np.abs(cbv.GRID[None, :] - centre[:, None]) <= cfg["window"] * cbv.RATIO
        i_hi, i_lo = np.argmax(np.where(inside, S, -np.inf), axis=1), np.argmin(np.where(inside, S, np.inf), axis=1)
        s_hi, s_lo = S[np.arange(len(i_hi)), i_hi], S[np.arange(len(i_lo)), i_lo]
        readable[sl] = (s_hi > 0) & (s_lo < 0)
        spacing[sl] = np.abs(cbv.GRID[i_hi] - cbv.GRID[i_lo]) * width[sl]
        amp[sl] = 0.5 * (s_hi - s_lo)
    rd = kept & readable
    r_read = spacing / 2
    x_belin = amp / SIN_BELIN * (2 * r_read / 3.17) / math.sqrt(Rl)               # Belin: U_mw = dS / (2 sin alpha), R_m = spacing / 3.17, x = U_mw R_m / (nu Re_lambda^(1/2))
    return dict(sin_w=sin_w, sigma_alpha=sigma_alpha, w=weight, kept=kept, rd=rd, r=r, umax=umax, r_read=r_read, amp=amp, x_belin=x_belin, ue=ue, U=U)


def summary(res):
    w, k, rd = res["w"], res["kept"], res["rd"]
    return dict(kept=float(w[k].sum() / w.sum()), read=float(w[rd].sum() / max(w[k].sum(), 1e-30)), r_read=wquantile(res["r_read"][rd], w[rd], 0.5), amp=wquantile(res["amp"][rd], w[rd], 0.5) * res["ue"],
                x=wquantile(res["x_belin"][rd], w[rd], 0.5), umax=wquantile(res["umax"][rd], w[rd], 0.5) * res["ue"])


def pdf(values, weights, edges):
    h = np.histogram(values, edges, weights=weights)[0].astype(float)
    return h / max(h.sum() * (edges[1] - edges[0]), 1e-30)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=6000)
    args = ap.parse_args()
    t5, t6, ok = fi.targets()
    groups = [("incidence angle: sigma of sin(alpha)", "sigma_alpha", [0.0, 0.14, 0.3, 0.6, 1.0]),
              ("mean flow U (x chain)", "ufac", [0.5, 1.0, 2.0, 4.0]),
              ("yaw coefficient k", "kyaw", [0.0, 0.2, 0.5, 1.0]),
              ("swirl scale U_max (x DNS)", "umax_scale", [1.0, 2.0, 4.0, 8.0])]
    Rl = 659
    fig, ax = plt.subplots(len(groups), 3, figsize=(17, 4.6 * len(groups)))
    xs, ps = bg.raw_points()
    d5 = np.loadtxt(os.path.join(HERE, "belin_fig5_digitised.csv"), delimiter=",", skiprows=1)
    c5, c6 = 0.5 * (fi.R5[1:] + fi.R5[:-1]), 0.5 * (fi.X6[1:] + fi.X6[:-1])
    for row, (title, key, values) in enumerate(groups):
        for j, val in enumerate(values):
            cfg = dict(BASE)
            cfg[key] = val
            res = run(Rl, cfg, args.n)
            sm = summary(res)
            print("%-38s %-6g kept %.2f  read/kept %.3f  r_read %.1f eta  amp %.0f cm/s  x_belin %.1f  U_max of the read events %.0f cm/s" % (title, val, sm["kept"], sm["read"], sm["r_read"], sm["amp"], sm["x"], sm["umax"]), flush=True)
            rd, w = res["rd"], res["w"]
            lab = "%s = %g" % (key, val)
            ax[row, 0].plot(c5, pdf(res["r_read"][rd], w[rd], fi.R5), lw=2, label=lab)
            ax[row, 1].plot(c6, pdf(res["x_belin"][rd], w[rd], fi.X6), lw=2, label=lab)
            ax[row, 2].bar(j, sm["read"], color="tab:red", alpha=0.7)
            ax[row, 2].text(j, sm["read"], "%.0f%%\n%.0f cm/s" % (100 * sm["read"], sm["amp"]), ha="center", va="bottom", fontsize=8)
        ax[row, 0].plot(c5, t5, "ko", ms=3, label="Belin Fig. 5")
        ax[row, 1].plot(c6[ok], t6[ok], "ko", ms=3, label="Belin Fig. 6")
        ax[row, 2].set_xticks(range(len(values)))
        ax[row, 2].set_xticklabels([str(v) for v in values])
        ax[row, 2].set_ylabel("share of the selected events that can be read")
        ax[row, 0].set_title(title + ": r_max read (pdf)", fontsize=10)
        ax[row, 1].set_title("x read with Belin's rule (pdf)", fontsize=10)
        ax[row, 2].set_title("readable share and median read amplitude", fontsize=10)
        ax[row, 0].set_xlabel("r_max read / eta")
        ax[row, 1].set_xlabel("x = Re_f / Re_lambda^(1/2)")
        for k in range(2):
            ax[row, k].legend(fontsize=7)
    fig.suptitle("sensitivity of the wire-and-tube model at Re_lambda %d (baseline: DNS tubes, sigma sin(alpha) 0.3, k 0.2, U chain, window 2)" % Rl, fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_sensitivity.png"), dpi=90)


if __name__ == "__main__":
    main()
