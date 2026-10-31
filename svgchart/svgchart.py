"""
svgchart -- draw an xlw XY chart definition (chartdef.md) as SVG, with matplotlib.

Why
    The HTML report and the workbook should show the same chart. The chart is one tkv node
    (xlw/chartdef.md); xlchart writes it into the workbook and this module draws it, so the
    two cannot drift apart. The picture follows Excel's rules where they are known: its
    automatic axis limits and major unit, log axes, which axis crosses where, and whether
    tick labels sit beside the axis or at the edge of the plot.

Algorithm
    Data come from the ranges of the series (a function `values(ref)` supplied by the
    caller, xlw.book_values for a book) or from literal lists. Every axis that has no
    min, max or major unit gets Excel's automatic ones (excel_scale, chartdef.md section 7).
    Series are drawn as lines and markers; a smoothed line is a Catmull-Rom spline through
    the points; trendlines are fitted here (linear, polynomial, exponential, logarithmic,
    power, moving average) and error bars computed from the series. The secondary value
    axis is a twin of the primary. The figure is saved as SVG with the text kept as text.

Axis details that matter (the finicky part; chartdef.md sections 6 and 7)
    * Limits not fixed in the chart are Excel's automatic ones (excel_scale), rounded out to
      the major unit, so an automatic axis is wider than the data. Excel does not store
      them; the rules are Microsoft's published description and an approximation.
    * crosses / crossesat on an axis say where the OTHER axis crosses it. autoZero is the
      zero of the axis, or the nearest end of the range when zero lies outside it. On a log
      axis the "zero" is taken as the value 1 (assumed, not seen in an Excel file), so
      charts with log axes should set crosses='min' (mumix does).
    * ticklabels: nextTo = labels beside the axis line wherever it crosses; low and high =
      at the lower or upper edge of the plot whatever the crossing; none = no labels.
    * The secondary value axis shares the x range, sits on the right, and has no gridlines
      unless asked.
    * Not checked against Excel's own output (no reference file has them): secondary axes,
      log axes, error bars, minor gridlines, crossing.

Use
    from svgchart import chart_svg
    svg = chart_svg(chart_node, values, width=640, height=400)    # SVG text
    svg = chart_svg(chart_node, values, inline=True)              # for embedding in HTML
    inline_svg(svg_text)    the same change applied to an SVG text already made
    chart_figure(...)  returns the matplotlib Figure; save it as PNG to look at it.
    excel_scale(lo, hi, log=None) -> (min, max, major): Excel's automatic axis.

    values(ref) -> list of cell values for 'Sheet!$A$2:$A$9' (xlw.book_values(book)).
    Needs xlw/ on sys.path (xlchart supplies the readers of the definition).

Versions
    M01  m01.v01  2026-10-31  first version: lines, markers, smoothing, trendlines, error
                              bars, data labels, log and secondary axes, crossing, legend.
"""

import io
import logging
import math
import re

import numpy as np
from matplotlib import rc_context
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter, LogLocator, MultipleLocator, NullLocator

import xlchart
from xlchart import PALETTE, field, get

__all__ = ['chart_svg', 'inline_svg', 'chart_figure', 'excel_scale', 'nice_step',
           'format_number',
           'resolve_color', 'catmull_rom', 'trend_fit', 'mathtext', 'crossing_value']

THEME_COLORS = {'bg1': 'FFFFFF', 'lt1': 'FFFFFF', 'tx1': '000000', 'dk1': '000000',
                'bg2': 'E7E6E6', 'lt2': 'E7E6E6', 'tx2': '44546A', 'dk2': '44546A',
                'accent1': '4472C4', 'accent2': 'ED7D31', 'accent3': 'A5A5A5',
                'accent4': 'FFC000', 'accent5': '5B9BD5', 'accent6': '70AD47',
                'hlink': '0563C1', 'folHlink': '954F72'}
SYSTEM_COLORS = {'windowText': '000000', 'window': 'FFFFFF'}
MARKERS = {'circle': 'o', 'square': 's', 'diamond': 'D', 'triangle': '^', 'x': 'x',
           'star': '*', 'dot': '.', 'dash': '_', 'plus': '+', 'auto': 'o'}
