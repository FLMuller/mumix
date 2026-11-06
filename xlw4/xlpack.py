"""
xlpack -- the .xlsx package: build the parts of a book and zip them, or unzip a file into a book.

Why
    An .xlsx is a zip of XML parts tied together by relationships. Everything that is about
    the package (which part names exist, how they point at each other, what goes in the
    workbook part) is here, so the codecs of the parts (xlcells, xlformat, xlscatter) stay about
    their own part, and the book model stays about editing.

Algorithm
    Out: build_parts(book) lists (name, text) in zip order: content types, relationships,
    workbook, styles, shared strings, one worksheet per sheet, and for a sheet with charts its
    relationships, its drawing and one part per chart. The worksheet text is assembled from
    the grid's own <sheetData>; a workbook holding a formula that has no cached value asks
    Excel to calculate on load. In: read_package() opens the zip once, resolves the
    relationships (a target is joined to the folder of the part that names it), reads the
    strings and styles into the book's tables, then each worksheet and the drawings it points to.
    The book is any object with the leaves of an xlbook Book (read through kvr) and a
    newsheet() method, so this module needs no model of its own.
    Cost: O(cells) plus the zip's deflate.

Use
    write_zip(filename, build_parts(book))               # the book's file
    read_package(filename, book, notes)               # fills the new, empty book; notes: dict
    book_values(book)(ref) -> the cell values of a range such as 'Data!$A$2:$A$9'
    A .xlsx made by Excel opens; pivot tables, pictures and shapes are not read and are
    named in `notes`.

VERSION  M01 m01.v01 (2026-11-06): first version; parts, relationships, zip, and the reader of the package.
"""

import os
import posixpath
import zipfile

from xlformat import read_styles, styles_xml
from xlscatter import Chart, drawing_xml, read_drawing
from xltext import parse_xml, tag, xml_text

__all__ = ['build_parts', 'write_zip', 'read_package', 'book_values']

DECLARATION = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
NS_MAIN = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
NS_REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NS_PKG = 'http://schemas.openxmlformats.org/package/2006/relationships'
CT = 'application/vnd.openxmlformats-officedocument.'


def relationships(items):
    """<Relationships> from (id, type, target) triples; the type is the part after /relationships/."""
    return tag('Relationships', *[
        tag('Relationship', Id=ident, Type=f'{NS_REL}/{kind}', Target=target)
        for ident, kind, target in items], xmlns=NS_PKG)


def content_types(sheets, drawings, charts):
    """[Content_Types].xml for the given counts of worksheets, drawings and charts."""
    overrides = [('/xl/workbook.xml', 'spreadsheetml.sheet.main+xml'),
                 ('/xl/styles.xml', 'spreadsheetml.styles+xml'),
                 ('/xl/sharedStrings.xml', 'spreadsheetml.sharedStrings+xml')]
    for count, folder, name, kind in ((sheets, 'worksheets', 'sheet', 'spreadsheetml.worksheet+xml'),
                                      (drawings, 'drawings', 'drawing', 'drawing+xml'),
                                      (charts, 'charts', 'chart', 'drawingml.chart+xml')):
        overrides += [(f'/xl/{folder}/{name}{n}.xml', kind) for n in range(1, count + 1)]
    return tag(
        'Types', tag('Default', Extension='rels',
                     ContentType='application/vnd.openxmlformats-package.relationships+xml'),
        tag('Default', Extension='xml', ContentType='application/xml'),
        *[tag('Override', PartName=name, ContentType=CT + kind) for name, kind in overrides],
        xmlns='http://schemas.openxmlformats.org/package/2006/content-types')


def workbook_xml(names, calculate):
    """workbook.xml; `calculate` asks Excel to calculate every formula on opening the file."""
    sheets = [tag('sheet', name=name, sheetId=n, **{'r:id': f'rId{n}'})
              for n, name in enumerate(names, 1)]
    calc = tag('calcPr', calcId=191029, fullCalcOnLoad=1) if calculate else ''
    spaces = {'xmlns': NS_MAIN, 'xmlns:r': NS_REL}
    return tag('workbook', tag('sheets', *sheets), calc, **spaces)


def shared_strings(strings):
    """sharedStrings.xml from the ordered list of distinct strings. The items are f-strings, not
    tag() calls: a workbook of text has thousands of them and they are all alike."""
    items = ''.join(f'<si><t xml:space="preserve">{xml_text(text)}</t></si>' for text in strings)
    return f'<sst xmlns="{NS_MAIN}" count="{len(strings)}" uniqueCount="{len(strings)}">{items}</sst>'


def sheet_xml(sheet, drawing):
    """The worksheet part of one sheet node; `drawing` adds the reference to its drawing."""
    data, columns = sheet.kvr('cells').to_xml()
    shown = sheet.kvr('showGrid') is not False
    view = tag('sheetViews', tag('sheetView', showGridLines=None if shown else 0, workbookViewId=0))
    return tag('worksheet', view, columns, data,
                          tag('drawing', **{'r:id': 'rId1'}) if drawing else '', xmlns=NS_MAIN,
                          **({'xmlns:r': NS_REL} if drawing else {}))


