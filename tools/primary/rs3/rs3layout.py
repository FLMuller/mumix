r"""rs3layout.py -- the layout string of a page: [ftv 70dxh, [serverstatus wx50d ; log wxh]]

    tree = parse(text)            the layout as a tree; LayoutError (a ValueError) says where
    names(tree) -> [loc, ...]     the locators, in order of appearance
    plain(tree, has_default) -> str   the layout as text with every size a block's own default makes needless left out
    render(tree, html_of) -> str  the page body: html_of is {loc: html of that block}

Grammar
    group  :=  '[' item (sep item)* ']'     one kind of separator inside a group
    sep    :=  ','  (side by side, a row)  |  ';'  (one under the other, a column)
    item   :=  group [size]  |  loc [size]
    loc    :=  a block name, with digits to tell two of a kind apart: code, code2
    size   :=  WIDTH x HEIGHT   or   WIDTH . HEIGHT     (one value alone is the width)
    value  :=  [w|h] [number] [f] [d]
               a number is millimetres; none (w, h) fills what is left; f marks the number as a
               share of what is left (flexible); d makes the edge on that side draggable.
    Examples  wxh (fill both)   50dxh (50 mm wide, draggable, full height)   wx25d   w50d.h

In a row the width is the size along the row (the main size); in a column it is the height. A
main size of a number is a fixed size; of w or h it shares what is left; the other value is the
size across, which fills unless it is a number. The d of either value makes the main edge
draggable (the page script, manager.js, does the dragging). The bar is always between two items: after
the item that has the d, or, when it is the last of its group (`edit wxhd` under the code), before it, and
then the bar resizes that item the other way (dragging up makes it taller).

VERSION  M1 m01.v02 (2026-11-04): block_of, and plain: the layout without the sizes the blocks' own sizes make needless.
         M1 m01.v01 (2026-11-03): first version.
"""
import html
import re

__all__ = ['parse', 'names', 'block_of', 'render', 'plain', 'LayoutError']

TOKEN = re.compile(r'\s*(\[|\]|,|;|[^\s\[\],;]+)')
LOC = re.compile(r'^[a-z][a-z]*[0-9]*$')
DIM = re.compile(r'^(?P<lead>[wh])?(?P<num>\d+(?:\.\d+)?)?(?P<f>f)?(?P<d>d)?$')


class LayoutError(ValueError):
    """The layout string is not one."""


def dimension(text):
    """('mm', n, drag) | ('fill', share, drag) from one value of a size."""
    found = DIM.match(text)
    if not found or not text:
        raise LayoutError(f'{text!r} is not a size value')
    drag = bool(found.group('d'))
    num = found.group('num')
    if num is None:
        return ('fill', 1.0, drag)
    if found.group('f'):
        return ('fill', float(num), drag)
    return ('mm', float(num), drag)


def size_of(text):
    """(width, height) of a size word, each from dimension()."""
    parts = re.split(r'x|(?<=[a-z])\.', text, maxsplit=1)
    width = dimension(parts[0])
    height = dimension(parts[1]) if len(parts) > 1 and parts[1] else ('fill', 1.0, False)
    return width, height


def tokens(text):
    out = []
    at = 0
    text = text.strip()
    while at < len(text):
        found = TOKEN.match(text, at)
        if not found:
            raise LayoutError(f'unexpected text at {at}')
        out.append(found.group(1))
        at = found.end()
    return out


def parse(text):
    """The layout as {'kind': 'group', 'dir': 'row'|'col', 'items': [...], 'size'} and
    {'kind': 'cell', 'loc', 'size'}. A string with no bracket is one cell."""
    if not isinstance(text, str) or len(text) > 2000:
        raise LayoutError('the layout is a string of at most 2000 characters')
    toks = tokens(text)
    if not toks:
        raise LayoutError('the layout is empty')
    at = [0]
    seen = set()

    def peek():
        return toks[at[0]] if at[0] < len(toks) else None

    def take():
        word = peek()
        if word is None:
            raise LayoutError('the layout ends too soon')
        at[0] += 1
        return word

    def size():
        word = peek()
        if word is not None and word not in '[],;':
            at[0] += 1
            return size_of(word)
        return (('fill', 1.0, False), ('fill', 1.0, False))

    def item():
        word = take()
        if word == '[':
            return group()
        if word in ('],;'):
            raise LayoutError(f'unexpected {word!r}')
        if not LOC.match(word):
            raise LayoutError(f'{word!r} is not a block name')
        if word in seen:
            raise LayoutError(f'{word!r} appears twice: give the second a number (like {word}2)')
        seen.add(word)
        return {'kind': 'cell', 'loc': word, 'size': size()}

    def group():
        items = [item()]
        sep = None
        while peek() in (',', ';'):
            here = take()
            if sep is not None and here != sep:
                raise LayoutError('a group takes , or ; between its items, not both')
            sep = here
            items.append(item())
        if take() != ']':
            raise LayoutError('a group ends with ]')
        return {'kind': 'group', 'dir': 'col' if sep == ';' else 'row', 'items': items,
                'size': size()}

    tree = item()
    if peek() is not None:
        raise LayoutError(f'unexpected {peek()!r} after the layout')
    return tree


