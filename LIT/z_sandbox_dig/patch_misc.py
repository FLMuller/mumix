import os
HERE = os.path.dirname(os.path.abspath(__file__))
LIT = os.path.dirname(HERE)

# ---------------------------------------------------------------- the checks table of the book: model I is now D4
p = os.path.join(LIT, "record", "evidence.py")
s = open(p, encoding="utf-8").read()
old = '''    tab.table(["check", "measured", "model I (D6)", "model II (all tubes)"],
              [[r"volume fraction of the tubes, Kida et al., \\(R_\\lambda=83\\)", "0.35", "0.36", "0.35"],
               [r"volume fraction of the tubes, Kida et al., \\(R_\\lambda=170\\)", "0.31", "0.22", "0.29"],
               [r"swirl exponent, Sassa and Makita (conditional sampling, \\(R_\\lambda\\) 19&ndash;2391)", "0.28", "1/3", "0.13 (all), 0.32 (intense)"],
               [r"swirl of all tubes at \\(Re_\\lambda\\approx80\\), Tanahashi et al. (2001) pdf, mean", "3.7", "3.3", "3.6"],
               [r"swirl of all tubes at \\(Re_\\lambda\\approx99\\), Pirozzoli (2012) pdf, mean", "2.5", "3.6", "3.7"]],'''
assert s.count(old) == 1
new = '''    import fitmodels
    kap = next(m for m in models if m["key"] == "D4")["params"][0] / 15 ** 0.25                       # model I: U_max/U_eta = kap Re^(1/2)
    vf = lambda re: float(fitmodels.budget(5.0, kap * re ** 0.5)["vf"])
    tab.table(["check", "measured", "model I (D4)", "model II (all tubes)"],
              [[r"volume fraction of the tubes, Kida et al., \\(R_\\lambda=83\\)", "0.35", "%.2f" % vf(83), "0.35"],
               [r"volume fraction of the tubes, Kida et al., \\(R_\\lambda=170\\)", "0.31", "%.2f" % vf(170), "0.29"],
               [r"swirl exponent, Sassa and Makita (conditional sampling, \\(R_\\lambda\\) 19&ndash;2391)", "0.28", "1/2", "0.13 (all), 0.32 (intense)"],
               [r"swirl of all tubes at \\(Re_\\lambda\\approx80\\), Tanahashi et al. (2001) pdf, mean", "3.7", "%.1f" % (kap * 80 ** 0.5), "3.6"],
               [r"swirl of all tubes at \\(Re_\\lambda\\approx99\\), Pirozzoli (2012) pdf, mean", "2.5", "%.1f" % (kap * 99 ** 0.5), "3.7"]],'''
s = s.replace(old, new)
open(p, "w", encoding="utf-8").write(s)

# ---------------------------------------------------------------- the paper: the stale sentence on the divisor, and the bridge to the multipliers of Fig. 1b
p = os.path.join(LIT, "analysis", "build_paper.py")
s = open(p, encoding="utf-8").read()


def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:80])
    s = s.replace(old, new)


rep(r"The corrected radii (4.7 to 5.3 \(\eta\)) agree with the simulations, and the fits are insensitive to the divisor between 1.6 and 1.9 (section 10).</p>",
    r"The corrected radii (4.7 to 5.3 \(\eta\)) agree with the simulations.</p>")
i = s.index("Four corrections were adopted before the fits")
j = s.index("</p>", i)
print(s[i:j][:600])
s = s[:j] + r" These four constant corrections are those of the first selection; the selection of section 10 and Fig. 1b use instead the multipliers computed from the models of the probes, which depend on \(Re_\lambda\) and which these constants approximate (for Mouri and Hori, the radius factor 1/1.75 = 0.57 and the swirl factor 3 against the model multipliers 0.46 to 0.58 and 2.7 to 3.8 for k = 0.33 between \(Re_\lambda=100\) and 2000)." + s[j:]
open(p, "w", encoding="utf-8").write(s)
print("ok")
