"""
xlreader -- read an .xlsx into the xlw tkv tree: cells, styles and XY charts.

Why
    The same tree that xlw builds can be filled from a workbook, so a workbook can be
    read, changed and written again, and, more to the point, the workbooks Excel itself
    writes become test material: a chart read from an Excel file is a chart node, which
    xlw can write and svgchart can draw.

Algorithm
    The package is unzipped once. Shared strings and the cell formats (cellXfs, each
    resolved against fonts, fills, borders and number formats into the same property
    dict xlw uses) are read first; each sheet is then streamed with iterparse and every
    cell becomes a sparse node holding 'val' and only the properties that differ from
    xlw's defaults. Each chart reached through a sheet's drawing is read into a chart
    node in the layout of chartdef.md: it is the inverse of xlchart.chart_part.
    Anything not mapped is collected in an 'unmapped' list (book.priv.unmapped), except
    the Excel extension noise (mc:AlternateContent, extLst, userShapes, chart style and
    colour parts, ink), which is skipped without comment.

Use
    xl = xlw()
    book = xl.open(r'data/results.xlsx')             # or  read_book(xl, path)
    sheet = book.Sheet1                              # a sheet, by its safe name
    sheet[3, 2].kvr('val')                           # a cell
    chart = sheet.kvr('priv').kvr('charts').nodes()[0]
    book.kvr('priv').kvr('unmapped')                 # what was not read

    The new book is saved to <name>_xlw.xlsx beside the source, never over it
    (change book.priv.fname to save elsewhere).

    A vertical alignment that a cell does not state is 'bottom' in Excel, while xlw's
    default is 'top'; cells read from a file therefore carry valign='bottom'.

Versions
    M01  m01.v01  2026-10-31  first version: cells, styles, drawings with XY charts.
"""

import os
import re
import zipfile
import xml.etree.ElementTree as ET

import xlchart
import xlstyle
from xlstyle import DEFAULTS

import xlw as xlwmodule

__all__ = ['read_book', 'read_chart_xml', 'EXCEL_THEME']

NS_MAIN = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
NS_REL = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
NS_PKG = '{http://schemas.openxmlformats.org/package/2006/relationships}'
NS_XDR = '{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}'
NS_A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
NS_C = '{http://schemas.openxmlformats.org/drawingml/2006/chart}'
NS_MC = '{http://schemas.openxmlformats.org/markup-compatibility/2006}'

# Theme colour slots 0-9 as the default Office theme has them (the workbook's own theme
# part is not parsed): lt1 dk1 lt2 dk2 accent1-6.
EXCEL_THEME = ('FFFFFF', '000000', 'E7E6E6', '44546A', '4472C4', 'ED7D31', 'A5A5A5',
               'FFC000', '5B9BD5', '70AD47')

BUILTIN_CODES = {0: '', 1: '0', 2: '0.00', 3: '#,##0', 4: '#,##0.00', 9: '0%',
                 10: '0.00%', 11: '0.00E+00', 14: 'mm-dd-yy', 15: 'd-mmm-yy',
                 16: 'd-mmm', 17: 'mmm-yy', 18: 'h:mm AM/PM', 19: 'h:mm:ss AM/PM',
                 20: 'h:mm', 21: 'h:mm:ss', 22: 'm/d/yy h:mm', 45: 'mm:ss',
                 46: '[h]:mm:ss', 47: 'mmss.0', 48: '##0.0E+0', 49: '@'}

# Top-level worksheet elements that are read, or that carry nothing the tree holds.
SHEET_KNOWN = ('sheetPr', 'dimension', 'sheetViews', 'sheetFormatPr', 'cols', 'sheetData',
               'pageMargins', 'pageSetup', 'headerFooter', 'drawing', 'extLst',
               'AlternateContent', 'printOptions', 'rowBreaks', 'colBreaks',
               'sheetProtection', 'phoneticPr', 'ignoredErrors')


def local(tag):
    return tag.rsplit('}', 1)[-1]


class Collector:
    """Unique messages about what was not read."""

    def __init__(me):
        me.items = []

    def add(me, message):
        if message not in me.items:
            me.items.append(message)


# ---------------------------------------------------------------------- colours --------
def rgb_of(text):
    """'FFRRGGBB' or 'RRGGBB' as RRGGBB."""
    return text[-6:].upper()


