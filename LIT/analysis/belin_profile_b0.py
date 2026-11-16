"""belin_profile_b0.py  v01  The signal of one tube along the wire path, at impact parameter b = 0 (the path meets the axis) and a few tilts, and at b = R and 2R, with the speed limits of the disks.
Tube: the fitted median tube of the b <= 2R fit (r_max = 4.77 eta, R = r_max / 1.585) with U_max = 160 cm/s (its fitted true median at Re_lambda 659, U_eta = 1.99 cm/s from the Table I chain).
Signal: chord_model.signal (unit tube, R = 1; the central crossing at tilt 0 and rotation 90 degrees peaks at 0.4512 = U_max), scaled to cm/s, s in eta.
Disk limits (chain at Re_lambda 659): Omega R and 2 Omega R (the disks counter-rotate, so the relative speed is up to 2 Omega R); the fraction of the fitted tubes above each limit is printed.
Usage: python belin_profile_b0.py     writes belin_profile_b0.png

Versions  M01 m01.v01 (2026-11-13): first version.
"""
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chord_model as cm                 # noqa: E402
import chord_population as cp            # noqa: E402
import chord_belin_x as cbx              # noqa: E402
import belin_umax_vs_relambda as bu      # noqa: E402
import belin_rumax_physical as brp       # noqa: E402


def main():
    Rl = 659
    c = bu.chain_at(Rl)
    omega = c["Re"] * c["nu"] / brp.R ** 2
    omegaR = omega * brp.R                                                    # cm/s
    r_max, U_max = 4.77, 160.0
    R = r_max / cp.RATIO
    scale = U_max / cp.GMAX
    cases = [("b = 0, tilt 0 (normal crossing)", 0.0, 0.0, "tab:red"), ("b = 0, tilt 30 deg", 30.0, 0.0, "tab:orange"), ("b = 0, tilt 60 deg", 60.0, 0.0, "tab:brown"),
             ("b = R, tilt 0", 0.0, 1.0, "tab:blue"), ("b = 2R, tilt 0", 0.0, 2.0, "tab:green")]
    fig, ax = plt.subplots(figsize=(10, 6))
    s = cm.S_GRID * R
    for label, tilt, b, colour in cases:
        S = cm.signal(np.array([math.radians(tilt)]), np.array([math.pi / 2]), np.array([b]))[0] * scale
        ax.plot(s, S, color=colour, lw=2, label="%s: swing %.0f cm/s, spacing %.1f eta" % (label, 0.5 * (S.max() - S.min()), abs(s[np.argmax(S)] - s[np.argmin(S)])))
    for v, ls in ((omegaR, "--"), (2 * omegaR, ":")):
        ax.axhline(v, color="k", ls=ls, lw=1)
        ax.axhline(-v, color="k", ls=ls, lw=1)
    ax.text(s[-1], omegaR, "  Omega R = %.0f cm/s" % omegaR, va="bottom", ha="right", fontsize=8)
    ax.text(s[-1], 2 * omegaR, "  2 Omega R = %.0f cm/s" % (2 * omegaR), va="bottom", ha="right", fontsize=8)
    ax.axvline(r_max, color="gray", lw=0.8)
    ax.axvline(-r_max, color="gray", lw=0.8)
    ax.set_xlim(-30, 30)
    ax.set_xlabel("s / eta  (along the path; grey: +-r_max = %.2f eta)" % r_max)
    ax.set_ylabel("signal (cm/s)")
    ax.set_title("signal of the median fitted tube (U_max = %.0f cm/s) at Re_lambda %d" % (U_max, Rl), fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_profile_b0.png"), dpi=105)
    cbx.BMAX = 2.0
    sim = cbx.simulate(Rl, 60000, math.log(12.8), 0.75, 5, 0.557, 4.767)
    U = sim["U_true"] * c["U_eta"]
    print("Omega R %.0f cm/s, 2 Omega R %.0f; fitted tubes (b <= 2R): median U_max %.0f; share above Omega R %.1f %%, above 2 Omega R %.1f %%" % (omegaR, 2 * omegaR, np.median(U), 100 * np.mean(U > omegaR), 100 * np.mean(U > 2 * omegaR)))


if __name__ == "__main__":
    main()
