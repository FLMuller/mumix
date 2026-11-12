r"""evidence.py  The evidence trail of the recording book: what was read on which page of each paper, the corrections and their rationale, and the link to the model.

    EVIDENCE[tab id]        the steps of a paper: (pdf, page, box, rotate, caption, what was read (html), status)
                            status 'ok' (the numbers were read on the page image and match the data file), 'note' (context),
                            or a tuple ('guess', what, why): an assumption, written in red.
    evidence_steps(tab)     adds the steps of a tab (the cut-out of the page, what is read from it, its status)
    corrections_tab(book)   the tab 'Corrections': every change made to the numbers of the papers, with its rationale and the review of it
    model_tab(book)         the tab 'Data to model': which rows enter the fits, the selection of the model, the checks

All page numbers are those of the pdf file in LIT/.  The review was made on 2026-11-12 from rendered page images (pypdfium2), not from the text layer:
the working notes are review_notes.md in this folder.

VERSION  M1 m01.v01 (2026-11-12): first version.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from recordbook import pdfcrop        # noqa: E402

__all__ = ["EVIDENCE", "evidence_steps", "corrections_tab", "model_tab"]

OK = "ok"
NOTE = "note"


def G(what, why):
    return ("guess", what, why)


# (pdf, page, (x0, y0, x1, y1), rotate degrees, caption, what was read, status)
EVIDENCE = {
    "ghira2022": [
        ("Ghira (2022).pdf", 6, (0.08, 0.05, 0.95, 0.95), 0, "The definitions (Sec. II B): the intense vorticity structures, the radius, the circulation.",
         r"The structures are 'flow points with the highest vorticity magnitude covering 1% of the total flow domain'. The radius \(R_{ivs}\) is where the azimuthal average of the axial vorticity has fallen to \(\omega_0/e\) (Eq. 8, a Gaussian profile, Eq. 7); the Burgers radius is \(R_B=2(\nu/\alpha)^{1/2}\) (Eq. 5); \(\Gamma=2\pi\langle U_{ivs}\rangle R_{ivs}\) (Eq. 9) is the circulation <i>at</i> \(R_{ivs}\), not the total.", OK),
        ("Ghira (2022).pdf", 8, (0.08, 0.05, 0.95, 0.45), 0, "Table III: the mean values for each simulation.",
         r"\(R_{ivs}/\eta\) = 4.28, 4.23, 4.10, 4.06, 3.98, 3.98, 3.90; \(R_{ivs}/R_B\) = 0.96, 0.98, 0.97, 0.98, 0.98, 0.98, 0.97; \(U_{ivs}/u_\eta\) = 6.01, 7.11, 7.83, 8.31, 9.33, 9.37, 10.23; \(Re_\Gamma Re_\lambda^{-1/2}\) = 14.36, 13.01, 12.19, 11.32, 10.92, 11.34, 10.35. All 28 numbers match the data file.", OK),
        ("Ghira (2022).pdf", 3, (0.08, 0.05, 0.95, 0.42), 0, "Table II: the simulations.",
         r"\(Re_\lambda\) = 90, 148, 191, 242, 314, 292, 399; \(\nu\) = 0.0145, 0.0057, 0.0034, 0.0023, 0.0014, 0.0009, 0.0010; \(\varepsilon\) = 9.98, 9.54, 9.88, 9.52, 9.84, 10.07, 11.91 (code units); \(k_{\max}\eta=2.0\). Match.", OK),
        ("Ghira (2022).pdf", 2, (0.08, 0.05, 0.95, 0.50), 0, "Table I: the compilation of earlier work (used for two cross-checks, not for data).",
         r"It lists the mixing layer of Tanahashi et al. (2001) at \(Re_\lambda=80\)&ndash;100, and repeats the swirl of Da Silva et al. (2011) as \(\langle U\rangle/u'=0.68\) and \(\langle U\rangle/u_\eta=9.0\) at \(Re_\lambda=111\) (see the tabs of those papers).", NOTE),
    ],
    "ghira2025": [
        ("Ghira (2025).pdf", 7, (0.08, 0.06, 0.92, 0.33), 0, "Table 2: the intense vorticity structures of all simulations.",
         r"\(Re_\lambda=54\) (128&sup3;): \(R_{ivs}/\eta=4.29\), \(U_{ivs}/u'=1.11\); \(Re_\lambda=54\) (256&sup3;, forcing at \(k_p=4\)): 4.23 and 1.13. The rows 91&ndash;239 are the simulations of the 2022 paper (not used twice). The swirl \(U_{ivs}/u'\) of the two \(Re_\lambda=54\) rows was not in the data before this review; it is added.", OK),
        ("Ghira (2025).pdf", 4, (0.05, 0.05, 0.95, 0.40), 0, r"Table 1: the simulations (\(\nu\), \(\varepsilon\)).",
         r"128&sup3;, \(Re_\lambda=54\): \(\nu=0.0370\), \(\varepsilon=10.01\); 256&sup3;, \(Re_\lambda=54\): \(\nu=0.0145\), \(\varepsilon=10.03\).", OK),
        (None, 0, None, 0, "", r"The paper gives no \(R_{ivs}/R_B\) for these runs.", G(r"R_ivs/R_B = 0.97", "the mean of the seven values of the 2022 paper (0.96&ndash;0.98), same code and method")),
    ],
    "jimenez1993": [
        ("Jimenez (1993).pdf", 15, (0.05, 0.03, 0.95, 0.60), 0, "The tracking algorithm (page 79 of the journal).",
         r"'the vorticity in the normal plane is averaged azimuthally, and the resulting radial distribution is fitted to a Gaussian. The local radius of the worm is defined as the 1/e radius of the Gaussian, and the circulation as that of the fitted distribution.' A worm is followed until its peak vorticity falls below \(\omega'\). So \(R\) is the Burgers radius and \(Re_\gamma\) the <i>total</i> circulation.", OK),
        ("Jimenez (1993).pdf", 16, (0.05, 0.60, 0.95, 0.78), 0, "Table 3: average worm characteristics.",
         r"\(Re_\lambda\) = 35.8, 62.8, 94.5, 168.1; \(R/\eta\) = 4.22, 4.16, 4.16, 3.85; \(Re_\gamma/Re_\lambda^{1/2}\) = 21.1, 17.0, 18.1, 16.5. The radii match the data file; the circulation column was not used before this review and is added (\(\Gamma/\nu\) = 126, 135, 176, 214).", OK),
    ],
    "aligolzadeh2023": [
        ("Aligolzadeh (2023).pdf", 4, (0.08, 0.05, 0.95, 0.55), 0, "The experiment (Sec. 2).",
         r"von K&aacute;rm&aacute;n flow in water, scanning PIV: \(R_\lambda=179\), \(\eta=0.926\) mm.", OK),
        ("Aligolzadeh (2023).pdf", 8, (0.08, 0.05, 0.95, 0.60), 0, "The mean radius (Sec. 3.1).",
         r"'the average radius of the structures found to be \(R=5.1\eta\)'.", OK),
        ("Aligolzadeh (2023).pdf", 16, (0.08, 0.52, 0.95, 0.80), 0, "The ratio to the Burgers radius (text after Fig. 11).",
         r"\(R_B=\sqrt{4\nu/\alpha_0}\); 'small differences in the mean \(R/R_B=0.95\) and 1.1' for 'the experiments and DNS'.",
         G("0.95 is the experiment and 1.1 the DNS", "the two numbers are given in the order 'experiments and DNS' of the same sentence; the paper does not label them")),
    ],
    "dasilva2011": [
        ("Da Silva (2011).pdf", 7, (0.05, 0.05, 0.97, 0.75), 0, "Section 3 (page 171 of the journal): what R, u0 and the circulation are.",
         r"\(R\) is the core radius, \(u_0\) the 'maximum tangential velocity', \(R_B=2(\nu/\sigma_0)^{1/2}\), \(\Gamma=\oint\vec u\cdot d\vec l=2\pi Ru_0\). 'For the present HIT and P. Jet we obtain \(\langle R\rangle/\eta=4.6\) for \(Re_\lambda=111\) and 120'; 'We have 0.68 and 0.76 for HIT and for P. Jet' (\(\langle u_0\rangle/u'\)); \(Re_\Gamma/Re_\lambda^{1/2}=28.8\) and 28.3.", OK),
        ("Da Silva (2011).pdf", 8, (0.10, 0.03, 0.92, 0.97), -90, "Table 1 (page 172 of the journal, printed sideways; turned here).",
         r"Present HIT: \(Re_\lambda=111\), \(\langle R\rangle/\eta=4.6\), \(\langle R/R_B\rangle=0.99\), \(\langle u_0\rangle/u'=0.68\), \(\langle u_0\rangle/u_\eta=9.0\), \(Re_\Gamma/Re_\lambda^{1/2}=28.8\). Plane jet: 120, 4.6, 0.97, 0.76, 7.15, 28.3.", OK),
        (None, 0, None, 0, "", r"<b>The paper is not consistent in the swirl.</b> With \(u'/u_\eta=(Re_\lambda/\sqrt{15})^{1/2}=5.35\) the printed \(u_0/u'=0.68\) gives \(u_0/u_\eta=3.6\) (4.2 for the jet), but the table prints 9.0 (7.15), and its circulation with \(\Gamma=2\pi Ru_0\) gives \(u_0/u_\eta=28.8\sqrt{111}/(2\pi\,4.6)=10.5\) (10.7). A factor 2.5. Ghira et al. (2022, Table I) repeat both numbers without comment.",
         G("the swirl of this source is shown as 3.7 and 4.3 (from u0/u') but left out of the fits", "the paper gives two values that differ by a factor 2.5 and nothing in it decides between them; the lower value was used before this review and was one of the supports of the Ghira &times; 0.6 correction")),
    ],
    "mouri2009": [
        ("Mouri (2009).pdf", 3, (0.08, 0.08, 0.95, 0.60), 0, "Table 1: the eleven experiments.",
         r"\(\eta\) [cm], \(u_K\) [m/s], \(Re_\lambda\): B1 0.0539, 0.0262, 332 ... D5 0.00955, 0.149, 1934. \(\nu=\eta u_K\) and \(\varepsilon=u_K^3/\eta\) follow from this table (B1: \(1.41\times10^{-5}\) m&sup2;/s, 0.033 W/kg): they match the values of the data file (taken earlier from the 2007 paper).", OK),
        ("Mouri (2009).pdf", 8, (0.08, 0.08, 0.95, 0.80), 0, "Table 2 and the text under it.",
         r"\(R_0/\eta\) = 8.45, 8.47, 8.59, 9.21, 8.93, 8.28, 8.56, 8.91, 9.12, 8.72, 8.81; \(V_0/u_K\) = 2.43, 2.39, 2.47, 2.73, 2.83, 2.88, 2.43, 2.56, 2.79, 2.91, 3.18; \(Re_0\) = 20.5 ... 28.0. All 33 numbers match. The text: 'While the \(R_0\) value is greater than the true mean radius, the \(V_0\) value is less than the true mean circulation velocity, because of the contribution from vortex tubes with \(|y_0|\gg R_0\) or \(\theta_0\gg0\). The \(R_0\) and \(V_0\) values are still proportional to the true mean values.'", OK),
        (None, 0, None, 0, "", r"<b>The correction is ours, not the paper's.</b> The paper says the values are biased and gives no factor, and none of the Mouri papers contains a chord-length calculation. The conversion of these values is our chord-length distribution work (chord_model.py; tested on the size distribution of Belin et al.; tab Corrections, steps 2&ndash;5). <b>Agreed use:</b> this paper, the average over the <i>whole</i> distribution of events, is the hot-wire source of the model, corrected; the threshold averages of Mouri et al. (2004, 2007) hold only a tail of the same distribution and are not used.", NOTE),
        (None, 0, None, 0, "", r"As used: \(r_{\max}/\eta=R_0/\eta\,/\,1.75\) and \(U_{\max}/U_\eta=3\,V_0/u_K\) (the table 'as used in the model' below lists every row).",
         G("radius &divide; 1.75 and swirl &times; 3", "our chord model and the comparison with the other sources: see the tab Corrections, where the review finds the swirl factor to be the weakest number of the data set (the all-tube data alone prefer about 1.8)")),
    ],
    "mouri2007": [
        ("Mouri (2007).pdf", 6, (0.03, 0.03, 0.97, 0.45), 0, "Table II: the intense vortical structures at the 0.1% and 1% thresholds.",
         r"0.1%: \(R_0/\eta\) = 5.21 ... 6.15, \(V_0/u_K\) = 8.67, 10.0, 11.3, 12.8, 14.0, 7.60, 8.37, 9.53, 10.6, 11.7, 12.8, \(Re_0\) = 45.2 ... 78.7. 1%: \(R_0/\eta\) = 6.50 ... 7.19, \(V_0/u_K\) = 6.11 ... 8.53. The 66 numbers of the data file match (columns 1&ndash;5 duct flows D1&ndash;D5, 6&ndash;11 boundary layers B1&ndash;B6).", OK),
        ("Mouri (2007).pdf", 5, (0.03, 0.03, 0.50, 0.62), 0, "Fig. 3: where the 0.1% and 1% thresholds sit on the pdf of the velocity increment.",
         r"The thresholds select the tail of the distribution of the spanwise velocity increment. These rows are left out of the fits (tab Corrections).", NOTE),
        (None, 0, None, 0, "", r"<b>Agreed use: not used in the model.</b> The 0.1% and 1% averages are two tails of the chord-length distribution of the same experiments as Mouri and Hori (2009): a high threshold keeps the near-central, near-normal crossings, so the radius is smaller and the swirl larger than the all-event average, by an amount that depends on the threshold. They cannot be corrected row by row, because each holds only part of the distribution; the 2009 paper, which averages the whole distribution, is used instead (corrected). The paper itself makes no chord correction: that work is ours (tab Corrections).",
         G("the difference between the threshold averages and the all-event average is mostly the chord distribution", "this is our reading; Mouri and Hori (2009) read it as a real difference (intense tubes scale with u', all tubes with u_K), and our own fit_threshold.py could not explain the swirl difference with chords alone (tab Corrections, step 5)")),
    ],
    "mouri2004": [
        ("Mouri (2004).pdf", 3, (0.03, 0.03, 0.97, 0.62), 0, "Table I: the six boundary-layer experiments and the tube parameters.",
         r"\(\nu\) = 0.144 ... 0.149 cm&sup2;/s; \(\varepsilon\) = 0.0316, 0.254, 2.03, 5.65, 14.6, 26.2 m&sup2;/s&sup3;; \(Re_\lambda\) = 295 ... 1258; \(R_0/\eta\) = 6.08, 6.04, 6.28, 7.14, 6.98, 7.37; \(V_0/u_K\) = 5.23 ... 8.37; \(Re_0\) = 32 ... 62. Match. Left out of the fits (tab Corrections).", OK),
        (None, 0, None, 0, "", r"<b>Agreed use: not used in the model.</b> This is the 1% threshold average of boundary-layer experiments: a tail of the chord-length distribution, as Mouri et al. (2007). The whole-distribution average of Mouri and Hori (2009) is used instead, corrected with our chord model (tab Corrections).", NOTE),
    ],
    "mouri2003": [
        ("Mouri (2003).pdf", 4, (0.05, 0.03, 0.97, 0.45), 0, "The radius (Sec. IV).",
         r"'\(r_0\approx(6\text{&ndash;}7)\,\eta\), regardless of the Reynolds number'; \(r_0=2.24(\nu/a)^{1/2}\) is the radius of maximum velocity (page 2). A range of \(Re_\lambda\) (105&ndash;329): shown, not fitted.", OK),
    ],
    "belin1996": [
        ("Belin (1996).pdf", 6, (0.05, 0.03, 0.97, 0.60), 0, "Eq. (6): what the radius R of this paper is.",
         r"\(\omega(r)=\omega_0\exp(-r^2/2R^2)\): \(R\) is the standard deviation of the Gaussian vorticity, so the 1/e radius is \(\sqrt2R\) and \(r_{\max}=1.1209\sqrt2\,R=1.585\,R\).", OK),
        ("Belin (1996).pdf", 8, (0.05, 0.03, 0.97, 0.55), 0, r"Fig. 5: the size distributions of the worms, \(R_\lambda\) = 151&ndash;718.",
         r"The distributions collapse when the radius is scaled with \(\eta\). The text (page 9): 'we find \(R=3.5\,\eta\) (to be compared, in the same units, to 2.8 obtained numerically)'. Used: \(3.5\times1.585=5.55\), a range of \(Re_\lambda\), shown and not fitted. This figure was digitised and fitted with the chord model (tab Corrections).", OK),
    ],
    "kida2002": [
        ("Kida (2002).pdf", 7, (0.03, 0.03, 0.97, 0.75), 0, "Tables 1 and 2 (images in the pdf: they could not be read from the text layer).",
         r"Table 1: \(\nu=2.50\times10^{-3}\), \(R_\lambda=83\), \(\epsilon=0.13\); \(\nu=6.25\times10^{-4}\), \(R_\lambda=170\), \(\epsilon=0.12\). Table 2: \(D/l_K\) = 10.4, 10.8; \(\Gamma/\nu\) = 110, 123; \(u_\theta/u_K\) = 3.1, 3.3; \(V_{core}/V\) = 0.35, 0.31; \(Q_{core}/Q\) = 0.60, 0.59; \(\epsilon_{core}/\epsilon\) = 0.31, 0.31. Match. \(D\) is the core diameter, \(u_\theta\) 'the mean azimuthal velocity at the core boundary'; the boundary is the inflection surface of the pressure.", OK),
        (None, 0, None, 0, "", r"The core boundary is not the radius of maximum swirl. For a Burgers vortex the inflection of the pressure lies at \(0.66\,r_{\max}\), where the swirl is 0.89 of its peak; the enstrophy inside is then 67% of the vortex's own (Kida et al.: 60% of the total).",
         G(r"r_max = D/2 and U_max = 1.175 u_theta", "the radius is taken as the boundary radius and the swirl as if the boundary were at 0.6 r_max: the two are not consistent with each other (a consistent Burgers reading gives r_max = D/1.32 = 7.9 and 8.2 and U_max = 1.12 u_theta); kept as before, because D of about 10 eta is what other authors compare with their diameters of maximum velocity")),
        (None, 0, None, 0, "", r"<b>Not used before this review:</b> \(\epsilon_{core}/\epsilon=0.31\) and \(V_{core}/V=0.35\), 0.31 are direct checks of the model's dissipation share and volume fraction (tab Data to model).", NOTE),
    ],
    "pirozzoli": [
        ("Pirozzoli (2009).pdf", 5, (0.05, 0.03, 0.97, 0.50), 0, "Pirozzoli (2009), Table 1: the average core radius.",
         r"DNS at \(Re_\lambda=250\) (512&sup3;, forced): \(r_0/\eta=5.12\); the other entries of the table are the experiments of Mouri et al. (2007). \(r_0\) is the radius of maximum velocity.", OK),
    ],
    "ishihara": [
        ("Ishihara (2011).pdf", 2, (0.05, 0.05, 0.97, 0.50), 0, "Ishihara, Hunt and Kaneda (2011): the abstract.",
         r"DNS at \(R_\lambda=1131\) (4096&sup3;): 'thin shear layers consisting of a cluster of strong vortex tubes with typical diameter of order \(10\eta\)'. An order of magnitude: used as \(r_{\max}=5\), shown and not weighted as a measurement.", OK),
    ],
    "sassa2005": [
        ("Sassa (2005).pdf", 1, (0.05, 0.05, 0.97, 0.65), 0, "The abstract.",
         r"Conditional sampling in fields with \(R_\lambda\) from 19 to 2391: 'the diameter of the elementary vortex was estimated to be about 10 times of the Kolmogorov scale being regardless of \(R_\lambda\). The maximum azimuthal velocity normalized by the Kolmogorov velocity increased in proportion to \(R_\lambda^{0.28}\)'.", OK),
        ("Sassa (2005).pdf", 8, (0.05, 0.03, 0.97, 0.97), 0, "Fig. 8: the dependence on the Reynolds number.",
         r"(b) \(w_{\max}/u_k\) of the paper's own data (filled symbols): about 2.1 and 2.8 at \(R_\lambda=19\), 4.0 at 190, 4.2 at 300, 3.6 at 586, 2.1 at 820 (shear flows), 6.5 at 2391.",
         G("the seven swirl values", "read by eye from the logarithmic plot, within about 15%; shown as an independent check of the trend, not fitted")),
    ],
    "das2006": [
        ("Das (2006).pdf", 1, (0.05, 0.10, 0.97, 0.55), 0, "Das et al. (2006): the abstract.",
         r"'diameter ... about \(10\eta\)&ndash;\(12\eta\) and average maximum azimuthal velocity is about 0.5&ndash;0.6 \(u'_{rms}\)'. No \(Re_\lambda\): shown, not fitted.", OK),
        ("Wang (2007).pdf", 1, (0.05, 0.10, 0.97, 0.60), 0, "Wang, Tanahashi and Miyauchi (2007): the abstract.",
         r"'The most expected value of maximum azimuthal velocity of the eddy is 2.0 times Kolmogorov velocity, and decreases to \(1.2u_k\), which is an asymptotic value in the fully-developed state'; diameter 8 times \(\eta\).",
         G("swirl 1.6 for this row", "the mean of the two values of the abstract; the fully developed value is 1.2")),
        (None, 0, None, 0, "", r"Miyauchi et al. (2006): there is no pdf of this paper in the folder.",
         G("D = 10 and 8.5 eta, swirl 2.0 and 1.7 u_K", "taken from the abstract online in an earlier session; not checked on a page")),
    ],
    "tanahashi2001": [
        ("Tanahashi (2001).pdf", 4, (0.10, 0.14, 0.90, 0.37), 0, "Fig. 1(b): the Reynolds number of the mixing layer.",
         r"\(Re_\lambda\) against time for \(Re_{\omega,0}\) = 500, 700, 900. For 500 (the case of Fig. 7) it is 75&ndash;85 over \(t=70\)&ndash;130. The text (page 4 of the journal): 'The highest \(Re_\lambda\) is about 100 for the case of \(Re_{\omega,0}=900\)'. The data file had 200 (assumed): corrected to 80 in this review.",
         G(r"Re_lambda = 80", "read from the figure to about &plusmn;8; Ghira et al. (2022, Table I) list this flow at 80&ndash;100")),
    ],
}


def evidence_steps(tab):
    """Add the steps of the tab's paper: the cut-out, what is read from it, and whether it was checked."""
    for pdf, page, box, rotate, caption, read, status in EVIDENCE.get(tab.id, []):
        if pdf:
            image = pdfcrop(pdf, page, box, 2.4)
            if rotate:
                image = image.rotate(rotate, expand=True)
            tab.img(image, "%s (%s, page %d of the pdf)" % (caption, pdf[:-4], page))
        if status == OK:
            tab.p("Read from the page: " + read + " <span class=\"okk\">[checked on the page image]</span>")
        elif status == NOTE:
            tab.p(read)
        else:
            tab.p(read + " " + tab.guess(status[1], status[2]))


