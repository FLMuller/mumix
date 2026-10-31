"""
xlchart -- XY scatter charts for xlw: the chart tkv, and its chart XML.

Why
    A chart is a tkv node (layout in chartdef.md), so it is edited like the rest of the
    document, read back by xlreader, and drawn by svgchart from the same definition.
    This module builds charts and turns one into the text of an Excel chart part.

Algorithm
    chart_part() walks the chart node once and writes the elements in the order Excel
    demands (chartdef.md section 6). Colours, lines, fills and fonts are small records
    (kv); nodes hold the groups. Anything absent takes its default, so a chart that sets
    only series and axis titles is complete. Data are ranges ('Sheet!$A$2:$A$100'); the
    values are looked up through a function the caller passes, to write the number
    cache that viewers without a recalculation engine need.

Use
    chart = xl.chart('conc')                          # on the active sheet
    chart.title.text = 'Concentration'
    chart.xaxis.title.text = 'time (s)'
    add_series(chart, x='Data!$A$2:$A$100', y='Data!$B$2:$B$100', label='A',
               line=dict(color='C00000', width=2), marker=dict(symbol='none'))
    place(chart, col=4, row=1, ncols=9, nrows=18)     # zero-based top-left, size in cells
    xl.save()

    ref('Data', 2, 1, 100, 1)  ->  'Data!$A$2:$A$100'
    parse_ref("'My Sheet'!$B$2:$B$9")  ->  ('My Sheet', 2, 2, 9, 2)
    rec(name='Calibri', height=14)                    # a record (kv)

Versions
    M01  m01.v01  2026-10-31  first version: scatter charts, secondary axes, trendlines,
                              error bars, data labels, log axes, crossing.
"""

import math
import re

from xlstore import KV, TKV
import xlparts
from xlstyle import num_text, safe_name, xml_escape

__all__ = ['rec', 'new_chart', 'add_series', 'place', 'ref', 'parse_ref', 'anchor_of',
           'chart_part', 'letters2col', 'PALETTE']

PALETTE = ('4472C4', 'ED7D31', 'A5A5A5', 'FFC000', '5B9BD5', '70AD47')
EMU_PER_POINT = 12700
AXIS_IDS = (500000001, 500000002, 500000003, 500000004)
REF_PATTERN = re.compile(r"^(?:'((?:[^']|'')+)'|([^'!]+))!\$?([A-Z]{1,3})\$?(\d+)"
                         r"(?::\$?([A-Z]{1,3})\$?(\d+))?$")

ERROR_MODES = {'fixed': 'fixedVal', 'percentage': 'percentage', 'stddev': 'stdDev',
               'stderr': 'stdErr', 'custom': 'cust'}
ERROR_DIRS = {'both': 'both', 'plus': 'plus', 'minus': 'minus'}
TICK_MARKS = ('none', 'in', 'out', 'cross')
DASHES = ('solid', 'dot', 'dash', 'dashDot', 'longDash', 'longDashDot', 'sysDot',
          'sysDash')


# ---------------------------------------------------------------- building ------------
def rec(**fields):
    """A record: a kv holding the given fields (None values are left out)."""
    record = KV()
    for key, value in fields.items():
        if value is not None:
            record.kvw(key, value)
    return record


def as_record(value):
    """A dict becomes a record; a record or None stays as it is."""
    if isinstance(value, dict):
        return rec(**value)
    return value


def new_chart(sheet, name=None):
    """A new chart node under the sheet's private 'charts' tree; returns it."""
    priv = sheet.kvr('priv')
    charts = priv.kvr('charts')
    if charts is None:
        charts = TKV()
        priv.kvw('charts', charts)
    key = safe_name(name) if name else f'chart{charts.count() + 1}'
    chart = charts.node(key)
    chart.node('series')
    return chart


def add_series(chart, x, y, label=None, **options):
    """Add a series; returns its node. x and y are ranges ('Sheet!$A$2:$A$9') or lists
    of numbers. Options: labelref, axis (1 or 2), smooth, and the records line, marker
    (dicts are accepted), and the nodes trend, xerr, yerr, labels are set on the returned
    node afterwards."""
    series = chart.kvr('series')
    if series is None:
        series = chart.node('series')
    node = series.node(f's{series.count() + 1}')
    node['x'] = x
    node['y'] = y
    if label is not None:
        node['label'] = label
    for key, value in options.items():
        node[key] = as_record(value)
    return node


