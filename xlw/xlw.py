"""
xlw -- a pure-Python .xlsx writer on a tkv tree. No COM, no Excel, no third-party code.

Why
    Excel output is easier to read than a console table, and a chart beside the data is
    easier still. xlw keeps the document in a tkv tree for its structure and in one kv per
    sheet for the cells, and turns it into an .xlsx in one pass.

Algorithm
    The document is a typed tree  root > book > sheet.  A sheet's cells are not nodes: they
    are one kv, the leaf 'cells' of the sheet, holding a tuple (kind, payload, xf) per
    (row, col); what cells share lives once in the book (leaf 'tables' of the book's priv):
    the text table and the style table (see xlsheet, which also writes and reads the sheet
    XML). Private state sits in an untyped tkv stored as the leaf 'priv' of each level: the
    cursor, the sheet list, the file name, the named styles and the chart definitions.
    The verbs (write, writeln, move, ...) are registered on the root, so a verb called
    on ANY node reaches its handler with that node, and returns the sheet so calls
    chain:  sheet.write('a').write('b').writeln().
    Save lists each sheet's grid in row order and writes its cells as strings; styles.xml and
    sharedStrings.xml come straight from the book tables. The default style is always xf 0.

Use
    import sys; sys.path.insert(0, r'<mumix>/tools')      # use.py builds kv/tkv
    from xlw import xlw
    xl = xlw()
    xl.newbook(r'out/results.xlsx', 'Data')               # book node; first sheet 'Data'
    xl.write('time').write('conc').writeln()              # cursor verbs, active sheet
    xl.write([[0.0, 1.5], [1.0, 1.7]])                    # a block: one cell per element
    xl.data.Data.write('Total', 'Total')                  # node form; 'Total' = a style
    xl.write('x', bold=True, fill='yellow')               # keyword form (xlw methods)
    xl.save()                                             # the active book

    Node form takes the style as positional pairs:  sheet.write(v, 'bold', True).
    Style properties: font sz bold italic underline strikethrough fill color halign
    valign numfmt wrap indent shrink rotation border bcolor (see xlstyle).
    Read a cell:  xlsheet.cell_value(sheet, 3, 4)  and  xlsheet.cell_style(sheet, 3, 4).
    Cursor:  sheet.kvr('priv').kvr('cursor').
    Verbs: write formula writeln nl blankRow move gridlines newsheet newstyle border
    activate save chart.   Charts: see xlchart and chartdef.md.
    A sheet or book name equal to a tkv method name (count, keys, type, ...) is refused.

Versions
    M02  m02.v02  2026-11-01  formulas: the formula verb; the workbook is calculated on load
                              when a formula has no cached value.
         m02.v01  2026-10-31  rebuilt on the grid: cells are one kv per sheet, text and
                              styles are book tables, the cell type of the tree is gone.
    M01  m01.v01  2026-10-31  ported from xlw.m v1.19 (tree, verbs, styles, ribosome save);
                              charts added; savehtml not ported; default style fixed at xf 0.
"""

import os
import re

from xlstore import KV, TKV
import xlparts
import xlsheet
import xlstyle
from xlsheet import BLANK, TXT, FML
from xlstyle import safe_name

__all__ = ['xlw', 'XlwError', 'XlwNoBook', 'XlwNoSheet', 'XlwBadArg', 'book_values']

NO_STYLE = {}                    # shared and never changed: copied before anything is added
FORMULA_WITHOUT_VALUE = re.compile(r'</f></c>|<f[^>]*/></c>')   # a formula cell with no <v>


class XlwError(Exception):
    pass


class XlwNoBook(XlwError):
    pass


class XlwNoSheet(XlwError):
    pass


class XlwBadArg(XlwError):
    pass


class Priv:
    """Private state of one xlw object."""
    __slots__ = ('root', 'rootpriv')


# ------------------------------------------------------------------ tree helpers -----
def addpriv(node):
    """The untyped tkv held as leaf 'priv' of a node, made on first use. It carries the
    cursor and a 'styles' node; stored as a leaf, so it never counts as a child node."""
    priv = node.kvr('priv')
    if priv is not None:
        return priv
    priv = TKV()
    priv.node('styles')
    node.kvw('priv', priv)
    return priv


def node2book(node):
    """The book a node belongs to (the active book when given the root)."""
    if node.type() == 'root':
        book = node.kvr('priv').kvr('cursor')
        if book is None:
            raise XlwNoBook('no book (newbook first)')
        return book
    book = node
    while book is not None and book.type() != 'book':
        book = book.parent()
    if book is None:
        raise XlwNoBook('cannot resolve book')
    return book


