"""plot_rescaled.py  v03  Rows rescaled to a common radius r_max/eta = 5, one curve through all of them, plot against Re_lambda.

Assumption: every tube has the true radius beta0 = 5 and each dataset's filter reports a radius beta' and swirl U'.  The swirl at the
true radius follows a power law in the radius ratio,
    U = U' (beta'/beta0)**n ,       Re_c = beta0 U ,       Gamma/nu = 8.78 Re_c ,       gamma/gamma_eta = 4x/beta0**2 ,
with n = 1 the Burgers value (circulation, hence Re_c = beta'U', kept) and n = 0 the swirl kept.
One curve Re_c = c Re_lambda**k is fitted to all rows of Ghira 2022, Da Silva 2011, Kida 2002, Mouri 2004 and Mouri 2007, each source
weighted equally; Mouri and Hori 2009 (radii biased high by the authors' account) is rescaled and plotted but left out of the fit
(EXCLUDE).  The swirl, the circulation, the budget volume V_f and the spacing d/eta follow from the curve.
Panels: U_max/U_eta, Re_c, Gamma/nu, (data/curve - 1) per row, V_f and d/eta (budget, derived).
v01: peak vorticity kept.  v02: fitted exponent n, two sets.  v03: one curve, n fixed (N_EXP), one source excluded.
v04: n, c and k fitted together.  Re_c = 5 U'(beta'/5)**n = c Re_lambda**k gives
    ln(5 U') = ln c + k ln Re_lambda - n ln(beta'/5),
which is linear in (ln c, k, n): one weighted least-squares regression (sources weighted equally, EXCLUDE left out) gives all three
with their errors and correlations.  A fourth parameter, a Re_lambda-dependence of the exponent (n = n0 + n1 ln Re_lambda), is also
fitted and reported.  v05: k held at K_FIXED = 0.5 (U proportional to the rms velocity u', u'/U_eta = (Re_lambda/sqrt(15))**0.5, so Re_c = 5 U ~ Re_lambda**0.5);
    c and n are fitted: ln(5 U') - 0.5 ln Re_lambda = ln c - n ln(beta'/5).  c = Re_c at Re_lambda = 1, and with U = kappa u' it is
    c = beta0 kappa / 15**0.25, so kappa = U_max/u' = 0.394 c.
v06: option kfree: c, k and n all fitted from the reported radius and swirl of every row.
Usage: python plot_rescaled.py [n] [kfree]   (no argument: c and n fitted at k = K_FIXED; n: n also held at that value; kfree: k, c, n fitted)
"""
import html
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
import build_data_sections as bds
import sourcedata as sd

BETA0 = 5.0
K_FREE = "kfree" in sys.argv[1:]                              # True: c, k and n are all fitted
_nums = [a for a in sys.argv[1:] if a != "kfree"]
N_FIXED = float(_nums[0]) if _nums else None                  # None: n is fitted
K_FIXED = 0.5                                                  # exponent of Re_c with Re_lambda (swirl proportional to u')
X = sd.x
S = 48 * X * X
E = 0.977 * 4 * X
SET = {s["key"]: s["tubes"] for s in sd.SOURCES}
SHORT = {s["key"]: html.unescape(s["short"]) for s in sd.SOURCES}
SOURCES = ("Ghira22", "DaSilva11", "Kida02", "Mouri04", "Mouri07", "Mouri09")
EXCLUDE = ("Mouri09",)
MARKERS = ["o", "s", "^", "v", "D", "P", "X", "<", ">", "h", "*", "p", "d"]
COLOURS = plt.get_cmap("tab20").colors


def rescaled(n):
    """Rows of SOURCES with a numeric Re_lambda, radius and swirl, rescaled to beta0 with U = U' (beta'/beta0)**n."""
    out = []
    for t in bds.tube_items():
        if t["src"] in SOURCES and isinstance(t["Re"], (int, float)) and t["beta"] and t["U"]:
            U = t["U"] * (t["beta"] / BETA0) ** n
            out.append(dict(src=t["src"], Re=t["Re"], beta=t["beta"], Ur=t["U"], U=U, Rec=BETA0 * U, R=sd.G * BETA0 * U))
    return out


def fit(rows):
    """Weighted least squares of ln Re_c on ln Re_lambda, every source with total weight 1: c, k, errors of (ln c, k), rms residual."""
    cnt = defaultdict(int)
    for r in rows:
        cnt[r["src"]] += 1
    x = np.array([math.log(r["Re"]) for r in rows])
    y = np.array([math.log(r["Rec"]) for r in rows])
    w = np.array([1.0 / cnt[r["src"]] for r in rows])
    A = np.vstack([np.ones_like(x), x]).T
    cov0 = np.linalg.inv(A.T @ (w[:, None] * A))
    b = cov0 @ A.T @ (w * y)
    res = y - A @ b
    s2 = float(np.sum(w * res**2)) / max(len(cnt) - 2, 1)
    return math.exp(b[0]), b[1], np.sqrt(np.diag(cov0 * s2)), math.sqrt(float(np.mean(res**2)))