DASHES = {'solid': '-', 'dot': ':', 'dash': '--', 'dashDot': '-.',
          'longDash': (0, (8, 3)), 'longDashDot': (0, (8, 3, 2, 3)),
          'sysDot': (0, (1, 1)), 'sysDash': (0, (3, 1))}
GRAPHITE = '595959'


# ---------------------------------------------------------------------- colours --------
def resolve_color(text, default='000000'):
    """A chartdef colour string as '#RRGGBB'. Theme colours use the Office palette and the
    HSL-free brightening of chartdef.md section 8."""
    if text is None:
        text = default
    if text.startswith('theme:'):
        parts = text.split(':')
        base = THEME_COLORS.get(parts[1], '000000')
        mod = int(parts[2]) / 100000 if len(parts) > 2 and parts[2] else 1.0
        off = int(parts[3]) / 100000 if len(parts) > 3 and parts[3] else 0.0
        channels = [int(base[i:i + 2], 16) for i in (0, 2, 4)]
        channels = [min(255, max(0, round(c * mod + 255 * off))) for c in channels]
        return '#%02X%02X%02X' % tuple(channels)
    if text.startswith('sys:'):
        parts = text.split(':')
        return '#' + (parts[2] if len(parts) > 2 and parts[2] else
                      SYSTEM_COLORS.get(parts[1], '000000'))
    return '#' + text.upper()


# ----------------------------------------------------------------------- numbers -------
def nice_step(span, limit=10):
    """The first of 1, 2, 5 times a power of ten that gives at most `limit` intervals."""
    if span <= 0:
        return 1.0
    power = 10.0 ** math.floor(math.log10(span / limit))
    for factor in (1, 2, 5, 10, 20, 50, 100):
        step = factor * power
        if span / step <= limit * (1 + 1e-9):
            return step
    return 100 * power


def excel_scale(lo, hi, log=None):
    """Excel's automatic axis (chartdef.md section 7): returns (min, max, major) for data
    in [lo, hi]. log is the base of a log axis (or None): limits are the enclosing powers,
    major is the base."""
    if log:
        lo = max(lo, 1e-300)
        low = math.floor(math.log(lo, log) + 1e-12)
        high = math.ceil(math.log(hi, log) - 1e-12)
        if high == low:
            high = low + 1
        return float(log) ** low, float(log) ** high, float(log)
    if hi == lo:
        hi = lo + (abs(lo) * 0.1 if lo else 1.0)
    span = hi - lo
    upper = hi + 0.05 * span
    lower = lo - 0.05 * span
    if lo >= 0 and lower < upper * 5.0 / 6.0:
        lower = 0.0
    step = nice_step(upper - lower)
    axis_min = math.floor(lower / step + 1e-9) * step
    axis_max = math.ceil(upper / step - 1e-9) * step
    return axis_min, axis_max, step


def format_number(value, code=None):
    """A number in an Excel format code: General (None), 0, 0.00, #,##0.00, 0%, 0.00%,
    0.00E+00. Anything else falls back to General."""
    if code in (None, '', 'General'):
        if value == 0:
            return '0'
        if abs(value) >= 1e11 or abs(value) < 1e-4:
            return '%.5G' % value
        return ('%.10g' % value)
    if code.endswith('%'):
        return format_number(value * 100, code[:-1]) + '%'
    match = re.fullmatch(r'([#0,]*)(?:\.([0#]*))?(E[+-]0+)?', code)
    if not match:
        return format_number(value, None)
    integer, decimals, exponent = match.groups()
    places = len(decimals or '')
    required = len((decimals or '').rstrip('#'))
    if exponent:
        text = ('%.' + str(places) + 'E') % value
        mantissa, power = text.split('E')
        if places > required:
            mantissa = mantissa.rstrip('0').rstrip('.') if '.' in mantissa else mantissa
        sign = power[0]
        digits = power[1:].lstrip('0').rjust(len(exponent) - 2, '0')
        return mantissa + 'E' + sign + digits
    text = ('%.' + str(places) + 'f') % value
    if places > required and '.' in text:
        text = text.rstrip('0').rstrip('.')
        if required and '.' not in text:
            text += '.' + '0' * required
    if ',' in integer:
        whole, _, fraction = text.partition('.')
        whole = '{:,}'.format(int(whole)) if whole.lstrip('-').isdigit() else whole
        text = whole + ('.' + fraction if fraction else '')
    return text


