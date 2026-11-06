r"""rs3pages.py -- pages made of blocks: the layout, the collation, the page, and the routes.

A page is a layout string (rs3layout.py) and, for each locator in it, a block with its data. A
block is rs_primary/panes/pane_NAME.py with write(*data, S=, page=, loc=) -> done(label, css, js, html, ...) (rs3util); the
locator `cd.2` is the block `code` (the part before the . is its kind, a short name or a block's name: rs3layout), unless the layout
defines it, `{cd3=code}`. The server runs each block's write, takes the html of each into its place in the
layout, collates the css and the js into ONE <style> and ONE <script> (a label seen before is
not written again; so are two identical texts), and fills rs_primary/html/page.html with them and with the
manager (html/manager.js), which routes the signals between the blocks. The result is a complete
html page. The data of a block that are ./ paths with a pattern in them (./mumix/**/*.py, ./a/{x,y}.py) are opened
here, to the files they name (rs3util.pathof); the block gets the files.

Verbs (websocket)
    load   {do: 'load', layout, blocks?, title?, show?}   -> {ok, hash, url, path}
           make a page of blocks and open it in the default browser (show false: only answer).
           blocks is {locator: [block, *data]}: contactRS('load', '[doc wxh]',
           {'doc': ['doc', js, css, html]}, 'a title'). When every block takes ./ paths or nothing, the page is
           its own address (/?layout=...: rs3util.address) and nothing is kept; else it is kept (the last 50 in memory
           and as specifications in rs3/pages/, so a restarted server builds it again) as /page/KEY.html.
    view   {do: 'view', path, show?}   -> {ok, hash, url, path}
           open one file, by its ./ path, as a commentable page (/code/...): methods, code, comment box.
Routes (HTTP GET)
    /reportserver        (or any path that starts with reportserver, or /?reportserver; the rest is ignored) the monitor page of the
                         server: file tree, status, log, stop, restart
    /?layout=...         a page that its address makes
    /code/mumix/x.py     the viewer of one file (a ./ path without the ./)
    /page/KEY.html       a page made by load and kept
    anything else        404 ('/' alone 403)

The page table is S['pages'] (rs3table). A page that is an address is put in it when it is served and when it says
hello (register_url), so a page whose server restarted finds its place again.

VERSION  M2 m01.v04 (2026-11-04): the viewer takes the methods block's own width; the page carries html/table.js and table.css.
         M2 m01.v03 (2026-11-04): the block of a locator comes from rs3layout.blocks (kind.suffix, definitions at the end); the status bar is a row added by parse(below=).
         M2 m01.v02 (2026-11-04): the panes of a page say where they sit, their blk{} list, what they take and hold (no where/TARGETS); a blk{} list is checked; a report that breaks the doc rules is served as its own page.
         M2 m01.v01 (2026-11-04): the address code is rs3util's, the page table rs3table's, the path rules pathof's;
         no file pages (a report is a doc block: /?layout=[doc]&doc=...); a block's sizes come from its write().
         M1 m01.v01 (2026-11-03): first version.
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

import rs3layout
from rs3util import address, asset, pathof

__all__ = ['VERBS', 'ROUTES', 'register_url']

HOST = '127.0.0.1'
HERE = os.path.dirname(os.path.abspath(__file__))
PANES = os.path.join(HERE, 'panes')
PAGE = os.path.join(HERE, 'html')                 # the page itself: page.html, page.css, manager.js, table.js, table.css, selftest.js
if PANES not in sys.path:                   # the blocks are modules of that folder
    sys.path.insert(0, PANES)
KEEP = 50                                   # built pages kept in memory, and specifications kept on disk
PAGES = os.path.join(HERE, 'pages')         # what load was given, for each page: a page survives a restart
MONITOR = ('[ftv, [serverstatus ; log]]', {})
VIEWER = '[methods, [code ; editbox wx35d]]'
ICON = 'data:image/svg+xml,' + quote(asset(os.path.join(PAGE, 'favicon.svg'), 'svg').strip(), safe='/:=,')   # the seven-dot ring, the tab icon of every page
MAX_TABS = 500                              # the files one block's data may name, patterns opened
ROUTED = ('commentline', 'commentselect', 'saved')   # the signals that go to one block, the nearest (manager.js), or the list of blk{a,b}
STATUSBAR = 'statusbar wx7'                 # added as the last row of every page that does not name its own
BLOCK = re.compile(r'^[a-z]{1,20}$')
TOKEN = re.compile(r'@@(\w+)@@')


def module_of(block):
    """The module of a block: rs_primary/panes/pane_NAME.py, by name only (no path can be given)."""
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


def opened(data):
    """The data of a block with its patterns opened: a ./ path with * ? or {} in it is the files it names (rs3util.pathof),
    anything else as it is."""
    out = []
    for item in data:
        if isinstance(item, str) and item.startswith('./') and any(c in item for c in '*?{'):
            out.extend(path for path in pathof(item, limit=MAX_TABS)[:MAX_TABS] if path not in out)
        else:
            out.append(item)
    return out


def listed(loc, to, specs_of, gave):
    """The `blk{a,b}` list of a block must name blocks that take what it sends: a file (mngshowfile, to blocks that
    take files) or a routed signal (to blocks that listen to it). ValueError says which does not."""
    sent = module_of(specs_of[loc][0]).OUT
    for target in to:
        heard = module_of(specs_of[target][0]).IN
        files = 'mngshowfile' in sent and gave[target]['takes']
        routed = any(name in sent and name in heard for name in ROUTED)
        if not (files or routed):
            raise ValueError(f'{loc}{{{",".join(to)}}}: {target} takes nothing that {loc} sends to one block')


def build(S, page, layout, specs, title, selftest=False):
    """The html of a page: see the module header. ValueError says what is wrong with the layout
    or a block. The sizes the blocks gave are left in page['sizes'] ({locator: (width, height)})."""
    tree = rs3layout.parse(layout)
    if 'statusbar' not in rs3layout.names(tree):          # every page has the status bar: the layout cannot lose it
        tree = rs3layout.parse(layout, below=STATUSBAR)
    html_of, parts, panes, sizes = {}, [], [], {}
    locs = rs3layout.names(tree)
    block_of = rs3layout.blocks(tree)
    specs_of = {loc: specs.get(loc) or [block_of[loc]] for loc in locs}
    specs_of = {loc: [spec] if isinstance(spec, str) else list(spec) for loc, spec in specs_of.items()}
    specs_of = {loc: spec[:1] + opened(spec[1:]) for loc, spec in specs_of.items()}
    places, wanted = rs3layout.places(tree), rs3layout.receivers(tree)
    gave = {}
    for loc in locs:
        block, data = specs_of[loc][0], specs_of[loc][1:]
        try:
            module = module_of(block)
        except ValueError as error:
            raise ValueError(f'{loc!r}: {error}' + (f' (define it at the end of the layout, like {{{loc}=code}})' if block == loc else ''))
        gave[loc] = module.write(*data, S=S, page=page, loc=loc)
    held = {got['holds'] for got in gave.values() if got['holds']}      # blocks that another takes over: only a place to show
    for loc, to in wanted.items():
        listed(loc, to, specs_of, gave)
    for loc in locs:
        block, got = specs_of[loc][0], gave[loc]
        if got['width'] or got['height']:                # its own size, where the layout gives none
            sizes[loc] = (got['width'], got['height'])
        html_of[loc] = got['html']
        parts.append((got['label'] or block, got['css'], got['js']))
        parts.extend(got.get('also', []))        # blocks this one makes inside itself (toptabs: code)
        panes.append({'loc': loc, 'block': block, 'at': places[loc], 'to': wanted.get(loc, []), 'takes': got['takes'],
                      'holds': got['holds'], 'hosted': block in held, 'search': got['search']})
    page['sizes'] = sizes
    css, js = collate(parts)
    info = {'hash': page['hash'], 'address': page['path'], 'title': title, 'port': S['port'],
            'admin': bool(page.get('admin')), 'panes': panes, 'routed': list(ROUTED),
            'config': S['verbs']['config']({}, S)['config']}
    fill = {'title': title.replace('<', '&lt;'), 'icon': ICON, 'pagecss': asset(os.path.join(PAGE, 'page.css'), 'css') + '\n' + asset(os.path.join(PAGE, 'table.css'), 'css'),
            'css': css, 'body': rs3layout.render(tree, html_of, defaults=sizes),
            'page': script_safe(json.dumps(info)), 'manager': asset(os.path.join(PAGE, 'manager.js'),
                                                                     'js') + '\n' + asset(os.path.join(PAGE, 'table.js'), 'js'),
            'js': script_safe(js + ('\n' + asset(os.path.join(PAGE, 'selftest.js'), 'js')
                                    + '\nRS.selftest();' if selftest else ''))}
    template = asset(os.path.join(PAGE, 'page.html'), 'html')
    return TOKEN.sub(lambda m: fill.get(m.group(1), ''), template)


def address_of(rel):
    """The address of the viewer of a ./ path."""
    return '/code/' + quote(rel[2:], safe='/')


def viewer_page(S, path_of_address):
    """(page record, layout, specs, title) of a viewer address, or None. The page's root is the root of its file."""
    path = './' + unquote(path_of_address[len('/code/'):])
    real = pathof(path, kinds=('code', 'md', 'text'))
    root = pathof('./', start=real) if real else None
    clean = pathof(real) if real else None
    if root is None or clean is None:
        return None
    page = S['pages'].view(path_of_address, root)
    specs = {'code': ['code', clean], 'methods': ['methods', clean]}
    return page, VIEWER, specs, os.path.basename(clean)


