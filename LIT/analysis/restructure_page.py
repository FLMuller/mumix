"""One-off restructuring of the page after the 3-parameter fit was dropped (guarded, safe to run twice):
  - removes Step 7 (fit), the data table and Step 8 (results) of the 3-parameter model, and the old Limits block
    (the limits now close section 9, written by build_sec8.py);
  - renames section 7 to 8 (the new section 7 is written by build_data_sections.py);
  - rewrites the cross-references of the model steps to section 9;
  - updates the model values of the evidence table (Step 6) to the 4-parameter fit;
  - adds the new references and sorts the list.
"""
import math
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sourcedata as sd

PAGE = os.path.join(os.path.dirname(HERE), "vortex-energy-balance.html")
t = open(PAGE, encoding="utf8").read()

# 4-parameter fit of the page (build_sec8.py): a, p, q, s
A, P, Q, S_ = 76.80, 0.1453, 0.2999, 0.1768
x, KB = sd.x, sd.KB
G = 2 * math.pi / KB
SS = 48 * x * x
E = 0.977 * 4 * x


def tube4(Rl):
    R = A * Rl**P
    beta = (R / (G * Rl**S_)) ** (1 / (1 + Q))
    U = beta**Q * Rl**S_
    Vf = (1 - SS / beta**4) * beta**2 / (E * U**2)
    return dict(R=R, beta=beta, U=U, Rec=R / G, gam=4 * x / beta**2, Vf=Vf, share=1 - SS / beta**4, d=beta * math.sqrt(math.pi / Vf))


def rep(old, new, count=1):
    global t
    assert t.count(old) == count, (old[:80], t.count(old))
    t = t.replace(old, new)


def between(a, b):
    i = t.index(a)
    j = t.index(b, i)
    return i, j


# ---------------------------------------------------------------- 1. remove the 3-parameter fit, data table, results and the old limits
STEP7 = r"<h3>Step 7: fit of \(a\), \(p\) and \(q\)</h3>"
if STEP7 in t:
    i, j = between(STEP7, "<h3>Limits of this model</h3>")
    t = t[:i] + t[j:]
if "<h3>Limits of this model</h3>" in t and t.index("<h3>Limits of this model</h3>") < t.index("<h2>8. Four-parameter"):
    i = t.index("<h3>Limits of this model</h3>")
    j = t.index("</ul>", i) + len("</ul>")
    t = t[:i] + t[j:].lstrip("\n")

# ---------------------------------------------------------------- 2. headings and the introduction of the model section
OLDH = "<h2>7. Tube model with Kolmogorov-scaled swirl, fitted to the literature</h2>"
if OLDH in t:
    t = t.replace(OLDH, "<h2>8. Tube model with Kolmogorov-scaled swirl</h2>")
i = t.index("<h2>8. Tube model with Kolmogorov-scaled swirl</h2>")
j = t.index("<h3>Step 1:", i)
intro = (r"<p>Section 6 closed the model with a spacing law \(\Gamma=c\,U(d)\,d\) containing an unknown constant. Here the closure comes from measured tube kinematics: radius, peak swirl and circulation expressed in Kolmogorov units, with the circulation growing slowly with the Taylor-scale Reynolds number. "
         r"The data are those of section 7 and the appendix, which also explains which tubes (whole or intense) each value refers to. The constants of the closure are fitted in section 9. Everything else follows from the dissipation budget of sections 2 to 5.</p>" "\n\n")
t = t[:i + len("<h2>8. Tube model with Kolmogorov-scaled swirl</h2>\n")] + intro + t[j:]

# ---------------------------------------------------------------- 3. cross-references of the steps
old = r"<tr><td>\(a,\ p,\ q\)</td><td>fitted (Step 7)</td><td>circulation prefactor, growth exponent of the circulation with \(Re_\lambda\), and swirl exponent</td></tr>"
if old in t:
    t = t.replace(old, r"<tr><td>\(a,\ p,\ q,\ s\)</td><td>fitted (section 9)</td><td>circulation prefactor, growth exponent of the circulation with \(Re_\lambda\), and the two exponents of the swirl</td></tr>")