def catmull_rom(x, y, per=12):
    """Points of a Catmull-Rom spline through (x, y) (the look of Excel's smoothed line):
    `per` points between each pair; the ends repeat their neighbour."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n = len(x)
    if n < 3:
        return x, y
    padded_x = np.concatenate([[2 * x[0] - x[1]], x, [2 * x[-1] - x[-2]]])
    padded_y = np.concatenate([[2 * y[0] - y[1]], y, [2 * y[-1] - y[-2]]])
    out_x = []
    out_y = []
    s = np.linspace(0.0, 1.0, per, endpoint=False)[:, None]
    for i in range(n - 1):
        px = padded_x[i:i + 4]
        py = padded_y[i:i + 4]
        out_x.append((0.5 * ((2 * px[1]) + (-px[0] + px[2]) * s
                             + (2 * px[0] - 5 * px[1] + 4 * px[2] - px[3]) * s**2
                             + (-px[0] + 3 * px[1] - 3 * px[2] + px[3]) * s**3)).ravel())
        out_y.append((0.5 * ((2 * py[1]) + (-py[0] + py[2]) * s
                             + (2 * py[0] - 5 * py[1] + 4 * py[2] - py[3]) * s**2
                             + (-py[0] + 3 * py[1] - 3 * py[2] + py[3]) * s**3)).ravel())
    out_x.append([x[-1]])
    out_y.append([y[-1]])
    return np.concatenate(out_x), np.concatenate(out_y)


# ------------------------------------------------------------------------ data ---------
def to_array(spec, values):
    """A range string or a list as a float array (blanks and text become NaN)."""
    if isinstance(spec, str):
        raw = values(spec) if values is not None else []
    else:
        raw = list(spec)
    out = np.full(len(raw), np.nan)
    for i, item in enumerate(raw):
        if isinstance(item, (int, float)) and not isinstance(item, bool):
            out[i] = item
    return out


def series_data(node, values):
    """x and y arrays of a series with the points that are NaN in either dropped."""
    x = to_array(node.kvr('x'), values)
    y = to_array(node.kvr('y'), values)
    n = min(len(x), len(y))
    x = x[:n]
    y = y[:n]
    keep = np.isfinite(x) & np.isfinite(y)
    return x[keep], y[keep]


def series_label(node, values):
    if node.kvr('labelref') and values is not None:
        cells = values(node.kvr('labelref'))
        if cells and cells[0] is not None:
            return str(cells[0])
    label = node.kvr('label')
    return None if label is None else str(label)


def trend_fit(kind, x, y, order=2, period=2):
    """(function or None, coefficients, r_squared, text) of a trendline fit; for a moving
    average the function is None and the coefficients are the averaged values."""
    if kind in ('linear', 'poly'):
        degree = 1 if kind == 'linear' else int(order)
        coefficients = np.polyfit(x, y, degree)
        predicted = np.polyval(coefficients, x)
        function = lambda xs: np.polyval(coefficients, xs)
        terms = []
        for i, c in enumerate(coefficients):
            power = degree - i
            number = format_number(c, None) if abs(c) >= 1e-4 or c == 0 else '%.4G' % c
            term = number + ('x' if power == 1 else f'x^{power}' if power > 1 else '')
            terms.append(term)
        text = 'y = ' + ' + '.join(terms).replace('+ -', '- ')
        return function, coefficients, r_squared(y, predicted), text
    if kind == 'exp':
        keep = y > 0
        b, a = np.polyfit(x[keep], np.log(y[keep]), 1)
        function = lambda xs: np.exp(a) * np.exp(b * xs)
        r2 = r_squared(np.log(y[keep]), a + b * x[keep])
        return function, (math.exp(a), b), r2, f'y = {math.exp(a):.4g}e^{b:.4g}x'
    if kind == 'log':
        keep = x > 0
        a, b = np.polyfit(np.log(x[keep]), y[keep], 1)
        function = lambda xs: a * np.log(xs) + b
        return function, (a, b), r_squared(y[keep], a * np.log(x[keep]) + b), \
            f'y = {a:.4g}ln(x) + {b:.4g}'
    if kind == 'power':
        keep = (x > 0) & (y > 0)
        b, a = np.polyfit(np.log(x[keep]), np.log(y[keep]), 1)
        function = lambda xs: np.exp(a) * np.power(xs, b)
        r2 = r_squared(np.log(y[keep]), a + b * np.log(x[keep]))
        return function, (math.exp(a), b), r2, f'y = {math.exp(a):.4g}x^{b:.4g}'
    if kind == 'movingAvg':
        period = max(2, int(period))
        kernel = np.ones(period) / period
        average = np.convolve(y, kernel, mode='valid')
        return None, average, float('nan'), f'{period} period moving average'
    raise ValueError(f'unknown trendline type {kind!r}')


def r_squared(y, predicted):
    residual = float(np.sum((y - predicted) ** 2))
    total = float(np.sum((y - np.mean(y)) ** 2))
    return 1.0 - residual / total if total > 0 else 1.0


def mathtext(text):
    """Title text for matplotlib: a string, or runs with baseline (percent) as sub or
    superscripts. '$' and other mathtext characters are escaped."""
    def plain(piece):
        return piece.replace('\\', '').replace('$', r'\$')
    if isinstance(text, str):
        return plain(text)
    out = ''
    for item in text:
        piece, props = (item, {}) if isinstance(item, str) else (item[0], dict(item[1]))
        base = props.get('baseline') or 0
        safe = re.sub(r'([{}_^#%&~])', r'\\\1', piece.replace('\\', '')) if base else ''
        if base > 0:
            out += '$^{\\mathrm{' + safe + '}}$'
        elif base < 0:
            out += '$_{\\mathrm{' + safe + '}}$'
        else:
            out += plain(piece)
    return out


def font_args(record, height=10.0, color=GRAPHITE, bold=False):
    return {'fontsize': float(field(record, 'height', height)),
            'color': resolve_color(field(record, 'color', color)),
            'fontweight': 'bold' if field(record, 'bold', bold) else 'normal',
            'fontstyle': 'italic' if field(record, 'ital', False) else 'normal'}


def line_style(record, color, width=0.75, dash=None):
    """matplotlib keywords for a line record: color, linewidth, linestyle (or none)."""
    if record is not None and record.kvr('none'):
        return {'linestyle': 'None', 'color': resolve_color(color)}
    shade = resolve_color(field(record, 'color', color))
    out = {'color': shade, 'linewidth': float(field(record, 'width', width))}
    style = field(record, 'dash', dash)
    out['linestyle'] = DASHES.get(style, '-') if style else '-'
    return out


# -------------------------------------------------------------------------- axes --------
class AxisInfo:
    """What the drawing needs to know about one axis."""
    __slots__ = ('low', 'high', 'major', 'log', 'reverse')


def axis_info(node, data):
    info = AxisInfo()
    base = get(node, 'log')
    info.log = float(base) if base else None
    finite = data[np.isfinite(data)] if len(data) else np.array([0.0, 1.0])
    if info.log:
        finite = finite[finite > 0]
    if len(finite) == 0:
        finite = np.array([1.0, 10.0] if info.log else [0.0, 1.0])
    auto_low, auto_high, auto_major = excel_scale(float(finite.min()), float(finite.max()),
                                                  info.log)
    info.low = float(get(node, 'min', auto_low))
    info.high = float(get(node, 'max', auto_high))
    info.major = get(node, 'major')
    if info.major is None:
        info.major = auto_major if info.log is None else float(info.log)
    info.reverse = bool(get(node, 'reverse', False))
    return info


def apply_axis(ax, which, node, info, cross_value, other_info, tick_edge):
    """Scale, limits, ticks, labels, gridlines, title and line of one value axis."""
    axis = ax.xaxis if which == 'x' else ax.yaxis
    setter = ax.set_xscale if which == 'x' else ax.set_yscale
    limit = ax.set_xlim if which == 'x' else ax.set_ylim
    if info.log:
        setter('log', base=info.log)
    limit((info.high, info.low) if info.reverse else (info.low, info.high))
    # major ticks
    if info.log:
        axis.set_major_locator(LogLocator(base=info.log, numticks=40))
    else:
        axis.set_major_locator(MultipleLocator(info.major))
    minor_step = get(node, 'minor')
    if minor_step is not None and not info.log:
        axis.set_minor_locator(MultipleLocator(float(minor_step)))
    elif get(node, 'tickminor', 'none') == 'none' and get(node, 'gridminor') is None:
        axis.set_minor_locator(NullLocator())
    code = get(node, 'numfmt')
    axis.set_major_formatter(FuncFormatter(lambda v, pos: format_number(v, code)))
    # tick marks and labels
    direction = {'out': 'out', 'in': 'in', 'cross': 'inout'}.get(
        get(node, 'tickmajor', 'out'), 'out')
    length = 0 if get(node, 'tickmajor', 'out') == 'none' else 3.5
    font = font_args(get(node, 'font'), height=9)
    axis_line = line_style(get(node, 'line'), 'BFBFBF', 0.75)
    visible = get(node, 'visible', True)
    mode = get(node, 'ticklabels', 'nextTo')
    rotation = get(node, 'labelrot', 0) or 0
    ax.tick_params(axis=which, which='major', direction=direction, length=length,
                   width=0.75, color=axis_line.get('color', '#BFBFBF'),
                   labelsize=font['fontsize'], labelcolor=font['color'],
                   labelrotation=rotation)
    minor_direction = {'out': 'out', 'in': 'in', 'cross': 'inout'}.get(
        get(node, 'tickminor', 'none'), 'out')
    ax.tick_params(axis=which, which='minor', direction=minor_direction,
                   length=0 if get(node, 'tickminor', 'none') == 'none' else 2,
                   color=axis_line.get('color', '#BFBFBF'))
    # gridlines
    major = get(node, 'gridmajor')
    if major is not None and major.kvr('none'):
        major = None
    elif major is None and tick_edge != 'secondary':
        major = xlchart.rec(color='D9D9D9', width=0.75)
    if major is not None:
        ax.grid(True, axis=which, which='major', **{
            key: value for key, value in line_style(major, 'D9D9D9', 0.75).items()})
    minor = get(node, 'gridminor')
    if minor is not None and not minor.kvr('none'):
        ax.grid(True, axis=which, which='minor', **line_style(minor, 'D9D9D9', 0.5))
    if not visible:
        axis.set_visible(False)
        return
    # label placement: beside the axis (the spine moves with its axis line) or at an edge
    spine_name = {'x': 'bottom', 'y': 'left'}[which] if tick_edge == 'primary' else 'right'
    spine = ax.spines[spine_name]
    inside = info_contains(other_info, cross_value)
    if tick_edge == 'primary':
        if mode == 'nextTo' and inside:
            spine.set_position(('data', cross_value))
            spine.set_visible(True)
            for key, value in axis_line.items():
                if key == 'color':
                    spine.set_color(value)
                elif key == 'linewidth':
                    spine.set_linewidth(value)
        else:
            spine.set_visible(False)
            line_at = cross_value if inside else (
                other_info.low if cross_value <= other_info.low else other_info.high)
            kw = dict(axis_line)
            if which == 'x':
                ax.axhline(line_at, zorder=2, **kw)
            else:
                ax.axvline(line_at, zorder=2, **kw)
            if mode == 'high':
                (axis.tick_top if which == 'x' else axis.tick_right)()
                axis.set_label_position('top' if which == 'x' else 'right')
        if mode == 'none':
            ax.tick_params(axis=which, labelbottom=False, labelleft=False)
    else:
        spine.set_color(axis_line.get('color', '#BFBFBF'))
        spine.set_linewidth(axis_line.get('linewidth', 0.75))
        if mode == 'none':
            ax.tick_params(axis=which, labelright=False)
    title = get(node, 'title')
    if title is not None and title.kvr('text') is not None:
        text = mathtext(title.kvr('text'))
        args = font_args(title.kvr('font'), height=10)
        args.pop('fontstyle', None)
        if which == 'x':
            ax.set_xlabel(text, **args)
        else:
            ax.set_ylabel(text, **args)


def info_contains(info, value):
    low, high = min(info.low, info.high), max(info.low, info.high)
    return low <= value <= high


def crossing_value(this_info, node_of_this):
    """Where the OTHER axis crosses this one, in this axis's units (chartdef.md)."""
    at = get(node_of_this, 'crossesat')
    if at is not None:
        return float(at)
    mode = get(node_of_this, 'crosses', 'autoZero')
    low, high = min(this_info.low, this_info.high), max(this_info.low, this_info.high)
    if mode == 'min':
        return low
    if mode == 'max':
        return high
    # autoZero: the zero of the axis, or the end of the axis nearest to it. The zero of a
    # log axis is the value 1 (assumed from Excel's behaviour on log charts whose data run
    # below 1: the other axis then sits across the middle of the plot). mumix sets
    # crosses='min' on its log axes, so nothing depends on this guess.
    zero = 1.0 if this_info.log else 0.0
    return min(max(zero, low), high)


