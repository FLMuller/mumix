r"""build_paper.py  v01  Build the paper (../vortex-energy-balance.html) in journal form from the theory of the page, the reconciled data and the fits.

    python build_paper.py            writes ../vortex-energy-balance.html; publish with publish_page.py

What is kept and what is new.  The derivation (sections 2-8 of the page: the Burgers vortex, its energy budget, the closure with the Kolmogorov scales) is taken
unchanged from the snapshot ../zprev/vortex-energy-balance_v47.html, so its notation is that of the page.  Everything else is written here: abstract, introduction
(section 1), the data and their treatment (9), the selection of the model (10), the selected model (11), the two-population reading (12), the use as a closure in
CFD with the delay of the cascade (13), limits (14), conclusions (15).  The references of the page are kept and the new ones added; the appendix (the source data,
paper by paper) is made again from sourcedata.py (build_data_sections.build_appendix).
The numbers of the text come from ../fittingtool/results/modelselect.json (modelselect.py) and from fits made here, through the @KEY@ place holders.

Versions  M01 m01.v01 (2026-11-12): first version (replaces the build of sections 1, 9, 10, 11 by build_intro_sections, build_data_sections.main and build_fit_sections).
"""
import json
import math
import os
import re
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
LIT = os.path.dirname(HERE)
TOOL = os.path.join(LIT, "fittingtool")
sys.path.insert(0, HERE)
sys.path.insert(0, TOOL)
import build_data_sections as bds    # noqa: E402
import fitdata                       # noqa: E402
import fitmodels                     # noqa: E402
import fitreport                     # noqa: E402
import modelselect                   # noqa: E402
import pagefigures                   # noqa: E402

__all__ = ["build", "main"]

BASE = os.path.join(LIT, "zprev", "vortex-energy-balance_v47.html")
PAGE = os.path.join(LIT, "vortex-energy-balance.html")
X = fitdata.BURGERS_X

NEW_REFS = [
    ("Baldyga89", r"Ba&#322;dyga, J. and Bourne, J. R. (1989). Simplification of micromixing calculations. I. Derivation and application of new model. <em>Chem. Eng. J.</em> 42, 83&ndash;92. (Not checked against a copy.)"),
    ("Burnham", r"Burnham, K. P. and Anderson, D. R. (2002). <em>Model Selection and Multimodel Inference</em>, 2nd edn. Springer. (Not checked against a copy.)"),
    ("Fox", r"Fox, R. O. (1995). The spectral relaxation model of the scalar dissipation rate in homogeneous turbulence. <em>Phys. Fluids</em> 7, 1082&ndash;1094. (Not checked against a copy.)"),
    ("Goto", r"Goto, S. and Vassilicos, J. C. (2016). Unsteady turbulence cascades. <em>Phys. Rev. E</em> 94, 053108. (Not checked against a copy.)"),
    ("Hanjalic", r"Hanjali&#263;, K., Launder, B. E. and Schiestel, R. (1980). Multiple-time-scale concepts in turbulent transport modelling. In <em>Turbulent Shear Flows 2</em>, 36&ndash;49. Springer. (Not checked against a copy.)"),
    ("Pearson", r"Pearson, B. R., Yousef, T. A., Haugen, N. E. L., Brandenburg, A. and Krogstad, P.-&Aring;. (2004). Delayed correlation between turbulent energy injection and dissipation. <em>Phys. Rev. E</em> 70, 056301. (Read as the preprint, arXiv physics/0404114.)"),
    ("Schiestel", r"Schiestel, R. (1987). Multiple-time-scale modeling of turbulent flows in one-point closures. <em>Phys. Fluids</em> 30, 722&ndash;731. (Not checked against a copy.)"),
    ("Vassilicos", r"Vassilicos, J. C. (2015). Dissipation in turbulent flows. <em>Annu. Rev. Fluid Mech.</em> 47, 95&ndash;114. (Not checked against a copy.)"),
    ("Yoffe", r"Yoffe, S. R. and McComb, W. D. (2018). Onset criteria for freely decaying isotropic turbulence. <em>Phys. Rev. Fluids</em> 3, 104605. (Read as the preprint, arXiv 1805.01238.)"),
]


def between(text, start, end):
    a = text.index(start)
    b = text.index(end, a)
    return text[a:b]


