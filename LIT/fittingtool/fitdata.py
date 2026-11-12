"""fitdata.py  v01  Load the tube data of the fitting tool and apply the corrections.

    rows = load(csv_path, corr_path)         one dict per row of tubes.csv with the corrected values
    obs  = observations(rows)                 the data of each quantity as arrays: obs['r'], obs['U'], obs['G']

A row has: id, src, reference, group, tube_set, method, re (Re_lambda, None for a range or none), re_lo, re_hi, r_raw, u_raw, r, u (corrected),
g (Gamma/nu = 8.784 r u from the corrected values, None without a swirl), factor_r, factor_u, d_over_eta.

Corrections (data/corrections.json): used = raw / r_divisor (radius), raw * u_factor (swirl), per source.  Gamma/nu and Re_c = r u follow from
the corrected values.  A quantity of a source can be left out of the fits (key "excluded_quantities" of the corrections file: {source: {kind: reason}}, kind r, U or G:
the rows stay in the data and in the plots).  A quantity of each data point carries a weight: every (source, quantity) group has total weight 1 divided over its
rows, scaled so that the weights of a quantity average 1; a source with one row counts as much as a source with twenty.

Versions  M01 m01.v02 (2026-11-12): excluded_quantities (a quantity of a source left out of the fits).
          M01 m01.v01 (2026-11-11): first version.
"""
import csv
import json
import math

import numpy as np

__all__ = ["G0", "load", "observations", "BURGERS_X"]

EXCLUDED_QUANTITIES = {}       # source -> {kind: reason}: a quantity of a source left out of the fits (corrections.json, key "excluded_quantities"); set by load

BURGERS_X = 1.2564312086261697                       # the root of exp(x) - 2x - 1 = 0
G0 = 2 * math.pi / (1 - math.exp(-BURGERS_X))        # Gamma/nu = G0 Re_c = 8.784 r_max U_max / nu


def number(text):
    return float(text) if text not in ("", None) else None


def load(csv_path, corr_path=None, corr=None, excluded=None):
    """The rows of the data file with the corrections applied: those of corr (a dict source -> {r_divisor, u_factor}) if given, else those
    of the file corr_path, else none."""
    if corr_path and (corr is None or excluded is None):
        with open(corr_path, encoding="utf-8") as f:
            data = json.load(f)
        corr = data.get("corrections", {}) if corr is None else corr
        excluded = data.get("excluded", {}) if excluded is None else excluded
        global EXCLUDED_QUANTITIES
        EXCLUDED_QUANTITIES = data.get("excluded_quantities", {})
    corr = {} if corr is None else corr
    excluded = {} if excluded is None else excluded
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for rec in csv.DictReader(f):
            lo, hi = number(rec["re_lo"]), number(rec["re_hi"])
            r_raw, u_raw = number(rec["r_raw"]), number(rec["u_raw"])
            c = corr.get(rec["src"], {})
            fr = 1.0 / c.get("r_divisor", 1.0)
            fu = c.get("u_factor", 1.0)
            r = None if r_raw is None else r_raw * fr
            u = None if u_raw is None else u_raw * fu
            rows.append(dict(id=int(rec["id"]), src=rec["src"], reference=rec["reference"], group=rec["group"], tube_set=rec["tube_set"],
                             method=rec["method"], re_lo=lo, re_hi=hi, re=(lo if lo is not None and lo == hi else None),
                             r_raw=r_raw, u_raw=u_raw, r=r, u=u, factor_r=fr, factor_u=fu,
                             g=(G0 * r * u if r is not None and u is not None else None), d_over_eta=number(rec["d_over_eta"]),
                             gamma_listed=number(rec["gamma_listed"]), excluded=rec["src"] in excluded))
    return rows


def observations(rows, exclude=()):
    """Data arrays by quantity for the rows with a single Re_lambda: dict kind -> dict(re, val, w, src, group, tube_set, ref, id).
    kind r is r_max/eta, U is U_max/U_eta, G is Gamma/nu = 8.784 r U.  Sources named in exclude, and rows flagged excluded by the corrections file (key "excluded"), are left out."""
    out = {}
    for kind, key in (("r", "r"), ("U", "u"), ("G", "g")):
        sel = [x for x in rows if x["re"] is not None and x[key] is not None and x["src"] not in exclude and not x["excluded"]
               and kind not in EXCLUDED_QUANTITIES.get(x["src"], {})]
        count = {}
        for x in sel:
            count[x["src"]] = count.get(x["src"], 0) + 1
        w = np.array([1.0 / count[x["src"]] for x in sel])
        if len(w):
            w = w * len(w) / w.sum()
        out[kind] = dict(re=np.array([x["re"] for x in sel]), val=np.array([x[key] for x in sel]), w=w,
                         src=[x["src"] for x in sel], group=[x["group"] for x in sel], tube_set=[x["tube_set"] for x in sel],
                         ref=[x["reference"] for x in sel], id=[x["id"] for x in sel])
    return out
