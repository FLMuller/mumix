"""ghira_cut_families.py  v01  Which tubes of the all-tube population of Pirozzoli (2012) does the cut of Ghira et al. (the strongest 1 % of the volume by vorticity) keep: the narrow family or the broad family of his radius pdf?
Population  r: the two-lognormal fit of his radius pdf (dns_pdfs_params.csv: a1 of the narrow family with median m1 and ln-width sigma1, the broad family m2, sigma2), each tube labelled with its family;  G = 8.784 r U independent of r (ghira_cut_rg.py), ln G normal with var ln G = var ln U - var ln r, so that
            ln U has the mean and variance of the lognormal of his swirl pdf (median m, ln-width s from dns_pdfs_params.csv).
Cut         tubes above w_c = 3.512 U/r, w_c fixed by the 1 % of the volume with all the tubes filling phi_all of the flow (ghira_cut_correlation.kept; volume of a tube above the cut 2 pi R^2 L ln(w0/w_c), R = r/1.585, volume of a tube pi r^2 L).
Result      the share of the kept tubes that belongs to each family; the radius of the kept tubes (mean, median) against the narrow family (mean, median) and the whole population; the factors f_R = (a statistic of the family) / (the same statistic of the kept tubes): no radius of the model is used.
Usage       python ghira_cut_families.py
Versions    M01 m01.v01 (2026-11-15): first version.
"""
import csv
import math
import os

import numpy as np

import ghira_cut_correlation as gcc

HERE = os.path.dirname(os.path.abspath(__file__))
N = 1_000_000


def row(source, quantity):
    for r in csv.DictReader(open(os.path.join(HERE, "dns_pdfs_params.csv"), encoding="utf-8")):
        if r["source"].startswith(source) and r["quantity"].startswith(quantity):
            return r
    raise KeyError((source, quantity))


def population():
    """The tubes of the two-lognormal radius pdf of Pirozzoli with r and G independent: arrays r, U, the family flags (narrow True) and the parameters (a1, m1, s1, m2, s2, var ln r, var ln U)."""
    pr = row("Pirozzoli 2012", "radius")
    pu = row("Pirozzoli 2012", "swirl / u_K")
    a1, m1, s1, m2, s2 = float(pr["a1"]), float(pr["m1"]), float(pr["sigma1"]), float(pr["m2"]), float(pr["sigma2"])
    mu_u, s_u = math.log(float(pu["m1"])), float(pu["sigma1"])
    rng = np.random.default_rng(9)
    narrow = rng.uniform(size=N) < a1
    lr = np.where(narrow, math.log(m1) + s1 * rng.standard_normal(N), math.log(m2) + s2 * rng.standard_normal(N))
    r = np.exp(lr)
    v_r, v_u = lr.var(), s_u ** 2
    if v_u <= v_r:
        raise ValueError("var ln U <= var ln r: independent r and G is not possible with these widths")
    lg = mu_u + lr.mean() + math.sqrt(v_u - v_r) * rng.standard_normal(N)
    return r, np.exp(lg) / r, narrow, (a1, m1, s1, m2, s2, v_r, v_u)


def cut(r, u, narrow, phi):
    """The cut of Ghira et al. for the tubes filling the fraction phi of the flow: the kept fraction, the share of the kept from the narrow family, the mean radius and swirl of the kept tubes, and the factors f_R (the mean radius of the narrow family over the mean radius of the kept tubes),
    f_R_all (the mean radius of all the tubes over it) and f_U (the mean swirl of all the tubes over the mean swirl of the kept)."""
    wc, pk, er, eu, ew = gcc.kept(r, u, phi)
    sel = (3.512 * u / r) > wc
    return dict(wc=wc, kept=pk, share_narrow=float(narrow[sel].mean()), er=er, eu=eu, ew=ew, f_R=float(r[narrow].mean() / er), f_R_all=float(r.mean() / er), f_U=float(u.mean() / eu))


def main():
    r, u, narrow, (a1, m1, s1, m2, s2, v_r, v_u) = population()
    print("radius: narrow family %.0f %% of the tubes (median %.2f, ln-width %.2f), broad family (median %.2f, ln-width %.2f); ln r variance %.3f; ln U variance %.3f -> var ln G = %.3f" % (100 * a1, m1, s1, m2, s2, v_r, v_u, v_u - v_r))
    stats = lambda x: "mean %.2f, median %.2f" % (x.mean(), np.median(x))
    print("whole population: r %s;  narrow family: r %s;  broad family: r %s" % (stats(r), stats(r[narrow]), stats(r[~narrow])))
    print("phi_all   kept   share of the kept from the narrow family   r of the kept: mean   f_R(narrow mean / kept mean)   f_R(whole mean / kept mean)   f_U")
    for phi in (0.10, 0.20, 0.35):
        c = cut(r, u, narrow, phi)
        print("%5.2f  %6.3f  %24.2f  %26.2f  %22.2f  %24.2f  %10.2f" % (phi, c["kept"], c["share_narrow"], c["er"], c["f_R"], c["f_R_all"], c["f_U"]))


if __name__ == "__main__":
    main()
