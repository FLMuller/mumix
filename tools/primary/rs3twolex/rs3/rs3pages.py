r"""rs3pages.py -- pages made of blocks: the layout, the collation, the page, and the routes.

A page is a layout string (rs3layout.py) and, for each locator in it, a block with its data. A
block is rs3/panes/pane_NAME.py with write(*data, S=, page=, loc=) -> {label, css, js, html}; the
locator `code2` takes its block from the name without the digits (code), unless the page says
otherwise. The server runs each block's write, takes the html of each into its place in the
layout, collates the css and the js into ONE <style> and ONE <script> (a label seen before is
not written again; so are two identical texts), and fills rs3/html/page.html with them and with the
manager (html/manager.js), which routes the signals between the blocks. The result is a complete
html page.

Verbs (websocket)
    load   {do: 'load', layout, blocks?, title?, show?}   -> {ok, hash, url, path}
           make a page of blocks and open it in the default browser (show false: only answer).
           blocks is {locator: [block, *data]}: contactRS('load', '[doc wxh]',
           {'doc': ['doc', js, css, html]}, 'a title').
    view   {do: 'view', path, show?}   -> {ok, hash, url, path}
           open one file, by its ./ path, as a commentable page (/code/...): methods, code, comment box.
Routes (HTTP GET)
    /reportserver        the monitor page of the server: file tree, status, log, stop, restart
    /code/mumix/x.py     the viewer of one file (a ./ path without the ./)
    /page/KEY.html       a page made by load (kept in memory: the last 50)
    anything else        a file page (an .html or .result inside the root): rs3files.get_file

The pages table. A page that is an address (not a file) is put in S['pages'] when it is served and
when it says hello (register_url), so a page whose server restarted finds its place again.

VERSION  M1 m01.v01 (2026-11-03): first version.
"""
import hashlib
import importlib
import json
import os
import re
import sys
import time
import webbrowser
from urllib.parse import quote, unquote

import rs3core
import rs3files
import rs3layout
from rs3files import page_path, real_of, register_view, relative, scope_of
from rs3util import asset

HOST = '127.0.0.1'
HERE = os.path.dirname(os.path.abspath(__file__))
PANES = os.path.join(HERE, 'panes')
PAGE = os.path.join(HERE, 'html')                 # the page itself: page.html, page.css, manager.js, selftest.js
if PANES not in sys.path:                   # the blocks are modules of that folder
    sys.path.insert(0, PANES)
KEEP = 50                                   # built pages kept in memory
TARGETS = ('code', 'toptabs')               # the blocks a file can be sent to
MONITOR = ('[ftv 70dxh, [serverstatus wx50d ; log wxh]]', {})
VIEWER = '[methods 50dxh, [code wxh ; editbox wx35d]]'
STATUSBAR = 'statusbar wx7'                 # added as the last row of every page that does not name its own
BLOCK = re.compile(r'^[a-z]{1,20}$')
TOKEN = re.compile(r'@@(\w+)@@')


def block_of(loc):
    """The kind of block of a locator: its name without the digits."""
    return re.sub(r'\d+$', '', loc)


def module_of(block):
    """The module of a block: rs3/panes/pane_NAME.py, by name only (no path can be given)."""
    if not BLOCK.match(block) or not os.path.isfile(os.path.join(PANES, f'pane_{block}.py')):
        raise ValueError(f'no block called {block!r}')
    return importlib.import_module(f'pane_{block}')


def collate(parts):
    """(css, js) from the (label, css, js) of the blocks, each label's text once and a text that
    an earlier one repeated not at all."""
    seen = set()
    css, js = [], []
    for label, c, j in parts:
        for kind, text, out in (('css', c, css), ('js', j, js)):
            key = (kind, label)
            if not text or key in seen or (kind, text) in seen:
                continue
            seen.add(key)
            seen.add((kind, text))
            out.append(f'/* block:{label} */\n{text.strip()}\n')
    return '\n'.join(css), '\n'.join(js)


def script_safe(text):
    """JSON or script text that cannot close the <script> it sits in."""
    return re.sub(r'</(script|!--)', r'<\\/\1', text, flags=re.I)


