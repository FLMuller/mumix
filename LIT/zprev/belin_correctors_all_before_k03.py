"""belin_correctors_all.py  v01  The missing column of belin_correctors.py: the corrector of the all-tube method of Mouri and Hori (2009), which gives one mean profile (R0, V0) and no distribution.
Method    chord_mouri.run on the tubes of the Belin fit (ground truth): increment over 6 eta, probe 1 mm (Mouri's table, log Re_lambda interpolation), events above a low threshold k (0.25, 0.5, 1 standard deviations of the increment; the model has no background, so
          the threshold takes its place), mean profile fitted by the Burgers vortex: R0, V0.
Corrector m_r = (mean r_max of the generated population) / R0,  m_U = (mean U_max of the population) / V0   (corrected = m x printed value).
Output    belin_correctors_all.json; the table is printed.
Usage     python belin_correctors_all.py [--n 20000]
Versions  M01 m01.v01 (2026-11-13): first version.
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chord_mouri as cm              # noqa: E402
import chord_belin_sens_fit as sf     # noqa: E402
import belin_range_numbers as rn      # noqa: E402

KS = (0.25, 0.5, 1.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--params", type=float, nargs=4, default=[7.29, 0.58, 2.58, 0.38])
    args = ap.parse_args()
    cfg = sf.config(np.log(np.array(args.params)))
    out = []
    for Rl in rn.RE_RANGE:
        _, probe = rn.mouri_setup(Rl)
        specs = [("k=%g" % k, 6.0, k, True) for k in KS]
        res = cm.run(Rl, cfg, args.n, specs, probe)
        pop = res["population"]
        row = dict(Re_lambda=Rl, population_mean_r=pop["true_r"], population_mean_U=pop["true_U"])
        for name, _, _, _ in specs:
            q = res.get(name)
            row[name] = None if q is None else dict(R0=q["R0"], V0=q["V0"], m_r=pop["true_r"] / q["R0"], m_U=pop["true_U"] / q["V0"], events=q["count"])
        out.append(row)
        print(Rl, "pop r %.2f U %.1f | " % (pop["true_r"], pop["true_U"]) + " | ".join("%s: R0 %.1f V0 %.1f -> m_r %.2f m_U %.2f" % (n, row[n]["R0"], row[n]["V0"], row[n]["m_r"], row[n]["m_U"]) for n in ("k=0.25", "k=0.5", "k=1") if row[n]), flush=True)
    json.dump(out, open(os.path.join(HERE, "belin_correctors_all.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
