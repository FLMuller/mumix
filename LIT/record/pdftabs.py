r"""pdftabs.py  The tabs of the four papers whose pdfs we digitised: Tanahashi et al. (2001), Tanahashi et al. (2004), Das et al. (2006), Pirozzoli (2012).

fill(book) adds to the generic tabs of tanahashi2001, das2006 and pirozzoli the steps of the figure (the page, the digitising, the fits, the statistics, the grid and the detection),
and makes the tab tanahashi2004. The numbers of the fits are made again when the book is built (summary_pdfs.main), from the digitised csv files of the analysis folder.

VERSION  M1 m01.v01 (2026-11-12): first version.
"""
import contextlib
import io
import math
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ANALYSIS = os.path.join(os.path.dirname(HERE), "analysis")
sys.path.insert(0, ANALYSIS)

from recordbook import paper_line, pdfcrop        # noqa: E402

__all__ = ["fill"]


def fits():
    """{(source key, quantity key): dict of the statistics and the two-lognormal fit} made again from the digitised csv files (summary_pdfs.main)."""
    import summary_pdfs
    with contextlib.redirect_stdout(io.StringIO()):
        summary_pdfs.main()
    out = {}
    with open(os.path.join(ANALYSIS, "pdfs_summary.csv"), encoding="utf-8") as f:
        next(f)
        for line in f:
            parts = line.rstrip("\n").split(",")
            nums = [float(v) for v in parts[-12:]]
            head = ",".join(parts[:-12])
            found = re.match(r"^(.*?),(radius|swirl .*)$", head)
            source, quantity = found.group(1), found.group(2)
            key = ("t01" if source.startswith("Tanahashi 2001") else "t04" if source.startswith("Tanahashi 2004") else "das" if source.startswith("Das") else "pir",
                   "radius" if quantity == "radius" else "swirl")
            names = ("mode", "median", "mean", "q10", "q90", "a1", "m1", "s1", "m2", "s2", "rms", "area")
            out[key] = dict(zip(names, nums))
    return out


def volume_fraction(a1, m1, s1, m2, s2):
    """The fraction of the volume of the tubes that component 1 holds: the second moment of each lognormal (cross-section ~ D^2): a e^(2 mu + 2 s^2), mu = ln median."""
    w1 = a1 * math.exp(2 * math.log(m1) + 2 * s1 * s1)
    w2 = (1 - a1) * math.exp(2 * math.log(m2) + 2 * s2 * s2)
    return w1 / (w1 + w2)


def fit_block(tab, fit, what, unit, tiny=""):
    """The steps from the digitised curve to the numbers: the statistics and the two lognormals, with the formulas."""
    tab.math(r"p(x)=a_1\,\frac{e^{-(\ln x-\mu_1)^2/2s_1^2}}{x\,s_1\sqrt{2\pi}}+(1-a_1)\,\frac{e^{-(\ln x-\mu_2)^2/2s_2^2}}{x\,s_2\sqrt{2\pi}},\qquad \text{median}=e^{\mu},\quad \text{mode}=e^{\mu-s^2},\quad \text{mean}=e^{\mu+s^2/2}")
    tab.table(["", "mode", "median", "mean", "10 %", "90 %"], [[what, "%.3g" % fit["mode"], "%.3g" % fit["median"], "%.3g" % fit["mean"], "%.3g" % fit["q10"], "%.3g" % fit["q90"]]],
              "The statistics of the digitised curve itself (no fit): cumulative integral of the curve scaled to area 1. Unit: %s." % unit)
    tab.table([r"\(a_1\)", "median 1", r"\(s_1\)", "median 2", r"\(s_2\)", "rms misfit / peak", "area of the digitised curve (before scaling to 1)"],
              [["%.3f" % fit["a1"], "%.3g" % fit["m1"], "%.3f" % fit["s1"], "%.3g" % fit["m2"], "%.3f" % fit["s2"], "%.3f" % fit["rms"], "%.3f" % fit["area"]]],
              "The two-lognormal fit " + tiny)


