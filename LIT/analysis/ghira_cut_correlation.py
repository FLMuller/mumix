"""ghira_cut_correlation.py  v01  How the factors of ghira_cut_factors.py depend on the unknown joint distribution of the radius and the swirl of the tubes.
Why      Pirozzoli (2012) gives the pdf of the core radius r0 and the pdf of the maximum velocity v0 separately, not the pdf of the pair: which swirl goes with which radius is not known.  ghira_cut_factors.py takes r and U as independent.  The cut of Ghira et al. is on the axis vorticity w0 = 3.512 U/r, so the pairing matters.
Method   the two marginals of Pirozzoli (ghira_cut_factors.population) are joined by a Gaussian copula with correlation rho (rho = 0: independent; rho > 0: large tubes are fast; rho < 0: small tubes are fast): samples (r, U) with these marginals and the rank correlation of the copula.
         The cut w_c keeps the 1 % of the volume (volume of a tube above the cut 2 pi R^2 L ln(w0/w_c), R = r/1.585; volume of a tube pi r^2 L; all the tubes fill the fraction phi_all of the flow, 0.35: Kida) and the factors are f_R = E[r]/E[r | kept], f_U = E[U]/E[U | kept];
         the mean axis vorticity of the kept tubes is printed against the 3.9-4.8 of Ghira et al. (Table III) as the check of the pairing.
Output   numbers printed.
Usage    python ghira_cut_correlation.py
Versions M01 m01.v01 (2026-11-15): first version.
"""
import math

import numpy as np
from scipy.special import ndtr

import ghira_cut_factors as gcf

N = 1_000_000
PHI = 0.35


def quantile(x, p):
    """The inverse of the cumulative distribution of the pdf p on the grid x, as a function of a uniform number."""
    c = np.r_[0.0, np.cumsum(0.5 * (p[1:] + p[:-1]) * np.diff(x))]
    c /= c[-1]
    return lambda q: np.interp(q, c, x)


def kept(r, u, phi):
    w0 = gcf.W0_FACTOR * u / r
    vol_all = float(np.sum(math.pi * r ** 2))
    q = 0.01 / phi
    lo, hi = 1e-3, float(w0.max())
    for _ in range(60):
        mid = math.sqrt(lo * hi)
        s = w0 > mid
        ratio = float(np.sum(2 * math.pi * (r[s] / 1.585) ** 2 * np.log(w0[s] / mid))) / vol_all
        lo, hi = (lo, mid) if ratio < q else (mid, hi)
    wc = math.sqrt(lo * hi)
    s = w0 > wc
    return wc, float(s.mean()), float(r[s].mean()), float(u[s].mean()), float(w0[s].mean())


def main():
    r, pr, u, pu = gcf.population()
    qr, qu = quantile(r, pr), quantile(u, pu)
    rng = np.random.default_rng(1)
    z1, z2 = rng.standard_normal(N), rng.standard_normal(N)
    print("phi_all = %.2f; population mean r %.2f eta, mean U %.2f u_K" % (PHI, float(np.trapezoid(r * pr, r)), float(np.trapezoid(u * pu, u))))
    print("rho    cut w_c  tubes kept  E[r|kept]  E[U|kept]  mean axis vorticity kept   f_R    f_U    (mean of r, U of the sample)")
    for rho in (-0.9, -0.6, -0.3, 0.0, 0.3, 0.6, 0.9):
        zu = rho * z1 + math.sqrt(1 - rho * rho) * z2
        rs, us = qr(np.clip(ndtr(z1), 1e-6, 1 - 1e-6)), qu(np.clip(ndtr(zu), 1e-6, 1 - 1e-6))
        wc, pk, er, eu, ew = kept(rs, us, PHI)
        print("%+.1f  %7.2f  %10.3f  %9.2f  %9.2f  %24.2f  %6.2f  %6.2f    (%.2f, %.2f)" % (rho, wc, pk, er, eu, ew, rs.mean() / er, us.mean() / eu, rs.mean(), us.mean()))


if __name__ == "__main__":
    main()
