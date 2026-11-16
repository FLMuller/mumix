"""dns_table.py  v01  The DNS rows of the data (fittingtool/data/tubes.csv, values as calculated from the papers, no correction) as a table whose cell layout follows the bracket notation
        [hdr; ref, [Re_lambda, r_max, U_max, G; next row ...], criterion]
one header row over all the columns (the columns of the sub-brackets included); the rows of a source are listed under each other and the cells of its reference and of its criterion span them (grow in height).
Only rows with at least two of the three numbers r_max, U_max, G are listed (G = 8.784 r U; the listed Gamma/nu where there is no U).
Usage    python dns_table.py     writes ../dns_table.html
Versions M01 m01.v02 (2026-11-14): one header row over all columns (the sub-rows have no header of their own); reference and criterion cells span the rows.
         M01 m01.v01 (2026-11-14): first version.
"""
import csv
import html
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(os.path.dirname(HERE), "fittingtool", "data", "tubes.csv")
OUT = os.path.join(os.path.dirname(HERE), "dns_table.html")
G0 = 8.784

# source key -> criterion text (radius definition, selection, distribution if any)
CRITERION = {
    "Ghira22": "Intense vorticity structures: the 1% of the volume with the highest vorticity magnitude. R_ivs is where the azimuthal mean of the axial vorticity falls to 1/e of its axis value; r_max = 1.12 R_ivs / (R_ivs/R_B); mean over the structures (Table III); no distribution used. U_max: the swirl at R_ivs converted to the Burgers peak.",
    "Ghira25": "As Ghira et al. (2022): 1%-volume structures, 1/e radius, R_ivs/R_B = 0.97 assumed. The other rows of its Table 2 repeat the 2022 runs.",
    "Jimenez93": "Worms: connected regions of the 1% of the volume with the highest vorticity. The radius is the 1/e radius of a Gaussian fitted to the azimuthal mean of the axial vorticity (the Burgers radius), r_max = 1.12 R; average over the worms (Table 3). G is the listed circulation; U_max is derived from it (G / 8.784 r_max).",
    "Kida02": "Low-pressure vortex cores (31-35% of the volume). r_max = D/2, D the diameter of the non-circular core boundary, mean over the cores. The paper lists Gamma/nu = 110 and 123, below 8.784 r U because the boundary is at about 0.6 r_max (assumption of the page).",
    "DaSilva11": "Intense vorticity structures as in Ghira (1% of the volume). R is the 1/e radius of the vorticity, r_max = 1.12 R / (R/R_B). U_max from u_0/u' (the paper's own Table 1 gives a swirl 2.5 times larger; unresolved).",
    "Pirozzoli09": "Vortex cores scanned out of the DNS database without a vorticity threshold (candidate centres at pressure minima, r_0 the radius of maximum velocity), all classes of vortices. Pirozzoli (2012) quotes the typical values 6 eta and 2 u_K for all his Re_lambda, without a table.",
    "Wang07": "Coherent fine-scale eddies (second invariant Q, no threshold) of a spatially developing mixing layer, the most expected values of the pdfs (the mode): D about 8 eta, so r_max = D/2 = 4; swirl falling from 2.0 u_K in the transition to 1.2 u_K fully developed (the row is the mean, 1.6). Re_lambda = 115: the flat end of the curve of his Fig. 1a (centre of the layer).",
    "Miyauchi06": "Coherent fine-scale eddies of channel flow, the most expected values of the pdfs (the mode): D = 10 eta near the wall and 8.5 eta in the logarithmic region, swirl 2.0 and 1.7 u_K (the row is the mean of the two). r_max = D/2. The channel has no isotropic Re_lambda in the paper.",
}
REFERENCE = {"Pirozzoli09": "Pirozzoli (2012), typical tubes", "Wang07": "Wang et al. (2007), mixing layer", "Miyauchi06": "Miyauchi et al. (2006), channel"}
ORDER = ["Ghira22", "Ghira25", "Jimenez93", "Kida02", "DaSilva11", "Pirozzoli09", "Wang07", "Miyauchi06"]