def two_population_figure(rows_raw, tp, c6):
    """The swirl as calculated from the papers (no correction), with the two laws of section 12 and the single law of section 11."""
    fig, ax = plt.subplots(figsize=(9, 6.2))
    style = {"Ghira22": ("o", "tab:red", "Ghira et al. (2022), 1% most intense, DNS"), "Ghira25": ("o", "darkred", "Ghira et al. (2025), DNS"),
             "Mouri07": ("^", "tab:orange", "Mouri et al. (2007), 0.1% and 1% thresholds, hot wire"), "Mouri04": ("v", "goldenrod", "Mouri et al. (2004), 1% threshold"),
             "Kida02": ("s", "tab:blue", "Kida et al. (2002), all low-pressure vortices, DNS"), "Mouri09": ("D", "tab:cyan", "Mouri and Hori (2009), all tubes, as printed"),
             "Sassa05": ("x", "0.35", "Sassa and Makita (2005), read from their Fig. 8(b)"), "DaSilva11": ("*", "tab:purple", "Da Silva et al. (2011), from u0/u' (lower) and as printed (upper)")}
    seen = set()
    for x in rows_raw:
        if x["re"] is None or x["u_raw"] is None or x["src"] not in style:
            continue
        m, col, lab = style[x["src"]]
        ax.plot(x["re"], x["u_raw"], m, color=col, ms=7, mfc="none" if x["src"] in ("Mouri09",) else col, label=None if x["src"] in seen else lab)
        seen.add(x["src"])
    ax.plot([111, 120], [9.0, 7.15], "*", color="tab:purple", ms=9, mfc="none")
    f = tp["all_free"]["f"]
    first = True
    for x in rows_raw:
        if x["src"] == "Mouri09" and x["re"] is not None:
            ax.plot(x["re"], f * x["u_raw"], "D", color="tab:cyan", ms=7, label=("Mouri and Hori (2009) x %.2f (fitted chord factor)" % f) if first else None)
            first = False
    re = np.exp(np.linspace(math.log(15), math.log(3000), 100))
    ax.plot(re, tp["intense"]["c"] * re ** tp["intense"]["s"], "-", color="tab:red", lw=1.8, label=r"intense tubes: $%.2f\,Re_\lambda^{%.2f}$" % (tp["intense"]["c"], tp["intense"]["s"]))
    ax.plot(re, tp["all_free"]["a"] * re ** tp["all_free"]["s"], "-", color="tab:blue", lw=1.8, label=r"all tubes: $%.2f\,Re_\lambda^{%.2f}$" % (tp["all_free"]["a"], tp["all_free"]["s"]))
    ax.plot(re, c6 * re ** (1 / 3), "--", color="k", lw=1.3, label=r"single law of section 11: $%.3f\,Re_\lambda^{1/3}$ (corrected data)" % c6)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"$Re_\lambda$", fontsize=11)
    ax.set_ylabel(r"$U_{max}/U_\eta$ as calculated from the papers", fontsize=11)
    ax.grid(alpha=0.25, which="both")
    ax.legend(fontsize=7.5, loc="upper left", frameon=True)
    fig.tight_layout()
    return pagefigures.fit_to_column(fitreport.svg_of(fig))


def table(head, rows):
    return ('<div class="tablebox"><table class="dt">\n<thead><tr>' + "".join("<th>%s</th>" % h for h in head) + "</tr></thead>\n<tbody>\n"
            + "\n".join("<tr>" + "".join("<td>%s</td>" % c for c in r) + "</tr>" for r in rows) + "\n</tbody></table></div>")


