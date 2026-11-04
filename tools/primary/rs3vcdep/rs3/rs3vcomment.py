r"""rs3vcomment.py -- the verbs of the code block: the file as commentable lines, the list of its
methods, and the comments.

Verbs (websocket; each takes the page's hash, whose root is the scope of the page: rs3files.
Paths are ./ from the root of the server, like every path in a message)
    open     {do: 'open', hash, path}        -> {ok, html, base, path}
             the lines of one file under the page's root: colouring, comment threads. `base` is
             the sha1 the file had when it was read; an edit must send it back.
    methods  {do: 'methods', hash, path}     -> {ok, path, methods: [{name, line, size, calls,
             colour}]}
             the functions and classes of the file (Class.method for the languages of vclang;
             Python is codemark's list), with the colour of codemark's rules: green exported
             and named by a test, red short or called under twice or not named, amber red with a
             ###cld comment above, '' the rest
    check    {do: 'check', hash, filename}   -> {ok}   may comments be added to that file?
    update   {do: 'update', hash, filename, first, last, base, tag, text}
                                             -> {ok, base, first, last, delta, html, removed}
             change the comment on lines first-last; empty text removes it
    insert   {do: 'insert', hash, filename, line, base, tag, text}   (the same reply)
             add a comment above a line
A refusal is {ok: false, error}. An edit is written only if the file's sha1 is `base`, only
comment lines change, and the comment marker is the file's language's (vclang), whatever the page
sends. The work is vcserver.py's (with vclang.py, vcode.py and codemark.py), which stay where
they are and are imported here: this module turns ./ paths into the real ones they take, and
their reply text into dicts.

VERSION  M2 m01.v01 (2026-11-03): rs3: open gives the lines only (the methods are their own verb).
         (rs2 rsvcomment m02.v01: ./ paths in and out.)
"""
import hashlib
import html
import json
import os
import re

import vcserver                       # first: it puts tools/ on the path, which vcode's use needs
import vclang
import vcode
from codemark import codemark
from rs3files import page_of, real_of, relative

BAR = re.compile(r'^\s*<div class="cbar">.*?</div>\s*', re.S)
ROW = re.compile(r'<tr><td class="l ?(?P<colour>\w*)"><a href="#" data-line="(?P<line>\d+)">'
                 r'(?P<name>.*?)</a></td><td data-v="\d+">\d+</td><td data-v="(?P<size>\d+)">'
                 r'\d+</td><td data-v="(?P<calls>\d+)">')


def refuse(why):
    return {'ok': False, 'error': why}


def located(S, msg, field):
    """(page, real path, error): the page of msg's hash and the real file of its ./ path."""
    page, why = page_of(S, msg.get('hash'))
    if page is None:
        return None, None, refuse(why)
    path = msg.get(field)
    real = real_of(S, path)
    if real is None:
        return None, None, refuse(f'{path!r} is not a ./ path inside the root')
    return page, real, None


def parts(real, root):
    """(function list html, code html, raw bytes) of one file, as vcode.vctab picks them."""
    spec = vclang.spec_for(real)
    rel = os.path.relpath(real, root).replace(os.sep, '/')
    with open(real, 'rb') as f:
        raw = f.read()
    if vclang.kind_of(real) not in ('code', 'md', 'text'):
        raise ValueError('not a file vcomment opens')
    if os.path.getsize(real) > vcode.MAX_BYTES:
        raise ValueError('too large to open (over 4 MB)')
    if spec.mode == 'python':
        tests = vcode.find_tests(root, real)
        functions, code = codemark(real, tests if not os.path.basename(real).startswith('b_') else None)
    else:
        functions, code = vcode.pane(real, rel, raw, spec)
    # the bar (functions button, path, arrows) the old page put above the lines: the code pane has its own
    code = BAR.sub('', bytes(code).decode('utf-8'), count=1)
    return bytes(functions).decode('utf-8'), code, raw


def open_file(msg, S):
    page, real, bad = located(S, msg, 'path')
    if bad:
        return bad
    try:
        functions, code, raw = parts(real, os.path.realpath(page['root']))
    except (OSError, ValueError) as error:
        return refuse(f'{msg.get("path")}: {error}')
    return {'html': code, 'base': hashlib.sha1(raw).hexdigest(), 'path': msg.get('path')}


def methods(msg, S):
    page, real, bad = located(S, msg, 'path')
    if bad:
        return bad
    try:
        functions, code, raw = parts(real, os.path.realpath(page['root']))
    except (OSError, ValueError) as error:
        return refuse(f'{msg.get("path")}: {error}')
    found = [{'name': html.unescape(m.group('name')), 'line': int(m.group('line')),
              'size': int(m.group('size')), 'calls': int(m.group('calls')),
              'colour': m.group('colour')} for m in ROW.finditer(functions)]
    return {'path': msg.get('path'), 'methods': found}


def run(function, S, msg, shaped, field):
    """Call a vcserver function for the page of msg's hash. shaped(real) is the old-shaped
    message, which gets the real path where it needs one."""
    page, real, bad = located(S, msg, field)
    if bad:
        return bad
    got = json.loads(function(S['say'], shaped(real), page['root']))
    if not isinstance(got, dict):                 # vcserver refuses with [] and logs why
        return refuse(f'{msg.get("do")} was refused (see the log)')
    return got


def check(msg, S):
    return run(vcserver.live_check, S, msg, lambda real: {'check': True, 'filename': real},
               'filename')


def update(msg, S):
    return run(vcserver.live_edit, S, msg,
               lambda real: {**msg, 'filename': real, 'update': True}, 'filename')


def insert(msg, S):
    return run(vcserver.live_edit, S, msg,
               lambda real: {**msg, 'filename': real, 'insert': True}, 'filename')


VERBS = {'open': open_file, 'methods': methods, 'check': check, 'update': update,
         'insert': insert}