def regress(rep_rows, extra_n_slope=False):
    """Joint weighted regression ln(5 U') = ln c + k ln Re - n ln(beta'/5) [- n1 ln Re ln(beta'/5)] over the unrescaled rows.
    Every source has total weight 1 (weights normalised to a mean of 1).  Returns (names, values, errors, correlation, rms residual)."""
    cnt = defaultdict(int)
    for r in rep_rows:
        cnt[r["src"]] += 1
    y = np.array([math.log(BETA0 * r["Ur"]) for r in rep_rows])
    lr = np.array([math.log(r["Re"]) for r in rep_rows])
    lb = np.array([math.log(r["beta"] / BETA0) for r in rep_rows])
    cols = [np.ones_like(y), lr, -lb] + ([-lb * lr] if extra_n_slope else [])
    A = np.vstack(cols).T
    w = np.array([1.0 / cnt[r["src"]] for r in rep_rows])
    w *= len(w) / w.sum()
    cov0 = np.linalg.inv(A.T @ (w[:, None] * A))
    b = cov0 @ A.T @ (w * y)
    res = y - A @ b
    s2 = float(np.sum(w * res**2)) / (len(y) - A.shape[1])
    cov = cov0 * s2
    err = np.sqrt(np.diag(cov))
    names = ["ln c", "k", "n"] + (["n1"] if extra_n_slope else [])
    return names, b, err, cov / np.outer(err, err), math.sqrt(float(np.mean(res**2)))


def regress_k(rep_rows, k):
    """As regress() with the Re_lambda exponent held at k: ln(5 U') - k ln Re = ln c - n ln(beta'/5).  Returns (ln c, n), errors, correlation, rms."""
    cnt = defaultdict(int)
    for r in rep_rows:
        cnt[r["src"]] += 1
    y = np.array([math.log(BETA0 * r["Ur"]) - k * math.log(r["Re"]) for r in rep_rows])
    lb = np.array([math.log(r["beta"] / BETA0) for r in rep_rows])
    A = np.vstack([np.ones_like(y), -lb]).T
    w = np.array([1.0 / cnt[r["src"]] for r in rep_rows])
    w *= len(w) / w.sum()
    cov0 = np.linalg.inv(A.T @ (w[:, None] * A))
    b = cov0 @ A.T @ (w * y)
    res = y - A @ b
    cov = cov0 * float(np.sum(w * res**2)) / (len(y) - 2)
    err = np.sqrt(np.diag(cov))
    return b, err, cov / np.outer(err, err), math.sqrt(float(np.mean(res**2)))


def model(Re, c, k):
    Rec = c * Re**k
    U = Rec / BETA0
    Vf = (1 - S / BETA0**4) * BETA0**2 / (E * U**2)
    return dict(U=U, Rec=Rec, R=sd.G * Rec, Vf=100 * Vf, d=BETA0 * math.sqrt(math.pi / Vf) if Vf > 0 else float("nan"))


