r"""vcserver.py -- the live verbs of vcomment, answered by the report server (reportserver.py).

The report server loads this module because its name is in reportserver.handlers (written by
vcomment.py), and asks `handler` about every message after the settings and before its own
report verbs. For a page that is not registered to a repository the handler answers None, and the
report server goes on as it always did.

    handler(S, msg, root, name, log) -> reply text, or None when the message is not ours

Which pages are ours is not a matter of their name: register(name, repository, folder) writes
the page into vcomment.repos beside the report server's roots file, and the handler answers a
page that is listed there. A report page is not listed, so its verbs are the report server's.

The report verbs check/update/insert refuse a file once it is newer than the page, because a
bench report holds a copy of the code. A vcomment page holds none: it asks for each file when you
open it, so these live verbs have no such rule, and they know the languages (vclang):

    {tree: true}                  {root, name, base, files: [{p, k, s}]}: p the path from the
                                  repository root with /, k code | md | text | html | other | big,
                                  s the bytes; the files git lists (tracked, and untracked but not
                                  ignored), without .git, caches, environments and folders with a
                                  dot except .claude
    {open: PATH, label}           {ok: true, html: the tab of vcode.vctab}
    {check: true, filename}       {ok: true} if comments may be added to that file
    {update: true, first, last, ...} | {insert: true, line, ...}  with filename, base, tag, text
                                  {ok, base, first, last, delta, html, removed}
Which comment marker a file takes is the file's language (lang/*.mu: ### for Python, %%% for
MATLAB, /// for JS, /*** */ for CSS, <!--### --> for Markdown, ### for txt); nothing the page sends
can change that. An edit is written only if the file's sha1 is `base`, the text is under 30000
characters and does not hold what closes the comment, the lines it changes are comment lines (for
.py the syntax tree is the same afterwards, for the rest the lines that are not comments), and it
does not fall inside a block comment or a back-quote string. Nothing else is ever written.

Reach. A page is registered to one repository (register), and a file is reachable if its real
path is inside it once links are followed, no part of the path given is .., it is not in .git, a cache,
an environment or a folder with a dot (except .claude), and vclang.kind_of opens it. (A file that git
ignores is not in the tree but can be opened by name: it is inside the repository all the same.) Finding the repository for a path (find_root) stops at the first folder
with .git, and never goes above the REACH of the path: the first folder up that holds .claude or
is one name below the drive root (C:/name), whichever comes first. C:/ itself is never looked at.

    reach_limit(path) -> folder         the reach of a path
    find_root(path) -> folder or None   the repository of a path: the first folder with .git, or
                                        the top folder under the reach; None outside any reach
    find_files(root, names) -> [(name, relative path or None)]
        Looks only downward from root. A name with a / matches the end of a path, a bare name
        matches a file name; of the matches the one nearest the root (fewest folders) wins, and
        of equals the newest.
    register(name, root, folder) / lookup(S, name)   which repository a page may read

VERSION  M1 m01.v02 (2026-11-01): the verbs of reportserver.py instead of a server of its own.
         M1 m01.v01 (2026-11-01): first version (a daemon of its own, dropped).
"""
###FLM changes req:
###FLM 
###FLM in some of the mu files there is an orange bg behind number, best to minimise bg changes. 
import ast
###FLM test change
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# the report server starts as a script with only primary/ on its path: tools/ (use.py) is added
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from use import load

import vclang
from vcode import vctab

load('marked')                       # md2htm, compiled: use finds marked.pyx beside this file

__all__ = ['handler', 'reach_limit', 'find_root', 'find_files', 'register', 'lookup',
           'listing']

REGISTRY = 'vcomment.repos'          # beside the report server's roots file: page name TAB repository
MAX_BYTES = 4 * 1024 * 1024
WALK_MAX = 20000                      # files a walk (no git) lists at most
HIDDEN = {'__pycache__', 'venv', '.venv', 'env', 'node_modules', '.git', '.mypy_cache',
          '.pytest_cache', '.idea', '.vscode', 'site-packages', '_tmp'}
SHOWN_DOT = {'.claude'}              # the one folder with a dot that the tree shows
JUNK = ('.pyc', '.pyo', '.tmp')


# ---- reach and the repository -----------------------------------------------------------------
def reach_limit(path):
    """The first folder from `path` upwards that holds .claude, or is one name below the drive
    root (C:/name), whichever comes first. A path directly on the drive root has none: its own
    first folder is the reach, which find_root treats as outside."""
    here = os.path.abspath(path)
    if os.path.isfile(here):
        here = os.path.dirname(here)
    while True:
        parent = os.path.dirname(here)
        if os.path.isdir(os.path.join(here, '.claude')) or os.path.dirname(parent) == parent:
            return here
        here = parent


