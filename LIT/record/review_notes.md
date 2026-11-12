# Review of the sources from page images (2026-11-12, Fable)

Working notes: one block a paper. "OK" = every number we use was read on the rendered page and matches sourcedata.py.
Crops are (pdf, page, x0, y0, x1, y1) as fractions of the page, for the recording book.

## Ghira 2022 (Phys. Rev. Fluids 7, 104605) -- OK
- Table III p8 (crop 0.08 0.05 0.95 0.45): R_ivs/eta 4.28 4.23 4.10 4.06 3.98 3.98 3.90; R_ivs/R_B 0.96 0.98 0.97 0.98 0.98 0.98 0.97; U_ivs/u_eta 6.01 7.11 7.83 8.31 9.33 9.37 10.23; Re_Gamma/Re_lambda^0.5 14.36 13.01 12.19 11.32 10.92 11.34 10.35. All match.
- Table II p3 (crop 0.08 0.05 0.95 0.42): Re_lambda 90 148 191 242 314 292 399; nu 0.0145 0.0057 0.0034 0.0023 0.0014 0.0009 0.0010; eps 9.98 9.54 9.88 9.52 9.84 10.07 11.91; kmax*eta 2.0 (2.1 last). Match.
- Definitions p6 (crop 0.08 0.05 0.95 0.95): IVS = points of highest vorticity magnitude covering 1% of the volume; R_ivs is where the azimuthal mean of the axial vorticity = omega_0/e (Eq. 8), Gaussian profile assumed (Eq. 7); R_B = 2 (nu/alpha)^0.5 (Eq. 5); Gamma = 2 pi <U_ivs> R_ivs (Eq. 9: circulation at R_ivs, not the total); Re_Gamma = Gamma_ivs/nu (Eq. 10). U_ivs is the azimuthal mean of u_theta at r = R_ivs (p7).
- Assumptions: none in reading. Conversion r_max = 1.1209 R_B uses the paper's own R_ivs/R_B.

## Ghira 2025 (J. Fluid Mech. 1007, A62) -- OK, and NEW data
- Table 2 p7 (crop 0.08 0.07 0.92 0.33): N^3, Re_lambda, R_ivs/eta, L_ivs/eta, U_ivs/u', R_ivs/U_ivs, eta/u': 128^3 54 4.29 39.75 1.11; 256^3 91 4.28 48.70 1.25; 512^3 143 4.23 53.18 1.15; 768^3 189 4.10 54.98 1.11; 1024^3 239 4.06 55.86 1.05; last row 256^3 54 4.23 44.83 1.13 (forcing at k_p = 4).
- Table 1 p4: nu 0.0370 (128^3, Re 54), eps 10.01; 256^3 Re 54 (k_p=4): nu 0.0145, eps 10.03. So nu and eps of the second Re=54 row ARE in the paper (sourcedata has None).
- NEW: U_ivs/u' is given for all rows (1.11 at Re 54, 1.13 for the k_p = 4 run): a swirl value at Re_lambda = 54 that we did not use. U_ivs/u_eta = (U_ivs/u') (Re_lambda/sqrt(15))^0.5.
- No R_ivs/R_B in this paper: 0.97 ASSUMED (the mean of the 2022 values 0.96-0.98).
- Rows 91-239 are the 2022 simulations relabelled (91, 143, 189, 239 against 90, 148, 191, 242 in 2022): not new, not used twice.

## Jimenez 1993 (J. Fluid Mech. 255, 65) -- OK, and unused circulation
- Table 3 p16 (crop 0.05 0.03 0.95 0.75 holds Fig. 11, Fig. 12 and Table 3): Re_lambda 35.8 62.8 94.5 168.1; l/L 3.16 2.60 3.15 2.88; R/eta 4.22 4.16 4.16 3.85; Re_gamma/Re_lambda^0.5 21.1 17.0 18.1 16.5; N_w 26 32 14 23. Match.
- p15: the radial vorticity distribution is fitted to a Gaussian; the radius is the 1/e radius of the Gaussian. So r_max = 1.1209 R (as sourcedata).
- Unused: Re_gamma/Re_lambda^0.5 (circulation). To check: definition of Re_gamma on p15.

