r"""rs3comment.py -- the verbs of the code, methods and editbox blocks: a file as commentable lines, the
list of its methods, and the comments. Nothing outside the rs3 folder and the standard library is used
(rs3lex.pyx and marked.py, a copy of md2htm, are loaded with use.load, which finds them beside this file).

Verbs (websocket; each takes the page's hash, whose root is the root of its file: rs3util.pathof.
Paths are ./ from HOME, like every path in a message)
    open     {do: 'open', hash, path}        -> {ok, html, base, path}
             the lines of one file under the page's root: colouring, comment threads. `base` is
             the sha1 the file had when it was read; an edit must send it back.
    methods  {do: 'methods', hash, path}     -> {ok, path, file, methods: [{name, owner, kind, line, top, last, size,
             calls, colour, text, band, pie, dot, score, why}]}
             the functions, classes and (Python) constants of the file, by line: name is the short name, owner
             the class (Outer.Inner) or the file's own name, kind def | class | const, top the line where its
             decorators start and last its last line (a class runs to the end of its methods), text its def line or
             the line that gives a constant its value (a constant is a module-level name that starts with three
             capitals, or __all__; a module-level name set to a literal with fewer capitals is listed too, and judged). A Python function or class also has its spaghettichk colour: band (green, '' the
             middle, orange, red), pie (percent of green, grey, orange and red), dot (for a name in __all__: red not
             tested, orange some tested, grey all tested but the functions under it not shown to be reached, green all
             tested and reached; '' for the others), score and why (the reasons), and colour, the band as the colour of its name (red, amber, green).
             file is the same for the whole file (None for a language without facts).
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

The colours of the methods (Python; the other languages are listed uncoloured) are spaghettichk's: see its header. The files
it looks in are the files of the file's own folder, and the suites are b_STEM.py of the test or tests folder beside the
tools folder; Source (rs3lex) keeps every file it reads, so a file that changed is read and judged again.

An edit is written only if the file's sha1 is `base`, the text is under 30000 characters and does not
hold what closes the comment, and the lines it changes are comment lines (for Python the syntax tree is the
same once the comment lines are taken out, for the rest the lines that are not comments). A comment may go on a line
inside a docstring, a string or a block comment: it is a line of that text then, which is what the user asked for (a
string that is data changes, the code may break, and the reply says so: `note`). Nothing else is ever written. The marker is the file's language's,
whatever the page sends. The file is written to a temporary name and renamed over the original.

VERSION  M3 m02.v01 (2026-11-04): the rows of methods come from Source.facts() and are judged by spaghettichk (pie, dot, score, why); the ast code of the list is gone (the edit guard keeps its ast.parse).
         M3 m01.v06 (2026-11-04): the rows of methods carry the owner, the kind (def, class, const), the lines a fold keeps (top, last) and the def line; module-level constants (three capitals to start, or __all__) are rows.
         M3 m01.v05 (2026-11-04): a comment may go inside a docstring or any string (the reply has a note); the syntax tree is compared with the comment lines taken out.
         M3 m01.v04 (2026-11-04): the file is a Source of rs3lex; located is here (pathof); markdown and escape are here; exports only VERBS.
         M3 m01.v03 (2026-11-04): a Markdown file opens as md2htm's page of it, in numbered blocks, its code blocks and the numbers of its text coloured, the columns of numbers centred; YAML front matter plain.
         M3 m01.v02 (2026-11-04): rs3lex is the language, the lexer and the comment marker: no vclang.
         M3 m01.v01 (2026-11-03): rebuilt from rs3vcomment: the work of vcserver.py (edits), vcode.py (the
         rows of other languages), and codemark.py (the rows and the colours of Python) is here, with Class.method
         names from the syntax tree; the file is read once for open and methods (rs3lex's Source).
         (rs3vcomment M2 m01.v01: open gave the lines only. rs2 rsvcomment m02.v01: ./ paths in and out.)
"""
import sys
import ast
import hashlib
import html
import os
import re

from rs3util import pathof
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))  # tools/: the one use.py
from use import load

load('marked')           # marked.py: md2htm, rs3's own copy, found beside this file
load('rs3lex')           # rs3lex.pyx: Source and css
load('spaghettichk')     # spaghettichk.py: isspaghetti

