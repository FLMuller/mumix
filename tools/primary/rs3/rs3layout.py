r"""rs3layout.py -- the layout string of a page: [ftv 70dxh, [serverstatus wx50d ; log wxh]]

    tree = parse(text)            the layout as a tree; LayoutError (a ValueError) says where
    names(tree) -> [loc, ...]     the locators, in order of appearance
    blocks(tree) -> {loc: block}  the block each locator is: see LOCATORS
    normal(tree, given) -> (tree, {old: new})   the tree with its locators written the short way, for the address
    places(tree) -> {loc: [i, ...]}   where each locator sits: its index in each group on the way down
    receivers(tree) -> {loc: [loc, ...]}   the `blk{a,b}` lists: who a block's routed signals go to
    plain(tree, has_default) -> str   the layout as text with every size a block's own default makes needless left out
                                  (and the definitions of the locators that need them)
    render(tree, html_of) -> str  the page body: html_of is {loc: html of that block}

LOCATORS. A locator is the kind of block it is, a 2-3 letter short name or the block's name, then an optional
.suffix to tell two of a kind apart: `eb`, `eb.1`, `eb.notes`, `cd.2`, `ftv.py`. The short names are SHORT: tt toptabs,
mt methods, cd code, eb editbox (ftv, log and doc are short already; serverstatus, statusbar, options and search are
never written by a user). A name that is neither (`cd3`: digits with no . are not a suffix) is defined at the end of
the layout: `[ftv,[cd.1,cd3]]{cd3=code}`. The address is written the short way when a page has several blocks of a
kind (`mt`, `mt.2`) and the block's own name when it has one (`code`): normal() does that.

Grammar
    layout :=  item ['{' loc '=' kind (',' loc '=' kind)* '}']      the definitions come last
    group  :=  '[' item (sep item)* ']'     one kind of separator inside a group
    sep    :=  ','  (side by side, a row)  |  ';'  (one under the other, a column)
    item   :=  group [size]  |  loc ['{' loc (',' loc)* '}'] [size]
    loc    :=  kind ['.' word]        eb  eb.1  cd.notes  code
    size   :=  WIDTH x HEIGHT                      (one value alone is the width)
    value  :=  [w|h] [number] [f] [d]
               a number is millimetres; none (w, h) fills what is left; f marks the number as a
               share of what is left (flexible); d makes the edge on that side draggable.
    Examples  wxh (fill both)   50dxh (50 mm wide, draggable, full height)   wx25d   w50dxh

`eb{cd2}` says that the signals eb sends to one pane (a comment, a file to open) go to cd2 and not to the nearest
pane that takes them; every locator in a list is one of the layout's.

In a row the width is the size along the row (the main size); in a column it is the height. A
main size of a number is a fixed size; of w or h it shares what is left; the other value is the
size across, which fills unless it is a number. The d of either value makes the main edge
draggable (the page script, manager.js, does the dragging). The bar is always between two items: after
the item that has the d, or, when it is the last of its group (`edit wxhd` under the code), before it, and
then the bar resizes that item the other way (dragging up makes it taller).

VERSION  M2 m02.v01 (2026-11-04): locators are kind.suffix (SHORT names, definitions {cd3=code} at the end), blocks(), normal(); block_of is gone.
         M1 m01.v03 (2026-11-04): `blk{a,b}` receivers; places(), receivers(); plain keeps the lists.
         M1 m01.v02 (2026-11-04): block_of, and plain: the layout without the sizes the blocks' own sizes make needless.
         M1 m01.v01 (2026-11-03): first version.
"""
import html
import re

__all__ = ['parse', 'names', 'places', 'receivers', 'blocks', 'normal', 'render', 'plain', 'LayoutError']

TOKEN = re.compile(r'\s*(\[|\]|,|;|\{[^{}]*\}|[^\s\[\],;{}]+(?:\{[^{}]*\})?)')
LOC = re.compile(r'^[a-z][a-z0-9]*(?:\.[a-z0-9]+)*$')
SHORT = {'tt': 'toptabs', 'mt': 'methods', 'cd': 'code', 'eb': 'editbox'}       # a block's short name, for a page with several
WORD = re.compile(r'^([^{}]+)(?:\{([^{}]*)\})?$')
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
    parts = text.split('x', 1)
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


def kind_of(loc):
    """The block a locator names by itself: the part before the ., with a short name made the block's name."""
    word = loc.split('.')[0]
    return SHORT.get(word, word)


def parse(text, below=''):
    """The layout as {'kind': 'group', 'dir': 'row'|'col', 'items': [...], 'size', 'defs'} and
    {'kind': 'cell', 'loc', 'size', 'to', 'defs'}; the top of the tree holds the definitions {loc: block} written at
    the end of the text. A string with no bracket is one cell. `below` is a layout text put under it as the last row."""
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
        if word is not None and word not in '[],;' and not word.startswith('{'):
            at[0] += 1
            return size_of(word)
        return (('fill', 1.0, False), ('fill', 1.0, False))

    def item():
        word = take()
        if word == '[':
            return group()
        if word in ('],;'):
            raise LayoutError(f'unexpected {word!r}')
        found = WORD.match(word)
        loc = found.group(1) if found else word
        if not LOC.match(loc):
            raise LayoutError(f'{word!r} is not a block name')
        if loc in seen:
            raise LayoutError(f'{loc!r} appears twice: give the second a number (like {loc}2)')
        seen.add(loc)
        to = [x.strip() for x in found.group(2).split(',')] if found.group(2) is not None else []
        for target in to:
            if not LOC.match(target):
                raise LayoutError(f'{target!r} in {word!r} is not a block name')
        return {'kind': 'cell', 'loc': loc, 'size': size(), 'to': to}

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
    defs = {}
    if peek() is not None and peek().startswith('{'):
        for pair in take()[1:-1].split(','):
            loc, _, block = (x.strip() for x in pair.partition('='))
            if loc not in seen or not re.fullmatch('[a-z]+', block):
                raise LayoutError(f'{pair.strip()!r} is not a definition of a locator of the layout (like cd3=code)')
            defs[loc] = SHORT.get(block, block)
    if peek() is not None:
        raise LayoutError(f'unexpected {peek()!r} after the layout')
    if below:
        under = parse(below)
        for loc in names(under):
            if loc in seen:
                raise LayoutError(f'{loc!r} appears twice')
        seen.update(names(under))
        tree = {'kind': 'group', 'dir': 'col', 'items': [tree, under], 'size': (('fill', 1.0, False), ('fill', 1.0, False))}
        defs.update(under['defs'])
    tree['defs'] = defs
    for loc, to in receivers(tree).items():
        for target in to:
            if target not in seen:
                raise LayoutError(f'{loc}{{{",".join(to)}}}: {target!r} is not in the layout')
            if target == loc:
                raise LayoutError(f'{loc}{{...}} names itself')
    return tree