def sheet_color(element):
    """A spreadsheet colour element (<color>, <fgColor>) as RRGGBB, or '' when it cannot
    be mapped (indexed palette entries other than the system ones)."""
    if element is None:
        return ''
    if element.get('rgb'):
        return rgb_of(element.get('rgb'))
    if element.get('theme') is not None:
        slot = int(element.get('theme'))
        return EXCEL_THEME[slot] if slot < len(EXCEL_THEME) else ''
    if element.get('indexed') in ('64', '8'):
        return '000000'
    if element.get('indexed') == '9':
        return 'FFFFFF'
    return ''


def draw_color(parent):
    """The colour string (chartdef.md section 3) of the colour element inside `parent`
    (a solidFill, or an element that holds one); None when there is none."""
    if parent is None:
        return None, None
    element = None
    for child in parent:
        if local(child.tag) in ('srgbClr', 'schemeClr', 'sysClr', 'prstClr'):
            element = child
    if element is None:
        return None, None
    kind = local(element.tag)
    alpha = None
    alpha_el = element.find(NS_A + 'alpha')
    if alpha_el is not None:
        alpha = int(alpha_el.get('val')) / 1000
    if kind == 'srgbClr':
        return element.get('val').upper(), alpha
    if kind == 'schemeClr':
        text = 'theme:' + element.get('val')
        mod = element.find(NS_A + 'lumMod')
        off = element.find(NS_A + 'lumOff')
        if mod is not None or off is not None:
            text += ':' + (mod.get('val') if mod is not None else '')
            if off is not None:
                text += ':' + off.get('val')
        return text, alpha
    if kind == 'sysClr':
        text = 'sys:' + element.get('val')
        if element.get('lastClr'):
            text += ':' + element.get('lastClr').upper()
        return text, alpha
    return None, None


def fill_record(sp):
    """A fill record from a spPr (or None when the spPr states no fill)."""
    if sp is None:
        return None
    if sp.find(NS_A + 'noFill') is not None:
        return xlchart.rec(none=True)
    solid = sp.find(NS_A + 'solidFill')
    if solid is not None:
        color, alpha = draw_color(solid)
        return xlchart.rec(color=color, alpha=alpha)
    return None


def line_record(ln):
    """A line record from an <a:ln> element (or None)."""
    if ln is None:
        return None
    width = ln.get('w')
    fields = {'width': round(int(width) / xlchart.EMU_PER_POINT, 4) if width else None,
              'cap': ln.get('cap')}
    if ln.find(NS_A + 'noFill') is not None:
        fields['none'] = True
    solid = ln.find(NS_A + 'solidFill')
    if solid is not None:
        fields['color'] = draw_color(solid)[0]
    dash = ln.find(NS_A + 'prstDash')
    if dash is not None:
        fields['dash'] = dash.get('val')
    return xlchart.rec(**fields)


def font_record(rpr):
    """A font record from an <a:defRPr> or <a:rPr> (None when absent)."""
    if rpr is None:
        return None
    fields = {}
    if rpr.get('sz'):
        fields['height'] = int(rpr.get('sz')) / 100
    if rpr.get('b') is not None:
        fields['bold'] = rpr.get('b') in ('1', 'true')
    if rpr.get('i') is not None:
        fields['ital'] = rpr.get('i') in ('1', 'true')
    if rpr.get('u') is not None:
        fields['under'] = rpr.get('u') != 'none'
    latin = rpr.find(NS_A + 'latin')
    if latin is not None and not latin.get('typeface', '').startswith('+'):
        fields['name'] = latin.get('typeface')
    solid = rpr.find(NS_A + 'solidFill')
    if solid is not None:
        fields['color'] = draw_color(solid)[0]
    return xlchart.rec(**fields)


