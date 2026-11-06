"""
xlformat -- cell formats: resolve the style of a write, and convert styles.xml both ways.

Why
    A cell's look is up to seventeen properties, and Excel stores each distinct look once in
    styles.xml. This module turns "write(v, 'Heading1', bold=True)" into the small set of
    properties that differ from the default, writes the distinct ones out as styles.xml, and
    reads them back from a file Excel made, so both directions share one property table.

Algorithm
    A style is a dict holding only the properties that differ from DEFAULTS (the default style
    is the empty dict, xf 0). resolve() builds one: the named style, then the positional pairs,
    then the keywords, each value normalised (bool, number, RRGGBB colour, border tuple); a value
    equal to its default is dropped. styles_xml() writes styles.xml from the list of styles: fonts,
    fills, number formats and borders are each de-duplicated on their own, through
    dict.setdefault(key, len(table)). read_styles() is the inverse: it resolves every cellXfs entry
    against fonts, fills, borders and number formats into the same dict form.
    Cost: O(distinct styles).

Use
    delta = resolve([book_styles, root_styles], ('Heading1', 'italic', True), {'fill': 'yellow'})
    resolve([], (), {'border': 'all:thin'})            # n e s w, or 'n:thin,s:double'
    root_styles = named_styles()                       # the built-in named styles, a fresh dict
    border_delta('all:thin', {'color': 'red'})         # the changes the border verb applies to a cell
    styles_xml(list_of_styles) -> the styles.xml part;  read_styles(root_element, notes) -> list of styles
    Properties: font sz bold italic underline strikethrough fill color halign valign numfmt
    wrap indent shrink rotation border bcolor. valign defaults to 'top' (Excel: 'bottom').
    Border: edges n s e w (top bottom right left), styles thin medium double ...

VERSION  M01 m01.v01 (2026-11-06): first version; one property table drives resolve, write and
         read, and the named styles are a built-in table in place of a defaults file.
"""
from xltext import safe_name, tag

__all__ = ['resolve', 'named_styles', 'border_delta', 'styles_xml', 'read_styles']

DEFAULTS = {'font': 'Calibri', 'sz': 11, 'bold': False, 'italic': False, 'underline': False,
            'strikethrough': False, 'fill': '', 'color': '000000', 'halign': '',
            'valign': 'top', 'numfmt': '', 'wrap': False, 'indent': 0, 'shrink': False,
            'rotation': 0, 'border': (), 'bcolor': '000000'}
BOOLS = ('bold', 'italic', 'underline', 'strikethrough', 'wrap', 'shrink')
NUMBERS = ('sz', 'indent', 'rotation')
COLORS = ('color', 'fill', 'bcolor')
FONT_PROPS = ('font', 'sz', 'bold', 'italic', 'underline', 'strikethrough', 'color')
FONT_FLAGS = (('b', 'bold'), ('i', 'italic'), ('u', 'underline'), ('strike', 'strikethrough'))
HEX = frozenset('0123456789abcdefABCDEF')
NAMED_COLORS = {'red': 'FF0000', 'green': '008000', 'blue': '0000FF', 'black': '000000',
                'white': 'FFFFFF', 'yellow': 'FFFF00', 'cyan': '00FFFF', 'magenta': 'FF00FF',
                'gray': '808080', 'grey': '808080', 'orange': 'FFA500'}
BUILTIN_FORMATS = {'0': 1, '0.00': 2, '#,##0': 3, '#,##0.00': 4, '0%': 9, '0.00%': 10,
                   '0.00E+00': 11, 'mm-dd-yy': 14, 'd-mmm-yy': 15, 'd-mmm': 16, 'mmm-yy': 17,
                   'h:mm AM/PM': 18, 'h:mm:ss AM/PM': 19, 'h:mm': 20, 'h:mm:ss': 21,
                   'm/d/yy h:mm': 22, 'mm:ss': 45, '[h]:mm:ss': 46, 'mmss.0': 47,
                   '##0.0E+0': 48, '@': 49}
FORMAT_CODES = {number: code for code, number in BUILTIN_FORMATS.items()}
EXCEL_THEME = ('FFFFFF', '000000', 'E7E6E6', '44546A', '4472C4', 'ED7D31', 'A5A5A5', 'FFC000',
               '5B9BD5', '70AD47')