def place(chart, col, row, ncols=9, nrows=18):
    """Put the chart on the sheet: zero-based top-left cell and size in cells."""
    chart['anchor'] = rec(col=col, colOff=0, row=row, rowOff=0, col2=col + ncols,
                          colOff2=0, row2=row + nrows, rowOff2=0)
    return chart


def quote_sheet(name):
    if re.fullmatch(r'[A-Za-z0-9_]+', name):
        return name
    return "'" + name.replace("'", "''") + "'"


def col2letters(col):
    return xlparts.col2letter(col)


def letters2col(letters):
    col = 0
    for char in letters:
        col = col * 26 + ord(char) - 64
    return col


def ref(sheet, row1, col1, row2=None, col2=None):
    """A data reference: ref('Data', 2, 1, 100, 1) -> 'Data!$A$2:$A$100'."""
    first = f'${col2letters(col1)}${row1}'
    if row2 is None:
        return f'{quote_sheet(sheet)}!{first}'
    return f'{quote_sheet(sheet)}!{first}:${col2letters(col2)}${row2}'


def parse_ref(text):
    """(sheet, row1, col1, row2, col2) for a reference, or None when it is not one."""
    if not isinstance(text, str):
        return None
    found = REF_PATTERN.match(text.strip())
    if found is None:
        return None
    quoted, plain, col1, row1, col2, row2 = found.groups()
    sheet = quoted.replace("''", "'") if quoted is not None else plain
    row1 = int(row1)
    col1 = letters2col(col1)
    if col2 is None:
        return sheet, row1, col1, row1, col1
    return sheet, row1, col1, int(row2), letters2col(col2)


def anchor_of(chart, ncols=0, index=0):
    """The 8-tuple anchor (col, colOff, row, rowOff, col2, colOff2, row2, rowOff2). Without
    an anchor the chart goes beside the data: one blank column right of the last used
    column, and below the previous chart of the sheet (`index`)."""
    anchor = chart.kvr('anchor')
    if anchor is None:
        col = ncols + 1
        row = 1 + index * 20
        return (col, 0, row, 0, col + 9, 0, row + 18, 0)
    fields = ('col', 'colOff', 'row', 'rowOff', 'col2', 'colOff2', 'row2', 'rowOff2')
    values = [anchor.kvr(field) for field in fields]
    if values[4] is None:
        values[4] = (values[0] or 0) + 9
    if values[6] is None:
        values[6] = (values[2] or 0) + 18
    return tuple(int(value or 0) for value in values)


# ------------------------------------------------------------------ small readers -----
def get(node, name, default=None):
    """A leaf or child node of a chart node, or `default` when absent."""
    if node is None:
        return default
    value = node.kvr(name)
    return default if value is None else value


def field(record, name, default=None):
    if record is None:
        return default
    value = record.kvr(name)
    return default if value is None else value


def emu(points):
    return int(round(float(points) * EMU_PER_POINT))


def flag(value):
    return '1' if value else '0'


# -------------------------------------------------------------------- DrawingML -------
def color_xml(color, alpha=None):
    """The colour element for a colour string (chartdef.md section 3)."""
    if color.startswith('theme:'):
        parts = color.split(':')
        inner = ''
        if len(parts) > 2 and parts[2]:
            inner += f'<a:lumMod val="{parts[2]}"/>'
        if len(parts) > 3 and parts[3]:
            inner += f'<a:lumOff val="{parts[3]}"/>'
        if alpha is not None:
            inner += f'<a:alpha val="{int(alpha * 1000)}"/>'
        return f'<a:schemeClr val="{parts[1]}">{inner}</a:schemeClr>'
    if color.startswith('sys:'):
        parts = color.split(':')
        last = f' lastClr="{parts[2]}"' if len(parts) > 2 and parts[2] else ''
        return f'<a:sysClr val="{parts[1]}"{last}/>'
    inner = f'<a:alpha val="{int(alpha * 1000)}"/>' if alpha is not None else ''
    return f'<a:srgbClr val="{color.upper()}">{inner}</a:srgbClr>'


