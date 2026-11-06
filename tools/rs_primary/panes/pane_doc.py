r"""pane_doc.py -- the doc block: any html, shown in a box that it cannot get out of.

    write(js, css, html)    the three pieces of a static page
    write(path)             a page that is a file: the ./ path of an .html or .result (rs3util.pathof, at most 8 MB)

A doc is what a table, a chart or a whole report page is. The html may carry its own <style> and <script>: they are taken
out (rs3util.split_package), the inside of its <body> is the html, and
    the css     every rule is made a rule of the box: html, body and :root are the box, any other selector is below it, so
                a report's `body{margin:20px}` and `td{...}` touch nothing outside it (@media is kept, @import is dropped)
    the script  runs inside the box with `document` meaning aDOM, the box (rs_primary/panes/pane_doc.js): aDOM.currentdiv is the box
                element, getElementById and querySelector(All) look only inside it, createElement makes elements, and
                addEventListener('DOMContentLoaded', f) runs f when the box is ready. window, location and localStorage are
                the box's own (a storage of its own, a location that is the page's address), and the names the rest of the
                page's world has (parent, top, fetch, WebSocket ...) are undefined. A script that reaches for more than that
                is refused before it runs (rs3jsguard.check: no this, no arrow function, no .constructor or .parentNode, no
                computed names), and the box says why.
    the inline handlers   onclick="f(this)" in the html becomes a function of the box (rs3jsguard.this_as writes this as
                the element), so the script's functions need not be global.
    links       a javascript: href or src is refused.
A script of a doc is one unit per page: its names are the box's, so two docs on one page do not meet.

Signals
    receives  onSearchtext {text, mode}  mode 'text': every place the text occurs in the box is marked, and the first is shown
              onSearchnext {mode}, onSearchprev {mode}   step through the marks (the status bar's down and up)
              onSearchhome {mode}        back to where the box was scrolled before the search (the status bar's star)
    emits     searchcount {index, total}   the count of the marks, for the status bar
IN and OUT below are these names.

VERSION  M2 m02.v03 (2026-11-06): the box's size and place are the layout's: a page's rule on html, body or :root keeps only type, colour, background and padding (a margin becomes padding); bare outer <div>s are unwrapped.
         M2 m02.v02 (2026-11-06): a layout of blocks that a page's html holds (<div class="rslayout">, made by rs3pages.unfold) is not the doc's own: its text is not searched, its tables get no star, aDOM does not look into it.
         M2 m02.v01 (2026-11-04): every table of the box that has a header row and no sort of its own gets the star and the hamburger (RS.table).
         M2 m01.v02 (2026-11-04): prepare() gives the parts and the problems of a doc's data (the server uses it to serve a report that breaks the rules as its own page).
         M2 m01.v01 (2026-11-04): rebuilt: the script runs as aDOM in a box (checked first), the css is scoped to the box, a
         file is a source like any other, and the box answers the status bar's search. Replaces the doc that took a file's
         script as the page's own.
         M1 m01.v02: a file given by its ./ path. M1 m01.v01 (2026-11-03): first version.
"""
import hashlib
import html as htmllib
import json
import re

from rs3jsguard import check, this_as
from rs3util import asset, done, pathof, split_package

__all__ = ['write']

IN = ['searchtext', 'searchnext', 'searchprev', 'searchhome']
OUT = ['searchcount']

MAX_PAGE = 8 * 1024 * 1024
BODY = re.compile(r'<body[^>]*>(.*)</body\s*>', re.S | re.I)
HANDLER = re.compile(r'''\son([a-z]+)\s*=\s*(?:"([^"]*)"|'([^']*)')''', re.I)
JAVASCRIPT_URL = re.compile(r'''\b(?:href|src|action|formaction|xlink:href)\s*=\s*["']?\s*javascript:''', re.I)
TOP_SELECTOR = re.compile(r'(?:html|body|:root)(?![\w-])\s*', re.I)
OWN_BODY = re.compile(r'body(?![\w-])\s*', re.I)
# what a rule on the box (html, body, :root) may say: the layout gives the box its size and place, so a page's css can only
# dress it (type, colour, background, padding); everything else it writes there is dropped, and a margin becomes padding
BOX_KEEP = {'color', 'background', 'font', 'line-height', 'letter-spacing', 'word-spacing', 'white-space', 'tab-size',
            'cursor', 'accent-color', 'caret-color', 'color-scheme', 'direction', 'quotes', 'hyphens', 'word-break',
            'overflow-wrap', 'padding'}
