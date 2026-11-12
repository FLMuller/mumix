"""plot3d.py  v01  Big gamma against little gamma, with r_max/eta and U_max/U_eta on the vertical axis.

x = Gamma/nu (circulation), y = gamma/gamma_eta (strain, 4x/beta**2), z = r_max/eta (top row) and U_max/U_eta (bottom row).
Points: every table row with a numeric Re_lambda (intense red, whole blue; Gamma/nu = 8.78 Re_c for every row).
Lines: the fitted two-law closure of fit5_geff.py as Re_lambda runs from 30 to 2200, whole tubes (variant B) and intense tubes
(variant C).  Each column of panels is one viewing angle.
Usage: python plot3d.py      (writes gamma_3d.png next to this file)
"""
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_data_sections as bds
import fit5_geff as f5
import sourcedata as sd

COLOUR = {"intense": "#c0392b", "whole": "#2471a3"}
SET = {s["key"]: s["tubes"] for s in sd.SOURCES}


def main():
    pars = {"whole": f5.fit([o for o in f5.OBS if o[0] != "Ghira22 IVS Re_c"])[0],
            "intense": f5.fit([o for o in f5.OBS if o[0] != "Mouri09 all Re_c"])[0]}
    for ts, p in pars.items():
        print("%-8s beta = %.3f Re^%.4f   Re_c = %.3f Re^%.4f" % (ts, p[0], p[1], p[2], p[3]))
    rows = [t for t in bds.tube_items() if isinstance(t["Re"], (int, float)) and t["beta"] and t["U"]]
    res = [30 * (2200 / 30) ** (i / 60) for i in range(61)]
    views = [(22, -62), (18, 28)]
    fig = plt.figure(figsize=(15, 11.5))
    for r, (zk, zl) in enumerate((("beta", r"$r_{max}/\eta$"), ("U", r"$U_{max}/U_\eta$"))):
        for c, (el, az) in enumerate(views):
            ax = fig.add_subplot(2, 2, 2 * r + c + 1, projection="3d")
            for ts in ("whole", "intense"):
                pts = [t for t in rows if SET[t["src"]] == ts]
                ax.scatter([sd.G * t["beta"] * t["U"] for t in pts], [4 * sd.x / t["beta"] ** 2 for t in pts], [t[zk] for t in pts],
                           c=COLOUR[ts], s=22, alpha=0.8, depthshade=False, label="%s rows" % ts)
                tm = [f5.tube(Re, pars[ts]) for Re in res]
                ax.plot([sd.G * m["Rec"] for m in tm], [m["gam"] for m in tm], [m["beta" if zk == "beta" else "U"] for m in tm],
                        c=COLOUR[ts], lw=2.2, label="%s fit" % ts)
            ax.set_xlabel(r"$\Gamma/\nu$")
            ax.set_ylabel(r"$\gamma/\gamma_\eta$")
            ax.set_zlabel(zl)
            ax.view_init(elev=el, azim=az)
            if r == 0 and c == 0:
                ax.legend(loc="upper left", fontsize=8)
    fig.suptitle("Big gamma, little gamma and r_max, U_max: rows and fitted two-law closure (Re_lambda 30-2200 along the lines)")
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "gamma_3d.png"), dpi=105)


if __name__ == "__main__":
    main()
