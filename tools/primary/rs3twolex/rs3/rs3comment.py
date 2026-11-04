r"""rs3comment.py -- the verbs of the code, methods and editbox blocks: a file as commentable lines, the
list of its methods, and the comments. Nothing outside the rs3 folder and the standard library is used
(vclang, codelex and marked are copies in this folder: rs3source.py checks that they are the ones loaded).

Verbs (websocket; each takes the page's hash, whose root is the scope of the page: rs3files.
Paths are ./ from the root of the server, like every path in a message)
    open     {do: 'open', hash, path}        -> {ok, html, base, path}
             the lines of one file under the page's root: colouring, comment threads. `base` is
             the sha1 the file had when it was read; an edit must send it back.
    methods  {do: 'methods', hash, path}     -> {ok, path, methods: [{name, line, size, calls,
             colour}]}
             the functions and classes of the file as Class.method, with the colour of the rules
             below: green exported and named by a test, red short or called under twice or not named,
             amber red with a ###cld comment above, '' the rest
    check    {do: 'check', hash, filename}   -> {ok}   may comments be added to that file?
    update   {do: 'update', hash, filename, first, last, base, tag, text}
                                             -> {ok, base, first, last, delta, html, removed}
             change the comment on lines first-last; empty text removes it
    insert   {do: 'insert', hash, filename, line, base, tag, text}   (the same reply)
             add a comment above a line
A refusal is {ok: false, error}.

The rows of `open`. A div for each line,
    <div class="ln" id="L12" data-n="12"><span class="no">12</span><span class="mg"></span><code>..</code></div>
(class "ln sep" for a rule, "ln b-lcomment" | "b-docstring" | "b-fileline" for a line that is only a
comment, a docstring or a banner, coloured across its row) and a div for each comment, in place of
its lines:
    <div class="cm" data-who="claude|user" data-initials=".." data-first=".." data-last=".."
         data-md=".."><span class="mg"><i class="dot"></i></span><div class="cmt"> HTML <a class="reply">
A comment is a run of lines `<triplet><tag> text` of the file's language (### for Python, %%% for
MATLAB ...): the tag says who wrote it (cld is Claude's, anything else a user's initials), the text is
Markdown. A line of the triplet alone is a rule.

The colours of the methods (Python and Cython; the other languages are listed uncoloured). A name is
green when the module exports it (__all__; with none, every name not starting with an underscore) and a
test names it; red when a test suite of the file exists and the name is not named by it, or is short
(under SHORT lines), or is called less than twice in its own file; black otherwise, and always black
for a file that is itself a suite (b_*.py) or has none. A red name with a comment right above it (the
reason it is acceptable) is amber. A method goes with its class. The suites of a file are
tests/b_STEM.py or test/b_STEM.py of the page's root.

An edit is written only if the file's sha1 is `base`, the text is under 30000 characters and does not
hold what closes the comment, the lines it changes are comment lines (for Python the syntax tree is the
same afterwards, for the rest the lines that are not comments), and it does not fall inside a block
comment or a back-quote string. Nothing else is ever written. The marker is the file's language's,
whatever the page sends. The file is written to a temporary name and renamed over the original.

VERSION  M3 m01.v01 (2026-11-03): rebuilt from rs3vcomment: the work of vcserver.py (edits), vcode.py (the
         rows of other languages), and codemark.py (the rows and the colours of Python) is here, with Class.method
         names from the syntax tree; the file is read once for open and methods (rs3source).
         (rs3vcomment M2 m01.v01: open gave the lines only. rs2 rsvcomment m02.v01: ./ paths in and out.)
"""
import ast
import hashlib
import html
import os
import re

import vclang
from rs3files import located
from rs3source import comments, escape, markdown, read, tokens

SHORT = 5                                                  # fewer lines than this is a short function
DEF = re.compile(r'^\s*(?:async\s+)?(?:cp?def|def)\s+(?:[\w\[\]\s*]+?\s+)?(\w+)\s*\(')
SUITES = ('test', 'tests')


