"""belintab.py  The extra sections of the Belin (1996) tab of the recording book: the correlations of Table I, the wire-and-tube model fitted to Figs. 5 and 6, the U_max pdfs, what the data say and the corrections.
The numbers come from LIT/analysis/belin_model_numbers.json (belin_results.py); the figures are the png files of LIT/analysis (belin_incidence_schematic.py, belin_umax_five.py, belin_results.py).
Sections are added at the end of the tab (the rule of the book: a line keeps its number).

Versions  M01 m01.v01 (2026-11-13): first version.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ANALYSIS = os.path.join(os.path.dirname(HERE), "analysis")

__all__ = ["extra"]


def numbers():
    with open(os.path.join(ANALYSIS, "belin_model_numbers.json")) as f:
        return json.load(f)


def extra(tab):
    data = numbers()
    rows = {r["Re_lambda"]: r for r in data["rows"]}
    p = data["params"]
    tab.h("7. The correlations behind the numbers of Table I")
    tab.p("Table I of the paper lists, for each run, the viscosity, the mean local velocity U, the rms u', the Reynolds number Re of the disks and Re_lambda. Only some of these are needed for the tubes, and some are misprinted. "
          "Fits to the table (scripts belin_table1_*.py in LIT/analysis) give the chain that turns any Re_lambda into the scales of the flow:")
    tab.math(r"\nu=280\,Re^{-0.865}\ \mathrm{cm^2/s},\qquad \varepsilon=Po\,\frac{N^3D^5}{V}\ (Po=0.2697),\qquad u'=(\varepsilon L)^{1/3},\ L=5.738\ \mathrm{cm},\qquad Re_\lambda=\left(\frac{15\,u'L}{\nu}\right)^{1/2}")
    tab.math(r"\eta=\left(\frac{\nu^3}{\varepsilon}\right)^{1/4},\quad U_\eta=\frac{\nu}{\eta},\quad \lambda=u'\left(\frac{15\nu}{\varepsilon}\right)^{1/2},\quad \Omega R=\frac{Re\,\nu}{R_{disk}},\quad U=0.588\,\Omega R\ \ (R_{disk}=10\ \mathrm{cm},\ \text{cell 2})")
    tab.p("The bullets that follow are the findings of the table analysis:")
    tab.p("&bull; The viscosity is set by the pressure of the helium (4.2&ndash;8 K), so Re is changed by changing \\(\\nu\\); the fit \\(\\nu=280\\,Re^{-0.865}\\) holds over the whole table (belin_table1_nu.png).<br>"
          "&bull; The power number of the disks is constant, \\(Po=0.2697\\), so \\(\\varepsilon\\) follows from the speed of the disks (about 0.3 W/kg at \\(Re_\\lambda=659\\); belin_table1_po_const.png).<br>"
          "&bull; \\(u'^3/\\varepsilon\\) is constant, \\(=L=5.738\\) cm, and \\(U=0.588\\,\\Omega R\\): so the ratio \\(u'/U=0.29\\) does not depend on \\(Re_\\lambda\\); it is the spread of the incidence angle used below.<br>"
          "&bull; Two misprints of the table: \\(Re_\\lambda=879\\) in the last row of cell 1 is 439 (from its own \\(u'\\), \\(\\nu\\) and \\(\\varepsilon\\)), and \\(Re=2\\times10^6\\) in cell 2 is \\(10^6\\) (\\(\\nu=1.1\\times10^{-3}\\), \\(U=64\\)).")
    tab.img("belin_table1_calc_vs_table_lin.png", "The Re_lambda calculated from the chain against the Re_lambda of Table I (linear axes).")
    chain = []
    for Rl in (255, 659):
        r = rows[Rl]
        chain.append([str(Rl), "%.2f" % r["U_eta_cm_s"], "%.0f" % r["U_cm_s"], "%.2f" % r["sigma_sin_alpha"]])
    tab.table([r"\(Re_\lambda\)", r"\(U_\eta\) (cm/s)", r"mean flow \(U\) (cm/s)", r"\(\sigma(\sin\alpha)=u'/U\)"], chain, "The chain at the two Reynolds numbers of the model figures.")

    tab.h("8. The wire-and-tube model: what a hot wire reads from a stretched vortex")
    tab.p(r"The model is described in the paper (section 9, 'The wire-and-tube model'). Short form: straight Burgers tubes of random radius \(r_{\max}\) and swirl \(U_{\max}\) with isotropic axes are carried past a fixed wire by the flow; the wire is cooled by the velocity normal to it. "
          r"Belin et al. (their Fig. 3 and eqs. 2&ndash;8) place the tube's velocity W at a small angle \(\alpha\) to the direction normal to the wire (the mean flow); the swirl at the wire then has the component \(\sin\alpha\,v_\theta\) along the sensed direction, so the signal is an S-shape of peak-to-peak amplitude \(\Delta S=2\sin\alpha\,U_{\max}\) and extrema \(3.17R\) apart. Belin reads \(U_{\max}=\Delta S/(2\sin\alpha)\) with the constant \(\sin\alpha=0.14\).")
    tab.img("belin_incidence_schematic.png", "The incidence angle alpha (belin_incidence_schematic.py): the wire is fixed; alpha is the angle between the tube's velocity W = U + w and the mean flow x, which is the direction normal to the wire.")
    tab.p(r"In the model every crossing has its own \(\alpha\): \(\sin\alpha\) is Gaussian with the standard deviation \(u'/U=0.29\) of the chain " + tab.guess("sin(alpha) Gaussian with sigma = u'/U", "Belin estimates 8 degrees from the signal; the spread of the angle of the flow is not measured in the paper, and u'/U with U = 0.588 Omega R is the one-component fluctuation over the mean flow")
          + r"; the wire's yaw coefficient (cooling by the velocity along the wire) is \(k=0.2\) " + tab.guess("k = 0.2", "Joergensen's typical value; the wire of the paper is not calibrated in the text, and the sensitivity study shows k up to 0.2 changes nothing (k = 1 would remove almost all readable events)")
          + r". The distance of closest approach is uniform within the largest distance at which the tube can still pass Belin's 5-sigma gradient cut, and a tube is weighted by that reach and the cosine of the tilt of its axis (the footprint of the tube in the plane normal to the flow; the length of the tube cancels).")
    tab.h("9. The fit to Figs. 5 and 6 of the paper")
    tab.p(r"Three numbers describe the tubes: a lognormal of \(r_{\max}\) (median %.2f \(\eta\), width %.2f), and \(U_{\max}\) as %.2f times the DNS value \(0.769\,Re_\lambda^{1/3}U_\eta\) with a lognormal spread of %.2f; \(r_{\max}\) and \(U_{\max}\) are independent " % (p[0], p[1], p[2], p[3])
          + tab.guess("r_max and U_max independent", "the DNS correlation between radius and swirl is weak (rank correlation 0.4), and the data (Figs. 5 and 6) cannot separate it")
          + r". They were fitted in three phases (script chord_belin_sens_fit.py): (1) \(r_{\max}\) alone to the size pdf of Fig. 5 (misfit 0.20, median 8.9 \(\eta\)); (2) the swirl alone to Fig. 6 (misfit 0.13, scale 1.65); (3) all four together on both (misfit 0.46). "
          r"The phases show the compromise: the radius pdf wants larger tubes and a weaker swirl than the product pdf does when they are fitted jointly.")
    tab.img("belin_model_fig.png", "The fit at Re_lambda 255 and 659: the pdf of r_max (Fig. 5), of the product r_max U_max as x = Re_f/Re_lambda^0.5 (Fig. 6), and of U_max in cm/s and in units of U_eta. Grey: the tubes as generated; blue: the tubes that hit the wire; "
            "red: as the wire reads them (and with Belin's rule for the product); dots: Belin's data.")
    tab.h("10. The velocity distributions: what each step does")
    tab.p(r"The curves of the right-hand panels are: (i) the tubes as generated; (ii) the tubes that hit the wire, and (ii') those that are selected by the cut and read; (iii) what the wire observes, the half swing \(\Delta S/2\); (iv) Belin's rule \(\Delta S/(2\times0.14)\); (v) the same with the actual \(\alpha\) of each event as sampled. Areas are one.")
    tab.img("belin_umax_five.png", "U_max pdfs, linear axes, one Reynolds number a column (belin_umax_five.py).")
    r659, r255 = rows[659], rows[255]
    tab.p("<b>What the curves say</b> (Re_lambda 659; 255 in brackets):<br>"
          "&bull; The generated tubes have a median \\(U_{\\max}/U_\\eta\\) of %.1f (%.1f); the tubes that hit the wire and are selected and read are stronger: %.1f (%.1f). The gradient cut favours strong tubes.<br>"
          "&bull; The wire observes only %.1f (%.1f): the half swing is \\(\\sin\\alpha\\,U_{\\max}\\) with the \\(\\sin\\alpha\\) of the read events (median %.2f).<br>"
          "&bull; Belin's rule gives %.1f (%.1f), a factor %.1f too high; with the actual \\(\\alpha\\) the median is %.1f (%.1f), on top of the true value of the read events, which confirms the chain.<br>"
          "&bull; The events that are read have larger angles than the average crossing (median \\(|\\sin\\alpha|\\) 0.37, against 0.19 for all): an S-shape needs the angle, and a high gradient needs a strong signal."
          % (r659["U_population"]["median"], r255["U_population"]["median"], r659["U_read_true"]["median"], r255["U_read_true"]["median"], r659["U_observed"]["median"], r255["U_observed"]["median"], r659["sin_alpha_read"]["median"],
             r659["U_belin"]["median"], r255["U_belin"]["median"], 1 / r659["U_correction_intense_median"], r659["U_actual_alpha"]["median"], r255["U_actual_alpha"]["median"]))
    tab.h("11. What was learned")
    tab.p("&bull; With the wire normal to the flow, a tube crossed at right angles gives no S-shape: the incidence angle is what makes the signal, and it is also why amplitudes are low. Without it (the first volume model, alpha = 0) only 1% of the selected events could be read and the swirl needed was 400 cm/s or more, above the speed of the disks.<br>"
          "&bull; With the angle spread from u'/U the fit needs a swirl of about 2.6 times the DNS value (about 36 cm/s at Re_lambda 659, below the disk speed of 154 cm/s), and the size pdf of the paper is reproduced up to a radius that is too narrow at the peak.<br>"
          "&bull; The Belin swirl (his eq. 8 with 0.14) is too high by a factor of about 2.6 for the events that can be read; the median sin(alpha) of those events is 0.37.<br>"
          "&bull; The sensitivity at Re_lambda 659 (belin_sensitivity.png): the readable share of the selected events is 1% without the angle, 34% for the spread of the flow and 75% for an isotropic wire; the yaw coefficient matters only near 1; the mean flow U matters little; the swirl scale moves the product pdf.<br>"
          "&bull; Not settled: the radius pdf is not fitted well at the peak (the lognormal is too narrow and too high), the swirl is 2.6 times the DNS value, and the fit is made at two Reynolds numbers with a pdf (Fig. 6) that Belin pooled over Re_lambda 151&ndash;718.")
    tab.img("belin_sensitivity.png", "Sensitivity at Re_lambda 659: the spread of the incidence angle, the mean flow, the yaw coefficient and the swirl scale (belin_sensitivity: chord_belin_sens.py, 4000 crossings a curve).")
    tab.h("12. How the observed data become tube sizes and swirl")
    tab.p("&bull; The record of the wire is a time series; with Taylor's hypothesis, \\(s=Ut\\), so the time between the two extrema of the signal, \\(\\Delta t\\), is a length: \\(\\Delta s=U\\Delta t=3.17R=2\\,r_{\\max}\\), hence \\(R=0.31\\,U\\Delta t\\) and \\(r_{\\max}=1.585R\\) (eq. 8 of the paper).<br>"
          "&bull; The amplitude \\(\\Delta S\\) gives \\(U_{\\max}\\) only through the angle: \\(U_{\\max}=\\Delta S/(2\\sin\\alpha)\\); Belin uses the constant \\(\\sin\\alpha=0.14\\).<br>"
          "&bull; Fig. 5 is the pdf of R/eta of the events read this way; Fig. 6 is the pdf of \\(x=Re_f/Re_\\lambda^{1/2}\\), \\(Re_f=U_{\\max}R/\\nu\\); both are pooled over \\(Re_\\lambda=151\\)&ndash;718.<br>"
          "&bull; The size that the table of the page uses for Belin is the peak of Fig. 5 (3.5 \\(\\eta\\) as R, 5.5 \\(\\eta\\) as \\(r_{\\max}\\)): a statistic of the chord distribution, not of the tubes. The model gives the true tubes behind it.")
    tab.h("13. The corrections for the Belin data")
    head = [r"\(Re_\lambda\)", r"\(r_{\max}/\eta\) as read, median", r"true \(r_{\max}\) of the same events, median", "factor (true / read)", r"\(U_{\max}/U_\eta\) Belin's rule, median", r"true \(U_{\max}/U_\eta\) of the same events, median", "factor (true / Belin)", r"observed \(\Delta S/2\)"]
    body = []
    for Rl in (151, 255, 359, 507, 659, 718):
        r = rows[Rl]
        body.append([str(Rl), "%.2f" % r["r_read"]["median"], "%.2f" % r["r_read_true"]["median"], "%.2f" % r["r_correction_intense_median"], "%.1f" % r["U_belin"]["median"], "%.1f" % r["U_read_true"]["median"], "%.2f" % r["U_correction_intense_median"], "%.1f" % r["U_observed"]["median"]])
    tab.table(head, body, "Medians of the events that the model reads (the intense tubes): the radius as the wire reads it and the true radius, the swirl by Belin's rule and the true swirl. The model is the fit of section 9.")
    tab.p("<b>Applied to the page</b> (2026-11-13): the Belin radius row is the median of Fig. 5 (7.6 \\(\\eta\\) as \\(r_{\\max}\\), digitised) instead of its peak, and is divided by the model factor (read / true), about 1.15 over \\(Re_\\lambda=359\\)&ndash;718 (1.06 at 151, 1.10 at 255): the radius of the intense tubes is about 6.5 \\(\\eta\\), "
          "not 5.5. The swirl of Belin is not a row of the table: Belin's rule is 2.6 times the true value of the model, and the model value (16&ndash;23 \\(U_\\eta\\)) is itself about three times the DNS swirl, so it is shown and not fitted "
          + tab.guess("the model swirl of the intense tubes is not entered in the table", "it rests on the assumed spread of the incidence angle and on the independence of radius and swirl, and it sits well above the DNS tubes (open issue)") + ".")
    tab.h("14. The tubes of Belin against the other one-dimensional methods")
    tab.p("The tubes found here from the records of Belin et al. (radius median 7.3 eta, swirl 2.6 times the DNS) were put through the methods of Mouri et al. (2007), Mouri and Hori (2009) and Sassa and Makita (2005) (tabs of those papers; analysis/chord_mouri.py). They read radii and velocities 1.5 to 5 times too high; tubes of the DNS "
          "(radius 5.2 eta, swirl 1.0 times the DNS) reproduce the three methods. The record of Belin et al. is therefore the outlier, and its amplitude needs tubes 2.6 times stronger than the DNS in the wire model of section 8, "
          "also with a wider spread of the incidence angle (sigma of sin(alpha) = 0.6: the fit gives a swirl of 2.4 times the DNS, misfit 0.44 against 0.46; analysis/fit_sens_sa06.log). The radius row of the page for Belin (section 13) is provisional for this reason "
          + tab.guess("the Belin radius correction (1.15) and the model swirl are provisional", "they rest on a population that the other three methods do not support; the open items are the wire's nonlinear response, the pooling of Fig. 6 over Re_lambda 151-718 and the independence of radius and swirl"))