# ------------------------------------------------------------------------- styles ------
def read_styles(archive, report):
    """The property dict of every cell format (cellXfs), as the delta against DEFAULTS
    (a list, index = the s attribute of a cell)."""
    if 'xl/styles.xml' not in archive.namelist():
        return [{}]
    root = ET.fromstring(archive.read('xl/styles.xml'))
    codes = dict(BUILTIN_CODES)
    for fmt in root.iter(NS_MAIN + 'numFmt'):
        codes[int(fmt.get('numFmtId'))] = fmt.get('formatCode')
    fonts = []
    for font in root.iter(NS_MAIN + 'font'):
        info = {'font': (font.find(NS_MAIN + 'name').get('val')
                         if font.find(NS_MAIN + 'name') is not None else 'Calibri'),
                'sz': (float(font.find(NS_MAIN + 'sz').get('val'))
                       if font.find(NS_MAIN + 'sz') is not None else 11),
                'bold': font.find(NS_MAIN + 'b') is not None,
                'italic': font.find(NS_MAIN + 'i') is not None,
                'underline': font.find(NS_MAIN + 'u') is not None,
                'strikethrough': font.find(NS_MAIN + 'strike') is not None}
        color = sheet_color(font.find(NS_MAIN + 'color'))
        if color:
            info['color'] = color
        fonts.append(info)
    fills = []
    for fill in root.iter(NS_MAIN + 'fill'):
        pattern = fill.find(NS_MAIN + 'patternFill')
        color = ''
        if pattern is not None and pattern.get('patternType') == 'solid':
            color = sheet_color(pattern.find(NS_MAIN + 'fgColor'))
            if not color:
                report.add('a fill colour that is not RGB or theme was left out')
        fills.append(color)
    borders = []
    for border in root.iter(NS_MAIN + 'border'):
        triples = []
        colors = []
        for edge, tag in (('n', 'top'), ('s', 'bottom'), ('e', 'right'), ('w', 'left')):
            side = border.find(NS_MAIN + tag)
            if side is not None and side.get('style'):
                color = sheet_color(side.find(NS_MAIN + 'color')) or '000000'
                triples.append((edge, side.get('style'), color))
                colors.append(color)
        borders.append((tuple(triples), colors[0] if colors else '000000'))
    deltas = []
    xfs = root.find(NS_MAIN + 'cellXfs')
    for xf in ([] if xfs is None else xfs.findall(NS_MAIN + 'xf')):
        style = dict(DEFAULTS)
        style['valign'] = 'bottom'                     # Excel's default when not stated
        font_id = int(xf.get('fontId', 0))
        if font_id < len(fonts):
            style.update(fonts[font_id])
        fill_id = int(xf.get('fillId', 0))
        if fill_id < len(fills):
            style['fill'] = fills[fill_id]
        border_id = int(xf.get('borderId', 0))
        if border_id < len(borders):
            style['border'] = borders[border_id][0]
            style['bcolor'] = borders[border_id][1]
        code_id = int(xf.get('numFmtId', 0))
        if code_id in codes:
            style['numfmt'] = codes[code_id]
        elif code_id:
            report.add(f'built-in number format {code_id} has no code here; left out')
        align = xf.find(NS_MAIN + 'alignment')
        if align is not None:
            if align.get('horizontal'):
                style['halign'] = align.get('horizontal')
            if align.get('vertical'):
                style['valign'] = align.get('vertical')
            style['wrap'] = align.get('wrapText') in ('1', 'true')
            style['indent'] = int(align.get('indent', 0))
            style['shrink'] = align.get('shrinkToFit') in ('1', 'true')
            rotation = int(align.get('textRotation', 0))
            style['rotation'] = 90 - rotation if 90 < rotation < 255 else rotation
        for prop in xlstyle.BOOL_PROPS:
            style[prop] = bool(style[prop])
        for prop in xlstyle.NUMBER_PROPS:
            number = float(style[prop])
            style[prop] = int(number) if number.is_integer() else number
        deltas.append(xlstyle.style_delta(style))
    return deltas or [{}]


def read_strings(archive):
    if 'xl/sharedStrings.xml' not in archive.namelist():
        return []
    root = ET.fromstring(archive.read('xl/sharedStrings.xml'))
    strings = []
    for item in root.iter(NS_MAIN + 'si'):
        # plain text sits in <t>; rich text in <r><t> runs; phonetic hints (rPh) are skipped
        pieces = [t.text or '' for t in item.findall(NS_MAIN + 't')]
        for run in item.findall(NS_MAIN + 'r'):
            pieces += [t.text or '' for t in run.findall(NS_MAIN + 't')]
        strings.append(''.join(pieces))
    return strings


