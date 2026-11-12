"""build_fit_sections.py  v01  Write sections 10 (the fits tried) and 11 (the selected model) of the page from a run of the fitting tool.

Runs LIT/fittingtool (fittingtool.run: the data of tubes.csv with the corrections of corrections.json, every model, the sensitivity variants) and replaces the block
between the headings '<h2>10. ...' and '<h2>References</h2>' of ../vortex-energy-balance.html with the two sections.  Re-running replaces them again.
Section 10 gives every fit as equations with its parameters and scores (all models in one table, so people can see the range of things tried); section 11 writes up the
selected model only (equations, the quantities that follow from it, the budget and its limits).  The figures are inline SVG from the fitting tool.

Usage: python build_fit_sections.py [--no-variants]
"""
import argparse
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(os.path.dirname(HERE), "fittingtool")
PAGE = os.path.join(os.path.dirname(HERE), "vortex-energy-balance.html")
sys.path.insert(0, TOOL)
import fitdata        # noqa: E402
import fitmodels      # noqa: E402
import fitreport      # noqa: E402
import fittingtool    # noqa: E402
import pagefigures    # noqa: E402

X0 = fitdata.BURGERS_X
G0 = fitdata.G0

# the equations of every model, in LaTeX (the key is the key of fitmodels.models)
EQ = {
    "D1": (r"r_{\max}/\eta=5,\qquad U_{\max}/U_\eta=c\,Re_\lambda^{\,s}", ["c", "s"]),
    "D2": (r"r_{\max}/\eta=b,\qquad U_{\max}/U_\eta=c\,Re_\lambda^{\,s}", ["b", "c", "s"]),
    "D3": (r"r_{\max}/\eta=b\,Re_\lambda^{\,m},\qquad U_{\max}/U_\eta=c\,Re_\lambda^{\,s}", ["b", "m", "c", "s"]),
    "D4": (r"r_{\max}/\eta=5,\qquad U_{\max}/U_\eta=\kappa\,u'/U_\eta=\kappa\,(Re_\lambda/\sqrt{15})^{1/2}", ["&kappa;"]),
    "D5": (r"r_{\max}/\eta=b,\qquad U_{\max}/U_\eta=\kappa\,(Re_\lambda/\sqrt{15})^{1/2}", ["b", "&kappa;"]),
    "D6": (r"r_{\max}/\eta=5,\qquad U_{\max}/U_\eta=c\,Re_\lambda^{1/3}", ["c"]),
    "D7": (r"r_{\max}/\eta=a+b\ln Re_\lambda,\qquad U_{\max}/U_\eta=c\,Re_\lambda^{\,s}", ["a", "b", "c", "s"]),
    "D8": (r"r_{\max}/\eta=a+b\ln Re_\lambda,\qquad U_{\max}/U_\eta=c\,Re_\lambda^{1/3}", ["a", "b", "c"]),
    "L1": (r"r_{\max}/\eta=5,\qquad U_{\max}/U_\eta=a+b\ln Re_\lambda", ["a", "b"]),
    "L2": (r"r_{\max}/\eta=5,\qquad \Gamma/\nu=a+b\ln Re_\lambda,\qquad U_{\max}/U_\eta=\frac{\Gamma/\nu}{8.78\,r_{\max}/\eta}", ["a", "b"]),
    "L3": (r"r_{\max}/\eta=r,\qquad U_{\max}/U_\eta=a+b\ln Re_\lambda", ["r", "a", "b"]),
    "L4": (r"r_{\max}/\eta=a_1+b_1\ln Re_\lambda,\qquad U_{\max}/U_\eta=a+b\ln Re_\lambda", ["a<sub>1</sub>", "b<sub>1</sub>", "a", "b"]),
    "L5": (r"r_{\max}/\eta=a_1+b_1\ln Re_\lambda,\qquad \Gamma/\nu=a+b\ln Re_\lambda", ["a<sub>1</sub>", "b<sub>1</sub>", "a", "b"]),
    "C1": (r"\Gamma/\nu=c\,Re_\lambda^{\,Q},\qquad r_{\max}/\eta=5,\qquad U_{\max}/U_\eta=\frac{\Gamma/\nu}{8.78\,r_{\max}/\eta}", ["c", "Q"]),
    "C2": (r"\Gamma/\nu=c\,Re_\lambda^{\,Q},\qquad r_{\max}/\eta=b", ["c", "Q", "b"]),
    "C3": (r"\Gamma/\nu=c\,Re_\lambda^{\,Q},\qquad r_{\max}/\eta=b\,Re_\lambda^{\,m}", ["c", "Q", "b", "m"]),
    "K3": (r"\Gamma/\nu=a\,Re_\lambda^{\,p},\qquad U_{\max}/U_\eta=(r_{\max}/\eta)^q\;\Rightarrow\;(r_{\max}/\eta)^{1+q}=\frac{\Gamma/\nu}{8.78}", ["a", "p", "q"]),
    "K4": (r"\Gamma/\nu=a\,Re_\lambda^{\,p},\qquad U_{\max}/U_\eta=(r_{\max}/\eta)^q\,Re_\lambda^{\,s}\;\Rightarrow\;(r_{\max}/\eta)^{1+q}=\frac{\Gamma/\nu}{8.78\,Re_\lambda^{\,s}}", ["a", "p", "q", "s"]),
    "K5": (r"U_{\max}/U_\eta=a+b\ln Re_\lambda,\qquad \Gamma/\nu=c\,Re_\lambda^{\,Q},\qquad r_{\max}/\eta=\frac{\Gamma/\nu}{8.78\,U_{\max}/U_\eta}", ["a", "b", "c", "Q"]),
    "T6": (r"r_{\max}/\eta=b\,Re_\lambda^{\,m},\qquad U_{\max}/U_\eta=c_1Re_\lambda^{\,s_1}\ \text{(intense tubes)},\quad c_2Re_\lambda^{\,s_2}\ \text{(whole tubes)}", ["b", "m", "c<sub>1</sub>", "s<sub>1</sub>", "c<sub>2</sub>", "s<sub>2</sub>"]),
}
FAMILY = [("direct", "Direct laws: radius and swirl as functions of \\(Re_\\lambda\\), circulation from \\(\\Gamma/\\nu=8.78\\,r_{\\max}U_{\\max}/(\\eta U_\\eta)\\)"),
          ("logarithmic", "Straight lines in \\(\\ln Re_\\lambda\\)"),
          ("circulation", "Circulation first: \\(\\Gamma/\\nu\\) a power law, the swirl follows from the radius"),
          ("closure", "Closures: the radius follows from the circulation and the swirl"),
          ("two sets", "Two tube sets (information only)")]


