"""Source data of the vortex-tube model: every value taken from a paper, how it was converted, and what the model uses.

Each source has a tube set (whole tubes or intense tubes, see section 9 of the page), the places in the paper, the
conversion equations, and rows.  A row is (mtype, Re_lambda, nu, raw entries, used value, role).

  mtype   rmax  radius of maximum swirl, r_max/eta
          gam   circulation Gamma/nu
          swirl peak swirl, U_max/U_eta
          rec   tube Reynolds number Re_c = r_max U_max/nu
          d     tube spacing d/eta
  role    fit      used in the fits of the page
          cmp      shown for comparison, not fitted
  nu      kinematic viscosity as tabulated by the paper (units differ: DNS code units or cm2/s); None if not tabulated.

Conversions (Burgers vortex, x = 1.2564312 is the root of e**x - 2x - 1 = 0, KB = 1 - exp(-x) = 0.7153):
  r_max = sqrt(x) R_B = 1.1209 R_B        R_B = 2 sqrt(nu/gamma) is also the 1/e radius of the vorticity
  U_max = KB Gamma/(2 pi r_max)           so Gamma/nu = 2 pi/KB * r_max U_max/nu = 8.78 r_max U_max/nu
  u(r)/U_max = (1 - exp(-x k^2)) / (k KB), k = r/r_max       swirl at radius r
  u'/U_eta = (Re_lambda/sqrt(15))**0.5
"""
import os
import sys
import math

x = 1.2564312086261697
KB = 1 - math.exp(-x)
SQX = math.sqrt(x)
G = 2 * math.pi / KB


def peak_from_swirl_at(u_at_r, r_over_RB):
    """Peak swirl from the swirl at radius r = (r/R_B) R_B of a Burgers vortex."""
    k = r_over_RB / SQX
    return u_at_r / ((1 - math.exp(-x * k * k)) / (k * KB))


def uprime_over_ueta(Re):
    return (Re / math.sqrt(15)) ** 0.5


ORDER = ["rmax", "gam", "swirl", "rec", "d"]
MTYPE = {"rmax": r"Radius \(r_{\max}/\eta\)", "gam": r"Circulation \(\Gamma/\nu\)", "swirl": r"Peak swirl \(U_{\max}/U_\eta\)",
         "rec": r"Tube Reynolds number \(Re_c\)", "d": r"Spacing \(d/\eta\)"}
MSHORT = {"rmax": r"\(r_{\max}/\eta\)", "gam": r"\(\Gamma/\nu\)", "swirl": r"\(U_{\max}/U_\eta\)", "rec": r"\(Re_c\)", "d": r"\(d/\eta\)"}
SETNAME = {"intense": "intense", "whole": "whole"}

SOURCES = []


def source(**kw):
    kw.setdefault("rows", [])
    SOURCES.append(kw)
    return kw


def row(src, mtype, Re, nu, raw, used, role, note="", eps=None):
    src["rows"].append(dict(mtype=mtype, Re=Re, nu=nu, eps=eps, raw=raw, used=used, role=role, note=note, src=src["key"]))


# ----------------------------------------------------------------------------------------------- Ghira 2022
g22 = source(key="Ghira22", cite="Ghira, Elsinga and da Silva (2022)", short="Ghira et al. (2022)", tubes="intense",
             where=r"Table III (mean values for the intense vorticity structures, one row per simulation); Table II (\(\nu\) in code units); definitions in Sec. III, Eq. (8)&ndash;(10).",
             selection=r"The structures are the points with the highest vorticity magnitude, 1% of the volume (the intense vorticity structures, IVS); the radius is where the azimuthal mean of the axial vorticity has fallen to \(1/e\) of its axis value.",
             eqs=[r"r_{\max}=\sqrt{x}\,R_B=1.12\,\dfrac{R_{ivs}}{R_{ivs}/R_B}",
                  r"\dfrac{\Gamma}{\nu}=\dfrac{2\pi}{K_B}\,Re_c=8.78\,\dfrac{r_{\max}}{\eta}\dfrac{U_{\max}}{U_\eta}\qquad(\text{total circulation from the converted radius and swirl; the listed }Re_\Gamma\text{ is not used})",
                  r"\dfrac{U_{\max}}{U_\eta}=\dfrac{U_{ivs}/u_\eta}{f(k)},\quad k=\dfrac{R_{ivs}/R_B}{\sqrt{x}},\quad f(k)=\dfrac{1-e^{-xk^2}}{k\,(1-e^{-x})}"],
             notes=r"Their \(\Gamma_{ivs}=2\pi\langle U_{ivs}\rangle R_{ivs}\) (Eq. 9) is the circulation inside \(R_{ivs}\), about 61% of the total of a Burgers vortex, and is about 0.83 of \(2\pi U_{ivs}R_{ivs}\) from the same table (162 against 136 at \(Re_\lambda=90\)), probably because the paper averages the product per structure. The total circulation is therefore taken from the converted radius and swirl, \(\Gamma/\nu=8.78\,Re_c\) with \(Re_c=(r_{\max}/\eta)(U_{\max}/U_\eta)\); the listed \(Re_\Gamma Re_\lambda^{-1/2}\) is kept in the table as the source value. The swirl row converts the swirl listed at \(R_{ivs}\) to the Burgers peak; the tubes are intense, so \(Re_c\) is about twice that of the whole tubes.")
RE = [90, 148, 191, 242, 314, 292, 399]
NU = [0.0145, 0.0057, 0.0034, 0.0023, 0.0014, 0.0009, 0.0010]
EPS_G = [9.98, 9.54, 9.88, 9.52, 9.84, 10.07, 11.91]
R_IVS = [4.28, 4.23, 4.10, 4.06, 3.98, 3.98, 3.90]
R_RB = [0.96, 0.98, 0.97, 0.98, 0.98, 0.98, 0.97]
U_IVS = [6.01, 7.11, 7.83, 8.31, 9.33, 9.37, 10.23]
C_G = [14.36, 13.01, 12.19, 11.32, 10.92, 11.34, 10.35]
for i in range(7):
    row(g22, "rmax", RE[i], NU[i], ["%.2f" % R_IVS[i], "%.2f" % R_RB[i]], 1.12 * R_IVS[i] / R_RB[i], "fit", eps=EPS_G[i])
    row(g22, "gam", RE[i], NU[i], ["%.2f" % C_G[i]], G * 1.12 * R_IVS[i] / R_RB[i] * peak_from_swirl_at(U_IVS[i], R_RB[i]), "cmp", eps=EPS_G[i])
    row(g22, "swirl", RE[i], NU[i], ["%.2f" % U_IVS[i], "%.2f" % R_RB[i]], peak_from_swirl_at(U_IVS[i], R_RB[i]), "cmp", eps=EPS_G[i])
