r"""pane_search.py -- one search box for the blocks of a page.

    write(*modes) -> {label, css, js, html}

modes are the kinds of search the page offers, from files (the tree), text (the lines of the
code), names (the list of methods), log. The box has a selector for the mode, so one box serves
the whole page; the block that matches the mode responds and the others ignore the signal.

Signals
    emits     searchtext {text, mode}   as the user types (empty clears)
              searchnext {mode}, searchprev {mode}   step through the hits
    receives  onSearchcount {index, total}   "3 / 17" from the code pane after a text search
IN and OUT below are these names.

VERSION  M1 m01.v02 (2026-11-04): no where in its signals.
         M1 m01.v01 (2026-11-03): first version.
"""
import html as htmllib

from rs3util import asset, done

__all__ = ['write']

IN = ['searchcount']
OUT = ['searchtext', 'searchnext', 'searchprev']
MODES = ('files', 'text', 'names', 'log')


def write(*modes, S=None, page=None, loc=None):
    modes = [m for m in modes if m in MODES] or list(MODES)
    options = ''.join(f'<option value="{m}">{htmllib.escape(m)}</option>' for m in modes)
    return done('search', asset(__file__, 'css'), asset(__file__, 'js'),
                f'<div class="bar srch"><select class="smode">{options}</select>'
                '<input class="sbox" type="search" placeholder="search">'
                '<button class="sprev" title="previous">&uarr;</button>'
                '<button class="snext" title="next">&darr;</button><span class="scount"></span></div>')
