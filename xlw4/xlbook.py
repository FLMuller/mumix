"""
xlbook -- the workbook model: root, book and sheet nodes, the cursor, and the verbs that edit.

Why
    The user writes into "the active sheet" with chained verbs (write, writeln, move ...), or on
    a node directly (xl.data.Sheet1.write(...)). A node is a Node, so the same tree holds the
    document and is read by the report and the chart drawer.

Algorithm
    The tree is  root > book > sheet. A sheet holds its cells as ONE leaf, the Grid of xlcells
    (leaf 'cells'), and the flag 'showGrid'; its leaf 'priv' holds the cursor [row, col] and the
    chart nodes. A book's priv holds its file name, the sheet display names and tree keys, the
    tables its cells share, its named styles and the active sheet; the root's priv holds the
    active book and the named styles every book sees. A verb that a node does not define goes to
    its neighbour: down to the active child (a 'Sheet1' is made when a book has none), or, from a
    sheet, up to its book. So a verb called on ANY node reaches the node that defines it, and a
    sheet verb returns the sheet, so calls chain: sheet.write('a').write('b').writeln().
    A style given to write is resolved once per call (xlformat.resolve), and the cells of the
    call share it. Cost: a verb is O(cells it writes).

Use
    root = Root(); book = root.add('results', Book(r'out/results.xlsx'))
    book.newsheet('Data'); sheet = book.Data             # or book.kvr('Data')
    sheet.write('time').write('conc').writeln()          # cursor verbs
    sheet.write([[0.0, 1.5], [1.0, 1.7]])                # a block: one cell per element
    sheet.write('Total', 'Total')                        # a style name; then ('bold', True) pairs
    sheet.formula('=SUM(B2:B3)', cached=3.2)             # cached shows until Excel calculates
    sheet.move('down', 2)   sheet.gridlines(False)   sheet.border([(1, 1)], 'all:thin')
    sheet.chart('conc')                                  # a Chart node (see xlscatter)
    sheet.cell(3, 4)  sheet.cell(3, 4, 'style')  sheet.cell(3, 4, 'formula')    # value, style, formula text
    book.newsheet('A', 'B')   book.newstyle('Mine', 'bold', True)   book.save()   sheet.activate()
    root.named('results')                                # the book by name, or XlwNoBook
    Verbs: write formula writeln nl blankRow move gridlines newsheet newstyle border chart save cell.
    Errors (xlerrors): XlwNoBook, XlwNoSheet, XlwBadArg. A book or sheet named like a method
    (count, write, ...) is refused.

VERSION  M01 m01.v01 (2026-11-06): first version; Node subclasses and verbs in place of the tkv
         verb registry, the cursor and the tables are plain leaves.
"""

import os

from xlcells import Grid, Tables
from xlerrors import XlwBadArg, XlwNoBook, XlwNoSheet
from xlformat import border_delta, named_styles, resolve
from xlpack import build_parts, write_zip
from xlscatter import Chart
from xltext import safe_name
from xltree import Node

__all__ = ['Root', 'Book']

SHEET_VERBS = ('write', 'formula', 'writeln', 'nl', 'blankRow', 'move', 'gridlines', 'border',
               'chart', 'cell')
BOOK_VERBS = ('newsheet', 'newstyle', 'save')
DIRECTIONS = {'up': (-1, 0), 'down': (1, 0), 'left': (0, -1), 'right': (0, 1)}
RESERVED = ('priv', 'cells', 'showGrid')
SCALARS = (float, int, str, bool, type(None))


def to_rows(value):
    """A value to write as a list of rows: a list of lists is rows, a flat list is one row,
    arrays (anything with tolist) are converted first; None for a scalar or text."""
    if type(value) in SCALARS:
        return None
    value = value.tolist() if hasattr(value, 'tolist') else value
    if isinstance(value, dict):
        raise XlwBadArg('write takes a value, a list or a list of lists, not a dict')
    if not isinstance(value, (list, tuple)):
        return None
    if value and isinstance(value[0], (list, tuple)):
        return [list(row) for row in value]
    return [list(value)] if value else []


