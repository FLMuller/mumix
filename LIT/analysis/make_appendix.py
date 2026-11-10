"""Append the data-row appendix to the page (replaces an earlier appendix if present); nothing else in the page changes."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
import sys

sys.path.insert(0, HERE)

import math

page = os.path.join(os.path.dirname(HERE), "vortex-energy-balance.html")
t = open(page, encoding="utf8").read()


def table(head, rows):
    return ('<div class="tablebox"><table class="dt">\n<thead><tr>' + "".join("<th>%s</th>" % h for h in head) + "</tr></thead>\n<tbody>\n" +
            "\n".join("<tr>" + "".join("<td>%s</td>" % c for c in r) + "</tr>" for r in rows) + "\n</tbody></table></div>\n")


# ---------------------------------------------------------------- Ghira et al. (2022), Table III
Re = [90, 148, 191, 242, 314, 292, 399]
Rivs = [4.28, 4.23, 4.10, 4.06, 3.98, 3.98, 3.90]
RB = [0.96, 0.98, 0.97, 0.98, 0.98, 0.98, 0.97]
Uivs = [6.01, 7.11, 7.83, 8.31, 9.33, 9.37, 10.23]
cG = [14.36, 13.01, 12.19, 11.32, 10.92, 11.34, 10.35]
rows = []
for i in range(7):
    rows.append(["%d" % Re[i], "%.2f / %.2f / %.2f" % (Rivs[i], RB[i], cG[i]),
                 "%.0f" % (cG[i] * math.sqrt(Re[i])), "%.2f" % (1.12 * Rivs[i] / RB[i]),
                 "%.2f" % Uivs[i]])
ghira = ("<h3>A1. Ghira, Elsinga and da Silva (2022)</h3>\n"
         "<p><strong>Where:</strong> Table III (mean values for the intense vorticity structures of each DNS; one row per simulation, \\(Re_\\lambda=90\\)–399, the 292 and 399 rows being both \\(2048^3\\)); the definitions are in Sec. III, Eq. (8)–(10).</p>\n"
         "<p><strong>Entries used:</strong> \\(R_{ivs}/\\eta\\) (mean radius of the intense vorticity structure: the radial distance from the axis where the azimuthal mean of the axial vorticity has fallen to \\(1/e\\) of its axis value, Eq. 8), \\(R_{ivs}/R_B\\) (that radius over the Burgers radius \\(R_B=2\\sqrt{\\nu/\\gamma}\\) built from the local strain \\(\\gamma\\)), and \\(Re_\\Gamma Re_\\lambda^{-1/2}\\) (last column; the circulation Reynolds number \\(\\Gamma_{ivs}/\\nu\\) divided by \\(Re_\\lambda^{1/2}\\)). \\(U_{ivs}/u_\\eta\\) is shown for reference only.</p>\n"
         "<p><strong>Interpretation:</strong> \\(R_\\Gamma=\\Gamma/\\nu=(Re_\\Gamma Re_\\lambda^{-1/2})\\sqrt{Re_\\lambda}\\). For the radius, \\(r_{\\max}=1.12\\,R_B=1.12\\,R_{ivs}/(R_{ivs}/R_B)\\), where 1.12 is \\(r_{\\max}/R_B=\\sqrt{x}\\) for a Burgers vortex (\\(x=1.2564\\)). Each entry is a mean over many structures, so there is no per-row uncertainty in the paper.</p>\n"
         "<p><strong>Reading adopted:</strong> Ghira et al. define \\(\\Gamma_{ivs}=2\\pi\\langle U_{ivs}\\rangle R_{ivs}\\) (Eq. 9), with the swirl read at \\(r=R_{ivs}\\), which for a Burgers vortex is the circulation inside \\(R_{ivs}\\) (about 61% of the total). Their listed \\(\\Gamma_{ivs}/\\nu\\) is also about 0.83 of \\(2\\pi U_{ivs}R_{ivs}\\) from the same table (162 against 136 at \\(Re_\\lambda=90\\)), most likely because the paper averages the product per structure. Here the listed value is taken as the total circulation \\(R_\\Gamma\\) of the model, which is the reading that agrees with Kida et al. and Mouri and Hori in magnitude (it gives a peak swirl \\(U_{\\max}/U_\\eta=3.1\\) at \\(Re_\\lambda=90\\) rising to 5.2 at 399). The cost is that the swirl listed in Table III, \\(U_{ivs}/u_\\eta=6.0\\)–10.2, is then 1.5–2.5 times the model's \\(U_{\\max}/U_\\eta\\) of 3.5–4.5, so the model describes the circulation of these tubes but not their swirl.</p>\n"
         + table(["\\(Re_\\lambda\\)", "Table III: \\(R_{ivs}/\\eta\\) / \\(R_{ivs}/R_B\\) / \\(Re_\\Gamma Re_\\lambda^{-1/2}\\)", "\\(R_\\Gamma\\) used", "\\(r_{\\max}/\\eta\\) used", "\\(U_{ivs}/u_\\eta\\) (not used)"], rows)
         + "<h3>A1b. Ghira, Elsinga and da Silva (2025)</h3>\n"
         "<p><strong>Where:</strong> Table 2 (characteristics of the IVS from all simulations of the lifetime study, obtained as in the 2022 paper), and Table 11 for \(R_{ivs}/R_B\).</p>\n"
         "<p><strong>Entries used:</strong> only the two \(R_{ivs}/\eta\) values at \(Re_\lambda=54\), 4.29 (\(128^3\)) and 4.23 (\(256^3\), forcing centred at \(k_p=4\)). The other rows of Table 2 (4.28, 4.23, 4.10, 4.06 at \(Re_\lambda=91\), 143, 189, 239) are the same simulations as Table III of the 2022 paper (quoted there as 90, 148, 191, 242) and were not repeated. The paper gives no circulation.</p>\n"
         "<p><strong>Interpretation:</strong> \(r_{\max}=1.12\,R_{ivs}/(R_{ivs}/R_B)\) as for the 2022 data, but Table 2 gives no \(R_{ivs}/R_B\) for these two cases (Table 11 gives 0.99 and 0.97 for a repeated \(512^3\) run). I took \(R_{ivs}/R_B=0.97\), the mean of the 2022 values, which is an assumption. With only two points the group takes the largest \(\\sigma_{\\text{ref}}\\) of the larger groups.</p>\n"
         + table(["\(Re_\lambda\)", "Table 2: \(R_{ivs}/\eta\)", "\(R_{ivs}/R_B\) (assumed)", "\(r_{\max}/\eta\) used"],
                 [["54", "%.2f" % a, "0.97", "%.2f" % (1.12 * a / 0.97)] for a in (4.29, 4.23)]))

# ---------------------------------------------------------------- Jimenez et al. (1993), Table 3
Rj = [(35.8, 4.22), (62.8, 4.16), (94.5, 4.16), (168.1, 3.85)]
jim = ("<h3>A2. Jiménez, Wray, Saffman and Rogallo (1993)</h3>\n"
       "<p><strong>Where:</strong> Table 3 (average worm characteristics from the tracking algorithm; one row per simulation, \\(Re_\\lambda=35.8\\), 62.8, 94.5, 168.1); the algorithm is described in the text above the table.</p>\n"
       "<p><strong>Entry used:</strong> the column \\(R/\\eta\\), the mean worm radius. The radius is the \\(1/e\\) radius of a Gaussian fitted to the azimuthally averaged vorticity in the plane normal to the axis.</p>\n"
       "<p><strong>Interpretation:</strong> the \\(1/e\\) radius of a Gaussian vorticity profile is the Burgers radius \\(R_B\\), so \\(r_{\\max}=1.12\\times R\\). The paper's circulation column (\\(Re_\\Gamma/Re_\\lambda\\)) is not used.</p>\n"
       + table(["\\(Re_\\lambda\\)", "Table 3: \\(R/\\eta\\)", "\\(r_{\\max}/\\eta\\) used"], [["%.1f" % a, "%.2f" % b, "%.2f" % (1.12 * b)] for a, b in Rj]))

# ---------------------------------------------------------------- Tanahashi et al. (2001)
tan = ("<h3>A3. Tanahashi, Iwase and Miyauchi (2001)</h3>\n"
       "<p><strong>Where:</strong> Fig. 7 and the text around it (DNS of a turbulent mixing layer, \\(Re_{\\theta0}=500\\); the cases \\(Re_{\\theta0}=700\\) and 900 are said to be similar), and the statement that the mean diameter of the coherent fine scale eddies remains about eight times \\(\\eta\\) in all cases.</p>\n"
       "<p><strong>Entry used:</strong> the probability density function of the eddy diameter peaks at \\(D\\approx9\\,\\eta\\) (Fig. 7). The radius of an eddy is defined as the distance from the centre to where the mean azimuthal velocity is at its maximum, so it is directly \\(r_{\\max}\\).</p>\n"
       "<p><strong>Interpretation:</strong> \\(r_{\\max}=D/2=4.5\\,\\eta\\). The paper does not give a single \\(Re_\\lambda\\) for the mixing layer; I placed the value at \\(Re_\\lambda=200\\), which is an assumption. It is a single point.</p>\n"
       + table(["\\(Re_\\lambda\\)", "Fig. 7: peak of the diameter pdf", "\\(r_{\\max}/\\eta\\) used"], [["200 (assumed)", "\\(D/\\eta\\approx9\\)", "4.50"]]))

# ---------------------------------------------------------------- Mouri and Hori, Table 2
runs = [("B1", 332, 8.45, 2.43, 20.5), ("B2", 488, 8.47, 2.39, 20.2), ("B3", 716, 8.59, 2.47, 21.2), ("B4", 945, 9.21, 2.73, 25.1), ("B5", 1080, 8.93, 2.83, 25.3),
        ("B6", 1304, 8.28, 2.88, 23.8), ("D1", 719, 8.56, 2.43, 20.8), ("D2", 1098, 8.91, 2.56, 22.8), ("D3", 1416, 9.12, 2.79, 25.4), ("D4", 1693, 8.72, 2.91, 25.4),
        ("D5", 1934, 8.81, 3.18, 28.0)]
mou = ("<h3>A4. Mouri and Hori (preprint, file Mouri (2009))</h3>\n"
       "<p><strong>Where:</strong> Table 2 (parameters of vortex tubes in boundary layers B1–B6 and duct flows D1–D5), with \\(Re_\\lambda\\) from Table 1 (hot-wire measurements in a wind tunnel).</p>\n"
       "<p><strong>Entry used:</strong> \\(Re_0=R_0V_0/\\nu\\), where \\(R_0\\) and \\(V_0\\) come from fitting a Burgers vortex to the conditionally averaged spanwise velocity profile of tubes crossing the probe (Fig. 3), \\(R_0\\) being the radius and \\(V_0\\) the maximum circulation velocity.</p>\n"
       "<p><strong>Interpretation:</strong> \\(Re_c=U_{\\max}r_{\\max}/\\nu\\) of the model is the same quantity as \\(Re_0\\), so the value is used directly. The authors state that \\(R_0\\) (8–9 \\(\\eta\\)) is larger than the true mean radius and \\(V_0\\) smaller than the true circulation velocity, because tubes passing off-centre or at an angle are included; the product \\(Re_0\\) is the least biased quantity and is the one used, not \\(R_0\\) or \\(V_0\\) separately. The Reynolds numbers are the largest of the data set (332–1934), and these are the all-tube population.</p>\n"
       + table(["Run", "\\(Re_\\lambda\\) (Table 1)", "Table 2: \\(R_0/\\eta\\)", "Table 2: \\(V_0/u_K\\)", "Table 2: \\(Re_0\\)", "\\(Re_c\\) used"],
               [[r, "%d" % a, "%.2f" % b, "%.2f" % c, "%.1f" % d, "%.1f" % d] for r, a, b, c, d in runs]))

# ---------------------------------------------------------------- Kida et al. (2002), Table 2 (not used)
kida_rows = []
for Rl, D, G, ut, vc in ((83, 10.4, 110, 3.1, 0.35), (170, 10.8, 123, 3.3, 0.31)):
    kida_rows.append(["%d" % Rl, "%.1f / %d / %.1f / %.2f" % (D, G, ut, vc), "%.1f" % (D / 2), "%.2f" % (ut * 1.175), "%d" % G, "%.1f" % (D / 2 * math.sqrt(math.pi / vc))])
kid = ("<h3>A5. Kida, Goto and Makihara (2002) (shown in red in the data table, not used in the fit)</h3>\n"
       "<p><strong>Where:</strong> Table 2 (characteristic quantities of the low-pressure vortices at the two resolutions: \\(256^3\\), \\(Re_\\lambda=83\\), and \\(512^3\\), \\(Re_\\lambda=170\\), from Table 1); the core boundary is shown in Fig. 3(a).</p>\n"
       "<p><strong>Entries used:</strong> \\(D/l_K\\) (core diameter; the core is the region inside the boundary of the low-pressure vortex, which is not circular), \\(\\Gamma/\\nu\\) (circulation), \\(u_\\theta/u_K\\) (mean azimuthal velocity at the core boundary) and \\(V_{\\text{core}}/V\\) (volume fraction of the cores).</p>\n"
       "<p><strong>Interpretation:</strong> radius \\(=D/2\\); circulation \\(\\Gamma/\\nu\\) as listed (it is the value at the core boundary, not the total of a Burgers vortex); swirl \\(=1.175\\,u_\\theta/u_K\\), where 1.175 converts the swirl at the core boundary to the Burgers peak assuming the boundary encloses 60% of the enstrophy (the boundary then sits at 0.6 of the peak radius); spacing \\(d=(D/2)\\sqrt{\\pi/(V_{\\text{core}}/V)}\\), from the tube density \\(L_e=(V_{\\text{core}}/V)/(\\pi(D/2)^2)\\) and \\(d=1/\\sqrt{L_e}\\). The 1.175 factor is an assumption of mine, and the boundary radius is not the Burgers peak radius, which is why these rows are shown but not used.</p>\n"
       + table(["\\(Re_\\lambda\\)", "Table 2: \\(D/l_K\\) / \\(\\Gamma/\\nu\\) / \\(u_\\theta/u_K\\) / \\(V_{\\text{core}}/V\\)", "radius \\(D/2\\)", "swirl \\(1.175\\,u_\\theta/u_K\\)", "\\(\\Gamma/\\nu\\)", "spacing \\(d/\\eta\\)"], kida_rows))

app = ('<h2>Appendix: data rows, where they come from and how they were read</h2>\n'
       '<p>Every literature value in the data table of Step 7 is listed here, with the location in the paper (table, figure or equation), the raw entries and the arithmetic that gives the number in our table. Quantities are in Kolmogorov units (\\(\\eta\\), \\(u_\\eta\\), \\(\\nu\\)). The PDFs are in the LIT folder under the file names given in the references.</p>\n'
       + ghira + jim + tan + mou + kid)

if "<h2>Appendix: data rows" in t:
    i = t.index("<h2>Appendix: data rows")
    j = t.index("</main>")
    t = t[:i] + app + t[j:]
else:
    t = t.replace("</main>", app + "</main>", 1)
open(page, "w", encoding="utf8", newline="\n").write(t)
print("appendix written", len(app))