def build():
    with open(BASE, encoding="utf-8") as f:
        base = f.read()
    with open(os.path.join(TOOL, "results", "modelselect.json"), encoding="utf-8") as f:
        sel = json.load(f)
    head = base[:base.index("<main>") + len("<main>")]
    theory = between(base, "<h2>2. Theory background</h2>", "<h2>9. The data")
    refs_old = between(base, "<h2>References</h2>", "<h2>Appendix")
    items = re.findall(r"<li style=\"margin:8px 0\">.*?</li>", refs_old, re.S)
    items += ['<li style="margin:8px 0">%s</li>' % text for key, text in NEW_REFS]
    items.sort(key=lambda s: re.sub(r"&[#\w]+;", "", re.sub(r"<[^>]+>", "", s)).lower())
    refs = ("<h2>References</h2>\n<p>Papers cited, with the DOI where one was found in the paper itself or in the Scopus export. Entries marked 'not checked' were not confirmed from a copy of the paper.</p>\n"
            "<ol style=\"padding-left:1.4em\">\n" + "\n".join(items) + "\n</ol>\n")

    rows = modelselect.load({})
    obs = fitdata.observations(rows)
    models = {m.key: m for m in fitmodels.models(obs)}
    res6 = fitmodels.fit(models["D6"], obs)
    c6 = float(res6["params"][0])
    scen = sel["scenarios"]
    main0 = {m["key"]: m for m in scen[0]["models"]}
    tp = sel["two_population"]
    rows_raw = fitdata.load(modelselect.DATA, modelselect.CORR, corr={}, excluded={})

    def bud(U, r=5.0):
        b = fitmodels.budget(r, U)
        return float(b["vf"]), float(b["d"])
    S = 48 * X * X
    share5 = 1 - S / 5.0 ** 4
    sel_rows = [[m["key"], str(m["k"]), "%.1f" % m["rms"], "%.1f" % m["loso"], "%.1f" % m["d_aicc"], "%.1f" % m["d_bic"], m["name"]]
                for m in sorted(scen[0]["models"], key=lambda m: m["loso"])]
    sens_rows = []
    for sc in scen:
        ms = sorted(sc["models"], key=lambda m: m["loso"])
        d = next(m for m in ms if m["key"] == "D6")
        sens_rows.append([sc["label"], "%s (%.1f%%)" % (ms[0]["key"], ms[0]["loso"]), "%.1f%%" % d["loso"], "%.3f" % d["params"][0]])
    pred_rows = []
    for Re in (50, 100, 300, 1000, 2000):
        U1 = c6 * Re ** (1 / 3)
        U2 = tp["all_free"]["a"] * Re ** tp["all_free"]["s"]
        Ui = tp["intense"]["c"] * Re ** tp["intense"]["s"]
        v1, d1 = bud(U1)
        v2, d2 = bud(U2)
        pred_rows.append(["%d" % Re, "%.2f" % U1, "%.0f" % (fitdata.G0 * 5 * U1), "%.3f" % v1, "%.1f" % d1, "%.2f" % U2, "%.0f" % (fitdata.G0 * 5 * U2), "%.3f" % v2, "%.1f" % d2, "%.2f" % Ui,
                          "%.3f" % (4.91 * 0.01 * (Ui / 5) ** 2)])
    n_src = len({x["src"] for x in rows})
    keys = {
        "@C6@": "%.3f" % c6, "@RMS6@": "%.1f" % main0["D6"]["rms"], "@LOSO6@": "%.1f" % main0["D6"]["loso"], "@LOSOL1@": "%.1f" % main0["L1"]["loso"], "@DAIC6@": "%.1f" % main0["D6"]["d_aicc"],
        "@L1A@": "%.2f" % main0["L1"]["params"][0], "@L1B@": "%.2f" % main0["L1"]["params"][1], "@NR@": str(len(obs["r"]["re"])), "@NU@": str(len(obs["U"]["re"])), "@NG@": str(main0["D6"]["groups"]),
        "@IC@": "%.2f" % tp["intense"]["c"], "@IS@": "%.2f" % tp["intense"]["s"], "@IRMS@": "%.0f" % tp["intense"]["rms_power"], "@IN@": str(tp["intense"]["n"]),
        "@AA@": "%.2f" % tp["all_free"]["a"], "@AS@": "%.2f" % tp["all_free"]["s"], "@AF@": "%.2f" % tp["all_free"]["f"], "@ARMS@": "%.1f" % tp["all_free"]["rms"],
        "@A3S@": "%.2f" % tp["all_f3.0"]["s"], "@A3RMS@": "%.1f" % tp["all_f3.0"]["rms"], "@SM@": "%.2f" % tp["slope_Mouri09"], "@SK@": "%.2f" % tp["slope_Kida02"],
        "@SHARE@": "%.2f" % share5, "@NSRC@": str(n_src),
        "@VK83A@": "%.2f" % bud(c6 * 83 ** (1 / 3))[0], "@VK170A@": "%.2f" % bud(c6 * 170 ** (1 / 3))[0],
        "@VK83B@": "%.2f" % bud(tp["all_free"]["a"] * 83 ** tp["all_free"]["s"])[0], "@VK170B@": "%.2f" % bud(tp["all_free"]["a"] * 170 ** tp["all_free"]["s"])[0],
        "@SELTABLE@": table(["model", "parameters", "rms %", "LOSO %", "&Delta;AICc", "&Delta;BIC", "form"], sel_rows),
        "@SENSTABLE@": table(["corrections", "best model by LOSO", "LOSO of the selected model", "its coefficient \\(c\\)"], sens_rows),
        "@PREDTABLE@": table([r"\(Re_\lambda\)", r"\(U_{\max}/U_\eta\) (I)", r"\(\Gamma/\nu\) (I)", r"\(V_f\) (I)", r"\(d/\eta\) (I)", r"\(U_{\max}/U_\eta\) (II, all)", r"\(\Gamma/\nu\) (II)", r"\(V_f\) (II)", r"\(d/\eta\) (II)",
                              r"\(U_{\max}/U_\eta\) (II, intense)", "dissipation share of the intense tubes (1% of the volume)"], pred_rows),
        "@DATAFIG@": pagefigures.data_figure(rows), "@MODELFIG@": pagefigures.model_figure(res6, rows), "@TWOFIG@": two_population_figure(rows_raw, tp, c6),
        "@DATATABLE@": bds.model_input_table(),
    }
    body = TEXT_FRONT + theory + TEXT_BACK
    for k, v in keys.items():
        body = body.replace(k, v)
    left = re.findall(r"@[A-Z0-9]+@", body)
    if left:
        raise ValueError("place holders not filled: %s" % sorted(set(left)))
    appendix = bds.build_appendix().replace("<h2>Appendix: the source data, how it was converted, and what the model uses</h2>",
                                            "<h2>Appendix: the source data, how it was converted, and what the model uses</h2>\n<p class=\"note\">The appendix lists every source with its conversions, made from the same data file as the fits. Its paragraphs on the corrections (A0c) give the rationale as it was decided; the review of that rationale is in sections 9 and 12, and the page-by-page evidence is in the recording book (<code>LIT/record</code>).</p>", 1)
    typeset = "<script>if (document.typeset) { document.typeset(); }</script>\n"      # in the report server the doc block loads MathJax on request; a plain browser uses the script of the head
    return head + "\n" + body + "\n" + refs + appendix + "</main>\n" + typeset