def digitised_table(tab, csv, cols, every=12, caption=""):
    d = np.genfromtxt(os.path.join(ANALYSIS, csv), delimiter=",", names=True)
    idx = list(range(0, len(d), every))
    rows = [["%.3g" % d[cols[0]][i], "%.3g" % d[cols[1]][i], "%.3g" % d[cols[2]][i], "%.3g" % d[cols[3]][i]] for i in idx]
    tab.table([cols[0], cols[1], cols[2], cols[3] + " = (top+bottom)/2"], rows, "%s (every %dth of %d points; the whole file is %s)" % (caption, every, len(d), csv))


METHOD = (r"The pdf is drawn with a logarithmic vertical axis, and the curves of the figure are a band (several curves). The digitiser finds, at each horizontal position, the upper bound "
          r"and the lower bound of the plotted curves, and takes \(P=(P_{top}+P_{bottom})/2\). The pixel rows are turned into values with the tick marks of the axis: "
          r"\(\log_{10}P = \text{top exponent} - \dfrac{y-y_0}{y_1-y_0}\times\text{decades}\) (a straight line on the logarithmic axis, fixed by two labelled ticks).")


def tanahashi2001(book, f):
    tab = next(t for t in book.tabs if t.id == "tanahashi2001")
    tab.h("7. The figure we digitised: Fig. 7 of the paper (page 9 of the journal, page 10 of the pdf)")
    tab.img(pdfcrop("Tanahashi (2001).pdf", 10, (0.12, 0.40, 0.88, 0.61)), "Fig. 7 of Tanahashi et al. (2001): pdf of D* (left) and v*θ,m (right), Re_ω,0 = 500, at t = 70, 90, 110, 130. Both axes of P are logarithmic.")
    tab.p(r"The text next to it: the pdfs of \(D^*\) and \(u^*_\theta\) 'show peaks at \(D^*\approx9\) and \(u^*_\theta\approx0.5\)'. \(D^*\) is the diameter over the Kolmogorov length \(\eta\) and \(v^*_{\theta,m}\) the "
          r"maximum azimuthal velocity over \(u'_{rms}\), both as the text of section 3 says. The curves of the four times lie close: that is the band the digitiser works on.")
    tab.p("The figure as we digitised it (the screenshot you gave, not the pdf page):")
    tab.img("tanahashi2001_fig7.png", "tanahashi2001_fig7.png, the image the digitiser was run on")
    tab.h("8. The simulation and the identification of the eddies")
    tab.img(pdfcrop("Tanahashi (2001).pdf", 5, (0.08, 0.15, 0.92, 0.33)), "Section 2 of the paper: the grids (216×325×144 for Re_ω,0 = 500; 288×433×192 for 700; 324×487×216 for 900) and the times analysed.")
    tab.table(["quantity", "value", "where in the paper"],
              [["flow", "temporally developing turbulent mixing layer, tanh(2y) initial profile", "section 2"],
               ["domain", r"\(4\Lambda\times6\Lambda\times(8/3)\Lambda\), \(\Lambda\) the most unstable wavelength; periodic in x and z, free-slip in y", "section 2"],
               ["method", "Fourier series in x and z, sine/cosine series in y; third-order Runge–Kutta, 3/2 dealiasing", "section 2"],
               ["grid, Re_ω,0 = 500", "216 × 325 × 144 (the case of Fig. 7)", "section 2"],
               ["times analysed", "t = 70, 90, 110, 130", "section 2"],
               ["detection", "second invariant Q of the velocity gradient tensor, 'without a vorticity threshold': the local maximum of Q is the centre; the radius is the distance to the maximum of the mean azimuthal velocity in the plane normal to the axis", "sections 3 and 4"]],
              "Everything in this table is a statement of the paper.")
    tab.img(pdfcrop("Tanahashi (2001).pdf", 4, (0.10, 0.14, 0.90, 0.37)), "Fig. 1 of the paper: (b) the Reynolds number based on the Taylor microscale, Re_λ, against time for the three cases.")
    tab.p(r"Reading Fig. 1(b) for the case of Fig. 7 (\(Re_{\omega,0}=500\), the circle symbols): \(Re_\lambda\) rises between t = 35 and 65 and then stays between about 75 and 85 for t = 70&ndash;130. "
          r"The text says 'the highest \(Re_\lambda\) is about 100 for the case of \(Re_{\omega,0}=900\)'. " +
          tab.guess(r"the reading Re_λ ≈ 80 for Re_ω,0 = 500", "it is read by eye from the figure, to about ±8; the paper prints no number for this case") +
          r" <b>The page assumed \(Re_\lambda=200\)</b> (sourcedata, Tanahashi01, 'the paper gives no \(Re_\lambda\)'): that was wrong, and the row would sit at about 80.")
    tab.p(tab.guess("the grid spacing in η of this mixing layer", "the paper gives no spacing in η: Fig. 2 shows the spectrum against k_x η, whose largest wavenumber would give it, but we have not read it") + " &mdash; not done.")
    tab.h("9. Digitising the pdf")
    tab.p(METHOD)
    tab.p("Rules of the digitiser: the points where the lower bound is below 2×10⁻⁴ are dropped (those are the noisy single-count tail lines of the figure); the curve starts at the first point above that and ends where the band falls to the floor of the plot.")
    tab.img("tanahashi2001_overlay.png", "The digitised curve (P = (top+bottom)/2) drawn on top of the figure, to check it: the left panel is the diameter, the right panel the swirl.")
    digitised_table(tab, "tanahashi2001_pdfs.csv", ("D_star", "pD_top", "pD_bottom", "pD"), 25, "The diameter pdf, D* = D/η.")
    digitised_table(tab, "tanahashi2001_pdfs.csv", ("v_star", "pv_top", "pv_bottom", "pv"), 25, "The swirl pdf, v* = v_θ,m/u_rms.")
    tab.h("10. The radius, and the fit with two lognormals")
    tab.p(r"The radius of maximum swirl is half the diameter: \(r_{\max}=D/2\), so \(p_r(r)=2\,p_D(2r)\). The curve is scaled to a total area of 1 (the digitised area, the rise below the first point and the "
          r"tail beyond the last point are all counted: summary_pdfs.normalise). A single lognormal does not fit (the curve has a narrow core and a long tail), so two are fitted in the "
          r"linear domain (a fit in log P weights the tail as much as the core, and the core is what we need), with the weight free, the medians ordered \(\mu_2>\mu_1\) and \(s_2\ge2s_1\) as you asked.")
    tab.img("tanahashi2001_lognormal.png", "The fit to the diameter pdf (older figure: the bimodal fit and its two components).")
    r = f[("t01", "radius")]
    fit_block(tab, r, "radius r_max/η", "η", "(components in r/η; the weights are for the area under each, summing to 1).")
    vf = volume_fraction(r["a1"], r["m1"], r["s1"], r["m2"], r["s2"])
    tab.p("Volume. The cross-section of a tube goes as D², so weighting each component by its second moment, E[D²] = e<sup>2μ+2s²</sup>, the first (narrow) family holds <b>%.0f %%</b> of the tube volume and the second (broad, "
          "about twice the size) <b>%.0f %%</b>, although the first has %.0f %% of the tubes." % (100 * vf, 100 * (1 - vf), 100 * r["a1"]))
    s = f[("t01", "swirl")]
    fit_block(tab, s, r"swirl v/u_rms", "u_rms", "(the swirl needs no width constraint).")
    tab.h("11. What the page uses, and what it could use")
    tab.table(["statistic of the radius pdf", "r_max/η"],
              [["<b>first lognormal function</b> (%.0f %% of the tubes, width %.2f): median" % (100 * r["a1"], r["s1"]), "<b>%.2f</b>" % r["m1"]],
               ["first lognormal function: mean", "<b>%.2f</b>" % (r["m1"] * math.exp(r["s1"] ** 2 / 2))],
               ["second lognormal function (%.0f %% of the tubes, width %.2f): median" % (100 * (1 - r["a1"]), r["s2"]), "%.2f" % r["m2"]],
               ["whole pdf: peak (mode) of the digitised curve", "%.2f" % r["mode"]], ["whole pdf: median", "%.2f" % r["median"]], ["whole pdf: mean (raised by the second function)", "%.2f" % r["mean"]],
               ["whole pdf: 10 % and 90 %", "%.2f and %.2f" % (r["q10"], r["q90"])], ["the page's row (the peak of the pdf quoted in the text, D ≈ 9 η, halved)", "4.5"]],
              "The first lognormal function is the tube of the model: its mean and median are the r_max/η to compare with the model's 5. The page's row took the peak quoted in the text.")
    tab.p(tab.guess("the table row uses the peak of the pdf quoted in the text (4.5), where the first lognormal function has a median of %.1f and a mean of %.1f" % (r["m1"], r["m1"] * math.exp(r["s1"] ** 2 / 2)),
                    "the paper's text quotes only the peak of the diameter pdf; the first function comes from our fit of the digitised curve. The whole-pdf mean, %.1f, includes the broad second function and is not the radius of the model's tube" % r["mean"]))


