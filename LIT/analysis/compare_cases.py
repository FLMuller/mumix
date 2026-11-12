"""compare_cases.py  v01  Two cases for the swirl corrections side by side: the data and the fitted laws.

Case A  Mouri and Hori (2009) swirl x 3, Ghira et al. (2022) swirl x 0.6 (the corrections in fittingtool/data/corrections.json).
Case B  Mouri and Hori (2009) swirl x 5 (= 3 / 0.6), Ghira et al. (2022) as calculated (x 1).
Both: Mouri and Hori radius / 1.95, Mouri 2004 and 2007 left out.  For each case the figure shows the swirl against Re_lambda (solid: values used; open: as calculated)
with D1 (r = 5, U = c Re^s), D6 (U = c Re^(1/3)), C1 (G = c Re^Q, r = 5) and K5 (U = a + b ln Re, G = c Re^Q, r = G/(G0 U)); columns: radius, swirl, circulation.
Output  compare_cases.png and compare_cases.svg (this folder; the svg is embedded in section 10 of the page by build_fit_sections.py).   Usage: python compare_cases.py
"""
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "fittingtool")
sys.path.insert(0, TOOL)
import fitdata       # noqa: E402
import fitmodels     # noqa: E402
import fitreport     # noqa: E402

CASES = (("A: Mouri 2009 swirl x 3, Ghira 2022 x 0.6", 3.0, 0.6), ("B: Mouri 2009 swirl x 5, Ghira 2022 as calculated (x 1)", 5.0, 1.0))


def main():
    base = json.load(open(os.path.join(TOOL, "data", "corrections.json"), encoding="utf-8"))
    fig, axes = plt.subplots(3, 2, figsize=(11, 13.5))     # rows: radius, swirl, circulation; columns: the two cases
    re = np.exp(np.linspace(np.log(30), np.log(2300), 200))
    for case, (label, mk, gk) in enumerate(CASES):
        corr = json.loads(json.dumps(base["corrections"]))
        corr["Mouri09"]["u_factor"] = mk
        corr["Ghira22"]["u_factor"] = gk
        rows = fitdata.load(os.path.join(TOOL, "data", "tubes.csv"), corr=corr, excluded=base["excluded"])
        obs = fitdata.observations(rows)
        mark = fitreport.marker_map(rows)
        fits = {}
        for m in fitmodels.models(obs):
            if m.key in ("D1", "D6", "C1", "K5"):
                fits[m.key] = (m, fitmodels.fit(m, obs))
        for line, kind, ylabel in ((0, "r", r"$r_{max}/\eta$"), (1, "U", r"$U_{max}/U_\eta$"), (2, "G", r"$\Gamma/\nu$")):
            ax = axes[line][case]
            fitreport.draw_data(ax, kind, rows, mark)
            for key, colour, ls in (("D1", "k", "-"), ("D6", "tab:red", "--"), ("C1", "tab:purple", ":"), ("K5", "tab:orange", "-.")):
                m, r = fits[key]
                y = m.predict(re, r["params"], np.array(["whole"] * len(re)))[kind]
                ax.plot(re, y, c=colour, ls=ls, lw=1.6, label="%s  %s  (combined %.1f%%)" % (key, ", ".join("%s=%.3g" % (n, v) for n, v in zip(m.names, r["params"])), 100 * r["scores"]["combined"]))
            ax.set_xscale("log")
            if kind == "G":
                ax.set_yscale("log")
            ax.set_xlabel(r"$Re_\lambda$")
            ax.set_ylabel(ylabel)
            ax.grid(alpha=0.25, which="both")
            ax.legend(fontsize=6.5, loc="upper left")
            ax.set_title("Case " + label, fontsize=8)
    from matplotlib.lines import Line2D
    handles = fitreport.legend_handles(rows, mark) + [Line2D([], [], marker="x", ls="", c="0.55", ms=6, label="   Mouri 2004, 2007 (left out of the fits)"),
                                                      Line2D([], [], marker="o", ls="", mfc="none", mec="0.4", ms=6, label="   open: value as calculated (corrected sources)")]
    fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=7.5, frameon=True, title="points: colour = method, marker = source", title_fontsize=8)
    fig.tight_layout(rect=(0, 0.17, 1, 1))
    path = os.path.join(HERE, "compare_cases.png")
    fig.savefig(path, dpi=110)
    fig.savefig(os.path.join(HERE, "compare_cases.svg"), format="svg", facecolor="white")
    print(path)


if __name__ == "__main__":
    main()
