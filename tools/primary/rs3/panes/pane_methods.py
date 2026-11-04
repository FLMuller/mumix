r"""pane_methods.py -- the methods block: the functions and classes of the file shown, coloured.

    write(path=None) -> {label, css, js, html}

The list comes from the methods verb (rs3comment): Class.method names. The colour of a name is
green exported and named by a test, red short or called under twice, amber red with a ###cld
comment above it (the rules are in rs3comment's header). A click
on a name sends the code to that line; a click on a line number in the code marks the method
that holds the line, scrolling the list to it.

Signals
    receives  onShowcode {path, loc, on}  on: load the list of that file (the file already listed: nothing) and
                                         remember the pane; off: clear, if that file is the one listed and that pane
                                         is the one remembered (one methods block serves every code pane)
              onLinenoClicked {lineno}   mark the method that holds the line, scroll to it
              onSaved {path}      the comments changed, so the lines moved: ask again
              onSearchtext {text, mode}  mode 'names': hide the names that do not match
    emits     selectfunk {lineno}   the user clicked a name: the line it starts on
              showpane {block, on}   its door button: shut this pane (its strip's door opens it again)
IN and OUT below are these names.

VERSION  M1 m01.v03 (2026-11-04): showcode in (one block serves every code pane; selectfunk goes back to the pane that was shown); no where.
         M1 m01.v02 (2026-11-04): its size and what it can find are returned by write(): no module constants.
         M1 m01.v01 (2026-11-03): first version.
"""
import html as htmllib

from rs3util import asset, done

__all__ = ['write']

IN = ['showcode', 'linenoClicked', 'saved', 'searchtext']
OUT = ['selectfunk', 'showpane']


def write(path=None, S=None, page=None, loc=None):
    attr = f' data-path="{htmllib.escape(path)}"' if path else ''
    return done('methods', asset(__file__, 'css'), asset(__file__, 'js'),
                f'<div class="methods"{attr}><div class="mhead"><span class="doors"></span>methods</div>'
                '<div class="mlist"><p class="mute">no file</p></div></div>', width=50, search='names')