def refuse(why):
    return {'ok': False, 'error': why}


# ---- open: the lines --------------------------------------------------------------------------
def band(pieces, python):
    """A line that is only a comment, a docstring or a file banner is coloured across its whole row:
    its class b-<role>. The other languages have the comment band only."""
    shown = [p for p in pieces if not (p[0] == 'default' and not p[1].strip())]
    if not shown:
        return ''
    role = shown[0][0]
    if role == 'lcomment' or (python and (role == 'fileline' or (
            role == 'docstring' and all(r == 'docstring' for r, t in shown)))):
        return ' b-' + role
    return ''


def line_html(pieces, text):
    if pieces is None:
        return escape(text)
    return ''.join(escape(t) if role == 'default' else f'<span class="r-{role}">{escape(t)}</span>'
                   for role, t in pieces)


def rows_html(src):
    """The html of the lines and the comment threads of a Source: see the module header."""
    pieces = tokens(src)
    blocks = comments(src)
    out = []
    row = 1
    while row <= len(src.lines):
        if row in blocks:
            first, last, tag = blocks[row]
            md = '\n'.join(src.rx.match(x).group(2) or '' for x in src.lines[first - 1:last])
            claude = tag == 'cld'
            out.append(f'<div class="cm" data-who="{"claude" if claude else "user"}" '
                       f'data-initials="{"" if claude else escape(tag)}" data-first="{first}" '
                       f'data-last="{last}" data-md="{html.escape(md)}">'
                       f'<span class="mg"><i class="dot"></i></span><div class="cmt">{markdown(md)}'
                       f'<a class="reply" href="#">reply</a></div></div>')
            row = last + 1
            continue
        rule = bool(src.sep.match(src.lines[row - 1]))
        here = pieces[row - 1] if pieces else None
        cls = ' sep' if rule else (band(here, bool(src.name)) if here else '')
        out.append(f'<div class="ln{cls}" id="L{row}" data-n="{row}"><span class="no">{row}</span>'
                   f'<span class="mg"></span><code>{"" if rule else line_html(here, src.lines[row - 1])}'
                   '</code></div>')
        row += 1
    return '\n'.join(out)


def open_file(msg, S):
    page, real, bad = located(S, msg, 'path')
    if bad:
        return bad
    try:
        src = read(real)
    except (OSError, ValueError) as error:
        return refuse(f'{msg.get("path")}: {error}')
    return {'html': rows_html(src), 'base': src.base, 'path': msg.get('path')}


# ---- methods: the functions and their colours ---------------------------------------------------
def exports(text, tree):
    """The names a module lists in __all__, or None when it lists none (a Python file read as a
    tree, a Cython file by its text)."""
    if tree is not None:
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == '__all__' for t in node.targets):
                try:
                    return set(ast.literal_eval(node.value))
                except (ValueError, TypeError):
                    return None
        return None
    m = re.search(r'^__all__\s*=\s*[\[(](.*?)[\])]', text, re.M | re.S)
    return set(re.findall(r'[\'"](\w+)[\'"]', m.group(1))) if m else None


def colour(tested, exported, named, size, calls):
    """'' black, 'green' or 'red': see the module header (red asks for a reason above the name)."""
    if not tested:
        return ''
    if exported and named:
        return 'green'
    return 'red' if (not named or size < SHORT or calls < 2) else ''


def find_tests(root, real):
    """The b_<stem>.py suites of root's test and tests folders that test this file."""
    stem = os.path.splitext(os.path.basename(real))[0]
    found = []
    for folder in SUITES:
        suite = os.path.join(root, folder, 'b_' + stem + '.py')
        if os.path.isfile(suite) and os.path.abspath(suite) != os.path.abspath(real):
            found.append(suite)
    return found


