"""belin_correctors_kscan.py  v01  The corrector of the all-tube method of Mouri and Hori (2009) as a function of the threshold k, in steps of 0.1, at every Re_lambda of the corrector tables.
Method    As belin_correctors_all.py (chord_mouri.run on the tubes of the Belin fit as the ground truth: increment over 6 eta, probe 1 mm, events above k standard deviations of the increment, mean profile fitted by the Burgers vortex), with k = 0.1, 0.2, ..., 1.0 in one run; the
          lowest k sets the footprint of the sampled tubes, so the multipliers differ from those of belin_correctors_all.py (whose lowest k is 0.2) by Monte Carlo noise only (under 1%).
Output    belin_correctors_kscan.json: per Re_lambda and k the radius and swirl read by the method (r_obs, U_obs), the true means of the population, and the multipliers m_r = true r / r_obs, m_U = true U / U_obs (corrected = m x printed value).
Usage     python belin_correctors_kscan.py [--n 20000]
Versions  M01 m01.v01 (2026-11-16): first version.
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

KS = tuple(round(0.1 * i, 1) for i in range(1, 11))


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
        row = dict(Re_lambda=Rl, true_r=pop["true_r"], true_U=pop["true_U"], k={})
        for k in KS:
            q = res.get("k=%g" % k)
            if q is not None:
                row["k"]["%g" % k] = dict(r_obs=q["R0"], U_obs=q["V0"], m_r=pop["true_r"] / q["R0"], m_U=pop["true_U"] / q["V0"], events=q["count"])
        out.append(row)
        print(Rl, "true r %.2f U %.2f" % (pop["true_r"], pop["true_U"]), flush=True)
    with open(os.path.join(HERE, "belin_correctors_kscan.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