# --------------------------------------------------------------------------- series -----
def draw_error_bars(ax, node, direction, x, y, shade, values):
    mode = get(node, 'mode', 'fixed')
    data = y if direction == 'y' else x
    if mode == 'fixed':
        plus = minus = np.full(len(data), float(get(node, 'value', 1)))
    elif mode == 'percentage':
        plus = minus = np.abs(data) * float(get(node, 'value', 5)) / 100.0
    elif mode == 'stddev':
        plus = minus = np.full(len(data), float(get(node, 'value', 1)) * np.std(data))
    elif mode == 'stderr':
        plus = minus = np.full(len(data), np.std(data) / math.sqrt(max(len(data), 1)))
    else:
        raw_plus = node.kvr('plus')
        raw_minus = node.kvr('minus')
        plus = to_array(raw_plus, values) if raw_plus is not None else np.zeros(len(data))
        minus = to_array(raw_minus, values) if raw_minus is not None else np.zeros(len(data))
        plus = np.resize(np.nan_to_num(plus), len(data))
        minus = np.resize(np.nan_to_num(minus), len(data))
    which = get(node, 'dir', 'both')
    if which == 'plus':
        minus = np.zeros(len(data))
    elif which == 'minus':
        plus = np.zeros(len(data))
    line = line_style(node.kvr('line'), shade, 0.75)
    caps = 3 if get(node, 'endcap', True) else 0
    keywords = {('yerr' if direction == 'y' else 'xerr'): [minus, plus]}
    ax.errorbar(x, y, fmt='none', ecolor=line.get('color', shade),
                elinewidth=line.get('linewidth', 0.75), capsize=caps, zorder=3, **keywords)