BOX_PREFIXES = ('font-', 'text-', 'background-', 'padding-')
MARGIN_AS_PADDING = {'margin': 'padding', 'margin-top': 'padding-top', 'margin-right': 'padding-right',
                     'margin-bottom': 'padding-bottom', 'margin-left': 'padding-left'}
DIV_TAG = re.compile(r'<(/?)div(?=[\s>/])[^>]*>', re.I)
# the names the box passes to a script, in order (pane_doc.js calls the script with the first five and the timers)
PARAMETERS = ('aDOM, document, window, location, localStorage, setTimeout, clearTimeout, setInterval, clearInterval, '
              'self, top, parent, frames, globalThis, fetch, XMLHttpRequest, WebSocket, Reflect, Proxy')


def file_text(path):
    """The text of a report page: a file inside HOME with the extension of a page. ValueError says why not."""
    real = pathof(path, kinds=('html',), maxsize=MAX_PAGE)
    if real is None:
        raise ValueError(f'{path} is not a report page (.html or .result) this server may show')
    with open(real, encoding='utf-8', errors='replace') as f:
        return f.read()


def scope_selector(selector, scope):
    """One selector made a selector of the box: html, body and :root are the box, the rest is below it."""
    selector = selector.strip()
    found = TOP_SELECTOR.match(selector)
    if found:
        rest = selector[found.end():]
        again = OWN_BODY.match(rest)                    # html body ...
        rest = rest[again.end():] if again else rest
        return scope + ((' ' + rest) if rest and rest[0] not in '.:[#' else rest)
    return scope + ' ' + selector


def declarations(body):
    """[(name, value)] of a rule's body, split at the ; that is outside brackets and quotes."""
    items, level, quote, last = [], 0, '', 0
    for pos, c in enumerate(body):
        if quote:
            quote = '' if c == quote else quote
        elif c in ('"', "'"):
            quote = c
        elif c == '(':
            level += 1
        elif c == ')':
            level -= 1
        elif c == ';' and level == 0:
            items.append(body[last:pos])
            last = pos + 1
    items.append(body[last:])
    out = []
    for item in items:
        name, colon, value = item.partition(':')
        if colon and name.strip():
            out.append((name.strip().lower(), value.strip()))
    return out


def box_body(body):
    """The body of a rule on the box as the box takes it: only BOX_KEEP, the BOX_PREFIXES and custom properties (--x) are
    kept, so a page's css cannot size, place, hide or move the box (an allow-list: a property that is not named is
    dropped, `all` and !important too); a margin is kept as the padding of the same side (not auto or negative)."""
    kept = []
    for name, value in declarations(body):
        value = re.sub(r'\s*!important\s*$', '', value, flags=re.I)
        if name in MARGIN_AS_PADDING:
            if 'auto' in value.lower() or re.search(r'(^|\s)-', value):
                continue
            name = MARGIN_AS_PADDING[name]
        elif not (name.startswith('--') or name in BOX_KEEP or name.startswith(BOX_PREFIXES)):
            continue
        kept.append(f'{name}:{value}')
    return ';'.join(kept)


def unwrap(markup):
    """The markup without outermost <div>s that carry nothing (no id, class or style: a bare wrapper round all of it),
    taken off one after another; a wrapper with an attribute is kept, as the page's css or script may address it."""
    while True:
        text = markup.strip()
        first = re.match(r'<div\s*>', text, re.I)
        if not first:
            return markup
        depth, last = 0, None
        for tag in DIV_TAG.finditer(text):
            depth += -1 if tag.group(1) else 1
            if depth == 0:
                last = tag
                break
        if last is None or last.end() != len(text):
            return markup
        markup = text[first.end():last.start()]