def is_monitor(path, query=''):
    """Is this address the report server page? Any path that starts with reportserver is (/reportserver, /reportserver%20?layout=..,
    /reportserver/x), and so is /?reportserver followed by any text (/?reportserver=1): the rest is ignored, and all are
    the same page."""
    return path.lstrip('/').startswith('reportserver') or (path == '/' and query.startswith('reportserver'))


def register_url(S, url):
    """The page record for an address a page says it was served from, or None."""
    if is_monitor(*url.partition('?')[::2]):
        return S['pages'].view('/reportserver', admin=True)
    if url.startswith('/?') or re.fullmatch(r'/page/[0-9a-f]{12}\.html', url):
        return S['pages'].view(url)
    if url.startswith('/code/'):
        got = viewer_page(S, url)
        return got[0] if got else None
    return None


def keep(S, key, html):
    S['built'][key] = html
    for old in list(S['built'])[:-KEEP]:
        del S['built'][old]


def save_spec(key, layout, blocks, title, selftest):
    """Keep what load was given (layout, blocks, title) in pages/KEY.json, the newest KEEP of them: the page is built
    from it again, with the code and styles of the day, when a restarted server is asked for it."""
    os.makedirs(PAGES, exist_ok=True)
    path = os.path.join(PAGES, key + '.json')
    with open(path + '.tmp', 'w', encoding='utf-8') as f:
        json.dump({'layout': layout, 'blocks': blocks, 'title': title, 'selftest': selftest}, f)
    os.replace(path + '.tmp', path)
    older = sorted((os.path.join(PAGES, n) for n in os.listdir(PAGES) if n.endswith('.json')), key=os.path.getmtime)
    for gone in older[:-KEEP]:
        try:
            os.remove(gone)
        except OSError:
            pass


