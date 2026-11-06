"""
xlw -- a pure-Python .xlsx writer and reader on a tree. No COM, no Excel, no third-party code.

Why
    Excel output is easier to read than a console table, and a chart beside the data is easier
    still. xlw keeps the document as a tree (root > book > sheet, see xlbook), writes it to an
    .xlsx in one pass (xlpack), and reads an .xlsx back into the same tree.

Algorithm
    The class below is the door: it holds the root node and forwards the verbs to the active
    sheet, so xl.write('a').write('b').writeln() chains. The cells are a dict of tuples per sheet
    with the text, styles and formulas shared by the book (xlcells), the look of a cell is a small
    style dict (xlformat), a chart is a tree of settings written to and read from the Excel chart
    part (xlscatter), and the package of parts is built and unzipped in xlpack. xlw4 is a rebuild
    of xlw with the same interface: one pure-Python tree (xltree) in place of the compiled kv and
    tkv, and each part of the file converted in one module, both ways.

Use
    from xlw import xlw
    xl = xlw()
    xl.newbook(r'out/results.xlsx', 'Data')               # book node; first sheet 'Data'
    xl.write('time').write('conc').writeln()              # cursor verbs, active sheet
    xl.write([[0.0, 1.5], [1.0, 1.7]])                    # a block: one cell per element
    xl.data.Data.write('Total', 'Total')                  # node form; 'Total' = a style
    xl.write('x', bold=True, fill='yellow')               # keyword form (xlw methods)
    xl.formula('=SUM(B2:B3)', cached=3.2)                 # a formula cell
    chart = xl.chart('conc')                              # a Chart (xlscatter): chart.add_series(...)
    xl.save()                                             # the active book; save('all'), save('name')
    book = xl.open(r'data/results.xlsx')                  # read a file; saved to results_xlw.xlsx
    book_values(book)('Data!$A$2:$A$9')                   # cell values of a range, for charts
    build_parts(book)                                     # the (part name, text) pairs of a book, as saved
    Node form takes the style as positional pairs: sheet.write(v, 'bold', True). Style properties:
    font sz bold italic underline strikethrough fill color halign valign numfmt wrap indent shrink
    rotation border bcolor (see xlformat). Read a cell: sheet.cell(3, 4), sheet.cell(3, 4, 'style'),
    sheet.cell(3, 4, 'formula'). Cursor: sheet.kvr('priv').kvr('cursor'). What a read could not
    map: book.kvr('priv').kvr('unmapped'). Verbs: write formula writeln nl blankRow move gridlines
    newsheet newstyle border activate save chart. Errors: XlwNoBook, XlwNoSheet, XlwBadArg (XlwError).
    A sheet or book name equal to a method name (count, keys, type, write ...) is refused.

VERSION  M01 m01.v01 (2026-11-06): xlw4, rebuilt from xlw m02.v02 for the same interface; pure
         Python in 8 modules and no compiled code, and the styles file became a built-in table.
"""

import os

from xlbook import Book, Root
from xlerrors import XlwBadArg, XlwError, XlwNoBook, XlwNoSheet
from xlformat import resolve
from xlpack import book_values, build_parts, read_package
from xltext import safe_name

__all__ = ['xlw', 'XlwError', 'XlwNoBook', 'XlwNoSheet', 'XlwBadArg', 'book_values', 'build_parts']

VERBS = ('write', 'formula', 'writeln', 'nl', 'blankRow', 'move', 'gridlines', 'border', 'chart',
         'newsheet')


class xlw:
    """The writer. Holds the tree; its methods act on the active book and sheet and return the
    xlw object so calls chain, except chart and newsheet, which return what they made. A book is
    reached as an attribute: xl.data (the book 'data'), and a sheet as xl.data.Sheet1."""

    def __init__(me):
        me.root = Root()

    @staticmethod
    def read(filename, name=None):
        """A new xlw holding the file as its active book: xl = xlw.read('data/results.xlsx')."""
        xl = xlw()
        xl.open(filename, name)
        return xl

    def __getattr__(me, name):
        """A verb of the active sheet (newsheet: of the active book), or the book called `name`.
        A verb returns this object so calls chain, except chart and newsheet, which return what
        they made. The verb is stored on the object at the first use, and finds the active sheet
        again at every call, so it keeps working after another sheet or book is activated."""
        if name.startswith('_') or name == 'root':
            raise AttributeError(name)
        if name not in VERBS:
            return me.root.named(name)
        root, kind = me.root, 'book' if name == 'newsheet' else 'sheet'
        if name in ('chart', 'newsheet'):
            verb = lambda *args, **keywords: getattr(root.target(kind), name)(*args, **keywords)
        else:
            verb = lambda *args, **keywords: (getattr(root.target(kind), name)(*args, **keywords), me)[1]
        me.__dict__[name] = verb
        return verb

    def newbook(me, filename, *sheets):
        """A new book, made active. The extension .xlsx is added when missing. Returns the book
        node; cache it. Optional names create sheets."""
        folder, base = os.path.split(str(filename))
        base = base[:-5] if base.lower().endswith('.xlsx') else base
        key = safe_name(base)
        book = me.root.add(key, Book(os.path.join(folder, base + '.xlsx')))
        book.activate()
        if sheets:
            book.newsheet(*sheets)
        return book

    def open(me, filename, name=None):
        """Read an .xlsx into the tree (cells, styles, XY charts) and return its book node. It is
        saved to <name>_xlw.xlsx beside the source, never over it; what was not read is listed in
        book.priv.unmapped."""
        folder = os.path.dirname(os.path.abspath(filename))
        base = os.path.splitext(os.path.basename(filename))[0]
        book = me.newbook(os.path.join(folder, (name or base) + '_xlw'))
        notes = {}
        read_package(filename, book, notes)
        book.kvr('priv').kvw('unmapped', list(notes))
        return book

    def newstyle(me, name, *pairs, **keywords):
        """A named style visible to every book: the pairs and keywords over an optional named
        base, as for write."""
        styles = me.root.kvr('priv').kvr('styles')
        styles[safe_name(name)] = resolve([styles], pairs, keywords)
        return me

    def activate(me, target):
        """Make a book active, by name or by node."""
        book = me.root.named(target) if isinstance(target, str) else target
        if not hasattr(book, 'type') or book.type() != 'book':
            raise XlwBadArg('activate takes a book, by name or by node')
        book.activate()
        return me

    def save(me, target=None):
        """Save the active book; or save('all'); or a book by name or node; or a list of those."""
        if target is None:
            me.root.save()
        elif isinstance(target, (list, tuple)):
            for item in target:
                me.save(item)
        elif isinstance(target, str) and target.lower() == 'all':
            for book in me.root.nodes():
                if book.type() == 'book':
                    book.save()
        else:
            (me.root.named(target) if isinstance(target, str) else target).save()
        return me