def find_root(path):
    """The repository of a path: the first folder up with .git, else the top folder under the
    reach (the folder whose parent is the reach, so the tree is one project), else the reach
    itself when the path is the reach. None for the drive root. The drive root is never read."""
    here = os.path.abspath(path)
    if os.path.isfile(here):
        here = os.path.dirname(here)
    if os.path.dirname(here) == here:
        return None
    limit = reach_limit(here)
    try:
        if os.path.commonpath([here, limit]) != limit:
            return None
    except ValueError:
        return None
    while True:
        if here == limit or os.path.exists(os.path.join(here, '.git')):
            return here
        if os.path.dirname(here) == limit:
            return here
        here = os.path.dirname(here)


def find_files(root, names):
    """[(name, relative path or None)]: see the module header."""
    shown = []
    for rel in (item['p'] for item in listing(root)):
        try:
            shown.append((rel, os.path.getmtime(os.path.join(root, rel))))
        except OSError:
            pass
    out = []
    for name in names:
        want = name.replace('\\', '/').strip('/').lower()
        hits = [(rel.count('/'), -when, rel) for rel, when in shown
                if rel.lower() == want or rel.lower().endswith('/' + want)]
        out.append((name, min(hits)[2] if hits else None))
    return out


def register(name, root, folder):
    """Let the page called `name` read the repository `root`. `folder` is the report server's
    folder (where its roots file is): one line for each page name, a new one replaces it."""
    path = os.path.join(folder, REGISTRY)
    known = []
    if os.path.isfile(path):
        with open(path, encoding='utf-8') as f:
            known = [line.rstrip('\n') for line in f if line.strip()]
    known = [line for line in known if line.split('\t')[0] != name]
    known.append(name + '\t' + os.path.abspath(root))
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(known) + '\n')


def lookup(S, name):
    """The repository registered for a page name, if it is still a folder."""
    try:
        with open(os.path.join(os.path.dirname(S['roots_file']), REGISTRY), encoding='utf-8') as f:
            for line in f:
                page, _, root = line.rstrip('\n').partition('\t')
                if page == name and os.path.isdir(root):
                    return root
    except OSError:
        pass
    return None


# ---- the tree ---------------------------------------------------------------------------------
def visible(rel):
    """Whether the tree shows a path (from the root, with /): not in .git, a cache or an
    environment, not a folder with a dot (except .claude), not compiled junk."""
    parts = rel.split('/')
    for folder in parts[:-1]:
        if folder in HIDDEN or (folder.startswith('.') and folder not in SHOWN_DOT):
            return False
    return not parts[-1].lower().endswith(JUNK) and parts[-1] not in ('Thumbs.db', 'Desktop.ini',
                                                                       '.DS_Store')


def names_of(root):
    """The files of the repository: git's list (tracked, and untracked but not ignored), else
    a walk that stops after WALK_MAX files."""
    flags = 0x08000000 if os.name == 'nt' else 0          # no console window from the daemon
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
    """[{p, k, s}] of the files the tree shows, sorted: see the module header."""
    out = []
    for rel in sorted(set(names_of(root)), key=str.lower):
        if not visible(rel):
            continue
        try:
            size = os.path.getsize(os.path.join(root, rel))
        except OSError:
            continue                                      # tracked, but gone from the disk
        kind = vclang.kind_of(rel) or 'other'
        out.append({'p': rel, 'k': 'big' if kind in ('code', 'md', 'text') and size > MAX_BYTES
                    else kind, 's': size})
    return out


def reachable(root, path):
    """The real path of a file the page may open and comment, else None."""
    if '..' in re.split(r'[\\/]', path):
        return None
    top = os.path.realpath(root)
    real = os.path.realpath(path if os.path.isabs(path) else os.path.join(root, path))
    try:
        inside = os.path.commonpath([real, top]) == top
    except ValueError:                                    # another drive
        inside = False
    if not inside or not os.path.isfile(real) or os.path.getsize(real) > MAX_BYTES:
        return None
    rel = os.path.relpath(real, top).replace(os.sep, '/')
    if not visible(rel) or vclang.kind_of(real) not in ('code', 'md', 'text'):
        return None
    return real


# ---- the verbs --------------------------------------------------------------------------------
def refuse(log, why):
    log('refused: ' + why)
    return '[]'


def open_reply(log, msg, root):
    """{open: PATH, label} -> {ok: true, html: the tab}."""
    path, label = msg.get('open'), msg.get('label')
    if not isinstance(path, str) or not (label is None or isinstance(label, str)):
        return refuse(log, 'open: path and label are strings')
    real = reachable(root, path)
    if real is None:
        return refuse(log, f'open: {path} is not a file inside {root}')
    try:
        page = vctab(real, os.path.realpath(root), (label or '')[:200])
    except (OSError, ValueError) as error:
        return refuse(log, f'open: {path}: {error}')
    return json.dumps({'ok': True, 'html': bytes(page).decode('utf-8')})


