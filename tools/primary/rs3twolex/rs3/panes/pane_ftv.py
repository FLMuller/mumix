r"""pane_ftv.py -- the file tree: the text files of the page's root, as folders that fold.

    write(root=None) -> {label, css, js, html}

The page is built with the list of files in it (rs3files.tree): the tree "has been initialised by
the server" and only responds to changes after that. A refresh button asks the server again.
Only text kinds are listed: code, md, text, and html. A click on a bare file name announces
openfile; a click on a file that is open announces closefile. An html file is a page, so its
`where` is 0 (a new browser tab); other files go to the pane the `send to` toggle names (the
toggle shows when the page has more than one pane that takes files, and a 'new tab' choice).

Signals
    receives  onOpenfile {path, where}   mark the file as open (its background changes), open the
                                          folders above it and scroll it into view
              onClosefile {path, where}  take the mark off
              onSearchtext {text, mode, where}   mode 'files': show only the names that match (the status bar's find)
The filter box in the header does the same: a part of a path, or a wildcard (* any text, ? one character):
*.py and rs3* match a file name, panes/pane_* the end of a path.
    emits     openfile {path, where}, closefile {path, where}
              showpane {block, on}   its door button: hide this pane (the code and options bars show it again)
IN and OUT below are these names.

VERSION  M1 m01.v01 (2026-11-03): first version.
"""
import html as htmllib
import json

from rs3files import tree
from rs3util import asset, done

__all__ = ['write']

WIDTH = 50                          # mm: its width in a row when the layout gives none (ftv wdxh, not ftv 70dxh)
IN = ['openfile', 'closefile', 'searchtext']
OUT = ['openfile', 'closefile', 'showpane']


def write(root=None, S=None, page=None, loc=None):
    listed = tree({'hash': page['hash']}, S) if S is not None and page is not None else {'files': []}
    files = listed.get('files', [])
    data = json.dumps([[x['p'], x['k']] for x in files], separators=(',', ':'))
    return done('ftv', asset(__file__, 'css'), asset(__file__, 'js'),
                '<div class="ftv"><div class="fhead"><span class="doors"></span><span class="fsend"></span>'
                '<span class="fname">' + htmllib.escape(listed.get('name', '')) + '</span>'
                '<input class="ffilter" type="search" placeholder="filter files (* ?)" title="a part of a path, or a wildcard: *.py  rs3*  panes/pane_*">'
                '<button class="freload" title="read the file list again">&#8635;</button></div>'
                '<div class="ftree" data-files="' + htmllib.escape(data) + '"></div></div>')
