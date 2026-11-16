"""chord_mouri_pdf.py  v01  The tail of the pdf of the spanwise-velocity increment of Mouri et al. (2007), Fig. 3, from the tube populations of the wire-and-tube model.
Idea     Without a background the increments of the signal are those of the tubes only.  The fraction of the path on which |increment| >= k sigma is, up to one constant C (the number of tubes per unit length, not known from the model),
         F(k) = C sum_i w_i l_i(k),   w_i the footprint weight of chord_mouri.run, l_i(k) the length of tube i's chord where the smoothed increment exceeds k sigma, sigma = sqrt(2/15) (U_eta/eta) dx_s.
         C is fixed by the printed 1% threshold, F(k_1%) = 1%; the model then PREDICTS the 0.1% threshold, to compare with the printed one (6.0-6.7 sigma).  The Gaussian tail is shown for reference.
Output   chord_mouri_pdf.json and chord_mouri_pdf.png.   Usage: python chord_mouri_pdf.py [--n 8000]
Versions  M01 m01.v01 (2026-11-13): first version.
"""
import argparse
import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.special import erfc

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chord_belin_volume as cbv      # noqa: E402
import chord_mouri as cm              # noqa: E402
import chord_belin_sens_fit as sf     # noqa: E402

KGRID = np.linspace(1.5, 9.0, 31)


def tail(Rl, eta_cm, dxs_cm, cfg, n, seed=7):
    rng = np.random.default_rng(seed)
    r = np.exp(math.log(cfg["r_median"]) + cfg["r_sigma"] * rng.standard_normal(n))
    umax = 0.769 * Rl ** (1 / 3) * cfg["umax_scale"] * np.exp(cfg["u_sigma"] * rng.standard_normal(n))
    width = r / cbv.RATIO
    old = cbv.CUT
    cbv.CUT = KGRID[0] * cm.SIGMA_GT / cbv.SIGMA_GRADIENT
    reach = cbv.reach(r, umax)
    cbv.CUT = old
    b = rng.uniform(-reach, reach, n)
    sa = rng.uniform(-1, 1, n)
    phi = rng.uniform(0, 2 * math.pi, n)
    w = np.sqrt(1 - sa ** 2) * reach
    step = cbv.STEP * width
    sep = dxs_cm / eta_cm
    probe = 0.1 / eta_cm
    F = np.zeros(len(KGRID))
    for start in range(0, n, 1000):
        sl = slice(start, start + 1000)
        v = cbv.signal(np.arcsin(sa[sl]), phi[sl], b[sl] / width[sl]) * (umax[sl] / cbv.GMAX)[:, None, None]
        S = v[:, :, 1]
        half = np.maximum(np.round(0.5 * probe / step[sl]).astype(int), 0)
        Ssm = cm.box_smooth(S, half)
        d = np.maximum(np.round(sep / step[sl]).astype(int), 1)
        inc = np.abs(cm.increment(Ssm, d))
        for j, k in enumerate(KGRID):
            F[j] += np.sum(w[sl] * np.sum(inc >= k * cm.SIGMA_GT * sep, axis=1) * step[sl])
    return F


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8000)
    args = ap.parse_args()
    pops = [("model tubes of the page (r_max 5 eta, U_max = 0.769 Re^(1/3) U_eta)", [5.0, 0.3, 1.0, 0.4], "tab:blue", "-"),
            ("tubes found from Belin (r_max 7.3 eta, U_max 2.6 x the page law)", [7.29, 0.58, 2.58, 0.38], "tab:red", "--")]
    sel = [m for m in cm.MOURI if m[0] in (719, 1934)]
    fig, ax = plt.subplots(1, len(sel), figsize=(12, 5), sharey=True)
    out = []
    for a, (Rl, eta_cm, dxs_cm, dx0, k01, k1, *_rest) in zip(ax, sel):
        a.plot(KGRID, erfc(KGRID / math.sqrt(2)), "k:", label="Gaussian")
        a.plot([k1], [1e-2], "ko", mfc="none", ms=10, label="printed 1% threshold")
        a.plot([k01], [1e-3], "ks", mfc="none", ms=10, label="printed 0.1% threshold")
        for label, params, colour, ls in pops:
            cfg = sf.config(np.log(np.array(params)))
            F = tail(Rl, eta_cm, dxs_cm, cfg, args.n)
            Fn = F * 1e-2 / np.interp(k1, KGRID, F)                       # C fixed: F(printed 1% threshold) = 1%
            k01_model = float(np.interp(1e-3, Fn[::-1], KGRID[::-1]))
            a.plot(KGRID, Fn, ls, color=colour, label="%s: 0.1%% at %.1f sigma" % (label, k01_model))
            out.append(dict(Re_lambda=Rl, population=label, k01_model=k01_model, k01_printed=k01, k1_printed=k1))
            print(Rl, label, "model 0.1%% threshold %.2f sigma (printed %.2f)" % (k01_model, k01), flush=True)
        a.set_yscale("log")
        a.set_ylim(1e-4, 1)
        a.set_xlabel("|velocity increment| / standard deviation")
        a.set_title("Re_lambda = %d" % Rl, fontsize=10)
        a.legend(fontsize=7)
    ax[0].set_ylabel("fraction of increments above the abscissa")
    fig.suptitle("Tail of the pdf of the increment (Mouri et al. 2007, Fig. 3): model, with the constant fixed by the printed 1% threshold", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "chord_mouri_pdf.png"), dpi=90)
    json.dump(out, open(os.path.join(HERE, "chord_mouri_pdf.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
