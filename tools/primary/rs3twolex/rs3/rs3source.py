r"""rs3source.py -- one source file, read and analysed once for the blocks that show it (code, methods,
editbox).

    src = read(real)            Source of the file at a real path
    tokens(src) -> [[(role, text)]] or None     the coloured pieces of each line; None: stays plain
    comments(src) -> {row: [first, last, tag]}  the review comments: a run of lines with one tag is one
    markdown(text) -> str       the HTML of some Markdown, without marked's section comment

A Source has raw (bytes), text, lines (the text split on line ends, no empty last line), base (the
sha1 of raw: an edit must send it back), spec (vclang's Spec of the file's language) and name, words
(codelex's language of a Python or Cython file; '' for the rest).

How a file is coloured. Python and Cython are coloured by codelex (lang/python.mu, cython.mu); MATLAB,
JavaScript, CSS, notes and Markdown by vclang.lexgen from their lang file (markdown.mu: the markup is
shown as it is, coloured by those rules; it is not rendered). Both give each
line as (role, text) pieces: <span class="r-ROLE"> in the page (codelex.css() holds the roles' colours).

The comment of a file is the triplet of its language (### for Python, %%% for MATLAB, /// for JS ...),
read by vclang.comment_regex: groups (tag, text). A comment is a run of such lines with the same tag; a
reply is the next run, with its own tag.

Cache. read keeps the last CACHED files, keyed by path, and gives the same Source while the file's
size and time are unchanged: code and methods ask for the same file one after the other and the colouring
is done once.

Markdown. markdown.mu has no rules for the markup, so rs3source colours it by syntax: headings, bold, italic,
`code`, links, list marks, quotes, tables, rules and fenced code, each with a role of the lang files (the colours
are theirs). The text is shown as it is written, not rendered.

VERSION  M1 m01.v02 (2026-11-04): Markdown is coloured by its syntax (markdown_pieces).
         M1 m01.v01 (2026-11-03): first version: what vcode.pane and codemark each read, once.
"""
import hashlib
import html
import os
import re

import codelex
import marked
import vclang
from marked import md2htm

__all__ = ['Source', 'read', 'tokens', 'comments', 'markdown', 'markdown_pieces', 'escape']

HERE = os.path.dirname(os.path.abspath(__file__))


def own(module):
    """The module must be rs3's own copy, in this folder. primary/ and tools/ hold modules of the same
    names (the old vcomment's), and a name is found where the path finds it first, or where a
    process already loaded it: rs3 will not run on those."""
    where = os.path.dirname(os.path.abspath(module.__file__))
    if os.path.normcase(where) != os.path.normcase(HERE):
        raise ImportError(f'rs3 needs its own {module.__name__}.py in {HERE}, but got {module.__file__}')


for module in (codelex, marked, vclang):
    own(module)

CACHED = 16
CACHE = {}

FENCE = re.compile(r'^\s*(```|~~~)')
HEADING = re.compile(r'^(\s{0,3})(#{1,6})(\s.*|)$')
RULE = re.compile(r'^\s{0,3}([-*_])(?:\s*\1){2,}\s*$')
QUOTE = re.compile(r'^(\s{0,3}>+\s?)(.*)$')
LISTMARK = re.compile(r'^(\s*)([-*+]|\d{1,9}[.)])(\s+)(.*)$')
TABLEROW = re.compile(r'^\s*\|.*\|\s*$')
TABLEGAP = re.compile(r'^[\s|:-]+$')
INLINE = re.compile(r'(\*\*[^*]+\*\*|__[^_]+__|`[^`]+`|!?\[[^\]]*\]\([^)]*\)|~~[^~]+~~|'
                    r'(?<![\w*])\*[^*\s][^*]*\*(?!\w)|(?<![\w_])_[^_\s][^_]*_(?!\w)|https?://[^\s)>\]]+)')
LINK = re.compile(r'^(!?\[[^\]]*\])(\([^)]*\))$')


def inline_pieces(text, role='default'):
    """The pieces of one line of running text: bold, italic, `code`, links and addresses."""
    out, at = [], 0
    for m in INLINE.finditer(text):
        if m.start() > at:
            out.append((role, text[at:m.start()]))
        word = m.group(0)
        if word.startswith(('**', '__')):
            out.append(('keyword', word))                         # bold: blue, bold
        elif word.startswith('`'):
            out.append(('special', word))                         # code span
        elif word.startswith('~~'):
            out.append(('comment', word))                         # struck through
        elif word.startswith(('http://', 'https://')):
            out.append(('url', word))
        elif word[0] in '[!':
            link = LINK.match(word)
            if link:
                out.extend([('imported', link.group(1)), ('url', link.group(2))])    # the text, then the address
            else:
                out.append((role, word))
        else:
            out.append(('decorator', word))                       # italic: amber, italic
        at = m.end()
    if at < len(text):
        out.append((role, text[at:]))
    return out


