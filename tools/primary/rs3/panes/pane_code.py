r"""pane_code.py -- the code block: one file as lines with its comment threads.

    write(path=None) -> {label, css, js, html}

The block shows the file it is sent. With a ./ path as data it opens that file when the page's
link is up (the viewer page does so); without, it waits for a signal.

Signals
    receives  onShowfile {path, show}    show that file (a file already shown: nothing; another: the one shown
                                         is dropped, announcing showcode off for it); show false: wipe, if that
                                         file is the one shown, and say so
              onSelectfunk {lineno}      scroll to that line and flash it
              onShowmethods {path, ranges, focus}   ranges [[first, last], ...] of the file shown: the other lines are
                                         folded away (a gap line shows where); focus: they are greyed, not folded; null
                                         ranges: the whole file again
              onSaved {path}             the file's comments changed: read it again
              onSearchtext {text, mode}  mode 'text': mark every hit, scroll to the first
              onSearchnext / onSearchprev {mode}   step through the hits
    emits     showcode {path, loc, on}   a file is shown in this pane, or no longer (a tab switch too)
              linenoClicked {lineno}     the user clicked a line (the whole line is marked, until a scroll or a click elsewhere)
              commentline {path, base, line}   ... and a comment above that line (to the nearest editbox); a click that ends a text selection does not
              commentselect {path, base, first, last, tag, text}   clicked a comment (the same)
              searchcount {index, total}   after a search
IN = [...] and OUT = [...] below are these names; a test checks every OUT has a receiver.

The lines come from the open verb (rs3comment): a row for each line and a thread for each comment, the
format is in rs3comment's header.

VERSION  M1 m01.v08 (2026-11-05): find works over the coloured pieces of a line (modules( is two).
         M1 m01.v07 (2026-11-04): showmethods in: fold the file to the methods the list shows, or grey all but one.
         M1 m01.v06 (2026-11-04): a click anywhere on a line also asks for a comment, unless text was selected.
         M1 m01.v05 (2026-11-04): the mark outranks the row colours of docstrings and comments; a click anywhere on a line marks it (the soft orange of the number's hover); only the number asks for a comment; it stays marked while the comment box (data-keepsel) is clicked.
         M1 m01.v04 (2026-11-04): a click on a line number marks the whole line until a scroll or a click elsewhere.
         M1 m01.v03 (2026-11-04): showfile in, showcode out (no more openfile/closefile, no where); write() says it takes files.
         M1 m01.v02 (2026-11-04): what it can find is returned by write().
         M1 m01.v01 (2026-11-03): first version.
"""
import sys
import os
import html as htmllib

from rs3util import asset, done
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))  # tools/: the one use.py
from use import load

load('rs3lex')           # rs3lex.pyx: css() gives the colour of every role

__all__ = ['write']

IN = ['showfile', 'selectfunk', 'showmethods', 'saved', 'searchtext',
      'searchnext', 'searchprev']
OUT = ['showcode', 'linenoClicked', 'commentline', 'commentselect', 'searchcount']

SKELETON = ('<div class="codeview"{path}><div class="cbar"><span class="cpath">no file</span>'
            '<button class="cprev" title="previous comment">&#8592;</button>'
            '<button class="cnext" title="next comment">&#8594;</button></div>'
            '<div class="clines"><p class="mute">no file open</p></div></div>')


def write(path=None, S=None, page=None, loc=None):
    attr = f' data-path="{htmllib.escape(path)}"' if path else ''
    return done('code', css() + asset(__file__, 'css'), asset(__file__, 'js'),
                SKELETON.format(path=attr), search='text', takes=True)
