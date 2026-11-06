r"""rsfiles.py -- the verbs that read or write files, and the one place for the scope rule.

Paths. Every path in a message or a reply is "./..." from the root of the server, the folder
that holds .claude, always with / (page_path checks one: it must start ./, hold no .. or
backslash or drive letter, and name an existing file inside the root that is a page, a
report name, or a file vcomment opens). A URL cannot carry "./", so GET /mumix/x.html means
./mumix/x.html.

The hash. A page is known by its hash: a short digest of its ./ path (path_hash), the same
every time, so a path and its hash are interchangeable and the server keeps only the hash. It
is not a secret. page_path checks a path once, when a page says hello or is loaded, and
register puts it in S['pages'] (hash -> {id, hash, path, abs, root}); from then on a hash is a
plain lookup. The table is only a memory: a page says hello again after a reconnect, gets the
same hash, and a restart loses nothing.

Verbs (websocket; each takes the page's hash)
    tree    {do: 'tree', hash}   -> {root, name, files: [{p, k, s}]}
            the files of the page's root, git-aware (vcserver.listing): p the ./ path, k code
            | md | text | html | other | big, s the bytes
    list    {do: 'list', hash}   -> {reports: [{file, when}]}
            the other reports of the page's series, in its folder, newest first
Routes (HTTP, one request per connection)
    GET  /mumix/results/page.html   the page: an .html or .result file inside the root
    POST /post/NAME.svg             a posted SVG, kept in .rsposts/ beside the page whose hash
                                    comes in the X-Rs-Token header: written to a temp file,
                                    then renamed into place, so a reader never sees half a
                                    file; NAME is plain letters, digits . _ -; the body must
                                    start like an SVG and hold no <script; at most 8 MB.
                                    Replies {ok, path, bytes}.

The scope rule. scope_of(path) is the nearest folder above a path that holds .git or .claude,
or is one name below the drive root (C:\name), and never the drive root itself. It is the
root a page may reach. Other handlers ask this module; none re-implements it.

VERSION  M1 m02.v01 (2026-11-03): ./ paths from the root; the hash is a digest of the path and
         the table is filled by register (hello, load); GET paths are root-relative.
         M1 m01.v01 (2026-11-03): first version: scope_of, tree, list, GET, POST.
"""
import hashlib
import json
import os
import re
import time
from urllib.parse import unquote

import vcserver

MAX_POST = 8 * 1024 * 1024
PAGE_KINDS = ('.html', '.result')
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


def inside(path, root):
    """Is the real path inside root (or root itself)?"""
    try:
        return os.path.commonpath([os.path.realpath(path), os.path.realpath(root)]) == \
            os.path.realpath(root)
    except ValueError:                       # another drive
        return False


def path_hash(path):
    """The hash of a ./ path: sixteen hex digits of its sha1."""
    return hashlib.sha1(path.encode('utf-8')).hexdigest()[:16]


def real_of(S, path):
    """The real file of a ./ path, if the form is right and it is inside the root, else None.
    No check that it exists or what it is: page_path does that."""
    if not isinstance(path, str) or not path.startswith('./') or len(path) > 400:
        return None
    parts = path[2:].split('/')
    if any(part in ('', '.', '..') for part in parts) or '\\' in path or ':' in path:
        return None
    real = os.path.realpath(os.path.join(S['root'], *parts))
    return real if inside(real, S['root']) else None


def page_path(S, path):
    """The clean ./ path of a page or file a page shows, or None: see real_of, and the file
    must exist and be a page (a report name) or a file vcomment opens."""
    real = real_of(S, path)
    if real is None or not os.path.isfile(real):
        return None
    if not (NAME.match(os.path.basename(real))
            or vcserver.vclang.kind_of(real) in ('code', 'md', 'text')):
        return None
    return './' + os.path.relpath(real, os.path.realpath(S['root'])).replace(os.sep, '/')


def register(S, path):
    """Put a checked ./ path in the table (or find it there); its entry, None if the path is
    not one page_path accepts."""
    clean = page_path(S, path)
    if clean is None:
        return None
    real = real_of(S, clean)
    key = path_hash(clean)
    page = S['pages'].get(key)
    if page is None:
        page = {'id': S['next_id'], 'hash': key}
        S['next_id'] += 1
        S['pages'][key] = page
    page['path'] = clean
    page['abs'] = real
    page['root'] = scope_of(real)
    return page if page['root'] is not None else None


def page_of(S, key):
    """(page, None) for a hash the table knows and whose file is still there, else
    (None, why)."""
    page = S['pages'].get(key) if isinstance(key, str) else None
    if page is None:
        return None, 'unknown page: it must say hello (or be loaded) first'
    if not os.path.isfile(page['abs']):
        return None, 'the page file is gone'
    return page, None


def relative(S, absolute):
    """The ./ path from the root of an absolute path inside it."""
    return './' + os.path.relpath(absolute, os.path.realpath(S['root'])).replace(os.sep, '/')


def tree(msg, S):
    page, why = page_of(S, msg.get('hash'))
    if page is None:
        return {'ok': False, 'error': why}
    root = page['root']
    base = relative(S, root)
    files = vcserver.listing(root)
    for entry in files:                      # p was from the repository root: now from ours
        entry['p'] = base + '/' + entry['p']
    return {'root': base, 'name': os.path.basename(root) or root, 'files': files}


def series(msg, S):
    page, why = page_of(S, msg.get('hash'))
    if page is None:
        return {'ok': False, 'error': why}
    mine = os.path.basename(page['abs'])
    stem = NAME.match(mine).group('stem')
    found = []
    for other in os.listdir(os.path.dirname(page['abs'])):
        got = NAME.match(other)
        if got and got.group('stem') == stem and other != mine:
            found.append((got.group('when'), other))
    found.sort(reverse=True)                 # 09;50.07 after 09;50: by time
    return {'reports': [{'file': name, 'when': when} for when, name in found]}


def get(req, S):
    """GET /mumix/results/page.html: the page. The path is percent-decoded once and is from the
    root; a second layer of encoding, a backslash, a colon, a dot segment or an empty segment
    is refused."""
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
    if page is None:
        return answer(403, {'ok': False, 'error': why})
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
ROUTES = {'GET': get, 'POST': post}