def block_of(loc):
    """The block of a locator: its name without the digits that tell two of a kind apart (code2 is a code block)."""
    return re.sub(r'\d+$', '', loc)


def names(tree):
    """The locators of a layout, in order."""
    if tree['kind'] == 'cell':
        return [tree['loc']]
    return [loc for sub in tree['items'] for loc in names(sub)]


def size_text(size):
    """The size word of a size: the inverse of size_of."""
    def one(dim, lead):
        kind, value, drag = dim
        base = (f'{value:g}' if kind == 'mm' else lead if value == 1.0 else f'{value:g}f')
        return base + ('d' if drag else '')
    return one(size[0], 'w') + 'x' + one(size[1], 'h')


def plain(tree, has_default, parent='col'):
    """The layout as text with the sizes that need not be said left out: a block that has a size of its own for
    the way it runs (has_default(loc, 'row' | 'col'): a width in a row, a height in a column) needs no `wdxh`, and a
    group or a block that fills needs no `wxh`. parse(plain(tree, ...)) lays out the same page."""
    fill = ('fill', 1.0, False)
    size = tree['size']
    if tree['kind'] == 'cell':
        main = size[0] if parent == 'row' else size[1]
        across = size[1] if parent == 'row' else size[0]
        needless = main[0] == 'fill' and main[1] == 1.0 and has_default(tree['loc'], parent) and across == fill
        if size == (fill, fill) or needless:
            return tree['loc']
        return tree['loc'] + ' ' + size_text(size)
    sep = ',' if tree['dir'] == 'row' else ';'
    text = '[' + sep.join(plain(sub, has_default, tree['dir']) for sub in tree['items']) + ']'
    return text if size == (fill, fill) else text + ' ' + size_text(size)


def style(size, direction):
    """The inline style that a size gives an item in a parent running in `direction`, and
    whether its main edge is draggable. In a row the main size is the width."""
    width, height = size
    main, across = (width, height) if direction == 'row' else (height, width)
    kind, value, _ = main
    flex = f'flex:0 0 {value:g}mm;' if kind == 'mm' else f'flex:{value:g} 1 0;'
    if across[0] == 'mm':
        prop = 'height' if direction == 'row' else 'width'
        flex += f'{prop}:{across[1]:g}mm;align-self:flex-start;'
    return flex, bool(width[2] or height[2])


def render(tree, html_of, parent='col', defaults=None, last=False):
    """The html of a layout. A cell is <div class="cell" data-loc=LOC>; the cells and groups with
    a draggable edge are followed by <div class="drag">. html_of is {loc: html of the block}.
    defaults is {loc: (width mm, height mm)}: what a block has in a row (its width) or in a column (its
    height) when the layout gives that size no number (`ftv`, `ftv wdxh`, `edit`), where otherwise it would
    fill, and that edge is draggable without a d (the bar goes before a last item, after the others); a number
    (`ftv 70dxh`) is always the layout's. A block with no size of its own is not in it."""
    size = tree['size']
    if defaults and tree['kind'] == 'cell' and tree['loc'] in defaults:
        given = defaults[tree['loc']][0 if parent == 'row' else 1]
        main = size[0] if parent == 'row' else size[1]
        if given and main[0] == 'fill' and main[1] == 1.0:
            main = ('mm', float(given), True)                  # a block's own size is draggable: the server puts the bar on its edge
            size = (main, size[1]) if parent == 'row' else (size[0], main)
    flex, drag = style(size, parent)
    if tree['kind'] == 'cell':
        loc = html.escape(tree['loc'])
        inner = html_of.get(tree['loc'], '')
        body = f'<div class="cell" data-loc="{loc}" style="{flex}">{inner}</div>'
    else:
        inner = ''.join(render(sub, html_of, tree['dir'], defaults, k == len(tree['items']) - 1)
                        for k, sub in enumerate(tree['items']))
        body = f'<div class="group {tree["dir"]}" style="{flex}">{inner}</div>'
    if drag:
        bar = f'<div class="drag {"v" if parent == "row" else "h"}{" before" if last else ""}"></div>'
        body = bar + body if last else body + bar            # between two items: a last item has it on its near side
    return body
