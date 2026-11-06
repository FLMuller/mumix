"""
xlcells -- the cells of a sheet: the grid, what cells share, and the worksheet XML both ways.

Why
    The cells are the bulk of a workbook. A sheet keeps them as one dict of small tuples, and
    what cells share (their text, their style, their formula markup) lives once per book, so
    writing and reading the XML moves tuples and never builds a node per cell.

Algorithm
    cells[row, col] = (kind, payload, xf):
        NUM    payload the number
        TXT    payload the position of the text in the book's text list
        BOOL   payload True or False
        BLANK  payload None (a styled cell with no value)
        FML    payload (position of the <f> markup, cached value, cached type '' 'str' 'b' 'e')
    and xf is the position of the cell's style in the book's style list; xf 0 is the default.
    Tables holds the three lists with a dict beside each, so every distinct text, style and
    formula is stored once, at the first write, and a save has nothing left to look up.
    Numbers written with no number format of their own get one that shows their significant
    figures (auto_numfmt); a block of numbers makes the style for each format once per call.
    Out: to_xml() lists the cells in row order and writes each as one string; the widest text of
    each column gives <cols>. In: from_xml() cuts <sheetData> out of the part, takes every cell
    with ONE regular expression and, when the expression finds fewer cells than the part holds
    (another attribute order, rich text runs), reads the whole part with ElementTree instead; the
    common cells (a number, a shared string) are stored in the loop itself and the rest through
    cell_from(). Elements around <sheetData> are checked once: the grid-lines flag is read, and
    elements xlw4 does not keep are noted. Why not a compiled loop: the tuples and dicts of
    CPython are already C, and the loops below cost about 1.5 us a cell (see the benchmarks).
    Cost: O(cells).

Use
    tables = Tables(); grid = Grid(tables)
    grid.put(row, col, value, delta)           # one cell; delta = a style dict (xlformat)
    grid.block(rows, row0, col0, delta)        # a list of rows, one cell per element
    grid.formula(row, col, '=SUM(B2:B9)', cached=None, delta=None)
    grid.read(row, col, 'value')               # or 'style' (a dict) or 'formula' (text, no '=')
    grid.restyle(row, col, changes)            # change a style, keep the value
    grid.extent()                              # (highest occupied row, highest occupied column)
    grid.needs_calc()                          # True when a formula has no cached value
    xml, cols = grid.to_xml()                  # <sheetData> and <cols>, in row order
    show_grid = grid.from_xml(data, remap, notes)   # data: the part as bytes
    remap = tables.load(tables.read_texts(data), styles)   # a file's text and style lists
    tables.texts  tables.xfs  tables.formulas  # the shared lists, as written to the file

VERSION  M01 m01.v01 (2026-11-06): first version; the grid, the tables and the sheet XML codec in
         one module, with one read route and one fallback, and no compiled twin.
"""

import re
from html import unescape

from xltext import column, parse_xml, xml_text

__all__ = ['Tables', 'Grid']

NUM, TXT, BOOL, BLANK, FML = range(5)
MAX_WIDTH, MIN_WIDTH = 80, 4
INFINITY = float('inf')
# Groups: column letters, row, style, type, <f> markup, inline string, value.
CELL = re.compile(r'<c r="([A-Z]+)(\d+)"(?: s="(\d+)")?(?: t="([A-Za-z]+)")?'
                  r'(?:/>|>(?:(<f[^>]*/>|<f[^>]*>[^<]*</f>))?(?:(<is>(?:<t[^>]*>[^<]*</t>)+</is>))?'
                  r'(?:<v>([^<]*)</v>)?</c>)')
# The same without formulas and inline strings, which most sheets lack: faster by a third.
PLAIN_CELL = re.compile(r'<c r="([A-Z]+)(\d+)"(?: s="(\d+)")?(?: t="([A-Za-z]+)")?'
                        r'(?:/>|>(?:<v>([^<]*)</v>)?</c>)')
