"""
xlsheet -- the worksheet of xlw: the cell grid, the book's text and style tables, and the
worksheet XML codec (grid <-> XML).

Why
    The cells of a sheet are the bulk of a workbook and were the slow part of xlw: a tkv
    node with leaves per cell, tens of thousands of them. Here a sheet's cells are ONE kv
    holding a small tuple per cell, and what a cell shares with other cells (its text, its
    style) lives once in the book. Reading and writing the XML then moves tuples, not nodes.

Algorithm
    The grid. sheet.cells is a kv (leaf 'cells' of the sheet node); the cell at row r, column
    c is cells[r, c] = (kind, payload, xf), a tuple:
        kind NUM   payload the number (a float, or an int when it was one)
        kind TXT   payload the index of the text in the book's text table
        kind BOOL  payload True or False
        kind BLANK payload None (a styled cell with no value)
        kind FML   payload (formula id, cached value, cached type): a formula cell; the id is
                   the position of its <f> markup in the book's formula table, the cached
                   value is what the file last calculated (None if nothing), the type is
                   '' (a number), 'str', 'b' or 'e'
    and xf is the index of the cell's style in the book's style table.
    The book tables (class Tables, leaf 'tables' of the book's priv): texts is a kv whose
    keys are the distinct texts in order of first use and whose values are their positions,
    so texts.at(n) is text n, and the order IS the order of sharedStrings.xml. xfs is a list
    of style deltas (the properties that differ from DEFAULTS), position = the s attribute of
    a cell; xf 0 is the default style. A text that starts with "[" or a control character is
    stored behind a control character (kv reserves "["). Each distinct text and style is
    stored once, at the first write, so a save has nothing left to look up. The formula table
    (formulas) is a kv of the distinct <f ...>...</f> markups, kept as written (shared and
    array formulas included, so they round-trip untouched).
    The XML. Going out, sheet_to_xml lists the grid in row order and writes each cell as one
    string. Coming in, xml_to_sheet cuts the part into head, <sheetData> body and tail; the
    head and tail go through ElementTree for the grid-lines flag and for elements we do not
    read. The body is cut by ONE regular-expression split that doubles as the index of the
    part: a plain cell (number, shared string, boolean, blank) needs the short expression;
    formulas and simple inline strings the wider one; a cell of unusual form (another
    attribute order, rich text runs) is parsed alone as a fragment with ElementTree; a part
    without a plain <sheetData> is read whole by ElementTree. All fragments are parsed before
    the first cell is written. The shared-string indices of the file are kept as they are
    (they are the positions of the text table), duplicates in a file are mapped to the first.
    The loops that touch every cell (write a block, scan the body, list the grid) exist twice:
    in Cython (xlsheetfun.pyx, FUN) and here in Python, which is the reference and the
    fallback when the extension cannot be built; the tests hold the two to the same cells and
    the same bytes. Set xlsheet.FUN = None to run the Python ones.
    Cost: O(cells); the grid costs about 0.4 us a cell to write.

Use
    cells = sheet.kvr('cells'); tables = tables_of(sheet)
    put_cell(sheet, row, col, value, delta)        # one cell; delta = style properties
    cell_value(sheet, row, col)                    # the value (text as text); None if blank
    cell_style(sheet, row, col)                    # the style delta (a dict)
    cell_list(sheet)                               # [(row, col, (kind, payload, xf))] sorted
    xml, cols, ncols = sheet_to_xml(sheet, texts)  # <sheetData>, <cols>, widest column
    grid = xml_to_sheet(data, sheet, report)       # data: the part as bytes; returns showGrid
    new_tables(), fill_tables(tables, strings, deltas)   # a book's tables, or from a file
    text_id(tables, text), text_at(tables, n), text_list(tables), style_id(tables, delta)
    put_formula(sheet, row, col, 'SUM(B2:B9)', cached=None, delta=None)   # a formula cell
    cell_formula(sheet, row, col)                  # its formula text, no leading '='; or None

Versions
    M02  m02.v03  2026-11-01  formula cells: the formula is read and written (kind FML).
         m02.v02  2026-10-31  the hot loops in Cython (xlsheetfun), the Python ones kept.
         m02.v01  2026-10-31  the grid and the book tables; the codec moves tuples. Rebuilt
                              from M01, which wrote and read tkv cell nodes (history 1c46628).
    M01  m01.v02  2026-10-31  the scan is a re.split index; formula cells and simple inline
                              strings in the expression; unusual cells as fragments.
"""