m = re.search(r"\$\$R_\\Gamma=a\\,Re_\\lambda\^\{\\,p\},\\qquad p=[0-9.]+\\;\(\\text\{fitted, Step 7; equivalent to \}Re\^\{[0-9.]+\}\\text\{ for the process \}Re\)\.\$\$", t)
if m:
    t = t.replace(m.group(0), r"$$R_\Gamma=a\,Re_\lambda^{\,p},\qquad p=%.3f\;(\text{fitted, section 9; equivalent to }Re^{%.2f}\text{ for the process }Re).$$" % (P, P / 2))
STEP3_NOTE = r"<p>In section 9 the swirl also carries a factor \(Re_\lambda^{\,s}\), \(U_{\max}=\beta^{\,q}Re_\lambda^{\,s}U_\eta\) (here \(s=0\)); which tubes the swirl refers to is explained in section 7.</p>" "\n"
if "In section 9 the swirl also carries" not in t:
    k = t.index(r"<p>Here \(r_{\max}=2.24")
    t = t[:k] + STEP3_NOTE + t[k:]

# ---------------------------------------------------------------- 4. evidence table: model values of the 4-parameter fit
m = re.search(r'<p>The table lists every published value I could compare with the model.*?</p>', t, flags=re.S)
if m:
    t = t.replace(m.group(0), (r'<p>The table lists every published value I could compare with the model, with the model value from the fit of section 9 (\(a=%.1f\), \(p=%.3f\), \(q=%.2f\), \(s=%.2f\)) at the same \(Re_\lambda\). Only rows marked "fitted" entered the fit; the source data, with the model value and \(\sigma_{	ext{norm}}^2\) of each fitted row, are in section 9 and the appendix.</p>') % (A, P, Q, S_))

pairs = re.findall(r'(<tr class="m"><td rowspan="2">(.*?)</td><td class="lab">Model</td><td class="c">(.*?)</td><td rowspan="2">(.*?)</td></tr>\n\n?<tr><td class="lab">Lit\.</td><td class="c">.*?</td></tr>)', t, flags=re.S)


def swap(key_start, model_html=None, status_html=None):
    global t
    for full, q_, mo, st in pairs:
        if q_.startswith(key_start):
            new = full
            if model_html is not None:
                new = new.replace('<td class="c">%s</td><td rowspan="2">' % mo, '<td class="c">%s</td><td rowspan="2">' % model_html, 1)
            if status_html is not None:
                new = new.replace('<td rowspan="2">%s</td></tr>' % st, '<td rowspan="2">%s</td></tr>' % status_html, 1)
            t = t.replace(full, new, 1)
            return
    raise KeyError(key_start)


def ratios(mtype, keys=None, role="fit"):
    rr = []
    for r in sd.all_rows():
        if r["mtype"] == mtype and isinstance(r["Re"], (int, float)) and (role is None or r["role"] == role) and (keys is None or r["src"] in keys):
            rr.append(tube4(r["Re"])[{"rmax": "beta", "gam": "R", "swirl": "U", "rec": "Rec", "d": "d"}[mtype]] / r["used"])
    return min(rr), max(rr)