class Router(Node):
    """A node that hands a verb it does not define to its neighbour: down to its active child,
    or, from a sheet, up to its book. Books and sheets are added through it, so a name that a
    method would hide is refused."""

    def __getattr__(me, name):
        if name not in SHEET_VERBS + BOOK_VERBS:
            return Node.__getattr__(me, name)
        if me.kind == 'sheet':
            return getattr(me.up, name)
        return getattr(me.target('book' if name in BOOK_VERBS else 'sheet'), name)

    def target(me, kind='sheet'):
        """The active node of that kind ('sheet' or 'book') below this one, found by walking down
        the active children: XlwNoBook when the root has no book, and a 'Sheet1' made when a book
        has no sheet."""
        node = me
        while node.kind != kind:
            found = node.leaves['priv'].leaves.get('cursor')
            if found is None and node.kind == 'root':
                raise XlwNoBook('no book (newbook first)')
            node = found or node.newsheet('Sheet1')
        return node

    def add(me, name, kid):
        """Link a book or a sheet as the child `name`; a name taken by a method or by a private
        leaf is refused (XlwBadArg), because the child could not be reached by it."""
        if name in RESERVED or any(hasattr(kind, name) for kind in (Sheet, Book, Root)):
            raise XlwBadArg(f'the name "{name}" is a method name')
        return Node.add(me, name, kid)

    def activate(me):
        """Make this sheet or book the active one, and so its parents. Returns the node."""
        parent = me.up
        if parent is None:
            raise XlwBadArg('the root cannot be activated: it holds the books')
        parent.kvr('priv').kvw('cursor', me)
        if parent.type() != 'root':
            parent.activate()
        return me


class Sheet(Router):
    """One worksheet: the cursor verbs, written into its Grid."""

    def write(me, *args, **keywords):
        """Write one value, or a block, at the cursor. args: the value, an optional style name,
        then property/value pairs; keywords are more properties. Returns the sheet."""
        if not args:
            raise XlwBadArg('write needs a value')
        value, grid, cursor = args[0], me.leaves['cells'], me.leaves['priv'].leaves['cursor']
        delta = {}
        if len(args) > 1 or keywords:
            book = me.up
            styles = [book.leaves['priv'].leaves['styles'], book.up.leaves['priv'].leaves['styles']]
            delta = resolve(styles, args[1:], keywords)
        rows = to_rows(value)
        if rows is None:
            grid.put(cursor[0], cursor[1], value, delta)
            cursor[1] += 1
        else:
            grid.block(rows, cursor[0], cursor[1], delta)
            cursor[1] += max(map(len, rows), default=0)
        return me

    def formula(me, formula, *args, cached=None, **keywords):
        """Write a formula at the cursor and move right; `cached` is the value to show until
        Excel calculates. Style as for write. Returns the sheet."""
        if not isinstance(formula, str):
            raise XlwBadArg('formula takes the text of the formula, for example "=SUM(A1:A9)"')
        styles = [me.up.leaves['priv'].leaves['styles'], me.up.up.leaves['priv'].leaves['styles']]
        delta = resolve(styles, args, keywords) if args or keywords else {}
        cursor = me.leaves['priv'].leaves['cursor']
        me.leaves['cells'].formula(cursor[0], cursor[1], formula, cached, delta)
        cursor[1] += 1
        return me

    def writeln(me, *args, **keywords):
        """Write (when given a value) and start a new row at column 1. Returns the sheet."""
        if args:
            me.write(*args, **keywords)
        cursor = me.leaves['priv'].leaves['cursor']
        cursor[0], cursor[1] = cursor[0] + 1, 1
        return me

    nl = blankRow = writeln

    def move(me, direction, count=1):
        """Move the cursor: up down left right cr home btm (btm = column 1 of the row after the
        last occupied one). Returns the sheet."""
        cursor = me.leaves['priv'].leaves['cursor']
        row, col = cursor
        word = str(direction).lower()
        if word in DIRECTIONS:
            down, right = DIRECTIONS[word]
            row, col = max(1, row + down * count), max(1, col + right * count)
        elif word in ('cr', 'home', 'btm', 'bottom'):
            row = {'cr': row, 'home': 1}.get(word) or me.kvr('cells').extent()[0] + 1
            col = 1
        else:
            raise XlwBadArg(f'unknown direction "{direction}"')
        cursor[0], cursor[1] = row, col
        return me

    def gridlines(me, onoff):
        """Show or hide the grid lines of the sheet. Returns the sheet."""
        shown = bool(onoff)
        me.kvw('showGrid', shown)
        return me

    def border(me, cells, sides, *pairs, **keywords):
        """Apply a border to each (row, col) of `cells`, keeping values; a missing cell becomes a
        value-less cell that keeps the border. A 'color' or 'bcolor' pair sets the edge colour.
        Returns the sheet."""
        changes = border_delta(sides, {**dict(zip(pairs[::2], pairs[1::2])), **keywords})
        for row, col in cells:
            me.kvr('cells').restyle(row, col, changes)
        return me

    def chart(me, name=None):
        """A new Chart on this sheet, named `name` (chartN when None); returns it."""
        charts = me.kvr('priv').node('charts')
        key = safe_name(name) if name else f'chart{charts.count() + 1}'
        if charts.kvr(key) is not None:
            raise XlwBadArg(f'chart "{name}" already exists on this sheet')
        return charts.add(key, Chart())

    def cell(me, row, col, what='value'):
        """One thing about a cell: its 'value' (text as text, a formula's cached value; None when
        blank), its 'style' (a dict) or its 'formula' text (no '='; None when not a formula)."""
        if what not in ('value', 'style', 'formula'):
            raise XlwBadArg(f'cell: what is value, style or formula, not "{what}"')
        if row < 1 or col < 1:
            raise XlwBadArg('rows and columns are counted from 1')
        return me.kvr('cells').read(row, col, what)


