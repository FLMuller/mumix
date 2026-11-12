r"""pane_toptabs.py -- a strip of tabs, each holding a code pane. It takes files in priority to a
bare code pane (write() says it takes files and holds code: a code block on its page is only the place its
tabs show their file).

    write(*items) -> {label, css, js, html}
        items   a ./ path (str): a file the page opens in a tab at the start; or [title, html] or [title, html, bad]: a
                section of a static page, a tab whose pane is that html as it was written (the report page's tabs), or the ./ path of
                an html file (a long page: one message to the server is at most 64 KB). Each section is a doc (pane_doc), so
                its <style> and <script> are the doc's, and a {{layout=...}} in it is made into panes (rs3pages.unfold). bad
                marks the tab red (a failed suite). Sections show in the order given.
        A section's close button puts the tab away, it does not lose it: the tabs list (the combo) shows it as
        (hidden) and brings it back when chosen. What is put away is kept for the page in the browser.

The tab strip only makes and destroys code panes (pane_code) and their content: on a file it
has no tab for, it makes a tab with a new, empty code pane and hands the file to it; on a file it
has, it switches to that tab. It never talks to ftv: when a tab's close button is pressed the code
pane of that tab is removed and the code pane announces showcode off for its file. A switch of tab
makes the pane that goes behind announce showcode off and the one now in front showcode on, so methods and ftv follow.

Signals
    receives  onShowfile {path, show}     switch to the tab of that file, or make one; show false: remove the tab
              onSelectfunk, onSaved, onNotesaved, onSearchtext, onSearchnext,
              onSearchprev, onShowmethods: handed on to the code pane of the tab that is shown
    emits     mngshowfile {path, show, to}   for the files the page was made with; and what the code panes inside emit
              (showcode, linenoClicked, commentline, commentselect, searchcount): they speak as this block; and what the
              doc sections emit (noteline, noteselect: the notes of an html section, rs3microDB), also as this block
IN and OUT below are these names.

The css and js of the code block ride along (the `also` of the dict write returns), so a
page with tabs and no code block of its own still works.

VERSION  M1 m02.v02 (2026-11-12): onNotesaved handed on to the section in front (its doc reads its notes again); noteline and noteselect of the sections are among its OUT.
         M1 m02.v01 (2026-11-06): a section is a doc of its own (pane_doc), given as html or as the ./ path of a file; search goes on to the doc in front.
         M1 m01.v05 (2026-11-04): hands showmethods on to the code pane of the tab shown.
         M1 m01.v04 (2026-11-04): showfile in, showcode out (no more openfile/closefile, no where); takes and holds are declared.
         M1 m01.v03 (2026-11-04): what it can find is returned by write().
         M1 m01.v02 (2026-11-05): sections of a static page as tabs (the report page), put away and brought back.
         M1 m01.v01 (2026-11-03): first version.
"""
import html as htmllib
import json

import pane_code
import pane_doc
from rs3util import asset, done

__all__ = ['write']

IN = ['showfile', 'selectfunk', 'showmethods', 'saved', 'notesaved', 'searchtext',
      'searchnext', 'searchprev', 'searchhome']
OUT = ['mngshowfile', 'showcode', 'linenoClicked', 'commentline', 'commentselect', 'searchcount', 'noteline', 'noteselect']


def write(*items, S=None, page=None, loc=None):
    inner = pane_code.write()               # the tabs make code panes: their css and js come along
    first = htmllib.escape(json.dumps([x for x in items if isinstance(x, str)]), quote=True)
    sections, css, js, docs = [], [asset(__file__, 'css')], [asset(__file__, 'js')], []
    for number, item in enumerate(x for x in items if not isinstance(x, str)):
        doc_loc = f'{loc}.s{number + 1}'                    # the section is a doc of its own, its html, css and script under the doc's rules
        data = (item[1],) if item[1].startswith('./') else ('', '', item[1])      # a ./ path to an html file, or the html itself
        made = pane_doc.write(*data, S=S, page=page, loc=doc_loc)
        css.append(made['css'])
        js.append(made['js'])
        docs.extend(made.get('also', []))
        bad = ' data-bad="1"' if len(item) > 2 and item[2] else ''
        sections.append(f'<template class="ttsec" data-title="{htmllib.escape(str(item[0]), quote=True)}" data-doc="{doc_loc}"{bad}>'
                        f'{made["html"]}</template>')
    got = done('toptabs', '\n'.join(css), '\n'.join(js),
               f'<div class="tt" data-open="{first}"><div class="ttop"><select class="ttcombo" title="the open tabs">'
               '<option value="">tabs&hellip;</option></select>'
               '<button class="scrollbtn ttl" title="earlier">&#9664;</button><div class="ttbar"></div>'
               '<button class="scrollbtn ttr" title="later">&#9654;</button></div><div class="ttbody"></div>' + ''.join(sections) + '</div>', search='text',
               takes=True, holds='code')
    got['also'] = [(inner['label'], inner['css'], inner['js'])] + docs
    return got
