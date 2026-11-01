# cython: language_level=3
"""
xlsheetfun.pyx -- the hot loops of xlsheet in Cython: write a block, scan a sheet, emit a sheet.

Why
    A sheet is thousands of cells and three loops touch every one: writing a block of values
    into the grid, scanning the worksheet XML into the grid, and listing the grid as XML.
    Done in Python each cell costs a handful of interpreter steps; done here the numbers are
    C doubles and C longs and only the tuples that the grid stores are Python objects.
    xlsheet.py keeps the structure (tables, fallbacks, the parts around the cells) and the
    pure-Python versions of these loops, which are the reference the tests hold these to.

Algorithm
    write_rows. For a block written with no style: a float or int gets its number format
    from its magnitude in C (numfmt_code, the same rule as xlstyle.auto_numfmt), the style
    index of each of the six formats is asked of xlsheet once and kept, a text goes through
    the book's text kv, and anything else (numpy values, other objects) is handed to
    xlsheet.make_cell. One tuple and one kv write per cell.
    scan_cells. Two passes over the <sheetData> body. The first walks it with pointers and
    parses every cell of the plain form (attributes r, s, t in that order, an optional
    <v>, no formula, type absent or s or b, or t="str" / t="e" / t="inlineStr" with one
    <t>) into a C array; anything else makes it return -1 before a single cell is written,
    and the caller takes the general path. A text held in the cell goes to the book's text kv
    as the file's own bytes (kv byte keys: no decode, no encode), behind  when it starts
    with "[" or ; a text with an entity goes to entity_text (Python decodes it). The second turns the array into tuples and kv writes. Numbers are parsed with
    PyOS_string_to_double and must consume the whole text.
    emit_grid. Lists the grid's keys, parses each "[r c]" in C, checks they are already in
    row order (a sheet written row by row is) and sorts only when they are not, then writes
    each cell's XML. Floats are formatted in C: a whole number below 1e15 as an integer, the
    rest as "%.15g", exactly as xlstyle.num_text does.
    Cost: O(cells) each; the kv write (about 0.4 us) is most of what is left.

Use
    from xlsheetfun import write_rows, scan_cells, emit_grid
    write_rows(cells, tables, rows, row0, col0, make_cell, style_id)
    count = scan_cells(body, cells, xfs, remap, texts, entity_text)   # -1: nothing written
    xml, widest, ncols = emit_grid(cells, texts, col2letter, formulas, cached_xml)

Versions
    M01  m01.v02  2026-11-01  scan_cells takes the text held in the cell (inlineStr, str, e)
                              into the text kv with byte keys.
    M01  m01.v01  2026-10-31  first version: the three loops.
"""

from libc.math cimport floor, fabs, log10, isfinite
from libc.stdlib cimport malloc, free
from libc.string cimport memchr, memcmp
from cpython.bytes cimport PyBytes_AS_STRING, PyBytes_GET_SIZE
from cpython.mem cimport PyMem_Free
from cpython.unicode cimport PyUnicode_AsUTF8AndSize

cdef extern from "Python.h":
    char* PyOS_double_to_string(double val, char format_code, int precision, int flags, int* ptype)

__all__ = ["write_rows", "scan_cells", "emit_grid"]

DEF NUM = 0
DEF TXT = 1
DEF BOOL = 2
DEF BLANK = 3
DEF FML = 4

cdef tuple FORMATS = ('0', '0.#', '0.##', '0.###', '0.####', '0.##E+00')


cdef inline int numfmt_code(double v):
    # xlstyle.auto_numfmt as a small integer: -1 none, 0..4 '0' or '0.' + '#' * code, 5 E+00
    cdef double m
    cdef int places
    if v == 0.0 or not isfinite(v):
        return -1
    m = fabs(v)
    if m == floor(m) and m < 1e7:
        return 0
    if 0.01 <= m < 1e5:
        places = 3 - <int>floor(log10(m)) - 1
        if places < 0:
            places = 0
        return places
    return 5


