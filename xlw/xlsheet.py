"""
xlsheet -- the worksheet XML codec of xlw: a sheet node in the tkv tree <-> sheet XML.

Why
    The xlw tree is the document; a worksheet part is its text. Writing and reading that
    text with general tools (f-strings per cell going out, ElementTree events per cell
    coming in) costs about as much as building the tree itself. Here both directions are
    written for the one XML dialect a worksheet really uses, and both come from the same
    description of it, so they cannot drift apart.

Algorithm
    The worksheet grammar we know (the same table drives both directions):
        worksheet > sheetViews, cols, sheetData > row r > c r s t > [f] [is] [v]
        c t:   absent or n  number    s  shared string (index)    b  boolean 1/0
               str, e       text      inlineStr  text inside <is><t>
               anything else is read as a number, as before
        f  a formula: counted for the report, its cached <v> is the value
    Going out, sheet_to_xml walks the sheet's cell nodes once, in row order. The style of a
    cell is the set of its leaves other than 'val'; its index (xf) is found through a
    cache keyed by that set, so the style tables are consulted once per distinct style, not
    once per cell. Text is charged to the shared string table at first sight.
    Coming in, xml_to_sheet cuts the part into head, <sheetData> body and tail. The head
    and tail (a handful of elements) go through ElementTree to find the grid-lines flag and
    to report elements we do not read. The body is cut by ONE regular-expression split
    that doubles as the index of the part: the compiled expression matches a cell in the
    forms above (the attribute order Excel and xlw write), and re.split returns, in order,
    the text between matches (the gaps: row tags, or a cell the expression did not accept)
    interleaved with the fields of each matched cell. The byte offset of every range is the
    running sum of the lengths. A gap that holds '<c ' is a cell of an unusual form
    (another attribute order, rich-text runs, ...): each such cell is parsed alone as a
    fragment by ElementTree, with exactly the rules of the general path, and written in its
    place in the document order. All fragments are parsed before the first cell is written,
    so a part that cannot be read leaves the sheet untouched. A part without a plain
    <sheetData> (a prefixed namespace, ...) is read whole by the general ElementTree path.
    Every path gives the same cells; the tests hold them to it.
    Cost: O(cells). One split pass; then per cell a dictionary lookup for the column, two
    int(), one float() and the tkv node write. A fragment costs about 20 us.

Use
    import xlsheet
    xml, cols, ncols = xlsheet.sheet_to_xml(sheet, state)     # <sheetData>, <cols>, widest
    grid = xlsheet.xml_to_sheet(data, sheet, strings, deltas, report)
    xlsheet.BLANK                  value of a styled cell that holds nothing
    xlsheet.sheet_cells(sheet)     [(row, col, cell node)] in row-major order
    state needs: xf_index (kv: style key -> xf), styles (list), strings (list),
    string_index (kv). deltas is the list of style deltas of the book (xlreader);
    report has .add(message). data is the part as bytes; strings the shared strings.

Versions
    M01  m01.v02  2026-10-31  the scan is a re.split index; formula cells and simple inline
                              strings are in the expression; any other unusual cell is a
                              fragment read by ElementTree instead of sending the whole part
                              to the slow path.
         m01.v01  2026-10-31  first version: the emitter (from xlw.sheet_data) with a style
                              cache, and the regex scanner with the ElementTree fallback
                              (from xlreader.read_cells). Both still live in their old
                              places until the integration step.
"""

import io
import math
import re
import xml.etree.ElementTree as ET
from operator import itemgetter

from xlparts import col2letter
from xlstyle import DEFAULTS, num_text, style_key

__all__ = ['BLANK', 'sheet_cells', 'sheet_to_xml', 'xml_to_sheet', 'read_with_elementtree',
           'parse_fragments', 'SHEET_KNOWN']

BLANK = '!empty'                 # a styled cell that carries no value
DEFAULT_KEY = 'x:'               # the style key of the default style
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


def local(tag):
    return tag.rsplit('}', 1)[-1]


# ------------------------------------------------------------------------- tkv side -----
def sheet_cells(sheet):
    """(row, col, cell node) for every cell of a sheet, in row-major order. The keys of
    a sheet's cell nodes are '(r c)'; names() and nodes() list them in one order."""
    cells = []
    for name, node in zip(sheet.names(), sheet.nodes()):
        if name[:1] == '(':
            parts = name[1:-1].split()
            cells.append((int(parts[0]), int(parts[1]), node))
    cells.sort(key=itemgetter(0, 1))
    return cells