def number(text):
    return float(text) if text not in ("", None) else None


def main():
    groups = {k: [] for k in ORDER}
    ref = {}
    for rec in csv.DictReader(open(CSV, encoding="utf-8")):
        s = rec["src"]
        if s == "Wall":                                                             # the three wall-flow papers share one source in the data: the Wang row has Re_lambda 115, the Miyauchi row none (the Das row has only r)
            s = "Wang07" if rec["re_lo"] == "115" else "Miyauchi06"
        if s not in groups:
            continue
        r, u, gl = number(rec["r_raw"]), number(rec["u_raw"]), number(rec["gamma_listed"])
        g = G0 * r * u if r is not None and u is not None else gl
        if sum(v is not None for v in (r, u, g)) < 2:
            continue
        lo, hi = number(rec["re_lo"]), number(rec["re_hi"])
        groups[s].append(("-" if lo is None else "%g" % lo, r, u, g, gl if (gl is not None and r is not None and u is not None and abs(gl - g) > 2) else None))
        ref[s] = REFERENCE.get(s, html.unescape(rec["reference"]))
    css = ("body{font-family:Segoe UI,Arial,sans-serif;margin:24px;color:#222}table{border-collapse:collapse}"
           "td,th{border:1px solid #888;padding:3px 10px;vertical-align:top}th{font-weight:600;color:#444;background:#f0f0f0}"
           "td.num{text-align:right}td.ref{font-weight:600;white-space:nowrap}td.crit{max-width:520px;font-size:0.92em}"
           "tr.first>td{border-top:2px solid #444}p.note{max-width:900px;color:#555;font-size:0.92em}")
    out = ["<!doctype html><html><head><meta charset='utf-8'><title>DNS data</title><style>%s</style></head><body>" % css,
           "<h2>DNS tube data: [ref;Re_&lambda;, r<sub>max</sub>, U<sub>max</sub>, G; ...; criterion]</h2>",
           "<p class='note'>Layout [hdr;ref,[Re,r,U,G;rows...],criterion]: one header row over all columns; the rows of a source are listed under each other, and its reference and criterion cells span them. "
           "Values as calculated from the papers (no correction). r<sub>max</sub> in &eta;, U<sub>max</sub> in U<sub>&eta;</sub>, G = &Gamma;/&nu; = 8.784 r U. Rows with at least two of the three numbers. "
           "A dash: no isotropic Re<sub>&lambda;</sub> given.</p>",
           "<table><thead><tr><th>reference</th><th>Re<sub>&lambda;</sub></th><th>r<sub>max</sub></th><th>U<sub>max</sub></th><th>G</th><th>criterion for r<sub>max</sub> (and distribution, if any)</th></tr></thead><tbody>"]
    for s in ORDER:
        if not groups[s]:
            continue
        n = len(groups[s])
        for i, (re, r, u, g, gl) in enumerate(groups[s]):
            cells = ["" if v is None else f for v, f in ((r, "%.2f" % r if r is not None else ""), (u, "%.2f" % u if u is not None else ""), (g, "%.0f" % g if g is not None else ""))]
            extra = "" if gl is None else " <span title='listed by the paper'>(listed %.0f)</span>" % gl
            head = "<td class='ref' rowspan='%d'>%s</td>" % (n, html.escape(ref[s])) if i == 0 else ""
            tail = "<td class='crit' rowspan='%d'>%s</td>" % (n, html.escape(CRITERION[s])) if i == 0 else ""
            out.append("<tr%s>%s<td class='num'>%s</td><td class='num'>%s</td><td class='num'>%s</td><td class='num'>%s%s</td>%s</tr>" % (" class='first'" if i == 0 else "", head, re, cells[0], cells[1], cells[2], extra, tail))
    out.append("</tbody></table></body></html>")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print("wrote", OUT, sum(len(v) for v in groups.values()), "rows")


if __name__ == "__main__":
    main()
