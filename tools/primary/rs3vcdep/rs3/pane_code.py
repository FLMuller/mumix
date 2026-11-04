r"""pane_code.py -- the code block: one file as lines with its comment threads.

    write(path=None) -> {label, css, js, html}

The block shows the file it is sent. With a ./ path as data it opens that file when the page's
link is up (the viewer page does so); without, it waits for a signal.

Signals
    receives  onOpenfile {path, where}   show that file (a file already shown: nothing; another:
                                         the one shown is dropped, announcing closefile for it)
              onClosefile {path, where}  wipe, if that file is the one shown (no announcement)
              onSelectfunk {lineno, where}  scroll to that line and flash it
              onWithlineno {on}          show or hide the line numbers
              onWithwrap {on}            wrap long lines, or not
              onSaved {path, where}      the file's comments changed: read it again
              onSearchtext {text, mode, where}   mode 'text': mark every hit, scroll to the first
              onSearchnext / onSearchprev {mode, where}   step through the hits
    emits     closefile {path, where}    its content is wiped or the pane is removed
              openfile {path, where}     the pane became visible with a file in it (a tab switch)
              linenoClicked {lineno, where}   the user clicked a line's number
              commentline {path, base, line, where}   ... and wants a comment above that line
              commentselect {path, base, first, last, tag, text, where}   clicked a comment
              searchcount {index, total, where}   after a search
IN = [...] and OUT = [...] below are these names; a test checks every OUT has a receiver.

The lines come from the open verb (rs3vcomment): the html is vcode's, as the vcomment page shows it.

VERSION  M1 m01.v01 (2026-11-03): first version.
"""
import html as htmllib

import codelex
from rs3util import asset, done

__all__ = ['write']

IN = ['openfile', 'closefile', 'selectfunk', 'withlineno', 'withwrap', 'saved', 'searchtext',
      'searchnext', 'searchprev']
OUT = ['closefile', 'openfile', 'linenoClicked', 'commentline', 'commentselect', 'searchcount']

SKELETON = ('<div class="codeview"{path}><div class="cbar"><span class="cpath">no file</span>'
            '<button class="cprev" title="previous comment">&#8592;</button>'
            '<button class="cnext" title="next comment">&#8594;</button></div>'
            '<div class="clines"><p class="mute">no file open</p></div></div>')


def write(path=None, S=None, page=None, loc=None):
    attr = f' data-path="{htmllib.escape(path)}"' if path else ''
    return done('code', codelex.css() + asset(__file__, 'css'), asset(__file__, 'js'),
                SKELETON.format(path=attr))
