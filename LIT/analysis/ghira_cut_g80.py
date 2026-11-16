"""ghira_cut_g80.py  v01  The circulation of the tubes of Pirozzoli (2012) as the link between his radius pdf and his swirl pdf, and the size of the strongest 1 % of the volume (the cut of Ghira et al.).
Link     Pirozzoli (p. 5): Re_Gamma = Gamma_inf/nu = 80 'roughly corresponds to the most frequent value of the total circulation of the educed vortices'; with Gamma_0 = 2 pi r0 v0 = 0.715 Gamma_inf, G = Gamma_inf/nu = 8.784 r0 v0 in Kolmogorov units.  If G is a constant G0 (the tubes of one circulation),
         U = G0 / (8.784 r): the swirl pdf follows from the radius pdf, p_U(U) = p_r(G0/(8.784 U)) G0/(8.784 U^2), and the axis vorticity w0 = 3.512 U/r = 3.512 G0/(8.784 r^2) = 0.4 G0 / r^2 (in units of the rms vorticity 1/tau_eta) depends on the radius alone.
Test     the U pdf from the radius pdf with G0 = 80 (and 94, the mode of the r-G-independent construction) against the digitised swirl pdf of Pirozzoli (mean, quantiles 10/50/90).
Cut      the tubes above w_c, the volume above the cut of a tube 2 pi R^2 L ln(w0/w_c), R = r/1.585, the volume of a tube pi r^2 L, the 1 % of the volume when all the tubes fill phi_all of the flow (0.1, 0.2, 0.35): the cut in radius r_c (w0 = w_c at r = r_c), the radius and swirl of the kept tubes, the mean axis vorticity (Ghira Table III: 3.9-4.8) and the factors
         f_R = (mean radius of the narrow family 4.55, or of all the tubes) / (mean radius of the kept tubes), f_U = (mean swirl of all the tubes) / (mean swirl of the kept tubes).
Usage    python ghira_cut_g80.py
Versions M01 m01.v01 (2026-11-15): first version.
"""
import math

import numpy as np

import ghira_cut_factors as gcf

NARROW_MEAN = 4.55                                                                   # mean r of the narrow family of the two-lognormal fit of the radius pdf (dns_pdfs_params.csv)


def quantiles(x, p, qs):
    c = np.r_[0.0, np.cumsum(0.5 * (p[1:] + p[:-1]) * np.diff(x))]
    c /= c[-1]
    return [float(np.interp(q, c, x)) for q in qs]


def constant_g(r, pr, g0, phi):
    """The cut of Ghira et al. on the radius pdf pr(r) with the circulation held at G = g0 (U = g0 / (8.784 r), w0 = 3.512 U / r), the tubes filling the fraction phi of the flow: the cut w_c and the radius r_c above which a tube is not kept, the fraction of the tubes kept, the mean radius,
    the mean swirl and the mean axis vorticity of the kept tubes, and the mean swirl of all the tubes."""
    dr = r[1] - r[0]
    us = g0 / (8.784 * r)
    w0 = 3.512 * us / r
    vol_all = float(np.sum(math.pi * r ** 2 * pr) * dr)
    lo, hi = 1e-3, float(w0.max())
    for _ in range(70):
        mid = math.sqrt(lo * hi)
        s = w0 > mid
        ratio = float(np.sum(2 * math.pi * (r[s] / 1.585) ** 2 * np.log(w0[s] / mid) * pr[s]) * dr) / vol_all
        lo, hi = (lo, mid) if ratio < 0.01 / phi else (mid, hi)
    wc = math.sqrt(lo * hi)
    s = w0 > wc
    pk = float(np.sum(pr[s]) * dr)
    return dict(wc=wc, r_c=float(r[s].max()), kept=pk, er=float(np.sum(r[s] * pr[s]) * dr / pk), eu=float(np.sum(us[s] * pr[s]) * dr / pk), ew=float(np.sum(w0[s] * pr[s]) * dr / pk), mean_u=float(np.sum(us * pr) * dr), mean_r=float(np.sum(r * pr) * dr))


def main():
    r, pr, u, pu = gcf.population()
    dr = r[1] - r[0]
    mean_r = float(np.sum(r * pr) * dr)
    print("Pirozzoli: mean r %.2f; swirl pdf: mean %.2f, quantiles 10/50/90 %s" % (mean_r, float(np.trapezoid(u * pu, u)), np.round(quantiles(u, pu, (0.1, 0.5, 0.9)), 2)))
    for g0 in (80.0, 94.0):
        us = g0 / (8.784 * r)
        order = np.argsort(us)
        cu = np.cumsum(pr[order] * dr)
        qu = [float(np.interp(q, cu / cu[-1], us[order])) for q in (0.1, 0.5, 0.9)]
        mean_u = float(np.sum(us * pr) * dr)
        print()
        print("G0 = %.0f (U = %.2f / r): the swirl from the radius pdf: mean %.2f, quantiles 10/50/90 %s;  axis vorticity w0 = %.1f / r^2" % (g0, g0 / 8.784, mean_u, np.round(qu, 2), 3.512 * g0 / 8.784))
        print("  phi_all   w_c     r_c    kept   E[r|kept]  E[U|kept]  mean axis vorticity kept   f_R(narrow %.2f)  f_R(all %.2f)   f_U(%.2f)" % (NARROW_MEAN, mean_r, mean_u))
        for phi in (0.10, 0.20, 0.35):
            c = constant_g(r, pr, g0, phi)
            print("  %6.2f  %6.2f  %6.2f  %5.3f  %9.2f  %9.2f  %20.2f  %18.2f  %13.2f  %8.2f" % (phi, c["wc"], c["r_c"], c["kept"], c["er"], c["eu"], c["ew"], NARROW_MEAN / c["er"], mean_r / c["er"], mean_u / c["eu"]))


if __name__ == "__main__":
    main()