def draw_trend(ax, node, x, y, shade, handles, labels, name):
    fit = get(node, 'fit', 'linear')
    function, coefficients, r2, equation = trend_fit(fit, x, y, get(node, 'order', 2),
                                                     get(node, 'period', 2))
    style = line_style(node.kvr('line'), shade, 1.5, 'sysDot')
    if function is None:
        period = max(2, int(get(node, 'period', 2)))
        line, = ax.plot(x[period - 1:], coefficients, zorder=3, **style)
    else:
        low = float(x.min()) - float(get(node, 'backward', 0) or 0)
        high = float(x.max()) + float(get(node, 'forward', 0) or 0)
        xs = np.linspace(low, high, 200)
        line, = ax.plot(xs, function(xs), zorder=3, **style)
    handles.append(line)
    labels.append(node.kvr('label') or f'{fit.capitalize()} ({name})')
    text = []
    if get(node, 'eq', False):
        text.append(equation)
    if get(node, 'rsq', False) and not math.isnan(r2):
        text.append('R² = ' + format_number(r2, get(node, 'numfmt') or '0.0000'))
    if text:
        font = font_args(node.kvr('font'), height=9)
        ax.text(0.04, 0.96, '\n'.join(text), transform=ax.transAxes, va='top', ha='left',
                zorder=5, **font)