TEXT_FRONT = r"""
<h1>A Burgers-vortex closure for the dissipative scales of turbulence: evidence, model selection and use in CFD</h1>
<p class="lede">Working paper (Burgers Vortex Energy Balance). Symbols: \(\gamma\) axial stretching rate, \(\Gamma\) circulation, \(\nu\) kinematic viscosity, \(\varepsilon\) dissipation rate per unit mass, \(\eta\), \(U_\eta\), \(\gamma_\eta\) the Kolmogorov length, velocity and rate, \(Re_\lambda\) the Taylor-scale Reynolds number, \(r_{\max}=\beta\eta\) the radius of maximum swirl of a tube and \(U_{\max}\) that swirl.</p>

<h2>Abstract</h2>
<p>The smallest scales of turbulence, where micromixing and viscous dissipation take place, are organised in stretched vortex tubes. We model a tube as a Burgers vortex, close its energy budget with the Kolmogorov scales, and determine its two free quantities, the radius of maximum swirl and the swirl velocity, from @NSRC@ published sources (simulations and experiments) covering \(35\le Re_\lambda\le1934\). Every number is traced from the page of its paper to the fit in an open recording book, and each correction is listed with its rationale. The radius is \(r_{\max}=5\,\eta\) in all flows. With the corrections adopted for probe measurements, a single one-parameter law, \(U_{\max}/U_\eta=@C6@\,Re_\lambda^{1/3}\), predicts sources left out of the fit to within @LOSO6@%, and no model with more parameters predicts them better. A review of the sources shows, however, that the uncorrected data separate into two populations: the 1% most intense tubes, \(U_{\max}/U_\eta=@IC@\,Re_\lambda^{@IS@}\), and all tubes, \(U_{\max}/U_\eta=@AA@\,Re_\lambda^{@AS@}\). The second reading needs one fitted probe factor instead of two corrections and reproduces the measured volume fraction of the tubes. We give the closure in a form usable in computational fluid dynamics, with the tube strain rate, circulation, volume fraction and spacing as functions of the local \(k\) and \(\varepsilon\), and add a first-order lag for the time the energy cascade takes to reach the tubes, \(T_c/\tau_\eta=C_c\,(Re_\lambda/\sqrt{15}-\beta^{2/3})\).</p>
<p class="src">Keywords: micromixing; vortex tubes; Burgers vortex; turbulence closure; energy cascade; model selection.</p>

<h2>1. Introduction</h2>
<p>Fast reactions, precipitation and the break-up of drops are controlled by the motion at the dissipative scales of turbulence. Engineering models of micromixing picture that motion as stretched vortices of about ten Kolmogorov lengths that engulf fluid at a rate set by \((\varepsilon/\nu)^{1/2}\) (Ba&#322;dyga and Bourne 1984, 1989). Direct numerical simulations have since shown such vortices directly: the intense vorticity of isotropic turbulence is concentrated in tubes with a radius of four to five \(\eta\) (Jim&eacute;nez et al. 1993; Ghira et al. 2022), and tubes with a similar radius are found in mixing layers, channels and jets (Tanahashi et al. 2001, 2004; Da Silva et al. 2011) and in hot-wire records up to \(Re_\lambda\approx2000\) (Belin et al. 1996; Mouri et al. 2007; Mouri and Hori 2009). The profile of a tube is close to that of the Burgers (1948) vortex, a balance of axial stretching and radial diffusion.</p>
<p>A closure for computational fluid dynamics (CFD) needs more than the picture: it needs the size, the swirl, the strain rate and the number of the tubes as functions of quantities the flow solver has. This paper derives those functions. The Burgers vortex has two free quantities, the stretching rate \(\gamma\) and the circulation \(\Gamma\). The radius of maximum swirl fixes the first, the swirl velocity the second, and an energy balance of tube and background (sections 3&ndash;7) then gives the volume fraction and the spacing of the tubes without a further constant. The radius and the swirl have to come from data, and three difficulties arise. The papers define the radius and the velocity of a tube in different ways. Probe measurements see a tube along a chord and need a correction. And the papers select different tubes: the 1% of the volume with the highest vorticity, the events above a threshold, or all tubes.</p>
<p>The contribution of this paper is fourfold. (i) All data are taken from the papers by a documented path: a recording book (<code>LIT/record</code>, one tab a paper) shows the page of the paper, the number read from it, each conversion, each assumption and the value that enters the fit (section 9). (ii) The model is chosen with an explicit penalty on complexity, by leaving each source out in turn (section 10). (iii) The review of the sources shows that the corrections adopted for the swirl are not needed if intense tubes and all tubes are treated as two populations; this second reading is developed in section 12 next to the single law of section 11, so that the reader can judge both. (iv) The closure is written for use in CFD, and the time the cascade needs to bring energy to the tubes is added as a lag (section 13). Sections 2 to 8 give the theory.</p>
"""

