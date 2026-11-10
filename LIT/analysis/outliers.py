"""Outlier and influence analysis of the (a, q) fit to the 34 literature observations."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

import math
import sys

import numpy as np
from scipy.optimize import least_squares, minimize

sys.path.insert(0, HERE)
import fit_aq as fa
import optimise2d as o

OBS = fa.obs + o.J93


def fit(obs, start=(57.0, 0.88)):
    f = lambda p: o.chi2(p, obs)
    r = minimize(f, start, method="Nelder-Mead", options=dict(xatol=1e-4, fatol=1e-7, maxiter=4000))
    return r.x, r.fun


def robust(obs, loss, start=(57.0, 0.88)):
    r = least_squares(lambda p: o.residuals(p, obs), start, loss=loss, f_scale=1.0)
    return r.x


best, chi0 = fit(OBS)
res = o.residuals(best, OBS)
print("best fit a=%.2f q=%.3f chi2=%.2f for %d points" % (best[0], best[1], chi0, len(OBS)))

# 1. standardised residuals --------------------------------------------------------------------
print("\n1. residuals in sigma (model above the data = positive); flagged if |r| > 1.5")
order = np.argsort(-np.abs(res))
for i in order[:8]:
    s, qn, Re, val, sig = OBS[i]
    m = o.model(Re, *best)[qn]
    print("  %-14s %-5s Re_l=%6.1f obs %.3g model %.3g  r=%+.2f" % (s, qn, Re, val, m, res[i]))
print("  count |r|>1: %d  |r|>1.5: %d  |r|>2: %d  (Gaussian expectation for 34: 11, 2, 1.5)" % ((abs(res) > 1).sum(), (abs(res) > 1.5).sum(), (abs(res) > 2).sum()))
print("  mean residual %+.2f, rms %.2f" % (res.mean(), math.sqrt((res**2).mean())))

# 2. leave-one-out --------------------------------------------------------------------------
print("\n2. leave-one-out: change of (a, q) and chi2 when one observation is dropped")
rows = []
for i in range(len(OBS)):
    sub = OBS[:i] + OBS[i + 1:]
    p, c = fit(sub, best)
    rows.append((i, p[0] - best[0], p[1] - best[1], chi0 - c))
rows.sort(key=lambda r: -abs(r[2]))
print("  largest shifts in q (sigma_q = 0.041, sigma_a = 2.3):")
for i, da, dq, dc in rows[:6]:
    s, qn, Re, val, sig = OBS[i]
    print("  drop %-14s %-5s Re_l=%6.1f : da=%+.2f dq=%+.3f  chi2 falls by %.2f" % (s, qn, Re, da, dq, dc))
print("  max |dq| = %.3f (%.1f sigma_q), max |da| = %.2f (%.1f sigma_a)" % (max(abs(r[2]) for r in rows), max(abs(r[2]) for r in rows) / 0.041,
                                                                         max(abs(r[1]) for r in rows), max(abs(r[1]) for r in rows) / 2.3))
dq = np.array([r[2] for r in rows]); da = np.array([r[1] for r in rows])
n = len(OBS)
print("  jackknife sigma_q = %.3f, sigma_a = %.2f" % (math.sqrt((n - 1) / n * np.sum((dq - dq.mean()) ** 2)), math.sqrt((n - 1) / n * np.sum((da - da.mean()) ** 2))))

# 3. leave one source out -----------------------------------------------------------------------
print("\n3. leave one source out")
for src in sorted({o_[0] for o_ in OBS}):
    sub = [o_ for o_ in OBS if o_[0] != src]
    p, c = fit(sub, best)
    k = len(OBS) - len(sub)
    print("  without %-14s (%2d pts): a=%.1f q=%.3f  chi2=%.1f/%d   shift in q %+.3f" % (src, k, p[0], p[1], c, len(sub), p[1] - best[1]))
print("\n   source by itself:")
for src in sorted({o_[0] for o_ in OBS}):
    sub = [o_ for o_ in OBS if o_[0] == src]
    c = o.chi2(best, sub)
    print("  %-14s %2d pts  chi2 %.1f  (%.2f per point)" % (src, len(sub), c, c / len(sub)))

# 4. robust loss ---------------------------------------------------------------------------------
print("\n4. robust fits (outliers down-weighted)")
for loss in ("linear", "huber", "soft_l1", "cauchy"):
    p = robust(OBS, loss)
    print("  %-8s a=%.2f q=%.3f" % (loss, p[0], p[1]))

# 5. without the two lowest-Re_lambda radii, outside the 83-1934 range of the rest ----------------------
sub = [o_ for o_ in OBS if not (o_[0] == "Jimenez93 IVS" and o_[2] < 70)]
p, c = fit(sub, best)
print("\n5. dropping the two Jimenez93 points below Re_l=70: a=%.2f q=%.3f chi2=%.1f/%d" % (p[0], p[1], c, len(sub)))
