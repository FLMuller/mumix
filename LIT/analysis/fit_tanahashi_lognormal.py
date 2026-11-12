"""fit_tanahashi_lognormal.py  v01  Fit lognormal distributions to the mean curves P of the digitised pdfs of Tanahashi et al. (2001), Fig. 7.

Reads tanahashi2001_pdfs.csv (plot_tanahashi_pdf.py): P = (P_top + P_bottom)/2 of the diameter D* and of the maximum azimuthal velocity v* (columns ignored where a curve drops to zero).
Model  p(x) = exp(-(ln x - mu)^2 / (2 s^2)) / (x s sqrt(2 pi)), a normalised pdf with two parameters (and the mixture a p1(x) + (1 - a) p2(x) of two of them, five parameters) (median exp(mu), width s in ln x); mode exp(mu - s^2), mean exp(mu + s^2/2).
Two single fits: (log) the logarithm of p, weighted by the spread of the bounds, which weights the tail as much as the core; (lin) p itself, which weights the core.  The mixtures are fitted in the linear domain (p, all points with the same weight; v03: a differential-evolution search polished by least squares) from v02 on.  P is first normalised to unit area.
Writes tanahashi2001_lognormal.png (the figure shows the bimodal fit only: the sum of two lognormals with s <= 0.7 and its two components) and prints the parameters, with the mode, median and mean of the fit against those of the digitised curve.
Usage: python fit_tanahashi_lognormal.py
"""
import os

import numpy as np
from scipy.optimize import least_squares
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))


def lognormal(x, mu, s):
    return np.exp(-(np.log(x) - mu) ** 2 / (2 * s * s)) / (x * s * np.sqrt(2 * np.pi))


def load():
    d = np.genfromtxt(os.path.join(HERE, "tanahashi2001_pdfs.csv"), delimiter=",", names=True)
    out = {}
    for key, cols, xmin in (("D", ("D_star", "pD_top", "pD_bottom", "pD"), 4.0), ("v", ("v_star", "pv_top", "pv_bottom", "pv"), 0.05)):
        x, top, bot, p = (d[c] for c in cols)
        ok = np.isfinite(x) & (x >= xmin)
        x, top, bot, p = x[ok], top[ok], bot[ok], p[ok]
        area = np.trapezoid(p, x)
        out[key] = (x, top / area, bot / area, p / area)
    return out


def fit(x, top, bot, p, mode):
    sig = np.maximum(0.5 * np.log(top / bot), 0.1)                 # the spread of the bounds, in ln p, as the uncertainty of a point
    def resid(q):
        m = lognormal(x, q[0], q[1])
        return (np.log(m) - np.log(p)) / sig if mode == "log" else (m - p) / (0.05 * p.max() + 0.0 * sig)
    start = [np.log(np.trapezoid(p * x, x)) - 0.3, 0.5]
    r = least_squares(resid, start, bounds=([-5, 0.05], [8, 3.0]))
    return r.x, r.fun


def mixture(x, q):
    """Two lognormals: weight w of the core (mu1, s1) and 1 - w of the tail (mu2, s2)."""
    return q[0] * lognormal(x, q[1], q[2]) + (1 - q[0]) * lognormal(x, q[3], q[4])


ORDER = "median"        # "median": mu2 >= mu1 (the medians are ordered); "mode": mu2 - s2^2 >= mu1 - s1^2 (the peaks of the two components are ordered)
SRATIO = 2.0            # the first component is the narrow one: s2 >= SRATIO s1 (sigma1 much smaller than sigma2); 0 = no constraint (the size pdfs use 2, the swirl pdfs 0)


LAST_KAPPA = 1.0        # the scale of the digitised pdf found by the last fit_mixture: digitised P = LAST_KAPPA x (the pdf that integrates to 1 over 0..infinity)
AREA_MATCH = True       # True: the model is scaled to the area of the digitised pdf over its range; False: the model is the mixture itself (the data are expected to be normalised to a total area of 1 beforehand)
MU1_FIXED = None        # a number: the MEDIAN (e^mu1) of the first component is held at that value
S1_FIXED = None         # a number: the width s1 of the first component is held at that value
A_FIXED = None          # a number (0.7): the weight a1 of the first component is held at that value instead of being fitted