# --------------------------------------------------------------------------- sheets -----
def read_cells(archive, path, sheet, strings, deltas, report):
    """Stream one worksheet part into the sheet node; returns the grid-lines flag. Cells
    are read as they close; the top-level elements met on the way are checked against
    SHEET_KNOWN so that anything not read is reported."""
    formulas = 0
    grid = True
    depth = 0
    row_re = re.compile(r'([A-Z]+)(\d+)')
    for event, element in ET.iterparse(archive.open(path), events=('start', 'end')):
        name = local(element.tag)
        if event == 'start':
            depth += 1
            if depth == 2 and name not in SHEET_KNOWN:
                report.add(f'worksheet element {name} was not read')
            if name == 'sheetView' and element.get('showGridLines') in ('0', 'false'):
                grid = False
            continue
        depth -= 1
        if name == 'c':
            reference = row_re.match(element.get('r'))
            col = xlchart.letters2col(reference.group(1))
            row = int(reference.group(2))
            kind = element.get('t')
            raw = element.find(NS_MAIN + 'v')
            if element.find(NS_MAIN + 'f') is not None:
                formulas += 1
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
            delta = deltas[style] if style < len(deltas) else {}
            if value is not None or delta:
                cell = sheet.node(row, col)
                cell['val'] = xlw_blank(value)
                for prop, setting in delta.items():
                    cell[prop] = setting
            element.clear()
    if formulas:
        report.add(f'{formulas} formula cells: the cached values were read, not the formulas')
    return grid


def xlw_blank(value):
    return xlwmodule.BLANK if value is None else value


# ---------------------------------------------------------------------------- charts ----
def title_node(parent, name, element, default_rot):
    """Fill the Text node `name` of `parent` from a <c:title> element."""
    node = parent.node(name)
    text = None
    rich = element.find(f'{NS_C}tx/{NS_C}rich')
    if rich is not None:
        runs = []
        for run in rich.iter(NS_A + 'r'):
            props = {}
            rpr = run.find(NS_A + 'rPr')
            if rpr is not None:
                if rpr.get('baseline') not in (None, '0'):
                    props['baseline'] = int(rpr.get('baseline')) / 1000
                if rpr.get('b') is not None:
                    props['bold'] = rpr.get('b') in ('1', 'true')
                if rpr.get('i') is not None:
                    props['ital'] = rpr.get('i') in ('1', 'true')
                if rpr.get('u') not in (None, 'none'):
                    props['under'] = True
                if rpr.get('sz'):
                    props['height'] = int(rpr.get('sz')) / 100
            piece = run.find(NS_A + 't')
            runs.append((piece.text or '' if piece is not None else '', props))
        if runs:
            text = runs[0][0] if len(runs) == 1 and not runs[0][1] else runs
        body = rich.find(NS_A + 'bodyPr')
        if body is not None and body.get('rot') is not None:
            rot = int(body.get('rot')) / 60000
            if rot != default_rot:
                node['rot'] = rot
        font = font_record(rich.find(f'.//{NS_A}pPr/{NS_A}defRPr'))
        if font is not None:
            node['font'] = font
    else:
        # an automatic title has no rich text; its font is in txPr
        font = font_record(element.find(f'{NS_C}txPr//{NS_A}defRPr'))
        if font is not None and font.numEntries() > 0:
            node['font'] = font
    if text is not None:
        node['text'] = text
    overlay = element.find(NS_C + 'overlay')
    if overlay is not None and overlay.get('val') in ('1', 'true'):
        node['overlay'] = True
    layout = layout_record(element.find(NS_C + 'layout'))
    if layout is not None:
        node['layout'] = layout
    return node


def layout_record(element):
    if element is None:
        return None
    manual = element.find(NS_C + 'manualLayout')
    if manual is None:
        return None
    fields = {}
    for name in ('x', 'y', 'w', 'h'):
        child = manual.find(NS_C + name)
        if child is not None:
            fields[name] = float(child.get('val'))
    return xlchart.rec(**fields) if fields else None


def numbers_of(element):
    """A range string or a list of numbers from a numRef / numLit container."""
    reference = element.find(f'{NS_C}numRef/{NS_C}f')
    if reference is not None:
        return reference.text
    literal = element.find(NS_C + 'numLit')
    if literal is None:
        return None
    return [float(pt.find(NS_C + 'v').text) for pt in literal.findall(NS_C + 'pt')]


