"""
xlstyle -- cell styles for xlw: properties, colours, borders, named styles, styles.xml.

Why
    A cell carries only the style properties that differ from the default, so a
    sheet of plain cells stays small. Everything that turns a style request into a
    resolved style, and a set of resolved styles into styles.xml, lives here.

Algorithm
    A resolved style is a dict of the 17 properties in STYLEPROPS. A request is
    defaults <- a named style (if given) <- key/value overrides. Colours are
    normalised to six hex digits, a border to a tuple of (edge, style, color).
    At save time each distinct style is charged to a kv table (style key -> xf
    index) and styles.xml is built from the distinct styles only: fonts, fills,
    borders and number formats are each de-duplicated again on their own projection,
    because OOXML keeps those tables separate.

Use
    from xlstyle import resolve_style, auto_numfmt, build_style_tables
    style = resolve_style(sheet_node, ['Heading1'], {'sz': 20})   # a dict
    xml = build_style_tables([DEFAULTS_COPY, style])              # styles.xml text

    Named styles live in the tree: load_defaults(styles_node) reads
    defaults/styles.txt into one node per style, holding only the leaves that differ
    from the file's 'default' block. register_style() adds one by hand.

    Border grammar: 'nesw' (all four edges, thin), 'all:medium', or per edge
    'n:medium,s:double'. Edges n s e w are top, bottom, right, left.

Versions
    M01  m01.v01  2026-10-31  ported from xlw.m v1.19. Fixed on the way: the built-in
                              number-format ids (xlw.m took index - 1, which sent
                              '0%' and '0.##E+00' to Excel's currency ids 5 to 8).
"""

import math
import os

from xlstore import KV

__all__ = ['STYLEPROPS', 'DEFAULTS', 'safe_name', 'color2hex', 'normalise_border',
           'border_key', 'resolve_style', 'style_delta', 'style_key', 'auto_numfmt',
           'register_style', 'load_defaults', 'find_style', 'is_style_prop',
           'build_style_tables', 'num_text', 'xml_escape']

STYLEPROPS = ('font', 'sz', 'bold', 'italic', 'underline', 'strikethrough',
              'fill', 'color', 'halign', 'valign', 'numfmt', 'wrap',
              'indent', 'shrink', 'rotation', 'border', 'bcolor')

# valign defaults to 'top', a deliberate departure from Excel's 'bottom' (xlw design:
# tables read better top-aligned). Treat DEFAULTS as a constant; copy it to change it.
DEFAULTS = {'font': 'Calibri', 'sz': 11, 'bold': False, 'italic': False,
            'underline': False, 'strikethrough': False, 'fill': '',
            'color': '000000', 'halign': '', 'valign': 'top', 'numfmt': '',
            'wrap': False, 'indent': 0, 'shrink': False, 'rotation': 0,
            'border': (), 'bcolor': '000000'}

BOOL_PROPS = ('bold', 'italic', 'underline', 'strikethrough', 'wrap', 'shrink')
NUMBER_PROPS = ('sz', 'indent', 'rotation')
COLOR_PROPS = ('color', 'fill', 'bcolor')
HEXDIGITS = '0123456789abcdefABCDEF'

NAMED_COLORS = {'red': 'FF0000', 'green': '008000', 'blue': '0000FF',
                'black': '000000', 'white': 'FFFFFF', 'yellow': 'FFFF00',
                'cyan': '00FFFF', 'magenta': 'FF00FF', 'gray': '808080',
                'grey': '808080', 'orange': 'FFA500'}

# Excel's own ids for the number formats it knows by code; everything else is custom.
BUILTIN_FORMATS = {'0': 1, '0.00': 2, '#,##0': 3, '#,##0.00': 4, '0%': 9,
                   '0.00%': 10, '0.00E+00': 11}

EDGE_ORDER = 'nsew'
EDGE_TAGS = {'n': 'top', 's': 'bottom', 'e': 'right', 'w': 'left'}

# Characters XML 1.0 cannot carry; Excel refuses a file that contains one.
BAD_XML = dict.fromkeys(list(range(0, 9)) + [11, 12] + list(range(14, 32)))


