import math, sys
sys.path.insert(0, r"C:\Users\Frans PREFLM\OneDrive - University of Leeds\code\Claude\mumix\LIT\analysis")
import fit_lfl as L, fit4 as F4
x, G = L.x, L.G
# Mouri 2007 Table II (0.1% and 1% thresholds), Mouri 2004 Table I (1%), Da Silva 2011
Re_duct = [719, 1098, 1416, 1693, 1934]; Re_bl = [332, 488, 716, 945, 1080, 1304]
M07 = {
 "0.1%": dict(R0=[5.21, 5.64, 5.47, 5.87, 6.20, 5.18, 5.24, 5.56, 5.97, 5.66, 6.15],
              Re0=[45.2, 56.4, 61.8, 75.1, 86.8, 39.4, 43.9, 53.0, 63.3, 66.2, 78.7]),
 "1%":   dict(R0=[6.50, 6.61, 6.92, 6.76, 7.03, 6.53, 6.44, 6.92, 7.38, 7.14, 7.19],
              Re0=[39.7, 45.2, 52.1, 56.9, 64.5, 36.6, 38.5, 46.0, 53.7, 55.9, 61.3])}
Re07 = Re_duct + Re_bl
M04 = dict(Re=[295, 430, 655, 861, 1054, 1258], R0=[6.08, 6.04, 6.28, 7.14, 6.98, 7.37], Re0=[32, 34, 40, 51, 54, 62])
def m3(Rl): return L.tube(Rl, 88.453, 0.1237, 0.8726)
def m4(Rl): return F4.tube(Rl, 76.80, 0.1453, 0.2999, 0.1768)
def mu(Rl, b=5.384, s=-0.0325, k=0.919):
    beta = b * Rl**s; U = k * (Rl / math.sqrt(15))**0.5
    return dict(beta=beta, Rec=beta * U)
print("Mouri 2007, 0.1% threshold: model/lit for r_max (=R0) and Re_c (=Re0)")
for Rl, r0, re0 in zip(Re07, M07["0.1%"]["R0"], M07["0.1%"]["Re0"]):
    print("  Re_l %4d  R0 %.2f Re0 %.1f | 3p: %.2f %.2f | 4p: %.2f %.2f | u' law: %.2f %.2f" % (Rl, r0, re0, m3(Rl)["beta"] / r0, m3(Rl)["Rec"] / re0, m4(Rl)["beta"] / r0, m4(Rl)["Rec"] / re0, mu(Rl)["beta"] / r0, mu(Rl)["Rec"] / re0))
print("Mouri 2004 (1% threshold)")
for Rl, r0, re0 in zip(M04["Re"], M04["R0"], M04["Re0"]):
    print("  Re_l %4d  R0 %.2f Re0 %d | 3p: %.2f %.2f | 4p: %.2f %.2f | u' law: %.2f %.2f" % (Rl, r0, re0, m3(Rl)["beta"] / r0, m3(Rl)["Rec"] / re0, m4(Rl)["beta"] / r0, m4(Rl)["Rec"] / re0, mu(Rl)["beta"] / r0, mu(Rl)["Rec"] / re0))
import numpy as np
for name, f in (("3p", m3), ("4p", m4)):
    for thr in ("0.1%", "1%"):
        rr = [math.log(f(R)["Rec"] / v) for R, v in zip(Re07, M07[thr]["Re0"])]
        print(name, thr, "mean ln(model/lit) of Re_c = %+.2f -> factor %.2f" % (np.mean(rr), math.exp(np.mean(rr))))