def solid_xml(color, alpha=None):
    return f'<a:solidFill>{color_xml(color, alpha)}</a:solidFill>'


def fill_xml(record, default=None):
    """A fill record as noFill or solidFill; `default` is the colour (or 'none')."""
    if record is None:
        record_none = False
        color = default
        alpha = None
    else:
        record_none = bool(record.kvr('none'))
        color = record.kvr('color') or default
        alpha = record.kvr('alpha')
    if record_none or color in (None, 'none'):
        return '<a:noFill/>'
    return solid_xml(color, alpha)


def line_xml(record, default_color=None, default_width=0.75, default_dash=None):
    """An <a:ln> from a line record. A record with none=True gives no line."""
    none = record is not None and bool(record.kvr('none'))
    color = field(record, 'color', default_color)
    width = field(record, 'width', default_width)
    dash = field(record, 'dash', default_dash)
    cap = field(record, 'cap')
    attrs = f' w="{emu(width)}"'
    if cap:
        attrs += f' cap="{cap}"'
    if none or color is None:
        return f'<a:ln{attrs}><a:noFill/></a:ln>'
    inner = solid_xml(color)
    if dash:
        inner += f'<a:prstDash val="{dash}"/>'
    return f'<a:ln{attrs}>{inner}<a:round/></a:ln>'


def shape_xml(fill=None, line=None):
    """<c:spPr> with the given fill and line text and an empty effect list."""
    return f'<c:spPr>{fill or ""}{line or ""}<a:effectLst/></c:spPr>'


def font_values(record, name='Calibri', height=10.0, color='595959', bold=False,
                ital=False, under=False):
    """A font record merged over defaults, as a dict."""
    return {'name': field(record, 'name', name), 'height': field(record, 'height', height),
            'color': field(record, 'color', color), 'bold': field(record, 'bold', bold),
            'ital': field(record, 'ital', ital), 'under': field(record, 'under', under)}


def defrpr_xml(font, extra=''):
    attrs = (f' sz="{int(round(float(font["height"]) * 100))}" b="{flag(font["bold"])}"'
             f' i="{flag(font["ital"])}" u="{"sng" if font["under"] else "none"}"'
             f' strike="noStrike" kern="1200" baseline="0"{extra}')
    return (f'<a:defRPr{attrs}>{solid_xml(font["color"])}'
            f'<a:latin typeface="{xml_escape(font["name"])}"/></a:defRPr>')


def body_xml(rotation=None):
    rot = '-60000000' if rotation is None else str(int(round(float(rotation) * 60000)))
    return (f'<a:bodyPr rot="{rot}" spcFirstLastPara="1" vertOverflow="ellipsis" '
            'vert="horz" wrap="square" anchor="ctr" anchorCtr="1"/>')


def txpr_xml(font, rotation=None):
    return (f'<c:txPr>{body_xml(rotation)}<a:lstStyle/><a:p><a:pPr>{defrpr_xml(font)}'
            '</a:pPr><a:endParaRPr lang="en-US"/></a:p></c:txPr>')


def layout_xml(record):
    if record is None:
        return '<c:layout/>'
    inner = '<c:xMode val="edge"/><c:yMode val="edge"/>'
    for name in ('x', 'y', 'w', 'h'):
        value = record.kvr(name)
        if value is not None:
            inner += f'<c:{name} val="{num_text(value)}"/>'
    return f'<c:layout><c:manualLayout>{inner}</c:manualLayout></c:layout>'


def runs_xml(text, font):
    """The <a:r> runs of a title: a string, or a list of (text, props) pairs."""
    runs = [(text, {})] if isinstance(text, str) else list(text)
    out = ''
    for item in runs:
        piece, props = (item, {}) if isinstance(item, str) else (item[0], dict(item[1]))
        attrs = ' lang="en-US"'
        if props.get('height') is not None:
            attrs += f' sz="{int(round(float(props["height"]) * 100))}"'
        if props.get('bold') is not None:
            attrs += f' b="{flag(props["bold"])}"'
        if props.get('ital') is not None:
            attrs += f' i="{flag(props["ital"])}"'
        if props.get('under') is not None:
            attrs += f' u="{"sng" if props["under"] else "none"}"'
        if props.get('baseline') is not None:
            attrs += f' baseline="{int(round(float(props["baseline"]) * 1000))}"'
        inner = ''
        if props.get('color'):
            inner += solid_xml(props['color'])
        if props.get('name'):
            inner += f'<a:latin typeface="{xml_escape(props["name"])}"/>'
        out += f'<a:r><a:rPr{attrs}>{inner}</a:rPr><a:t>{xml_escape(piece)}</a:t></a:r>'
    return out


