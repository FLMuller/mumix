r"""pane_log.py -- the server's log, growing to at most 10000 lines.

    write() -> {label, css, js, html}

The manager asks the server about once a second (pulse) and announces the new lines. The block
keeps the lines in a Map keyed by their row number (row -> [time, text]), so every line stays
and the order is the order of arrival; when there are more than MAX lines the oldest go, from
the Map and from the page. (A dict keyed by the text, as first suggested, would fold repeated
lines into one: the key by row keeps every one.)

Signals
    receives  onLog {rows: [[row, time, text], ...]} | {reset: true}   new lines, or start again
              onSearchtext {text, mode, where}   mode 'log': show only the lines that hold the text
    emits     nothing
IN and OUT below are these names.

VERSION  M1 m01.v02 (2026-11-04): what it can find is returned by write().
         M1 m01.v01 (2026-11-03): first version.
The newest line is at the top; follow keeps the view there as lines arrive. The oldest is dropped past MAX.
m01.v02: a time button on the bar turns the order (newest first v, oldest first ^); the choice is kept in the browser.
"""
from rs3util import asset, done

__all__ = ['write']

MAX = 10000
IN = ['log', 'searchtext']
OUT = []


def write(S=None, page=None, loc=None):
    return done('log', asset(__file__, 'css'), asset(__file__, 'js').replace('@@MAX@@', str(MAX)),
                '<div class="log"><div class="lbar"><button class="lsort"></button>'
                '<label title="stay with the newest line as lines arrive"><input type="checkbox" class="lfollow" checked> follow</label>'
                '<span class="lcount">0 lines</span></div>'
                '<div class="llines"></div></div>', search='log')