def chart_parts(book, sheets):
    """(parts, drawings, charts): the parts of the charts of the sheets, numbered through the
    whole book. A sheet with charts gets its chart parts, its relationships, its drawing and
    the drawing's relationships."""
    values, parts, number, drawing = book_values(book), [], 0, 0
    for position, sheet in enumerate(sheets, 1):
        charts = sheet.kvr('priv').kvr('charts')
        nodes = charts.nodes() if charts is not None else []
        if not nodes:
            continue
        drawing += 1
        frames, numbers = [], []
        for index, chart in enumerate(nodes):
            number += 1
            numbers.append(number)
            frames.append((f'Chart {number}', chart.corner(sheet.kvr('cells').extent()[1], index)))
            parts.append((f'xl/charts/chart{number}.xml', chart.to_xml(values)))
        parts += [(f'xl/worksheets/_rels/sheet{position}.xml.rels', relationships(
            [('rId1', 'drawing', f'../drawings/drawing{drawing}.xml')])),
            (f'xl/drawings/drawing{drawing}.xml', drawing_xml(frames)),
            (f'xl/drawings/_rels/drawing{drawing}.xml.rels', relationships(
                [(f'rId{n}', 'chart', f'../charts/chart{chart_number}.xml')
                 for n, chart_number in enumerate(numbers, 1)]))]
    return parts, drawing, number


def build_parts(book):
    """All parts of a book as a list of (part name, text) in zip order."""
    priv = book.kvr('priv')
    tables = priv.kvr('tables')
    sheets = [book.kvr(key) for key in priv.kvr('sheetkeys')]
    calculate = bool(tables.formulas) and any(sheet.kvr('cells').needs_calc() for sheet in sheets)
    extra, drawings, charts = chart_parts(book, sheets)
    drawn = {name for name, _ in extra if name.startswith('xl/worksheets/_rels/')}
    count = len(sheets)
    sheet_rels = [(f'rId{n}', 'worksheet', f'worksheets/sheet{n}.xml') for n in range(1, count + 1)]
    parts = [('[Content_Types].xml', content_types(count, drawings, charts)),
             ('_rels/.rels', relationships([('rId1', 'officeDocument', 'xl/workbook.xml')])),
             ('xl/workbook.xml', workbook_xml(priv.kvr('sheets'), calculate)),
             ('xl/_rels/workbook.xml.rels', relationships(
                 sheet_rels + [(f'rId{count + 1}', 'styles', 'styles.xml'),
                               (f'rId{count + 2}', 'sharedStrings', 'sharedStrings.xml')])),
             ('xl/styles.xml', styles_xml(tables.xfs)),
             ('xl/sharedStrings.xml', shared_strings(tables.texts))]
    parts += [(f'xl/worksheets/sheet{n}.xml',
               sheet_xml(sheet, f'xl/worksheets/_rels/sheet{n}.xml.rels' in drawn))
              for n, sheet in enumerate(sheets, 1)]
    return parts + extra


def write_zip(filename, parts):
    """Write the parts (name, text) to an .xlsx: UTF-8, deflate, the folder made when missing."""
    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
    with zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, text in parts:
            archive.writestr(name, (DECLARATION + text).encode('utf-8'))


def book_values(book):
    """A function ref -> list of cell values (row-major) for a chart's data reference
    ('Sheet!$A$2:$A$10'); [] for a reference that names no sheet of the book."""
    priv = book.kvr('priv')
    key_of = dict(zip(priv.kvr('sheets'), priv.kvr('sheetkeys')))

    def values(reference):
        parsed = Chart.parse_ref(reference)
        if parsed is None or parsed[0] not in key_of:
            return []
        name, row1, col1, row2, col2 = parsed
        grid = book.kvr(key_of[name]).kvr('cells')
        return [grid.read(row, col) for row in range(row1, row2 + 1)
                for col in range(col1, col2 + 1)]
    return values


# ------------------------------------------------------------------------- read ------
def targets_of(files, part):
    """{id: (kind, part path)} of the relationships of `part` ('xl/workbook.xml'): a target is
    joined to the folder of the part; {} when the part has no relationships. `files` is
    {part name: bytes}."""
    folder, base = posixpath.split(part)
    data = files.get(f'{folder}/_rels/{base}.rels')
    return {item.get('Id'): (item.get('Type', '').rsplit('/', 1)[-1],
                             posixpath.normpath(posixpath.join(folder, item.get('Target'))).lstrip('/'))
            for item in parse_xml(data)} if data else {}


def read_package(filename, book, notes):
    """Fill the new, empty `book` from an .xlsx file; what is not read goes to the dict `notes`.
    The zip is read once into a dict of its parts, so every later step is a lookup."""
    with zipfile.ZipFile(filename) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    rels = targets_of(files, 'xl/workbook.xml')
    styles = files.get('xl/styles.xml')
    tables = book.kvr('priv').kvr('tables')
    remap = tables.load(tables.read_texts(files.get('xl/sharedStrings.xml')),
                        read_styles(parse_xml(styles), notes) if styles else [{}])
    for element in parse_xml(files['xl/workbook.xml']).iter('sheet'):
        path = rels[element.get('id')][1]
        sheet = book.newsheet(element.get('name'))
        sheet.kvw('showGrid', sheet.kvr('cells').from_xml(files[path], remap, notes))
        for kind, drawing in targets_of(files, path).values():
            if kind == 'drawing':
                targets = {ident: found for ident, (_, found) in targets_of(files, drawing).items()}
                read_drawing(files[drawing], targets, files.get, sheet.chart, notes)
    if any(name.startswith('xl/') and posixpath.basename(name).startswith('pivot') for name in files):
        notes['pivot tables were not read'] = True
