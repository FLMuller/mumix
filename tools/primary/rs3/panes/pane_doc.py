r"""pane_doc.py -- the doc block: any static html, which is what a table or a chart of a report is.

    write(js, css, html) -> {label, css, js, html}

The data is the three pieces of a static page. A page that carries its own <style> and <script>
may be given whole as `html` (the other two empty): the server takes every <style> and <script>
out of it (rs3util.split_package) and collates them with the rest of the page. The ideal package
is one <style>, one <script> and the html. The script runs with `aDOM`, the element of the block,
as its one parameter, so it can reach its own html and nothing else: write document.getElementById
as aDOM.querySelector. With no server the package is still a working static page.

Signals: none. IN = [] OUT = []

VERSION  M1 m01.v01 (2026-11-03): first version.
"""
import hashlib

from rs3util import done, split_package

__all__ = ['write']

IN = []
OUT = []


def write(js='', css='', html='', S=None, page=None, loc=None):
    if '<style' in html.lower() or '<script' in html.lower():
        html, more_css, more_js = split_package(html)
        css = '\n'.join(x for x in (css, more_css) if x)
        js = '\n'.join(x for x in (js, more_js) if x)
    label = 'doc:' + hashlib.sha1((css + '\0' + js).encode('utf-8')).hexdigest()[:10]
    wrapped = f'RS.doc({loc!r}, function(aDOM){{\n{js}\n}});' if js.strip() else ''
    return done(label, css, wrapped, f'<div class="doc">{html}</div>')
