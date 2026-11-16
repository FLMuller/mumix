"""belin_sin_alpha_equiv.py  v01  The constant sin alpha that turns the wire amplitude dS / 2 of the events read into the true U_max distribution, in the model of the Belin fit.
Three matches (all weighted by the footprint): the mean, the mode, and the best overall match of the pdf (minimum L1 distance); against (a) the true U_max of the events that were read, (b) the whole generated population.
Usage  python belin_sin_alpha_equiv.py [--n 40000]   prints and writes belin_sin_alpha_equiv.json
Versions M01 m01.v01 (2026-11-13): first version.
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chord_belin_sens as cs         # noqa: E402
import chord_belin_sens_fit as sf     # noqa: E402


def pdf(v, w, edges):
    h = np.histogram(v, edges, weights=w)[0].astype(float)
    return h / (h.sum() * (edges[1] - edges[0]))


def best(amp, w, target, tw, edges):
    grid = np.linspace(0.05, 1.0, 191)
    ref = pdf(target, tw, edges)
    cost = [np.sum(np.abs(pdf(amp / s, w, edges) - ref)) for s in grid]
    return float(grid[int(np.argmin(cost))])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40000)
    args = ap.parse_args()
    cfg = sf.config(np.log(np.array([7.29, 0.58, 2.58, 0.38])))
    out = []
    edges = np.linspace(0, 120, 241)
    mid = 0.5 * (edges[1:] + edges[:-1])
    for Rl in (151, 255, 359, 507, 659, 718):
        res = cs.run(Rl, cfg, args.n, 11)
        w, rd = res["w"], res["rd"]
        amp = res["amp"][rd]
        wr = w[rd]
        true_ev, true_pop = res["umax"][rd], res["umax"]
        mean_amp = np.sum(amp * wr) / wr.sum()
        row = dict(Re_lambda=Rl, mean_abs_sin_alpha=float(np.sum(np.abs(res["sin_w"][rd]) * wr) / wr.sum()),
                   mean_match_events=float(mean_amp / (np.sum(true_ev * wr) / wr.sum())), mean_match_population=float(mean_amp / np.mean(true_pop)),
                   mode_match_events=float(mid[np.argmax(pdf(amp, wr, edges))] / mid[np.argmax(pdf(true_ev, wr, edges))]),
                   mode_match_population=float(mid[np.argmax(pdf(amp, wr, edges))] / mid[np.argmax(pdf(true_pop, np.ones_like(true_pop), edges))]),
                   pdf_match_events=best(amp, wr, true_ev, wr, edges), pdf_match_population=best(amp, wr, true_pop, np.ones_like(true_pop), edges))
        out.append(row)
        print(Rl, {k: round(v, 3) for k, v in row.items() if k != "Re_lambda"}, flush=True)
    json.dump(out, open(os.path.join(HERE, "belin_sin_alpha_equiv.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