def title_xml(node, height, rotation):
    """<c:title> from a Text node. With text it is a rich title; without, an automatic
    one (the series name). `height` and `rotation` are the defaults for this kind of
    title."""
    if node is None:
        return ''
    text = node.kvr('text')
    font = font_values(node.kvr('font'), height=height, color='595959')
    rot = node.kvr('rot')
    rot = rotation if rot is None else rot
    inner = ''
    if text is not None:
        inner += (f'<c:tx><c:rich>{body_xml(rot)}<a:lstStyle/><a:p><a:pPr>'
                  f'{defrpr_xml(font)}</a:pPr>{runs_xml(text, font)}</a:p></c:rich></c:tx>')
    layout = node.kvr('layout')
    if layout is not None:
        inner += layout_xml(layout)
    inner += f'<c:overlay val="{flag(get(node, "overlay", False))}"/>'
    inner += shape_xml('<a:noFill/>', '<a:ln><a:noFill/></a:ln>')
    inner += txpr_xml(font, rot)
    return f'<c:title>{inner}</c:title>'


# ---------------------------------------------------------------------- data ----------
def number_cache(values):
    """<c:numCache> for a list of values; blanks and text leave no point."""
    points = ''
    for index, value in enumerate(values):
        if (isinstance(value, (int, float)) and not isinstance(value, bool)
                and math.isfinite(value)):
            points += f'<c:pt idx="{index}"><c:v>{num_text(value)}</c:v></c:pt>'
    return (f'<c:numCache><c:formatCode>General</c:formatCode>'
            f'<c:ptCount val="{len(values)}"/>{points}</c:numCache>')


def data_xml(spec, values):
    """The inside of xVal, yVal, plus or minus: a range as numRef, a list as numLit."""
    if isinstance(spec, str):
        cached = values(spec) if values is not None else []
        return (f'<c:numRef><c:f>{xml_escape(spec)}</c:f>{number_cache(cached)}'
                '</c:numRef>')
    numbers = [float(item) for item in spec]
    inner = number_cache(numbers).replace('numCache', 'numLit')
    return inner


# --------------------------------------------------------------------- series ---------
def marker_xml(record, color, default_symbol):
    symbol = field(record, 'symbol', default_symbol)
    if symbol == 'none':
        return '<c:marker><c:symbol val="none"/></c:marker>'
    size = field(record, 'size', 5)
    fill = field(record, 'fill', color)
    edge = field(record, 'linecolor', fill)
    width = field(record, 'linewidth', 0.75)
    return (f'<c:marker><c:symbol val="{symbol}"/><c:size val="{int(size)}"/>'
            + shape_xml(solid_xml(fill), line_xml(None, edge, width)) + '</c:marker>')


def trendline_xml(node, color):
    fit = get(node, 'fit', 'linear')
    inner = ''
    if node.kvr('label') is not None:
        inner += f'<c:name>{xml_escape(node.kvr("label"))}</c:name>'
    inner += shape_xml(None, line_xml(node.kvr('line'), color, 1.5, 'sysDot'))
    inner += f'<c:trendlineType val="{fit}"/>'
    if fit == 'poly':
        inner += f'<c:order val="{int(get(node, "order", 2))}"/>'
    if fit == 'movingAvg':
        inner += f'<c:period val="{int(get(node, "period", 2))}"/>'
    if get(node, 'forward', 0):
        inner += f'<c:forward val="{num_text(node.kvr("forward"))}"/>'
    if get(node, 'backward', 0):
        inner += f'<c:backward val="{num_text(node.kvr("backward"))}"/>'
    if node.kvr('intercept') is not None:
        inner += f'<c:intercept val="{num_text(node.kvr("intercept"))}"/>'
    inner += f'<c:dispRSqr val="{flag(get(node, "rsq", False))}"/>'
    inner += f'<c:dispEq val="{flag(get(node, "eq", False))}"/>'
    if node.kvr('numfmt') or node.kvr('font') or node.kvr('layout'):
        label = layout_xml(node.kvr('layout'))
        if node.kvr('numfmt'):
            label += f'<c:numFmt formatCode="{xml_escape(node.kvr("numfmt"))}" sourceLinked="0"/>'
        label += shape_xml('<a:noFill/>', '<a:ln><a:noFill/></a:ln>')
        label += txpr_xml(font_values(node.kvr('font'), height=9))
        inner += f'<c:trendlineLbl>{label}</c:trendlineLbl>'
    return f'<c:trendline>{inner}</c:trendline>'