def read_series(group_series, series_node, axis, report):
    """Fill one series node from a <c:ser> element."""
    node = series_node
    tx = group_series.find(NS_C + 'tx')
    if tx is not None:
        literal = tx.find(NS_C + 'v')
        reference = tx.find(f'{NS_C}strRef/{NS_C}f')
        if literal is not None:
            node['label'] = literal.text or ''
        elif reference is not None:
            node['labelref'] = reference.text
    x_element = group_series.find(NS_C + 'xVal')
    y_element = group_series.find(NS_C + 'yVal')
    x = numbers_of(x_element) if x_element is not None else None
    y = numbers_of(y_element) if y_element is not None else None
    if x is None or y is None:
        report.add('a series whose x or y data is not a number range was left empty')
    node['x'] = x if x is not None else []
    node['y'] = y if y is not None else []
    if axis == 2:
        node['axis'] = 2
    sp = group_series.find(NS_C + 'spPr')
    if sp is not None and line_record(sp.find(NS_A + 'ln')) is not None:
        node['line'] = line_record(sp.find(NS_A + 'ln'))
    marker = group_series.find(NS_C + 'marker')
    if marker is not None:
        symbol = marker.find(NS_C + 'symbol')
        fields = {'symbol': symbol.get('val') if symbol is not None else None}
        size = marker.find(NS_C + 'size')
        if size is not None:
            fields['size'] = int(size.get('val'))
        msp = marker.find(NS_C + 'spPr')
        if msp is not None:
            fill = fill_record(msp)
            if fill is not None and fill.kvr('color'):
                fields['fill'] = fill.kvr('color')
            edge = line_record(msp.find(NS_A + 'ln'))
            if edge is not None:
                fields['linecolor'] = edge.kvr('color')
                fields['linewidth'] = edge.kvr('width')
        node['marker'] = xlchart.rec(**fields)
    smooth = group_series.find(NS_C + 'smooth')
    if smooth is not None:
        node['smooth'] = smooth.get('val') in ('1', 'true')
    labels = group_series.find(NS_C + 'dLbls')
    if labels is not None:
        read_labels(node.node('labels'), labels)
    trend = group_series.find(NS_C + 'trendline')
    if trend is not None:
        read_trend(node.node('trend'), trend)
    for element in group_series.findall(NS_C + 'errBars'):
        direction = element.find(NS_C + 'errDir')
        name = 'xerr' if direction is not None and direction.get('val') == 'x' else 'yerr'
        read_errbars(node.node(name), element)
    return node


def read_labels(node, element):
    def on(name):
        child = element.find(NS_C + name)
        return child is not None and child.get('val') in ('1', 'true')
    for leaf, tag in (('showy', 'showVal'), ('showx', 'showCatName'),
                      ('showname', 'showSerName'), ('showkey', 'showLegendKey')):
        if on(tag):
            node[leaf] = True
    position = element.find(NS_C + 'dLblPos')
    if position is not None:
        node['pos'] = position.get('val')
    fmt = element.find(NS_C + 'numFmt')
    if fmt is not None and fmt.get('sourceLinked') in ('0', 'false'):
        node['numfmt'] = fmt.get('formatCode')
    font = font_record(element.find(f'{NS_C}txPr//{NS_A}defRPr'))
    if font is not None:
        node['font'] = font


def read_trend(node, element):
    kind = element.find(NS_C + 'trendlineType')
    node['fit'] = kind.get('val') if kind is not None else 'linear'
    for tag, leaf in (('order', 'order'), ('period', 'period'), ('forward', 'forward'),
                      ('backward', 'backward'), ('intercept', 'intercept')):
        child = element.find(NS_C + tag)
        if child is not None:
            node[leaf] = float(child.get('val'))
    for tag, leaf in (('dispRSqr', 'rsq'), ('dispEq', 'eq')):
        child = element.find(NS_C + tag)
        if child is not None and child.get('val') in ('1', 'true'):
            node[leaf] = True
    name = element.find(NS_C + 'name')
    if name is not None:
        node['label'] = name.text or ''
    line = line_record(element.find(f'{NS_C}spPr/{NS_A}ln'))
    if line is not None:
        node['line'] = line
    label = element.find(NS_C + 'trendlineLbl')
    if label is not None:
        fmt = label.find(NS_C + 'numFmt')
        if fmt is not None:
            node['numfmt'] = fmt.get('formatCode')
        layout = layout_record(label.find(NS_C + 'layout'))
        if layout is not None:
            node['layout'] = layout
        font = font_record(label.find(f'{NS_C}txPr//{NS_A}defRPr'))
        if font is not None:
            node['font'] = font


def read_errbars(node, element):
    inverse = {value: key for key, value in xlchart.ERROR_MODES.items()}
    mode = element.find(NS_C + 'errValType')
    node['mode'] = inverse.get(mode.get('val'), 'fixed') if mode is not None else 'fixed'
    direction = element.find(NS_C + 'errBarType')
    if direction is not None:
        node['dir'] = direction.get('val')
    cap = element.find(NS_C + 'noEndCap')
    if cap is not None and cap.get('val') in ('1', 'true'):
        node['endcap'] = False
    value = element.find(NS_C + 'val')
    if value is not None:
        node['value'] = float(value.get('val'))
    for side in ('plus', 'minus'):
        child = element.find(NS_C + side)
        if child is not None:
            data = numbers_of(child)
            if data is not None:
                node[side] = data
    line = line_record(element.find(f'{NS_C}spPr/{NS_A}ln'))
    if line is not None:
        node['line'] = line


