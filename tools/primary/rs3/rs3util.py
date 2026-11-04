r"""rs3util.py -- what the blocks and the server share: five names.

    asset(file, ext) -> str       the text of a file that sits beside a block: asset(__file__, 'js')
                                  reads pane_code.js for pane_code.py ('' if there is none)
    done(label, css, js, html, width=, height=, search=, takes=, holds=) -> dict
                                  what a block's write() returns: {label, css, js, html, width, height, search,
                                  takes, holds}. takes: the block shows files, so a file can be sent to it (code,
                                  toptabs); holds: the name of a block it takes over (toptabs holds code: a code
                                  block on its page is only the place its tabs show their file).
                                  width and height are the block's own size in mm where a layout gives none (a
                                  bare `ftv` is 75 mm wide); search is what the block can find for the status bar
                                  ('files', 'text', 'names', 'log')
    split_package(html) -> (html, css, js)   a static page as the server takes it apart: every <style> and
                                  <script> without a src comes out, in order, the rest is the html
    pathof(path, start=None, kinds=None, maxsize=None, limit=20000) -> str | None | Paths
                                  one path, either way, or the files a pattern names: see PATHS below
    address(source, blocks=None, title='', selftest=False, sizes=None) -> str | None | tuple
                                  a page as an address, or an address as a page: see ADDRESS below

A block is a Python function write(*data) -> done(...). Its css and js are labelled with the block's name; a page
that holds two blocks of one kind carries that css and js once.

PATHS. Every path in a message or an address is "./x/y" (or "x/y") from a root. The default root is HOME: the
parent of the repository that holds rs3 (the Claude folder), found once when this module loads (an error when rs3 is
in no repository). A path may name another root with `start`: any path, from which the root is found by walking up
to the nearest folder with .git or .claude (never the bare drive). The server's own folder is the server's business
(logs, pid, settings) and is no root here.
    pathof('./mumix/x.py')                 the real path, if it is a well formed path inside the root, else None:
                                           no '..', no empty or '.' part, no backslash or drive letter, at most 400
                                           characters, and still inside the root once links are followed
    pathof('C:/Claude/mumix/x.py')         the other way: './mumix/x.py', or None when it is outside the root
    pathof('./')                           the root itself (with start=<a path>: the root of that path)
    kinds=('code', 'md')                   the file must exist and be of one of these kinds (kind_of: code, md, text,
                                           html; the table below) ; maxsize=n: and at most n bytes
    pathof('./mumix/**/*.{py,md}')         a pattern (any of * ? ** {a,b}): the files it names, as a Paths (a list
                                           of './' paths with .truncated, and .kind and .size of each)
A pattern's * and ? are in a file name or in a folder name; ** is any number of folders; shell braces nest. The files
are those the tree shows: not in a folder called __pycache__, venv, env, node_modules, zprev ..., not in a folder
with a dot (except .claude), not junk (.pyc .tmp Thumbs.db), and not ignored by a .gitignore or .ignore on the way
(its patterns as git reads them: * ? ** [a-z] a leading / a trailing / and ! to take one back), tracked or not. A
folder's files come first, then its folders, by name. A path with no * ? in it is not looked up (a file the tree
hides can still be named); a pattern that names nothing gives an empty Paths. The walk stops at `limit` files and
says so (.truncated), so the server can tell the user that the list is not whole.

ADDRESS. A page whose blocks take './' paths (or nothing) is written as an address that makes it again:
    /?layout=[ftv,[toptabs;[methods,[code;editbox]]]]&toptabs=mumix/tools/primary/{rs3.py,rs3/**}
    address(layout, blocks, title, selftest, sizes)  -> that string, or None when the page cannot be written so (a
                       block holds html, a name has a comma, or the address passes 6000 characters). blocks is
                       {locator: [block, *data]}; sizes {locator: (width, height)} is what the blocks said they are
                       (done): a size that is a block's own is left out, so `ftv wdxh` is written `ftv`. Spaces are
                       written _ , the paths start at the root (no ./), the paths of a block are one value in shell
                       braces. The locators are written the short way when a page has several blocks of a kind and
                       the block's name when it has one (rs3layout.normal); one that does not say its block is
                       defined at the end of the layout, {cd3=code}.
    address('/?layout=...')  -> (layout, specs, title, selftest): the page, specs {locator: [block, *data]} with the
                       data as written (patterns still patterns: the page builder opens them with pathof).
                       ValueError says what is wrong.

VERSION  M2 m02.v01 (2026-11-04): locators written by rs3layout.normal, locators written by rs3layout.normal (eb.1), no &block.X=.
         M2 m01.v02 (2026-11-04): done() says what a block takes (files) and holds.
         M2 m01.v01 (2026-11-04): five names: pathof (the path rules of rs3files, the wildcard walk, the ignore rules,
         HOME) and address (rs3pages' page_url and query_page) join asset, done and split_package.
         M1 m01.v01 (2026-11-03): first version.
"""
import functools
import os
import re
from urllib.parse import parse_qs, quote, urlencode

