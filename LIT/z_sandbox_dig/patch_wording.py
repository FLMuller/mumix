import os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "analysis", "build_paper.py")
s = open(p, encoding="utf-8").read()


def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:70])
    s = s.replace(old, new)


rep(r"so 1/2 is as good as the free exponent, and the exponent 1/3 of model I is worse (§SUT§ and §SUTW§). Because", r"so 1/2 is as good as the free exponent. Because")
rep(r"""does not depend on the Reynolds number. The circulation of the lines of the third panel is \(8.784\,r_{\max}U_{\max}\) of the two fits. On this set of corrections the data therefore prefer a swirl exponent near 1/2 to the 1/3 of model I; the corrections of the figure are those computed from the models and the corrections adopted for the fits (section 9) are fewer and simpler, so the two are kept apart: this subsection does not change the selection of section 10, which was not repeated on these values.</p>""",
    r"""does not depend on the Reynolds number: this is the scaling \(U_{\max}\propto u'\) that Mouri et al. (2007) found for the intense tubes of their experiments (reported by Mouri and Hori 2009, section 6), and Fig. 1b shows that it holds for simulations and experiments together over the range of the data. The circulation of the lines of the third panel is \(8.784\,r_{\max}U_{\max}\) of the two fits.</p>""")
rep(r"the line falls from §R100§ at \(Re_\lambda=100\) to §R2000§ at 2000.", r"the line falls from §R100§ at \(Re_\lambda=100\) to §R2000§ at 2000, a very small reduction over a wide range of Reynolds number, in simulations and experiments together.")
i = s.index("<h3>B5. What it replaces</h3>")
j = s.index('"""', i)
s = s[:i] + s[j:]
rep(r"The radius is \(r_{\max}\approx5\,\eta\) in all flows (@RFIT@ \(\eta\) fitted, without a trend with \(Re_\lambda\)).",
    r"The radius is \(r_{\max}\approx5\,\eta\) in all flows (@RFIT@ \(\eta\) fitted); simulations and experiments together show only a very small reduction with the Reynolds number, from @RL100@ \(\eta\) at \(Re_\lambda=100\) to @RL2000@ \(\eta\) at 2000.")
rep(r"(@RFIT@ \(\eta\) fitted) in every flow examined, with no trend with the Reynolds number; this is the firmest result.",
    r"(@RFIT@ \(\eta\) fitted) in every flow examined, with only a very small reduction with the Reynolds number, from @RL100@ \(\eta\) at \(Re_\lambda=100\) to @RL2000@ \(\eta\) at 2000; this is the firmest result.")
rep('        "@DNSPDF@": dns_pdf_section(),', '        "@DNSPDF@": dns_pdf_section(),\n        "@RL100@": "%.1f" % (fit_numbers()["o"]["r_line"]["a"] + 100 * fit_numbers()["o"]["r_line"]["b"]), "@RL2000@": "%.1f" % (fit_numbers()["o"]["r_line"]["a"] + 2000 * fit_numbers()["o"]["r_line"]["b"]),')
open(p, "w", encoding="utf-8").write(s)
print("patched")
