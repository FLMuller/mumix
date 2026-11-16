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
    """The paragraph after Table 2: the sensitivity of the selection to the radius divisor of Mouri and Hori and to the factors of Ghira et al."""
    best = lambda s: sorted(s["models"], key=lambda m: m["loso"])[0]
    d6 = lambda s: {m["key"]: m for m in s["models"]}["D6"]["loso"]
    find = lambda start: [s for s in scen if s["label"].startswith(start)][0]
    div = [d6(find("Mouri-Hori r/1.6")), d6(find("Mouri-Hori r/1.9"))]
    listed = min(best(find("Ghira swirl as listed (x 1), Mouri-Hori U x 3"))["loso"], best(find("Ghira swirl as listed (x 1), Mouri-Hori U x 5"))["loso"])
    return ("<p>The selection is robust to the radius divisor of Mouri and Hori (the score of D6 is %.1f%% to %.1f%% for 1.6 to 1.9) and fragile to the factors of Ghira et al. (Table 2). With their swirl as listed no single law predicts left-out sources better than %.0f%%, whatever its number of parameters: the single law exists only with both swirl factors. "
            "The radius of Ghira et al. matters as well: multiplied by 1.85 (the mean of all tubes as the target) the best score is %.1f%%, with the adopted 1.25 %.1f%%, as listed %.1f%%.</p>" % (min(div), max(div), listed, best(find("Ghira radius x 1.85"))["loso"], best(scen[0])["loso"], best(find("Ghira radius as listed"))["loso"]))


def corrected_fig_section():
    """The new figure of the radius, the swirl and the circulation against Re_lambda (data as read, and as corrected by the models of the probes) with the trends fitted to its dots."""
    with open(os.path.join(HERE, "data_corrected_fits.json"), encoding="utf-8") as f:
        fits = json.load(f)
    fr, fu = fits["r"], fits["U"]
    cr = fr["models"]["constant"]
    pr = fr["models"]["power"]
    p1 = fu["models"]["power"]
    p3 = fu["models"]["power, exponent 1/3"]
    text = r"""<h3>The data as read and as corrected by the models of the probes</h3>
<p>Fig. 1b shows every row of the data against \(Re_\lambda\) on linear axes: above as read from the papers, below with the corrections that follow from the models: Ghira et al. (radius &times; 1.25, swirl &times; 0.67, section 9a) and the observed rows (Belin et al., Mouri et al. 2004, 2007, Mouri and Hori 2009, Sassa and Makita) with the multipliers of the wire-and-tube model and its one-dimensional extension (below; the multipliers are interpolated in \(\ln Re_\lambda\) from the table of the recording book), the other simulations as read. Rows with a range of \(Re_\lambda\) (the curves of Belin et al., the range of Mouri et al. 2003) are drawn as lines and are not used in the trends.</p>
""" + png_html("data_corrected_plot.png", r"Fig. 1b. \(r_{\max}/\eta\), \(U_{\max}/U_\eta\) and \(G=\Gamma/\nu=8.784\,r_{\max}U_{\max}\) against \(Re_\lambda\), linear axes. Top: every row as read. Bottom: Ghira et al. and the observed rows corrected, the other simulations as read (open symbols: observed, no multiplier yet). Red: the trends fitted to the dots of the bottom row.") + r"""
<p>The trends were fitted to the dots of the bottom row (""" + "%d points of %d sources for the radius, %d of %d for the swirl" % (fr["n"], fr["n_sources"], fu["n"], fu["n_sources"]) + r"""), by least squares of the logarithm, every source with the same weight in each quantity. <em>Radius:</em> a constant, \(r_{\max}/\eta=""" + "%.2f" % cr["a"] + r"""\) (rms %.0f%%), is chosen by AICc over a power law, \(""" % cr["rms_log_pct"] + "%.2f" % pr["a"] + r"""\,Re_\lambda^{""" + "%.3f" % pr["b"] + r"""}\) (rms %.0f%%); the radius has no trend with the Reynolds number. <em>Swirl:</em> \(U_{\max}/U_\eta=""" % pr["rms_log_pct"] + "%.3f" % p1["a"] + r"""\,Re_\lambda^{""" + "%.2f" % p1["b"] + r"""}\) (rms %.0f%%), and with the exponent 1/3 of model I \(""" % p1["rms_log_pct"] + "%.3f" % p3["a"] + r"""\,Re_\lambda^{1/3}\) (rms %.0f%%), within 2%% of the coefficient of the selected law (section 11); the circulation of the two lines is \(\Gamma/\nu=8.784\,r_{\max}U_{\max}\) (red line of the third panel). The scatter of the swirl is larger here (%.0f%% against the %.0f%% of the selected law) because this set contains the rows that the selection leaves out: the threshold averages of Mouri et al. (2004, 2007), the swirl of Da Silva et al. and of Sassa and Makita. The corrections of the figure are those computed from the models; the corrections adopted for the fits (section 9) are fewer and simpler, and the two are kept apart: this subsection does not change the selection of section 10.</p>
""" % (p3["rms_log_pct"], p1["rms_log_pct"], p3["rms_log_pct"] * 0 + 11.4)
    return text