def node2sheet(node):
    """The sheet a node means: itself, or the active sheet of its book (a 'Sheet1' is made
    when the book has none yet)."""
    if node.type() == 'sheet':
        return node
    book = node2book(node)
    sheet = book.kvr('priv').kvr('cursor')
    if sheet is None:
        sheet = fwd_newsheet(book, 'Sheet1')
    return sheet


# ------------------------------------------------------------------ verb handlers ----
def fwd_activate(node):
    """Make a book or a sheet the active one (cascading upward)."""
    kind = node.type()
    if kind == 'book':
        node.parent().kvr('priv').kvw('cursor', node)
    elif kind == 'sheet':
        book = node.parent()
        book.parent().kvr('priv').kvw('cursor', book)
        book.kvr('priv').kvw('cursor', node)
    else:
        raise XlwBadArg('activate on an untyped node')
    return node


def fwd_newsheet(node, *names):
    """Add sheets to the book of `node`; the first one added becomes the active sheet.
    Returns that sheet node."""
    if not names:
        raise XlwBadArg('no sheet name supplied')
    book = node2book(node)
    bpriv = book.kvr('priv')
    first = None
    for name in names:
        if safe_name(name) in bpriv.kvr('sheetkeys'):
            raise XlwBadArg(f'sheet "{name}" already exists')
        sheet = book.node(safe_name(name))
        spriv = addpriv(sheet)
        spriv.kvw('cursor', [1, 1])
        sheet.kvw('showGrid', True)
        sheet.kvw('cells', KV())
        bpriv.kvw('sheets', list(bpriv.kvr('sheets')) + [str(name)])
        bpriv.kvw('sheetkeys', list(bpriv.kvr('sheetkeys')) + [safe_name(name)])
        if first is None:
            first = sheet
    bpriv.kvw('cursor', first)
    return first


def fwd_newstyle(node, name, *pairs):
    """A named style: a node plus leaves under the owning level's priv.styles. Given a
    sheet it is stored on the book."""
    if node.type() == 'sheet':
        node = node.parent()
    styles = node.kvr('priv').kvr('styles')
    key = safe_name(name)
    style = styles.kvr(key)
    if style is None:
        style = styles.node(key)
    for index in range(0, len(pairs) - 1, 2):
        prop = str(pairs[index]).lower()
        if xlstyle.is_style_prop(prop):
            style.kvw(prop, pairs[index + 1])
    return node


def to_rows(value):
    """A value to write as a list of rows. A list of lists is rows; a flat list is one
    row; text and scalars are a single cell; arrays (anything with tolist) are
    converted first."""
    if hasattr(value, 'tolist'):
        value = value.tolist()
    if isinstance(value, (list, tuple)):
        if not value:
            return []
        if isinstance(value[0], (list, tuple)):
            return [list(row) for row in value]
        return [list(value)]
    if isinstance(value, dict):
        raise XlwBadArg('write takes a value, a list or a list of lists, not a dict')
    return None


def fwd_write(node, *args, **keywords):
    """Write one value, or a block, at the cursor; returns the sheet so calls chain.
    args = value, then an optional style name, then style key/value pairs."""
    sheet = node2sheet(node)
    if not args:
        raise XlwBadArg('write needs a value')
    do_write(sheet, args[0], args[1:], keywords)
    return sheet


def fwd_formula(node, formula, *args, **keywords):
    """Write a formula at the cursor, then move right; `cached` (a keyword) is the value to
    show until Excel calculates. Style as for write. Returns the sheet."""
    sheet = node2sheet(node)
    cached = keywords.pop('cached', None)
    if args or keywords:
        delta = xlstyle.style_delta(xlstyle.resolve_style(sheet, args, keywords))
    else:
        delta = None
    spriv = sheet.kvr('priv')
    row, col = spriv.kvr('cursor')
    xlsheet.put_formula(sheet, row, col, formula, cached, delta)
    spriv.kvw('cursor', [row, col + 1])
    return sheet


def fwd_writeln(node, *args, **keywords):
    """Write (if given a value) and start a new row at column 1."""
    sheet = node2sheet(node)
    if args:
        do_write(sheet, args[0], args[1:], keywords)
    spriv = sheet.kvr('priv')
    row, _ = spriv.kvr('cursor')
    spriv.kvw('cursor', [row + 1, 1])
    return sheet


def fwd_gridlines(node, onoff):
    sheet = node2sheet(node)
    sheet.kvw('showGrid', bool(onoff))
    return sheet