import rs3layout

__all__ = ['asset', 'done', 'split_package', 'pathof', 'address']

STYLE = re.compile(r'<style\b[^>]*>(.*?)</style\s*>', re.S | re.I)
SCRIPT = re.compile(r'<script\b(?![^>]*\bsrc\s*=)[^>]*>(.*?)</script\s*>', re.S | re.I)

LIMIT = 20000                               # the files one walk lists at most
SCAN = 200000                               # the folder entries one walk looks at at most
MAX_PATH = 400
HIDDEN = {'__pycache__', 'venv', '.venv', 'env', 'node_modules', '.git', '.mypy_cache', '.pytest_cache', '.idea',
          '.vscode', 'site-packages', '_tmp', 'zprev'}         # folders the walk never enters (and every dot folder but .claude)
SHOWN_DOT = {'.claude'}
JUNK = ('.pyc', '.pyo', '.tmp')
JUNK_NAMES = ('thumbs.db', 'desktop.ini', '.ds_store')
KINDS = {'.html': 'html', '.htm': 'html', '.result': 'html', '.md': 'md', '.mu': 'md', '.txt': 'text'}
KINDS.update({ext: 'code' for ext in ('.py .pyx .pxd .pxi .js .mjs .css .m .vba .vb .bas .cls .frm').split()})
FLAGS = re.I if os.name == 'nt' else 0
ROOTS = {}                                  # folder -> its root, found by walking up once
ADDRESS_MAX = 6000


def asset(file, ext):
    """The text of the file beside `file` with the same name and the extension `ext`."""
    path = os.path.splitext(os.path.abspath(file))[0] + '.' + ext
    try:
        with open(path, encoding='utf-8') as f:
            return f.read()
    except OSError:
        return ''


def done(label, css='', js='', html='', width=None, height=None, search=None, takes=False, holds=None):
    """What write() returns."""
    return {'label': label, 'css': css, 'js': js, 'html': html, 'width': width, 'height': height, 'search': search,
            'takes': takes, 'holds': holds}


def split_package(html):
    """(html without them, all the css, all the js) of a page that carries its own <style> and
    <script> blocks, wherever they sit. The ideal package has one of each; more are joined in
    order. A script with a src is left where it is (it cannot be collated)."""
    css = '\n'.join(m.group(1).strip() for m in STYLE.finditer(html))
    js = '\n'.join(m.group(1).strip() for m in SCRIPT.finditer(html))
    return SCRIPT.sub('', STYLE.sub('', html)), css, js


# ---- paths ------------------------------------------------------------------------------------------------------

def _home():
    """The parent of the repository that holds this file."""
    folder = os.path.dirname(os.path.abspath(__file__))
    while True:
        up = os.path.dirname(folder)
        if os.path.exists(os.path.join(folder, '.git')) and up != folder:
            return os.path.realpath(up)
        if up == folder:
            raise RuntimeError(f'rs3 is in no repository (no .git above {__file__}): there is no home for its paths')
        folder = up


HOME = _home()


class Paths(list):
    """The './' paths a pattern names, in order, with .truncated (the walk stopped at its limit) and, for each,
    .kind (code, md, text, html or other) and .size (bytes)."""

    def __init__(me):
        super().__init__()
        me.truncated = False
        me.kind = {}
        me.size = {}


def kind_of(path):
    """code, md, text or html by the extension, '' for a file of no kind the tree knows."""
    return KINDS.get(os.path.splitext(path)[1].lower(), '')


