"""chord_belin_volume_fit.py  v01  Fit the two input lognormals of the volume model (chord_belin_volume.py) until the read distributions match Belin et al. (1996), in stages of growing size.
Inputs  (1) r_max: lognormal, median m_r (eta), ln-width s_r;  (2) x = Re_f / Re_lambda^(1/2): lognormal, median m_x, ln-width s_x.  The tubes have the length L = 42 eta, volume fraction 0.2, no hand cap on the impact parameter.
Outlets as chord_belin_fit_inputs.py: the radius read against Fig. 5 (r_max below 30 eta), the product read x_read = amp R_m / Re_lambda^(1/2) against Fig. 6 (0-40), at Re_lambda 659 and 2850;
        misfit = sum of the rms differences relative to the peak of the target.
Method  Nelder-Mead on (ln m_r, ln s_r, ln m_x, ln s_x); common random numbers; the stages (--stages, events kept and read per Re_lambda) run in turn and each starts from the best of the one before.
Usage:  python chord_belin_volume_fit.py [--stages 5000 10000 50000] [--start 4.44 0.55 14.01 0.75]      prints every step; the figure command of the best is printed at the end

Versions  M01 m01.v01 (2026-11-13): first version.
"""
import argparse
import math
import os
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
from scipy.optimize import minimize

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import belin_gamma_pdf as bg          # noqa: E402
import chord_belin_fit_inputs as fi   # noqa: E402
import chord_belin_volume as cbv      # noqa: E402


def outlets(params, target, length, vf):
    m_r, s_r, m_x, s_x = params
    args = SimpleNamespace(target=target, length=length, vf=vf, rmedian=m_r, sharp=s_r)
    out = []
    for row, Rl in enumerate((659, 2850)):
        res = cbv.simulate(Rl, args, math.log(m_x), s_x, 7 + row)
        rd = res["read"]
        x_read = res["amp"][rd] * (2 * res["r_read"][rd] / 3.17) / math.sqrt(Rl)
        h5 = np.histogram(res["r_read"][rd], fi.R5)[0].astype(float)
        h6 = np.histogram(x_read, fi.X6)[0].astype(float)
        out.append((h5 / (h5.sum() * 0.5), h6 / (h6.sum() * 2.0)))
    return out


def misfit(params, target, length, vf, t5, t6, ok):
    total = 0.0
    for h5, h6 in outlets(params, target, length, vf):
        total += math.sqrt(np.mean((h5 - t5) ** 2)) / t5.max() + math.sqrt(np.mean((h6 - t6)[ok] ** 2)) / np.nanmax(t6)
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages", type=int, nargs="+", default=[5000, 10000, 50000])
    ap.add_argument("--maxfev", type=int, nargs="+", default=[60, 40, 25], help="function evaluations per stage")
    ap.add_argument("--length", type=float, default=42.0)
    ap.add_argument("--vf", type=float, default=0.2)
    ap.add_argument("--start", type=float, nargs=4, default=[4.44, 0.55, 14.01, 0.75], metavar=("R_MEDIAN", "R_WIDTH", "X_MEDIAN", "X_WIDTH"))
    args = ap.parse_args()
    t5, t6, ok = fi.targets()
    mu0, s0, _ = bg.lognormal_fit()
    best = np.log(np.array(args.start))
    for stage, (target, maxfev) in enumerate(zip(args.stages, args.maxfev)):
        def objective(v):
            value = misfit(tuple(math.exp(u) for u in v), target, args.length, args.vf, t5, t6, ok)
            print("  [%d] r median %.2f ln-width %.2f | x median %.2f ln-width %.2f | misfit %.4f" % (target, *(math.exp(u) for u in v), value), flush=True)
            return value
        step = (0.3, 0.3, 0.2, 0.2) if stage == 0 else (0.1, 0.1, 0.07, 0.07)
        simplex = np.array([best] + [best + np.eye(4)[k] * step[k] for k in range(4)])
        res = minimize(objective, best, method="Nelder-Mead", options={"maxfev": maxfev, "xatol": 0.02, "fatol": 0.003, "initial_simplex": simplex})
        best = res.x
        m_r, s_r, m_x, s_x = (math.exp(v) for v in best)
        print("best after %d events: r_max median %.2f eta, ln-width %.2f; x median %.2f, ln-width %.2f; misfit %.4f" % (target, m_r, s_r, m_x, s_x, res.fun), flush=True)
        subprocess.run([sys.executable, os.path.join(HERE, "chord_belin_volume.py"), "--target", str(target), "--rmedian", "%.3f" % m_r, "--sharp", "%.3f" % s_r, "--median", "%.4f" % (m_x / math.exp(mu0)),
                        "--narrow", "%.4f" % (s_x / s0), "--tag", "_fit%d" % target, "--length", str(args.length), "--vf", str(args.vf)], check=True, stdout=subprocess.DEVNULL)
        print("figure written: chord_belin_volume_fit%d.png" % target, flush=True)               # the gate of the stage: its pdfs
    print("figure: python chord_belin_volume.py --target %d --rmedian %.3f --sharp %.3f --median %.4f --narrow %.4f" % (args.stages[-1], m_r, s_r, m_x / math.exp(mu0), s_x / s0))


if __name__ == "__main__":
    main()
