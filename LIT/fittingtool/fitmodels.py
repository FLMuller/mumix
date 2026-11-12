"""fitmodels.py  v01  The models of the tube closure, their fitting and their scores.

A model predicts, from Re_lambda and its parameters, the tube as a Burgers vortex in Kolmogorov units:
    r = r_max/eta,  U = U_max/U_eta,  G = Gamma/nu = G0 r U   (G0 = 2 pi/(1 - exp(-x)) = 8.784, x = 1.2564)
and the budget quantities that follow from r and U:
    g = gamma/gamma_eta = 4x/r**2,  share = 1 - S/r**4 (S = 48 x**2),  V_f = share r**2/(E U**2) (E = 0.977 * 4x),  d/eta = r sqrt(pi/V_f).

    models()                          the list of Model objects (below), in the order of the report
    fit(model, obs)                   least squares of the log residuals; returns a dict (params, errors, scores)
    score(model, params, obs)         the scores of a parameter set against any data
    budget(r, U)                      the budget quantities
    select(results)                   the simplest model that fits reasonably well

Fitting.  The residual of a data point is sqrt(w) ln(model/data), summed over the quantities the model is fitted to (Model.kinds); the
weights are those of fitdata (each source counts equally within a quantity).  The errors of the parameters are from the Jacobian,
cov = (J'J)^-1 SS/(N - p), and treat every data point as independent, so they are too small.
Scores (the same for every model, whatever it was fitted to): the weighted rms log residual of r, U and G ("rms_r", "rms_U", "rms_G");
the unweighted RMSE/mean in per cent ("rmse_r" ...); combined = sqrt((rms_r**2 + rms_U**2)/2), the figure used to rank the models.
Selection: the models that are physically sensible (0.01 < V_f < 0.5 for 100 <= Re_lambda <= 2000, no negative or infinite r, U) and not marked
information-only; of those the one with the fewest parameters whose combined score is within TOLERANCE (1.25) of the best, the smaller score on a tie.

Versions  M01 m01.v01 (2026-11-11): first version.
"""
import math

import numpy as np
from scipy.optimize import least_squares

from fitdata import BURGERS_X, G0

__all__ = ["Model", "models", "fit", "score", "budget", "select", "TOLERANCE", "loglin", "legacy_n", "sensible", "RE_CHECK"]

X = BURGERS_X
S = 48 * X * X
E = 0.977 * 4 * X
TOLERANCE = 1.25
RE_CHECK = (50, 100, 300, 1000, 2000)


def budget(r, U):
    """The quantities that follow from the radius and the swirl: g = gamma/gamma_eta, share, V_f, d/eta."""
    r = np.asarray(r, float)
    U = np.asarray(U, float)
    share = 1 - S / r**4
    vf = share * r**2 / (E * U**2)
    with np.errstate(invalid="ignore", divide="ignore"):
        d = r * np.sqrt(np.pi / vf)
    return dict(g=4 * X / r**2, share=share, vf=vf, d=d)


def loglin(re, val, w=None):
    """Start values: ln val = ln a + s ln Re by weighted least squares; returns (a, s)."""
    x = np.log(re)
    y = np.log(val)
    w = np.ones_like(x) if w is None else w
    A = np.vstack([np.ones_like(x), x]).T
    b = np.linalg.lstsq(A * np.sqrt(w)[:, None], y * np.sqrt(w), rcond=None)[0]
    return math.exp(b[0]), b[1]


class Model:
    """A model: key, name, family, parameter names, starts, bounds, predict(Re, p, sets) -> dict(r, U, G), the quantities it is fitted to."""

    def __init__(self, key, name, family, names, starts, bounds, predict, equations, kinds, info=False, note=""):
        self.key, self.name, self.family = key, name, family
        self.names, self.starts, self.bounds = names, starts, bounds
        self.predict, self.equations, self.kinds, self.info, self.note = predict, equations, kinds, info, note
        self.nparam = len(names)


def pack(r, U):
    return dict(r=r, U=U, G=G0 * r * U)


def power(Re, a, s):
    return a * np.asarray(Re, float) ** s


