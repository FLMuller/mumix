"""plot_vs_relambda.py  v02  The table rows and the fitted two-law closure against Re_lambda, one symbol per reference.

Panels: r_max/eta, U_max/U_eta, Re_c, Gamma/nu (= 8.78 Re_c), gamma/gamma_eta (= 4x/beta**2) and the budget volume V_f.
Points: every table row with a numeric Re_lambda, one colour and marker per reference (filled = intense tubes, open = whole
tubes); a single legend at the right lists the references and the two fits.  Lines: the fits of fit5_geff.py, whole tubes
(variant B, solid black) and intense tubes (variant C, dashed black); both share the radius law.  V_f is derived from r_max and
U_max (not fitted); the bands are the literature ranges (whole tubes 0.20-0.35 of the volume, intense tubes about 0.01).
v01: points coloured by tube set.  v02: points by reference, one legend box.
Usage: python plot_vs_relambda.py      (writes results_vs_relambda.png next to this file)
"""
import html
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_data_sections as bds
import fit5_geff as f5
import sourcedata as sd

SET = {s["key"]: s["tubes"] for s in sd.SOURCES}
SHORT = {s["key"]: html.unescape(s["short"]) for s in sd.SOURCES}
PANELS = [("beta", r"$r_{max}/\eta$", False), ("U", r"$U_{max}/U_\eta$", False), ("Rec", r"$Re_c$", True),
          ("R", r"$\Gamma/\nu = 8.78\,Re_c$", True), ("gam", r"$\gamma/\gamma_\eta$", False), ("Vf", r"$V_f$ (budget, derived)", True)]
MARKERS = ["o", "s", "^", "v", "D", "P", "X", "<", ">", "h", "*", "p", "d"]
COLOURS = plt.get_cmap("tab20").colors


def main():
    pars = {"whole": f5.fit([o for o in f5.OBS if o[0] != "Ghira22 IVS Re_c"])[0],
            "intense": f5.fit([o for o in f5.OBS if o[0] != "Mouri09 all Re_c"])[0]}
    rows = [t for t in bds.tube_items() if isinstance(t["Re"], (int, float)) and t["beta"]]
    order = [s["key"] for s in sd.SOURCES if any(t["src"] == s["key"] for t in rows)]
    style = {src: (COLOURS[(2 * i) % 20], MARKERS[i % len(MARKERS)]) for i, src in enumerate(order)}
    res = [30 * (2200 / 30) ** (i / 80) for i in range(81)]
    fig, axes = plt.subplots(2, 3, figsize=(17, 9))
    for ax, (key, label, logy) in zip(axes.ravel(), PANELS):
        for ts, ls in (("whole", "-"), ("intense", "--")):
            tm = [f5.tube(Re, pars[ts]) for Re in res]
            ax.plot(res, [(sd.G * m["Rec"] if key == "R" else 100 * m["Vf"] if key == "Vf" else m[key]) for m in tm], c="k", ls=ls, lw=1.6)
        if key != "Vf":
            for src in order:
                pts = []
                for t in rows:
                    if t["src"] != src:
                        continue
                    v = {"beta": t["beta"], "U": t["U"], "Rec": t["rec"], "R": t["RG"], "gam": 4 * sd.x / t["beta"] ** 2}[key]
                    if v is not None:
                        pts.append((t["Re"], v))
                if pts:
                    col, mk = style[src]
                    filled = SET[src] == "intense"
                    ax.scatter(*zip(*pts), marker=mk, s=34, facecolors=col if filled else "none", edgecolors=col, linewidths=1.3, alpha=0.9)
        else:
            ax.axhspan(20, 35, color="0.8", alpha=0.5)
            ax.axhline(1.0, c="0.4", ls=":", lw=1)
            ax.text(32, 25, "whole tubes, literature 20-35%", fontsize=8)
            ax.text(32, 1.15, "intense tubes, about 1%", fontsize=8)
            ax.set_ylim(0.5, 100)
        ax.set_xscale("log")
        if logy:
            ax.set_yscale("log")
        ax.set_xlabel(r"$Re_\lambda$")
        ax.set_ylabel(r"$V_f$ (%)" if key == "Vf" else label)
        ax.set_title(label, fontsize=10)
        ax.grid(alpha=0.25, which="both")
    handles = [Line2D([], [], c="k", ls="-", lw=1.6, label="fit, whole tubes"), Line2D([], [], c="k", ls="--", lw=1.6, label="fit, intense tubes")]
    for src in order:
        col, mk = style[src]
        filled = SET[src] == "intense"
        handles.append(Line2D([], [], marker=mk, ls="", mfc=col if filled else "none", mec=col, mew=1.3, ms=7,
                              label="%s, %s" % (SHORT[src], SET[src])))
    fig.suptitle("Tube parameters against Re_lambda: table rows by reference (filled intense, open whole) and the two-law closure")
    fig.tight_layout(rect=(0, 0, 0.80, 0.96))
    fig.legend(handles=handles, loc="center right", fontsize=9, title="Reference", frameon=True)
    fig.savefig(os.path.join(HERE, "results_vs_relambda.png"), dpi=110)


if __name__ == "__main__":
    main()
