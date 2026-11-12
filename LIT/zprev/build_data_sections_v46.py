"""Write section 7 (whole and intense tubes, with the table of all measurements) and the appendix of the page
from sourcedata.py.  Re-running replaces both blocks; nothing else in the page is touched.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sourcedata as sd

PAGE = os.path.join(os.path.dirname(HERE), "vortex-energy-balance.html")
FMT = {"rmax": "%.2f", "gam": "%.0f", "swirl": "%.2f", "rec": "%.1f", "d": "%.1f"}
ROLE = {"fit": "fitted", "cmp": "comparison"}


def re_text(Re):
    return "%g" % Re if isinstance(Re, (int, float)) else str(Re)


def nu_text(nu):
    if nu is None:
        return "&mdash;"
    return "%g" % nu if isinstance(nu, (int, float)) else str(nu)


def eps_text(e):
    if e is None:
        return "&mdash;"
    return "%g" % e if isinstance(e, (int, float)) else str(e)


def sci(v):
    e = int(__import__("math").floor(__import__("math").log10(abs(v))))
    return "%.3g&times;10<sup>%d</sup>" % (v / 10**e, e)


def num(v):
    return sci(v) if isinstance(v, float) and (abs(v) < 1e-2 or abs(v) >= 1e4) else ("%g" % v)


def used_texts(r):
    """(nu used, eps used, eta) as text for the model side; a dagger marks the reference values (water, 0.1 W/kg)."""
    nu, eps, eta, how = sd.physical(r)
    star = "<sup>&dagger;</sup>" if how == "reference" else ("<sup>&Dagger;</sup>" if how.startswith("derived") else "")
    nu_t = nu if isinstance(nu, str) else num(nu)
    eps_t = eps if isinstance(eps, str) else num(eps)
    eta_t = "&mdash;" if eta is None else "%.3g" % (eta * 1e6)
    return nu_t + star, eps_t + star, eta_t


def sort_key(r):
    Re = r["Re"]
    num = Re if isinstance(Re, (int, float)) else (2e9 if "mdash" in str(Re) else 1e9)
    return (sd.ORDER.index(r["mtype"]), num, r["src"])


# ------------------------------------------------------------------------------------------------ appendix
def source_table(src):
    html = []
    for mt in sd.ORDER:
        rows = sorted([r for r in src["rows"] if r["mtype"] == mt], key=sort_key)
        if not rows:
            continue
        raw = src["rawcols"][mt]
        unit = src["nuunit"]
        eunit = src.get("epsunit", "")
        head = ["Meas. type", r"\(Re_\lambda\)", r"\(\nu\)" + (" (%s)" % unit if unit else ""), r"\(\varepsilon\)" + (" (%s)" % eunit if eunit else "")] + raw + ["Model", "Role"]
        out = ['<div class="tablebox"><table class="dt">\n<thead><tr>' + "".join(('<th class="msep">%s</th>' if k == 4 + len(raw) else "<th>%s</th>") % h for k, h in enumerate(head)) + "</tr></thead>\n<tbody>"]
        for k, r in enumerate(rows):
            cells = ""
            if k == 0:
                cells += '<td rowspan="%d">%s</td>' % (len(rows), sd.MSHORT[mt])
            cells += "<td>%s</td><td>%s</td><td>%s</td>" % (re_text(r["Re"]), nu_text(r["nu"]), eps_text(r["eps"]))
            cells += "".join("<td>%s</td>" % v for v in r["raw"])
            fac = sd.corr_factor(r["src"], mt)
            cells += '<td class="msep">%s=%s%s</td>' % (sd.MSHORT[mt], FMT[mt] % sd.used_value(r),
                                                          ("<br><small>= %s &times; %.3g (A0c)</small>" % (FMT[mt] % r["used"], fac)) if fac != 1.0 else "")
            cells += "<td>%s%s</td>" % (sd.reason(r), ("<br><small>%s</small>" % r["note"]) if r["note"] else "")
            out.append("<tr>%s</tr>" % cells)
        out.append("</tbody></table></div>")
        html.append("\n".join(out))
    return "\n".join(html)


def source_footnote(src):
    """The model-side nu and eps of a source: stated once, instead of a column that repeats the same value in every row."""
    r = src["rows"][0]
    nu, eps, eta, how = sd.physical(r)
    if how == "reference":
        return (r"<p class='note'>Model values refer to water (\(\nu=10^{-6}\) m\(^2\)/s) at the reference \(\varepsilon=0.1\) W/kg, \(\eta=56.2\ \mu\)m, \(u_\eta=17.8\) mm/s. "
                r"The DNS results in Kolmogorov units hold for any \(\varepsilon\) (appendix A0b).</p>").replace("'", chr(34))
    if how == "measured":
        return (r"<p class='note'>Model values use the measured \(\nu\) and \(\varepsilon\) of each run (air; \(\nu\) in the column \(\times10^{-4}\) m\(^2\)/s, \(\varepsilon\) in W/kg), "
                r"so \(\eta=(\nu^3/\varepsilon)^{1/4}\) differs from run to run (e.g. 0.54 mm at the lowest and 0.10 mm at the highest \(\varepsilon\)).</p>").replace("'", chr(34))
    return (r"<p class='note'>Model values use water (\(\nu=10^{-6}\) m\(^2\)/s) and the Kolmogorov length of the experiment, \(\eta=0.926\) mm, "
            r"so \(\varepsilon=\nu^3/\eta^4=1.4\times10^{-6}\) W/kg.</p>").replace("'", chr(34))


def a0b():
    """Physical equivalents of the DNS rows: the two equations that fix the units, and the table for the runs of Ghira et al."""
    import math
    eta_p = (sd.NU_REF**3 / sd.EPS_REF) ** 0.25
    rows = []
    for Re, nu_c, eps_c in zip(sd.RE, sd.NU, sd.EPS_G):
        eta_c = (nu_c**3 / eps_c) ** 0.25
        l0 = eta_p / eta_c
        L11 = sd.L11_CODE[Re]
        u0 = sd.NU_REF / (nu_c * l0)
        rows.append("<tr><td>%d</td><td>%g</td><td>%g</td><td>%.5f</td><td>%.2f</td><td>%.2f</td><td>%.0f</td><td>%.0f</td></tr>"
                    % (Re, nu_c, eps_c, eta_c, L11, l0 * 1e3, 2 * math.pi * l0 * 1e3, u0 * 1e3))
    table = ('<div class="tablebox"><table class="dt">\n<thead><tr><th>\\(Re_\\lambda\\)</th><th>\\(\\tilde\\nu\\)</th><th>\\(\\tilde\\varepsilon\\)</th><th>\\(\\tilde\\eta\\)</th><th>\\(\\tilde L_{11}\\) (DNS)</th>'
             '<th>\\(\\ell_0\\) (mm)</th><th>box \\(2\\pi\\ell_0\\) (mm)</th><th>\\(u_0\\) (mm/s)</th></tr></thead>\n<tbody>\n' + "\n".join(rows) + "\n</tbody></table></div>")
    text = r"""<h3>A0b. Physical equivalents of the DNS rows</h3>
