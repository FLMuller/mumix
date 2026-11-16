"""belin_correctors_sassa.py  v01  The corrector of the method of Sassa and Makita (2005): events where dw/dt >= C rms(dw/dt), the mean trace of the events gives the radius (half the peak separation) and the peak velocity.
Method    chord_mouri.run on the tubes of the Belin fit (ground truth): gradient of the transverse velocity (increment over 0.5 eta), probe 1 eta, events above C standard deviations (C = 1.5 ... 3.5, their Fig. 2), mean trace: r = half the peak separation, V = the peak.
Corrector m_r = (mean r_max of the generated population) / r_peak,  m_U = (mean U_max of the population) / V_peak   (corrected = m x printed value).
Output    belin_correctors_sassa.json; the table is printed.
Usage     python belin_correctors_sassa.py [--n 20000]
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

KS = (1.5, 2.0, 2.5, 3.0, 3.5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--params", type=float, nargs=4, default=[7.29, 0.58, 2.58, 0.38])
    args = ap.parse_args()
    cfg = sf.config(np.log(np.array(args.params)))
    out = []
    for Rl in rn.RE_RANGE:
        specs = [("C=%g" % k, 0.5, k, False) for k in KS]
        res = cm.run(Rl, cfg, args.n, specs, 1.0)
        pop = res["population"]
        row = dict(Re_lambda=Rl, population_mean_r=pop["true_r"], population_mean_U=pop["true_U"])
        for name, _, _, _ in specs:
            q = res.get(name)
            row[name] = None if q is None else dict(R0=q["r_peak"], V0=q["v_peak"], m_r=pop["true_r"] / q["r_peak"], m_U=pop["true_U"] / q["v_peak"], events=q["count"])
        out.append(row)
        print(Rl, "pop r %.2f U %.1f | " % (pop["true_r"], pop["true_U"]) + " | ".join("%s: R0 %.1f V0 %.1f -> m_r %.2f m_U %.2f" % (n, row[n]["R0"], row[n]["V0"], row[n]["m_r"], row[n]["m_U"]) for n in ["C=%g" % k for k in KS] if row[n]), flush=True)
    json.dump(out, open(os.path.join(HERE, "belin_correctors_sassa.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