def _inside(path, root):
    try:
        return os.path.commonpath([os.path.normcase(path), os.path.normcase(root)]) == os.path.normcase(root)
    except ValueError:                       # another drive
        return False


def _root_of(start):
    """HOME for no start, else the nearest folder at or above start that holds .git or .claude, or is one name below
    the drive root; None for the drive root itself."""
    if start is None:
        return HOME
    here = os.path.realpath(start)
    if os.path.isfile(here):
        here = os.path.dirname(here)
    if here not in ROOTS:
        found, folder = None, here
        while True:
            up = os.path.dirname(folder)
            if up == folder:
                break
            if (os.path.exists(os.path.join(folder, '.git')) or os.path.isdir(os.path.join(folder, '.claude'))
                    or os.path.dirname(up) == up):
                found = folder
                break
            folder = up
        ROOTS[here] = found
    return ROOTS[here]


def _fits(real, root, kinds, maxsize):
    """kinds or maxsize given: the path must be a file the tree could show (it exists, of a kind asked for, not over maxsize,
    in no folder the walk never enters, not junk)."""
    if kinds is None and maxsize is None:
        return True
    if not os.path.isfile(real) or (kinds is not None and kind_of(real) not in kinds):
        return False
    parts = os.path.relpath(real, root).split(os.sep)
    if any(_hidden_folder(part) for part in parts[:-1]) or _hidden_file(parts[-1]):
        return False
    return maxsize is None or os.path.getsize(real) <= maxsize


def _short(real, root):
    rel = os.path.relpath(real, root).replace(os.sep, '/')
    return '.' if rel == '.' else './' + rel


def _single(path, root, kinds, maxsize):
    """pathof of one path with no pattern: the real path of a short one, the short one of a real one, or None."""
    if not isinstance(path, str) or not path or len(path) > MAX_PATH:
        return None
    if os.path.splitdrive(path)[0]:                      # real to short
        if not os.path.isabs(path):                      # C:x.py is on the drive but from no folder
            return None
        real = os.path.realpath(path)
        if not _inside(real, root) or not _fits(real, root, kinds, maxsize):
            return None
        return _short(real, root)
    text = path[2:] if path.startswith('./') else path
    if text in ('', '.'):
        real = root
    else:
        parts = text.split('/')
        if any(part in ('', '.', '..') for part in parts) or '\\' in text or ':' in text:
            return None
        real = os.path.realpath(os.path.join(root, *parts))
        if not _inside(real, root):
            return None
    return real if _fits(real, root, kinds, maxsize) else None


def _split_top(text):
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


def _expand(text):
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
                return [before + inner + tail for part in _split_top(body) for inner in _expand(part)
                        for tail in _expand(after)]
    return [text]


def _glob(pattern):
    """The regular expression text of a .gitignore glob (* ? ** [a-z])."""
    out, i, n = [], 0, len(pattern)
    while i < n:
        c = pattern[i]
        if c == '*':
            if pattern.startswith('**', i):
                i += 2
                if pattern.startswith('/', i):
                    out.append('(?:.*/)?')
                    i += 1
                else:
                    out.append('.*')
                continue
            out.append('[^/]*')
        elif c == '?':
            out.append('[^/]')
        elif c == '[' and pattern.find(']', i + 1) > 0:
            j = pattern.find(']', i + 1)
            body = pattern[i + 1:j]
            out.append('[' + ('^' + body[1:] if body.startswith('!') else body) + ']')
            i = j
        else:
            out.append(re.escape(c))
        i += 1
    return ''.join(out)


def _rules(folder):
    """[(regex, taken back, folders only)] of the .gitignore and .ignore in a folder, in order."""
    rules = []
    for name in ('.gitignore', '.ignore'):
        try:
            with open(os.path.join(folder, name), encoding='utf-8', errors='replace') as f:
                text = f.read()
        except OSError:
            continue
        for line in text.splitlines():
            line = line.rstrip()
            if not line or line.startswith('#'):
                continue
            back = line.startswith('!')
            line = line[1:] if back else line
            line = line[1:] if line.startswith('\\') else line
            folders = line.endswith('/')
            line = line.rstrip('/')
            if not line:
                continue
            anchored = '/' in line
            regex = ('^' if anchored else '^(?:.*/)?') + _glob(line.lstrip('/')) + '$'
            rules.append((re.compile(regex, FLAGS), back, folders))
    return rules


