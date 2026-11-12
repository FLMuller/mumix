# Vortex tube model: fitting to the literature

Scripts behind `../vortex-energy-balance.html` (sections 7 and 8 and the appendix).
Run with `C:/flmapps/python/python.exe` (numpy, scipy). Every script finds its siblings through its own
folder and writes to `../vortex-energy-balance.html`, so the folder can be moved with the page.

## Model

Burgers tube: `r_max = beta eta`, peak swirl `U_max`, total circulation `R_G = Gamma/nu = 8.78 beta U_max/U_eta`
(`8.78 = 2 pi/(1 - exp(-x))`, `x = 1.2564`). Dissipation budget: vortex share `1 - 75.8/beta^4`,
`V_f = (1 - 75.8/beta^4) beta^2 / (4.91 U^2)`, spacing `d/eta = beta sqrt(pi/V_f)`.

- Section 7 (3 parameters): `R_G = a Re_l^p`, `U_max/U_eta = beta^q`.
- Section 8 (4 parameters): `R_G = a Re_l^p`, `U_max/U_eta = beta^q Re_l^s`, so `beta^(1+q) = a Re_l^(p-s)/8.78`
  and `Re_c = R_G/8.78`.

Fit: minimise `chi2 = sum [ln(model/literature)/sigma_ref]^2`. `sigma_ref` is the rms of each source's own log
residuals (groups of three or more observations); groups with fewer take the largest of those. The fit and
`sigma_ref` are iterated together. Parameter errors come from the curvature of chi2 (Delta chi2 = 1) and are
approximate because `sigma_ref` is taken from the residuals.

## Results (N = 33 observations)

| Model | a | p | q | s | chi2/N |
|---|---|---|---|---|---|
| Section 7, 3 parameters | 88.5 +- 9.6 | 0.124 +- 0.017 | 0.873 +- 0.031 | - | 1.22 |
| Section 8, 4 parameters (5% sigma floor) | 76.8 +- 8.7 | 0.145 +- 0.017 | 0.30 +- 0.10 | 0.18 +- 0.03 | 1.05 |

`q` and `s` are strongly degenerate (correlation -0.98); a run without the floor gave q = 0.12, s = 0.23 with the
same a and p (before the Aligolzadeh row was added). The floor is needed because the Ghira et al. radius group otherwise collapses to sigma_ref = 0.4%.
Kida et al. (2002) are listed in the tables (red rows) but not used.

The last row added is the experimental radius of Aligolzadeh et al. (2023): R/eta = 5.1, R/R_B = 0.95 at Re_l = 179, so
r_max = 1.12 R/0.95 = 6.01 eta. It is the largest residual in both fits (model 20% and 22% below it); with it the 3-parameter
fit moved from a = 91.5, p = 0.119, q = 0.901 (chi2/N = 1.05, N = 32) to the values above, and a and p of the 4-parameter fit did not move.

## Run order (regenerates the page)

The 3-parameter model (`update_s7_v2.py`, Step 7 of the old section 7) was dropped from the page; the script is kept
but is no longer run. The page now has: section 7 (data: whole and intense tubes), section 8 (tube model, steps 1-6),
section 9 (4-parameter closure, fit, results and limits), the references and the appendix.

1. `sourcedata.py` - every value taken from a paper (tables, equations, conversions, nu and eps of the run, tube set,
   role), the single source for sections 7 and the appendix. Edit it to change or add a data row.
2. `build_data_sections.py` - writes section 7 (with the table of all measurements) and the appendix from `sourcedata.py`.
3. `build_sec8.py` - refits the 4-parameter model (imports `fit4_floor.py`) and writes section 9, with its limits.
4. `restructure_page.py` - one-off, guarded: removed the 3-parameter fit from the page, renamed section 7 to 8, moved the
   evidence table to the 4-parameter model values and added the new references. Safe to run again.

`make_appendix.py` is the earlier appendix generator, replaced by `build_data_sections.py`.

New data of the last extension (Mouri 2003, 2004, 2007, Da Silva 2011, Pirozzoli, Sassa, Ishihara, Das, Wang) are in
`sourcedata.py` as comparison rows (not fitted). `newrows_test.py` compares them with the models and with the
swirl-proportional-to-u' law: both models give a tube Reynolds number 2-3 times too low against the intense tubes of
Mouri et al., the u' law agrees within 30%.

## Trials and checks (not used by the page)

