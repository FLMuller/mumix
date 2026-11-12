# Notes for the update of the page (not yet applied)

Prepared 2026-11-11 while the fits were run. The page `vortex-energy-balance.html` is unchanged; the update waits for the fitting results to be seen.

## Plan of the page (as asked)

1. **First section:** a concise summary of the literature, referring to the section 7 data table and the appendix; the plot of r_max/eta and U_max/U_eta against Re_lambda
   (`fittingtool/results`, tab "R and U"); the discrepancies met (the chord length of hot-wire radii; the extreme swirl values: Ghira 2022 high, Mouri and Hori 2009 low,
   Belin's 1/(2 sin alpha)); ends with the aim: a subgrid closure model built on physical and numerical experiments.
2. **Section 2 (theory):** the Burgers vortex and vortex stretching; Moffatt, Kida and Ohkitani (1994) on stretched vortices ("the sinews of turbulence"); then the DNS work.
3. **Section 8:** the fit functions tried, as equations, one per fit (the models of `fittingtool/fitmodels.py`: D1-D6, C1-C3, K3, K4, T6, legacy n).
4. **Section 9:** the selected model only.
5. The reference list updated (new sources: Belin 1996, Mouri 2003/2004/2007/2009, Aligolzadeh 2023, Lawson and Dawson 2014, Kang et al. 2006, Nomura and Post 1998, ...).

## Moffatt's references (checked)

Moffatt, Kida and Ohkitani (1994), J. Fluid Mech. 259, 241-264, "Stretched vortices - the sinews of turbulence; large-Reynolds-number asymptotics",
does **not** cite Richardson (searched the text and the reference list). The nearest names are Rhines and Young (1982, homogenisation of potential vorticity) and
Robinson and Saffman (1984). If the cascade picture ("big whorls have little whorls") is meant, that is L. F. Richardson, *Weather Prediction by Numerical Process*
(Cambridge University Press, 1922): it is not in Moffatt's list and not in the LIT folder; it would have to be added from outside.

References of Moffatt et al. (1994) that belong in the theory section (not all are in the LIT folder): Burgers (1948) [in LIT, scanned, no text layer]; Townsend (1951), On the fine-scale
structure of turbulence, Proc. R. Soc. A 208, 534; Tennekes (1968), Simple model for the small-scale structure of turbulence, Phys. Fluids 11, 669; Lundgren (1982), Strained spiral vortex
model for turbulent fine structure, Phys. Fluids 25, 2193; Robinson and Saffman (1984), Stability and structure of stretched vortices, Stud. Appl. Math. 70, 163;
Neu (1984), The dynamics of stretched vortices, J. Fluid Mech. 143, 253; Kida and Ohkitani (1992), Phys. Fluids A 4, 1018; Jim&eacute;nez et al. (1993) [in LIT]; Saffman (1992), Vortex Dynamics (CUP);
Batchelor (1953), Homogeneous Turbulence (CUP); She, Jackson and Orszag (1990), Nature 344, 226; Vincent and Meneguzzi (1991) [in LIT]; Douady, Couder and Brachet (1991), PRL 67, 983.

## The fits (fittingtool/results/fit_2026.11.11_13;57.59.html)

Data with the corrections of fittingtool/data/corrections.json: Mouri and Hori (2009) radius / 1.17 and swirl x 3; Ghira et al. (2022) swirl x 0.6.
Selected: D6, r_max/eta = 5, U_max/U_eta = c Re_lambda^(1/3) (the fit D1 gives 0.798 Re^0.336). See the report for the scores, the sensitivity and the budget quantities.
Page items to change when the update is made: the factor 1.7 in the text and the table of section 7 and in appendix A0c becomes 1.17 (sourcedata.CORR, rmax = 1/1.17 and its text).

## Decisions on the swirl corrections (2026-11-11, after the fits with the corrected data)

- **Ghira et al. (2022) swirl x 0.6** and **Mouri and Hori (2009) swirl x 3** (the data would also allow 2.5) are the base case ("case A"); the fit D1 passes through Ghira, Da Silva, Kida and Mouri 2009 within 3% (combined 8.5%).
- The alternative "case B" (Mouri 2009 x 5, Ghira as calculated) scores 17-22% for every law tried (power laws D1/C1, u' scaling D4, straight in ln Re L1-L5, K5): the misfit is the disagreement between sources at the same Re_lambda (Ghira 6.1 against Da Silva 3.7-4.3 and Kida 3.7-3.9 at Re_lambda 83-120), not the form of the equation. Figure: analysis/compare_cases.png.
- The Mouri et al. (2007) and (2004) rows are left out of the fits (grey crosses in the figures): they are the tails (0.1% and 1% thresholds) of the experiments of Mouri and Hori (2009). Their difference from the all-tube values is most likely mostly the chord distribution (a high threshold keeps near-central, near-normal crossings), although Mouri and Hori (2009, section 6) attribute it to a difference in true tube strength; the data cannot separate the two. If it is chord only, the 0.1% row is a lower bound of the true swirl: factor 3.1 (Re_lambda 332) to 4.4 (1934) on the 2009 values, so x 3 is at the lower end and x 2.5 below it. The chord model on their pairs (analysis/fit_threshold.py) gives a true tube that depends on the tilt limit and on the selection variable (peak or velocity increment), so it is not used as a calibration (analysis/fit_smoothing.py: the wire length does not settle it either).
- The radius divisor of Mouri and Hori (2009) is **1.75** (decided 2026-11-11): 8.8 / 4.97, the chord-model radius ratio of an all-tube average; the page (v46) still has 1.7. The selected model does not depend on it (D6 for 1.17, 1.7, 1.75, 1.95).

## Done 2026-11-11 (page v47, not yet published as an Artifact)

Sections 1, 2, 10, 11 and the references were written (analysis/build_intro_sections.py and build_fit_sections.py); the old sections moved down by two (the page now has
1 literature, 2 theory, 3-8 derivation, 9 data, 10 fits tried, 11 selected model). The numbers asked for as sections 8 and 9 are 10 and 11 because of the two new sections.
Points to check: the table of section 1 and its figure; the theory section (its statements about Townsend, Tennekes, Lundgren, Robinson and Saffman, Neu were written from the
Moffatt et al. (1994) reference list, not from the papers; Richardson 1922 and Kolmogorov 1941 from memory); the reasons of the corrections in A0c.
