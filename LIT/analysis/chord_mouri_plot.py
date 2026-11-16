"""chord_mouri_plot.py  v01  The figure of chord_mouri.py: what the one-dimensional methods of Mouri et al. (2007), Mouri and Hori (2009) and Sassa and Makita (2005) read from two tube populations, against the papers.
Populations  DNS-like (chord_mouri_dns.json: r_max lognormal median 5.0 eta width 0.3, U_max = 1.0 x 0.769 Re_lambda^(1/3) U_eta) and the Belin fit (chord_mouri_belinfit.json: 7.29 eta, 2.58 x DNS).
Usage: python chord_mouri_plot.py     writes chord_mouri.png
Versions  M01 m01.v01 (2026-11-13): first version.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


def main():
    pops = [("model tubes of the page: r_max 5 eta, U_max 0.769 Re^(1/3) U_eta", load("chord_mouri_dns.json"), "tab:blue", "-"), ("tubes found from Belin: r_max 7.3 eta, U_max 2.6 x the page value", load("chord_mouri_belinfit.json"), "tab:red", "--")]
    fig, ax = plt.subplots(1, 3, figsize=(18, 5.6))
    methods = [("0.1%", "0.1% (Mouri 2007)", "o"), ("1%", "1% (Mouri 2007)", "s"), ("all k=2", "all tubes (Mouri and Hori 2009), threshold 2 sigma", "^")]
    for label, data, colour, ls in pops:
        Re = [m["Re_lambda"] for m in data["mouri"]]
        for key, name, marker in methods:
            ax[0].plot(Re, [m[key]["R0"] for m in data["mouri"]], marker + ls, color=colour, alpha=0.9 if key == "0.1%" else 0.55, ms=6)
            ax[1].plot(Re, [m[key]["V0"] for m in data["mouri"]], marker + ls, color=colour, alpha=0.9 if key == "0.1%" else 0.55, ms=6)
        ax[2].plot([s["Re_lambda"] for s in data["sassa"]], [2 * s["C=2.5"]["r_peak"] for s in data["sassa"]], "o" + ls, color=colour, label=label + ": diameter D/eta")
    Re = [m["Re_lambda"] for m in pops[0][1]["mouri"]]
    for key, name, marker in methods:
        idx = {"0.1%": ("r01", "v01"), "1%": ("r1", "v1"), "all k=2": ("r_all", "v_all")}[key]
        ax[0].plot(Re, [m["paper"][idx[0]] for m in pops[0][1]["mouri"]], marker, color="k", mfc="none", ms=10, label=None)
        ax[1].plot(Re, [m["paper"][idx[1]] for m in pops[0][1]["mouri"]], marker, color="k", mfc="none", ms=10, label=None)
    ax[2].axhline(10, color="k", ls=":", label="Sassa and Makita: D about 10 eta, whatever Re_lambda")
    ax[0].set_ylabel("R0 / eta  (Burgers fit of the mean profile)")
    ax[1].set_ylabel("V0 / u_K")
    ax[2].set_ylabel("diameter of the mean trace D / eta, C = 2.5")
    for a in ax:
        a.set_xlabel("Re_lambda")
        a.set_xscale("log")
        if a is ax[2]:
            a.legend(fontsize=7)
    from matplotlib.lines import Line2D
    h = [Line2D([], [], color="tab:blue", ls="-", label=pops[0][0]), Line2D([], [], color="tab:red", ls="--", label=pops[1][0])]
    h += [Line2D([], [], color="gray", marker=m, ls="", label="method: " + n) for _, n, m in methods]
    h += [Line2D([], [], color="k", marker="o", mfc="none", ls="", ms=9, label="values printed in the papers (open black symbols)")]
    ax[0].legend(handles=h, fontsize=7, loc="upper left")
    ax[1].legend(handles=h, fontsize=7, loc="upper left")
    ax[0].set_ylim(4, 19)
    ax[1].set_ylim(1.5, 28)
    ax[0].set_title("radius", fontsize=10)
    ax[1].set_title("circulation velocity", fontsize=10)
    ax[2].set_title("Sassa and Makita (2005)", fontsize=10)
    fig.suptitle("What the one-dimensional methods read from model tubes (coloured lines) against what the papers print (open black symbols)", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "chord_mouri.png"), dpi=90)


if __name__ == "__main__":
    main()