def blocks(tree):
    """{loc: block}: the block a locator is defined as, else the kind it names."""
    defs = tree.get('defs', {})
    return {loc: defs.get(loc) or kind_of(loc) for loc in names(tree)}


def normal(tree, given=None):
    """(tree, {old: new}): the tree with every locator written for an address: the block's own name when a page has one
    of that block, the short name (and the .suffix it had) when it has several, and a definition `{x=block}` for any
    locator whose name does not say its block. `given` is {loc: block} where the caller says the block (else blocks()).
    A name that another locator has or would get is left as it was."""
    block_of = {**blocks(tree), **(given or {})}
    locs = names(tree)
    count = {}
    for loc in locs:
        count[block_of[loc]] = count.get(block_of[loc], 0) + 1
    short = {full: word for word, full in SHORT.items()}
    want = {}
    for loc in locs:
        block = block_of[loc]
        if not LOC.match(block):
            want[loc] = loc
        elif count[block] == 1:
            want[loc] = block                                  # one of its kind: the block's name
        elif kind_of(loc) != block:
            want[loc] = loc                                    # defined: it keeps its name
        else:
            want[loc] = short.get(block, block) + loc[len(loc.split('.')[0]):]
    seen = {}
    for loc in locs:
        seen.setdefault(want[loc], []).append(loc)
    new = {loc: (want[loc] if len(seen[want[loc]]) == 1 else loc) for loc in locs}
    new = {loc: (name if name == loc or sum(1 for n in new.values() if n == name) == 1 else loc) for loc, name in new.items()}
    defs = {new[loc]: block_of[loc] for loc in locs if kind_of(new[loc]) != block_of[loc]}

    def again(node):
        if node['kind'] == 'cell':
            return {**node, 'loc': new[node['loc']], 'to': [new[t] for t in node.get('to', [])]}
        return {**node, 'items': [again(sub) for sub in node['items']]}
    out = again(tree)
    out['defs'] = defs
    return out, new


def names(tree):
    """The locators of a layout, in order."""
    if tree['kind'] == 'cell':
        return [tree['loc']]
    return [loc for sub in tree['items'] for loc in names(sub)]


def places(tree, here=()):
    """{loc: [index in each group on the way down]}: two blocks in one group share the start of their paths, and
    the longer the shared start, the nearer they are."""
    if tree['kind'] == 'cell':
        return {tree['loc']: list(here)}
    out = {}
    for k, sub in enumerate(tree['items']):
        out.update(places(sub, here + (k,)))
    return out


def receivers(tree):
    """{loc: [loc, ...]} of the blocks that have a `{...}` list; the others are not in it."""
    if tree['kind'] == 'cell':
        return {tree['loc']: tree['to']} if tree.get('to') else {}
    out = {}
    for sub in tree['items']:
        out.update(receivers(sub))
    return out


def size_text(size):
    """The size word of a size: the inverse of size_of."""
    def one(dim, lead):
        kind, value, drag = dim
        base = (f'{value:g}' if kind == 'mm' else lead if value == 1.0 else f'{value:g}f')
        return base + ('d' if drag else '')
    return one(size[0], 'w') + 'x' + one(size[1], 'h')


def plain(tree, has_default):
    """The layout as text, and the definitions at its end: see plain_of."""
    defs = tree.get('defs', {})
    text = plain_of(tree, has_default)
    return text + ('{' + ','.join(f'{loc}={block}' for loc, block in defs.items()) + '}' if defs else '')


def plain_of(tree, has_default, parent='col'):
    """The layout as text with the sizes that need not be said left out: a block that has a size of its own for
    the way it runs (has_default(loc, 'row' | 'col'): a width in a row, a height in a column) needs no `wdxh`, and a
    group or a block that fills needs no `wxh`. parse(plain(tree, ...)) lays out the same page."""
    fill = ('fill', 1.0, False)
    size = tree['size']
    if tree['kind'] == 'cell':
        main = size[0] if parent == 'row' else size[1]
        across = size[1] if parent == 'row' else size[0]
        needless = main[0] == 'fill' and main[1] == 1.0 and has_default(tree['loc'], parent) and across == fill
        name = tree['loc'] + ('{' + ','.join(tree['to']) + '}' if tree.get('to') else '')
        if size == (fill, fill) or needless:
            return name
        return name + ' ' + size_text(size)
    sep = ',' if tree['dir'] == 'row' else ';'
    text = '[' + sep.join(plain_of(sub, has_default, tree['dir']) for sub in tree['items']) + ']'
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