## Aligolzadeh 2023 (J. Fluid Mech.) -- OK with one reading assumption
- p4: R_lambda = 179, eta = 0.926 mm (von Karman tank, scanning PIV). p8: 'average radius of the structures found to be R = 5.1 eta'. p21 repeats it.
- p15-16: R_B = sqrt(4 nu/alpha_0) (same as 2 sqrt(nu/alpha)); 'small differences in the mean R/R_B = 0.95 and 1.1' for 'the experiments and DNS'.
- ASSUMPTION: 0.95 is the experiment and 1.1 the DNS (the order of the sentence).
- Jimenez p15 (crop 0.05 0.03 0.95 0.97): 'the vorticity in the normal plane is averaged azimuthally, and the resulting radial distribution is fitted to a Gaussian. The local radius of the worm is defined as the 1/e radius of the Gaussian, and the circulation as that of the fitted distribution.' So Re_gamma is the TOTAL circulation of the fitted Gaussian over nu: Gamma/nu = 21.1 sqrt(35.8) = 126, 17.0 sqrt(62.8) = 135, 18.1 sqrt(94.5) = 176, 16.5 sqrt(168.1) = 214. NEW circulation data for intense tubes (not in sourcedata). Worms are followed until the peak vorticity falls below omega' (intense tubes).

## Da Silva 2011 (J. Fluid Mech. 685, 165) -- CONFLICT in the swirl
- Table 1 p8 (rotated; crop 0.05 0.05 0.97 0.60): present HIT: Re_lambda 111, <R>/eta 4.6, <R/R_B> 0.99, <u0>/u' 0.68, <u0>/u_eta 9.0, Re_Gamma/Re_lambda^0.5 28.8. Plane jet: 120, 4.6, 0.97, 0.76, 7.15, 28.3.
- Text p7 (crop 0.05 0.05 0.97 0.97): R = core radius, u0 = maximum tangential velocity, Gamma = 2 pi R u0, R_B = 2 (nu/sigma_0)^0.5.
- sourcedata used u0/u' times u'/u_eta = (Re_lambda/sqrt 15)^0.5 = 5.35 (HIT): 0.68 x 5.35 = 3.64, and 0.76 x 5.57 = 4.23 (jet). But the table prints <u0>/u_eta = 9.0 and 7.15 directly, and Re_Gamma/Re^0.5 = 28.8 with Gamma = 2 pi R u0 gives u0/u_eta = 28.8 sqrt(111)/(2 pi 4.6) = 10.5 (HIT) and 28.3 sqrt(120)/(2 pi 4.6) = 10.7 (jet).
- So the paper is not consistent with u'/u_eta = (Re_lambda/sqrt 15)^0.5: its printed u0/u_eta and its circulation both say about 9-10.5, its u0/u' says 3.6-4.2. FACTOR 2.5 AMBIGUITY. The values 3.68 and 4.30 were used earlier as support for the Ghira x 0.6 correction: that support is not safe.
- Radius: r_max = 1.1209 R/(R/R_B): 5.20 (HIT), 5.31 (jet). OK.
- Ghira 2022 Table I p2 (crop 0.08 0.05 0.95 0.50) repeats the Da Silva values without comment (FHIT [5] 111: 4.6, 0.99, 0.68, 9.0, 28.8; PJ [5] 120: 4.6, 0.97, 0.76, 7.15, 28.3), so the conflict is in the source, not in our reading. Ghira's own rows ARE consistent (6.01/1.25 = 4.81 = (90/sqrt 15)^0.5).
- The same Table I lists the mixing layer of Tanahashi et al. 2001 ([12]) at Re_lambda = 80-100 with R/eta 4.5 and U/u' 0.50: an independent confirmation that Tanahashi 2001 is at Re_lambda 80-100, not 200.

## Mouri and Hori 2009 (Fluid Dyn. Res. 41, 021402; preprint) -- OK
- Table 2 p8 (crop 0.08 0.08 0.95 0.62): all eleven rows match sourcedata (dx0/eta, R0/eta, V0/uK, V0/<v2>^0.5, Re0, Re0/Re_lambda^0.5): B1 6.30 8.45 2.43 0.263 20.5 1.13 ... D5 6.66 8.81 3.18 0.143 28.0 0.637.
- Table 1 p3 (crop 0.08 0.08 0.95 0.60): eta [cm], u_K [m/s], Re_lambda: B1 0.0539 0.0262 332; B2 0.0335 0.0423 488; B3 0.0198 0.0716 716; B4 0.0152 0.0934 945; B5 0.0120 0.118 1080; B6 0.0104 0.137 1304; D1 0.0288 0.0489 719; D2 0.0177 0.0798 1098; D3 0.0133 0.107 1416; D4 0.0111 0.128 1693; D5 0.00955 0.149 1934. nu = eta u_K and eps = u_K^3/eta follow from this table alone (B1: nu = 1.412e-5 m2/s, eps = 0.0334 W/kg; sourcedata 0.141 cm2/s and 0.0332: match).
- Text p8 under Table 2: 'While the R0 value is greater than the true mean radius, the V0 value is less than the true mean circulation velocity, because of the contribution from vortex tubes with |y0| >> R0 or theta0 >> 0. The R0 and V0 values are still proportional to the true mean values.' The paper gives NO factor: our radius / 1.75 and swirl x 3 are OUR corrections (chord model), an assumption.
- p1 abstract: all vortex tubes; 'the radius scales with the Kolmogorov length and the circulation velocity scales with the Kolmogorov velocity, in contrast to the case of intense vortex tubes alone where the circulation velocity scales with the rms velocity fluctuation'.