def skeleton(text, spec, rx):
    """What must not change when comments change: for .py the syntax tree (comments are not in
    it, a comment line pushed into a string is); for the rest the lines that are not comments."""
    if spec.name == 'python':
        try:
            return ast.dump(ast.parse(text))
        except (SyntaxError, ValueError):
            pass
    return [x.rstrip() for x in text.split('\n') if not rx.match(x)]


def live_check(log, msg, root):
    """May this page add comments to that file? {check: true, filename} -> {ok: true}."""
    name = msg.get('filename')
    if not (isinstance(name, str) and reachable(root, name)):
        return refuse(log, 'check: not a file inside the repository')
    return '{"ok": true}'


def live_edit(log, msg, root):
    """Add, change or remove one comment of a file; see the module header."""
    path, text, base, tag = msg.get('filename'), msg.get('text'), msg.get('base'), msg.get('tag')
    if not (isinstance(path, str) and isinstance(text, str) and isinstance(base, str)):
        return refuse(log, 'edit: filename, text and base are strings')
    if not (isinstance(tag, str) and re.fullmatch(r'\w{1,8}', tag)):
        return refuse(log, 'edit: the tag is 1 to 8 letters or digits')
    if '\x00' in text or len(text) > 30000:
        return refuse(log, 'edit: that text')
    real = reachable(root, path)
    if real is None:
        return refuse(log, f'edit: {path} is not a file inside {root}')
    spec = vclang.spec_for(real)                          # the file's language says the marker
    if spec.close and spec.close in text:
        return refuse(log, f'edit: the text holds {spec.close}, which would end the comment')
    with open(real, 'rb') as f:
        raw = f.read()
    if hashlib.sha1(raw).hexdigest() != base:
        return refuse(log, 'edit: the file has changed since the page read it')
    eol = '\r\n' if b'\r\n' in raw else '\n'
    try:
        old = raw.decode('utf-8').replace('\r\n', '\n')
    except UnicodeDecodeError:
        return refuse(log, 'edit: the file is not UTF-8')
    lines = old.split('\n')
    rx = vclang.comment_regex(spec)
    try:
        if msg.get('update'):
            first, last = int(msg['first']), int(msg['last'])
            block = lines[first - 1:last]
            if not 1 <= first <= last <= len(lines) or not block or not all(rx.match(x) for x in block):
                return refuse(log, 'edit: those lines are not a comment')
            indent = re.match(r'\s*', lines[first - 1]).group(0)
        elif msg.get('insert'):
            first = int(msg['line'])
            if not 1 <= first <= len(lines) + 1:
                return refuse(log, 'edit: no such line')
            indent = re.match(r'\s*', lines[min(first, len(lines)) - 1]).group(0)
            last = first - 1                              # nothing is replaced: it goes in before
        else:
            return refuse(log, 'edit: neither update nor insert')
    except (KeyError, TypeError, ValueError):
        return refuse(log, 'edit: the lines are not numbers')
    if vclang.is_inside_block(lines, spec, first):
        return refuse(log, 'edit: that line is inside a block comment or a string')
    new = vclang.comment_lines(spec, indent, tag, text) if text.strip() else []
    after = lines[:first - 1] + new + lines[last:]
    if skeleton('\n'.join(after), spec, rx) != skeleton(old, spec, rx):
        return refuse(log, 'edit: more than comments would change')
    data = eol.join(after).encode('utf-8')
    tmp = real + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(data)
    os.replace(tmp, real)
    log(f'edit: {real} lines {first}-{last} now {len(new)} lines')
    shown = bytes(md2htm(text)).split(b'-->\n', 1)
    return json.dumps({'ok': True, 'base': hashlib.sha1(data).hexdigest(), 'first': first,
                       'last': first + len(new) - 1, 'delta': len(new) - (last - first + 1),
                       'html': shown[1].decode('utf-8') if len(shown) > 1 else '',
                       'removed': not new})


def handler(S, msg, root, name, log):
    """The report server's extension point (see reportserver.handlers): the reply to a message
    of a page that is registered to a repository, or None for any other page and for a verb the
    report server answers."""
    wanted = msg.get('tree') or 'open' in msg or msg.get('check') or msg.get('update') \
        or msg.get('insert')
    repo = lookup(S, name) if wanted else None
    if repo is None:
        return None
    if msg.get('tree'):
        return json.dumps({'root': repo, 'name': os.path.basename(repo),
                           'base': Path(repo).as_uri(), 'files': listing(repo)})
    if 'open' in msg:
        return open_reply(log, msg, repo)
    if msg.get('check'):
        return live_check(log, msg, repo)
    return live_edit(log, msg, repo)
