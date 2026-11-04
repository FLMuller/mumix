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
    /reportserver        (or any path that starts with reportserver, or /?reportserver; the rest is ignored) the monitor page of the
                         server: file tree, status, log, stop, restart
    /code/mumix/x.py     the viewer of one file (a ./ path without the ./)
    /page/KEY.html       a page made by load (the last 50 are kept, in memory and as specifications in rs3/pages/:
                         a restarted server builds the page again from its specification)
    anything else        a file page (an .html or .result inside the root): rs3files.get_file

The pages table. A page that is an address (not a file) is put in S['pages'] when it is served and
when it says hello (register_url), so a page whose server restarted finds its place again.

VERSION  M1 m01.v01 (2026-11-03): first version.
"""
import hashlib
import fnmatch
import importlib
import json
import os
import re
import sys
import time
import webbrowser
from urllib.parse import parse_qs, quote, unquote, urlencode

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
KEEP = 50                                   # built pages kept in memory, and specifications kept on disk
PAGES = os.path.join(HERE, 'pages')         # what load was given, for each page: a page survives a restart
TARGETS = ('code', 'toptabs')               # the blocks a file can be sent to
MONITOR = ('[ftv, [serverstatus ; log]]', {})
VIEWER = '[methods 50dxh, [code ; editbox wx35d]]'
ICON = 'data:image/svg+xml,' + quote(asset(os.path.join(PAGE, 'favicon.svg'), 'svg').strip(), safe='/:=,')   # the seven-dot ring, the tab icon of every page
WILD_SCAN = 20000                           # the folder entries a wildcard looks at: a pattern over a huge folder stops here
MAX_TABS = 500                              # the files one block's data may name, wildcards opened
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


def wild(S, data):
    """The data of a block with its wildcards opened. A ./ path with * or ? in it is the files it matches, by name, that the
    tree would show (the same reach rules as opening a file): * and ? in a file name (./mumix/tools/primary/rs3/*.py) or in
    a folder name (./mumix/*/b_*.py), and ** for any number of folders below one (./mumix/tools/primary/rs3/**/*.js; a
    trailing ./mumix/tools/primary/rs3/** is every file below it). Folders the tree hides are not entered. A path with none
    is as it was, and a pattern that matches nothing gives nothing. Order: a folder's files, then its folders, by name."""
    out = []
    root = os.path.realpath(S['root'])
    for item in data:
        if not (isinstance(item, str) and item.startswith('./') and len(item) <= 400 and any(c in item for c in '*?')):
            out.append(item)
            continue
        parts = item[2:].split('/')
        if '' in parts or '.' in parts or '..' in parts or chr(92) in item or ':' in item:
            continue
        if parts[-1] == '**':
            parts.append('*')
        found, budget = [], [WILD_SCAN]
        _walk(S, root, '.', parts, found, budget)
        out.extend(path for path in found if path not in out)
        del out[MAX_TABS:]
    return out


def _walk(S, folder, rel, parts, found, budget):
    """Add to found the ./ paths below folder (the ./ path rel) that the segments in parts match: see wild."""
    head, rest = parts[0], parts[1:]
    try:
        with os.scandir(folder) as scan:
            entries = sorted(scan, key=lambda e: e.name.lower())
    except OSError:
        return
    budget[0] -= len(entries)
    if budget[0] < 0 or len(found) >= MAX_TABS:
        return
    if head == '**':                                     # no folder, then one more and again
        _walk(S, folder, rel, rest, found, budget)
    if not rest:
        for entry in entries:
            if entry.is_file() and fnmatch.fnmatch(entry.name, head):
                real = rs3files.reachable(S['root'], entry.path)
                if real is not None and rs3files.visible(relative(S, real)[2:]):
                    found.append(relative(S, real))
        return
    for entry in entries:
        if entry.is_dir(follow_symlinks=False) and (head == '**' or fnmatch.fnmatch(entry.name, head))                 and rs3files.visible(f'{rel[2:] + "/" if rel != "." else ""}{entry.name}/x'):
            _walk(S, entry.path, f'{rel}/{entry.name}', parts if head == '**' else rest, found, budget)


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
    specs_of = {loc: spec[:1] + wild(S, spec[1:]) for loc, spec in specs_of.items()}
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
    fill = {'title': title.replace('<', '&lt;'), 'icon': ICON, 'pagecss': asset(os.path.join(PAGE, 'page.css'), 'css'),
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


def split_top(text):
    """The text cut at the commas that are not inside braces."""
    parts, level, last = [], 0, 0
    for i, c in enumerate(text):
        if c == '{':
            level += 1
        elif c == '}':
            level -= 1
        elif c == ',' and level == 0:
            parts.append(text[last:i])
            last = i + 1
    parts.append(text[last:])
    return parts


def expand(text):
    """Shell brace expansion, in order: a/{b,c{d,e}}.py is a/b.py, a/cd.py, a/ce.py ({} nest; text with none is itself)."""
    level, start = 0, 0
    for i, c in enumerate(text):
        if c == '{':
            if level == 0:
                start = i
            level += 1
        elif c == '}' and level:
            level -= 1
            if level == 0:
                before, body, after = text[:start], text[start + 1:i], text[i + 1:]
                return [before + inner + tail for part in split_top(body) for inner in expand(part) for tail in expand(after)]
    return [text]


def paths_of(values):
    """The ./ paths of the values given for a block: each value is a comma-separated list, each item of it a path with
    shell braces if it likes (./a/{x,y}.py): the same paths, in the same order, as compact wrote them."""
    return [path for value in values for item in split_top(value) for path in expand(item) if path]


def factor(names):
    """The file names of one folder as short as braces can write them in the same order: names with the same stem and
    different extensions are stem.{ext,ext}, and neighbouring stems with the same extensions share them:
    pane_{code,ftv,log}.{css,js,py}. A name with a character the braces use is left as it is (None)."""
    if any(c in name for name in names for c in '{},&=#%'):
        return None
    runs = []                                        # (stem, [extensions]) for neighbours of one stem
    for name in names:
        stem, dot, ext = name.rpartition('.')
        stem, ext = (stem, ext) if dot and stem else (name, '')
        if runs and runs[-1][0] == stem:
            runs[-1][1].append(ext)
        else:
            runs.append((stem, [ext]))
    groups = []                                      # ([stems], [extensions]): neighbouring stems with the same extensions
    for stem, exts in runs:
        if groups and groups[-1][1] == exts:
            groups[-1][0].append(stem)
        else:
            groups.append(([stem], exts))
    written = []
    for stems, exts in groups:
        if len(stems) == 1:
            head = stems[0]
        else:
            prefix = os.path.commonprefix(stems)
            if len(prefix) >= 2 and all(len(s) > len(prefix) for s in stems):
                head = prefix + '{' + ','.join(s[len(prefix):] for s in stems) + '}'
            else:
                head = '{' + ','.join(stems) + '}'
        tail = '' if exts == [''] else '.' + (exts[0] if len(exts) == 1 else '{' + ','.join(exts) + '}')
        written.append(head + tail)
    return written[0] if len(written) == 1 else '{' + ','.join(written) + '}'


def compact(data):
    """The ./ paths of a block as one value, the common folder once and the rest in braces:
    ./mumix/tools/primary/{rs3.py,rs3/{SIGNALS.md,pane_{code,ftv}.{css,js}}}. Their order is kept, so paths_of gives
    them back as they were. The paths one by one, comma separated, when a name has a character braces use."""
    if len(data) == 1:
        return data[0]
    runs = []                                        # (folder, [names]) for neighbours in one folder
    for path in data:
        folder, name = path.rsplit('/', 1)
        if runs and runs[-1][0] == folder:
            runs[-1][1].append(name)
        else:
            runs.append((folder, [name]))
    common = []                                      # the folders' common part, by components (os.path would drop the ./)
    for parts in zip(*[folder.split('/') for folder, names in runs]):
        if any(part != parts[0] for part in parts):
            break
        common.append(parts[0])
    root = '/'.join(common)
    items = []
    for folder, names in runs:
        written = factor(names)
        if written is None:
            return ','.join(data)
        below = folder[len(root):].lstrip('/')
        items.append((below + '/' if below else '') + written)
    return root + '/' + (items[0] if len(items) == 1 else '{' + ','.join(items) + '}')


def plain_layout(layout, blocks):
    """The layout without the sizes that the blocks' own sizes make needless (see rs3layout.plain); the layout as it
    was given when it is not one."""
    def has_default(loc, direction):
        spec = blocks.get(loc)
        name = spec if isinstance(spec, str) else spec[0] if spec else None
        try:
            module = module_of(name or block_of(loc))
        except (ValueError, ImportError, KeyError):
            return False
        return bool(getattr(module, 'WIDTH' if direction == 'row' else 'HEIGHT', None))
    try:
        return rs3layout.plain(rs3layout.parse(layout), has_default)
    except ValueError:
        return layout


def page_url(layout, blocks, title='', selftest=False):
    """The address that makes a page again, /?layout=[ftv,[toptabs;code]]&toptabs=a/{x,y}.py (the paths start at the root: no ./), when the data of every
    block is ./ paths (all of a block's in one value, in shell braces: see compact, and * and ? in a file name opens at
    build time: see wild; a block that is not named like its
    locator says so: block.edit=editbox); None when some is not (a doc block holds html), or the address would be over 6000
    characters."""
    items = [('layout', plain_layout(layout, blocks).replace(' ', '_'))]                    # a space is written _ (not %20); query_page reads it back
    if title:
        items.append(('title', title.replace(' ', '_')))
    if selftest:
        items.append(('selftest', '1'))
    for loc, spec in blocks.items():
        spec = [spec] if isinstance(spec, str) else list(spec)
        if not spec or not isinstance(spec[0], str):
            return None
        block, data = spec[0], spec[1:]
        if not all(isinstance(d, str) and d.startswith('./') and len(d) <= 400 and not any(c in d for c in '{},') for d in data):
            return None
        if block != block_of(loc):
            items.append(('block.' + loc, block))
        if data:
            value = compact(data)
            items.append((loc, (value[2:] if value.startswith('./') else value).replace(',./', ',')))      # (the root is where every path starts)
    url = '/?' + urlencode(items, quote_via=quote, safe='/[];,(){}*')
    return url if len(url) <= 6000 else None


def query_page(query):
    """(layout, specs, title, selftest) of the address /?... : see page_url. ValueError says what is wrong."""
    q = parse_qs(query, keep_blank_values=True, max_num_fields=400)
    layout = q.get('layout', [''])[0].replace('_', ' ')                # (so a locator has no _ in it)
    if not layout:
        raise ValueError('a page address needs a layout: /?layout=[ftv,[toptabs;code]]&toptabs=./a.py')
    names = rs3layout.names(rs3layout.parse(layout))
    data = {loc: [(d if d.startswith('./') else './' + d)[:400] for d in paths_of(q.get(loc, []))[:500]] for loc in names}
    specs = {loc: [q.get('block.' + loc, [block_of(loc)])[0], *data[loc]] for loc in names}
    first = next((d for loc in names for d in data[loc]), '')
    title = q.get('title', [''])[0].replace('_', ' ') or (' + '.join(names) + (' - ' + first.rsplit('/', 1)[-1] if first else ''))
    return layout, specs, title[:200], q.get('selftest', ['0'])[0] == '1'


def is_monitor(path, query=''):
    """Is this address the report server page? Any path that starts with reportserver is (/reportserver, /reportserver%20?layout=..,
    /reportserver/x), and so is /?reportserver followed by any text (/?reportserver=1): the rest is ignored, and all are
    the same page."""
    return path.lstrip('/').startswith('reportserver') or (path == '/' and query.startswith('reportserver'))


def register_url(S, url):
    """The page record for an address a page says it was served from, or None."""
    if is_monitor(*url.partition('?')[::2]):
        return register_view(S, '/reportserver', S['root'], admin=True)
    if url.startswith('/?'):
        return register_view(S, url, S['root'])
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
    page = register_view(S, f'/page/{key}.html', S['root'])
    html = build(S, page, spec['layout'], spec['blocks'], spec['title'], bool(spec.get('selftest')))
    keep(S, key, html)
    return html


def show(S, url, wanted):
    if wanted:
        try:
            webbrowser.open(url)
        except Exception as error:
            S['say'](f'the browser would not open {url}: {error!r}')


def where(S, address):
    return f'http://{HOST}:{S["port"]}{address}'


def opened(spec):
    """A block's spec with the shell braces of its ./ paths opened ({py,md}): a path of any other kind (html, css, js
    text of a doc block) is as it was."""
    if not isinstance(spec, list) or not spec:
        return spec
    return spec[:1] + [path for item in spec[1:]
                       for path in (expand(item) if isinstance(item, str) and item.startswith('./') and '{' in item else [item])]


def load(msg, S):
    layout, blocks = msg.get('layout'), msg.get('blocks') or {}
    title = msg.get('title') or 'report'
    if not isinstance(layout, str) or not isinstance(blocks, dict) or not isinstance(title, str):
        return {'ok': False, 'error': 'load takes a layout string, a blocks dict and a title'}
    blocks = {loc: opened(spec) for loc, spec in blocks.items()}        # shell braces in ./ paths are opened here, as in an address
    named = page_url(layout, blocks, msg.get('title') or '', bool(msg.get('selftest')))
    if named:                                       # an address that makes the page again: nothing to keep
        try:
            lay, specs, name, selftest = query_page(named.split('?', 1)[1])
            page = register_view(S, named, S['root'])
            build(S, page, lay, specs, name, selftest)           # (once, to say what is wrong with it)
        except (ValueError, TypeError, KeyError) as error:
            return {'ok': False, 'error': str(error)}
        url = where(S, named)
        show(S, url, msg.get('show', True))
        return {'hash': page['hash'], 'url': url, 'path': named}
    key = hashlib.sha1(f'{layout}{json.dumps(blocks, sort_keys=True)}{time.time()}'
                       .encode('utf-8')).hexdigest()[:12]
    address = f'/page/{key}.html'
    page = register_view(S, address, S['root'])
    try:
        html = build(S, page, layout, blocks, title[:200], bool(msg.get('selftest')))
    except (ValueError, TypeError, KeyError) as error:
        return {'ok': False, 'error': str(error)}
    keep(S, key, html)
    save_spec(key, layout, blocks, title[:200], bool(msg.get('selftest')))
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
        if is_monitor(path, req['query']):
            page = register_view(S, '/reportserver', S['root'], admin=True)
            layout, specs = MONITOR
            return page_reply(build(S, page, layout, {**specs}, 'rs3 monitor',
                                    'selftest=1' in req['query']))
        if path == '/' and req['query']:                         # a page that its address makes: see page_url
            layout, specs, title, selftest = query_page(req['query'])
            page = register_view(S, '/?' + req['query'], S['root'])
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
    return rs3files.get_file(req, S)


VERBS = {'load': load, 'view': view}
ROUTES = {'GET': get}