# ---------------------------------------------------------------------------------------------------- predict functions
def p_r5_powerU(Re, p, sets=None):                  # r = 5, U = c Re^s
    return pack(np.full_like(np.asarray(Re, float), 5.0), power(Re, p[0], p[1]))


def p_rb_powerU(Re, p, sets=None):                  # r = b, U = c Re^s
    return pack(np.full_like(np.asarray(Re, float), p[0]), power(Re, p[1], p[2]))


def p_powerr_powerU(Re, p, sets=None):              # r = b Re^m, U = c Re^s
    return pack(power(Re, p[0], p[1]), power(Re, p[2], p[3]))


def p_lnr_powerU(Re, p, sets=None):                 # r = a + b ln Re, U = c Re^s
    return pack(p[0] + p[1] * np.log(np.asarray(Re, float)), power(Re, p[2], p[3]))


def p_lnr_third(Re, p, sets=None):                  # r = a + b ln Re, U = c Re^(1/3)
    return pack(p[0] + p[1] * np.log(np.asarray(Re, float)), power(Re, p[2], 1.0 / 3.0))


def lin_ln(Re, a, b):
    return a + b * np.log(np.asarray(Re, float))


def p_r5_lnU(Re, p, sets=None):                     # r = 5, U = a + b ln Re
    Re = np.asarray(Re, float)
    return pack(np.full_like(Re, 5.0), lin_ln(Re, p[0], p[1]))


def p_r5_lnG(Re, p, sets=None):                     # r = 5, G = a + b ln Re, U = G/(G0 r)
    Re = np.asarray(Re, float)
    G = lin_ln(Re, p[0], p[1])
    r = np.full_like(Re, 5.0)
    return dict(r=r, U=G / (G0 * r), G=G)


def p_rb_lnU(Re, p, sets=None):                     # r = b, U = a + c ln Re
    Re = np.asarray(Re, float)
    return pack(np.full_like(Re, p[0]), lin_ln(Re, p[1], p[2]))


def p_lnr_lnU(Re, p, sets=None):                    # r = a1 + b1 ln Re, U = a + b ln Re
    return pack(lin_ln(Re, p[0], p[1]), lin_ln(Re, p[2], p[3]))


def p_lnr_lnG(Re, p, sets=None):                    # r = a1 + b1 ln Re, G = a + b ln Re, U = G/(G0 r)
    r = lin_ln(Re, p[0], p[1])
    G = lin_ln(Re, p[2], p[3])
    return dict(r=r, U=G / (G0 * np.maximum(r, 1e-9)), G=G)


def p_closure_lnU_powG(Re, p, sets=None):           # U = a + b ln Re, G = c Re^Q, r = G/(G0 U)
    Re = np.asarray(Re, float)
    U = lin_ln(Re, p[0], p[1])
    G = power(Re, p[2], p[3])
    return dict(r=G / (G0 * np.maximum(U, 1e-9)), U=U, G=G)


def p_r5_uprime(Re, p, sets=None):                  # r = 5, U = kappa u'/U_eta, u'/U_eta = (Re/sqrt 15)^(1/2)
    Re = np.asarray(Re, float)
    return pack(np.full_like(Re, 5.0), p[0] * np.sqrt(Re / math.sqrt(15)))


def p_r5_third(Re, p, sets=None):                   # r = 5, U = c Re^(1/3)
    Re = np.asarray(Re, float)
    return pack(np.full_like(Re, 5.0), p[0] * Re ** (1.0 / 3.0))


def p_rb_uprime(Re, p, sets=None):                  # r = b, U = kappa u'
    Re = np.asarray(Re, float)
    return pack(np.full_like(Re, p[0]), p[1] * np.sqrt(Re / math.sqrt(15)))


def p_G_r5(Re, p, sets=None):                       # G = c Re^Q, r = 5, U = G/(G0 r)
    Re = np.asarray(Re, float)
    G = power(Re, p[0], p[1])
    r = np.full_like(Re, 5.0)
    return dict(r=r, U=G / (G0 * r), G=G)


def p_G_rb(Re, p, sets=None):                       # G = c Re^Q, r = b
    Re = np.asarray(Re, float)
    G = power(Re, p[0], p[1])
    r = np.full_like(Re, p[2])
    return dict(r=r, U=G / (G0 * r), G=G)