g22["rawcols"] = {"rmax": [r"\(R_{ivs}/\eta\)", r"\(R_{ivs}/R_B\)"], "gam": [r"\(Re_\Gamma Re_\lambda^{-1/2}\)"], "swirl": [r"\(U_{ivs}/u_\eta\)", r"\(R_{ivs}/R_B\)"]}
g22["nuunit"] = "code units"
g22["epsunit"] = "code units"

# ----------------------------------------------------------------------------------------------- Ghira 2025
g25 = source(key="Ghira25", cite="Ghira, Elsinga and da Silva (2025)", short="Ghira et al. (2025)", tubes="intense",
             where=r"Table 2 (characteristics of the IVS of all simulations, obtained as in the 2022 paper); Table 1 and Ghira et al. (2024), Table 1, for \(\nu\).",
             selection=r"As Ghira et al. (2022): the intense vorticity structures, 1% of the volume.",
             eqs=[r"r_{\max}=1.12\,\dfrac{R_{ivs}}{R_{ivs}/R_B},\qquad R_{ivs}/R_B=0.97\ (\text{assumed})"],
             notes=r"Only the two \(Re_\lambda=54\) radii are new: the other rows of Table 2 (4.28, 4.23, 4.10, 4.06 at \(Re_\lambda=91\), 143, 189, 239) are the simulations of the 2022 paper. Table 2 gives no \(R_{ivs}/R_B\) for these runs (Table 11 gives 0.99 and 0.97 for a repeated \(512^3\) run), so the mean of the 2022 values, 0.97, is assumed. The paper gives no circulation.")
row(g25, "rmax", 54, 0.0370, ["4.29", "0.97 (assumed)"], 1.12 * 4.29 / 0.97, "fit", "128^3", eps=10.01)
row(g25, "rmax", 54, None, ["4.23", "0.97 (assumed)"], 1.12 * 4.23 / 0.97, "fit", "256^3, forcing at k_p = 4")
g25["rawcols"] = {"rmax": [r"\(R_{ivs}/\eta\)", r"\(R_{ivs}/R_B\)"]}
g25["nuunit"] = "code units"
g25["epsunit"] = "code units"

# ----------------------------------------------------------------------------------------------- Jimenez 1993
j93 = source(key="Jimenez93", cite="Jim&eacute;nez, Wray, Saffman and Rogallo (1993)", short="Jim&eacute;nez et al. (1993)", tubes="intense",
             where=r"Table 3 (average worm characteristics from the tracking algorithm, one row per simulation); the algorithm is described in the text above the table.",
             selection=r"Worms: connected regions of vorticity above a threshold (the 1% of the volume of highest vorticity); the radius is the \(1/e\) radius of a Gaussian fitted to the azimuthal mean of the axial vorticity.",
             eqs=[r"r_{\max}=\sqrt{x}\,R_B=1.12\,R"],
             notes=r"The \(1/e\) radius of a Gaussian vorticity profile is the Burgers radius. The circulation column of the table is not used. \(\nu\) is not read here because the copy of Table 1 is a scan.")
for Re, R in ((35.8, 4.22), (62.8, 4.16), (94.5, 4.16), (168.1, 3.85)):
    row(j93, "rmax", Re, None, ["%.2f" % R], 1.12 * R, "fit")
j93["rawcols"] = {"rmax": [r"\(R/\eta\)"]}
j93["nuunit"] = ""

# ----------------------------------------------------------------------------------------------- Tanahashi 2001
t01 = source(key="Tanahashi01", cite="Tanahashi, Iwase and Miyauchi (2001)", short="Tanahashi et al. (2001)", tubes="whole",
             where=r"Fig. 7 and the text around it (DNS of a turbulent mixing layer, \(Re_{\theta0}=500\)).",
             selection=r"Coherent fine-scale eddies educed with the second invariant of the velocity gradient and the vorticity, without a vorticity threshold; the radius is the distance from the centre to the maximum of the mean azimuthal velocity.",
             eqs=[r"r_{\max}=\dfrac{D}{2}"],
             notes=r"The probability density function of the diameter peaks at \(D\approx9\,\eta\) (the text says the mean diameter stays about \(8\,\eta\)). The paper gives no \(Re_\lambda\) for the mixing layer; \(Re_\lambda=200\) is assumed.")
row(t01, "rmax", 200, None, ["9 (peak of the pdf)"], 4.5, "fit", "Re_lambda assumed")
t01["rawcols"] = {"rmax": [r"\(D/\eta\)"]}
t01["nuunit"] = ""

# ----------------------------------------------------------------------------------------------- Aligolzadeh 2023
a23 = source(key="Aligolzadeh23", cite="Aligolzadeh, Holzner and Dawson (2023)", short="Aligolzadeh et al. (2023)", tubes="intense",
             where=r"Sec. 2 (the von K&aacute;rm&aacute;n facility; DNS of Li et al. at \(Re_\lambda=418\)); Sec. 3.1 and the Conclusions (the mean radius); Fig. 12 and the text before it (the ratio \(R/R_B\)).",
             selection=r"Objectively defined vortices (Haller et al.) detected in 3D PIV data (resolution about \(1\,\eta\)); they occupy 1.4% of the volume. \(R\) is the distance from the axis to the boundary of the vortex, and \(R_B=(4\nu/\gamma_0)^{1/2}\) comes from the centre-line stretching rate (their Eq. 2.5).",
             eqs=[r"R_B=\dfrac{R}{R/R_B},\qquad r_{\max}=\sqrt{x}\,R_B=1.12\,\dfrac{R}{R/R_B}"],
             notes=r"Assumptions: the value 5.1 and the mean \(R/R_B=0.95\) are those of the experiment (the text gives the two means as 0.95 and 1.1, and says the experimental pdf is skewed to the left of 1). The DNS mean \(R/R_B=1.1\) cannot be used because the paper gives no separate DNS radius. The radius is larger than those of the DNS studies.")