def fwd_move(node, direction, count=1):
    """Move the cursor: up down left right cr home btm (btm = first column of the row
    after the last occupied one)."""
    sheet = node2sheet(node)
    spriv = sheet.kvr('priv')
    row, col = spriv.kvr('cursor')
    direction = str(direction).lower()
    if direction == 'up':
        row = max(1, row - count)
    elif direction == 'down':
        row += count
    elif direction == 'left':
        col = max(1, col - count)
    elif direction == 'right':
        col += count
    elif direction == 'cr':
        col = 1
    elif direction == 'home':
        row = 1
        col = 1
    elif direction in ('btm', 'bottom'):
        found = xlsheet.cell_list(sheet)
        row = max(item[0] for item in found) + 1 if found else 1
        col = 1
    else:
        raise XlwBadArg(f'unknown direction "{direction}"')
    spriv.kvw('cursor', [row, col])
    return sheet


def fwd_border(node, cells, sides, *pairs, **keywords):
    """Apply a border to each (row, col) of `cells` without touching values. Cells that
    do not exist yet are made value-less (a blank cell: no <v> in the sheet XML, but the
    border style is kept). An optional 'color' or 'bcolor' pair sets the edge colour."""
    sheet = node2sheet(node)
    bcolor = '000000'
    options = dict(keywords)
    for index in range(0, len(pairs) - 1, 2):
        options[str(pairs[index])] = pairs[index + 1]
    for key, value in options.items():
        if key.lower() in ('color', 'bcolor'):
            bcolor = xlstyle.color2hex(value)
    border = xlstyle.normalise_border(sides, bcolor)
    grid = sheet.kvr('cells')
    tables = xlsheet.tables_of(sheet)
    for row, col in cells:
        cell = grid.kvr((row, col))
        if cell is None:
            cell = (BLANK, None, 0)
        delta = dict(tables.xfs[cell[2]])
        delta['border'] = border
        if bcolor != '000000':
            delta['bcolor'] = bcolor
        grid[row, col] = (cell[0], cell[1], xlsheet.style_id(tables, delta))
    return sheet


def do_write(sheet, value, args, keywords):
    """Write `value` at the cursor: one cell for a scalar or text, one cell per element
    for a block (a list of lists is rows). The cursor moves right of the block."""
    if args or keywords:
        delta = xlstyle.style_delta(xlstyle.resolve_style(sheet, args, keywords))
    else:
        delta = NO_STYLE                      # the common write: nothing to resolve
    spriv = sheet.kvr('priv')
    row0, col0 = spriv.kvr('cursor')
    cells = sheet.kvr('cells')
    tables = xlsheet.tables_of(sheet)
    make = xlsheet.make_cell
    rows = to_rows(value)
    fun = xlsheet.FUN
    if fun is not None and delta is NO_STYLE:      # the Cython loop writes unstyled blocks
        block = [[value]] if rows is None else rows
        fun.write_rows(cells, tables, block, row0, col0, make, xlsheet.style_id)
    elif rows is None:
        cells[row0, col0] = make(tables, value, delta)
    else:
        for i, rowvalues in enumerate(rows):
            for j, item in enumerate(rowvalues):
                cells[row0 + i, col0 + j] = make(tables, item, delta)
    width = 1 if rows is None else max((len(item) for item in rows), default=0)
    spriv.kvw('cursor', [row0, col0 + width])


# -------------------------------------------------------------------------- save -----
def book_values(book):
    """A function ref -> list of cell values for a chart's data reference
    ("Sheet!$A$2:$A$10", row-major); None for an empty or text cell."""
    import xlchart                            # only books with charts need chart code
    bpriv = book.kvr('priv')
    tables = bpriv.kvr('tables')
    key_of = KV()                             # sheet display name -> tree key
    for name, key in zip(bpriv.kvr('sheets'), bpriv.kvr('sheetkeys')):
        key_of.kvw('n:' + name, key)

    def values(ref):
        parsed = xlchart.parse_ref(ref)
        if parsed is None or key_of.kvr('n:' + parsed[0]) is None:
            return []
        name, row1, col1, row2, col2 = parsed
        grid = book.kvr(key_of.kvr('n:' + name)).kvr('cells')
        found = []
        for row in range(row1, row2 + 1):
            for col in range(col1, col2 + 1):
                cell = grid.kvr((row, col))
                if cell is None or cell[0] == BLANK:
                    found.append(None)
                elif cell[0] == TXT:
                    found.append(xlsheet.text_at(tables, cell[1]))
                elif cell[0] == FML:
                    found.append(cell[1][1])
                else:
                    found.append(cell[1])
        return found
    return values


