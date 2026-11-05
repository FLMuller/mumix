r"""codemark.py -- a source file as HTML for the code tab: highlighted lines, the comments
converted from Markdown, and a list of the functions. One public function.

    from codemark import codemark
    functions, code = codemark('unit.py', ['b_unit.py'])   # two bytearrays of HTML

codemark(path) -> (functions, code)
    path        a .py file, or .pyx / .pxd / .pxi (Cython). The language, its word lists and
                its colours are read by codelex from lang/<name>.mu; a file of another kind is
                shown without colours. Each piece of code is <span class="r-ROLE"> (see
                codelex.css() for the style of the roles); a line that is only a docstring is
                a div with class "ln b-docstring", so its colour fills the row.
    tests       the paths of the b_ suite files that test this file, or None when this file is
                itself a test (its functions are never exported: all black).
    functions   a table (class grid, so the page gives it sort and filter) of the functions:
                name, line, length, calls, in tests (how often a test file names it). The name
                is green for a function or class the module exports (__all__; with no __all__,
                every name not starting with an underscore) that a test file names; red for any
                other that no test names, or that is short (under SHORT = 5 lines), or that is
                called less than twice in its own file; black for all the rest. A red one with a
                ###cld comment directly above it (the reason it is acceptable) is amber. A method
                goes with its class. Each name is a link with data-line. flag_red(path, tests)
                writes that ###cld comment above each red one that has none, asking whoever
                works on the file next to say why.
    code        the bar (the path, previous and next comment arrows, a button for the function
                list), then a div for each line:
                  <div class="ln" id="L12" data-n="12"><span class="no">12</span><span class="mg"></span><code>..</code></div>
                and a div for each comment block, in place of its lines:
                  <div class="cm" data-who="claude|user" data-initials=".." data-first=".."
                       data-last=".." data-md="..."> the comment as HTML </div>
    A comment is a run of full-line ###tag lines with the same tag (one or more); the ### and
    the tag are not shown, the text is Markdown. The tag is who wrote it: ###cld is Claude's
    (blue circle), any other tag is a user's initials (###flm: an orange circle, the initials
    in data-initials). A reply is the next run, with its own tag; the runs follow each other
    and the page shows them as one thread. A line of only ### (three or more # and nothing else)
    is a separator: a row with class "ln sep", drawn as a rule. Every other line, # comments
    and docstrings among them, is code. The code div has data-base, a fingerprint of the file,
    which an edit must send back.

VERSION  M1 m01.v07 (2026-10-31): the colours: green is exported and named by a test; red is not named
         by a test, or short, or called less than twice (an unexported function no test names is
         now red, not black); black is the rest. flag_red lists every reason that applies.
         M1 m01.v06 (2026-10-29): red also means short or called once or not at all; amber is red
         with a comment above; classes are listed; flag_red writes the ###cld comments.
         M1 m01.v05 (2026-10-29): comments are ###tag lines (###cld Claude, ###flm and other
         initials a user), a reply is a run with another tag, ### alone is a separator; # lines
         and long strings are no longer comments.
         M1 m01.v04 (2026-10-29): the code is coloured by role by codelex (the scheme of
         lang/*.mu), not by Python's tokenize module in five classes.
         M1 m01.v03 (2026-10-29): codemark(path, tests): function colours say what the tests reach
         (green exported and named by a test, red exported and not, black not exported).
         M1 m01.v02 (2026-10-29): the word lists come from lang/python.mu and cython.mu (the
         colour scheme files), not from lang/*.json.
         M1 m01.v01 (2026-10-28): first version.
"""
import sys
import ast
import hashlib
import html
import os
import re

from codelex import language, lex
from htmlwriter import htmappend, htmwriteln
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # tools/: the one use.py
from use import load

load('marked')                       # md2htm, compiled: use finds marked.pyx beside this file

__all__ = ['codemark', 'flag_red']

HERE = os.path.dirname(os.path.abspath(__file__))
COMMENT = re.compile(r'^\s*###(\w{1,8})(?: (.*))?$')      # ###tag text: who wrote the line
SEPARATOR = re.compile(r'^\s*#{3,}\s*$')                   # ### alone: a rule across the page
SHORT = 5                                          # fewer lines than this is a short function
DEF = re.compile(r'^\s*(?:async\s+)?(?:cp?def|def)\s+(?:[\w\[\]\s*]+?\s+)?(\w+)\s*\(')


def esc(text):
    return html.escape(text, quote=False)