row(a23, "rmax", 179, None, ["5.1", "0.95"], 1.12 * 5.1 / 0.95, "fit", "experiment; water, nu not tabulated")
a23["rawcols"] = {"rmax": [r"\(R/\eta\)", r"mean \(R/R_B\)"]}
a23["nuunit"] = ""

# ----------------------------------------------------------------------------------------------- Da Silva 2011
d11 = source(key="DaSilva11", cite="Da Silva, Dos Reis and Pereira (2011)", short="Da Silva et al. (2011)", tubes="intense",
             where=r"Sec. 3 (the text before and after Table 1 and Fig. 3): forced isotropic turbulence (HIT) at \(Re_\lambda=111\) and the turbulent plane jet at \(Re_\lambda=120\) (deep inside the shear layer).",
             selection=r"Intense vorticity structures as in Ghira et al. (1% of the volume); \(R\) is the \(1/e\) radius of the vorticity, \(u_0\) the mean tangential velocity at \(R\), \(R_B\) the Burgers radius from the stretching rate.",
             eqs=[r"r_{\max}=1.12\,\dfrac{R}{R/R_B}",
                  r"\dfrac{U_{ivs}}{u_\eta}=\dfrac{u_0}{u'}\left(\dfrac{Re_\lambda}{\sqrt{15}}\right)^{1/2},\qquad \dfrac{U_{\max}}{U_\eta}=\dfrac{U_{ivs}/u_\eta}{f(k)}"],
             notes=r"The text gives \(R/\eta=4.6\) for both flows, \(u_0/u'=0.68\) and 0.76, and \(R/R_B=0.99\) and 0.97. Table 1 of the paper (a compilation of IVS data from the literature) is an image and was not read, and the circulation Reynolds number quoted there uses a different definition (\(Re_\Gamma Re_\lambda^{-1/2}\approx28\)), so it is not used. Their \(u_0/u'\) (0.7&ndash;0.8) is lower than that of Ghira et al. (1.0&ndash;1.25).")
for Re, flow, R, rr, u0 in ((111, "HIT", 4.6, 0.99, 0.68), (120, "jet", 4.6, 0.97, 0.76)):
    row(d11, "rmax", Re, None, ["%.1f" % R, "%.2f" % rr], 1.12 * R / rr, "cmp", flow)
    U = u0 * uprime_over_ueta(Re)
    row(d11, "swirl", Re, None, ["%.2f" % u0, "%.2f" % uprime_over_ueta(Re), "%.2f" % rr], peak_from_swirl_at(U, rr), "cmp", flow)
d11["rawcols"] = {"rmax": [r"\(R/\eta\)", r"\(R/R_B\)"], "swirl": [r"\(u_0/u'\)", r"\(u'/u_\eta\)", r"\(R/R_B\)"]}
d11["nuunit"] = ""

# ----------------------------------------------------------------------------------------------- Mouri 2009 (all tubes)
EPS_M = {332: 0.0332, 488: 0.226, 716: 1.85, 945: 5.37, 1080: 13.8, 1304: 24.6, 719: 0.405, 1098: 2.87, 1416: 9.13, 1693: 19.2, 1934: 34.4}
EPS_04 = {295: 0.0316, 430: 0.254, 655: 2.03, 861: 5.65, 1054: 14.6, 1258: 26.2}
RUNS09 = [("B1", 332, 0.141, 8.45, 2.43, 0.263, 20.5), ("B2", 488, 0.142, 8.47, 2.39, 0.213, 20.2), ("B3", 716, 0.142, 8.59, 2.47, 0.182, 21.2),
          ("B4", 945, 0.142, 9.21, 2.73, 0.175, 25.1), ("B5", 1080, 0.142, 8.93, 2.83, 0.169, 25.3), ("B6", 1304, 0.143, 8.28, 2.88, 0.157, 23.8),
          ("D1", 719, 0.141, 8.56, 2.43, 0.179, 20.8), ("D2", 1098, 0.141, 8.91, 2.56, 0.152, 22.8), ("D3", 1416, 0.142, 9.12, 2.79, 0.146, 25.4),
          ("D4", 1693, 0.142, 8.72, 2.91, 0.138, 25.4), ("D5", 1934, 0.142, 8.81, 3.18, 0.143, 28.0)]
m09 = source(key="Mouri09", cite="Mouri and Hori (2009)", short="Mouri and Hori (2009)", tubes="whole",
             where=r"Table 2 (parameters of vortex tubes in boundary layers B1&ndash;B6 and duct flows D1&ndash;D5), \(Re_\lambda\) from Table 1 of the same paper; \(\nu\) from Table I of Mouri et al. (2007) for the same experiments. Published as Fluid Dyn. Res. 41, 021402 (the file is the preprint).",
             selection=r"All vortex tubes: the conditionally averaged spanwise velocity around moderate enhancements of the velocity increment is fitted with a Burgers profile; \(R_0\) and \(V_0\) are the radius and the maximum circulation velocity of the fit.",
             eqs=[r"r_{\max}=R_0,\qquad \dfrac{U_{\max}}{U_\eta}=\dfrac{V_0}{u_K},\qquad Re_c=Re_0=\dfrac{R_0V_0}{\nu}"],
             notes=r"The authors say \(R_0\) is larger and \(V_0\) smaller than the true means, because off-centre and inclined tubes are included. The radius and the swirl are corrected (A0c: radius divided by 1.75, swirl multiplied by 3) and both are fitted; the listed \(Re_0\) is not fitted, the tube Reynolds number follows from the corrected values.")
for lab, Re, nu, R0, V0, vr, Re0 in RUNS09:
    row(m09, "rmax", Re, nu, [lab, "%.2f" % R0], R0, "cmp", eps=EPS_M[Re])
    row(m09, "swirl", Re, nu, [lab, "%.2f" % V0, "%.3f" % vr], V0, "cmp", eps=EPS_M[Re])
    row(m09, "rec", Re, nu, [lab, "%.1f" % Re0], Re0, "fit", eps=EPS_M[Re])
m09["rawcols"] = {"rmax": ["run", r"\(R_0/\eta\)"], "swirl": ["run", r"\(V_0/u_K\)", r"\(V_0/\langle v^2\rangle^{1/2}\)"], "rec": ["run", r"\(Re_0\)"]}
m09["nuunit"] = r"cm\(^2\)/s"
m09["epsunit"] = r"m\(^2\)/s\(^3\)"