import io
import math
import re
import xml.etree.ElementTree as ET
from operator import itemgetter

from use import load
from xlparts import col2letter
from xlstore import KV
from xlstyle import auto_numfmt, num_text, style_key, xml_escape

try:
    load(asmodule=['xlsheetfun'])             # the Cython loops; None runs the Python ones
    FUN = xlsheetfun
except Exception:
    FUN = None

__all__ = ['FUN', 'NUM', 'TXT', 'BOOL', 'BLANK', 'FML', 'Tables', 'new_tables',
           'formula_id', 'formula_at', 'formula_list', 'put_formula', 'cell_formula',
           'formula_markup', 'cached_xml', 'fill_tables', 'tables_of',
           'text_id', 'text_at', 'text_list', 'style_id', 'put_cell', 'cell_value',
           'cell_style', 'cell_list', 'sheet_to_xml', 'xml_to_sheet',
           'read_with_elementtree', 'parse_fragments', 'SHEET_KNOWN']

NUM = 0
TXT = 1
BOOL = 2
BLANK = 3
FML = 4
MAX_COLUMN_WIDTH = 80
MIN_COLUMN_WIDTH = 4
NS_MAIN = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
# Top-level worksheet elements that are read, or that carry nothing the tree holds.
SHEET_KNOWN = ('sheetPr', 'dimension', 'sheetViews', 'sheetFormatPr', 'cols', 'sheetData',
               'pageMargins', 'pageSetup', 'headerFooter', 'drawing', 'extLst',
               'AlternateContent', 'printOptions', 'rowBreaks', 'colBreaks',
               'sheetProtection', 'phoneticPr', 'ignoredErrors')
# Groups: 1 column letters, 2 row, 3 style, 4 type, 5 formula, 6 inline string, 7 value.
CELL = re.compile(rb'<c r="([A-Z]+)(\d+)"(?: s="(\d+)")?(?: t="([A-Za-z]+)")?'
                  rb'(?:/>|>(?:(<f[^>]*/>|<f[^>]*>[^<]*</f>))?'
                  rb'(?:(<is>(?:<t[^>]*>[^<]*</t>)+</is>))?'
                  rb'(?:<v>([^<]*)</v>)?</c>)')
# The plain form (no formula, no inline string): used when the body has neither.
CELL_FAST = re.compile(rb'<c r="([A-Z]+)(\d+)"(?: s="(\d+)")?(?: t="([A-Za-z]+)")?'
                       rb'(?:/>|>(?:<v>([^<]*)</v>)?</c>)')
GROUPS = 7                       # capture groups of CELL; split returns GROUPS + 1 per cell
ODD_CELL = re.compile(rb'<c\b[^>]*?/>|<c\b[^>]*>.*?</c>', re.DOTALL)
INLINE_TEXT = re.compile(rb'<t[^>]*>([^<]*)</t>')
CELL_START = b'<c '
GRID_OFF = ('0', 'false')
ESCAPED = ('[', '\x01')          # a text starting with one of these is stored behind \x01


def local(tag):
    return tag.rsplit('}', 1)[-1]


# ------------------------------------------------------------------ the book tables -----
class Tables:
    """What cells share: the text table (a kv, text -> position) and the style table
    (a list of deltas, position = xf; xf_index is its kv, built on the first lookup)."""
    __slots__ = ('texts', 'xfs', 'xf_index', 'xf_cache', 'formulas')