def draw_labels(ax, node, x, y, name, secondary):
    show = []
    if get(node, 'showx', False):
        show.append('x')
    if get(node, 'showy', False):
        show.append('y')
    if get(node, 'showname', False):
        show.append('n')
    if not show:
        return
    code = get(node, 'numfmt')
    offset = {'r': (5, 0), 'l': (-5, 0), 't': (0, 5), 'b': (0, -5), 'ctr': (0, 0)}.get(
        get(node, 'pos', 'r'), (5, 0))
    align = {'r': 'left', 'l': 'right'}.get(get(node, 'pos', 'r'), 'center')
    font = font_args(node.kvr('font'), height=9)
    font.pop('fontstyle', None)
    for xv, yv in zip(x, y):
        parts = []
        for item in show:
            parts.append(format_number(xv, code) if item == 'x' else
                         format_number(yv, code) if item == 'y' else name or '')
        ax.annotate(', '.join(parts), (xv, yv), textcoords='offset points', xytext=offset,
                    ha=align, va='center', zorder=6, **font)


def draw_series(ax, node, position, chart_style, values, handles, labels):
    """Draw one series on `ax`; returns (x, y)."""
    x, y = series_data(node, values)
    shade = PALETTE[position % len(PALETTE)]
    line_record = node.kvr('line')
    if line_record is not None and line_record.kvr('color'):
        shade = line_record.kvr('color')
    if line_record is None and chart_style in ('marker', 'none'):
        line_record = xlchart.rec(none=True)
    marker_record = node.kvr('marker')
    default_symbol = 'none' if chart_style in ('line', 'smooth') else 'circle'
    symbol = field(marker_record, 'symbol', default_symbol)
    style = line_style(line_record, shade, 2.25)
    smooth = node.kvr('smooth')
    if smooth is None:
        smooth = chart_style in ('smooth', 'smoothMarker')
    name = series_label(node, values)
    marker_args = {}
    if symbol != 'none':
        fill = field(marker_record, 'fill', shade)
        marker_args = dict(marker=MARKERS.get(symbol, 'o'),
                           markersize=float(field(marker_record, 'size', 5)),
                           markerfacecolor=resolve_color(fill),
                           markeredgecolor=resolve_color(field(marker_record, 'linecolor', fill)),
                           markeredgewidth=float(field(marker_record, 'linewidth', 0.75)))
    if smooth and len(x) > 2 and style.get('linestyle') != 'None':
        sx, sy = catmull_rom(x, y)
        ax.plot(sx, sy, zorder=3, **style)                          # the curve
        ax.plot(x, y, zorder=4, **{**style, 'linestyle': 'None'}, **marker_args)  # points
        handle = ax.plot([], [], **style, **marker_args)[0]         # legend entry
    else:
        handle, = ax.plot(x, y, zorder=3, **style, **marker_args)
    if name is not None:
        handles.append(handle)
        labels.append(name)
    if node.kvr('xerr') is not None:
        draw_error_bars(ax, node.kvr('xerr'), 'x', x, y, shade, values)
    if node.kvr('yerr') is not None:
        draw_error_bars(ax, node.kvr('yerr'), 'y', x, y, shade, values)
    if node.kvr('trend') is not None and len(x) > 1:
        draw_trend(ax, node.kvr('trend'), x, y, shade, handles, labels, name or 'series')
    if node.kvr('labels') is not None:
        draw_labels(ax, node.kvr('labels'), x, y, name, ax)
    return x, y


