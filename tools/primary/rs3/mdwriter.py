r"""mdwriter.py -- write Markdown into a byte array. Plain functions: `md` is a bytearray
that every function appends to and returns. marked.py (md2htm) reads what these write; the
markers are in marker.md.

    from mdwriter import mdwrite, mdwriteln, mdappend, md2str
    md = mdwriteln(None, '| name | r |')                  # a new bytearray
    mdwriteln(md, '|:--|--:|')
    mdwriteln(md, '|', ['a', 'b'], '|', [1.5, 20000], '|')  # two rows, one for each item
    print(md2str(md))

mdwrite(md, *args) -> md       append the args, a space between them, no line end
mdwriteln(md, *args) -> md     the same, then a new line (no args: a blank line)
mdappend(md, *args) -> md      append the args with nothing between them
md2str(md, code='utf8') -> str     the text of md; code='ascii' keeps only ASCII: an accent is
                               dropped, a letter such as a Greek one is spelt (" mu "), another
                               character with a name becomes its name, one without is _

md      None or an int (a new bytearray) or the bytearray of an earlier call.
args    str as it is; bytes as UTF-8; None nothing; a number in engineering form (4
        significant figures, 12.3k, 1.5M, 513e-3: see val2str); anything else str().
        The arguments are columns: a list is a column with one row per item, a single value
        is repeated on every row, and the columns are joined by the separator (a space; none
        for mdappend). Lists of different lengths (none of them 1) raise ValueError; an
        empty list is no rows, and nothing is written.
        A | inside text that goes in a table cell has to be written \| by the caller.

VERSION  M2 m02.v01 (2026-10-28): rebuilt: three writers and md2str; numbers as in mformat.
"""
import math
import unicodedata

__all__ = ['mdwrite', 'mdwriteln', 'mdappend', 'md2str']

SIGFIG = 4
SUFFIX = {3: 'k', 6: 'M', 9: 'G', 12: 'T'}


def val2str(x):
    """One value as text. A float follows mformat (4 significant figures): plain from 0.01
    to 99999, else mantissa and engineering exponent, e3 e6 e9 e12 as k M G T."""
    if isinstance(x, str):
        return x
    if x is None:
        return ''
    if isinstance(x, (bytes, bytearray)):
        return bytes(x).decode('utf-8', 'replace')
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return str(x)
    if isinstance(x, int):
        return str(x)
    ax = abs(x)
    if not (1e-99 <= ax <= 1e99):                       # specials and the very small or large
        if x != x:
            return 'NaN'
        return '0' if ax < 1 else ('Inf' if x > 0 else '-Inf') if ax == math.inf else (
            'inf' if x > 0 else '-inf')
    if ax < 99999.42 and (x == math.floor(x) or ax >= 10 ** SIGFIG - 1):
        return str(math.floor(x))
    rx = round(x, SIGFIG - 1 - math.floor(math.log10(ax)))
    arx = abs(rx)
    mag = math.log10(arx)
    if 0.01 <= arx < 10 ** SIGFIG - 1:                  # plain, fixed significant figures
        text = str(int(rx)) if rx == int(rx) else str(rx)
        want = SIGFIG + (rx < 0) + (mag < 0) + max(0, -math.floor(mag) - 1)
        if '.' in text:
            text += '0' * (want - len(text) + 1)
        return text
    e = 3 * math.floor(mag / 3)                         # engineering: the exponent is a multiple of 3
    xe = round(x / 10.0 ** e, SIGFIG - 2)
    text = str(int(xe)) if xe == int(xe) else str(xe)
    want = math.floor(mag - e + 1) + SIGFIG - 2 + (xe < 0)
    if '.' in text:
        text += '0' * (want - len(text) + 1)
    elif want > len(text):
        text += '.' + '0' * (want - len(text))
    return text + (SUFFIX[e] if e in SUFFIX else f'e{e}')


def put(md, args, sep, end):
    """Append args to md: the columns (a list is a column of rows) joined by sep, then end."""
    if md is None or isinstance(md, int):
        md = bytearray()
    elif not isinstance(md, bytearray):
        raise TypeError('mdwriter: md is None, an int or a bytearray')
    cols = [[val2str(y) for y in x] if isinstance(x, (list, tuple)) else val2str(x)
            for x in args]
    sizes = {len(c) for c in cols if isinstance(c, list) and len(c) != 1}
    if len(sizes) > 1:
        raise ValueError(f'mdwriter: lists of different lengths {sorted(sizes)}')
    count = sizes.pop() if sizes else 1
    if count == 0:                                      # an empty list: no rows, nothing written
        return md
    lines = [sep.join(c if isinstance(c, str) else (c[r] if len(c) > 1 else c[0])
                      for c in cols if isinstance(c, str) or c) for r in range(count)]
    md += (('\n'.join(lines) if count > 1 else lines[0]) + end).encode('utf-8')
    return md


def mdwrite(md, *args):
    return put(md, args, ' ', '')


def mdwriteln(md, *args):
    return put(md, args, ' ', '\n')


def mdappend(md, *args):
    return put(md, args, '', '')


def md2str(md, code='utf8'):
    text = bytes(md).decode('utf-8', 'replace')
    if code == 'utf8':
        return text
    if code != 'ascii':
        raise ValueError("mdwriter: code is 'utf8' or 'ascii'")
    out = []
    for c in text:
        if c < '\x80':
            out.append(c)
            continue
        plain = ''.join(x for x in unicodedata.normalize('NFKD', c)
                        if not unicodedata.combining(x))
        if plain and plain < '\x80':                    # an accent: the letter beneath
            out.append(plain)
            continue
        name = unicodedata.name(c, '')
        if name == 'MICRO SIGN':
            out.append(' mu ')
        elif name.startswith('GREEK'):
            word = name.split()[-1].lower()
            out.append(f' {word} ' if 'SMALL' in name else f' {word.capitalize()} ')
        elif name:
            out.append(f' {name.lower()} ')
        else:
            out.append('_')
    return ''.join(out)