def errbars_xml(node, direction, color, values):
    mode = get(node, 'mode', 'fixed')
    inner = f'<c:errDir val="{direction}"/>'
    inner += f'<c:errBarType val="{ERROR_DIRS[get(node, "dir", "both")]}"/>'
    inner += f'<c:errValType val="{ERROR_MODES[mode]}"/>'
    inner += f'<c:noEndCap val="{flag(not get(node, "endcap", True))}"/>'
    if mode == 'custom':
        for side in ('plus', 'minus'):
            spec = node.kvr(side)
            if spec is not None:
                inner += f'<c:{side}>{data_xml(spec, values)}</c:{side}>'
    else:
        inner += f'<c:val val="{num_text(get(node, "value", 1))}"/>'
    inner += shape_xml(None, line_xml(node.kvr('line'), color, 0.75))
    return f'<c:errBars>{inner}</c:errBars>'


def labels_xml(node):
    inner = ''
    if node.kvr('numfmt'):
        inner += f'<c:numFmt formatCode="{xml_escape(node.kvr("numfmt"))}" sourceLinked="0"/>'
    if node.kvr('font') is not None:
        inner += txpr_xml(font_values(node.kvr('font'), height=9))
    if node.kvr('pos'):
        inner += f'<c:dLblPos val="{node.kvr("pos")}"/>'
    inner += f'<c:showLegendKey val="{flag(get(node, "showkey", False))}"/>'
    inner += f'<c:showVal val="{flag(get(node, "showy", False))}"/>'
    inner += f'<c:showCatName val="{flag(get(node, "showx", False))}"/>'
    inner += f'<c:showSerName val="{flag(get(node, "showname", False))}"/>'
    inner += '<c:showPercent val="0"/><c:showBubbleSize val="0"/>'
    return f'<c:dLbls>{inner}</c:dLbls>'


def series_xml(node, position, chart_style, values):
    """One <c:ser>; `position` is its 0-based place in the chart (idx and order)."""
    color = PALETTE[position % len(PALETTE)]
    line_record = node.kvr('line')
    if line_record is not None and line_record.kvr('color'):
        color = line_record.kvr('color')
    inner = f'<c:idx val="{position}"/><c:order val="{position}"/>'
    if node.kvr('labelref'):
        inner += (f'<c:tx><c:strRef><c:f>{xml_escape(node.kvr("labelref"))}</c:f>'
                  '</c:strRef></c:tx>')
    elif node.kvr('label') is not None:
        inner += f'<c:tx><c:v>{xml_escape(node.kvr("label"))}</c:v></c:tx>'
    markers_only = chart_style == 'marker'
    line_default_none = markers_only or chart_style == 'none'
    if line_record is None and line_default_none:
        line_record = rec(none=True)
    inner += shape_xml(None, line_xml(line_record, color, 2.25))
    default_symbol = 'none' if chart_style in ('line', 'smooth') else 'circle'
    inner += marker_xml(node.kvr('marker'), color, default_symbol)
    if node.kvr('labels') is not None:
        inner += labels_xml(node.kvr('labels'))
    if node.kvr('trend') is not None:
        inner += trendline_xml(node.kvr('trend'), color)
    if node.kvr('xerr') is not None:
        inner += errbars_xml(node.kvr('xerr'), 'x', color, values)
    if node.kvr('yerr') is not None:
        inner += errbars_xml(node.kvr('yerr'), 'y', color, values)
    inner += f'<c:xVal>{data_xml(node.kvr("x"), values)}</c:xVal>'
    inner += f'<c:yVal>{data_xml(node.kvr("y"), values)}</c:yVal>'
    smooth = node.kvr('smooth')
    if smooth is None:
        smooth = chart_style in ('smooth', 'smoothMarker')
    inner += f'<c:smooth val="{flag(smooth)}"/>'
    return f'<c:ser>{inner}</c:ser>'


