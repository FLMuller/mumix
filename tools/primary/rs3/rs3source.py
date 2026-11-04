r"""rs3source.py -- one source file, read and analysed once for the blocks that show it (code, methods,
editbox).

    src = read(real)            Source of the file at a real path
    tokens(src) -> [[(role, text)]]     the coloured pieces of each line
    lexed(src) -> [(tokens, in_block, depth)]   the same, with the state each line starts in (rs3lex.lex)
    comments(src) -> {row: [first, last, tag]}  the review comments: a run of lines with one tag is one
    markdown(text) -> str       the HTML of some Markdown, without marked's section comment

A Source has raw (bytes), text, lines (the text split on line ends, no empty last line), base (the sha1 of raw:
an edit must send it back), lang (rs3lex's Lang of the file) and mark (its comment marker: review(lang)).
read raises ValueError for a file that no lang file describes (the message says which extension).

Everything about a language is rs3lex's, from lang/*.mu: the colouring, the comment marker, the functions. This module
loads rs3lex.pyx (use.load) and only reads the file once and keeps the result.

A comment is a run of lines of the language's marker (### for Python, %%% for MATLAB, /// for JS ...) with the
same tag; a reply is the next run, with its own tag.

Cache. read keeps the last CACHED files, keyed by path, and gives the same Source while the file's size and time
are unchanged: code and methods ask for the same file one after the other and the colouring is done once.

VERSION  M1 m01.v03 (2026-11-04): rs3lex is the lexer, the comment marker and the language: no vclang, no
         codelex, and no Markdown tokenizer of its own (the lang file colours it).
         M1 m01.v02 (2026-11-04): Markdown coloured by its syntax (dropped again in v03).
         M1 m01.v01 (2026-11-03): first version: what vcode.pane and codemark each read, once.
"""
import hashlib
import html
import os
import sys

import marked
from marked import md2htm
from use import load

load('rs3lex')           # rs3lex.pyx: built into pyxfiles/ when it has no build or is newer; binds language, lex, review ...

HERE = os.path.dirname(os.path.abspath(__file__))

__all__ = ['Source', 'read', 'tokens', 'lexed', 'comments', 'markdown', 'escape']


def own(module):
    """The module must be rs3's own copy, in this folder. primary/ and tools/ hold modules of the same
    names (the old vcomment's), and a name is found where the path finds it first, or where a
    process already loaded it: rs3 will not run on those."""
    where = os.path.dirname(os.path.abspath(module.__file__))
    if os.path.normcase(where) not in (os.path.normcase(HERE), os.path.normcase(os.path.join(HERE, 'pyxfiles'))):
        raise ImportError(f'rs3 needs its own {module.__name__}.py in {HERE}, but got {module.__file__}')


for module in (sys.modules['rs3lex'], marked):
    own(module)

CACHED = 16
CACHE = {}


class Source:
    __slots__ = ('real', 'raw', 'text', 'lines', 'base', 'lang', 'mark', 'lexed', 'blocks')


def read(real):
    """The Source of a file: ValueError for a kind of file no lang file describes, OSError if it cannot be read."""
    stat = os.stat(real)
    key = (stat.st_mtime_ns, stat.st_size)
    hit = CACHE.get(real)
    if hit is not None and hit[0] == key:
        return hit[1]
    try:
        lang = language(real)
    except NoLanguage as error:
        raise ValueError(str(error))
    src = Source()
    src.real, src.lang = real, lang
    with open(real, 'rb') as f:
        src.raw = f.read()
    src.base = hashlib.sha1(src.raw).hexdigest()
    src.text = src.raw.decode('utf-8', 'replace')
    src.lines = src.text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    if src.lines and src.lines[-1] == '':
        src.lines.pop()
    src.mark = review(lang)
    src.lexed = None
    src.blocks = None
    CACHE[real] = (key, src)
    for old in list(CACHE)[:-CACHED]:
        del CACHE[old]
    return src


def lexed(src):
    """[(tokens, in_block, depth)] for each line, scanned once."""
    if src.lexed is None:
        src.lexed = lex(src.lines, src.lang)
    return src.lexed


def tokens(src):
    """The coloured pieces of each line, [(role, text)]."""
    return [got[0] for got in lexed(src)]


def comments(src):
    """{first row: [first, last, tag]} of the comment runs, rows from 1."""
    if src.blocks is None:
        found = {}
        n = 0
        while n < len(src.lines):
            m = src.mark.match(src.lines[n])
            if m:
                k = n
                while k + 1 < len(src.lines) and (c := src.mark.match(src.lines[k + 1])) \
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
