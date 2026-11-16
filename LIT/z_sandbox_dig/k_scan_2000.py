"""k scan of the all-tube corrector at Re_lambda = 2000 (same set-up as belin_correctors_all.py, k in steps of 0.1)."""
import json, sys
import numpy as np
sys.path.insert(0, "C:/Users/Frans PREFLM/OneDrive - University of Leeds/code/Claude/mumix/LIT/analysis")
import chord_mouri as cm, chord_belin_sens_fit as sf, belin_range_numbers as rn
cfg = sf.config(np.log(np.array([7.29, 0.58, 2.58, 0.38])))
Rl = 2000
_, probe = rn.mouri_setup(Rl)
ks = [round(0.1 * i, 1) for i in range(1, 11)]
res = cm.run(Rl, cfg, 20000, [("k=%g" % k, 6.0, k, True) for k in ks], probe)
pop = res["population"]
rows = []
for k in ks:
    q = res.get("k=%g" % k)
    if q: rows.append(dict(k=k, r_read=q["R0"], U_read=q["V0"], m_r=pop["true_r"] / q["R0"], m_U=pop["true_U"] / q["V0"], events=q["count"]))
print("true r %.2f U %.2f" % (pop["true_r"], pop["true_U"]))
for r in rows: print("%.1f  r_read %.2f  U_read %.2f  m_r %.3f  m_U %.3f  events %d" % (r["k"], r["r_read"], r["U_read"], r["m_r"], r["m_U"], r["events"]))
json.dump(dict(pop=pop, rows=rows), open("k_scan_2000.json", "w"), indent=1)