def read_axis(chart, name, element, other_name, secondary):
    """Fill axis node `name` from a <c:valAx>; where this axis crosses the other axis is
    stored on the OTHER node (chartdef.md section 6)."""
    node = chart.node(name)
    scaling = element.find(NS_C + 'scaling')
    if scaling is not None:
        for tag, leaf in (('logBase', 'log'), ('max', 'max'), ('min', 'min')):
            child = scaling.find(NS_C + tag)
            if child is not None:
                node[leaf] = float(child.get('val'))
        orientation = scaling.find(NS_C + 'orientation')
        if orientation is not None and orientation.get('val') == 'maxMin':
            node['reverse'] = True
    deleted = element.find(NS_C + 'delete')
    if deleted is not None and deleted.get('val') in ('1', 'true'):
        node['visible'] = False
    elif secondary and name == 'x2axis':
        node['visible'] = True
    for tag, leaf in (('majorGridlines', 'gridmajor'), ('minorGridlines', 'gridminor')):
        grid = element.find(NS_C + tag)
        if grid is not None:
            line = line_record(grid.find(f'{NS_C}spPr/{NS_A}ln'))
            node[leaf] = line if line is not None else xlchart.rec(color='D9D9D9')
        elif leaf == 'gridmajor' and not secondary:
            node[leaf] = xlchart.rec(none=True)
    title = element.find(NS_C + 'title')
    if title is not None:
        title_node(node, 'title', title, -90 if name in ('yaxis', 'y2axis') else 0)
    fmt = element.find(NS_C + 'numFmt')
    if fmt is not None and fmt.get('sourceLinked') in ('0', 'false'):
        node['numfmt'] = fmt.get('formatCode')
    for tag, leaf in (('majorTickMark', 'tickmajor'), ('minorTickMark', 'tickminor'),
                      ('tickLblPos', 'ticklabels'), ('crossBetween', 'between')):
        child = element.find(NS_C + tag)
        if child is not None:
            node[leaf] = child.get('val')
    for tag, leaf in (('majorUnit', 'major'), ('minorUnit', 'minor')):
        child = element.find(NS_C + tag)
        if child is not None:
            node[leaf] = float(child.get('val'))
    sp = element.find(NS_C + 'spPr')
    if sp is not None:
        line = line_record(sp.find(NS_A + 'ln'))
        if line is not None:
            node['line'] = line
    tx = element.find(NS_C + 'txPr')
    if tx is not None:
        font = font_record(tx.find(f'.//{NS_A}defRPr'))
        if font is not None:
            node['font'] = font
        body = tx.find(NS_A + 'bodyPr')
        if body is not None and body.get('rot') not in (None, '-60000000'):
            node['labelrot'] = int(body.get('rot')) / 60000
    other = chart.node(other_name)
    at = element.find(NS_C + 'crossesAt')
    crosses = element.find(NS_C + 'crosses')
    if at is not None:
        other['crossesat'] = float(at.get('val'))
    elif crosses is not None:
        default = 'max' if name == 'y2axis' else 'autoZero'
        if crosses.get('val') != default:
            other['crosses'] = crosses.get('val')
    return node


