"""fit_source_beta.py  v01  One filter radius per dataset, fitted together with c and k.

Model: each dataset s has one filter radius beta'_s (instead of the radius reported in each row).  A row of dataset s with Re_lambda
and reported swirl U' obeys
    ln(5 U') = ln c + k ln Re_lambda - n ln(beta'_s / 5) = ln c + k ln Re_lambda + a_s ,    a_s = -n ln(beta'_s / 5).
Only the product n ln(beta'_s/5) is identifiable, so n is held at N_EXP (2); and the offsets a_s are degenerate with ln c, so one
dataset is the anchor: the DNS of Ghira et al. (2022) is taken to have beta' = 5 (a = 0), which makes c the Re_c level of that DNS.
The fit is a linear regression in (ln c, k, a_s) over the rows of the five sources (Mouri and Hori 2009 left out), rows of a source
weighted equally and sources equally.  With the fitted beta'_s each row is rescaled, Re_c = 5 U' (beta'_s/5)**n, and the curve is
Re_c = c Re_lambda**k, U_max = Re_c/5.  Variants: k free and k = 0.5.
Usage: python fit_source_beta.py      (writes source_beta.png next to this file)
"""
import math
import os
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import plot_rescaled as pr
import sourcedata as sd

N_EXP = 2.0
BETA0 = pr.BETA0
ANCHOR = "Ghira22"
FITTED = ("Ghira22", "DaSilva11", "Kida02", "Mouri04", "Mouri07")


def regress(rows, k_fixed=None):
    """Linear regression of ln(5U') on [1, ln Re (if k free), source dummies except the anchor], sources equally weighted."""
    srcs = [s for s in FITTED if s != ANCHOR]
    cnt = defaultdict(int)
    for r in rows:
        cnt[r["src"]] += 1
    y = np.array([math.log(BETA0 * r["Ur"]) for r in rows])
    lr = np.array([math.log(r["Re"]) for r in rows])
    cols = [np.ones_like(y)]
    if k_fixed is None:
        cols.append(lr)
    else:
        y = y - k_fixed * lr
    for s in srcs:
        cols.append(np.array([1.0 if r["src"] == s else 0.0 for r in rows]))
    A = np.vstack(cols).T
    w = np.array([1.0 / cnt[r["src"]] for r in rows])
    w *= len(w) / w.sum()
    cov0 = np.linalg.inv(A.T @ (w[:, None] * A))
    b = cov0 @ A.T @ (w * y)
    res = y - A @ b
    cov = cov0 * float(np.sum(w * res**2)) / (len(y) - A.shape[1])
    err = np.sqrt(np.diag(cov))
    j = 1
    if k_fixed is None:
        k, ek = b[1], err[1]
        j = 2
    else:
        k, ek = k_fixed, 0.0
    a = {ANCHOR: (0.0, 0.0)}
    for i, s in enumerate(srcs):
        a[s] = (b[j + i], err[j + i])
    return math.exp(b[0]), err[0], k, ek, a, math.sqrt(float(np.mean(res**2))), res


def beta_of(a, ea):
    """beta'_s = 5 exp(-a/n) and its error."""
    return BETA0 * math.exp(-a / N_EXP), BETA0 * math.exp(-a / N_EXP) * ea / N_EXP


