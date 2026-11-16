import os
HERE = os.path.dirname(os.path.abspath(__file__))
LIT = os.path.dirname(HERE)

# ------------------------------------------------------------------ modelselect.dots: the keys the figure code of the fitting tool reads
p = os.path.join(LIT, "fittingtool", "modelselect.py")
m = open(p, encoding="utf-8").read()
old = '''            row.update(r=r, u=u, g=(fitdata.G0 * r * u if r is not None and u is not None else None),'''
new = '''            row.update(r=r, u=u, r_raw=r_raw, u_raw=u_raw, re_lo=row["re"], re_hi=row["re"], gamma_listed=None, d_over_eta=None, g=(fitdata.G0 * r * u if r is not None and u is not None else None),'''
assert m.count(old) == 1
m = m.replace(old, new)
open(p, "w", encoding="utf-8").write(m)

# ------------------------------------------------------------------ build_paper.py
p = os.path.join(LIT, "analysis", "build_paper.py")
s = open(p, encoding="utf-8").read()


def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:80])
    s = s.replace(old, new)


# the single law in the figure of the two populations
rep(r'''ax.plot(re, c6 * re ** (1 / 3), "--", color="k", lw=1.3, label=r"single law of section 11: $%.3f\,Re_\lambda^{1/3}$ (corrected data)" % c6)''',
    r'''ax.plot(re, c6 * re ** 0.5, "--", color="k", lw=1.3, label=r"single law of section 11: $%.3f\,Re_\lambda^{1/2}$ (corrected data)" % c6)''')

# the note on the DNS law of the wire-and-tube section
i = s.index('    text += r"""<p class="note">The DNS law of this section')
j = s.index('"""', s.index('"""', i) + 3) + 3
note = '''    text += r"""<p class="note">The DNS law of this section, \\(U_{\\max}=0.769\\,Re_\\lambda^{1/3}U_\\eta\\), is the law of the selection at the time the model was fitted; the selection of section 10 now gives \\(U_{\\max}/U_\\eta=@C6@\\,Re_\\lambda^{1/2}\\) (\\(U_{\\max}=@KAPPA@\\,u'\\)), on the data of Fig. 1b. The tubes found from the records of Belin et al. do not depend on it: their swirl, 2.58 times the old law, is fitted to their Fig. 6 and is the fixed product \\(1.98\\,Re_\\lambda^{1/3}U_\\eta\\), so the multipliers computed on them (Fig. 1b, the recording book) stand. The runs with tubes of the DNS (this section and the next) were not repeated with the new law, which is larger than the old one by a factor @DNSRATIO@ at \\(Re_\\lambda=332\\) and @DNSRATIO2@ at 1934.</p>
"""'''
s = s[:i] + note + s[j:]

# the sensitivity text of section 10
i = s.index("def sens_text(scen):")
j = s.index("def fit_numbers():")
sens = '''def sens_text(scen):
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
            "Keeping the two rows of Sassa and Makita at \\\\(Re_\\\\lambda=820\\\\) and 2391 gives %s (%.1f%%) and D4 %.1f%%.</p>" % (best(listed)["key"], best(listed)["loso"], d4(listed), best(rad)["key"], best(rad)["loso"], d4(rad), best(big)["key"], best(big)["loso"], d4(big),
                                                                                                                                      best(sas)["key"], best(sas)["loso"], d4(sas)))


'''
s = s[:i] + sens + s[j:]

