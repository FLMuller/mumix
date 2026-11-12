"""plot_pairs.py  v01  Pair plots of the tube parameters with the points marked intense or whole.

Reads the model-input rows (build_data_sections.tube_items(): every source row of the section 7 table, completed with the
Burgers relations) and draws, for each pair of the parameters
    Re_lambda, r_max/eta, U_max/U_eta, Re_c, Gamma/nu, gamma/gamma_eta (= 4x/(r_max/eta)^2),
one scatter panel, red for intense tubes and blue for whole tubes, marker by source family.  A second figure plots
U_max/U_eta against r_max/eta with lines of constant Re_c and the points coloured by Re_lambda.
A third figure, gamma_dimensionless.png, shows the dimensionless circulation Gamma/(r_max U_max) (8.78 for a Burgers vortex,
6.28 for the circulation inside r_max) for the two sources that list Gamma, Ghira and Kida, and Gamma/nu against gamma/gamma_eta.
Usage:  python plot_pairs.py      (writes the three png files next to this file)

v01: pair plots and swirl against radius.  v02: gamma_dimensionless.png.
"""
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_data_sections as bds
import sourcedata as sd

HERE = os.path.dirname(os.path.abspath(__file__))
SET = {s["key"]: s["tubes"] for s in sd.SOURCES}
COLOUR = {"intense": "#c0392b", "whole": "#2471a3"}
MARKER = {"Ghira22": "o", "Ghira25": "o", "Mouri09": "s", "Mouri07": "s", "Mouri04": "s", "Mouri03": "s"}
VARS = [  # label, key, log axis
    (r"$Re_\lambda$", "Re", True), (r"$r_{max}/\eta$", "beta", False), (r"$U_{max}/U_\eta$", "U", False),
    (r"$Re_c$", "rec", True), (r"$\Gamma/\nu$", "RGn", True), (r"$\gamma/\gamma_\eta$", "gam", False)]


def rows():
    out = []
    for it in bds.tube_items():
        if not isinstance(it["Re"], (int, float)):
            continue
        it = dict(it)
        it["set"] = SET[it["src"]]
        it["RGn"] = it["RG"]
        it["gam"] = 4 * sd.x / it["beta"] ** 2 if it["beta"] else None
        out.append(it)
    return out


def gamma_figure(data):
    """Left: Gamma/(r_max U_max) against Re_lambda for rows where Gamma is listed by the source (not computed from Re_c);
    right: Gamma/nu against gamma/gamma_eta for all rows, the listed-Gamma rows with a black edge."""
    listed = ("Ghira22", "Kida02")
    fig, (axa, axb) = plt.subplots(1, 2, figsize=(13, 5.5))
    for src, mk in (("Ghira22", "o"), ("Kida02", "D")):
        pts = [it for it in data if it["src"] == src and it["beta"] and it["U"]]
        axa.scatter([it["Re"] for it in pts], [it["RG"] / (it["beta"] * it["U"]) for it in pts], marker=mk, s=50,
                    c=COLOUR[SET[src]], label="%s (%s)" % (src, SET[src]))
    axa.axhline(sd.G, c="k", lw=1)
    axa.text(95, sd.G + 0.1, "Burgers, total circulation: 2pi/K_B = 8.78", fontsize=8)
    axa.axhline(2 * math.pi, c="0.4", lw=1, ls="--")
    axa.text(95, 2 * math.pi + 0.1, "Burgers, inside r_max: 2pi = 6.28", fontsize=8)
    axa.set_xscale("log")
    axa.set_ylim(3, 10)
    axa.set_xlabel(r"$Re_\lambda$")
    axa.set_ylabel(r"$\Gamma/(r_{max}U_{max})$")
    axa.set_title("Listed circulation in units of r_max U_max")
    axa.legend(loc="lower right")
    axa.grid(alpha=0.25)
    for it in data:
        if it["gam"] is None or it["RGn"] is None:
            continue
        axb.scatter(it["gam"], it["RGn"], s=34, marker="o", c=COLOUR[it["set"]], alpha=0.75,
                    edgecolors="k" if it["src"] in listed else "none", linewidths=1.1)
    axb.set_yscale("log")
    axb.set_xlabel(r"$\gamma/\gamma_\eta = 4x/(r_{max}/\eta)^2$")
    axb.set_ylabel(r"$\Gamma/\nu$")
    axb.set_title("Big gamma against small gamma (black edge: Gamma listed by source)")
    axb.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "gamma_dimensionless.png"), dpi=115)


