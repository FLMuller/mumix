r"""codelex.py -- a Python or Cython file as coloured tokens: each piece of text with the role it
plays (keyword, def name, bracket level 2, docstring ...), and the colours of the roles.

    from codelex import language, lex, css
    name, words = language('unit.pyx')       # 'cython', the word lists of lang/*.mu
    lines = lex(open('unit.pyx').read(), name == 'cython', words)
    # lines[k] is the line k+1 as a list of (role, text); the texts join back into the line
    css()                                    # .r-keyword{color:#0000FF;...} for every role

The two files lang/python.mu and lang/cython.mu say how the code is coloured. Each has a
`Files:` line, optionally `Extends:`, a Words table (List | Words) and a Rules table
(Role | Id | Matches | Colour | Back | Weight | Italic | Underline) that lang/colour_editor.html
writes. Words and rules are read from them here, so there is one place that says what is a
keyword and what colour it is.

How a word gets its role (the same as colour_editor.html, which this is a port of). Nothing is
parsed to a tree: the text is read one line at a time, left to right. A word is a name; what
KIND of name comes from three sources. (1) The word lists, for words the text does not
explain: keywords, builtins, C types, self. (2) Position: the name after def is a def name, after
a dot an attribute (a method call when ( follows), before ( a call, in an annotation a type.
(3) A first pass over the whole file that collects what the file itself defines and imports: a
class defined here is a class when used, a name bound by `import` is a module and one bound by
`from ... import` an imported name. Strings are split into their parts: escapes, %-formats,
{fields} (an f-string field is lexed again as code), regular expressions, __all__ names. Brackets
take a role by nesting depth, so a close bracket matches its open one.

lex(text, cython, words) -> list of lines, each a list of (role, text)
    cython  True for .pyx/.pxd/.pxi: the cdef words, C types, casts, pointers
    words   from language(): a dict of sets: keyword, kwconst, builtin, self, ckeyword, ctype
language(path) -> (name, words)    ('', {}) for a file of another kind
rules(name) -> list of dicts       id, fg, bg, weight, italic, underline, for the Rules table
css() -> str                       one rule for every role of python.mu and cython.mu, and the
                                   band rules: a line that is only a comment, a docstring or a
                                   file banner is coloured across its whole row (div.ln.b-<role>)

Speed: one pass over the text with a handful of regular expressions a line, O(n) in the
characters; a 1000-line file takes some tens of milliseconds.

VERSION  M1 m01.v01 (2026-10-29): first version, ported from the script of colour_editor.html.
"""
import os
import re
from types import SimpleNamespace

__all__ = ['css', 'language', 'lex', 'rules']

HERE = os.path.dirname(os.path.abspath(__file__))
A = re.ASCII
BANDS = ('lcomment', 'docstring', 'fileline')                  # roles painted across the row
SOFT = {'_', 'type', 'match', 'case'}                          # keywords only in some places
EXC = re.compile(r'^(?:[A-Z]\w*(?:Error|Exception|Warning|Exit)|StopIteration|'
                 r'StopAsyncIteration|KeyboardInterrupt|GeneratorExit)$', A)
PCT = re.compile(r'^%(?:\([^)]*\))?[-+#0]*(?:\d+|\*)?(?:\.(?:\d+|\*))?[hlL]?'
                 r'[diouxXeEfFgGcrsa%]', A)
STRING = re.compile(r"^([rRbBuUfF]{0,2})('''|\"\"\"|'|\")")
NUMBER = re.compile(r'^(?:0[xX][0-9a-fA-F_]+|0[bB][01_]+|0[oO][0-7_]+|'
                    r'\d[\d_]*\.?[\d_]*(?:[eE][+-]?\d+)?[jJ]?)[uUlLfF]?')
CAST = re.compile(r'^<\s*(?:(?:unsigned|const)\s+)?[A-Za-z_]\w*(?:\s*\*+)?\s*>'
                  r'(?=\s*[\w(&<-])', A)
OPERATOR = re.compile(r'^(?:\*\*=?|//=?|->|:=|==|!=|<=|>=|<<=?|>>=?|[-+*/%@&|^~<>=!]=?)')
COMMENT_PARTS = re.compile(r'(https?://\S+)|\b(TODO|FIXME|XXX|HACK|NOTE)\b', A)
FORMAT_FIELD = re.compile(r'^(?:\w*(?:\.\w+|\[\w+\])*)?(?:![rsa])?(?::[^{}]*)?$', A)
DEFLINE = re.compile(r'^\s*(?:async\s+)?(?:def|cdef|cpdef)\b')
CLINE = re.compile(r'^\s*(?:cdef|cpdef|ctypedef)\b')
DOCOPEN = re.compile(r'^(?:async\s+)?(?:def|cdef|cpdef|class|cdef\s+class)\b')


