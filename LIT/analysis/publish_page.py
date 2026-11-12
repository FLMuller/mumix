"""publish_page.py  v01  Publish the page as a new file in LIT/results, then show it through the report server.

    python publish_page.py [--no-open]

Copies ../vortex-energy-balance.html to ../results/vortex-energy-balance_YYYY.MM.DD_HH;MM.html (the name pattern of the other results; a file is never overwritten, so the
results keep every published version, newest last) and, unless --no-open, loads it into the report server with contactRS (the layout [doc], with the status bar).  The page is
one self-contained file (its equations load MathJax from a CDN), so a published copy opens with or without the server.  Run it after the build scripts
(build_data_sections.py, build_intro_sections.py, build_fit_sections.py; see README.md).

Versions  M01 m01.v01 (2026-11-11): first version.
"""
import argparse
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LIT = os.path.dirname(HERE)
PAGE = os.path.join(LIT, "vortex-energy-balance.html")
RESULTS = os.path.join(LIT, "results")
sys.path.insert(0, os.path.join(HERE, "..", "fittingtool"))
import fittingtool    # noqa: E402

__all__ = ["publish", "main"]


def publish(open_in_server=True):
    """Copy the page to a new stamped file in results/; returns its path."""
    os.makedirs(RESULTS, exist_ok=True)
    stem = "vortex-energy-balance_" + time.strftime("%Y.%m.%d_%H;%M")
    path = os.path.join(RESULTS, stem + ".html")
    n = 1
    while os.path.exists(path):                                   # two publishes in one minute: a suffix, never an overwrite
        n += 1
        path = os.path.join(RESULTS, "%s_%d.html" % (stem, n))
    shutil.copyfile(PAGE, path)
    print("published:", path)
    if open_in_server:
        fittingtool.open_report(path)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-open", action="store_true", help="do not show the file through the report server")
    a = ap.parse_args(argv)
    publish(not a.no_open)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
