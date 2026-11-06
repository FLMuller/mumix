r"""vcode.py -- one file as a tab for the vcomment page: the code with its comment threads and a
function list, laid out exactly as the Code tab of a bench report.

    from vcode import vctab
    html = vctab('C:/repo/tools/unit.py', 'C:/repo', 'unit.py')    # a bytearray of HTML

vctab(path, root, label='') -> bytearray
    The tab div `<div class="mk mk-tab" data-name=LABEL data-rel=RELPATH>`. The page script
    (runbench.js) reads the code pane inside it: the function list, the comment margin, the
    editor. By kind of file (vclang.kind_of):
      Python, Cython   codemark does the page, unchanged (colours by codelex; the function colours
                       say what the b_ suites of test/ and tests/ reach: green, red, amber).
      MATLAB, JS, CSS  the same page, coloured by vclang.lexgen from the lang file.
      txt              the same page, uncoloured.
      md               two sub-tabs: Rendered (marked.md2htm) and Source (the page above).
    The comment lines of the file are shown as threads, never as code: the triplet of its lang
    file (### for Python, %%% for MATLAB, /// for JS, /*** */ for CSS, <!--### --> for Markdown,
    ### for txt) and a tag (cld is Claude's, anything else a user's). Nothing here writes a file.

find_tests(root, path) -> [paths]   the b_<stem>.py suites in test/ or tests/ of root, for the
                                    colours of the function list of a Python file; [] if none

VERSION  M1 m01.v01 (2026-11-01): first version, for vcomment.
"""
import sys
import hashlib
import html
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # tools/: the one use.py
from use import load

import vclang
from codemark import codemark
from htmlwriter import htmappend, htmwriteln

load('marked')                       # md2htm, compiled: use finds marked.pyx beside this file

__all__ = ['vctab', 'find_tests']

CEDIT = ('<div class="cedit"><textarea rows="4" placeholder="click the margin of a line to write '
         'a comment on it, or of a comment to change it (Markdown)"></textarea>'
         '<span class="cstate"></span></div>')
SHORT = 5
MAX_BYTES = 4 * 1024 * 1024


def esc(text):
    return html.escape(text, quote=False)


def find_tests(root, path):
    """The b_<stem>.py suites of root's test and tests folders that test this file."""
    stem = os.path.splitext(os.path.basename(path))[0]
    found = []
    for folder in ('test', 'tests'):
        suite = os.path.join(root, folder, 'b_' + stem + '.py')
        if os.path.isfile(suite) and os.path.abspath(suite) != os.path.abspath(path):
            found.append(suite)
    return found


def body(md):
    """The HTML of some Markdown, without marked's section comment."""
    parts = bytes(md2htm(md)).split(b'-->\n', 1)
    return parts[1] if len(parts) > 1 else b''


def thread_blocks(lines, rx):
    """The comments: a run of lines with one tag is one. {first row: [first, last, tag]}."""
    blocks = {}
    n = 0
    while n < len(lines):
        m = rx.match(lines[n])
        if m:
            k = n
            while k + 1 < len(lines) and (c := rx.match(lines[k + 1])) and c.group(1) == m.group(1):
                k += 1
            blocks[n + 1] = [n + 1, k + 1, m.group(1)]
            n = k
        n += 1
    return blocks