def new_tables():
    tables = Tables()
    tables.texts = KV()
    tables.xfs = [{}]
    tables.xf_index = None
    tables.xf_cache = {}
    tables.formulas = KV()
    return tables


def tables_of(sheet):
    """The tables of the book a sheet belongs to."""
    return sheet.parent().kvr('priv').kvr('tables')


def fill_tables(tables, strings, deltas):
    """Load the tables from a file: the shared strings in file order and the cell formats.
    Returns the map from a file's text index to ours, or None when they are the same (a
    text listed twice in the file is mapped to the first)."""
    texts = tables.texts
    remap = []
    same = True
    for number, text in enumerate(strings):
        key = '\x01' + text if text[:1] in ESCAPED else text
        found = texts.kvr(key)
        if found is None:
            found = len(texts)
            texts.kvw(key, found)
        if found != number:
            same = False
        remap.append(found)
    tables.xfs = list(deltas) if deltas else [{}]
    tables.xf_index = None
    tables.xf_cache = {}
    return None if same else remap


def text_id(tables, text):
    """The position of a text in the book's text table, added at the first use."""
    key = '\x01' + text if text[:1] in ESCAPED else text
    found = tables.texts.kvr(key)
    if found is None:
        found = len(tables.texts)
        tables.texts.kvw(key, found)
    return found


def text_at(tables, number):
    """The text at a position of the text table."""
    key = tables.texts.at(number)
    return key[1:] if key[:1] == '\x01' else key


def text_list(tables):
    """All texts in order (the sharedStrings.xml order)."""
    return [key[1:] if key[:1] == '\x01' else key for key in tables.texts.keys()]


def formula_id(tables, markup):
    """The position of a formula markup in the book's formula table, added at the first use."""
    found = tables.formulas.kvr(markup)
    if found is None:
        found = len(tables.formulas)
        tables.formulas.kvw(markup, found)
    return found


def formula_at(tables, number):
    """The markup at a position of the formula table."""
    return tables.formulas.at(number)


def formula_list(tables):
    """All formula markups in order."""
    return tables.formulas.keys()


def formula_markup(attrib, text):
    """The <f> element as Excel writes it: attributes in order, the text with & < > escaped,
    self-closing when it has no text (a shared formula's followers)."""
    attrs = ''.join(' %s="%s"' % (name, value.replace('&', '&amp;').replace('<', '&lt;')
                                  .replace('"', '&quot;')) for name, value in attrib.items())
    if not text:
        return f'<f{attrs}/>'
    return f'<f{attrs}>' + text.replace('&', '&amp;').replace('<', '&lt;').replace(
        '>', '&gt;') + '</f>'


def cached_xml(formula):
    """(t attribute, <v> element, width) of a formula cell's payload (id, cached, type)."""
    cached = formula[1]
    ctype = formula[2]
    tattr = f' t="{ctype}"' if ctype else ''
    if cached is None:
        return tattr, '', 0
    if ctype == 'b':
        return tattr, f'<v>{int(cached)}</v>', 5
    if isinstance(cached, str):
        return tattr, f'<v>{xml_escape(cached)}</v>', len(cached)
    if isinstance(cached, float) and not math.isfinite(cached):
        return tattr, '', 0
    text = num_text(cached)
    return tattr, f'<v>{text}</v>', len(text)


def style_id(tables, delta):
    """The xf index of a style delta, added to the style table at the first use."""
    if not delta:
        return 0
    key = tuple(delta.items())
    try:
        found = tables.xf_cache.get(key)
    except TypeError:                         # an unhashable setting: no caching
        key = None
        found = None
    if found is not None:
        return found
    if tables.xf_index is None:
        tables.xf_index = KV()
        for number, known in enumerate(tables.xfs):
            name = style_key(known)
            if tables.xf_index.kvr(name) is None:
                tables.xf_index.kvw(name, number)
    name = style_key(delta)
    found = tables.xf_index.kvr(name)
    if found is None:
        found = len(tables.xfs)
        tables.xfs.append(dict(delta))
        tables.xf_index.kvw(name, found)
    if key is not None:
        tables.xf_cache[key] = found
    return found