def p_G_powerr(Re, p, sets=None):                   # G = c Re^Q, r = b Re^m
    Re = np.asarray(Re, float)
    G = power(Re, p[0], p[1])
    r = power(Re, p[2], p[3])
    return dict(r=r, U=G / (G0 * r), G=G)


def p_closure4(Re, p, sets=None):                   # G = a Re^p, U = r^q Re^s, G = G0 r U
    Re = np.asarray(Re, float)
    a, pe, q, s = p
    G = a * Re**pe
    r = (G / (G0 * Re**s)) ** (1.0 / (1.0 + q))
    return dict(r=r, U=r**q * Re**s, G=G)


def p_closure3(Re, p, sets=None):                   # s = 0: U = r^q
    Re = np.asarray(Re, float)
    a, pe, q = p
    G = a * Re**pe
    r = (G / G0) ** (1.0 / (1.0 + q))
    return dict(r=r, U=r**q, G=G)


def p_twoset(Re, p, sets=None):                     # r = b Re^m common, U = c_i Re^s_i per tube set
    Re = np.asarray(Re, float)
    b, m, c1, s1, c2, s2 = p
    if sets is None:
        sets = np.array(["intense"] * len(Re))
    sets = np.asarray(sets)
    U = np.where(sets == "intense", c1 * Re**s1, c2 * Re**s2)
    return pack(b * Re**m, U)