# ----------------------------------------------------------------------------------------------- Mouri 2007 (intense tubes)
# Table II, columns 1-5 duct flows D1-D5, columns 6-11 boundary layers B1-B6; for the 0.1% and the 1% threshold
RUNS07 = [("D1", 719, 0.141), ("D2", 1098, 0.141), ("D3", 1416, 0.142), ("D4", 1693, 0.142), ("D5", 1934, 0.142),
          ("B1", 332, 0.141), ("B2", 488, 0.142), ("B3", 716, 0.142), ("B4", 945, 0.142), ("B5", 1080, 0.142), ("B6", 1304, 0.143)]
T07 = {"0.1%": dict(R0=[5.21, 5.64, 5.47, 5.87, 6.20, 5.18, 5.24, 5.56, 5.97, 5.66, 6.15],
                    VK=[8.67, 10.0, 11.3, 12.8, 14.0, 7.60, 8.37, 9.53, 10.6, 11.7, 12.8],
                    Re0=[45.2, 56.4, 61.8, 75.1, 86.8, 39.4, 43.9, 53.0, 63.3, 66.2, 78.7]),
       "1%": dict(R0=[6.50, 6.61, 6.92, 6.76, 7.03, 6.53, 6.44, 6.92, 7.38, 7.14, 7.19],
                  VK=[6.11, 6.83, 7.53, 8.41, 9.17, 5.61, 5.98, 6.65, 7.28, 7.83, 8.53],
                  Re0=[39.7, 45.2, 52.1, 56.9, 64.5, 36.6, 38.5, 46.0, 53.7, 55.9, 61.3])}
m07 = source(key="Mouri07", cite="Mouri, Hori and Kawashima (2007)", short="Mouri et al. (2007)", tubes="intense",
             where=r"Table II (parameters for intense vortical structures: radius \(R_0\), maximum circulation velocity \(V_0\), \(Re_0=R_0V_0/\nu\), for the 0.1% and the 1% threshold; columns 1&ndash;5 duct flows, 6&ndash;11 boundary layers); Table I (\(Re_\lambda\), \(\nu\)).",
             selection=r"Intense vortical structures: the highest 0.1% or 1% of the absolute spanwise-velocity increments; the averaged profile is fitted with a Burgers vortex. The table is a scrambled text layer: the columns were read in order and checked against the radii that Pirozzoli (2009, Table 1) quotes from the same table (5.18, 5.24, 5.56, 5.97, 5.66 at \(Re_\lambda\) 332, 488, 716, 945, 1080).",
             eqs=[r"r_{\max}=R_0,\qquad \dfrac{U_{\max}}{U_\eta}=\dfrac{V_0}{u_K},\qquad Re_c=Re_0=\dfrac{R_0V_0}{\nu}"],
             notes=r"These are the intense tubes of the same experiments as Mouri and Hori (2009): at the 0.1% threshold \(R_0=5.2\)&ndash;6.2 \(\eta\), \(V_0=7.6\)&ndash;14 \(u_K\) (0.6&ndash;0.8 of the r.m.s. velocity) and \(Re_0=39\)&ndash;87; at 1%, \(R_0=6.4\)&ndash;7.4, \(V_0=5.6\)&ndash;9.2 and \(Re_0=37\)&ndash;65. The swirl scales with the r.m.s. velocity and \(Re_0\propto Re_\lambda^{1/2}\) (their Fig. 7).")
for thr in ("0.1%", "1%"):
    for k, (lab, Re, nu) in enumerate(RUNS07):
        tag = "%s %s" % (thr, lab)
        row(m07, "rmax", Re, nu, [tag, "%.2f" % T07[thr]["R0"][k]], T07[thr]["R0"][k], "cmp", eps=EPS_M[Re])
        row(m07, "swirl", Re, nu, [tag, "%.2f" % T07[thr]["VK"][k]], T07[thr]["VK"][k], "cmp", eps=EPS_M[Re])
        row(m07, "rec", Re, nu, [tag, "%.1f" % T07[thr]["Re0"][k]], T07[thr]["Re0"][k], "cmp", eps=EPS_M[Re])
m07["rawcols"] = {"rmax": ["threshold, run", r"\(R_0/\eta\)"], "swirl": ["threshold, run", r"\(V_0/u_K\)"], "rec": ["threshold, run", r"\(Re_0\)"]}
m07["nuunit"] = r"cm\(^2\)/s"
m07["epsunit"] = r"m\(^2\)/s\(^3\)"

# ----------------------------------------------------------------------------------------------- Mouri 2004 (intense tubes, 1%)
RUNS04 = [(295, 0.144, 6.08, 0.600, 5.23, 32), (430, 0.145, 6.04, 0.526, 5.55, 34), (655, 0.145, 6.28, 0.485, 6.31, 40),
          (861, 0.147, 7.14, 0.476, 7.10, 51), (1054, 0.150, 6.98, 0.469, 7.73, 54), (1258, 0.149, 7.37, 0.464, 8.37, 62)]
m04 = source(key="Mouri04", cite="Mouri, Hori and Kawashima (2004)", short="Mouri et al. (2004)", tubes="intense",
             where=r"Table I (experimental conditions, flow characteristics and parameters of vortex tubes; one column per data set; boundary layers, \(Re_\lambda=295\)&ndash;1258).",
             selection=r"The highest 1% of the absolute spanwise-velocity increments (intense tubes), fitted with a Burgers profile.",
             eqs=[r"r_{\max}=R_0,\qquad \dfrac{U_{\max}}{U_\eta}=\dfrac{V_0}{u_K},\qquad Re_c=Re_0=\dfrac{R_0V_0}{\nu}"],
             notes=r"The table is a scrambled text layer; the six data sets were read in order of \(Re_\lambda\). \(V_0\) is about half the r.m.s. velocity (0.46&ndash;0.60) and \(Re_0\propto Re_\lambda^{1/2}\); these values agree with Mouri et al. (2007) at 1% threshold.")
for Re, nu, R0, vr, VK, Re0 in RUNS04:
    row(m04, "rmax", Re, nu, [str(Re), "%.2f" % R0], R0, "cmp", eps=EPS_04[Re])
    row(m04, "swirl", Re, nu, [str(Re), "%.2f" % VK, "%.3f" % vr], VK, "cmp", eps=EPS_04[Re])
    row(m04, "rec", Re, nu, [str(Re), "%d" % Re0], Re0, "cmp", eps=EPS_04[Re])