r83, r170, r332, r1934 = tube4(83), tube4(170), tube4(332), tube4(1934)
lo_b, hi_b = ratios("rmax")
lo_R, hi_R = ratios("gam")
lo_c, hi_c = ratios("rec")
lo_U, hi_U = ratios("swirl", role="cmp", keys=["Kida02"])
lo_d, hi_d = ratios("d", role="cmp")
swap(r"\(r_{\max}/\eta\) (intense", "%.1f (83), %.1f (170), %.1f (332)" % (r83["beta"], r170["beta"], r332["beta"]), "fitted; ratio %.2f–%.2f" % (lo_b, hi_b))
swap(r"Strain", "%.2f (83), %.2f (170), %.2f (332)" % (r83["gam"], r170["gam"], r332["gam"]))
swap(r"Circulation", "%.0f (83), %.0f (170), %.0f (332), %.0f (1934)" % (r83["R"], r170["R"], r332["R"], r1934["R"]), "fitted; ratio %.2f–%.2f" % (lo_R, hi_R))
swap(r"Tube Reynolds", "%.1f (83) → %.1f (1934)" % (r83["Rec"], r1934["Rec"]), "fitted; ratio %.2f–%.2f" % (lo_c, hi_c))
swap(r"Peak swirl \(U_{\max}/U_\eta\) (all", "%.1f (83), %.1f (170)" % (r83["U"], r170["U"]), "not fitted (Kida et al.); ratio %.2f–%.2f; sources spread over 1.2–14" % (lo_U, hi_U))
swap(r"Tube spacing", "%.1f (83), %.1f (170)" % (r83["d"], r170["d"]), "not fitted (Kida et al.); ratio %.2f–%.2f" % (lo_d, hi_d))
swap(r"Tube length density", r"\(%.1f\times10^{-3}\) (83), \(%.1f\times10^{-3}\) (170)" % (r83["Vf"] / (math.pi * r83["beta"] ** 2) * 1e3, r170["Vf"] / (math.pi * r170["beta"] ** 2) * 1e3))
swap(r"Tube diameter", r"\(2r_{\max}=%.1f\)–%.1f \(\eta\)" % (2 * r83["beta"], 2 * r332["beta"]))
swap(r"Core volume fraction", "%.0f%% (83), %.0f%% (170), to \\(r_{\\max}\\)" % (r83["Vf"] * 100, r170["Vf"] * 100),
     r"model %.0f–%.0f%% is close to the 25%% above \(\omega'\); not a clean test (radius and threshold differ)" % (r83["Vf"] * 100, r170["Vf"] * 100))
swap(r"Vortex share", "%.0f%% (83) → %.0f%% (1934)" % (r83["share"] * 100, r1934["share"] * 100),
     "model %.0f–%.0f%% (83–170) matches 80%% in 25%% of the volume (Jiménez et al.) and 75%% in 20%% (Hosokawa and Yamamoto); conflicts with core-only values (31%%) and with the intense subset" % (r83["share"] * 100, r170["share"] * 100))
t = re.sub(r'<td class="c">[0-9.]+ ± [0-9.]+ \(fitted\)</td>', '<td class="c">%.3f ± 0.017 (fitted)</td>' % P, t, count=1)

