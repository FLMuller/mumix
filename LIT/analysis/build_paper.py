r"""build_paper.py  v01  Build the paper (../vortex-energy-balance.html) in journal form from the theory of the page, the reconciled data and the fits.

    python build_paper.py            writes ../vortex-energy-balance.html; publish with publish_page.py

What is kept and what is new.  The derivation (sections 2-8 of the page: the Burgers vortex, its energy budget, the closure with the Kolmogorov scales) is taken
unchanged from the snapshot ../zprev/vortex-energy-balance_v47.html, so its notation is that of the page.  Everything else is written here: abstract, introduction
(section 1), the data and their treatment (9), the selection of the model (10), the selected model (11), the two-population reading (12), the use as a closure in
CFD with the delay of the cascade (13), limits (14), conclusions (15).  The references of the page are kept and the new ones added; the appendix (the source data,
paper by paper) is made again from sourcedata.py (build_data_sections.build_appendix).
The numbers of the text come from ../fittingtool/results/modelselect.json (modelselect.py) and from fits made here, through the @KEY@ place holders.

Versions  M01 m01.v02 (2026-11-15): the section 9a DNS PDF, between sections 9 and 10 (tables D1, D2, figures D1-D3; dns_pdf_section; numbered 9a so that sections 10-15 keep their numbers).
          M01 m01.v01 (2026-11-12): first version (replaces the build of sections 1, 9, 10, 11 by build_intro_sections, build_data_sections.main and build_fit_sections).
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
    ax.plot(re, c6 * re ** 0.5, "--", color="k", lw=1.3, label=r"single law of section 11: $%.3f\,Re_\lambda^{1/2}$ (corrected data)" % c6)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"$Re_\lambda$", fontsize=11)
    ax.set_ylabel(r"$U_{max}/U_\eta$ as calculated from the papers", fontsize=11)
    ax.grid(alpha=0.25, which="both")
    ax.legend(fontsize=7.5, loc="upper left", frameon=True)
    fig.tight_layout()
    return pagefigures.fit_to_column(fitreport.svg_of(fig))


def png_html(name, caption):
    """A figure of analysis/<name> (png) embedded in the page, with its caption."""
    import base64
    with open(os.path.join(HERE, name), "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    return "<p style=\"text-align:center\"><img alt=\"%s\" style=\"max-width:100%%\" src=\"data:image/png;base64,%s\"></p>\n<p class=\"note\">%s</p>" % (name, data, caption)


def wire_tube_section():
    """The section on the wire-and-tube model (hot-wire crossings of stretched vortices): the model, the fit to Belin et al. (1996), what it says about the tubes, and the comparison with the DNS."""
    with open(os.path.join(HERE, "belin_model_numbers.json"), encoding="utf-8") as f:
        bm = json.load(f)
    with open(os.path.join(HERE, "paper_chord_numbers.json"), encoding="utf-8") as f:
        pc = json.load(f)
    r659 = {r["Re_lambda"]: r for r in bm["rows"]}[659]
    p = bm["params"]
    ratio = r659["U_belin"]["median"] / r659["U_read_true"]["median"]
    text = r"""<h3>The wire-and-tube model of a hot-wire crossing</h3>
