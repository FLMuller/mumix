p = "build_data_sections.py"
t = open(p, encoding="utf-8").read()
def rep(a, b):
    global t
    assert a in t, a[:60]
    t = t.replace(a, b, 1)
rep('"none (Ghira 2022: &times;0.6)"', '"none (Ghira 2022, 2025: radius &times;1.25, swirl &times;0.67; Belin: radius &divide;1.15)"')
rep("and 0.6 is used. This is an empirical factor", "and 0.6 was used; the derivation of section 9a, from the all-tube population of Pirozzoli (2012), gives 0.66&ndash;0.68, so 0.67 is used now, with a radius factor of 1.25. This is an empirical factor")
rep("no choice of the Mouri and Hori factor brings the fits below 17% (combined score), against 8% with the factor 0.6.", "no choice of the Mouri and Hori factor brings the fits below @LRMS@% (combined score), against @NRMS@% with the factors of section 9a.")
a = "the DNS and the corrected hot-wire radii lie at 4.3&ndash;5.4 \(\eta\) for both sets (Ghira, Jim&eacute;nez, Da Silva, Tanahashi, Kida, Mouri and Hori), and the boundary radius of the PIV (Aligolzadeh) is 6.0 \(\eta\)."
rep(a, "the DNS and the corrected hot-wire radii lie at 4.3&ndash;5.4 \(\eta\) for both sets (Jim&eacute;nez, Da Silva, Tanahashi, Kida, Mouri and Hori; Ghira et al. as calculated, 4.5&ndash;5.0 \(\eta\)), the radius of Ghira et al. after the factor 1.25 of section 9a (the cut of the strongest 1% of the volume keeps small tubes) is 5.6&ndash;6.2 \(\eta\), and the boundary radius of the PIV (Aligolzadeh) is 6.0 \(\eta\).")
a = "and the swirl of Ghira et al. (2022) &times; 0.6 (it lies above the swirl of the other sources and above the swirl implied by their own axis vorticity)."
rep(a, "the radius of Ghira et al. (2022, 2025) &times; 1.25 and their swirl &times; 0.67 (the 1% of the volume with the strongest vorticity is a subset of the tubes, smaller and faster than the whole population; the factors are worked out in section 9a from the all-tube population of Pirozzoli 2012), and the radius of Belin et al. (1996) &divide; 1.15 (the median of their Fig. 5 over the true radius of the intense tubes in the wire-and-tube model).")
open(p, "w", encoding="utf-8").write(t)
p = "build_paper.py"
t = open(p, encoding="utf-8").read()
a = "    typeset = "
assert a in t
t = t.replace(a, '''    best_of = lambda s: sorted(s["models"], key=lambda m: m["loso"])[0]
    listed = [s for s in scen if s["label"].startswith("Ghira swirl as listed (x 1), Mouri-Hori U x 3")][0]
    appendix = appendix.replace("@LRMS@", "%.1f" % best_of(listed)["rms"]).replace("@NRMS@", "%.1f" % best_of(scen[0])["rms"])
''' + a, 1)
open(p, "w", encoding="utf-8").write(t)
print("ok")