def exports(text, tree):
    """The names a module lists in __all__, or None when it lists none (the Python file read
    as a tree, a Cython file by its text)."""
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
    """The colour of a function or class in the list: '' black, green, red.
    No tests (the file is itself a suite): black. Exported (__all__, or a name with no leading
    underscore when there is none) and a test names it: green. Otherwise red when something is
    wrong (see reasons), else black. Red asks for a reason; see flag_red."""
    if not tested:
        return ''
    if exported and named:
        return 'green'
    return 'red' if reasons(tested, exported, named, size, calls) else ''


def reasons(tested, exported, named, size, calls):
    """Why a function or class is red, as words; '' when it is not: no test names it, it is
    short (under SHORT lines), or it is called less than twice in its own file. A function
    that is exported and named by a test is green, whatever its size."""
    if not tested or (exported and named):
        return ''
    why = []
    if not named:
        why.append('exported and no test names it' if exported else 'no test names it')
    if size < SHORT:
        why.append(f'short ({size} lines)')
    if calls < 2:
        why.append('called once or not at all in its own file')
    return ' and '.join(why)

###flm plop

def codemark(path, tests=None):
    with open(path, 'rb') as f:
        raw = f.read()
    text = raw.decode('utf-8', 'replace')
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    ###flm test
    name, words = language(path)
    # the comments: a run of ###tag lines with one tag is one: [first, last, tag] by first line
    blocks = {}
    n = 0
    while n < len(lines):
        m = COMMENT.match(lines[n])
        if m:
            k = n
            while k + 1 < len(lines) and (c := COMMENT.match(lines[k + 1])) and c.group(1) == m.group(1):
                k += 1
            blocks[n + 1] = [n + 1, k + 1, m.group(1)]
            n = k
        n += 1
    funcs = []                                         # name, line, last line, top line, kind
    tree = None
    if name == 'python':
        try:
            tree = ast.parse(text)
        except (SyntaxError, ValueError):
            tree = None
    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                funcs.append((node.name, node.lineno, node.end_lineno,
                              min([d.lineno for d in node.decorator_list] + [node.lineno]), 'function'))
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                funcs.append((node.name, node.lineno, node.end_lineno,
                              min([d.lineno for d in node.decorator_list] + [node.lineno]), 'class'))
        funcs.sort(key=lambda f: f[1])
        used = {}
        for node in ast.walk(tree):
            word = node.id if isinstance(node, ast.Name) else node.attr if isinstance(
                node, ast.Attribute) else None
            if word:
                used[word] = used.get(word, 0) + 1
    else:
        starts = [(i + 1, DEF.match(x).group(1)) for i, x in enumerate(lines) if DEF.match(x)]
        for k, (at, word) in enumerate(starts):
            funcs.append((word, at, (starts[k + 1][0] - 1) if k + 1 < len(starts) else len(lines),
                          at, 'function'))
        used = {}
        for word in re.findall(r'\w+', text):
            used[word] = used.get(word, 0) + 1
    # the colour of each: see colour() (tests=None: the file is itself a test, all black)
    listed = exports(text, tree)
    tested_text = ''
    for test in tests or ():
        with open(test, encoding='utf-8', errors='replace') as f:
            tested_text += f.read() + '\n'
    owner = {}                                         # a method belongs to its class
    if tree is not None:
        for top in tree.body:
            if isinstance(top, ast.ClassDef):
                for node in ast.walk(top):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        owner[node.name] = top.name
    # the colours: the lines as (role, text) pieces, read by codelex with the words and rules
    # of lang/python.mu or cython.mu; a file of another kind stays plain
    pieces = lex('\n'.join(lines), name == 'cython', words) if name else None

    def line_html(row):
        out = []
        for role, text in pieces[row - 1] if pieces else [('default', lines[row - 1])]:
            out.append(esc(text) if role == 'default'
                       else f'<span class="r-{role}">{esc(text)}</span>')
        return ''.join(out)

    def band(row):
        """A line that is only a comment, a docstring or a file banner is coloured across its
        whole row: its class b-<role>."""
        quiet = lambda r, t: r == 'default' and not t.strip()
        tokens = [t for t in (pieces[row - 1] if pieces else []) if not quiet(*t)]
        if tokens and (tokens[0][0] in ('lcomment', 'fileline') or (
                tokens[0][0] == 'docstring' and all(r == 'docstring' for r, t in tokens))):
            return ' b-' + tokens[0][0]
        return ''

    base = hashlib.sha1(raw).hexdigest()
    code = bytearray()
    htmwriteln(code, f'<div class="cbar"><button class="fnbtn" title="show or hide the '
                     f'functions">&#9707;</button><span class="cpath" data-path="'
                     f'{html.escape(os.path.abspath(path))}">{esc(os.path.abspath(path))}</span>'
                     f'<button class="cprev" title="previous comment">&#8592;</button>'
                     f'<button class="cnext" title="next comment">&#8594;</button></div>')
    htmwriteln(code, f'<div class="clines" data-base="{base}">')
    row = 1
    while row <= len(lines):
        if row in blocks:
            first, last, tag = blocks[row]
            md = '\n'.join(COMMENT.match(x).group(2) or '' for x in lines[first - 1:last])
            inner = bytes(md2htm(md)).split(b'-->\n', 1)[1]
            claude = tag == 'cld'
            htmwriteln(code, f'<div class="cm" data-who="{"claude" if claude else "user"}" '
                             f'data-initials="{"" if claude else html.escape(tag)}" '
                             f'data-first="{first}" data-last="{last}" '
                             f'data-md="{html.escape(md)}">'
                             f'<span class="mg"><i class="dot"></i></span>'
                             f'<div class="cmt">')
            htmappend(code, inner)
            htmwriteln(code, '<a class="reply" href="#">reply</a></div></div>')
            row = last + 1
            continue
        sep = SEPARATOR.match(lines[row - 1])
        htmwriteln(code, f'<div class="ln{" sep" if sep else band(row)}" id="L{row}" data-n="{row}"><span class="no">{row}'
                         f'</span><span class="mg"></span><code>{'' if sep else line_html(row)}</code></div>')
        row += 1
    htmwriteln(code, '</div>')
    table = bytearray()
    reds = []                                          # top line, kind, name, why: filled below
    if funcs:
        htmwriteln(table, '<table class="grid funclist"><thead><tr><th>function</th><th>line</th>'
                          '<th>lines</th><th>calls</th><th>in tests</th></tr></thead><tbody>')
        ended = {b[1] for b in blocks.values()}          # the last line of each comment
        for word, first, last, top, kind in funcs:
            size = last - first + 1
            calls = max(0, used.get(word, 0) - (0 if tree is not None else 1))   # a def is a word
            named = len(re.findall(r'\b' + re.escape(word) + r'\b', tested_text)) if tests else 0
            owned = owner.get(word, word)              # a method counts as its class
            out = (listed is None and not owned.startswith('_')) or (listed is not None
                                                                     and owned in listed)
            reds.append((top, kind, word, reasons(bool(tests), out, named, size, calls)))
            color = colour(bool(tests), out, named, size, calls)
            if color == 'red' and top - 1 in ended:
                color = 'amber'                        # red, and a comment above says why that is fine
            htmwriteln(table, f'<tr><td class="l {color}"><a href="#" data-line="{first}">'
                              f'{esc(word)}</a></td><td data-v="{first}">{first}</td>'
                              f'<td data-v="{size}">{size}</td><td data-v="{calls}">{calls}'
                              f'</td><td data-v="{named}">{named if tests else ""}</td></tr>')
        htmwriteln(table, '</tbody></table>')
    else:
        htmwriteln(table, '<p class="mute">no functions</p>')
    codemark.reds = [(t, k, w, y) for t, k, w, y in reds if y and (t - 1) not in ended] if funcs else []
    return table, code


def flag_red(path, tests):
    """Put a ###cld comment above each red function or class that has none, asking whoever
    works on the file next to say why it is acceptable (or fix it); once there is a comment
    above, the name shows amber in the list. Only comment lines are added; a file with nothing
    red is left alone. Returns the number of comments written.

        flag_red('unit.py', ['b_unit.py'])      # idempotent: a second call writes nothing"""
    codemark(path, tests)
    todo = sorted(codemark.reds, reverse=True)           # from the bottom, so the lines above hold
    if not todo:
        return 0
    with open(path, 'rb') as f:
        raw = f.read()
    eol = '\r\n' if b'\r\n' in raw else '\n'
    lines = raw.decode('utf-8').replace('\r\n', '\n').split('\n')
    for top, kind, word, why in todo:
        indent = re.match(r'\s*', lines[top - 1]).group(0)
        lines[top - 1:top - 1] = [
            f'{indent}###cld RED: this {kind} is red ({why}).',
            f'{indent}###cld Claude: say here why that is acceptable, or change it; this turns amber.']
    with open(path, 'wb') as f:
        f.write(eol.join(lines).encode('utf-8'))
    return len(todo)