def _ignored(stack, rel, is_dir):
    """Do the rules on the way (a stack of (folder, rules)) ignore the path rel (from the root of the walk)? The last
    rule that matches decides."""
    ignored = False
    for base, rules in stack:
        sub = rel[len(base) + 1:] if base else rel
        for regex, back, folders in rules:
            if (is_dir or not folders) and regex.match(sub):
                ignored = not back
    return ignored


def _hidden_folder(name):
    return name in HIDDEN or (name.startswith('.') and name not in SHOWN_DOT)


def _hidden_file(name):
    return name.lower().endswith(JUNK) or name.lower() in JUNK_NAMES


def _walk(folder, rel, segments, got):
    """Add to got the files below folder (rel: its path from the root, '' for the root) that the pattern segments name."""
    head, rest = segments[0], segments[1:]
    try:
        with os.scandir(folder) as scan:
            entries = sorted(scan, key=lambda e: e.name.lower())
    except OSError:
        return
    got.scan -= len(entries)
    if got.scan < 0 or len(got) >= got.limit:
        got.truncated = True
        return
    rules = _rules(folder)
    if rules:
        got.stack.append((rel, rules))
    try:
        if head == '**':                                 # no folder, and then one and the same again
            _walk(folder, rel, rest, got)
        if not rest:
            for entry in entries:
                if got.truncated:
                    return
                if not entry.is_file() or not _match(entry.name, head) or _hidden_file(entry.name):
                    continue
                path = rel + '/' + entry.name if rel else entry.name
                kind = kind_of(entry.name) or 'other'
                if (got.kinds is not None and kind not in got.kinds) or _ignored(got.stack, path, False):
                    continue
                try:
                    size = entry.stat().st_size
                except OSError:
                    continue
                if got.maxsize is not None and size > got.maxsize:
                    continue
                if len(got) >= got.limit:
                    got.truncated = True
                    return
                _add(got, './' + path, kind, size)
            return
        for entry in entries:
            if got.truncated:
                return
            if entry.is_dir(follow_symlinks=False) and not _hidden_folder(entry.name) \
                    and (head == '**' or _match(entry.name, head)):
                path = rel + '/' + entry.name if rel else entry.name
                nested = os.path.exists(os.path.join(entry.path, '.git'))     # a repository of its own: its own rules, not the outer one's
                if nested or not _ignored(got.stack, path, True):
                    outer = got.stack
                    got.stack = [] if nested else outer
                    try:
                        _walk(entry.path, path, segments if head == '**' else rest, got)
                    finally:
                        got.stack = outer
    finally:
        if rules:
            got.stack.pop()


@functools.lru_cache(maxsize=512)
def _regex(pattern):
    return re.compile('^' + _glob(pattern) + '$', FLAGS)


def _match(name, pattern):
    return _regex(pattern).match(name) is not None


def _add(got, path, kind, size):
    if path not in got.kind:
        got.append(path)
        got.kind[path] = kind
        got.size[path] = size


def _pattern(path, root, kinds, maxsize, limit):
    got = Paths()
    got.limit, got.scan, got.stack, got.kinds, got.maxsize = limit, SCAN, [], kinds, maxsize
    for item in _expand(path):
        if len(item) > MAX_PATH:
            continue
        text = item[2:] if item.startswith('./') else item
        if not any(c in text for c in '*?'):             # a plain path of a list: as it is, not looked up
            real = _single(item, root, kinds, maxsize)
            if real is not None:
                short = _short(real, root)
                try:
                    _add(got, short, kind_of(real) or 'other', os.path.getsize(real))
                except OSError:
                    _add(got, short, 'other', 0)
            continue
        parts = text.split('/')
        if any(part in ('', '.', '..') for part in parts) or '\\' in text or ':' in text:
            continue
        if parts[-1] == '**':                            # a trailing ** is every file below
            parts.append('*')
        _walk(root, '', parts, got)
        if got.truncated:
            break
    return got


def pathof(path, start=None, kinds=None, maxsize=None, limit=LIMIT):
    """See PATHS in the module header. None when there is no root (a start with none above it) or the path is not one."""
    root = _root_of(start)
    if root is None:
        return None
    if isinstance(path, str) and any(c in path for c in '*?{'):
        return _pattern(path, root, kinds, maxsize, limit)
    return _single(path, root, kinds, maxsize)