# ------------------------------------------------------------------------- the grid -----
def make_cell(tables, value, delta):
    """The grid tuple of a value written with a style delta. Numbers without a number
    format of their own get one that shows their significant figures."""
    if type(value).__module__ == 'numpy':
        value = value.item()
    if value is None or value == '':
        return (BLANK, None, style_id(tables, delta))
    if isinstance(value, bool):
        return (BOOL, value, style_id(tables, delta))
    if isinstance(value, (int, float)):
        if 'numfmt' not in delta:
            code = auto_numfmt(float(value))
            if code:
                delta = dict(delta)
                delta['numfmt'] = code
        return (NUM, value, style_id(tables, delta))
    return (TXT, text_id(tables, str(value)), style_id(tables, delta))


def put_cell(sheet, row, col, value, delta):
    """Write one cell of a sheet."""
    sheet.kvr('cells')[row, col] = make_cell(tables_of(sheet), value, delta)


def put_formula(sheet, row, col, formula, cached=None, delta=None):
    """Write a formula cell. `formula` is the text with or without its leading '='; `cached`
    is the value to show until Excel calculates (None: the workbook is calculated on load)."""
    tables = tables_of(sheet)
    text = formula[1:] if formula[:1] == '=' else formula
    if isinstance(cached, bool):
        ctype = 'b'
    elif isinstance(cached, str):
        ctype = 'str'
    else:
        ctype = ''
    sheet.kvr('cells')[row, col] = (FML, (formula_id(tables, formula_markup({}, text)), cached,
                                         ctype), style_id(tables, delta or {}))


def cell_formula(sheet, row, col):
    """The formula text of a cell (no leading '='; a shared formula's follower gives its
    markup attributes only), or None when the cell is not a formula."""
    cell = sheet.kvr('cells').kvr((row, col))
    if cell is None or cell[0] != FML:
        return None
    markup = formula_at(tables_of(sheet), cell[1][0])
    inner = markup[markup.find('>') + 1:markup.rfind('</f>')] if markup.endswith('</f>') else ''
    return inner.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')


def cell_value(sheet, row, col):
    """The value of a cell (text as text; a formula's cached value); None for a blank or
    absent cell."""
    cell = sheet.kvr('cells').kvr((row, col))
    if cell is None or cell[0] == BLANK:
        return None
    if cell[0] == TXT:
        return text_at(tables_of(sheet), cell[1])
    if cell[0] == FML:
        return cell[1][1]
    return cell[1]


def cell_style(sheet, row, col):
    """The style delta of a cell as a dict (empty for the default style or no cell)."""
    cell = sheet.kvr('cells').kvr((row, col))
    return {} if cell is None else dict(tables_of(sheet).xfs[cell[2]])


def cell_list(sheet):
    """[(row, col, (kind, payload, xf))] of a sheet in row-major order. A grid written row
    by row is already in order, and the sort of an ordered list is one pass."""
    cells = sheet.kvr('cells')
    found = []
    for key in cells.indici():
        parts = key[1:-1].split()
        found.append((int(parts[0]), int(parts[1]), cells.kvr(key)))
    found.sort(key=itemgetter(0, 1))
    return found