def write_rows(cells, tables, list rows, Py_ssize_t row0, Py_ssize_t col0, make_cell, style_id):
    """Write a block of values with the default style: rows is a list of lists, the first
    cell goes to (row0, col0). Anything but float, int, str, bool and None goes to
    make_cell(tables, value, {})."""
    cdef list xfcode = [-1, -1, -1, -1, -1, -1]
    cdef Py_ssize_t i, j, n, m
    cdef int code, xf
    cdef double v
    cdef list line
    texts = tables.texts
    for i in range(len(rows)):
        line = rows[i]
        m = len(line)
        for j in range(m):
            item = line[j]
            t = type(item)
            if t is float or t is int:
                v = <double>item
                code = numfmt_code(v)
                if code < 0:
                    xf = 0
                else:
                    xf = xfcode[code]
                    if xf < 0:
                        xf = style_id(tables, {'numfmt': FORMATS[code]})
                        xfcode[code] = xf
                cells[(row0 + i, col0 + j)] = (NUM, item, xf)
            elif t is str:
                if item == '':
                    cells[(row0 + i, col0 + j)] = (BLANK, None, 0)
                else:
                    key = '\x01' + item if (item[0] == '[' or item[0] == '\x01') else item
                    found = texts.kvr(key)
                    if found is None:
                        found = len(texts)
                        texts.kvw(key, found)
                    cells[(row0 + i, col0 + j)] = (TXT, found, 0)
            elif t is bool:
                cells[(row0 + i, col0 + j)] = (BOOL, item, 0)
            elif item is None:
                cells[(row0 + i, col0 + j)] = (BLANK, None, 0)
            else:
                cells[(row0 + i, col0 + j)] = make_cell(tables, item, {})


# ---------------------------------------------------------------------------- scan -------
cdef struct Parsed:
    long row
    long col
    long style          # -1: no s attribute
    int kind            # 0 number or blank, 1 shared string, 2 boolean, 3 text in the cell
    int amp             # kind 3: the text holds an '&' (entities to decode)
    long number         # the string index, or 1 for a true boolean
    Py_ssize_t vstart   # where the number text starts in the body, and its length
    Py_ssize_t vlen
    int has_value


cdef inline bint is_digit(char c):
    return 48 <= c <= 57


cdef Py_ssize_t parse_cell(const char* p, Py_ssize_t n, Py_ssize_t pos, Parsed* out):
    # pos is at the '<' of '<c ': returns the position after the cell, or -1 when the cell
    # is not of the plain form.
    cdef Py_ssize_t start, vstart, vlen
    cdef long col = 0, row = 0
    cdef int kind = 0
    cdef int has_value = 0
    cdef Py_ssize_t numstart = 0, numlen = 0, tlen
    cdef long number = 0
    cdef int amp = 0
    cdef bint inline = False
    if pos + 7 > n or memcmp(p + pos, b'<c r="', 6) != 0:
        return -1
    pos += 6
    start = pos
    while pos < n and 65 <= p[pos] <= 90:
        col = col * 26 + (p[pos] - 64)
        pos += 1
    if pos == start or pos >= n or not is_digit(p[pos]):
        return -1
    while pos < n and is_digit(p[pos]):
        row = row * 10 + (p[pos] - 48)
        pos += 1
    if pos + 1 >= n or p[pos] != 34:                       # the closing quote of r
        return -1
    pos += 1
    out.style = -1
    if pos + 4 < n and memcmp(p + pos, b' s="', 4) == 0:
        pos += 4
        start = pos
        out.style = 0
        while pos < n and is_digit(p[pos]):
            out.style = out.style * 10 + (p[pos] - 48)
            pos += 1
        if pos == start or pos >= n or p[pos] != 34:
            return -1
        pos += 1
    if pos + 4 < n and memcmp(p + pos, b' t="', 4) == 0:
        if pos + 7 < n and p[pos + 5] == 34 and p[pos + 4] == 115:      # t="s"
            kind = 1
        elif pos + 7 < n and p[pos + 5] == 34 and p[pos + 4] == 98:     # t="b"
            kind = 2
        else:
            tlen = 0
            while pos + 4 + tlen < n and p[pos + 4 + tlen] != 34 and tlen < 10:
                tlen += 1
            if pos + 4 + tlen >= n:
                return -1
            if tlen == 3 and memcmp(p + pos + 4, b'str', 3) == 0:
                kind = 3                                   # a formula-free text result
            elif tlen == 1 and p[pos + 4] == 101:          # t="e"
                kind = 3
            elif tlen == 9 and memcmp(p + pos + 4, b'inlineStr', 9) == 0:
                kind = 3
                inline = True
            else:
                return -1                                  # n, d, ...
            pos += 5 + tlen
        if kind != 3:
            pos += 6
    if pos + 1 < n and p[pos] == 47 and p[pos + 1] == 62:  # '/>': an empty cell
        pos += 2
    elif pos < n and p[pos] == 62:                         # '>'
        pos += 1
        if inline:
            if pos + 6 > n or memcmp(p + pos, b'<is><t', 6) != 0:
                return -1
            pos += 6
            if pos < n and p[pos] == 62:
                pos += 1
            elif pos + 22 <= n and memcmp(p + pos, b' xml:space="preserve">', 22) == 0:
                pos += 22
            else:
                return -1
            vstart = pos
            while pos < n and p[pos] != 60:
                if p[pos] == 38:
                    amp = 1
                pos += 1
            vlen = pos - vstart
            if pos + 10 > n or memcmp(p + pos, b'</t></is>', 9) != 0:
                return -1
            pos += 9
            if vlen > 0:
                has_value = 1
                numstart = vstart
                numlen = vlen
        elif pos + 3 <= n and memcmp(p + pos, b'<v>', 3) == 0:
            pos += 3
            vstart = pos
            while pos < n and p[pos] != 60:
                if p[pos] == 38:
                    amp = 1
                pos += 1
            vlen = pos - vstart
            if pos + 4 > n or memcmp(p + pos, b'</v>', 4) != 0:
                return -1
            pos += 4
            if vlen > 0:
                has_value = 1
                if kind == 3:
                    numstart = vstart
                    numlen = vlen
                elif vlen >= 63:
                    return -1
                elif kind == 1:
                    for start in range(vstart, vstart + vlen):
                        if not is_digit(p[start]):
                            return -1
                        number = number * 10 + (p[start] - 48)
                elif kind == 2:
                    if vlen == 1 and p[vstart] == 49:
                        number = 1
                    elif vlen == 4 and memcmp(p + vstart, b'true', 4) == 0:
                        number = 1
                    else:
                        number = 0
                else:
                    numstart = vstart
                    numlen = vlen
        if pos + 4 > n or memcmp(p + pos, b'</c>', 4) != 0:
            return -1
        pos += 4
    else:
        return -1
    out.row = row
    out.col = col
    out.kind = kind
    out.amp = amp
    out.number = number
    out.vstart = numstart
    out.vlen = numlen
    out.has_value = has_value
    return pos


