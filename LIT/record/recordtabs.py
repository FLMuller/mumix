r"""recordtabs.py  The content of the recording book: one function per tab, and fill(book) that makes them all (recordbook.py draws them).

A tab for a paper is a list of steps. Every number of the table in the summary tab is made again here from the paper's own numbers:
the generic tab of a source (generic_tab) takes its rows from sourcedata.py (what we typed from the paper) and shows the chain
paper number -> converted -> corrected -> SI with the formulas and a worked example; the pdf sources (Tanahashi 2001 and 2004, Das 2006,
Pirozzoli 2012) have their own tabs (pdftabs.py) with the figure, the digitising, the fits and the grid and detection of each.
Anything we guessed is written with tab.guess(what, why): red in the page, listed at the top of the tab and in the summary.

VERSION  M1 m01.v01 (2026-11-12): first version: the summary tab, the generic tab of every source.
"""
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ANALYSIS = os.path.join(os.path.dirname(HERE), "analysis")
sys.path.insert(0, ANALYSIS)
sys.path.insert(0, HERE)

import sourcedata as sd                     # noqa: E402
import build_data_sections as bds           # noqa: E402
from recordbook import plain                # noqa: E402

__all__ = ["fill"]

TAB_ID = {"Ghira22": "ghira2022", "Ghira25": "ghira2025", "Jimenez93": "jimenez1993", "Tanahashi01": "tanahashi2001", "Aligolzadeh23": "aligolzadeh2023",
          "DaSilva11": "dasilva2011", "Mouri09": "mouri2009", "Mouri07": "mouri2007", "Mouri04": "mouri2004", "Mouri03": "mouri2003", "Belin96": "belin1996",
          "Kida02": "kida2002", "Pirozzoli09": "pirozzoli", "Ishihara13": "ishihara", "Sassa05": "sassa2005", "Wall": "das2006"}


def number(v, fmt="%.4g"):
    return "&mdash;" if v is None else fmt % v


