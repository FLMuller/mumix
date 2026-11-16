import os
HERE = os.path.dirname(os.path.abspath(__file__))
LIT = os.path.dirname(HERE)
p = os.path.join(LIT, "record", "evidence.py")
s = open(p, encoding="utf-8").read()
a = s.index('    rows = modelselect.load({})\n    obs = fitdata.observations(rows)\n    tab.h("1. Which numbers enter the fits")')
b = s.index('    tab.h("4. Model II: two populations, no swirl correction")')
new = '''    rows = modelselect.dots(**modelselect.SCENARIOS[0][1])
    obs = fitdata.observations(rows)
    tab.h("1. Which numbers enter the fits")
    tab.p(r"The fits use the dots of the bottom row of Fig. 1b of the paper (rows with one \\(Re_\\lambda\\)): Ghira et al. and the observed rows with the multipliers computed from the models of the probes (tab Corrections of each paper), the other simulations as read; the all-tube average of Mouri and Hori (2009) and the rows of Sassa and Makita at \\(Re_\\lambda\\) 820 and 2391 are left out of the main scenario. Every point has the same weight (the weighted sum of squares of the last appendix of the paper).")
    lines = []
    for kind, label in (("r", r"\\(r_{\\max}/\\eta\\)"), ("U", r"\\(U_{\\max}/U_\\eta\\)")):
        o = obs[kind]
        by = {}
        for s_, v, re in zip(o["src"], o["val"], o["re"]):
            by.setdefault(s_, []).append((re, v))
        for s_, pts in sorted(by.items()):
            lines.append([label, s_, str(len(pts)), "%g&ndash;%g" % (min(p_[0] for p_ in pts), max(p_[0] for p_ in pts)), "%.2f&ndash;%.2f" % (min(p_[1] for p_ in pts), max(p_[1] for p_ in pts))])
    tab.table(["quantity", "source", "rows", r"\\(Re_\\lambda\\)", "values (corrected)"], lines, "The data of the fits: %d radius points and %d swirl points from %d source-quantity groups." % (len(obs["r"]["re"]), len(obs["U"]["re"]), len(lines)))
    tab.h("2. The selection of the model (model I: one population)")
    tab.p(r"Every candidate is fitted to the same data by minimising the weighted sum of squares S of the last appendix of the paper (relative plus absolute error, linear domain; s = sqrt(S/(N-p)) is quoted in per cent). Three criteria: AICc and BIC (information criteria; a difference under 2 is no evidence, over 10 is decisive), counted with one unit a source-quantity group, and LOSO (leave one source out: the model is fitted without a source and predicts it). LOSO is the criterion used; among the best the model with the fewest parameters is taken.")
    models = sorted(res["scenarios"][0]["models"], key=lambda m: m["loso"])
    tab.table(["model", "parameters", "s %", "LOSO %", "&Delta;AICc", "&Delta;BIC", "what it is"],
              [[m["key"], str(m["k"]), "%.1f" % m["rms"], "%.1f" % m["loso"], "%.1f" % m["d_aicc"], "%.1f" % m["d_bic"], m["name"]] for m in models],
              "Scenario: the data of Fig. 1b without the all-tube average of Mouri and Hori. Sorted by LOSO.")
    best = models[0]
    d6 = next(m for m in models if m["key"] == "D6")
    tab.p("<b>Reading.</b> %s (%s, %d parameter%s) predicts left-out sources best (%.1f%%); D6 (radius 5, swirl c Re^(1/3)) scores %.1f%%. kappa = U_max/u' = %.3f for D4, that is U_max/U_eta = %.3f Re_lambda^(1/2)." % (
        best["key"], best["name"], best["k"], "" if best["k"] == 1 else "s", best["loso"], d6["loso"], next(m for m in models if m["key"] == "D4")["params"][0], next(m for m in models if m["key"] == "D4")["params"][0] / 15 ** 0.25))
    tab.h("3. How the choice depends on the data")
    rowsx = []
    for sc in res["scenarios"]:
        ms = sorted(sc["models"], key=lambda m: m["loso"])
        d = next(m for m in ms if m["key"] == "D4")
        rowsx.append([sc["label"], "%s (%.1f%%)" % (ms[0]["key"], ms[0]["loso"]), "%.1f%%" % d["loso"], "%.3f" % d["params"][0]])
    tab.table(["scenario", "best by LOSO", "D4 LOSO", "D4 coefficient kappa = U_max/u'"], rowsx, "The same comparison under other treatments of the data.")
    tab.p("<b>Reading.</b> D4 is the best model in most scenarios and within about 0.1 to 1.5 percentage points of the best in the others; the all-tube average of Mouri and Hori raises the error whatever its threshold (k = 0.25 to 1), and the factors of Ghira et al. decide the rest (section 9a of the paper).")
'''
s = s[:a] + new + s[b:]
open(p, "w", encoding="utf-8").write(s)
print("ok")