def models(data=None):
    """The models, in the order of the report; data (observations) gives the start values."""
    ms = []
    def start_power(kind):
        if data is None:
            return 1.0, 0.3
        return loglin(data[kind]["re"], data[kind]["val"], data[kind]["w"])
    a_u, s_u = start_power("U")
    a_r, m_r = start_power("r")
    a_g, q_g = start_power("G")
    ms.append(Model("D1", "radius 5, swirl a power of Re_lambda", "direct", ["c", "s"], [[a_u, s_u]], [(1e-3, -1), (50, 2)], p_r5_powerU,
                    ["r = 5", "U = c Re^s"], ["U"]))
    ms.append(Model("D2", "constant radius (fitted), swirl a power", "direct", ["b", "c", "s"], [[5.0, a_u, s_u]], [(2, 1e-3, -1), (12, 50, 2)], p_rb_powerU,
                    ["r = b", "U = c Re^s"], ["r", "U"]))
    ms.append(Model("D3", "radius and swirl both powers of Re_lambda", "direct", ["b", "m", "c", "s"], [[a_r, m_r, a_u, s_u]],
                    [(0.5, -1, 1e-3, -1), (30, 1, 50, 2)], p_powerr_powerU, ["r = b Re^m", "U = c Re^s"], ["r", "U"]))
    ms.append(Model("D4", "radius 5, swirl proportional to u' (k = 1/2)", "direct", ["kappa"], [[0.9]], [(1e-3,), (20,)], p_r5_uprime,
                    ["r = 5", "U = kappa u'/U_eta = kappa (Re/sqrt 15)^(1/2)"], ["U"]))
    ms.append(Model("D5", "constant radius (fitted), swirl proportional to u'", "direct", ["b", "kappa"], [[5.0, 0.9]], [(2, 1e-3), (12, 20)], p_rb_uprime,
                    ["r = b", "U = kappa (Re/sqrt 15)^(1/2)"], ["r", "U"]))
    ms.append(Model("D6", "radius 5, swirl c Re^(1/3) (exponent fixed)", "direct", ["c"], [[0.8]], [(1e-3,), (50,)], p_r5_third,
                    ["r = 5", "U = c Re^(1/3)"], ["U"], note="the exponent 1/3 is the rounded value of the fit of D1 (0.336 +- 0.016); empirical, not derived"))
    ms.append(Model("D7", "radius a + b ln Re_lambda, swirl a power", "direct", ["a", "b", "c", "s"], [[5.2, -0.03, a_u, s_u]],
                    [(2, -3, 1e-3, -1), (12, 3, 50, 2)], p_lnr_powerU, ["r = a + b ln Re", "U = c Re^s"], ["r", "U"],
                    note="the radius as a straight line in ln Re (natural log); b < 0 is a radius that shrinks with Re_lambda"))
    ms.append(Model("D8", "radius a + b ln Re_lambda, swirl c Re^(1/3)", "direct", ["a", "b", "c"], [[5.2, -0.03, 0.8]],
                    [(2, -3, 1e-3), (12, 3, 50)], p_lnr_third, ["r = a + b ln Re", "U = c Re^(1/3)"], ["r", "U"],
                    note="D7 with the swirl exponent fixed at 1/3 as in D6"))
    def start_lin(kind):
        if data is None:
            return 0.0, 1.0
        x, y, w = np.log(data[kind]["re"]), data[kind]["val"], data[kind]["w"]
        A = np.vstack([np.ones_like(x), x]).T
        b = np.linalg.lstsq(A * np.sqrt(w)[:, None], y * np.sqrt(w), rcond=None)[0]
        return float(b[0]), float(b[1])
    a_ul, b_ul = start_lin("U")
    a_gl, b_gl = start_lin("G")
    a_rl, b_rl = start_lin("r")
    ms.append(Model("L1", "radius 5, swirl a + b ln Re_lambda", "logarithmic", ["a", "b"], [[a_ul, b_ul]], [(-50, 0), (50, 20)], p_r5_lnU,
                    ["r = 5", "U = a + b ln Re"], ["U"]))
    ms.append(Model("L2", "radius 5, circulation a + b ln Re_lambda", "logarithmic", ["a", "b"], [[a_gl, b_gl]], [(-2000, 0), (2000, 500)], p_r5_lnG,
                    ["r = 5", "G = a + b ln Re", "U = G/(G0 r)"], ["G"]))
    ms.append(Model("L3", "constant radius (fitted), swirl a + b ln Re_lambda", "logarithmic", ["r", "a", "b"], [[5.0, a_ul, b_ul]], [(2, -50, 0), (12, 50, 20)], p_rb_lnU,
                    ["r = r", "U = a + b ln Re"], ["r", "U"]))
    ms.append(Model("L4", "radius and swirl both a + b ln Re_lambda", "logarithmic", ["a1", "b1", "a", "b"], [[a_rl, b_rl, a_ul, b_ul]],
                    [(0.5, -3, -50, 0), (30, 3, 50, 20)], p_lnr_lnU, ["r = a1 + b1 ln Re", "U = a + b ln Re"], ["r", "U"]))
    ms.append(Model("L5", "radius a1 + b1 ln Re_lambda, circulation a + b ln Re_lambda", "logarithmic", ["a1", "b1", "a", "b"], [[a_rl, b_rl, a_gl, b_gl]],
                    [(0.5, -3, -2000, 0), (30, 3, 2000, 500)], p_lnr_lnG, ["r = a1 + b1 ln Re", "G = a + b ln Re", "U = G/(G0 r)"], ["r", "G"]))
    ms.append(Model("K5", "closure: swirl a + b ln Re, circulation c Re^Q, radius G/(G0 U)", "closure", ["a", "b", "c", "Q"], [[a_ul, b_ul, a_g, q_g]],
                    [(-50, 0, 1e-2, -1), (50, 20, 1e5, 2)], p_closure_lnU_powG, ["U = a + b ln Re", "G = c Re^Q", "r = G/(G0 U)"], ["r", "U", "G"],
                    note="swirl a straight line in ln Re, circulation a power law; the radius follows from G = G0 r U"))
    ms.append(Model("C1", "circulation c Re^Q, radius 5", "circulation", ["c", "Q"], [[a_g, q_g]], [(1e-2, -1), (1e5, 2)], p_G_r5,
                    ["G = c Re^Q", "r = 5", "U = G/(G0 r)"], ["G"]))
    ms.append(Model("C2", "circulation c Re^Q, constant radius (fitted)", "circulation", ["c", "Q", "b"], [[a_g, q_g, 5.0]], [(1e-2, -1, 2), (1e5, 2, 12)], p_G_rb,
                    ["G = c Re^Q", "r = b", "U = G/(G0 r)"], ["r", "G"]))
    ms.append(Model("C3", "circulation c Re^Q, radius b Re^m", "circulation", ["c", "Q", "b", "m"], [[a_g, q_g, a_r, m_r]],
                    [(1e-2, -1, 0.5, -1), (1e5, 2, 30, 1)], p_G_powerr, ["G = c Re^Q", "r = b Re^m", "U = G/(G0 r)"], ["r", "G"],
                    note="the same family as D3 (G = G0 r U); fitted to G instead of to U"))
    ms.append(Model("K3", "closure with three parameters: G = a Re^p, U = r^q", "closure", ["a", "p", "q"], [[80, 0.13, 0.5], [50, 0.3, 1.0]],
                    [(1, -1, 0.0), (1e4, 2, 4)], p_closure3, ["G = a Re^p", "U = r^q", "G = G0 r U  =>  r^(1+q) = G/G0"], ["r", "U", "G"]))
    ms.append(Model("K4", "closure with four parameters: G = a Re^p, U = r^q Re^s", "closure", ["a", "p", "q", "s"],
                    [[80, 0.13, 0.3, 0.18], [50, 0.2, 1.0, 0.0]], [(1, -1, 0.0, -1), (1e4, 2, 4, 2)], p_closure4,
                    ["G = a Re^p", "U = r^q Re^s", "G = G0 r U  =>  r^(1+q) = G/(G0 Re^s)"], ["r", "U", "G"]))
    ms.append(Model("T6", "two tube sets: common radius b Re^m, a swirl power law for each set", "two sets", ["b", "m", "c1", "s1", "c2", "s2"],
                    [[a_r, m_r, a_u, s_u, a_u * 0.6, s_u]], [(0.5, -1, 1e-3, -1, 1e-3, -1), (30, 1, 50, 2, 50, 2)], p_twoset,
                    ["r = b Re^m", "U = c1 Re^s1 (intense tubes), c2 Re^s2 (whole tubes)"], ["r", "U"], info=True,
                    note="information only: two functions, the generality of one is lost; not considered for the selection"))
    return ms


