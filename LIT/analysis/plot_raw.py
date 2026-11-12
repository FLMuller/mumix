"""plot_raw.py  v01  Raw big gamma and little gamma against Re_lambda and Re_c, by methodology, no conversion.

Every table row with a reported radius beta' = r_max/eta and swirl U' = U_max/U_eta, exactly as reported (no rescaling):
    Re_c = beta' U'
    G = Gamma/nu = 8.784 Re_c  (the circulation listed by Kida et al. where the source gives one)
    g = gamma/gamma_eta = 4x/beta'**2
Top row: G against Re_lambda and against Re_c; bottom row: g against Re_lambda and against Re_c.
Colour = methodology (A DNS intense, B DNS whole tubes, C experiments, as in plot_groups.py), marker = reference; one legend at the right.
Usage: python plot_raw.py      (writes raw_vs_re.png next to this file)
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_data_sections as bds
import plot_groups as pg
import sourcedata as sd

X = sd.x


def main():
    rows = [t for t in bds.tube_items() if t["beta"] and t["U"] and t["RG"] is not None and isinstance(t["Re"], (int, float))]
    srcs = [s["key"] for s in sd.SOURCES if any(t["src"] == s["key"] for t in rows)]
    mark = {}
    for g in "ABC":
        for i, s in enumerate([s for s in srcs if pg.GROUP[s] == g]):
            mark[s] = pg.MARKERS[i % len(pg.MARKERS)]
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    for (r, c), ax in zip(((0, 0), (0, 1), (1, 0), (1, 1)), axes.ravel()):
        for t in rows:
            xv = t["Re"] if c == 0 else t["beta"] * t["U"]
            yv = t["RG"] if r == 0 else 4 * X / t["beta"] ** 2
            ax.scatter(xv, yv, marker=mark[t["src"]], s=38, c=pg.COLOUR[pg.GROUP[t["src"]]], alpha=0.8, edgecolors="none")
        ax.set_xscale("log")
        if r == 0:
            ax.set_yscale("log")
        ax.set_xlabel(r"$Re_\lambda$" if c == 0 else r"$Re_c=\beta'U'$ (reported)")
        ax.set_ylabel(r"$G=\Gamma/\nu$" if r == 0 else r"$g=\gamma/\gamma_\eta=4x/(r_{max}/\eta)^2$")
        ax.grid(alpha=0.25, which="both")
    handles = []
    for g in "ABC":
        handles.append(Line2D([], [], ls="", label=pg.GNAME[g], marker="s", mfc=pg.COLOUR[g], mec=pg.COLOUR[g], ms=0))
        for s in [s for s in srcs if pg.GROUP[s] == g]:
            handles.append(Line2D([], [], marker=mark[s], ls="", mfc=pg.COLOUR[g], mec=pg.COLOUR[g], ms=7, label="   " + pg.SHORT[s]))
    fig.suptitle("Raw big gamma and little gamma against Re_lambda and Re_c, by methodology (reported values, no conversion; radius-only rows have no G)")
    fig.tight_layout(rect=(0, 0, 0.75, 0.96))
    leg = fig.legend(handles=handles, loc="center left", bbox_to_anchor=(0.755, 0.5), fontsize=9, title="Methodology and reference", frameon=True)
    for txt, g in zip([t for t in leg.get_texts() if not t.get_text().startswith("   ")], "ABC"):
        txt.set_color(pg.COLOUR[g])
        txt.set_fontweight("bold")
    fig.savefig(os.path.join(HERE, "raw_vs_re.png"), dpi=110)
    print("rows plotted:", len(rows))


if __name__ == "__main__":
    main()
