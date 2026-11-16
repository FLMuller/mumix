"""dns_pdfs_fit.py  v01  A lognormal and a sum of two lognormals fitted to every digitised radius and swirl pdf of dns_pdfs_collate.py (Tanahashi 2001 and 2004, Das 2006, Pirozzoli 2012, Wang 2007, Ghira 2022 (7 Re_lambda), Jimenez and Wray 1998, Aligolzadeh 2023 (2)).
Model    lognormal(x; mu, s) = exp(-(ln x - mu)^2 / (2 s^2)) / (x s sqrt(2 pi)): median exp(mu), mode exp(mu - s^2), mean exp(mu + s^2/2).  Two lognormals: a p1 + (1 - a) p2 with the medians ordered (mu2 >= mu1).
Method   the function of the page, fit_tanahashi_lognormal.fit_mixture, in the linear domain (p itself, 2 % of the peak + 15 % of the point as the error), on the curve scaled to unit area (the data are not rescaled by the fit: AREA_MATCH off, as summary_pdfs).  First ONE lognormal (the weight held at 1,
         width free up to 3), then TWO: for the radius the first component is the narrow one (s2 >= 2 s1, widths at most 0.7, the constraints of summary_pdfs.fit), for the swirl no width ratio and widths up to 3.  rms = rms misfit / the peak of the curve.
         The mode and median of the sum of two are taken from the curve on a fine grid, its mean is exact.
Output   dns_pdfs_fits.md, dns_pdfs_fits.csv (parameters, statistics, misfit), dns_fits_radius.png and dns_fits_swirl.png (data, one lognormal, two lognormals with their components, linear axes), numbers printed.
Usage    python dns_pdfs_fit.py
Versions M01 m01.v01 (2026-11-15): first version.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import dns_pdfs_collate as dc
import fit_tanahashi_lognormal as fl

HERE = os.path.dirname(os.path.abspath(__file__))


def fit_one(x, p):
    fl.AREA_MATCH, fl.S1_FIXED, fl.MU1_FIXED, fl.ORDER, fl.SRATIO, fl.A_FIXED = False, None, None, "median", 0.0, 1.0       # weight held at 1: a single lognormal
    try:
        q = fl.fit_mixture(x, p, p, p, 3.0, "lin")
    finally:
        fl.A_FIXED = None
    return q[1], q[2]


def fit_two(x, p, size):
    fl.AREA_MATCH, fl.S1_FIXED, fl.MU1_FIXED, fl.A_FIXED, fl.ORDER = False, None, None, None, "median"
    fl.SRATIO = 2.0 if size else 0.0
    return fl.fit_mixture(x, p, p, p, 0.7 if size else 3.0, "lin")


def rms(model, p):
    return float(np.sqrt(np.mean((model - p) ** 2)) / p.max())


def mix_stats(q):
    xs = np.exp(np.linspace(np.log(1e-2), np.log(300.0), 6000))
    m = fl.mixture(xs, q)
    c = np.r_[0, np.cumsum(0.5 * (m[1:] + m[:-1]) * np.diff(xs))]
    return dict(mode=float(xs[np.argmax(m)]), median=float(np.interp(0.5 * c[-1], c, xs)), mean=float(q[0] * np.exp(q[1] + q[2] ** 2 / 2) + (1 - q[0]) * np.exp(q[3] + q[4] ** 2 / 2)))


def main():
    rc = dc.radius_curves()
    uk, urms = dc.swirl_curves()
    jobs = [("radius", rc, True), ("swirl / u_K", uk, False), ("swirl / u'", urms, False)]
    rows = []
    figs = {}
    for quantity, curves, size in jobs:
        n = len(curves)
        cols = 4
        fig, axes = plt.subplots((n + cols - 1) // cols, cols, figsize=(4.4 * cols, 3.4 * ((n + cols - 1) // cols)), squeeze=False)
        figs[quantity] = fig
        for k, cv in enumerate(curves):
            x, p = cv["x"], cv["p"]
            o = np.argsort(x)
            x, p = x[o], p[o]
            mu, s = fit_one(x, p)
            q = fit_two(x, p, size)
            m1 = fl.lognormal(x, mu, s)
            m2 = fl.mixture(x, q)
            e1, e2 = rms(m1, p), rms(m2, p)
            st = dc.stats(x, p)
            s2 = mix_stats(q)
            rows.append(dict(label=cv["label"], quantity=quantity, data=st, one=dict(median=np.exp(mu), s=s, mode=np.exp(mu - s * s), mean=np.exp(mu + s * s / 2), rms=e1), two=dict(a=q[0], m1=np.exp(q[1]), s1=q[2], m2=np.exp(q[3]), s2=q[4], rms=e2, **s2)))
            print("%-48s one: median %.2f s %.2f rms %.3f | two: a %.2f  %.2f/%.2f  %.2f/%.2f rms %.3f" % (cv["label"], np.exp(mu), s, e1, q[0], np.exp(q[1]), q[2], np.exp(q[3]), q[4], e2))
            a = axes[k // cols][k % cols]
            xs = np.linspace(x.min(), x.max(), 600)
            a.plot(x, p, "k-", lw=1.5, label="digitised")
            a.plot(xs, fl.lognormal(xs, mu, s), "b--", lw=1.3, label="1 lognormal (rms %.3f)" % e1)
            a.plot(xs, fl.mixture(xs, q), "r-", lw=1.3, label="2 lognormals (rms %.3f)" % e2)
            a.plot(xs, q[0] * fl.lognormal(xs, q[1], q[2]), "r:", lw=1.0)
            a.plot(xs, (1 - q[0]) * fl.lognormal(xs, q[3], q[4]), "r:", lw=1.0)
            a.set_title(cv["label"], fontsize=8)
            a.set_xlim(0, {"radius": 25, "swirl / u_K": 10, "swirl / u'": 3}[quantity])
            a.set_ylim(bottom=0)
            a.legend(fontsize=6)
        for k in range(n, len(axes.ravel())):
            axes[k // cols][k % cols].axis("off")
        fig.tight_layout()
    figs["radius"].savefig(os.path.join(HERE, "dns_fits_radius.png"), dpi=85)
    figs["swirl / u_K"].savefig(os.path.join(HERE, "dns_fits_swirl_uK.png"), dpi=85)
    figs["swirl / u'"].savefig(os.path.join(HERE, "dns_fits_swirl_urms.png"), dpi=85)
    head = ["source", "quantity", "data mode", "data median", "data mean", "1 LN median", "1 LN s", "1 LN mode", "1 LN mean", "1 LN rms", "2 LN a1", "2 LN median1", "2 LN s1", "2 LN median2", "2 LN s2", "2 LN mode", "2 LN median", "2 LN mean", "2 LN rms", "rms 2 / rms 1"]
    body = []
    for r in rows:
        d, o, t = r["data"], r["one"], r["two"]
        body.append([r["label"], r["quantity"], "%.2f" % d["mode"], "%.2f" % d["median"], "%.2f" % d["mean"], "%.2f" % o["median"], "%.2f" % o["s"], "%.2f" % o["mode"], "%.2f" % o["mean"], "%.3f" % o["rms"],
                     "%.2f" % t["a"], "%.2f" % t["m1"], "%.2f" % t["s1"], "%.2f" % t["m2"], "%.2f" % t["s2"], "%.2f" % t["mode"], "%.2f" % t["median"], "%.2f" % t["mean"], "%.3f" % t["rms"], "%.2f" % (t["rms"] / o["rms"])])
    with open(os.path.join(HERE, "dns_pdfs_fits.md"), "w", encoding="utf-8") as f:
        f.write("| " + " | ".join(head) + " |\n|" + "---|" * len(head) + "\n")
        for b in body:
            f.write("| " + " | ".join(b) + " |\n")
    with open(os.path.join(HERE, "dns_pdfs_fits.csv"), "w", encoding="utf-8") as f:
        f.write(",".join('"%s"' % h for h in head) + "\n")
        for b in body:
            f.write(",".join('"%s"' % v for v in b) + "\n")


if __name__ == "__main__":
    main()