def tanahashi2004(book, f, after):
    tab = book.tab("tanahashi2004", "Tanahashi et al. (2004)")
    book.tabs.remove(tab)
    book.tabs.insert(book.tabs.index(after) + 1, tab)
    tab.h("1. The paper")
    paper_line(tab, ["Tanahashi (2004).pdf"], ["Tanahashi, Kang, Miyamoto, Shiokawa and Miyauchi (2004)"])
    tab.p("<b>Tanahashi, Kang, Miyamoto, Shiokawa and Miyauchi (2004)</b>, Int. J. Heat and Fluid Flow 25, 331&ndash;340, doi 10.1016/j.ijheatfluidflow.2004.02.016. Whole tubes (all coherent fine-scale eddies, no threshold) in channel flow at "
          r"\(Re_\tau=180\), 400 and 800. This paper is <i>not</i> a row of the summary table (it has no \(Re_\lambda\)); we digitised its Fig. 5 as a second whole-tube size and swirl pdf.")
    tab.h("2. The simulation: Table 1 of the paper")
    tab.img(pdfcrop("Tanahashi (2004).pdf", 2, (0.07, 0.07, 0.95, 0.19)), "Table 1: the domain, the grid and the spacings in wall units. δ is the channel half-width; Δ⁺ = Δ u_τ/ν.")
    tab.table([r"\(Re_\tau\)", "bulk Re", r"\(L_x\times L_y\times L_z\)", r"\(N_x\times N_y\times N_z\)", r"\(\Delta x^+\)", r"\(\Delta y^+\)", r"\(\Delta z^+\)"],
              [["180", "3276", "4πδ × 2δ × 2πδ", "192 × 193 × 160", "11.781", "0.433&ndash;4.664", "7.069"], ["400", "8200", "2πδ × 2δ × πδ", "256 × 385 × 192", "9.817", "0.479&ndash;5.183", "6.544"],
               ["800", "17 760", "2πδ × 2δ × πδ", "512 × 769 × 384", "9.817", "0.479&ndash;5.183", "6.544"]], "Typed from the image above (each row one run). Check: 4π·180/192 = 11.78, 2π·180/160 = 7.07, 2π·800/512 = 9.82, π·800/384 = 6.54.")
    tab.p("The figure we digitised, Fig. 5, is for Re_τ = 800 (the last row). The channel is 2δ⁺ = 1600 wall units high, 5027 long and 2513 wide.")
    tab.h("3. How the eddies are found")
    tab.img(pdfcrop("Tanahashi (2004).pdf", 4, (0.07, 0.07, 0.50, 0.40)), "The identification of the paper: the local flow pattern, no threshold.")
    tab.p(r"The scheme (from the text): Q of the velocity gradient tensor at each collocation point; the probability that a positive maximum of Q lies near each point; the points with high probability "
          r"are searched with a 3-D fourth-order Lagrange interpolation for the true maximum; a plane normal to the vorticity vector through the maximum gives the mean azimuthal velocity, and the point of minimum "
          r"variance of the azimuthal velocity is searched around it. The radius is where the mean azimuthal velocity is maximal; \(\eta\) and \(u_K\) are those 'calculated from mean energy dissipation rate at \(y^+\), where the eddy exists'.")
    tab.h("4. Fig. 5: the pdfs")
    tab.img(pdfcrop("Tanahashi (2004).pdf", 4, (0.10, 0.64, 0.90, 0.92)), "Fig. 5 of the paper: pdf of the diameter D/η (a) and of the maximum azimuthal velocity v_θmax/u_k (b), Re_τ = 800, for nine bands of the wall distance y⁺ (0&ndash;40 ... 560&ndash;800).")
    tab.p("The text: 'both pdfs do not depend on Re_τ ... whereas they have weak y⁺-dependence. Near the wall the most expected diameter and maximum azimuthal velocity are about 10η and 2.0u_k; leaving from the wall they become about 8η and 1.2u_k.'")
    tab.img("tanahashi2004_fig5.png", "The image the digitiser was run on (your screenshot of the figure).")
    tab.h("5. Digitising")
    tab.p(METHOD + " Here the band is the nine curves of the nine wall bands: the result is the pdf of the tubes <i>over all bands</i>, with the bands' spread as the width of the band.")
    tab.img("tanahashi2004_overlay.png", "The digitised mean curve drawn on the figure.")
    digitised_table(tab, "tanahashi2004_pdfs.csv", ("D_over_eta", "pD_top", "pD_bottom", "pD"), 20, "The diameter pdf, D/η.")
    digitised_table(tab, "tanahashi2004_pdfs.csv", ("v_over_uk", "pv_top", "pv_bottom", "pv"), 20, "The swirl pdf, v/u_K.")
    tab.p(tab.guess("the mean of the nine bands is a pdf of the whole channel", "the bands do not hold equal numbers of eddies, so the mean of the nine curves is not the pdf of all the eddies; the paper shows no pooled curve") +
          " &mdash; the bands differ little (the paper says), so the error is small; the bounds of the band are in the csv.")
    tab.h("6. The fits")
    r = f[("t04", "radius")]
    fit_block(tab, r, "radius r_max/η", "η", "(r = D/2).")
    tab.p("Volume: the narrow family holds %.0f %% of the tube volume (%.0f %% of the tubes)." % (100 * volume_fraction(r["a1"], r["m1"], r["s1"], r["m2"], r["s2"]), 100 * r["a1"]))
    s = f[("t04", "swirl")]
    fit_block(tab, s, "swirl v/u_K", "u_K")
    tab.p("The statistics against the text: the text quotes the most expected D = 8&ndash;10 η and v = 1.2&ndash;2.0 u_K. The digitised peaks are D/2 = %.1f η (D = %.1f η) and v = %.2f u_K." % (r["mode"], 2 * r["mode"], s["mode"]))
    tab.h("7. How big is the cell, in η")
    tab.p(r"The spacing in η follows from the spacing in wall units and \(\eta^+=\varepsilon^{+-1/4}\), with \(\varepsilon^+\) read from the dissipation curve of Fig. 3 of the paper (the budget of the turbulent kinetic energy) at the wall distance of the band.")
    tab.img(pdfcrop("Tanahashi (2004).pdf", 3, (0.07, 0.31, 0.50, 0.54)), "Fig. 3 of the paper: the budget of the turbulent kinetic energy; the lower curves are the viscous dissipation (loss).")
    tab.p(r"At \(y^+\approx145\) the dissipation reads \(\varepsilon^+\approx0.015\) " + tab.guess("ε⁺ ≈ 0.015 at y⁺ = 145", "read by eye from Fig. 3, to ±10 %") + r", so \(\eta^+\approx2.9\). At \(Re_\tau=800\): \(\Delta x/\eta=9.82/2.9=3.4\), \(\Delta z/\eta=6.54/2.9=2.3\); at \(Re_\tau=180\): 4.1 and 2.4. "
          r"\(\Delta/\eta\) depends on the wall distance (near the wall \(\varepsilon^+\) is larger, \(\eta^+\) smaller): the pdf pools all the bands, so no single number describes it.")


    tab.h("8. As used in the model")
    tab.p(r"No number of this paper enters the fits: it has no \(Re_\lambda\). It is evidence for the width of the size and swirl distributions of all tubes (this tab), for the grid and detection of the channel simulations, and for the dissipation profile used to put the grid in Kolmogorov units.")


