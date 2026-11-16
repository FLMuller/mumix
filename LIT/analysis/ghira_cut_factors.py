"""ghira_cut_factors.py  v01  What the Ghira criterion (the strongest vorticity, 1 % of the volume) does to the radius and the swirl of the tubes, worked out on the all-tube population of Pirozzoli (2012), and the factors that bring Ghira's values back to the population.
Population  Pirozzoli (2012) Fig. 2: the pdf of the core radius r0/eta (p_r) and of the maximum induced velocity v0/u_K (p_U) of ALL the vortex cores found (no lower threshold on the vorticity), the digitised curves of dns_pdfs_collate scaled to unit area.  r and U are taken as independent (the joint pdf is not given: assumption).
Tube        a Burgers vortex with r_max = r0 and U_max = v0: the vorticity on the axis is w0 = U_max / (0.4513 R) with R = r_max / 1.585, i.e. w0 = 3.512 U_max / r_max in units of 1/tau_eta; in homogeneous isotropic turbulence epsilon = nu <w^2>, so the rms vorticity is exactly 1/tau_eta
            and w0 / w_rms = 3.512 U/r (r in eta, U in u_K).
Cut         Ghira et al. keep the points above the vorticity w_ivs that holds 1 % of the volume; their Table III gives the mean axis vorticity of the structures, w_ivs/w_rms = (Table III column) x Re_lambda^(1/2) = 3.89 (Re 90) ... 4.79 (399).  The cut w_c is found for each Re_lambda such that the mean axis vorticity of the tubes above it, E[w0 | w0 > w_c], equals that number.
Result      for the tubes above the cut: the mean radius E[r | sel] and swirl E[U | sel] against the whole population E[r], E[U] (count-weighted, as Ghira's mean over the structures): the factors f_R = E[r] / E[r | sel], f_U = E[U] / E[U | sel] that multiply Ghira's values to give the all-tube values; the number fraction selected; and the total tube volume fraction
            that the 1 % implies (volume of a tube above the cut 2 pi R^2 L ln(w0/w_c); the volume of a tube taken as pi r_max^2 L; equal lengths).  Check: the model's E[r | sel] and E[U | sel] against the R_ivs and U_ivs of Ghira's Table III (the conversion to the Burgers peak of the page is done in sourcedata).
Second route  the cut from the 1 % volume itself with the total volume fraction of the tubes phi_all as an input (cut_by_volume), and the mean axis vorticity of the kept tubes as the check against Ghira's 3.9-4.8.
Output      ghira_cut_factors.csv and the numbers printed.
Usage       python ghira_cut_factors.py
Versions    M01 m01.v01 (2026-11-15): first version (the cut from Ghira's mean axis vorticity; the second route from the volume).
"""
import math
import os

import numpy as np

import dns_pdfs_collate as dc

HERE = os.path.dirname(os.path.abspath(__file__))
W0_FACTOR = 1.585 / 0.4513                                                          # w0 = W0_FACTOR U_max / r_max  (3.512)
# Ghira et al. (2022) Table III: Re_lambda, R_ivs/eta, R_ivs/R_B, U_ivs/u_eta, w_ivs Re^-1/2 / w'
GHIRA = [(90, 4.28, 0.96, 6.01, 0.41), (148, 4.23, 0.98, 7.11, 0.35), (191, 4.10, 0.97, 7.83, 0.32), (242, 4.06, 0.98, 8.31, 0.29), (292, 3.98, 0.98, 9.37, 0.28), (314, 3.98, 0.98, 9.33, 0.27), (399, 3.90, 0.97, 10.23, 0.24)]


def population():
    """The two pdfs of Pirozzoli (2012) on a common grid, each normalised to unit area."""
    rc = [c for c in dc.radius_curves() if c["label"].startswith("Pirozzoli 2012")][0]
    uk = [c for c in dc.swirl_curves()[0] if c["label"].startswith("Pirozzoli 2012")][0]
    r = np.linspace(0.5, 50.0, 800)
    u = np.linspace(0.1, 11.0, 800)
    pr = np.interp(r, rc["x"], rc["p"], left=0.0, right=0.0)
    pu = np.interp(u, uk["x"], uk["p"], left=0.0, right=0.0)
    return r, pr / np.trapezoid(pr, r), u, pu / np.trapezoid(pu, u)


def cut(r, pr, u, pu, target):
    """The cut w_c (in w_rms) for which the mean axis vorticity of the tubes above it equals target; returns the statistics of the tubes above it."""
    dr, du = r[1] - r[0], u[1] - u[0]
    w = pu[:, None] * pr[None, :] * du * dr                                          # probability of each (U, r) cell
    w0 = W0_FACTOR * u[:, None] / r[None, :]
    lo, hi = 0.0, float(w0.max())
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        sel = w0 > mid
        m = float(np.sum(w0[sel] * w[sel]) / np.sum(w[sel])) if np.sum(w[sel]) > 0 else float("inf")
        lo, hi = (mid, hi) if m < target else (lo, mid)
    wc = 0.5 * (lo + hi)
    sel = w0 > wc
    ws = w[sel]
    p_sel = float(ws.sum())
    rr = np.broadcast_to(r[None, :], w0.shape)
    uu = np.broadcast_to(u[:, None], w0.shape)
    er, eu = float(np.sum(rr[sel] * ws) / p_sel), float(np.sum(uu[sel] * ws) / p_sel)
    vol_sel = float(np.sum(2 * math.pi * (rr[sel] / 1.585) ** 2 * np.log(w0[sel] / wc) * ws))     # volume above the cut per tube of the population (unit length)
    vol_all = float(np.sum(math.pi * rr ** 2 * w))                                                  # volume of all tubes (cylinders of radius r_max), unit length
    return dict(wc=wc, p_sel=p_sel, er=er, eu=eu, ew=float(np.sum(w0[sel] * ws) / p_sel), phi_all=0.01 * vol_all / vol_sel)