m04["rawcols"] = {"rmax": ["data set", r"\(R_0/\eta\)"], "swirl": ["data set", r"\(V_0/u_K\)", r"\(V_0/\langle v^2\rangle^{1/2}\)"], "rec": ["data set", r"\(Re_0\)"]}
m04["nuunit"] = r"cm\(^2\)/s"
m04["epsunit"] = r"m\(^2\)/s\(^3\)"

# ----------------------------------------------------------------------------------------------- Mouri 2003
m03 = source(key="Mouri03", cite="Mouri, Hori and Kawashima (2003)", short="Mouri et al. (2003)", tubes="intense",
             where=r"Sec. IV (the text after Fig. 1) and Table I (ten grid-turbulence experiments, \(Re_\lambda=105\)&ndash;329, \(\nu=0.143\)&ndash;0.160 cm\(^2\)/s).",
             selection=r"Vortex tubes from enhancements of the transverse-velocity increment (\(|v|>3\langle v^2\rangle^{1/2}\)), Burgers-profile comparison.",
             eqs=[r"r_{\max}=r_0"],
             notes=r"Only a range is given in the text, \(r_0\approx(6\)&ndash;\(7)\,\eta\) regardless of \(Re_\lambda\); the paper has no per-run table of \(R_0\) or \(V_0\). The authors say that these radii are well above the resolution and represent typical radii.")
row(m03, "rmax", "105&ndash;329", "0.143&ndash;0.160", ["6&ndash;7 (text)"], 6.5, "cmp", "range", eps="0.051&ndash;5.71")
m03["rawcols"] = {"rmax": [r"\(r_0/\eta\)"]}
m03["nuunit"] = r"cm\(^2\)/s"
m03["epsunit"] = r"m\(^2\)/s\(^3\)"

# ----------------------------------------------------------------------------------------------- Belin 1996
b96 = source(key="Belin96", cite="Belin, Maurer, Tabeling and Willaime (1996)", short="Belin et al. (1996)", tubes="intense",
             where=r"Sec. 4 (Burgers filament crossing the probe, Eqs. (6)&ndash;(8)); Sec. 5 and Fig. 5 (size distributions of the worms for \(Re_\lambda=151\)&ndash;718, mean size \(R=3.5\,\eta\)); Sec. 7 (\(Re_\lambda>700\)).",
             selection=r"Intense events in the tails of the pdf of the velocity derivative, in helium gas between counter-rotating disks (hot film on a 7 \(\mu\)m carbon fibre, resolution 0.2&ndash;3 \(\eta\)), selected by conditional sampling and interpreted as Burgers filaments crossing the probe close to their axis; \(R\) is the Gaussian width of the vorticity, \(\omega=\omega_0e^{-r^2/2R^2}\).",
             eqs=[r"R=0.31\,U\,\Delta t\quad(\text{peak spacing }\Delta x=U\Delta t\approx3.2\,R=2\,r_{\max})",
                  r"r_{\max}=\sqrt{2x}\,R=1.585\,R\qquad(R_B=\sqrt{2}\,R)"],
             notes=r"The method measures a time record, which the mean velocity \(U\) turns into a distance (frozen flow); the radius follows from the spacing of the two extrema of the signal as the filament passes, and the peak amplitude gives \(U_{\max}\). The value \(R=3.5\,\eta\) is the position of the maximum of the size distribution seen by the probe (Fig. 5, which collapses for \(Re_\lambda=151\)&ndash;718), quoted by the authors as the mean worm size; the same distribution built from the DNS of Jim&eacute;nez et al. through the same probe geometry (their Eq. 9) peaks at 2.8 \(\eta\), so the probe sizes are 1.25 times the DNS sizes. The distribution is skewed with a tail to about 20 \(\eta\), and a rough reading of the figure puts its mean near 6 \(\eta\) and its median near 5 \(\eta\). The row uses the peak, \(r_{\max}=1.585\times3.5=5.5\,\eta\), as a range of \(Re_\lambda\). Above \(Re_\lambda\approx700\) the size distribution widens: the mean velocity increment across the filament decreases and its mean radius increases so that the circulation does not change; the authors read this as an instability of the filaments. The paper has no table of \(R\), \(U_{\max}\) or the circulation by \(Re_\lambda\).")
row(b96, "rmax", "151&ndash;718", None, ["3.5 (text)"], 1.585 * 3.5, "cmp", "range")
b96["rawcols"] = {"rmax": [r"\(R/\eta\)"]}
b96["nuunit"] = ""


# ----------------------------------------------------------------------------------------------- Kida 2002
k02 = source(key="Kida02", cite="Kida, Goto and Makihara (2002)", short="Kida et al. (2002)", tubes="whole",
             where=r"Table 2 (a table image; characteristic quantities of the low-pressure vortices at the two resolutions) and Table 1 (\(Re_\lambda\), \(\nu\) in code units); the core boundary is shown in Fig. 3(a).",
             selection=r"Low-pressure vortices: the cores occupy 31&ndash;35% of the volume; \(D\) is the diameter of the (non-circular) core boundary, \(u_\theta\) the mean azimuthal velocity at the boundary, \(\Gamma\) the circulation along it.",
             eqs=[r"r_{\max}=\dfrac{D}{2},\qquad \dfrac{\Gamma}{\nu}\ \text{as listed (inside the boundary)}",
                  r"\dfrac{U_{\max}}{U_\eta}=1.175\,\dfrac{u_\theta}{u_K}\ (\text{boundary taken at }0.6\,r_{\max}\text{, where }f=0.855)",
                  r"\dfrac{d}{\eta}=\dfrac{D}{2\eta}\sqrt{\dfrac{\pi}{V_{\text{core}}/V}}\qquad(L_e=\dfrac{V_{\text{core}}/V}{\pi(D/2)^2},\ d=L_e^{-1/2})"],
             notes=r"The factor 1.175 assumes that the boundary encloses 60% of the enstrophy of a Burgers vortex, which puts it at \(0.6\,r_{\max}\); then \(f(0.6)=0.855\). This is an assumption of mine, and the boundary radius is not the Burgers peak radius.")
KIDA = [(83, 2.50e-3, 10.4, 110, 3.1, 0.35, 0.13), (170, 6.25e-4, 10.8, 123, 3.3, 0.31, 0.12)]
for Re, nu, D, Gm, ut, vc, ek in KIDA:
    row(k02, "rmax", Re, nu, ["%.1f" % D], D / 2, "cmp", eps=ek)
    row(k02, "gam", Re, nu, ["%d" % Gm], Gm, "cmp", eps=ek)
    row(k02, "swirl", Re, nu, ["%.1f" % ut], 1.175 * ut, "cmp", eps=ek)
    row(k02, "d", Re, nu, ["%.1f" % D, "%.2f" % vc], D / 2 * math.sqrt(math.pi / vc), "cmp", eps=ek)
