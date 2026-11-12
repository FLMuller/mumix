"""summary_pdfs.py  v01  All the tube-size and swirl pdfs digitised from the literature, on one figure.

Sources (the csv files written by the digitising scripts): Tanahashi et al. (2001) Fig. 7, mixing layer (D*, v*_theta,m / u_rms); Tanahashi et al. (2004) Fig. 5, channel Re_tau = 800, all wall
bands (D/eta, v_theta,max / u_K); Das et al. (2006) Fig. 7, channel Re_tau = 180, the open symbols (110 < y+ < 180; D*, u*_theta,max / u_rms; the diameter tail above D* = 18 is the straight
line of fit_das2006_open.py); Pirozzoli (2012) Fig. 2, DNS test case D with the Tanahashi curve at Re_lambda = 97 (r0/eta, v0/u_K).
The diameters are converted to the radius of maximum swirl, r_max = D/2, p_r(r) = 2 p_D(2 r).  Each curve is scaled to a total area of 1 (the digitised range plus the rise below its first point and
the tail beyond its last, as check_das_area.py) and fitted with two lognormals (the figure also shows component 1 of each fit, dotted) (fit_tanahashi_lognormal.fit_mixture: free weight, median ordered, start a1 = 0.7; sigma2 >= 2 sigma1 for the sizes,
no width constraint for the swirl).  Writes pdfs_summary.png, pdfs_summary.csv (the statistics) and prints the table.   Usage: python summary_pdfs.py
"""
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import fit_tanahashi_lognormal as fl

HERE = os.path.dirname(os.path.abspath(__file__))
TAIL_FROM, TAIL_A, TAIL_K = 18.0, 0.1053, -0.0682            # the straight-line tail of the Das diameter pdf (D*)

# (label, csv, x column, p column, xmin, rise from, factor to r_max, colour)
SIZE = [("Tanahashi 2001, mixing layer", "tanahashi2001_pdfs.csv", "D_star", "pD", 4.0, 2.0, 0.5, "tab:blue"),
        ("Tanahashi 2004, channel Re_tau 800", "tanahashi2004_pdfs.csv", "D_over_eta", "pD", 4.0, 2.0, 0.5, "tab:orange"),
        ("Das 2006, channel Re_tau 180, open symbols", "das2006_open_pdfs.csv", "D_star", "pD", 3.0, 2.0, 0.5, "tab:green"),
        ("Pirozzoli 2012, DNS", "pirozzoli2012_pdfs.csv", "r0_over_eta", "pr", 1.0, 0.5, 1.0, "tab:red")]
SWIRL_UK = [("Tanahashi 2004, channel Re_tau 800", "tanahashi2004_pdfs.csv", "v_over_uk", "pv", 0.0, 0.0, "tab:orange"),
            ("Pirozzoli 2012, DNS", "pirozzoli2012_pdfs.csv", "v0_over_uk", "pv", 0.2, 0.0, "tab:red")]
SWIRL_URMS = [("Tanahashi 2001, mixing layer", "tanahashi2001_pdfs.csv", "v_star", "pv", 0.0, 0.0, "tab:blue"),
              ("Das 2006, channel Re_tau 180, open symbols", "das2006_open_pdfs.csv", "u_star", "pv", 0.0, 0.0, "tab:green")]


def load(csv, xc, pc, xmin):
    d = np.genfromtxt(os.path.join(HERE, csv), delimiter=",", names=True)
    x, p = d[xc], d[pc]
    ok = np.isfinite(x) & np.isfinite(p) & (x >= xmin)
    return x[ok], p[ok]


def normalise(x, p, rise_from, tail_line=None):
    """Total area of the digitised pdf with the rise below its first point (a linear rise from zero at rise_from) and the tail beyond the last point (exponential from the last eight points, or the given
    straight line (A, k)); returns the pdf scaled to a total area of 1 and the total."""
    area = np.trapezoid(p, x)
    left = 0.5 * p[0] * max(x[0] - rise_from, 0.0)
    slope = -np.polyfit(x[-8:], np.log(p[-8:]), 1)[0] if tail_line is None else -tail_line[1]
    right = p[-1] / slope if slope > 0 else 0.0
    total = area + left + right
    return p / total, total


def fit(x, p, size):
    fl.AREA_MATCH = False
    fl.A_FIXED = fl.S1_FIXED = fl.MU1_FIXED = None
    fl.ORDER = "median"
    fl.SRATIO = 2.0 if size else 0.0
    return fl.fit_mixture(x, p, p, p, 0.7 if size else 3.0, "lin")


def stats(x, p):
    cum = np.cumsum(np.r_[0, 0.5 * (p[1:] + p[:-1]) * np.diff(x)])
    q = lambda f: x[np.searchsorted(cum, f * cum[-1])]
    return dict(mode=x[np.argmax(p)], median=q(0.5), mean=np.trapezoid(p * x, x) / cum[-1], q10=q(0.1), q90=q(0.9))