def cut_by_volume(r, pr, u, pu, phi_all):
    """The cut w_c for which the volume of the tubes above it (2 pi R^2 L ln(w0/w_c)) is 1 % of the flow when the tubes fill the fraction phi_all of the flow (the volume of a tube taken as pi r_max^2 L): vol_sel / vol_all = 0.01 / phi_all."""
    dr, du = r[1] - r[0], u[1] - u[0]
    w = pu[:, None] * pr[None, :] * du * dr
    w0 = W0_FACTOR * u[:, None] / r[None, :]
    rr = np.broadcast_to(r[None, :], w0.shape)
    uu = np.broadcast_to(u[:, None], w0.shape)
    vol_all = float(np.sum(math.pi * rr ** 2 * w))
    q = 0.01 / phi_all

    def ratio(wc):
        s = w0 > wc
        return float(np.sum(2 * math.pi * (rr[s] / 1.585) ** 2 * np.log(w0[s] / wc) * w[s])) / vol_all

    lo, hi = 1e-3, float(w0.max())
    for _ in range(80):
        mid = math.sqrt(lo * hi)
        lo, hi = (lo, mid) if ratio(mid) < q else (mid, hi)
    wc = math.sqrt(lo * hi)
    s = w0 > wc
    ws = w[s]
    return dict(wc=wc, p_sel=float(ws.sum()), er=float(np.sum(rr[s] * ws) / ws.sum()), eu=float(np.sum(uu[s] * ws) / ws.sum()), ew=float(np.sum(w0[s] * ws) / ws.sum()))


def main():
    r, pr, u, pu = population()
    mr, mu_ = float(np.trapezoid(r * pr, r)), float(np.trapezoid(u * pu, u))
    print("population (Pirozzoli 2012, all cores): E[r] = %.2f eta, E[U] = %.2f u_K; mean axis vorticity E[w0] = %.2f w_rms" % (mr, mu_, float(np.sum(W0_FACTOR * u[:, None] / r[None, :] * pu[:, None] * pr[None, :]) * (u[1] - u[0]) * (r[1] - r[0]))))
    rows = []
    print("Re_l  w_ivs/w'  cut w_c  tubes kept  E[r|kept]  E[U|kept]  f_R = E[r]/E[r|kept]  f_U = E[U]/E[U|kept]   | Ghira R_ivs  U_ivs  | implied total tube volume fraction")
    for re, rivs, rb, uivs, wnorm in GHIRA:
        target = wnorm * math.sqrt(re)
        c = cut(r, pr, u, pu, target)
        rows.append((re, target, c, mr / c["er"], mu_ / c["eu"], rivs, uivs))
        print("%4d  %6.2f  %7.2f  %8.3f  %9.2f  %9.2f  %14.3f  %20.3f   | %5.2f  %5.2f  | %.2f" % (re, target, c["wc"], c["p_sel"], c["er"], c["eu"], mr / c["er"], mu_ / c["eu"], rivs, uivs, c["phi_all"]))
    with open(os.path.join(HERE, "ghira_cut_factors.csv"), "w", encoding="utf-8") as f:
        f.write("Re_lambda,w_ivs_over_w_rms,cut_wc,tubes_kept,E_r_kept,E_U_kept,f_R,f_U,Ghira_R_ivs,Ghira_U_ivs,implied_total_volume_fraction\n")
        for re, t, c, fr, fu, rivs, uivs in rows:
            f.write("%d,%.3f,%.3f,%.4f,%.3f,%.3f,%.4f,%.4f,%.2f,%.2f,%.3f\n" % (re, t, c["wc"], c["p_sel"], c["er"], c["eu"], fr, fu, rivs, uivs, c["phi_all"]))
    fr, fu = [x[3] for x in rows], [x[4] for x in rows]
    print()
    print("second route: the cut from the 1 % volume with the total volume fraction of the tubes phi_all given (no use of Ghira's vorticity):")
    print("phi_all   cut w_c   tubes kept   mean axis vorticity of the kept tubes (Ghira: 3.9-4.8)   E[r|kept]  E[U|kept]   f_R     f_U")
    for phi in (0.05, 0.10, 0.20, 0.35):
        c = cut_by_volume(r, pr, u, pu, phi)
        print("%6.2f  %8.2f  %10.3f  %30.2f  %29.2f  %9.2f  %6.2f  %6.2f" % (phi, c["wc"], c["p_sel"], c["ew"], c["er"], c["eu"], mr / c["er"], mu_ / c["eu"]))
    print("f_R: %.2f - %.2f (mean %.2f);  f_U: %.2f - %.2f (mean %.2f)" % (min(fr), max(fr), np.mean(fr), min(fu), max(fu), np.mean(fu)))


if __name__ == "__main__":
    main()