def scan_cells(bytes body, cells, list xfs, remap, texts=None, entity_text=None):
    """Read the cells of a <sheetData> body (the part between the tags) into the grid when
    every cell has the plain form; returns the number of cells seen, or -1 (nothing written).
    texts is the book's text kv; entity_text(raw bytes) gives the text position of a text with
    entities in it; without them a cell that holds its own text makes the scan return -1."""
    cdef const char* p = PyBytes_AS_STRING(body)
    cdef Py_ssize_t n = PyBytes_GET_SIZE(body), pos = 0, count = 0, cap = 1024, k, end
    cdef Parsed* found = <Parsed*>malloc(cap * sizeof(Parsed))
    cdef Parsed* grown
    cdef long nxf = len(xfs), xf
    cdef unsigned char first
    cdef char* tag
    if found == NULL:
        raise MemoryError()
    try:
        while pos < n:
            if p[pos] != 60:                                # text between tags: not ours
                return -1
            if pos + 3 < n and p[pos + 1] == 99 and p[pos + 2] == 32:          # '<c '
                if count == cap:
                    cap *= 2
                    grown = <Parsed*>malloc(cap * sizeof(Parsed))
                    if grown == NULL:
                        raise MemoryError()
                    for k in range(count):
                        grown[k] = found[k]
                    free(found)
                    found = grown
                pos = parse_cell(p, n, pos, found + count)
                if pos < 0 or (found[count].kind == 3 and texts is None):
                    return -1
                count += 1
            elif pos + 5 <= n and memcmp(p + pos, b'<row ', 5) == 0:
                tag = <char*>memchr(p + pos, 62, n - pos)
                if tag == NULL:
                    return -1
                pos = tag - p + 1
            elif pos + 6 <= n and memcmp(p + pos, b'</row>', 6) == 0:
                pos += 6
            else:
                return -1
        for k in range(count):
            xf = found[k].style
            if xf < 0 or xf >= nxf:
                xf = 0
            if not found[k].has_value:
                if xfs[xf]:
                    cells[(found[k].row, found[k].col)] = (BLANK, None, xf)
            elif found[k].kind == 1:
                cells[(found[k].row, found[k].col)] = (
                    TXT, remap[found[k].number] if remap is not None else found[k].number, xf)
            elif found[k].kind == 3:
                raw = body[found[k].vstart:found[k].vstart + found[k].vlen]
                if found[k].amp:
                    tid = entity_text(raw)
                else:
                    first = p[found[k].vstart]
                    if first == 91 or first == 1:          # the escape of xlsheet.text_id
                        raw = b'' + raw
                    tid = texts.kvr(raw)                    # bytes key: no decode, no encode
                    if tid is None:
                        tid = len(texts)
                        texts.kvw(raw, tid)
                cells[(found[k].row, found[k].col)] = (TXT, tid, xf)
            elif found[k].kind == 2:
                cells[(found[k].row, found[k].col)] = (BOOL, found[k].number == 1, xf)
            else:
                cells[(found[k].row, found[k].col)] = (
                    NUM, float(body[found[k].vstart:found[k].vstart + found[k].vlen]), xf)
        return count
    finally:
        free(found)