# ---------------------------------------------------------------------------------------------------- fitting and scores
def residuals(model, p, obs):
    out = []
    for kind in model.kinds:
        d = obs[kind]
        if not len(d["re"]):
            continue
        pred = model.predict(d["re"], p, d["tube_set"])[kind]
        out.append(np.sqrt(d["w"]) * np.log(np.maximum(pred, 1e-300) / d["val"]))
    return np.concatenate(out)


def score(model, p, obs):
    """Scores of a parameter set against the data: weighted rms log residual and unweighted RMSE/mean (%) of r, U, G; combined."""
    out = {}
    for kind in ("r", "U", "G"):
        d = obs[kind]
        pred = model.predict(d["re"], p, d["tube_set"])[kind]
        lr = np.log(np.maximum(pred, 1e-300) / d["val"])
        out["rms_" + kind] = float(math.sqrt(np.sum(d["w"] * lr**2) / np.sum(d["w"])))
        out["rmse_" + kind] = float(100 * math.sqrt(np.mean((pred - d["val"]) ** 2)) / np.mean(d["val"]))
    out["combined"] = math.sqrt((out["rms_r"] ** 2 + out["rms_U"] ** 2) / 2)
    return out


def deviations(model, p, obs):
    """Mean deviation (model/data - 1) of each source, per quantity, and the number of points."""
    out = {}
    for kind in ("r", "U", "G"):
        d = obs[kind]
        pred = model.predict(d["re"], p, d["tube_set"])[kind]
        by = {}
        for src, ref, a, b in zip(d["src"], d["ref"], pred, d["val"]):
            by.setdefault((src, ref), []).append(a / b - 1)
        out[kind] = {k: (float(np.mean(v)), len(v)) for k, v in by.items()}
    return out


