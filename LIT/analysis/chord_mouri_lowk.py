"""chord_mouri_lowk.py  v01  The all-tube method of Mouri and Hori (2009) at low thresholds, on DNS-like tubes (chord_mouri.py): which threshold of the increment over 6 eta brings the model to R0/eta and V0/u_K of their Table 2, and what correction that implies.
Output  chord_mouri_lowk.json: per Re_lambda (332, 719, 1098, 1934) and threshold k = 0.25, 0.5, 1 (in standard deviations of the increment): R0, V0 of the Burgers fit, the true radius and swirl of the same events, the paper's values.
Usage:  python chord_mouri_lowk.py [--n 6000]
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=6000)
    ap.add_argument("--params", type=float, nargs=4, default=[5.0, 0.3, 1.0, 0.4], help="r_median, r_sigma, U scale, U sigma")
    ap.add_argument("--tag", default="", help="suffix of the json name")
    ap.add_argument("--ks", type=float, nargs="+", default=[0.25, 0.5, 1.0])
    args = ap.parse_args()
    cfg = sf.config(np.log(np.array(args.params)))
    out = []
    for Rl, eta_cm, dxs_cm, dx0, k01, k1, r_all, v_all, r01, v01, r1, v1 in cm.MOURI:
        specs = [("k=%g" % k, dx0, k, True) for k in args.ks]
        res = cm.run(Rl, cfg, args.n, specs, 0.1 / eta_cm)
        res.update(Re_lambda=Rl, paper=dict(r_all=r_all, v_all=v_all))
        out.append(res)
        for name, _, _, _ in specs:
            q = res[name]
            print("Re_lambda %d %s: R0 %.2f (paper %.2f)  V0/uK %.2f (paper %.2f) | true r %.2f U %.1f | radius factor %.2f swirl factor %.2f" % (Rl, name, q["R0"], r_all, q["V0"], v_all, q["true_r"], q["true_U"], q["R0"] / q["true_r"], q["true_U"] / q["V0"]), flush=True)
    with open(os.path.join(HERE, "chord_mouri_lowk%s.json" % args.tag), "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
