"""exportdata.py  v01  Write data/tubes.csv, the data of the fitting tool, from the source data of the literature page.

Why
    The fitting tool must be shareable: it reads data/tubes.csv and data/corrections.json and nothing else.  This script is the one
    place that knows where the numbers come from (../analysis/sourcedata.py, the converted values of every paper; the appendix of the
    page documents each conversion).  Re-run it after the source data change.

Columns of tubes.csv (one row per source, run and Re_lambda; values as calculated from the papers, no correction)
    id           row number
    src          source key (Ghira22, Mouri07, ...)
    reference    short reference as in the page, e.g. "Ghira et al. (2022)"
    group        A DNS intense tubes, B DNS whole tubes, C experiments (hot wire or film, PIV)
    tube_set     intense or whole (section 7 of the page)
    method       how the tubes were measured
    re_lo, re_hi Re_lambda (equal when one value; a range for Belin, Mouri 2003, Sassa; empty when none is given)
    r_raw        r_max / eta
    u_raw        U_max / U_eta (empty where the source gives no swirl)
    gamma_listed Gamma / nu as listed by the source where it differs from 8.784 r U (Kida et al.), else empty
    d_over_eta   tube spacing where given
    note         text

Usage:  python exportdata.py
"""
import csv
import html
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ANALYSIS = os.path.join(os.path.dirname(HERE), "analysis")
sys.path.insert(0, ANALYSIS)
import build_data_sections as bds          # noqa: E402
import sourcedata as sd                    # noqa: E402

GROUP = {"Ghira22": "A", "Ghira25": "A", "Jimenez93": "A", "DaSilva11": "A",
         "Tanahashi01": "B", "Kida02": "B", "Pirozzoli09": "B", "Ishihara13": "B", "Wall": "B",
         "Aligolzadeh23": "C", "Mouri03": "C", "Mouri04": "C", "Mouri07": "C", "Mouri09": "C", "Belin96": "C", "Sassa05": "C"}


def parse_re(text):
    """Re_lambda as (lo, hi) numbers, or (None, None) when the source gives none."""
    if isinstance(text, (int, float)):
        return float(text), float(text)
    s = str(text).replace("&ndash;", "-")
    try:
        lo, hi = [float(v) for v in s.split("-")]
        return lo, hi
    except ValueError:
        return None, None


def main():
    items = bds.tube_items(corrected=False)
    path = os.path.join(HERE, "data", "tubes.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "src", "reference", "group", "tube_set", "method", "re_lo", "re_hi", "r_raw", "u_raw", "gamma_listed", "d_over_eta", "note"])
        for i, it in enumerate(items, 1):
            s = sd.BY_KEY[it["src"]]
            lo, hi = parse_re(it["Re"])
            listed = ""
            if it["src"] in ("Kida02", "Jimenez93") and it["RG"] is not None:      # the circulation the paper lists (Kida: Gamma/nu; Jimenez: Re_gamma)
                listed = "%.1f" % it["RG"]
            w.writerow([i, it["src"], html.unescape(s["short"]), GROUP[it["src"]], s["tubes"], s["method"],
                        "" if lo is None else "%g" % lo, "" if hi is None else "%g" % hi,
                        "" if it["beta"] is None else "%.4f" % it["beta"], "" if it["U"] is None else "%.4f" % it["U"],
                        listed, "" if it["d"] is None else "%.2f" % it["d"], ""])
    print("wrote", path, len(items), "rows")


if __name__ == "__main__":
    main()