def rebuilt(S, key):
    """The html of a page made by load before the server was restarted, built again from its kept specification, or
    None when there is none."""
    try:
        with open(os.path.join(PAGES, key + '.json'), encoding='utf-8') as f:
            spec = json.load(f)
    except (OSError, ValueError):
        return None
    page = S['pages'].view(f'/page/{key}.html')
    html = build(S, page, spec['layout'], spec['blocks'], spec['title'], bool(spec.get('selftest')))
    keep(S, key, html)
    return html


def show(S, url, wanted):
    if wanted:
        try:
            webbrowser.open(url)
        except Exception as error:
            S['say'](f'the browser would not open {url}: {error!r}')


def where(S, path_of_address):
    return f'http://{HOST}:{S["port"]}{path_of_address}'


def load(msg, S):
    layout, blocks = msg.get('layout'), msg.get('blocks') or {}
    title = msg.get('title') or 'report'
    if not isinstance(layout, str) or not isinstance(blocks, dict) or not isinstance(title, str):
        return {'ok': False, 'error': 'load takes a layout string, a blocks dict and a title'}
    selftest = bool(msg.get('selftest'))
    probe = {'hash': '', 'path': ''}
    try:
        build(S, probe, layout, blocks, title[:200], selftest)              # (once, to say what is wrong with it)
    except (ValueError, TypeError, KeyError) as error:
        return {'ok': False, 'error': str(error)}
    named = address(layout, blocks, msg.get('title') or '', selftest, probe['sizes'])
    if named:                                       # an address that makes the page again: nothing to keep
        page = S['pages'].view(named)
        url = where(S, named)
        show(S, url, msg.get('show', True))
        return {'hash': page['hash'], 'url': url, 'path': named}
    key = hashlib.sha1(f'{layout}{json.dumps(blocks, sort_keys=True)}{time.time()}'
                       .encode('utf-8')).hexdigest()[:12]
    path = f'/page/{key}.html'
    page = S['pages'].view(path)
    html = build(S, page, layout, blocks, title[:200], selftest)
    keep(S, key, html)
    save_spec(key, layout, blocks, title[:200], selftest)
    url = where(S, path)
    show(S, url, msg.get('show', True))
    return {'hash': page['hash'], 'url': url, 'path': path}


