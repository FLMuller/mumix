"""belin_correctors.py  v01  The multiplier that makes each observed distribution of the model self-similar to the real (generated) one: the corrector to apply to the data of each probe and method.
Observed  Belin's wire, events read: r (half the extrema spacing), U with his published rule dS / (2 x 0.14), and the raw reading dS / 2; Mouri's crossed wire: the 1% and 0.1% classes, r and U per event (belin_range_numbers.py, window +-10 R).
Multiplier m  the factor that, applied to the observed values, brings their distribution closest to the real distribution (the generated population, area 1): (a) matching the means, (b) minimum L1 distance between the two pdfs (the shape match), (c) matching the modes.
Use       corrected value = m x observed value.  For Belin's published U: m_published = m_raw x 0.14, m_raw = 1 / sin alpha* (the constant of belin_sin_alpha_equiv.py).
Output    belin_correctors.json; belin_correctors.png (m against Re_lambda); belin_correctors_dists.png (the corrected curves against the real one, Re_lambda 255 and 659).
Usage     python belin_correctors.py [--n 40000]
Versions  M01 m01.v01 (2026-11-13): first version.
"""
import argparse
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chord_belin_sens as cs         # noqa: E402
import chord_belin_sens_fit as sf     # noqa: E402
import belin_range_numbers as rn      # noqa: E402

RE_RANGE = (100, 150, 255, 400, 659, 1000, 1500, 2000)
EDGES = {"r": np.linspace(0, 60, 241), "U": np.linspace(0, 200, 401)}
GRID = np.exp(np.linspace(np.log(0.05), np.log(6.0), 400))


def pdf(v, w, edges):
    h = np.histogram(v, edges, weights=w)[0].astype(float)
    return h / max(h.sum() * (edges[1] - edges[0]), 1e-30)


def mode(v, w, edges):
    h = np.histogram(v, edges, weights=w)[0]
    k = int(np.argmax(h))
    return 0.5 * (edges[k] + edges[k + 1])


def multipliers(obs, w, true, kind):
    """The multipliers of observed values obs (weights w) that match the real values true (all tubes, equal weights)."""
    e = EDGES[kind]
    ref = pdf(true, np.ones_like(true), e)
    cost = [np.sum(np.abs(pdf(obs * m, w, e) - ref)) for m in GRID]
    return dict(mean=float(np.mean(true) / (np.sum(obs * w) / np.sum(w))), shape=float(GRID[int(np.argmin(cost))]),
                mode=float(mode(true, np.ones_like(true), e) / mode(obs, w, e)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40000)
    ap.add_argument("--params", type=float, nargs=4, default=[7.29, 0.58, 2.58, 0.38])
    args = ap.parse_args()
    cfg = sf.config(np.log(np.array(args.params)))
    out, demo = [], {}
    for Rl in RE_RANGE:
        res = cs.run(Rl, cfg, args.n, 11)
        ev = rn.mouri_events(Rl, cfg, args.n)
        w, rd = res["w"], res["rd"]
        c1, c01 = ev["peak"] >= rn.K1, ev["peak"] >= rn.K01
        curves = {"r": {"Belin's wire": (res["r_read"][rd], w[rd]), "Mouri 1%": (ev["r_obs"][c1], ev["w"][c1]), "Mouri 0.1%": (ev["r_obs"][c01], ev["w"][c01])},
                  "U": {"Belin's wire, published rule dS/(2 x 0.14)": (res["amp"][rd] / cs.SIN_BELIN, w[rd]), "Belin's wire, raw dS/2": (res["amp"][rd], w[rd]),
                        "Mouri 1%": (ev["u_obs"][c1], ev["w"][c1]), "Mouri 0.1%": (ev["u_obs"][c01], ev["w"][c01])}}
        truth = {"r": res["r"], "U": res["umax"]}
        row = dict(Re_lambda=Rl)
        for kind in ("r", "U"):
            row[kind] = {name: multipliers(v, wt, truth[kind], kind) for name, (v, wt) in curves[kind].items()}
        out.append(row)
        demo[Rl] = dict(curves=curves, truth=truth, mult=row)
        print(Rl, {k: {n: round(m["shape"], 3) for n, m in row[k].items()} for k in ("r", "U")}, flush=True)
    json.dump(out, open(os.path.join(HERE, "belin_correctors.json"), "w"), indent=1)
    colours = {"Belin's wire": "tab:red", "Belin's wire, published rule dS/(2 x 0.14)": "tab:red", "Belin's wire, raw dS/2": "tab:brown", "Mouri 1%": "tab:blue", "Mouri 0.1%": "tab:green"}
    fig, ax = plt.subplots(1, 2, figsize=(13, 5))
    for col, kind in enumerate(("r", "U")):
        a = ax[col]
        for name in out[0][kind]:
            a.plot(RE_RANGE, [r[kind][name]["shape"] for r in out], "o-", color=colours[name], label=name + ": shape match")
            a.plot(RE_RANGE, [r[kind][name]["mean"] for r in out], "x:", color=colours[name], label=name + ": mean match")
        a.axvspan(100, 718, color="0.93", zorder=0)
        a.set_xscale("log")
        if kind == "U":
            a.set_yscale("log")
        a.set_xlabel("Re_lambda")
        a.set_ylabel("multiplier on the observed %s" % ("r_max" if kind == "r" else "U_max"))
        a.legend(fontsize=6)
        a.set_title("corrector for %s (corrected = multiplier x observed)" % ("r_max" if kind == "r" else "U_max"), fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_correctors.png"), dpi=90)
    fig, ax = plt.subplots(2, 2, figsize=(13, 9))
    for row, Rl in enumerate((255, 659)):
        for col, kind in enumerate(("r", "U")):
            b = ax[row, col]
            e = EDGES[kind]
            mid = 0.5 * (e[1:] + e[:-1])
            d = demo[Rl]
            b.plot(mid, pdf(d["truth"][kind], np.ones_like(d["truth"][kind]), e), "k", lw=2.4, label="real distribution")
            for name, (v, wt) in d["curves"][kind].items():
                m = d["mult"][kind][name]["shape"]
                b.plot(mid, pdf(v * m, wt, e), color=colours[name], lw=1.8, label="%s x %.2f" % (name, m))
            b.set_xlim(0, 30 if kind == "r" else 80)
            b.set_xlabel("r_max / eta" if kind == "r" else "U_max / U_eta")
            b.set_ylabel("pdf (area 1)")
            b.set_title("Re_lambda %d: observed distributions after the shape-match multiplier" % Rl, fontsize=9)
            b.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "belin_correctors_dists.png"), dpi=90)


if __name__ == "__main__":
    main()
