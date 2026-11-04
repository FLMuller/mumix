r"""pane_options.py -- the option box: switches that the other blocks follow.

    write() -> {label, css, js, html}

Signals
    emits     withlineno {on}   show the line numbers (true) or not
              withwrap {on}     wrap long lines (true) or not
    receives  nothing
Both are kept in the config (verb config) so the next page starts the same way. IN and OUT below
are these names.

VERSION  M1 m01.v01 (2026-11-03): first version.
"""
from rs3util import asset, done

__all__ = ['write']

IN = []
OUT = ['withlineno', 'withwrap']


def write(S=None, page=None, loc=None):
    return done('options', asset(__file__, 'css'), asset(__file__, 'js'),
                '<div class="bar opt"><label><input type="checkbox" class="olines"> line numbers'
                '</label><label><input type="checkbox" class="owrap"> wrap</label></div>')