## Mouri 2007 (Phys. Fluids 19, 055101) -- OK (excluded from the fits)
- Table II p6 (crop 0.03 0.03 0.97 0.45), columns 1-5 duct (D1-D5), 6-11 boundary layer (B1-B6):
  0.1%: R0/eta 5.21 5.64 5.47 5.87 6.20 5.18 5.24 5.56 5.97 5.66 6.15; V0/uK 8.67 10.0 11.3 12.8 14.0 7.60 8.37 9.53 10.6 11.7 12.8; Re0 45.2 56.4 61.8 75.1 86.8 39.4 43.9 53.0 63.3 66.2 78.7; V0/<v2>^0.5 0.637 0.595 0.593 0.610 0.629 0.822 0.745 0.701 0.677 0.700 0.700.
  1%: R0/eta 6.50 6.61 6.92 6.76 7.03 6.53 6.44 6.92 7.38 7.14 7.19; V0/uK 6.11 6.83 7.53 8.41 9.17 5.61 5.98 6.65 7.28 7.83 8.53; Re0 39.7 45.2 52.1 56.9 64.5 36.6 38.5 46.0 53.7 55.9 61.3.
- The table on the page is clean (the earlier note 'scrambled text layer' was about the extraction). Fig. 3 p5 shows the 0.1% and 1% ranges on the pdf of the velocity increment (crop p5 0.03 0.03 0.5 0.62).
- R0 is the radius of maximum circulation velocity (Mouri 2003 p2: 'the velocity is maximal at r = r0 = 2.24 (nu/a)^0.5'), so r_max = R0: no conversion.

## Mouri 2004 (Phys. Rev. E 70, 066305) -- OK (excluded from the fits)
- Table I p3 (crop 0.03 0.03 0.97 0.62): nu 0.144 0.145 0.145 0.147 0.150 0.149 cm2/s; eps 0.0316 0.254 2.03 5.65 14.6 26.2; Re_lambda 295 430 655 861 1054 1258; (text layer, same table) R0/eta 6.08 6.04 6.28 7.14 6.98 7.37; V0/<v2>^0.5 0.600 0.526 0.485 0.476 0.469 0.464; V0/uK 5.23 5.55 6.31 7.10 7.73 8.37; Re0 32 34 40 51 54 62. Match.

## Mouri 2003 (grid turbulence) -- OK (range only, excluded)
- p4 text: 'r0 = (6-7) eta, regardless of the Reynolds number'. p2: r0 = 2.24 (nu/a)^0.5 is the radius of maximum velocity. Used as 6.5, a range.

## Belin 1996 (J. Phys. II France 6, 573) -- OK (range only; chord distribution work applies)
- p6 (crop 0.05 0.03 0.97 0.60): Eq. (6) omega(r) = omega_0 exp(-r^2/(2 R^2)): R is the Gaussian standard deviation, so the 1/e radius is sqrt(2) R and r_max = 1.1209 sqrt(2) R = 1.585 R.
- p9 text: 'experimental estimate for the mean worm size: we find R = 3.5 eta (to be compared, in the same units, to 2.8 eta obtained numerically)'. Fig. 5 p8: size distributions for R_lambda 151-718, rescaled by eta. Used: 3.5 x 1.585 = 5.55, a range (151-718), comparison only.
- USER NOTE: the chord-length distribution work on Belin Fig. 5 and Mouri (chord_model.py, digitise_belin.py, fit_chord.py, fit_threshold.py, fit_smoothing.py) must be in the corrections tab.