<p>The experimental rows of the table (Belin et al., Mouri et al., Sassa and Makita) are not measurements of tubes: they are what a wire reads as tubes are carried past it, converted back to a tube by a rule. The earlier version of this correction (appendix A0c, the chord model) took a tube, a straight path through it at a random offset and tilt, and a sensed component, and reproduced the size distribution of Belin et al. only with a swirl at or above the speed of the disks. The cause was found in the paper of Belin et al. itself (their Fig. 3 and eqs. 2&ndash;8): the wire is cooled by the velocity normal to it, and the tube crosses the wire at a small angle \(\alpha\) to that direction. The model that follows adds that angle and the cooling law, and replaces the weights of the old model by the geometry of a volume of tubes.</p>
<p><em>Tube.</em> A straight Burgers vortex, \(v_\theta(\rho)=\omega_0R^2\,(1-e^{-\rho^2/2R^2})/\rho\), \(r_{\max}=1.585R\), \(U_{\max}=0.4512\,\omega_0R\), circulation \(\Gamma=8.784\,r_{\max}U_{\max}\), with an isotropic axis. <em>Wire.</em> A fixed wire along \(y\); the mean flow \(U=0.588\,\Omega R\) of the table (recording book, tab Belin) is along \(x\), normal to the wire. A tube is carried with the velocity \(\mathbf W=\mathbf U+\mathbf w\), where \(\mathbf w\) is the large-scale fluctuation along the wire (rms \(u'\)); the incidence angle \(\alpha\) is the angle between \(\mathbf W\) and \(x\), \(\tan\alpha=w/U\), so \(\sin\alpha\) is random with a standard deviation \(u'/U=0.29\), the same at every \(Re_\lambda\) in the table. By Taylor's hypothesis the time is a distance, \(s=|\mathbf W|\,t\). The wire cools with the speed</p>
$$U_{\mathrm{eff}}=\sqrt{|\mathbf u|^2-(1-k^2)\,(\mathbf u\cdot\mathbf e_w)^2},\qquad \mathbf u=\mathbf U+\mathbf v,$$
<p>with the yaw coefficient \(k=0.2\) (the velocity along the wire cools it only a little), and the signal is \(S=U_{\mathrm{eff}}-U_{\mathrm{eff}}(\text{no tube})\). To first order the wire reads the component of the swirl along its normal direction, and for a tube whose axis is normal to \(\mathbf W\) and to the wire, crossed through its axis,</p>
$$S(s)=\sin\alpha\;\mathrm{sgn}(s)\,v_\theta(|s|),\qquad \Delta S=2\sin\alpha\,U_{\max},$$
<p>two extrema \(3.17R\) apart (Belin et al., eq. 7). Without the angle there is almost no S-shape: for such a tube the swirl at the wire is perpendicular to the path. <em>Reading.</em> Belin et al. read \(r_{\max}=\tfrac12\Delta s\) from the spacing of the extrema and \(U_{\max}=\Delta S/(2\sin\alpha)\) with the constant \(\sin\alpha=0.14\) (8&deg;, estimated from the signal); the model applies the same rules to its own signals.</p>
<p><em>Which tubes the wire meets.</em> Tubes of length \(L\gg R\) fill a volume. A tube whose closest approach to the wire is closer than the largest distance at which it can still pass the detection threshold, \(b_{\max}=\sqrt{\Gamma/(2\pi G_c)}\), can be detected (the velocity gradient of a line vortex is at most \(\Gamma/2\pi b^2\) outside the core); the number of tubes of a class met per unit time is the flow past the wire times the number of tubes per volume times their footprint in the plane normal to the flow, \(2b_{\max}L\cos(\text{tilt})\). The length \(L\) cancels in the distribution. A tube is therefore met in proportion to its detection range, not to its radius, and no tube that can be selected is dropped. <em>Selection.</em> Belin et al. keep the events at the far tails of the velocity derivative (area \(2.6\times10^{-3}\)), a velocity gradient above five standard deviations, \(|dS/ds|\ge5\,U_\eta/(\sqrt{15}\,\eta)\); an event is read when its signal has a maximum and a minimum within \(\pm2r_{\max}\) of the steepest point.</p>
<p><em>Inputs and fit.</em> The radius \(r_{\max}/\eta\) is lognormal, and the swirl is a scale \(S\) times the DNS value \(0.769\,Re_\lambda^{1/3}U_\eta\) with a lognormal spread; the two are independent. Fitting the size pdf (Fig. 5 of Belin et al.) and the pdf of the product \(Re_f/Re_\lambda^{1/2}\) (Fig. 6) at \(Re_\lambda=255\) and 659, in three phases (the radius alone, the swirl alone, all four), gives a radius median of %(m_r).2f \(\eta\) (ln-width %(s_r).2f) and a swirl %(S).2f times the DNS value (ln-width %(s_u).2f). The flow quantities (\(\nu\), \(\varepsilon\), \(U_\eta\), \(U\), \(u'\)) come from the correlations of Table I of Belin et al. (recording book, tab Belin).</p>
""" % dict(m_r=p[0], s_r=p[1], S=p[2], s_u=p[3])
    text += png_html("belin_model_fig659.png", "Fig. W1. The model fitted to Belin et al. (1996) at \\(Re_\\lambda=659\\) (the same fit at 255 is in the recording book). Top left: the radius, the tubes as generated (grey), the tubes that hit the wire (blue), the intense tubes (dashed) "
                     "and the radius as read (red) against Fig. 5; top right: the product \\(r_{\\max}U_{\\max}\\) as \\(x=Re_f/Re_\\lambda^{1/2}\\) against Fig. 6; bottom: \\(U_{\\max}\\) in cm/s and in \\(U_\\eta\\): (i) generated, (ii) hit the wire, (ii') hit, selected and read, (iii) observed by the wire (\\(\\Delta S/2\\)), "
                     "(iv) with Belin's \\(\\sin\\alpha=0.14\\), (v) with the actual \\(\\alpha\\) of each event.")
    text += r"""<p><strong>What the model says about the experiment.</strong> (1) The incidence angle makes the signal: the wire observes only \(\sin\alpha\,U_{\max}\), a median of %(obs).1f \(U_\eta\) against the true median of %(true).1f \(U_\eta\) of the events that are read; with \(\alpha=0\) only 1%% of the selected events could be read. (2) The events that are read and selected have large angles (median \(|\sin\alpha|=%(sa).2f\), against 0.19 over all crossings), so Belin's constant 0.14 overstates their swirl by a factor of %(ratio).1f; with the actual angle the median is %(act).1f \(U_\eta\), on the true value. (3) The cut favours strong tubes: the swirl of the tubes that are read is %(sel).1f times that of all tubes. (4) The radius that Belin reads is a little too large: the ratio of the radius read to the true radius of the same events is 1.06 at \(Re_\lambda=151\) and 1.18 at 718. (5) The fit needs a swirl %(S).1f times the DNS value (%(cm).0f cm/s at \(Re_\lambda=659\); the speed of the disks is 154 cm/s), and the radius pdf is narrower at the peak than Fig. 5; both are open (below).</p>
""" % dict(obs=r659["U_observed"]["median"], true=r659["U_read_true"]["median"], sa=r659["sin_alpha_read"]["median"], ratio=ratio, act=r659["U_actual_alpha"]["median"], sel=r659["U_read_true"]["median"] / r659["U_population"]["median"],
        S=p[2], cm=r659["U_population"]["median"] * r659["U_eta_cm_s"])
    text += png_html("paper_chord_compare.png", "Fig. W2. The tubes behind the records of Belin et al. (the model of Fig. W1 at \\(Re_\\lambda=659\\): all tubes, grey, and the intense tubes that are selected and read, dashed) against the pdfs of Tanahashi et al. (2001) "
                     "(orange, two lognormals fitted to their digitised pdfs, \\(Re_\\lambda\\approx80\\)). (a) \\(r_{\\max}/\\eta\\); (b) \\(U_{\\max}/u'\\).")
    text += r"""<p><strong>Comparison with the DNS.</strong> The radius of the tubes found from the hot-wire pdfs is that of the DNS: median %(rp).1f and mean %(rpm).1f \(\eta\) for all tubes (Tanahashi et al.: %(rt).1f and %(rtm).1f), and %(ri).1f and %(rim).1f for the intense tubes, close to the narrow lognormal of the DNS at about 5 \(\eta\) that the closure uses. The swirl is not: the median \(U_{\max}/u'\) of all tubes is %(up).2f and of the intense tubes %(ui).2f, against %(ut).2f of Tanahashi et al. (a factor 1.8 and 2.3); in units of \(U_\eta\) the intense tubes have %(ui2).0f at \(Re_\lambda=659\), about three times the law \(0.77\,Re_\lambda^{1/3}\). Three assumptions bear on this and are not tested by the pdfs of Belin et al.: the Gaussian spread of \(\sin\alpha\) with \(u'/U\), the independence of radius and swirl, and the use of one pdf (Fig. 6) pooled over \(Re_\lambda=151\)&ndash;718 for two Reynolds numbers.</p>
""" % dict(rp=pc["r_population"]["median"], rpm=pc["r_population"]["mean"], rt=pc["r_tanahashi"]["median"], rtm=pc["r_tanahashi"]["mean"], ri=pc["r_intense"]["median"], rim=pc["r_intense"]["mean"],
        up=pc["u_population"]["median"], ui=pc["u_intense"]["median"], ut=pc["u_tanahashi"]["median"], ui2=r659["U_read_true"]["median"])
    text += r"""<p class="note">The DNS law of this section, \(U_{\max}=0.769\,Re_\lambda^{1/3}U_\eta\), is the law of the selection at the time the model was fitted; the selection of section 10 now gives \(U_{\max}/U_\eta=@C6@\,Re_\lambda^{1/2}\) (\(U_{\max}=@KAPPA@\,u'\)), on the data of Fig. 1b. The tubes found from the records of Belin et al. do not depend on it: their swirl, 2.58 times the old law, is fitted to their Fig. 6 and is the fixed product \(1.98\,Re_\lambda^{1/3}U_\eta\), so the multipliers computed on them (Fig. 1b, the recording book) stand. The runs with tubes of the DNS (this section and the next) were not repeated with the new law, which is larger than the old one by a factor @DNSRATIO@ at \(Re_\lambda=332\) and @DNSRATIO2@ at 1934.</p>
"""
    return text


def onedim_section():
    """The one-dimensional methods of Mouri et al. (2007), Mouri and Hori (2009) and Sassa and Makita (2005) applied to model tubes (chord_mouri.py): the test of the tubes and of the two chord factors."""
    def load(name):
        with open(os.path.join(HERE, name), encoding="utf-8") as f:
            return json.load(f)
    dns, bel, low = load("chord_mouri_dns.json"), load("chord_mouri_belinfit.json"), load("chord_mouri_lowk.json")
    re = [m["Re_lambda"] for m in dns["mouri"]]

    def row(key, field, data=dns["mouri"], fmt="%.1f"):
        return ", ".join(fmt % m[key][field] for m in data)

    def pap(field):
        return ", ".join("%.1f" % m["paper"][field] for m in dns["mouri"])
    sa = {s["Re_lambda"]: s["C=2.5"] for s in dns["sassa"]}
    k5 = {q["Re_lambda"]: q["k=0.5"] for q in low}
    k25 = {q["Re_lambda"]: q["k=0.25"] for q in low}
    rf5 = [k5[R]["R0"] / k5[R]["true_r"] for R in re]
    uf5 = [k5[R]["true_U"] / k5[R]["V0"] for R in re]
    rf25 = [k25[R]["R0"] / k25[R]["true_r"] for R in re]
    uf25 = [k25[R]["true_U"] / k25[R]["V0"] for R in re]
    m719 = {m["Re_lambda"]: m for m in dns["mouri"]}[719]
    text = r"""<h3>The one-dimensional methods of Mouri et al. and Sassa and Makita on the model tubes</h3>
<p>The hot-wire rows of the table come from three methods that average the signals of the events found by a threshold. All three use a crossed wire and the <em>transverse</em> velocity (the spanwise \(v\) of Mouri et al., the vertical \(w\) of Sassa and Makita), which is linear in the swirl and needs no incidence angle. Mouri et al. (2007) take the increment \(v(x+\delta x_s/2)-v(x-\delta x_s/2)\) over the sampling interval, keep the events above the threshold that holds 0.1% or 1% of all increments (6.0&ndash;6.7 and 3.5&ndash;3.7 standard deviations, their Table II), align and average the signals and fit the mean profile with the Burgers vortex around its peaks (\(R_0\), \(V_0\)). Mouri and Hori (2009) take all local extrema of the Gaussian-smoothed increment over \(6\eta\), above the background, and do the same. Sassa and Makita (2005) keep the events with \(dw/dt\ge C\,\mathrm{rms}(dw/dt)\), \(C=2.5\), and read the diameter and the maximum velocity from the two peaks of the mean trace. The wire-and-tube model above gives these methods a population to act on: the transverse component of the swirl along the path of the mean flow, smoothed by the probe (1 mm for Mouri et al., about \(\eta\) for Sassa and Makita), the thresholds in units of the rms increment \(\sqrt{2/15}\,(U_\eta/\eta)\,\delta x\) of the dissipative range, and the same weights, so the three methods are applied to the same model as the wire of Belin et al. There is no background turbulence in the model.</p>
<p><strong>The result.</strong> Tubes of the DNS (\(r_{\max}\approx5.2\,\eta\) with a narrow lognormal width of 0.3, and \(U_{\max}=0.769\,Re_\lambda^{1/3}U_\eta\) times a lognormal of width 0.4, no scale factor) reproduce the three methods. (1) <em>Mouri et al. (2007), 0.1%:</em> \(V_0/u_K\) at \(Re_\lambda=@RE@\) is @V01M@ in the model against @V01P@ in the paper, and \(R_0/\eta\) is @R01M@ against @R01P@. <em>1%:</em> \(V_0/u_K\) is @V1M@ against @V1P@, and \(R_0/\eta\) @R1M@ against @R1P@. (2) <em>Sassa and Makita (2005):</em> the maximum velocity of the mean trace is @SV19@ \(u_K\) at \(Re_\lambda=19\), @SV300@ at 300 and @SV2391@ at 2391, against 2.8, 4.2 and 6.5 in the paper (the shear flow at 820 is lower in the paper, 2.1, than the model, @SV820@), and the diameter is @SD19@, @SD300@, @SD2391@ \(\eta\) against their value of about 10 \(\eta\). (3) <em>Mouri and Hori (2009), all tubes:</em> the all-tube average is reproduced when the threshold is very low, 0.25&ndash;0.5 standard deviations of the increment over \(6\eta\): \(R_0/\eta=@R05M@\) and \(V_0/u_K=@V05M@\) for the threshold 0.5 at \(Re_\lambda=@RE@\), against @RALLP@ and @VALLP@ in the paper (the threshold 0.25 gives @R025M@ and @V025M@). The true radius of the same events is 5.4 \(\eta\) and the true swirl @UTRUE@ \(U_\eta\) (\(Re_\lambda=332\)&ndash;1934). The ratios of the model are, for the thresholds 0.5 and 0.25, a radius factor of @RF5@ and @RF25@ and a swirl factor of @UF5@ and @UF25@; the corrections adopted in this paper for Mouri and Hori, 1.75 and 3, lie inside these ranges.</p>
"""
    rep = {"@RE@": ", ".join(str(r) for r in re), "@V01M@": row("0.1%", "V0"), "@V01P@": pap("v01"), "@R01M@": row("0.1%", "R0"), "@R01P@": pap("r01"), "@V1M@": row("1%", "V0"), "@V1P@": pap("v1"), "@R1M@": row("1%", "R0"), "@R1P@": pap("r1"),
           "@SV19@": "%.1f" % sa[19]["v_peak"], "@SV300@": "%.1f" % sa[300]["v_peak"], "@SV2391@": "%.1f" % sa[2391]["v_peak"], "@SV820@": "%.1f" % sa[820]["v_peak"],
           "@SD19@": "%.0f" % (2 * sa[19]["r_peak"]), "@SD300@": "%.0f" % (2 * sa[300]["r_peak"]), "@SD2391@": "%.0f" % (2 * sa[2391]["r_peak"]),
           "@R05M@": ", ".join("%.1f" % k5[R]["R0"] for R in re), "@V05M@": ", ".join("%.1f" % k5[R]["V0"] for R in re), "@RALLP@": pap("r_all"), "@VALLP@": pap("v_all"),
           "@R025M@": ", ".join("%.1f" % k25[R]["R0"] for R in re), "@V025M@": ", ".join("%.1f" % k25[R]["V0"] for R in re),
           "@UTRUE@": "%.1f&ndash;%.1f" % (k5[re[0]]["true_U"], k5[re[-1]]["true_U"]),
           "@RF5@": "%.2f&ndash;%.2f" % (min(rf5), max(rf5)), "@RF25@": "%.2f&ndash;%.2f" % (min(rf25), max(rf25)), "@UF5@": "%.1f&ndash;%.1f" % (min(uf5), max(uf5)), "@UF25@": "%.1f&ndash;%.1f" % (min(uf25), max(uf25))}
    for k, v in rep.items():
        text = text.replace(k, v)
    text += png_html("chord_mouri.png", "Fig. W3. The three one-dimensional methods applied to model tubes. Blue: tubes of the DNS (\\(r_{\\max}\\approx5\\,\\eta\\), \\(U_{\\max}\\) of the DNS); red dashed: the tubes found from Belin et al. (median \\(r_{\\max}\\) 7.3 \\(\\eta\\), \\(U_{\\max}\\) 2.6 times the DNS); "
                     "open black symbols: the papers. Circles: the 0.1% class (Mouri et al. 2007), squares: 1%, triangles: all tubes at the threshold of 2 standard deviations (the paper's all-tube average needs 0.25&ndash;0.5, see the text). Right: the diameter of the mean trace of Sassa and Makita (2005).")
    r01_719 = m719["0.1%"]["R0"] / m719["0.1%"]["true_r"]
    r1_719 = m719["1%"]["R0"] / m719["1%"]["true_r"]
    u01_719 = m719["0.1%"]["V0"] / m719["0.1%"]["true_U"]
    u1_719 = m719["1%"]["V0"] / m719["1%"]["true_U"]
    text += r"""<p><strong>What this says.</strong> (1) The three one-dimensional methods and the DNS tubes agree: a radius of about \(5\,\eta\) and a swirl of the DNS law, \(0.77\,Re_\lambda^{1/3}U_\eta\), explain the 0.1% and 1% classes of Mouri et al., the mean trace of Sassa and Makita and, with a threshold at the level of the background, the all-tube average of Mouri and Hori. The tubes found from the records of Belin et al. do not: with the same methods they read radii and velocities 1.5 to 5 times too high (Fig. W3). The record of Belin et al. is the outlier of the data, and its amplitude needs tubes 2.6 times stronger than the DNS with the wire model above, also with a wider spread of the incidence angle (\(\sin\alpha\) of width 0.6: 2.4 times). (2) The relation between the classes, at \(Re_\lambda=719\): the radius read is @RR01@ (0.1%), @RR1@ (1%) and @RRALL@ (all tubes, threshold 0.5) times the true radius of the events, and the swirl read is @UR01@, @UR1@ and @URALL@ times the true swirl, so that a high threshold reads near-axis crossings (and smaller, stronger tubes: the true radius of the events falls and the true swirl rises with the threshold). (3) The two chord factors of this paper, radius divided by 1.75 and swirl multiplied by 3 for the all-tube average of Mouri and Hori, are supported by a model with one-dimensional geometry only; the threshold of the all-tube average is not given in the paper and is the one free quantity (0.25&ndash;0.5 standard deviations). Limits: no background turbulence in the model (the lowest thresholds are where it matters most), radius and swirl independent, and one smoothing length for the probe.</p>
""".replace("@RR01@", "%.2f" % r01_719).replace("@RR1@", "%.2f" % r1_719).replace("@RRALL@", "%.2f" % (k5[719]["R0"] / k5[719]["true_r"])).replace("@UR01@", "%.2f" % u01_719).replace("@UR1@", "%.2f" % u1_719).replace("@URALL@", "%.2f" % (k5[719]["V0"] / k5[719]["true_U"]))
    return text


def dns_pdf_section():
    """The section 9a DNS PDF: the digitised radius and swirl pdfs of the DNS and PIV papers, scaled to unit area, with the lognormal fits (one lognormal, two only if the misfit falls by 30 %) from dns_pdfs_params.csv."""
    import csv
    rows = list(csv.DictReader(open(os.path.join(HERE, "dns_pdfs_params.csv"), encoding="utf-8")))
    dash = lambda v: "&ndash;" if v == "-" else v
    def tab(quantity, with_rmax):
        head = ["source", "area", "mode", "mean"] + ([r"mean \(r_{\max}\)"] if with_rmax else []) + ["n", r"\(a_1\)", r"\(m_1\)", r"\(\sigma_1\)", r"\(m_2\)", r"\(\sigma_2\)", "rms"]
        body = []
        for r in rows:
            if r["quantity"].startswith(quantity):
                lab = r["source"].replace("Jimenez", "Jim&eacute;nez").replace("Re_lambda", r"\(Re_\lambda\)").replace("Re_tau", r"\(Re_\tau\)")
                body.append([lab, r["area"], r["mode"], r["mean"]] + ([dash(r["r_max mean (page)"])] if with_rmax else []) + [r["n"], r["a1"], r["m1"], r["sigma1"], dash(r["m2"]), dash(r["sigma2"]), r["rms"]])
        return table(head, body)
    text = r"""<h2>9a. DNS PDF</h2>
<p>The probability densities of the radius and of the swirl of the tubes were digitised from every DNS and scanning-PIV paper that prints them (Tanahashi et al. 2001, 2004; Das et al. 2006; Pirozzoli 2012; Wang et al. 2007; Ghira et al. 2022; Jim&eacute;nez and Wray 1998; Aligolzadeh et al. 2023), each from the figure of the paper (recording book, with the digitised curve drawn over the figure). The radius is that of each paper: \(D/2\) of the coherent eddy (Tanahashi, Das, Wang), \(r_0\) of the core (Pirozzoli), the \(1/e\) radius \(R_{ivs}\) or \(R\) of the vorticity of the intense structures (Ghira, Jim&eacute;nez) and the radius \(R/\eta\) of the structure boundary (Aligolzadeh). Every curve was scaled to unit area; the area of the curve as digitised, 0.94 to 1.06, checks the axes. Ghira et al. (2022) are read from the vector paths of the pdf, so for them the check is exact.</p>
<p>Each curve was fitted with one lognormal function, \(p(x)=\exp[-(\ln x-\mu)^2/2\sigma^2]/(x\sigma\sqrt{2\pi})\), median \(m=e^{\mu}\), and with a sum of two, \(a_1p_1+(1-a_1)p_2\) (the function of the page, the first the narrow one, widths at most 0.7 for the radius). The sum of two is kept only where its rms misfit (divided by the peak) is below 0.7 times that of the single one; this threshold is our choice, and the entries with a ratio between 0.65 and 0.8 (the swirl of Tanahashi et al. 2004, 0.69, of Wang et al., 0.66, and of Pirozzoli, 0.75, and the two histograms of Aligolzadeh et al., 0.80 and 0.75) would change with it. Where \(n=1\), \(a_1=1\) and there is no second lognormal. \(m\) is in \(\eta\) for the radius and in \(u_K\) or \(u'\) for the swirl.</p>
<p class="note">Table D1. Radius pdfs: area as digitised, mode and mean of the curve, the mean times 1.12 for the \(1/e\) radii (the conversion to \(r_{\max}\)), and the parameters of the lognormal fit.</p>
""" + tab("radius", True) + r"""
<p class="note">Table D2. Swirl pdfs, in \(u_K\) (the first four rows; Tanahashi et al. 2001 converted with \(Re_\lambda=80\), an assumption) and in the rms velocity \(u'\) (the last three).</p>
""" + tab("swirl / u_K", False) + tab("swirl / u'", False) + "\n"
    text += png_html("dns_pdfs_radius.png", "Fig. D1. The radius pdfs of the DNS and PIV papers on linear axes, each scaled to unit area.")
    text += png_html("dns_pdfs_swirl.png", r"Fig. D2. The swirl pdfs, on linear axes: left in \(u_K\) (Tanahashi et al. 2001, dotted, converted with \(Re_\lambda=80\)), right in \(u'\).")
    text += png_html("dns_pdfs_mu_sigma.png", r"Fig. D3. The width \(\sigma\) against the position \(\mu=\ln m\) of Tables D1 and D2: one point per pdf, its first lognormal: circle, where one lognormal was chosen; triangle, the first (narrow) of two.")
    text += r"""<p>The pdfs without a volume threshold (Tanahashi, Das, Pirozzoli, Wang) are sums of two lognormals: a narrow family of median 4.3 to 6.2 \(\eta\) and width 0.23 to 0.35, and a broad one of median 8.5 to 17 \(\eta\) and width 0.6 to 0.7, which is the long tail of Fig. D1 and carries the mean to 7.2 to 10.2 \(\eta\). The sets that select the intense tubes by a threshold on the volume (Ghira et al., 1%; Jim&eacute;nez and Wray) and the PIV histograms of Aligolzadeh et al. have no such tail: the seven runs of Ghira et al. are one lognormal each, of median 4.14 (\(Re_\lambda=90\)) falling to 3.73 \(\eta\) (399) and width 0.26 to 0.28. In Fig. D3 (one point per pdf, always its first lognormal, so that the same family is compared across the sets) the radius points have \(\mu=1.04\) to 1.82 (median 2.8 to 6.2 \(\eta\)) and \(\sigma=0.13\) to 0.50. There is no one relation between \(\sigma\) and \(\mu\): over the 15 points the correlation is only 0.45 (0.41 over the 9 sources, the seven runs of Ghira et al. counted as one); within the thresholded sets it is +0.85 (\(\sigma\approx-0.49+0.57\mu\), 10 points) and within the unthresholded sets \(-0.85\) (5 points), whose narrow lognormals cluster at \(\mu=1.46\) to 1.82 and \(\sigma=0.23\) to 0.35 (median 4.3 to 6.2 \(\eta\)). The swirl pdfs are too few to give a trend: the first lognormals of the four pdfs in \(u_K\) are alike (median 1.9 to 2.3 \(u_K\), \(\sigma=0.62\) to 0.77) and those of the three in \(u'\) have \(\sigma=0.54\) to 0.86 (median 0.29 to 0.64 \(u'\)), the curve of Tanahashi et al. (2001) being in both units.</p>
"""
    text += ghira_cut_section()
    return text


def ghira_cut_section():
    """The correction of the 1%-volume DNS (Ghira et al.) worked out on the all-tube population of Pirozzoli (2012), in steps down to the two multipliers (radius x 1.25, swirl x 0.67), with the tubes filling 35% of the flow."""
    import ghira_cut_factors as gcf
    import ghira_cut_families as gcfam
    import ghira_cut_g80 as g80
    r, pr, u, pu = gcf.population()
    rf, uf, narrow, _ = gcfam.population()
    body = []
    for phi in (0.10, 0.20, 0.35):
        for g0 in (80.0, 94.0):
            c = g80.constant_g(r, pr, g0, phi)
            body.append(["%.0f%%" % (100 * phi), "G constant, %.0f" % g0, "%.2f" % c["wc"], "%.2f" % c["r_c"], "%.2f" % c["kept"], "%.2f" % c["er"], "%.2f" % c["eu"], "%.2f" % (g80.NARROW_MEAN / c["er"]), "%.2f" % (c["mean_u"] / c["eu"])])
        c = gcfam.cut(rf, uf, narrow, phi)
        body.append(["%.0f%%" % (100 * phi), r"\(r\) and \(G\) independent", "%.2f" % c["wc"], "&ndash;", "%.2f" % c["kept"], "%.2f" % c["er"], "%.2f" % c["eu"], "%.2f" % c["f_R"], "%.2f" % c["f_U"]])
    with open(os.path.join(TOOL, "results", "modelselect.json"), encoding="utf-8") as f:
        scen = json.load(f)["scenarios"]
    now = {m["key"]: m for m in scen[0]["models"]}
    old = {m["key"]: m for m in [s for s in scen if s["label"].startswith("without Mouri-Hori, Ghira radius as listed")][0]["models"]}               # the same fits with the radius of Ghira et al. as listed
    big = {m["key"]: m for m in [s for s in scen if s["label"].startswith("without Mouri-Hori, Ghira radius x 1.85")][0]["models"]}                   # and with the whole-pdf mean as the target (x 1.85, x 0.6)
    keys = ("D4", "D2", "L1")
    def rng(d, k):
        lo, hi = "%.0f" % min(d[x][k] for x in keys), "%.0f" % max(d[x][k] for x in keys)
        return "%s%%" % lo if lo == hi else "%s%% to %s%%" % (lo, hi)
    text = r"""<h3>The correction of the 1%-volume DNS (Ghira et al.), in steps</h3>
<p>The DNS of Ghira et al. (2022, 2025) keep the strongest 1% of the volume by vorticity: a subset of the tubes, smaller and faster than the whole population. To bring it to the whole population we chose Pirozzoli (2012) as the reference, because his pdfs of the core radius and of the maximum velocity are of all the vortex cores found, with no lower threshold on the vorticity (his only selections are an angle of at most 20&deg; between the vorticity and the plane normal and a clear swirling pattern), and worked out the scaling factors from it, in the steps below, with the tubes filling 35% of the flow.</p>
<ol>
<li><strong>The row to correct.</strong> The row of Ghira et al. is the mean \(r_{\max}\) and \(U_{\max}\) of the structures above the vorticity \(\omega_c\) that holds the strongest 1% of the volume: \(r_{\max}=4.5\) to 5.0 \(\eta\) (\(1.12\,R_{ivs}/(R_{ivs}/R_B)\)), the swirl converted to the Burgers peak.</li>
<li><strong>The reference.</strong> Pirozzoli (2012), Fig. 2: the pdf of the radius \(r_0\) (mean 7.2 \(\eta\) over the range digitised, median 5.3, most frequent 4.2; the text says 'expected value about 6'; a narrow family of 53% of the tubes with mean 4.55 \(\eta\) and a broad family with median 8.5 \(\eta\) whose far tail sets the mean) and of the maximum velocity \(v_0\) (mean 2.5 \(u_K\); the text says about 2).</li>
<li><strong>The vorticity of a tube.</strong> A Burgers vortex has \(\omega(\rho)=\omega_0\,e^{-\rho^2/2R^2}\), \(R=r_{\max}/1.585\) and \(\omega_0=3.512\,U_{\max}/r_{\max}\) in units of \(1/\tau_\eta\), which is the rms vorticity of homogeneous isotropic turbulence (\(\varepsilon=\nu\langle\omega^2\rangle\)).</li>
<li><strong>Pairing the radius with the swirl.</strong> His pdfs are separate, but his text gives the most frequent circulation, \(\Gamma_\infty/\nu=80\), with \(\Gamma_0=2\pi r_0v_0=0.715\,\Gamma_\infty\), so \(G=\Gamma_\infty/\nu=8.784\,r\,U\) and \(U=G/(8.784\,r)\): a small tube is fast, \(\omega_0\) falls roughly as \(1/r^2\). Two versions bracket the spread of \(G\): (a) \(G\) constant, 80 or 94; (b) \(r\) and \(G\) independent, with \(\mathrm{var}\ln G=\mathrm{var}\ln U-\mathrm{var}\ln r=0.49-0.40=0.09\) (the swirl pdf as the lognormal of median 2.0 and ln-width 0.70, the radius pdf as its two lognormals), which gives \(\ln r\) and \(\ln U\) a correlation of \(-0.9\).</li>
<li><strong>The 1% of the volume.</strong> A tube of length \(L\) has the volume \(\pi\rho_c^2L=2\pi R^2L\ln(\omega_0/\omega_c)\) inside the surface where its vorticity falls to \(\omega_c\) (\(\rho_c=R\sqrt{2\ln(\omega_0/\omega_c)}\)), and the volume \(\pi r_{\max}^2L\) out to \(r_{\max}\). The cut \(\omega_c\) is fixed so that the volume above it is 1% of the flow when all the tubes fill 35% of it (Kida et al.: 0.31 to 0.35): the sum of the first volumes over the sum of the second is 0.01/0.35.</li>
<li><strong>The tubes that are kept.</strong> At 35% about 45% of the tubes are kept, those of small radius (version a: \(r<4.9\,\eta\)), of mean radius 3.6 to 3.7 \(\eta\) and mean swirl 2.7 to 3.8 \(u_K\) (Table D3), with a mean axis vorticity of 3.2 to 4.3 against the 3.9 to 4.8 of Ghira et al. (Table III). 71% to 77% of them belong to the narrow family of the radius pdf, which they represent (23% to 43% of the broad family is kept as well).</li>
<li><strong>The multipliers</strong> are the value of the reference over the value of the kept tubes. Radius: the mean of the narrow family, 4.55 \(\eta\), over the mean radius of the kept tubes, \(f_R=4.55/3.56=1.28\) (a) and \(4.55/3.72=1.22\) (b). Swirl: the mean of all the tubes over that of the kept tubes, \(f_U=0.68\) (a) and 0.66 (b).</li>
<li><strong>Used: radius multiplied by 1.25 and swirl by 0.67</strong>, for Ghira et al. (2022, 2025). At other fillings the factors are 1.12 to 1.16 and 0.71 to 0.73 (20%) and 1.0 and 0.8 (10%).</li>
</ol>
<p class="note">Table D3. The cut of Ghira et al. on the all-tube population of Pirozzoli (2012): the cut \(\omega_c/\omega_{rms}\), the radius \(r_c\) above which a tube is not kept, the fraction of the tubes kept, their mean radius (\(\eta\)) and swirl (\(u_K\)), and the factors: \(f_R\), the mean radius of the narrow family (4.55 \(\eta\)) over that of the kept tubes, and \(f_U\), the mean swirl of all the tubes over that of the kept tubes.</p>
""" + table(["tubes fill", "pairing", r"\(\omega_c/\omega_{rms}\)", r"\(r_c\)", "kept", r"mean \(r\) kept", r"mean \(U\) kept", r"\(f_R\)", r"\(f_U\)"], body) + r"""
<p>What fixes the result. (1) <em>The radius target.</em> The vorticity cut cannot see the large tubes of the broad family, and the narrow family is the tube of the model, so the radius is brought to the narrow family; brought to the mean of all the tubes (7.2 \(\eta\), and 6 in his text) the factor would be 1.7 to 2.0, and the fits are then much worse (below). (2) <em>The filling \(\varphi\).</em> It is an input; its range in the literature is the one quoted. (3) <em>The pairing.</em> Independent \(r\) and \(U\) would give a most frequent \(G\) of 44, not his 80, so a negative correlation of \(\ln r\) and \(\ln U\) (\(-0.9\) in version b) is needed.</p>
<p>Limits. The pdfs are those of one population at one \(Re_\lambda\) (251, the open circles of his Fig. 2; the caption says case D, 98.6), the runs of Ghira et al. cover 90 to 399, and their structures are larger than the kept tubes of the model (\(r_{\max}\) of 4.5 to 5.0 \(\eta\) against 3.6 to 3.7), so the corrected radius, 5.6 to 6.2 \(\eta\), lies above the narrow family. The consequence in the fits (section 10): with the radius of Ghira et al. multiplied by 1.25 and the swirl by 0.67 the standard error of the fit of the best models is """ + rng(now, "rms") + r""" and the leave-one-source-out error """ + rng(now, "loso") + r"""; with the radius as listed they are """ + rng(old, "rms") + r""" and """ + rng(old, "loso") + r""", and with the radius multiplied by 1.85 (the mean of all the tubes as the target) """ + rng(big, "rms") + r""" and """ + rng(big, "loso") + r""".</p>
"""
    return text


def table(head, rows):
    return ('<div class="tablebox"><table class="dt">\n<thead><tr>' + "".join("<th>%s</th>" % h for h in head) + "</tr></thead>\n<tbody>\n"
            + "\n".join("<tr>" + "".join("<td>%s</td>" % c for c in r) + "</tr>" for r in rows) + "\n</tbody></table></div>")


def selection_text(models):
    """The paragraph after Table 1, written from the scores of the main scenario (no model named in advance)."""
    order = sorted(models, key=lambda m: m["loso"])
    b = order[0]
    plural = lambda m: "%d parameter%s" % (m["k"], "" if m["k"] == 1 else "s")
    near = [m for m in order[1:] if m["loso"] - b["loso"] <= 1.5]
    text = "<p>The model %s (%s; %s) predicts left-out sources best, %.1f%%" % (b["key"], b["name"], plural(b), b["loso"])
    if near:
        text += "; " + ", ".join("%s (%s) follows at %.1f%%" % (m["key"], plural(m), m["loso"]) for m in near)
    text += ". "
    close = [m for m in order if m["key"] != b["key"] and m["d_aicc"] - b["d_aicc"] < 2.0]
    if close:
        text += "The information criteria do not separate %s from it (&Delta;AICc = %s). " % (", ".join(m["key"] for m in close), ", ".join("%.1f" % (m["d_aicc"] - b["d_aicc"]) for m in close))
    big = [m for m in order if m["k"] >= 3]
    if big and big[0]["loso"] > b["loso"]:
        text += "No model with three or four parameters predicts better than %s: the best of them, %s, scores %.1f%%, so a fitted radius, a radius that varies with \\(Re_\\lambda\\) or a free exponent add nothing that survives leaving a source out. " % (b["key"], big[0]["key"], big[0]["loso"])
    elif big:
        text += "A model with more parameters, %s (%s), predicts better (%.1f%%). " % (big[0]["key"], plural(big[0]), big[0]["loso"])
    text += "With complexity penalised, the model with the fewest parameters among the best is selected."
    l1 = {m["key"]: m for m in models}.get("L1")
    if l1 and l1["params"][0] < 0:
        text += " The logarithmic law, \\(U_{\\max}/U_\\eta=%.2f+%.2f\\ln Re_\\lambda\\), is equivalent within the range of the data (L1, %.1f%%) but turns negative below \\(Re_\\lambda\\approx%.0f\\)." % (l1["params"][0], l1["params"][1], l1["loso"], math.exp(-l1["params"][0] / l1["params"][1]))
    return text + "</p>"


def sens_text(scen):
    """The paragraph after Table 2: the sensitivity of the selection to the threshold of the all-tube average of Mouri and Hori, to the factors of Ghira et al. and to the two rows of Sassa and Makita."""
    best = lambda s: sorted(s["models"], key=lambda m: m["loso"])[0]
    d4 = lambda s: {m["key"]: m for m in s["models"]}["D4"]["loso"]
    find = lambda start: [s for s in scen if s["label"].startswith(start)][0]
    ks = [(k, find("with Mouri-Hori at k = " + k)) for k in ("0.25", "0.5", "1")] + [("0.33", find("Fig. 1b data with Mouri-Hori"))]
    ks.sort(key=lambda t: float(t[0]))
    parts = ["%s at k = %s (%.1f%%)" % (best(s)["key"], k, best(s)["loso"]) for k, s in ks]
    listed, rad, big, sas = find("without Mouri-Hori, Ghira as listed"), find("without Mouri-Hori, Ghira radius as listed"), find("without Mouri-Hori, Ghira radius x 1.85"), find("without Mouri-Hori, the two rows")
    return ("<p>With the all-tube average of Mouri and Hori included, the best model is, by the threshold of its average, " + ", ".join(parts) + "; D4 scores %.1f%% at k = 0.33 against %.1f%% without it. " % (d4(ks[1][1]), d4(scen[0])) +
            "The selection is therefore the same for the thresholds in the range in which the model reproduces their values, and it is the average of Mouri and Hori itself, not the threshold, that raises the error: its rows are the least certain of the corrected data. "
            "With the factors of Ghira et al. as listed (radius &times; 1, swirl &times; 1) the best is %s (%.1f%%) and D4 %.1f%%; with the radius as listed and the swirl &times; 0.67 %s (%.1f%%) and D4 %.1f%%; with the whole-pdf mean as the target (&times; 1.85, &times; 0.6) %s (%.1f%%), D4 %.1f%%. "
            "Keeping the two rows of Sassa and Makita at \\(Re_\\lambda=820\\) and 2391 gives %s (%.1f%%) and D4 %.1f%%.</p>" % (best(listed)["key"], best(listed)["loso"], d4(listed), best(rad)["key"], best(rad)["loso"], d4(rad), best(big)["key"], best(big)["loso"], d4(big),
                                                                                                                                      best(sas)["key"], best(sas)["loso"], d4(sas)))


def fit_numbers():
    """The fits of Fig. 1b (data_corrected_fits.json) as numbers for the text: with and without Mouri and Hori (2009)."""
    with open(os.path.join(HERE, "data_corrected_fits.json"), encoding="utf-8") as f:
        fits = json.load(f)
    out = {}
    for tag, f_ in (("w", fits), ("o", fits["without_Mouri09"])):
        r, u = f_["r"], f_["U"]
        rm, um = r["models"], u["models"]
        out[tag] = dict(nr=r["n"], nu=u["n"], sr=r["n_sources"], su=u["n_sources"],
                        r_line=rm["straight line"], r_const=rm["constant"], r_pow=rm["power"],
                        u_half=um["power, exponent 1/2"], u_third=um["power, exponent 1/3"], u_free=um["power"], u_line=um["straight line"],
                        br=r["stats"]["b"], bu=u["stats"]["b"], wr=r["stats"]["weight_ratio"], wu=u["stats"]["weight_ratio"], rs=r["stats"], us=u["stats"],
                        r_best=r["best_by_s"], u_best=u["best_by_s"])
    return out


def corrected_fig_section():
    """The new figure of the radius, the swirl and the circulation against Re_lambda (data as read, and as corrected by the models of the probes) with the trends fitted to its dots (the fitting measure is in the last appendix); the text is written from data_corrected_fits.json."""
    n = fit_numbers()
    w, o = n["w"], n["o"]
    S = lambda m: "%.3f" % (m["rss"] ** 0.5)
    r_at = lambda m, re: m["a"] + m["b"] * re
    assert o["r_best"] == "straight line" and w["r_best"] == "straight line", "the text assumes that a straight line describes the radius best"
    assert o["u_best"] in ("power", "power, exponent 1/2") and w["u_best"] in ("power", "power, exponent 1/2"), "the text assumes that a power law describes the swirl best"
    with open(os.path.join(HERE, "belin_correctors_all.json"), encoding="utf-8") as f:
        allk = [q for q in json.load(f) if round(q["Re_lambda"]) == 2000][0]
    spread = 100 * (allk["k=0.25"]["m_U"] / allk["k=0.5"]["m_U"] - 1)
    text = r"""<h3>The data as read and as corrected by the models of the probes</h3>
<p>Fig. 1b shows every row of the data against \(Re_\lambda\) on linear axes: above as read from the papers, below with the corrections that follow from the models: Ghira et al. (radius &times; 1.25, swirl &times; 0.67, section 9a) and the observed rows (Belin et al., Mouri et al. 2004, 2007, Mouri and Hori 2009, Sassa and Makita) with the multipliers of the wire-and-tube model and its one-dimensional extension (below; the multipliers are interpolated in \(\ln Re_\lambda\) from the table of each paper in the recording book), the other simulations as read. The all-tube average of Mouri and Hori does not state its amplitude threshold; its multiplier is that of the threshold \(k=0.33\) standard deviations of the increment, a choice inside the range 0.25 to 0.5 in which the model reproduces their values (over that range the swirl multiplier at \(Re_\lambda=2000\) changes by §SPREAD§%). Rows with a range of \(Re_\lambda\) (the curves of Belin et al., the range of Mouri et al. 2003) are drawn as lines and are not used in the fits. Colour: blue for experiments, orange for simulations; each source has its own marker.</p>
""" + png_html("data_corrected_plot.png", r"Fig. 1b. \(r_{\max}/\eta\), \(U_{\max}/U_\eta\) and \(G=\Gamma/\nu=8.784\,r_{\max}U_{\max}\) against \(Re_\lambda\), linear axes. Top: every row as read. Bottom: Ghira et al. and the observed rows corrected, the other simulations as read (open symbols: observed, no multiplier yet). Blue: experiments; orange: simulations. Dashed lines: the fits of this section, red without and grey with the all-tube average of Mouri and Hori (2009), whose dots are grey, as are the two rows of Sassa and Makita that no fit uses.") + r"""
<p>The radius and the swirl were fitted to the dots of the bottom row (§NR§ points of §SR§ sources for the radius and §NU§ of §SU§ for the swirl; §NRW§ and §NUW§ with the rows of Mouri and Hori 2009), with the weighted sum of squares of the last appendix, in which every point has the same weight and the small and the large values are balanced; the standard error \(s\) of that appendix is quoted. Two kinds of dot are left out: the all-tube average of Mouri and Hori (2009) in the red fit, because it carries the largest multiplier and its threshold is not known (the grey fit includes it), and, in both fits, the two rows of Sassa and Makita at \(Re_\lambda=820\) (a shear flow) and 2391, grey in the figure. <em>Radius:</em> a straight line describes the radius better than a constant or a power law, \(r_{\max}/\eta=§RA§-§RB§\,Re_\lambda\) without the all-tube average of Mouri and Hori (§SRL§; a constant, §RC§, has §SRC§) and \(§RAW§-§RBW§\,Re_\lambda\) with it (§SRLW§); the line falls from §R100§ at \(Re_\lambda=100\) to §R2000§ at 2000, a very small reduction over a wide range of Reynolds number, in simulations and experiments together. <em>Swirl:</em> \(U_{\max}/U_\eta=§UA§\,Re_\lambda^{1/2}\) without and \(§UAW§\,Re_\lambda^{1/2}\) with the all-tube average (§SUH§ and §SUHW§); the free exponent is §UB§ and §UBW§ (§SUF§ and §SUFW§), so 1/2 is as good as the free exponent. Because \(u'/U_\eta=Re_\lambda^{1/2}/15^{1/4}\), an exponent of 1/2 means that \(U_{\max}/u'=15^{1/4}\cdot§UA§=§UP§\) (§UPW§ with the all-tube average) does not depend on the Reynolds number: this is the scaling \(U_{\max}\propto u'\) that Mouri et al. (2007) found for the intense tubes of their experiments (reported by Mouri and Hori 2009, section 6), and Fig. 1b shows that it holds for simulations and experiments together over the range of the data. The circulation of the lines of the third panel is \(8.784\,r_{\max}U_{\max}\) of the two fits.</p>
"""
    rep = {"§SPREAD§": "%.0f" % spread, "§NR§": "%d" % o["nr"], "§SR§": "%d" % o["sr"], "§NU§": "%d" % o["nu"], "§SU§": "%d" % o["su"], "§NRW§": "%d" % w["nr"], "§NUW§": "%d" % w["nu"],
           "§RA§": "%.2f" % o["r_line"]["a"], "§RB§": "%.4f" % -o["r_line"]["b"], "§SRL§": "s = %s" % S(o["r_line"]), "§RC§": "%.2f" % o["r_const"]["a"], "§SRC§": "s = %s" % S(o["r_const"]),
           "§RAW§": "%.2f" % w["r_line"]["a"], "§RBW§": "%.4f" % -w["r_line"]["b"], "§SRLW§": "s = %s" % S(w["r_line"]),
           "§R100§": "%.2f" % r_at(o["r_line"], 100), "§R2000§": "%.2f" % r_at(o["r_line"], 2000),
           "§UA§": "%.3f" % o["u_half"]["a"], "§UAW§": "%.3f" % w["u_half"]["a"], "§SUH§": "s = %s" % S(o["u_half"]), "§SUHW§": "%s" % S(w["u_half"]),
           "§UB§": "%.2f" % o["u_free"]["b"], "§UBW§": "%.2f" % w["u_free"]["b"], "§SUF§": "s = %s" % S(o["u_free"]), "§SUFW§": "%s" % S(w["u_free"]),
           "§SUT§": "s = %s" % S(o["u_third"]), "§SUTW§": "%s" % S(w["u_third"]),
           "§UP§": "%.2f" % (15 ** 0.25 * o["u_half"]["a"]), "§UPW§": "%.2f" % (15 ** 0.25 * w["u_half"]["a"])}
    for k, v in rep.items():
        text = text.replace(k, v)
    return text


def sos_appendix():
    """The last appendix: the weighted sum of squares of the fits of Fig. 1b, where it comes from and how its factor b follows."""
    n = fit_numbers()
    o, w = n["o"], n["w"]
    us = o["us"]
    w_one = (1 / us["min"] ** 2 + 1 / us["mean"] ** 2) / (1 / us["max"] ** 2 + 1 / us["mean"] ** 2)             # the weight ratio of the swirl for b = 1
    text = r"""<h2>Appendix: the fitting measure of Fig. 1b (a weighted sum of squares)</h2>
<p class="note">Written so that the fits of section 9 can be repeated: the formula, where it comes from, how its one factor is derived, and the values it takes for the data of Fig. 1b.</p>
<h3>B1. Definition</h3>
<p>A model \(c_i=f(Re_{\lambda,i};\theta)\) with \(p\) fitted parameters \(\theta\) is fitted to \(N\) values \(e_i\) (the experimental or simulated values of \(r_{\max}/\eta\) or of \(U_{\max}/U_\eta\), after the corrections). The fit minimises the corrected sum of relative error
$$S=b\sum_{i=1}^{N}\left(1-\frac{c_i}{e_i}\right)^2+\sum_{i=1}^{N}\frac{(c_i-e_i)^2}{\bar e^{\,2}},\qquad \bar e=\frac1N\sum_i e_i,$$
and its quality is reported as the standard error of the fit, dimensionless,
$$s=\sqrt{\frac{S}{N-p}} .$$
The first sum is the relative error of each point and the second the absolute error, in units of the mean of the data, of each point; \(b\) is a factor derived in B3. Every point has the same weight, whatever its source; there is no weight per source.</p>
<h3>B2. Where it comes from</h3>
<p>Two measures are in common use. The sum of the squared relative errors, \(\sum(1-c/e)^2=\sum(c-e)^2/e^2\), divides each misfit by \(e^2\): a misfit of 10% counts the same at \(e=2\) and at \(e=16\), but in the fit the points of small \(e\) have a large weight and those of large \(e\) hardly count. The sum of the squared absolute errors, \(\sum(c-e)^2\), does the reverse: the absolute scatter of the data grows with their size, so the large values dominate the misfit and the small values are ignored. The data of Fig. 1b span a factor of ten in the swirl (§UMIN§ to §UMAX§) and scatter widely from source to source, so neither measure alone is acceptable.</p>
<p>The author has used this weighted sum of squares in earlier work to balance the contribution of the small and of the large values without one of them dominating. That matters in particular when data with a significant spread are fitted, as is the case here. It is not a published standard measure; in effect it resembles the combined error model, in which the variance of a point has a constant part and a part proportional to its value, but its factor \(b\) is fixed from the data by the condition below and not fitted.</p>
<h3>B3. The factor b</h3>
<p>Since \((1-c/e)^2=(c-e)^2/e^2\), the sum is a weighted least squares,
$$S=\sum_i (c_i-e_i)^2\,w(e_i),\qquad w(e)=\frac{b}{e^2}+\frac{1}{\bar e^{\,2}} .$$
The second part of the weight is the same for every point. The first part, \(b/e^2\), is the relative error: at the mean, \(1/\bar e^{\,2}\), it equals the weight of the absolute error (for \(b=1\)), above it for the values below the mean and below it for the values above. For a given \(b\) the relative part is balanced between the two ends of the data when its deficit at the largest value equals \(b\) times its excess at the smallest, the points being spread evenly through the decades so that the two extremes stand for the whole range:
$$-\left(\frac{1}{e_{\max}^2}-\frac{1}{\bar e^{\,2}}\right)=b\left(\frac{1}{e_{\min}^2}-\frac{1}{\bar e^{\,2}}\right).$$
Solving for \(b\) and multiplying numerator and denominator by \(\bar e^{\,2}\),
$$b=\frac{\dfrac{1}{\bar e^{\,2}}-\dfrac{1}{e_{\max}^2}}{\dfrac{1}{e_{\min}^2}-\dfrac{1}{\bar e^{\,2}}}=\frac{1-\bar e^{\,2}/e_{\max}^2}{\bar e^{\,2}/e_{\min}^2-1},$$
which is positive, since \(e_{\min}\lt\bar e\lt e_{\max}\), and is computed for each fit from the values that enter it. For \(b\to0\) the measure is the absolute error and the weights of all points are equal; for \(b=1\) it is the plain sum of the relative and the absolute error. The ratio of the weight of the smallest value to that of the largest is
$$\frac{w(e_{\min})}{w(e_{\max})}=\frac{b/e_{\min}^2+1/\bar e^{\,2}}{b/e_{\max}^2+1/\bar e^{\,2}} .$$</p>
<h3>B4. Values for Fig. 1b</h3>
<p>For the radius (§NR§ values from §RMIN§ to §RMAX§, mean §RMEAN§) \(b=§BR§\) and the weight ratio is §WR§ to 1; for the swirl (§NU§ values from §UMIN§ to §UMAX§, mean §UMEAN§) \(b=§BU§\) and the ratio is §WU§ to 1 (all values without the all-tube average of Mouri and Hori; with it \(b=§BRW§\) for the radius and \(§BUW§\) for the swirl). With \(b=1\) the swirl would have a ratio of §WONE§ to 1 and be fitted mostly at its small values. The models fitted are, for the radius, a constant, a power law and a straight line, and for the swirl a power law with a free exponent, the exponents 1/3 and 1/2, and a straight line; \(p\) is 1 for a constant and a fixed exponent and 2 otherwise, and the model of the lowest \(s\) is taken. Without the all-tube average of Mouri and Hori the lowest \(s\) is §SRL§ for the radius (a straight line) and §SUF§ for the swirl (the free power law, whose exponent is §UB§; the exponent 1/2 has §SUH§).</p>
"""
    rep = {"§UMIN§": "%.1f" % o["us"]["min"], "§UMAX§": "%.1f" % o["us"]["max"], "§UMEAN§": "%.1f" % o["us"]["mean"], "§RMIN§": "%.1f" % o["rs"]["min"], "§RMAX§": "%.1f" % o["rs"]["max"], "§RMEAN§": "%.1f" % o["rs"]["mean"],
           "§NR§": "%d" % o["nr"], "§NU§": "%d" % o["nu"], "§BR§": "%.2f" % o["br"], "§BU§": "%.3f" % o["bu"], "§BRW§": "%.2f" % w["br"], "§BUW§": "%.3f" % w["bu"],
           "§WR§": "%.1f" % o["wr"], "§WU§": "%.1f" % o["wu"], "§WONE§": "%.0f" % w_one, "§SRL§": "%.3f" % (o["r_line"]["rss"] ** 0.5), "§SUF§": "%.3f" % (o["u_free"]["rss"] ** 0.5), "§SUH§": "%.3f" % (o["u_half"]["rss"] ** 0.5), "§UB§": "%.2f" % o["u_free"]["b"]}
    for k, v in rep.items():
        text = text.replace(k, v)
    return text


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

    rows = modelselect.dots(**modelselect.SCENARIOS[0][1])                           # the data of Fig. 1b without the all-tube average of Mouri and Hori
    obs = fitdata.observations(rows)
    models = {m.key: m for m in fitmodels.models(obs)}
    res6 = modelselect.fit(models["D4"], obs)                                        # the selected model: radius 5, swirl proportional to u'
    kappa = float(res6["params"][0])                                                 # U_max = kappa u', u'/U_eta = (Re/sqrt 15)^(1/2)
    c6 = kappa / 15 ** 0.25                                                          # U_max/U_eta = c6 Re^(1/2)
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
        d = next(m for m in ms if m["key"] == "D4")
        sens_rows.append([sc["label"], "%s (%.1f%%)" % (ms[0]["key"], ms[0]["loso"]), "%.1f%%" % d["loso"], "%.3f" % d["params"][0]])
    pred_rows = []
    for Re in (50, 100, 300, 1000, 2000):
        U1 = c6 * Re ** 0.5
        U2 = tp["all_free"]["a"] * Re ** tp["all_free"]["s"]
        Ui = tp["intense"]["c"] * Re ** tp["intense"]["s"]
        v1, d1 = bud(U1)
        v2, d2 = bud(U2)
        pred_rows.append(["%d" % Re, "%.2f" % U1, "%.0f" % (fitdata.G0 * 5 * U1), "%.3f" % v1, "%.1f" % d1, "%.2f" % U2, "%.0f" % (fitdata.G0 * 5 * U2), "%.3f" % v2, "%.1f" % d2, "%.2f" % Ui,
                          "%.3f" % (4.91 * 0.01 * (Ui / 5) ** 2)])
    n_src = len({x["src"] for x in rows})
    keys = {
        "@C6@": "%.3f" % c6, "@RMS6@": "%.1f" % main0["D4"]["rms"], "@LOSO6@": "%.1f" % main0["D4"]["loso"], "@LOSOL1@": "%.1f" % main0["L1"]["loso"], "@DAIC6@": "%.1f" % main0["D4"]["d_aicc"], "@KAPPA@": "%.2f" % kappa,
        "@DNSRATIO@": "%.2f" % (c6 * 332 ** 0.5 / (0.769 * 332 ** (1 / 3))), "@DNSRATIO2@": "%.2f" % (c6 * 1934 ** 0.5 / (0.769 * 1934 ** (1 / 3))),
        "@L1A@": "%.2f" % main0["L1"]["params"][0], "@L1B@": "%.2f" % main0["L1"]["params"][1], "@NR@": str(len(obs["r"]["re"])), "@NU@": str(len(obs["U"]["re"])), "@NG@": str(main0["D4"]["groups"]),
        "@IC@": "%.2f" % tp["intense"]["c"], "@IS@": "%.2f" % tp["intense"]["s"], "@IRMS@": "%.0f" % tp["intense"]["rms_power"], "@IN@": str(tp["intense"]["n"]),
        "@AA@": "%.2f" % tp["all_free"]["a"], "@AS@": "%.2f" % tp["all_free"]["s"], "@AF@": "%.2f" % tp["all_free"]["f"], "@ARMS@": "%.1f" % tp["all_free"]["rms"],
        "@A3S@": "%.2f" % tp["all_f3.0"]["s"], "@A3RMS@": "%.1f" % tp["all_f3.0"]["rms"], "@SM@": "%.2f" % tp["slope_Mouri09"], "@SK@": "%.2f" % tp["slope_Kida02"],
        "@SHARE@": "%.2f" % share5, "@NSRC@": str(n_src),
        "@VK83A@": "%.2f" % bud(c6 * 83 ** 0.5)[0], "@VK170A@": "%.2f" % bud(c6 * 170 ** 0.5)[0],
        "@VK83B@": "%.2f" % bud(tp["all_free"]["a"] * 83 ** tp["all_free"]["s"])[0], "@VK170B@": "%.2f" % bud(tp["all_free"]["a"] * 170 ** tp["all_free"]["s"])[0],
        "@SELTABLE@": table(["model", "parameters", "s %", "LOSO %", "&Delta;AICc", "&Delta;BIC", "form"], sel_rows),
        "@SENSTABLE@": table(["data", "best model by LOSO", "LOSO of the selected model D4", "its \\(\\kappa=U_{\\max}/u'\\)"], sens_rows),
        "@PREDTABLE@": table([r"\(Re_\lambda\)", r"\(U_{\max}/U_\eta\) (I)", r"\(\Gamma/\nu\) (I)", r"\(V_f\) (I)", r"\(d/\eta\) (I)", r"\(U_{\max}/U_\eta\) (II, all)", r"\(\Gamma/\nu\) (II)", r"\(V_f\) (II)", r"\(d/\eta\) (II)",
                              r"\(U_{\max}/U_\eta\) (II, intense)", "dissipation share of the intense tubes (1% of the volume)"], pred_rows),
        "@DATAFIG@": pagefigures.data_figure(rows), "@MODELFIG@": pagefigures.model_figure(res6, rows), "@TWOFIG@": two_population_figure(rows_raw, tp, c6),
        "@DATATABLE@": bds.model_input_table(),
        "@CORRFIG@": corrected_fig_section(),
        "@SELTEXT@": selection_text(scen[0]["models"]),
        "@SENSTEXT@": sens_text(scen),
        "@RFIT@": "%.1f" % main0["D2"]["params"][0], "@RRMS6@": "%.1f" % main0["D4"]["rms_r"],
        "@R1000@": "%.2f" % ((c6 * 1000 ** 0.5) / (tp["all_free"]["a"] * 1000 ** tp["all_free"]["s"])),
        "@P251@": "%.1f" % (tp["all_free"]["a"] * 251 ** tp["all_free"]["s"]),
        "@DNSPDF@": dns_pdf_section(),
        "@RL100@": "%.1f" % (fit_numbers()["o"]["r_line"]["a"] + 100 * fit_numbers()["o"]["r_line"]["b"]), "@RL2000@": "%.1f" % (fit_numbers()["o"]["r_line"]["a"] + 2000 * fit_numbers()["o"]["r_line"]["b"]),
        "@WIRETUBE@": wire_tube_section(),
        "@ONEDIM@": onedim_section(),
    }
    body = TEXT_FRONT + theory + TEXT_BACK
    for _ in range(2):                                                    # a second pass: some blocks (the text of the new figure) carry tokens of their own
        for k, v in keys.items():
            body = body.replace(k, v)
    left = re.findall(r"@[A-Z0-9]+@", body)
    if left:
        raise ValueError("place holders not filled: %s" % sorted(set(left)))
    appendix = bds.build_appendix().replace("<h2>Appendix: the source data, how it was converted, and what the model uses</h2>",
                                            "<h2>Appendix: the source data, how it was converted, and what the model uses</h2>\n<p class=\"note\">The appendix lists every source with its conversions, made from the same data file as the fits. Its paragraphs on the corrections (A0c) give the rationale as it was decided; the review of that rationale is in sections 9 and 12, and the page-by-page evidence is in the recording book (<code>LIT/record</code>).</p>", 1)
    best_of = lambda s: sorted(s["models"], key=lambda m: m["loso"])[0]
    listed = [s for s in scen if s["label"].startswith("without Mouri-Hori, Ghira as listed")][0]
    appendix = appendix.replace("@LRMS@", "%.1f" % best_of(listed)["loso"]).replace("@NRMS@", "%.1f" % best_of(scen[0])["loso"])
    typeset = "<script>if (document.typeset) { document.typeset(); }</script>\n"      # in the report server the doc block loads MathJax on request; a plain browser uses the script of the head
    return head + "\n" + body + "\n" + refs + appendix + sos_appendix() + "</main>\n" + typeset


TEXT_FRONT = r"""
<h1>A Burgers-vortex closure for the dissipative scales of turbulence: evidence, model selection and use in CFD</h1>
<p class="lede">Working paper (Burgers Vortex Energy Balance). Symbols: \(\gamma\) axial stretching rate, \(\Gamma\) circulation, \(\nu\) kinematic viscosity, \(\varepsilon\) dissipation rate per unit mass, \(\eta\), \(U_\eta\), \(\gamma_\eta\) the Kolmogorov length, velocity and rate, \(Re_\lambda\) the Taylor-scale Reynolds number, \(r_{\max}=\beta\eta\) the radius of maximum swirl of a tube and \(U_{\max}\) that swirl.</p>

<h2>Abstract</h2>
<p>The smallest scales of turbulence, where micromixing and viscous dissipation take place, are organised in stretched vortex tubes. We model a tube as a Burgers vortex, close its energy budget with the Kolmogorov scales, and determine its two free quantities, the radius of maximum swirl and the swirl velocity, from @NSRC@ published sources (simulations and experiments) covering \(35\le Re_\lambda\le1934\). Every number is traced from the page of its paper to the fit in an open recording book, and each correction is listed with its rationale. The radius is \(r_{\max}\approx5\,\eta\) in all flows (@RFIT@ \(\eta\) fitted); simulations and experiments together show only a very small reduction with the Reynolds number, from @RL100@ \(\eta\) at \(Re_\lambda=100\) to @RL2000@ \(\eta\) at 2000. With the corrections computed for the probe measurements from the models of their signals, a single one-parameter law, \(U_{\max}/U_\eta=@C6@\,Re_\lambda^{1/2}\), that is \(U_{\max}=@KAPPA@\,u'\), describes simulations and experiments together and predicts sources left out of the fit to within @LOSO6@%; no model with more parameters predicts them better. Read as calculated from the papers, the data separate into two populations: the 1% most intense tubes, \(U_{\max}/U_\eta=@IC@\,Re_\lambda^{@IS@}\), and all tubes, \(U_{\max}/U_\eta=@AA@\,Re_\lambda^{@AS@}\). The second reading needs one fitted probe factor and reproduces the measured volume fraction of the tubes. We give the closure in a form usable in computational fluid dynamics, with the tube strain rate, circulation, volume fraction and spacing as functions of the local \(k\) and \(\varepsilon\), and add a first-order lag for the time the energy cascade takes to reach the tubes, \(T_c/\tau_\eta=C_c\,(Re_\lambda/\sqrt{15}-\beta^{2/3})\).</p>
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
@CORRFIG@

<h3>Corrections</h3>
<p>Four corrections were adopted before the fits (the radius and the swirl of Mouri and Hori, the radius of Belin et al., the radius and the swirl of Ghira et al.); their rationale is given in full in the recording book (tab Corrections) and in appendix A0c. These four constant corrections are those of the first selection; the selection of section 10 and Fig. 1b use instead the multipliers computed from the models of the probes, which depend on \(Re_\lambda\) and which these constants approximate (for Mouri and Hori, the radius factor 1/1.75 = 0.57 and the swirl factor 3 against the model multipliers 0.46 to 0.58 and 2.7 to 3.8 for k = 0.33 between \(Re_\lambda=100\) and 2000).</p>
<p><strong>The radius of the all-event hot-wire average (Mouri and Hori 2009), divided by 1.75.</strong> A probe crosses a tube along a chord at a random offset and tilt, so the mean profile of all events is wider than the tube; the authors say so and give no factor. A model of the crossing statistics (the chord model of appendix A0c, without the incidence angle; the wire-and-tube model below, applied to the method of Mouri and Hori with tubes of the DNS, gives a radius factor of 1.5&ndash;1.9 and a swirl factor of 2.4&ndash;3.8 at the thresholds that reproduce their averages, which supports the two factors) gives a ratio of 1.7 to 1.85. The corrected radii (4.7 to 5.3 \(\eta\)) agree with the simulations.</p>
<p><strong>The swirl of the same source, multiplied by 3,</strong> for the same reason: the chord model gives 2 to 3.5. <strong>The swirl of Ghira et al. (2022, 2025), multiplied by 0.67,</strong> to bring the swirl of the 1% most intense tubes to the whole population (section 9a; the factor 0.6 used before agrees with the level of the other sources at the same \(Re_\lambda\)). The threshold averages of Mouri et al. (2004, 2007) are left out, as tails of the distribution that the all-event average of Mouri and Hori contains whole.</p>
<p><strong>The radius of Belin et al. (1996), divided by 1.15.</strong> The row is the median of their Fig. 5 (7.6 \(\eta\) as \(r_{\max}\)), not its peak, and the factor is the ratio of the radius read to the true radius of the intense tubes in the wire-and-tube model below (1.06 at \(Re_\lambda=151\) to 1.18 at 718); the corrected radius is 6.6 \(\eta\) (provisional: it rests on the tubes found from their own records, which the one-dimensional methods of Mouri et al. and of Sassa and Makita do not support, section 9). Their swirl, \(\Delta S/(2\sin\alpha)\) with \(\sin\alpha=0.14\), is too high by a factor of about 2.6 in the model, and the model value is itself about three times the DNS law; it is not a row of the table.</p>
<p><strong>The radius of Ghira et al. (2022, 2025), multiplied by 1.25.</strong> The strongest 1% of the volume by vorticity is a subset of the tubes, smaller and faster than the whole population. The factors are worked out in section 9a, in steps, from the all-tube population of Pirozzoli (2012), chosen as the reference because it has no lower threshold on the vorticity: his pdfs of the radius and of the maximum velocity are linked by his most frequent circulation (\(\Gamma/\nu=80\)), the cut of Ghira et al. is applied with the tubes filling 35% of the flow, and the multipliers are the value of the reference (the narrow family of the radius pdf, all tubes for the swirl) over that of the kept tubes: 1.22 to 1.28 for the radius and 0.66 to 0.68 for the swirl. The corrected radius is 5.6 to 6.2 \(\eta\) and the swirl is multiplied by 0.67 in place of 0.6.</p>
<p><strong>Review of the corrections.</strong> The two swirl factors are the weakest numbers of the data set, for three reasons found in the review. First, Da Silva et al. (2011), whose swirl (3.7 and 4.3 \(U_\eta\), from their \(u_0/u'\)) was a support of the factor 0.6 of the swirl of Ghira et al. (now 0.67, section 9a), print \(\langle u_0\rangle/u_\eta=9.0\) and 7.15 in the same table, and their circulation implies 10.5; the paper does not resolve the factor 2.5, and its swirl is therefore not fitted. Secondly, without any factor the intense-tube sources agree with each other: Ghira et al. (simulation) and the 0.1% averages of Mouri et al. (2007, hot wire) lie on one line. Thirdly, the all-tube sources alone (Kida et al. and Mouri and Hori) are best joined with a swirl factor of @AF@, not 3. These points do not affect the radius. They are taken up in section 12.</p>
<p>The review also moved Tanahashi et al. (2001) from an assumed \(Re_\lambda=200\) to 80 (their Fig. 1b), and added the swirl of the \(Re_\lambda=54\) runs of Ghira et al. (2025) and the circulation of Jim&eacute;nez et al. (1993).</p>

<h3>The width of the distributions</h3>
<p>The values above are means or peaks of distributions. The probability densities of the diameter and the swirl of all tubes were digitised from Tanahashi et al. (2001, 2004), Das et al. (2006) and Pirozzoli (2012) (recording book). Each radius distribution is the sum of two lognormal functions. The first is narrow (width 0.29 to 0.35) and holds 53 to 71% of the tubes; its median is 5.2, 4.9 and 4.3 \(\eta\) and its mean 5.5, 5.3 and 4.6 \(\eta\) in Tanahashi et al. (2001), Tanahashi et al. (2004) and Pirozzoli (2012). This first lognormal is the tube of the model: \(r_{\max}/\eta\approx5\), the value found for the intense tubes and for the corrected probe data. The second lognormal is broad (width 0.6 to 0.7), with a median of 8.5 to 16.8 \(\eta\), two to three times the first; it raises the mean of the whole distribution to 7.2 to 8.2 \(\eta\) although the peak stays at 4.2 to 4.8. The open-symbol data of Das et al. (2006), from the centre of a channel at \(Re_\tau=180\), show almost only the broad function. What the second family is (larger tubes, or sheets and tubes in formation that the eduction also counts) is not settled; section 14 returns to it.</p>

@WIRETUBE@
@ONEDIM@
<h3>The data</h3>
@DATATABLE@

@DNSPDF@

<h2>10. Selection of the model</h2>
<p>Candidate models express \(r_{\max}/\eta\) and \(U_{\max}/U_\eta\) as functions of \(Re_\lambda\) with one to four parameters: a constant radius or one that varies as a power or a logarithm of \(Re_\lambda\), and a swirl that is a power law, a power law with a fixed exponent (1/2: proportional to the r.m.s. velocity; 1/3), a logarithmic law, or that follows from a law for the circulation. Each is fitted by minimising the weighted sum of squares of the last appendix over the radius (@NR@ points) and the swirl (@NU@ points) of Fig. 1b, every point having the same weight (@NG@ source-quantity groups).</p>
<p>An earlier version chose the model with the fewest parameters within 25% of the best root-mean-square (rms) residual; the width of that band has no basis. Here the choice is made by cross-validation: each source in turn is left out, the model is fitted to the others and predicts the one left out, and the standard error of those prediction errors, measured with the same sum of squares (LOSO, in per cent), is the score. A parameter that follows the noise of one source worsens the score, so complexity is penalised by the data. The Akaike criterion with small-sample correction (AICc) and the Bayesian criterion (BIC), with a source-quantity group as the unit of data, are given for comparison; differences below 2 carry no evidence (Burnham and Anderson 2002).</p>
@SELTABLE@
<p class="note">Table 1. The candidate models, sorted by the leave-one-source-out error, on the data of Fig. 1b without the all-tube average of Mouri and Hori (2009); s is the standard error of the fit of the last appendix, in per cent.</p>
@SELTEXT@
@SENSTABLE@
<p class="note">Table 2. The selection under other treatments of the data.</p>
@SENSTEXT@

<h2>11. The selected single-population model (model I)</h2>
$$r_{\max}=5\,\eta,\qquad \frac{U_{\max}}{U_\eta}=@C6@\,Re_\lambda^{1/2},\quad\text{that is}\quad U_{\max}=@KAPPA@\,u',\qquad \frac{u'}{U_\eta}=\left(\frac{Re_\lambda}{\sqrt{15}}\right)^{1/2}$$
<p>and, from sections 3 to 7 with \(\beta=5\),</p>
$$\frac{\gamma}{\gamma_\eta}=\frac{4x}{\beta^2}=0.201,\qquad \frac{\Gamma}{\nu}=8.78\,\beta\,\frac{U_{\max}}{U_\eta},\qquad V_f=\left(1-\frac{75.8}{\beta^4}\right)\frac{\beta^2}{4.91\,(U_{\max}/U_\eta)^2},\qquad \frac{d}{\eta}=\beta\sqrt{\frac{\pi}{V_f}} .$$
<p>The standard error of the fit (last appendix) is @RRMS6@% for the radius and @RMS6@% for radius and swirl together. The swirl dissipation of the tubes is @SHARE@ of the total at \(\beta=5\), the remainder being the dissipation of the background strain; the volume fraction \(V_f\) follows from this balance and is a prediction, not a fit.</p>
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
<p><strong>Checks with data not used in a fit.</strong> Kida et al. measured the volume fraction of their vortex cores: 0.35 at \(Re_\lambda=83\) and 0.31 at 170. The budget of section 7 gives @VK83B@ and @VK170B@ with the all-tube swirl of model II, and @VK83A@ and @VK170A@ with model I. Sassa and Makita (2005), who sample events at a moderate threshold between \(Re_\lambda=19\) and 2391, report an exponent 0.28 for the swirl, between the two families. The mean swirl of all tubes in the mixing layer of Tanahashi et al. (2001; \(Re_\lambda\approx80\)) is 3.7 \(U_\eta\) (model II: 3.6); that of Pirozzoli (2012; \(Re_\lambda\approx99\), the test case D named in the caption of his Fig. 2) is 2.5 (model II: 3.7); the plotted symbols are those of his case E (\(Re_\lambda=251\); model II: @P251@), so the disagreement remains whichever case it is.</p>
@PREDTABLE@
<p class="note">Table 3. Predictions of the two models at \(\beta=5\). The last column is \(4.91\,V_f\,(U_{\max}/\beta U_\eta)^2\) for \(V_f=0.01\).</p>
<p><strong>Which model.</strong> Model I is retained as the reference. With the corrections computed from the models of the probes (section 9) it describes simulations and experiments together with one parameter, the swirl proportional to the r.m.s. velocity, \(U_{\max}=@KAPPA@\,u'\), the scaling that Mouri et al. (2007) report for intense tubes; model II reads the values as calculated as two populations and rests on one fitted factor for the chord effect, and its weakness is that the all-tube law rests on two sources. The two differ little near \(Re_\lambda\approx100\), where most simulations are, and by a factor @R1000@ in the swirl at \(Re_\lambda=1000\) (Table 3). For a closure of micromixing, which depends on all tubes weighted by their volume, we recommend model I and regard the difference between the two as the uncertainty of the swirl at high Reynolds number. The intense tubes, if they keep 1% of the volume, carry 6% of the dissipation at \(Re_\lambda=100\) and a growing share above (Table 3, last column).</p>

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
<li><strong>The swirl at high Reynolds number.</strong> Models I and II differ by a factor @R1000@ at \(Re_\lambda=1000\). The all-tube law rests on Kida et al. (two simulations) and Mouri and Hori (one probe method, one fitted factor). A simulation above \(Re_\lambda\approx400\) analysed without a threshold would decide.</li>
<li><strong>The second family of radii.</strong> The model's \(r_{\max}=5\eta\) is the first lognormal function of the radius distributions (mean 4.6 to 5.5 \(\eta\), 53 to 71% of the tubes). The second, broad function (median 8.5 to 16.8 \(\eta\)) is not in the model. The budget of section 7 varies as \(\beta^2\) and \(\beta^4\), so a closure of a property to which the larger structures contribute would need a second term for them. The radius divisor of the probe data (1.75) assumes that the probe average follows the first function.</li>
<li><strong>Definitions.</strong> The core of Kida et al. is bounded by the inflection of the pressure, which for a Burgers vortex lies at \(0.66\,r_{\max}\); we follow the literature in comparing its diameter with the diameter of maximum swirl. Da Silva et al. give two inconsistent values of the swirl.</li>
<li><strong>The budget.</strong> The volume fraction follows from assigning to the background the dissipation of a uniform strain at the rate of the tubes; it is checked against two measured values only.</li>
<li><strong>The lag.</strong> The form of \(T_c\) is a scaling argument and \(C_c\) is not calibrated.</li>
<li><strong>Range.</strong> Isotropic small scales, \(35\le Re_\lambda\le1934\); no wall or interface effects.</li>
</ul>

<h2>15. Conclusions</h2>
<p>The vortex tubes of the dissipative range have a radius of maximum swirl of about \(5\eta\) (@RFIT@ \(\eta\) fitted) in every flow examined, with only a very small reduction with the Reynolds number, from @RL100@ \(\eta\) at \(Re_\lambda=100\) to @RL2000@ \(\eta\) at 2000; this is the firmest result. Their swirl is described by one law, \(U_{\max}/U_\eta=@C6@\,Re_\lambda^{1/2}\), that is a constant fraction \(@KAPPA@\) of the r.m.s. velocity, if probe data and the most intense tubes are corrected to a common level with the multipliers computed from the models of the probes, and by two laws without swirl corrections if the most intense tubes and all tubes are taken as two populations. Model selection with leave-one-source-out validation shows that the data support no more than one or two parameters in either case. The Burgers budget then gives the strain rate, circulation, volume fraction and spacing of the tubes from \(k\) and \(\varepsilon\), which places the engulfment model of micromixing on measured ground, and a first-order lag with one constant accounts for the time the cascade takes to feed the tubes. The path of every number from its paper to the model is recorded and open to comment.</p>
"""


def main(argv=None):
    text = build()
    with open(PAGE, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("wrote %s (%.2f MB)" % (PAGE, len(text.encode("utf-8")) / 1e6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
