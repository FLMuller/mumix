"""
xlparts -- the OOXML packaging parts of an .xlsx, as text, and the zip writer.

Why
    An .xlsx is a zip of XML parts. The parts that carry no cell data (content types,
    relationships, the workbook, the shared-string table) are small templates; they
    are kept together here so the exact text that Excel accepted is in one place.
    The templates are those of xlw.m v1.19, plus the drawing and chart plumbing as
    Excel itself writes it (read from workbooks saved by Excel 16).

Use
    parts = KV()                                    # insertion order = zip order
    parts.kvw('[Content_Types].xml', content_types(n_sheets, n_drawings, n_charts))
    parts.kvw('_rels/.rels', root_rels())
    ...
    write_zip(r'out\book.xlsx', parts)

    A part name is the path inside the zip. The parts a book needs: [Content_Types].xml,
    _rels/.rels, xl/workbook.xml, xl/_rels/workbook.xml.rels, xl/styles.xml,
    xl/sharedStrings.xml, xl/worksheets/sheetN.xml; and for a sheet with charts also
    xl/worksheets/_rels/sheetN.xml.rels, xl/drawings/drawingK.xml,
    xl/drawings/_rels/drawingK.xml.rels and xl/charts/chartM.xml.

Versions
    M01  m01.v01  2026-10-31  ported from xlw.m v1.19; drawing and chart parts added.
"""

import os
import zipfile

from xlstyle import xml_escape

__all__ = ['XML_HEAD', 'NS_MAIN', 'NS_REL', 'col2letter', 'content_types', 'root_rels',
           'workbook_part', 'workbook_rels', 'shared_strings', 'sheet_rels',
           'drawing_part', 'drawing_rels', 'write_zip']

XML_HEAD = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
NS_MAIN = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
NS_REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NS_PKG = 'http://schemas.openxmlformats.org/package/2006/relationships'
NS_XDR = 'http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing'
NS_DML = 'http://schemas.openxmlformats.org/drawingml/2006/main'
NS_CHART = 'http://schemas.openxmlformats.org/drawingml/2006/chart'
CT_PREFIX = 'application/vnd.openxmlformats-officedocument.'


def col2letter(number):
    """Bijective base 26: 1 = A, 26 = Z, 27 = AA."""
    letters = ''
    while number > 0:
        number, rest = divmod(number - 1, 26)
        letters = chr(65 + rest) + letters
    return letters


def content_types(n_sheets, n_drawings=0, n_charts=0):
    sheets = ''.join(f'<Override PartName="/xl/worksheets/sheet{n}.xml" '
                     f'ContentType="{CT_PREFIX}spreadsheetml.worksheet+xml"/>'
                     for n in range(1, n_sheets + 1))
    drawings = ''.join(f'<Override PartName="/xl/drawings/drawing{n}.xml" '
                       f'ContentType="{CT_PREFIX}drawing+xml"/>'
                       for n in range(1, n_drawings + 1))
    charts = ''.join(f'<Override PartName="/xl/charts/chart{n}.xml" '
                     f'ContentType="{CT_PREFIX}drawingml.chart+xml"/>'
                     for n in range(1, n_charts + 1))
    return (XML_HEAD
            + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/'
            'content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-'
            'package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            f'<Override PartName="/xl/workbook.xml" '
            f'ContentType="{CT_PREFIX}spreadsheetml.sheet.main+xml"/>'
            f'<Override PartName="/xl/styles.xml" '
            f'ContentType="{CT_PREFIX}spreadsheetml.styles+xml"/>'
            f'<Override PartName="/xl/sharedStrings.xml" '
            f'ContentType="{CT_PREFIX}spreadsheetml.sharedStrings+xml"/>'
            + sheets + drawings + charts + '</Types>')


def root_rels():
    return (XML_HEAD + f'<Relationships xmlns="{NS_PKG}">'
            f'<Relationship Id="rId1" Type="{NS_REL}/officeDocument" '
            'Target="xl/workbook.xml"/></Relationships>')


def workbook_part(sheet_names):
    sheets = ''.join(f'<sheet name="{xml_escape(name)}" sheetId="{n}" r:id="rId{n}"/>'
                     for n, name in enumerate(sheet_names, start=1))
    return (XML_HEAD + f'<workbook xmlns="{NS_MAIN}" xmlns:r="{NS_REL}">'
            f'<sheets>{sheets}</sheets></workbook>')