INLINE_TEXT = re.compile(r'<t[^>]*>([^<]*)</t>')
SHARED_TEXT = re.compile(r'<si><t[^>]*>([^<]*)</t></si>')
SHEET_KNOWN = ('sheetPr', 'dimension', 'sheetViews', 'sheetFormatPr', 'cols', 'sheetData',
               'pageMargins', 'pageSetup', 'headerFooter', 'drawing', 'extLst',
               'AlternateContent', 'printOptions', 'rowBreaks', 'colBreaks',
               'sheetProtection', 'phoneticPr', 'ignoredErrors')


class Tables:
    """What the cells of a book share: texts, styles and formula markups, each stored once."""

    def __init__(me):
        me.texts, me.xfs, me.formulas = [], [{}], []
        me.index = {'texts': {}, 'xfs': {(): 0}, 'formulas': {}}
        me.number_xf = {}

    def ident(me, kind, key, item=None):
        """The position of `key` in the list `kind` ('texts', 'xfs' or 'formulas'), after adding
        `item` (the key itself when None) at the first use. A dict beside each list finds the
        position at once, so a text, a style or a formula is stored once however often it is written."""
        known, items = me.index[kind], getattr(me, kind)
        found = known.get(key)
        if found is None:
            found = known[key] = len(items)
            items.append(key if item is None else item)
        return found

    def style_id(me, delta):
        """The position of a style dict in the style list, added at the first use."""
        return me.ident('xfs', tuple(sorted(delta.items())), dict(delta))

    @staticmethod
    def read_texts(data):
        """The shared strings of a sharedStrings.xml part (bytes, or None) in file order: plain
        <t> and rich-text runs joined, phonetic hints skipped. A part made only of plain items is
        read with one expression; anything else goes through ElementTree."""
        if data is None:
            return []
        text = data.decode('utf-8')
        plain = SHARED_TEXT.findall(text)
        if len(plain) == text.count('<si>') + text.count('<si/>') and '<r>' not in text:
            return [unescape(item) for item in plain]
        return [''.join(piece.text or '' for piece in item.findall('t') + item.findall('r/t'))
                for item in parse_xml(data).iter('si')]

    def load(me, strings, styles):
        """Take the text list and style list of a file. Returns the map from a file's text
        position to ours, or None when they are the same (a text listed twice goes to the first)."""
        remap = [me.ident('texts', text) for text in strings]
        me.xfs, me.index['xfs'] = [], {}
        for style in styles or [{}]:
            me.index['xfs'].setdefault(tuple(sorted(style.items())), len(me.xfs))
            me.xfs.append(style)
        return None if remap == list(range(len(remap))) else remap

    def numbered_xf(me, delta, key, code):
        """The style of a number written with `delta` (`key` is its sorted items): the number
        format `code` is added unless the style has one. Cached per (style, code)."""
        found = me.number_xf.get((key, code))
        if found is None:
            plain = delta if not code or 'numfmt' in delta else {**delta, 'numfmt': code}
            found = me.number_xf[key, code] = me.style_id(plain)
        return found


def auto_numfmt(value):
    """A format code that shows a number's significant figures ('' = General): whole numbers under
    1e7 and anything from 100 to 1e5 as '0', 0.01 to 100 with up to four decimals (fewer as the
    size grows), else '0.##E+00'. Zero and non-finite numbers keep General. A chain of comparisons
    is faster than a logarithm, and this runs once for every number written."""
    magnitude = abs(value)
    if magnitude != magnitude or magnitude == INFINITY:
        return ''
    if magnitude >= 1e5:
        return '0' if magnitude < 1e7 and magnitude % 1 == 0 else '0.##E+00'
    if magnitude >= 100:
        return '0'
    if magnitude >= 1:
        return '0' if magnitude % 1 == 0 else '0.#' if magnitude >= 10 else '0.##'
    if magnitude >= 0.01:
        return '0.###' if magnitude >= 0.1 else '0.####'
    return '' if magnitude == 0 else '0.##E+00'


