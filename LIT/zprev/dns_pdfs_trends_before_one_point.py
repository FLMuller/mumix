"""dns_pdfs_trends.py  v01  Trends in the lognormal parameters of the DNS pdfs (dns_pdfs_fits.csv): sigma against mu, by group, and the Re_lambda dependence of the Ghira et al. (2022) radius.
Sets     radius: (1) the one-lognormal fit of every row (15 rows), (2) the dominant component of the two-lognormal fit (the first where a1 >= 0.5, else the second), (3) the same split into the pdfs without a volume threshold (Tanahashi, Das, Pirozzoli, Wang)
         and the thresholded sets (Ghira, Jimenez, Aligolzadeh); swirl: the one-lognormal fit in u_K (4 rows) and in u' (3 rows).
Numbers  for each set: n, the least-squares line sigma = c0 + c1 mu, the correlation r, the rms residual; for the two radius groups the implied relation between the mean m e^(sigma^2/2) and the median; the Ghira medians against Re_lambda as m = A Re^p.
Usage    python dns_pdfs_trends.py
Versions M01 m01.v01 (2026-11-15): first version.
"""
import csv
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
NOTHRESH = ("Tanahashi 2001", "Tanahashi 2004", "Das 2006", "Pirozzoli 2012", "Wang 2007")


def line(mu, s):
    mu, s = np.asarray(mu), np.asarray(s)
    if len(mu) < 3:
        return None
    c1, c0 = np.polyfit(mu, s, 1)
    res = s - (c0 + c1 * mu)
    return dict(n=len(mu), c0=c0, c1=c1, r=float(np.corrcoef(mu, s)[0, 1]), rms=float(np.sqrt(np.mean(res ** 2))), mu_range=(float(mu.min()), float(mu.max())), s_range=(float(s.min()), float(s.max())))


def show(name, d):
    if d is None:
        print("%-52s too few points" % name)
        return
    print("%-52s n=%2d  sigma = %.3f + %.3f mu   r = %+.2f  rms residual %.3f   mu %.2f..%.2f  sigma %.2f..%.2f" % (name, d["n"], d["c0"], d["c1"], d["r"], d["rms"], *d["mu_range"], *d["s_range"]))


def main():
    rows = list(csv.DictReader(open(os.path.join(HERE, "dns_pdfs_fits.csv"), encoding="utf-8")))
    sets = {}
    for r in rows:
        q = r["quantity"]
        nt = r["source"].startswith(NOTHRESH)
        one = (math.log(float(r["1 LN median"])), float(r["1 LN s"]))
        a1 = float(r["2 LN a1"])
        dom = (math.log(float(r["2 LN median1"])), float(r["2 LN s1"])) if a1 >= 0.5 else (math.log(float(r["2 LN median2"])), float(r["2 LN s2"]))
        key = "radius" if q.startswith("radius") else q
        for kind, pt in (("one", one), ("dominant", dom)):
            sets.setdefault((key, kind, "all"), []).append(pt)
            if key == "radius":
                sets.setdefault((key, kind, "no threshold" if nt else "thresholded"), []).append(pt)
    for key in ("radius", "swirl / u_K", "swirl / u'"):
        print("\n" + key)
        for kind in ("one", "dominant"):
            for grp in ("all", "no threshold", "thresholded"):
                pts = sets.get((key, kind, grp))
                if pts:
                    show("%s lognormal, %s" % ("one" if kind == "one" else "dominant component", grp), line(*zip(*pts)))
    print("\nmean / median = exp(sigma^2 / 2) for the one-lognormal fits of the radius")
    for r in rows:
        if r["quantity"].startswith("radius"):
            s = float(r["1 LN s"])
            print("  %-48s sigma %.2f  mean/median of the fit %.2f   (data mean/median %.2f)" % (r["source"], s, math.exp(s * s / 2), float(r["data mean"]) / float(r["data median"])))
    g = [(float(re), float(r["1 LN median"]), float(r["1 LN s"])) for r in rows if r["source"].startswith("Ghira") for re in [r["source"].split("lambda")[-1]]]
    g.sort()
    re, m, s = (np.array(v) for v in zip(*g))
    p, lnA = np.polyfit(np.log(re), np.log(m), 1)
    ps = np.polyfit(np.log(re), s, 1)
    print("\nGhira et al. (2022), R_ivs/eta, one lognormal: median m = %.2f Re_lambda^%.3f (%.1f %% over Re 90 -> 399); sigma %.2f..%.2f, slope of sigma on ln Re %.4f" % (math.exp(lnA), p, 100 * (m[-1] / m[0] - 1), s.min(), s.max(), ps[0]))
    print("  Re  median  sigma:", ", ".join("%d %.2f %.2f" % (a, b, c) for a, b, c in g))


if __name__ == "__main__":
    main()
