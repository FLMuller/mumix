r"""pane_ftv.py -- the file tree: the text files of the page's root, as folders that fold.

    write(root=None) -> {label, css, js, html}

The page is built with the list of files in it (the tree verb of rs3core): the tree "has been initialised by
the server" and only responds to changes after that. A refresh button asks the server again.
Only these kinds are listed: code, md, text, html and pdf. A click on a pdf asks the server to open it in the system's program for pdfs (the verb openfile of rs3microDB). A click on a bare file name announces
mngshowfile (show true); a click on a file that is shown announces it with show false. An html file is a
page, so it goes to a new browser tab; other files go where the manager says (a container, else a code pane, else a
tab) or to the block the `send to` toggle names (it shows when the page has more than one block that takes files; its
`auto` leaves it to the manager). ftv{a,b} in the layout string names the blocks for every file.

Signals
    receives  onShowcode {path, loc, on}  on: mark the file as shown (its background changes), open the
                                          folders above it and scroll it into view; off: take the mark off
              onSearchtext {text, mode}   mode 'files': show only the names that match (the status bar's find)
The filter box in the header does the same: a part of a path, or a wildcard (* any text, ? one character):
*.py and rs3* match a file name, panes/pane_* the end of a path.
    emits     mngshowfile {path, show, to?}   to the manager only: it says who gets the file
              showpane {block, on}   its door button: hide this pane (the code and options bars show it again)
IN and OUT below are these names.

VERSION  M1 m01.v03 (2026-11-04): mngshowfile out, showcode in (no more openfile/closefile, no where, no block names).
         M1 m01.v02 (2026-11-04): its size and what it can find are returned by write(); the tree verb; says when the list is not whole.
         M1 m01.v01 (2026-11-03): first version.
"""
import html as htmllib
import json

from rs3util import asset, done

__all__ = ['write']

IN = ['showcode', 'searchtext']
OUT = ['mngshowfile', 'showpane', 'notice']


def write(root=None, S=None, page=None, loc=None):
    listed = S['verbs']['tree']({'hash': page['hash']}, S) if S is not None and page is not None else {'files': []}
    files = listed.get('files', [])
    data = json.dumps([[x['p'], x['k']] for x in files], separators=(',', ':'))
    return done('ftv', asset(__file__, 'css'), asset(__file__, 'js'),
                '<div class="ftv"><div class="fhead"><span class="doors"></span><span class="fsend"></span>'
                '<span class="fname">' + htmllib.escape(listed.get('name', '')) + '</span>'
                '<input class="ffilter" type="search" placeholder="filter files (* ?)" title="a part of a path, or a wildcard: *.py  rs3*  panes/pane_*">'
                '<button class="freload" title="read the file list again">&#8635;</button></div>'
                '<div class="ftree" data-files="' + htmllib.escape(data) + '"' + (' data-truncated="1"' if listed.get('truncated') else '') + '></div></div>', width=75, search='files')