k02["rawcols"] = {"rmax": [r"\(D/\eta\)"], "gam": [r"\(\Gamma/\nu\)"], "swirl": [r"\(u_\theta/u_K\)"], "d": [r"\(D/\eta\)", r"\(V_{\text{core}}/V\)"]}
k02["nuunit"] = "code units"
k02["epsunit"] = "code units"

# ----------------------------------------------------------------------------------------------- Pirozzoli 2009
p09 = source(key="Pirozzoli09", cite="Pirozzoli (2009, 2012)", short="Pirozzoli (2009, 2012)", tubes="whole",
             where=r"Pirozzoli (2009), Table 1 (average radius of vortex cores extracted from DNS and from the experiments of Mouri et al.); Pirozzoli (2012), Sec. 3 and Fig. 2 (pdfs of core radius and induced velocity, DNS at several \(Re_\lambda\)).",
             selection=r"Vortex cores scanned out of the DNS database without a vorticity threshold (candidate centres from pressure minima, \(r_0\) the radius of maximum velocity); all classes of vortices.",
             eqs=[r"r_{\max}=r_0"],
             notes=r"One DNS value, \(Re_\lambda=250\): \(r_0/\eta=5.12\). Pirozzoli (2012) states that typical tubes have \(r_0\approx6\,\eta\) and \(v_0\approx2\,u_K\) at all the \(Re_\lambda\) of his DNS, without a table. The experimental entries of the table (5.18, 5.24, 5.56, 5.97, 5.66 at \(Re_\lambda\) 332, 488, 716, 945, 1080) repeat the 0.1%-threshold radii of Mouri et al. (2007) and are not counted again.")
row(p09, "rmax", 250, None, ["5.12"], 5.12, "cmp", "DNS")
row(p09, "rmax", "&mdash;", None, ["6 (typical, text 2012)"], 6.0, "cmp", "Pirozzoli 2012, DNS at several Re_lambda")
row(p09, "swirl", "&mdash;", None, ["2 (typical, text 2012)"], 2.0, "cmp", "Pirozzoli 2012")
p09["rawcols"] = {"rmax": [r"\(r_0/\eta\)"], "swirl": [r"\(v_0/u_K\)"]}
p09["nuunit"] = ""

# ----------------------------------------------------------------------------------------------- Ishihara 2011 / 2013
i13 = source(key="Ishihara13", cite="Ishihara, Hunt and Kaneda (2011); Ishihara, Kaneda and Hunt (2013)", short="Ishihara et al. (2011, 2013)", tubes="whole",
             where=r"Abstracts and Sec. 3 of both papers (DNS to \(4096^3\), \(Re_\lambda=1131\)).",
             selection=r"Strong vortex tubes inside thin shear layers of thickness about \(\lambda\); typical diameter of the tubes of order \(10\,\eta\); peak vorticity up to \(35\,\omega_{\text{rms}}\).",
             eqs=[r"r_{\max}\approx\dfrac{D}{2}\approx5"],
             notes=r"Only an order of magnitude (\(D\sim10\,\eta\)) is given, not a mean, so the row is a comparison of the right size, not a measurement.")
row(i13, "rmax", 1131, None, ["~10 (order of)"], 5.0, "cmp", "order of magnitude")
i13["rawcols"] = {"rmax": [r"\(D/\eta\)"]}
i13["nuunit"] = ""

# ----------------------------------------------------------------------------------------------- Sassa 2005
s05 = source(key="Sassa05", cite="Sassa and Makita (2005)", short="Sassa and Makita (2005)", tubes="whole",
             where=r"Chapter in Engineering Turbulence Modelling and Experiments 6, Table 1 (the flows), Sec. on results and Fig. 8 (dependence on \(Re_\lambda\)).",
             selection=r"Elementary vortices from conditional sampling of the transverse-velocity change at a moderate threshold (\(C=2.5\)) in stably stratified grid turbulence, homogeneous shear turbulence and a nocturnal surface layer, \(Re_\lambda=19\)&ndash;2391.",
             eqs=[r"r_{\max}=\dfrac{D}{2}\approx5,\qquad \dfrac{W_{\max}}{u_K}\propto Re_\lambda^{0.28}"],
             notes=r"The diameter is about \(10\,\eta\) at all \(Re_\lambda\); the maximum azimuthal velocity over \(u_K\) grows as \(Re_\lambda^{0.28}\) (about twice the exponent of Kida et al.), except in the shear flows, and Mouri et al. (2004) measure larger values with a higher threshold. Only the trends are given in the text (the values are in Fig. 8), so the radius is a single comparison row.")
row(s05, "rmax", "19&ndash;2391", None, ["~10 (text)"], 5.0, "cmp", "range")
s05["rawcols"] = {"rmax": [r"\(D/\eta\)"]}
s05["nuunit"] = ""

# ----------------------------------------------------------------------------------------------- wall-bounded and mixing-layer DNS (no Re_lambda)
w = source(key="Wall", cite="Das et al. (2006); Miyauchi et al. (2006); Wang et al. (2007)", short="Das, Miyauchi, Wang (2006, 2007)", tubes="whole",
           where=r"Abstracts (Das et al., Theor. Comput. Fluid Dyn. 20, 55; Miyauchi et al., Fluid Mech. Appl. 79, 71; Wang et al., Int. J. Heat Fluid Flow 28, 1280).",
           selection=r"Coherent fine-scale eddies in channel flow (\(Re_\tau\) up to 1270) and in a mixing layer (\(Re_{\omega0}=700\)), most expected values of the pdfs.",
           eqs=[r"r_{\max}=\dfrac{D}{2}"],
           notes=r"These flows have no isotropic \(Re_\lambda\), so the rows cannot be placed on the \(Re_\lambda\) axis. Das et al.: \(D=10\)&ndash;\(12\,\eta\) and a mean maximum azimuthal velocity \(0.5\)&ndash;\(0.6\,u'_{\text{rms}}\); Miyauchi et al.: \(D\approx10\,\eta\), \(2.0\,u_K\) near the wall and \(8.5\,\eta\), \(1.7\,u_K\) in the logarithmic region; Wang et al.: \(D\approx8\,\eta\), swirl \(2.0\to1.2\,u_K\) through the transition.")