def main():
    rows = [r for r in pr.rescaled(0.0) if r["src"] in FITTED]
    reported = {s: sum(r["beta"] for r in rows if r["src"] == s) / sum(1 for r in rows if r["src"] == s) for s in FITTED}
    out = {}
    for label, kf in (("k free", None), ("k = 0.5", 0.5)):
        c, ec, k, ek, a, rms, res = regress(rows, kf)
        out[label] = (c, k, a)
        print("\n%s: c = %.3f (+-%.0f%%)  k = %.3f%s   rms residual %.1f%%   (N = %d rows, n = %.0f)" % (label, c, 100 * ec, k, " +- %.3f" % ek if kf is None else " (fixed)", 100 * rms, len(rows), N_EXP))
        print("   kappa = U_max/u' = c 15^0.25 / 5 = %.3f" % (c * 15 ** 0.25 / BETA0))
        for s in FITTED:
            bs, ebs = beta_of(*a[s])
            print("   %-22s beta' fitted %.2f +- %.2f   (mean reported %.2f)%s" % (pr.SHORT[s], bs, ebs, reported[s], "   anchor" if s == ANCHOR else ""))
    c, k, a = out["k free"]
    bsrc = {s: beta_of(*a[s])[0] for s in FITTED}
    resc = [dict(r, Rec=BETA0 * r["Ur"] * (bsrc[r["src"]] / BETA0) ** N_EXP, U=r["Ur"] * (bsrc[r["src"]] / BETA0) ** N_EXP) for r in rows]
    style = {src: (pr.COLOURS[(2 * i) % 20], pr.MARKERS[i % len(pr.MARKERS)]) for i, src in enumerate(FITTED)}
    res_x = [30 * (2200 / 30) ** (i / 80) for i in range(81)]
    fig, axes = plt.subplots(2, 3, figsize=(17, 9))
    panels = [("U", r"$U_{max}/U_\eta$ (rescaled with fitted $\beta'_s$)"), ("Rec", r"$Re_c$"), ("dev", "data / curve - 1 (%)"),
              ("beta", r"filter radius $\beta'$: fitted per dataset (large) and reported per row (small)"), ("Vf", r"$V_f$ (%, derived)"), ("d", r"$d/\eta$ (derived)")]
    for ax, (key, label) in zip(axes.ravel(), panels):
        if key == "beta":
            for i, s in enumerate(FITTED):
                col, mk = style[s]
                ax.scatter([r["Re"] for r in rows if r["src"] == s], [r["beta"] for r in rows if r["src"] == s], marker=mk, s=14, c=[col], alpha=0.5)
                ax.axhline(bsrc[s], c=col, lw=1.5)
            ax.axhline(BETA0, c="k", ls=":", lw=1)
            ax.set_xscale("log")
            ax.set_xlabel(r"$Re_\lambda$")
            ax.set_ylabel(r"$r_{max}/\eta$")
            ax.set_title(label, fontsize=9)
            ax.grid(alpha=0.25, which="both")
            continue
        if key == "dev":
            ax.axhline(0, c="k", lw=1)
            for s in FITTED:
                col, mk = style[s]
                pts = [(r["Re"], 100 * (r["Rec"] / (c * r["Re"] ** k) - 1)) for r in resc if r["src"] == s]
                ax.scatter(*zip(*pts), marker=mk, s=34, c=[col], alpha=0.9)
        else:
            ax.plot(res_x, [pr.model(Re, c, k)[key] for Re in res_x], c="k", lw=1.8)
            if key in ("U", "Rec"):
                for s in FITTED:
                    col, mk = style[s]
                    pts = [(r["Re"], r[key]) for r in resc if r["src"] == s]
                    ax.scatter(*zip(*pts), marker=mk, s=34, c=[col], alpha=0.9)
        ax.set_xscale("log")
        if key in ("Rec", "Vf"):
            ax.set_yscale("log")
        ax.set_xlabel(r"$Re_\lambda$")
        ax.set_title(label, fontsize=10)
        ax.grid(alpha=0.25, which="both")
    axes[1][1].axhspan(20, 35, color="0.8", alpha=0.5)
    axes[1][1].axhline(1.0, c="0.4", ls=":", lw=1)
    axes[1][1].set_ylim(0.3, 100)
    handles = [Line2D([], [], c="k", lw=1.8, label="curve: Re_c = %.2f Re_l^%.3f" % (c, k))]
    for s in FITTED:
        col, mk = style[s]
        handles.append(Line2D([], [], marker=mk, ls="", mfc=col, mec=col, ms=7, label="%s, beta'=%.2f" % (pr.SHORT[s], bsrc[s])))
    fig.suptitle("One fitted filter radius per dataset (n = 2, Ghira anchored at 5), with c and k; Mouri and Hori (2009) not included")
    fig.tight_layout(rect=(0, 0, 0.80, 0.96))
    fig.legend(handles=handles, loc="center right", fontsize=9, title="Reference", frameon=True)
    fig.savefig(os.path.join(HERE, "source_beta.png"), dpi=110)


if __name__ == "__main__":
    main()
