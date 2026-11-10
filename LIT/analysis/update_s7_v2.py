"""Section 7 rewrite, version 2: three-parameter fit without Kida et al. (shown in the data table, red, not used)."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
import sys

sys.path.insert(0, HERE)

import math
import re
import sys

import numpy as np

OLD = HERE
sys.path.insert(0, OLD)
import iterate_sigma as it

f3 = it.f3
ALL = list(it.OBS)
USED = [o for o in ALL if o[0] != "Kida02 all"]
# Ghira et al. (2025), Table 2: R_ivs/eta = 4.29, 4.23 at Re_lambda = 54; r_max = 1.12 R_ivs/0.97 (ratio R_ivs/R_B taken as the 2022 mean)
NEW = [("Ghira25 IVS", "beta", 54, 1.12 * 4.29 / 0.97, 0.12), ("Ghira25 IVS", "beta", 54, 1.12 * 4.23 / 0.97, 0.12)]
USED += NEW
ALL += NEW
it.NAMES[("Ghira25 IVS", "beta")] = "Ghira25 r_max"
KIDA = [o for o in ALL if o[0] == "Kida02 all"]
# Kida et al. Table 2: core diameter D/l_K = 10.4, 10.8 (radius D/2) and circulation Gamma/nu = 110, 123 at Re_lambda = 83, 170
KIDA += [("Kida02 all", "beta", 83, 10.4 / 2, 0), ("Kida02 all", "beta", 170, 10.8 / 2, 0), ("Kida02 all", "R", 83, 110.0, 0), ("Kida02 all", "R", 170, 123.0, 0)]
ALL += KIDA[-4:]
it.OBS = USED
it.GROUPS = {}
for i, o in enumerate(USED):
    it.GROUPS.setdefault((o[0], o[1]), []).append(i)
OBS, GROUPS = USED, it.GROUPS
N = len(OBS)
page = os.path.join(os.path.dirname(HERE), "vortex-energy-balance.html")
t = open(page, encoding="utf8").read()

# ---------------------------------------------------------------- fit with iterated sigma_ref
sig = np.array([o[4] for o in OBS], float)
par = np.array([81.0, 0.137, 0.89])
for iteration in range(1, 300):
    new_par, _ = it.fit(sig, True, par)
    r = it.logres(new_par, True)
    big = {g: math.sqrt(np.mean(r[i] ** 2)) for g, i in GROUPS.items() if len(i) >= 3}
    new = sig.copy()
    for g, idx in GROUPS.items():
        new[idx] = big[g] if g in big else max(big.values())
    change = max(abs(new_par - par).max(), abs(new - sig).max())
    par, sig = new_par, new
    if change < 1e-7:
        break
A, P, Q = par
res = it.logres(par, True)
chi2N = float(np.sum((res / sig) ** 2)) / N


def chi(p_):
    rr = it.logres(p_, True)
    return 1e9 if rr is None else float(np.sum((rr / sig) ** 2))


h = np.array([0.5, 0.005, 0.01])
H = np.zeros((3, 3))
for i in range(3):
    for j in range(3):
        ei = np.zeros(3); ei[i] = h[i]
        ej = np.zeros(3); ej[j] = h[j]
        H[i, j] = (chi(par + ei + ej) - chi(par + ei - ej) - chi(par - ei + ej) + chi(par - ei - ej)) / (4 * h[i] * h[j])
cov = np.linalg.inv(H / 2)
err = np.sqrt(np.diag(cov))
corr = cov / np.outer(err, err)
print("N=%d iterations %d  a=%.3f p=%.4f q=%.4f chi2/N=%.3f errors %s" % (N, iteration, A, P, Q, chi2N, np.round(err, 4)))
print("corr", np.round(corr, 2).tolist())
print({it.NAMES[g]: round(float(sig[idx[0]]), 4) for g, idx in GROUPS.items()})


def m(Rl):
    return f3.model(Rl, A, P, Q)


CATS = ["R", "beta", "Rec", "U", "d"]
QUANT = {"R": r"\(R_\Gamma=\Gamma/\nu\)", "beta": r"\(r_{\max}/\eta\)", "Rec": r"\(Re_c\)", "U": r"\(U_{\max}/U_\eta\)", "d": r"\(d/\eta\)"}
FMT = {"R": "%.0f", "beta": "%.2f", "Rec": "%.1f", "U": "%.2f", "d": "%.1f"}
REF = {"Ghira22 IVS": "Ghira et al. (2022)", "Ghira25 IVS": "Ghira et al. (2025)", "Jimenez93 IVS": "Jiménez et al. (1993)", "Mouri09 all": "Mouri and Hori",
       "Kida02 all": "Kida et al. (2002)", "Tanahashi01": "Tanahashi et al. (2001)"}
ORDER = ["Ghira22 IVS", "Ghira25 IVS", "Jimenez93 IVS", "Tanahashi01", "Mouri09 all", "Kida02 all"]
stats = {}
for c in CATS:
    sub = [o for o in USED if o[1] == c]
    if not sub:
        continue
    lit = np.array([o[3] for o in sub])
    mod = np.array([m(o[2])[c] for o in sub])
    rmse = math.sqrt(np.mean((mod - lit) ** 2))
    stats[c] = dict(n=len(sub), mean=lit.mean(), mmean=mod.mean(), rmse=rmse, pct=100 * rmse / lit.mean())
    print(c, {k: round(float(v), 3) for k, v in stats[c].items()})
kida_ratio = {}
for c in ("U", "d", "R", "beta"):
    rr = [m(o[2])[c] / o[3] for o in KIDA if o[1] == c]
    kida_ratio[c] = (min(rr), max(rr))
print("Kida ratios", kida_ratio)
allrel = np.array([math.exp(x) - 1 for x in res])
print("overall rms relative %.1f%%, max %.1f%%" % (100 * math.sqrt(np.mean(allrel**2)), 100 * np.abs(allrel).max()))

# ---------------------------------------------------------------- data table
rows = []
for c in CATS:
    papers = [(src, sorted([o for o in ALL if o[0] == src and o[1] == c], key=lambda z: z[2])) for src in ORDER]
    papers = [(src, mem) for src, mem in papers if mem]
    if not papers:
        continue
    total = sum(len(mem) for src, mem in papers)
    f = FMT[c]
    if c in stats:
        last = "%s ± %.1f%%" % (f % stats[c]["mmean"], stats[c]["pct"])
    else:
        last = "—"
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
                cells += "<td>%g</td><td>%s</td><td>%s</td><td>%.1f%%</td><td>%.2f</td>" % (Re, f % val, f % mv, sig[i] * 100, nv)
            else:
                cells += "<td>%g</td><td>%s</td><td>%s</td><td>—</td><td>—</td>" % (Re, f % val, f % mv)
            if first_row:
                cells += '<td rowspan="%d">%s</td>' % (total, last)
            first_row = False
            rows.append('<tr%s>%s</tr>' % ("" if used else ' class="nu"', cells))
tot = float(np.sum((res / sig) ** 2))
data_table = ('<div class="tablebox"><table class="dt">\n<thead><tr><th>Quantity</th><th>Source</th><th>\\(Re_\\lambda\\)</th><th>Literature</th>'
              '<th>Model</th><th>\\(\\sigma_{\\text{ref}}\\)<sup>†</sup></th><th>\\(\\sigma_{\\text{norm}}^2\\)</th>'
              '<th>Model mean ± <em>x</em><sup>*</sup></th></tr></thead>\n<tbody>\n' + "\n".join(rows) +
              '\n<tr><td colspan="6"><strong>Mean of \\(\\sigma_{\\text{norm}}^2\\), \\(\\chi^2/N\\) (\\(N=%d\\), red rows excluded)</strong></td><td><strong>%.2f</strong></td><td></td></tr>\n</tbody></table></div>' % (N, tot / N))
footnotes = (r"""<p class="note"><sup>†</sup> \(\sigma_{\text{ref}}\) is the reference relative uncertainty of an observation: the standard deviation of \(\ln(\text{model}/\text{literature})\). For each source and quantity with three or more observations it is the rms of that group's own \(\ln(\text{model}/\text{literature})\) at the fit; a group with fewer observations (Ghira et al. 2025, Tanahashi et al.) takes the largest \(\sigma_{\text{ref}}\) of the groups with three or more. Starting from assumed values of 12–25%%, the fit and \(\sigma_{\text{ref}}\) were iterated together (fit, recompute \(\sigma_{\text{ref}}\), refit) until neither changed (%d iterations). Because \(\sigma_{\text{ref}}\) comes from the residuals themselves, \(\chi^2/N\) is close to 1 by construction and the parameter errors of Step 7 are approximate.<br>
<sup>*</sup> The model mean is the average of the model values at the observed \(Re_\lambda\) of that quantity, and \(x=100\,\sqrt{\sum(M_i-M_{i,\text{lit}})^2/n}\,/\,\overline{M_{\text{lit}}}\) is the RMSE as a percentage of the literature average.<br>
<sup>‡</sup> Red rows are shown for comparison and were not used in the fit, so they have no \(\sigma_{\text{ref}}\). Kida et al. define a tube by the boundary of its vortex core (diameter about 10.4–10.8 \(\eta\)), which is a different and larger population from the intense structures of Ghira et al., Jiménez et al. and Tanahashi et al. The model tube is calibrated on the latter, so a comparison with their swirl and spacing tests the definition of the tube as much as the model. Their radius is half the core diameter \(D\) (Table 2: \(D/\eta=10.4\) and 10.8), and their circulation \(\Gamma/\nu=110\) and 123 is that inside the core boundary, not the total of a Burgers vortex. The swirl is measured at the core boundary and converted to the Burgers peak with an assumed factor of 1.175, the spacing follows from their core volume fraction and diameter, and each quantity has only two points (\(Re_\lambda=83\) and 170), too few to set a \(\sigma_{\text{ref}}\) of its own.</p>
""" % iteration)

S7 = (r"""<h3>Step 7: fit of \(a\), \(p\) and \(q\)</h3>
<p>The three constants of the closure, \(R_\Gamma=a\,Re_\lambda^{\,p}\) and \(U_{\max}=\beta^{\,q}U_\eta\), were found by minimising the sum of squared normalised residuals
$$\chi^2(a,p,q)=\sum_{i=1}^{N}\left[\frac{\ln\left(\text{model}_i/\text{literature}_i\right)}{\sigma_{\text{ref},i}}\right]^2,$$
where \(\sigma_{\text{ref},i}\) is the reference relative uncertainty of observation \(i\) (footnote † to the data table). The minimum was located with a global minimiser (differential evolution) and the uncertainties are from the curvature of \(\chi^2\) at the minimum (\(\Delta\chi^2=1\)). The \(N=@N@\) observations (Ghira et al. 2022 and 2025, Jiménez et al., Tanahashi et al. and Mouri and Hori), with the model value and \(\sigma_{\text{norm}}^2\) of each, are tabulated below; the swirl and spacing of Kida et al. are listed there too but were not used.</p>
$$\boxed{\;a=@A@\pm@SA@,\qquad p=@P@\pm@SP@,\qquad q=@Q@\pm@SQ@\;}\qquad\left(R_\Gamma=@A@\,Re_\lambda^{@P@},\quad U_{\max}=\beta^{@Q@}U_\eta,\quad Re_c=\beta^{@Q1@}\right)$$
<p>The mean of \(\sigma_{\text{norm}}^2\) is \(\chi^2/N=@CHI@\). The parameters are correlated: \(a\) and \(p\) strongly (\(\rho_{ap}=@RAP@\), because \(a\,Re_\lambda^{p}\) is what the circulation data constrain, \(R_\Gamma=@R200@\) at \(Re_\lambda=200\)), \(a\) and \(q\) with \(\rho_{aq}=@RAQ@\), \(p\) and \(q\) with \(\rho_{pq}=@RPQ@\). The fitted exponent \(p=@P@\) lies close to the measured growth of the circulation Reynolds number with \(Re_\lambda\) (0.16–0.28, Step 4) and is well determined by the Ghira et al. circulations and the Mouri and Hori tube Reynolds numbers. Without the swirl data of Kida et al., \(q\) is set by the tube Reynolds numbers of Mouri and Hori together with the radii.</p>
""")
for k, v in {"@N@": str(N), "@A@": "%.1f" % A, "@SA@": "%.1f" % err[0], "@P@": "%.3f" % P, "@SP@": "%.3f" % err[1], "@Q@": "%.3f" % Q, "@SQ@": "%.3f" % err[2],
             "@Q1@": "%.3f" % (1 + Q), "@CHI@": "%.2f" % chi2N, "@RAP@": "%+.2f" % corr[0, 1], "@RAQ@": "%+.2f" % corr[0, 2], "@RPQ@": "%+.2f" % corr[1, 2],
             "@R200@": "%.0f" % (A * 200**P)}.items():
    S7 = S7.replace(k, v)

S7D = r"""<h3>Data used in the fit</h3>
<p>Rows are listed for each measure, then by paper, in ascending \(Re_\lambda\). Literature values are as given in the sources, converted to the model's quantities as follows. Ghira et al.: \(R_\Gamma=Re_\Gamma Re_\lambda^{1/2}\) from their Table III, and \(r_{\max}=1.12\,R_{ivs}/(R_{ivs}/R_B)\). Jiménez et al.: \(r_{\max}=1.12\times\) the 1/e radius of Table 3. Tanahashi et al.: \(r_{\max}=D/2\) with \(D=9\,\eta\), placed at \(Re_\lambda=200\) (the paper gives no single value). Mouri and Hori: \(Re_0\) of Table 2 taken as \(Re_c\). Kida et al. (not used): swirl at the core boundary multiplied by 1.175 to give the peak swirl of a Burgers vortex (60% of the enstrophy inside the core), and the spacing from \(1/\sqrt{L_e}\) with \(L_e=V_{\text{core}}/(V\pi D^2/4)\). How \(\sigma_{\text{norm}}^2\) is obtained: for observation \(i\) the model is compared with the literature value as a log-ratio, \(\ln(M_i/M_{i,\text{lit}})\), so that an excess of 10% and a shortfall of 10% weigh about the same and quantities of different size (\(R_\Gamma\approx170\), \(r_{\max}/\eta\approx4.6\)) are comparable. That log-ratio is divided by \(\sigma_{\text{ref},i}\), the reference uncertainty of the observation (footnote †), giving the normalised residual \(\sigma_{\text{norm},i}=\ln(M_i/M_{i,\text{lit}})/\sigma_{\text{ref},i}\), the miss in units of the expected scatter. The column lists its square, \(\sigma_{\text{norm},i}^2\). Their sum over the \(N=@N@\) observations is \(\chi^2\) and their mean is \(\chi^2/N\), the quantity minimised in the fit; a value of 1 means the model misses that observation by exactly \(\sigma_{\text{ref}}\).</p>
""".replace("@N@", str(N)) + data_table + "\n" + footnotes

# ---------------------------------------------------------------- Step 8 (same layout as before)
res_rows = []
for Rl, tag in ((83, ""), (170, ""), (274, " (feed pipe)"), (332, ""), (1000, ""), (1934, ""), (2170, " (impeller)")):
    r = m(Rl)
    res_rows.append("<tr><td>%d%s</td><td>%.0f</td><td>%.2f</td><td>%.1f</td><td>%.1f</td><td>%.2f</td><td>%.0f%%</td><td>%.0f%%</td><td>%.1f</td></tr>" % (
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


S8 = r"""<h3>Step 8: results</h3>
<p>For \(R_\Gamma=@A@\,Re_\lambda^{@P@}\) and \(q=@Q@\):</p>
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
"""
for k, v in {"@A@": "%.1f" % A, "@P@": "%.3f" % P, "@Q@": "%.3f" % Q, "@ROWS@": "\n".join(res_rows),
             "@F1@": "%.3f" % fp["ue"], "@F2@": spc(fp["ge"], -2), "@I1@": "%.3f" % ip["ue"], "@I2@": spc(ip["ge"], -2),
             "@F3@": "%.0f" % (fp["rmax"] * 1e6), "@I3@": "%.0f" % (ip["rmax"] * 1e6), "@F4@": "%.2f" % fp["U"], "@I4@": "%.2f" % ip["U"],
             "@F5@": spc(fp["gam"], -1), "@I5@": spc(ip["gam"], -1), "@F6@": sci(fp["Gam"]), "@I6@": sci(ip["Gam"]),
             "@F7@": "%.0f%%, %.0f%%" % (fp["Vf"] * 100, fp["share"] * 100), "@I7@": "%.0f%%, %.0f%%" % (ip["Vf"] * 100, ip["share"] * 100),
             "@F8@": "%.0f" % (fp["d"] * 1e6), "@F9@": sci(fp["Le"]), "@I8@": "%.0f" % (ip["d"] * 1e6), "@I9@": sci(ip["Le"])}.items():
    S8 = S8.replace(k, v)

r83, r170, r332, r1934 = m(83), m(170), m(332), m(1934)


def ratio_range(keys, pool=ALL):
    rr = [m(Re)[qn] / val for s, qn, Re, val, sg in pool if (s, qn) in keys]
    return min(rr), max(rr)


lo_b, hi_b = ratio_range({("Ghira22 IVS", "beta"), ("Jimenez93 IVS", "beta"), ("Tanahashi01", "beta")})
lo_R, hi_R = ratio_range({("Ghira22 IVS", "R")})
lo_c, hi_c = ratio_range({("Mouri09 all", "Rec")})

RESULT = (r"""<div class="result"><p>With three fitted constants (\(\chi^2/N=%.2f\), %d observations) the model reproduces the intense-tube radius and circulation of Ghira et al., Jiménez et al. and Tanahashi et al. and the tube Reynolds number of Mouri and Hori. The RMSE is %.1f%% (circulation), %.1f%% (radius) and %.1f%% (tube Reynolds number) of the literature averages, across \(Re_\lambda=36\)–1934. The values of Kida et al., not used in the fit, differ from the model by %.0f%% (swirl), %.0f%% (spacing), %.0f%% (radius, half their core diameter) and %.0f%% (circulation inside their core boundary). The volume fraction of the cylinders is %.0f–%.0f%% and their separation about \(%.0f\,\eta\). The main disagreement is the dissipation: the model puts %.0f–%.0f%% of it in the tubes, which matches the 80%% held by the vorticity region above the rms value (25%% of the volume, Jiménez et al.) and the 75%% of Hosokawa and Yamamoto, but is above core-only measurements and the intense subset.</p></div>
""" % (chi2N, N, stats["R"]["pct"], stats["beta"]["pct"], stats["Rec"]["pct"],
       *[100 * max(abs(kida_ratio[c][0] - 1), abs(kida_ratio[c][1] - 1)) for c in ("U", "d", "beta", "R")],
       m(83)["Vf"] * 100, m(1934)["Vf"] * 100, m(83)["d"], m(83)["share"] * 100, m(1934)["share"] * 100))

# ---------------------------------------------------------------- splice and prose
i7 = t.index("<h3>Step 7: fit of \\(a\\), \\(p\\) and \\(q\\)</h3>")
iL = t.index("<h3>Limits of this model</h3>")
t = t[:i7] + S7 + S7D + "\n" + S8 + "\n" + RESULT + "\n" + t[iL:]


def rep(old, new):
    global t
    assert t.count(old) == 1, (t.count(old), old[:60])
    t = t.replace(old, new)


if ".dt tr.nu" not in t:
    rep(".dt th, .dt td { text-align: center; vertical-align: middle; }",
        ".dt th, .dt td { text-align: center; vertical-align: middle; }\n.dt tr.nu td { background: rgba(214, 69, 65, 0.25); }")
t = re.sub(r"8\.78\\times8\^\{[0-9.]+\}\\approx[0-9]+", lambda _: r"8.78\times8^{%.2f}\approx%.0f" % (1 + Q, round(8.78 * 8 ** (1 + Q), -1)), t, count=1)

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


swap(r"\(r_{\max}/\eta\) (intense", "%.1f (83), %.1f (170), %.1f (332)" % (r83["beta"], r170["beta"], r332["beta"]), "fitted; ratio %.2f–%.2f" % (lo_b, hi_b))
swap(r"Strain", "%.2f (83), %.2f (170), %.2f (332)" % (r83["gam"], r170["gam"], r332["gam"]))
swap(r"Circulation", "%.0f (83), %.0f (170), %.0f (332), %.0f (1934)" % (r83["R"], r170["R"], r332["R"], r1934["R"]), "fitted; ratio %.2f–%.2f" % (lo_R, hi_R))
swap(r"Tube Reynolds", "%.1f (83) → %.1f (1934)" % (r83["Rec"], r1934["Rec"]), "fitted; ratio %.2f–%.2f" % (lo_c, hi_c))
swap(r"Peak swirl \(U_{\max}/U_\eta\) (all", "%.1f (83), %.1f (170)" % (r83["U"], r170["U"]),
     "not fitted (Kida et al.); ratio %.2f–%.2f; sources spread over 1.2–3.3" % kida_ratio["U"])
swap(r"Tube spacing", "%.1f (83), %.1f (170)" % (r83["d"], r170["d"]), "not fitted (Kida et al.); ratio %.2f–%.2f" % kida_ratio["d"])
swap(r"Tube length density", r"\(%.1f\times10^{-3}\) (83), \(%.1f\times10^{-3}\) (170)" % (r83["Vf"] / (math.pi * r83["beta"] ** 2) * 1e3, r170["Vf"] / (math.pi * r170["beta"] ** 2) * 1e3))
swap(r"Tube diameter", r"\(2r_{\max}=%.1f\)–%.1f \(\eta\)" % (2 * r83["beta"], 2 * r332["beta"]))
swap(r"Core volume fraction", "%.0f%% (83), %.0f%% (170), to \\(r_{\\max}\\)" % (r83["Vf"] * 100, r170["Vf"] * 100),
     r"model %.0f–%.0f%% is close to the 25%% above \(\omega'\); not a clean test (radius and threshold differ)" % (r83["Vf"] * 100, r170["Vf"] * 100))
swap(r"Vortex share", "%.0f%% (83) → %.0f%% (1934)" % (r83["share"] * 100, r1934["share"] * 100),
     "model %.0f–%.0f%% (83–170) matches 80%% in 25%% of the volume (Jiménez et al.) and 75%% in 20%% (Hosokawa and Yamamoto); conflicts with core-only values (31%%) and with the intense subset" % (r83["share"] * 100, r170["share"] * 100))
swap("Growth exponent", None, None)
t = t.replace('<td class="c">%.3f ± %.3f (fitted)</td>' % (0.1366, 0.015), '<td class="c">%.3f ± %.3f (fitted)</td>' % (P, err[1]))
open(page, "w", encoding="utf8", newline="\n").write(t)
print("written")
