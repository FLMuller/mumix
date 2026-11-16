"""ghira_cut_rg.py  v01  The cut of Ghira et al. (the strongest 1 % of the volume by vorticity) on the all-tube population of Pirozzoli (2012), with the radius r and the circulation G = Gamma/nu = 8.784 r U INDEPENDENT (as in the deconvolution of Belin et al.: the pdf of r and the pdf of r U), so that the swirl is U = G / (8.784 r).
Why      the pdfs of r0 and v0 of Pirozzoli are given separately; the pairing is not.  Independent r and U (ghira_cut_factors.py) is one choice; independent r and G (this script) makes the large tubes slow and the small tubes fast, as Burgers tubes of a circulation that does not depend on the size.
Method   ln r is sampled from the pdf of r0; ln G is normal with the mean and the variance fixed so that ln U = ln G - ln r (- const) has the mean and the variance of ln v0 of Pirozzoli: var ln G = var ln U - var ln r (it must be positive), mean ln G = mean ln U + mean ln r + ln 8.784.
         Tests of the construction: the U sampled is compared with the pdf of v0 (mean, mode, quantiles); the mode of G with the 80 of the text of Pirozzoli ('the most frequent value of the total circulation', p. 5).
Cut      as ghira_cut_correlation.kept: the tubes above w_c = 3.512 U/r, the 1 % of the volume with all the tubes filling phi_all (0.35: Kida; 0.2; 0.1), f_R = E[r]/E[r|kept] (all-tube mean) and 5/E[r|kept] (the r_max = 5 eta of the model), f_U = E[U]/E[U|kept]; the mean axis vorticity of the kept tubes against the 3.9-4.8 of Ghira et al. (Table III).
Output   numbers printed.
Usage    python ghira_cut_rg.py
Versions M01 m01.v01 (2026-11-15): first version.
"""
import math

import numpy as np

import ghira_cut_correlation as gcc
import ghira_cut_factors as gcf

N = 1_000_000


def main():
    r, pr, u, pu = gcf.population()
    qr, qu = gcc.quantile(r, pr), gcc.quantile(u, pu)
    rng = np.random.default_rng(5)
    lr_all = np.log(qr(rng.uniform(1e-6, 1 - 1e-6, N)))
    lu_target = np.log(qu(rng.uniform(1e-6, 1 - 1e-6, N)))
    m_r, v_r, m_u, v_u = lr_all.mean(), lr_all.var(), lu_target.mean(), lu_target.var()
    print("ln r: mean %.3f var %.3f (sd %.2f);  ln v0: mean %.3f var %.3f (sd %.2f);  var ln G = var ln U - var ln r = %.3f (sd %.2f)" % (m_r, v_r, math.sqrt(v_r), m_u, v_u, math.sqrt(v_u), v_u - v_r, math.sqrt(max(v_u - v_r, 0))))
    if v_u <= v_r:
        print("var ln U <= var ln r: independent r and G is impossible for these marginals")
        return
    lg = m_u + m_r + math.sqrt(v_u - v_r) * rng.standard_normal(N)            # ln (r U), independent of r
    rs = np.exp(lr_all)
    us = np.exp(lg) / rs
    G = 8.784 * np.exp(lg)
    h, e = np.histogram(G, bins=np.linspace(0, 400, 161), density=True)
    c = 0.5 * (e[1:] + e[:-1])
    hs = np.convolve(h, np.ones(5) / 5, mode="same")
    q = [0.1, 0.5, 0.9]
    print("test of the construction: U sampled: mean %.2f (v0 pdf %.2f), quantiles 10/50/90 %s against v0 pdf %s" % (us.mean(), float(np.trapezoid(u * pu, u)), np.round(np.quantile(us, q), 2), np.round([float(qu(x)) for x in q], 2)))
    print("                          mode of G %.0f (Pirozzoli: about 80), median %.0f, mean %.0f;  correlation of ln r and ln U: %.2f (= -sd r / sd U = %.2f)" % (c[np.argmax(hs)], np.median(G), G.mean(), np.corrcoef(np.log(rs), np.log(us))[0, 1], -math.sqrt(v_r / v_u)))
    print("phi_all  cut w_c  kept   E[r|kept]  E[U|kept]  mean axis vorticity (Ghira 3.9-4.8)   f_R (all-tube mean 7.2)   f_R (to 5 eta)   f_U")
    for phi in (0.10, 0.20, 0.35):
        wc, pk, er, eu, ew = gcc.kept(rs, us, phi)
        print("%6.2f  %7.2f  %5.3f  %9.2f  %9.2f  %28.2f  %24.2f  %14.2f  %6.2f" % (phi, wc, pk, er, eu, ew, rs.mean() / er, 5.0 / er, us.mean() / eu))


if __name__ == "__main__":
    main()
