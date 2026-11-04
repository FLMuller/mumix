r"""pane_doc.py -- the doc block: any static html, which is what a table or a chart of a report is.

    write(js, css, html) -> {label, css, js, html}
    write(path)          a report page that is a file: its ./ path (an .html, .htm or .result inside the root)

The data is the three pieces of a static page. A page that carries its own <style> and <script>
may be given whole as `html` (the other two empty): the server takes every <style> and <script>
out of it (rs3util.split_package) and collates them with the rest of the page. The ideal package
is one <style>, one <script> and the html. The script runs with `aDOM`, the element of the block,
as its one parameter, so it can reach its own html and nothing else: write document.getElementById
as aDOM.querySelector. With no server the package is still a working static page.
Given one ./ path instead, the block is that file: the page of a report (a runbench .html, a .result) in a layout of
its own, so it has the status bar and the rest of rs3 (/?layout=[doc]&doc=mumix/results/b_x.html): its <style> and
<script> are taken out as above and the inside of its <body> is the html.

Signals: none. IN = [] OUT = []

VERSION  M1 m01.v01 (2026-11-03): first version.
         m01.v02: a file given by its ./ path.
"""
import hashlib
import os
import re

import rs3files
from rs3util import done, split_package

__all__ = ['write']

IN = []
OUT = []


BODY = re.compile(r'<body[^>]*>(.*)</body\s*>', re.S | re.I)
SELECTOR = re.compile(r'([^{}]+)\{')
PAGE_TAG = re.compile(r'(?<![\w#.\-])(?:html|body)(?![\w\-])')


def scoped(css):
    """The css of a page with its html and body rules made rules of the block (.doc): the page of rs3 keeps its own html
    and body (a margin or a height on body would push the status bar off the page)."""
    def fix(found):
        selector = found.group(1)
        if selector.strip().startswith('@'):
            return found.group(0)
        return PAGE_TAG.sub('.doc', selector).replace('.doc .doc', '.doc') + '{'
    return SELECTOR.sub(fix, css)


def file_html(S, path):
    """The text of a report page, a file inside the root with the extension of a page (the ones the server serves as
    pages: rs3files.PAGE_KINDS). ValueError says why not."""
    real = rs3files.real_of(S, path)
    if real is None or os.path.splitext(real)[1].lower() not in rs3files.PAGE_KINDS or not os.path.isfile(real):
        raise ValueError(f'{path} is not a report page of the root')
    if os.path.getsize(real) > rs3files.MAX_POST:
        raise ValueError(f'{path} is too long')
    with open(real, encoding='utf-8', errors='replace') as f:
        return f.read()


def write(*data, S=None, page=None, loc=None):
    whole = len(data) == 1 and data[0].startswith('./')       # a report file: its script is the page's own, not wrapped
    if whole:
        js, css, html = '', '', file_html(S, data[0])
    else:
        js, css, html = (list(data) + ['', '', ''])[:3]
    if '<style' in html.lower() or '<script' in html.lower():
        html, more_css, more_js = split_package(html)
        css = '\n'.join(x for x in (css, more_css) if x)
        js = '\n'.join(x for x in (js, more_js) if x)
    body = BODY.search(html)
    if body:                                  # a whole page: the inside of its body
        html = body.group(1)
    css = scoped(css)
    label = 'doc:' + hashlib.sha1((css + '\0' + js).encode('utf-8')).hexdigest()[:10]
    if whole:
        wrapped = js                          # the page's own script: its inline onclick and DOMContentLoaded work as in the file
    else:
        wrapped = f'RS.doc({loc!r}, function(aDOM){{\n{js}\n}});' if js.strip() else ''
    return done(label, css, wrapped, f'<div class="doc">{html}</div>')