def read_chart_xml(data, sheet, name, report=None):
    """A chart node (under the sheet's private chart tree) from the bytes of a chart part."""
    report = report or Collector()
    root = ET.fromstring(data)
    chart = xlchart.new_chart(sheet, name)
    chart_el = root.find(NS_C + 'chart')
    plot = chart_el.find(NS_C + 'plotArea')
    groups = plot.findall(NS_C + 'scatterChart')
    for other in plot:
        tag = local(other.tag)
        if tag not in ('layout', 'scatterChart', 'valAx', 'spPr', 'extLst'):
            report.add(f'chart plot-area element {tag} was not read')
    if not groups:
        report.add('this chart has no XY scatter group; it was left empty')
    axes_by_id = {}
    for axis in plot.findall(NS_C + 'valAx'):
        axes_by_id[axis.find(NS_C + 'axId').get('val')] = axis
    if plot.find(NS_C + 'catAx') is not None:
        report.add('a category axis was not read')
    series_number = 0
    for group_index, group in enumerate(groups):
        style = group.find(NS_C + 'scatterStyle')
        if style is not None and group_index == 0:
            chart['style'] = style.get('val')
        ids = [item.get('val') for item in group.findall(NS_C + 'axId')]
        names = (('xaxis', 'yaxis') if group_index == 0 else ('x2axis', 'y2axis'))
        if len(ids) == 2 and ids[0] in axes_by_id and ids[1] in axes_by_id:
            read_axis(chart, names[0], axes_by_id[ids[0]], names[1], group_index > 0)
            read_axis(chart, names[1], axes_by_id[ids[1]], names[0], group_index > 0)
        ordered = sorted(group.findall(NS_C + 'ser'),
                         key=lambda item: int(item.find(NS_C + 'order').get('val')))
        for series_el in ordered:
            series_number += 1
            series = chart.kvr('series')
            read_series(series_el, series.node(f's{series_number}'), 2 if group_index else 1,
                        report)
    title = chart_el.find(NS_C + 'title')
    if title is not None:
        title_node(chart, 'title', title, 0)
    legend = chart_el.find(NS_C + 'legend')
    if legend is not None:
        read_legend(chart.node('legend'), legend)
    blanks = chart_el.find(NS_C + 'dispBlanksAs')
    if blanks is not None and blanks.get('val') != 'gap':
        chart['blanks'] = blanks.get('val')
    visible = chart_el.find(NS_C + 'plotVisOnly')
    if visible is not None and visible.get('val') in ('0', 'false'):
        chart['visibleonly'] = False
    plot_sp = plot.find(NS_C + 'spPr')
    plot_node = chart.node('plotarea')
    if plot_sp is not None:
        fill = fill_record(plot_sp)
        if fill is not None:
            plot_node['fill'] = fill
        line = line_record(plot_sp.find(NS_A + 'ln'))
        if line is not None:
            plot_node['line'] = line
    layout = layout_record(plot.find(NS_C + 'layout'))
    if layout is not None:
        plot_node['layout'] = layout
    area = chart.node('chartarea')
    area_sp = root.find(NS_C + 'spPr')
    if area_sp is not None:
        fill = fill_record(area_sp)
        if fill is not None:
            area['fill'] = fill
        line = line_record(area_sp.find(NS_A + 'ln'))
        if line is not None:
            area['line'] = line
    rounded = root.find(NS_C + 'roundedCorners')
    if rounded is not None and rounded.get('val') in ('1', 'true'):
        area['rounded'] = True
    area_font = font_record(root.find(f'{NS_C}txPr//{NS_A}defRPr'))
    if area_font is not None and area_font.numEntries() > 0:
        area['font'] = area_font
    for tag in ('view3D', 'floor', 'sideWall', 'backWall', 'pivotFmts'):
        if chart_el.find(NS_C + tag) is not None:
            report.add(f'chart element {tag} was not read')
    return chart


def read_legend(node, element):
    pos = element.find(NS_C + 'legendPos')
    if pos is not None:
        node['pos'] = pos.get('val')
    hidden = []
    for entry in element.findall(NS_C + 'legendEntry'):
        deleted = entry.find(NS_C + 'delete')
        if deleted is not None and deleted.get('val') in ('1', 'true'):
            hidden.append(int(entry.find(NS_C + 'idx').get('val')) + 1)
    if hidden:
        node['hide'] = hidden
    layout = layout_record(element.find(NS_C + 'layout'))
    if layout is not None:
        node['layout'] = layout
    overlay = element.find(NS_C + 'overlay')
    if overlay is not None and overlay.get('val') in ('1', 'true'):
        node['overlay'] = True
    sp = element.find(NS_C + 'spPr')
    if sp is not None:
        fill = fill_record(sp)
        if fill is not None:
            node['fill'] = fill
        line = line_record(sp.find(NS_A + 'ln'))
        if line is not None:
            node['line'] = line
    font = font_record(element.find(f'{NS_C}txPr//{NS_A}defRPr'))
    if font is not None:
        node['font'] = font


