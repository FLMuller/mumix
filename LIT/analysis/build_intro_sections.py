"""build_intro_sections.py  v01  Write section 1 (summary of the literature), section 2 (theory background) and the new references of the page.

Section 1 has a table of what each source gives (made from the fitting tool's data file with the corrections of A0c) and the figure of radius and swirl against Re_lambda.
Section 2 is the background: vortex stretching, the Burgers vortex, the stretched vortices of the literature (Moffatt et al. 1994 and the models before it), the scales of
Kolmogorov and what the Burgers vortex says about them, and the DNS and experiments.  The text is here, so re-running replaces the sections.
The block from '<h2>1. Summary of the literature</h2>' to '<h2>3. ' of ../vortex-energy-balance.html is replaced; the references are merged (sorted by author) into the list.

Usage: python build_intro_sections.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(os.path.dirname(HERE), "fittingtool")
PAGE = os.path.join(os.path.dirname(HERE), "vortex-energy-balance.html")
sys.path.insert(0, TOOL)
sys.path.insert(0, HERE)
import fitdata        # noqa: E402
import fitreport      # noqa: E402
import sourcedata as sd   # noqa: E402
import pagefigures        # noqa: E402


def rng(vals, digits=2):
    vals = [v for v in vals if v is not None]
    if not vals:
        return "&mdash;"
    lo, hi = min(vals), max(vals)
    f = "%%.%df" % digits
    return f % lo if abs(hi - lo) < 1e-9 else (f + "&ndash;" + f) % (lo, hi)


def source_table(rows, corrections, excluded):
    by = {}
    for x in rows:
        by.setdefault(x["src"], []).append(x)
    body = []
    for key in [s["key"] for s in sd.SOURCES]:
        xs = by.get(key)
        if not xs:
            continue
        s = sd.BY_KEY[key]
        res = [x["re"] if x["re"] is not None else None for x in xs]
        lows = [x["re_lo"] for x in xs if x["re_lo"] is not None]
        highs = [x["re_hi"] for x in xs if x["re_hi"] is not None]
        re_text = "&mdash;" if not lows else ("%g&ndash;%g" % (min(lows), max(highs)) if min(lows) != max(highs) else "%g" % lows[0])
        c = corrections.get(key, {})
        corr = []
        if c.get("r_divisor", 1.0) != 1.0:
            corr.append("radius &divide; %g" % c["r_divisor"])
        if c.get("u_factor", 1.0) != 1.0:
            corr.append("swirl &times; %g" % c["u_factor"])
        single = any(x["re"] is not None for x in xs)
        if key in excluded:
            fit = "no: left out (A0c)"
        elif not single:
            fit = "no: no single Re<sub>&lambda;</sub>"
        else:
            fit = "yes"
        body.append("<tr><td class=\"l\">%s</td><td class=\"l\">%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td class=\"l\">%s</td><td class=\"l\">%s</td></tr>" % (
            s["short"], sd.METHOD.get(key, ""), s["tubes"], re_text, rng([x["r_raw"] for x in xs]), rng([x["u_raw"] for x in xs]),
            rng([x["r"] for x in xs]) + " / " + rng([x["u"] for x in xs]), "; ".join(corr) or "none", fit))
    head = ["Source", "Method", "Tubes", r"\(Re_\lambda\)", r"\(r_{\max}/\eta\) as calculated", r"\(U_{\max}/U_\eta\) as calculated", r"after correction: \(r_{\max}/\eta\) / \(U_{\max}/U_\eta\)", "Correction", "Fitted"]
    return ('<div class="tablebox"><table class="dt">\n<thead><tr>%s</tr></thead>\n<tbody>\n%s\n</tbody></table></div>'
            % ("".join("<th>%s</th>" % h for h in head), "\n".join(body)))


SECTION1 = r"""<h2>1. Summary of the literature</h2>
<p>Intense vortex tubes of the small scales of turbulence were found in simulations of isotropic turbulence in the early 1990s (Jim&eacute;nez et al. 1993; Vincent and Meneguzzi 1991) and have since been measured in simulations of isotropic turbulence (Ghira et al. 2022, 2025; Da Silva et al. 2011; Kida et al. 2002; Pirozzoli 2009, 2012; Ishihara et al. 2011, 2013), mixing layers and channels (Tanahashi et al. 2001, 2004; Das et al. 2006; Wang et al. 2007), in 3D scanning PIV (Lawson and Dawson 2014; Aligolzadeh et al. 2023) and with hot wires and films in laboratory flows up to \(Re_\lambda\approx2000\) (Belin et al. 1996; Mouri et al. 2003, 2004, 2007; Mouri and Hori 2009; Sassa and Makita 2005). The table lists what each source gives, converted to the Burgers vortex of section 3: the radius of maximum swirl \(r_{\max}\) and the peak swirl \(U_{\max}\) in Kolmogorov units, \(r_{\max}/\eta\) and \(U_{\max}/U_\eta\). The conversions are in the appendix (A0 and one subsection for each source); the values of every run are in the table of section 9.</p>
@TABLE@
<p>The sources do not describe one set of tubes. Their tubes are selected by a threshold on the vorticity (the 1% of the volume of highest vorticity: intense tubes) or by a low threshold or none (whole tubes: low-pressure cores, second-invariant eddies, all velocity-increment events), their radius is a 1/e radius, the radius of maximum swirl or a core boundary, and a probe in an experiment reads a one-dimensional cut of the tube. Section 9 sorts the sources into the two sets, and A0c gives the corrections applied before the values are compared. With the corrections the picture is simple: the radius is about \(5\,\eta\) at every \(Re_\lambda\) from 35 to 1900 (4.3&ndash;5.4 \(\eta\); the PIV boundary radius of Aligolzadeh et al. and the typical radius of Pirozzoli are 6.0 \(\eta\)), the swirl grows slowly with \(Re_\lambda\) from about 4 \(U_\eta\) at \(Re_\lambda=100\) to about 10 \(U_\eta\) at 2000, and the circulation \(\Gamma/\nu=8.78\,r_{\max}U_{\max}/(\eta U_\eta)\) from about 165 to 450.</p>
@FIGURE@
<p class="note">Radius and swirl of every source against \(Re_\lambda\) (colour: method, marker: source). Solid symbols are the values used (after the corrections of A0c); open symbols are the values as calculated from the paper where a correction was applied; grey crosses are rows left out of the fits; horizontal bars are sources that give a range of \(Re_\lambda\).</p>
<h3>Discrepancies met</h3>
<ul>
<li><strong>The chord length of a hot wire.</strong> A probe records a straight cut through the tube, not the tube. At a random offset from the axis and a random tilt the spacing of the two extrema of the signal grows and the amplitude falls (A0c). Averaged over all tubes, Mouri and Hori (2009) read \(R_0=8.3\)&ndash;\(9.2\,\eta\) and \(V_0=2.4\)&ndash;\(3.2\,U_\eta\), against about 5 \(\eta\) and 4&ndash;10 \(U_\eta\) in the simulations; the authors say so themselves. The chord model of A0c brings the radius to 5.0 \(\eta\) (a divisor of 1.75) and gives a swirl factor between 2 and 3.5, 3 being used. The tails of the same experiments (the highest 0.1% and 1% of the velocity increments, Mouri et al. 2004, 2007) keep the near-axis crossings and read 5.2&ndash;7.4 \(\eta\) and 5&ndash;14 \(U_\eta\); they are left out of the fits.</li>
<li><strong>The extreme swirl values.</strong> The swirl is the least consistent quantity. Ghira et al. (2022) list 6.1&ndash;10.4 \(U_\eta\) at \(Re_\lambda=90\)&ndash;400, above Kida et al. (3.7&ndash;3.9) and Da Silva et al. (3.7&ndash;4.3) at the same \(Re_\lambda\) and above the 5.5&ndash;6.2 that their own mean axis vorticity implies; a factor 0.6 puts them on the common curve. Mouri and Hori (2009) are too low (the chord) and the 0.1% class of Mouri et al. (2007) is too high for a whole tube. The swirl of Belin et al. (1996) needs the unknown tilt of the filament (a factor of about 3.6) and is not used. Above \(Re_\lambda\approx400\) the swirl rests on one source.</li>
<li><strong>The definition of the radius.</strong> The 1/e radius of the vorticity is the Burgers radius, \(r_{\max}=1.12\,R_B\); Kida et al. (2002) and Aligolzadeh et al. (2023) give a core boundary (a factor 0.6 and a value 6.0 \(\eta\) that is not corrected); Ishihara et al. and Sassa and Makita give a diameter of order \(10\,\eta\) without a mean.</li>
<li><strong>The volume of the tubes.</strong> Intense tubes are 1% of the volume by definition; low-pressure cores take 31&ndash;35% (Kida et al. 2002). The mean spacing \(d/\eta\) is given only by Kida et al., so the volume fraction \(V_f\) of the dissipation budget has one check.</li>
</ul>
<p>The aim of this work is to construct a subgrid closure model based on physical and numerical experiments. The tube is a Burgers vortex whose size, swirl and strain, written in Kolmogorov units, depend on \(Re_\lambda\) only; sections 3&ndash;8 derive its energy budget, section 9 collects the data and sections 10 and 11 fit the radius, swirl and circulation as functions of \(Re_\lambda\).</p>
"""

SECTION2 = r"""<h2>2. Theory background</h2>
<h3>Vortex stretching</h3>
<p>In an incompressible flow the vorticity \(\boldsymbol\omega=\nabla\times\mathbf u\) follows</p>
$$\frac{D\boldsymbol\omega}{Dt}=(\boldsymbol\omega\cdot\nabla)\mathbf u+\nu\nabla^2\boldsymbol\omega .$$
<p>The first term on the right is vortex stretching: a strain rate \(\gamma\) along the vorticity raises \(|\boldsymbol\omega|\) at the rate \(\gamma\) and, because the circulation is conserved (Kelvin), thins the vortex. The last term is viscous diffusion, which spreads the vorticity at the rate \(\nu/r^2\). Small scales are made by stretching and removed by viscosity; in turbulence the vorticity lies preferentially along the intermediate eigenvector of the strain, which is mostly extensional (Ashurst et al. 1987), so the stretching is persistent.</p>
<h3>The Burgers vortex</h3>
<p>Burgers (1948) found the exact steady solution in which the two effects balance: a vortex of circulation \(\Gamma\) in the axisymmetric strain \(\mathbf u=(-\gamma r/2,\,0,\,\gamma z)\), whose radial inflow convects the vorticity inwards as fast as viscosity spreads it out,</p>
$$u_\theta=\frac{\Gamma}{2\pi r}\left(1-e^{-\gamma r^2/4\nu}\right),\qquad \omega_z=\frac{\Gamma\gamma}{4\pi\nu}\,e^{-\gamma r^2/4\nu}.$$
<p>Its size, \(r_{\max}=2.24\sqrt{\nu/\gamma}\) (section 3), depends on the strain and the viscosity and not on the circulation; its Reynolds numbers are \(Re_\gamma=\gamma r_{\max}^2/\nu=4x=5.03\) (fixed) and \(Re_c=r_{\max}U_{\max}/\nu\) or \(\Gamma/\nu=8.78\,Re_c\) (free). The dissipation it adds to the strain, \(\rho\gamma\Gamma^2/8\pi\) per unit length, does not depend on \(\nu\) (section 3). The vortex is a model: the strain is imposed and does not feel the vortex.</p>
<h3>Stretched vortices in turbulence</h3>
<p>Townsend (1951) described the fine structure of turbulence as a collection of Burgers-type vortex sheets and tubes. Tennekes (1968) built the small scales from a random array of Burgers vortices and derived their spectrum and size. Lundgren (1982) wound a vortex sheet into a spiral round a stretched tube (the strained spiral vortex), which gives the \(k^{-5/3}\) spectrum, and Horiuti and Fujisawa (2008) extended the idea to several modes in a simulation. Robinson and Saffman (1984) and Neu (1984) studied how a stretched vortex is changed by a non-axisymmetric strain and by its own induced flow. Moffatt, Kida and Ohkitani (1994) showed for large Reynolds number \(\Gamma/\nu\) that the stretched vortex is an asymptotic solution of the Navier&ndash;Stokes equations when the strain is not axisymmetric, called such vortices the sinews of turbulence, and found that the excess dissipation of a Burgers vortex does not change in a non-axisymmetric strain while 98.7% of it falls outside \(r=\sqrt2\,\delta\), where only 37% of the enstrophy sits (section 3). The tube is thus the part of the structure that carries the vorticity, and most of the dissipation it causes lies in its shear layer.</p>
<h3>Scales and what the Burgers vortex says about them</h3>
<p>Richardson (1922) pictured the energy passing from large eddies to smaller ones, and Kolmogorov (1941) gave the scales at which it ends, set by \(\nu\) and the dissipation \(\varepsilon\):</p>
$$\eta=\left(\frac{\nu^3}{\varepsilon}\right)^{1/4},\qquad U_\eta=(\nu\varepsilon)^{1/4},\qquad \gamma_\eta=\left(\frac{\varepsilon}{\nu}\right)^{1/2},\qquad Re_\eta=\frac{U_\eta\eta}{\nu}=1 .$$
<p>Dissipation is intermittent (Meneveau and Sreenivasan 1991) and the velocity-gradient field is organised in vortex tubes and sheets (Nomura and Post 1998). Write the Burgers vortex in Kolmogorov units, \(r_{\max}=\beta\eta\) and \(U_{\max}=u\,U_\eta\). Then \(\gamma r_{\max}^2=4x\nu\) gives</p>
$$\beta^2\,\frac{\gamma}{\gamma_\eta}=4x=5.03,\qquad Re_c=\beta\,u,\qquad \frac{\Gamma}{\nu}=8.78\,\beta u .$$
<p>By dimensional analysis the two numbers \(\beta\) and \(u\) depend on \(Re_\lambda\) only, and nothing else about the tube is free. This is what sections 9&ndash;11 determine from the data. A radius of \(5\eta\) means a strain \(\gamma=0.2\,\gamma_\eta\): the strain that stretches the tubes is a fixed fraction of the Kolmogorov strain at every \(Re_\lambda\). One reading is that where the strain exceeds the Kolmogorov value eddies form and reduce it, so that the strain that survives around a tube is a fraction of \(\gamma_\eta\); the radius and the strain are then one observation, not two.</p>
<h3>Simulations and experiments</h3>
<p>The tubes were found in simulations as connected regions of high vorticity, the worms of Jim&eacute;nez et al. (1993) and Jim&eacute;nez and Wray (1998), and later as the intense vorticity structures (the 1% of the volume of highest vorticity) whose radius is the 1/e radius of the vorticity (Da Silva et al. 2011; Ghira et al. 2022, 2025; Moisy and Jim&eacute;nez 2004 on their geometry and clustering). Other definitions give more of the volume: low-pressure vortex cores (Kida et al. 2002; Makihara et al. 2002; 31&ndash;35% of the volume), coherent fine-scale eddies from the second invariant of the velocity gradient (Tanahashi et al. 2001, 2004), cores scanned out of a database without a threshold (Pirozzoli 2009, 2012) and vortex tubes in thin shear layers (Ishihara et al. 2011, 2013; Elsinga et al. 2023). In experiments a tube is a conditional average of the signal around events of a large velocity increment, fitted with a Burgers profile (Mouri et al. 2003, 2004, 2007; Mouri and Hori 2009; Sassa and Makita 2005), or the tails of the distribution of a velocity derivative (Belin et al. 1996), or an objectively defined vortex in a 3D measurement (Aligolzadeh et al. 2023). The radius is about 5 \(\eta\) in all of them once the geometry of the cut and the definition are accounted for (section 9); the swirl and the circulation differ because the selection decides which tubes are counted (section 9).</p>
"""

NEW_REFS = [
    ("Ashurst", "Ashurst, W. T., Kerstein, A. R., Kerr, R. M. and Gibson, C. H. (1987). Alignment of vorticity and scalar gradient with strain rate in simulated Navier&ndash;Stokes turbulence. <em>Phys. Fluids</em> 30, 2343&ndash;2353. DOI: <a href=\"https://doi.org/10.1063/1.866513\">10.1063/1.866513</a>"),
    ("Horiuti", "Horiuti, K. and Fujisawa, T. (2008). The multi-mode stretched spiral vortex in homogeneous isotropic turbulence. <em>J. Fluid Mech.</em> 595, 341&ndash;366. DOI: <a href=\"https://doi.org/10.1017/S0022112007009251\">10.1017/S0022112007009251</a>"),
    ("Kida", "Kida, S. and Ohkitani, K. (1992). Spatiotemporal intermittency and instability of a forced turbulence. <em>Phys. Fluids A</em> 4, 1018&ndash;1027. As listed in Moffatt et al. (1994); DOI not checked."),
    ("Kolmogorov", "Kolmogorov, A. N. (1941). The local structure of turbulence in incompressible viscous fluid for very large Reynolds numbers. <em>Dokl. Akad. Nauk SSSR</em> 30, 301&ndash;305 (reprinted in <em>Proc. R. Soc. Lond. A</em> 434, 9&ndash;13, 1991). From memory; not in the LIT folder; DOI not checked."),
    ("Lawson", "Lawson, J. M. and Dawson, J. R. (2014). A scanning PIV method for fine-scale turbulence measurements. <em>Exp. Fluids</em> 55, 1857. DOI: <a href=\"https://doi.org/10.1007/s00348-014-1857-7\">10.1007/s00348-014-1857-7</a>"),
    ("Lundgren", "Lundgren, T. S. (1982). Strained spiral vortex model for turbulent fine structure. <em>Phys. Fluids</em> 25, 2193&ndash;2203. As listed in Moffatt et al. (1994); DOI not checked."),
    ("Meneveau", "Meneveau, C. and Sreenivasan, K. R. (1991). The multifractal nature of turbulent energy dissipation. <em>J. Fluid Mech.</em> 224, 429&ndash;484. DOI: <a href=\"https://doi.org/10.1017/S0022112091001830\">10.1017/S0022112091001830</a>"),
    ("Neu", "Neu, J. C. (1984). The dynamics of stretched vortices. <em>J. Fluid Mech.</em> 143, 253&ndash;276. As listed in Moffatt et al. (1994); DOI not checked."),
    ("Nomura", "Nomura, K. K. and Post, G. K. (1998). The structure and dynamics of vorticity and rate of strain in incompressible homogeneous turbulence. <em>J. Fluid Mech.</em> 377, 65&ndash;97. DOI: <a href=\"https://doi.org/10.1017/S0022112098003024\">10.1017/S0022112098003024</a>"),
    ("Richardson", "Richardson, L. F. (1922). <em>Weather Prediction by Numerical Process</em>. Cambridge University Press. The cascade picture; it is not cited in Moffatt et al. (1994) (the reference list was searched) and the book is not in the LIT folder; from memory."),
    ("Robinson", "Robinson, A. C. and Saffman, P. G. (1984). Stability and structure of stretched vortices. <em>Stud. Appl. Math.</em> 70, 163&ndash;181. As listed in Moffatt et al. (1994); DOI not checked."),
    ("Tennekes", "Tennekes, H. (1968). Simple model for the small-scale structure of turbulence. <em>Phys. Fluids</em> 11, 669&ndash;672. As listed in Moffatt et al. (1994); DOI not checked."),
    ("Townsend", "Townsend, A. A. (1951). On the fine-scale structure of turbulence. <em>Proc. R. Soc. Lond. A</em> 208, 534&ndash;542. As listed in Moffatt et al. (1994); DOI not checked."),
    ("Vincent", "Vincent, A. and Meneguzzi, M. (1991). The spatial structure and statistical properties of homogeneous turbulence. <em>J. Fluid Mech.</em> 225, 1&ndash;20. DOI: <a href=\"https://doi.org/10.1017/S0022112091001957\">10.1017/S0022112091001957</a>"),
]


def merge_refs(t):
    """Add NEW_REFS to the list of references, sorted by the author's name; an entry whose first word is already there with the same year is not added twice."""
    a = t.index("<h2>References</h2>")
    b = t.index("</ol>", a)
    ol = t.index("<ol", a)
    start = t.index(">", ol) + 1
    items = re.findall(r"<li style=\"margin:8px 0\">.*?</li>", t[start:b], flags=re.S)
    keys = {re.sub(r"<[^>]+>", "", i).strip().split(",")[0].lower() + re.search(r"\((\d{4})", i).group(1) for i in items if re.search(r"\((\d{4})", i)}
    for name, html in NEW_REFS:
        year = re.search(r"\((\d{4})", html).group(1)
        if name.lower() + year in keys:
            continue
        items.append("<li style=\"margin:8px 0\">%s</li>" % html)
    items.sort(key=lambda i: re.sub(r"<[^>]+>", "", i).replace("&eacute;", "e").replace("é", "e").lower())
    return t[:start] + "\n" + "\n".join(items) + "\n" + t[b:]


def main():
    corr_file = os.path.join(TOOL, "data", "corrections.json")
    import json
    cf = json.load(open(corr_file, encoding="utf-8"))
    rows = fitdata.load(os.path.join(TOOL, "data", "tubes.csv"), corr_file)
    table = source_table(rows, cf["corrections"], cf.get("excluded", {}))
    fig = pagefigures.data_figure(rows)
    sec1 = SECTION1.replace("@TABLE@", table).replace("@FIGURE@", fig)
    t = open(PAGE, encoding="utf8").read()
    stop = t.index("<h2>3. One stretched vortex</h2>")
    if "<h2>1. Summary of the literature</h2>" in t:
        start = t.index("<h2>1. Summary of the literature</h2>")
    else:
        start = stop
    t = t[:start] + sec1 + "\n" + SECTION2 + "\n" + t[stop:]
    t = merge_refs(t)
    open(PAGE, "w", encoding="utf8", newline=chr(10)).write(t)
    print("written sections 1 and 2 and the references")


if __name__ == "__main__":
    main()