## Kida 2002 (IUTAM, low-pressure vortex) -- OK, and NEW budget evidence
- p7 (crop 0.03 0.03 0.97 0.97; the tables are images): Table 1: N^3 256^3 / 512^3; nu 2.50e-3 / 6.25e-4; R_lambda 83 / 170; eps 0.13 / 0.12; l_K 0.019 / 0.007; kmax/kK 1.7.
  Table 2 (core statistics): D/l_K 10.4 / 10.8; Gamma/nu 110 / 123; u_theta/u_K 3.1 / 3.3; u_theta/u_rms 0.66 / 0.51; V_core/V 0.35 / 0.31; Q_core/Q 0.60 / 0.59; eps_core/eps 0.31 / 0.31. Match.
- Text p7: 'D is the core diameter, Gamma the circulation, u_theta the mean azimuthal velocity at the core boundary'; core boundary = inflection surface of the pressure (p2). 'The enstrophy inside the vortex cores is about 60% of the total, and the energy dissipation is about 30% of the total.'
- ASSUMPTION: the swirl at the core boundary is converted to the peak with a factor 1.175 (boundary at D/2 against r_max of a Burgers profile); r_max = D/2.
- NEW: eps_core/eps = 0.31 and V_core/V = 0.35, 0.31 are direct checks of the model's vortex share of the dissipation and of its volume fraction.

## Pirozzoli 2009 (Theor. Comput. Fluid Dyn.) -- OK
- Table 1 p5 (text layer clean): DNS Re_lambda 250: r0/eta 5.12; experiments (Mouri 2007, 0.1%): 332 5.18, 448(488) 5.24, 716 5.56, 945 5.97, 1080 5.66. r0 is the radius of maximum velocity. p2: 512^3 forced isotropic DNS at Re_lambda = 250.
## Pirozzoli 2012 (Physica D 241, 202) -- see pdftabs (Fig. 2 digitised; Table 1 p2; caption says case D, symbols are those of case E).

## Ishihara 2011 / 2013 -- OK (order of magnitude only)
- Ishihara 2011 p2: DNS at R_lambda = 1131: 'thin shear layers consisting of a cluster of strong vortex tubes with typical diameter of order 10 eta'. Used as r_max = 5, comparison only.

## Sassa and Makita 2005 (ETMM6) -- OK, and Fig. 8 has usable values
- p1 abstract: turbulence fields R_lambda 19 to 2391, conditional sampling on a steep change of the transverse component; 'diameter of the elementary vortex about 10 times the Kolmogorov scale regardless of R_lambda'; 'maximum azimuthal velocity normalized by the Kolmogorov velocity increased in proportion to R_lambda^0.28' (p7: 'our power index, 0.28, is about twice as large as' that of Kida et al.).
- Fig. 8 p8 (crop 0.05 0.03 0.97 0.97): (a) d/eta about 10 for all; (b) w_max/u_k from about 2.1 at R_lambda 19 to about 6.5 at 2391 with the regression line; (c) w_max/w'; (d) Gamma/nu about 90 at 19 to about 300 at 2391.
- READ BY EYE from Fig. 8(b) (present data only, +-15 %): LSG R 19: 2.1 and 2.8; LSE 190: 4.0, 300: 4.2; ST2 586: 3.6; ST1 820: 2.1; ATM 2391: 6.5. Regression of the paper: exponent 0.28.
- This is an independent whole-range trend for the swirl: exponent 0.28 against the 1/3 of model D6.

## Das 2006 / Wang 2007 / Miyauchi 2006 (the 'Wall' rows) -- text statements
- Das 2006 p1 abstract: 'diameter about 10 eta - 12 eta and average maximum azimuthal velocity about 0.5 - 0.6 u_rms'. p9: the pdf of the diameter peaks at about 10-12 eta; near the wall at about 12 eta. Used: 5.5.
- Wang 2007 p1 abstract: spatially developing mixing layer; 'the most expected value of maximum azimuthal velocity is 2.0 u_k and decreases to 1.2 u_k, an asymptotic value in the fully-developed state'; diameter 8 eta. Used: r 4.0, swirl 1.6 (the mean of 2.0 and 1.2: ASSUMPTION; the fully developed value is 1.2).
- Miyauchi 2006: NO pdf in LIT. The values (D 10 and 8.5 eta, swirl 2.0 and 1.7 u_K) were taken from the abstract online: NOT CHECKED on a page.
- These rows have no Re_lambda and are comparison only.

## Tanahashi 2001 -- CORRECTION needed (see pdftabs)
- Fig. 7 p10: pdf peaks at D* about 9 (text p10). Fig. 1(b) p4: Re_lambda about 80 for Re_omega,0 = 500 at t = 70-130; text p5: 'the highest Re_lambda is about 100 for the case of Re_omega,0 = 900'. sourcedata has Re_lambda = 200 (assumed): WRONG, use 80.