# ---------------------------------------------------------------------------- emit -------
cdef str format_double(double v):
    # xlstyle.num_text for a float: a whole number below 1e15 as an integer, else '%.15g'
    cdef char* text
    cdef str result
    if v == floor(v) and fabs(v) < 1e15:
        return str(<long long>v)
    text = PyOS_double_to_string(v, 103, 15, 0, NULL)        # 'g'
    try:
        result = (<bytes>text).decode('ascii')
    finally:
        PyMem_Free(text)
    return result


def emit_grid(cells, list texts, col2letter, list formulas, cached_xml):
    """The <sheetData> text of a grid, the widest text per column (index = column, 0 unused)
    and the number of columns. col2letter(n) names column n; formulas are the <f> markups;
    cached_xml(payload) gives (t attribute, <v> element, width) of a formula cell."""
    cdef list keys = cells.indici()
    cdef Py_ssize_t n = len(keys), i, k, slen
    cdef long row, col, prev_row = -1, prev_col = -1, current = -1, ncols = 0
    cdef long* rows = <long*>malloc((n + 1) * sizeof(long))
    cdef long* cols = <long*>malloc((n + 1) * sizeof(long))
    cdef const char* s
    cdef bint ordered = True
    cdef list cellvals, order, out, widest, letters
    cdef int kind
    cdef str text, head
    cdef long width
    if rows == NULL or cols == NULL:
        raise MemoryError()
    try:
        cellvals = []
        for i in range(n):
            key = keys[i]
            s = PyUnicode_AsUTF8AndSize(key, &slen)
            k = 1
            row = 0
            while k < slen and 48 <= s[k] <= 57:
                row = row * 10 + (s[k] - 48)
                k += 1
            k += 1
            col = 0
            while k < slen and 48 <= s[k] <= 57:
                col = col * 10 + (s[k] - 48)
                k += 1
            rows[i] = row
            cols[i] = col
            if col > ncols:
                ncols = col
            if row < prev_row or (row == prev_row and col <= prev_col):
                ordered = False
            prev_row = row
            prev_col = col
            cellvals.append(cells.kvr(key))
        letters = [''] + [col2letter(c) for c in range(1, ncols + 1)]
        widest = [0] * (ncols + 1)
        if ordered:
            order = None
        else:
            order = [item[2] for item in sorted([(rows[x], cols[x], x) for x in range(n)])]
        out = ['<sheetData>']
        for i in range(n):
            k = i if order is None else order[i]
            row = rows[k]
            col = cols[k]
            cell = cellvals[k]
            if row != current:
                if current > 0:
                    out.append('</row>')
                out.append(f'<row r="{row}">')
                current = row
            kind = cell[0]
            head = f'<c r="{letters[col]}{row}" s="{cell[2]}"'
            width = 0
            if kind == NUM:
                value = cell[1]
                if type(value) is float:
                    if isfinite(<double>value):
                        text = format_double(<double>value)
                        out.append(f'{head}><v>{text}</v></c>')
                        width = len(text)
                    else:
                        out.append(head + '/>')
                else:
                    text = str(value)
                    out.append(f'{head}><v>{text}</v></c>')
                    width = len(text)
            elif kind == TXT:
                out.append(f'{head} t="s"><v>{cell[1]}</v></c>')
                width = len(texts[cell[1]])
            elif kind == BOOL:
                out.append(f'{head} t="b"><v>{int(cell[1])}</v></c>')
                width = 5
            elif kind == FML:
                tattr, vxml, width = cached_xml(cell[1])
                out.append(f'{head}{tattr}>{formulas[cell[1][0]]}{vxml}</c>')
            else:
                out.append(head + '/>')
            if width > widest[col]:
                widest[col] = width
        if current > 0:
            out.append('</row>')
        out.append('</sheetData>')
        return ''.join(out), widest, ncols
    finally:
        free(rows)
        free(cols)