# ----------------------------------------------------------------------- axes ---------
def axis_xml(node, other, axis_id, cross_id, position, secondary=False, hidden=False):
    """One <c:valAx>. `node` is its Axis node (or None for all defaults), `other` the node
    of the axis it crosses (its crossesat/crosses say where THIS axis crosses it)."""
    inner = f'<c:axId val="{axis_id}"/>'
    scaling = ''
    if get(node, 'log') is not None:
        scaling += f'<c:logBase val="{num_text(node.kvr("log"))}"/>'
    scaling += f'<c:orientation val="{"maxMin" if get(node, "reverse", False) else "minMax"}"/>'
    if get(node, 'max') is not None:
        scaling += f'<c:max val="{num_text(node.kvr("max"))}"/>'
    if get(node, 'min') is not None:
        scaling += f'<c:min val="{num_text(node.kvr("min"))}"/>'
    inner += f'<c:scaling>{scaling}</c:scaling>'
    visible = get(node, 'visible', True) and not hidden
    inner += f'<c:delete val="{flag(not visible)}"/>'
    inner += f'<c:axPos val="{position}"/>'
    # Gridlines: absent leaf = the default (grey major lines on the primary axes, none
    # otherwise); a record with none=True = no gridlines.
    major = get(node, 'gridmajor')
    if major is None and not secondary:
        major = rec(color='D9D9D9', width=0.75)
    if major is not None and not major.kvr('none'):
        inner += ('<c:majorGridlines>' + shape_xml(None, line_xml(major, 'D9D9D9'))
                  + '</c:majorGridlines>')
    minor = get(node, 'gridminor')
    if minor is not None and not minor.kvr('none'):
        inner += ('<c:minorGridlines>' + shape_xml(None, line_xml(minor, 'D9D9D9'))
                  + '</c:minorGridlines>')
    inner += title_xml(get(node, 'title'), 10, -90 if position in ('l', 'r') else 0)
    numfmt = get(node, 'numfmt')
    if numfmt is None:
        inner += '<c:numFmt formatCode="General" sourceLinked="1"/>'
    else:
        inner += f'<c:numFmt formatCode="{xml_escape(numfmt)}" sourceLinked="0"/>'
    inner += f'<c:majorTickMark val="{get(node, "tickmajor", "out")}"/>'
    inner += f'<c:minorTickMark val="{get(node, "tickminor", "none")}"/>'
    inner += f'<c:tickLblPos val="{get(node, "ticklabels", "nextTo")}"/>'
    inner += shape_xml('<a:noFill/>', line_xml(get(node, 'line'), 'BFBFBF', 0.75))
    inner += txpr_xml(font_values(get(node, 'font'), height=9), get(node, 'labelrot'))
    inner += f'<c:crossAx val="{cross_id}"/>'
    at = get(other, 'crossesat')
    if at is not None:
        inner += f'<c:crossesAt val="{num_text(at)}"/>'
    else:
        crosses = get(other, 'crosses', 'max' if position == 'r' else 'autoZero')
        inner += f'<c:crosses val="{crosses}"/>'
    inner += f'<c:crossBetween val="{get(node, "between", "midCat")}"/>'
    if get(node, 'major') is not None:
        inner += f'<c:majorUnit val="{num_text(node.kvr("major"))}"/>'
    if get(node, 'minor') is not None:
        inner += f'<c:minorUnit val="{num_text(node.kvr("minor"))}"/>'
    return f'<c:valAx>{inner}</c:valAx>'


def legend_xml(node):
    if node is None:
        return ''
    inner = f'<c:legendPos val="{get(node, "pos", "r")}"/>'
    for number in get(node, 'hide', []) or []:
        inner += f'<c:legendEntry><c:idx val="{int(number) - 1}"/><c:delete val="1"/></c:legendEntry>'
    if node.kvr('layout') is not None:
        inner += layout_xml(node.kvr('layout'))
    inner += f'<c:overlay val="{flag(get(node, "overlay", False))}"/>'
    inner += shape_xml(fill_xml(node.kvr('fill'), 'none'),
                       line_xml(node.kvr('line'), None))
    inner += txpr_xml(font_values(node.kvr('font'), height=9))
    return f'<c:legend>{inner}</c:legend>'


