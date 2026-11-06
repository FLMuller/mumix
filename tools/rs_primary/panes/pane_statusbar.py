r"""pane_statusbar.py -- the status bar block: the settings menu, the find box, the state line, the
server and its pulse. Every page has one: the page builder (rs3pages.build) adds it as the last row
of a layout that does not name a `statusbar` of its own, so no layout can lose it.

    write() -> {label, css, js, html}

On the bar, from the left
    the menu button     the settings: font, size, initials, tab width, line numbers, wrap, your
                        colour, and a link that opens the report server (/reportserver) in a new tab, leaving this page as it is
                        (when a report server page is already open with a live socket it does nothing, and
                        the state line says so). A change is kept by the server (the config verb), so every
                        page and every restart shows it, and it takes effect on the page at once.
    Find                a box, a choice of what to search (what the blocks of the page say they can find: their
                        write() returns it as `search`), the star button (next, previous, back) and the count of hits. Enter steps
                        to the next hit, Shift+Enter to the one before.
    the state           the last message of a block (editbox: saving, saved, a refusal), in red when bad
    the server          rs3 and its port; "stopped" or "no link" when it is not answering
    the pulse           a circle that pulses while the server answers, turns while a request is out
                        (a file loading), and is a red disc when there is no link. A click on it opens the report
                        server in a new tab, unless a report server page is already open (the hover says so).

Signals
    receives  onSearchcount {index, total}   the count of the hits of the search that was run
              onStatus {...}                 the server's status (every second), or {lost}, {stopped}
              onBusy {on}                    a request to the server is out (on) or all are answered
              onNotice {text, bad}           a message for the state line
    emits     searchtext {text, mode}, searchnext {mode}, searchprev {mode}   the find box
              searchhome {mode}              the star: back to where the view was before the search
              withlineno {on}, withwrap {on}   the settings menu (the option box follows them)
              withconfig {}                  the settings changed: the manager sets the font, size,
                                             tab width and colour on the page
IN and OUT below are these names.

VERSION  M1 m01.v03 (2026-11-05): one button, the star of the tables, does the work of three: each click moves on, next hit
         (the down triangle), previous hit (the up one), back to where it was (the star); Enter and Shift+Enter step as before.
         M1 m01.v02 (2026-11-04): Find offers what the blocks of the page say they can find; the star (searchhome).
         M1 m01.v01 (2026-11-04): first version: the footer of the old report pages (rs2: runbench and
         vcomment) as a block, with the search that was in a top bar.
"""
from rs3util import asset, done

__all__ = ['write']

IN = ['searchcount', 'status', 'busy', 'notice']
OUT = ['searchtext', 'searchnext', 'searchprev', 'searchhome', 'withlineno', 'withwrap', 'withconfig']

# seven dots on a ring, each fainter than the one before: a comet that turns while the server is busy
DOTS = ''.join(f'<circle cx="{x}" cy="{y}" r="2.1" opacity="{o}"/>' for x, y, o in (
    (11, 4, 1), (16.47, 6.64, .82), (17.82, 12.56, .65), (14.04, 17.31, .5), (7.96, 17.31, .37),
    (4.18, 12.56, .28), (5.53, 6.64, .22)))

HTML = ('<div class="sbar">'
        '<button class="cfgbtn" title="settings"><svg viewBox="0 0 14 10"><path d="M1 1.5h12M1 5h12M1 8.5h12"/></svg></button>'
        '<div class="cfgmenu" hidden>'
        '<label>font <select class="cfgfont"></select></label>'
        '<label>size <input class="cfgsize" type="number" min="6" max="40"></label>'
        '<label>initials <input class="cfginitials" type="text" maxlength="8"></label>'
        '<label>tab width <input class="cfgtab" type="number" min="1" max="16"></label>'
        '<label>line numbers <input class="cfglines" type="checkbox"></label>'
        '<label>wrap <input class="cfgwrap" type="checkbox"></label>'
        '<label>your colour <input class="cfgcolor" type="color"></label>'
        '<a class="cfgsrv" href="/reportserver" target="_blank" rel="noopener">open the report server (new tab)</a>'
        '</div>'
        '<span>Find</span><select class="smode" title="what to search"></select>'
        '<input class="sfind" type="search" placeholder="find">'
        '<button class="sortbtn shome" title="find: next hit, previous hit, back to where it was">'
        '<svg viewBox="0 0 20 20"><polygon class="up" points="10,1.5 17.4,14.5 2.6,14.5"/>'
        '<polygon class="dn" points="10,18.5 2.6,5.5 17.4,5.5"/></svg></button>'
        '<span class="sinfo"></span><span class="sstate"></span><span class="gap"></span><span class="ssrv"></span>'
        '<svg class="slive" viewBox="0 0 22 22" data-live="disc"><title>pulsing: the server answers (turning while it '
        'loads a file); red: it does not&#10;click: open the report server in a new tab (nothing is opened when one is already open)</title><g class="lring"><g class="lpulse">' + DOTS +
        '</g></g><circle class="ldisc" cx="11" cy="11" r="4"/></svg></div>')


def write(S=None, page=None, loc=None):
    return done('statusbar', asset(__file__, 'css'), asset(__file__, 'js'), HTML)