# -------------------------------------------------------------------------- the chart ---
def chart_figure(chart, values=None, width=640, height=400):
    """The matplotlib Figure of a chart node. `values(ref)` supplies the cell values."""
    logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
    series_node = chart.kvr('series')
    nodes = [] if series_node is None else series_node.nodes()
    style = get(chart, 'style', 'lineMarker')
    area = chart.kvr('chartarea')
    plot = chart.kvr('plotarea')
    figure = Figure(figsize=(width / 96.0, height / 96.0), dpi=96, layout='constrained')
    figure.patch.set_facecolor(resolve_color(field(get(area, 'fill'), 'color', 'FFFFFF'))
                               if not field(get(area, 'fill'), 'none', False) else 'none')
    edge = get(area, 'line')
    figure.patch.set_edgecolor(resolve_color(field(edge, 'color', 'D9D9D9'))
                               if not field(edge, 'none', False) else 'none')
    figure.patch.set_linewidth(float(field(edge, 'width', 0.75)))
    ax = figure.subplots()
    ax.set_axisbelow(True)
    ax.set_facecolor(resolve_color(field(get(plot, 'fill'), 'color', 'FFFFFF'))
                     if get(plot, 'fill') is not None and not get(plot, 'fill').kvr('none')
                     else 'none')
    secondary = [node for node in nodes if get(node, 'axis', 1) == 2]
    ax2 = ax.twinx() if secondary else None
    for spine in ax.spines.values():
        spine.set_visible(False)
    handles = []
    labels = []
    drawn = {1: [], 2: []}
    for position, node in enumerate(nodes):
        target = ax2 if get(node, 'axis', 1) == 2 else ax
        x, y = draw_series(target, node, position, style, values, handles, labels)
        drawn[2 if target is ax2 else 1].append((x, y))

    def collect(group, index):
        arrays = [pair[index] for pair in group if len(pair[index])]
        return np.concatenate(arrays) if arrays else np.array([])

    xnode = chart.kvr('xaxis')
    ynode = chart.kvr('yaxis')
    xdata = np.concatenate([collect(drawn[1], 0), collect(drawn[2], 0)])
    xinfo = axis_info(xnode, xdata)
    yinfo = axis_info(ynode, collect(drawn[1], 1))
    apply_axis(ax, 'x', xnode, xinfo, crossing_value(yinfo, ynode), yinfo, 'primary')
    apply_axis(ax, 'y', ynode, yinfo, crossing_value(xinfo, xnode), xinfo, 'primary')
    if ax2 is not None:
        y2node = chart.kvr('y2axis')
        y2info = axis_info(y2node, collect(drawn[2], 1))
        for spine in ax2.spines.values():
            spine.set_visible(False)
        ax2.spines['right'].set_visible(True)
        ax2.set_xlim(ax.get_xlim())
        apply_axis(ax2, 'y', y2node, y2info, xinfo.high, xinfo, 'secondary')
        ax2.tick_params(axis='x', which='both', length=0, labelbottom=False)
        ax2.set_axisbelow(True)

    title = chart.kvr('title')
    if title is not None and title.kvr('text') is not None:
        args = font_args(title.kvr('font'), height=14)
        figure.suptitle(mathtext(title.kvr('text')), **args)
    legend = chart.kvr('legend')
    if legend is not None and handles:
        hide = {int(number) - 1 for number in (get(legend, 'hide', []) or [])}
        keep = [i for i in range(len(handles)) if i not in hide]
        position = get(legend, 'pos', 'r')
        place = {'r': 'outside center right', 'l': 'outside center left',
                 't': 'outside upper center', 'b': 'outside lower center',
                 'tr': 'upper right'}[position]
        font = font_args(legend.kvr('font'), height=9)
        keywords = dict(fontsize=font['fontsize'], labelcolor=font['color'])
        fill = legend.kvr('fill')
        line = legend.kvr('line')
        keywords['frameon'] = bool((fill is not None and not fill.kvr('none'))
                                   or (line is not None and not line.kvr('none')))
        layout = legend.kvr('layout')
        if get(legend, 'overlay', False) and layout is not None:
            box = (field(layout, 'x', 0.7), 1 - field(layout, 'y', 0.1) - field(layout, 'h', 0.2))
            figure.legend([handles[i] for i in keep], [labels[i] for i in keep],
                          loc='lower left', bbox_to_anchor=box,
                          bbox_transform=figure.transFigure, **keywords)
        elif position == 'tr':
            ax.legend([handles[i] for i in keep], [labels[i] for i in keep], loc=place,
                      **keywords)
        else:
            figure.legend([handles[i] for i in keep], [labels[i] for i in keep], loc=place,
                          **keywords)
    return figure


def chart_svg(chart, values=None, width=640, height=400, inline=False):
    """The chart as SVG text. inline=True drops the XML prolog and the fixed size, so the
    SVG scales inside an HTML page."""
    with rc_context({'svg.fonttype': 'none', 'svg.hashsalt': 'xlw',
                     'font.family': 'sans-serif',
                     'font.sans-serif': ['Calibri', 'Carlito', 'Arial', 'DejaVu Sans'],
                     'axes.unicode_minus': False, 'mathtext.default': 'regular'}):
        figure = chart_figure(chart, values, width, height)
        buffer = io.StringIO()
        # no timestamp (same chart, same bytes) and no matplotlib version / web address
        figure.savefig(buffer, format='svg', metadata={'Date': None, 'Creator': 'svgchart'})
    text = buffer.getvalue()
    return inline_svg(text) if inline else text


def inline_svg(text):
    """An SVG document as an element to embed in HTML: no XML prolog or doctype, and the
    fixed width and height replaced by a style, so the picture scales with its container
    (the viewBox stays)."""
    text = text[text.index('<svg'):]
    return re.sub(r'\swidth="[^"]*"\sheight="[^"]*"', ' style="max-width:100%;height:auto"',
                  text, count=1)
