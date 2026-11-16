def ghira_cut_section():
    """The correction of the 1%-volume DNS (Ghira et al.) worked out on the all-tube population of Pirozzoli (2012), in steps down to the two multipliers (radius x 1.25, swirl x 0.67), with the tubes filling 35% of the flow."""
    import ghira_cut_factors as gcf
    import ghira_cut_families as gcfam
    import ghira_cut_g80 as g80
    r, pr, u, pu = gcf.population()
    rf, uf, narrow, _ = gcfam.population()
    body = []
    for phi in (0.10, 0.20, 0.35):
        for g0 in (80.0, 94.0):
            c = g80.constant_g(r, pr, g0, phi)
            body.append(["%.0f%%" % (100 * phi), "G constant, %.0f" % g0, "%.2f" % c["wc"], "%.2f" % c["r_c"], "%.2f" % c["kept"], "%.2f" % c["er"], "%.2f" % c["eu"], "%.2f" % (g80.NARROW_MEAN / c["er"]), "%.2f" % (c["mean_u"] / c["eu"])])
        c = gcfam.cut(rf, uf, narrow, phi)
        body.append(["%.0f%%" % (100 * phi), r"\(r\) and \(G\) independent", "%.2f" % c["wc"], "&ndash;", "%.2f" % c["kept"], "%.2f" % c["er"], "%.2f" % c["eu"], "%.2f" % c["f_R"], "%.2f" % c["f_U"]])
    with open(os.path.join(TOOL, "results", "modelselect.json"), encoding="utf-8") as f:
        scen = json.load(f)["scenarios"]
    now = {m["key"]: m for m in scen[0]["models"]}
    old = {m["key"]: m for m in [s for s in scen if s["label"].startswith("Ghira radius as listed")][0]["models"]}               # the same fits with the radius of Ghira et al. as listed
    big = {m["key"]: m for m in [s for s in scen if s["label"].startswith("Ghira radius x 1.85")][0]["models"]}                   # and with the whole-pdf mean as the target (x 1.85, x 0.6)
    keys = ("D6", "D2", "L1")
    rng = lambda d, k: "%.0f%% to %.0f%%" % (min(d[x][k] for x in keys), max(d[x][k] for x in keys))
    text = r"""<h2>9a. DNS PDF</h2>
<h3>The correction of the 1%-volume DNS (Ghira et al.), in steps</h3>
<p>The DNS of Ghira et al. (2022, 2025) keep the strongest 1% of the volume by vorticity: a subset of the tubes, smaller and faster than the whole population. To bring it to the whole population we chose Pirozzoli (2012) as the reference, because his pdfs of the core radius and of the maximum velocity are of all the vortex cores found, with no lower threshold on the vorticity (his only selections are an angle of at most 20&deg; between the vorticity and the plane normal and a clear swirling pattern), and worked out the scaling factors from it, in the steps below, with the tubes filling 35% of the flow.</p>
<ol>
<li><strong>The row to correct.</strong> The row of Ghira et al. is the mean \(r_{\max}\) and \(U_{\max}\) of the structures above the vorticity \(\omega_c\) that holds the strongest 1% of the volume: \(r_{\max}=4.5\) to 5.0 \(\eta\) (\(1.12\,R_{ivs}/(R_{ivs}/R_B)\)), the swirl converted to the Burgers peak.</li>
<li><strong>The reference.</strong> Pirozzoli (2012), Fig. 2: the pdf of the radius \(r_0\) (mean 7.2 \(\eta\) over the range digitised, median 5.3, most frequent 4.2; the text says 'expected value about 6'; a narrow family of 53% of the tubes with mean 4.55 \(\eta\) and a broad family with median 8.5 \(\eta\) whose far tail sets the mean) and of the maximum velocity \(v_0\) (mean 2.5 \(u_K\); the text says about 2).</li>
<li><strong>The vorticity of a tube.</strong> A Burgers vortex has \(\omega(\rho)=\omega_0\,e^{-\rho^2/2R^2}\), \(R=r_{\max}/1.585\) and \(\omega_0=3.512\,U_{\max}/r_{\max}\) in units of \(1/\tau_\eta\), which is the rms vorticity of homogeneous isotropic turbulence (\(\varepsilon=\nu\langle\omega^2\rangle\)).</li>
<li><strong>Pairing the radius with the swirl.</strong> His pdfs are separate, but his text gives the most frequent circulation, \(\Gamma_\infty/\nu=80\), with \(\Gamma_0=2\pi r_0v_0=0.715\,\Gamma_\infty\), so \(G=\Gamma_\infty/\nu=8.784\,r\,U\) and \(U=G/(8.784\,r)\): a small tube is fast, \(\omega_0\) falls roughly as \(1/r^2\). Two versions bracket the spread of \(G\): (a) \(G\) constant, 80 or 94; (b) \(r\) and \(G\) independent, with \(\mathrm{var}\ln G=\mathrm{var}\ln U-\mathrm{var}\ln r=0.46-0.40\), which reproduces his swirl pdf (mean 2.45 against 2.47) and gives a most frequent \(G\) of 94.</li>
<li><strong>The 1% of the volume.</strong> A tube of length \(L\) has the volume \(\pi\rho_c^2L=2\pi R^2L\ln(\omega_0/\omega_c)\) inside the surface where its vorticity falls to \(\omega_c\) (\(\rho_c=R\sqrt{2\ln(\omega_0/\omega_c)}\)), and the volume \(\pi r_{\max}^2L\) out to \(r_{\max}\). The cut \(\omega_c\) is fixed so that the volume above it is 1% of the flow when all the tubes fill 35% of it (Kida et al.: 0.31 to 0.35): the sum of the first volumes over the sum of the second is 0.01/0.35.</li>
<li><strong>The tubes that are kept.</strong> At 35% about 45% of the tubes are kept, those of small radius (version a: \(r<4.9\,\eta\)), of mean radius 3.6 to 3.7 \(\eta\) and mean swirl 2.7 to 3.8 \(u_K\) (Table D3), with a mean axis vorticity of 3.2 to 4.3 against the 3.9 to 4.8 of Ghira et al. (Table III). 71% to 77% of them belong to the narrow family of the radius pdf, which they represent (23% to 43% of the broad family is kept as well).</li>
<li><strong>The multipliers</strong> are the value of the reference over the value of the kept tubes. Radius: the mean of the narrow family, 4.55 \(\eta\), over the mean radius of the kept tubes, \(f_R=4.55/3.56=1.28\) (a) and \(4.55/3.72=1.22\) (b). Swirl: the mean of all the tubes over that of the kept tubes, \(f_U=0.68\) (a) and 0.66 (b).</li>
<li><strong>Used: radius multiplied by 1.25 and swirl by 0.67</strong>, for Ghira et al. (2022, 2025). At other fillings the factors are 1.12 to 1.16 and 0.71 to 0.73 (20%) and 1.0 and 0.8 (10%).</li>
</ol>
<p class="note">Table D3. The cut of Ghira et al. on the all-tube population of Pirozzoli (2012): the cut \(\omega_c/\omega_{rms}\), the radius \(r_c\) above which a tube is not kept, the fraction of the tubes kept, their mean radius (\(\eta\)) and swirl (\(u_K\)), and the factors: \(f_R\), the mean radius of the narrow family (4.55 \(\eta\)) over that of the kept tubes, and \(f_U\), the mean swirl of all the tubes over that of the kept tubes.</p>
""" + table(["tubes fill", "pairing", r"\(\omega_c/\omega_{rms}\)", r"\(r_c\)", "kept", r"mean \(r\) kept", r"mean \(U\) kept", r"\(f_R\)", r"\(f_U\)"], body) + r"""
<p>What fixes the result. (1) <em>The radius target.</em> The vorticity cut cannot see the large tubes of the broad family, and the narrow family is the tube of the model, so the radius is brought to the narrow family; brought to the mean of all the tubes (7.2 \(\eta\), and 6 in his text) the factor would be 1.7 to 2.0, and the fits are then much worse (below). (2) <em>The filling \(\varphi\).</em> It is an input; its range in the literature is the one quoted. (3) <em>The pairing.</em> Independent \(r\) and \(U\) would give a most frequent \(G\) of 44, not his 80, so a negative correlation of \(\ln r\) and \(\ln U\) (\(-0.9\) in version b) is needed.</p>
<p>Limits. The pdfs are those of one population at one \(Re_\lambda\) (251, the open circles of his Fig. 2; the caption says case D, 98.6), the runs of Ghira et al. cover 90 to 399, and their structures are larger than the kept tubes of the model (\(r_{\max}\) of 4.5 to 5.0 \(\eta\) against 3.6 to 3.7), so the corrected radius, 5.6 to 6.2 \(\eta\), lies above the narrow family. The consequence in the fits (section 10): with the radius of Ghira et al. multiplied by 1.25 and the swirl by 0.67 the rms misfit of the best models is """ + rng(now, "rms") + r""" and the leave-one-source-out error """ + rng(now, "loso") + r"""; with the radius as listed they are """ + rng(old, "rms") + r""" and """ + rng(old, "loso") + r""", and with the radius multiplied by 1.85 (the mean of all the tubes as the target) """ + rng(big, "rms") + r""" and """ + rng(big, "loso") + r""".</p>
"""
    return text
