"""
xlscatter -- XY scatter charts: the chart definition, and the chart and drawing XML both ways.

Why
    A chart is a Node tree (layout in chartdef.md, kept in mumix/xlw and shared with svgchart),
    so it is edited like the rest of the document, drawn by svgchart from the same definition,
    and converted to and from the Excel chart part here. Writing and reading sit together because each is the inverse of the other,
    and they share the colour, line, fill, font and layout records.

Algorithm
    Chart.to_xml() walks the chart node once and writes the elements in the order Excel demands
    (chartdef.md section 6): colours, lines, fills and fonts are small records (Node); the nodes
    hold the groups; anything absent takes its default, so a chart that sets only series and axis
    titles is complete. Data are ranges ('Sheet!$A$2:$A$100'); their values come through a
    function the caller passes, to write the number cache that viewers without a calculation
    engine need. Chart.from_xml() is the inverse: it fills the chart from the XML, mapping leaf by
    leaf through small tables (element, leaf, converter), so a setting is named once on the way
    in. drawing_xml() and read_drawing() do the same for the anchors that place the charts on a
    sheet. Anything not mapped goes to the dict `notes`.

Use
    chart = xl.chart('conc')                          # a Chart, on the active sheet
    chart.title.text = 'Concentration'                # leaves and nodes by attribute (chartdef.md)
    chart.xaxis.title.text = 'time (s)'
    chart.add_series(x=chart.ref('Data', 2, 1, 100, 1), y='Data!$B$2:$B$100', label='A',
                     line=dict(color='C00000', width=2), marker=dict(symbol='none'))
    chart.place(col=4, row=1, ncols=9, nrows=18)      # zero-based top-left, size in cells
    chart.ref('Data', 2, 1, 100, 1)  ->  'Data!$A$2:$A$100'
    chart.parse_ref("'My Sheet'!$B$2:$B$9")  ->  ('My Sheet', 2, 2, 9, 2)
    chart.rec(color='C00000', width=2)                # a record, for line, marker, fill, font, layout
    chart.to_xml(values) -> the chart part;  chart.from_xml(data, notes) fills the chart
    chart.corner(ncols, index) -> the 8-tuple anchor
    drawing_xml(frames) -> the drawing part;  read_drawing(data, targets, read_part, make_chart, notes)

VERSION  M01 m01.v01 (2026-11-06): first version; definition, writer and reader in one module,
         the XML built with xltext.tag and read through tables.
"""

import math
import re

from xltext import column, parse_xml, tag, xml_text
from xltree import Node, rec

__all__ = ['Chart', 'drawing_xml', 'read_drawing']

PALETTE = ('4472C4', 'ED7D31', 'A5A5A5', 'FFC000', '5B9BD5', '70AD47')
EMU_PER_POINT = 12700
AXIS_IDS = (500000001, 500000002, 500000003, 500000004)
REF_PATTERN = re.compile(r"^(?:'((?:[^']|'')+)'|([^'!]+))!\$?([A-Z]{1,3})\$?(\d+)"
                         r"(?::\$?([A-Z]{1,3})\$?(\d+))?$")
ERROR_MODES = {'fixed': 'fixedVal', 'percentage': 'percentage', 'stddev': 'stdDev',
               'stderr': 'stdErr', 'custom': 'cust'}
