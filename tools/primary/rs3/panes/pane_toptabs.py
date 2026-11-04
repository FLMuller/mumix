r"""pane_toptabs.py -- a strip of tabs, each holding a code pane. It takes files in priority to a
bare code pane when the page has it as the target (it is pane number n of the page's panes that
take files).

    write(*items) -> {label, css, js, html}
        items   a ./ path (str): a file the page opens in a tab at the start; or [title, html] or [title, html, bad]: a
                section of a static page, a tab whose pane is that html as it was written (the report page's tabs). The
                <style> and <script> of a section are taken out and collated with the page (rs3util.split_package). bad
                marks the tab red (a failed suite). Sections show in the order given.
        A section's close button puts the tab away, it does not lose it: the tabs list (the combo) shows it as
        (hidden) and brings it back when chosen. What is put away is kept for the page in the browser.

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

VERSION  M1 m01.v02 (2026-11-05): sections of a static page as tabs (the report page), put away and brought back.
         M1 m01.v01 (2026-11-03): first version.
"""
import html as htmllib
import json

import pane_code
from rs3util import asset, done, split_package

__all__ = ['write']

IN = ['openfile', 'closefile', 'selectfunk', 'saved', 'searchtext',
      'searchnext', 'searchprev']
OUT = []


def write(*items, S=None, page=None, loc=None):
    inner = pane_code.write()               # the tabs make code panes: their css and js come along
    first = htmllib.escape(json.dumps([x for x in items if isinstance(x, str)]), quote=True)
    sections, css, js = [], [asset(__file__, 'css')], [asset(__file__, 'js')]
    for item in (x for x in items if not isinstance(x, str)):
        shown, style, script = split_package(item[1])
        css.append(style)
        js.append(script)
        bad = ' data-bad="1"' if len(item) > 2 and item[2] else ''
        sections.append(f'<template class="ttsec" data-title="{htmllib.escape(str(item[0]), quote=True)}"{bad}>{shown}</template>')
    got = done('toptabs', '\n'.join(css), '\n'.join(js),
               f'<div class="tt" data-open="{first}"><div class="ttop"><select class="ttcombo" title="the open tabs">'
               '<option value="">tabs&hellip;</option></select>'
               '<button class="scrollbtn ttl" title="earlier">&#9664;</button><div class="ttbar"></div>'
               '<button class="scrollbtn ttr" title="later">&#9654;</button></div><div class="ttbody"></div>' + ''.join(sections) + '</div>')
    got['also'] = [(inner['label'], inner['css'], inner['js'])]
    return got
