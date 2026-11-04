r"""vclang.py -- what vcomment needs to know about a language: which files it owns, how a
reviewer's comment is written in it, how its text is coloured, and where its functions are.

    from vclang import kind_of, spec_for, comment_regex, comment_lines, lexgen, functions
    spec = spec_for('unit.m')                  # None for a file vcomment does not open
    rx = comment_regex(spec)                   # matches '%%%flm why?'
    lines = comment_lines(spec, '    ', 'flm', 'why?\nbecause')
    pieces = lexgen(text.split('\n'), spec)    # per line: (tokens, in_block, depth)
    functions(text.split('\n'), spec, pieces)  # [(name, first, last, kind)]

The languages are the files of lang/*.mu that have a `Files:` line. Beside the lists and the
colours that colour_editor.html writes, a lang file carries these header lines (the lines above
its first `## ` heading):

    Files: .m                       the extensions
    Mode: code | css | markdown | text
    Comment: %%% [close]            the triplet a comment line starts with, then what closes it
    Line comment: %                 the plain comment of the language
    Block comment: %{ %}            opens and closes
    Block alone: yes                the block marks stand on lines of their own (MATLAB)
    Continuation: ...               the rest of the line is a comment
    Quotes: ' "                     the string quotes (a back quote runs over lines)
    Escape: backslash | double      how a quote is written inside a string
    Transpose: yes                  ' after a name or a bracket is an operator, not a string
    Function: REGEX                 group 1 (or the first group that matched) is the name
    Class: REGEX
    Case: no                        the language ignores case (VBA): the word lists match any case
    Notes: # % '                    Mode text: what starts a note line (a whole line of comment)
    Trailing: # % ;                 Mode text: what starts a note after other text, when it follows
                                    a space and is followed by a space or the end of the line

Mode text is for notes and configuration (lang/text.mu): a note line, `[section]` and `Title:`
lines, `key: value` and `key = value` with the key and the numbers in their own colours, true
false yes no on off null as constants, "quoted text", links. It uses the roles that python.mu
colours (annotation for a key, classname for a heading, number, kwconst, string, url), and it
never reads past one line.

The comment triplet is the whole of the review protocol: a comment is a run of lines
`<triplet><tag> text<close>`, one tag for one run (see codemark.py, whose ### this generalises).
python.mu and cython.mu need no Comment line: their triplet is ### unless they say otherwise.

kind_of(path) -> 'code', 'md', 'text', 'html' or ''
    What vcomment does with the file: code, md and text open as a tab with a comment margin, html
    opens in a new browser tab, '' is listed but cannot be opened. 'code' includes Python, Cython,
    MATLAB, JavaScript and CSS.
spec_for(path) -> Spec or None      Spec has name, mode, exts, open, close, line, block, quotes,
                                    words, functions, classes ... (a plain class with __slots__)
comment_regex(spec) -> compiled     groups: (tag, text or None)
separator_regex(spec) -> compiled   the triplet alone on a line: a rule across the page
comment_lines(spec, indent, tag, text) -> [str]    the lines that hold one comment
lexgen(lines, spec) -> [(tokens, in_block, depth)]  tokens are (role, text); roles are the ids of
                                    the Rules table (keyword, string, lcomment ...); in_block and
                                    depth are the state at the START of the line. Python and Cython
                                    are coloured by codelex, not here.
functions(lines, spec, pieces) -> [(name, first, last, kind)]   kind is function or class

Speed: lexgen is one pass of a few regular expressions per token, O(n) in the characters.

VERSION  M1 m01.v02 (2026-11-03): Mode text colours notes, sections and key: value lines; Case: no
         (VBA); .mu files open as Markdown.
         M1 m01.v01 (2026-11-01): first version, for vcomment.
"""
import os
import re

__all__ = ['kind_of', 'spec_for', 'comment_regex', 'separator_regex', 'comment_lines', 'lexgen',
           'functions', 'is_inside_block']

HERE = os.path.dirname(os.path.abspath(__file__))
LANG = os.path.join(HERE, 'lang')
A = re.ASCII
NUMBER = re.compile(r'(?:0[xX][0-9a-fA-F]+|\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)'
                    r'[A-Za-z%]*', A)