def main():
    unscaled = [r for r in rescaled(0.0) if r["src"] not in EXCLUDE]      # n = 0 keeps U', beta'
    bk, ek, ck, rmsk = regress_k(unscaled, K_FIXED)
    n_use = bk[1] if N_FIXED is None else N_FIXED
    if N_FIXED is None:
        c = math.exp(bk[0])
    else:                                     # n held: ln c is the source-weighted mean of ln(5 U') - k ln Re + n ln(beta'/5)
        cnt = defaultdict(int)
        for r in unscaled:
            cnt[r["src"]] += 1
        v = [math.log(BETA0 * r["Ur"]) - K_FIXED * math.log(r["Re"]) + n_use * math.log(r["beta"] / BETA0) for r in unscaled]
        w = [1.0 / cnt[r["src"]] for r in unscaled]
        lnc = sum(a * b for a, b in zip(w, v)) / sum(w)
        wn = [a * len(w) / sum(w) for a in w]
        sd_ = math.sqrt(sum(a * (b - lnc) ** 2 for a, b in zip(wn, v)) / (len(v) - 1))
        c, bk, ek = math.exp(lnc), [lnc, n_use], [sd_ / math.sqrt(len(v)), 0.0]
        rmsk = math.sqrt(sum((b - lnc) ** 2 for b in v) / len(v))
        ck = [[1.0, 0.0], [0.0, 1.0]]
    print("k held at %.2f, N = %d rows: c = %.3f (ln c = %.3f +- %.3f)   n = %.3f +- %.3f   corr(ln c, n) = %.2f   rms %.1f%%"
          % (K_FIXED, len(unscaled), c, bk[0], ek[0], bk[1], ek[1], ck[0][1], 100 * rmsk))
    print("  kappa = U_max/u' = c 15^0.25 / 5 = %.3f   (swirl as a fraction of the rms velocity)" % (c * 15 ** 0.25 / BETA0))
    names, b, err, corr, rms = regress(unscaled)
    print("  (k free for comparison: k = %.3f +- %.3f, n = %.3f, rms %.1f%%)" % (b[1], err[1], b[2], 100 * rms))
    if K_FREE:
        c, k, n_use, rmsk = math.exp(b[0]), b[1], b[2], rms
        print("k free: c = %.3f +- %.0f%%, k = %.4f +- %.4f, n = %.3f +- %.3f, rms %.1f%%" % (c, 100 * err[0], k, err[1], n_use, err[2], 100 * rms))
    rows = rescaled(n_use)
    if not K_FREE:
        k = K_FIXED
    print("n = %.3f  Re_c = %.3f Re_lambda^%.2f   rms residual %.1f%%" % (n_use, c, k, 100 * rmsk))
    for src in SOURCES:
        v = [math.log(r["Rec"] / (c * r["Re"] ** k)) for r in rows if r["src"] == src]
        print("  %-24s n=%2d  mean deviation %+4.0f%%  rms %4.0f%%%s" % (SHORT[src], len(v), 100 * (math.exp(sum(v) / len(v)) - 1),
              100 * math.sqrt(sum(a * a for a in v) / len(v)), "   (excluded)" if src in EXCLUDE else ""))
    for Re in (90, 332, 1000, 1934):
        m = model(Re, c, k)
        print("  Re_l %4d  U_max %.2f  Re_c %.1f  Gamma/nu %.0f  V_f %.1f%%  d/eta %.1f" % (Re, m["U"], m["Rec"], m["R"], m["Vf"], m["d"]))
    order = [s for s in SOURCES]
    style = {src: (COLOURS[(2 * i) % 20], MARKERS[i % len(MARKERS)]) for i, src in enumerate(order)}
    panels = [("U", r"$U_{max}/U_\eta$ (rescaled)", False), ("Rec", r"$Re_c=5\,U_{max}/U_\eta$", True), ("R", r"$\Gamma/\nu=8.78\,Re_c$", True),
              ("dev", "data / curve - 1 (%)", False), ("Vf", r"$V_f$ (%, budget, derived)", True), ("d", r"$d/\eta$ (budget, derived)", False)]
    res = [30 * (2200 / 30) ** (i / 80) for i in range(81)]
    fig, axes = plt.subplots(2, 3, figsize=(17, 9))
    for ax, (key, label, logy) in zip(axes.ravel(), panels):
        if key == "dev":
            ax.axhline(0, c="k", lw=1)
        elif key not in ("U", "Rec", "R") or True:
            ax.plot(res, [model(Re, c, k)[key] for Re in res], c="k", lw=1.8) if key != "dev" else None
        if key in ("U", "Rec", "R", "dev"):
            for src in order:
                pts = [(r["Re"], 100 * (r["Rec"] / (c * r["Re"] ** k) - 1) if key == "dev" else r[key]) for r in rows if r["src"] == src]
                if pts:
                    col, mk = style[src]
                    ax.scatter(*zip(*pts), marker=mk, s=34, facecolors="none" if src in EXCLUDE else col, edgecolors=col, linewidths=1.3, alpha=0.9)
        ax.set_xscale("log")
        if logy:
            ax.set_yscale("log")
        ax.set_xlabel(r"$Re_\lambda$")
        ax.set_title(label, fontsize=10)
        ax.grid(alpha=0.25, which="both")
    axes[1][1].axhspan(20, 35, color="0.8", alpha=0.5)
    axes[1][1].axhline(1.0, c="0.4", ls=":", lw=1)
    axes[1][1].set_ylim(0.3, 100)
    handles = [Line2D([], [], c="k", lw=1.8, label="curve: Re_c = %.2f Re_l^%.3f" % (c, k))]
    for src in order:
        col, mk = style[src]
        handles.append(Line2D([], [], marker=mk, ls="", mfc="none" if src in EXCLUDE else col, mec=col, mew=1.3, ms=7,
                              label="%s%s" % (SHORT[src], " (not fitted)" if src in EXCLUDE else "")))
    fig.suptitle("Rows rescaled to r_max/eta = 5 with U = U' (beta'/5)^n, n = %.2f, and one curve through all but Mouri and Hori (2009)" % n_use)
    fig.tight_layout(rect=(0, 0, 0.80, 0.96))
    fig.legend(handles=handles, loc="center right", fontsize=9, title="Reference", frameon=True)
    fig.savefig(os.path.join(HERE, "results_rescaled.png"), dpi=110)


if __name__ == "__main__":
    main()