def pm(v, e):
    return "%s &plusmn; %s" % (fitreport.num(float(v), 3), fitreport.num(float(e), 2))


def params_text(key, res):
    names = EQ[key][1]
    return ", ".join("%s = %s" % (n, pm(v, e)) for n, v, e in zip(names, res["params"], res["errors"]))


def build_section10(ctx):
    results = {r["model"].key: r for r in ctx["results"] if r.get("ok")}
    obs = ctx["obs"]
    n_r, n_u = len(obs["r"]["re"]), len(obs["U"]["re"])
    out = [r"""<h2>10. The fits tried</h2>
<p>Every law below was fitted to the corrected data of section 9 by the fitting tool (<code>LIT/fittingtool</code>; the report of each run is a self-contained page, <code>results/fit_*.html</code>). The data are the values used in the table of section 9 with a single \(Re_\lambda\): %d radii and %d swirls from %d sources (the hot-wire tails of Mouri et al. 2004 and 2007 are left out, A0c); the circulation is \(\Gamma/\nu=8.78\,r_{\max}U_{\max}/(\eta U_\eta)\) from the corrected values, as in section 9. Every source counts equally within a quantity (the weights of its points sum to the same total), so a source with one point counts as much as a source with twenty. The fit minimises the sum of the squares of \(\ln(\text{model}/\text{data})\) over the quantities the model is fitted to.</p>
<p>The scores are the same for every model, whatever it was fitted to: the weighted rms of \(\ln(\text{model}/\text{data})\) for the radius, the swirl and the circulation (a score of 8%% means the model is typically 8%% from the data), and the <em>combined</em> score \(\sqrt{(\text{rms}_r^2+\text{rms}_U^2)/2}\), which ranks the models. The parameter errors are from the Jacobian of the fit with every point treated as independent; they are too small, because points of one source and points of one flow are correlated.</p>
<p>The equations are grouped by what the model takes as given. \(U_\eta\) is the Kolmogorov velocity, \(u'/U_\eta=(Re_\lambda/\sqrt{15})^{1/2}\), \(8.78=2\pi/(1-e^{-x})\) with \(x=1.2564\) (section 3), \(\ln\) the natural logarithm.</p>""" % (n_r, n_u, len(set(obs["r"]["src"]) | set(obs["U"]["src"])))]
    for fam, title in FAMILY:
        keys = [k for k in EQ if k in results and results[k]["model"].family == fam]
        if not keys:
            continue
        out.append("<h3>%s</h3>" % title)
        rows = []
        for k in keys:
            r = results[k]
            sc = r["scores"]
            out.append("$$\\text{%s:}\\quad %s$$" % (k, EQ[k][0]))
            rows.append("<tr><td>%s</td><td class=\"l\">%s</td><td>%d</td><td>%s</td><td>%s</td><td>%s</td><td><strong>%s</strong></td></tr>" % (
                k, params_text(k, r), r["model"].nparam, fitreport.pct(sc["rms_r"]), fitreport.pct(sc["rms_U"]), fitreport.pct(sc["rms_G"]), fitreport.pct(sc["combined"])))
        out.append('<div class="tablebox"><table class="dt"><thead><tr><th>model</th><th>parameters</th><th>number</th><th>rms r</th><th>rms U</th><th>rms &Gamma;</th><th>combined</th></tr></thead><tbody>\n%s\n</tbody></table></div>' % "\n".join(rows))
    best = min(r["scores"]["combined"] for k, r in results.items() if not r["model"].info)
    out.append(r"""<h3>What the fits say</h3>
<ul>
<li><strong>The radius is constant.</strong> A constant radius fits to \(r_{\max}=%s\,\eta\) (D2). Letting it vary as a power of \(Re_\lambda\) gives an exponent \(m=%s\) (D3) and as a straight line in \(\ln Re_\lambda\) a slope %s per unit \(\ln Re_\lambda\) (D7), both consistent with zero, and the score does not improve. The radius 5 (D1) is within one standard error of the fitted constant.</li>
<li><strong>The swirl grows as a power of \(Re_\lambda\) close to one third.</strong> D1 gives \(U_{\max}/U_\eta=%s\,Re_\lambda^{%s}\), D6 fixes the exponent at 1/3 and gives \(%s\,Re_\lambda^{1/3}\) with the same score. A straight line in \(\ln Re_\lambda\) (L1) is slightly worse (%s against %s) and the swirl proportional to \(u'\) (D4, exponent 1/2) is clearly worse (%s). The fit of the circulation as a power law (C1, \(Q=%s\)) is as good as the fit of the swirl.</li>
<li><strong>The closures do not help.</strong> K3 (swirl a power of the radius) and K5 (a log law of the swirl with a power law of the circulation) make the radius vary with \(Re_\lambda\), against the data (scores %s and %s). K4 reduces to a constant radius (\(q=0\), \(r_{\max}=4.9\,\eta\)) and a power-law swirl.</li>
<li><strong>The two tube sets are not different.</strong> With a separate swirl law for each (T6), the intense tubes give \(%s\,Re_\lambda^{%s}\) and the whole tubes \(%s\,Re_\lambda^{%s}\), nearly the same curve, with only a slightly better score (%s) for two more parameters; this model is information only.</li>
</ul>
<p>The scores of D1, D2, D3, D6, D7 and D8 differ by less than 0.1 percentage points: the data fix the radius (5) and the swirl (a power near 1/3), and nothing more. The best combined score of a model that is not information only is %s.</p>""" % (
        fitreport.num(results["D2"]["params"][0], 3), pm(results["D3"]["params"][1], results["D3"]["errors"][1]), pm(results["D7"]["params"][1], results["D7"]["errors"][1]),
        fitreport.num(results["D1"]["params"][0], 3), fitreport.num(results["D1"]["params"][1], 3), fitreport.num(results["D6"]["params"][0], 3),
        fitreport.pct(results["L1"]["scores"]["combined"]), fitreport.pct(results["D1"]["scores"]["combined"]), fitreport.pct(results["D4"]["scores"]["combined"]),
        fitreport.num(results["C1"]["params"][1], 3), fitreport.pct(results["K3"]["scores"]["combined"]), fitreport.pct(results["K5"]["scores"]["combined"]),
        fitreport.num(results["T6"]["params"][2], 3), fitreport.num(results["T6"]["params"][3], 3), fitreport.num(results["T6"]["params"][4], 3), fitreport.num(results["T6"]["params"][5], 3),
        fitreport.pct(results["T6"]["scores"]["combined"]), fitreport.pct(best)))
    # sensitivity
    if ctx["variants"]:
        x5 = [fitreport.pct(v["by"]["D1"]["scores"]["combined"]) for v in ctx["variants"] if "swirl x 5" in v["label"]][0]
        rows = []
        for v in ctx["variants"]:
            by = v["by"]
            d1 = by["D1"]
            label = (v["label"].replace("(the Corrections tab)", "(A0c)").replace(" (the value on the page, v46)", "").replace(" (the high amplitude cut chord ratio)", "")
                     .replace("(the comparison with the threshold pairs)", "(the lower bound from the threshold pairs is 3.1&ndash;4.4)"))
            rows.append("<tr><td class=\"l\">%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                label, v["selected"], "%s Re<sup>%s</sup>" % (fitreport.num(d1["params"][0], 3), fitreport.num(d1["params"][1], 2)), fitreport.pct(d1["scores"]["combined"]), fitreport.pct(by["D6"]["scores"]["combined"])))
        out.append(r"""<h3>How much the corrections matter</h3>
<p>The same fits with other choices of the corrections of A0c. The first row is the case of section 11. The selected model is the one with the fewest parameters whose combined score is within 25%% of the best (D6 here; a tolerance of 15%% selects the same model).</p>
<div class="tablebox"><table class="dt"><thead><tr><th>case</th><th>selected</th><th>D1: swirl</th><th>D1 combined</th><th>D6 combined</th></tr></thead><tbody>
%s
</tbody></table></div>
<p>Three results stand out. (i) Without any correction the swirl law is flat (\(Re_\lambda^{0.12}\)) and the fit is poor (35%%): the sources do not describe one set of tubes as they stand. (ii) The swirl exponent depends on the factor applied to Mouri and Hori (2009): with the swirl as calculated no law fits, with a factor 5 (above the 3 used) the exponent rises to about 0.5 (the swirl proportional to \(u'\)) and the combined score is %s. (iii) The selection of D6 does not depend on the radius divisor of Mouri and Hori (1.17, 1.7, 1.75 or 1.95 all give D6), but the score does.</p>""" % ("\n".join(rows), x5))
    out.append(r"""<h3>A second reading of the corrections: Mouri and Hori &times; 5, Ghira et al. as listed</h3>
<p>The factor 3 for Mouri and Hori (2009) and the factor 0.6 for Ghira et al. (2022) were chosen together, and they support each other: the same fit that passes through Ghira (&times; 0.6) passes through Mouri and Hori (&times; 3), Da Silva et al. and Kida et al. within 3%%. The alternative is to leave Ghira et al. as listed and raise Mouri and Hori by 3/0.6 = 5. That case fits much worse: D1 gives \(0.373\,Re_\lambda^{0.522}\) with a combined score of 17.2%%, against 8.2%% for D1 with the factors of A0c. The misfit does not come from the form of the law: a power law, a straight line in \(\ln Re_\lambda\) (L1) and the swirl proportional to \(u'\) (D4) all score 17&ndash;18%%. It comes from the sources at the same \(Re_\lambda\): at 83&ndash;120 the swirl listed by Ghira et al. is 6.1&ndash;7.1, against 3.7&ndash;3.9 (Kida et al.) and 3.7&ndash;4.3 (Da Silva et al.), a factor 1.65 that no function of \(Re_\lambda\) can bridge, so the fit leaves Ghira 25%% above and the two others 12&ndash;22%% below.</p>
%s
<p class="note">Left column: the case of A0c (Mouri and Hori &times; 3, Ghira &times; 0.6); right column: Mouri and Hori &times; 5 and Ghira as listed. Rows: radius, swirl, circulation. Lines: D1, D6, C1 and K5. Grey crosses are the hot-wire tails of Mouri et al. (2004, 2007), left out of the fits.</p>""" % compare_figure())
    return "\n".join(out)


def compare_figure():
    svg_path = os.path.join(HERE, "compare_cases.svg")
    import compare_cases
    compare_cases.main()
    text = open(svg_path, encoding="utf-8").read()
    return pagefigures.fit_to_column(text[text.index("<svg"):])


def build_section11(ctx):
    results = {r["model"].key: r for r in ctx["results"] if r.get("ok")}
    d6, d1, d2 = results["D6"], results["D1"], results["D2"]
    c = float(d6["params"][0])
    ce = float(d6["errors"][0])
    k = 4 * X0 / 5.0 ** 2
    res = np.array([50, 100, 300, 1000, 2000], float)
    u = c * res ** (1 / 3)
    G = G0 * 5.0 * u
    fv_over_vf = 4.91 * (u / 5.0) ** 2
    vf = d6["bud"]["vf"]
    dd = d6["bud"]["d"]
    rows_t = []
    for i, Re in enumerate(res):
        rows_t.append("<tr><td>%d</td><td>%.2f</td><td>%.0f</td><td>%.0f</td><td>%.1f</td><td>%.3f</td><td>%.1f</td></tr>" % (Re, u[i], G[i], G[i] / G0, fv_over_vf[i], vf[i], dd[i]))
    fig = pagefigures.model_figure(d6, ctx["rows"])
    text = r"""<h2>11. The selected model</h2>
<p>The simplest model whose combined score is within 25%% of the best is D6, with one parameter. The tube is a Burgers vortex with</p>
$$\boxed{\;\frac{r_{\max}}{\eta}=5,\qquad \frac{U_{\max}}{U_\eta}=c\,Re_\lambda^{1/3},\qquad c=%.3f\pm%.3f\;}$$
<p>and everything else follows from the relations of sections 3&ndash;7. The error on \(c\) is from the fit with independent points (too small); the free exponent of D1 is \(0.326\pm0.019\) and the fitted constant radius of D2 is \(%.2f\pm%.2f\,\eta\). The values of \(c\) and the exponent depend on the factor applied to Mouri and Hori (2009), section 10.</p>
<h3>What follows from the two lines</h3>
<p>With \(r_{\max}=\beta\eta\), \(\beta=5\) (section 7):</p>
$$\frac{\gamma}{\gamma_\eta}=\frac{4x}{\beta^2}=%.3f,\qquad Re_\gamma=\frac{\gamma r_{\max}^2}{\nu}=4x=5.03,\qquad Q=\pi\gamma r_{\max}^2=15.8\,\nu,$$
$$Re_c=\frac{r_{\max}U_{\max}}{\nu}=\beta\frac{U_{\max}}{U_\eta}=%.2f\,Re_\lambda^{1/3},\qquad \frac{\Gamma}{\nu}=8.78\,Re_c=%.1f\,Re_\lambda^{1/3}.$$
<p>The strain rate that stretches the tube is a fixed fraction of the Kolmogorov strain, \(\gamma\approx0.2\,\gamma_\eta\): the radius 5 and the strain 1/5 are one observation (\(\beta^2\gamma/\gamma_\eta=4x\) is fixed by the Burgers vortex). The swirl grows as \(Re_\lambda^{1/3}\) while the radius does not, so the circulation of the tube grows as \(Re_\lambda^{1/3}\) in units of \(\nu\), and the tube becomes relatively stronger at higher \(Re_\lambda\) (\(Re_c\) from %.0f at \(Re_\lambda=50\) to %.0f at 2000).</p>
<div class="tablebox"><table class="dt"><thead><tr><th>\(Re_\lambda\)</th><th>\(U_{\max}/U_\eta\)</th><th>\(\Gamma/\nu\)</th><th>\(Re_c\)</th><th>\(f_v/V_f\)</th><th>\(V_f\) (closure)</th><th>\(d/\eta\) (closure)</th></tr></thead><tbody>
%s
</tbody></table></div>
%s
<p class="note">Data (solid: values used; open: as calculated where corrected; grey crosses: left out) and the model D6 (black). The scatter around the line is the 8%% of the combined score.</p>
<h3>The dissipation budget</h3>
<p>The dissipation inside the tubes enters through the vortex term of section 6, \(\varepsilon_{\text{vortex}}/\varepsilon=4.91\,V_f\,(U_{\max}/(\beta U_\eta))^2\), where \(V_f\) is the fraction of the volume inside the cores (\(r<r_{\max}\)). Its two unknowns, the share \(f_v=\varepsilon_{\text{vortex}}/\varepsilon\) and \(V_f\), are linked by the data alone through</p>
$$\frac{f_v}{V_f}=4.91\left(\frac{U_{\max}}{\beta U_\eta}\right)^2=%.3f\,Re_\lambda^{2/3}:$$
<p>the dissipation per unit volume inside the cores is %.1f times the mean at \(Re_\lambda=100\) and %.0f times at 2000. This is the closure-free result of the fits.</p>
<p>The closure of section 6, \(\varepsilon=\varepsilon_{\text{strain}}+\varepsilon_{\text{vortex}}\) with \(\varepsilon_{\text{strain}}=3\nu\gamma^2\) at the strain of the tubes (\(0.2\gamma_\eta\)), adds a second relation: the strain takes 12%% of \(\varepsilon\) at \(\beta=5\) at every \(Re_\lambda\), the tubes the other 88%%, and \(V_f\) follows (the last two columns of the table; the spacing is \(d=r_{\max}\sqrt{\pi/V_f}\)). It is an assumption, not a result: it takes the dissipation outside the tubes to be that of the strain that feeds the tubes. In the picture where eddies form when the strain exceeds \(\gamma_\eta\) and limit it, as the radius 5 suggests, this is consistent. The one measurement that tests it is the mean tube spacing of Kida et al. (2002), \(d/\eta=15.6\) and 17.2 at \(Re_\lambda=83\) and 170, which gives \(V_f=\pi r_{\max}^2/d^2=0.35\) and 0.31, against 0.36 and 0.22 from the closure: it agrees at 83 and is 40%% higher at 170. The volume fraction of the closure falls from 0.5 at \(Re_\lambda=50\) to 0.04 at 2000 and its share is constant (0.88) because the radius is constant.</p>
<h3>Limits</h3>
<ul>
<li>The exponent 1/3 and the factor 3 for Mouri and Hori (2009) are linked: the data allow a factor between 2.4 and 3 (free exponent 0.24&ndash;0.33), and a larger factor, with Ghira et al. as listed, moves the exponent to about 0.5 at a much worse score (section 10). The chord model of A0c gives 2&ndash;3.5 for the factor. The swirl above \(Re_\lambda\approx400\) rests on one source.</li>
<li>The radius 5 is the Burgers radius of the swirl maximum; sources that give a boundary radius or a 1/e radius are converted with the Burgers relations (A0). The PIV radius of Aligolzadeh et al. (6.0 \(\eta\)) is a boundary radius and is not corrected.</li>
<li>The budget quantities (\(V_f\), the share and the spacing) depend on the closure above, and \(V_f\) is only checked at two points.</li>
<li>The tubes are straight Burgers vortices; their lengths, curvature, clustering and lifetime (Ghira et al. 2025) are not part of the model.</li>
</ul>
<p>This is the tube that the subgrid closure of the next step has to represent: a vortex of radius \(5\eta\), swirl \(0.81\,Re_\lambda^{1/3}U_\eta\) and strain \(0.2\gamma_\eta\) at every \(Re_\lambda\) from 35 to 1900.</p>
""" % (c, ce, float(d2["params"][0]), float(d2["errors"][0]), k, 5 * c, G0 * 5 * c, 5 * u[0], 5 * u[-1], "\n".join(rows_t), fig,
       4.91 * c * c / 25.0, fv_over_vf[1], fv_over_vf[-1])
    return text


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-variants", action="store_true")
    a = ap.parse_args(argv)
    ctx = fittingtool.run(os.path.join(TOOL, "data", "tubes.csv"), os.path.join(TOOL, "data", "corrections.json"), with_variants=not a.no_variants)
    t = open(PAGE, encoding="utf8").read()
    i = t.index("<h2>10. ")
    j = t.index("<h2>References</h2>")
    new = build_section10(ctx) + "\n" + build_section11(ctx) + "\n"
    t = t[:i] + new + t[j:]
    open(PAGE, "w", encoding="utf8", newline=chr(10)).write(t)
    print("written sections 10 and 11; selected", ctx["selected"])


if __name__ == "__main__":
    main()