def das2006(book, f):
    tab = next(t for t in book.tabs if t.id == "das2006")
    tab.h("7. The figure we digitised: Fig. 7 (page 65)")
    tab.img(pdfcrop("Das (2006).pdf", 11, (0.10, 0.07, 0.92, 0.60)), "Fig. 7 of Das et al. (2006): pdf of coherent fine eddies. (a) Diameter D*, (b) maximum azimuthal velocity <u*θ>max. Five bands of wall distance; the legend is in y⁺.")
    tab.p(r"The text under the figure: the circulation is \(\Gamma^*=\Gamma/(u'_{rms}\eta)\), 'normalized by Kolmogorov microscale, \(\eta\), and \(u'_{rms}\)'; Fig. 8 normalises the mean azimuthal velocity with \(u'_{rms}\). "
          r"So the swirl axis of Fig. 7(b) is in units of \(u'_{rms}\) (the text near Fig. 8 says the maximum mean azimuthal velocity is about 0.5&ndash;0.6 \(u'_{rms}\)) &mdash; the open point of the earlier list (the normalisation of the Das swirl) is settled by the paper's text.")
    tab.h("8. The simulation: grid and detection")
    tab.img(pdfcrop("Das (2006).pdf", 4, (0.08, 0.70, 0.92, 0.84)), "Section 2 of the paper: Re_τ = 100 and 180, domain 4πδ × 2δ × 2πδ, grids 128×129×128 and 192×193×160 'in x, y, z respectively'.")
    tab.table([r"\(Re_\tau\)", "grid", r"\(\Delta x^+\)", r"\(\Delta z^+\)"],
              [["100", "128 × 129 × 128", "4π·100/128 = 9.8", "2π·100/128 = 4.9"], ["180", "192 × 193 × 160", "4π·180/192 = 11.8", "2π·180/160 = 7.1"]],
              "The two runs of the paper, matched in the order the paper gives them ('and ... respectively'). The spacings are computed here, not printed. The Fig. 7 data are in bands up to y⁺ = 180, so they are the Re_τ = 180 run.")
    tab.p(r"<b>Correction of what we said earlier.</b> I had matched the 128×129×128 grid to \(Re_\tau=180\) and concluded that Das et al. had the coarsest grid (\(\Delta x^+=17.7\)). The text says the grids go with the two Reynolds numbers in order, "
          r"which makes the \(Re_\tau=180\) grid 192×193×160 &mdash; the same as Tanahashi et al. (2004) at \(Re_\tau=180\) (\(\Delta x^+=11.8\), \(\Delta z^+=7.1\)). " +
          tab.guess("Fig. 7 is the Re_τ = 180 run, on the 192×193×160 grid", "the bands end at y⁺ = 180 = Re_τ, and the paper lists the grids in the order of the Reynolds numbers; the figure caption does not say which run it shows") +
          " So the resolution does not explain why the Das pdf lies far out from the others; the lower Re_τ and the different wall bands (y⁺ 110&ndash;180 at the centre of a Re_τ = 180 channel) are what is left.")
    tab.p("Identification: the local flow pattern method of Tanahashi et al. (the same as in the 2004 paper); η from the paper's Eq. (13), (ν³/ε)^(1/4).")
    tab.h("9. Digitising: the open symbols only")
    tab.p(r"The figure has filled symbols (the bands near the wall) and open symbols (the bands <b>110 &lt; y⁺ &lt; 145 and 145 &lt; y⁺ &lt; 180</b>, the outer bands). You asked for the open ones only, because the others lie in the buffer region. "
          r"The two high-resolution crops you gave (das2006_fig7a.png, das2006_fig7b.png) were used.")
    tab.img("das2006_fig7a.png", "The high-resolution crop of panel (a), the diameter pdf.")
    tab.p(r"Open markers are found as holes: the image is binarised, the holes of the closed marker outlines are filled, the dark pixels (the black lines and filled markers) are subtracted, and what remains is a ring. "
          r"A ring with too much dark inside it (a hole between two black markers, not a marker) is rejected (annulus darkness above 0.60). The marker positions then lie on a grid of the x positions of the series: "
          r"where a marker is hidden behind a black one, the expected x position is taken from the two series' spacing and the pixels there are averaged in y.")
    tab.img("das2006_holes_filter.png", "The hole detection and the outlier test.")
    tab.p(METHOD)
    tab.p(tab.guess("16 points are hand-marked dots (green round on red square in the screenshot you made)", "the open markers that go behind black ones cannot be found by the program; you added dots, and the program takes their position") +
          " " + tab.guess("above D* = 18 the curve is a straight line (log P = ln(0.1053) − 0.0682 D*)", "the upper markers hide behind the filled ones; you said they can be approximated with a straight line (orange dots)"))
    tab.img("das2006_open_on_dots.png", "The final open-symbol curve (points) on the screenshot with the hand dots.")
    digitised_table(tab, "das2006_open_pdfs.csv", ("D_star", "pD_top", "pD_bottom", "pD"), 8, "The diameter pdf of the open symbols, D* = D/η.")
    digitised_table(tab, "das2006_open_pdfs.csv", ("u_star", "pv_top", "pv_bottom", "pv"), 8, "The swirl pdf of the open symbols, u* = u_θmax/u_rms.")
    tab.h("10. Normalisation, the area, and the fits")
    tab.p(r"The pdf of Das et al. should integrate to 1. The digitised area of the diameter curve was 1.02 (with the straight tail) and its rise below the first point and the tail beyond the last add the rest: "
          r"the total is scaled to 1 (check_das_area.py, summary_pdfs.normalise). You asked for this because the first version of the curve did not integrate to 1 and the fit then lay under the data everywhere.")
    r = f[("das", "radius")]
    tab.p(r"Fit. The curve is nearly one broad lognormal (\(s_2\approx0.69\)) with a small narrow bump near the peak. " + tab.guess("the fit starts from a1 = 0.7 with the weight free, and finishes with a1 = 0.08 and a narrow family s1 = 0.23", "the narrow family is almost absent in the open-symbol data, so the fit moves to a broad single lognormal; the fixed-start experiments (a1 = 0.42&ndash;0.55, medians 10&ndash;20, σ1 0.3&ndash;1) all gave a shoulder"))
    fit_block(tab, r, "radius r_max/η (r = D*/2)", "η")
    s = f[("das", "swirl")]
    fit_block(tab, s, "swirl u/u_rms", "u_rms")
    tab.p("Page rows: the summary table has 'Das, Miyauchi, Wang (2006, 2007)' with radius 10&ndash;12η (the text's diameter range, giving 5.5 as the radius). The digitised open-symbol radius pdf has mode %.2f, median %.2f, mean %.2f." % (r["mode"], r["median"], r["mean"]))