SYSTEM_COLORS = {'64': '000000', '8': '000000', '9': 'FFFFFF'}
EDGES = {'n': 'top', 's': 'bottom', 'e': 'right', 'w': 'left'}
BOX = 'n:thin,e:thin,s:thin,w:thin'
NAMED_SOURCE = {
    'Heading_1': {'sz': 15, 'bold': True}, 'Heading_2': {'sz': 13, 'bold': True},
    'Heading_3': {'bold': True}, 'Heading_4': {'underline': True},
    'Good': {'fill': 'C6EFCE', 'color': '006100'}, 'Bad': {'fill': 'FFC7CE', 'color': '9C0006'},
    'Neutral': {'fill': 'FFEB9C', 'color': '9C6500'},
    'Title': {'font': 'Cambria', 'sz': 18, 'bold': True},
    'Total': {'bold': True, 'border': 'n:thin,s:double'},
    'Input': {'fill': 'FFCC99', 'color': '3F3F76', 'border': BOX, 'bcolor': '7F7F7F'},
    'Output': {'bold': True, 'fill': 'F2F2F2', 'color': '3F3F3F', 'border': BOX,
               'bcolor': '3F3F3F'},
    'Calculation': {'bold': True, 'fill': 'F2F2F2', 'color': 'FA7D00', 'border': BOX,
                    'bcolor': '7F7F7F'},
    'Check_Cell': {'bold': True, 'fill': 'A5A5A5', 'color': 'FFFFFF',
                   'border': 'n:double,e:double,s:double,w:double', 'bcolor': '3F3F3F'},
    'Linked_Cell': {'color': 'FA7D00', 'border': 's:double', 'bcolor': 'FF8001'},
    'Note': {'fill': 'FFFFCC', 'border': BOX, 'bcolor': 'B2B2B2'},
    'Warning_Text': {'color': 'FF0000'}, 'Explanatory_Text': {'italic': True, 'color': '7F7F7F'}}


def color2hex(value):
    """Any colour spec as six uppercase hex digits ('' stays ''): 'RRGGBB', '#RRGGBB', 'RGB',
    a colour name, or an (r, g, b) triple of 0-1 or 0-255."""
    if isinstance(value, (list, tuple)) and len(value) == 3:
        parts = [part * 255 for part in value] if max(value) <= 1 else value
        return '%02X%02X%02X' % tuple(int(round(part)) for part in parts)
    text = str(value or '').strip().lstrip('#')
    if text.lower() in NAMED_COLORS:
        return NAMED_COLORS[text.lower()]
    if len(text) == 3 and set(text) <= HEX:
        text = ''.join(char * 2 for char in text)
    return text.upper()


def edge_border(spec, bcolor='000000'):
    """Any border spec as a tuple of (edge, style, color) triples; () means none.
    'all:thin' or 'n:thin,s:double' or a sequence of triples or dicts; idempotent, and the edges
    come out in the order n s e w, so equal borders compare equal."""
    if not spec:
        return ()
    triples = []
    for item in spec.split(',') if isinstance(spec, str) else spec:
        if isinstance(item, str):
            edges, _, style = item.strip().partition(':')
            edges = 'nesw' if edges.lower() == 'all' else edges.lower()
            triples += [(edge, style.strip().lower() or 'thin', bcolor)
                        for edge in edges if edge in EDGES]
            continue
        if isinstance(item, dict):
            item = (item['edge'], item.get('style', 'thin'), item.get('color', ''))
        parts = list(item) + ['', 'thin', ''][len(item):]
        triples.append((str(parts[0]).lower(), str(parts[1]), parts[2] or bcolor))
    return tuple(sorted(triples, key=lambda triple: 'nsew'.find(triple[0])))


def normal(prop, value, bcolor):
    """One property value in its stored form: bool, int-or-float, RRGGBB, border tuple, text."""
    if prop in BOOLS:
        return bool(value)
    if prop in NUMBERS:
        number = float(value)
        return int(number) if number.is_integer() else number
    if prop in COLORS:
        return color2hex(value)
    if prop == 'border':
        return edge_border(value, bcolor)
    return '' if value is None else str(value)


def is_prop(key):
    """True when `key` names a style property, or is 'style' (a named style)."""
    return str(key).lower() in DEFAULTS or str(key).lower() == 'style'


def found_style(styles, name):
    """The named style `name` (as a tree key) in the first of the dicts `styles` that has it, else {}."""
    key = safe_name(name)
    return next((table[key] for table in styles if key in table), {})