def br_role(depth):
    """The role of a bracket at a nesting depth: outer pair normal, then levels 1 to 5 again."""
    return 'br0' if depth == 0 else 'br%d' % ((depth - 1) % 5 + 1)


# ---- the rule files --------------------------------------------------------------------------
def table(text, heading):
    """The rows of the first table under a `## heading`, as lists of cell texts."""
    if '## ' + heading not in text:
        return []
    body = text.split('## ' + heading, 1)[1].split('\n## ', 1)[0]
    rows = []
    for line in body.splitlines():
        if line.startswith('|'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if not cells[0].startswith(':-'):
                rows.append(cells)
    return rows[1:]                                            # without the header row


def rulefile(name):
    """(extensions, base language or '', {list name: set of words}, rule rows) of lang/<name>.mu."""
    with open(os.path.join(HERE, 'lang', name + '.mu'), encoding='utf-8') as f:
        text = f.read()
    files = re.search(r'^Files: (.+)$', text, re.M)
    base = re.search(r'^Extends: (\w+)', text, re.M)
    lists = {row[0]: set(row[1].split()) for row in table(text, 'Words') if len(row) == 2}
    return files.group(1).split(), base.group(1) if base else '', lists, table(text, 'Rules')


def language(path):
    """(name, words) of the file's language: the sets keyword, kwconst, builtin, self, and for
    Cython ckeyword and ctype, from the Words table of lang/python.mu or lang/cython.mu."""
    ext = os.path.splitext(path)[1].lower()
    for name in ('python', 'cython'):
        extensions, base, lists, _ = rulefile(name)
        if ext in extensions:
            py = rulefile('python')[2]
            words = {'keyword': py['keyword'] - SOFT - py['keyword constant'],
                     'kwconst': py['keyword constant'], 'builtin': py['builtin'],
                     'self': py['self'], 'ckeyword': set(), 'ctype': set()}
            if name == 'cython':
                words['ckeyword'] = lists['keyword'] - {'cython'}
                words['ctype'] = lists.get('C type', set())
            return name, words
    return '', {}


def rules(name):
    """The rules of lang/<name>.mu: dicts with id, fg, bg, weight, italic, underline."""
    out = []
    for row in rulefile(name)[3]:
        if len(row) >= 8 and re.fullmatch(r'#[0-9A-Fa-f]{6}', row[3]):
            out.append({'id': row[1], 'fg': row[3], 'bg': row[4] if row[4] != '-' else '',
                        'weight': int(row[5]), 'italic': row[6] == 'yes',
                        'underline': row[7] == 'yes'})
    return out


def css():
    """The style of every role: .r-<id>{...}, and div.ln.b-<id>{background} for the rows that a
    comment line, a docstring or a file banner fills."""
    out = []
    for name in ('python', 'cython'):
        for r in rules(name):
            style = f'color:{r["fg"]};font-weight:{r["weight"]};'
            style += 'font-style:italic;' if r['italic'] else ''
            style += 'text-decoration:underline;' if r['underline'] else ''
            style += f'background:{r["bg"]};' if r['bg'] else ''
            out.append(f'.r-{r["id"]}{{{style}}}')
            if r['id'] in BANDS and r['bg']:
                out.append(f'div.ln.b-{r["id"]}{{background:{r["bg"]}}}')
    return '\n'.join(out) + '\n'


# ---- the first pass: what the file defines and imports -----------------------------------------
def survey(lines):
    """(defined names, modules, imported names, classes, kind of each defined name)."""
    ctx = SimpleNamespace(defined=set(), modules=set(), imported=set(), classes=set(), kinds={})
    for line in lines:
        cm = re.match(r'^\s*(?:cdef\s+)?class\s+(\w+)', line, A)
        if cm:
            ctx.classes.add(cm.group(1))
        m = re.match(r'^\s*(?:async\s+)?(?:cdef\s+class|cdef|cpdef|def|class)\b([^(:]*)', line, A)
        if m:
            word = re.split(r'[\s*]+', m.group(1).strip())[-1]
            if word:
                ctx.defined.add(word)
                ctx.kinds[word] = 'class' if cm else 'def'
    k = 0
    while k < len(lines):
        m = re.match(r'^\s*(?:from\s+(\S+)\s+)?c?import\s+(.+)$', lines[k], A)
        k += 1
        if not m:
            continue
        rest = m.group(2)
        while '(' in rest and ')' not in rest and k < len(lines):
            rest += ' ' + lines[k]
            k += 1
        for item in re.sub(r'[()]', '', rest).split(','):
            mm = re.match(r'^\s*([\w.*]+)(?:\s+as\s+(\w+))?', re.sub(r'#.*', '', item), A)
            if mm and mm.group(1) != '*':
                (ctx.imported if m.group(1) else ctx.modules).add(
                    mm.group(2) or mm.group(1).split('.')[0])
    return ctx


# ---- the lexer ---------------------------------------------------------------------------------
def lex(text, cython, words):
    """The lines of text as lists of (role, text); see the module header."""
    lines = text.split('\n')
    ctx = survey(lines)
    ctx.cy, ctx.words = cython, words
    st = SimpleNamespace(tri=None, role='', docok=True, bd=0, imp=False, ff=False, all=False)
    out = []
    for line in lines:
        if line == '\f':
            st.docok = True                    # a form feed starts a new file
        if st.ff:                              # the line after it names the file
            st.ff = False
            out.append([('fileline', line)])
            continue
        st.ff = line == '\f'
        indoc = st.tri and st.role == 'docstring'
        tokens = lex_line(line, st, ctx)
        if indoc and not tokens:
            tokens.append(('docstring', ''))   # a blank line inside a docstring
        out.append(tokens)
    return out


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
    (lexed again), the conversion and the spec are format code, fields may nest in the spec."""
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
        sub = SimpleNamespace(tri=None, role='', docok=False, bd=depth + 1, imp=False, all=False)
        for role, tok in lex_line(expr, sub, ctx):
            push(role, tok)
    else:
        for m in re.findall(r'\d+|\W+|\w+', expr, A):
            push('number' if m[0].isdigit() else 'default', m)
    rest = body[cut:]
    cv = re.match(r'^![rsa]', rest)
    if cv:
        push('format', cv.group(0))
        rest = rest[2:]
    if rest[:1] == ':':
        push('format', ':')
        for part in re.split(r'(\{[^{}]*\})', rest[1:]):
            if part[:1] == '{' and len(part) > 1:
                field_tokens(part[1:-1], is_code, depth + 1, push, ctx)
            else:
                push('format', part)
    push(br_role(depth), '}')


def regex_tokens(text, depth, push):
    """A regular expression in a string: brackets by depth, literals as string text, digits as
    numbers, | * + ? . ^ $ as operators, \\d-style escapes as escapes."""
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
            m = re.match(r'\d+', text[k:], A).group(0)
            push('number', m)
            k += len(m) - 1
        elif c in '|*+?.^$,':
            flush()
            push('operator', c)
        else:
            lit += c
        k += 1
    flush()


def lex_line(line, st, ctx):
    """One line as (role, text) pairs; st carries what runs over lines (an open triple string,
    the bracket depth, an import or __all__ list that goes on)."""
    out, n, i, first = [], len(line), 0, True
    words, cy = ctx.words, ctx.cy

    def push(role, tok):
        if tok:
            out.append((role, tok))

    started_tri = bool(st.tri)
    defline = bool(DEFLINE.match(line))
    cline = cy and bool(CLINE.match(line))
    depth, annot, after_dot, cy_next = 0, False, False, False
    prev_word, prev2, prev_role = '', '', ''
    imp = 'names' if st.imp else ('mod' if re.match(r'^\s*(?:from\b|c?import\b)', line, A) else '')
    is_from = bool(re.match(r'^\s*from\b', line, A))
    in_all = getattr(st, 'all', False) or bool(re.match(r'^\s*__all__\s*\+?=', line))

    def eat_tri(frm, q, role):
        e = line.find(q, frm)
        if e < 0:
            push(role, line[frm:])
            st.tri, st.role = q, role
            return n
        push(role, line[frm:e + 3])
        st.tri = None
        return e + 3

    if st.tri:
        i = eat_tri(0, st.tri, st.role)
        first = False
    while i < n:
        c, rest = line[i], line[i:]
        if c in ' \t':
            m = re.match(r'\s+', rest)
            push('default', m.group(0))
            i += len(m.group(0))
            continue
        if c == '#':
            if cy and first and re.match(r'^#\s*(?:cython|distutils)\s*:', rest, A):
                push('directive', rest)
                i = n
                break
            role = 'lcomment' if first else 'comment'
            at = 0
            for x in COMMENT_PARTS.finditer(rest):
                push(role, rest[at:x.start()])
                push('url' if x.group(1) else 'marker', x.group(0))
                at = x.end()
            push(role, rest[at:])
            i = n
            break
        m = STRING.match(rest)
        if m:
            p, q = m.group(1), m.group(2)
            if len(q) == 3:
                role = 'docstring' if first and st.docok and not re.search('[fFbB]', p) else 'triple'
                push(role, p + q)
                i = eat_tri(i + len(p) + 3, q, role)
            else:
                i = single_string(line, i, p, q, st, ctx, push, in_all)
            first = False
            prev_role = 'string'
            continue
        if c == '@' and first:
            m = re.match(r'^@[\w.]+', rest, A)
            if m:
                push('cydeco' if m.group(0).startswith('@cython.') else 'decorator', m.group(0))
                i += len(m.group(0))
                first = False
                continue
        if c.isdigit():
            m = NUMBER.match(rest)
            push('number', m.group(0))
            i += len(m.group(0))
            first, prev_role = False, 'number'
            continue
        if cy and c == '<':
            m = CAST.match(rest)
            if m:
                push('cast', m.group(0))
                i += len(m.group(0))
                first, prev_role = False, 'cast'
                continue
        if c.isalpha() and c.isascii() or c == '_':
            m = re.match(r'^[A-Za-z_]\w*', rest, A)
            w = m.group(0)
            after = rest[len(w):]
            nc = after[:1]
            role = 'default'
            if imp and not after_dot and w not in ('from', 'import', 'cimport', 'as'):
                role = 'module' if imp == 'mod' else 'imported'
            elif re.fullmatch(r'__\w+__', w, A):
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
            elif w in words['keyword'] or (w in ('match', 'case') and first
                                           and re.search(r':\s*$', line)):
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
                  and (cline or annot or re.match(r'^\s*[A-Za-z_*\[&]', after))):
                role = 'cobject' if w == 'object' else 'ctype'
                mv = re.match(r'^\[[\s:,1]*\]', after)
                if mv:
                    push('memview', w + mv.group(0))
                    i += len(w) + len(mv.group(0))
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
            elif re.fullmatch(r'[A-Z][A-Z0-9_]+', w, A):
                role = 'constant'
            elif nc == '(':
                role = 'localcall' if w in ctx.defined else 'call'
            push(role, w)
            i += len(w)
            if is_from and w in ('import', 'cimport'):
                imp = 'names'
            if after_dot and cy_next:
                cy_next = False
            after_dot, first = False, False
            prev2, prev_word, prev_role = prev_word, w, role
            continue
        if cy and c == '&' and re.match(r'^&[A-Za-z_]', rest):
            push('pointer', '&')
            i += 1
            first, prev_role = False, 'pointer'
            continue
        if cy and c == '*' and prev_role in ('ctype', 'pointer'):
            push('pointer', '*')
            i += 1
            prev_role = 'pointer'
            continue
        m = OPERATOR.match(rest)
        if m:
            o = m.group(0)
            push('operator', o)
            i += len(o)
            first, prev_role = False, 'operator'
            if o == '->' and defline:
                annot = True
            if o == '=' and defline and depth == 1:
                annot = False
            if o == '!':
                out.pop()
                push('invalid', '!')
            continue
        if c in '()[]{},;.:':
            role = 'punct'
            if c in '([{':
                role = br_role(st.bd)
                st.bd += 1
            elif c in ')]}':
                st.bd -= 1
                if st.bd < 0:
                    st.bd, role = 0, 'invalid'
                else:
                    role = br_role(st.bd)
            push(role, c)
            i += 1
            first, prev_role = False, 'punct'
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth <= 0:
                    annot = False
            if c == '.':
                after_dot = True
            if defline:
                if c == ':' and depth == 1:
                    annot = True
                if c == ',' and depth == 1:
                    annot = False
                if c == ':' and depth == 0:
                    annot = False
            continue
        push('invalid', c)
        i += 1
        first = False
    st.imp = imp != '' and st.bd > 0
    st.all = in_all and st.bd > 0
    if not started_tri or out:
        t = line.strip()
        if t and t[0] != '#' and not (started_tri and st.tri):
            st.docok = bool(DOCOPEN.match(t)) and t.endswith(':')
    return out


def single_string(line, i, p, q, st, ctx, push, in_all):
    """A one-line string that opens at i with prefix p and quote q; returns where it ends."""
    n = len(line)
    is_f = bool(re.search('[fF]', p))
    j = i + len(p) + 1
    buf = p + q
    e = j
    while e < n and line[e] != q:
        e += 2 if line[e] == '\\' else 1
    body, before = line[j:e], line[:i]
    is_re = (not is_f and e < n and (
        re.search(r'\bre\.\w+\(\s*(?:pattern\s*=\s*)?$', before, A)
        or re.search(r'\b\w*(?:regex|pattern|rx)\w*\s*=\s*$', before, A | re.I)
        or (re.search('[rR]', p) and re.search(r'[\[\](){}|*+?^$]|\\[dDwWsSbB]', body))))
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