def xml_escape(text):
    """Text safe inside an XML element or a double-quoted attribute."""
    text = str(text).translate(BAD_XML)
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return text.replace('"', '&quot;').replace("'", '&apos;')


def num_text(value):
    """A number as XML text: 11 not 11.0, and full precision for the rest."""
    if isinstance(value, bool):
        return '1' if value else '0'
    if isinstance(value, int):
        return str(value)
    if float(value).is_integer() and abs(value) < 1e15:
        return str(int(value))
    return '%.15g' % value


def safe_name(name):
    """A sheet or book name as a tree key: letters, digits and _ only, starting with
    a letter (a name that does not gets the prefix s_)."""
    text = ''.join(ch if (ch.isascii() and ch.isalnum()) or ch == '_' else '_'
                   for ch in str(name))
    if not text or not text[0].isalpha() or not text[0].isascii():
        text = 's_' + text
    return text


def color2hex(value):
    """Any colour spec as six uppercase hex digits ('' stays ''). Accepts 'RRGGBB',
    '#RRGGBB', 'RGB', a few colour names, or an (r, g, b) triple (0-1 or 0-255)."""
    if value is None:
        return ''
    if isinstance(value, str):
        text = value.strip()
        if len(text) == 6 and all(ch in HEXDIGITS for ch in text):
            return text.upper()          # fast path: the default and named-style values
        if not text:
            return ''
        if text[0] == '#':
            text = text[1:]
        if text.lower() in NAMED_COLORS:
            return NAMED_COLORS[text.lower()]
        if len(text) == 3 and all(ch in HEXDIGITS for ch in text):
            return (text[0] * 2 + text[1] * 2 + text[2] * 2).upper()
        return text.upper()
    if isinstance(value, (list, tuple)) and len(value) == 3:
        parts = list(value)
        if max(parts) <= 1:
            parts = [round(part * 255) for part in parts]
        return '%02X%02X%02X' % tuple(int(round(part)) for part in parts)
    return ''


def normalise_border(spec, bcolor='000000'):
    """Any border spec as a tuple of (edge, style, color) triples; () means none.
    Idempotent: a tuple in gives an equivalent tuple out."""
    if not bcolor:
        bcolor = '000000'
    if spec is None or spec == '' or spec == ():
        return ()
    if not isinstance(spec, str):
        triples = []
        for item in spec:
            if isinstance(item, dict):
                parts = [item['edge'], item.get('style', 'thin'), item.get('color', '')]
            else:
                parts = list(item)
            edge = str(parts[0]).lower()
            style = str(parts[1]) if len(parts) > 1 else 'thin'
            color = parts[2] if len(parts) > 2 and parts[2] else bcolor
            triples.append((edge, style, color))
        return tuple(triples)
    triples = []
    for segment in spec.split(','):
        segment = segment.strip()
        if not segment:
            continue
        parts = segment.split(':')
        edges = parts[0].strip()
        if edges.lower() == 'all':
            edges = 'nesw'
        style = 'thin'
        if len(parts) >= 2 and parts[1].strip():
            style = parts[1].strip().lower()
        for edge in edges.lower():
            if edge in EDGE_ORDER:
                triples.append((edge, style, bcolor))
    return tuple(triples)


def border_key(border):
    """A canonical string for a border: edges sorted into n, s, e, w order."""
    if not border:
        return ''
    ranked = sorted(border, key=lambda item: EDGE_ORDER.find(item[0]) % 99)
    return '|'.join(f'{edge}:{style}:{color}' for edge, style, color in ranked)


def border_edge_xml(border, edge):
    tag = EDGE_TAGS[edge]
    for item in border:
        if item[0] == edge:
            color = item[2] or '000000'
            return f'<{tag} style="{item[1]}"><color rgb="FF{color}"/></{tag}>'
    return f'<{tag}/>'


