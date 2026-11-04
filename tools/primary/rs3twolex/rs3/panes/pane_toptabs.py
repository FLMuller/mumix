r"""pane_toptabs.py -- a strip of tabs, each holding a code pane. It takes files in priority to a
bare code pane when the page has it as the target (it is pane number n of the page's panes that
take files).

    write(*paths) -> {label, css, js, html}     paths: files (./ paths) the page opens in tabs at the start

The tab strip only makes and destroys code panes (pane_code) and their content: on a file it
has no tab for, it makes a tab with a new, empty code pane and hands the file to it; on a file it
has, it switches to that tab. It never talks to ftv: when a tab's close button is pressed the code
pane of that tab is removed and the code pane announces closefile for its file. A switch of tab
makes the pane that is now visible announce openfile for its file, so methods and ftv follow.

Signals
    receives  onOpenfile {path, where}    switch to the tab of that file, or make one
              onClosefile {path, where}   remove the tab of that file (it was asked by ftv)
              onSelectfunk, onSaved, onSearchtext, onSearchnext,
              onSearchprev: handed on to the code pane of the tab that is shown
    emits     nothing of its own (the code panes inside emit with this pane's number)
IN and OUT below are these names.

The css and js of the code block ride along (the `also` of the dict write returns), so a
page with tabs and no code block of its own still works.

VERSION  M1 m01.v01 (2026-11-03): first version.
"""
import html as htmllib
import json

import pane_code
from rs3util import asset, done

__all__ = ['write']

IN = ['openfile', 'closefile', 'selectfunk', 'saved', 'searchtext',
      'searchnext', 'searchprev']
OUT = []


def write(*paths, S=None, page=None, loc=None):
    inner = pane_code.write()               # the tabs make code panes: their css and js come along
    first = htmllib.escape(json.dumps(list(paths)), quote=True)
    got = done('toptabs', asset(__file__, 'css'), asset(__file__, 'js'),
               f'<div class="tt" data-open="{first}"><div class="ttop"><select class="ttcombo" title="the open tabs">'
               '<option value="">tabs&hellip;</option></select>'
               '<button class="scrollbtn ttl" title="earlier">&#9664;</button><div class="ttbar"></div>'
               '<button class="scrollbtn ttr" title="later">&#9654;</button></div><div class="ttbody"></div></div>')
    got['also'] = [(inner['label'], inner['css'], inner['js'])]
    return got