def pirozzoli(book, f):
    tab = next(t for t in book.tabs if t.id == "pirozzoli")
    tab.h("7. The figure we digitised: Fig. 2")
    tab.img(pdfcrop("Pirozzoli (2012).pdf", 3, (0.06, 0.06, 0.95, 0.275)), "Fig. 2 of Pirozzoli (2012): the pdf of the vortex core radius r0/η (a) and of the maximum induced velocity v0/u_K (b). Symbols: present DNS (the caption says test case D); line: Tanahashi et al. [24], Re_λ = 97.")
    tab.p(r"The text: 'typical vortex tubes have radii of a few Kolmogorov units (the expected value is \(\bar r_0\approx6\)), and the expected induced velocity is \(\bar v_0\approx2u_k\)'; 'excellent agreement between the present dataset and Tanahashi's gives confidence in the validity of our eduction algorithm'. "
          r"Reference [24] is Tanahashi, Miyauchi and Ikeda (2008), IUTAM Symposium, on isotropic turbulence, not the channel paper.")
    tab.h("8. The simulation: Table 1 and the algorithm")
    tab.img(pdfcrop("Pirozzoli (2012).pdf", 2, (0.06, 0.07, 0.52, 0.20)), "Table 1: the five test cases (Re_λ, mesh, k_max η, number of cores, symbol).")
    tab.table(["test case", "A", "B", "C", "D", "E"], [[r"\(Re_\lambda\)", "38.3", "71.3", "99.9", "98.6", "251.4"], ["mesh", "256³", "256³", "256³", "512³", "512³"],
              [r"\(k_{\max}\eta\)", "8.55", "3.81", "2.16", "4.49", "1.31"], [r"\(N_{sam}\)", "3826", "8019", "18 598", "28 087", "170 289"], ["symbol", "□", "◇", "▽", "△", "○"]],
              "Typed from the image above. The row k_max η is labelled in the paper (the text extraction had lost the label).")
    tab.p(r"The box is \((2\pi)^3\), periodic, forced isotropic turbulence at \(k\le k_F=3\) (the DNS of P. Orlandi, J. Fluid Mech. 623). With dealiasing \(k_{\max}=N/3\) the spacing is \(\Delta/\eta=2\pi/(3\,k_{\max}\eta)\): case D 0.47, E 1.6. " +
          tab.guess("k_max = N/3 for the dealiasing", "the paper does not say how k_max is defined; with k_max = N/2 the spacings are 1.5 times larger"))
    tab.img(pdfcrop("Pirozzoli (2012).pdf", 2, (0.52, 0.58, 0.95, 0.97)), "The eduction algorithm: the planes are scanned, candidate centres are pressure minima, the velocity pattern around them must be a vortex, and the core is averaged in the azimuth; r0 is the radius of the maximum velocity.")
    tab.p(r"<b>A discrepancy.</b> The caption of Fig. 2 says the symbols are test case D (\(Re_\lambda=98.6\), △ in Table 1), but the plotted symbols are open <b>circles</b>, which Table 1 assigns to case E (\(Re_\lambda=251.4\)). " +
          tab.guess("Fig. 2 shows case D", "the caption says so, and the Tanahashi line it is compared with is at Re_λ = 97, close to D's 98.6; but the circle symbols are those of case E") + " If it were E, the pdf would belong to a larger Re_λ and the agreement with the Re_λ = 97 line would be less natural.")
    tab.h("9. Digitising")
    tab.p(METHOD + " Here the plotted DNS circles and the Tanahashi line are two series on one figure; our curve follows the markers (open circles) and the line where the circles are absent (the tail beyond r0/η ≈ 35).")
    tab.img("pirozzoli2012_overlay.png", "The digitised curve on the figure.")
    digitised_table(tab, "pirozzoli2012_pdfs.csv", ("r0_over_eta", "pr_top", "pr_bottom", "pr"), 20, "The radius pdf r0/η.")
    digitised_table(tab, "pirozzoli2012_pdfs.csv", ("v0_over_uk", "pv_top", "pv_bottom", "pv"), 20, "The swirl pdf v0/u_K.")
    tab.p(tab.guess("the digitised curve is the DNS circles, not the Tanahashi line", "the figure shows both; where the circles scatter in the tail (r0/η > 35) the line and the circles are mixed in the 'band', so the tail follows both") + " You noticed that the Tanahashi and Pirozzoli curves look alike: they are two curves of the same kind of flow (isotropic turbulence, Re_λ ≈ 97&ndash;99) drawn on one figure, so they agree by construction of the figure.")
    tab.h("10. The fits")
    r = f[("pir", "radius")]
    fit_block(tab, r, "radius r0/η", "η")
    tab.p("Volume: the narrow family holds %.0f %% of the tube volume (%.0f %% of the tubes)." % (100 * volume_fraction(r["a1"], r["m1"], r["s1"], r["m2"], r["s2"]), 100 * r["a1"]))
    s = f[("pir", "swirl")]
    fit_block(tab, s, "swirl v0/u_K", "u_K")
    tab.p("Page rows: 'Pirozzoli (2009, 2012)': radius 6 (the text), swirl 2 (the text), and one value %s from the 2009 paper at Re_λ = 250. " % "5.12" + tab.guess("the table uses the text's 'expected values' 6 and 2", "the text calls them the expected values; the digitised pdf gives a peak at %.1f, a median %.1f and a mean %.1f for the radius" % (r["mode"], r["median"], r["mean"])))


def fill(book):
    f = fits()
    tanahashi2001(book, f)
    after = next(t for t in book.tabs if t.id == "tanahashi2001")
    tanahashi2004(book, f, after)
    das2006(book, f)
    pirozzoli(book, f)