def top_of(node):
    """The first line of a def or class, its decorators included."""
    return min([d.lineno for d in node.decorator_list] + [node.lineno])


def walk(node, classes, found, tree):
    """Collect (name, word, first, last, top, kind, owner) of every function (as Class.method inside a
    class) and every top-level class, depth first."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found.append(('.'.join(classes + [child.name]), child.name, child.lineno, child.end_lineno,
                          top_of(child), 'function', classes[0] if classes else child.name))
            walk(child, classes, found, tree)
        elif isinstance(child, ast.ClassDef):
            if node is tree:
                found.append((child.name, child.name, child.lineno, child.end_lineno, top_of(child),
                              'class', child.name))
            walk(child, classes + [child.name], found, tree)
        else:
            walk(child, classes, found, tree)


def python_functions(src, tree):
    """([(name, word, first, last, top, kind, owner)], {word: uses}) of a Python file read as a tree."""
    found = []
    walk(tree, [], found, tree)
    found.sort(key=lambda f: f[2])
    used = {}
    for node in ast.walk(tree):
        word = node.id if isinstance(node, ast.Name) else node.attr if isinstance(
            node, ast.Attribute) else None
        if word:
            used[word] = used.get(word, 0) + 1
    return found, used


def text_functions(src):
    """The same for a Cython file, or a Python one that does not parse: found by a line pattern, a
    def counting as a use of its own name."""
    starts = [(i + 1, DEF.match(x).group(1)) for i, x in enumerate(src.lines) if DEF.match(x)]
    found = []
    for k, (at, word) in enumerate(starts):
        last = (starts[k + 1][0] - 1) if k + 1 < len(starts) else len(src.lines)
        found.append((word, word, at, last, at, 'function', word))
    used = {}
    for word in re.findall(r'\w+', src.text):
        used[word] = used.get(word, 0) + 1
    return found, {w: n - (1 if w in {s[1] for s in found} else 0) for w, n in used.items()}


def methods_of(src, root):
    """[{name, line, size, calls, colour}] of a Source, by line."""
    if not src.name:                                        # MATLAB, JS, CSS, notes: vclang finds them
        if tokens(src) is None:
            return []
        used = {}
        for word in re.findall(r'\w+', src.text):
            used[word] = used.get(word, 0) + 1
        return [{'name': name, 'line': first, 'size': last - first + 1,
                 'calls': max(0, used.get(name.rsplit('.', 1)[-1], 0) - 1), 'colour': ''}
                for name, first, last, kind in vclang.functions(src.lines, src.spec, src.lexed)]
    tree = None
    if src.name == 'python':
        try:
            tree = ast.parse(src.text)
        except (SyntaxError, ValueError):
            tree = None
    found, used = python_functions(src, tree) if tree is not None else text_functions(src)
    tests = None if os.path.basename(src.real).startswith('b_') else find_tests(root, src.real)
    tested_text = ''
    for test in tests or ():
        with open(test, encoding='utf-8', errors='replace') as f:
            tested_text += f.read() + '\n'
    listed = exports(src.text, tree)
    ended = {b[1] for b in comments(src).values()}          # the last line of each comment
    out = []
    for name, word, first, last, top, kind, owner in found:
        size = last - first + 1
        calls = max(0, used.get(word, 0))
        named = len(re.findall(r'\b' + re.escape(word) + r'\b', tested_text)) if tests else 0
        exported = (listed is None and not owner.startswith('_')) or (listed is not None
                                                                      and owner in listed)
        shade = colour(bool(tests), exported, named, size, calls)
        if shade == 'red' and top - 1 in ended:
            shade = 'amber'                                 # red, and a comment above says why that is fine
        out.append({'name': name, 'line': first, 'size': size, 'calls': calls, 'colour': shade})
    return out


def methods(msg, S):
    page, real, bad = located(S, msg, 'path')
    if bad:
        return bad
    try:
        src = read(real)
    except (OSError, ValueError) as error:
        return refuse(f'{msg.get("path")}: {error}')
    return {'path': msg.get('path'), 'methods': methods_of(src, os.path.realpath(page['root']))}


# ---- the edits ----------------------------------------------------------------------------------
def skeleton(text, spec, rx):
    """What must not change when comments change: for Python the syntax tree (comments are not in it,
    a comment line pushed into a string is); for the rest the lines that are not comments."""
    if spec.name == 'python':
        try:
            return ast.dump(ast.parse(text))
        except (SyntaxError, ValueError):
            pass
    return [x.rstrip() for x in text.split('\n') if not rx.match(x)]


def check(msg, S):
    page, real, bad = located(S, msg, 'filename')
    return bad or {}


def edit(msg, S, kind):
    """Add (kind 'insert') or change (kind 'update') one comment of a file; see the module header."""
    text, base, tag = msg.get('text'), msg.get('base'), msg.get('tag')
    if not (isinstance(msg.get('filename'), str) and isinstance(text, str) and isinstance(base, str)):
        return refuse('edit: filename, text and base are strings')
    if not (isinstance(tag, str) and re.fullmatch(r'\w{1,8}', tag)):
        return refuse('edit: the tag is 1 to 8 letters or digits')
    if '\x00' in text or len(text) > 30000:
        return refuse('edit: that text')
    page, real, bad = located(S, msg, 'filename')
    if bad:
        return bad
    spec = vclang.spec_for(real)                            # the file's language says the marker
    if spec.close and spec.close in text:
        return refuse(f'edit: the text holds {spec.close}, which would end the comment')
    with open(real, 'rb') as f:
        raw = f.read()
    if hashlib.sha1(raw).hexdigest() != base:
        return refuse('edit: the file has changed since the page read it')
    eol = '\r\n' if b'\r\n' in raw else '\n'
    try:
        old = raw.decode('utf-8').replace('\r\n', '\n')
    except UnicodeDecodeError:
        return refuse('edit: the file is not UTF-8')
    lines = old.split('\n')
    rx = vclang.comment_regex(spec)
    try:
        if kind == 'update':
            first, last = int(msg['first']), int(msg['last'])
            block = lines[first - 1:last]
            if not 1 <= first <= last <= len(lines) or not block or not all(rx.match(x) for x in block):
                return refuse('edit: those lines are not a comment')
            indent = re.match(r'\s*', lines[first - 1]).group(0)
        else:
            first = int(msg['line'])
            if not 1 <= first <= len(lines) + 1:
                return refuse('edit: no such line')
            indent = re.match(r'\s*', lines[min(first, len(lines)) - 1]).group(0)
            last = first - 1                                # nothing is replaced: it goes in before
    except (KeyError, TypeError, ValueError):
        return refuse('edit: the lines are not numbers')
    if vclang.is_inside_block(lines, spec, first):
        return refuse('edit: that line is inside a block comment or a string')
    new = vclang.comment_lines(spec, indent, tag, text) if text.strip() else []
    after = lines[:first - 1] + new + lines[last:]
    if skeleton('\n'.join(after), spec, rx) != skeleton(old, spec, rx):
        return refuse('edit: more than comments would change')
    data = eol.join(after).encode('utf-8')
    temp = real + '.tmp'
    with open(temp, 'wb') as f:
        f.write(data)
    os.replace(temp, real)
    S['say'](f'edit: {real} lines {first}-{last} now {len(new)} lines')
    return {'base': hashlib.sha1(data).hexdigest(), 'first': first, 'last': first + len(new) - 1,
            'delta': len(new) - (last - first + 1), 'html': markdown(text), 'removed': not new}


def update(msg, S):
    return edit(msg, S, 'update')


def insert(msg, S):
    return edit(msg, S, 'insert')


VERBS = {'open': open_file, 'methods': methods, 'check': check, 'update': update, 'insert': insert}