def pane(path, rel, raw, spec):
    """(function list, code) as bytearrays, for a file that codemark does not do."""
    text = raw.decode('utf-8', 'replace')
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    rx = vclang.comment_regex(spec)
    sep = vclang.separator_regex(spec)
    blocks = thread_blocks(lines, rx)
    colour = spec.mode in ('code', 'css', 'text')
    pieces = vclang.lexgen(lines, spec) if colour else None

    def line_html(row):
        out = []
        for role, tok in pieces[row - 1][0] if pieces else [('default', lines[row - 1])]:
            out.append(esc(tok) if role == 'default' else f'<span class="r-{role}">{esc(tok)}</span>')
        return ''.join(out)

    def band(row):
        tokens = [t for t in (pieces[row - 1][0] if pieces else []) if t[0] != 'default' or t[1].strip()]
        return ' b-lcomment' if tokens and tokens[0][0] == 'lcomment' else ''

    base = hashlib.sha1(raw).hexdigest()
    code = bytearray()
    htmwriteln(code, f'<div class="cbar"><button class="fnbtn" title="show or hide the '
                     f'functions">&#9707;</button><span class="cpath" data-path="'
                     f'{html.escape(os.path.abspath(path))}">{esc(rel)}</span>'
                     f'<button class="cprev" title="previous comment">&#8592;</button>'
                     f'<button class="cnext" title="next comment">&#8594;</button></div>')
    htmwriteln(code, f'<div class="clines" data-base="{base}">')
    row = 1
    while row <= len(lines):
        if row in blocks:
            first, last, tag = blocks[row]
            md = '\n'.join(rx.match(x).group(2) or '' for x in lines[first - 1:last])
            claude = tag == 'cld'
            htmwriteln(code, f'<div class="cm" data-who="{"claude" if claude else "user"}" '
                             f'data-initials="{"" if claude else html.escape(tag)}" '
                             f'data-first="{first}" data-last="{last}" '
                             f'data-md="{html.escape(md)}">'
                             f'<span class="mg"><i class="dot"></i></span><div class="cmt">')
            htmappend(code, body(md))
            htmwriteln(code, '<a class="reply" href="#">reply</a></div></div>')
            row = last + 1
            continue
        rule = bool(sep.match(lines[row - 1]))
        htmwriteln(code, f'<div class="ln{" sep" if rule else band(row)}" id="L{row}" '
                         f'data-n="{row}"><span class="no">{row}</span><span class="mg"></span>'
                         f'<code>{"" if rule else line_html(row)}</code></div>')
        row += 1
    htmwriteln(code, '</div>')
    table = bytearray()
    funcs = vclang.functions(lines, spec, pieces) if colour else []
    if funcs:
        used = {}
        for word in re.findall(r'\w+', text):
            used[word] = used.get(word, 0) + 1
        htmwriteln(table, '<table class="grid funclist"><thead><tr><th>function</th><th>line</th>'
                          '<th>lines</th><th>calls</th></tr></thead><tbody>')
        for name, first, last, kind in funcs:
            size = last - first + 1
            calls = max(0, used.get(name.rsplit('.', 1)[-1], 0) - 1)
            htmwriteln(table, f'<tr><td class="l"><a href="#" data-line="{first}">{esc(name)}</a>'
                              f'</td><td data-v="{first}">{first}</td><td data-v="{size}">{size}'
                              f'</td><td data-v="{calls}">{calls}</td></tr>')
        htmwriteln(table, '</tbody></table>')
    else:
        htmwriteln(table, '<p class="mute">no functions</p>')
    return table, code


def codepane(functions, code):
    """The code pane div, as bench.py's codetab writes it."""
    out = bytearray()
    htmwriteln(out, '<div class="codepane"><div class="funcs">')
    htmappend(out, functions)
    htmwriteln(out, '</div><div class="code">')
    htmappend(out, code)
    htmwriteln(out, CEDIT + '</div></div>')
    return out


def vctab(path, root, label=''):
    """The tab of one file; see the module header. ValueError for a file that is not openable."""
    path = os.path.abspath(path)
    if os.path.getsize(path) > MAX_BYTES:
        raise ValueError('too large to open (over 4 MB)')
    kind = vclang.kind_of(path)
    if kind not in ('code', 'md', 'text'):
        raise ValueError('not a file vcomment opens')
    rel = os.path.relpath(path, root).replace(os.sep, '/')
    spec = vclang.spec_for(path)
    with open(path, 'rb') as f:
        raw = f.read()
    if spec.mode == 'python':
        tests = find_tests(root, path)
        functions, code = codemark(path, tests if not os.path.basename(path).startswith('b_') else None)
        mark = esc(os.path.abspath(path)).encode('utf-8')
        code = bytearray(bytes(code).replace(b'>' + mark + b'</span>', b'>' + esc(rel).encode('utf-8')
                                             + b'</span>', 1))
    else:
        functions, code = pane(path, rel, raw, spec)
    out = bytearray()
    name = html.escape(label or os.path.basename(path))
    htmwriteln(out, f'<div class="mk mk-tab" data-name="{name}" data-rel="{html.escape(rel)}">')
    if kind == 'md':
        rx = vclang.comment_regex(spec)
        shown = '\n'.join(x for x in raw.decode('utf-8', 'replace').splitlines() if not rx.match(x))
        htmwriteln(out, '<div class="mk mk-tab" data-name="Rendered"><div class="mdview">')
        htmappend(out, body(shown))
        htmwriteln(out, '</div></div><div class="mk mk-tab" data-name="Source">')
        htmappend(out, codepane(functions, code))
        htmwriteln(out, '</div>')
    else:
        htmappend(out, codepane(functions, code))
    htmwriteln(out, '</div>')
    return out
