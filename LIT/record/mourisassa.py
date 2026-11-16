"""mourisassa.py  The extra sections of the tabs of Mouri et al. (2004, 2007), Mouri and Hori (2009) and Sassa and Makita (2005) of the recording book: their method applied to model tubes (analysis/chord_mouri.py), against the numbers of the paper.
Numbers: analysis/chord_mouri_dns.json (tubes of the DNS), chord_mouri_belinfit.json (the tubes found from Belin's records), chord_mouri_lowk.json (the all-tube method at low thresholds); figure: chord_mouri.png (chord_mouri_plot.py).
Sections are added at the end of the tab (the rule of the book: a line keeps its number).

Versions  M01 m01.v01 (2026-11-13): first version.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ANALYSIS = os.path.join(os.path.dirname(HERE), "analysis")

__all__ = ["extra", "KEYS"]
KEYS = ("Mouri04", "Mouri07", "Mouri09", "Sassa05")


def load(name):
    with open(os.path.join(ANALYSIS, name), encoding="utf-8") as f:
        return json.load(f)


COMMON = (r"The model of the tubes is the wire-and-tube model of the Belin tab, with the sensed quantity changed: a crossed wire gives the <em>transverse</em> velocity (the spanwise \(v\) of Mouri, the vertical \(w\) of Sassa), which is linear in the swirl and needs no incidence angle. "
          r"Straight Burgers tubes with isotropic axes and uniform offsets are crossed along the path of the mean flow, the signal is smoothed by the probe (a boxcar of 1 mm for Mouri, about \(\eta\) for Sassa), the thresholds are in units of the rms increment \(\sqrt{2/15}\,(U_\eta/\eta)\,\delta x\) of the dissipative range, and a tube is weighted by the distance within which it can be detected. There is no background turbulence in the model "
          r"(script chord_mouri.py).")


def extra(tab, key):
    dns, bel = load("chord_mouri_dns.json"), load("chord_mouri_belinfit.json")
    if key in ("Mouri07", "Mouri04"):
        tab.h("7. The method applied to the model tubes")
        tab.p(COMMON)
        tab.p(r"Method of the paper: the increment \(v(x+\delta x_s/2)-v(x-\delta x_s/2)\) over the sampling interval \(\delta x_s\); the events above the threshold that holds 0.1% or 1% of all increments (the threshold levels of Table II of Mouri et al. 2007: 6.0&ndash;6.7 and 3.5&ndash;3.7 standard deviations); "
              r"the signals are aligned on the increment, given the same sign, averaged, and the mean profile is fitted around its peaks by the Burgers vortex for \(x_0=y_0=\theta_0=0\) to give \(R_0\) and \(V_0\).")
        head = [r"\(Re_\lambda\)", "class", r"\(R_0/\eta\) paper", r"\(R_0/\eta\) model (DNS-like tubes)", r"\(V_0/u_K\) paper", r"\(V_0/u_K\) model", r"true \(r_{\max}\) of the events", r"true \(U_{\max}/U_\eta\) of the events", r"\(V_0/u_K\), Belin-fit tubes"]
        rows = []
        for m, b in zip(dns["mouri"], bel["mouri"]):
            for cls, kr, kv in (("0.1%", "r01", "v01"), ("1%", "r1", "v1")):
                q, qb = m[cls], b[cls]
                rows.append([str(m["Re_lambda"]), cls, "%.2f" % m["paper"][kr], "%.2f" % q["R0"], "%.2f" % m["paper"][kv], "%.2f" % q["V0"], "%.2f" % q["true_r"], "%.1f" % q["true_U"], "%.1f" % qb["V0"]])
        tab.table(head, rows, "Mouri et al. (2007), Table II (paper) against the model at the four Reynolds numbers of the model runs (12000 tubes each). The model with DNS-like tubes (r_max 5.2 eta, U_max = 0.769 Re^(1/3) U_eta) reproduces the paper; the tubes found from Belin's records read 1.5 to 2 times too high.")
        tab.img("chord_mouri.png", "The three methods on model tubes (chord_mouri_plot.py): blue, tubes of the DNS; red dashed, the tubes found from Belin's records; black open symbols, the papers.")
        tab.p("&bull; A high threshold keeps near-axis crossings and strong tubes: the true radius of the events falls and the true swirl rises with the threshold; the radius read is 1.2&ndash;1.3 times the true radius of the events and the swirl read 0.7&ndash;0.8 of it.<br>"
              "&bull; The paper reads a radius of 5&ndash;7 eta and a swirl of 6&ndash;14 u_K: these are the DNS tubes seen through the threshold, so the rows of the 0.1% and 1% classes are close to the true tubes " + tab.guess("the 0.1% and 1% classes are not corrected", "the model reads 1.2 times the radius and 0.7 of the swirl of the events at these thresholds, inside the scatter of the sources; they are tails of the sample of Mouri and Hori (2009) and stay out of the fits"))
        if key == "Mouri04":
            tab.p("Mouri et al. (2004) used the 1% threshold on the same kind of data (Re_lambda 295&ndash;1258, radius 6.0&ndash;7.4 eta in the table of the page); the model radius of the 1% class at 332&ndash;1934 is 5.7&ndash;8.5 eta.")
    elif key == "Mouri09":
        low = load("chord_mouri_lowk.json")
        tab.h("7. The all-tube method applied to the model tubes")
        tab.p(COMMON)
        tab.p(r"Method of the paper: the increment over \(\delta x_0\approx6\eta\), smoothed with the Gaussian window \(e^{-x^2/2\delta x_0^2}\); the positions of all its local maxima and minima are taken as tube positions, the unsmoothed signals are averaged around them and the mean profile is fitted around its peaks. "
              r"In the model the background is absent, so the lowest threshold of the increment (in standard deviations of the increment over \(6\eta\)) takes its place; thresholds of 0.25, 0.5 and 1 were tried (section 8: 0.1 to 1 in steps of 0.1).")
        head = [r"\(Re_\lambda\)", "threshold", r"\(R_0/\eta\) paper", "model", r"\(V_0/u_K\) paper", "model", r"true \(r_{\max}\)", r"true \(U_{\max}/U_\eta\)", "radius factor (read / true)", "swirl factor (true / read)"]
        rows = []
        for q in low:
            for k in ("k=0.25", "k=0.5", "k=1"):
                v = q[k]
                rows.append([str(q["Re_lambda"]), k[2:], "%.2f" % q["paper"]["r_all"], "%.2f" % v["R0"], "%.2f" % q["paper"]["v_all"], "%.2f" % v["V0"], "%.2f" % v["true_r"], "%.1f" % v["true_U"], "%.2f" % (v["R0"] / v["true_r"]), "%.2f" % (v["true_U"] / v["V0"])])
        tab.table(head, rows, "Mouri and Hori (2009), Table 2 (paper) against the model with DNS-like tubes at three thresholds (6000 tubes each).")
        tab.img("chord_mouri.png", "The three methods on model tubes (chord_mouri_plot.py; the all-tube triangles are at the threshold of 2 standard deviations; the paper's average needs 0.25&ndash;0.5).")
        tab.p("&bull; The paper's all-tube average (R0 8.3&ndash;9.2 eta, V0 2.4&ndash;3.2 u_K) is reproduced at a threshold of 0.25&ndash;0.5 standard deviations by tubes of the DNS (5.4 eta, 6&ndash;11 U_eta).<br>"
              "&bull; The factors that the model gives are a radius factor of 1.5&ndash;1.9 and a swirl factor of 2.4&ndash;3.8 (threshold 0.25&ndash;0.5): the corrections of the page, 1.75 and 3, are inside these ranges and rest on the geometry of a one-dimensional cut.<br>"
              "&bull; The threshold of the paper is not given: it is the one free quantity " + tab.guess("the all-tube threshold is 0.25-0.5 standard deviations", "the paper says only that the extrema are above the background fluctuation; the model has no background"))
        scan, classes = load("belin_correctors_kscan.json"), load("belin_correctors.json")
        tab.h("8. The correctors of the all-tube method as a function of the threshold k")
        tab.p("The multipliers m_r and m_U (corrected value = m x value read) of the all-tube method on the tubes of the fit to Belin et al. (analysis/belin_correctors_kscan.py), for the threshold k from 0.1 to 1 standard deviations of the increment over 6 eta, in steps of 0.1, at each Reynolds number of the corrector tables. "
              "r_obs and U_obs are what the method reads from the model tubes (r_max/eta and U_max/U_eta); the true means of the model tubes are given in the caption. For comparison the multipliers of the 1% and 0.1% classes of Mouri et al. (2007), whose thresholds are fixed by the class (about 3.6 and 6.4 standard deviations of the increment over the sampling interval), are repeated in every row: they do not depend on k. "
              "The 1% and 0.1% multipliers are those of the table of the class at the nearest Reynolds number (255 and 659 for 250 and 650). Fig. 1b of the paper uses k = 0.33, between 0.3 and 0.4 of this table; the multipliers of the main tables (belin_correctors_all.py) differ from these by Monte Carlo noise (under 1%).")
        head = ["k", "r_max/&eta; obs", "M_r", "M_r 1%", "M_r 0.1%", "U_max/U_&eta; obs", "M_U", "M_U 1%", "M_U 0.1%"]
        for row, cls in zip(scan, classes):                                           # the same eight Reynolds numbers (the class tables have 255 and 659 where the scan has 250 and 650)
            m1r, m01r = cls["r"]["Mouri 1%"]["shape"], cls["r"]["Mouri 0.1%"]["shape"]
            m1u, m01u = cls["U"]["Mouri 1%"]["shape"], cls["U"]["Mouri 0.1%"]["shape"]
            body = [["%s" % k, "%.2f" % v["r_obs"], "%.3f" % v["m_r"], "%.3f" % m1r, "%.3f" % m01r, "%.2f" % v["U_obs"], "%.2f" % v["m_U"], "%.2f" % m1u, "%.2f" % m01u] for k, v in row["k"].items()]
            tab.table(head, body, "Re<sub>&lambda;</sub> = %d: true r_max/&eta; = %.2f and U_max/U_&eta; = %.1f of the model tubes." % (round(row["Re_lambda"]), row["true_r"], row["true_U"]))
    elif key == "Sassa05":
        tab.h("7. The method applied to the model tubes")
        tab.p(COMMON)
        tab.p(r"Method of the paper: events where \(dw/dt\ge C\,\mathrm{rms}(dw/dt)\) (\(C=2.5\); their Fig. 2 scans 1&ndash;3.5), 1000 points averaged around each event, the diameter and the maximum velocity read from the two peaks of the mean trace. The model uses a probe of one \(\eta\) (their resolution, 0.8 mm, is about \(\eta\)) and the Reynolds numbers of their Table 1.")
        head = [r"\(Re_\lambda\)", "C", r"diameter \(D/\eta\), model", r"peak \(V/u_K\), model", r"peak \(V/u_K\) paper (read by eye from Fig. 8)", r"true \(r_{\max}\)", r"true \(U_{\max}/U_\eta\)", r"peak \(V/u_K\), Belin-fit tubes"]
        paper = {19: "2.8", 300: "4.2", 820: "2.1", 2391: "6.5"}
        rows = []
        for s, b in zip(dns["sassa"], bel["sassa"]):
            for C in ("C=1.5", "C=2.5", "C=3.5"):
                if C not in s or C not in b:                                              # a threshold with fewer than 100 events is not in the json
                    continue
                q = s[C]
                rows.append([str(s["Re_lambda"]), C[2:], "%.0f" % (2 * q["r_peak"]), "%.2f" % q["v_peak"], paper[s["Re_lambda"]] if C == "C=2.5" else "", "%.2f" % q["true_r"], "%.1f" % q["true_U"], "%.2f" % b[C]["v_peak"]])
        tab.table(head, rows, "Sassa and Makita (2005): the model with DNS-like tubes. The paper's diameter is about 10 eta at C = 2.5, whatever the Reynolds number.")
        tab.img("chord_mouri.png", "The three methods on model tubes (right panel: the diameter of the mean trace, Sassa and Makita).")
        tab.p("&bull; At C = 2.5 the model gives a maximum velocity of 2.8, 4.6 and 7.0 u_K at Re_lambda 19, 300 and 2391, the paper 2.8, 4.2 and 6.5; the shear flow (Re_lambda 820) is lower in the paper (2.1) than in the model (5.6).<br>"
              "&bull; The diameter is 10&ndash;14 eta in the model (true r_max about 5 eta) against about 10 eta in the paper: the row of Sassa and Makita is close to the true tube.<br>"
              "&bull; Only the mean diameter and the Reynolds-number trend of the paper are used; the size pdf of their Fig. 3 (the diameter of the vortices detected by dw/dt, up to 80 eta) has not been modelled.")
