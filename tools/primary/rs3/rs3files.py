r"""rs3files.py -- the verbs that read files, the page table, the scope rule and the POST route.

Paths. Every path in a message or a reply is "./..." from the root of the server, the folder
that holds .claude, always with / (real_of checks one: it must start ./, hold no .. or
backslash or drive letter, and name a place inside the root). A URL cannot carry "./", so
GET /mumix/x.html means ./mumix/x.html.

The hash. A page is known by its hash: a short digest of its path (path_hash), the same every
time, so a restart loses nothing. The path is a ./ file path for a page that is a file, or the
page's own address for a page the server builds (/reportserver, /code/mumix/x.py, /page/KEY).
register (a file) and register_view (an address) put the page in S['pages']
(hash -> {id, hash, path, abs, root, admin}); a page says hello again after a reconnect.

Verbs (websocket; each takes the page's hash)
    tree    {do: 'tree', hash}   -> {root, name, files: [{p, k, s}]}
            the text files of the page's root, git-aware (listing below): p the ./ path,
            k code | md | text | html, s the bytes. Other kinds and big files are left out.
    list    {do: 'list', hash}   -> {reports: [{file, when}]}
            the other reports of the page's series, in its folder, newest first
Route (HTTP) POST /post/NAME.svg   a posted SVG, kept in .rsposts/ beside the page whose hash is
            in the X-Rs-Token header: written to a temp file, then renamed into place; NAME is
            plain letters, digits . _ -; the body must start like an SVG and hold no <script;
            at most 8 MB. Replies {ok, path, bytes}.
    get_file(request, S) is the GET of a file page (an .html or .result inside the root);
    rs3pages.py owns the GET route and calls it.

The scope rule. scope_of(path) is the nearest folder above a path that holds .git or .claude,
or is one name below the drive root (C:\name), and never the drive root itself. It is the
root a page may reach. Other handlers ask this module; none re-implements it.

VERSION  M2 m01.v01 (2026-11-03): rs3: pages that are addresses (register_view), tree keeps
         only text kinds, GET is rs3pages'.
         (rs2 rsfiles m02.v01: ./ paths from the root; the hash is a digest of the path.)
"""
import hashlib
import json
import os
import re
import subprocess
import time
from urllib.parse import unquote

MAX_POST = 8 * 1024 * 1024
MAX_BYTES = 4 * 1024 * 1024                 # a source file longer than this is not opened
WALK_MAX = 20000                            # files a walk (no git) lists at most
PAGE_KINDS = ('.html', '.result')
SHOWN = ('code', 'md', 'text', 'html')
KINDS = {'.html': 'html', '.htm': 'html', '.md': 'md', '.mu': 'md', '.txt': 'text'}     # what the tree shows, by extension
KINDS.update({ext: 'code' for ext in ('.py .pyx .pxd .pxi .js .mjs .css .m .vba .vb .bas .cls .frm').split()})
HIDDEN = {'__pycache__', 'venv', '.venv', 'env', 'node_modules', '.git', '.mypy_cache',
          '.pytest_cache', '.idea', '.vscode', 'site-packages', '_tmp'}
SHOWN_DOT = {'.claude'}                     # the one folder with a dot that the tree shows
JUNK = ('.pyc', '.pyo', '.tmp')
NAME = re.compile(r'^(?P<stem>[A-Za-z0-9_.\-]{1,60})_(?P<when>\d{4}\.\d\d\.\d\d_\d\d;\d\d'
                  r'(?:\.\d\d)?[a-z]{0,2})\.(?:html|result)$')
POST_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._\-]{0,79}\.svg$')


def scope_of(path):
    """The nearest folder above path that holds .git or .claude, or is one name below the
    drive root; None for the drive root itself. See the module header."""
    here = os.path.abspath(path)
    if os.path.isfile(here):
        here = os.path.dirname(here)
    while True:
        parent = os.path.dirname(here)
        if parent == here:
            return None
        if (os.path.exists(os.path.join(here, '.git'))
                or os.path.isdir(os.path.join(here, '.claude'))
                or os.path.dirname(parent) == parent):
            return here
        here = parent


def kind_of(path):
    """code, md, text or html by the extension, '' for a file the tree does not show. The tree knows no
    language: this is a table of extensions and nothing more."""
    return KINDS.get(os.path.splitext(path)[1].lower(), '')


def inside(path, root):
    """Is the real path inside root (or root itself)?"""
    try:
        return os.path.commonpath([os.path.realpath(path), os.path.realpath(root)]) == \
            os.path.realpath(root)
    except ValueError:                       # another drive
        return False


def path_hash(path):
    """The hash of a path or address: sixteen hex digits of its sha1."""
    return hashlib.sha1(path.encode('utf-8')).hexdigest()[:16]


def real_of(S, path):
    """The real file of a ./ path, if the form is right and it is inside the root, else None.
    No check that it exists or what it is."""
    if not isinstance(path, str) or not path.startswith('./') or len(path) > 400:
        return None
    parts = path[2:].split('/')
    if any(part in ('', '.', '..') for part in parts) or '\\' in path or ':' in path:
        return None
    real = os.path.realpath(os.path.join(S['root'], *parts))
    return real if inside(real, S['root']) else None


