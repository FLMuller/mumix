"""plot_groups.py  v01  Big gamma times little gamma against little gamma, and big gamma against little gamma, by methodology.

Every table row with both a reported radius beta' = r_max/eta and swirl U' = U_max/U_eta gives
    g = gamma/gamma_eta = 4x/beta'**2      (little gamma, the strain seen from the radius)
    G = Gamma/nu = 8.784 beta' U'          (big gamma; the circulation listed by Kida et al. where the source gives one)
and P = G g = 4 pi omega_0/gamma_eta = 44.1 U'/beta'  (peak axis vorticity, omega_0/omega_rms = P/4pi).
Three groupings by how the radius was obtained:
  A  DNS, intense tubes: the top 1% of the volume by vorticity (Ghira, Jimenez, Da Silva);
  B  DNS, whole tubes: a narrow distribution of tube sizes without a vorticity threshold, quoted as a mean or most expected value
     (Tanahashi, Kida, Pirozzoli, Ishihara, Das and others);
  C  experiments: hot wire or hot film records (Mouri, Belin, Sassa) and 3D PIV in the water tank (Aligolzadeh).
Rows without a swirl (radius only) have no G and are not plotted.  Left: P against g with lines of constant omega_0/omega_rms
(horizontal) and of constant U' (slope 1/2); right: G against g with lines of constant U'.
The points are the reported (beta', U') pairs, unconverted.  The thin lines show the n = 1 conversion (circulation kept, G unchanged) to the
assumed true radius r_max/eta = 5, g = 0.201: horizontal in the right panel, along slope 1 in the left.
Usage: python plot_groups.py      (writes groups_map.png next to this file)
"""
import html
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_data_sections as bds
import sourcedata as sd

X = sd.x
GROUP = {"Ghira22": "A", "Ghira25": "A", "Jimenez93": "A", "DaSilva11": "A",
         "Tanahashi01": "B", "Kida02": "B", "Pirozzoli09": "B", "Ishihara13": "B", "Wall": "B",
         "Aligolzadeh23": "C", "Mouri03": "C", "Mouri04": "C", "Mouri07": "C", "Mouri09": "C", "Belin96": "C", "Sassa05": "C"}
GNAME = {"A": "A  DNS, intense (top 1% volume)", "B": "B  DNS, whole tubes (mean or mode)", "C": "C  experiments (probe, PIV)"}
COLOUR = {"A": "#c0392b", "B": "#2471a3", "C": "#1e8449"}
MARKERS = ["o", "s", "^", "v", "D", "P", "X", "<", ">", "h", "*", "p", "d"]
SHORT = {s["key"]: html.unescape(s["short"]) for s in sd.SOURCES}


def main():
    rows = [t for t in bds.tube_items() if t["beta"] and t["U"] and t["RG"] is not None]
    srcs = [s["key"] for s in sd.SOURCES if any(t["src"] == s["key"] for t in rows)]
    mark = {}
    for g in "ABC":
        for i, s in enumerate([s for s in srcs if GROUP[s] == g]):
            mark[s] = MARKERS[i % len(MARKERS)]
    gs = [4 * X / t["beta"] ** 2 for t in rows]
    fig, (axl, axr) = plt.subplots(1, 2, figsize=(17, 7))
    gx = [0.05 * (0.3 / 0.05) ** (i / 50) for i in range(51)]
    for q in (1, 2, 4, 8):
        axl.axhline(4 * math.pi * q, c="0.75", lw=0.8, ls=":")
        axl.text(0.0505, 4 * math.pi * q * 1.04, r"$\omega_0/\omega_{rms}=%d$" % q, fontsize=7, color="0.45")
    for u in (2, 4, 8, 16):
        axl.plot(gx, [sd.G * 4 * X * u * math.sqrt(g / (4 * X)) for g in gx], c="0.85", lw=0.8)
        axl.text(0.295, sd.G * 4 * X * u * math.sqrt(0.295 / (4 * X)) * 0.9, "U'=%d" % u, fontsize=7, color="0.45", ha="right")
        axr.plot(gx, [sd.G * u * math.sqrt(4 * X / g) for g in gx], c="0.85", lw=0.8)
        axr.text(0.0505, sd.G * u * math.sqrt(4 * X / 0.0505) * 0.93, "U'=%d" % u, fontsize=7, color="0.45")
    g0 = 4 * X / 25.0                      # little gamma of the assumed true radius r_max/eta = 5
    for t, g in zip(rows, gs):
        s = t["src"]
        # n = 1 (circulation kept): the point slides to g0 at constant G, so P = G g changes in proportion to g
        axr.plot([g, g0], [t["RG"], t["RG"]], c=COLOUR[GROUP[s]], lw=0.6, alpha=0.25)
        axl.plot([g, g0], [t["RG"] * g, t["RG"] * g0], c=COLOUR[GROUP[s]], lw=0.6, alpha=0.25)
        axl.scatter(g, t["RG"] * g, marker=mark[s], s=38, c=COLOUR[GROUP[s]], alpha=0.8, edgecolors="none")
        axr.scatter(g, t["RG"], marker=mark[s], s=38, c=COLOUR[GROUP[s]], alpha=0.8, edgecolors="none")
    for ax, yl in ((axl, r"$G\,g=(\Gamma/\nu)(\gamma/\gamma_\eta)=4\pi\,\omega_0/\gamma_\eta$"), (axr, r"$G=\Gamma/\nu$")):
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel(r"$g=\gamma/\gamma_\eta=4x/(r_{max}/\eta)^2$")
        ax.set_ylabel(yl)
        ax.set_xlim(0.05, 0.3)
        ax.grid(alpha=0.25, which="both")
    axl.set_title("big gamma times little gamma against little gamma", fontsize=11)
    axr.set_title("big gamma against little gamma", fontsize=11)
    handles = []
    for g in "ABC":
        handles.append(Line2D([], [], ls="", label=GNAME[g], marker="s", mfc=COLOUR[g], mec=COLOUR[g], ms=0))
        for s in [s for s in srcs if GROUP[s] == g]:
            handles.append(Line2D([], [], marker=mark[s], ls="", mfc=COLOUR[g], mec=COLOUR[g], ms=7, label="   " + SHORT[s]))
    fig.suptitle("Tube parameters by methodology: A DNS intense, B DNS whole tubes, C experiments (radius-only rows are not shown)")
    fig.tight_layout(rect=(0, 0, 0.78, 0.95))
    leg = fig.legend(handles=handles, loc="center left", bbox_to_anchor=(0.785, 0.5), fontsize=9, title="Methodology and reference", frameon=True)
    for txt, g in zip([t for t in leg.get_texts() if not t.get_text().startswith("   ")], "ABC"):
        txt.set_color(COLOUR[g])
        txt.set_fontweight("bold")
    fig.savefig(os.path.join(HERE, "groups_map.png"), dpi=110)
    for g in "ABC":
        n = sum(1 for t in rows if GROUP[t["src"]] == g)
        print("group %s: %d rows plotted (%s)" % (g, n, ", ".join(sorted({SHORT[t["src"]] for t in rows if GROUP[t["src"]] == g}))))


if __name__ == "__main__":
    main()