TEXT_BACK = r"""
<h2>9. The data and their treatment</h2>
<h3>Sources</h3>
<p>The radius and the swirl of vortex tubes were taken from @NSRC@ sources: simulations of forced isotropic turbulence (Jim&eacute;nez et al. 1993; Kida et al. 2002; Pirozzoli 2009, 2012; Da Silva et al. 2011; Ishihara et al. 2011, 2013; Ghira et al. 2022, 2025), of mixing layers and channels (Tanahashi et al. 2001, 2004; Das et al. 2006; Wang et al. 2007), hot-wire and hot-film records (Belin et al. 1996; Mouri et al. 2003, 2004, 2007; Mouri and Hori 2009; Sassa and Makita 2005) and scanning PIV (Aligolzadeh et al. 2023). Each number was read from the rendered page of the paper and checked against the data file; the recording book shows the page, the number and the path to the value used. All values are expressed as the radius of maximum swirl of a Burgers vortex over \(\eta\) and the maximum swirl over \(U_\eta\) (the conversions are in the appendix, A0).</p>
<p>The sources select tubes in three ways, and this matters for what follows. <em>Intense tubes</em> are the connected regions of the 1% of the volume with the highest vorticity (Jim&eacute;nez et al.; Da Silva et al.; Ghira et al.) or the events above a high threshold of a probe signal (the 0.1% and 1% averages of Mouri et al. 2004, 2007; Belin et al.). <em>All tubes</em> are found without a threshold, from the local flow pattern (Tanahashi et al.), the pressure (Kida et al.; Pirozzoli) or the average over all events of a probe record (Mouri and Hori).</p>
@DATAFIG@
<p class="note">Fig. 1. Radius and swirl of vortex tubes against \(Re_\lambda\), as used in the fits (open symbols: the value as calculated from the paper where a correction was applied; crosses: left out of the fits).</p>

<h3>Corrections</h3>
<p>Three corrections were adopted before the fits; their rationale is given in full in the recording book (tab Corrections) and in appendix A0c.</p>
<p><strong>The radius of the all-event hot-wire average (Mouri and Hori 2009), divided by 1.75.</strong> A probe crosses a tube along a chord at a random offset and tilt, so the mean profile of all events is wider than the tube; the authors say so and give no factor. A model of the crossing statistics, tested on the size distribution of Belin et al. (1996), gives a ratio of 1.7 to 1.85. The corrected radii (4.7 to 5.3 \(\eta\)) agree with the simulations, and the fits are insensitive to the divisor between 1.6 and 1.9 (section 10).</p>
<p><strong>The swirl of the same source, multiplied by 3,</strong> for the same reason: the chord model gives 2 to 3.5. <strong>The swirl of Ghira et al. (2022, 2025), multiplied by 0.6,</strong> to bring the swirl of the 1% most intense tubes to the level of the other sources at the same \(Re_\lambda\). The threshold averages of Mouri et al. (2004, 2007) are left out, as tails of the distribution that the all-event average of Mouri and Hori contains whole.</p>
<p><strong>Review of the corrections.</strong> The two swirl factors are the weakest numbers of the data set, for three reasons found in the review. First, Da Silva et al. (2011), whose swirl (3.7 and 4.3 \(U_\eta\), from their \(u_0/u'\)) was a support of the factor 0.6, print \(\langle u_0\rangle/u_\eta=9.0\) and 7.15 in the same table, and their circulation implies 10.5; the paper does not resolve the factor 2.5, and its swirl is therefore not fitted. Secondly, without any factor the intense-tube sources agree with each other: Ghira et al. (simulation) and the 0.1% averages of Mouri et al. (2007, hot wire) lie on one line. Thirdly, the all-tube sources alone (Kida et al. and Mouri and Hori) are best joined with a swirl factor of @AF@, not 3. These points do not affect the radius. They are taken up in section 12.</p>
<p>The review also moved Tanahashi et al. (2001) from an assumed \(Re_\lambda=200\) to 80 (their Fig. 1b), and added the swirl of the \(Re_\lambda=54\) runs of Ghira et al. (2025) and the circulation of Jim&eacute;nez et al. (1993).</p>

<h3>The width of the distributions</h3>
<p>The values above are means or peaks of distributions. The probability densities of the diameter and the swirl of all tubes were digitised from Tanahashi et al. (2001, 2004), Das et al. (2006) and Pirozzoli (2012) (recording book). The radius has a peak at 4.2 to 4.8 \(\eta\), a median of 5.3 to 5.9 and a mean of 7.2 to 8.2: a narrow family (a lognormal of width 0.3) and a broad second family of about twice the size. The model uses the peak, \(\beta=5\). The mean is larger by a factor 1.5, and which statistic a closure should use depends on the property that is closed; this is one of the open points of section 14.</p>

<h3>The data</h3>
@DATATABLE@

<h2>10. Selection of the model</h2>
<p>Candidate models express \(r_{\max}/\eta\) and \(U_{\max}/U_\eta\) as functions of \(Re_\lambda\) with one to four parameters: a constant radius or one that varies as a power or a logarithm of \(Re_\lambda\), and a swirl that is a power law, a power law with a fixed exponent (1/2: proportional to the r.m.s. velocity; 1/3), a logarithmic law, or that follows from a law for the circulation. Each is fitted by least squares of the logarithmic residuals of the radius (@NR@ points) and the swirl (@NU@ points), every source having the same weight in each quantity (@NG@ source-quantity groups).</p>
<p>An earlier version chose the model with the fewest parameters within 25% of the best root-mean-square (rms) residual; the width of that band has no basis. Here the choice is made by cross-validation: each source in turn is left out, the model is fitted to the others and predicts the one left out, and the rms of those prediction errors (LOSO, in per cent) is the score. A parameter that follows the noise of one source worsens the score, so complexity is penalised by the data. The Akaike criterion with small-sample correction (AICc) and the Bayesian criterion (BIC), with a source-quantity group as the unit of data, are given for comparison; differences below 2 carry no evidence (Burnham and Anderson 2002).</p>
@SELTABLE@
<p class="note">Table 1. The candidate models, sorted by the leave-one-source-out error. Corrections as adopted in section 9.</p>
<p>The logarithmic swirl law with radius 5 (L1, two parameters) predicts left-out sources best, @LOSOL1@%; the one-parameter law with the exponent 1/3 (D6) follows at @LOSO6@%, and the information criteria do not separate the two (\(\Delta\)AICc = @DAIC6@). No model with three or four parameters predicts better than these: a fitted radius, a radius that varies with \(Re_\lambda\), or a free exponent add nothing that survives leaving a source out. With complexity penalised, the one-parameter model is selected. The logarithmic law, \(U_{\max}/U_\eta=@L1A@+@L1B@\ln Re_\lambda\), is equivalent within the range of the data but turns negative below \(Re_\lambda\approx13\).</p>
@SENSTABLE@
<p class="note">Table 2. The selection under other corrections.</p>
<p>The selection is robust to the radius divisor and fragile to the swirl factors (Table 2). With the swirl of Ghira et al. as listed, no single law predicts left-out sources better than 21%, whatever its number of parameters: the single law exists only with both swirl factors.</p>

<h2>11. The selected single-population model (model I)</h2>
$$r_{\max}=5\,\eta,\qquad \frac{U_{\max}}{U_\eta}=@C6@\,Re_\lambda^{1/3}$$
<p>and, from sections 3 to 7 with \(\beta=5\),</p>
$$\frac{\gamma}{\gamma_\eta}=\frac{4x}{\beta^2}=0.201,\qquad \frac{\Gamma}{\nu}=8.78\,\beta\,\frac{U_{\max}}{U_\eta},\qquad V_f=\left(1-\frac{75.8}{\beta^4}\right)\frac{\beta^2}{4.91\,(U_{\max}/U_\eta)^2},\qquad \frac{d}{\eta}=\beta\sqrt{\frac{\pi}{V_f}} .$$
<p>The rms residual is 8.2% for the radius and @RMS6@% for radius and swirl together. The swirl dissipation of the tubes is @SHARE@ of the total at \(\beta=5\), the remainder being the dissipation of the background strain; the volume fraction \(V_f\) follows from this balance and is a prediction, not a fit.</p>
@MODELFIG@
<p class="note">Fig. 2. Model I with the data (corrected as in section 9).</p>

<h2>12. A two-population reading (model II)</h2>
<p>Plotted as calculated from the papers, without any swirl correction, the data form two families (Fig. 3).</p>
@TWOFIG@
<p class="note">Fig. 3. The swirl as calculated from the papers. Red: the most intense tubes. Blue: all tubes; the open diamonds are Mouri and Hori (2009) as printed, the filled diamonds the same times the fitted chord factor.</p>
<p><strong>Intense tubes.</strong> The 1% most intense tubes of simulations (Ghira et al. 2022, 2025; \(Re_\lambda\) 54 to 399) and the 0.1% threshold averages of hot-wire records (Mouri et al. 2007; 332 to 1934) follow one law over @IN@ points without correction,</p>
$$\frac{U_{\max}}{U_\eta}\bigg|_{\text{intense}}=@IC@\,Re_\lambda^{@IS@}\qquad(\text{rms }@IRMS@\%),$$
<p>close to a constant fraction of the r.m.s. velocity at the Reynolds numbers of the simulations, as their authors report. The values printed by Da Silva et al. (9.0 and 7.15) lie on this family.</p>
<p><strong>All tubes.</strong> The low-pressure vortices of Kida et al. (2002) and the all-event averages of Mouri and Hori (2009), with one fitted factor for the chord effect on the swirl, give</p>
$$\frac{U_{\max}}{U_\eta}\bigg|_{\text{all}}=@AA@\,Re_\lambda^{@AS@},\qquad\text{chord factor }@AF@\qquad(\text{rms }@ARMS@\%).$$
<p>The exponent within Mouri and Hori alone is @SM@ and within Kida et al. alone @SK@; a chord factor of 3 forces an exponent of @A3S@ that neither source shows (rms @A3RMS@%). The fitted factor @AF@ lies at the low end of the chord model (2 to 3.5). This is what Mouri and Hori state: the swirl of all tubes scales with the Kolmogorov velocity, that of intense tubes with the r.m.s. velocity.</p>
<p><strong>Checks with data not used in a fit.</strong> Kida et al. measured the volume fraction of their vortex cores: 0.35 at \(Re_\lambda=83\) and 0.31 at 170. The budget of section 7 gives @VK83B@ and @VK170B@ with the all-tube swirl of model II, and @VK83A@ and @VK170A@ with model I. Sassa and Makita (2005), who sample events at a moderate threshold between \(Re_\lambda=19\) and 2391, report an exponent 0.28 for the swirl, between the two families. The mean swirl of all tubes in the mixing layer of Tanahashi et al. (2001; \(Re_\lambda\approx80\)) is 3.7 \(U_\eta\) (model II: 3.6); that of Pirozzoli (2012; \(Re_\lambda\approx99\)) is 2.5 (model II: 3.7), a disagreement that remains.</p>
@PREDTABLE@
<p class="note">Table 3. Predictions of the two models at \(\beta=5\). The last column is \(4.91\,V_f\,(U_{\max}/\beta U_\eta)^2\) for \(V_f=0.01\).</p>
<p><strong>Which model.</strong> Model I is the simplest description of the corrected data and is retained as the reference. Model II rests on fewer adjustments (one fitted factor against two), agrees with what the authors of the hot-wire papers conclude, and reproduces the measured volume fraction at both Reynolds numbers; its weakness is that the all-tube law rests on two sources. The two differ little near \(Re_\lambda\approx100\), where most simulations are, and by a factor 1.5 in the swirl at \(Re_\lambda=1000\) (Table 3). For a closure of micromixing, which depends on all tubes weighted by their volume, we recommend model II and regard the difference between the two as the uncertainty of the swirl at high Reynolds number. The intense tubes, if they keep 1% of the volume, carry 6% of the dissipation at \(Re_\lambda=100\) and a growing share above (Table 3, last column).</p>

<h2>13. Use as a closure in CFD, and the delay of the cascade</h2>
<h3>The closure</h3>
<p>A Reynolds-averaged or large-eddy solver provides the turbulent kinetic energy \(k\) and the dissipation rate \(\varepsilon\) in each cell (in a large-eddy simulation, the subgrid values). With \(u'^2=2k/3\) and isotropic small scales,</p>
$$Re_\lambda=\sqrt{\frac{20}{3}}\,\frac{k}{\sqrt{\nu\varepsilon}},\qquad \eta=\left(\frac{\nu^3}{\varepsilon}\right)^{1/4},\qquad \tau_\eta=\sqrt{\frac{\nu}{\varepsilon}} .$$
<p>The tubes in the cell then have the radius \(r_{\max}=5\eta\), the stretching rate \(\gamma=0.201/\tau_\eta\), the swirl of model I or II, and the circulation, volume fraction and spacing of section 11. These are the quantities a micromixing model needs: \(\gamma\) is the rate at which a fluid element in a tube is thinned, \(d\) the distance over which fresh fluid must be brought to a tube, \(\Gamma/\nu\) the Reynolds number of the engulfing motion. The engulfment rate of Ba&#322;dyga and Bourne, \(E=0.058\,(\varepsilon/\nu)^{1/2}\), is \(0.29\,\gamma\), and the vortex size they assumed, \(12\,\eta\), is the tube diameter \(2r_{\max}=10\,\eta\): the closure gives their model a measured basis and adds the dependence on \(Re_\lambda\) through the swirl and the volume fraction.</p>
<p>The closure applies where the small scales are in local equilibrium with \(\varepsilon\) and \(Re_\lambda\) is within the data (35 to about 2000). Stirred tanks and jets at process scale are within this range; near walls and at interfaces the tubes are aligned and somewhat wider (Tanahashi et al. 2004), which the closure does not represent.</p>

<h3>The delay between energy input and dissipation</h3>
<p>The closure is local in time: it takes the tubes to follow \(\varepsilon\) at once. They cannot. Energy put into the large scales reaches the dissipative scales only after it has passed down the cascade, and the dissipation in the tubes lags the input. In forced turbulence the dissipation follows the energy input with a delay of the order of a large-eddy turnover time (Pearson et al. 2004); in decaying turbulence the transit takes about half an initial turnover time (Yoffe and McComb 2018); and where the large scales change faster than this, the dissipation departs from its equilibrium scaling altogether (Vassilicos 2015; Goto and Vassilicos 2016). In a stirred tank a fluid element passes the impeller stream in a time comparable with the turnover time of the eddies made there, so the tubes that perform the micromixing downstream were fed by the energy input upstream.</p>
<p>The transit time follows from the cascade itself. An eddy of size \(\ell\) hands its energy on in its turnover time \(\ell^{2/3}\varepsilon^{-1/3}\). Integrating \(d\ell/dt=-a\,\ell^{1/3}\varepsilon^{1/3}\) from the energy-containing scale \(L=u'^3/\varepsilon\) to the tube radius \(\beta\eta\) gives</p>
$$T_c=\frac{3}{2a}\,\frac{L^{2/3}-(\beta\eta)^{2/3}}{\varepsilon^{1/3}}=C_c\,\tau_\eta\left(\frac{Re_\lambda}{\sqrt{15}}-\beta^{2/3}\right),\qquad C_c=\frac{3}{2a},$$
<p>using \(L/\eta=(Re_\lambda/\sqrt{15})^{3/2}\). The transit time is \(C_c\) large-eddy times \(u'^2/\varepsilon=\tfrac23k/\varepsilon\), less the part of the cascade below the tubes, and it vanishes at \(Re_\lambda=\sqrt{15}\,\beta^{2/3}\approx11\), where the tubes are the large eddies. The response of a tube itself, \(1/\gamma\approx5\,\tau_\eta\), is short compared with \(T_c\) above \(Re_\lambda\approx40\): the delay is that of the cascade, not of the formation of the tube. This is the idea of the multiple-time-scale models (Hanjali&#263; et al. 1980; Schiestel 1987) and of the spectral relaxation model for scalars (Fox 1995), reduced here to the one lag the tube closure needs.</p>
<p>In a flow solver the lag is one transport equation for the dissipation rate that the tubes see, \(\varepsilon_t\),</p>
$$\frac{D\varepsilon_t}{Dt}=\frac{\varepsilon-\varepsilon_t}{T_c}+\nabla\!\cdot\!\left(\frac{\nu_t}{\sigma}\nabla\varepsilon_t\right),$$
<p>with \(\varepsilon\) the solver's dissipation rate, read as the rate at which energy enters the cascade, and the tube closure evaluated with \(\varepsilon_t\). In steady homogeneous turbulence \(\varepsilon_t=\varepsilon\) and the closure of the previous subsection is recovered. The constant \(C_c\) is of order one: halving the scale at each step gives 2.7, the observed lags correspond to 0.5 to 1 in units of the turnover time used by those authors. We propose \(C_c\) as the single constant to be calibrated, against the time series of injection and dissipation in forced simulations and against the yield of a fast competitive reaction at varying feed position in a stirred tank, where the lag moves the zone of intense micromixing downstream of the zone of intense energy input.</p>

<h2>14. Limits and open questions</h2>
<ul>
<li><strong>The swirl at high Reynolds number.</strong> Models I and II differ by a factor 1.5 at \(Re_\lambda=1000\). The all-tube law rests on Kida et al. (two simulations) and Mouri and Hori (one probe method, one fitted factor). A simulation above \(Re_\lambda\approx400\) analysed without a threshold would decide.</li>
<li><strong>Which radius.</strong> The peak of the radius distribution is \(5\eta\), its mean 7 to 8 \(\eta\). The budget of section 7 varies as \(\beta^2\) and \(\beta^4\); a closure of a property dominated by the larger tubes would need the mean. The radius divisor of the probe data (1.75) assumes the peak.</li>
<li><strong>Definitions.</strong> The core of Kida et al. is bounded by the inflection of the pressure, which for a Burgers vortex lies at \(0.66\,r_{\max}\); we follow the literature in comparing its diameter with the diameter of maximum swirl. Da Silva et al. give two inconsistent values of the swirl.</li>
<li><strong>The budget.</strong> The volume fraction follows from assigning to the background the dissipation of a uniform strain at the rate of the tubes; it is checked against two measured values only.</li>
<li><strong>The lag.</strong> The form of \(T_c\) is a scaling argument and \(C_c\) is not calibrated.</li>
<li><strong>Range.</strong> Isotropic small scales, \(35\le Re_\lambda\le1934\); no wall or interface effects.</li>
</ul>

<h2>15. Conclusions</h2>
<p>The vortex tubes of the dissipative range have a radius of maximum swirl of \(5\eta\) in every flow examined, independent of the Reynolds number; this is the firmest result. Their swirl is described by one law, \(U_{\max}/U_\eta=@C6@\,Re_\lambda^{1/3}\), if probe data and the most intense tubes are corrected to a common level, and by two laws without swirl corrections if the most intense tubes and all tubes are taken as two populations. Model selection with leave-one-source-out validation shows that the data support no more than one or two parameters in either case. The Burgers budget then gives the strain rate, circulation, volume fraction and spacing of the tubes from \(k\) and \(\varepsilon\), which places the engulfment model of micromixing on measured ground, and a first-order lag with one constant accounts for the time the cascade takes to feed the tubes. The path of every number from its paper to the model is recorded and open to comment.</p>
"""


def main(argv=None):
    text = build()
    with open(PAGE, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("wrote %s (%.2f MB)" % (PAGE, len(text.encode("utf-8")) / 1e6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