def relative(S, absolute):
    """The ./ path from the root of an absolute path inside it."""
    rel = os.path.relpath(absolute, os.path.realpath(S['root'])).replace(os.sep, '/')
    return '.' if rel == '.' else './' + rel


def page_path(S, path):
    """The clean ./ path of a page or file a page shows, or None: see real_of, and the file
    must exist and be a page (a report name) or a file vcomment opens."""
    real = real_of(S, path)
    if real is None or not os.path.isfile(real):
        return None
    if not (NAME.match(os.path.basename(real)) or kind_of(real) in ('code', 'md', 'text')):
        return None
    return relative(S, real)


def visible(rel):
    """Whether a path (from the root, with /) is shown: not in .git, a cache or an environment, not
    a folder with a dot (except .claude), not compiled junk."""
    parts = rel.split('/')
    for folder in parts[:-1]:
        if folder in HIDDEN or (folder.startswith('.') and folder not in SHOWN_DOT):
            return False
    return not parts[-1].lower().endswith(JUNK) and parts[-1] not in ('Thumbs.db', 'Desktop.ini',
                                                                       '.DS_Store')


def reachable(root, real):
    """The real path of a source file a page whose scope is `root` may open and comment, else
    None: inside root once links are followed, a file of a kind the tree shows,
    not over MAX_BYTES. (A file git ignores is not in the tree but can be opened by name.)"""
    top = os.path.realpath(root)
    real = os.path.realpath(real)
    if not inside(real, top) or not os.path.isfile(real) or os.path.getsize(real) > MAX_BYTES:
        return None
    rel = os.path.relpath(real, top).replace(os.sep, '/')
    if not visible(rel) or kind_of(real) not in ('code', 'md', 'text'):
        return None
    return real


def located(S, msg, field):
    """(page, real path, None) of the page of msg's hash and the source file msg[field] names (a
    ./ path), or (None, None, {ok: false, error}) when either is not allowed."""
    page, why = page_of(S, msg.get('hash'))
    if page is None:
        return None, None, {'ok': False, 'error': why}
    path = msg.get(field)
    real = real_of(S, path)
    if real is None:
        return None, None, {'ok': False, 'error': f'{path!r} is not a ./ path inside the root'}
    real = reachable(page['root'], real)
    if real is None:
        return None, None, {'ok': False, 'error': f'{path} is not a file this page may open'}
    return page, real, None


def entry(S, key, path):
    page = S['pages'].get(key)
    if page is None:
        page = {'id': S['next_id'], 'hash': key, 'admin': False}
        S['next_id'] += 1
        S['pages'][key] = page
    page['path'] = path
    return page


def register(S, path):
    """Put a checked ./ file path in the table (or find it there); its entry, None if the path
    is not one page_path accepts."""
    clean = page_path(S, path)
    if clean is None:
        return None
    real = real_of(S, clean)
    page = entry(S, path_hash(clean), clean)
    page['abs'] = real
    page['root'] = scope_of(real)
    return page if page['root'] is not None else None


def register_view(S, address, root, admin=False):
    """Put a page that is an address (made by the server, no file) in the table."""
    page = entry(S, path_hash(address), address)
    page['abs'] = None
    page['root'] = root
    page['admin'] = admin
    return page


def page_of(S, key):
    """(page, None) for a hash the table knows (and whose file is still there), else
    (None, why)."""
    page = S['pages'].get(key) if isinstance(key, str) else None
    if page is None:
        return None, 'unknown page: it must say hello (or be loaded) first'
    if page['abs'] is not None and not os.path.isfile(page['abs']):
        return None, 'the page file is gone'
    return page, None


def names_of(root):
    """The files of the repository: git's list (tracked, and untracked but not ignored), else a
    walk that stops after WALK_MAX files."""
    flags = 0x08000000 if os.name == 'nt' else 0          # no console window from the server
    try:
        got = subprocess.run(['git', '-C', root, 'ls-files', '-z', '-c', '-o',
                              '--exclude-standard'], capture_output=True, timeout=30,
                             creationflags=flags)
        if got.returncode == 0:
            return [x for x in got.stdout.decode('utf-8', 'replace').split('\0') if x]
    except (OSError, subprocess.SubprocessError):
        pass
    out = []
    for folder, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in HIDDEN
                         and not (d.startswith('.') and d not in SHOWN_DOT))
        for name in names:
            out.append(os.path.relpath(os.path.join(folder, name), root).replace(os.sep, '/'))
        if len(out) >= WALK_MAX:                          # a folder that is no project: stop
            break
    return out


def listing(root):
    """[{p, k, s}] of the files the tree shows, sorted: p the path from root with /, k the kind
    (kind_of: code, md, text, html, 'other'; 'big' for a source file over MAX_BYTES), s the
    bytes."""
    out = []
    for rel in sorted(set(names_of(root)), key=str.lower):
        if not visible(rel):
            continue
        try:
            size = os.path.getsize(os.path.join(root, rel))
        except OSError:
            continue                                      # tracked, but gone from the disk
        kind = kind_of(rel) or 'other'
        out.append({'p': rel, 'k': 'big' if kind in ('code', 'md', 'text') and size > MAX_BYTES
                    else kind, 's': size})
    return out