# build(): the data, the selected model D4 and the tokens
rep('''    rows = modelselect.load({})
    obs = fitdata.observations(rows)
    models = {m.key: m for m in fitmodels.models(obs)}
    res6 = fitmodels.fit(models["D6"], obs)
    c6 = float(res6["params"][0])
''', '''    rows = modelselect.dots(**modelselect.SCENARIOS[0][1])                           # the data of Fig. 1b without the all-tube average of Mouri and Hori
    obs = fitdata.observations(rows)
    models = {m.key: m for m in fitmodels.models(obs)}
    res6 = modelselect.fit(models["D4"], obs)                                        # the selected model: radius 5, swirl proportional to u'
    kappa = float(res6["params"][0])                                                 # U_max = kappa u', u'/U_eta = (Re/sqrt 15)^(1/2)
    c6 = kappa / 15 ** 0.25                                                          # U_max/U_eta = c6 Re^(1/2)
''')
rep('''        d = next(m for m in ms if m["key"] == "D6")
        sens_rows.append([sc["label"], "%s (%.1f%%)" % (ms[0]["key"], ms[0]["loso"]), "%.1f%%" % d["loso"], "%.3f" % d["params"][0]])''',
    '''        d = next(m for m in ms if m["key"] == "D4")
        sens_rows.append([sc["label"], "%s (%.1f%%)" % (ms[0]["key"], ms[0]["loso"]), "%.1f%%" % d["loso"], "%.3f" % d["params"][0]])''')
rep("        U1 = c6 * Re ** (1 / 3)\n", "        U1 = c6 * Re ** 0.5\n")
rep('"@RMS6@": "%.1f" % main0["D6"]["rms"], "@LOSO6@": "%.1f" % main0["D6"]["loso"], "@LOSOL1@": "%.1f" % main0["L1"]["loso"], "@DAIC6@": "%.1f" % main0["D6"]["d_aicc"],',
    '"@RMS6@": "%.1f" % main0["D4"]["rms"], "@LOSO6@": "%.1f" % main0["D4"]["loso"], "@LOSOL1@": "%.1f" % main0["L1"]["loso"], "@DAIC6@": "%.1f" % main0["D4"]["d_aicc"], "@KAPPA@": "%.2f" % kappa,\n        "@DNSRATIO@": "%.2f" % (c6 * 332 ** 0.5 / (0.769 * 332 ** (1 / 3))), "@DNSRATIO2@": "%.2f" % (c6 * 1934 ** 0.5 / (0.769 * 1934 ** (1 / 3))),')
rep('"@NG@": str(main0["D6"]["groups"]),', '"@NG@": str(main0["D4"]["groups"]),')
rep('"@VK83A@": "%.2f" % bud(c6 * 83 ** (1 / 3))[0], "@VK170A@": "%.2f" % bud(c6 * 170 ** (1 / 3))[0],', '"@VK83A@": "%.2f" % bud(c6 * 83 ** 0.5)[0], "@VK170A@": "%.2f" % bud(c6 * 170 ** 0.5)[0],')
rep('"@RRMS6@": "%.1f" % main0["D6"]["rms_r"],', '"@RRMS6@": "%.1f" % main0["D4"]["rms_r"],')
rep('"@R1000@": "%.2f" % ((c6 * 1000 ** (1 / 3)) /', '"@R1000@": "%.2f" % ((c6 * 1000 ** 0.5) /')
rep('table(["model", "parameters", "rms %", "LOSO %"', 'table(["model", "parameters", "s %", "LOSO %"')
rep('table(["corrections", "best model by LOSO", "LOSO of the selected model", "its coefficient \\\\(c\\\\)"], sens_rows)', 'table(["data", "best model by LOSO", "LOSO of the selected model D4", "its \\\\(\\\\kappa=U_{\\\\max}/u\'\\\\)"], sens_rows)')

# the exponent of the selected law in the text
rep("@C6@\\,Re_\\lambda^{1/3}", "@C6@\\,Re_\\lambda^{1/2}", 3)

# abstract
rep(r"With the corrections adopted for probe measurements, a single one-parameter law, \(U_{\max}/U_\eta=@C6@\,Re_\lambda^{1/2}\), predicts sources left out of the fit to within @LOSO6@%, and no model with more parameters predicts them better. A review of the sources shows, however, that the uncorrected data separate into two populations:",
    r"With the corrections computed for the probe measurements from the models of their signals, a single one-parameter law, \(U_{\max}/U_\eta=@C6@\,Re_\lambda^{1/2}\), that is \(U_{\max}=@KAPPA@\,u'\), describes simulations and experiments together and predicts sources left out of the fit to within @LOSO6@%; no model with more parameters predicts them better. Read as calculated from the papers, the data separate into two populations:")