def resolve(styles, args=(), keywords=None):
    """The style of a write as a dict of the properties that differ from DEFAULTS.
    args: an optional named style, then property/value pairs; keywords: more pairs;
    styles: a list of dicts of named styles, searched in order (an unknown name adds nothing)."""
    args = list(args)
    delta = {}
    if args and isinstance(args[0], str) and not is_prop(args[0]):
        delta.update(found_style(styles, args.pop(0)))
    for key, value in list(zip(args[::2], args[1::2])) + list((keywords or {}).items()):
        if str(key).lower() == 'style':
            delta.update(found_style(styles, value))
        elif str(key).lower() in DEFAULTS:
            delta[str(key).lower()] = value
    full = {**DEFAULTS, **delta}
    full = {prop: normal(prop, full[prop], full['bcolor']) for prop in DEFAULTS}
    return {prop: value for prop, value in full.items() if value != DEFAULTS[prop]}


def named_styles():
    """The built-in named styles as a fresh dict of normalised style dicts; Heading_N is also
    reachable as HeadingN."""
    table = {}
    for name, block in NAMED_SOURCE.items():
        table[name] = resolve([], (), block)
        if name.startswith('Heading'):
            table[name.replace('_', '')] = table[name]
    return table


def border_delta(sides, options):
    """The changes the border verb applies to a cell: the border of `sides` (see edge_border) and,
    when `options` holds a 'color' or 'bcolor', its edge colour."""
    colors = [color2hex(value) for key, value in options.items()
              if str(key).lower() in ('color', 'bcolor')]
    bcolor = colors[-1] if colors else DEFAULTS['bcolor']
    changes = {'border': edge_border(sides, bcolor)}
    if bcolor != DEFAULTS['bcolor']:
        changes['bcolor'] = bcolor
    return changes


# ------------------------------------------------------------------ styles.xml out ----
def font_xml(style):
    """One <font> from the font properties of a full style."""
    flags = [tag(name) for name, prop in FONT_FLAGS if style[prop]]
    return tag('font', *flags, tag('sz', val=style['sz']),
               tag('color', rgb='FF' + style['color']), tag('name', val=style['font']))


def border_xml(border):
    """One <border>: OOXML fixes the order left right top bottom diagonal, all present."""
    sides = {edge: (style, color) for edge, style, color in border}
    parts = []
    for edge in 'wens':
        style, color = sides.get(edge, (None, None))
        parts.append(tag(EDGES[edge], tag('color', rgb='FF' + color) if style else '',
                         style=style))
    return tag('border', *parts, tag('diagonal'))


def align_xml(style):
    """The <alignment> of a full style ('' when it sets none)."""
    rotation = style['rotation']
    if rotation not in (0, 255) and rotation < 0:
        rotation = 90 - rotation
    attrs = {'horizontal': style['halign'] or None, 'vertical': style['valign'] or None,
             'wrapText': style['wrap'] or None, 'indent': style['indent'] or None,
             'shrinkToFit': style['shrink'] or None, 'textRotation': rotation or None}
    return tag('alignment', **attrs) if any(value is not None for value in attrs.values()) else ''