def tree(msg, S):
    page, why = page_of(S, msg.get('hash'))
    if page is None:
        return {'ok': False, 'error': why}
    root = page['root']
    files = []
    for folder in [root] + child_repos(root):
        base = relative(S, folder)
        for item in listing(folder):
            if item['k'] in SHOWN:           # p was from the repository root: now from ours
                item['p'] = './' + item['p'] if base == '.' else base + '/' + item['p']
                files.append(item)
    return {'root': relative(S, root), 'name': os.path.basename(root) or root, 'files': files}


def child_repos(root):
    """The folders directly under root that are repositories of their own (git lists a nested
    repository's files only for the repository itself), when root is not one of those."""
    if not os.path.isdir(os.path.join(root, '.git')) and not os.path.isdir(os.path.join(root, '.claude')):
        return []
    found = []
    for name in sorted(os.listdir(root)):
        if os.path.isdir(os.path.join(root, name, '.git')):
            found.append(os.path.join(root, name))
    return found


def series(msg, S):
    page, why = page_of(S, msg.get('hash'))
    if page is None or page['abs'] is None:
        return {'ok': False, 'error': why or 'this page is not a report file'}
    mine = os.path.basename(page['abs'])
    found = []
    stem = NAME.match(mine)
    if stem is None:
        return {'reports': []}
    for other in os.listdir(os.path.dirname(page['abs'])):
        got = NAME.match(other)
        if got and got.group('stem') == stem.group('stem') and other != mine:
            found.append((got.group('when'), other))
    found.sort(reverse=True)                 # 09;50.07 after 09;50: by time
    return {'reports': [{'file': name, 'when': when} for when, name in found]}


def get_file(req, S):
    """GET /mumix/results/page.html: a file page. The path is percent-decoded once and is
    from the root; a second layer of encoding, a backslash, a colon, a dot segment or an empty
    segment is refused."""
    decoded = unquote(req['path'])
    if (not decoded.startswith('/') or '%' in decoded or '\\' in decoded or ':' in decoded
            or '\x00' in decoded):
        return 403, b'', None
    real = real_of(S, '.' + decoded)
    if real is None or os.path.splitext(real)[1].lower() not in PAGE_KINDS:
        return 403, b'', None
    if not os.path.isfile(real):
        return 404, b'', None
    if os.path.getsize(real) > MAX_POST:
        return 413, b'', None
    with open(real, 'rb') as f:
        return 200, f.read(), 'text/html; charset=utf-8'


def answer(code, body):
    return code, json.dumps(body).encode('utf-8'), 'application/json'


def sweep(folder):
    """Remove temp files a crash left in the folder: older than an hour."""
    now = time.time()
    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        try:
            if name.startswith('.') and name.endswith('.tmp') and now - os.path.getmtime(path) > 3600:
                os.remove(path)
        except OSError:
            pass


def post(req, S):
    """POST /post/NAME.svg with X-Rs-Token: keep the body in .rsposts beside the page."""
    found = re.fullmatch(r'/post/([^/]+)', req['path'])
    if found is None:
        return 404, b'', None
    name = found.group(1)
    if not POST_NAME.match(name):
        return answer(400, {'ok': False, 'error': 'the name is plain letters, digits . _ - and ends .svg'})
    page, why = page_of(S, req['headers'].get('x-rs-token'))
    if page is None or page['abs'] is None:
        return answer(403, {'ok': False, 'error': why or 'only a page that is a file may post'})
    body = req['body']
    start = body[:400].lstrip(b'\xef\xbb\xbf \t\r\n')
    if not (start.startswith(b'<svg') or start.startswith(b'<?xml')):
        return answer(400, {'ok': False, 'error': 'the body is not an SVG'})
    if b'<script' in body.lower():
        return answer(400, {'ok': False, 'error': 'an SVG with a script is refused'})
    folder = os.path.join(os.path.dirname(page['abs']), '.rsposts')
    os.makedirs(folder, exist_ok=True)
    sweep(folder)
    final = os.path.join(folder, name)
    temp = os.path.join(folder, f'.{name}.{os.getpid()}.{time.time_ns()}.tmp')
    with open(temp, 'wb') as f:
        f.write(body)
        f.flush()
        os.fsync(f.fileno())
    for attempt in range(5):                 # a reader that has the old file open can hold it
        try:
            os.replace(temp, final)
            break
        except OSError:
            if attempt == 4:
                os.remove(temp)
                return answer(409, {'ok': False, 'error': 'the file is in use, try again'})
            time.sleep(0.02)
    S['say'](f'post: {final} {len(body)} bytes')
    return answer(200, {'ok': True, 'path': relative(S, final), 'bytes': len(body)})


VERBS = {'tree': tree, 'list': series}
ROUTES = {'POST': post}