def fit(model, obs):
    """Fit one model. Returns dict: model, params, errors, cost, n, scores, budget at RE_CHECK, ok (the fit ran), message."""
    best = None
    for start in model.starts:
        lo, hi = model.bounds
        try:
            r = least_squares(lambda p: residuals(model, p, obs), start, bounds=(lo, hi), max_nfev=4000, x_scale="jac")
        except (ValueError, FloatingPointError):
            continue
        if best is None or r.cost < best.cost:
            best = r
    if best is None:
        return dict(model=model, ok=False, message="no start converged")
    p = best.x
    n = len(best.fun)
    J = best.jac
    dof = max(n - len(p), 1)
    try:
        cov = np.linalg.pinv(J.T @ J) * (2 * best.cost) / dof
        err = np.sqrt(np.abs(np.diag(cov)))
    except np.linalg.LinAlgError:
        err = np.full(len(p), np.nan)
    sc = score(model, p, obs)
    re = np.array(RE_CHECK, float)
    sets = np.array(["intense"] * len(re))
    pr = model.predict(re, p, sets)
    bud = budget(pr["r"], pr["U"])
    return dict(model=model, ok=True, params=p, errors=err, cost=float(best.cost), n=n, scores=sc, re_check=re, pred=pr, bud=bud,
                dev=deviations(model, p, obs), message="")


def legacy_n(rows, sources=("Ghira22", "DaSilva11", "Kida02", "Mouri04", "Mouri07")):
    """The earlier rescaling model on the values as calculated from the papers (no corrections): Re_c = c Re^k and the swirl at the true radius
    5 is U'(r'/5)^n, i.e. ln(5 U') = ln c + k ln Re - n ln(r'/5), fitted by weighted least squares (each source weight 1).
    Returns dict(c, k, n, errors, rms, n_points) or None."""
    sel = [x for x in rows if x["re"] is not None and x["r_raw"] and x["u_raw"] and x["src"] in sources]
    if len(sel) < 5:
        return None
    cnt = {}
    for x in sel:
        cnt[x["src"]] = cnt.get(x["src"], 0) + 1
    w = np.array([1.0 / cnt[x["src"]] for x in sel])
    w = w * len(w) / w.sum()
    y = np.log([5 * x["u_raw"] for x in sel])
    A = np.vstack([np.ones(len(sel)), np.log([x["re"] for x in sel]), -np.log([x["r_raw"] / 5 for x in sel])]).T
    cov0 = np.linalg.inv(A.T @ (w[:, None] * A))
    b = cov0 @ A.T @ (w * y)
    res = y - A @ b
    cov = cov0 * float(np.sum(w * res**2)) / (len(y) - 3)
    return dict(c=math.exp(b[0]), k=float(b[1]), n=float(b[2]), errors=np.sqrt(np.diag(cov)), rms=float(math.sqrt(np.mean(res**2))), n_points=len(sel))


def sensible(res):
    """Physically sensible: finite r and U, 0.01 < V_f < 0.5 for 100 <= Re_lambda <= 2000."""
    if not res.get("ok"):
        return False
    use = res["re_check"] >= 100
    vf = res["bud"]["vf"][use]
    r, U = res["pred"]["r"][use], res["pred"]["U"][use]
    return bool(np.all(np.isfinite(r)) and np.all(np.isfinite(U)) and np.all(r > 0) and np.all(U > 0) and np.all(np.isfinite(vf))
                and np.all(vf > 0.01) and np.all(vf < 0.5))


def select(results):
    """The simplest sensible model within TOLERANCE of the best combined score; returns (selected key, list of (key, reason))."""
    reasons = []
    eligible = []
    for res in results:
        m = res["model"]
        if not res.get("ok"):
            reasons.append((m.key, "fit failed"))
        elif m.info:
            reasons.append((m.key, "information only"))
        elif not sensible(res):
            reasons.append((m.key, "not physically sensible: V_f outside 0.01-0.5 for Re_lambda 100-2000"))
        else:
            eligible.append(res)
    if not eligible:
        return None, reasons
    best = min(r["scores"]["combined"] for r in eligible)
    near = [r for r in eligible if r["scores"]["combined"] <= TOLERANCE * best]
    pick = min(near, key=lambda r: (r["model"].nparam, r["scores"]["combined"]))
    for r in eligible:
        if r is pick:
            reasons.append((r["model"].key, "selected: fewest parameters (%d) within %.0f%% of the best combined score" % (r["model"].nparam, 100 * (TOLERANCE - 1))))
        elif r in near:
            reasons.append((r["model"].key, "within tolerance, more parameters"))
        else:
            reasons.append((r["model"].key, "combined score %.1f%% against the best %.1f%%" % (100 * r["scores"]["combined"], 100 * best)))
    return pick["model"].key, reasons
