"""fitreport.py  v01  The report of the fitting tool: one self-contained HTML document, and the index of the reports.

    write_report(results_dir, ctx) -> path        the report of a run, in results_dir, named fit_YYYY.MM.DD_HH;MM.html
    write_index(results_dir)       -> path        index.html: a tree of every report file (a file tree view), newest first

The report follows the conventions of the runbench reports (mumix/tools): one document that needs nothing beside it, a tab bar (class btab,
data-go) over panels (class bpanel, data-group="run"), tables of class grid, the style and the script of the page written into the file.
It can be opened without the report server; the server, when it opens the file, only adds interactivity.  Figures are inline SVG.

ctx (a dict made by fittingtool.py): rows, obs, results, selected, reasons, legacy, corrections, stamp, files.

Versions  M01 m01.v01 (2026-11-11): first version.
"""
import html
import io
import json
import os
import re
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from fitdata import G0

__all__ = ["write_report", "write_index"]

HERE = os.path.dirname(os.path.abspath(__file__))
COLOUR = {"A": "#c0392b", "B": "#2471a3", "C": "#1e8449"}
GNAME = {"A": "A  DNS, intense tubes (1% volume)", "B": "B  DNS, whole tubes", "C": "C  experiments (probe, PIV)"}
MARKERS = ["o", "s", "^", "v", "D", "P", "X", "<", ">", "h", "*", "p", "d"]
LINES = ["#000000", "#c0392b", "#2471a3", "#1e8449", "#8e44ad", "#d68910", "#17a589", "#7f8c8d", "#ba4a00", "#2e4053", "#a569bd"]
plt.rcParams["svg.fonttype"] = "none"


def esc(text):
    return html.escape(str(text), quote=True)


def num(v, digits=3):
    """A number with significant digits; a dash for None or nan."""
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "&mdash;"
    return ("%." + str(digits) + "g") % v


def pct(v, digits=1):
    return "&mdash;" if v is None or not np.isfinite(v) else ("%." + str(digits) + "f%%") % (100 * v)


def table(headers, rows, left=(0,), row_class=None):
    """A table of class grid; left: the columns aligned left; row_class(i) the class of row i."""
    head = "".join('<th%s>%s</th>' % (' class="l"' if i in left else "", h) for i, h in enumerate(headers))
    body = []
    for n, row in enumerate(rows):
        cls = row_class(n) if row_class else ""
        body.append("<tr%s>%s</tr>" % (' class="%s"' % cls if cls else "", "".join('<td%s>%s</td>' % (' class="l"' if i in left else "", c) for i, c in enumerate(row))))
    return '<div class="tablebox"><table class="grid"><thead><tr>%s</tr></thead><tbody>\n%s\n</tbody></table></div>' % (head, "\n".join(body))


def svg_of(fig):
    buf = io.StringIO()
    fig.savefig(buf, format="svg", facecolor="white")
    plt.close(fig)
    text = buf.getvalue()
    return text[text.index("<svg"):]


def marker_map(rows):
    """One marker per reference within each group."""
    mark = {}
    for g in "ABC":
        refs = []
        for x in rows:
            if x["group"] == g and x["reference"] not in refs:
                refs.append(x["reference"])
        for i, ref in enumerate(refs):
            mark[ref] = MARKERS[i % len(MARKERS)]
    return mark


def draw_data(ax, kind, rows, mark, corrected=True, alpha=0.85, only_numeric=True):
    """Points of one quantity (r, u or g) by reference; open symbols at the raw value where a correction was applied; bars for Re ranges."""
    for x in rows:
        val = {"r": x["r"], "U": x["u"], "G": x["g"]}[kind]
        raw = {"r": x["r_raw"], "U": x["u_raw"], "G": None}[kind]
        col, mk = COLOUR[x["group"]], mark[x["reference"]]
        if x.get("excluded"):                                  # left out of the fits: a grey cross at the value as calculated
            if x["re"] is not None and raw is not None:
                ax.scatter([x["re"]], [raw], marker="x", s=22, c="0.55", alpha=0.7, linewidths=1.0)
            continue
        if x["re"] is not None and val is not None:
            ax.scatter([x["re"]], [val], marker=mk, s=34, c=col, alpha=alpha, edgecolors="none")
            if raw is not None and abs(raw - val) > 1e-9 * max(1.0, abs(val)):
                ax.scatter([x["re"]], [raw], marker=mk, s=30, facecolors="none", edgecolors=col, alpha=0.55)
        elif x["re_lo"] is not None and val is not None and kind == "r":
            ax.plot([x["re_lo"], x["re_hi"]], [val, val], c=col, lw=2.5, alpha=0.85, solid_capstyle="butt")
            ax.scatter([np.sqrt(x["re_lo"] * x["re_hi"])], [val], marker=mk, s=50, c=col, edgecolors="k", linewidths=0.7)