def fit_mixture(x, top, bot, p, smax=3.0, domain="lin"):
    """Two lognormals a p1 + (1 - a) p2 with mu2 >= mu1 (ORDER), s2 >= SRATIO s1 and the start a = 0.7.  The parameters are (a, mu1, s1, d, t): mu2 = mu1 + d (+ s2^2 - s1^2 for the ordering of
    the modes), s2 = SRATIO s1 + (smax - SRATIO s1) t with d >= 0 and 0 <= t <= 1, from several starts (a = 0.7 always); the widths are at most smax (0.7 forces two separate modes)."""
    sig = np.maximum(0.5 * np.log(top / bot), 0.1) if domain == "log" else 0.02 * p.max() + 0.15 * p   # log: spread of the bounds in ln p; lin: 2% of the peak + 15% of the point
    lx = np.log(x)
    smx = min(smax, 3.0)
    def s2_of(q):
        return SRATIO * q[2] + (smx - SRATIO * q[2]) * q[4]
    def mu2_of(q):
        return q[1] + q[3] + ((s2_of(q) ** 2 - q[2] ** 2) if ORDER == "mode" else 0.0)
    area_p = np.trapezoid(p, x)
    def model(q):
        m = mixture(x, [q[0], q[1], q[2], mu2_of(q), s2_of(q)])          # integrates to 1 over 0..infinity, so to less than 1 over the digitised range
        if not AREA_MATCH:
            return m
        return area_p * m / np.trapezoid(m, x)                            # the model is scaled to the area of the digitised pdf over the range: the digitised pdf is off by a few per cent and some mass lies outside the range
    def resid(q):
        m = model(q)
        return ((np.log(m + 1e-300) - np.log(p)) if domain == "log" else (m - p)) / sig
    mode = x[np.argmax(p)]
    best = None
    for m1 in (np.log(mode * np.array([0.7, 0.85, 1.0, 1.2])) if MU1_FIXED is None else (np.log(MU1_FIXED),)):
        for delta in ((0.2, 0.5, 0.9, 1.3) if ORDER != "free" else (-0.8, -0.4, 0.0, 0.4)):
            for s1 in ((0.15, 0.25, 0.33) if S1_FIXED is None else (S1_FIXED,)):
                for t in (0.2, 0.6):
                    if SRATIO * s1 > smx:
                        continue
                    try:
                        r = least_squares(resid, [0.7 if A_FIXED is None else A_FIXED, m1, s1, delta, t, 1.0], bounds=([0.02 if A_FIXED is None else A_FIXED - 1e-9, lx.min() if MU1_FIXED is None else m1 - 1e-9, 0.05 if S1_FIXED is None else S1_FIXED - 1e-9, 0.0 if ORDER != "free" else -3.0, 0.0, 0.7],
                                                                  [0.999 if A_FIXED is None else A_FIXED + 1e-9, lx.max() if MU1_FIXED is None else m1 + 1e-9, (smx / SRATIO if SRATIO > 0 else smx) if S1_FIXED is None else S1_FIXED + 1e-9, 3.0, 1.0, 1.4]))
                    except Exception:
                        continue
                    if best is None or r.cost < best.cost:
                        best = r
    q = best.x
    m = mixture(x, [q[0], q[1], q[2], mu2_of(q), s2_of(q)])
    globals()["LAST_KAPPA"] = float(area_p / np.trapezoid(m, x)) if AREA_MATCH else 1.0          # digitised P / kappa has the area (over the range) that the fit has: the fit mass inside the range
    return np.array([q[0], q[1], q[2], mu2_of(q), s2_of(q)])


def report_volume(x, p, q, label):
    """The share of the number and of the volume (weight D^2, the area of the cross-section) of the two components of the diameter pdf, integrated over D* = 4-100 (the range
    of the figure) and over the whole lognormals (analytic)."""
    xs = np.linspace(4.0, 100.0, 4000)
    parts = [q[0] * lognormal(xs, q[1], q[2]), (1 - q[0]) * lognormal(xs, q[3], q[4])]
    num = [np.trapezoid(f, xs) for f in parts]
    vol = [np.trapezoid(f * xs ** 2, xs) for f in parts]
    ana = [w * np.exp(2 * mu + 2 * sg * sg) for w, mu, sg in ((q[0], q[1], q[2]), (1 - q[0], q[3], q[4]))]
    print("   %s: by number (D* 4-100) core %.2f tail %.2f; by D^2 (volume) core %.2f tail %.2f; analytic (to infinity) core %.2f tail %.2f; volume-weighted rms diameter %.1f (r_max %.1f)" % (
        label, num[0] / sum(num), num[1] / sum(num), vol[0] / sum(vol), vol[1] / sum(vol), ana[0] / sum(ana), ana[1] / sum(ana), np.sqrt(sum(vol) / sum(num)), np.sqrt(sum(vol) / sum(num)) / 2))
    dd = np.trapezoid(p * x ** 2, x) / np.trapezoid(p, x)
    print("      digitised P: rms diameter %.1f (r_max %.1f)" % (np.sqrt(dd), np.sqrt(dd) / 2))


def stats(mu, s):
    return dict(median=np.exp(mu), mode=np.exp(mu - s * s), mean=np.exp(mu + s * s / 2), sigma=s)