def formula_markup(attrib, text):
    """The <f> element as Excel writes it: attributes in order, the text escaped, and
    self-closing when it has no text (the followers of a shared formula)."""
    attrs = ''.join(f' {name}="{xml_text(value)}"' for name, value in attrib.items())
    return f'<f{attrs}>{xml_text(text)}</f>' if text else f'<f{attrs}/>'


class Grid:
    """The cells of one sheet, and the sheet's worksheet XML."""

    def __init__(me, tables):
        me.tables = tables
        me.cells = {}

    def cell_of(me, value, delta, key):
        """The cell tuple of a value written with a style (`key` is the sorted items of delta)."""
        tables = me.tables
        kind = type(value)
        if kind is float or kind is int:
            return (NUM, value, tables.numbered_xf(delta, key, auto_numfmt(value)))
        if value is None or value == '':
            return (BLANK, None, tables.style_id(delta))
        if kind is str:
            return (TXT, tables.ident('texts', value), tables.style_id(delta))
        if kind is bool:
            return (BOOL, value, tables.style_id(delta))
        if hasattr(value, 'item'):
            return me.cell_of(value.item(), delta, key)
        return (TXT, tables.ident('texts', str(value)), tables.style_id(delta))

    def put(me, row, col, value, delta):
        """Write one cell."""
        me.cells[row, col] = me.cell_of(value, delta, tuple(sorted(delta.items())) if delta else ())

    def block(me, rows, row0, col0, delta):
        """Write a list of rows, one cell per element, from (row0, col0). The style of each number
        format is found once per call, so a number costs one comparison chain and one dict lookup."""
        key = tuple(sorted(delta.items()))
        cells, cell_of, numbered_xf, by_code = me.cells, me.cell_of, me.tables.numbered_xf, {}
        for i, values in enumerate(rows, row0):
            for j, value in enumerate(values, col0):
                kind = type(value)
                if kind is float or kind is int:
                    code = auto_numfmt(value)
                    xf = by_code.get(code)
                    if xf is None:
                        xf = by_code[code] = numbered_xf(delta, key, code)
                    cells[i, j] = (NUM, value, xf)
                else:
                    cells[i, j] = cell_of(value, delta, key)

    def formula(me, row, col, formula, cached=None, delta=None):
        """Write a formula cell; `cached` is shown until Excel calculates (None: the
        workbook is calculated on load)."""
        text = formula[1:] if formula[:1] == '=' else formula
        ctype = 'b' if isinstance(cached, bool) else 'str' if isinstance(cached, str) else ''
        fid = me.tables.ident('formulas', formula_markup({}, text))
        me.cells[row, col] = (FML, (fid, cached, ctype), me.tables.style_id(delta or {}))

    def restyle(me, row, col, changes):
        """Add `changes` to the style of a cell, keeping its value; a missing cell becomes a
        blank styled cell."""
        tables = me.tables
        kind, payload, xf = me.cells.get((row, col), (BLANK, None, 0))
        me.cells[row, col] = (kind, payload, tables.style_id({**tables.xfs[xf], **changes}))

    def read(me, row, col, what='value'):
        """One thing about a cell: its 'value' (text as text, a formula's cached value; None when
        blank or absent), its 'style' (a dict, empty for the default) or its 'formula' text (no
        '='; None when the cell is not a formula)."""
        kind, payload, xf = me.cells.get((row, col), (BLANK, None, 0))
        if what == 'style':
            return dict(me.tables.xfs[xf])
        if what == 'formula':
            if kind != FML:
                return None
            markup = me.tables.formulas[payload[0]]
            return unescape(markup[markup.find('>') + 1:markup.rfind('</f>')]) \
                if markup.endswith('</f>') else ''
        return me.tables.texts[payload] if kind == TXT else payload[1] if kind == FML else payload

    def extent(me):
        """(the highest occupied row, the highest occupied column); (0, 0) when the sheet is empty."""
        return (max((row for row, _ in me.cells), default=0),
                max((col for _, col in me.cells), default=0))

    def needs_calc(me):
        """True when a formula has no cached value, so Excel must calculate on opening the file."""
        return any(cell[0] == FML and cell[1][1] is None for cell in me.cells.values())

    # ------------------------------------------------------------------------- out ----
    def formula_xml(me, ref, xf, payload):
        """(xml, width) of a formula cell: its <f> markup and, when it has one, its cached value."""
        cached, ctype = payload[1], payload[2]
        shown = '' if cached is None or cached != cached or cached in (INFINITY, -INFINITY)             else xml_text(int(cached) if ctype == 'b' else cached)
        attr = f' t="{ctype}"' if ctype else ''
        value = f'<v>{shown}</v>' if shown != '' else ''
        return f'<c r="{ref}" s="{xf}"{attr}>{me.tables.formulas[payload[0]]}{value}</c>', len(shown)

    @staticmethod
    def cols_xml(widest):
        """<cols> from {column: widest text}: the width is the text plus 2, between 4 and 80."""
        cols = ''.join(f'<col min="{col}" max="{col}" '
                       f'width="{min(MAX_WIDTH, max(MIN_WIDTH, width + 2))}" customWidth="1"/>'
                       for col, width in sorted(widest.items()) if width > 0)
        return f'<cols>{cols}</cols>' if cols else ''

    def to_xml(me):
        """(<sheetData> text, <cols> text) of the grid, in row order; the widest text of a column
        sets its width. The cell strings are made in the loop, with the column letters kept in a
        dict, because a method call and a tuple for each cell cost more than the string."""
        texts, letters = me.tables.texts, {}
        parts, widest, current = ['<sheetData>'], {}, 0
        append = parts.append
        for (row, col), (kind, payload, xf) in sorted(me.cells.items()):
            if row != current:
                append(f'</row><row r="{row}">' if current else f'<row r="{row}">')
                current = row
            ref = f'{letters.get(col) or letters.setdefault(col, column(col))}{row}'
            width = 0
            if kind == NUM:
                text = repr(payload)
                if text[-1] in 'nf':
                    append(f'<c r="{ref}" s="{xf}"/>')
                    continue
                text = text[:-2] if text[-2:] == '.0' else text
                append(f'<c r="{ref}" s="{xf}"><v>{text}</v></c>')
                width = len(text)
            elif kind == TXT:
                append(f'<c r="{ref}" s="{xf}" t="s"><v>{payload}</v></c>')
                width = len(texts[payload])
            elif kind == BOOL:
                append(f'<c r="{ref}" s="{xf}" t="b"><v>{int(payload)}</v></c>')
                width = 5
            elif kind == FML:
                xml, width = me.formula_xml(ref, xf, payload)
                append(xml)
            else:
                append(f'<c r="{ref}" s="{xf}"/>')
            if width > widest.get(col, 0):
                widest[col] = width
        append('</row></sheetData>' if current else '</sheetData>')
        return ''.join(parts), me.cols_xml(widest)

    # -------------------------------------------------------------------------- in ----
    def cell_from(me, kind, raw, markup, inline, xf, remap):
        """The cell tuple of the pieces of a cell's XML: type attribute, <v> text (decoded),
        <f> markup, inline text and style. None for an unstyled cell with no value."""
        tables = me.tables
        xf = xf if xf < len(tables.xfs) else 0
        if markup:
            ctype = kind if kind in ('str', 'e', 'b') else ''
            cached = None if not raw else raw in ('1', 'true') if ctype == 'b' else \
                raw if ctype else float(raw)
            return (FML, (tables.ident('formulas', markup), cached, ctype), xf)
        if kind == 'inlineStr':
            return (TXT, tables.ident('texts', inline or ''), xf)
        if not raw:
            return (BLANK, None, xf) if tables.xfs[xf] else None
        if kind == 's':
            return (TXT, remap[int(raw)] if remap else int(raw), xf)
        if kind == 'b':
            return (BOOL, raw in ('1', 'true'), xf)
        if kind in ('str', 'e'):
            return (TXT, tables.ident('texts', raw), xf)
        return (NUM, float(raw), xf)

    def scan_general(me, body, remap):
        """Read a body that has formulas or inline strings: every cell goes through cell_from().
        Returns the number of cells the part holds that the expression did not match."""
        found, columns = CELL.findall(body), {}
        for letters, digits, style, kind, markup, inline, raw in found:
            words = ''.join(unescape(piece) for piece in INLINE_TEXT.findall(inline)) if inline else ''
            cell = me.cell_from(kind, unescape(raw) if '&' in raw else raw, markup, words,
                                int(style or 0), remap)
            if cell is not None:
                col = columns.get(letters) or columns.setdefault(letters, column(letters))
                me.cells[int(digits), col] = cell
        return body.count('<c ') - len(found)

    def scan_regex(me, body, remap):
        """Read the cells of a <sheetData> body (text) with one expression: the plain one when the
        body has no formula and no inline string, else the general one. Returns the number of
        cells the part holds that the expression did not match. A number and a shared string,
        which are nearly every cell of a plain body, are stored in the loop itself; the rest go
        through cell_from()."""
        if '<f' in body or '<is>' in body:
            return me.scan_general(body, remap)
        found = PLAIN_CELL.findall(body)
        cells, columns, known = me.cells, {}, len(me.tables.xfs)
        for letters, digits, style, kind, raw in found:
            col = columns.get(letters) or columns.setdefault(letters, column(letters))
            xf = int(style) if style else 0
            if raw and xf < known and kind in ('', 's'):
                cells[int(digits), col] = (NUM, float(raw), xf) if not kind else                     (TXT, remap[int(raw)] if remap else int(raw), xf)
                continue
            cell = me.cell_from(kind, unescape(raw) if '&' in raw else raw, '', '', xf, remap)
            if cell is not None:
                cells[int(digits), col] = cell
        return body.count('<c ') - len(found)

    def scan_tree(me, root, remap):
        """Read the cells of a parsed worksheet (the general route)."""
        for element in root.iter('c'):
            letters, digits = re.match(r'([A-Z]+)(\d+)', element.get('r')).groups()
            formula, value = element.find('f'), element.find('v')
            markup = formula_markup(formula.attrib, formula.text) if formula is not None else ''
            inline = ''.join(piece.text or '' for piece in element.iter('t'))
            cell = me.cell_from(element.get('t'), value.text if value is not None else None,
                                markup, inline, int(element.get('s', 0)), remap)
            if cell is not None:
                me.cells[int(digits), column(letters)] = cell

    def from_xml(me, data, remap, notes):
        """Read a worksheet part (bytes) into the grid; returns the grid-lines flag. Elements
        the grid does not keep are added to the dict `notes`. `remap` maps the file's text
        positions to ours (None: the same)."""
        start = data.find(b'<sheetData')
        finish = data.rfind(b'</sheetData>')
        if start >= 0 and finish < 0:                       # <sheetData/>: no body
            finish = start + data[start:].find(b'>')
            body = ''
            around = data[:start] + b'<sheetData/>' + data[finish + 1:]
        elif start >= 0:
            body = data[data.find(b'>', start) + 1:finish].decode('utf-8')
            around = data[:start] + b'<sheetData/>' + data[finish + 12:]
        else:
            body, around = '', data
        root = parse_xml(around)
        for child in root:
            if child.tag not in SHEET_KNOWN:
                notes[f'worksheet element {child.tag} was not read'] = True
        if start < 0 or me.scan_regex(body, remap):
            me.cells.clear()
            me.scan_tree(parse_xml(data), remap)
        return not any(view.get('showGridLines') in ('0', 'false')
                       for view in root.iter('sheetView'))