def legend_handles(rows, mark):
    from matplotlib.lines import Line2D
    handles = []
    for g in "ABC":
        handles.append(Line2D([], [], ls="", marker="s", ms=0, label=GNAME[g]))
        seen = []
        for x in rows:
            if x["group"] == g and x["reference"] not in seen:
                seen.append(x["reference"])
                handles.append(Line2D([], [], marker=mark[x["reference"]], ls="", mfc=COLOUR[g], mec=COLOUR[g], ms=6, label="   " + x["reference"]))
    return handles


def svg_data(rows):
    mark = marker_map(rows)
    fig, axes = plt.subplots(1, 2, figsize=(16, 5.2))
    for ax, kind, label in ((axes[0], "r", r"$r_{max}/\eta$"), (axes[1], "U", r"$U_{max}/U_\eta$")):
        draw_data(ax, kind, rows, mark)
        ax.set_xscale("log")
        ax.set_xlabel(r"$Re_\lambda$")
        ax.set_ylabel(label)
        ax.grid(alpha=0.25, which="both")
    axes[0].set_title("radius: values used (solid), as calculated where corrected (open); bars: range of Re_lambda", fontsize=9)
    axes[1].set_title("swirl: values used (solid), as calculated where corrected (open)", fontsize=9)
    fig.legend(handles=legend_handles(rows, mark), loc="center left", bbox_to_anchor=(0.795, 0.5), fontsize=7.5, frameon=True)
    for t in fig.legends[0].get_texts():
        if t.get_text() in GNAME.values():
            t.set_fontweight("bold")
    fig.tight_layout(rect=(0, 0, 0.78, 1))
    return svg_of(fig)


def svg_model(res, rows):
    m = res["model"]
    mark = marker_map(rows)
    x = np.exp(np.linspace(np.log(30), np.log(2300), 120))
    sets = np.array(["intense"] * len(x))
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4))
    for ax, kind, key, label, logy in ((axes[0], "r", "r", r"$r_{max}/\eta$", False), (axes[1], "U", "U", r"$U_{max}/U_\eta$", False), (axes[2], "G", "G", r"$\Gamma/\nu$", True)):
        draw_data(ax, kind, rows, mark)
        pred = m.predict(x, res["params"], sets)
        ax.plot(x, pred[key], c="k", lw=1.8)
        if m.key == "T6":
            ax.plot(x, m.predict(x, res["params"], np.array(["whole"] * len(x)))[key], c="k", lw=1.2, ls="--")
        ax.set_xscale("log")
        if logy:
            ax.set_yscale("log")
        ax.set_xlabel(r"$Re_\lambda$")
        ax.set_ylabel(label)
        ax.grid(alpha=0.25, which="both")
    fig.suptitle("%s  %s" % (m.key, m.name), fontsize=10)
    fig.tight_layout()
    return svg_of(fig)


def svg_compare(results, rows):
    mark = marker_map(rows)
    x = np.exp(np.linspace(np.log(30), np.log(2300), 120))
    sets = np.array(["intense"] * len(x))
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    for ax, kind, key, label, logy in ((axes[0], "r", "r", r"$r_{max}/\eta$", False), (axes[1], "U", "U", r"$U_{max}/U_\eta$", False), (axes[2], "G", "G", r"$\Gamma/\nu$", True)):
        draw_data(ax, kind, rows, mark, alpha=0.35)
        for i, res in enumerate(results):
            if res.get("ok"):
                ax.plot(x, res["model"].predict(x, res["params"], sets)[key], c=LINES[i % len(LINES)], lw=1.5, ls="--" if res["model"].info else "-",
                        label=res["model"].key)
        ax.set_xscale("log")
        if logy:
            ax.set_yscale("log")
        ax.set_xlabel(r"$Re_\lambda$")
        ax.set_ylabel(label)
        ax.grid(alpha=0.25, which="both")
    axes[2].legend(fontsize=8, ncol=2)
    fig.tight_layout()
    return svg_of(fig)


