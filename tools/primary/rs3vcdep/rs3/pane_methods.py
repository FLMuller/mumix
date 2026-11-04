r"""pane_methods.py -- the methods block: the functions and classes of the file shown, coloured.

    write(path=None) -> {label, css, js, html}

The list comes from the methods verb (rs3vcomment): Class.method names for the languages of
vclang, Python as codemark lists it. The colour of a name is codemark's: green exported and named
by a test, red short or called under twice, amber red with a ###cld comment above it. A click
on a name sends the code to that line; a click on a line number in the code marks the method
that holds the line, scrolling the list to it.

Signals
    receives  onOpenfile {path, where}   load the list of that file (the file already listed: nothing)
              onClosefile {path, where}  clear, if that file is the one listed
              onLinenoClicked {lineno, where}   mark the method that holds the line, scroll to it
              onSaved {path, where}      the comments changed, so the lines moved: ask again
              onSearchtext {text, mode, where}  mode 'names': hide the names that do not match
    emits     selectfunk {lineno, where}   the user clicked a name: the line it starts on
IN and OUT below are these names.

VERSION  M1 m01.v01 (2026-11-03): first version.
"""
import html as htmllib

from rs3util import asset, done

__all__ = ['write']

IN = ['openfile', 'closefile', 'linenoClicked', 'saved', 'searchtext']
OUT = ['selectfunk']


def write(path=None, S=None, page=None, loc=None):
    attr = f' data-path="{htmllib.escape(path)}"' if path else ''
    return done('methods', asset(__file__, 'css'), asset(__file__, 'js'),
                f'<div class="methods"{attr}><div class="mhead">methods</div>'
                '<div class="mlist"><p class="mute">no file</p></div></div>')