def view(msg, S):
    real = pathof(msg.get('path'), kinds=('code', 'md', 'text'))
    clean = pathof(real) if real else None
    if clean is None:
        return {'ok': False, 'error': 'not a file a page may show'}
    path = address_of(clean)
    page = viewer_page(S, path)[0]
    url = where(S, path)
    show(S, url, msg.get('show', True))
    return {'hash': page['hash'], 'url': url, 'path': path}


def alone(layout, specs):
    """The bytes of a report file when the page is only a doc of it and its script does not keep the rules of the
    doc box (pane_doc.prepare): such a file is served as it is, its own page with no rs3 around it (it may still call
    the server the way the old reports do). None for any other page."""
    data = specs.get('doc', [])[1:]
    if layout.strip() != '[doc]' or len(data) != 1 or not data[0].startswith('./'):
        return None
    if not module_of('doc').prepare(*data)[4]:
        return None
    with open(pathof(data[0], kinds=('html',)), 'rb') as f:
        return f.read()


def page_reply(html):
    return 200, html.encode('utf-8'), 'text/html; charset=utf-8'


def get(req, S):
    """GET: the monitor, a page made by its address, a viewer, or a page made by load."""
    path = req['path']
    try:
        if is_monitor(path, req['query']):
            page = S['pages'].view('/reportserver', admin=True)
            layout, specs = MONITOR
            return page_reply(build(S, page, layout, {**specs}, 'rs3 monitor', 'selftest=1' in req['query']))
        if path == '/' and req['query']:                         # a page that its address makes: see rs3util.address
            layout, specs, title, selftest = address('/?' + req['query'])
            own = alone(layout, specs)
            if own:                                              # a report that keeps no rules of the box: its own page
                return 200, own, 'text/html; charset=utf-8'
            page = S['pages'].view('/?' + req['query'])
            return page_reply(build(S, page, layout, specs, title, selftest))
        if path.startswith('/code/'):
            got = viewer_page(S, path)
            if got is None:
                return 404, b'', None
            page, layout, specs, title = got
            return page_reply(build(S, page, layout, specs, title, 'selftest=1' in req['query']))
        found = re.fullmatch(r'/page/([0-9a-f]{12})\.html', path)
        if found:
            html = S['built'].get(found.group(1)) or rebuilt(S, found.group(1))
            return page_reply(html) if html else (404, b'', None)
    except (ValueError, TypeError, KeyError) as error:
        S['say'](f'GET {path}: {error}')
        return 500, str(error).encode('utf-8'), 'text/plain; charset=utf-8'
    return (403 if path == '/' else 404), b'', None


VERBS = {'load': load, 'view': view}
ROUTES = {'GET': get}