ANCHOR_FIELDS = ('col', 'colOff', 'row', 'rowOff', 'col2', 'colOff2', 'row2', 'rowOff2')
NS = {'xdr': 'http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
ANCHORS = ('twoCellAnchor', 'oneCellAnchor', 'absoluteAnchor')


class Chart(Node):
    """One XY scatter chart: a Node whose leaves and children follow chartdef.md. The methods
    below are the only names a leaf cannot have."""

    def __init__(me, name=''):
        Node.__init__(me, 'chart', None, name)
        me.node('series')

    @staticmethod
    def rec(**fields):
        """A record (see xltree.rec): None values are left out."""
        return rec(**fields)

    @staticmethod
    def ref(sheet, row1, col1, row2=None, col2=None):
        """A data reference: ref('Data', 2, 1, 100, 1) -> 'Data!$A$2:$A$100'. A sheet name with
        anything but letters, digits and _ is quoted, with ' doubled."""
        name = sheet if re.fullmatch(r'[A-Za-z0-9_]+', sheet) else "'" + sheet.replace("'", "''") + "'"
        last = '' if row2 is None else f':${column(col2)}${row2}'
        return f'{name}!${column(col1)}${row1}{last}'

    @staticmethod
    def parse_ref(text):
        """(sheet, row1, col1, row2, col2) for a reference, or None when it is not one."""
        found = REF_PATTERN.match(text.strip()) if isinstance(text, str) else None
        if found is None:
            return None
        quoted, plain, col1, row1, col2, row2 = found.groups()
        sheet = quoted.replace("''", "'") if quoted is not None else plain
        return sheet, int(row1), column(col1), int(row2 or row1), column(col2 or col1)

    def add_series(me, x, y, label=None, **options):
        """Add a series; returns its node. x and y are ranges ('Sheet!$A$2:$A$9') or lists of
        numbers. Options: labelref, axis (1 or 2), smooth, and the records line and marker (dicts
        are accepted); trend, xerr, yerr and labels are nodes, set on the returned node."""
        series = me.node('series')
        node = series.node(f's{series.count() + 1}')
        node['x'], node['y'], node['label'] = x, y, label
        for key, value in options.items():
            node[key] = rec(**value) if isinstance(value, dict) else value
        return node

    def place(me, col, row, ncols=9, nrows=18):
        """Put the chart on the sheet: zero-based top-left cell and its size in cells."""
        me['anchor'] = rec(col=col, colOff=0, row=row, rowOff=0, col2=col + ncols, colOff2=0,
                           row2=row + nrows, rowOff2=0)
        return me

    def corner(me, ncols=0, index=0):
        """The 8-tuple anchor (col, colOff, row, rowOff, col2, colOff2, row2, rowOff2). Without
        an anchor the chart goes beside the data: one blank column right of the last used column,
        and below the previous chart of the sheet (`index`)."""
        anchor = me.kvr('anchor')
        if anchor is None:
            return (ncols + 1, 0, 1 + index * 20, 0, ncols + 10, 0, 19 + index * 20, 0)
        values = [anchor.kvr(name) for name in ANCHOR_FIELDS]
        values[4] = (values[0] or 0) + 9 if values[4] is None else values[4]
        values[6] = (values[2] or 0) + 18 if values[6] is None else values[6]
        return tuple(int(value or 0) for value in values)

    def to_xml(me, values=None):
        """The text of xl/charts/chartN.xml. `values(ref)` returns the cell values of a range
        (for the number caches); without it the caches are empty."""
        return chart_xml(me, values)

    def from_xml(me, data, notes):
        """Fill the chart from the bytes of a chart part; what is not mapped goes to the dict `notes`."""
        read_chart(data, me, notes)


# ---------------------------------------------------------------- small readers ------
def truth(text):
    """An OOXML boolean attribute as a bool."""
    return text in ('1', 'true')



def get(node, name, default=None):
    """A leaf or child node of a chart node, or `default` when the node or the name is absent."""
    value = None if node is None else node.kvr(name)
    return default if value is None else value


def field(record, name, default=None):
    """A field of a record, or `default` (a record is a Node; the call reads like get)."""
    return get(record, name, default)


# ------------------------------------------------------------------ DrawingML out -----
def emu(points):
    """Points to EMU (12700 to the point)."""
    return int(round(float(points) * EMU_PER_POINT))


def color_xml(color, alpha=None):
    """The colour element of a colour string: RRGGBB, theme:NAME[:lumMod[:lumOff]] or
    sys:NAME[:RRGGBB] (chartdef.md section 3)."""
    kind, *parts = color.split(':')
    opacity = [tag('a:alpha', val=int(alpha * 1000))] if alpha is not None else []
    if kind == 'theme':
        mods = [tag(f'a:{name}', val=part) for name, part in zip(('lumMod', 'lumOff'), parts[1:])
                if part]
        return tag('a:schemeClr', *mods, *opacity, val=parts[0])
    if kind == 'sys':
        return tag('a:sysClr', val=parts[0], lastClr=parts[1] if len(parts) > 1 else None)
    return tag('a:srgbClr', *opacity, val=color.upper())


def solid_xml(color, alpha=None):
    """A solid fill of a colour string."""
    return tag('a:solidFill', color_xml(color, alpha))


def fill_xml(record, default=None):
    """A fill record as noFill or solidFill; `default` is the colour (or 'none')."""
    color = field(record, 'color', default)
    if field(record, 'none') or color in (None, 'none'):
        return tag('a:noFill')
    return solid_xml(color, field(record, 'alpha'))


def line_xml(record, default_color=None, default_width=0.75, default_dash=None):
    """An <a:ln> from a line record; a record with none=True, or no colour, gives no line."""
    color = field(record, 'color', default_color)
    attrs = {'w': emu(field(record, 'width', default_width)), 'cap': field(record, 'cap')}
    if field(record, 'none') or color is None:
        return tag('a:ln', tag('a:noFill'), **attrs)
    dash = field(record, 'dash', default_dash)
    return tag('a:ln', solid_xml(color), tag('a:prstDash', val=dash) if dash else '',
               tag('a:round'), **attrs)


def shape_xml(fill=None, line=None):
    """<c:spPr> with the given fill and line text and an empty effect list."""
    return tag('c:spPr', fill or '', line or '', tag('a:effectLst'))


def font_values(record, name='Calibri', height=10.0, color='595959'):
    """A font record merged over the defaults, as a dict."""
    return {'name': field(record, 'name', name), 'height': field(record, 'height', height),
            'color': field(record, 'color', color), 'bold': field(record, 'bold', False),
            'ital': field(record, 'ital', False), 'under': field(record, 'under', False)}


def defrpr_xml(font):
    """<a:defRPr> of a font dict."""
    return tag('a:defRPr', solid_xml(font['color']), tag('a:latin', typeface=font['name']),
               sz=int(round(float(font['height']) * 100)), b=bool(font['bold']),
               i=bool(font['ital']), u='sng' if font['under'] else 'none', strike='noStrike',
               kern=1200, baseline=0)


def body_xml(rotation=None):
    """<a:bodyPr>; rotation in degrees (None: the automatic angle)."""
    rot = -60000000 if rotation is None else int(round(float(rotation) * 60000))
    return tag('a:bodyPr', rot=rot, spcFirstLastPara=1, vertOverflow='ellipsis', vert='horz',
               wrap='square', anchor='ctr', anchorCtr=1)


def txpr_xml(font, rotation=None):
    """<c:txPr>: the text properties of a font dict."""
    return tag('c:txPr', body_xml(rotation), tag('a:lstStyle'),
               tag('a:p', tag('a:pPr', defrpr_xml(font)), tag('a:endParaRPr', lang='en-US')))


def layout_xml(record):
    """<c:layout>, empty or with the manual position of a layout record."""
    if record is None:
        return tag('c:layout')
    edges = [tag('c:xMode', val='edge'), tag('c:yMode', val='edge')]
    edges += [tag(f'c:{name}', val=record.kvr(name)) for name in 'xywh'
              if record.kvr(name) is not None]
    return tag('c:layout', tag('c:manualLayout', *edges))


def runs_xml(text):
    """The <a:r> runs of a title: a string, or a list of (text, props) pairs."""
    runs = []
    for item in [(text, {})] if isinstance(text, str) else text:
        piece, props = (item, {}) if isinstance(item, str) else item
        inner = [solid_xml(props['color'])] if props.get('color') else []
        inner += [tag('a:latin', typeface=props['name'])] if props.get('name') else []
        height, baseline = props.get('height'), props.get('baseline')
        runs.append(tag('a:r', tag('a:rPr', *inner, lang='en-US',
                                   sz=None if height is None else int(round(float(height) * 100)),
                                   b=props.get('bold'), i=props.get('ital'),
                                   u=None if props.get('under') is None else
                                   'sng' if props['under'] else 'none',
                                   baseline=None if baseline is None else
                                   int(round(float(baseline) * 1000))),
                        tag('a:t', xml_text(piece))))
    return ''.join(runs)


def title_xml(node, height, rotation):
    """<c:title> of a Text node: rich with text, automatic (the series name) without. `height`
    and `rotation` are the defaults of this kind of title; '' when the node is absent."""
    if node is None:
        return ''
    font = font_values(node.kvr('font'), height=height)
    rot = get(node, 'rot', rotation)
    rich = tag('c:tx', tag('c:rich', body_xml(rot), tag('a:lstStyle'), tag(
        'a:p', tag('a:pPr', defrpr_xml(font)), runs_xml(node.kvr('text'))))) \
        if node.kvr('text') is not None else ''
    layout = layout_xml(node.kvr('layout')) if node.kvr('layout') is not None else ''
    return tag('c:title', rich, layout, tag('c:overlay', val=bool(get(node, 'overlay', False))),
               shape_xml(tag('a:noFill'), tag('a:ln', tag('a:noFill'))), txpr_xml(font, rot))


def number_cache(values, name='numCache'):
    """<c:numCache> (or numLit) of a list of values; blanks and text leave no point."""
    points = [tag('c:pt', tag('c:v', xml_text(value)), idx=index)
              for index, value in enumerate(values)
              if isinstance(value, (int, float)) and not isinstance(value, bool)
              and math.isfinite(value)]
    return tag(f'c:{name}', tag('c:formatCode', 'General'), tag('c:ptCount', val=len(values)),
               *points)


def data_xml(spec, values):
    """The inside of xVal, yVal, plus or minus: a range as numRef, a list as numLit."""
    if isinstance(spec, str):
        cached = values(spec) if values is not None else []
        return tag('c:numRef', tag('c:f', xml_text(spec)), number_cache(cached))
    return number_cache([float(item) for item in spec], 'numLit')


def marker_xml(record, color, default_symbol):
    """<c:marker> of a marker record (symbol 'none' has no size and no shape)."""
    symbol = field(record, 'symbol', default_symbol)
    if symbol == 'none':
        return tag('c:marker', tag('c:symbol', val='none'))
    fill = field(record, 'fill', color)
    edge = field(record, 'linecolor', fill)
    return tag('c:marker', tag('c:symbol', val=symbol), tag('c:size', val=int(field(record, 'size', 5))),
               shape_xml(solid_xml(fill), line_xml(None, edge, field(record, 'linewidth', 0.75))))


def trendline_xml(node, color):
    """<c:trendline> of a Trendline node."""
    fit = get(node, 'fit', 'linear')
    extra = [tag(f'c:{name}', val=get(node, name)) for name in ('forward', 'backward')
             if get(node, name, 0)]
    steps = [tag('c:order', val=int(get(node, 'order', 2)))] if fit == 'poly' else []
    steps += [tag('c:period', val=int(get(node, 'period', 2)))] if fit == 'movingAvg' else []
    steps += extra + [tag('c:intercept', val=node.kvr('intercept'))] \
        if node.kvr('intercept') is not None else extra
    label = ''
    if node.kvr('numfmt') or node.kvr('font') or node.kvr('layout'):
        numfmt = tag('c:numFmt', formatCode=node.kvr('numfmt'), sourceLinked=False) \
            if node.kvr('numfmt') else ''
        label = tag('c:trendlineLbl', layout_xml(node.kvr('layout')), numfmt,
                    shape_xml(tag('a:noFill'), tag('a:ln', tag('a:noFill'))),
                    txpr_xml(font_values(node.kvr('font'), height=9)))
    name = tag('c:name', xml_text(node.kvr('label'))) if node.kvr('label') is not None else ''
    return tag('c:trendline', name, shape_xml(None, line_xml(node.kvr('line'), color, 1.5, 'sysDot')),
               tag('c:trendlineType', val=fit), *steps,
               tag('c:dispRSqr', val=bool(get(node, 'rsq', False))),
               tag('c:dispEq', val=bool(get(node, 'eq', False))), label)


def errbars_xml(node, direction, color, values):
    """<c:errBars> of an ErrorBars node; `direction` is 'x' or 'y'."""
    mode = get(node, 'mode', 'fixed')
    amount = [tag(f'c:{side}', data_xml(node.kvr(side), values)) for side in ('plus', 'minus')
              if node.kvr(side) is not None] if mode == 'custom' \
        else [tag('c:val', val=get(node, 'value', 1))]
    return tag('c:errBars', tag('c:errDir', val=direction), tag('c:errBarType', val=get(node, 'dir', 'both')),
               tag('c:errValType', val=ERROR_MODES[mode]),
               tag('c:noEndCap', val=not get(node, 'endcap', True)), *amount,
               shape_xml(None, line_xml(node.kvr('line'), color, 0.75)))


def labels_xml(node):
    """<c:dLbls> of a DataLabels node."""
    numfmt = [tag('c:numFmt', formatCode=node.kvr('numfmt'), sourceLinked=False)] \
        if node.kvr('numfmt') else []
    text = [txpr_xml(font_values(node.kvr('font'), height=9))] if node.kvr('font') is not None else []
    pos = [tag('c:dLblPos', val=node.kvr('pos'))] if node.kvr('pos') else []
    shows = [tag(f'c:{element}', val=bool(get(node, leaf, False))) for element, leaf in (
        ('showLegendKey', 'showkey'), ('showVal', 'showy'), ('showCatName', 'showx'),
        ('showSerName', 'showname'))]
    return tag('c:dLbls', *numfmt, *text, *pos, *shows, tag('c:showPercent', val=0),
               tag('c:showBubbleSize', val=0))


def series_xml(node, position, style, values):
    """One <c:ser>; `position` is its 0-based place in the chart (idx and order)."""
    line = node.kvr('line')
    color = field(line, 'color', PALETTE[position % len(PALETTE)])
    if line is None and style in ('marker', 'none'):
        line = rec(none=True)
    if node.kvr('labelref'):
        name = tag('c:tx', tag('c:strRef', tag('c:f', xml_text(node.kvr('labelref')))))
    else:
        name = tag('c:tx', tag('c:v', xml_text(node.kvr('label')))) \
            if node.kvr('label') is not None else ''
    parts = [name, shape_xml(None, line_xml(line, color, 2.25)),
             marker_xml(node.kvr('marker'), color, 'none' if style in ('line', 'smooth') else 'circle')]
    parts += [labels_xml(node.kvr('labels'))] if node.kvr('labels') is not None else []
    parts += [trendline_xml(node.kvr('trend'), color)] if node.kvr('trend') is not None else []
    parts += [errbars_xml(node.kvr(name + 'err'), name, color, values) for name in 'xy'
              if node.kvr(name + 'err') is not None]
    smooth = get(node, 'smooth', style in ('smooth', 'smoothMarker'))
    return tag('c:ser', tag('c:idx', val=position), tag('c:order', val=position), *parts,
               tag('c:xVal', data_xml(node.kvr('x'), values)),
               tag('c:yVal', data_xml(node.kvr('y'), values)), tag('c:smooth', val=bool(smooth)))


def option(node, name, element):
    """<element val=...> of the leaf `name` of a node, or '' when the node has none."""
    value = get(node, name)
    return '' if value is None else tag(element, val=value)


def grid_xml(node, secondary):
    """The major and minor gridlines of an Axis node: an absent leaf is the default (light grey
    major lines on the primary axes, nothing otherwise); a record with none=True is no lines."""
    major = get(node, 'gridmajor', None if secondary else rec(color='D9D9D9', width=0.75))
    return [tag(f'c:{kind}Gridlines', shape_xml(None, line_xml(record, 'D9D9D9')))
            for kind, record in (('major', major), ('minor', get(node, 'gridminor')))
            if record is not None and not record.kvr('none')]


def axis_xml(node, other, axis_id, cross_id, position, secondary=False, hidden=False):
    """One <c:valAx>. `node` is its Axis node (None: all defaults), `other` the node of the axis
    it crosses (its crossesat / crosses say where THIS axis crosses it)."""
    scaling = [option(node, 'log', 'c:logBase'),
               tag('c:orientation', val='maxMin' if get(node, 'reverse', False) else 'minMax'),
               option(node, 'max', 'c:max'), option(node, 'min', 'c:min')]
    numfmt, crossing = get(node, 'numfmt'), get(other, 'crossesat')
    cross = tag('c:crossesAt', val=crossing) if crossing is not None else tag(
        'c:crosses', val=get(other, 'crosses', 'max' if position == 'r' else 'autoZero'))
    return tag('c:valAx', tag('c:axId', val=axis_id), tag('c:scaling', *scaling),
               tag('c:delete', val=not (get(node, 'visible', True) and not hidden)),
               tag('c:axPos', val=position), *grid_xml(node, secondary),
               title_xml(get(node, 'title'), 10, -90 if position in ('l', 'r') else 0),
               tag('c:numFmt', formatCode=numfmt or 'General', sourceLinked=numfmt is None),
               tag('c:majorTickMark', val=get(node, 'tickmajor', 'out')),
               tag('c:minorTickMark', val=get(node, 'tickminor', 'none')),
               tag('c:tickLblPos', val=get(node, 'ticklabels', 'nextTo')),
               shape_xml(tag('a:noFill'), line_xml(get(node, 'line'), 'BFBFBF', 0.75)),
               txpr_xml(font_values(get(node, 'font'), height=9), get(node, 'labelrot')),
               tag('c:crossAx', val=cross_id), cross,
               tag('c:crossBetween', val=get(node, 'between', 'midCat')),
               option(node, 'major', 'c:majorUnit'), option(node, 'minor', 'c:minorUnit'))


def legend_xml(node):
    """<c:legend> of a Legend node ('' when the node is absent)."""
    if node is None:
        return ''
    hidden = [tag('c:legendEntry', tag('c:idx', val=int(number) - 1), tag('c:delete', val=1))
              for number in get(node, 'hide', [])]
    layout = layout_xml(node.kvr('layout')) if node.kvr('layout') is not None else ''
    return tag('c:legend', tag('c:legendPos', val=get(node, 'pos', 'r')), *hidden, layout,
               tag('c:overlay', val=bool(get(node, 'overlay', False))),
               shape_xml(fill_xml(node.kvr('fill'), 'none'), line_xml(node.kvr('line'), None)),
               txpr_xml(font_values(node.kvr('font'), height=9)))


def plot_xml(chart, style, values):
    """<c:plotArea>: the scatter group of each axis pair, then all the axes, then the shape."""
    groups = {1: [], 2: []}
    for position, node in enumerate(chart.kvr('series').nodes()):
        groups[2 if get(node, 'axis', 1) == 2 else 1].append(series_xml(node, position, style, values))
    nodes = [chart.kvr(name) for name in ('xaxis', 'yaxis', 'x2axis', 'y2axis')]
    x2shown = nodes[2] is not None and get(nodes[2], 'visible', False)
    pairs = [(groups[1], nodes[0], nodes[1], AXIS_IDS[:2], ('b', 'l'), False, False)] \
        if groups[1] or not groups[2] else []
    pairs += [(groups[2], nodes[2], nodes[3], AXIS_IDS[2:], ('b', 'r'), True, not x2shown)] \
        if groups[2] else []
    scatter, axes = [], []
    for series, xnode, ynode, (xid, yid), (xpos, ypos), secondary, hide_x in pairs:
        scatter.append(tag('c:scatterChart', tag('c:scatterStyle', val=style),
                           tag('c:varyColors', val=0), *series, tag('c:axId', val=xid),
                           tag('c:axId', val=yid)))
        axes += [axis_xml(xnode, ynode, xid, yid, xpos, secondary, hide_x),
                 axis_xml(ynode, xnode, yid, xid, ypos, secondary)]
    plot = chart.kvr('plotarea')
    return tag('c:plotArea', layout_xml(get(plot, 'layout')), *scatter, *axes,
               shape_xml(fill_xml(get(plot, 'fill'), 'none'), line_xml(get(plot, 'line'), None)))


def chart_xml(chart, values=None):
    """The text of xl/charts/chartN.xml for a chart node. `values(ref)` returns the cell
    values of a range (for the number caches); without it the caches are empty."""
    style = get(chart, 'style', 'lineMarker')
    title, area = chart.kvr('title'), chart.kvr('chartarea')
    inner = [title_xml(title, 14, 0), tag('c:autoTitleDeleted', val=title is None),
             plot_xml(chart, style, values), legend_xml(chart.kvr('legend')),
             tag('c:plotVisOnly', val=bool(get(chart, 'visibleonly', True))),
             tag('c:dispBlanksAs', val=get(chart, 'blanks', 'gap'))]
    text = txpr_xml(font_values(area.kvr('font'), height=10)) if get(area, 'font') is not None \
        else tag('c:txPr', tag('a:bodyPr'), tag('a:lstStyle'), tag(
            'a:p', tag('a:pPr', tag('a:defRPr')), tag('a:endParaRPr', lang='en-US')))
    margins = tag('c:pageMargins', b=0.75, l=0.7, r=0.7, t=0.75, header=0.3, footer=0.3)
    return tag(
        'c:chartSpace', tag('c:date1904', val=0), tag('c:lang', val='en-US'),
        tag('c:roundedCorners', val=bool(get(area, 'rounded', False))),
        tag('c:chart', *inner),
        shape_xml(fill_xml(get(area, 'fill'), 'FFFFFF'), line_xml(get(area, 'line'), 'D9D9D9', 0.75)),
        text, tag('c:printSettings', tag('c:headerFooter'), margins, tag('c:pageSetup')),
        **{'xmlns:c': NS['c'], 'xmlns:a': NS['a'], 'xmlns:r': NS['r']})


def corner_xml(label, values):
    """<xdr:from> or <xdr:to> of an anchor from (col, colOff, row, rowOff)."""
    return tag(f'xdr:{label}', *[tag(f'xdr:{name}', str(value)) for name, value in zip(
        ('col', 'colOff', 'row', 'rowOff'), values)])


def frame_xml(number, name, anchor):
    """One <xdr:twoCellAnchor> holding chart `number` (relationship rId<number>)."""
    chart = tag('a:graphic', tag('a:graphicData', tag('c:chart', **{'r:id': f'rId{number}'}),
                                 uri=NS['c']))
    frame = tag('xdr:graphicFrame', tag('xdr:nvGraphicFramePr',
                                        tag('xdr:cNvPr', id=number + 1, name=name),
                                        tag('xdr:cNvGraphicFramePr')),
                tag('xdr:xfrm', tag('a:off', x=0, y=0), tag('a:ext', cx=0, cy=0)), chart, macro='')
    return tag('xdr:twoCellAnchor', corner_xml('from', anchor[:4]), corner_xml('to', anchor[4:]),
               frame, tag('xdr:clientData'))


def drawing_xml(frames):
    """xl/drawings/drawingK.xml for a list of (name, anchor) pairs; chart n is rId<n>."""
    items = [frame_xml(number, name, anchor) for number, (name, anchor) in enumerate(frames, 1)]
    return tag('xdr:wsDr', *items, **{f'xmlns:{key}': NS[key]
                                                 for key in ('xdr', 'a', 'r', 'c')})


# ------------------------------------------------------------------ DrawingML in ------
def attr(element, path, convert=str):
    """The val attribute of the child at `path` converted, or None when there is no such child."""
    child = element.find(path) if element is not None else None
    return None if child is None or child.get('val') is None else convert(child.get('val'))


def grab(node, element, table):
    """Copy the val of each listed child of `element` to a leaf of `node`: table lines are
    (child element, leaf, converter)."""
    for name, leaf, convert in table:
        value = attr(element, name, convert)
        if value is not None:
            node[leaf] = value


def draw_color(parent):
    """(colour string, alpha) of the colour element inside `parent` (chartdef.md section 3)."""
    found = [child for child in parent if child.tag in ('srgbClr', 'schemeClr', 'sysClr')] \
        if parent is not None else []
    if not found:
        return None, None
    element = found[-1]
    alpha = attr(element, 'alpha', lambda text: int(text) / 1000)
    if element.tag == 'srgbClr':
        return element.get('val').upper(), alpha
    if element.tag == 'sysClr':
        return ':'.join(['sys', element.get('val')] + ([element.get('lastClr').upper()]
                                                       if element.get('lastClr') else [])), alpha
    mods = [attr(element, name) for name in ('lumMod', 'lumOff')]
    text = 'theme:' + element.get('val')
    return (text + ':' + (mods[0] or '') + (':' + mods[1] if mods[1] else '')
            if any(mods) else text), alpha


def fill_record(shape):
    """A fill record of a spPr, or None when it states no fill."""
    if shape is None:
        return None
    if shape.find('noFill') is not None:
        return rec(none=True)
    solid = shape.find('solidFill')
    if solid is None:
        return None
    color, alpha = draw_color(solid)
    return rec(color=color, alpha=alpha)


def line_record(ln):
    """A line record of an <a:ln> element (or None)."""
    if ln is None:
        return None
    width = ln.get('w')
    return rec(width=round(int(width) / EMU_PER_POINT, 4) if width else None, cap=ln.get('cap'),
               none=True if ln.find('noFill') is not None else None,
               color=draw_color(ln.find('solidFill'))[0], dash=attr(ln, 'prstDash'))


def font_record(rpr):
    """A font record of an <a:defRPr> or <a:rPr> (None when absent)."""
    if rpr is None:
        return None
    latin = rpr.find('latin')
    typeface = latin.get('typeface', '') if latin is not None else ''
    return rec(height=int(rpr.get('sz')) / 100 if rpr.get('sz') else None,
               bold=truth(rpr.get('b')) if rpr.get('b') is not None else None,
               ital=truth(rpr.get('i')) if rpr.get('i') is not None else None,
               under=rpr.get('u') != 'none' if rpr.get('u') is not None else None,
               name=typeface if typeface and not typeface.startswith('+') else None,
               color=draw_color(rpr.find('solidFill'))[0])


def layout_record(element):
    """A layout record of a <c:layout> (None when it has no manual layout)."""
    manual = element.find('manualLayout') if element is not None else None
    fields = {name: attr(manual, name, float) for name in 'xywh'} if manual is not None else {}
    return rec(**fields) if any(value is not None for value in fields.values()) else None


def set_records(node, element, shape='spPr', text='txPr', layout='layout'):
    """Set the leaves fill, line, font and layout of `node` from the children of `element`."""
    sp = element.find(shape)
    leaves = {'fill': fill_record(sp), 'line': line_record(sp.find('ln')) if sp is not None else None,
              'font': font_record(element.find(f'{text}//defRPr')),
              'layout': layout_record(element.find(layout))}
    for leaf, record in leaves.items():
        if record is not None and (leaf != 'font' or record.keys()):
            node[leaf] = record


def run_props(run):
    """The (text, props) pair of one <a:r> run of a title."""
    rpr, piece = run.find('rPr'), run.find('t')
    props = {}
    if rpr is not None:
        if rpr.get('baseline') not in (None, '0'):
            props['baseline'] = int(rpr.get('baseline')) / 1000
        for key, name, convert in (('b', 'bold', truth), ('i', 'ital', truth),
                                   ('u', 'under', lambda text: text != 'none'),
                                   ('sz', 'height', lambda text: int(text) / 100)):
            if rpr.get(key) is not None and not (key == 'u' and rpr.get(key) == 'none'):
                props[name] = convert(rpr.get(key))
    return (piece.text or '' if piece is not None else ''), props


def read_title(parent, name, element, default_rot):
    """Fill the Text node `name` of `parent` from a <c:title> element."""
    node = parent.node(name)
    rich = element.find('tx/rich')
    if rich is not None:
        runs = [run_props(run) for run in rich.iter('r')]
        if runs:
            node['text'] = runs[0][0] if len(runs) == 1 and not runs[0][1] else runs
        body = rich.find('bodyPr')
        rot = int(body.get('rot')) / 60000 if body is not None and body.get('rot') else default_rot
        if rot != default_rot:
            node['rot'] = rot
        font = font_record(rich.find('.//pPr/defRPr'))
    else:
        font = font_record(element.find('txPr//defRPr'))
    if font is not None and (rich is not None or font.keys()):
        node['font'] = font
    if attr(element, 'overlay', truth):
        node['overlay'] = True
    layout = layout_record(element.find('layout'))
    if layout is not None:
        node['layout'] = layout
    return node


def numbers_of(element):
    """A range string or a list of numbers from a numRef / numLit container."""
    reference = element.find('numRef/f') if element is not None else None
    if reference is not None:
        return reference.text
    literal = element.find('numLit') if element is not None else None
    return None if literal is None else [float(pt.find('v').text) for pt in literal.findall('pt')]


def read_marker(element):
    """A marker record of a <c:marker>."""
    shape = element.find('spPr')
    fill = fill_record(shape)
    edge = line_record(shape.find('ln')) if shape is not None else None
    return rec(symbol=attr(element, 'symbol'), size=attr(element, 'size', int),
               fill=fill.kvr('color') if fill is not None else None,
               linecolor=edge.kvr('color') if edge is not None else None,
               linewidth=edge.kvr('width') if edge is not None else None)


def read_series(element, node, axis, notes):
    """Fill one series node from a <c:ser> element."""
    literal, reference = element.find('tx/v'), element.find('tx/strRef/f')
    node['label'] = (literal.text or '') if literal is not None else None
    node['labelref'] = reference.text if reference is not None else None
    x, y = numbers_of(element.find('xVal')), numbers_of(element.find('yVal'))
    if x is None or y is None:
        notes['a series whose x or y data is not a number range was left empty'] = True
    node['x'], node['y'] = x if x is not None else [], y if y is not None else []
    node['axis'] = 2 if axis == 2 else None
    line = line_record(element.find('spPr/ln')) if element.find('spPr') is not None else None
    node['line'] = line
    node['marker'] = read_marker(element.find('marker')) if element.find('marker') is not None else None
    node['smooth'] = attr(element, 'smooth', truth)
    if element.find('dLbls') is not None:
        read_labels(node.node('labels'), element.find('dLbls'))
    if element.find('trendline') is not None:
        read_trend(node.node('trend'), element.find('trendline'))
    for bars in element.findall('errBars'):
        read_errbars(node.node('xerr' if attr(bars, 'errDir') == 'x' else 'yerr'), bars)
    return node


def read_labels(node, element):
    """Fill a DataLabels node from a <c:dLbls>."""
    for tag_name, leaf in (('showVal', 'showy'), ('showCatName', 'showx'),
                           ('showSerName', 'showname'), ('showLegendKey', 'showkey')):
        if attr(element, tag_name, truth):
            node[leaf] = True
    node['pos'] = attr(element, 'dLblPos')
    fmt = element.find('numFmt')
    node['numfmt'] = fmt.get('formatCode') if fmt is not None and not truth(fmt.get('sourceLinked')) else None
    node['font'] = font_record(element.find('txPr//defRPr'))


def read_trend(node, element):
    """Fill a Trendline node from a <c:trendline>."""
    node['fit'] = attr(element, 'trendlineType') or 'linear'
    grab(node, element, [(name, name, float) for name in
                         ('order', 'period', 'forward', 'backward', 'intercept')])
    for name, leaf in (('dispRSqr', 'rsq'), ('dispEq', 'eq')):
        if attr(element, name, truth):
            node[leaf] = True
    node['label'] = element.find('name').text or '' if element.find('name') is not None else None
    node['line'] = line_record(element.find('spPr/ln'))
    label = element.find('trendlineLbl')
    if label is not None:
        fmt = label.find('numFmt')
        node['numfmt'] = fmt.get('formatCode') if fmt is not None else None
        node['layout'] = layout_record(label.find('layout'))
        node['font'] = font_record(label.find('txPr//defRPr'))


def read_errbars(node, element):
    """Fill an ErrorBars node from a <c:errBars>."""
    inverse = {value: key for key, value in ERROR_MODES.items()}
    node['mode'] = inverse.get(attr(element, 'errValType'), 'fixed')
    node['dir'] = attr(element, 'errBarType')
    node['endcap'] = False if attr(element, 'noEndCap', truth) else None
    node['value'] = attr(element, 'val', float)
    for side in ('plus', 'minus'):
        node[side] = numbers_of(element.find(side))
    node['line'] = line_record(element.find('spPr/ln'))


def read_grids(node, element, secondary):
    """Set gridmajor and gridminor of an Axis node: a missing major gridline on a primary axis
    means the lines were switched off, which a record with none=True says."""
    for tag_name, leaf in (('majorGridlines', 'gridmajor'), ('minorGridlines', 'gridminor')):
        grid = element.find(tag_name)
        if grid is not None:
            node[leaf] = line_record(grid.find('spPr/ln')) or rec(color='D9D9D9')
        elif leaf == 'gridmajor' and not secondary:
            node[leaf] = rec(none=True)


def read_crossing(other, element, name):
    """Where this axis crosses the other one is stored on the OTHER node, as crossesat or crosses."""
    if attr(element, 'crossesAt', float) is not None:
        other['crossesat'] = attr(element, 'crossesAt', float)
    elif attr(element, 'crosses') not in (None, 'max' if name == 'y2axis' else 'autoZero'):
        other['crosses'] = attr(element, 'crosses')


def read_axis(chart, name, element, other_name, secondary):
    """Fill axis node `name` from a <c:valAx>; where this axis crosses the other axis is
    stored on the OTHER node (chartdef.md section 6)."""
    node = chart.node(name)
    grab(node, element.find('scaling'), [('logBase', 'log', float), ('max', 'max', float),
                                         ('min', 'min', float)])
    if attr(element.find('scaling'), 'orientation') == 'maxMin':
        node['reverse'] = True
    if attr(element, 'delete', truth):
        node['visible'] = False
    elif secondary and name == 'x2axis':
        node['visible'] = True
    read_grids(node, element, secondary)
    if element.find('title') is not None:
        read_title(node, 'title', element.find('title'), -90 if name in ('yaxis', 'y2axis') else 0)
    fmt = element.find('numFmt')
    node['numfmt'] = fmt.get('formatCode') if fmt is not None and not truth(fmt.get('sourceLinked')) else None
    grab(node, element, [('majorTickMark', 'tickmajor', str), ('minorTickMark', 'tickminor', str),
                         ('tickLblPos', 'ticklabels', str), ('crossBetween', 'between', str),
                         ('majorUnit', 'major', float), ('minorUnit', 'minor', float)])
    node['line'] = line_record(element.find('spPr/ln'))
    node['font'] = font_record(element.find('txPr//defRPr'))
    body = element.find('txPr/bodyPr')
    if body is not None and body.get('rot') not in (None, '-60000000'):
        node['labelrot'] = int(body.get('rot')) / 60000
    read_crossing(chart.node(other_name), element, name)
    return node


def read_legend(node, element):
    """Fill a Legend node from a <c:legend>."""
    node['pos'] = attr(element, 'legendPos')
    hidden = [attr(entry, 'idx', int) + 1 for entry in element.findall('legendEntry')
              if attr(entry, 'delete', truth)]
    node['hide'] = hidden or None
    if attr(element, 'overlay', truth):
        node['overlay'] = True
    set_records(node, element)


def read_plot(chart, plot, notes):
    """Fill the axes and series of a chart node from a <c:plotArea>."""
    groups = plot.findall('scatterChart')
    for child in plot:
        if child.tag not in ('layout', 'scatterChart', 'valAx', 'spPr', 'extLst'):
            notes[f'chart plot-area element {child.tag} was not read'] = True
    notes.update({} if groups else {'this chart has no XY scatter group; it was left empty': True})
    notes.update({'a category axis was not read': True} if plot.find('catAx') is not None else {})
    axes = {attr(axis, 'axId'): axis for axis in plot.findall('valAx')}
    series_number = 0
    for index, group in enumerate(groups):
        if index == 0 and attr(group, 'scatterStyle'):
            chart['style'] = attr(group, 'scatterStyle')
        ids = [item.get('val') for item in group.findall('axId')]
        names = ('xaxis', 'yaxis') if index == 0 else ('x2axis', 'y2axis')
        if len(ids) == 2 and ids[0] in axes and ids[1] in axes:
            read_axis(chart, names[0], axes[ids[0]], names[1], index > 0)
            read_axis(chart, names[1], axes[ids[1]], names[0], index > 0)
        for element in sorted(group.findall('ser'), key=lambda item: attr(item, 'order', int)):
            series_number += 1
            read_series(element, chart.kvr('series').node(f's{series_number}'),
                        2 if index else 1, notes)


def read_chart(data, chart, notes):
    """Fill the chart node `chart` from the bytes of a chart part; what is not mapped goes
    to the dict `notes`."""
    root = parse_xml(data)
    element = root.find('chart')
    plot = element.find('plotArea')
    read_plot(chart, plot, notes)
    if element.find('title') is not None:
        read_title(chart, 'title', element.find('title'), 0)
    if element.find('legend') is not None:
        read_legend(chart.node('legend'), element.find('legend'))
    blanks = attr(element, 'dispBlanksAs')
    chart['blanks'] = blanks if blanks != 'gap' else None
    chart['visibleonly'] = False if attr(element, 'plotVisOnly', truth) is False else None
    set_records(chart.node('plotarea'), plot)
    area = chart.node('chartarea')
    set_records(area, root)
    if attr(root, 'roundedCorners', truth):
        area['rounded'] = True
    for name in ('view3D', 'floor', 'sideWall', 'backWall', 'pivotFmts'):
        if element.find(name) is not None:
            notes[f'chart element {name} was not read'] = True


def read_anchored(anchor, targets, read_part, make_chart, notes):
    """Read the charts under one drawing anchor into new chart nodes, with their cell anchor."""
    for frame in anchor.iter('chart'):
        part = read_part(targets.get(frame.get('id')))
        if part is None:
            notes['a chart relationship pointed at a missing part'] = True
            continue
        chart = make_chart()
        read_chart(part, chart, notes)
        if anchor.find('graphicFrame') is None:
            notes['a chart inside a shape group is placed by the whole group'] = True
        if anchor.tag == 'twoCellAnchor':
            numbers = [int(anchor.find(f'{side}/{name}').text) for side in ('from', 'to')
                       for name in ('col', 'colOff', 'row', 'rowOff')]
            chart['anchor'] = rec(**dict(zip(ANCHOR_FIELDS, numbers)))


def read_drawing(data, targets, read_part, make_chart, notes):
    """Read the charts of one drawing part (bytes). `targets` maps a relationship id to the
    part it names; read_part(name) gives that part's bytes or None; make_chart() gives a new
    chart node. Pictures and shapes are counted in `notes`."""
    root = parse_xml(data)
    anchors = [child for child in root if child.tag in ANCHORS]
    for child in root:
        choice = child.find('Choice') if child.tag == 'AlternateContent' else None
        anchors += [item for item in choice if item.tag in ANCHORS] if choice is not None else []
    for anchor in anchors:
        read_anchored(anchor, targets, read_part, make_chart, notes)
    for what, name in (('pic', 'pictures'), ('sp', 'shapes')):
        count = sum(len(list(anchor.iter(what))) for anchor in anchors)
        notes.update({f'{count} {name} in a drawing were not read': True} if count else {})