# ---- addresses --------------------------------------------------------------------------------------------------

def _factor(names):
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


def _compact(data):
    """The ./ paths of a block as one value, the common folder once and the rest in braces:
    ./mumix/tools/primary/{rs3.py,rs3/{SIGNALS.md,pane_{code,ftv}.{css,js}}}. Their order is kept. The paths one by one,
    comma separated, when a name has a character braces use."""
    if len(data) == 1:
        return data[0]
    runs = []                                        # (folder, [names]) for neighbours in one folder
    for path in data:
        folder, name = path.rsplit('/', 1)
        if runs and runs[-1][0] == folder:
            runs[-1][1].append(name)
        else:
            runs.append((folder, [name]))
    common = []                                      # the folders' common part, by components
    for parts in zip(*[folder.split('/') for folder, names in runs]):
        if any(part != parts[0] for part in parts):
            break
        common.append(parts[0])
    root = '/'.join(common)
    items = []
    for folder, names in runs:
        written = _factor(names)
        if written is None:
            return ','.join(data)
        below = folder[len(root):].lstrip('/')
        items.append((below + '/' if below else '') + written)
    return root + '/' + (items[0] if len(items) == 1 else '{' + ','.join(items) + '}')


def _write(layout, blocks, title, selftest, sizes):
    try:
        tree = rs3layout.parse(layout)
    except ValueError:
        return None
    given = {loc: (spec if isinstance(spec, str) else spec[0]) for loc, spec in blocks.items()
             if isinstance(spec, str) or (spec and isinstance(spec[0], str))}
    tree, new = rs3layout.normal(tree, given)
    old = {name: loc for loc, name in new.items()}

    def has_default(loc, direction):
        width, height = (sizes or {}).get(old.get(loc, loc), (None, None))
        return bool(width if direction == 'row' else height)
    items = [('layout', rs3layout.plain(tree, has_default).replace(' ', '_'))]        # a space is written _ (not %20)
    if title:
        items.append(('title', title.replace(' ', '_')))
    if selftest:
        items.append(('selftest', '1'))
    for loc, spec in blocks.items():
        spec = [spec] if isinstance(spec, str) else list(spec)
        if not spec or not isinstance(spec[0], str):
            return None
        block, data = spec[0], spec[1:]
        if not all(isinstance(d, str) and d.startswith('./') and len(d) <= MAX_PATH for d in data):
            return None
        data = [path for d in data for path in _expand(d)]
        if any(c in path for path in data for c in '{},'):
            return None
        if data:
            value = _compact(data)
            items.append((new.get(loc, loc), (value[2:] if value.startswith('./') else value).replace(',./', ',')))
    url = '/?' + urlencode(items, quote_via=quote, safe='/[];,(){}*=')
    return url if len(url) <= ADDRESS_MAX else None


def _read(query):
    q = parse_qs(query, keep_blank_values=True, max_num_fields=400)
    layout = q.get('layout', [''])[0].replace('_', ' ')                # (so a locator has no _ in it)
    if not layout:
        raise ValueError('a page address needs a layout: /?layout=[ftv,[toptabs;code]]&toptabs=a/b.py')
    tree = rs3layout.parse(layout)
    names = rs3layout.names(tree)
    data = {}
    for loc in names:
        items = [item for value in q.get(loc, []) for item in _split_top(value) if item]
        data[loc] = [(item if item.startswith('./') else './' + item)[:MAX_PATH] for item in items[:500]]
    specs = {loc: [block, *data[loc]] for loc, block in rs3layout.blocks(tree).items()}
    first = next((d for loc in names for d in data[loc]), '')
    named = _expand(first)[0].rsplit('/', 1)[-1] if first else ''
    title = q.get('title', [''])[0].replace('_', ' ') or (' + '.join(names) + (' - ' + named if named else ''))
    return layout, specs, title[:200], q.get('selftest', ['0'])[0] == '1'


def address(source, blocks=None, title='', selftest=False, sizes=None):
    """See ADDRESS in the module header: an address string is read, anything else is a layout to be written."""
    if source.startswith('/?'):
        return _read(source[2:])
    return _write(source, blocks or {}, title, selftest, sizes)
