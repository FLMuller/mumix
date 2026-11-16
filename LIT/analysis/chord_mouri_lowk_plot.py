"""chord_mouri_lowk_plot.py  v01  Figure of chord_mouri_lowk_belin.json: the all-tube method of Mouri and Hori (2009) on the tubes found from Belin's records (taken as the ground truth), at thresholds 0.5-5 sigma, against the printed values.
Usage: python chord_mouri_lowk_plot.py   writes chord_mouri_lowk_belin.png
Versions  M01 m01.v01 (2026-11-13): first version.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(HERE, "chord_mouri_lowk_belin.json"), encoding="utf-8"))
Re = [q["Re_lambda"] for q in data]
fig, ax = plt.subplots(1, 2, figsize=(12, 5))
ks = ["k=0.5", "k=1", "k=2", "k=3", "k=5"]
for i, k in enumerate(ks):
    c = plt.cm.viridis(i / 4)
    ax[0].plot(Re, [q[k]["R0"] for q in data], "o-", color=c, label="read by the method, threshold %s sigma" % k[2:])
    ax[1].plot(Re, [q[k]["V0"] for q in data], "o-", color=c, label="read by the method, threshold %s sigma" % k[2:])
ax[0].plot(Re, [q["k=5"]["true_r"] for q in data], "k--", label="true mean r_max of the events (threshold 5)")
ax[1].plot(Re, [q["k=5"]["true_U"] for q in data], "k--", label="true mean U_max of the events (threshold 5)")
ax[0].plot(Re, [q["paper"]["r_all"] for q in data], "s", color="red", ms=10, mfc="none", label="printed (Mouri and Hori 2009)")
ax[1].plot(Re, [q["paper"]["v_all"] for q in data], "s", color="red", ms=10, mfc="none", label="printed (Mouri and Hori 2009)")
ax[0].set_ylabel("R0 / eta")
ax[1].set_ylabel("V0 / u_K")
ax[1].set_yscale("log")
for a in ax:
    a.set_xscale("log")
    a.set_xlabel("Re_lambda")
    a.legend(fontsize=7)
fig.suptitle("All-tube method of Mouri and Hori on the tubes found from Belin (ground truth: r_max 7.3 eta median, U_max 2.6 x the page law)", fontsize=10)
fig.tight_layout()
fig.savefig(os.path.join(HERE, "chord_mouri_lowk_belin.png"), dpi=90)