def corrections_tab(book):
    tab = book.tab("corrections", "Corrections")
    with open(os.path.join(LIT, "fittingtool", "data", "corrections.json"), encoding="utf-8") as f:
        data = json.load(f)
    c = data["corrections"]
    tab.h("1. What is changed between the papers and the model, in one table")
    tab.p("Every number of the model starts as a number printed in a paper (the tabs of the papers). Four kinds of change are made before the fits. The first is a conversion of definition and is exact; the other three are judgements, and each is listed here with its rationale and with what the review of 2026-11-12 found.")
    tab.table(["change", "applies to", "value", "kind"],
              [[r"definition of the radius: the radius of maximum swirl of a Burgers vortex, \(r_{\max}=1.1209\,R_B\), from the 1/e radius of the vorticity; \(r_{\max}=1.585\,R\) from a Gaussian standard deviation; \(r_{\max}=D/2\) from a diameter between the velocity maxima", "all sources", "exact for a Burgers vortex", "conversion"],
               [r"swirl at \(R_{ivs}\) to the peak swirl", "Ghira et al. (2022, 2025)", "factor 1.01&ndash;1.02", "conversion"],
               ["radius divided", "Mouri and Hori (2009)", "&divide; %.2f" % c["Mouri09"]["r_divisor"], "<span class=\"guess\">judgement</span>"],
               ["swirl multiplied", "Mouri and Hori (2009)", "&times; %.1f" % c["Mouri09"]["u_factor"], "<span class=\"guess\">judgement</span>"],
               ["swirl multiplied", "Ghira et al. (2022, 2025)", "&times; %.1f" % c["Ghira22"]["u_factor"], "<span class=\"guess\">judgement</span>"],
               ["left out of the fits", "Mouri et al. (2004, 2007): threshold averages", "all rows", "<span class=\"guess\">judgement</span>"],
               ["left out of the fits", "Da Silva et al. (2011): swirl; Sassa and Makita (2005): swirl", "swirl only", "review 2026-11-12"],
               ["Reynolds number corrected", "Tanahashi et al. (2001)", r"\(Re_\lambda\) 200 &rarr; 80", "review 2026-11-12"]],
              "The changes. The first two rows are definitions; the rest are choices.")
    tab.h("2. The hot wire reads a chord: the model behind the Mouri and Hori corrections")
    tab.p(r"A hot wire records the velocity along a straight line through the flow (frozen turbulence). A vortex tube is rarely crossed through its axis at a right angle: the path passes at a distance \(b\) from the axis (the impact parameter) and the axis is tilted by an angle \(\alpha\). The record then shows a wider and weaker swirl than the tube has. chord_model.py computes what a straight path reads from a Burgers tube for a random offset and orientation, and which events survive an amplitude cut \(f\) (an event is kept when its peak is at least \(f\) times the peak of a central, normal crossing).")
    tab.img(pdfcrop("Mouri (2009).pdf", 5, (0.08, 0.05, 0.95, 0.75), 2.2), "Mouri and Hori (2009), page 5: the geometry of a tube crossing the probe, with offset and inclination, and the mean profiles of Burgers vortices with random positions and inclinations.")
    tab.img(pdfcrop("Mouri (2009).pdf", 8, (0.08, 0.62, 0.95, 0.78), 2.4), "Mouri and Hori (2009), under Table 2: the authors' own statement that the radius is too large and the swirl too small, without a factor.")
    tab.img("chord_pdf.png", "chord_model.py: the distribution of the measured radius over the true radius for random crossings, for several tilt limits and amplitude cuts.")
    tab.h("3. The test of the chord model: the size distribution of Belin et al. (1996)")
    tab.p(r"Belin et al. measured the distribution of the size of single events in helium (\(R_\lambda\) = 151&ndash;718). Their Fig. 5 was digitised (digitise_belin.py) and fitted (fit_chord.py) with: a lognormal distribution of true radii, seen through the chord distribution of the model. The broad measured distribution is reproduced by a narrow distribution of true radii crossed at random: this is the evidence that a chord distribution, not a wide range of tube sizes, makes most of the width seen by a probe.")
    tab.img(pdfcrop("Belin (1996).pdf", 8, (0.05, 0.03, 0.97, 0.55), 2.2), "Belin et al. (1996), Fig. 5: the measured size distributions.")
    tab.img("belin_overlay.png", "digitise_belin.py: the digitised distribution (curve) on the original figure.")
    tab.img("belin_fit.png", "fit_chord.py: the fit of the chord model to the digitised distribution.")
    tab.p(tab.guess("the tubes of Belin et al. have one narrow distribution of true radii", "the fit is good, but a fit of a broad true distribution without chords was also possible within the scatter; the DNS pdfs (Tanahashi, Pirozzoli) show that true radii do have a broad second family"))
    tab.h("4. The radius of Mouri and Hori (2009): &divide; 1.75")
    tab.p(r"Mouri and Hori average the profile of <i>all</i> events and fit a Burgers profile to the mean: \(R_0=8.3\)&ndash;\(9.2\,\eta\) (mean 8.8). The chord model gives the ratio of such an all-event radius to the true radius as 1.7&ndash;1.85 (tilt limit 20&ndash;70&deg;, true radius about 5). 8.8/1.75 = 5.0, the radius of the other sources. Rationale: the chord model and the agreement with the DNS radii.")
    tab.img("chordcorr_fit.png", "fit_chordcorr.py: the fit with the hot-wire radii corrected.")
    tab.p(r"The radius pdfs of all tubes (tabs of Tanahashi et al. and Pirozzoli) are each the sum of two lognormal functions. The first is narrow (width 0.29&ndash;0.35) and holds 53&ndash;71% of the tubes: median 5.2, 4.9, 4.3 \(\eta\) and mean 5.5, 5.3, 4.6 \(\eta\) (Tanahashi 2001, Tanahashi 2004, Pirozzoli 2012). This first function is the \(r_{\max}/\eta\) of the model, 5. The second is broad (median 8.5&ndash;16.8 \(\eta\)) and raises the mean of the whole pdf to 7.2&ndash;8.2.")
    tab.p(tab.guess("the probe average of Mouri and Hori follows the first lognormal function (radius about 5 eta)", "the divisor 1.75 brings 8.8 to 5.0, the mean of the first function; if the probe average also took in the second, broad function (whole-pdf mean 7&ndash;8 eta), the chord divisor would be nearer 1.2"))
    tab.h("5. The swirl of Mouri and Hori (2009): &times; 3, and what the review finds")
    tab.p(r"Rationale as decided: with Ghira et al. &times; 0.6, one power law passes through Ghira, Da Silva, Kida and Mouri and Hori; the chord model gives 2&ndash;3.5 depending on the tilt limit; the threshold pairs of Mouri et al. (2007) give a lower bound of 3.1&ndash;4.4 if the difference between the 0.1% average and the all-tube average is only a chord effect.")
    tab.img("fit_threshold.png", "fit_threshold.py: the threshold pairs of Mouri et al. (2007) against the chord model.")
    tab.p(r"<b>Review.</b> (i) fit_threshold.py itself found that the chord model explains the radius of the all-tube average but not its swirl: the swirl needs a factor 4.5&ndash;5.9 that grows with \(Re_\lambda\), outside the range of the model; fit_smoothing.py added the length of the wire to close the gap. (ii) Mouri and Hori state in their abstract that the swirl of all tubes scales with \(u_K\) 'in contrast to the case of intense vortex tubes alone where the circulation velocity scales with the rms velocity fluctuation'. (iii) Fitting the all-tube sources alone (Kida et al. and Mouri and Hori with a free factor; modelselect.py) gives a factor <b>1.84</b> and \(U_{\max}/U_\eta=2.0\,Re_\lambda^{0.13}\) with an rms of 1.3%; a factor 3 gives 3.9% and an exponent 0.33 that neither source shows on its own (0.15 within Mouri and Hori, 0.09 within Kida et al.). " +
          tab.guess("swirl &times; 3", "it rests on joining the all-tube and the intense-tube data into one law; on the all-tube data alone the factor is 1.8&ndash;2.0, the low end of the chord model"))
    tab.h("6. The swirl of Ghira et al.: &times; 0.6, and what the review finds")
    tab.p(r"Rationale as decided: the listed swirl (6&ndash;10 \(U_\eta\), 1.0&ndash;1.25 \(u'\)) lies above Da Silva et al. (3.7&ndash;4.3) and Kida et al. (3.6&ndash;3.9) at the same \(Re_\lambda\); a constant 0.58 puts it on their curve.")
    tab.p(r"<b>Review.</b> (i) The Da Silva values 3.7 and 4.3 are not safe: the same table prints 9.0 and 7.15 (tab Da Silva), which is <i>above</i> Ghira. (ii) Kida et al. measure all low-pressure vortices, Ghira et al. the 1% most intense: they need not have the same swirl. (iii) Without any factor, the intense-tube data agree with each other: Ghira et al. (DNS, \(Re_\lambda\) 54&ndash;399) and the 0.1% threshold averages of Mouri et al. (2007, hot wire, 332&ndash;1934) follow one law, \(U_{\max}/U_\eta=1.29\,Re_\lambda^{0.32}\), with an rms of 12% (modelselect.py). " +
          tab.guess("swirl &times; 0.6 for Ghira et al.", "it is needed only if intense tubes and all tubes are one population; the two other intense-tube sources (Mouri et al. 2007; Da Silva et al. as printed) support the listed values"))
    tab.h("7. Left out: the threshold averages of Mouri et al. (2004, 2007)")
    tab.p(data["excluded"]["Mouri07"] + " " + data["excluded"]["Mouri04"])
    tab.p(r"<b>Review.</b> They are kept out of the single-population fit (tab Data to model, model I). In the two-population reading (model II) the 0.1% rows are the hot-wire measure of the intense tubes and are used.")
    return tab


