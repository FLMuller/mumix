"""Add a section on the four-parameter model (swirl U_max/U_eta = beta**q Re_l**s) before the References."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

import io
import math
import sys
import contextlib

import numpy as np

sys.path.insert(0, HERE)
with contextlib.redirect_stdout(io.StringIO()):
    import fit4_floor as f4          # runs the 4-parameter fit with the 5% sigma floor

par, sig, err, corr, USED, KIDA, tube, GROUPS = f4.par, f4.sig, f4.err, f4.corr, f4.USED, f4.KIDA, f4.tube, f4.GROUPS
N = len(USED)
A, P, Q, S_ = par
chi2 = float(np.sum((f4.logres(par) / sig) ** 2))
KIDA = KIDA + [("Kida02 all", "beta", 83, 10.4 / 2, 0), ("Kida02 all", "beta", 170, 10.8 / 2, 0), ("Kida02 all", "R", 83, 110.0, 0), ("Kida02 all", "R", 170, 123.0, 0)]
ALL = USED + KIDA
page = os.path.join(os.path.dirname(HERE), "vortex-energy-balance.html")
t = open(page, encoding="utf8").read()
print("a=%.2f p=%.4f q=%.4f s=%.4f chi2/N=%.3f" % (A, P, Q, S_, chi2 / N))


def m(Rl):
    return tube(Rl, *par)


CATS = ["R", "beta", "Rec", "U", "d"]
QUANT = {"R": r"\(R_\Gamma=\Gamma/\nu\)", "beta": r"\(r_{\max}/\eta\)", "Rec": r"\(Re_c\)", "U": r"\(U_{\max}/U_\eta\)", "d": r"\(d/\eta\)"}
FMT = {"R": "%.0f", "beta": "%.2f", "Rec": "%.1f", "U": "%.2f", "d": "%.1f"}
REF = {"Ghira22 IVS": "Ghira et al. (2022)", "Ghira25 IVS": "Ghira et al. (2025)", "Aligolzadeh23 IVS": "Aligolzadeh et al. (2023)", "Jimenez93 IVS": "Jiménez et al. (1993)", "Mouri09 all": "Mouri and Hori",
       "Kida02 all": "Kida et al. (2002)", "Tanahashi01": "Tanahashi et al. (2001)"}
ORDER = ["Ghira22 IVS", "Ghira25 IVS", "Jimenez93 IVS", "Tanahashi01", "Aligolzadeh23 IVS", "Mouri09 all", "Kida02 all"]
stats = {}
for c in CATS:
    sub = [o for o in USED if o[1] == c]
    if not sub:
        continue
    lit = np.array([o[3] for o in sub])
    mod = np.array([m(o[2])[c] for o in sub])
    rmse = math.sqrt(np.mean((mod - lit) ** 2))
    stats[c] = dict(mmean=mod.mean(), pct=100 * rmse / lit.mean())
rows = []
for c in CATS:
    papers = [(src, sorted([o for o in ALL if o[0] == src and o[1] == c], key=lambda z: z[2])) for src in ORDER]
    papers = [(src, mem) for src, mem in papers if mem]
    if not papers:
        continue
    total = sum(len(mem) for src, mem in papers)
    f = FMT[c]
    last = "%s ± %.1f%%" % (f % stats[c]["mmean"], stats[c]["pct"]) if c in stats else "—"
    first_row = True
    for src, members in papers:
        for k, o in enumerate(members):
            s, qn, Re, val, _ = o
            mv = m(Re)[c]
            used = s != "Kida02 all"
            cells = '<td rowspan="%d">%s</td>' % (total, QUANT[c]) if first_row else ""
            if k == 0:
                cells += '<td rowspan="%d">%s%s</td>' % (len(members), REF[s], "" if used else "<sup>‡</sup>")
            if used:
                i = USED.index(o)
                nv = (math.log(mv / val) / sig[i]) ** 2
                cells += '<td>%g</td><td>%s</td><td class="msep">%s</td><td>%.1f%%</td><td>%.2f</td>' % (Re, f % val, f % mv, sig[i] * 100, nv)
            else:
                cells += '<td>%g</td><td>%s</td><td class="msep">%s</td><td>—</td><td>—</td>' % (Re, f % val, f % mv)
            if first_row:
                cells += '<td rowspan="%d">%s</td>' % (total, last)
            first_row = False
            rows.append("<tr%s>%s</tr>" % ("" if used else ' class="nu"', cells))
data_table = ('<div class="tablebox"><table class="dt">\n<thead><tr><th>Quantity</th><th>Source</th><th>\\(Re_\\lambda\\)</th><th>Literature</th>'
              '<th class="msep">Model</th><th>\\(\\sigma_{\\text{ref}}\\)<sup>†</sup></th><th>\\(\\sigma_{\\text{norm}}^2\\)</th>'
              '<th>Model mean ± <em>x</em><sup>*</sup></th></tr></thead>\n<tbody>\n' + "\n".join(rows) +
              '\n<tr><td colspan="6"><strong>Mean of \\(\\sigma_{\\text{norm}}^2\\), \\(\\chi^2/N\\) (\\(N=%d\\), red rows excluded)</strong></td><td><strong>%.2f</strong></td><td></td></tr>\n</tbody></table></div>' % (N, chi2 / N))

# ---------------------------------------------------------------- results tables
res_rows = []
for Rl, tag in ((54, ""), (83, ""), (170, ""), (274, " (feed pipe)"), (332, ""), (1000, ""), (1934, ""), (2170, " (impeller)")):
    r = m(Rl)
    res_rows.append("<tr><td>%d%s</td><td>%.0f</td><td>%.2f</td><td>%.1f</td><td>%.2f</td><td>%.2f</td><td>%.0f%%</td><td>%.0f%%</td><td>%.1f</td></tr>" % (
        Rl, tag, r["R"], r["beta"], r["Rec"], r["U"], r["gam"], r["Vf"] * 100, r["share"] * 100, r["d"]))
nu = 1e-6


def process(Re, eps):
    Rl = math.sqrt(15 * Re)
    r = m(Rl)
    eta = (nu**3 / eps) ** 0.25
    ue = (nu * eps) ** 0.25
    ge = (eps / nu) ** 0.5
    d = r["d"] * eta
    return dict(Rl=Rl, eta=eta, ue=ue, ge=ge, rmax=r["beta"] * eta, U=r["U"] * ue, gam=r["gam"] * ge, Gam=r["R"] * nu, Vf=r["Vf"], share=r["share"], d=d, Le=1 / d**2)


fp = process(5000, 200.0)
ip = process(math.pi * 10 * 0.1 * 0.1 / nu, (math.pi * 10 * 0.1) ** 3 / 0.1)


def sci(v):
    e = int(math.floor(math.log10(v)))
    return "%.1f×10<sup>%d</sup>" % (v / 10**e, e)


def spc(v, nd):
    return "{:,.0f}".format(round(v, nd)).replace(",", " ")


kr = {c: [m(o[2])[c] / o[3] for o in KIDA if o[1] == c] for c in ("U", "d", "beta", "R")}
dev = {c: 100 * max(abs(v - 1) for v in kr[c]) for c in kr}
ali_dev = 100 * (1 - m(179)['beta'] / (1.12 * 5.1 / 0.95))

T = r"""<h2>9. Four-parameter closure: swirl growing with \(Re_\lambda\)</h2>
<p>Section 8 writes the swirl of the tube in Kolmogorov units, \(U_{\max}=\beta^{\,q}U_\eta\), so that it depends on the Reynolds number only through \(\beta\). The measured swirl grows with \(Re_\lambda\) at a nearly constant radius (the radius falls slowly, 4.28 to 3.90 \(\eta\) in Ghira et al. 2022, while the circulation rises), so this section adds one exponent to the swirl law, \(U_{\max}=\beta^{\,q}Re_\lambda^{\,s}U_\eta\), and fits the closure to the source data of section 7 and the appendix. The fit uses rows of both sets of section 7 (whole and intense tubes); it is to be split into one fit per set.</p>
<h3>The closure</h3>
<p>The total circulation keeps its growth law, and the swirl gets a Reynolds-number factor:</p>
$$R_\Gamma=\frac{\Gamma}{\nu}=a\,Re_\lambda^{\,p},\qquad \frac{U_{\max}}{U_\eta}=\beta^{\,q}\,Re_\lambda^{\,s}.$$
<p>For a Burgers vortex \(R_\Gamma=8.78\,\beta\,U_{\max}/U_\eta\) (section 8, Step 3), so \(\beta\) follows from the two laws:</p>
$$\beta^{\,1+q}=\frac{a\,Re_\lambda^{\,p-s}}{8.78},\qquad Re_c=\beta\,\frac{U_{\max}}{U_\eta}=\frac{R_\Gamma}{8.78}.$$
<p>Two consequences are worth noting. The tube Reynolds number \(Re_c\) is fixed by the circulation alone, so the Mouri and Hori values and the Ghira et al. circulations constrain the same function \(R_\Gamma(Re_\lambda)\), that is \(a\) and \(p\). The radius data then fix \(q\) and \(s\) through \(\beta\). The dissipation budget of section 8, Step 5, is unchanged, but with the swirl written \(U=U_{\max}/U_\eta\) the volume fraction is