<p>A DNS is solved in dimensionless variables, \(\tilde x=x/\ell_0\), \(\tilde u=u/u_0\), \(\tilde t=t\,u_0/\ell_0\), \(\tilde\nu=\nu/(u_0\ell_0)\), \(\tilde\varepsilon=\varepsilon\,\ell_0/u_0^3\). Ghira et al. fix the box at \(2\pi\times2\pi\times2\pi\) (so \(\ell_0=L_{\text{box}}/2\pi\) and the Fourier wavenumbers are integers) and impose a random body force, delta-correlated in time and concentrated at the wavenumbers around \(k_p=2\) (Alvelius's scheme), whose mean power \(P=\langle f_iu_i\rangle=10\) is the same in every run. There are no walls and no mean flow; at steady state the viscous dissipation balances the power, so \(\tilde\varepsilon\approx10\) (Table II: 9.5&ndash;11.9) and the integral length \(\tilde L_{11}\approx0.85\) is set by the forcing. Only \(\tilde\nu\) changes between the runs (0.0145 to 0.0010), and it sets \(Re_\lambda\); the Kolmogorov length \(\tilde\eta=(\tilde\nu^3/\tilde\varepsilon)^{1/4}\) is the value listed in Table II (0.0235 for the first run). One series is therefore the same stirrer in fluids of falling viscosity.</p>
<p>To compare with a physical flow with kinematic viscosity \(\nu\) and dissipation rate \(\varepsilon\), the two scales \(\ell_0\) and \(u_0\) follow from two equations, \(\varepsilon=\tilde\varepsilon\,u_0^3/\ell_0\) and \(\nu=\tilde\nu\,u_0\ell_0\):</p>
$$\ell_0=\frac{\eta_{\text{phys}}}{\tilde\eta}=\left(\frac{\nu^3/\varepsilon}{\tilde\nu^3/\tilde\varepsilon}\right)^{1/4},\qquad u_0=\frac{\nu}{\tilde\nu\,\ell_0},\qquad \eta_{\text{phys}}=\left(\frac{\nu^3}{\varepsilon}\right)^{1/4}.$$
<p>The Reynolds number \(Re_\lambda\) is already used (through \(\tilde\nu\)), so one of \(\varepsilon\), \(\ell_0\) or \(u_0\) must be given besides \(\nu\). The model takes \(\varepsilon\) as given, as in section 5, and the reference used here is water, \(\nu=10^{-6}\) m\(^2\)/s, at \(\varepsilon=0.1\) W/kg, so \(\eta_{\text{phys}}=56.2\ \mu\)m. The results of the DNS in Kolmogorov units hold for any \(\varepsilon\); a different reference only rescales the lengths, and an \(r_{\max}\) of \(\beta\,\eta\) becomes \(\beta\times56.2\ \mu\)m. For the runs of Ghira et al. (2022), with the integral lengths of their Table II:</p>
""" + table + "\n" + r"""<p class="note"><strong>Note on \(L_{11}\).</strong> \(L_{11}\) is the longitudinal integral length scale, the integral of the longitudinal velocity autocorrelation, the size of the energy-containing eddies (Ghira et al. compute it from the energy spectrum, their Appendix A). The column \(\tilde L_{11}\) is the DNS value (Ghira et al., Table II, in code units) and is given for information only: it is not converted to metres and is not used in the phenomenological turbulence model, whose inputs are \(\varepsilon\) and \(\nu\) (with \(\eta\) and the Kolmogorov scales following from them), and it enters none of the fits.</p>
"""
    return text


def correction_paragraph(src):
    """The statement, in the section of a source, of why its values are corrected (nothing for the sources that are used as reported)."""
    c = sd.CORR.get(src["key"])
    if not c:
        return ""
    return '<p><strong>Correction applied:</strong> %s See A0c.</p>\n' % c["text"]


def a0c():
    """Corrections applied to the reported values, the reason for each, and the chord model behind the radius correction."""
    rows = [
        ("DNS: Ghira et al. 2022 (radius), 2025, Jim&eacute;nez, Da Silva, Tanahashi, Kida, Pirozzoli, Ishihara, Das et al.", "none", "none (Ghira 2022: &times;0.6)",
         "3D fields: no one-dimensional cut, so no chord effect; the radius is read from the profile itself. The definitions differ (1/e radius, most expected value, core boundary) but not the geometry. Ghira 2022: see below."),
        ("Mouri et al. 2003, 2004, 2007 (hot wire, intense)", "none", "none",
         "A high threshold (the top 0.1&ndash;1% of the increments, 3&sigma; for 2003) favours crossings close to the axis, where the signal is largest; the authors say the radius is close to the true mean (5&ndash;7 \\(\\eta\\)). The amplitude is then about 0.9 of the peak."),
        ("Mouri and Hori 2009 (hot wire, all tubes)", "&divide; 1.7", "&times; 3",
         "The average over all tubes includes off-axis and tilted crossings: radius too large, amplitude too small (see below)."),
        ("Belin et al. 1996 (hot film)", "none", "not used",
         "The peak of the chord distribution (3.5 \\(\\eta\\) as \\(R\\), 5.5 \\(\\eta\\) as \\(r_{\\max}\\)) is set by near-axis crossings; the mean (about 6 \\(\\eta\\) as \\(R\\), 9.5 \\(\\eta\\) as \\(r_{\\max}\\)) divided by 1.7 gives 5.6 \\(\\eta\\), the same value. The swirl needs \\(1/(2\\sin\\alpha)\\) with an assumed \\(\\alpha\\), a factor of about 3.6, and is not used."),
        ("Aligolzadeh et al. 2023 (3D PIV)", "none", "none",
         "A 3D field, resolution about 1 \\(\\eta\\) with no spatial averaging (Sec. 2.1), so neither a chord effect nor a smoothing correction applies. The radius is the boundary of the vortex, not \\(r_{\\max}\\); this is not corrected yet."),
        ("Sassa and Makita 2005 (probe records)", "none", "none", "A moderate threshold (2.5&sigma;); the probe and its smoothing have not been checked."),
    ]
    tab = '<div class="tablebox"><table class="dt">\n<thead><tr><th>Source</th><th>Radius</th><th>Swirl</th><th>Reason</th></tr></thead>\n<tbody>\n' + "\n".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % r for r in rows) + "\n</tbody></table></div>"
    offs = '<div class="tablebox"><table class="dt">\n<thead><tr><th>\\(b/r_{\\max}\\)</th><th>0</th><th>0.5</th><th>1</th><th>1.5</th><th>2</th><th>3</th></tr></thead>\n<tbody>\n' \
           '<tr><td>spacing of the extrema \\(/2r_{\\max}\\)</td><td>1.00</td><td>1.04</td><td>1.20</td><td>1.53</td><td>2.00</td><td>3.00</td></tr>\n' \
           '<tr><td>amplitude \\(/\\) central amplitude</td><td>1.00</td><td>0.89</td><td>0.66</td><td>0.46</td><td>0.35</td><td>0.23</td></tr>\n</tbody></table></div>'
    cut = '<div class="tablebox"><table class="dt">\n<thead><tr><th>amplitude cut \\(f\\)</th><th>0.8</th><th>0.5</th><th>0.3</th><th>0.2</th></tr></thead>\n<tbody>\n' \
          '<tr><td>mean radius ratio \\(R_m/R\\)</td><td>1.18</td><td>1.54</td><td>2.01</td><td>2.56</td></tr>\n' \
          '<tr><td>mean amplitude ratio \\(U\'/U\\)</td><td>0.89</td><td>0.71</td><td>0.56</td><td>0.45</td></tr>\n' \
          '<tr><td>product (\\(Re_c\'/Re_c\\))</td><td>1.05</td><td>1.05</td><td>1.01</td><td>0.96</td></tr>\n</tbody></table></div>'
    text = r"""<h3>A0c. Corrections applied to the reported values</h3>
<p>The values in the section 7 table are the values calculated from the papers (appendix A1 onwards) multiplied by the factors below, where a factor is applied; the table shows the calculated value and the factor under the corrected value. The tube Reynolds number and the circulation are recomputed from the corrected radius and swirl. The corrections are working choices, made to bring the experiments to the same tube as the simulations, and are listed with the reason for each:</p>
""" + tab + r"""
<h4>The chord correction (hot wire, all tubes)</h4>
<p>A single wire or crossed wire records one velocity component along a straight path through the flow. With Taylor's hypothesis the time is a distance \(s=Ut\), and a tube is a vortex with Gaussian vorticity \(\omega=\omega_0e^{-\rho^2/2R^2}\) (\(R\) its Gaussian width, \(R_B=\sqrt2\,R\), \(r_{\max}=\sqrt{2x}\,R=1.585\,R\)) and azimuthal velocity \(v_\theta=\omega_0R^2(1-e^{-\rho^2/2R^2})/\rho\). For a tube with axis \(\mathbf a\) crossed by a path with direction \(\mathbf e_x\) at impact parameter \(b\) (the distance between the path and the axis), the distance of the path from the axis is \(\rho^2=b^2+\sin^2\gamma\,(s-s_c)^2\), with \(\gamma\) the angle between path and axis, and the signal in the sensed direction \(\mathbf e_y\) is</p>
$$S(s)=\frac{v_\theta(\rho)}{\rho}\;\mathbf e_y\cdot\left(\mathbf a\times\mathbf p(s)\right).$$
<p>For a tube normal to the path and crossed through its axis the signal is \(v_\theta(|s|)\,\mathrm{sgn}\,s\): two extrema at \(\pm r_{\max}\), a spacing of \(2r_{\max}=3.17R\) (the rule \(R=0.31\,U\Delta t\) of Belin et al.) and an amplitude \(U_{\max}\). Off the axis the spacing grows and the amplitude falls (tube normal to the path):</p>
""" + offs + r"""
<p>A tilt of the axis stretches the path through the tube by \(1/\cos\alpha\) (mean 1.12 for a tilt uniform up to 45&deg;, 1.41 at 45&deg;) and adds an even part to the signal. Averaging over all orientations (isotropic, tilt up to 45&deg;) and a uniform offset \(b\), keeping the events whose peak is at least a fraction \(f\) of the central amplitude (the detection threshold relative to the strength of the tube), the means of the events that are kept are:</p>
""" + cut + r"""
<p>A high threshold (large \(f\)) keeps only near-axis crossings (ratio close to 1); the average over all tubes includes weak crossings (small \(f\)), and a mean ratio of about 1.7 corresponds to \(f\approx0.25\)&ndash;0.3. The same crossings lower the amplitude by a factor 1/0.56 = 1.8 and leave the product \(Re_c\) about unchanged (the circulation is roughly conserved). Checks: (i) the size distribution that Belin et al. measured with a hot film has its peak at \(R=3.5\,\eta\) and its mean near \(6\,\eta\) (read from his Fig. 5); the peak is set by near-axis crossings and corresponds to \(r_{\max}=5.5\,\eta\), the mean divided by 1.7 gives \(5.6\,\eta\); (ii) Mouri and Hori state that \(R_0\) is above the true mean radius for all tubes but close to it for intense tubes. The model assumes identical tubes; the width of the measured distribution comes mostly from a real spread of tube radii (lognormal, spread about 0.5 in \(\ln R\)).</p>
<p>The probe has a finite length (1.25 mm sensing length and 1.4 mm wire separation for Mouri et al., against 0.2&ndash;3 \(\eta\) for the masked fibre of Belin et al.), which grows from 2 \(\eta\) at \(Re_\lambda=332\) to 13 \(\eta\) at 1934 and smooths the signal. A boxcar average over a length \(L\) adds \(L^2/6\) to \(R^2\) and conserves the circulation; for \(L=1\) mm and a true \(r_{\max}=5\,\eta\) it would give a radius of 5.1 \(\eta\) at \(Re_\lambda=332\) and 8.4 \(\eta\) at 1934. The hot-wire radii of Mouri et al. (2004, 2007) are below this estimate at high \(Re_\lambda\), and it is not applied.</p>
<h4>Why not the same factor for the intense hot-wire classes</h4>
<p>The intense classes of Mouri et al. are selected by the highest 0.1&ndash;1% of the increments, so the events that remain have a large amplitude relative to the cut and are mostly close to the axis; the authors write that the intense radius is close to the true mean radius. Dividing their radii (5.2&ndash;7.4 \(\eta\)) by 1.7 would give 3.1&ndash;4.4 \(\eta\), below the simulations. They are used as reported.</p>
<h4>Ghira et al. (2022): the swirl</h4>
<p>Their listed swirl \(U_{ivs}\), the mean tangential velocity at \(R_{ivs}\), is 1.0&ndash;1.25 \(u'\), against 0.86&ndash;0.99 for Jim&eacute;nez and Wray, 0.68&ndash;0.76 for Da Silva et al., 0.5 for the mixing layer and 0.5&ndash;0.8 for the hot wire. The swirl that a Burgers vortex has with their mean axis vorticity (\(\omega_{ivs}/\omega_{rms}=3.9\), 4.3, 4.4, 4.5, 4.8 at \(Re_\lambda=90\), 148, 191, 242, 314) and their Burgers radius is \(U_{\max}=0.319\,\omega_0R_B=5.5\), 5.9, 6.0, 6.0, 6.2 \(U_\eta\), nearly constant, while the listed swirl grows with \(u'\) from 6.1 to 9.5. The ratio of the vorticity-based to the listed swirl falls from 0.90 to 0.65. A constant factor that puts the Ghira swirl on the curve of the other sources, \(U_{\max}/U_\eta=0.79\,Re_\lambda^{0.34}\), is 0.58 (0.56&ndash;0.60 for the seven runs), and 0.6 is used. This is an empirical factor, closer to the vorticity argument at \(Re_\lambda\approx300\)&ndash;400 than at 90.</p>
"""
    return text


def build_appendix():
    parts = [r"""<h2>Appendix: the source data, how it was converted, and what the model uses</h2>
<p>Every literature value that enters or is compared with the model is listed here, source by source. For each paper there is a short discussion of how the tubes were selected and the equations that convert the tabulated numbers to the model quantities, followed by one table per measurement type, with the rows in ascending \(Re_\lambda\). Each table has the measurement type, \(Re_\lambda\), the kinematic viscosity \(\nu\) and the dissipation rate \(\varepsilon\) of the run (the two given quantities that fix \(\eta\) and \(u_\eta\); in the units of the paper, which differ: DNS code units, cm\(^2\)/s and m\(^2\)/s\(^3\); a dash where the paper does not give one), then the entries taken from the paper's table, then the value used in the model with the \(\nu\), \(\varepsilon\) and \(\eta\) used by the model in SI units, and the role: fitted in section 9, or not fitted with the reason. The model-side \(\nu\) and \(\varepsilon\) are measured for the laboratory experiments in air (Mouri et al.), derived from the Kolmogorov length for Aligolzadeh et al. (&Dagger;), and for all DNS rows a reference, water (\(\nu=10^{-6}\) m\(^2\)/s) at \(\varepsilon=0.1\) W/kg (&dagger;), explained in A0b. The tube set of each source (whole or intense) is explained in section 7.</p>
<h3>A0. Conversions used for all sources</h3>
<p>A Burgers vortex has \(u_\theta(r)=\dfrac{\Gamma}{2\pi r}\left(1-e^{-r^2/R_B^2}\right)\) with \(R_B=2\sqrt{\nu/\gamma}\), the radius at which the vorticity has fallen to \(1/e\) of its axis value. The swirl is maximal at \(r_{\max}=\sqrt{x}\,R_B=1.121\,R_B\), where \(x=1.2564\) is the root of \(e^x-2x-1=0\), and</p>
$$U_{\max}=\frac{(1-e^{-x})\,\Gamma}{2\pi\,r_{\max}},\qquad \frac{\Gamma}{\nu}=\frac{2\pi}{1-e^{-x}}\,\frac{r_{\max}U_{\max}}{\nu}=8.78\,Re_c,\qquad Re_c=\frac{r_{\max}U_{\max}}{\nu}.$$
<p>The circulation inside a radius \(r\) is \(\Gamma(r)=\Gamma\left(1-e^{-r^2/R_B^2}\right)\) and the swirl at \(r=k\,r_{\max}\) is \(U_{\max}f(k)\), with</p>
$$f(k)=\frac{1-e^{-xk^2}}{k\,(1-e^{-x})}.$$
<p>The Kolmogorov scales satisfy \(\nu=u_\eta\,\eta\), and for isotropic turbulence the rms velocity is \(u'/u_\eta=\left(Re_\lambda/\sqrt{15}\right)^{1/2}\) (the isotropic relation \(\varepsilon=15\nu u'^2/\lambda^2\)). All radii are in units of \(\eta\), all velocities in units of \(u_\eta\) (written \(U_\eta\) in the model), and \(\Gamma\) in units of \(\nu\).</p>"""]
    parts.append(a0b())
    parts.append(a0c())
    for i, src in enumerate(sd.SOURCES, 1):
        eq = "".join("\n$$%s$$" % e for e in src["eqs"])
        parts.append(
            '<h3>A%d. %s (%s tubes)</h3>\n<p><strong>Where in the paper:</strong> %s</p>\n<p><strong>Method:</strong> %s</p>\n<p><strong>Which tubes:</strong> %s</p>\n<p><strong>Conversion:</strong>%s</p>\n<p><strong>Notes:</strong> %s</p>\n%s%s'
            % (i, src["cite"], src["tubes"], src["where"], src["method"], src["selection"], eq, src["notes"], correction_paragraph(src),
               source_table(src) + "\n" + source_footnote(src)))
    parts.append(r"""<h3>Papers read for which no row was used</h3>