class Book(Router):
    """One workbook: its sheets, its named styles and its file."""

    def __init__(me, filename):
        Node.__init__(me, 'book')
        folder, base = os.path.split(str(filename))
        priv = Node()
        for leaf, value in (('fname', os.path.join(folder or os.getcwd(), base)), ('sheets', []),
                            ('sheetkeys', []), ('tables', Tables()), ('styles', {})):
            priv.kvw(leaf, value)
        me.kvw('priv', priv)

    def newsheet(me, *names):
        """Add sheets; the first one added becomes the active sheet, which is returned."""
        if not names:
            raise XlwBadArg('no sheet name supplied')
        priv = me.kvr('priv')
        first = None
        for name in names:
            key = safe_name(name)
            if key in priv.kvr('sheetkeys'):
                raise XlwBadArg(f'sheet "{name}" already exists')
            sheet = me.add(key, Sheet('sheet'))
            sheet.kvw('priv', Node())
            sheet.kvr('priv').kvw('cursor', [1, 1])
            sheet.kvw('cells', Grid(priv.kvr('tables')))
            sheet.kvw('showGrid', True)
            priv.kvw('sheets', priv.kvr('sheets') + [str(name)])
            priv.kvw('sheetkeys', priv.kvr('sheetkeys') + [key])
            first = first or sheet
        priv.kvw('cursor', first)
        return first

    def newstyle(me, name, *pairs, **keywords):
        """A named style visible to this book: the pairs and keywords over an optional named
        base, as for write. Returns the book."""
        mine = me.kvr('priv').kvr('styles')
        shared = me.up.kvr('priv').kvr('styles')
        key = safe_name(name)
        style = resolve([mine, shared], pairs, keywords)
        mine[key] = style
        return me

    def save(me):
        """Save the book to its file; returns the book."""
        priv = me.kvr('priv')
        if not priv.kvr('sheetkeys'):
            raise XlwNoSheet('nothing to save')
        parts = build_parts(me)
        write_zip(priv.kvr('fname'), parts)
        return me


class Root(Router):
    """The root of the tree: the books, and the named styles every book sees."""

    def __init__(me):
        Node.__init__(me, 'root')
        styles = named_styles()
        priv = Node()
        priv.kvw('styles', styles)
        me.kvw('priv', priv)

    def named(me, name):
        """The book called `name`, or XlwNoBook."""
        found = me.kids.get(safe_name(name))
        if not isinstance(found, Book):
            known = ', '.join(kid.name for kid in me.nodes() if isinstance(kid, Book))
            raise XlwNoBook(f'No book named "{name}"; the books are: {known or "none"}.')
        return found