def figure(svg, caption):
    return "<figure>%s<figcaption>%s</figcaption></figure>" % (svg, caption)


# ---------------------------------------------------------------------------------------------------- tabs
def eqs(lines):
    return "".join('<div class="eq">%s</div>' % esc(line) for line in lines)


def params_table(res):
    m = res["model"]
    rows = [[esc(n), num(v, 4), num(e, 2), pct(e / abs(v)) if v else "&mdash;"] for n, v, e in zip(m.names, res["params"], res["errors"])]
    return table(["parameter", "value", "error", "error / value"], rows)


def scores_table(res):
    sc = res["scores"]
    return table(["quantity", "rms log residual (weighted)", "RMSE / mean (%)"],
                 [["r (radius)", pct(sc["rms_r"]), "%.1f" % sc["rmse_r"]], ["U (swirl)", pct(sc["rms_U"]), "%.1f" % sc["rmse_U"]],
                  ["G = Gamma/nu", pct(sc["rms_G"]), "%.1f" % sc["rmse_G"]], ["combined (r, U)", pct(sc["combined"]), ""]])


def budget_table(res):
    b, p = res["bud"], res["pred"]
    rows = []
    for i, re in enumerate(res["re_check"]):
        rows.append(["%g" % re, num(p["r"][i], 3), num(p["U"][i], 3), num(p["G"][i], 3), num(p["r"][i] * p["U"][i], 3), num(b["g"][i], 3), pct(b["share"][i], 0), pct(b["vf"][i]), num(b["d"][i], 3)])
    return table(["Re_lambda", "r", "U", "G", "Re_c = r U", "gamma/gamma_eta", "vortex share", "V_f", "d/eta"], rows)


def deviation_table(res):
    dev = res["dev"]
    keys = sorted(set(k for per_kind in dev.values() for k in per_kind), key=lambda k: k[1])
    rows = []
    for k in keys:
        cells = [esc(k[1])]
        for kind in ("r", "U", "G"):
            v = dev[kind].get(k)
            cells.append("&mdash;" if v is None else "%+.0f%% (%d)" % (100 * v[0], v[1]))
        rows.append(cells)
    return table(["source", "r: mean deviation (n)", "U: mean deviation (n)", "G: mean deviation (n)"], rows)


def tab_model(res, ctx):
    m = res["model"]
    if not res.get("ok"):
        return "<h2>%s  %s</h2><p>The fit failed: %s</p>" % (m.key, esc(m.name), esc(res.get("message", "")))
    note = '<p class="note">%s</p>' % esc(m.note) if m.note else ""
    reason = dict(ctx["reasons"]).get(m.key, "")
    return ("<h2>%s &nbsp; %s</h2><p class=\"sub\">family: %s &nbsp;|&nbsp; %d parameters &nbsp;|&nbsp; fitted to: %s &nbsp;|&nbsp; status: %s</p>%s"
            % (m.key, esc(m.name), esc(m.family), m.nparam, ", ".join(m.kinds), esc(reason), note)
            + "<h3>Equations</h3>" + eqs(m.equations) + "<h3>Parameters</h3>" + params_table(res)
            + "<p class=\"note\">Errors from the Jacobian; every data point is treated as independent, so they are too small.</p>"
            + "<h3>Figure</h3>" + figure(svg_model(res, ctx["rows"]), "Data (as used: solid; as calculated where corrected: open) and the model (black).")
            + "<h3>Scores</h3>" + scores_table(res) + "<h3>The tube it gives</h3>" + budget_table(res)
            + "<h3>Mean deviation of each source (model / data - 1)</h3>" + deviation_table(res))