def border_xml(border):
    """One <border> element. OOXML fixes the child order left, right, top, bottom,
    diagonal, and Excel wants all five present (an absent edge is an empty tag)."""
    return ('<border>' + border_edge_xml(border, 'w') + border_edge_xml(border, 'e')
            + border_edge_xml(border, 'n') + border_edge_xml(border, 's')
            + '<diagonal/></border>')


def is_style_prop(key):
    return str(key).lower() in STYLEPROPS or str(key).lower() == 'style'


def norm_value(prop, value):
    """One property value in its stored form: bool, int-or-float, or text."""
    if prop in BOOL_PROPS:
        return bool(value)
    if prop in NUMBER_PROPS:
        number = float(value)
        return int(number) if number.is_integer() else number
    if prop in COLOR_PROPS:
        return color2hex(value)
    if prop == 'border':
        return value
    return '' if value is None else str(value)


def merge_style_node(style, node):
    """Overlay the leaves a named-style node carries onto a resolved style."""
    for prop in STYLEPROPS:
        value = node.kvr(prop)
        if value is not None:
            style[prop] = value


def find_style(sheet, name):
    """The named-style node, looking in the book first and then in the root."""
    key = safe_name(name)
    current = sheet.parent()
    while current is not None:
        priv = current.kvr('priv')
        if priv is not None:
            styles = priv.kvr('styles')
            if styles is not None:
                found = styles.kvr(key)
                if found is not None:
                    return found
        current = current.parent()
    return None


def resolve_style(sheet, args=(), overrides=None):
    """defaults <- named base <- overrides, as a dict. args is the positional list
    after the value: an optional style name, then key, value pairs. overrides is a
    dict of the same pairs (keyword arguments)."""
    style = dict(DEFAULTS)
    args = list(args)
    pairs = []
    if args and isinstance(args[0], str) and not is_style_prop(args[0]):
        node = find_style(sheet, args[0])
        if node is not None:
            merge_style_node(style, node)
            args = args[1:]
    for index in range(0, len(args) - 1, 2):
        pairs.append((args[index], args[index + 1]))
    if overrides:
        pairs.extend(overrides.items())
    for key, value in pairs:
        key = str(key).lower()
        if key == 'style':
            node = find_style(sheet, value)
            if node is not None:
                merge_style_node(style, node)
        elif key in style:
            style[key] = value
    for prop in STYLEPROPS:
        if prop == 'border':
            continue
        style[prop] = norm_value(prop, style[prop])
    style['border'] = normalise_border(style['border'], style['bcolor'])
    return style


def style_delta(style):
    """The properties that differ from DEFAULTS, as a dict (what a cell stores)."""
    return {prop: style[prop] for prop in STYLEPROPS if style[prop] != DEFAULTS[prop]}


def value_text(value):
    if isinstance(value, bool):
        return 'T' if value else 'F'
    if isinstance(value, (int, float)):
        return num_text(value)
    if isinstance(value, tuple):
        return border_key(value)
    return str(value)


def style_key(delta):
    """A canonical dedup key over the non-default properties: two cells share a
    cellXf only when every one of these matches. Starts with a letter, never '('."""
    return 'x:' + '|'.join(f'{prop}={value_text(delta[prop])}' for prop in sorted(delta))


def auto_numfmt(value):
    """A sigfig-aware Excel format code for a number (log means log10)."""
    if not math.isfinite(value) or value == 0:
        return ''
    magnitude = abs(value)
    if magnitude == math.floor(magnitude) and magnitude < 1e7:
        return '0'
    if 0.01 <= magnitude < 1e5:
        places = max(0, 3 - math.floor(math.log10(magnitude)) - 1)
        return '0' if places == 0 else '0.' + '#' * places
    return '0.##E+00'


# ---------------------------------------------------------------- named styles ------
def register_style(styles, name, block, base=None):
    """One named-style node under `styles`, holding only the leaves that differ from
    `base` (default: DEFAULTS). `block` is a dict of properties."""
    base = DEFAULTS if base is None else base
    node = styles.node(safe_name(name))
    for prop in STYLEPROPS:
        if prop in block and (prop not in base or block[prop] != base[prop]):
            node.kvw(prop, block[prop])
    return node


