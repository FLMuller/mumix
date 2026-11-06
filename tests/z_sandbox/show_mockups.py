"""show_mockups.py -- the two bench mockups as the tabs of one toptabs, through the report server (contactRS).

Each tab is the html of one mockup file; the server turns the {{layout=...}} tokens in it into panes (methods, code,
editbox) of their own. Run it with the report server running; the page opens in the default browser."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools'))
from reportserver import contactRS

TABS = [('b_rs3pages', 'bench_mockup.html', False), ('b_checker', 'bench_mockup2.html', True)]    # (title, file, shown red)
LAYOUT = '[tt]'


def sections():
    out = []
    for title, name, bad in TABS:
        with open(os.path.join(HERE, name), encoding='utf-8') as f:
            out.append([title, f.read(), bad])
    return out


def main(show=True):
    got = contactRS('load', LAYOUT, {'tt': ['toptabs'] + sections()}, 'two mockups', show)
    print(got['url'])


if __name__ == '__main__':
    main(show='--hidden' not in sys.argv)