def tab_summary(ctx):
    res = ctx["results"]
    sel = ctx["selected"]
    reasons = dict(ctx["reasons"])
    rows, cls = [], []
    for r in res:
        m = r["model"]
        if not r.get("ok"):
            rows.append([m.key, esc(m.name), m.nparam, "&mdash;", "&mdash;", "&mdash;", "&mdash;", "&mdash;", "&mdash;", esc(reasons.get(m.key, ""))])
        else:
            sc, b = r["scores"], r["bud"]
            rows.append([m.key, esc(m.name), m.nparam, pct(sc["rms_r"]), pct(sc["rms_U"]), pct(sc["rms_G"]), pct(sc["combined"]), pct(b["vf"][2]), pct(b["vf"][4]), esc(reasons.get(m.key, ""))])
        cls.append("sel" if m.key == sel else ("info" if m.info else ""))
    cards = ('<div class="cards"><div class="card">data points<b>%d r, %d U</b></div><div class="card">sources<b>%d</b></div><div class="card">models<b>%d</b></div>'
             '<div class="card">selected<b>%s</b></div></div>' % (len(ctx["obs"]["r"]["re"]), len(ctx["obs"]["U"]["re"]), len(set(ctx["obs"]["r"]["src"])), len(res), sel or "none"))
    selres = next((r for r in res if r["model"].key == sel), None)
    selected = ""
    if selres:
        m = selres["model"]
        selected = ("<h2>Selected model: %s &nbsp; %s</h2>" % (m.key, esc(m.name)) + eqs(m.equations)
                    + "<p>Parameters: %s.</p>" % ", ".join("%s = %s &plusmn; %s" % (esc(n), num(v, 4), num(e, 2)) for n, v, e in zip(m.names, selres["params"], selres["errors"])))
    return ("<h1>Fit of the tube closure: %s</h1><p class=\"sub\">Corrected data (%s), every source weighted equally; Re_lambda %s</p>" % (ctx["stamp"], ctx["corr_summary"], ctx["re_range"])
            + cards + "<h2>The models</h2>"
            + "<p>Scores are the weighted rms of the log residuals of the radius and the swirl, the same for every model, whatever it was fitted to; "
              "combined = sqrt((rms r<sup>2</sup> + rms U<sup>2</sup>)/2). V_f is the volume fraction the dissipation budget gives for the tube "
              "(sections 4&ndash;5 of the page) at Re_lambda = 300 and 2000. Click a header to sort.</p>"
            + table(["model", "description", "params", "rms r", "rms U", "rms G", "combined", "V_f (300)", "V_f (2000)", "status"], rows, left=(0, 1, 9), row_class=lambda i: cls[i])
            + selected
            + "<h2>How the selection is made</h2><p>Models marked information-only (two functions, or fitted to other data) are not candidates. A candidate must be physically sensible "
              "(finite r and U; V_f between 0.01 and 0.5 for Re_lambda 100&ndash;2000). Among the candidates, the selected model is the one with the fewest parameters whose "
              "combined score is within %.0f%% of the best; the smaller score decides a tie. The rule is a choice: the table shows the scores, so another tolerance gives another model.</p>"
              % (100 * (ctx["tolerance"] - 1)))


def tab_data(ctx):
    rows = []
    for x in ctx["rows"]:
        corrected = abs(x["factor_r"] - 1) > 1e-9 or abs(x["factor_u"] - 1) > 1e-9
        re = "%g" % x["re"] if x["re"] is not None else ("%g&ndash;%g" % (x["re_lo"], x["re_hi"]) if x["re_lo"] is not None else "&mdash;")
        rows.append([x["id"], esc(x["reference"]), x["group"], esc(x["tube_set"]), esc(x["method"]), re, num(x["r_raw"], 4), num(x["r"], 4), num(x["u_raw"], 4), num(x["u"], 4),
                     num(x["u"] * x["r"], 4) if x["u"] is not None and x["r"] is not None else "&mdash;", num(x["g"], 4), "yes" if corrected else ""])
    return ("<h2>The data</h2><p>One row per source, run and Re_lambda (data/tubes.csv); r = r_max/eta, U = U_max/U_eta, Re_c = r U, G = Gamma/nu = %.3f r U. "
            "Raw = as calculated from the paper; used = after the corrections of the Corrections tab. Rows with a range of Re_lambda are drawn but not fitted.</p>" % G0
            + table(["id", "reference", "group", "tube set", "method", "Re_lambda", "r raw", "r used", "U raw", "U used", "Re_c used", "G used", "corrected"], rows, left=(1, 2, 3, 4)))


def tab_corrections(ctx):
    rows = []
    for src, c in ctx["corrections"].items():
        refs = sorted(set(x["reference"] for x in ctx["rows"] if x["src"] == src))
        rows.append([esc(", ".join(refs) or src), "/ %g" % c.get("r_divisor", 1.0), "&times; %g" % c.get("u_factor", 1.0), esc(c.get("why", ""))])
    return ("<h2>Corrections</h2><p>Values used = value calculated from the paper, radius divided by r_divisor and swirl multiplied by u_factor "
            "(data/corrections.json; pass another file with --corrections). Sources not listed are used as calculated.</p>"
            + table(["source", "radius", "swirl", "reason"], rows, left=(0, 3))
            + "<h3>Left out of the fits</h3>" + table(["source", "reason"], [[esc(", ".join(sorted(set(x["reference"] for x in ctx["rows"] if x["src"] == k))) or k), esc(v)]
                                                                            for k, v in ctx.get("excluded", {}).items()], left=(0, 1))
            + "<p>These rows are drawn as grey crosses and are not fitted.</p>")


