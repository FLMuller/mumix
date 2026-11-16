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
<p>The radius and the swirl were fitted to the dots of the bottom row (§NR§ points of §SR§ sources for the radius and §NU§ of §SU§ for the swirl; §NRW§ and §NUW§ with the rows of Mouri and Hori 2009), with the weighted sum of squares of the last appendix, in which every point has the same weight and the small and the large values are balanced; the standard error \(s\) of that appendix is quoted. Two kinds of dot are left out: the all-tube average of Mouri and Hori (2009) in the red fit, because it carries the largest multiplier and its threshold is not known (the grey fit includes it), and, in both fits, the two rows of Sassa and Makita at \(Re_\lambda=820\) (a shear flow) and 2391, grey in the figure. <em>Radius:</em> a straight line describes the radius better than a constant or a power law, \(r_{\max}/\eta=§RA§-§RB§\,Re_\lambda\) without the all-tube average of Mouri and Hori (§SRL§; a constant, §RC§, has §SRC§) and \(§RAW§-§RBW§\,Re_\lambda\) with it (§SRLW§); the line falls from §R100§ at \(Re_\lambda=100\) to §R2000§ at 2000. <em>Swirl:</em> \(U_{\max}/U_\eta=§UA§\,Re_\lambda^{1/2}\) without and \(§UAW§\,Re_\lambda^{1/2}\) with the all-tube average (§SUH§ and §SUHW§); the free exponent is §UB§ and §UBW§ (§SUF§ and §SUFW§), so 1/2 is as good as the free exponent, and the exponent 1/3 of model I is worse (§SUT§ and §SUTW§). Because \(u'/U_\eta=Re_\lambda^{1/2}/15^{1/4}\), an exponent of 1/2 means that \(U_{\max}/u'=15^{1/4}\cdot§UA§=§UP§\) (§UPW§ with the all-tube average) does not depend on the Reynolds number. The circulation of the lines of the third panel is \(8.784\,r_{\max}U_{\max}\) of the two fits. On this set of corrections the data therefore prefer a swirl exponent near 1/2 to the 1/3 of model I; the corrections of the figure are those computed from the models and the corrections adopted for the fits (section 9) are fewer and simpler, so the two are kept apart: this subsection does not change the selection of section 10, which was not repeated on these values.</p>
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
which is positive, since \(e_{\min}<\bar e<e_{\max}\), and is computed for each fit from the values that enter it. For \(b\to0\) the measure is the absolute error and the weights of all points are equal; for \(b=1\) it is the plain sum of the relative and the absolute error. The ratio of the weight of the smallest value to that of the largest is
$$\frac{w(e_{\min})}{w(e_{\max})}=\frac{b/e_{\min}^2+1/\bar e^{\,2}}{b/e_{\max}^2+1/\bar e^{\,2}} .$$</p>
<h3>B4. Values for Fig. 1b</h3>
<p>For the radius (§NR§ values from §RMIN§ to §RMAX§, mean §RMEAN§) \(b=§BR§\) and the weight ratio is §WR§ to 1; for the swirl (§NU§ values from §UMIN§ to §UMAX§, mean §UMEAN§) \(b=§BU§\) and the ratio is §WU§ to 1 (all values without the all-tube average of Mouri and Hori; with it \(b=§BRW§\) for the radius and \(§BUW§\) for the swirl). With \(b=1\) the swirl would have a ratio of §WONE§ to 1 and be fitted mostly at its small values. The models fitted are, for the radius, a constant, a power law and a straight line, and for the swirl a power law with a free exponent, the exponents 1/3 and 1/2, and a straight line; \(p\) is 1 for a constant and a fixed exponent and 2 otherwise, and the model of the lowest \(s\) is taken. Without the all-tube average of Mouri and Hori the lowest \(s\) is §SRL§ for the radius (a straight line) and §SUF§ for the swirl (the free power law, whose exponent is §UB§; the exponent 1/2 has §SUH§).</p>
<h3>B5. What it replaces</h3>
<p>Earlier versions of Fig. 1b fitted the logarithm of the values with the same total weight for each source. That put one row of Wang et al. on the same footing as the 22 rows of Mouri et al. (2007), and the logarithm penalised a point below the curve more than a point above it, so the curve did not pass through the middle of the data. Both were dropped.</p>
"""
    rep = {"§UMIN§": "%.1f" % o["us"]["min"], "§UMAX§": "%.1f" % o["us"]["max"], "§UMEAN§": "%.1f" % o["us"]["mean"], "§RMIN§": "%.1f" % o["rs"]["min"], "§RMAX§": "%.1f" % o["rs"]["max"], "§RMEAN§": "%.1f" % o["rs"]["mean"],
           "§NR§": "%d" % o["nr"], "§NU§": "%d" % o["nu"], "§BR§": "%.2f" % o["br"], "§BU§": "%.3f" % o["bu"], "§BRW§": "%.2f" % w["br"], "§BUW§": "%.3f" % w["bu"],
           "§WR§": "%.1f" % o["wr"], "§WU§": "%.1f" % o["wu"], "§WONE§": "%.0f" % w_one, "§SRL§": "%.3f" % (o["r_line"]["rss"] ** 0.5), "§SUF§": "%.3f" % (o["u_free"]["rss"] ** 0.5), "§SUH§": "%.3f" % (o["u_half"]["rss"] ** 0.5), "§UB§": "%.2f" % o["u_free"]["b"]}
    for k, v in rep.items():
        text = text.replace(k, v)
    return text