row(w, "rmax", "&mdash;", None, ["10&ndash;12 (channel)"], 5.5, "cmp", "Das 2006")
row(w, "rmax", "&mdash;", None, ["10; 8.5 (channel)"], 4.6, "cmp", "Miyauchi 2006")
row(w, "rmax", "&mdash;", None, ["8 (mixing layer)"], 4.0, "cmp", "Wang 2007")
row(w, "swirl", "&mdash;", None, ["2.0; 1.7 (channel)"], 1.85, "cmp", "Miyauchi 2006")
row(w, "swirl", "&mdash;", None, ["2.0 to 1.2 (mixing layer)"], 1.6, "cmp", "Wang 2007")
w["rawcols"] = {"rmax": [r"\(D/\eta\)"], "swirl": [r"\(u_{\theta,\max}/u_K\)"]}
w["nuunit"] = ""

BY_KEY = {s["key"]: s for s in SOURCES}

# ---------------------------------------------------------------------------------------------- physical equivalents
# Model side: the fluid is water (nu = 1e-6 m2/s) and the dissipation rate is a reference value, eps = 0.1 W/kg, unless the
# paper is a laboratory experiment with a tabulated nu and eps (Mouri et al., in air) or gives the Kolmogorov length
# (Aligolzadeh et al., water).  eta = (nu**3/eps)**0.25 then converts every length given in eta to metres.
NU_REF = 1.0e-6          # m2/s, water
EPS_REF = 0.1            # W/kg, reference dissipation rate
ETA_ALIGO = 0.926e-3     # m, Kolmogorov length of the von Karman experiment (their Sec. 2)
L11_CODE = {90: 0.90, 148: 0.84, 191: 0.86, 242: 0.84, 314: 0.86, 292: 0.60, 399: 0.96}   # Ghira 2022, Table II (code units)

# measurement method of each source (shown in the section 9 table and the appendix)
METHOD = {
    "Ghira22": "DNS, forced isotropic", "Ghira25": "DNS, forced isotropic", "Jimenez93": "DNS, forced isotropic",
    "Tanahashi01": "DNS, mixing layer", "Aligolzadeh23": "3D scanning PIV, water tank",
    "DaSilva11": "DNS, isotropic and plane jet",
    "Mouri09": "hot wire, 1D velocity increments", "Mouri07": "hot wire, 1D velocity increments",
    "Mouri04": "hot wire, 1D velocity increments", "Mouri03": "hot wire, 1D velocity increments, grid",
    "Belin96": "hot film, 1D velocity derivative, helium",
    "Kida02": "DNS, forced isotropic", "Pirozzoli09": "DNS, isotropic", "Ishihara13": "DNS, isotropic 4096^3",
    "Sassa05": "probe records, conditional sampling", "Wall": "DNS, channel and mixing layer",
}
for _s in SOURCES:
    _s["method"] = METHOD[_s["key"]]


WHY = {
    ("Ghira22", "gam"): "the listed Re<sub>&Gamma;</sub> is the circulation inside R<sub>ivs</sub>; the total, 8.78 r<sub>max</sub>U<sub>max</sub>, is used and awaits the intense-tube fit",
    ("Ghira22", "swirl"): "swirl at R<sub>ivs</sub> of intense tubes; awaits the intense-tube fit (section 9)",
    ("DaSilva11", "rmax"): "intense tubes, new data; awaits the intense-tube fit (section 9)",
    ("DaSilva11", "swirl"): "intense tubes, new data; awaits the intense-tube fit (section 9)",
    ("Mouri09", "rmax"): "R<sub>0</sub> biased high by the authors' account; only Re<sub>0</sub> is fitted",
    ("Mouri09", "swirl"): "V<sub>0</sub> biased low by the authors' account; only Re<sub>0</sub> is fitted",
    ("Mouri07", "*"): "intense tubes; Re<sub>c</sub> is 2&ndash;3 times the model (section 9); awaits the intense-tube fit",
    ("Mouri04", "*"): "intense tubes; Re<sub>c</sub> is 2&ndash;3 times the model (section 9); awaits the intense-tube fit",
    ("Mouri03", "rmax"): "range only (6&ndash;7 &eta;), no per-run values",
    ("Kida02", "rmax"): "core-boundary radius D/2, not the Burgers peak; two points",
    ("Kida02", "gam"): "circulation inside the core boundary, not the total; two points",
    ("Kida02", "swirl"): "swirl at the core boundary, factor 1.175 assumed; two points",
    ("Kida02", "d"): "from the core volume fraction and D; two points",
    ("Pirozzoli09", "rmax"): "whole-tube DNS radius; awaits the whole-tube fit (section 9)",
    ("Pirozzoli09", "swirl"): "typical value without an Re<sub>&lambda;</sub>",
    ("Ishihara13", "rmax"): "order of magnitude only (D ~ 10 &eta;)",
    ("Sassa05", "rmax"): "trend only; the values are in a figure",
    ("Wall", "*"): "wall or mixing-layer flow, no isotropic Re<sub>&lambda;</sub>",
}