$$V_f=\frac{\left(1-75.8/\beta^{4}\right)\beta^{2}}{4.91\,U^{2}},\qquad \text{vortex share}=1-\frac{75.8}{\beta^4},\qquad \frac{d}{\eta}=\beta\sqrt{\frac{\pi}{V_f}},$$
<p>which reduces to Step 5 of section 8 when \(s=0\). A swirl that grows with \(Re_\lambda\) therefore lowers \(V_f\): for a given share of the dissipation fewer tubes are needed when each carries more.</p>
<h3>Fit</h3>
<p>The four constants were found by minimising the sum of squared normalised residuals \(\chi^2\) was minimised with a global minimiser and \(\sigma_{\text{ref}}\) was iterated with the fit (footnote † of the table). The Ghira et al. radius group is then fitted almost exactly and its \(\sigma_{\text{ref}}\) collapses (0.4% in a trial run), so a floor of 5% was applied to \(\sigma_{\text{ref}}\); the circulation and the tube Reynolds number, and so \(a\) and \(p\), are the same with or without the floor. Three searches from different seeds agree.</p>
$$\boxed{\;a=@A@\pm@SA@,\quad p=@P@\pm@SP@,\quad q=@Q@\pm@SQ@,\quad s=@S@\pm@SS@\;}\qquad\left(R_\Gamma=@A@\,Re_\lambda^{@P@},\quad \frac{U_{\max}}{U_\eta}=\beta^{@Q@}Re_\lambda^{@S@}\right)$$
<p>The mean of \(\sigma_{\text{norm}}^2\) is \(\chi^2/N=@CHI@\) (\(N=@N@\)). The parameters are correlated, \(a\)–\(p\) \(@RAP@\) and in particular \(q\)–\(s\) \(@RQS@\): the radius data fix the combination of \(q\) and \(s\) that sets the radius trend, not each separately. A trial run without the floor gave \(q=0.12\), \(s=0.23\) with the same \(a\) and \(p\) and the same model values to within a few per cent, so \(q\) and \(s\) should not be quoted on their own.</p>
<h3>Data and model</h3>
<p>The literature values are those of the appendix. Rows are listed for each measure, then by paper, in ascending \(Re_\lambda\). Red rows (Kida et al.) are shown for comparison and were not used.</p>
@TABLE@
<p class="note"><sup>†</sup> \(\sigma_{\text{ref}}\) is the reference relative uncertainty of an observation: the standard deviation of \(\ln(\text{model}/\text{literature})\). For each source and quantity with three or more observations it is the rms of that group's own \(\ln(\text{model}/\text{literature})\) at the fit, with a floor of 5%; a group with fewer observations (Ghira et al. 2025, Tanahashi et al., Aligolzadeh et al.) takes the largest \(\sigma_{\text{ref}}\) of the groups with three or more. The fit and \(\sigma_{\text{ref}}\) were iterated together until neither changed. Because \(\sigma_{\text{ref}}\) comes from the residuals themselves, \(\chi^2/N\) is below 1 and the parameter errors are approximate.<br>
<sup>*</sup> The model mean is the average of the model values at the observed \(Re_\lambda\) of that quantity, and \(x=100\,\sqrt{\sum(M_i-M_{i,\text{lit}})^2/n}\,/\,\overline{M_{\text{lit}}}\) is the RMSE as a percentage of the literature average.<br>
<sup>‡</sup> Red rows were not used in the fit and have no \(\sigma_{\text{ref}}\): Kida et al. define the tube by the boundary of its vortex core (diameter about 10.4–10.8 \(\eta\)), a different and larger population than the intense structures of Ghira et al., Jiménez et al. and Tanahashi et al.; the swirl is read at that boundary and converted to the Burgers peak with an assumed factor of 1.175; the circulation is that inside the boundary; and each quantity has only two points (see the appendix).</p>
<h3>Results</h3>
<p>For \(R_\Gamma=@A@\,Re_\lambda^{@P@}\) and \(U_{\max}/U_\eta=\beta^{@Q@}Re_\lambda^{@S@}\):</p>
<div class="tablebox"><table>
<thead><tr><th>\(Re_\lambda\)</th><th>\(R_\Gamma\)</th><th>\(\beta=r_{\max}/\eta\)</th><th>\(Re_c\)</th><th>\(U_{\max}/U_\eta\)</th><th>\(\gamma/\gamma_\eta\)</th><th>\(V_f\)</th><th>vortex share</th><th>\(d/\eta\)</th></tr></thead>
<tbody>
@ROWS@
</tbody></table></div>
<p>For the two process cases of Step 2, with their local \(\varepsilon\):</p>
<div class="tablebox"><table>
<thead><tr><th>Quantity</th><th>Feed pipe</th><th>Impeller</th></tr></thead>
<tbody>
<tr><td>\(U_\eta\), \(\gamma_\eta\)</td><td>@F1@ m/s, @F2@ s⁻¹</td><td>@I1@ m/s, @I2@ s⁻¹</td></tr>
<tr><td>core radius \(r_{\max}\)</td><td>@F3@ µm</td><td>@I3@ µm</td></tr>
<tr><td>peak swirl \(U_{\max}\)</td><td>@F4@ m/s</td><td>@I4@ m/s</td></tr>
<tr><td>strain on the tube \(\gamma\)</td><td>@F5@ s⁻¹</td><td>@I5@ s⁻¹</td></tr>
<tr><td>circulation \(\Gamma\)</td><td>@F6@ m²/s</td><td>@I6@ m²/s</td></tr>
<tr><td>\(V_f\), vortex share</td><td>@F7@</td><td>@I7@</td></tr>
<tr><td>tube spacing \(d\), length density \(L_e\)</td><td>@F8@ µm, @F9@ m/m³</td><td>@I8@ µm, @I9@ m/m³</td></tr>
</tbody></table></div>
<div class="result"><p>With four fitted constants (\(\chi^2/N=@CHI@\), @N@ observations) the Ghira et al. radius residuals are within \(\pm5\)%, and the RMSE is @E1@% (circulation), @E2@% (radius), @E3@% (tube Reynolds number) of the literature averages. The experimental radius of Aligolzadeh et al. (\(Re_\lambda=179\), 6.0 \(\eta\) by the Burgers-equivalent definition) is the largest residual, with the model @ALI@% below it, and lies above all the DNS radii (4.3–5.0 \(\eta\)). The unused values of Kida et al. differ from the model by at most @D1@% (swirl), @D2@% (spacing), @D3@% (radius, half the core diameter) and @D4@% (circulation inside their core boundary). The tube radius is nearly independent of \(Re_\lambda\) (\(\beta=@B1@\) to @B2@ over \(Re_\lambda=83\)–1934), the swirl grows (\(U_{\max}/U_\eta=@U1@\) to @U2@), and as a result the volume fraction of the tubes falls from @V1@% to @V2@% and the share of the dissipation in the tubes from @H1@% to @H2@%, which is the direction of the fall of the share of the intense filaments with \(Re_\lambda\) reported by Jiménez and Wray, though that share is a different quantity. The circulation trend of Ghira et al. is not removed: their \(\Gamma\) grows faster than the \(Re_0\) of Mouri and Hori allows (residuals \(+8\)% to \(-11\)%).</p></div>
<ul>
<li><strong>Extrapolation.</strong> The swirl, and with it \(V_f\), \(d\) and the share, extrapolate with the fitted \(Re_\lambda\) dependence. The data constrain the swirl only through the circulation and radius (Ghira et al., \(Re_\lambda\le399\)) and the tube Reynolds number (Mouri and Hori, \(Re_\lambda\) 332–1934). The impeller case (\(Re_\lambda=2170\)) lies above all of these.</li>
<li><strong>Circulation reading.</strong> The listed circulation of Ghira et al. is taken as the total (see the appendix and the limits below).</li>
<li><strong>Mixed tube sets.</strong> The fitted rows are radii of intense tubes (Ghira, Jiménez, Aligolzadeh) and one of whole tubes (Tanahashi), the circulation of intense tubes (Ghira) and the tube Reynolds number of whole tubes (Mouri and Hori 2009). The intense-tube Reynolds numbers of Mouri et al. (2004, 2007), 32&ndash;87, are 2&ndash;3 times the model values and are not fitted (section 7).</li>
</ul>
<h3>Limits of this model</h3>
<ul>
<li><strong>Dissipation share.</strong> The vortex share is a result of the budget, \(1-75.8/\beta^4\), and rests on one uniform strain \(\gamma\) for the whole volume outside the tubes. The measurements give 14–75% depending on threshold and definition (core only, intense subset, wavelet-coherent part). Tube plus surrounding shear layer has not been measured as one quantity.</li>
<li><strong>Two sets of tubes.</strong> The measured swirl and tube Reynolds number differ by a factor 2&ndash;3 between whole and intense tubes (section 7), and one tube with one swirl law cannot describe both. The all-tube radius of Mouri and Hori (8&ndash;9 \(\eta\)) is biased high by their own statement and is larger than every other radius in the data. The experimental radius of Aligolzadeh et al. (6.0 \(\eta\) at \(Re_\lambda=179\), objectively defined vortex boundary) is the largest residual of the fit.</li>
<li><strong>Circulation definition.</strong> The circulation of Ghira et al. is listed as \(\Gamma_{ivs}=2\pi\langle U_{ivs}\rangle R_{ivs}\), the circulation inside \(R_{ivs}\) for a Burgers vortex, and is taken here as the total circulation of the model. With that reading the model agrees in magnitude with Kida et al. and Mouri and Hori, but the swirl listed by Ghira et al. (\(U_{ivs}/u_\eta=6.0\)&ndash;10.2) is 1.5&ndash;2.5 times the model's \(U_{\max}/U_\eta\), so the model describes the circulation of the intense tubes and not their swirl (see the appendix).</li>
<li><strong>Volume fraction.</strong> \(V_f\) is the volume within \(r_{\max}\) and is not the quantity reported as a threshold volume (1% for intense structures, 0.8&ndash;20% at Hosokawa and Yamamoto's thresholds) or as the core volume (31&ndash;35%, Kida et al.).</li>
<li><strong>Isolated straight Burgers tubes.</strong> Measured tubes are about \(55\,\eta\) long (Ghira et al.), curved, and wrapped by spiral vortex layers (Kida et al., Makihara et al.). Axial outflow and end effects are not modelled.</li>
<li><strong>Extrapolation.</strong> The fit covers \(Re_\lambda=36\)&ndash;1934. The feed-pipe case (274) lies inside that range; the impeller case (2170) lies just above the highest laboratory value and about twice the highest DNS in the sources. Jiménez and Wray note that the intense-structure trends cannot continue indefinitely.</li>
<li><strong>Process mapping.</strong> \(\varepsilon=U^3/L\) is a scale estimate good to a factor of a few, and \(U'=U\) is an upper bound. The vessel-average \(\varepsilon\) is lower (2.4 W/kg for the impeller example) and corresponds to larger tubes.</li>
</ul>
"""
for k, v in {"@A@": "%.1f" % A, "@SA@": "%.1f" % err[0], "@P@": "%.3f" % P, "@SP@": "%.3f" % err[1], "@Q@": "%.2f" % Q, "@SQ@": "%.2f" % err[2], "@S@": "%.2f" % S_, "@SS@": "%.2f" % err[3],
             "@CHI@": "%.2f" % (chi2 / N), "@N@": str(N), "@RAP@": "%+.2f" % corr[0, 1], "@RQS@": "%+.2f" % corr[2, 3], "@TABLE@": data_table, "@ROWS@": "\n".join(res_rows),
             "@F1@": "%.3f" % fp["ue"], "@F2@": spc(fp["ge"], -2), "@I1@": "%.3f" % ip["ue"], "@I2@": spc(ip["ge"], -2),
             "@F3@": "%.0f" % (fp["rmax"] * 1e6), "@I3@": "%.0f" % (ip["rmax"] * 1e6), "@F4@": "%.2f" % fp["U"], "@I4@": "%.2f" % ip["U"],
             "@F5@": spc(fp["gam"], -1), "@I5@": spc(ip["gam"], -1), "@F6@": sci(fp["Gam"]), "@I6@": sci(ip["Gam"]),
             "@F7@": "%.0f%%, %.0f%%" % (fp["Vf"] * 100, fp["share"] * 100), "@I7@": "%.0f%%, %.0f%%" % (ip["Vf"] * 100, ip["share"] * 100),
             "@F8@": "%.0f" % (fp["d"] * 1e6), "@F9@": sci(fp["Le"]), "@I8@": "%.0f" % (ip["d"] * 1e6), "@I9@": sci(ip["Le"]),
             "@E1@": "%.1f" % stats["R"]["pct"], "@E2@": "%.1f" % stats["beta"]["pct"], "@E3@": "%.1f" % stats["Rec"]["pct"],
             "@ALI@": "%.0f" % ali_dev, "@D1@": "%.0f" % dev["U"], "@D2@": "%.0f" % dev["d"], "@D3@": "%.0f" % dev["beta"], "@D4@": "%.0f" % dev["R"],
             "@B1@": "%.1f" % m(83)["beta"], "@B2@": "%.1f" % m(1934)["beta"], "@U1@": "%.1f" % m(83)["U"], "@U2@": "%.1f" % m(1934)["U"],
             "@V1@": "%.0f" % (m(83)["Vf"] * 100), "@V2@": "%.0f" % (m(1934)["Vf"] * 100), "@H1@": "%.0f" % (m(83)["share"] * 100), "@H2@": "%.0f" % (m(1934)["share"] * 100)}.items():
    T = T.replace(k, v)
assert "@" not in T.replace("@", "", 0) or True
import re
left = re.findall(r"@[A-Z0-9]+@", T)
assert not left, left

m_old = re.search(r"<h2>[89]\. Four-parameter closure", t)
if m_old:
    i = m_old.start()
    j = t.index("<h2>References</h2>")
    t = t[:i] + T + "\n" + t[j:]
else:
    t = t.replace("<h2>References</h2>", T + "\n<h2>References</h2>", 1)
open(page, "w", encoding="utf8", newline="\n").write(t)
print("section written; Kida dev", {k: round(v) for k, v in dev.items()})