IDENT = re.compile(r'[A-Za-z_]\w*', A)
CSSIDENT = re.compile(r'-?[A-Za-z_][\w-]*', A)
OPERATOR = re.compile(r'(?:===?|!==?|<=|>=|=>|\+\+|--|&&|\|\||\?\?|\.\.\.|\.[*/\\^\']|~=|[-+*/\\^<>=~!&|?@%])')
COMMENT_PARTS = re.compile(r'(https?://\S+)|\b(TODO|FIXME|XXX|HACK|NOTE)\b', A)
HEX = re.compile(r'#[0-9a-fA-F]{3,8}\b')
SELECTOR = re.compile(r'[.#][A-Za-z_][\w-]*', A)
ATRULE = re.compile(r'@[\w-]+', A)
CLOSERS = set(')]}\'.' + 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_')
HTML = ('.html', '.htm')
MODES = {'code': 'code', 'css': 'code', 'python': 'code', 'markdown': 'md', 'text': 'text'}


class Spec:
    """One language, as its lang file describes it."""
    __slots__ = ('name', 'mode', 'exts', 'open', 'close', 'line', 'block', 'block_alone',
                 'cont', 'quotes', 'escape', 'transpose', 'functions', 'classes', 'words',
                 'fold', 'notes', 'trailing')


# ---- reading the lang files -----------------------------------------------------------------
def table(text, heading):
    """The rows of the first table under `## heading`, without the header row."""
    if '## ' + heading not in text:
        return []
    body = text.split('## ' + heading, 1)[1].split('\n## ', 1)[0]
    rows = []
    for line in body.splitlines():
        if line.startswith('|'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if not cells[0].startswith(':-'):
                rows.append(cells)
    return rows[1:]


def header(text):
    """The `Key: value` lines above the first `## ` heading, as a dict."""
    out = {}
    for line in text.split('\n## ', 1)[0].splitlines():
        m = re.match(r'^([A-Z][A-Za-z ]*): (.*)$', line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def build(name, text):
    """The Spec of lang/<name>.mu."""
    head = header(text)
    spec = Spec()
    spec.name = name
    spec.mode = head.get('Mode', 'python' if name in ('python', 'cython') else 'code')
    spec.exts = head.get('Files', '').split()
    triplet = head.get('Comment', '###').split(' ')
    spec.open = triplet[0]
    spec.close = triplet[1] if len(triplet) > 1 else ''
    spec.line = head.get('Line comment', '')
    block = head.get('Block comment', '').split()
    spec.block = tuple(block) if len(block) == 2 else None
    spec.block_alone = head.get('Block alone', '') == 'yes'
    spec.cont = head.get('Continuation', '')
    spec.quotes = head.get('Quotes', '').replace(' ', '')
    spec.escape = head.get('Escape', 'backslash')
    spec.transpose = head.get('Transpose', '') == 'yes'
    spec.functions = re.compile(head['Function']) if 'Function' in head else None
    spec.classes = re.compile(head['Class']) if 'Class' in head else None
    spec.fold = head.get('Case', '') == 'no'
    spec.notes = tuple(head.get('Notes', '').split())
    spec.trailing = tuple(head.get('Trailing', '').split())
    spec.words = {row[0]: set(row[1].split()) for row in table(text, 'Words') if len(row) == 2}
    if spec.fold:                                       # the lists hold lower case, the lexer folds the word
        spec.words = {key: {w.lower() for w in words} for key, words in spec.words.items()}
    return spec


SPECS = {}


def specs():
    """Every language, read once from lang/*.mu."""
    if not SPECS:
        for name in sorted(f[:-3] for f in os.listdir(LANG) if f.endswith('.mu')):
            with open(os.path.join(LANG, name + '.mu'), encoding='utf-8') as f:
                text = f.read()
            if 'Files:' in text:
                SPECS[name] = build(name, text)
    return SPECS


def spec_for(path):
    """The Spec of the file by its extension, or None."""
    ext = os.path.splitext(path)[1].lower()
    for spec in specs().values():
        if ext in spec.exts:
            return spec
    return None


def kind_of(path):
    """code, md, text or html: what vcomment does with the file; '' if nothing."""
    if os.path.splitext(path)[1].lower() in HTML:
        return 'html'
    spec = spec_for(path)
    return MODES[spec.mode] if spec else ''


# ---- the comment triplet --------------------------------------------------------------------
def comment_regex(spec):
    """Matches one comment line: groups are the tag (1 to 8 letters or digits) and the text."""
    tail = r'\s*' + re.escape(spec.close) if spec.close else ''
    return re.compile(r'^\s*' + re.escape(spec.open) + r'(\w{1,8})(?: (.*?))?' + tail + '$')


def separator_regex(spec):
    """Matches the triplet alone on a line (for ###, any run of three or more #)."""
    if spec.open == '###':
        return re.compile(r'^\s*#{3,}\s*$')
    tail = r'\s*' + re.escape(spec.close) if spec.close else ''
    return re.compile(r'^\s*' + re.escape(spec.open) + tail + '$')


def comment_lines(spec, indent, tag, text):
    """The lines of one comment: the triplet and tag, then the text; a blank line keeps its tag."""
    tail = ' ' + spec.close if spec.close else ''
    return [indent + spec.open + tag + ' ' + x + tail for x in text.rstrip('\n').split('\n')]


# ---- the lexer ------------------------------------------------------------------------------
def bracket(depth):
    """The role of a bracket at a nesting depth, as codelex does."""
    return 'br0' if depth == 0 else 'br%d' % ((depth - 1) % 5 + 1)


class State:
    """What runs over lines: in a block comment, a back-quote string, the bracket depth."""
    __slots__ = ('block', 'tpl', 'bd', 'depth')

    def __init__(me):
        me.block = False
        me.tpl = ''
        me.bd = 0
        me.depth = 0


def comment_tokens(text, whole):
    """A comment cut at its urls and markers: [(role, text)]."""
    role = 'lcomment' if whole else 'comment'
    out = []
    at = 0
    for m in COMMENT_PARTS.finditer(text):
        out.append((role, text[at:m.start()]))
        out.append(('url' if m.group(1) else 'marker', m.group(0)))
        at = m.end()
    out.append((role, text[at:]))
    return [t for t in out if t[1]]


def string_end(line, start, quote, spec):
    """Where the string that opens at start closes (index of the quote), or -1."""
    j = start + 1
    n = len(line)
    while j < n:
        if spec.escape == 'double':
            if line[j] == quote:
                if line[j + 1:j + 2] == quote:
                    j += 2
                    continue
                return j
            j += 1
        elif line[j] == '\\':
            j += 2
        elif line[j] == quote:
            return j
        else:
            j += 1
    return -1


TEXT_KEY = re.compile(r'^(\s*)([A-Za-z_][\w .\-/\[\]]{0,38}?)(\s*)([:=])(?![=/\\])(\s*)(.*)$')
TEXT_SECTION = re.compile(r'^(\s*)(\[[^\]\n]+\])(\s*)$')
TEXT_PIECE = re.compile(r'"[^"\n]*"|https?://\S+|\s+|[^\s"]+|"', A)       # the last: a quote that never closes
TEXT_CONSTANTS = {'true', 'false', 'yes', 'no', 'on', 'off', 'null', 'none', 'nil'}


def note_start(line, trailing):
    """Where a trailing note starts in a line (the index of its marker), or -1: a marker that
    follows a space and is followed by a space or the end of the line, outside "quotes"."""
    quoted = False
    for k, c in enumerate(line):
        if c == '"':
            quoted = not quoted
        elif not quoted and k and line[k - 1] in ' \t':
            for marker in trailing:
                if line.startswith(marker, k) and line[k + len(marker):k + len(marker) + 1] in ('', ' ', '\t'):
                    return k
    return -1


def text_value(text, role):
    """The pieces of a value or a plain line: numbers, constants, "quoted text" and links."""
    out = []
    for m in TEXT_PIECE.finditer(text):
        piece = m.group(0)
        if piece.isspace():
            out.append(('default', piece))
        elif piece[0] == '"' and len(piece) > 1 and piece[-1] == '"':
            out.append(('string', piece))
        elif piece.startswith('http'):
            out.append(('url', piece))
        elif NUMBER.fullmatch(piece.rstrip(',;.')) and re.search(r'\d', piece):
            out.append(('number', piece))
        elif piece.lower().rstrip(',;.') in TEXT_CONSTANTS:
            out.append(('kwconst', piece))
        else:
            out.append((role, piece))
    return out


def lextext(line, spec):
    """A line of a notes or configuration file as (role, text) pairs whose text is the line:
    a note line (whole-line comment), a [section] or `Title:` heading, `key: value` and
    `key = value`, then a trailing note. See Mode text in the module header."""
    stripped = line.lstrip()
    if stripped and any(stripped.startswith(m) for m in spec.notes):
        return comment_tokens(line, True)
    cut = note_start(line, spec.trailing)
    body, note = (line, '') if cut < 0 else (line[:cut], line[cut:])
    out = []
    m = TEXT_SECTION.match(body)
    key = TEXT_KEY.match(body)
    if m:
        out = [('default', m.group(1)), ('classname', m.group(2)), ('default', m.group(3))]
    elif key:
        indent, name, gap, sep, space, value = key.groups()
        out = [('default', indent), ('classname' if not value.strip() else 'annotation', name),
               ('default', gap), ('punct', sep), ('default', space)] + text_value(value, 'default')
    else:
        out = text_value(body, 'default')
    if note:
        out += comment_tokens(note, False)
    return [t for t in out if t[1]]


def lexline(line, st, spec):
    """One line as (role, text) pairs; st carries what runs over lines."""
    if spec.mode == 'text':
        return lextext(line, spec)
    out = []
    n = len(line)
    i = 0
    first = True
    css = spec.mode == 'css'
    words = spec.words
    names = set()
    kinds = {}
    for rx, kind in ((spec.functions, 'defname'), (spec.classes, 'classname')):
        m = rx.match(line) if rx else None
        if m:
            for name in m.groups():
                if name:
                    names.add(name)
                    kinds[name] = kind
    if spec.block and spec.block_alone:                 # MATLAB: %{ and %} alone on a line
        mark = line.strip()
        if st.block or mark == spec.block[0]:
            if st.block and mark == spec.block[1]:
                st.block = False
            elif not st.block:
                st.block = True
            return comment_tokens(line, True)
    if st.block and spec.block:                        # inside /* ... */
        close = spec.block[1]
        e = line.find(close)
        if e < 0:
            return comment_tokens(line, True)
        i = e + len(close)
        st.block = False
        out += comment_tokens(line[:i], line[i:].strip() == '')
        first = False
    if st.tpl:                                          # inside a back-quote string
        e = string_end(line, -1, st.tpl, spec)
        if e < 0:
            return [('string', line)] if line else []
        out.append(('string', line[:e + 1]))
        st.tpl = ''
        i = e + 1
        first = False
    prev_word = ''
    after_dot = False
    while i < n:
        c = line[i]
        rest = line[i:]
        if c in ' \t':
            m = re.match(r'\s+', rest)
            out.append(('default', m.group(0)))
            i += len(m.group(0))
            continue
        if spec.line and rest.startswith(spec.line):
            out += comment_tokens(rest, first)
            return out
        if spec.cont and rest.startswith(spec.cont):
            out += comment_tokens(rest, False)
            return out
        if spec.block and not spec.block_alone and rest.startswith(spec.block[0]):
            close = spec.block[1]
            e = line.find(close, i + len(spec.block[0]))
            if e < 0:
                st.block = True
                out += comment_tokens(rest, first)
                return out
            end = e + len(close)
            out += comment_tokens(line[i:end], first and line[end:].strip() == '')
            i = end
            continue
        if c in spec.quotes:
            if (c == "'" and spec.transpose and i > 0 and line[i - 1] in CLOSERS):
                out.append(('operator', c))
                i += 1
                first = False
                continue
            e = string_end(line, i, c, spec)
            if e < 0:
                if c == '`':
                    st.tpl = c
                out.append(('string', rest))
                return out
            out.append(('string', line[i:e + 1]))
            i = e + 1
            first = False
            prev_word, after_dot = '', False
            continue
        if css:
            m = HEX.match(rest)
            if m:
                out.append(('number', m.group(0)))
                i += len(m.group(0))
                first = False
                continue
            m = ATRULE.match(rest) or (SELECTOR.match(rest) if st.depth == 0 or '{' in rest else None)
            if m:
                out.append(('keyword' if c == '@' else 'classname', m.group(0)))
                i += len(m.group(0))
                first = False
                continue
        if c.isdigit() or (c == '.' and rest[1:2].isdigit() and not after_dot):
            m = NUMBER.match(rest)
            out.append(('number', m.group(0)))
            i += len(m.group(0))
            first, prev_word, after_dot = False, '', False
            continue
        m = (CSSIDENT if css else IDENT).match(rest)
        if m:
            w = m.group(0)
            lw = w.lower() if spec.fold else w            # VBA: any case
            after = rest[len(w):].lstrip(' ')
            nc = after[:1]
            role = 'default'
            if after_dot:
                role = 'methodcall' if nc == '(' else 'attribute'
            elif w in kinds and prev_word.lower() in ('function', 'class', 'classdef', '=', 'const', 'let',
                                                      'var', '*', 'default', 'export', 'async', 'sub',
                                                      'get', 'set', 'type', 'enum'):
                role = kinds[w]
            elif lw in words.get('keyword constant', ()):
                role = 'kwconst'
            elif lw in words.get('keyword', ()):
                role = 'keyword'
            elif lw in words.get('self', ()) and w:
                role = 'self'
            elif lw in words.get('builtin', ()):
                role = 'builtin'
            elif css and nc == ':' and st.depth > 0 and '{' not in rest:
                role = 'attribute'
            elif nc == '(':
                role = 'call'
            elif len(w) > 1 and re.fullmatch(r'[A-Z][A-Z0-9_]+', w, A):
                role = 'constant'
            out.append((role, w))
            i += len(w)
            first, after_dot, prev_word = False, False, w
            continue
        m = OPERATOR.match(rest)
        if m and not (css and c in '-%'):
            out.append(('operator', m.group(0)))
            i += len(m.group(0))
            first, prev_word, after_dot = False, m.group(0), False
            continue
        if c in '([{':
            out.append((bracket(st.bd), c))
            st.bd += 1
            if c == '{':
                st.depth += 1
        elif c in ')]}':
            st.bd -= 1
            if st.bd < 0:
                st.bd = 0
                out.append(('invalid', c))
            else:
                out.append((bracket(st.bd), c))
            if c == '}':
                st.depth = max(0, st.depth - 1)
        elif c in ',;:.':
            out.append(('punct', c))
            after_dot = c == '.'
            prev_word = ''
            first = False
            i += 1
            continue
        else:
            out.append(('default', c))
        i += 1
        first, prev_word, after_dot = False, '', False
    return out


def lexgen(lines, spec):
    """Every line as (tokens, in_block, depth); in_block and depth are the state at its start."""
    st = State()
    out = []
    for line in lines:
        start = (st.block or bool(st.tpl), st.depth)
        out.append((lexline(line, st, spec), start[0], start[1]))
    return out


def is_inside_block(lines, spec, row):
    """True if line `row` (1-based) starts inside a block comment or a back-quote string, so a
    comment line written there would change what the code means."""
    if spec.mode in ('python', 'text', 'markdown'):
        return False
    st = State()
    for line in lines[:row - 1]:                   # the lines above: what they leave open
        lexline(line, st, spec)
    return st.block or bool(st.tpl)


# ---- the functions --------------------------------------------------------------------------
def functions(lines, spec, pieces=None):
    """[(name, first, last, kind)] of the functions and classes, by the Function and Class lines
    of the lang file (CSS: the rules that start at the left, named by their selector). A
    function ends where the next one starts. A function indented inside a class is named
    Class.method (by indentation, so it holds for Python, JavaScript and indented MATLAB)."""
    found = []
    owners = []              # (indent, name) of the classes still open: a deeper function is theirs
    pieces = pieces or [(None, False, 0)] * len(lines)
    for row, line in enumerate(lines, 1):
        tokens, in_block, depth = pieces[row - 1]
        if in_block or (spec.line and line.lstrip().startswith(spec.line)):
            continue
        if spec.mode == 'css':
            m = re.match(r'^([^\s@/}][^{]*?)\s*\{', line)
            if m and depth == 0:
                found.append((m.group(1).strip(), row, 0, 'function'))
            continue
        for rx, kind in ((spec.functions, 'function'), (spec.classes, 'class')):
            m = rx.match(line) if rx else None
            if m:
                name = next((g for g in m.groups() if g), '')
                if name:
                    indent = len(line) - len(line.lstrip())
                    while owners and owners[-1][0] >= indent:    # that class has ended
                        owners.pop()
                    if owners and kind == 'function':            # a method: Class.method
                        name = owners[-1][1] + '.' + name
                    elif kind == 'class':
                        owners.append((indent, name))
                    found.append((name, row, 0, kind))
                break
    out = []
    for k, (name, first, last, kind) in enumerate(found):
        end = found[k + 1][1] - 1 if k + 1 < len(found) else len(lines)
        out.append((name, first, end, kind))
    return out