# ---------------------------------------------------------------- 5. references
REFS = [
    "Aligolzadeh, F., Holzner, M. and Dawson, J. R. (2023). Entrainment, detrainment and enstrophy transport by small-scale vortex structures. <em>J. Fluid Mech.</em> 973, A5. DOI: <a href=\"https://doi.org/10.1017/jfm.2023.745\">10.1017/jfm.2023.745</a>",
    "Da Silva, C. B., Dos Reis, R. J. N. and Pereira, J. C. F. (2011). The intense vorticity structures near the turbulent/non-turbulent interface in a jet. <em>J. Fluid Mech.</em> 685, 165. DOI: <a href=\"https://doi.org/10.1017/jfm.2011.296\">10.1017/jfm.2011.296</a>",
    "Das, S. K., Tanahashi, M., Shoji, K. and Miyauchi, T. (2006). Statistical properties of coherent fine eddies in wall-bounded turbulent flows by direct numerical simulation. <em>Theor. Comput. Fluid Dyn.</em> 20, 55–71. DOI: <a href=\"https://doi.org/10.1007/s00162-006-0008-z\">10.1007/s00162-006-0008-z</a>",
    "Ishihara, T., Hunt, J. C. R. and Kaneda, Y. (2011). Conditional analysis near strong shear layers in DNS of isotropic turbulence at high Reynolds number. <em>J. Phys.: Conf. Ser.</em> 318, 042004. DOI: <a href=\"https://doi.org/10.1088/1742-6596/318/4/042004\">10.1088/1742-6596/318/4/042004</a>",
    "Ishihara, T., Kaneda, Y. and Hunt, J. C. R. (2013). Thin shear layers in high Reynolds number turbulence – DNS results. <em>Flow Turbul. Combust.</em> 91, 895. DOI: <a href=\"https://doi.org/10.1007/s10494-013-9499-z\">10.1007/s10494-013-9499-z</a>",
    "Miyauchi, T., Kang, S.-J. and Tanahashi, M. (2006). Coherent fine scale eddies in the logarithmic region of turbulent channel flows. <em>Fluid Mechanics and its Applications</em> 79, 71–80. DOI: <a href=\"https://doi.org/10.1007/1-4020-4181-0_7\">10.1007/1-4020-4181-0_7</a> (abstract only).",
    "Mouri, H., Hori, A. and Kawashima, Y. (2003). Vortex tubes in velocity fields of laboratory isotropic turbulence: dependence on the Reynolds number. <em>Phys. Rev. E</em> 67, 016305. DOI: <a href=\"https://doi.org/10.1103/PhysRevE.67.016305\">10.1103/PhysRevE.67.016305</a>",
    "Mouri, H., Hori, A. and Kawashima, Y. (2004). Vortex tubes in turbulence velocity fields at Reynolds numbers \\(Re_\\lambda\\simeq300\\)–1300. <em>Phys. Rev. E</em> 70, 066305. DOI: <a href=\"https://doi.org/10.1103/PhysRevE.70.066305\">10.1103/PhysRevE.70.066305</a>",
    "Mouri, H., Hori, A. and Kawashima, Y. (2007). Laboratory experiments for intense vortical structures in turbulence velocity fields. <em>Phys. Fluids</em> 19, 055101. DOI: <a href=\"https://doi.org/10.1063/1.2720827\">10.1063/1.2720827</a>",
    "Mouri, H. and Hori, A. (2009). Vortex tubes in turbulence velocity fields at high Reynolds numbers. <em>Fluid Dyn. Res.</em> 41, 021402. DOI: <a href=\"https://doi.org/10.1088/0169-5983/41/2/021402\">10.1088/0169-5983/41/2/021402</a>. The file in the LIT folder is the preprint, arXiv:<a href=\"https://arxiv.org/abs/0801.2276\">0801.2276</a>.",
    "Pirozzoli, S. (2009). A structural model for the vortex tubes of isotropic turbulence. <em>Theor. Comput. Fluid Dyn.</em> 23, 55–62. DOI: <a href=\"https://doi.org/10.1007/s00162-009-0092-y\">10.1007/s00162-009-0092-y</a>",
    "Pirozzoli, S. (2012). On the velocity and dissipation signature of vortex tubes in isotropic turbulence. <em>Physica D</em> 241, 202. DOI: <a href=\"https://doi.org/10.1016/j.physd.2011.03.005\">10.1016/j.physd.2011.03.005</a>",
    "Sassa, K. and Makita, H. (2005). Reynolds number dependence of elementary vortices in turbulence. In: <em>Engineering Turbulence Modelling and Experiments 6</em>, 431–440. DOI: <a href=\"https://doi.org/10.1016/B978-008044544-1/50041-8\">10.1016/B978-008044544-1/50041-8</a>",
    "Wang, Y., Tanahashi, M. and Miyauchi, T. (2007). Coherent fine scale eddies in turbulence transition of spatially-developing mixing layer. <em>Int. J. Heat Fluid Flow</em> 28, 1280–1290. DOI: <a href=\"https://doi.org/10.1016/j.ijheatfluidflow.2007.06.009\">10.1016/j.ijheatfluidflow.2007.06.009</a>",
    "Ghira, A. A., Vela-Martin, A. and Da Silva, C. B. (2024). Temporal vortex tracking in isotropic turbulence. <em>J. Phys.: Conf. Ser.</em> 2753, 012011. DOI: <a href=\"https://doi.org/10.1088/1742-6596/2753/1/012011\">10.1088/1742-6596/2753/1/012011</a>",
    "Elsinga, G. E., Ishihara, T. and Hunt, J. C. R. (2023). Intermittency across Reynolds numbers – the influence of large-scale shear layers on the scaling of the enstrophy and dissipation in homogeneous isotropic turbulence. <em>J. Fluid Mech.</em> 974, A17. DOI: <a href=\"https://doi.org/10.1017/jfm.2023.799\">10.1017/jfm.2023.799</a>",
    "Watanabe, T. and Nagata, K. (2023). The response of small-scale shear layers to perturbations in turbulence. <em>J. Fluid Mech.</em> 963, A31. DOI: <a href=\"https://doi.org/10.1017/jfm.2023.316\">10.1017/jfm.2023.316</a>",
    "Watanabe, T., Mori, T., Ishizawa, K. and Nagata, K. (2024). Scale dependence of local shearing motion in decaying turbulence generated by multiple-jet interaction. <em>J. Fluid Mech.</em> 997, A14. DOI: <a href=\"https://doi.org/10.1017/jfm.2024.727\">10.1017/jfm.2024.727</a>",
    "Enoki, R., Watanabe, T. and Nagata, K. (2023). Statistical properties of shear and nonshear velocity components in isotropic turbulence and turbulent jets. <em>Phys. Rev. Fluids</em> 8, 104602. DOI: <a href=\"https://doi.org/10.1103/PhysRevFluids.8.104602\">10.1103/PhysRevFluids.8.104602</a>",
    "Leung, T., Swaminathan, N. and Davidson, P. A. (2012). Geometry and interaction of structures in homogeneous isotropic turbulence. <em>J. Fluid Mech.</em> 710, 453. DOI: <a href=\"https://doi.org/10.1017/jfm.2012.373\">10.1017/jfm.2012.373</a>",
    "Okamoto, N., Yoshimatsu, K., Schneider, K., Farge, M. and Kaneda, Y. (2007). Coherent vortices in high resolution direct numerical simulation of homogeneous isotropic turbulence: a wavelet viewpoint. <em>Phys. Fluids</em> 19, 115109. DOI: <a href=\"https://doi.org/10.1063/1.2771661\">10.1063/1.2771661</a>",
    "Cherry, R. S. and Kwon, K.-Y. (1990). Transient shear stresses on a suspension cell in turbulence. <em>Biotechnol. Bioeng.</em> 36, 563–571. DOI: <a href=\"https://doi.org/10.1002/bit.260360603\">10.1002/bit.260360603</a>",
    "Wojtas, K., Orciuch, W., Wysocki, Ł. and Makowski, Ł. (2017). Modeling and experimental validation of subgrid scale scalar variance at high Schmidt numbers. <em>Chem. Eng. Res. Des.</em> 123, 141–151. DOI: <a href=\"https://doi.org/10.1016/j.cherd.2017.05.003\">10.1016/j.cherd.2017.05.003</a>",
]
i = t.index("<h2>References</h2>")
j = t.index("<ol", i)
k = t.index("</ol>", j)
head_end = t.index(">", j) + 1
items = re.findall(r'<li style="margin:8px 0">.*?</li>', t[head_end:k], flags=re.S)
items = [it for it in items if not it.startswith('<li style="margin:8px 0">Mouri, H. and Hori, A. Vortex tubes')]
for r in REFS:
    doi = re.search(r'DOI: <a href="https://doi.org/([^"]+)"', r).group(1)
    if not any(doi in it for it in items):
        items.append('<li style="margin:8px 0">%s</li>' % r)


def key(it):
    txt = re.sub(r"<[^>]+>", "", it)
    return unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode().lower()


items.sort(key=key)
t = t[:head_end] + "\n" + "\n".join(items) + "\n" + t[k:]

open(PAGE, "w", encoding="utf8", newline="\n").write(t)
print("restructured; references:", len(items), "; control chars:", len(re.findall(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", t)))
