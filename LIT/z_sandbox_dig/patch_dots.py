import os
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "analysis", "data_corrected_plot.py")
s = open(p, encoding="utf-8").read()


def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:70])
    s = s.replace(old, new)


rep('corrected=bool(key), key=key, id=x["id"])', 'corrected=bool(key), key=key, id=x["id"], reference=x["reference"], group=x["group"])')
rep('    sources = sorted({d["src"] for d in out})\n', '''    sources = sorted({d["src"] for d in out})
    write_dots(out, mult)
''')
rep("def fit_trends(", '''def write_dots(out, mult):
    """data_corrected_dots.csv: the dots of the bottom row of the figure (rows with a single Re_lambda) with the values the fits use (the corrected values of Ghira and of the observed rows, the other simulations as read), the multipliers applied,
    and for the all-tube average of Mouri and Hori the multipliers of the other thresholds (k = 0.25, 0.33, 0.5, 1).  Read by fittingtool/modelselect.py."""
    allk = load("belin_correctors_all.json")
    ks = ("0.25", "0.33", "0.5", "1")
    tabs = {k: (Table([(q["Re_lambda"], q["k=%s" % k]["m_r"]) for q in allk]), Table([(q["Re_lambda"], q["k=%s" % k]["m_U"]) for q in allk])) for k in ks}
    with open(os.path.join(HERE, "data_corrected_dots.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "src", "reference", "group", "tube_set", "method", "re", "r_raw", "u_raw", "r", "u"] + ["m_r_k%s" % k for k in ks] + ["m_u_k%s" % k for k in ks])
        for d in out:
            if d["lo"] is None or d["lo"] != d["hi"]:
                continue
            corr = d["corrected"] and (not d["method"].startswith("DNS") or d["src"].startswith("Ghira"))
            r = (d["r_lo"] if corr else d["r_raw"]) if d["r_raw"] is not None else None
            u = (d["u_lo"] if corr else d["u_raw"]) if d["u_raw"] is not None else None
            alt = [[("%.5f" % tabs[k][i](d["lo"])) if d["src"] == "Mouri09" else "" for k in ks] for i in (0, 1)]
            w.writerow([d["id"], d["src"], d["reference"], d["group"], d["tube_set"], d["method"], d["lo"], "" if d["r_raw"] is None else d["r_raw"], "" if d["u_raw"] is None else d["u_raw"],
                        "" if r is None else "%.5f" % r, "" if u is None else "%.5f" % u] + alt[0] + alt[1])


def fit_trends(''')
rep("Versions  M01 m01.v19", "Versions  M01 m01.v20 (2026-11-16): writes data_corrected_dots.csv (the dots with the values the fits use) for fittingtool/modelselect.py.\n          M01 m01.v19")
open(p, "w", encoding="utf-8").write(s)
print("ok")