<p>Ghira et al. (2024) has the \(Re_\lambda=54\) DNS but no radius or swirl for it (its radius is that of Ghira et al. 2025, Table 2). Elsinga et al. (2023) has the enstrophy and dissipation scaling to \(Re_\lambda=1445\), with a change near \(Re_\lambda\approx250\) where large-scale shear layers develop, and no tube dimensions. Watanabe and Nagata (2023) and Watanabe et al. (2024) describe shear layers (half-width \(\ell_S/\eta\approx4\), velocity jump \(\Delta u_S/u_\eta\approx5\) at \(Re_\lambda\) 43&ndash;202; aspect ratio about 4.5 at \(Re_\lambda\) 400&ndash;900), not tubes. Enoki et al. (2023) give the r.m.s. shares of the shear and non-shear velocities (70% and 30%). Leung et al. (2012) analyse the geometry of educed structures at \(Re_\lambda=141\) without a tube radius. Okamoto et al. (2007) extract coherent vortices at \(Re_\lambda\) 167&ndash;732 by wavelets and report degrees of freedom, not a radius. Cherry and Kwon (1990) take a Burgers vortex as the Kolmogorov eddy, with strain \(0.18\,(\varepsilon/\nu)^{1/2}\) for stirred vessels, \(r_{\max}=2\sqrt{1.265\,\nu/\alpha}=5.3\,\eta\) (computed here), \(\omega_0=7.14\,(\varepsilon/\nu)^{1/2}\) and a half-spacing of \(20\,\eta\); this is a model eddy without a stated \(Re_\lambda\), and the half-spacing is close to the model \(d/\eta\) of 17&ndash;19 at \(Re_\lambda\) 170&ndash;330. Wojtas et al. (2017) has no tube data.</p>""")
    return "\n".join(parts) + "\n"


# ------------------------------------------------------------------------------------------------ section 7
def ranges():
    out = {}
    for r in sd.all_rows():
        if not isinstance(r["Re"], (int, float)):
            continue
        s = sd.BY_KEY[r["src"]]
        out.setdefault((s["tubes"], r["mtype"]), []).append(sd.used_value(r))
    return out


def rng(vals, mt):
    if not vals:
        return "&mdash;"
    f = FMT[mt]
    return "%s&ndash;%s (%d)" % (f % min(vals), f % max(vals), len(vals))


def tube_items(corrected=False):
    """One dict per source, run and Re_lambda with the complete tube description used as model input: measured quantities as
    converted in the appendix, the rest completed with the Burgers relations (Re_c = beta U, Gamma/nu = 8.78 Re_c,
    gamma = 4 x gamma_eta/beta**2) and converted to SI with the nu and eps of the model side. Sorted by Re_lambda, then source.
    corrected=False (the default) gives the values as calculated from the papers (the fit and plot scripts apply their own factors);
    corrected=True applies the corrections of sourcedata.CORR (radius, swirl; Re_c and Gamma follow), the values of the section 7 table.
    The keys beta_raw, U_raw and fr, fu hold the uncorrected values and the factors."""
    groups = {}
    for r in sd.all_rows():
        if r["src"] in ("Mouri09", "Mouri07", "Mouri04"):
            tag = r["raw"][0]
        elif r["src"] == "Pirozzoli09":
            tag = "2009" if isinstance(r["Re"], (int, float)) else "2012"
        elif r["src"] in ("DaSilva11", "Wall", "Ghira25"):
            tag = r["note"]
        else:
            tag = ""
        groups.setdefault((r["src"], str(r["Re"]), tag), {})[r["mtype"]] = r
    order = {s["key"]: k for k, s in enumerate(sd.SOURCES)}
    items = []
    for (src, _, _), g in groups.items():
        r0 = next(iter(g.values()))
        beta_raw = g["rmax"]["used"] if "rmax" in g else None
        U_raw = g["swirl"]["used"] if "swirl" in g else None
        fr = sd.corr_factor(src, "rmax") if corrected else 1.0
        fu = sd.corr_factor(src, "swirl") if corrected else 1.0
        beta = beta_raw * fr if beta_raw is not None else None
        U = U_raw * fu if U_raw is not None else None
        if "rec" in g:
            rec = g["rec"]["used"] * sd.corr_factor(src, "rec") if corrected else g["rec"]["used"]
        else:
            rec = beta * U if beta is not None and U is not None else None
        if "gam" in g:
            RG = g["gam"]["used"] * sd.corr_factor(src, "gam") if corrected else g["gam"]["used"]
        else:
            RG = sd.G * rec if rec is not None else None
        d = g["d"]["used"] if "d" in g else None
        nofit = [mt for mt, row in g.items() if not sd.reason(row).startswith("fitted")]
        label = {"rmax": "r<sub>max</sub>", "gam": "&Gamma;", "swirl": "U<sub>max</sub>", "rec": "Re<sub>c</sub>", "d": "d/&eta;"}
        if len(nofit) == len(g):
            included = "no"
        elif nofit:
            included = "no: " + ", ".join(label[mt] for mt in sd.ORDER if mt in nofit)
        else:
            included = ""
        nu, eps, eta, how = sd.physical(r0)
        phys = isinstance(nu, (int, float)) and eta
        ueta = (nu * eps) ** 0.25 if phys else None
        items.append(dict(src=src, Re=r0["Re"], RG=RG, included=included, beta_raw=beta_raw, U_raw=U_raw, fr=fr, fu=fu, augmented=bool(phys and not isinstance(r0["Re"], (int, float))), beta=beta, U=U, rec=rec, d=d, eta=eta if phys else None, ueta=ueta,
                          rmax=beta * eta if (phys and beta is not None) else None, Umax=U * ueta if (phys and U is not None) else None,
                          gam=4 * sd.x / beta**2 * (eps / nu) ** 0.5 if (phys and beta is not None) else None,
                          Gam=RG * nu if (phys and RG is not None) else None))
    items.sort(key=lambda it: ((it["Re"] if isinstance(it["Re"], (int, float)) else (2e9 if "mdash" in str(it["Re"]) else 1e9)), order[it["src"]]))
    return items


def model_input_table():
    """The section 7 table of tube_items(): SI columns, Burgers-completed values, tube set and the Included flag."""
    items = tube_items(corrected=True)

    def f(v, fmt):
        if v is None:
            return "&mdash;"
        out = fmt % v
        return "%d" % round(float(out)) if "e" in out else out

    def fc(v, fmt, raw, factor):
        """A value cell; where a correction is applied the calculated value and the factor are shown under it."""
        base = f(v, fmt)
        if factor == 1.0 or v is None or raw is None:
            return base
        return "%s<br><small>= %s &times; %.3g</small>" % (base, fmt % raw, factor)
    mark = {"Ghira22": "c", "Aligolzadeh23": "b", "Mouri09": "a,e", "Mouri07": "a", "Mouri04": "a", "Mouri03": "a"}
    body = []
    for number, it in enumerate(items, 1):
        s = sd.BY_KEY[it["src"]]
        body.append("<tr><td>%d</td><td>%s%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            number, s["short"], "<sup>%s</sup>" % ",".join([m for m in [mark.get(it["src"])] if m] + (["d"] if it["augmented"] else [])) if (mark.get(it["src"]) or it["augmented"]) else "", re_text(it["Re"]), f(it["eta"] and it["eta"] * 1e6, "%.3g"), f(it["ueta"] and it["ueta"] * 1e3, "%.3g"),
            f(it["rmax"] and it["rmax"] * 1e6, "%.3g"), f(it["Umax"] and it["Umax"] * 1e3, "%.3g"), f(it["rec"], "%.1f"), fc(it["beta"], "%.2f", it["beta_raw"], it["fr"]), fc(it["U"], "%.2f", it["U_raw"], it["fu"]),
            f(it["gam"], "%.3g"), "&mdash;" if it["Gam"] is None else sci(it["Gam"]), f(it["d"], "%.1f"), s["tubes"], s["method"], it["included"]))
    head = ["No.", "Ref.", r"\(Re_\lambda\)", r"\(\eta\) (&micro;m)", r"\(u_\eta\) (mm/s)", r"\(r_{\max}\) (&micro;m)", r"\(U_{\max}\) (mm/s)", r"\(Re_c\)",
            r"\(r_{\max}/\eta\)", r"\(U_{\max}/U_\eta\)", r"\(\gamma\) (s\(^{-1}\))", r"\(\Gamma\) (m\(^2\)/s)", r"\(d/\eta\)", "Tube set", "Method", "Included"]
    return ('<div class="tablebox"><table class="dt">' + chr(10) + "<thead><tr>" + "".join("<th>%s</th>" % h for h in head) + "</tr></thead>" + chr(10) + "<tbody>" + chr(10)
            + chr(10).join(body) + chr(10) + "</tbody></table></div>")


def build_section7():
    rg = ranges()
    tab = ['<div class="tablebox"><table class="dt">\n<thead><tr><th>Measurement</th><th>Intense tubes: range (number)</th><th>Whole tubes: range (number)</th></tr></thead>\n<tbody>']
    for mt in sd.ORDER:
        tab.append("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (sd.MSHORT[mt], rng(rg.get(("intense", mt)), mt), rng(rg.get(("whole", mt)), mt)))
    tab.append("</tbody></table></div>")
    ranges_table = "\n".join(tab)

    big = model_input_table()

    text = r"""<h2>7. The data: whole tubes and intense tubes</h2>