# ---------------------------------------------------------------------------- out -------
def sheet_to_xml(sheet, texts=None, formulas=None):
    """The <sheetData> text and <cols> text of one sheet, and its number of columns.
    `texts` is text_list(tables) and `formulas` formula_list(tables), shared by the sheets of
    a book (the texts also give the column widths)."""
    if texts is None:
        texts = text_list(tables_of(sheet))
    if formulas is None:
        formulas = formula_list(tables_of(sheet))
    if FUN is not None:
        xml, widest, ncols = FUN.emit_grid(sheet.kvr('cells'), texts, col2letter, formulas,
                                              cached_xml)
        return xml, columns_xml(widest, ncols), ncols
    found = cell_list(sheet)
    ncols = max((item[1] for item in found), default=0)
    letters = [''] + [col2letter(n) for n in range(1, ncols + 1)]
    widest = [0] * (ncols + 1)
    fragments = ['<sheetData>']
    append = fragments.append
    current = -1
    for row, col, cell in found:
        if row != current:
            if current > 0:
                append('</row>')
            append(f'<row r="{row}">')
            current = row
        kind = cell[0]
        head = f'<c r="{letters[col]}{row}" s="{cell[2]}"'
        width = 0
        if kind == NUM:
            value = cell[1]
            if math.isfinite(value):
                text = num_text(value)
                append(f'{head}><v>{text}</v></c>')
                width = len(text)
            else:
                append(head + '/>')
        elif kind == TXT:
            append(f'{head} t="s"><v>{cell[1]}</v></c>')
            width = len(texts[cell[1]])
        elif kind == BOOL:
            append(f'{head} t="b"><v>{int(cell[1])}</v></c>')
            width = 5
        elif kind == FML:
            tattr, vxml, width = cached_xml(cell[1])
            append(f'{head}{tattr}>{formulas[cell[1][0]]}{vxml}</c>')
        else:
            append(head + '/>')
        if width > widest[col]:
            widest[col] = width
    if current > 0:
        append('</row>')
    append('</sheetData>')
    return ''.join(fragments), columns_xml(widest, ncols), ncols


def columns_xml(widest, ncols):
    """The <cols> text from the widest text of each column (index = column)."""
    columns = ''
    for col in range(1, ncols + 1):
        if widest[col] > 0:
            size = min(MAX_COLUMN_WIDTH, max(MIN_COLUMN_WIDTH, widest[col] + 2))
            columns += (f'<col min="{col}" max="{col}" width="{size}" '
                        'customWidth="1"/>')
    return '<cols>' + columns + '</cols>' if columns else ''


# ----------------------------------------------------------------------------- in -------
def text_value(raw):
    """The text of a <v> or <t> element given as bytes, with entities and character
    references decoded (the rare case goes through ElementTree, so it is exactly as
    before)."""
    if b'&' in raw:
        return ET.fromstring(b'<v>' + raw + b'</v>').text or ''
    return raw.decode('utf-8')


def letters2col(letters):
    """Column number of bytes such as b'AB' (bijective base 26)."""
    col = 0
    for char in letters:
        col = col * 26 + char - 64
    return col


def head_and_tail(head, tail, report):
    """Check the elements around <sheetData> as the general path does: report those not
    read; return the grid-lines flag."""
    root = ET.fromstring(head + b'<sheetData/>' + tail)
    for child in root:
        name = local(child.tag)
        if name not in SHEET_KNOWN:
            report.add(f'worksheet element {name} was not read')
    grid = True
    for element in root.iter():
        if local(element.tag) == 'sheetView' and element.get('showGridLines') in GRID_OFF:
            grid = False
    return grid


def store_cell(tables, cells, remap, row, col, kind, raw, style, inline, decoded=False):
    """Write one cell given as the pieces of its XML (the slow paths; the hot loops of
    xml_to_sheet do the same inline). kind is the t attribute (bytes or None), raw the <v>
    text (bytes or None), inline the text of an inline string (str or None). decoded: the
    <v> text has its entities decoded already (it came from ElementTree)."""
    nxf = len(tables.xfs)
    xf = style if style < nxf else 0
    if inline:
        cells[row, col] = (TXT, text_id(tables, inline), xf)
    elif not raw:
        if tables.xfs[xf]:
            cells[row, col] = (BLANK, None, xf)
    elif not kind:
        cells[row, col] = (NUM, float(raw), xf)
    elif kind == b's':
        number = int(raw)
        cells[row, col] = (TXT, remap[number] if remap else number, xf)
    elif kind == b'b':
        cells[row, col] = (BOOL, raw in (b'1', b'true'), xf)
    elif kind == b'str' or kind == b'e':
        cells[row, col] = (TXT, text_id(tables, raw.decode('utf-8') if decoded
                                        else text_value(raw)), xf)
    else:
        cells[row, col] = (NUM, float(raw), xf)