def markdown_pieces(lines):
    """[[(role, text)]] for the lines of a Markdown file; the texts of a line join back into it."""
    out, fenced = [], None
    for line in lines:
        fence = FENCE.match(line)
        if fenced:
            out.append([('special', line)] if fence and fence.group(1) == fenced else [('constant', line)])
            if fence and fence.group(1) == fenced:
                fenced = None
        elif fence:
            fenced = fence.group(1)
            out.append([('special', line)])
        elif HEADING.match(line):
            m = HEADING.match(line)
            out.append([p for p in (('default', m.group(1)), ('defname', m.group(2)), ('classname', m.group(3))) if p[1]])
        elif RULE.match(line):
            out.append([('punct', line)])
        elif QUOTE.match(line):
            m = QUOTE.match(line)
            out.append([('operator', m.group(1))] + inline_pieces(m.group(2), 'annotation'))
        elif TABLEROW.match(line) and TABLEGAP.match(line):
            out.append([('constant', line)])                      # the | --- | --- | row
        elif TABLEROW.match(line):
            row = []
            for k, cell in enumerate(line.split('|')):
                if k:
                    row.append(('br0', '|'))
                row.extend(inline_pieces(cell))
            out.append([p for p in row if p[1]])
        elif LISTMARK.match(line):
            m = LISTMARK.match(line)
            out.append([p for p in (('default', m.group(1)), ('keyword', m.group(2)), ('default', m.group(3))) if p[1]]
                       + inline_pieces(m.group(4)))
        else:
            out.append(inline_pieces(line))
    return [row or [('default', '')] for row in out]


class Source:
    __slots__ = ('real', 'raw', 'text', 'lines', 'base', 'spec', 'name', 'words', 'rx', 'sep',
                 'pieces', 'lexed', 'blocks')


def read(real):
    """The Source of a file: ValueError for a kind of file that is not opened, OSError if it cannot
    be read."""
    stat = os.stat(real)
    key = (stat.st_mtime_ns, stat.st_size)
    hit = CACHE.get(real)
    if hit is not None and hit[0] == key:
        return hit[1]
    spec = vclang.spec_for(real)
    if spec is None or vclang.kind_of(real) not in ('code', 'md', 'text'):
        raise ValueError('not a file that is opened')
    src = Source()
    src.real, src.spec = real, spec
    with open(real, 'rb') as f:
        src.raw = f.read()
    src.base = hashlib.sha1(src.raw).hexdigest()
    src.text = src.raw.decode('utf-8', 'replace')
    src.lines = src.text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    if src.lines and src.lines[-1] == '':
        src.lines.pop()
    src.name, src.words = codelex.language(real)
    src.rx = vclang.comment_regex(spec)
    src.sep = vclang.separator_regex(spec)
    src.pieces = None
    src.lexed = None
    src.blocks = None
    CACHE[real] = (key, src)
    for old in list(CACHE)[:-CACHED]:
        del CACHE[old]
    return src


def tokens(src):
    """The coloured pieces of each line, [(role, text)]; None for a file that is not coloured."""
    if src.pieces is None:
        if src.name:
            src.pieces = codelex.lex('\n'.join(src.lines), src.name == 'cython', src.words)
        elif src.spec.mode == 'markdown':
            src.pieces = markdown_pieces(src.lines)
        elif src.spec.mode in ('code', 'css', 'text'):
            src.lexed = vclang.lexgen(src.lines, src.spec)      # vclang.functions takes these whole
            src.pieces = [got[0] for got in src.lexed]
        else:
            src.pieces = False
    return src.pieces or None


def comments(src):
    """{first row: [first, last, tag]} of the comment runs, rows from 1."""
    if src.blocks is None:
        found = {}
        n = 0
        while n < len(src.lines):
            m = src.rx.match(src.lines[n])
            if m:
                k = n
                while k + 1 < len(src.lines) and (c := src.rx.match(src.lines[k + 1])) \
                        and c.group(1) == m.group(1):
                    k += 1
                found[n + 1] = [n + 1, k + 1, m.group(1)]
                n = k
            n += 1
        src.blocks = found
    return src.blocks


def markdown(text):
    """The HTML of some Markdown (marked.md2htm starts it with a section comment: dropped)."""
    parts = bytes(md2htm(text)).split(b'-->\n', 1)
    return parts[1].decode('utf-8') if len(parts) > 1 else ''


def escape(text):
    return html.escape(text, quote=False)
