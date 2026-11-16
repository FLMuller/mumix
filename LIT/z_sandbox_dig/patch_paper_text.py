import re
p = "build_paper.py"
t = open(p, encoding="utf-8").read()

def rep(a, b, count=1):
    global t
    assert a in t, a[:70]
    t = t.replace(a, b, count)

# (a) abstract and (b) conclusion: the radius
rep(r"The radius is \(r_{\max}=5\,\eta\) in all flows.", r"The radius is \(r_{\max}\approx5\,\eta\) in all flows (@RFIT@ \(\eta\) fitted, without a trend with \(Re_\lambda\)).")
rep(r"have a radius of maximum swirl of \(5\eta\) in every flow examined, independent of the Reynolds number; this is the firmest result.", r"have a radius of maximum swirl of about \(5\eta\) (@RFIT@ \(\eta\) fitted) in every flow examined, with no trend with the Reynolds number; this is the firmest result.")
# (c) corrections count
rep("<p>Three corrections were adopted before the fits;", "<p>Four corrections were adopted before the fits (the radius and the swirl of Mouri and Hori, the radius of Belin et al., the radius and the swirl of Ghira et al.);")
# (d) the review paragraph
rep("was a support of the factor 0.6,", "was a support of the factor 0.6 of the swirl of Ghira et al. (now 0.67, section 9a),")
# (e) section 10 selection paragraph -> token
i = t.index("<p>The logarithmic swirl law with radius 5 (L1, two parameters) predicts left-out sources best")
j = t.index("</p>", i) + 4
t = t[:i] + "@SELTEXT@" + t[j:]
# (f) section 11 radius rms
rep("The rms residual is 8.2% for the radius and @RMS6@% for radius and swirl together.", "The rms residual is @RRMS6@% for the radius and @RMS6@% for radius and swirl together.")
# (g) Table 2 sentence
i = t.index("<p>The selection is robust to the radius divisor and fragile to the swirl factors (Table 2).")
j = t.index("</p>", i) + 4
t = t[:i] + "@SENSTEXT@" + t[j:]
# (h) factor between the models at Re 1000
rep(r"and by a factor 1.5 in the swirl at \(Re_\lambda=1000\) (Table 3)", r"and by a factor @R1000@ in the swirl at \(Re_\lambda=1000\) (Table 3)")
rep(r"Models I and II differ by a factor 1.5 at \(Re_\lambda=1000\).", r"Models I and II differ by a factor @R1000@ at \(Re_\lambda=1000\).")
# (i) Pirozzoli Re_lambda
rep(r"that of Pirozzoli (2012; \(Re_\lambda\approx99\)) is 2.5 (model II: 3.7), a disagreement that remains.", r"that of Pirozzoli (2012; \(Re_\lambda\approx99\), the test case D named in the caption of his Fig. 2) is 2.5 (model II: 3.7); the plotted symbols are those of his case E (\(Re_\lambda=251\); model II: @P251@), so the disagreement remains whichever case it is.")
# the new figure and fits in section 9
rep('<p class="note">Fig. 1. Radius and swirl of vortex tubes against \(Re_\lambda\), as used in the fits (open symbols: the value as calculated from the paper where a correction was applied; crosses: left out of the fits).</p>', '<p class="note">Fig. 1. Radius and swirl of vortex tubes against \(Re_\lambda\), as used in the fits (open symbols: the value as calculated from the paper where a correction was applied; crosses: left out of the fits).</p>\n@CORRFIG@')
open(p, "w", encoding="utf-8").write(t)
print("ok")