# --------------------------------------------------------------------------- the book ---
def read_drawing(archive, drawing_path, sheet, report, counter):
    """Read the charts of one drawing part into the sheet; returns the chart count."""
    rels_path = os.path.dirname(drawing_path) + '/_rels/' + os.path.basename(
        drawing_path) + '.rels'
    targets = {}
    if rels_path in archive.namelist():
        for rel in ET.fromstring(archive.read(rels_path)):
            targets[rel.get('Id')] = os.path.normpath(os.path.join(
                os.path.dirname(drawing_path), rel.get('Target'))).replace('\\', '/')
    root = ET.fromstring(archive.read(drawing_path))
    pictures = 0
    shapes = 0
    anchors = []
    for child in root:
        if local(child.tag) in ('twoCellAnchor', 'oneCellAnchor', 'absoluteAnchor'):
            anchors.append(child)
        elif local(child.tag) == 'AlternateContent':
            choice = child.find(NS_MC + 'Choice')       # the Fallback repeats the Choice
            if choice is not None:
                anchors.extend(item for item in choice if local(item.tag) in (
                    'twoCellAnchor', 'oneCellAnchor', 'absoluteAnchor'))
    for anchor in anchors:
        kind = local(anchor.tag)
        # Pictures, shapes and charts may sit anywhere under the anchor (a chart grouped
        # with a picture is anchor > grpSp > graphicFrame), so search the whole subtree.
        pictures += len(list(anchor.iter(NS_XDR + 'pic')))
        shapes += len(list(anchor.iter(NS_XDR + 'sp')))
        for chart_ref in anchor.iter(NS_C + 'chart'):
            part = targets.get(chart_ref.get(NS_REL + 'id'))
            if part is None or part not in archive.namelist():
                report.add('a chart relationship pointed at a missing part')
                continue
            counter[0] += 1
            chart = read_chart_xml(archive.read(part), sheet, f'chart{counter[0]}', report)
            if anchor.find(NS_XDR + 'graphicFrame') is None:
                report.add('a chart inside a shape group is placed by the whole group')
            if kind == 'twoCellAnchor':
                def number(parent, tag):
                    return int(anchor.find(f'{NS_XDR}{parent}/{NS_XDR}{tag}').text)
                chart['anchor'] = xlchart.rec(
                    col=number('from', 'col'), colOff=number('from', 'colOff'),
                    row=number('from', 'row'), rowOff=number('from', 'rowOff'),
                    col2=number('to', 'col'), colOff2=number('to', 'colOff'),
                    row2=number('to', 'row'), rowOff2=number('to', 'rowOff'))
    if pictures:
        report.add(f'{pictures} pictures in a drawing were not read')
    if shapes:
        report.add(f'{shapes} shapes in a drawing were not read')


def read_book(xl, filename, name=None):
    """Read an .xlsx into xl and return the new book node; what was not read is listed
    in book.priv.unmapped. The book's file name is <name>_xlw.xlsx beside the source."""
    filename = str(filename)
    report = Collector()
    base = os.path.splitext(os.path.basename(filename))[0]
    with zipfile.ZipFile(filename) as archive:
        names = archive.namelist()
        workbook = ET.fromstring(archive.read('xl/workbook.xml'))
        rels = {rel.get('Id'): rel.get('Target') for rel in ET.fromstring(
            archive.read('xl/_rels/workbook.xml.rels'))}
        strings = read_strings(archive)
        deltas = read_styles(archive, report)
        out_name = os.path.join(os.path.dirname(os.path.abspath(filename)),
                                (name or base) + '_xlw')
        book = xl.newbook(out_name)
        chart_counter = [0]
        for sheet_el in workbook.iter(NS_MAIN + 'sheet'):
            sheet_name = sheet_el.get('name')
            target = rels[sheet_el.get(NS_REL + 'id')]
            path = target.lstrip('/') if target.startswith('/') else 'xl/' + target
            sheet = xlwmodule.fwd_newsheet(book, sheet_name)
            grid = read_cells(archive, path, sheet, strings, deltas, report)
            sheet.kvw('showGrid', grid)
            rels_path = os.path.dirname(path) + '/_rels/' + os.path.basename(path) + '.rels'
            if rels_path in names:
                for rel in ET.fromstring(archive.read(rels_path)):
                    if rel.get('Type', '').endswith('/drawing'):
                        drawing = os.path.normpath(os.path.join(
                            os.path.dirname(path), rel.get('Target'))).replace('\\', '/')
                        read_drawing(archive, drawing, sheet, report, chart_counter)
        for part in names:
            if part.startswith('xl/') and local(part).startswith('pivot'):
                report.add('pivot tables were not read')
                break
    book.kvr('priv').kvw('unmapped', list(report.items))
    return book