def main():
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    rows = []
    print("radius r_max/eta = D/2 (Pirozzoli: r0/eta): mode, median, mean, 10-90%; two-lognormal fit (weight, median, s | median, s), rms of the peak")
    for label, csv, xc, pc, xmin, rise, fac, col in SIZE:
        x, p = load(csv, xc, pc, xmin)
        line = None
        if csv.startswith("das2006"):                              # digitised below TAIL_FROM, the straight line above it
            low = x < TAIL_FROM
            xt = np.arange(TAIL_FROM, 80.01, 1.0)
            x = np.r_[x[low], xt]
            p = np.r_[p[low], TAIL_A * np.exp(TAIL_K * xt)]
            line = (TAIL_A, TAIL_K)
        p, total = normalise(x, p, rise, line)
        q = fit(x, p, True)
        r, pr = x * fac, p / fac                                    # p_r(r) = p_D(D) dD/dr
        st = stats(r, pr)
        xs = np.exp(np.linspace(np.log(x.min()), np.log(x.max()), 500))
        pf = fl.mixture(xs, q) / fac
        c1 = q[0] * fl.lognormal(xs, q[1], q[2]) / fac                # component 1 (the narrow family) of the fit, with its weight
        for ax in (axes[0][0], axes[0][1]):
            ax.plot(r, pr, c=col, lw=1.3, label=label)
            ax.plot(xs * fac, pf, c=col, lw=1.0, ls="--")
            ax.plot(xs * fac, c1, c=col, lw=1.4, ls=":")
        rows.append((label, "radius", st, q, np.sqrt(np.mean((fl.mixture(x, q) - p) ** 2)) / p.max(), fac, total))
        print("  %-44s mode %.2f median %.2f mean %.2f 10-90%% %.2f-%.2f | fit %.2f %.2f %.2f | %.2f %.2f, rms %.3f; area of the digitised curve %.3f" % (
            label, st["mode"], st["median"], st["mean"], st["q10"], st["q90"], q[0], np.exp(q[1]) * fac, q[2], np.exp(q[3]) * fac, q[4], rows[-1][4], total))
    for ax, sw, title, xlab in ((axes[1][0], SWIRL_UK, "maximum swirl in units of u_K", "v_theta,max / u_K"), (axes[1][1], SWIRL_URMS, "maximum swirl in units of u_rms", "v_theta,max / u_rms")):
        for label, csv, xc, pc, xmin, rise, col in sw:
            x, p = load(csv, xc, pc, xmin)
            p, total = normalise(x, p, rise)
            q = fit(x, p, False)
            st = stats(x, p)
            xs = np.exp(np.linspace(np.log(max(x.min(), 1e-3)), np.log(x.max()), 500))
            ax.plot(x, p, c=col, lw=1.3, label=label)
            ax.plot(xs, fl.mixture(xs, q), c=col, lw=1.0, ls="--")
            ax.plot(xs, q[0] * fl.lognormal(xs, q[1], q[2]), c=col, lw=1.4, ls=":")
            rows.append((label, "swirl " + xlab, st, q, np.sqrt(np.mean((fl.mixture(x, q) - p) ** 2)) / p.max(), 1.0, total))
            print("  %-44s %s: mode %.2f median %.2f mean %.2f 10-90%% %.2f-%.2f | fit %.2f %.2f %.2f | %.2f %.2f, rms %.3f; area %.3f" % (
                label, xlab, st["mode"], st["median"], st["mean"], st["q10"], st["q90"], q[0], np.exp(q[1]), q[2], np.exp(q[3]), q[4], rows[-1][4], total))
        ax.set_yscale("log")
        ax.set_title(title, fontsize=10)
        ax.set_xlabel(xlab)
        ax.set_ylabel("pdf (log)")
        ax.set_ylim(1e-3, 4)
        ax.grid(alpha=0.25, which="both")
        ax.legend(fontsize=8)
    for ax, logy in ((axes[0][0], False), (axes[0][1], True)):
        ax.set_xlabel("r_max / eta  (= D / 2 eta)")
        ax.set_ylabel("pdf" + (" (log)" if logy else ""))
        ax.set_xlim(0, 30 if not logy else 50)
        if logy:
            ax.set_yscale("log")
            ax.set_ylim(1e-5, 0.6)
        ax.grid(alpha=0.25, which="both")
        ax.legend(fontsize=8)
    axes[0][0].set_title("radius: digitised (solid), fit (dashed), component 1 of the fit (dotted)", fontsize=10)
    axes[0][1].set_title("the same on a logarithmic axis", fontsize=10)
    fig.suptitle("Tube-size and swirl pdfs from the literature (DNS: mixing layer, channels; Pirozzoli isotropic)", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "pdfs_summary.png"), dpi=110)
    with open(os.path.join(HERE, "pdfs_summary.csv"), "w", encoding="utf-8") as f:
        f.write("source,quantity,mode,median,mean,q10,q90,fit_weight1,fit_median1,fit_s1,fit_median2,fit_s2,rms_of_peak,area_digitised\n")
        for label, quantity, st, q, rms, fac, total in rows:
            f.write("%s,%s,%.4g,%.4g,%.4g,%.4g,%.4g,%.3f,%.4g,%.3f,%.4g,%.3f,%.3f,%.3f\n" % (label, quantity, st["mode"], st["median"], st["mean"], st["q10"], st["q90"], q[0], np.exp(q[1]) * fac, q[2], np.exp(q[3]) * fac, q[4], rms, total))


if __name__ == "__main__":
    main()