# ---------------------------------------------------------------------- the chart ------
def chart_part(chart, values=None):
    """The text of xl/charts/chartN.xml for a chart node. `values(ref)` returns the
    cell values of a range (for the number caches); without it caches are empty."""
    style = get(chart, 'style', 'lineMarker')
    series_node = chart.kvr('series')
    nodes = [] if series_node is None else series_node.nodes()
    primary = []
    secondary = []
    for position, node in enumerate(nodes):
        target = secondary if get(node, 'axis', 1) == 2 else primary
        target.append(series_xml(node, position, style, values))

    ids = AXIS_IDS
    xaxis = chart.kvr('xaxis')
    yaxis = chart.kvr('yaxis')
    x2axis = chart.kvr('x2axis')
    y2axis = chart.kvr('y2axis')
    groups = ''
    axes = ''
    if primary or not secondary:
        groups += (f'<c:scatterChart><c:scatterStyle val="{style}"/>'
                   '<c:varyColors val="0"/>' + ''.join(primary)
                   + f'<c:axId val="{ids[0]}"/><c:axId val="{ids[1]}"/></c:scatterChart>')
        axes += axis_xml(xaxis, yaxis, ids[0], ids[1], 'b')
        axes += axis_xml(yaxis, xaxis, ids[1], ids[0], 'l')
    if secondary:
        groups += (f'<c:scatterChart><c:scatterStyle val="{style}"/>'
                   '<c:varyColors val="0"/>' + ''.join(secondary)
                   + f'<c:axId val="{ids[2]}"/><c:axId val="{ids[3]}"/></c:scatterChart>')
        shown = x2axis is not None and get(x2axis, 'visible', False)
        axes += axis_xml(x2axis, y2axis, ids[2], ids[3], 'b', secondary=True,
                         hidden=not shown)
        axes += axis_xml(y2axis, x2axis, ids[3], ids[2], 'r', secondary=True)

    plot = chart.kvr('plotarea')
    plot_shape = shape_xml(fill_xml(get(plot, 'fill'), 'none'),
                           line_xml(get(plot, 'line'), None))
    plot_xml = (f'<c:plotArea>{layout_xml(get(plot, "layout"))}{groups}{axes}'
                f'{plot_shape}</c:plotArea>')

    title = chart.kvr('title')
    inner = title_xml(title, 14, 0)
    inner += f'<c:autoTitleDeleted val="{"0" if title is not None else "1"}"/>'
    inner += plot_xml + legend_xml(chart.kvr('legend'))
    inner += f'<c:plotVisOnly val="{flag(get(chart, "visibleonly", True))}"/>'
    inner += f'<c:dispBlanksAs val="{get(chart, "blanks", "gap")}"/>'

    area = chart.kvr('chartarea')
    area_shape = shape_xml(fill_xml(get(area, 'fill'), 'FFFFFF'),
                           line_xml(get(area, 'line'), 'D9D9D9', 0.75))
    if get(area, 'font') is not None:
        area_text = txpr_xml(font_values(area.kvr('font'), height=10))
    else:
        area_text = ('<c:txPr><a:bodyPr/><a:lstStyle/><a:p><a:pPr><a:defRPr/></a:pPr>'
                     '<a:endParaRPr lang="en-US"/></a:p></c:txPr>')
    return (xlparts.XML_HEAD
            + f'<c:chartSpace xmlns:c="{xlparts.NS_CHART}" xmlns:a="{xlparts.NS_DML}" '
            f'xmlns:r="{xlparts.NS_REL}">'
            '<c:date1904 val="0"/><c:lang val="en-US"/>'
            f'<c:roundedCorners val="{flag(get(area, "rounded", False))}"/>'
            f'<c:chart>{inner}</c:chart>{area_shape}{area_text}'
            '<c:printSettings><c:headerFooter/><c:pageMargins b="0.75" l="0.7" r="0.7" '
            't="0.75" header="0.3" footer="0.3"/><c:pageSetup/></c:printSettings>'
            '</c:chartSpace>')