| Script | What it does |
|---|---|
| `fit_lfl.py` | like-for-like fit: each source's quantity is compared with the model Burgers profile evaluated the way the source defines it (Ghira circulation inside R_ivs, 1/e radii, swirl at the core boundary) |
| `diag_lfl.py` | like-for-like fits on subsets of the data (intense tubes only, Ghira only, without Ghira circulation) |
| `intense_fit.py` | like-for-like fit to the intense-tube data (Ghira, Jimenez, Tanahashi) |
| `alt_uprime.py` | swirl law `U_max = kappa u'` fitted to the intense-tube data |
| `refit_a.py` | refit under reading (a) with global search, residuals by Re_lambda |
| `fit4.py`, `fit4_floor.py` | the 4-parameter fit without and with the sigma floor |
| `iterate_sigma2.py`, `iterate_sigma3.py` | sigma_ref rules for small groups (pooled mean, highest) |
| `outliers.py`, `diffs.py`, `rmse.py` | outlier and influence analysis, differences and RMSE per measure |
| `hy_extract.py`, `kgm_extract.py` | pull page images from the scanned Hosokawa and Yamamoto and Kida PDFs (output in `extracts/`) |

## Open issues

- **Circulation of Ghira et al.** Their `Gamma_ivs = 2 pi <U_ivs> R_ivs` (Eq. 9) is the circulation inside `R_ivs`
  (about 61% of a Burgers total), and the listed value is about 0.83 of `2 pi U R` from the same table. Here the
  listed value is taken as the total (reading a). The swirl they list, `U_ivs/u_eta = 6.0-10.2`, is then 1.5-2.5 times
  the model's.
- **Two populations.** Intense tubes (Ghira, Jimenez, Tanahashi) and all tubes (Mouri and Hori, Kida) differ in radius
  and swirl; one tube does not match both.
- **Trend in the circulation.** Ghira's `Gamma` rises as `Re_l^0.28`, faster than the tube Reynolds number of Mouri and Hori allows.
- **Assumptions of mine:** Tanahashi at `Re_l = 200`; `R_ivs/R_B = 0.97` for the two Ghira (2025) radii at `Re_l = 54`;
  the factor 1.175 converting Kida's swirl at the core boundary to a Burgers peak.
- Candidate DNS papers not yet checked: Vincent and Meneveau, Ishihara et al. (review of high-Re isotropic DNS),
  Pullin and Saffman (review), Passot et al.


## Page v47 (2026-11-11): sections 1, 2, 10 and 11, the corrections of the fitting tool

The page has a new section 1 (summary of the literature, table and figure), a new section 2 (theory), and the old sections 1-7 are now 3-9
(section 9 is the data); the old sections 8 and 9 (the tube model and the 4-parameter closure) are replaced by section 10 (every fit tried, as equations)
and section 11 (the selected model). The old page is kept as `../zprev/vortex-energy-balance_v46.html`, the old scripts as `../zprev/sourcedata_v46.py` and
`../zprev/build_data_sections_v46.py`.

Order of a rebuild (each script replaces only its own blocks):
1. `sourcedata.py` - the data and the corrections (`CORR`: Mouri and Hori 2009 radius / 1.75 and swirl x 3, Ghira et al. 2022 swirl x 0.6); `reason()` says which rows
   the fitting tool fits (it reads `../fittingtool/data/tubes.csv` and `corrections.json`).
2. `../fittingtool/exportdata.py` then `build_data_sections.py` - section 9 and the appendix (A0c has the chord model and the reasons of the corrections).
3. `build_intro_sections.py` - sections 1 and 2 and the new references (merged by author).
4. `build_fit_sections.py` - runs the fitting tool and writes sections 10 and 11 (needs matplotlib; takes about a minute).
5. `restructure_v47.py` - one-off (already done): renumbering of the old sections.

Analyses behind the corrections (not run by the page): `fit_threshold.py` (what the 0.1% and 1% threshold averages of Mouri et al. say about the true tube, with the
chord model; selection by peak or by velocity increment with `--sep`), `fit_smoothing.py` (the same with the hot-wire length added; it does not settle the swirl
factor), `compare_cases.py` (the two cases of section 10: Mouri and Hori x 3 with Ghira x 0.6, and x 5 with Ghira as listed; writes `compare_cases.svg` and `.png`),
`fit_chord.py` (Belin's size distribution). Results are summarised in `../page_update_notes.md`.

Publishing: `publish_page.py` copies the page to `../results/vortex-energy-balance_YYYY.MM.DD_HH;MM.html` (a new file each time, never overwritten, like the other results)
and shows it through the report server; run it last in the rebuild order above.