def model_tab(book):
    tab = book.tab("model", "Data to model")
    sys.path.insert(0, os.path.join(LIT, "fittingtool"))
    import fitdata
    import modelselect
    with open(os.path.join(LIT, "fittingtool", "results", "modelselect.json"), encoding="utf-8") as f:
        res = json.load(f)
    rows = modelselect.load({})
    obs = fitdata.observations(rows)
    tab.h("1. Which numbers enter the fits")
    tab.p(r"The fits use the rows of the summary table that have one \(Re_\lambda\), after the corrections (tab Corrections). Each source has the same total weight in each quantity, however many rows it has.")
    lines = []
    for kind, label in (("r", r"\(r_{\max}/\eta\)"), ("U", r"\(U_{\max}/U_\eta\)")):
        o = obs[kind]
        by = {}
        for s, v, re in zip(o["src"], o["val"], o["re"]):
            by.setdefault(s, []).append((re, v))
        for s, pts in sorted(by.items()):
            lines.append([label, s, str(len(pts)), "%g&ndash;%g" % (min(p[0] for p in pts), max(p[0] for p in pts)), "%.2f&ndash;%.2f" % (min(p[1] for p in pts), max(p[1] for p in pts))])
    tab.table(["quantity", "source", "rows", r"\(Re_\lambda\)", "values (corrected)"], lines, "The data of the fits: %d radius points and %d swirl points from %d source-quantity groups." % (len(obs["r"]["re"]), len(obs["U"]["re"]), len(lines)))
    tab.h("2. The selection of the model (model I: one population, the corrections as decided)")
    tab.p(r"Every candidate is fitted to the same data by least squares of the log residuals. Three criteria: AICc and BIC (information criteria; a difference under 2 is no evidence, over 10 is decisive), counted with one unit a source-quantity group, and LOSO: each source in turn is left out, the model fitted to the rest predicts it, and the rms of those errors is the score. LOSO penalises a parameter that follows the noise of one source, so the penalty on complexity comes from the data. (The earlier rule was: the fewest parameters within 25% of the best rms.)")
    models = sorted(res["scenarios"][0]["models"], key=lambda m: m["loso"])
    tab.table(["model", "parameters", "rms %", "LOSO %", "&Delta;AICc", "&Delta;BIC", "what it is"],
              [[m["key"], str(m["k"]), "%.1f" % m["rms"], "%.1f" % m["loso"], "%.1f" % m["d_aicc"], "%.1f" % m["d_bic"], m["name"]] for m in models],
              "Scenario: the corrections as decided. Sorted by LOSO.")
    d6 = next(m for m in models if m["key"] == "D6")
    l1 = next(m for m in models if m["key"] == "L1")
    tab.p(r"<b>Reading.</b> L1 (radius 5, swirl \(a+b\ln Re_\lambda\), two parameters) predicts left-out sources best (%.1f%%); D6 (radius 5, swirl \(c\,Re_\lambda^{1/3}\), one parameter) follows at %.1f%%, and the information criteria cannot separate them (&Delta;AICc %.1f). No model with three or four parameters does better out of sample than these two: the extra parameters fit noise. With the penalty on complexity the one-parameter model stays: \(U_{\max}/U_\eta=%.3f\,Re_\lambda^{1/3}\), \(r_{\max}=5\,\eta\). L1 is \(U_{\max}/U_\eta=%.2f+%.2f\ln Re_\lambda\); it goes negative below \(Re_\lambda\approx13\), which a power law cannot." % (
        l1["loso"], d6["loso"], d6["d_aicc"], d6["params"][0], l1["params"][0], l1["params"][1]))
    tab.h("3. How the choice depends on the corrections")
    rowsx = []
    for sc in res["scenarios"]:
        ms = sorted(sc["models"], key=lambda m: m["loso"])
        d = next(m for m in ms if m["key"] == "D6")
        rowsx.append([sc["label"], "%s (%.1f%%)" % (ms[0]["key"], ms[0]["loso"]), "%.1f%%" % d["loso"], "%.3f" % d["params"][0]])
    tab.table(["scenario", "best by LOSO", "D6 LOSO", "D6 coefficient c"], rowsx, "The same comparison under other corrections.")
    tab.p(r"<b>Reading.</b> The radius divisor hardly matters (1.6 to 1.9). The swirl factors decide everything: with Ghira as listed no single law fits (errors of 21&ndash;23%), and with Mouri and Hori &times; 2 the errors grow to 16%. Model I stands or falls with the pair (&times; 3, &times; 0.6).")
    tab.h("4. Model II: two populations, no swirl correction")
    tp = res["two_population"]
    tab.p(r"The swirl as calculated from the papers splits into two families. <b>Intense tubes</b> (the 1%% of highest vorticity in DNS: Ghira et al.; the 0.1%% threshold of the hot wire: Mouri et al. 2007): \(U_{\max}/U_\eta=%.2f\,Re_\lambda^{%.2f}\), rms %.0f%%, %d points, no correction. <b>All tubes</b> (Kida et al.; Mouri and Hori with one fitted chord factor): \(U_{\max}/U_\eta=%.2f\,Re_\lambda^{%.2f}\) with a chord factor %.2f, rms %.1f%%. The exponent inside Mouri and Hori alone is %.2f and inside Kida et al. alone %.2f: the all-tube swirl grows slowly, as Mouri and Hori say (it scales with \(u_K\))." % (
        tp["intense"]["c"], tp["intense"]["s"], tp["intense"]["rms_power"], tp["intense"]["n"], tp["all_free"]["a"], tp["all_free"]["s"], tp["all_free"]["f"], tp["all_free"]["rms"], tp["slope_Mouri09"], tp["slope_Kida02"]))
    tab.table(["chord factor of Mouri and Hori (swirl)", "fitted law of all tubes", "rms %"],
              [["%.1f%s" % (tp[k]["f"], " (free fit)" if k == "all_free" else ""), r"\(%.2f\,Re_\lambda^{%.3f}\)" % (tp[k]["a"], tp[k]["s"]), "%.1f" % tp[k]["rms"]] for k in ("all_f1.0", "all_f1.5", "all_free", "all_f2.0", "all_f2.5", "all_f3.0")],
              "The all-tube swirl against the chord factor: the factor 3 of model I is not preferred by these data.")
    tab.h("5. Independent checks (data not used in any fit)")
    tab.table(["check", "measured", "model I (D6)", "model II (all tubes)"],
              [[r"volume fraction of the tubes, Kida et al., \(R_\lambda=83\)", "0.35", "0.36", "0.35"],
               [r"volume fraction of the tubes, Kida et al., \(R_\lambda=170\)", "0.31", "0.22", "0.29"],
               [r"swirl exponent, Sassa and Makita (conditional sampling, \(R_\lambda\) 19&ndash;2391)", "0.28", "1/3", "0.13 (all), 0.32 (intense)"],
               [r"swirl of all tubes at \(Re_\lambda\approx80\), Tanahashi et al. (2001) pdf, mean", "3.7", "3.3", "3.6"],
               [r"swirl of all tubes at \(Re_\lambda\approx99\), Pirozzoli (2012) pdf, mean", "2.5", "3.6", "3.7"]],
              r"The volume fraction of the model is \(V_f=(1-75.8/\beta^4)\,\beta^2/(4.91\,U^2)\) with \(\beta=5\).")
    tab.p(r"Kida et al. also report that the vortex cores hold 31% of the dissipation. A Burgers vortex has only 10% of its swirl dissipation inside \(r_{\max}\) (37% inside \(1.5\,r_{\max}\), 61% inside \(2\,r_{\max}\)): most of the dissipation of a tube is in the annulus around the core, as Kida et al. describe. The model's vortex share of the dissipation (88% at \(\beta=5\)) is the whole swirl field, so the two numbers are not in conflict, but they are not a quantitative check either.")
    return tab