def build_parts(book):
    """All parts of one book as a list of (part name, text) in zip order."""
    bpriv = book.kvr('priv')
    keys = bpriv.kvr('sheetkeys')
    names = bpriv.kvr('sheets')
    if not keys:
        raise XlwNoSheet('nothing to save')
    tables = bpriv.kvr('tables')
    texts = xlsheet.text_list(tables)
    formulas = xlsheet.formula_list(tables)
    needs_calc = False
    sheet_xmls = []
    sheet_charts = []
    sheet_widths = []
    for key in keys:
        sheet = book.kvr(key)
        data_xml, columns_xml, width = xlsheet.sheet_to_xml(sheet, texts, formulas)
        if formulas and not needs_calc:
            needs_calc = FORMULA_WITHOUT_VALUE.search(data_xml) is not None
        sheet_widths.append(width)
        charts = sheet.kvr('priv').kvr('charts')
        chart_nodes = [] if charts is None else charts.nodes()
        sheet_charts.append(chart_nodes)
        grid = sheet.kvr('showGrid')
        grid_attr = '' if grid is None or grid else ' showGridLines="0"'
        views = f'<sheetViews><sheetView{grid_attr} workbookViewId="0"/></sheetViews>'
        namespaces = f'xmlns="{xlparts.NS_MAIN}"'
        drawing = ''
        if chart_nodes:
            namespaces += f' xmlns:r="{xlparts.NS_REL}"'
            drawing = '<drawing r:id="rId1"/>'
        sheet_xmls.append(xlparts.XML_HEAD + f'<worksheet {namespaces}>' + views
                          + columns_xml + data_xml + drawing + '</worksheet>')

    n_drawings = sum(1 for charts in sheet_charts if charts)
    n_charts = sum(len(charts) for charts in sheet_charts)
    styles = []
    for delta in tables.xfs:
        style = dict(xlstyle.DEFAULTS)
        style.update(delta)
        styles.append(style)
    parts = [('[Content_Types].xml',
              xlparts.content_types(len(keys), n_drawings, n_charts)),
             ('_rels/.rels', xlparts.root_rels()),
             ('xl/workbook.xml', xlparts.workbook_part(names, needs_calc)),
             ('xl/_rels/workbook.xml.rels', xlparts.workbook_rels(len(keys))),
             ('xl/styles.xml', xlstyle.build_style_tables(styles)),
             ('xl/sharedStrings.xml', xlparts.shared_strings(texts))]
    for n, sheet_xml in enumerate(sheet_xmls, start=1):
        parts.append((f'xl/worksheets/sheet{n}.xml', sheet_xml))

    if n_charts:
        import xlchart
        values = book_values(book)
        drawing_number = 0
        chart_number = 0
        for n, chart_nodes in enumerate(sheet_charts, start=1):
            if not chart_nodes:
                continue
            drawing_number += 1
            numbers = []
            frames = []
            for index, chart in enumerate(chart_nodes):
                chart_number += 1
                numbers.append(chart_number)
                frames.append((f'Chart {chart_number}',
                               xlchart.anchor_of(chart, sheet_widths[n - 1], index)))
                parts.append((f'xl/charts/chart{chart_number}.xml',
                              xlchart.chart_part(chart, values)))
            parts.append((f'xl/worksheets/_rels/sheet{n}.xml.rels',
                          xlparts.sheet_rels(drawing_number)))
            parts.append((f'xl/drawings/drawing{drawing_number}.xml',
                          xlparts.drawing_part(frames)))
            parts.append((f'xl/drawings/_rels/drawing{drawing_number}.xml.rels',
                          xlparts.drawing_rels(numbers)))
    return parts


def fwd_save(node):
    """Save the book of `node` to its file; returns the book."""
    book = node2book(node)
    xlparts.write_zip(book.kvr('priv').kvr('fname'), build_parts(book))
    return book


def fwd_chart(node, name=None):
    """A new chart on the sheet of `node` (see xlchart); returns the chart node."""
    import xlchart
    return xlchart.new_chart(node2sheet(node), name)