# Corrections applied to the reported values before the model sees them (section 9 table, appendix A0c).  Each factor multiplies the value
# calculated from the paper: radius (rmax), swirl (swirl); the tube Reynolds number and the circulation follow as the product.
CORR = {
    "Mouri09": {"rmax": 1 / 1.75, "swirl": 3.0,
                "text": r"Radius divided by 1.75 and swirl multiplied by 3. The authors fit the mean profile of all tubes: the tube positions are all the local extrema of the Gaussian-smoothed "
                        r"velocity increment (scale about \(6\,\eta\)), so weak and off-axis crossings count as much as central ones. A hot-wire path crosses a tube at a random offset from its axis "
                        r"and a random tilt, and the radius read is the spacing of the two extrema of the signal, which grows with the offset, so the radius is too large and, for the same crossings, "
                        r"the amplitude too small. Mouri and Hori say that \(R_0\) is greater than the true mean radius and \(V_0\) less than the true mean circulation velocity for all vortex "
                        r"tubes, because of tubes with \(|y_0|\gtrsim R_0\) and \(\theta_0\ne0\). Radius: the chord model (A0c, tilt limit 45&deg;) gives a ratio of 1.75 for the mean profile of an "
                        r"all-tube average (an amplitude cut of about a quarter of the central swirl), so the true radius is \(8.8/1.75=5.0\,\eta\), the value of the other sources. Swirl: the same "
                        r"crossings lower the amplitude by a factor 2&ndash;3.5 (tilt limit 20&ndash;70&deg;, true radius 4.5&ndash;5.4 \(\eta\)); the factor 3 is the value at which the swirl lies "
                        r"within 3% of the common curve through Ghira et al. (&times;0.6), Da Silva et al. and Kida et al. (the data allow 2.5 as well). The threshold averages of Mouri et al. (2004, 2007) "
                        r"come from the same experiments and are left out of the fits (A8, A9)."},
    "Ghira22": {"swirl": 0.6,
                "text": r"Swirl multiplied by 0.6. The listed \(U_{ivs}/u'=1.0\)&ndash;1.25 is high against the other simulations of intense tubes (Jim&eacute;nez and Wray 0.86&ndash;0.99, "
                        r"Da Silva et al. 0.68&ndash;0.76, mixing layer 0.5) and the hot wire (0.5&ndash;0.8). Their own mean axis vorticity (\(\omega_{ivs}/\omega_{rms}=3.9\)&ndash;4.8, Table III) "
                        r"and the Burgers radius imply a peak swirl of 5.5&ndash;6.2 \(U_\eta\) at all \(Re_\lambda\), against the listed 6&ndash;9.5: the excess grows with \(u'\), which "
                        r"suggests that the swirl at \(R_{ivs}\) includes a velocity from the surrounding flow. A constant factor of 0.58 (0.56&ndash;0.60 for the seven runs) puts the swirl on "
                        r"the curve \(U_{\max}/U_\eta\propto Re_\lambda^{0.34}\) of the other sources; 0.6 is used. At the same \(Re_\lambda\) of 83&ndash;120 the swirl of Kida et al. (3.7&ndash;3.9) "
                        r"and Da Silva et al. (3.7&ndash;4.3) is well below the listed 6.1&ndash;7.1, so more data at low \(Re_\lambda\) support moving Ghira et al. than moving the others; with the "
                        r"swirl as listed the fits are 17&ndash;19% off, against 8% with the factor."},
}


def corr_factor(src, mtype):
    """Factor multiplying the value used of a row of this source and measurement type (1 where no correction is applied)."""
    c = CORR.get(src)
    if not c:
        return 1.0
    fr, fu = c.get("rmax", 1.0), c.get("swirl", 1.0)
    return {"rmax": fr, "swirl": fu, "rec": fr * fu, "gam": fr * fu}.get(mtype, 1.0) if not (src == "Kida02" and mtype == "gam") else 1.0


def used_value(r):
    """The value of a row after the correction."""
    return r["used"] * corr_factor(r["src"], r["mtype"])


FIT_SOURCES_OUT = {"Mouri04": "a tail (the 1% threshold) of the chord distribution of the experiments of Mouri and Hori (2009), left out of the fits",
                   "Mouri07": "a tail (the 0.1% and 1% thresholds) of the chord distribution of the experiments of Mouri and Hori (2009), left out of the fits"}
FITTED = {}


def fitted_set():
    """The (source, Re_lambda, kind) of the rows that the fitting tool (LIT/fittingtool, section 10) fits: single Re_lambda, kind r or U, source not left out.
    Read from the tool's data file with its corrections, so this page and the tool cannot disagree."""
    if not FITTED:
        tool = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fittingtool")
        if tool not in sys.path:
            sys.path.insert(0, tool)
        import fitdata
        rows = fitdata.load(os.path.join(tool, "data", "tubes.csv"), os.path.join(tool, "data", "corrections.json"))
        obs = fitdata.observations(rows)
        for kind in ("r", "U"):
            for src, re in zip(obs[kind]["src"], obs[kind]["re"]):
                FITTED[(src, float(re), kind)] = True
        FITTED[("loaded", 0.0, "")] = True
    return FITTED


def reason(r):
    """Role of a row: 'fitted' (it enters the fits of section 10), or 'not fitted' with the reason."""
    if r["src"] in FIT_SOURCES_OUT:
        return "not fitted: " + FIT_SOURCES_OUT[r["src"]]
    if r["mtype"] in ("rec", "gam"):
        return "not fitted: the fits compute the circulation and the tube Reynolds number from the corrected radius and swirl"
    if r["mtype"] == "d":
        return "not fitted: the spacing is compared with the volume fraction only"
    kind = {"rmax": "r", "swirl": "U"}[r["mtype"]]
    if isinstance(r["Re"], (int, float)) and (r["src"], float(r["Re"]), kind) in fitted_set():
        return "fitted"
    if not isinstance(r["Re"], (int, float)):
        return "not fitted: no single Re<sub>&lambda;</sub> (drawn as a bar or a trend, not fitted)"
    return "not fitted: " + (WHY.get((r["src"], r["mtype"])) or WHY.get((r["src"], "*")) or "not in the data of the fits")


def physical(r):
    """(nu m2/s, eps W/kg, eta m or None, how) as used on the model side for a row."""
    s = BY_KEY[r["src"]]
    if "cm" in s.get("nuunit", ""):                       # Mouri et al.: laboratory air, tabulated nu (cm2/s) and eps (W/kg)
        nu, eps = r["nu"], r["eps"]
        if isinstance(nu, (int, float)):
            nu = nu * 1e-4
            return nu, eps, (nu**3 / eps) ** 0.25, "measured"
        return "1.43&ndash;1.60&times;10<sup>-5</sup>", eps, None, "measured"
    if r["src"] == "Aligolzadeh23":                       # eta given, water assumed
        eps = NU_REF**3 / ETA_ALIGO**4
        return NU_REF, eps, ETA_ALIGO, "derived from eta = 0.926 mm, water"
    return NU_REF, EPS_REF, (NU_REF**3 / EPS_REF) ** 0.25, "reference"


def all_rows():
    out = []
    for s in SOURCES:
        out.extend(s["rows"])
    return out


def re_sort_key(r):
    Re = r["Re"]
    return Re if isinstance(Re, (int, float)) else (1e9 if "&mdash;" in str(Re) else 1e8)


if __name__ == "__main__":
    rows = all_rows()
    print(len(SOURCES), "sources,", len(rows), "rows")
    for s in SOURCES:
        print("  %-14s %-8s %3d rows" % (s["key"], s["tubes"], len(s["rows"])))