def parse_style_value(key, text):
    if key in BOOL_PROPS:
        return text.strip().lower() == 'true'
    if key in NUMBER_PROPS:
        try:
            number = float(text)
        except ValueError:
            return 0
        return int(number) if number.is_integer() else number
    return text


def parse_styles_file(path):
    """'name' header lines followed by indented 'key:value' lines. Comments (%) and
    blank lines are ignored. Returns the names and one dict of properties per name."""
    names = []
    blocks = []
    with open(path, encoding='utf-8') as handle:
        lines = handle.read().splitlines()
    for raw in lines:
        if '%' in raw:
            raw = raw[:raw.index('%')]
        if not raw.strip():
            continue
        if not raw[0].isspace() and ':' not in raw:
            names.append(raw.strip())
            blocks.append({})
        elif blocks and ':' in raw:
            key, _, rest = raw.strip().partition(':')
            key = key.strip()
            blocks[-1][key] = parse_style_value(key, rest.strip())
    return names, blocks


FALLBACK_STYLES = (('Heading1', {'sz': 15, 'bold': True}),
                   ('Heading2', {'sz': 13, 'bold': True}),
                   ('Title', {'font': 'Cambria', 'sz': 18, 'bold': True}),
                   ('Good', {'fill': 'C6EFCE', 'color': '006100'}),
                   ('Bad', {'fill': 'FFC7CE', 'color': '9C0006'}),
                   ('Neutral', {'fill': 'FFEB9C', 'color': '9C6500'}))


def load_defaults(styles, path=None):
    """Fill the named-style node from defaults/styles.txt (beside this file); a small
    built-in set is used when the file is absent. Heading_N is also reachable as
    HeadingN."""
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'defaults',
                            'styles.txt')
    if not os.path.isfile(path):
        for name, block in FALLBACK_STYLES:
            register_style(styles, name, block)
        return
    names, blocks = parse_styles_file(path)
    lowered = [name.lower() for name in names]
    if 'default' not in lowered:
        for name, block in FALLBACK_STYLES:
            register_style(styles, name, block)
        return
    base_index = lowered.index('default')
    base = dict(DEFAULTS)
    base.update(blocks[base_index])
    base['border'] = normalise_border(base['border'], base['bcolor'])
    for index, name in enumerate(names):
        if index == base_index:
            continue
        block = dict(blocks[index])
        if 'border' in block:
            block['border'] = normalise_border(block['border'],
                                               block.get('bcolor', base['bcolor']))
        register_style(styles, name, block, base)
        if name.startswith('Heading') and '_' in name:
            register_style(styles, name.replace('_', ''), block, base)