def store_formula(tables, cells, row, col, kind, markup, raw, style, decoded=False):
    """Write a formula cell given as the pieces of its XML: the t attribute (bytes or None),
    the <f> markup (bytes) and the cached <v> text (bytes or None). decoded: the <v> text has
    its entities decoded already (it came from ElementTree)."""
    xf = style if style < len(tables.xfs) else 0
    fid = formula_id(tables, markup.decode('utf-8'))
    ctype = ''
    cached = None
    if kind == b'str' or kind == b'e':
        ctype = kind.decode()
        if raw:
            cached = raw.decode('utf-8') if decoded else text_value(raw)
    elif raw:
        if kind == b'b':
            ctype = 'b'
            cached = raw in (b'1', b'true')
        else:
            cached = float(raw)
    cells[row, col] = (FML, (fid, cached, ctype), xf)


def element_cell(element, tables, cells, remap):
    """Write the cell of a parsed <c> element, by the rules of the general path."""
    reference = re.match(r'([A-Z]+)(\d+)', element.get('r'))
    col = letters2col(reference.group(1).encode())
    row = int(reference.group(2))
    kind = element.get('t')
    raw = element.find(NS_MAIN + 'v')
    formula = element.find(NS_MAIN + 'f')
    if formula is not None:
        cached = None if raw is None or raw.text is None else raw.text.encode('utf-8')
        store_formula(tables, cells, row, col, None if kind is None else kind.encode(),
                      formula_markup(formula.attrib, formula.text).encode('utf-8'), cached,
                      int(element.get('s', 0)), True)
        return
    inline = None
    if kind == 'inlineStr':
        inline = ''.join(t.text or '' for t in element.iter(NS_MAIN + 't'))
    text = None if raw is None or raw.text is None else raw.text
    store_cell(tables, cells, remap, row, col, None if kind is None else kind.encode(),
               None if text is None else text.encode('utf-8'),
               int(element.get('s', 0)), inline, True)


def parse_fragments(gap):
    """The cells of unusual form inside a gap between two matches, each parsed alone as an
    element. Raises ET.ParseError for a fragment that is not well-formed XML."""
    elements = []
    for fragment in ODD_CELL.findall(gap):
        root = ET.fromstring(b'<root xmlns="' + NS_MAIN[1:-1].encode() + b'">' + fragment
                             + b'</root>')
        elements.append(root[0])
    return elements


def inline_value(markup):
    """The text of a simple <is><t>..</t></is> given as bytes."""
    return ''.join(text_value(piece) for piece in INLINE_TEXT.findall(markup))


def scan_plain(found, cells, tables, remap):
    """Write the cells of CELL_FAST.findall: numbers, shared strings, booleans, text and
    blanks with their styles, the tables most worksheets are."""
    columns = {}
    xfs = tables.xfs
    nxf = len(xfs)
    for letters, digits, style, kind, raw in found:
        col = columns.get(letters)
        if col is None:
            col = columns[letters] = letters2col(letters)
        xf = int(style) if style else 0
        if xf >= nxf:
            xf = 0
        if not raw:
            if xfs[xf]:
                cells[int(digits), col] = (BLANK, None, xf)
        elif not kind:
            cells[int(digits), col] = (NUM, float(raw), xf)
        elif kind == b's':
            number = int(raw)
            cells[int(digits), col] = (TXT, remap[number] if remap else number, xf)
        elif kind == b'b':
            cells[int(digits), col] = (BOOL, raw in (b'1', b'true'), xf)
        elif kind == b'str' or kind == b'e':
            cells[int(digits), col] = (TXT, text_id(tables, text_value(raw)), xf)
        else:
            cells[int(digits), col] = (NUM, float(raw), xf)