<p>The literature values of tube radius, swirl and circulation do not describe one population. Papers select tubes in different ways, and the selection changes the swirl and the circulation strongly and the radius only a little. Two sets are therefore distinguished, and every value in the appendix is assigned to one of them.</p>
<h3>What is meant by the two sets</h3>
<ul>
<li><strong>Intense tubes</strong> are the strongest structures only. They are the 1% of the volume with the highest vorticity (the intense vorticity structures or worms of Jim&eacute;nez et al., Ghira et al., Da Silva et al.; 1.4% in Aligolzadeh et al.), so in the simulations and the 3D measurement they occupy a volume fraction \(V_i\approx0.01\). In the hot-wire records (Mouri et al. 2003, 2004, 2007) the cut is on the signal: the highest 0.1% or 1% of the absolute velocity increments, a share of the samples along the record and not of the volume. The volume that these tubes occupy is not given, so \(V_i\approx0.01\) applies to the DNS-defined tubes only.</li>
<li><strong>Whole tubes</strong> are tube-like vortices selected with a low threshold or none: the low-pressure cores of Kida et al. (31&ndash;35% of the volume), the vortices fitted by Mouri and Hori (2009), the coherent fine-scale eddies of Tanahashi et al., the cores of Pirozzoli and the elementary vortices of Sassa and Makita. They occupy a volume fraction \(V_w\approx0.2\)&ndash;0.35, the order of the \(V_f\) of the budget in sections 4 and 5.</li>
</ul>
<p>The intense tubes are the tail of the distribution of tube strengths and the whole set contains them. The two sets overlap in radius and differ in swirl. The ranges of the values used (rows with an \(Re_\lambda\); the number of values in brackets) are:</p>
@RANGES@
<p>The radii overlap: 4.3&ndash;7.4 \(\eta\) for intense tubes and 4.5&ndash;5.4 \(\eta\) for whole tubes, except the \(8\)&ndash;\(9\,\eta\) of Mouri and Hori (2009), fits that the authors say are biased high (the same experiments give 5.2&ndash;7.4 \(\eta\) for intense tubes). The swirl and the tube Reynolds number differ by a factor 2&ndash;3: intense tubes have \(U_{\max}\approx4\)&ndash;14 \(U_\eta\) and \(Re_c\approx32\)&ndash;87, whole tubes \(U_{\max}\approx2.4\)&ndash;3.9 \(U_\eta\) and \(Re_c\approx20\)&ndash;28.</p>
<h3>How the two sets scale</h3>
<p>For intense tubes the swirl follows the r.m.s. velocity: \(V_0/\langle v^2\rangle^{1/2}\approx0.5\)&ndash;0.8 (Mouri et al.), \(u_0/u'\approx0.7\)&ndash;0.8 (Da Silva et al.) and \(U_{ivs}/u'\approx1.0\)&ndash;1.25 (Ghira et al.), so, with \(u'/U_\eta=(Re_\lambda/\sqrt{15})^{1/2}\) and a nearly constant radius \(\beta_i\approx5\),</p>
$$U_i=\kappa\,u'=\kappa\left(\frac{Re_\lambda}{\sqrt{15}}\right)^{1/2}U_\eta,\qquad Re_{c,i}=\beta_iU_i/U_\eta\propto Re_\lambda^{1/2},\qquad \frac{\Gamma_i}{\nu}=8.78\,Re_{c,i}.$$
<p>This agrees with the measured \(Re_0\propto Re_\lambda^{1/2}\) of Mouri et al. For whole tubes the swirl is a few Kolmogorov velocities and grows slowly (\(Re_0\propto Re_\lambda^{0.18}\) of Mouri and Hori, \(\Gamma/\nu\propto Re_\lambda^{0.16}\) of Kida et al., \(W_{\max}/u_K\propto Re_\lambda^{0.28}\) of Sassa and Makita):</p>
$$U_w=c\,\beta_w^{\,q}\,Re_\lambda^{\,s}\,U_\eta,\qquad Re_{c,w}=\beta_wU_w/U_\eta,\qquad \frac{\Gamma_w}{\nu}=8.78\,Re_{c,w},$$
<p>which is the closure of section 9 (with \(c=1\)). The ratio of the two swirls, \(U_i/U_w\propto Re_\lambda^{1/2-s}\), is about 2 at \(Re_\lambda=300\) and about 2.5 at 2000: the intense tubes become relatively stronger as \(Re_\lambda\) rises.</p>
<h3>How this enters the model</h3>
<p>The dissipation budget of sections 4 and 5 describes the whole set: the volume \(V_f\) it closes is the volume of the tubes that carry the vortex dissipation, and the swirl in it must be that of the whole set,</p>
$$\frac{\varepsilon_{\text{vortex}}}{\varepsilon}=4.91\,V_w\,\frac{(U_w/U_\eta)^2}{\beta_w^{2}}\;\Rightarrow\;V_w=\frac{\left(1-75.8/\beta_w^{4}\right)\beta_w^{2}}{4.91\,(U_w/U_\eta)^{2}}.$$
<p>The intense tubes are a small subset, with a volume \(V_i\approx0.01\) and a share of the dissipation</p>
$$\frac{\varepsilon_i}{\varepsilon}=4.91\,V_i\,\frac{(U_i/U_\eta)^2}{\beta_i^{2}}.$$
<p>With \(V_i=0.01\), \(\beta_i=5\) and \(U_i/U_\eta=9\) (\(Re_\lambda\approx300\)) this is \(\varepsilon_i/\varepsilon\approx0.16\), close to the 15% of the enstrophy that Jim&eacute;nez et al. find in their intense 1%. So the two sets are consistent with each other in the budget, but they must not be fitted by the same swirl law.</p>
<p>The fits of section 9 mix the two sets: the radii come from intense tubes (Ghira, Jim&eacute;nez, Aligolzadeh) and one whole-tube radius (Tanahashi), the circulation from intense tubes (Ghira), and the tube Reynolds number from whole tubes (Mouri and Hori 2009). One swirl law then has to serve both, which shows up as the factor 1.5&ndash;2.5 between the swirl listed by Ghira et al. and the model swirl, as the 2&ndash;3 times too low \(Re_c\) against the intense tubes of Mouri et al., and as the degenerate exponents \(q\) and \(s\). The next step is to fit the two sets separately: the intense set with \(\beta_i\) and \(\kappa\) (or a free exponent), the whole set with the closure of section 9, and to use the whole set in the budget.</p>
<h3>The data</h3>
<p>The table has one row per source, run and \(Re_\lambda\), sorted by \(Re_\lambda\) and then by source, and gives the tube as the model sees it: the Kolmogorov length \(\eta\) and velocity \(u_\eta\), the radius \(r_{\max}\) and swirl \(U_{\max}\) in SI units and in Kolmogorov units, the tube Reynolds number, the strain \(\gamma\), the circulation \(\Gamma\), the spacing \(d/\eta\) and the tube set (intense or whole, section 7). A dash means that the source does not give the quantity and the Burgers relations cannot supply it. The measured quantities are those of the appendix (A0 and the source sections); the others are completed with the Burgers relations: \(Re_c=r_{\max}U_{\max}/\nu=(r_{\max}/\eta)(U_{\max}/U_\eta)\) when the source gives both, otherwise the Re_c of the source; \(\Gamma/\nu=8.78\,Re_c\) unless the source lists \(\Gamma\); and \(\gamma=4x\gamma_\eta/(r_{\max}/\eta)^2\) from the radius, with \(\gamma_\eta=(\varepsilon/\nu)^{1/2}\).</p>
<p class="note">The SI columns use water (\(\nu=10^{-6}\) m\(^2\)/s) at the reference \(\varepsilon=0.1\) W/kg (\(\eta=56.2\ \mu\)m, \(u_\eta=17.8\) mm/s, \(\gamma_\eta=316\) s\(^{-1}\)), except where marked. The DNS results in Kolmogorov units hold for any \(\varepsilon\); the reference only fixes the physical size (appendix A0b).</p>
<div class="note">
<div><sup>a</sup> Mouri et al.: experiments in air; the measured \(\nu\) and \(\varepsilon\) of each run are used (appendix A7&ndash;A10).</div>
<div><sup>b</sup> Aligolzadeh et al.: water in a large 2 m tank driven by two counter-rotating impellers of 1.6 m diameter at low speed (\(Re_I=\Omega R_I^2/\nu=23\,000\), so \(\Omega\approx0.04\) rad/s). Only \(\eta=0.926\) mm is given, so \(\varepsilon=\nu^3/\eta^4=1.4\times10^{-6}\) W/kg follows for water, with \(\nu=10^{-6}\) m\(^2\)/s assumed, not stated by the authors. The low \(\varepsilon\) and the large \(\eta\) and \(r_{\max}\) are those of this slow, large facility; the values in Kolmogorov units are unaffected.</div>
<div><sup>c</sup> Ghira et al.: \(Re_c\) is the product of the converted radius and swirl, and \(\Gamma/\nu=8.78\,Re_c\) is the total Burgers circulation from them, as for every other row. The circulation they list (Eq. 9, \(\Gamma_{ivs}=2\pi\langle U_{ivs}\rangle R_{ivs}\)) is the circulation inside \(R_{ivs}\), about 60% of the total (\(R_{ivs}/R_B\approx0.97\)); divided by 0.60 it is 0.83&ndash;0.84 of \(8.78\,Re_c\) at every \(Re_\lambda\) (appendix A1), and it is not used.</div>
<div><sup>d</sup> How the data were augmented: a source that gives no single \(Re_\lambda\) (none, or a range) gives the tube only in Kolmogorov units. The SI columns of these rows are the reference values (water, 0.1 W/kg) applied to those dimensionless numbers, so they show the size at the reference condition and are not measurements. The strain \(\gamma\), \(Re_c\) and \(\Gamma\) of every row are likewise computed from the Burgers relations where the source does not give them.</div>
<div><sup>e</sup> Mouri and Hori (2009): the radii \(R_0/\eta\) of 8.3&ndash;9.2 are biased high by the authors' own account (their fits of the whole vortex; the same experiments give 5.2&ndash;7.4 for the intense tubes of Mouri et al. 2007). They are kept in the table and not fitted; only \(Re_c\) is fitted. They are candidates for a later outlier label.</div>
<div>Corrections: where a value carries "= calculated &times; factor", the calculated value of the paper has been multiplied by the factor (appendix A0c gives the reason for each): Mouri and Hori (2009) radius &times; 1/1.7 and swirl &times; 3 (the average over all tubes read by a hot wire has too large a radius and too small a swirl), and the swirl of Ghira et al. (2022) &times; 0.6 (it lies above the swirl of the other sources and above the swirl implied by their own axis vorticity). \(Re_c\), \(\Gamma\) and \(\gamma\) are computed from the corrected radius and swirl. All other values are as calculated from the papers.</div>
<div>Included: empty = every value of the row enters the fits of sections 8 and 9; <em>no</em> = none does; <em>no: &hellip;</em> = the listed values do not, the others do. Rows not included are shown for comparison.</div>
</div>
@BIG@
"""
    return text.replace("@RANGES@", ranges_table).replace("@BIG@", big)


def main():
    t = open(PAGE, encoding="utf8").read()
    app = build_appendix()
    i = t.index("<h2>Appendix")
    j = t.index("</main>")
    t = t[:i] + app + t[j:]
    sec7 = build_section7()
    if "<h2>7. The data: whole tubes and intense tubes</h2>" in t:
        a = t.index("<h2>7. The data: whole tubes and intense tubes</h2>")
        b = t.index("<h2>8. ", a)
        t = t[:a] + sec7 + "\n" + t[b:]
    else:
        anchor = "<h2>7. Tube model with Kolmogorov-scaled swirl"
        assert anchor in t, "run restructure_page.py first or the old section 7 heading is missing"
        t = t.replace(anchor, sec7 + "\n" + anchor, 1)
    open(PAGE, "w", encoding="utf8", newline="\n").write(t)
    bad = re.findall(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", t)
    print("written; control characters:", len(bad))


if __name__ == "__main__":
    main()
