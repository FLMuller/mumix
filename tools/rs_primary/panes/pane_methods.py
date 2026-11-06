r"""pane_methods.py -- the methods block: a table of the functions, classes and constants of the file shown.

    write(path=None) -> {label, css, js, html}

The rows come from the methods verb (rs3comment). Columns: a status circle (green exported and named by a test, red short
or called under twice or untested, amber red with a ###cld comment above it: the rules are in rs3comment's header; none: a
hollow circle), the line, the name (coloured the same), the class (or the file's own name for a function, or for a constant),
and the definition line (a constant: its value). The headers are RS.table's: a star (sort) and a hamburger (filter, with
a tick list of the values when there are 20 or fewer, the filter guide on a right click). The rows start by class and name.
A click on a row sends the code to that line; ctrl or shift click picks several; a double click greys all the text of the
code but that method (again: back). The code shows only the picked methods when two or more are picked, and only the
methods the table shows while a filter is on (a class row is the whole class); a click on a line in the code marks the
method that holds it, scrolling the table to it.

Signals
    receives  onShowcode {path, loc, on}  on: load the list of that file (the file already listed: nothing) and
                                         remember the pane; off: clear, if that file is the one listed and that pane
                                         is the one remembered (one methods block serves every code pane)
              onLinenoClicked {lineno}   mark the method that holds the line, scroll to it
              onSaved {path}      the comments changed, so the lines moved: ask again
              onSearchtext {text, mode}  mode 'names': hide the rows whose name or class does not match
    emits     selectfunk {lineno, to}   the user clicked a row: the line it starts on, for the code pane it follows
              showmethods {path, ranges, focus, to}   the lines of the code to keep ([[first, last], ...]), or null for all;
                                  focus: grey the rest instead of folding it away
              showpane {block, on}   its door button: shut this pane (its strip's door opens it again)
IN and OUT below are these names.

VERSION  M2 m03.v05 (2026-11-04): no frame round the pane: the pale header says the band of the file.
         M2 m03.v04 (2026-11-04): the header takes a pale colour of the file's band and shows the score of the file as a percent (1 to 100) before its pie.
         M2 m03.v03 (2026-11-04): no circle behind the pie; the proof dot (red, orange, grey, green) is a small dot a pie diameter before it.
         M2 m03.v02 (2026-11-04): a dot is a larger red or orange circle behind the pie (with a white gap), not a dot on it; the pie keeps its size and centre.
         M2 m03.v01 (2026-11-04): the status cell is the SVG pie of spaghettichk (and its red dot), the header has the pie of the file and the frame of the pane takes the colour of the file's band.
         M2 m02.v02 (2026-11-04): only a name can be selected as text; a shift click picks rows without selecting text.
         M2 m02.v01 (2026-11-04): rebuilt as a table (RS.table): status circle, line, name, class, definition; sort and filter; the code folds to what the table shows; 55 mm wide.
         M1 m01.v03 (2026-11-04): showcode in (one block serves every code pane; selectfunk goes back to the pane that was shown); no where.
         M1 m01.v02 (2026-11-04): its size and what it can find are returned by write(): no module constants.
         M1 m01.v01 (2026-11-03): first version.
"""
import html as htmllib

from rs3util import asset, done

__all__ = ['write']

IN = ['showcode', 'linenoClicked', 'saved', 'searchtext']
OUT = ['selectfunk', 'showmethods', 'showpane']


def write(path=None, S=None, page=None, loc=None):
    attr = f' data-path="{htmllib.escape(path)}"' if path else ''
    return done('methods', asset(__file__, 'css'), asset(__file__, 'js'),
                f'<div class="methods"{attr}><div class="mhead"><span class="doors"></span>methods<span class="fscore"></span><span class="fpie"></span></div>'
                '<div class="mlist"><p class="mute">no file</p></div></div>', width=55, search='names')