# ------------------------------------------------------------------- styles.xml ------
def build_style_tables(styles):
    """styles.xml from the distinct resolved styles (a list of dicts, xf index =
    position). Fonts, fills, number formats and borders are de-duplicated again on
    their own projection, through kv tables."""
    if not styles:
        styles = [dict(DEFAULTS)]
    count = len(styles)

    fonts = []
    font_index = KV()
    font_of = [0] * count
    for n, style in enumerate(styles):
        key = 'f:' + '|'.join(value_text(style[prop]) for prop in (
            'font', 'sz', 'bold', 'italic', 'underline', 'strikethrough', 'color'))
        found = font_index.kvr(key)
        if found is None:
            found = len(fonts)
            font_index.kvw(key, found)
            fonts.append(style)
        font_of[n] = found

    fills = ['', '']                         # ids 0 and 1 are reserved by Excel
    fill_index = KV()
    fill_of = [0] * count
    for n, style in enumerate(styles):
        color = style['fill']
        if not color:
            fill_of[n] = 0
            continue
        found = fill_index.kvr('c:' + color)
        if found is None:
            found = len(fills)
            fill_index.kvw('c:' + color, found)
            fills.append(color)
        fill_of[n] = found

    custom_formats = []
    format_index = KV()
    format_of = [0] * count
    next_id = 164
    for n, style in enumerate(styles):
        code = style['numfmt']
        if not code:
            continue
        if code in BUILTIN_FORMATS:
            format_of[n] = BUILTIN_FORMATS[code]
            continue
        found = format_index.kvr('n:' + code)
        if found is None:
            found = next_id
            format_index.kvw('n:' + code, found)
            custom_formats.append((found, code))
            next_id += 1
        format_of[n] = found

    borders = [()]                           # index 0 is the empty border
    border_index = KV()
    border_of = [0] * count
    for n, style in enumerate(styles):
        key = border_key(style['border'])
        if not key:
            continue
        found = border_index.kvr('b:' + key)
        if found is None:
            found = len(borders)
            border_index.kvw('b:' + key, found)
            borders.append(style['border'])
        border_of[n] = found

    numfmt_xml = ''
    if custom_formats:
        items = ''.join(f'<numFmt numFmtId="{code_id}" formatCode="{xml_escape(code)}"/>'
                        for code_id, code in custom_formats)
        numfmt_xml = f'<numFmts count="{len(custom_formats)}">{items}</numFmts>'

    font_items = []
    for style in fonts:
        tags = ''
        if style['bold']:
            tags += '<b/>'
        if style['italic']:
            tags += '<i/>'
        if style['underline']:
            tags += '<u/>'
        if style['strikethrough']:
            tags += '<strike/>'
        font_items.append(f'<font>{tags}<sz val="{num_text(style["sz"])}"/>'
                          f'<color rgb="FF{style["color"]}"/>'
                          f'<name val="{xml_escape(style["font"])}"/></font>')
    fonts_xml = f'<fonts count="{len(fonts)}">' + ''.join(font_items) + '</fonts>'

    fill_items = ['<fill><patternFill patternType="none"/></fill>',
                  '<fill><patternFill patternType="gray125"/></fill>']
    for color in fills[2:]:
        fill_items.append('<fill><patternFill patternType="solid">'
                          f'<fgColor rgb="FF{color}"/><bgColor indexed="64"/>'
                          '</patternFill></fill>')
    fills_xml = f'<fills count="{len(fills)}">' + ''.join(fill_items) + '</fills>'

    borders_xml = (f'<borders count="{len(borders)}">'
                   + ''.join(border_xml(border) for border in borders) + '</borders>')

    xf_items = []
    for n, style in enumerate(styles):
        apply = ''
        if format_of[n]:
            apply += ' applyNumberFormat="1"'
        alignment = ''
        if (style['halign'] or style['valign'] or style['wrap'] or style['indent'] > 0
                or style['shrink'] or style['rotation'] != 0):
            attrs = ''
            if style['halign']:
                attrs += f' horizontal="{style["halign"]}"'
            if style['valign']:
                attrs += f' vertical="{style["valign"]}"'
            if style['wrap']:
                attrs += ' wrapText="1"'
            if style['indent'] > 0:
                attrs += f' indent="{num_text(style["indent"])}"'
            if style['shrink']:
                attrs += ' shrinkToFit="1"'
            if style['rotation'] != 0:
                # OOXML textRotation: 0-90 counter-clockwise, 91-180 clockwise
                # (90 + |deg|), 255 stacked text.
                rotation = style['rotation']
                if rotation != 255 and rotation < 0:
                    rotation = 90 - rotation
                attrs += f' textRotation="{num_text(rotation)}"'
            alignment = f'<alignment{attrs}/>'
            apply += ' applyAlignment="1"'
        border_flag = ' applyBorder="1"' if border_of[n] else ''
        xf_items.append(f'<xf numFmtId="{format_of[n]}" fontId="{font_of[n]}" '
                        f'fillId="{fill_of[n]}" borderId="{border_of[n]}" xfId="0" '
                        f'applyFont="1" applyFill="1"{border_flag}{apply}>'
                        f'{alignment}</xf>')

    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            + numfmt_xml + fonts_xml + fills_xml + borders_xml
            + '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" '
            'borderId="0"/></cellStyleXfs>'
            + f'<cellXfs count="{count}">' + ''.join(xf_items) + '</cellXfs>'
            + '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/>'
            '</cellStyles></styleSheet>')
