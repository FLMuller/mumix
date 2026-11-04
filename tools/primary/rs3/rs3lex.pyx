# cython: language_level=3, infer_types=True
r"""rs3lex.pyx -- the one lexer of rs3: a file as coloured pieces, its comment marker, its functions, and
whether a line is inside a string or block comment. It reads lang/*.mu and nothing else.

    from use import load
    load('rs3lex')                               # builds rs3lex.pyx into pyxfiles/ if need be, binds the names below
    lang = language('unit.py')            # a Lang; NoLanguage if no lang file holds that extension
    got = lex(lines, lang)                # [(tokens, in_block, depth)] one for each line
    tokens = got[0][0]                           # [(role, text)]: the texts join back into the line
    css()                                 # .r-<role>{color..} for every role, from the Rules tables
    mark = review(lang)                   # the comment marker: mark.match(line), mark.write(...)
    inside(lines, lang, row)              # is that row inside a block comment or a string?
    functions(lines, lang)                # [(name, first, last, kind)] by the Function/Class lines

language(path) -> Lang
    The language of a file by its extension: the `Files:` line of the lang/*.mu files. NoLanguage (an
    Exception with the extension in its text) when none has it: nothing here guesses.
lex(lines, lang) -> [(tokens, in_block, depth)]
    One scan, left to right, over every line; what runs over lines (an open triple string or block
    comment, the bracket depth) is carried. in_block and depth are the state at the START of a line.
review(lang) -> Review         match(line) (groups tag, text), separator (a regex), write(indent, tag, text)
inside(lines, lang, row) -> bool
functions(lines, lang, got=None) -> [(name, first, last, kind)]   kind is function or class; Class.method by indent

What a lang file gives (the lines above its first `## `, and its tables)
    Files:, Mode: (python, css, code, markdown or text; python for python.mu and cython.mu), Comment: (the
    marker of a review comment and what closes it, `###`, `/*** */`), Line comment:, Block comment:,
    Block alone:, Continuation:, Quotes:, Escape: (backslash or double), Transpose:, Case: no, Function:,
    Class:, Notes:, Trailing:; `## Words` the word lists; `## Rules` the colour of each role.

One scanner. Whitespace, comments, strings, numbers, words, dots, operators and brackets are written once and
switched by the language: the delimiters and word lists are its own, and Mode picks the rest. Python and Cython
read docstrings, f-strings, %-formats, regular expressions in strings, decorators and what the file itself
defines and imports; css reads colours and selectors; text reads notes, [sections] and key: value lines. A word
after a dot is an attribute (a method call when ( follows) in every language.

How a piece gets its role is as codelex.py and vclang.py gave it (rs3twolex/ holds them): this is those two
rebuilt as one, and tests/b_rs3lex.py holds the proof against them.

Speed: one pass, O(n) in the characters. A character decides what starts here (a set or a dictionary: no regular
expression is tried at every token, and nothing is sliced off the line); patterns are used only for what is rare or
long (a string's prefix, a number, a Cython cast). It is a .pyx: plain Python that Cython compiles. Measured
2026-11-04 on a 350-line Python file: codelex 8.5 ms, this as Python 5.7 ms, compiled 4.0 ms (JavaScript against
vclang 1.4x, Markdown 2.5x faster). tests/b_rs3lex.py has the timings and the proof that the pieces are the same.

VERSION  M1 m01.v02 (2026-11-04): a .pyx, loaded with use.load.
         M1 m01.v01 (2026-11-04): first version: codelex.py and vclang.py as one lexer (and one place for the
         comment marker, the function list and the inside test).
"""
import os
import re
from types import SimpleNamespace

__all__ = ['Lang', 'NoLanguage', 'css', 'functions', 'inside', 'language', 'lex', 'review']

HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(HERE) == 'pyxfiles':          # use.load builds into <folder>/pyxfiles: the lang folder is the module's folder's
    HERE = os.path.dirname(HERE)
