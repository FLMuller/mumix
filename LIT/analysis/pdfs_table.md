# Digitised tube-size and swirl pdfs: statistics, two-lognormal fits, grids, detection

Radius = r_max/η = D/(2η) (Pirozzoli: r0/η). Fit: a1·LN(median1, s1) + (1−a1)·LN(median2, s2), each curve scaled to unit area. rms = rms misfit / peak.

## Radius r_max/η

| Source | mode | median | mean | q10 | q90 | a1 | median1 | s1 | median2 | s2 | rms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Tanahashi 2001 (mixing layer) | 4.82 | 5.86 | 8.03 | 3.78 | 14.9 | 0.71 | 5.23 | 0.29 | 11.27 | 0.61 | 0.019 |
| Tanahashi 2004 (channel Re_τ 800) | 4.31 | 5.86 | 8.15 | 3.54 | 17.3 | 0.64 | 4.95 | 0.35 | 16.76 | 0.70 | 0.045 |
| Das 2006 (channel Re_τ 180, open symbols) | 6.12 | 8.45 | 10.2 | 4.18 | 20.0 | 0.08 | 6.17 | 0.23 | 8.74 | 0.69 | 0.012 |
| Pirozzoli 2012 (isotropic DNS) | 4.23 | 5.29 | 7.21 | 2.96 | 14.4 | 0.53 | 4.30 | 0.34 | 8.54 | 0.69 | 0.026 |

## Swirl

| Source | unit | mode | median | mean | q10 | q90 | a1 | median1 | s1 | median2 | s2 | rms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Tanahashi 2004 | v/u_K | 1.23 | 2.34 | 2.62 | 0.90 | 4.80 | 0.69 | 1.93 | 0.73 | 2.95 | 0.40 | 0.045 |
| Pirozzoli 2012 | v/u_K | 1.40 | 2.10 | 2.47 | 0.83 | 4.77 | 0.64 | 1.54 | 0.66 | 3.20 | 0.48 | 0.030 |
| Tanahashi 2001 | v/u_rms | 0.48 | 0.75 | 0.82 | 0.33 | 1.40 | 0.42 | 0.50 | 0.62 | 0.90 | 0.41 | 0.038 |
| Das 2006 | v/u_rms | 0.37 | 0.61 | 0.69 | 0.23 | 1.31 | 0.21 | 0.29 | 0.86 | 0.66 | 0.60 | 0.026 |

## Grid and detection (one block per source: a row per grid, the detection method once)

| Source | Grid (Nx x Ny x Nz) | Re | Dx+ | Dz+ | resolution in eta | Detection (all grids of the source) |
|---|---|---|---|---|---|---|
| Tanahashi 2001 (mixing layer) | 216x325x144 | Re_w0 = 500 | - | - | not given | Eduction without threshold: local flow pattern from the second invariant Q (Tanahashi et al. 1997); D = 2 x distance to the maximum azimuthal velocity |
| | 288x433x192 | Re_w0 = 700 | - | - | not given | |
| | 324x487x216 | Re_w0 = 900 | - | - | not given | |
| Tanahashi 2004 (channel) | 192x193x160 (4 pi d x 2d x 2 pi d) | Re_tau = 180 | 11.78 | 7.07 | not given | Same eduction without threshold (Tanahashi et al. 1999) |
| | 256x385x192 (2 pi d x 2d x pi d) | Re_tau = 400 | 9.82 | 6.54 | not given | |
| | 512x769x384 (2 pi d x 2d x pi d) | Re_tau = 800 | 9.82 | 6.54 | not given | |
| Das 2006 (channel) | 128x129x128 | Re_tau = 180 (also 100) | 17.7 (computed) | 8.8 (computed) | not given | Tanahashi local flow pattern; eta = (nu^3/eps)^(1/4) |
| | 192x193x160 | Re_tau = 180 | - | - | not given | |
| Pirozzoli 2012 (isotropic) | 256^3 | Re_lambda = 38.3 | - | - | kmax eta = 8.55 | Candidate centres at pressure minima in coordinate planes; r0 = radius of maximum velocity; arbitrary core shapes |
| | 256^3 | Re_lambda = 71.3 | - | - | kmax eta = 3.81 | |
| | 256^3 | Re_lambda = 99.9 | - | - | kmax eta = 2.16 | |
| | 512^3 | Re_lambda = 98.6 (D: the curve) | - | - | kmax eta = 4.49 | |
| | 512^3 | Re_lambda = 251.4 | - | - | kmax eta = 1.31 | |

The 'kmax eta' row of Pirozzoli's Table 1 lost its label in the text extraction; I read it as kmax*eta. The curve combines his case D circles with the Tanahashi et al. (2008) line at Re_lambda = 97.