def tab_plots(ctx):
    return ("<h2>Radius and swirl against Re_lambda</h2><p>All data by methodology (colour) and reference (marker). Solid symbols are the values used; "
            "open symbols are the values as calculated from the paper where a correction was applied; horizontal bars are sources that give a range of Re_lambda.</p>"
            + figure(svg_data(ctx["rows"]), "r_max/eta and U_max/U_eta against Re_lambda."))


def tab_compare(ctx):
    rows = []
    for r in ctx["results"]:
        m = r["model"]
        if r.get("ok"):
            rows.append([m.key, esc(m.name), ", ".join("%s=%s" % (n, num(v, 4)) for n, v in zip(m.names, r["params"]))])
    return ("<h2>All models on the data</h2>" + figure(svg_compare(ctx["results"], ctx["rows"]), "All models (dashed: information only) over the data (pale).")
            + table(["model", "description", "parameters"], rows, left=(0, 1, 2)))


def tab_legacy(ctx):
    L = ctx["legacy"]
    if not L:
        return "<h2>Legacy model</h2><p>No result.</p>"
    return ("<h2>Legacy: the rescaling model on the values as calculated from the papers</h2>"
            "<p>The model of the earlier fits: every row is brought to the radius 5 by U = U'(r'/5)^n and one curve Re_c = c Re_lambda^k is fitted "
            "(sources Ghira 2022, Da Silva, Kida, Mouri 2004 and 2007; no corrections; each source weighted equally). It is information only: the corrections "
            "of the other models replace the exponent n.</p>" + eqs(["ln(5 U') = ln c + k ln Re - n ln(r'/5)"])
            + table(["parameter", "value", "error"], [["c", num(L["c"], 4), num(L["errors"][0] * L["c"], 2)], ["k", num(L["k"], 4), num(L["errors"][1], 2)], ["n", num(L["n"], 4), num(L["errors"][2], 2)]])
            + "<p>rms residual %s, %d points.</p>" % (pct(L["rms"]), L["n_points"]))


def tab_sensitivity(ctx):
    V = ctx["variants"]
    if not V:
        return "<h2>Sensitivity</h2><p>Not computed.</p>"
    rows = []
    for v in V:
        by = v["by"]
        def sc(key):
            return pct(by[key]["scores"]["combined"]) if key in by else "&mdash;"
        d1 = by.get("D1")
        d2 = by.get("D2")
        rows.append([esc(v["label"]), esc(v["selected"] or "none"),
                     ("U = %s Re^%s" % (num(d1["params"][0], 3), num(d1["params"][1], 3))) if d1 else "&mdash;",
                     ("r = %s, U = %s Re^%s" % tuple(num(p, 3) for p in d2["params"])) if d2 else "&mdash;",
                     sc("D1"), sc("D2"), sc("D3"), sc("C3"), sc("K4")])
    return ("<h2>Sensitivity to the corrections and to single sources</h2><p>The same fits under other choices; the combined score of each model "
            "(rms of the log residuals of r and U) and the parameters of D1 and D2. Scores of runs with different data are not comparable with each other, "
            "only the ranking of the models within a row.</p>"
            + table(["variant", "selected", "D1 (r = 5)", "D2", "D1", "D2", "D3", "C3", "K4"], rows, left=(0, 1, 2, 3)))


def tab_notes(ctx):
    return ("<h2>How this report was made</h2><ul>"
            "<li><b>Data:</b> %s (made by exportdata.py from the source data of the literature page); corrections: %s.</li>"
            "<li><b>Run:</b> <code>python fittingtool.py</code> in the folder fittingtool; <code>--corrections FILE</code> uses another correction file, <code>--exclude SRC,...</code> leaves sources out of the fits.</li>"
            "<li><b>Weights:</b> each source counts equally within a quantity; the fits are least squares of log(model/data).</li>"
            "<li><b>Errors:</b> from the Jacobian, treating points as independent; too small where the points of a source are correlated.</li>"
            "<li><b>Server:</b> the file is one document and needs no server. Opened through the report server (reportserver.bat FILE) it gets the server's interactivity.</li>"
            "</ul>" % (esc(ctx["files"]["data"]), esc(ctx["files"]["corrections"])))


