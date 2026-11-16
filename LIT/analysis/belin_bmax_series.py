"""belin_bmax_series.py  v01  The fitted inputs of the chord model against the impact-parameter limit b_max (in R).
Reads the logs of chord_belin_fit_inputs.py (the 'best:' line of each) for b_max = 1, 1.5, 2, 3, 4, 6 and 12 (files below), then simulates each best fit (chord_belin_x.simulate) to get the true U_max of the crossed tubes.
Panels: true r_max median and ln-width; x median (Belin's own Fig. 6 lognormal: 9.74) and ln-width; true U_max median (cm/s) of the tubes at Re_lambda 659 and 2850 with the mean flow and 2.5 u' for comparison; misfit.
Usage: python belin_bmax_series.py     writes belin_bmax_series.png

Versions  M01 m01.v01 (2026-11-13): first version.
"""
import math
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chord_belin_x as cbx             # noqa: E402
import belin_umax_vs_relambda as bu     # noqa: E402

LOGS = {1.0: "fit_inputs_b1.log", 1.5: "fit_inputs_b1.5.log", 2.0: "fit_inputs_b2_A.log", 3.0: "fit_inputs_b3.log", 4.0: "fit_inputs_b4.log", 6.0: "fit_inputs_b6.log", 12.0: "fit_inputs_window_A.log"}


def best(path):
    text = open(os.path.join(HERE, path), encoding="utf-8").read()
    m = re.search(r"best: r_max median ([\d.]+) eta, ln-width ([\d.]+); x median ([\d.]+), ln-width ([\d.]+); misfit ([\d.]+)", text)
    return tuple(float(v) for v in m.groups()) if m else None


def main():
    rows = {}
    for b, path in LOGS.items():
        res = best(path)
        if res is None:
            print("b_max %g: not finished (%s)" % (b, path))
            continue
        m_r, s_r, m_x, s_x, mis = res
        out = {}
        for Rl in (659, 2850):
            cbx.BMAX = b
            sim = cbx.simulate(Rl, 40000, math.log(m_x), s_x, 5, s_r, m_r)
            c = bu.chain_at(Rl)
            out[Rl] = (np.median(sim["U_true"]) * c["U_eta"], np.median(sim["U_read"]) * c["U_eta"], c)
        rows[b] = (m_r, s_r, m_x, s_x, mis, out)
        print("b_max %4g: r_max %.2f (ln-width %.2f), x %.1f (%.2f), misfit %.3f; true U_max %.0f / %.0f cm/s, read %.0f / %.0f" % (b, m_r, s_r, m_x, s_x, mis, out[659][0], out[2850][0], out[659][1], out[2850][1]))
    bs = sorted(rows)
    fig, ax = plt.subplots(1, 4, figsize=(22, 5.4))
    ax[0].plot(bs, [rows[b][0] for b in bs], "o-", color="tab:blue", label="median")
    ax[0].set_ylabel("true r_max / eta (median)")
    a2 = ax[0].twinx()
    a2.plot(bs, [rows[b][1] for b in bs], "s--", color="tab:gray", label="ln-width")
    a2.set_ylabel("ln-width", color="tab:gray")
    ax[1].plot(bs, [rows[b][2] for b in bs], "o-", color="tab:red", label="fitted x median")
    ax[1].axhline(9.74, color="k", ls=":", label="Belin Fig. 6 lognormal: 9.74")
    ax[1].set_ylabel("x = Re_f / Re_lambda^(1/2), median (r_max U_max input)")
    for Rl, colour in ((659, "tab:green"), (2850, "tab:orange")):
        c = rows[bs[0]][5][Rl][2]
        ax[2].plot(bs, [rows[b][5][Rl][0] for b in bs], "o-", color=colour, label="true U_max of the tubes, Re_lambda %d" % Rl)
        ax[2].plot(bs, [rows[b][5][Rl][1] for b in bs], "x--", color=colour, label="as read, Re_lambda %d" % Rl)
        ax[2].axhline(2.5 * c["up"], color=colour, ls=":", lw=1, label="2.5 u', Re_lambda %d: %.0f cm/s" % (Rl, 2.5 * c["up"]))
    ax[2].set_ylabel("U_max (cm/s), median")
    ax[3].plot(bs, [rows[b][4] for b in bs], "o-", color="k")
    ax[3].set_ylabel("misfit")
    for a, title in zip(ax, ("true radius", "r_max U_max input", "true U_max", "fit quality")):
        a.set_xlabel("impact parameter limit b_max (in R)")
        a.set_xscale("log")
        a.set_title(title, fontsize=10)
    for a in (ax[1], ax[2]):
        a.legend(fontsize=7)
    ax[0].legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_bmax_series.png"), dpi=105)


if __name__ == "__main__":
    main()