# ---------------------------------------------------------------------------- out -------
def style_index(delta, cache, state):
    """The xf index of a style delta, registered in the state's tables at first sight.
    `cache` maps the delta (as a tuple of its items) to the index: a repeated style costs
    one dictionary lookup."""
    key = tuple(delta.items())
    try:
        found = cache.get(key)
    except TypeError:                         # an unhashable setting: no caching
        key = None
        found = None
    if found is not None:
        return found
    skey = style_key(delta)
    xf = state.xf_index.kvr(skey)
    if xf is None:
        xf = len(state.styles)
        state.xf_index.kvw(skey, xf)
        style = dict(DEFAULTS)
        style.update(delta)
        state.styles.append(style)
    if key is not None:
        cache[key] = xf
    return xf


def sheet_to_xml(sheet, state):
    """The <sheetData> text and <cols> text of one sheet, and its number of columns,
    charging the style and string tables of `state` as cells are met."""
    cells = sheet_cells(sheet)
    ncols = max((item[1] for item in cells), default=0)
    letters = [''] + [col2letter(n) for n in range(1, ncols + 1)]
    widest = [0] * (ncols + 1)
    fragments = ['<sheetData>']
    append = fragments.append
    cache = {}
    strings = state.strings
    string_index = state.string_index
    current = -1
    for row, col, cell in cells:
        if row != current:
            if current > 0:
                append('</row>')
            append(f'<row r="{row}">')
            current = row
        value = None
        delta = {}
        for key, setting in cell.entries():
            if key == 'val':
                value = setting
            else:
                delta[key] = setting
        xf = style_index(delta, cache, state) if delta else 0
        head = f'<c r="{letters[col]}{row}" s="{xf}"'
        width = 0
        if value is None or value == '' or value == BLANK:
            append(head + '/>')
        elif isinstance(value, bool):
            append(f'{head} t="b"><v>{int(value)}</v></c>')
            width = 5
        elif isinstance(value, (int, float)):
            if math.isfinite(value):
                text = num_text(value)
                append(f'{head}><v>{text}</v></c>')
                width = len(text)
            else:
                append(head + '/>')
        else:
            text = str(value)
            skey = 's' + text                 # a leading letter keeps '(' keys legal
            index = string_index.kvr(skey)
            if index is None:
                index = len(strings)
                string_index.kvw(skey, index)
                strings.append(text)
            append(f'{head} t="s"><v>{index}</v></c>')
            width = len(text)
        if width > widest[col]:
            widest[col] = width
    if current > 0:
        append('</row>')
    append('</sheetData>')
    columns = ''
    for col in range(1, ncols + 1):
        if widest[col] > 0:
            size = min(MAX_COLUMN_WIDTH, max(MIN_COLUMN_WIDTH, widest[col] + 2))
            columns += (f'<col min="{col}" max="{col}" width="{size}" '
                        'customWidth="1"/>')
    if columns:
        columns = '<cols>' + columns + '</cols>'
    return ''.join(fragments), columns, ncols


# ----------------------------------------------------------------------------- in -------
def put_cell(sheet, row, col, value, delta):
    """Write one cell node: the value leaf and the style leaves (nothing for a blank cell
    without a style)."""
    if value is not None or delta:
        cell = sheet.node(row, col)
        cell['val'] = BLANK if value is None else value
        for prop, setting in delta.items():
            cell[prop] = setting


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


def element_cell(element, sheet, strings, deltas):
    """Write the cell of a parsed <c> element, by the rules of the general path; returns 1
    when it holds a formula (the caller counts them for the report)."""
    reference = re.match(r'([A-Z]+)(\d+)', element.get('r'))
    col = letters2col(reference.group(1).encode())
    row = int(reference.group(2))
    kind = element.get('t')
    raw = element.find(NS_MAIN + 'v')
    formula = 1 if element.find(NS_MAIN + 'f') is not None else 0
    if kind == 'inlineStr':
        value = ''.join(t.text or '' for t in element.iter(NS_MAIN + 't'))
    elif raw is None or raw.text is None:
        value = None
    elif kind == 's':
        value = strings[int(raw.text)]
    elif kind == 'b':
        value = raw.text in ('1', 'true')
    elif kind in ('str', 'e'):
        value = raw.text
    else:
        value = float(raw.text)
    style = int(element.get('s', 0))
    put_cell(sheet, row, col, value, deltas[style] if style < len(deltas) else {})
    return formula


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