def generic_tab(book, src):
    """The tab of a source made from sourcedata.py alone: the places in the paper, how its numbers were taken, and the chain of conversions to the table row."""
    tab = book.tab(TAB_ID[src["key"]], src["short"].replace("&eacute;", "é"))
    tab.h("1. The paper and where the numbers are")
    tab.p("<b>%s</b>. Tube set: <b>%s tubes</b>. Method: %s." % (plain(src["cite"]).replace("&eacute;", "é"), src["tubes"], src.get("method", "")))
    tab.p("Where in the paper: %s" % plain(src["where"]))
    tab.p("What was measured, and how the tubes were picked: %s" % plain(src["selection"]))
    tab.p("<i>The page of the paper and a screenshot of the table or figure are still to be added to this tab (the text layer of the pdf was used so far).</i>")
    tab.h("2. The numbers as we typed them from the paper")
    head = ["quantity", r"\(Re_\lambda\)", r"\(\nu\) (paper's units)", r"\(\varepsilon\) (paper's units)", "entries of the paper", "value used", "role", "note"]
    rows = []
    for r in src["rows"]:
        mark = ""
        if "assum" in (" ".join(map(str, r["raw"])) + r["note"]).lower():
            mark = " " + tab.guess("a value assumed in the page", "the paper does not give it: %s" % (r["note"] or " ".join(map(str, r["raw"]))))
        rows.append([plain(sd.MSHORT[r["mtype"]]), str(r["Re"]), bds.nu_text(r["nu"]), bds.eps_text(r["eps"]), plain(", ".join(map(str, r["raw"]))) + mark,
                     bds.num(r["used"]) if hasattr(bds, "num") else "%.4g" % r["used"], "fitted" if r["role"] == "fit" else "comparison", plain(r["note"])])
    tab.table(head, rows, "One row for each number: the entries are the numbers printed in the paper (or read from its text), 'value used' is what the conversions below make of them.")
    if src.get("notes"):
        tab.p("Remarks in the page: %s" % plain(src["notes"]))
    tab.h("3. The conversions")
    for eq in src.get("eqs", []):
        tab.math(eq)
    tab.p(r"The Burgers vortex: \(x=1.2564312\) is the root of \(e^{x}-2x-1=0\), \(K_B=1-e^{-x}=0.71531\), \(r_{\max}=\sqrt{x}\,R_B=1.1209\,R_B\), "
          r"\(U_{\max}=K_B\,\Gamma/(2\pi r_{\max})\), so \(\Gamma/\nu=(2\pi/K_B)\,Re_c=8.784\,Re_c\) with \(Re_c=r_{\max}U_{\max}/\nu\).")
    items = [it for it in bds.tube_items(corrected=True) if it["src"] == src["key"]]
    tab.h("4. From the entries to the row of the summary table")
    if not items:
        tab.p("No row of the summary table (this source has no tube values that the table can complete).")
        return tab
    head = [r"\(Re_\lambda\)", r"\(r_{\max}/\eta\) (as read)", "× factor", r"\(r_{\max}/\eta\) used", r"\(U_{\max}/U_\eta\) (as read)", "× factor", r"\(U_{\max}/U_\eta\) used", r"\(Re_c=\beta U\)", r"\(\Gamma/\nu\)", "table: included?"]
    rows = []
    for it in items:
        rows.append([str(it["Re"]), number(it["beta_raw"], "%.3f"), "%.3g" % it["fr"], number(it["beta"], "%.3f"), number(it["U_raw"], "%.3f"), "%.3g" % it["fu"], number(it["U"], "%.3f"),
                     number(it["rec"], "%.2f"), number(it["RG"], "%.1f"), it["included"] or "yes"])
    tab.table(head, rows, r"Radius and swirl in units of \(\eta\) and \(U_\eta=(\nu\varepsilon)^{1/4}\), the correction factors of the page (sourcedata.CORR: Mouri and Hori radius ÷ 1.75 and swirl × 3, Ghira swirl × 0.6; the others 1).")
    first = items[0]
    if first["eta"]:
        nu, eps = None, None
        r0 = next(r for r in src["rows"])
        nu, eps, eta, how = sd.physical(r0)
        tab.p(r"Worked example, the first row (\(Re_\lambda\) = %s). The model side needs lengths in metres, so \(\eta\) is made from a \(\nu\) and an \(\varepsilon\) (%s):" % (first["Re"], "measured in the paper" if how == "measured" else
              "reference values: " + tab.guess("water, ν = 1e-6 m²/s, ε = 0.1 W/kg", "the paper's flow has no physical units, and the page converts every length given in η with these reference values")))
        tab.math(r"\eta=\left(\frac{\nu^3}{\varepsilon}\right)^{1/4}=\left(\frac{(%.3g)^3}{%.3g}\right)^{1/4}=%.4g\ \mathrm{m}=%.4g\ \mu\mathrm{m}" % (nu, eps, eta, eta * 1e6))
        tab.math(r"U_\eta=(\nu\varepsilon)^{1/4}=%.4g\ \mathrm{m/s}=%.4g\ \mathrm{mm/s}" % ((nu * eps) ** 0.25, (nu * eps) ** 0.25 * 1e3))
        if first["beta"] is not None:
            tab.math(r"r_{\max}=\beta\,\eta=%.3f\times%.4g\ \mu\mathrm{m}=%.4g\ \mu\mathrm{m}" % (first["beta"], eta * 1e6, first["beta"] * eta * 1e6))
        if first["U"] is not None:
            tab.math(r"U_{\max}=U\,U_\eta=%.3f\times%.4g\ \mathrm{mm/s}=%.4g\ \mathrm{mm/s}" % (first["U"], (nu * eps) ** 0.25 * 1e3, first["U"] * (nu * eps) ** 0.25 * 1e3))
        if first["beta"] is not None:
            tab.math(r"\gamma=\frac{4x}{\beta^2}\left(\frac{\varepsilon}{\nu}\right)^{1/2}=\frac{4\times1.2564}{%.3f^2}\left(\frac{%.3g}{%.3g}\right)^{1/2}=%.4g\ \mathrm{s^{-1}}" % (first["beta"], eps, nu, first["gam"] or float("nan")))
    else:
        tab.p("This row has no η, so no physical units: " + tab.guess("the row is shown without η, u_η, r_max, U_max, γ and Γ in SI units",
              r"the paper gives no single \(Re_\lambda\) or no \(\nu\) and \(\varepsilon\), so the page cannot place it on the \(Re_\lambda\) axis"))
    return tab


def summary_tab(book):
    tab = book.tab("summary", "Summary")
    tab.h("The recording book")
    tab.p("One tab for each paper, from the paper to the numbers of the table below. Click a line to comment on it: the box at the bottom takes your comment and saves it "
          "(comments.notes, beside this page). Our guesses are in <span class=\"guess\">red</span>; this tab ends with a list of all of them.")
    tab.h("The table of the tube data used by the model (the data table of the page)")
    tab.p(r"Each row is one source at one \(Re_\lambda\). 'a' to 'e' on a reference are the page's footnotes (corrections and augmentations). Every row is made again, step by step, in the tab of its source.")
    tab.add("t", "<div class=\"tablebox\">" + plain(bds.model_input_table()) + "</div>")
    return tab


def guess_index(book, tab):
    tab.h("All the guesses of the book")
    rows = []
    for t in book.tabs:
        for k, (gid, what, why) in enumerate(t.guesses, 1):
            rows.append(["<b>%s</b>, guess %d" % (t.title, k), "<span class=\"guess\">%s</span>" % what, why])
    tab.table(["where", "what we guessed", "why"], rows, "%d guesses. Each is in red in the tab named, and the tab lists its own at the top." % len(rows))


def fill(book):
    summary = summary_tab(book)
    for src in sd.SOURCES:
        generic_tab(book, src)
    import pdftabs
    import srctabs
    pdftabs.fill(book)
    srctabs.fill(book)
    guess_index(book, summary)
