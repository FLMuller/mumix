# fittingtool

Fits closure models of the stretched-vortex tube (radius, swirl, circulation against the Taylor Reynolds number) to the data collected from
the literature, and writes the result as one HTML report. Part of the LIT folder of mumix (`vortex-energy-balance.html` is the page that
documents the data and the physics); the tool itself is self-contained and can be copied elsewhere.

## Use

    python fittingtool.py                       # fit every model, write results/fit_<date>_<time>.html, results/index.html, results/latest.json
    python fittingtool.py --exclude Mouri09     # leave a source out of the fits
    python fittingtool.py --corrections my.json # use another file of corrections
    python fittingtool.py --tolerance 1.15      # the selection tolerance on the combined score (default 1.25)
    python fittingtool.py --no-open             # do not show the report through the report server at the end of the run

Needs Python 3 with numpy, scipy and matplotlib. It reads only `data/tubes.csv` and `data/corrections.json`.

## Files

| File | What |
|:--|:--|
| `fittingtool.py` | the program: fits all models, the sensitivity variants, writes the report and the index |
| `fitdata.py` | loads the data, applies the corrections, makes the data arrays and the weights |
| `fitmodels.py` | the models (equations, parameters, start values), the fit, the scores, the selection |
| `fitreport.py` | the report (one self-contained HTML document) and the index |
| `exportdata.py` | writes `data/tubes.csv` from the source data of the literature page (`../analysis/sourcedata.py`); only needed to refresh the data |
| `data/tubes.csv` | one row per source, run and Re_lambda: reference, group (A DNS intense, B DNS whole, C experiments), tube set, method, Re_lambda, r and U as calculated from the paper |
| `data/corrections.json` | the corrections applied before fitting (radius divisor, swirl factor, with the reason) |
| `html/page.css`, `html/page.js` | the style and the script of the report (written into every report) |
| `results/` | the reports (`fit_YYYY.MM.DD_HH;MM.html`), `index.html` (a file tree of the reports), `latest.json` (parameters and scores of the last run) |

## The data and the corrections

A row of `tubes.csv` is a tube as one source reports it, converted to the Burgers vortex (appendix A of the literature page): `r_raw = r_max/eta`,
`u_raw = U_max/U_eta` (empty where the source gives no swirl). The tube Reynolds number is `Re_c = r U` and the circulation `Gamma/nu = 8.784 Re_c`
(the exact value for a Burgers vortex, `2 pi/(1 - exp(-x))`, `x = 1.2564`). `corrections.json` divides the radius and multiplies the swirl of named sources
(for example the all-tube average of a hot wire reads too large a radius and too small a swirl); a source that is not listed is used as calculated.

## The models (fitmodels.py)

| Key | Family | Equations | Parameters |
|:--|:--|:--|:--:|
| D1 | direct | r = 5, U = c Re^s | 2 |
| D2 | direct | r = b, U = c Re^s | 3 |
| D3 | direct | r = b Re^m, U = c Re^s | 4 |
| D4 | direct | r = 5, U = kappa u'/U_eta (u'/U_eta = (Re/sqrt 15)^(1/2)) | 1 |
| D5 | direct | r = b, U = kappa u'/U_eta | 2 |
| D6 | direct | r = 5, U = c Re^(1/3) (exponent fixed at the rounded value of D1) | 1 |
| D7 | direct | r = a + b ln Re, U = c Re^s (ln: natural log) | 4 |
| D8 | direct | r = a + b ln Re, U = c Re^(1/3) | 3 |
| L1 | logarithmic | r = 5, U = a + b ln Re | 2 |
| L2 | logarithmic | r = 5, G = a + b ln Re | 2 |
| L3 | logarithmic | r = r (fitted), U = a + b ln Re | 3 |
| L4 | logarithmic | r = a1 + b1 ln Re, U = a + b ln Re | 4 |
| L5 | logarithmic | r = a1 + b1 ln Re, G = a + b ln Re | 4 |
| K5 | closure | U = a + b ln Re, G = c Re^Q, r = G/(G0 U) | 4 |
| C1 | circulation | G = c Re^Q, r = 5, U = G/(G0 r) | 2 |
| C2 | circulation | G = c Re^Q, r = b | 3 |
| C3 | circulation | G = c Re^Q, r = b Re^m | 4 |
| K3 | closure | G = a Re^p, U = r^q, G = G0 r U | 3 |
| K4 | closure | G = a Re^p, U = r^q Re^s | 4 |
| T6 | two sets | common r = b Re^m, a swirl power law for each tube set | 6 (information only) |

To add a model: write its `predict(Re, params, sets)` returning `dict(r=, U=, G=)` and add a `Model(...)` in `models()`.

**Scores** are the same for every model: the weighted rms of the log residuals of r, U and G (every source counts equally within a quantity), and the
unweighted RMSE/mean in per cent. `combined = sqrt((rms_r^2 + rms_U^2)/2)` ranks the models. **Selection**: the simplest model (fewest parameters)
that is physically sensible (the dissipation budget gives a tube volume fraction between 0.01 and 0.5 for Re_lambda 100-2000) and whose combined score is within
`TOLERANCE` (1.25) of the best; models marked information-only are not candidates. The tolerance is a choice: change it with `--tolerance`.

## Reports and the report server

A report is one HTML document that needs nothing beside it (style, script and the SVG figures are inside), with the conventions of the runbench
reports in `mumix/tools` (a tab bar of `btab` buttons with `data-go`, panels of class `bpanel`, tables of class `grid`). It opens without the report
server; opened through it (`reportserver.bat FILE`) the server adds its interactivity. `results/index.html` lists the reports as a tree, newest first;
open it directly, or through the server.

## Versions

M01 m01.v02 (2026-11-11): the report is shown through the report server at the end of a run (contactRS 'load' of the file as a [doc]; --no-open skips it); models D6-D8, L1-L5, K5; the corrections file has a list of sources left out (key excluded); figures have a size slider; the page script follows the rules of the report server's script guard.
M01 m01.v01 (2026-11-11): first version.