def main():
    data = load()
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for col, (key, name, unit, lin_max, log_floor) in enumerate((("D", r"$D^*=D/\eta$", r"$D^*$", 60, 1e-4), ("v", r"$v^*_{\theta,m}=v_{\theta,m}/u'_{rms}$", r"$v^*_{\theta,m}$", 3.0, 1e-3))):
        x, top, bot, p = data[key]
        xs = np.exp(np.linspace(np.log(x.min()), np.log(x.max()), 400))
        raw = dict(median=x[np.searchsorted(np.cumsum(p) / np.sum(p), 0.5)], mode=x[np.argmax(p)], mean=np.trapezoid(p * x, x))
        print("%s digitised: mode %.3g median %.3g mean %.3g" % (key, raw["mode"], raw["median"], raw["mean"]))
        fits = {}
        for mode, colour in (("log", "tab:red"), ("lin", "tab:blue")):
            q, res = fit(x, top, bot, p, mode)
            fits[mode] = (q, colour)
            st = stats(*q)
            print("   fit %s: mu %.3f sigma %.3f  median %.3g mode %.3g mean %.3g   rms ln residual %.2f" % (mode, q[0], q[1], st["median"], st["mode"], st["mean"], np.sqrt(np.mean(np.log(lognormal(x, *q) / p) ** 2))))
        mixes = {}
        for label, smax in (("two lognormals, free widths", 3.0), ("bimodal: widths <= 0.7", 0.7)):
            globals()["SRATIO"] = 2.0 if key == "D" else 0.0
            mix = fit_mixture(x, top, bot, p, smax, "lin")
            mixes[label] = mix
            c1, c2 = stats(mix[1], mix[2]), stats(mix[3], mix[4])
            m = mixture(xs, mix)
            peaks = [xs[i] for i in range(1, len(xs) - 1) if m[i] > m[i - 1] and m[i] > m[i + 1]]
            print("   %s: weight %.2f, median %.3g s %.2f | median %.3g s %.2f   rms ln residual %.2f, rms residual in p %.4f (in units of the peak: %.3f); peaks at %s; mean %.3g (digitised %.3g)" % (
                label, mix[0], c1["median"], mix[2], c2["median"], mix[4], np.sqrt(np.mean(np.log(mixture(x, mix) / p) ** 2)), np.sqrt(np.mean((mixture(x, mix) - p) ** 2)), np.sqrt(np.mean((mixture(x, mix) - p) ** 2)) / p.max(), ", ".join("%.3g" % v for v in peaks), np.trapezoid(m * xs, xs), raw["mean"]))
        if key == "D":
            report_volume(x, p, mixes["bimodal: widths <= 0.7"], "linear-domain fit")
            report_volume(x, p, fit_mixture(x, top, bot, p, 0.7, "log"), "log-domain fit")
        for row, logy in enumerate((False, True)):
            a = axes[row][col]
            a.fill_between(x, bot, top, color="0.85")
            mix = mixes["bimodal: widths <= 0.7"]
            m1, m2 = mix[0] * lognormal(xs, mix[1], mix[2]), (1 - mix[0]) * lognormal(xs, mix[3], mix[4])
            a.plot(xs, m1, c="tab:blue", lw=1.0, ls=":", label="component 1: weight %.2f, median %.3g, s = %.2f" % (mix[0], np.exp(mix[1]), mix[2]))
            a.plot(xs, m2, c="tab:orange", lw=1.0, ls=":", label="component 2: weight %.2f, median %.3g, s = %.2f" % (1 - mix[0], np.exp(mix[3]), mix[4]))
            a.plot(xs, m1 + m2, c="tab:red", lw=1.8, label="bimodal fit: sum of the two lognormals")
            a.plot(x, p, c="k", lw=1.2, label="digitised P")
            a.set_xlim(0, lin_max if not logy else (100 if key == "D" else 3.0))
            if logy:
                a.set_yscale("log")
                a.set_ylim(log_floor, None)
            a.set_xlabel(unit)
            a.set_ylabel("pdf" + (" (log)" if logy else ""))
            a.grid(alpha=0.25, which="both")
            a.legend(fontsize=7.5)
            if row == 0:
                a.set_title(name, fontsize=10)
    fig.suptitle("Tanahashi et al. (2001) Fig. 7: the mean curves P fitted with two lognormals in the linear domain, widths <= 0.7 (grey: between the bounds)", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "tanahashi2001_lognormal.png"), dpi=110)
    plt.rcParams["svg.fonttype"] = "none"
    fig.savefig(os.path.join(HERE, "tanahashi2001_lognormal.svg"), format="svg", facecolor="white")      # embedded in section 9 of the page by build_data_sections.py


if __name__ == "__main__":
    main()