def build_tabs(ctx):
    tabs = [("Summary", tab_summary(ctx)), ("Data", tab_data(ctx)), ("Corrections", tab_corrections(ctx)), ("R and U", tab_plots(ctx)), ("Compare", tab_compare(ctx))]
    for r in ctx["results"]:
        tabs.append((r["model"].key, tab_model(r, ctx)))
    tabs.append(("Sensitivity", tab_sensitivity(ctx)))
    tabs.append(("Legacy", tab_legacy(ctx)))
    tabs.append(("Notes", tab_notes(ctx)))
    return tabs


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write_report(results_dir, ctx):
    tabs = build_tabs(ctx)
    buttons = "".join('<button class="btab%s" data-go="run%d" data-name="%s">%s</button>' % (" on" if i == 0 else "", i, esc(name), esc(name)) for i, (name, _) in enumerate(tabs))
    panels = "".join('<div class="bpanel" data-group="run" id="run%d"%s>\n%s\n</div>\n' % (i, "" if i == 0 else " hidden", body) for i, (_, body) in enumerate(tabs))
    page = ('<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n<meta name="generator" content="fittingtool">\n<title>fit %s</title>\n<style>\n%s</style>\n</head>\n<body>\n<main>\n'
            '<div class="bbar">%s</div>\n%s</main>\n<script>\n%s</script>\n</body>\n</html>\n'
            % (esc(ctx["stamp"]), read(os.path.join(HERE, "html", "page.css")), buttons, panels, read(os.path.join(HERE, "html", "page.js"))))
    os.makedirs(results_dir, exist_ok=True)
    local = time.localtime()
    base = "fit_%s" % time.strftime("%Y.%m.%d_%H;%M", local)
    names = [base, base + time.strftime(".%S", local)] + [base + time.strftime(".%S", local) + chr(97 + i) for i in range(26)]
    for name in names:
        try:
            with open(os.path.join(results_dir, name + ".html"), "x", encoding="utf-8") as f:
                f.write(page)
            return f.name
        except FileExistsError:
            continue
    raise FileExistsError("no free report name")


def write_index(results_dir):
    """index.html: a file tree of the report files (grouped by date, newest first) and of the tool's data and configuration files."""
    files = sorted((n for n in os.listdir(results_dir) if n.endswith(".html") and n != "index.html"), reverse=True)
    groups = {}
    for n in files:
        m = re.search(r"(\d{4}\.\d{2}\.\d{2})", n)
        groups.setdefault(m.group(1) if m else "other", []).append(n)
    tree = []
    for i, (day, names) in enumerate(sorted(groups.items(), reverse=True)):
        items = []
        for n in names:
            path = os.path.join(results_dir, n)
            items.append('<li><a href="%s">%s</a> <span class="meta">%d KB, %s</span></li>' % (esc(n), esc(n), os.path.getsize(path) // 1024,
                                                                                               time.strftime("%H:%M", time.localtime(os.path.getmtime(path)))))
        tree.append("<li><details%s><summary>%s &nbsp;<span class=\"meta\">%d report%s</span></summary><ul>%s</ul></details></li>" % (" open" if i == 0 else "", esc(day), len(names), "" if len(names) == 1 else "s", "".join(items)))
    other = []
    for label, rel in (("data/tubes.csv", "../data/tubes.csv"), ("data/corrections.json", "../data/corrections.json"), ("README.md", "../README.md")):
        other.append('<li><a href="%s">%s</a></li>' % (rel, label))
    page = ('<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n<title>fitting tool: reports</title>\n<style>\n%s</style>\n</head>\n<body>\n<main class="ftv">\n'
            '<h1>Fitting tool: reports</h1><p class="sub">One file per run, newest first. The files open without the report server; opened through it (reportserver.bat FILE) they get its interactivity.</p>'
            '<ul><li><details open><summary>results</summary><ul>%s</ul></details></li><li><details open><summary>tool files</summary><ul>%s</ul></details></li></ul>\n</main>\n</body>\n</html>\n'
            % (read(os.path.join(HERE, "html", "page.css")), "".join(tree), "".join(other)))
    path = os.path.join(results_dir, "index.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)
    return path