# -------------------------------------------------------------------------- class ----
class xlw:
    """The writer. Holds the typed tree; its methods act on the active book and sheet
    and return the xlw object so calls chain. A book is reached as an attribute:
    xl.data (the book 'data'), and a sheet as xl.data.Sheet1."""

    def __init__(me):
        me.priv = Priv()
        me.priv.root = TKV(['root', 'book', 'sheet'],
                           write=fwd_write, formula=fwd_formula, writeln=fwd_writeln,
                           nl=fwd_writeln,
                           blankRow=fwd_writeln, move=fwd_move, gridlines=fwd_gridlines,
                           newsheet=fwd_newsheet, newstyle=fwd_newstyle,
                           border=fwd_border, activate=fwd_activate, save=fwd_save,
                           chart=fwd_chart)
        me.priv.rootpriv = addpriv(me.priv.root)
        xlstyle.load_defaults(me.priv.rootpriv.kvr('styles'))

    @property
    def root(me):
        return me.priv.root

    def __getattr__(me, name):
        # Only called for names that are not attributes: resolve a book by name.
        if name.startswith('_') or name == 'priv':
            raise AttributeError(name)
        book = me.priv.root.kvr(name)
        if book is None:
            raise XlwNoBook(f'No book named "{name}".')
        return book

    def newbook(me, filename, *sheets):
        """A new book, made active. The extension .xlsx is added when missing. Returns
        the book node; cache it. Optional names create sheets."""
        folder, base = os.path.split(str(filename))
        if base.lower().endswith('.xlsx'):
            base = base[:-5]
        folder = folder or os.getcwd()
        book = me.priv.root.node(safe_name(base))
        bpriv = addpriv(book)
        bpriv.kvw('fname', os.path.join(folder, base + '.xlsx'))
        bpriv.kvw('sheets', [])
        bpriv.kvw('sheetkeys', [])
        bpriv.kvw('tables', xlsheet.new_tables())
        me.priv.rootpriv.kvw('cursor', book)
        if sheets:
            fwd_newsheet(book, *sheets)
        return book

    def open(me, filename, name=None):
        """Read an .xlsx into the tree (cells, styles, XY charts) and return its book
        node. It is saved to <name>_xlw.xlsx beside the source, never over it; what was
        not read is listed in book.priv.unmapped (see xlreader)."""
        import xlreader                       # xlreader imports this module
        return xlreader.read_book(me, filename, name)

    def newstyle(me, name, *pairs, **keywords):
        """A named style visible to every book."""
        merged = list(pairs)
        for key, value in keywords.items():
            merged += [key, value]
        fwd_newstyle(me.priv.root, name, *merged)
        return me

    def newsheet(me, *names):
        return fwd_newsheet(me.priv.root, *names)

    def write(me, value, *args, **keywords):
        fwd_write(me.priv.root, value, *args, **keywords)
        return me

    def formula(me, formula, *args, **keywords):
        """A formula at the cursor, e.g. xl.formula('=SUM(B2:B9)', cached=3.5)."""
        fwd_formula(me.priv.root, formula, *args, **keywords)
        return me

    def writeln(me, *args, **keywords):
        fwd_writeln(me.priv.root, *args, **keywords)
        return me

    def nl(me):
        fwd_writeln(me.priv.root)
        return me

    def blankRow(me):
        fwd_writeln(me.priv.root)
        return me

    def move(me, direction, count=1):
        fwd_move(me.priv.root, direction, count)
        return me

    def gridlines(me, onoff):
        fwd_gridlines(me.priv.root, onoff)
        return me

    def border(me, cells, sides, *pairs, **keywords):
        fwd_border(me.priv.root, cells, sides, *pairs, **keywords)
        return me

    def chart(me, name=None):
        """A new chart on the active sheet; returns the chart node."""
        return fwd_chart(me.priv.root, name)

    def activate(me, target):
        """Make a book active, by name or by node."""
        if isinstance(target, str):
            book = me.priv.root.kvr(safe_name(target))
            if book is None:
                raise XlwNoBook(f'No book named "{target}".')
            me.priv.rootpriv.kvw('cursor', book)
        else:
            fwd_activate(target)
        return me

    def save(me, target=None):
        """Save the active book; or save('all'); or a book by name or node; or a list
        of those."""
        root = me.priv.root
        if target is None:
            fwd_save(root)
        elif isinstance(target, str) and target.lower() == 'all':
            for book in root.nodes():
                if book.type() == 'book':
                    fwd_save(book)
        elif isinstance(target, (list, tuple)):
            for item in target:
                me.save(item)
        elif isinstance(target, str):
            book = root.kvr(safe_name(target))
            if book is None:
                raise XlwNoBook(f'No book named "{target}".')
            fwd_save(book)
        else:
            fwd_save(target)
        return me
