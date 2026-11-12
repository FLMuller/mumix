r"""srctabs.py  The pages of the papers behind the generic tabs: the table or figure each source's numbers come from, cut out of the pdf.

fill(book) appends, to the tab of each source in SPECS, a step with the cut-outs. A cut-out is found by its caption (find_crop: the line that starts with the text of the caption, in
the pdf of LIT/), and is the full page width from just above the caption down by a fraction of the page height. Where a caption is not found the step says so (in red).

VERSION  M1 m01.v01 (2026-11-12): first version.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from recordbook import pdfcrop       # noqa: E402

__all__ = ["fill", "find_crop", "SPECS"]

LIT = os.path.dirname(HERE)
NEWLINE, RETURN = chr(10), chr(13)

# tab id: [(pdf, caption text to search, height of the cut-out as a fraction of the page, what it shows)]
SPECS = {
    "ghira2022": [("Ghira (2022).pdf", "Table III", 0.30, "Table III: the mean values of the intense vorticity structures, one row for each simulation."),
                  ("Ghira (2022).pdf", "Table II", 0.28, "Table II: the simulations (ν in code units).")],
    "ghira2025": [("Ghira (2025).pdf", "Table 2", 0.32, "Table 2: the characteristics of the intense vorticity structures of all the simulations."),
                  ("Ghira (2024).pdf", "Table 1", 0.30, "Ghira et al. (2024), Table 1: the simulations (ν).")],
    "jimenez1993": [("Jimenez (1993).pdf", "Table 3", 0.30, "Table 3: the average worm characteristics, one row for each simulation.")],
    "aligolzadeh2023": [("Aligolzadeh (2023).pdf", "Fig. 12|Figure 12|FIG. 12", 0.30, "Fig. 12: the ratio of the radius of the vortices to the Burgers radius.")],
    "dasilva2011": [("Da Silva (2011).pdf", "Table 1", 0.28, "Table 1.")],
    "mouri2009": [("Mouri (2009).pdf", "Table 2", 0.38, "Table 2: the parameters of the vortex tubes, B1&ndash;B6 and D1&ndash;D5."),
                  ("Mouri (2009).pdf", "Table 1", 0.30, "Table 1: the flows and their Re_λ.")],
    "mouri2007": [("Mouri (2007).pdf", "Table II", 0.40, "Table II: radius, maximum circulation velocity and Re_0 of the intense structures."),
                  ("Mouri (2007).pdf", "Table I", 0.30, "Table I: the experiments (ν).")],
    "mouri2004": [("Mouri (2004).pdf", "Table I", 0.40, "Table I: experimental conditions and the parameters of the vortex tubes.")],
    "mouri2003": [("Mouri (2003).pdf", "Table I", 0.30, "Table I: the ten grid-turbulence experiments.")],
    "belin1996": [("Belin (1996).pdf", "Fig. 5|Figure 5|FIG. 5", 0.30, "Fig. 5: the size distributions of the worms.")],
    "kida2002": [("Kida (2002).pdf", "Table 2", 0.30, "Table 2: the characteristic quantities of the low-pressure vortices."),
                 ("Kida (2002).pdf", "Table 1", 0.25, "Table 1: Re_λ and ν in code units.")],
    "sassa2005": [("Sassa (2005).pdf", "Table 1", 0.30, "Table 1: the flows."), ("Sassa (2005).pdf", "Fig. 8|Figure 8|FIG. 8", 0.30, "Fig. 8: the dependence on Re_λ.")],
}


def find_crop(pdf, query, below, above=0.015, scale=2.6):
    """(image, page number) of the cut-out that starts above the line that begins with `query` in LIT/<pdf> and runs `below` of the page height down, or (None, 0) if no line begins with it."""
    import pypdfium2
    doc = pypdfium2.PdfDocument(os.path.join(LIT, pdf))
    for number in range(len(doc)):
        page = doc[number]
        text = page.get_textpage()
        width, height = page.get_size()
        for variant in query.split("|"):
            searcher = text.search(variant, match_case=False)
            while True:
                hit = searcher.get_next()
                if hit is None:
                    break
                index, count = hit
                before = text.get_text_range(index - 1, 1) if index > 0 else NEWLINE
                after = text.get_text_range(index + count, 1)
                follow = text.get_text_range(index + count + 1, 1)
                caption = after in '.:' + NEWLINE + RETURN or (after == ' ' and (follow.isupper() or follow in (NEWLINE, RETURN)))      # 'Table 2.', 'Table 2:', 'Table 2' then the title, 'Fig. 7 Probability ...'; not 'Table 2 lists ...'
                if before in (NEWLINE, RETURN) and caption:                  # the line starts with the caption: not a mention in a sentence
                    left, bottom, right, top = text.get_charbox(index)
                    y0 = max(0.0, 1 - top / height - above)
                    y1 = min(1.0, y0 + min(0.6, below * 1.4) + above)      # a table is longer than its caption suggests: 40 % more
                    return pdfcrop(pdf, number + 1, (0, y0, 1, y1), scale), number + 1
    return None, 0


def fill(book):
    for tab in book.tabs:
        specs = SPECS.get(tab.id)
        if not specs:
            continue
        tab.h("5. The pages of the paper: where the numbers are (cut out of the pdf)")
        for pdf, query, below, caption in specs:
            image, page = find_crop(pdf, query, below)
            if image is None:
                tab.p(tab.guess("no cut-out for '%s' of %s" % (query, pdf), "no line of the pdf starts with that caption, so the page was not found by program"))
            else:
                tab.img(image, "%s (page %d of the pdf %s)" % (caption, page, pdf))
        tab.p("Compare these with the table of step 2: every entry is a number printed above. Comment on any line here where the number we typed differs from the page.")
