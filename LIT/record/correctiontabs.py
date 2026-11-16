r"""correctiontabs.py  The corrections of every paper in its tab of the recording book.

fill(book) adds to each paper tab a section 'Corrections' with
  (1) the correction ADOPTED for the fits of the paper (fittingtool/data/corrections.json: the radius divided by r_divisor, the swirl multiplied by u_factor; 'none' where the value of the paper is used as calculated) and its reason;
  (2) for the probe papers (Belin et al., Mouri et al. 2004, 2007, Mouri and Hori 2009, Sassa and Makita) the multipliers COMPUTED from the wire-and-tube model and its one-dimensional extension, against Re_lambda (analysis/belin_correctors*.json): the values used in Fig. 1b of the paper, not in the fits;
  (3) for Ghira et al. (2022, 2025) the derivation of the factors from the all-tube population of Pirozzoli (2012), as in section 9a of the paper, and in the tab of Pirozzoli the use of that paper as the reference.

VERSION  M1 m01.v01 (2026-11-15): first version.
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LIT = os.path.dirname(HERE)
ANALYSIS = os.path.join(LIT, "analysis")
sys.path.insert(0, ANALYSIS)

__all__ = ["fill"]

CORRECTIONS = os.path.join(LIT, "fittingtool", "data", "corrections.json")
# tab id -> list of (heading of the pair of columns, key of the radius multiplier, key of the swirl multiplier, json file, how to read a row)
PROBES = {
    "belin1996": [("Belin's wire (radius: shape match; swirl: his rule dS/(2 x 0.14))", "belin_correctors.json", ("r", "Belin's wire", "shape"), ("U", "Belin's wire, published rule dS/(2 x 0.14)", "shape"))],
    "mouri2007": [("Mouri et al. 0.1 % class", "belin_correctors.json", ("r", "Mouri 0.1%", "shape"), ("U", "Mouri 0.1%", "shape")), ("Mouri et al. 1 % class", "belin_correctors.json", ("r", "Mouri 1%", "shape"), ("U", "Mouri 1%", "shape"))],
    "mouri2004": [("Mouri et al. 1 % class", "belin_correctors.json", ("r", "Mouri 1%", "shape"), ("U", "Mouri 1%", "shape"))],
    "mouri2009": [("Mouri and Hori, all-tube average (amplitude cut 0.33 sigma)", "belin_correctors_all.json", ("k=0.33", "m_r", None), ("k=0.33", "m_U", None))],
    "sassa2005": [("Sassa and Makita (threshold C = 2.5)", "belin_correctors_sassa.json", ("C=2.5", "m_r", None), ("C=2.5", "m_U", None))],
}


def load(name):
    with open(os.path.join(ANALYSIS, name), encoding="utf-8") as f:
        return json.load(f)


def number(v):
    return "&ndash;" if v is None else "%.2f" % v


def pick(row, spec):
    """A multiplier from a row of a correctors file: spec = (group, key, field) or (group, field, None)."""
    group, key, field = spec
    return row[group][key][field] if field else row[group][key]


def next_number(tab):
    import re
    n = 0
    for kind, markup in tab.lines:
        found = re.match(r"^(\d+)\.", markup) if kind == "h" else None
        if found:
            n = max(n, int(found.group(1)))
    return n + 1


def ghira_table():
    """The rows of Table D3 of the paper (the cut of Ghira et al. on the population of Pirozzoli, 35 % filling and the other fillings)."""
    import ghira_cut_factors as gcf
    import ghira_cut_families as gcfam
    import ghira_cut_g80 as g80
    r, pr, u, pu = gcf.population()
    rf, uf, narrow, _ = gcfam.population()
    rows = []
    for phi in (0.10, 0.20, 0.35):
        for g0 in (80.0, 94.0):
            c = g80.constant_g(r, pr, g0, phi)
            rows.append(["%.0f %%" % (100 * phi), "G constant, %.0f" % g0, "%.2f" % c["wc"], "%.2f" % c["r_c"], "%.2f" % c["kept"], "%.2f" % c["er"], "%.2f" % c["eu"], "%.2f" % (g80.NARROW_MEAN / c["er"]), "%.2f" % (c["mean_u"] / c["eu"])])
        c = gcfam.cut(rf, uf, narrow, phi)
        rows.append(["%.0f %%" % (100 * phi), "r and G independent", "%.2f" % c["wc"], "&ndash;", "%.2f" % c["kept"], "%.2f" % c["er"], "%.2f" % c["eu"], "%.2f" % c["f_R"], "%.2f" % c["f_U"]])
    return rows


def fill(book):
    import recordtabs
    with open(CORRECTIONS, encoding="utf-8") as f:
        data = json.load(f)
    adopted, excluded, quantities = data.get("corrections", {}), data.get("excluded", {}), data.get("excluded_quantities", {})
    for src, tab_id in recordtabs.TAB_ID.items():
        tab = next((t for t in book.tabs if t.id == tab_id), None)
        if tab is None:
            continue
        tab.h("%d. Corrections" % next_number(tab))
        c = adopted.get(src)
        if c:
            tab.table(["quantity", "correction adopted for the fits", "value used"], [["radius r_max/&eta;", "divided by %.4g (&times; %.4g)" % (c.get("r_divisor", 1.0), 1.0 / c.get("r_divisor", 1.0)), "as calculated &times; %.4g" % (1.0 / c.get("r_divisor", 1.0))],
                                                                                    ["swirl U_max/U_&eta;", "multiplied by %.4g" % c.get("u_factor", 1.0), "as calculated &times; %.4g" % c.get("u_factor", 1.0)]],
                      "The correction of this paper as used in the fits and in the data table of the paper (fittingtool/data/corrections.json). The circulation &Gamma;/&nu; and the tube Reynolds number follow as the product of the corrected radius and swirl.")
            tab.p("<b>Rationale:</b> " + c.get("why", ""))
        else:
            tab.p("<b>Correction adopted for the fits:</b> none; the values enter as calculated from the paper (the data table of the paper shows them with a factor of 1).")
        if src in excluded:
            tab.p("<b>Not fitted:</b> " + excluded[src])
        if src in quantities:
            tab.p("<b>Quantities not fitted:</b> " + "; ".join("%s: %s" % (q, why) for q, why in quantities[src].items()))
        if tab_id in PROBES:
            tab.p("<b>Corrections computed from the models of the probes</b> (the wire-and-tube model fitted to Figs. 5 and 6 of Belin et al. and its one-dimensional extension to the methods of Mouri et al. and Sassa and Makita; analysis/belin_correctors*.json): a multiplier, interpolated in ln Re<sub>&lambda;</sub>, that brings the value read to the tubes of the model population. They are used in Fig. 1b of the paper (bottom row) and are <b>not</b> the corrections of the fits above.")
            for title, fname, spec_r, spec_u in PROBES[tab_id]:
                rows = load(fname)
                body = [["%d" % round(r["Re_lambda"]), number(pick(r, spec_r)), number(pick(r, spec_u))] for r in rows]
                tab.table(["Re<sub>&lambda;</sub>", "radius multiplier", "swirl multiplier"], body, "%s: corrected value = multiplier &times; value as read." % title)
        if src in ("Ghira22", "Ghira25"):
            tab.p("<b>Derivation of the factors (radius &times; 1.25, swirl &times; 0.67; section 9a of the paper).</b> The criterion of this paper keeps the strongest 1 % of the volume by vorticity, a subset of the tubes. Reference: Pirozzoli (2012), the pdfs of the radius r<sub>0</sub> and of the maximum velocity v<sub>0</sub> of all the vortex cores found, with no lower threshold on the vorticity. "
                  "Steps: (1) the row is the mean r<sub>max</sub> and U<sub>max</sub> of the structures above the vorticity &omega;<sub>c</sub> that holds 1 % of the volume; (2) the reference population is that of Pirozzoli; (3) a Burgers tube has &omega;<sub>0</sub> = 3.512 U/r in units of the rms vorticity 1/&tau;<sub>&eta;</sub>; "
                  "(4) the radius and the swirl are linked by his most frequent circulation &Gamma;/&nu; = 80, G = 8.784 r U, in two versions (G constant; r and G independent); (5) the cut &omega;<sub>c</sub> is fixed so that the volume above it, 2&pi;R<sup>2</sup>L ln(&omega;<sub>0</sub>/&omega;<sub>c</sub>), is 1 % of the flow when all the tubes fill 35 % of it (the volume of a tube &pi; r<sub>max</sub><sup>2</sup>L); "
                  "(6) the kept tubes are about 45 % of the tubes, of small radius; (7) the multipliers are the reference over the kept tubes: radius, the mean of the narrow family of the radius pdf (4.55 &eta;) over the mean radius of the kept tubes, 1.22&ndash;1.28; swirl, the mean of all tubes over that of the kept tubes, 0.66&ndash;0.68; (8) used: 1.25 and 0.67.")
            tab.table(["tubes fill", "pairing", "&omega;<sub>c</sub>/&omega;<sub>rms</sub>", "r<sub>c</sub>", "kept", "mean r kept", "mean U kept", "f<sub>R</sub>", "f<sub>U</sub>"], ghira_table(),
                      "The cut of Ghira et al. on the all-tube population of Pirozzoli (2012); f<sub>R</sub> brings the radius of the kept tubes to the mean of the narrow family (4.55 &eta;), f<sub>U</sub> the swirl to the mean of all tubes (analysis/ghira_cut_g80.py, ghira_cut_families.py).")
        if tab_id == "pirozzoli":
            tab.p("<b>Use as the reference of the correction of Ghira et al.</b> The pdfs of the radius and of the maximum velocity of this paper (Fig. 2; digitised above), linked by the most frequent circulation &Gamma;/&nu; = 80 of its text (p. 5), are the all-tube population to which the factors of Ghira et al. (radius &times; 1.25, swirl &times; 0.67) are referred: see the tabs of Ghira et al. (2022, 2025) and section 9a of the paper. His text says the expected radius is about 6 &eta; and the velocity about 2 u<sub>K</sub>; the mean of the digitised pdf is 7.2 &eta; (the far tail sets it) and 2.5 u<sub>K</sub>.")