def workbook_rels(n_sheets):
    sheets = ''.join(f'<Relationship Id="rId{n}" Type="{NS_REL}/worksheet" '
                     f'Target="worksheets/sheet{n}.xml"/>'
                     for n in range(1, n_sheets + 1))
    return (XML_HEAD + f'<Relationships xmlns="{NS_PKG}">' + sheets
            + f'<Relationship Id="rId{n_sheets + 1}" Type="{NS_REL}/styles" '
            'Target="styles.xml"/>'
            + f'<Relationship Id="rId{n_sheets + 2}" Type="{NS_REL}/sharedStrings" '
            'Target="sharedStrings.xml"/></Relationships>')


def shared_strings(strings):
    """sharedStrings.xml from the ordered list of distinct strings (index = position).
    An all-numeric workbook has none and gets an empty <sst>."""
    items = ''.join(f'<si><t xml:space="preserve">{xml_escape(text)}</t></si>'
                    for text in strings)
    return (XML_HEAD + f'<sst xmlns="{NS_MAIN}" count="{len(strings)}" '
            f'uniqueCount="{len(strings)}">{items}</sst>')


def sheet_rels(drawing_number):
    """The relationships of a worksheet that holds a drawing (always rId1)."""
    return (XML_HEAD + f'<Relationships xmlns="{NS_PKG}">'
            f'<Relationship Id="rId1" Type="{NS_REL}/drawing" '
            f'Target="../drawings/drawing{drawing_number}.xml"/></Relationships>')


def anchor_xml(index, name, anchor):
    """One twoCellAnchor holding the chart graphic frame with relationship rId<index>.
    anchor = (col, colOff, row, rowOff, col2, colOff2, row2, rowOff2), zero-based
    cells and EMU offsets."""
    col, col_off, row, row_off, col2, col_off2, row2, row_off2 = anchor
    return ('<xdr:twoCellAnchor>'
            f'<xdr:from><xdr:col>{col}</xdr:col><xdr:colOff>{col_off}</xdr:colOff>'
            f'<xdr:row>{row}</xdr:row><xdr:rowOff>{row_off}</xdr:rowOff></xdr:from>'
            f'<xdr:to><xdr:col>{col2}</xdr:col><xdr:colOff>{col_off2}</xdr:colOff>'
            f'<xdr:row>{row2}</xdr:row><xdr:rowOff>{row_off2}</xdr:rowOff></xdr:to>'
            '<xdr:graphicFrame macro="">'
            f'<xdr:nvGraphicFramePr><xdr:cNvPr id="{index + 1}" '
            f'name="{xml_escape(name)}"/><xdr:cNvGraphicFramePr/></xdr:nvGraphicFramePr>'
            '<xdr:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/></xdr:xfrm>'
            '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/'
            f'drawingml/2006/chart"><c:chart r:id="rId{index}"/></a:graphicData>'
            '</a:graphic></xdr:graphicFrame><xdr:clientData/></xdr:twoCellAnchor>')


def drawing_part(charts):
    """xl/drawings/drawingK.xml for a list of (name, anchor) pairs; chart n of the
    list is relationship rId<n>."""
    frames = ''.join(anchor_xml(n, name, anchor)
                     for n, (name, anchor) in enumerate(charts, start=1))
    return (XML_HEAD + f'<xdr:wsDr xmlns:xdr="{NS_XDR}" xmlns:a="{NS_DML}" '
            f'xmlns:r="{NS_REL}" xmlns:c="{NS_CHART}">{frames}</xdr:wsDr>')


def drawing_rels(chart_numbers):
    """Relationships of a drawing: rId<n> -> ../charts/chart<chart_numbers[n-1]>.xml."""
    items = ''.join(f'<Relationship Id="rId{n}" Type="{NS_REL}/chart" '
                    f'Target="../charts/chart{number}.xml"/>'
                    for n, number in enumerate(chart_numbers, start=1))
    return XML_HEAD + f'<Relationships xmlns="{NS_PKG}">{items}</Relationships>'


def write_zip(filename, parts):
    """Write the parts (a kv: part name -> text, in zip order) to an .xlsx file.
    UTF-8 bytes, deflate at the default level, no temporary files."""
    folder = os.path.dirname(os.path.abspath(filename))
    os.makedirs(folder, exist_ok=True)
    with zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in parts.keys():
            archive.writestr(name, parts.kvr(name).encode('utf-8'))