def build(S, page, layout, specs, title, selftest=False):
    """The html of a page: see the module header. ValueError says what is wrong with the layout
    or a block."""
    tree = rs3layout.parse(layout)
    if 'statusbar' not in rs3layout.names(tree):          # every page has the status bar: the layout cannot lose it
        tree = rs3layout.parse(f'[{layout.strip()} ; {STATUSBAR}]')
    html_of, parts, panes, counts, defaults = {}, [], [], {}, {}
    locs = rs3layout.names(tree)
    specs_of = {loc: specs.get(loc) or [block_of(loc)] for loc in locs}
    specs_of = {loc: [spec] if isinstance(spec, str) else list(spec) for loc, spec in specs_of.items()}
    tabbed = any(spec[0] == 'toptabs' for spec in specs_of.values())
    for loc in locs:
        block, data = specs_of[loc][0], specs_of[loc][1:]
        module = module_of(block)
        got = module.write(*data, S=S, page=page, loc=loc)
        if getattr(module, 'WIDTH', None) or getattr(module, 'HEIGHT', None):    # its own size, where the layout gives none
            defaults[loc] = (getattr(module, 'WIDTH', None), getattr(module, 'HEIGHT', None))
        html_of[loc] = got['html']
        parts.append((got.get('label') or block, got.get('css', ''), got.get('js', '')))
        parts.extend(got.get('also', []))        # blocks this one makes inside itself (toptabs: code)
        host = tabbed and block == 'code'        # with tabs, a code block is where the tabs show their file
        kind = 'target' if block in TARGETS and not host else block
        counts[kind] = counts.get(kind, 0) + 1
        panes.append({'loc': loc, 'block': block, 'where': counts[kind], 'host': host})
    css, js = collate(parts)
    info = {'hash': page['hash'], 'address': page['path'], 'title': title, 'port': S['port'],
            'admin': bool(page.get('admin')), 'panes': panes,
            'config': rs3core.settings(S)}
    fill = {'title': title.replace('<', '&lt;'), 'pagecss': asset(os.path.join(PAGE, 'page.css'), 'css'),
            'css': css, 'body': rs3layout.render(tree, html_of, defaults=defaults),
            'page': script_safe(json.dumps(info)), 'manager': asset(os.path.join(PAGE, 'manager.js'),
                                                                     'js'),
            'js': script_safe(js + ('\n' + asset(os.path.join(PAGE, 'selftest.js'), 'js')
                                    + '\nRS.selftest();' if selftest else ''))}
    template = asset(os.path.join(PAGE, 'page.html'), 'html')
    return TOKEN.sub(lambda m: fill.get(m.group(1), ''), template)


def address_of(rel):
    """The address of the viewer of a ./ path."""
    return '/code/' + quote(rel[2:], safe='/')


def viewer_page(S, address):
    """(page record, layout, specs, title) of a viewer address, or None."""
    path = './' + unquote(address[len('/code/'):])
    clean = page_path(S, path)
    if clean is None:
        return None
    root = scope_of(real_of(S, clean))
    if root is None:
        return None
    page = register_view(S, address, root)
    specs = {'code': ['code', clean], 'methods': ['methods', clean]}
    return page, VIEWER, specs, os.path.basename(clean)


def register_url(S, url):
    """The page record for an address a page says it was served from, or None."""
    if url == '/reportserver':
        return register_view(S, url, S['root'], admin=True)
    if url.startswith('/code/'):
        got = viewer_page(S, url)
        return got[0] if got else None
    if re.fullmatch(r'/page/[0-9a-f]{12}\.html', url):
        return register_view(S, url, S['root'])
    return None


def keep(S, key, html):
    S['built'][key] = html
    for old in list(S['built'])[:-KEEP]:
        del S['built'][old]


def show(S, url, wanted):
    if wanted:
        try:
            webbrowser.open(url)
        except Exception as error:
            S['say'](f'the browser would not open {url}: {error!r}')


def where(S, address):
    return f'http://{HOST}:{S["port"]}{address}'


def load(msg, S):
    layout, blocks = msg.get('layout'), msg.get('blocks') or {}
    title = msg.get('title') or 'report'
    if not isinstance(layout, str) or not isinstance(blocks, dict) or not isinstance(title, str):
        return {'ok': False, 'error': 'load takes a layout string, a blocks dict and a title'}
    key = hashlib.sha1(f'{layout}{json.dumps(blocks, sort_keys=True)}{time.time()}'
                       .encode('utf-8')).hexdigest()[:12]
    address = f'/page/{key}.html'
    page = register_view(S, address, S['root'])
    try:
        html = build(S, page, layout, blocks, title[:200], bool(msg.get('selftest')))
    except (ValueError, TypeError, KeyError) as error:
        return {'ok': False, 'error': str(error)}
    keep(S, key, html)
    url = where(S, address)
    show(S, url, msg.get('show', True))
    return {'hash': page['hash'], 'url': url, 'path': address}


def view(msg, S):
    path = msg.get('path')
    clean = page_path(S, path)
    if clean is None:
        return {'ok': False, 'error': 'not a file a page may show'}
    address = address_of(clean)
    page = viewer_page(S, address)[0]
    url = where(S, address)
    show(S, url, msg.get('show', True))
    return {'hash': page['hash'], 'url': url, 'path': address}


def page_reply(html):
    return 200, html.encode('utf-8'), 'text/html; charset=utf-8'


def get(req, S):
    """GET: the monitor, a viewer, a made page, or a file page."""
    path = req['path']
    try:
        if path == '/reportserver':
            page = register_view(S, path, S['root'], admin=True)
            layout, specs = MONITOR
            return page_reply(build(S, page, layout, {**specs}, 'rs3 monitor',
                                    'selftest=1' in req['query']))
        if path.startswith('/code/'):
            got = viewer_page(S, path)
            if got is None:
                return 404, b'', None
            page, layout, specs, title = got
            return page_reply(build(S, page, layout, specs, title, 'selftest=1' in req['query']))
        found = re.fullmatch(r'/page/([0-9a-f]{12})\.html', path)
        if found:
            html = S['built'].get(found.group(1))
            return page_reply(html) if html else (404, b'', None)
    except (ValueError, TypeError, KeyError) as error:
        S['say'](f'GET {path}: {error}')
        return 500, str(error).encode('utf-8'), 'text/plain; charset=utf-8'
    return rs3files.get_file(req, S)


VERBS = {'load': load, 'view': view}
ROUTES = {'GET': get}