def xml_to_sheet(data, sheet, report, remap=None):
    """Read a worksheet part (bytes) into the sheet's grid; returns the grid-lines flag.
    A body with no formula and no inline string is read with the plain expression; otherwise
    the body is cut by CELL.split and unusual cells are read one by one as fragments; a part
    without a plain <sheetData> is read whole by the general ElementTree path. `remap` maps
    the shared-string indices of the file to the text table (None: the same)."""
    start = data.find(b'<sheetData')
    if start < 0:
        return read_with_elementtree(data, sheet, report, remap)
    close = data.find(b'>', start)
    if data[close - 1:close + 1] == b'/>':
        body = b''
        tail = data[close + 1:]
    else:
        end = data.find(b'</sheetData>', close)
        if end < 0:
            return read_with_elementtree(data, sheet, report, remap)
        body = data[close + 1:end]
        tail = data[end + len(b'</sheetData>'):]
    tables = tables_of(sheet)
    cells = sheet.kvr('cells')
    if b'<f' not in body:
        if FUN is not None and FUN.scan_cells(
                body, cells, tables.xfs, remap, tables.texts,
                lambda raw: text_id(tables, text_value(raw))) >= 0:
            return head_and_tail(data[:start], tail, report)
        found = CELL_FAST.findall(body) if b'<is>' not in body else ()
        if len(found) == body.count(CELL_START):
            grid = head_and_tail(data[:start], tail, report)
            scan_plain(found, cells, tables, remap)
            return grid
    parts = CELL.split(body)
    stride = GROUPS + 1
    count = len(parts) // stride
    gaps = parts[0::stride]
    odd = {}
    for number, gap in enumerate(gaps):
        if CELL_START in gap:
            try:
                elements = parse_fragments(gap)
            except ET.ParseError:             # the general path raises the error itself
                return read_with_elementtree(data, sheet, report, remap)
            if len(elements) != gap.count(CELL_START):
                return read_with_elementtree(data, sheet, report, remap)
            odd[number] = elements
    if len(odd) == 0 and body.count(CELL_START) != count:
        return read_with_elementtree(data, sheet, report, remap)
    grid = head_and_tail(data[:start], tail, report)
    columns = {}
    number = 0
    fields = zip(parts[1::stride], parts[2::stride], parts[3::stride], parts[4::stride],
                 parts[5::stride], parts[6::stride], parts[7::stride])
    for letters, digits, style, kind, formula, inline, raw in fields:
        if odd and number in odd:
            for element in odd[number]:
                element_cell(element, tables, cells, remap)
        number += 1
        col = columns.get(letters)
        if col is None:
            col = columns[letters] = letters2col(letters)
        if formula:
            store_formula(tables, cells, int(digits), col, kind, formula, raw,
                          int(style) if style else 0)
        else:
            store_cell(tables, cells, remap, int(digits), col, kind, raw,
                       int(style) if style else 0,
                       (inline_value(inline) if inline else '') if kind == b'inlineStr'
                       else None)
    if odd and count in odd:
        for element in odd[count]:
            element_cell(element, tables, cells, remap)
    return grid


def read_with_elementtree(data, sheet, report, remap=None):
    """The general path: stream the part through ElementTree, cell by cell as each closes;
    anything not read is reported. Returns the grid-lines flag."""
    tables = tables_of(sheet)
    cells = sheet.kvr('cells')
    grid = True
    depth = 0
    for event, element in ET.iterparse(io.BytesIO(data), events=('start', 'end')):
        name = local(element.tag)
        if event == 'start':
            depth += 1
            if depth == 2 and name not in SHEET_KNOWN:
                report.add(f'worksheet element {name} was not read')
            if name == 'sheetView' and element.get('showGridLines') in GRID_OFF:
                grid = False
            continue
        depth -= 1
        if name == 'c':
            element_cell(element, tables, cells, remap)
            element.clear()
    return grid
