"""
gridcheck -- helpers that let the tests read a sheet's cell grid the way they read cells.

The suites for xlw, the reader and the model check what is in a sheet. The grid holds tuples
and a book-level text and style table (see xlsheet), so reading a cell takes a few steps;
these functions take them. They use only the public readers of xlsheet.
"""

import xlsheet


class Cell:
    """A cell as a small object: kvr('val') is its value (None for a blank cell), any other
    name is a style property (None when it has the default)."""

    def __init__(me, sheet, row, col):
        me.sheet = sheet
        me.row = row
        me.col = col

    def kvr(me, name):
        if name == 'val':
            return xlsheet.cell_value(me.sheet, me.row, me.col)
        return xlsheet.cell_style(me.sheet, me.row, me.col).get(name)


def at(sheet, row, col):
    """The cell at (row, col), or None when the grid has none there."""
    return Cell(sheet, row, col) if sheet.kvr('cells').kvr((row, col)) is not None else None


def ncells(sheet):
    """The number of cells in a sheet's grid."""
    return sheet.kvr('cells').icount()


def formula_table(sheet):
    """{(row, col): (markup, cached value, cached type)} of the formula cells of a sheet."""
    tables = xlsheet.tables_of(sheet)
    found = {}
    for row, col, cell in xlsheet.cell_list(sheet):
        if cell[0] == xlsheet.FML:
            found[(row, col)] = (xlsheet.formula_at(tables, cell[1][0]), cell[1][1], cell[1][2])
    return found


def cell_table(sheet):
    """{(row, col): (value, ((property, repr(setting)), ...))} of a sheet: value as
    cell_value gives it, the properties sorted."""
    table = {}
    for row, col, cell in xlsheet.cell_list(sheet):
        style = xlsheet.cell_style(sheet, row, col)
        table[(row, col)] = (xlsheet.cell_value(sheet, row, col),
                             tuple(sorted((key, repr(setting)) for key, setting in style.items())))
    return table