def scoped(css, scope):
    """The css with every rule made a rule of the box `scope` (an attribute selector). @media and @supports are scoped
    inside, @keyframes and @font-face are left, @import and @charset are dropped."""
    out, i, n = [], 0, len(css)
    while i < n:
        j = css.find('{', i)
        k = css.find(';', i)
        if j < 0:
            break
        head = css[i:j].strip()
        if head.startswith('@') and 0 <= k < j:         # @import / @charset: a statement with no block
            i = k + 1
            continue
        level, end = 1, j + 1
        while end < n and level:
            if css.startswith('/*', end):
                stop = css.find('*/', end + 2)
                end = n if stop < 0 else stop + 2
                continue
            level += (css[end] == '{') - (css[end] == '}')
            end += 1
        body = css[j + 1:end - 1]
        head = re.sub(r'/\*.*?\*/', '', head, flags=re.S).strip()
        if head.startswith('@media') or head.startswith('@supports'):
            out.append(f'{head}{{{scoped(body, scope)}}}')
        elif head.startswith('@'):
            out.append(f'{head}{{{body}}}')
        elif head:
            parts, level2, last = [], 0, 0
            for pos, c in enumerate(head):
                level2 += (c in '([') - (c in ')]')
                if c == ',' and level2 == 0:
                    parts.append(head[last:pos])
                    last = pos + 1
            parts.append(head[last:])
            box = [part for part in parts if scope_selector(part, scope) == scope]
            if box:                                     # a rule on the box: what the box may take, and the rest of its selectors as they were
                dressing = box_body(body)
                if dressing:
                    out.append(scope + '{' + dressing + '}')
                parts = [part for part in parts if part not in box]
            if parts:
                out.append(','.join(scope_selector(part, scope) for part in parts) + '{' + body + '}')
        i = end
    return '\n'.join(out)


def take_handlers(markup):
    """(markup with each on...="code" turned into data-aon-TYPE="N", [(type, code)]): the code of the handlers, in order."""
    found = []

    def one(match):
        code = htmllib.unescape(match.group(2) if match.group(2) is not None else match.group(3))
        found.append((match.group(1).lower(), code))
        return f' data-aon-{match.group(1).lower()}="{len(found) - 1}"'
    return HANDLER.sub(one, markup), found


def refused(label, loc, reasons):
    items = ''.join(f'<li>{htmllib.escape(r)}</li>' for r in reasons)
    return done(label, '', '', f'<div class="doc docerr" data-doc="{htmllib.escape(loc)}"><b>this page cannot be shown: '
                'its script says more than a doc may (rs3jsguard)</b><ul>' + items + '</ul></div>', search='text')


def prepare(*data):
    """(js, css, markup, handlers, problems) of the data of a doc: what write() makes its box of, and why the page may
    not be shown ([] when it may). A page that has problems is a page that does not keep the rules of the box."""
    if len(data) == 1 and data[0].startswith('./'):
        js, css, markup = '', '', file_text(data[0])
    else:
        js, css, markup = (list(data) + ['', '', ''])[:3]
    if '<style' in markup.lower() or '<script' in markup.lower():
        markup, more_css, more_js = split_package(markup)
        css = '\n'.join(x for x in (css, more_css) if x)
        js = '\n'.join(x for x in (js, more_js) if x)
    body = BODY.search(markup)
    if body:                                              # a whole page: the inside of its body
        markup = body.group(1)
    markup = unwrap(markup)
    if JAVASCRIPT_URL.search(markup):
        return js, css, markup, [], ['a javascript: link or source is not allowed']
    markup, handlers = take_handlers(markup)
    problems = check(js, [code for _, code in handlers]) if (js.strip() or handlers) else []
    return js, css, markup, handlers, problems[:20]


def write(*data, S=None, page=None, loc=None):
    js, css, markup, handlers, problems = prepare(*data)
    label = 'doc:' + hashlib.sha1((loc + '\0' + css + '\0' + js + '\0' + markup).encode('utf-8')).hexdigest()[:10]
    if problems:
        return refused(label, loc, problems)
    scope = f'[data-doc="{loc}"]'
    wrapped = ''
    if js.strip() or handlers:
        kinds = json.dumps(sorted({kind for kind, _ in handlers}))
        table = ','.join(f'function(event, aThis){{\n{this_as(code)}\n}}' for _, code in handlers)
        wrapped = (f'(RS.docs = RS.docs || {{}})[{loc!r}] = function({PARAMETERS}){{\n\'use strict\';\n{js}\n'
                   f'aDOM.on({kinds}, [{table}]);\n}};')
    got = done(label, scoped(css, scope), wrapped,
               f'<div class="doc" data-doc="{htmllib.escape(loc)}">{markup}</div>', search='text')
    got['also'] = [('doc', asset(__file__, 'css'), asset(__file__, 'js'))]
    return got