def styles_xml(styles):
    """styles.xml from the list of style dicts (position = the s attribute of a cell)."""
    fonts, fills, borders, formats = {}, {None: 0, 'gray125': 1}, {(): 0}, {}
    xfs = []
    for style in styles or [{}]:
        full = {**DEFAULTS, **style}
        font = fonts.setdefault(tuple(full[prop] for prop in FONT_PROPS), len(fonts))
        fill = fills.setdefault(full['fill'], len(fills)) if full['fill'] else 0
        border = borders.setdefault(full['border'], len(borders))
        code = full['numfmt']
        number = BUILTIN_FORMATS.get(code) or (
            formats.setdefault(code, 164 + len(formats)) if code else 0)
        align = align_xml(full)
        xfs.append(tag('xf', align, numFmtId=number, fontId=font, fillId=fill, borderId=border,
                       xfId=0, applyFont=1, applyFill=1, applyBorder=1 if border else None,
                       applyNumberFormat=1 if number else None,
                       applyAlignment=1 if align else None))
    fill_items = [tag('fill', tag('patternFill', patternType='none')),
                  tag('fill', tag('patternFill', patternType='gray125'))]
    fill_items += [tag('fill', tag('patternFill', tag('fgColor', rgb='FF' + color),
                                   tag('bgColor', indexed=64), patternType='solid'))
                   for color in list(fills)[2:]]
    font_items = [font_xml(dict(zip(FONT_PROPS, key))) for key in fonts]
    format_items = [tag('numFmt', numFmtId=number, formatCode=code)
                    for code, number in formats.items()]
    return tag(
        'styleSheet',
        tag('numFmts', *format_items, count=len(format_items)) if format_items else '',
        tag('fonts', *font_items, count=len(font_items)),
        tag('fills', *fill_items, count=len(fill_items)),
        tag('borders', *[border_xml(item) for item in borders], count=len(borders)),
        tag('cellStyleXfs', tag('xf', numFmtId=0, fontId=0, fillId=0, borderId=0), count=1),
        tag('cellXfs', *xfs, count=len(xfs)),
        tag('cellStyles', tag('cellStyle', name='Normal', xfId=0, builtinId=0), count=1),
        xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main')


# ------------------------------------------------------------------ styles.xml in -----
def sheet_color(element):
    """A spreadsheet colour element (<color>, <fgColor>) as RRGGBB, or '' when it cannot be
    mapped (indexed palette entries other than the system ones)."""
    if element is None:
        return ''
    if element.get('rgb'):
        return element.get('rgb')[-6:].upper()
    if element.get('theme') is not None:
        slot = int(element.get('theme'))
        return EXCEL_THEME[slot] if slot < len(EXCEL_THEME) else ''
    return SYSTEM_COLORS.get(element.get('indexed'), '')


def font_of(font):
    """The style properties of one <font> element."""
    size, name = font.find('sz'), font.find('name')
    info = {'font': name.get('val') if name is not None else 'Calibri',
            'sz': float(size.get('val')) if size is not None else 11}
    info.update({prop: font.find(element) is not None for element, prop in FONT_FLAGS})
    color = sheet_color(font.find('color'))
    return {**info, 'color': color} if color else info


def border_of(border):
    """(border tuple, edge colour) of one <border> element."""
    triples = []
    for edge, name in EDGES.items():
        side = border.find(name)
        if side is not None and side.get('style'):
            triples.append((edge, side.get('style'), sheet_color(side.find('color')) or '000000'))
    return tuple(triples), (triples[0][2] if triples else '000000')


def align_of(align):
    """The alignment properties of one <alignment> element."""
    rotation = int(align.get('textRotation', 0))
    return {'halign': align.get('horizontal', ''), 'valign': align.get('vertical', 'bottom'),
            'wrap': align.get('wrapText') in ('1', 'true'), 'indent': int(align.get('indent', 0)),
            'shrink': align.get('shrinkToFit') in ('1', 'true'),
            'rotation': 90 - rotation if 90 < rotation < 255 else rotation}


def fill_of(fill, notes):
    """The fill colour of one <fill> element ('' for none); an unmappable one is noted."""
    pattern = fill.find('patternFill')
    if pattern is None or pattern.get('patternType') != 'solid':
        return ''
    color = sheet_color(pattern.find('fgColor'))
    if not color:
        notes['a fill colour that is not RGB or theme was left out'] = True
    return color


def entry(table, xf, key, default):
    """The entry of `table` that attribute `key` of an <xf> points at, or `default`."""
    index = int(xf.get(key, 0))
    return table[index] if index < len(table) else default


def read_styles(root, notes):
    """The style dict of every cell format (cellXfs) of a parsed styles.xml. Things that
    cannot be mapped are added to the dict `notes`. A cell that states no vertical alignment
    is 'bottom', as in Excel (xlw4 itself defaults to 'top')."""
    codes = {**FORMAT_CODES, **{int(item.get('numFmtId')): item.get('formatCode')
                                for item in root.iter('numFmt')}}
    fonts = [font_of(item) for item in root.iter('font')]
    fills = [fill_of(item, notes) for item in root.iter('fill')]
    borders = [border_of(item) for item in root.iter('border')]
    deltas = []
    xfs = root.find('cellXfs')
    for xf in xfs if xfs is not None else []:
        number = int(xf.get('numFmtId', 0))
        style = {'valign': 'bottom', **entry(fonts, xf, 'fontId', {})}
        style['fill'] = entry(fills, xf, 'fillId', '')
        style['border'], style['bcolor'] = entry(borders, xf, 'borderId', ((), '000000'))
        if number in codes:
            style['numfmt'] = codes[number]
        elif number:
            notes[f'built-in number format {number} has no code here; left out'] = True
        if xf.find('alignment') is not None:
            style.update(align_of(xf.find('alignment')))
        deltas.append(resolve({}, (), style))
    return deltas or [{}]
