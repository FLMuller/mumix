"""pagefigures.py  v01  The figures of the page (inline SVG) in the width of the reading column: panels stacked, the legend below, the svg scaled to the column.

    data_figure(rows)           radius and swirl against Re_lambda (section 1)
    model_figure(res, rows)     radius, swirl and circulation with the model of one fit (section 11)
    fit_to_column(svg)          the same style for any svg: the width of the column, the height in proportion

rows are those of fitdata.load (the corrections applied); res is a result of fitmodels.fit.  The svgs are matplotlib's with the text kept as text.
"""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "fittingtool"))
import fitreport   # noqa: E402

__all__ = ["data_figure", "model_figure", "fit_to_column"]


def fit_to_column(svg):
    """The svg takes the width of the column (at most its own width) and keeps its proportions; wrapped in a white box so it reads in a dark theme."""
    svg = svg.replace("<svg ", '<svg style="max-width:100%;height:auto;display:block" ', 1)
    return '<div style="background:#fff;border:1px solid var(--rule);padding:4px">%s</div>' % svg


def extra_handles():
    return [Line2D([], [], marker="x", ls="", c="0.55", ms=6, label="   rows left out of the fits"),
            Line2D([], [], marker="o", ls="", mfc="none", mec="0.4", ms=6, label="   open: value as calculated")]


def data_figure(rows):
    mark = fitreport.marker_map(rows)
    fig, axes = plt.subplots(2, 1, figsize=(9, 10), sharex=True)
    for ax, kind, label in ((axes[0], "r", r"$r_{max}/\eta$"), (axes[1], "U", r"$U_{max}/U_\eta$")):
        fitreport.draw_data(ax, kind, rows, mark)
        ax.set_xscale("log")
        ax.set_ylabel(label, fontsize=11)
        ax.grid(alpha=0.25, which="both")
    axes[1].set_xlabel(r"$Re_\lambda$", fontsize=11)
    fig.legend(handles=fitreport.legend_handles(rows, mark) + extra_handles(), loc="lower center", ncol=3, fontsize=8, frameon=True)
    for t in fig.legends[0].get_texts():
        if t.get_text() in fitreport.GNAME.values():
            t.set_fontweight("bold")
    fig.tight_layout(rect=(0, 0.19, 1, 1))
    return fit_to_column(fitreport.svg_of(fig))


def model_figure(res, rows):
    m = res["model"]
    mark = fitreport.marker_map(rows)
    x = np.exp(np.linspace(np.log(30), np.log(2300), 120))
    sets = np.array(["intense"] * len(x))
    fig, axes = plt.subplots(3, 1, figsize=(9, 12.5), sharex=True)
    for ax, kind, label, logy in ((axes[0], "r", r"$r_{max}/\eta$", False), (axes[1], "U", r"$U_{max}/U_\eta$", False), (axes[2], "G", r"$\Gamma/\nu$", True)):
        fitreport.draw_data(ax, kind, rows, mark)
        ax.plot(x, m.predict(x, res["params"], sets)[kind], c="k", lw=1.8)
        ax.set_xscale("log")
        if logy:
            ax.set_yscale("log")
        ax.set_ylabel(label, fontsize=11)
        ax.grid(alpha=0.25, which="both")
    axes[2].set_xlabel(r"$Re_\lambda$", fontsize=11)
    fig.legend(handles=fitreport.legend_handles(rows, mark) + extra_handles(), loc="lower center", ncol=3, fontsize=8, frameon=True)
    fig.tight_layout(rect=(0, 0.15, 1, 1))
    return fit_to_column(fitreport.svg_of(fig))