def escape(text):
    return html.escape(text, quote=False)


def markdown(text):
    """The HTML of some Markdown (md2htm starts it with a section comment: dropped)."""
    parts = bytes(md2htm(text)).split(b'-->\n', 1)
    return parts[1].decode('utf-8') if len(parts) > 1 else ''


MAX_BYTES = 4 * 1024 * 1024                                # a source file longer than this is not opened
OPENABLE = ('code', 'md', 'text')
FENCED = re.compile(r'<pre><code class="language-([\w+-]+)">(.*?)</code></pre>', re.S)       # as md2htm writes a fence
FENCE = re.compile(r'^\s*(```|~~~)')
HEADING = re.compile(r'^\s{0,3}#{1,6}(?:\s|$)')
LISTLINE = re.compile(r'^\s*(?:[-*+]|\d{1,9}[.)])\s')
REFDEF = re.compile(r'^\s{0,3}\[[^\]\n]+\]:\s*\S')
NUMBER_TEXT = re.compile(r'(?<![\w.#&])(?:0[xX][0-9a-fA-F]+|\d[\d,]*\.?\d*(?:[eE][+-]?\d+)?)(?!\w)')
TAG = re.compile(r'(<[^>]+>)')
ENTITY = re.compile(r'(&#?\w+;)')
TABLE = re.compile(r'<table\b[^>]*>.*?</table>', re.S)
ROW = re.compile(r'<tr>.*?</tr>', re.S)
CELL = re.compile(r'<(t[dh])((?: [^>]*)?)>(.*?)</t[dh]>', re.S)
NUMBER_CELL = re.compile(r'\s*<span class="r-number">[^<]*</span>\s*')
SKIPPED = {'pre', 'code', 'a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'script', 'style'}      # their text keeps its own look
EXTENSIONS = {'python': 'py', 'py': 'py', 'cython': 'pyx', 'javascript': 'js', 'js': 'js', 'css': 'css', 'matlab': 'm',
              'vba': 'bas', 'text': 'txt', 'txt': 'txt', 'markdown': 'md', 'md': 'md'}


def located(S, msg, field):
    """(page, real path, None) of the page of msg's hash and the source file msg[field] names (a ./ path), or
    (None, None, {ok: false, error}) when either is not allowed: the file must be a text file the tree shows, not
    too long, and inside the root of the page (HOME for a page with no file)."""
    page, why = S['pages'].known(msg.get('hash'))
    if page is None:
        return None, None, {'ok': False, 'error': why}
    path = msg.get(field)
    if pathof(path) is None:
        return None, None, {'ok': False, 'error': f'{path!r} is not a ./ path inside the root'}
    real = pathof(path, kinds=OPENABLE, maxsize=MAX_BYTES)
    if real is None or pathof(real, start=page['root']) is None:
        return None, None, {'ok': False, 'error': f'{path} is not a file this page may open'}
    return page, real, None


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


def comment_html(src, first, last, tag):
    """One comment thread: a run of marker lines of one tag, its Markdown as html."""
    md = '\n'.join(src.mark.match(x).group(2) or '' for x in src.lines[first - 1:last])
    claude = tag == 'cld'
    return (f'<div class="cm" data-who="{"claude" if claude else "user"}" '
            f'data-initials="{"" if claude else escape(tag)}" data-first="{first}" '
            f'data-last="{last}" data-md="{html.escape(md)}">'
            f'<span class="mg"><i class="dot"></i></span><div class="cmt">{markdown(md)}'
            f'<a class="reply" href="#">reply</a></div></div>')


def md_blocks(lines, first, last):
    """[[first, last]] rows of the top-level blocks of the Markdown lines first..last: cut at blank lines but never
    inside a fenced code block, and a list with blank lines between its items stays one block. A heading line is a
    block of its own, even with text right under it, so that it has its own number."""
    found, start, fence = [], None, None
    for row in range(first, last + 1):
        line = lines[row - 1]
        mark = FENCE.match(line)
        if fence is None and not line.strip():
            if start is not None:
                found.append([start, row - 1])
                start = None
            continue
        if fence is None and HEADING.match(line):         # a heading is a block of its own
            if start is not None:
                found.append([start, row - 1])
            found.append([row, row])
            start = None
            continue
        if start is None:
            start = row
        if fence is None and mark:
            fence = mark.group(1)
        elif fence is not None and mark and mark.group(1) == fence:
            fence = None
    if start is not None:
        found.append([start, last])
    merged = []
    for block in found:
        if merged and LISTLINE.match(lines[merged[-1][0] - 1]) and (
                LISTLINE.match(lines[block[0] - 1]) or lines[block[0] - 1].startswith('  ')):
            merged[-1][1] = block[1]                      # the blank lines between are inside it
        else:
            merged.append(block)
    return merged


def coloured(page):
    """md2htm's html with its fenced code blocks coloured by the lang file of their language (the blocks of a
    language no lang file describes are left as they are)."""
    def one(m):
        ext = EXTENSIONS.get(m.group(1).lower())
        if ext is None:
            return m.group(0)
        lines = html.unescape(m.group(2)).split('\n')
        if lines and lines[-1] == '':
            lines.pop()
        pieces = Source.coloured(ext, '\n'.join(lines))
        if pieces is None:                           # no lang file has the extension
            return m.group(0)
        shown = '\n'.join(line_html(got, text) for got, text in zip(pieces, lines))
        return f'<pre><code class="language-{m.group(1)}">{shown}\n</code></pre>'
    return FENCED.sub(one, page)


def front_matter(lines):
    """The row of the closing --- of the YAML front matter at the top of the file (--- first, --- again within the
    first 40 lines), or 0 when there is none."""
    if not lines or lines[0].rstrip() != '---':
        return 0
    for row in range(2, min(len(lines), 40) + 1):
        if lines[row - 1].rstrip() == '---':
            return row
    return 0


def numbered(page):
    """md2htm's html with the numbers in its text (table cells, paragraphs, lists) wrapped in the number role of the
    lang files, so they have its colour. Code, links and headings are left as they are, and so are the entities."""
    out, skip = [], 0
    for part in TAG.split(page):
        if part.startswith('<'):
            name = re.match(r'</?(\w+)', part)
            if name and name.group(1).lower() in SKIPPED and not part.endswith('/>'):
                skip = max(0, skip + (-1 if part.startswith('</') else 1))
            out.append(part)
        elif skip or not part:
            out.append(part)
        else:
            out.append(''.join(p if p.startswith('&') else NUMBER_TEXT.sub(r'<span class="r-number">\g<0></span>', p)
                               for p in ENTITY.split(part)))
    return ''.join(out)


def centred(page):
    """The tables of md2htm's html with the columns of numbers centred. A column is one when every cell of its body
    is nothing but a number (a blank cell does not count against it, and one number is enough): its header is
    centred with it. An alignment the author wrote (:-- :-: --:, which md2htm makes an align attribute) is kept, and
    the rest of the cells are left."""
    def table(found):
        text = found.group(0)
        rows = [CELL.findall(row) for row in ROW.findall(text)]
        body = [row for row in rows if row and row[0][0] == 'td']
        width = max((len(row) for row in rows), default=0)
        numeric = {k for k in range(width)
                   if any(k < len(row) and NUMBER_CELL.fullmatch(row[k][2]) for row in body)
                   and all(k >= len(row) or not row[k][2].strip() or NUMBER_CELL.fullmatch(row[k][2]) for row in body)}
        if not numeric:
            return text

        def row(found_row):
            at = [-1]

            def cell(m):
                at[0] += 1
                if at[0] in numeric and 'align=' not in m.group(2):
                    return f'<{m.group(1)}{m.group(2)} align="center">{m.group(3)}</{m.group(1)}>'
                return m.group(0)
            return CELL.sub(cell, found_row.group(0))
        return ROW.sub(row, text)
    return TABLE.sub(table, page)


def markdown_rows(src):
    """A Markdown file as md2htm formats it: a row for each top-level block, numbered by its first line, with the
    comment threads between them. The reference lines of the file ([x]: url) go to every block, so a link to one
    works wherever it is."""
    lines, blocks, out = src.lines, src.comments(), []
    refs = [x for x in lines if REFDEF.match(x)]
    starts = sorted(blocks)
    row = 1
    done = front_matter(lines)
    if done and not any(r <= done for r in starts):        # front matter is data, not a heading: shown plain and small
        out.append(f'<div class="ln md" id="L1" data-n="1"><span class="no">1</span><span class="mg"></span>'
                   f'<div class="mdblock front"><pre>{escape(chr(10).join(lines[1:done - 1]))}</pre></div></div>')
        row = done + 1
    while row <= len(lines):
        if row in blocks:
            first, last, tag = blocks[row]
            out.append(comment_html(src, first, last, tag))
            row = last + 1
            continue
        stop = next((s for s in starts if s > row), len(lines) + 1)        # the next comment, or the end
        for first, last in md_blocks(lines, row, stop - 1):
            text = '\n'.join(lines[first - 1:last] + ([''] + refs if refs else []))
            out.append(f'<div class="ln md" id="L{first}" data-n="{first}"><span class="no">{first}</span>'
                       f'<span class="mg"></span><div class="mdblock">{centred(numbered(coloured(markdown(text))))}</div></div>')
        row = stop
    return '\n'.join(out)


def rows_html(src):
    """The html of the lines and the comment threads of a Source: see the module header. A Markdown file is
    shown as md2htm formats it (markdown_rows)."""
    if src.lang.mode == 'markdown':
        return markdown_rows(src)
    pieces = src.tokens()
    blocks = src.comments()
    out = []
    row = 1
    while row <= len(src.lines):
        if row in blocks:
            first, last, tag = blocks[row]
            out.append(comment_html(src, first, last, tag))
            row = last + 1
            continue
        rule = bool(src.mark.separator.match(src.lines[row - 1]))
        here = pieces[row - 1] if pieces else None
        cls = ' sep' if rule else (band(here, src.lang.mode == 'python') if here else '')
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
        src = Source.read(real)
    except (OSError, ValueError) as error:
        return refuse(f'{msg.get("path")}: {error}')
    return {'html': rows_html(src), 'base': src.base, 'path': msg.get('path')}


# ---- methods: the functions and their colours ---------------------------------------------------
TEXT_MAX = 200                                          # the longest def line or value a row carries
BANDS = {'red': 'red', 'orange': 'amber', 'green': 'green', '': ''}     # the colour of a name, from the band of its pie


def areas(real):
    """(area, testarea) of a file for spaghettichk: the files of its own folder, and the suites of the tests folder next to
    its tools folder (tests live in ./test or ./tests beside ./tools); '' for what is outside HOME."""
    here = os.path.dirname(real).replace('\\', '/')
    short = pathof(here)
    cut = (here + '/').find('/tools/')
    tests = pathof(here[:cut]) if cut > 0 else None
    return (short + '/*.{py,pyx}' if short else ''), (tests + '/{test,tests}/b_*.py' if tests else '')


def row_of(src, name, owner, kind, line, top, last, calls, colour=None):
    """One row of the methods list: name is the short name, owner the class (Outer.Inner) or the file's own name, kind
    def | class | const; top is where its decorators start, last its last line (the lines a fold of it keeps); text is its
    def line, or for a constant the line that gives its value. colour is the spaghettichk colour of a function or class:
    band, pie (percent of green, grey, orange, red), dot, score and why (the reasons)."""
    row = {'name': name, 'owner': owner, 'kind': kind, 'line': line, 'top': top, 'last': last, 'size': last - line + 1,
           'calls': calls, 'colour': '', 'text': src.lines[line - 1].strip()[:TEXT_MAX]}
    if colour is not None:
        row.update(colour='' if kind == 'const' else BANDS[str(colour)], band=str(colour), pie=list(colour.pie), dot=colour.dot,
                   score=round(colour.score, 1), why=colour.why)
    return row


def methods_of(src):
    """({the rows of the methods list, by line}, the colour of the file): see the module header. A Python file's rows come
    from its facts and are judged by spaghettichk; the other languages are listed by their lang file's Function and Class
    lines, uncoloured."""
    facts = src.facts()
    stem = os.path.splitext(os.path.basename(src.real))[0]
    if facts is None:
        used = {}
        for word in re.findall(r'\w+', src.text):
            used[word] = used.get(word, 0) + 1
        return [row_of(src, name.rsplit('.', 1)[-1], name.rpartition('.')[0] or stem, 'class' if kind == 'class' else 'def',
                       first, first, last, max(0, used.get(name.rsplit('.', 1)[-1], 0) - 1))
                for name, first, last, kind in src.functions()], None
    whole = isspaghetti(src, *areas(src.real))
    out = [row_of(src, d.name, d.owner or stem, d.kind, d.first, d.top, d.last, facts.words.get(d.name, 0), whole.rows.get(d.first))
           for d in facts.defs]
    out += [row_of(src, name, stem, 'const', first, first, last, facts.words.get(name, 0), whole.rows.get(first))
            for name, first, last in facts.consts + facts.literals]
    if 0 in whole.rows:                                        # a file with no __all__: a red note row at the top
        note = row_of(src, '__all__', stem, 'const', 1, 1, 1, 0, whole.rows[0])
        note['text'] = 'no __all__ in this file: nothing is exposed, and nothing can be tested through it'
        out.append(note)
    out.sort(key=lambda row: row['line'])
    return out, {'band': str(whole), 'pie': list(whole.pie), 'dot': whole.dot, 'score': round(whole.score, 1), 'why': whole.why}


def methods(msg, S):
    page, real, bad = located(S, msg, 'path')
    if bad:
        return bad
    try:
        src = Source.read(real)
    except (OSError, ValueError) as error:
        return refuse(f'{msg.get("path")}: {error}')
    rows, whole = methods_of(src)
    return {'path': msg.get('path'), 'methods': rows, 'file': whole}


# ---- the edits ----------------------------------------------------------------------------------
def skeleton(text, lang, is_comment):
    """What must not change when comments change: for Python the syntax tree of the text without its comment lines (one
    that is a line of a string goes out of the string too, so a comment may be written in a docstring); for the rest the
    lines that are not comments."""
    kept = [x.rstrip() for x in text.split('\n') if not is_comment(x)]
    if lang.name == 'python':
        try:
            return ast.dump(ast.parse('\n'.join(kept)))
        except (SyntaxError, ValueError):
            pass
    return kept


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
    try:
        src = Source.read(real)
    except (OSError, ValueError) as error:
        return refuse(f'edit: {error}')
    lang, mark = src.lang, src.mark                   # the file's language says the marker
    if lang.close and lang.close in text:
        return refuse(f'edit: the text holds {lang.close}, which would end the comment')
    if src.base != base:
        return refuse('edit: the file has changed since the page read it')
    eol = '\r\n' if b'\r\n' in src.raw else '\n'
    try:
        old = src.raw.decode('utf-8').replace('\r\n', '\n')
    except UnicodeDecodeError:
        return refuse('edit: the file is not UTF-8')
    lines = old.split('\n')
    try:
        if kind == 'update':
            first, last = int(msg['first']), int(msg['last'])
            block = lines[first - 1:last]
            if not 1 <= first <= last <= len(lines) or not block or not all(mark.match(x) for x in block):
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
    new = mark.write(indent, tag, text) if text.strip() else []
    after = lines[:first - 1] + new + lines[last:]
    if skeleton('\n'.join(after), lang, mark.match) != skeleton(old, lang, mark.match):
        return refuse('edit: more than comments would change')
    data = eol.join(after).encode('utf-8')
    temp = real + '.tmp'
    with open(temp, 'wb') as f:
        f.write(data)
    os.replace(temp, real)
    S['say'](f'edit: {real} lines {first}-{last} now {len(new)} lines')
    got = {'base': hashlib.sha1(data).hexdigest(), 'first': first, 'last': first + len(new) - 1,
           'delta': len(new) - (last - first + 1), 'html': markdown(text), 'removed': not new}
    if new and src.inside(first):
        got['note'] = 'saved inside a string or a block comment: the comment is a line of its text'
    return got


def update(msg, S):
    return edit(msg, S, 'update')


def insert(msg, S):
    return edit(msg, S, 'insert')


VERBS = {'open': open_file, 'methods': methods, 'check': check, 'update': update, 'insert': insert}
__all__ = ['VERBS']