LANG_DIR = os.path.join(HERE, 'lang')
A = re.ASCII
BANDS = ('lcomment', 'docstring', 'fileline')                  # roles painted across the row
SOFT = {'_', 'type', 'match', 'case'}                          # Python keywords only in some places
COMMENT_PARTS = re.compile(r'(https?://\S+)|\b(TODO|FIXME|XXX|HACK|NOTE)\b', A)
CLOSERS = set(')]}\'.' + 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_')

# Python and Cython
EXC = re.compile(r'^(?:[A-Z]\w*(?:Error|Exception|Warning|Exit)|StopIteration|'
                 r'StopAsyncIteration|KeyboardInterrupt|GeneratorExit)$', A)
PCT = re.compile(r'^%(?:\([^)]*\))?[-+#0]*(?:\d+|\*)?(?:\.(?:\d+|\*))?[hlL]?'
                 r'[diouxXeEfFgGcrsa%]', A)
STRING = re.compile(r"([rRbBuUfF]{0,2})('''|\"\"\"|'|\")")       # (matched at a position: no ^)
PY_NUMBER = re.compile(r'(?:0[xX][0-9a-fA-F_]+|0[bB][01_]+|0[oO][0-7_]+|'
                       r'\d[\d_]*\.?[\d_]*(?:[eE][+-]?\d+)?[jJ]?)[uUlLfF]?')
CAST = re.compile(r'<\s*(?:(?:unsigned|const)\s+)?[A-Za-z_]\w*(?:\s*\*+)?\s*>'
                  r'(?=\s*[\w(&<-])', A)
FORMAT_FIELD = re.compile(r'^(?:\w*(?:\.\w+|\[\w+\])*)?(?:![rsa])?(?::[^{}]*)?$', A)
DEFLINE = re.compile(r'^\s*(?:async\s+)?(?:def|cdef|cpdef)\b')
CLINE = re.compile(r'^\s*(?:cdef|cpdef|ctypedef)\b')
DOCOPEN = re.compile(r'^(?:async\s+)?(?:def|cdef|cpdef|class|cdef\s+class)\b')

# patterns the scan and the survey use: compiled once (re.match(pattern, ...) looks the pattern up on every call)
DIRECTIVE = re.compile(r'#\s*(?:cython|distutils)\s*:', A)
CTYPE_NEXT = re.compile(r'\s*[A-Za-z_*\[&]', A)
MEMVIEW = re.compile(r'\[[\s:,1]*\]', A)
POINTER = re.compile(r'&[A-Za-z_]', A)
HAS_FB, HAS_F, HAS_R = re.compile('[fFbB]'), re.compile('[fF]'), re.compile('[rR]')
IMPORT_LINE = re.compile(r'^\s*(?:from\b|c?import\b)', A)
FROM_LINE = re.compile(r'^\s*from\b', A)
ALL_LINE = re.compile(r'^\s*__all__\s*\+?=')
RE_CALL = re.compile(r'\bre\.\w+\(\s*(?:pattern\s*=\s*)?$', A)
RE_NAME = re.compile(r'\b\w*(?:regex|pattern|rx)\w*\s*=\s*$', A | re.I)
RE_BODY = re.compile(r'[\[\](){}|*+?^$]|\\[dDwWsSbB]')
CLASS_LINE = re.compile(r'^\s*(?:cdef\s+)?class\s+(\w+)', A)
DEF_LINE = re.compile(r'^\s*(?:async\s+)?(?:cdef\s+class|cdef|cpdef|def|class)\b([^(:]*)', A)
WORD_BREAK = re.compile(r'[\s*]+')
IMPORT_STMT = re.compile(r'^\s*(?:from\s+(\S+)\s+)?c?import\s+(.+)$', A)
IMPORT_ITEM = re.compile(r'^\s*([\w.*]+)(?:\s+as\s+(\w+))?', A)
PARENS = re.compile(r'[()]')
TO_EOL = re.compile(r'#.*')
FIELD_PARTS = re.compile(r'\d+|\W+|\w+', A)
CONVERSION = re.compile(r'^![rsa]')
FIELD_SPLIT = re.compile(r'(\{[^{}]*\})')
DIGITS = re.compile(r'\d+', A)
HAS_DIGIT = re.compile(r'\d')
CSS_RULE = re.compile(r'^([^\s@/}][^{]*?)\s*\{')

# the other languages
NUMBER = re.compile(r'(?:0[xX][0-9a-fA-F]+|\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)'
                    r'[A-Za-z%]*', A)
HEX = re.compile(r'#[0-9a-fA-F]{3,8}\b')
SELECTOR = re.compile(r'[.#][A-Za-z_][\w-]*', A)
ATRULE = re.compile(r'@[\w-]+', A)
TEXT_KEY = re.compile(r'^(\s*)([A-Za-z_][\w .\-/\[\]]{0,38}?)(\s*)([:=])(?![=/\\])(\s*)(.*)$')
TEXT_SECTION = re.compile(r'^(\s*)(\[[^\]\n]+\])(\s*)$')
TEXT_PIECE = re.compile(r'"[^"\n]*"|https?://\S+|\s+|[^\s"]+|"', A)       # the last: a quote that never closes
TEXT_CONSTANTS = {'true', 'false', 'yes', 'no', 'on', 'off', 'null', 'none', 'nil'}


LETTERS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
IDSTART = frozenset(LETTERS + '_')                       # a word starts with one of these
WORDCH = frozenset(LETTERS + '0123456789_')              # and goes on with these (ASCII, as \w with re.ASCII)
CSSWORD = WORDCH | {'-'}
UPPERCH = frozenset('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
STRSTART = frozenset('rRbBuUfF\'"')                      # a Python string starts with a prefix letter or a quote
# the operators by their first character, the longer ones first
PY_OPS = {'*': ('**=', '**', '*=', '*'), '/': ('//=', '//', '/=', '/'), '-': ('->', '-=', '-'), ':': (':=',),
          '<': ('<<=', '<<', '<=', '<'), '>': ('>>=', '>>', '>=', '>'), '=': ('==', '='), '!': ('!=', '!'),
          '+': ('+=', '+'), '%': ('%=', '%'), '@': ('@=', '@'), '&': ('&=', '&'), '|': ('|=', '|'), '^': ('^=', '^'),
          '~': ('~=', '~')}
OPS = {'=': ('===', '==', '=>', '='), '!': ('!==', '!=', '!'), '<': ('<=', '<'), '>': ('>=', '>'), '+': ('++', '+'),
       '-': ('--', '-'), '&': ('&&', '&'), '|': ('||', '|'), '?': ('??', '?'), '~': ('~=', '~'), '*': ('*',),
       '/': ('/',), '\\': ('\\',), '^': ('^',), '@': ('@',), '%': ('%',),
       '.': ('...', '.*', './', '.\\', '.^', ".'")}


def word_end(line, i, css):
    """Where the word that starts at i ends, or i when none does: [A-Za-z_] and then [A-Za-z0-9_], and in CSS
    a leading - and - inside."""
    n = len(line)
    j = i
    if css and j < n and line[j] == '-':
        j += 1
    if j >= n or line[j] not in IDSTART:
        return i
    j += 1
    chars = CSSWORD if css else WORDCH
    while j < n and line[j] in chars:
        j += 1
    return j


def op_at(line, i, ops):
    """The operator that starts at i ('' when none does)."""
    for op in ops.get(line[i], ()):
        if line.startswith(op, i):
            return op
    return ''


def is_constant(w):
    """UPPER_CASE: a capital, then capitals, digits and underscores, two characters at least."""
    return len(w) > 1 and w[0] in UPPERCH and w == w.upper()


class NoLanguage(Exception):
    """No lang file holds the extension of the file."""


class Lang:
    """One language, as its lang file describes it."""
    __slots__ = ('name', 'mode', 'exts', 'open', 'close', 'line', 'block', 'block_alone', 'cont', 'quotes',
                 'escape', 'transpose', 'functions', 'classes', 'words', 'fold', 'notes', 'trailing', 'rules',
                 'cy', 'number', 'ops', 'dotnumber')


# ---- reading the lang files ----------------------------------------------------------------------
def table(text, heading):
    """The rows of the first table under a `## heading` (without its header row), as lists of cells."""
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


def build(name, text, python_words=None):
    """The Lang of lang/<name>.mu; python_words are python.mu's lists, which cython.mu extends."""
    head = header(text)
    lang = Lang()
    lang.name = name
    lang.mode = head.get('Mode', 'python' if name in ('python', 'cython') else 'code')
    lang.cy = name == 'cython'
    lang.exts = head.get('Files', '').split()
    triplet = head.get('Comment', '###').split(' ')
    lang.open = triplet[0]
    lang.close = triplet[1] if len(triplet) > 1 else ''
    lang.line = head.get('Line comment', '#' if lang.mode == 'python' else '')
    block = head.get('Block comment', '').split()
    lang.block = tuple(block) if len(block) == 2 else None
    lang.block_alone = head.get('Block alone', '') == 'yes'
    lang.cont = head.get('Continuation', '')
    lang.quotes = head.get('Quotes', '').replace(' ', '')
    lang.escape = head.get('Escape', 'backslash')
    lang.transpose = head.get('Transpose', '') == 'yes'
    lang.functions = re.compile(head['Function']) if 'Function' in head else None
    lang.classes = re.compile(head['Class']) if 'Class' in head else None
    lang.fold = head.get('Case', '') == 'no'
    lang.notes = tuple(head.get('Notes', '').split())
    lang.trailing = tuple(head.get('Trailing', '').split())
    lists = {row[0]: set(row[1].split()) for row in table(text, 'Words') if len(row) == 2}
    if lang.mode == 'python':
        py = python_words if python_words is not None else lists
        lang.words = {'keyword': py['keyword'] - SOFT - py['keyword constant'], 'kwconst': py['keyword constant'],
                      'builtin': py['builtin'], 'self': py['self'], 'ckeyword': set(), 'ctype': set()}
        if lang.cy:
            lang.words['ckeyword'] = lists['keyword'] - {'cython'}
            lang.words['ctype'] = lists.get('C type', set())
    else:
        lang.words = {'keyword': lists.get('keyword', set()), 'kwconst': lists.get('keyword constant', set()),
                      'builtin': lists.get('builtin', set()), 'self': lists.get('self', set())}
        if lang.fold:                                   # the lists hold lower case, the lexer folds the word
            lang.words = {key: {w.lower() for w in words} for key, words in lang.words.items()}
    lang.rules = [{'id': row[1], 'fg': row[3], 'bg': row[4] if row[4] != '-' else '', 'weight': int(row[5]),
                   'italic': row[6] == 'yes', 'underline': row[7] == 'yes'}
                  for row in table(text, 'Rules')
                  if len(row) >= 8 and re.fullmatch(r'#[0-9A-Fa-f]{6}', row[3])]
    py = lang.mode == 'python'
    lang.number = PY_NUMBER if py else NUMBER
    lang.ops = PY_OPS if py else OPS
    lang.dotnumber = not py                             # .5 is a number, except in Python (a dot, then 5)
    return lang


LANGS = {}


def languages():
    """Every language, read once from lang/*.mu: {name: Lang}. python.mu is read first: cython.mu extends it."""
    if not LANGS:
        names = sorted(f[:-3] for f in os.listdir(LANG_DIR) if f.endswith('.mu'))
        texts = {}
        for name in names:
            with open(os.path.join(LANG_DIR, name + '.mu'), encoding='utf-8') as f:
                texts[name] = f.read()
        base = {row[0]: set(row[1].split()) for row in table(texts['python'], 'Words') if len(row) == 2}
        for name in names:
            if 'Files:' in texts[name]:
                LANGS[name] = build(name, texts[name], base)
    return LANGS


def language(path):
    """The Lang of a file by its extension; NoLanguage when no lang file has it."""
    ext = os.path.splitext(path)[1].lower()
    for lang in languages().values():
        if ext in lang.exts:
            return lang
    raise NoLanguage(f'no language file holds the extension {ext or "(none)"!r}: {os.path.basename(path)}')


def css():
    """The style of every role: .r-<id>{...}, and div.ln.b-<id>{background} for the rows that a comment line,
    a docstring or a file banner fills. Roles are read from every lang file; the first to name one gives it."""
    out, seen = [], set()
    for name in ('python', 'cython') + tuple(n for n in languages() if n not in ('python', 'cython')):
        if name not in languages():
            continue
        for r in languages()[name].rules:
            if r['id'] in seen:
                continue
            seen.add(r['id'])
            style = f'color:{r["fg"]};font-weight:{r["weight"]};'
            style += 'font-style:italic;' if r['italic'] else ''
            style += 'text-decoration:underline;' if r['underline'] else ''
            style += f'background:{r["bg"]};' if r['bg'] else ''
            out.append(f'.r-{r["id"]}{{{style}}}')
            if r['id'] in BANDS and r['bg']:
                out.append(f'div.ln.b-{r["id"]}{{background:{r["bg"]}}}')
    return '\n'.join(out) + '\n'


# ---- the comment marker --------------------------------------------------------------------------
class Review:
    """The marker of a review comment of one language: a run of lines `<open><tag> text<close>`."""
    __slots__ = ('open', 'close', 'regex', 'separator')

    def __init__(me, lang):
        me.open, me.close = lang.open, lang.close
        tail = r'\s*' + re.escape(lang.close) if lang.close else ''
        me.regex = re.compile(r'^\s*' + re.escape(lang.open) + r'(\w{1,8})(?: (.*?))?' + tail + '$')
        if lang.open == '###':
            me.separator = re.compile(r'^\s*#{3,}\s*$')              # any run of three or more #
        else:
            me.separator = re.compile(r'^\s*' + re.escape(lang.open) + tail + '$')

    def match(me, line):
        """The match of one comment line (groups: the tag, the text or None), or None."""
        return me.regex.match(line)

    def write(me, indent, tag, text):
        """The lines of one comment: the marker and tag, then the text; a blank line keeps its tag."""
        tail = ' ' + me.close if me.close else ''
        return [indent + me.open + tag + ' ' + x + tail for x in text.rstrip('\n').split('\n')]


def review(lang):
    return Review(lang)


# ---- what Python files define and import (read before the scan) ----------------------------------
def survey(lines):
    """(defined names, modules, imported names, classes, kind of each defined name)."""
    ctx = SimpleNamespace(defined=set(), modules=set(), imported=set(), classes=set(), kinds={})
    for line in lines:
        cm = CLASS_LINE.match(line)
        if cm:
            ctx.classes.add(cm.group(1))
        m = DEF_LINE.match(line)
        if m:
            word = WORD_BREAK.split(m.group(1).strip())[-1]
            if word:
                ctx.defined.add(word)
                ctx.kinds[word] = 'class' if cm else 'def'
    k = 0
    while k < len(lines):
        m = IMPORT_STMT.match(lines[k])
        k += 1
        if not m:
            continue
        rest = m.group(2)
        while '(' in rest and ')' not in rest and k < len(lines):
            rest += ' ' + lines[k]
            k += 1
        for item in PARENS.sub('', rest).split(','):
            mm = IMPORT_ITEM.match(TO_EOL.sub('', item))
            if mm and mm.group(1) != '*':
                (ctx.imported if m.group(1) else ctx.modules).add(
                    mm.group(2) or mm.group(1).split('.')[0])
    return ctx


# ---- pieces both kinds of scan use ---------------------------------------------------------------------
def br_role(depth):
    """The role of a bracket at a nesting depth: outer pair normal, then levels 1 to 5 again."""
    return 'br0' if depth == 0 else 'br%d' % ((depth - 1) % 5 + 1)


def comment_tokens(text, whole):
    """A comment cut at its urls and markers: [(role, text)]; lcomment when it is the whole line."""
    role = 'lcomment' if whole else 'comment'
    out = []
    at = 0
    for m in COMMENT_PARTS.finditer(text):
        out.append((role, text[at:m.start()]))
        out.append(('url' if m.group(1) else 'marker', m.group(0)))
        at = m.end()
    out.append((role, text[at:]))
    return [t for t in out if t[1]]


def string_end(line, start, quote, lang):
    """Where the string that opens at start closes (index of the quote), or -1."""
    j = start + 1
    n = len(line)
    while j < n:
        if lang.escape == 'double':
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


def field_end(line, j, q):
    """Where the {field} that opens at j closes, or -1."""
    depth = 0
    k = j
    while k < len(line):
        c = line[k]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if not depth:
                return k
        elif c == q:
            return -1
        elif c in '\'"':
            e = line.find(c, k + 1)
            if e < 0:
                return -1
            k = e
        k += 1
    return -1


def field_tokens(body, is_code, depth, push, ctx):
    """An f-string or format field {expr!r:spec}: braces are brackets, the expression is code
    (scanned again), the conversion and the spec are format code, fields may nest in the spec."""
    push(br_role(depth), '{')
    cut, d, k = len(body), 0, 0
    while k < len(body):
        c = body[k]
        if c in '([{':
            d += 1
        elif c in ')]}':
            d -= 1
        elif c in '\'"':
            e = body.find(c, k + 1)
            if e < 0:
                break
            k = e
        elif not d and ((c == '!' and body[k + 1:k + 2] != '=') or c == ':'):
            cut = k
            break
        k += 1
    expr = body[:cut]
    if is_code:
        sub = SimpleNamespace(tri=None, role='', docok=False, bd=depth + 1, imp=False, all=False, block=False,
                              tpl='', depth=0, ff=False)
        for role, tok in scan(expr, sub, ctx):
            push(role, tok)
    else:
        for m in FIELD_PARTS.findall(expr):
            push('number' if m[0].isdigit() else 'default', m)
    rest = body[cut:]
    cv = CONVERSION.match(rest)
    if cv:
        push('format', cv.group(0))
        rest = rest[2:]
    if rest[:1] == ':':
        push('format', ':')
        for part in FIELD_SPLIT.split(rest[1:]):
            if part[:1] == '{' and len(part) > 1:
                field_tokens(part[1:-1], is_code, depth + 1, push, ctx)
            else:
                push('format', part)
    push(br_role(depth), '}')


def regex_tokens(text, depth, push):
    """A regular expression in a string: brackets by depth, literals as string text, digits as numbers,
    | * + ? . ^ $ as operators, \\d-style escapes as escapes."""
    k, in_class, lit = 0, False, ''

    def flush():
        nonlocal lit
        push('string', lit)
        lit = ''

    while k < len(text):
        c = text[k]
        if c == '\\':
            flush()
            push('escape', text[k:k + 2])
            k += 2
            continue
        if in_class:
            if c == ']':
                flush()
                depth -= 1
                push(br_role(max(depth, 0)), c)
                in_class = False
            elif c == '-' or (c == '^' and text[k - 1:k] == '['):
                flush()
                push('operator', c)
            elif c.isdigit():
                flush()
                push('number', c)
            else:
                lit += c
            k += 1
            continue
        if c == '[':
            flush()
            push(br_role(depth), c)
            depth += 1
            in_class = True
        elif c in '({':
            flush()
            push(br_role(depth), c)
            depth += 1
        elif c in ')}':
            flush()
            depth -= 1
            push(br_role(max(depth, 0)), c)
        elif c.isdigit():
            flush()
            m = DIGITS.match(text, k).group(0)
            push('number', m)
            k += len(m) - 1
        elif c in '|*+?.^$,':
            flush()
            push('operator', c)
        else:
            lit += c
        k += 1
    flush()


def py_string(line, i, p, q, st, ctx, push, in_all):
    """A one-line Python string that opens at i with prefix p and quote q; returns where it ends."""
    n = len(line)
    is_f = bool(HAS_F.search(p))
    j = i + len(p) + 1
    buf = p + q
    e = j
    while e < n and line[e] != q:
        e += 2 if line[e] == '\\' else 1
    body, before = line[j:e], line[:i]
    is_re = (not is_f and e < n and (
        RE_CALL.search(before)
        or RE_NAME.search(before)
        or (HAS_R.search(p) and RE_BODY.search(body))))
    if in_all and e < n:
        kind = ctx.kinds.get(body)
        role = ('classname' if kind == 'class' else 'defname' if kind == 'def' else
                'imported' if body in ctx.imported else 'module' if body in ctx.modules else '')
        if role:
            push(role, p + q + body + q)
            return e + 1
    if is_re:
        push('string', p + q)
        regex_tokens(body, st.bd, push)
        push('string', q)
        return e + 1

    def flush():
        nonlocal buf
        push('string', buf)
        buf = ''

    while j < n:
        ch = line[j]
        if ch == '\\':
            flush()
            push('escape', line[j:j + 2])
            j += 2
            continue
        if ch == q:
            buf += q
            j += 1
            break
        if ch in '{}' and line[j + 1:j + 2] == ch:
            flush()
            push('escape', ch + ch)
            j += 2
            continue
        if ch == '{':
            fe = field_end(line, j, q)
            if fe > 0:
                fb = line[j + 1:fe]
                if is_f or FORMAT_FIELD.match(fb):
                    flush()
                    field_tokens(fb, is_f, st.bd, push, ctx)
                    j = fe + 1
                    continue
        if ch == '%':
            pm = PCT.match(line[j:])
            if pm:
                flush()
                push('format', pm.group(0))
                j += len(pm.group(0))
                continue
        buf += ch
        j += 1
    flush()
    return j


# ---- the scan: one loop for every language -------------------------------------------------------------
def scan(line, st, ctx):
    """One line as (role, text) pairs; st carries what runs over lines (an open triple string or block comment,
    the bracket depth, an import or __all__ list that goes on). The scan reads the line left to right, once: a
    character decides which kind of piece starts here, and nothing is sliced off or matched from the left."""
    lang = ctx.lang
    if lang.mode == 'text':
        return scan_text(line, lang)
    py, css_mode, cy = lang.mode == 'python', lang.mode == 'css', lang.cy
    words, fold, ops = lang.words, lang.fold, lang.ops
    out, n, i, first = [], len(line), 0, True

    def push(role, tok):
        if tok:
            out.append((role, tok))

    # state of the line (Python): its kind, and the names an import or __all__ list brings
    started_tri = bool(st.tri)
    if py:
        defline = bool(DEFLINE.match(line))
        cline = cy and bool(CLINE.match(line))
        imp = 'names' if st.imp else ('mod' if IMPORT_LINE.match(line) else '')
        is_from = bool(FROM_LINE.match(line))
        in_all = st.all or bool(ALL_LINE.match(line))
    depth, annot, after_dot, cy_next = 0, False, False, False
    prev_word, prev2, prev_role = '', '', ''
    # what the line's Function and Class patterns name (the other languages: a name after `function`, `class` ...)
    kinds = {}
    if not py:
        for rx, kind in ((lang.functions, 'defname'), (lang.classes, 'classname')):
            m = rx.match(line) if rx else None
            if m:
                for name in m.groups():
                    if name:
                        kinds[name] = kind

    def eat_tri(frm, q, role):
        e = line.find(q, frm)
        if e < 0:
            push(role, line[frm:])
            st.tri, st.role = q, role
            return n
        push(role, line[frm:e + 3])
        st.tri = None
        return e + 3

    if lang.block and lang.block_alone:                 # MATLAB: %{ and %} alone on a line
        mark = line.strip()
        if st.block or mark == lang.block[0]:
            if st.block and mark == lang.block[1]:
                st.block = False
            elif not st.block:
                st.block = True
            return comment_tokens(line, True)
    if st.block and lang.block:                         # inside /* ... */
        close = lang.block[1]
        e = line.find(close)
        if e < 0:
            return comment_tokens(line, True)
        i = e + len(close)
        st.block = False
        out += comment_tokens(line[:i], line[i:].strip() == '')
        first = False
    if st.tpl:                                          # inside a back-quote string
        e = string_end(line, -1, st.tpl, lang)
        if e < 0:
            return [('string', line)] if line else []
        out.append(('string', line[:e + 1]))
        st.tpl = ''
        i = e + 1
        first = False
    if st.tri:
        i = eat_tri(0, st.tri, st.role)
        first = False
    while i < n:
        c = line[i]
        if c == ' ' or c == '\t':                       # whitespace
            j = i + 1
            while j < n and line[j].isspace():
                j += 1
            push('default', line[i:j])
            i = j
            continue
        # comments
        if lang.line and line.startswith(lang.line, i):
            if cy and first and DIRECTIVE.match(line, i):
                out.append(('directive', line[i:]))
            else:
                out += comment_tokens(line[i:], first)
            if py:
                break                                   # (the end-of-line state below is still due)
            return out
        if lang.cont and line.startswith(lang.cont, i):
            out += comment_tokens(line[i:], False)
            return out
        if lang.block and not lang.block_alone and line.startswith(lang.block[0], i):
            close = lang.block[1]
            e = line.find(close, i + len(lang.block[0]))
            if e < 0:
                st.block = True
                out += comment_tokens(line[i:], first)
                return out
            end = e + len(close)
            out += comment_tokens(line[i:end], first and line[end:].strip() == '')
            i = end
            continue
        # strings
        if py:
            if c in STRSTART:
                m = STRING.match(line, i)
                if m:
                    p, q = m.group(1), m.group(2)
                    if len(q) == 3:
                        role = 'docstring' if first and st.docok and not HAS_FB.search(p) else 'triple'
                        push(role, p + q)
                        i = eat_tri(i + len(p) + 3, q, role)
                    else:
                        i = py_string(line, i, p, q, st, ctx, push, in_all)
                    first = False
                    prev_role = 'string'
                    continue
            elif c == '@' and first:                    # a decorator
                j = i + 1
                while j < n and (line[j] in WORDCH or line[j] == '.'):
                    j += 1
                if j > i + 1:
                    tok = line[i:j]
                    push('cydeco' if tok.startswith('@cython.') else 'decorator', tok)
                    i = j
                    first = False
                    continue
        elif c in lang.quotes:
            if c == "'" and lang.transpose and i > 0 and line[i - 1] in CLOSERS:
                out.append(('operator', c))
                i += 1
                first = False
                continue
            e = string_end(line, i, c, lang)
            if e < 0:
                if c == '`':
                    st.tpl = c
                out.append(('string', line[i:]))
                return out
            out.append(('string', line[i:e + 1]))
            i = e + 1
            first = False
            prev_word, after_dot = '', False
            continue
        if css_mode:                                    # colours, selectors and at-rules
            m = HEX.match(line, i)
            if m:
                out.append(('number', m.group(0)))
                i += len(m.group(0))
                first = False
                continue
            m = ATRULE.match(line, i) or (SELECTOR.match(line, i) if st.depth == 0 or line.find('{', i) >= 0 else None)
            if m:
                out.append(('keyword' if c == '@' else 'classname', m.group(0)))
                i += len(m.group(0))
                first = False
                continue
        # numbers
        if c.isdigit() or (lang.dotnumber and c == '.' and line[i + 1:i + 2].isdigit() and not after_dot):
            m = lang.number.match(line, i)
            if m:                                       # (a digit that is not 0-9, like a superscript 2, is not one)
                push('number', m.group(0))
                i += len(m.group(0))
                first, prev_role = False, 'number'
                if not py:
                    prev_word, after_dot = '', False
                continue
        if cy and c == '<':                             # a Cython cast
            m = CAST.match(line, i)
            if m:
                push('cast', m.group(0))
                i += len(m.group(0))
                first, prev_role = False, 'cast'
                continue
        # words, and the dot before them
        j = word_end(line, i, css_mode) if (c in IDSTART or (css_mode and c == '-')) else i
        if j > i:
            w = line[i:j]
            if py:
                nc = line[j:j + 1]
                role = 'default'
                if imp and not after_dot and w not in ('from', 'import', 'cimport', 'as'):
                    role = 'module' if imp == 'mod' else 'imported'
                elif len(w) > 4 and w.startswith('__') and w.endswith('__'):
                    role = 'special'
                elif after_dot:
                    role = (('module' if imp == 'mod' else 'imported') if imp else 'cymod' if cy_next
                            else 'methodcall' if nc == '(' else 'attribute')
                elif prev_word == 'def':
                    role = 'defname'
                elif prev_word == 'class':
                    role = 'cdefclass' if prev2 == 'cdef' else 'classname'
                elif cy and prev_word in ('struct', 'union', 'enum', 'fused'):
                    role = 'cstruct'
                elif w in words['kwconst']:
                    role = 'kwconst'
                elif w in words['keyword'] or (w in ('match', 'case') and first and line.rstrip().endswith(':')):
                    role = 'keyword'
                elif cy and w in words['ckeyword']:
                    role = 'ckeyword'
                elif cy and w == 'NULL':
                    role = 'cconst'
                elif w in words['self']:
                    role = 'self'
                elif cy and w == 'cython' and nc == '.':
                    role, cy_next = 'cymod', True
                elif (cy and w in words['ctype'] and nc != '('
                      and (cline or annot or CTYPE_NEXT.match(line, j))):
                    role = 'cobject' if w == 'object' else 'ctype'
                    mv = MEMVIEW.match(line, j)
                    if mv:
                        push('memview', w + mv.group(0))
                        i = j + len(mv.group(0))
                        first, prev2, prev_word, prev_role = False, prev_word, w, 'ctype'
                        continue
                elif w in ctx.classes:
                    role = 'classuse'
                elif w in ctx.modules and nc != '=' and w not in ctx.defined:
                    role = 'module'
                elif w in ctx.imported and w not in ctx.defined:
                    role = 'imported'
                elif annot:
                    role = 'annotation'
                elif cline and depth == 0 and nc == '(':
                    role = 'cdefname'
                elif EXC.match(w):
                    role = 'exception'
                elif w in words['builtin']:
                    role = 'builtin'
                elif is_constant(w):
                    role = 'constant'
                elif nc == '(':
                    role = 'localcall' if w in ctx.defined else 'call'
                push(role, w)
                i = j
                if is_from and w in ('import', 'cimport'):
                    imp = 'names'
                if after_dot and cy_next:
                    cy_next = False
                after_dot, first = False, False
                prev2, prev_word, prev_role = prev_word, w, role
                continue
            lw = w.lower() if fold else w               # VBA: any case
            k = j
            while k < n and line[k] == ' ':
                k += 1
            nc = line[k:k + 1]
            role = 'default'
            if after_dot:
                role = 'methodcall' if nc == '(' else 'attribute'
            elif w in kinds and prev_word.lower() in ('function', 'class', 'classdef', '=', 'const', 'let', 'var',
                                                      '*', 'default', 'export', 'async', 'sub', 'get', 'set',
                                                      'type', 'enum'):
                role = kinds[w]
            elif lw in words['kwconst']:
                role = 'kwconst'
            elif lw in words['keyword']:
                role = 'keyword'
            elif lw in words['self'] and w:
                role = 'self'
            elif lw in words['builtin']:
                role = 'builtin'
            elif css_mode and nc == ':' and st.depth > 0 and line.find('{', i) < 0:
                role = 'attribute'
            elif nc == '(':
                role = 'call'
            elif is_constant(w):
                role = 'constant'
            out.append((role, w))
            i = j
            first, after_dot, prev_word = False, False, w
            continue
        if cy and c == '&' and POINTER.match(line, i):  # Cython pointers
            push('pointer', '&')
            i += 1
            first, prev_role = False, 'pointer'
            continue
        if cy and c == '*' and prev_role in ('ctype', 'pointer'):
            push('pointer', '*')
            i += 1
            prev_role = 'pointer'
            continue
        # operators
        o = op_at(line, i, ops)
        if o and not (css_mode and c in '-%'):
            push('operator', o)
            i += len(o)
            first, prev_role = False, 'operator'
            if py:
                if o == '->' and defline:
                    annot = True
                if o == '=' and defline and depth == 1:
                    annot = False
                if o == '!':
                    out.pop()
                    push('invalid', '!')
            else:
                prev_word, after_dot = o, False
            continue
        # brackets, and the dots, commas and colons between
        if c in '()[]{},;.:':
            role = 'punct'
            if c in '([{':
                role = br_role(st.bd)
                st.bd += 1
                if c == '{' and not py:
                    st.depth += 1
            elif c in ')]}':
                st.bd -= 1
                if st.bd < 0:
                    st.bd, role = 0, 'invalid'
                else:
                    role = br_role(st.bd)
                if c == '}' and not py:
                    st.depth = max(0, st.depth - 1)
            push(role, c)
            i += 1
            first = False
            if py:
                prev_role = 'punct'
                if c == '(':
                    depth += 1
                elif c == ')':
                    depth -= 1
                    if depth <= 0:
                        annot = False
                if c == '.':
                    after_dot = True
                if defline:                             # the annotations of a def line
                    if c == ':' and depth == 1:
                        annot = True
                    if c == ',' and depth == 1:
                        annot = False
                    if c == ':' and depth == 0:
                        annot = False
            else:
                after_dot, prev_word = c == '.', ''
            continue
        push('invalid' if py else 'default', c)          # anything else
        i += 1
        first = False
        if not py:
            prev_word, after_dot = '', False
    if py:
        st.imp = imp != '' and st.bd > 0
        st.all = in_all and st.bd > 0
        if not started_tri or out:
            t = line.strip()
            if t and t[0] != '#' and not (started_tri and st.tri):
                st.docok = bool(DOCOPEN.match(t)) and t.endswith(':')
    return out


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
        elif NUMBER.fullmatch(piece.rstrip(',;.')) and HAS_DIGIT.search(piece):
            out.append(('number', piece))
        elif piece.lower().rstrip(',;.') in TEXT_CONSTANTS:
            out.append(('kwconst', piece))
        else:
            out.append((role, piece))
    return out


def note_start(line, trailing):
    """Where a trailing note starts in a line (the index of its marker), or -1: a marker that follows a space
    and is followed by a space or the end of the line, outside "quotes"."""
    quoted = False
    for k, c in enumerate(line):
        if c == '"':
            quoted = not quoted
        elif not quoted and k and line[k - 1] in ' \t':
            for marker in trailing:
                if line.startswith(marker, k) and line[k + len(marker):k + len(marker) + 1] in ('', ' ', '\t'):
                    return k
    return -1


def scan_text(line, lang):
    """A line of a notes or configuration file as (role, text) pairs whose text is the line: a note line (whole-line
    comment), a [section] or `Title:` heading, `key: value` and `key = value`, then a trailing note."""
    stripped = line.lstrip()
    if stripped and any(stripped.startswith(m) for m in lang.notes):
        return comment_tokens(line, True)
    cut = note_start(line, lang.trailing)
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


def new_state():
    """What runs over lines."""
    return SimpleNamespace(block=False, tpl='', tri=None, role='', docok=True, bd=0, depth=0, imp=False,
                           all=False, ff=False)


def lex(lines, lang):
    """[(tokens, in_block, depth)] for every line; in_block and depth are the state at the START of the line
    (in_block: inside a block comment, a back-quote string or a triple string)."""
    ctx = survey(lines) if lang.mode == 'python' else SimpleNamespace()
    ctx.lang = lang
    st = new_state()
    out = []
    for line in lines:
        start = (bool(st.block or st.tpl or st.tri), st.depth)
        if lang.mode == 'python':
            if line == '\f':
                st.docok = True                         # a form feed starts a new file
            if st.ff:                                   # the line after it names the file
                st.ff = False
                out.append(([('fileline', line)], start[0], start[1]))
                continue
            st.ff = line == '\f'
            indoc = st.tri and st.role == 'docstring'
            tokens = scan(line, st, ctx)
            if indoc and not tokens:
                tokens.append(('docstring', ''))        # a blank line inside a docstring
        else:
            tokens = scan(line, st, ctx)
        out.append((tokens, start[0], start[1]))
    return out


def inside(lines, lang, row):
    """True if line `row` (1-based) starts inside a block comment or a string that runs over lines, so a comment
    line written there would change what the code means."""
    if lang.mode in ('text', 'markdown'):
        return False
    ctx = survey(lines) if lang.mode == 'python' else SimpleNamespace()
    ctx.lang = lang
    st = new_state()
    for line in lines[:row - 1]:
        scan(line, st, ctx)
    return bool(st.block or st.tpl or st.tri)


# ---- the functions -------------------------------------------------------------------------------------
def functions(lines, lang, got=None):
    """[(name, first, last, kind)] of the functions and classes, by the Function and Class lines of the lang file
    (CSS: the rules that start at the left, named by their selector). A function ends where the next one starts.
    A function indented inside a class is named Class.method (by indentation, so it holds for Python, JavaScript
    and indented MATLAB)."""
    found = []
    owners = []              # (indent, name) of the classes still open: a deeper function is theirs
    got = got or lex(lines, lang)
    for row, line in enumerate(lines, 1):
        tokens, in_block, depth = got[row - 1]
        if in_block or (lang.line and line.lstrip().startswith(lang.line)):
            continue
        if lang.mode == 'css':
            m = CSS_RULE.match(line)
            if m and depth == 0:
                found.append((m.group(1).strip(), row, 0, 'function'))
            continue
        for rx, kind in ((lang.functions, 'function'), (lang.classes, 'class')):
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
