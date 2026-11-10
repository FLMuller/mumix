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

## Results (N = 32 observations)

| Model | a | p | q | s | chi2/N |
|---|---|---|---|---|---|
| Section 7, 3 parameters | 91.5 +- 10.1 | 0.119 +- 0.017 | 0.901 +- 0.030 | - | 1.05 |
| Section 8, 4 parameters (5% sigma floor) | 76.8 +- 8.7 | 0.145 +- 0.017 | 0.29 +- 0.10 | 0.18 +- 0.03 | 0.72 |

`q` and `s` are strongly degenerate (correlation -0.98); a run without the floor gives q = 0.12, s = 0.23 with the
same a and p. The floor is needed because the Ghira et al. radius group otherwise collapses to sigma_ref = 0.4%.
Kida et al. (2002) are listed in the tables (red rows) but not used.

## Run order (regenerates the page)

1. `update_s7_v2.py` - refits the 3-parameter model and rewrites Step 7 to the Limits section of the page.
2. `build_sec8.py` - refits the 4-parameter model (imports `fit4_floor.py`) and writes section 8.
3. `make_appendix.py` - writes the appendix (data rows, paper locations, interpretation). It holds the numbers
   as read from the papers; edit it to change a data value.

The observations of sections 7 and 8 are in `fit_aq.py` (Ghira 2022, Mouri and Hori, Kida, Tanahashi), `optimise2d.py`
(Jimenez 1993) and, for Ghira 2025, `update_s7_v2.py` and `fit4.py`. `iterate_sigma.py` and `fit3d.py` hold the
3-parameter model and the sigma_ref iteration.

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