def product_figure(data):
    """(Gamma/nu)(gamma/gamma_eta) against Omega/gamma_eta with Omega = U_max/(2 pi r_max).  For a Burgers vortex the product
    is 4 pi omega_0/gamma_eta = 8.78 * 4x * U/beta = 2 pi * 8.78 * 4x * Omega/gamma_eta, a straight line through the origin.
    Every row whose Gamma is computed from Re_c lies on that line by construction.  The two sources that list Gamma (Ghira,
    Kida) lie on lines of the same slope times a factor f (0.51 and 0.67); the computed rows are rescaled by the equal-source
    geometric mean f of the two, so that the predicted and the provided values correspond."""
    listed = ("Ghira22", "Kida02")
    line = 2 * math.pi * sd.G * 4 * sd.x
    omega = lambda it: it["U"] / (2 * math.pi * it["beta"])
    ratio = {src: [it["RGn"] * it["gam"] / (line * omega(it)) for it in data if it["src"] == src and it["beta"] and it["U"]]
             for src in listed}
    geo = lambda v: math.exp(sum(math.log(x) for x in v) / len(v))
    fac = {src: geo(v) for src, v in ratio.items()}
    adopted = math.sqrt(fac["Ghira22"] * fac["Kida02"])
    fig, ax = plt.subplots(figsize=(8.5, 6.5))
    xs = [0.04, 0.5]
    ax.plot(xs, [line * x for x in xs], c="0.7", lw=1, ls=":", label=r"Burgers, as computed: $P=%.0f\,\Omega/\gamma_\eta$" % line)
    ax.plot(xs, [adopted * line * x for x in xs], c="k", lw=1.4, label="adapted, f=%.2f (equal-source mean)" % adopted)
    ax.plot(xs, [fac["Ghira22"] * line * x for x in xs], c=COLOUR["intense"], lw=0.8, ls="--", label="Ghira alone, f=%.2f" % fac["Ghira22"])
    ax.plot(xs, [fac["Kida02"] * line * x for x in xs], c=COLOUR["whole"], lw=0.8, ls="--", label="Kida alone, f=%.2f" % fac["Kida02"])
    for ts in ("whole", "intense"):
        for src_listed, mk, size, scale in ((False, "o", 28, adopted), (True, "D", 60, 1.0)):
            pts = [(omega(it), it["RGn"] * it["gam"] * scale) for it in data
                   if it["set"] == ts and it["beta"] and it["U"] and it["RGn"] is not None and ((it["src"] in listed) == src_listed)]
            if pts:
                ax.scatter(*zip(*pts), marker=mk, s=size, c=COLOUR[ts], alpha=0.8, edgecolors="k" if src_listed else "none",
                           label="%s, %s" % (ts, "Gamma listed by source" if src_listed else "computed from Re_c, times f"))
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"$\Omega/\gamma_\eta=U_{max}/(2\pi\,r_{max}\gamma_\eta)$")
    ax.set_ylabel(r"$P=(\Gamma/\nu)(\gamma/\gamma_\eta)$")
    ax.set_title("Big gamma times small gamma against core rotation frequency, predicted rescaled to the listed values", fontsize=9)
    ax.grid(alpha=0.25, which="both")
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "product_vs_omega.png"), dpi=120)
    print("f Ghira %.3f, Kida %.3f, adopted %.3f" % (fac["Ghira22"], fac["Kida02"], adopted))


def main():
    data = rows()
    gamma_figure(data)
    product_figure(data)
    n = len(VARS)
    fig, axes = plt.subplots(n - 1, n - 1, figsize=(15, 15))
    for r in range(n - 1):
        for c in range(n - 1):
            ax = axes[r][c]
            if c > r:
                ax.axis("off")
                continue
            xl, xk, xlog = VARS[c]
            yl, yk, ylog = VARS[r + 1]
            for ts in ("whole", "intense"):
                for fam, mk in (("DNS/other", "^"), ("Ghira", "o"), ("Mouri", "s")):
                    pts = [(it[xk], it[yk]) for it in data if it["set"] == ts and it[xk] is not None and it[yk] is not None
                           and (("Ghira" in it["src"] and fam == "Ghira") or ("Mouri" in it["src"] and fam == "Mouri")
                                or ("Ghira" not in it["src"] and "Mouri" not in it["src"] and fam == "DNS/other"))]
                    if pts:
                        ax.scatter(*zip(*pts), s=22, marker=mk, c=COLOUR[ts], alpha=0.75, edgecolors="none",
                                   label="%s, %s" % (ts, fam))
            if xlog:
                ax.set_xscale("log")
            if ylog:
                ax.set_yscale("log")
            if r == n - 2:
                ax.set_xlabel(xl)
            if c == 0:
                ax.set_ylabel(yl)
            ax.grid(alpha=0.25)
    h, l = axes[0][0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper right", bbox_to_anchor=(0.97, 0.93), fontsize=11, title="red intense, blue whole")
    fig.suptitle("Tube parameters: intense (red) and whole (blue); marker: Ghira o, Mouri s, other triangle", y=0.995)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "pairs_intense_whole.png"), dpi=110)

    fig2, ax = plt.subplots(figsize=(8.5, 6.5))
    for rc in (15, 20, 30, 40, 60, 80, 100):
        xs = [3.5 + 0.1 * i for i in range(0, 80)]
        ax.plot(xs, [rc / x for x in xs], c="0.7", lw=0.8)
        ax.text(10.9, rc / 10.9, "Re_c=%d" % rc, fontsize=7, color="0.45", va="center")
    for ts in ("whole", "intense"):
        pts = [it for it in data if it["set"] == ts and it["beta"] and it["U"]]
        sc = ax.scatter([it["beta"] for it in pts], [it["U"] for it in pts], c=[math.log10(it["Re"]) for it in pts],
                        cmap="viridis", vmin=1.5, vmax=3.4, s=40, marker="o" if ts == "intense" else "D",
                        edgecolors=COLOUR[ts], linewidths=1.6, label=ts)
    cb = fig2.colorbar(sc, ax=ax)
    cb.set_label(r"$\log_{10} Re_\lambda$")
    ax.set_xlabel(r"$r_{max}/\eta$")
    ax.set_ylabel(r"$U_{max}/U_\eta$")
    ax.set_xlim(3.5, 11.5)
    ax.set_ylim(1, 15)
    ax.set_title("Swirl against radius: circles intense (red edge), diamonds whole (blue edge)")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper left")
    fig2.tight_layout()
    fig2.savefig(os.path.join(HERE, "umax_vs_rmax.png"), dpi=120)
    print("written", len(data), "rows")


if __name__ == "__main__":
    main()