rep(r"The second reading needs one fitted probe factor instead of two corrections and reproduces the measured volume fraction of the tubes.", r"The second reading needs one fitted probe factor and reproduces the measured volume fraction of the tubes.")

# section 10
rep(r"Each is fitted by least squares of the logarithmic residuals of the radius (@NR@ points) and the swirl (@NU@ points), every source having the same weight in each quantity (@NG@ source-quantity groups).",
    r"Each is fitted by minimising the weighted sum of squares of the last appendix over the radius (@NR@ points) and the swirl (@NU@ points) of Fig. 1b, every point having the same weight (@NG@ source-quantity groups).")
rep(r"and the rms of those prediction errors (LOSO, in per cent) is the score.", r"and the standard error of those prediction errors, measured with the same sum of squares (LOSO, in per cent), is the score.")
rep("Table 1. The candidate models, sorted by the leave-one-source-out error. Corrections as adopted in section 9.", "Table 1. The candidate models, sorted by the leave-one-source-out error, on the data of Fig. 1b without the all-tube average of Mouri and Hori (2009); s is the standard error of the fit of the last appendix, in per cent.")
rep("Table 2. The selection under other corrections.", "Table 2. The selection under other treatments of the data.")

# section 11
rep(r"""$$r_{\max}=5\,\eta,\qquad \frac{U_{\max}}{U_\eta}=@C6@\,Re_\lambda^{1/2}$$""", r"""$$r_{\max}=5\,\eta,\qquad \frac{U_{\max}}{U_\eta}=@C6@\,Re_\lambda^{1/2},\quad\text{that is}\quad U_{\max}=@KAPPA@\,u',\qquad \frac{u'}{U_\eta}=\left(\frac{Re_\lambda}{\sqrt{15}}\right)^{1/2}$$""")
rep("<p>The rms residual is @RRMS6@% for the radius and @RMS6@% for radius and swirl together.", "<p>The standard error of the fit (last appendix) is @RRMS6@% for the radius and @RMS6@% for radius and swirl together.")

# section 12: which model
i = s.index("<p><strong>Which model.</strong>")
j = s.index("</p>", i) + 4
which = (r"<p><strong>Which model.</strong> Model I is retained as the reference. With the corrections computed from the models of the probes (section 9) it describes simulations and experiments together with one parameter, the swirl proportional to the r.m.s. velocity, \(U_{\max}=@KAPPA@\,u'\), the scaling that Mouri et al. (2007) report for intense tubes; model II reads the values as calculated as two populations and rests on one fitted factor for the chord effect, and its weakness is that the all-tube law rests on two sources. "
         r"The two differ little near \(Re_\lambda\approx100\), where most simulations are, and by a factor @R1000@ in the swirl at \(Re_\lambda=1000\) (Table 3). For a closure of micromixing, which depends on all tubes weighted by their volume, we recommend model I and regard the difference between the two as the uncertainty of the swirl at high Reynolds number. The intense tubes, if they keep 1% of the volume, carry 6% of the dissipation at \(Re_\lambda=100\) and a growing share above (Table 3, last column).</p>")
s = s[:i] + which + s[j:]

# conclusions
rep(r"Their swirl is described by one law, \(U_{\max}/U_\eta=@C6@\,Re_\lambda^{1/2}\), if probe data and the most intense tubes are corrected to a common level, and by two laws without swirl corrections if the most intense tubes and all tubes are taken as two populations.",
    r"Their swirl is described by one law, \(U_{\max}/U_\eta=@C6@\,Re_\lambda^{1/2}\), that is a constant fraction \(@KAPPA@\) of the r.m.s. velocity, if probe data and the most intense tubes are corrected to a common level with the multipliers computed from the models of the probes, and by two laws without swirl corrections if the most intense tubes and all tubes are taken as two populations.")
open(p, "w", encoding="utf-8").write(s)
print("patched")