def scan_plain(found, sheet, strings, deltas):
    """Write the cells of CELL_FAST.findall: numbers, shared strings, booleans, text and
    blanks with their styles, the tables most worksheets are."""
    columns = {}
    ndeltas = len(deltas)
    for letters, digits, style, kind, raw in found:
        col = columns.get(letters)
        if col is None:
            col = columns[letters] = letters2col(letters)
        if not raw:
            value = None
        elif not kind:
            value = float(raw)
        elif kind == b's':
            value = strings[int(raw)]
        elif kind == b'b':
            value = raw in (b'1', b'true')
        elif kind == b'str' or kind == b'e':
            value = text_value(raw)
        else:
            value = float(raw)
        index = int(style) if style else 0
        put_cell(sheet, int(digits), col, value, deltas[index] if index < ndeltas else {})


def xml_to_sheet(data, sheet, strings, deltas, report):
    """Read a worksheet part (bytes) into the sheet node; returns the grid-lines flag.
    A body with no formula and no inline string is read with the plain expression
    (CELL_FAST.findall), the common table; otherwise the body is cut by CELL.split and
    unusual cells are read one by one as fragments; a part without a plain <sheetData> is
    read whole by the general ElementTree path."""
    start = data.find(b'<sheetData')
    if start < 0:
        return read_with_elementtree(data, sheet, strings, deltas, report)
    close = data.find(b'>', start)
    if data[close - 1:close + 1] == b'/>':
        body = b''
        tail = data[close + 1:]
    else:
        end = data.find(b'</sheetData>', close)
        if end < 0:
            return read_with_elementtree(data, sheet, strings, deltas, report)
        body = data[close + 1:end]
        tail = data[end + len(b'</sheetData>'):]
    if b'<f' not in body and b'<is>' not in body:
        found = CELL_FAST.findall(body)
        if len(found) == body.count(CELL_START):
            grid = head_and_tail(data[:start], tail, report)
            scan_plain(found, sheet, strings, deltas)
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
                return read_with_elementtree(data, sheet, strings, deltas, report)
            if len(elements) != gap.count(CELL_START):
                return read_with_elementtree(data, sheet, strings, deltas, report)
            odd[number] = elements
    if len(odd) == 0 and body.count(CELL_START) != count:
        return read_with_elementtree(data, sheet, strings, deltas, report)
    grid = head_and_tail(data[:start], tail, report)
    columns = {}
    ndeltas = len(deltas)
    formulas = 0
    number = 0
    fields = zip(parts[1::stride], parts[2::stride], parts[3::stride], parts[4::stride],
                 parts[5::stride], parts[6::stride], parts[7::stride])
    for letters, digits, style, kind, formula, inline, raw in fields:
        if odd and number in odd:
            for element in odd[number]:
                formulas += element_cell(element, sheet, strings, deltas)
        number += 1
        col = columns.get(letters)
        if col is None:
            col = columns[letters] = letters2col(letters)
        if formula:
            formulas += 1
        if kind == b'inlineStr':
            value = inline_value(inline) if inline else ''
        elif not raw:
            value = None
        elif not kind:
            value = float(raw)
        elif kind == b's':
            value = strings[int(raw)]
        elif kind == b'b':
            value = raw in (b'1', b'true')
        elif kind == b'str' or kind == b'e':
            value = text_value(raw)
        else:
            value = float(raw)
        index = int(style) if style else 0
        put_cell(sheet, int(digits), col, value, deltas[index] if index < ndeltas else {})
    if odd and count in odd:
        for element in odd[count]:
            formulas += element_cell(element, sheet, strings, deltas)
    if formulas:
        report.add(f'{formulas} formula cells: the cached values were read, not the formulas')
    return grid


def read_with_elementtree(data, sheet, strings, deltas, report):
    """The general path: stream the part through ElementTree, cell by cell as each closes;
    anything not read is reported. Returns the grid-lines flag."""
    formulas = 0
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
            formulas += element_cell(element, sheet, strings, deltas)
            element.clear()
    if formulas:
        report.add(f'{formulas} formula cells: the cached values were read, not the formulas')
    return grid
