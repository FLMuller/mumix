"""
xltree -- the tree and the records of xlw4: one small class in place of the kv and tkv stores.

Why
    A workbook is a tree (root > book > sheet) and a chart is a tree of settings, so both need
    named children, named leaves, a path read and a dotted attribute walk. A Python dict gives
    each of those at C speed, so no compiled store is needed: a node is two dicts. Node and rec
    are all this module exposes; Chart, Sheet, Book and Root are Nodes with verbs.

Algorithm
    A node holds `leaves` (name -> value) and `kids` (name -> child node). Reading a name that
    is neither gives a speculative child: it is linked to its parent but does not count until
    something is written below it, which makes it and every ancestor live. So
    `chart.title.text = 'x'` builds the title node, and merely reading `chart.title.text`
    builds nothing. Writing None to a leaf deletes the leaf. A path 'a.b.c' walks children,
    one dict lookup per segment. kvr and kvw read and write by name or path; x[name] is the same.
    rec() builds a record: a node holding flat fields. Node subclasses may add methods, and a
    leaf cannot be given the name of a method (it would be hidden by it).

Use
    chart = Node('chart')
    chart.title.text = 'Concentration'      # node 'title' made on the write
    chart.kvr('title.text')                 # 'Concentration'; None (or the default given) when absent
    chart.kvw('xaxis.log', 10)              # a path write; chart['xaxis.log'] is the same
    chart.nodes(); chart.keys(); chart.count()      # live children, leaf names, the number of children
    chart.node('series')                    # the child, made when missing; chart.add(name, node) links one
    chart.type(); chart.parent()            # the kind given at creation, and the parent node
    line = rec(color='C00000', width=2)     # a record; line.kvr('width') is 2

VERSION  M01 m01.v01 (2026-11-06): first version; replaces xlw's kv and tkv for xlw4.
"""

__all__ = ['Node', 'rec']


class Node:
    """A named group of leaves and child nodes. A leaf name equal to a method name is refused
    by an attribute write, because the method would hide the leaf from an attribute read."""
    __slots__ = ('kind', 'up', 'name', 'leaves', 'kids', 'live')

    def __init__(me, kind='', up=None, name='', live=True):
        me.kind, me.up, me.name, me.leaves, me.kids, me.live = kind, up, name, {}, {}, live

    def type(me):
        """The kind given at creation: 'root', 'book', 'sheet', 'chart' or ''."""
        return me.kind

    def parent(me):
        """The node this one hangs from (None for a root)."""
        return me.up

    def confirm(me):
        """Make this node and its ancestors count: a speculative node became real."""
        while me is not None and not me.live:
            me.live = True
            me = me.up

    def kvr(me, path, default=None):
        """A leaf or live child by name or dotted path; `default` when absent. A path may pass
        through a record held as a leaf: chart.kvr('title.font.color') reads the field of the record."""
        here = me
        names = path.split('.') if isinstance(path, str) else [path]
        for name in names[:-1]:
            step = here.leaves.get(name)
            if not isinstance(step, Node):
                step = here.kids.get(name)
            if step is None or not step.live:
                return default
            here = step
        if names[-1] in here.leaves:
            return here.leaves[names[-1]]
        kid = here.kids.get(names[-1])
        return kid if kid is not None and kid.live else default

    def kvw(me, path, value):
        """Write a leaf by name or dotted path (None deletes it); nodes on the way are made."""
        names = path.split('.') if isinstance(path, str) else [path]
        here = me
        for name in names[:-1]:
            here = here.node(name)
        if value is None:
            here.leaves.pop(names[-1], None)
            return
        here.confirm()
        here.leaves[names[-1]] = value

    def node(me, name):
        """The child `name`, made (and counted) when missing."""
        kid = me.kids.get(name)
        if kid is None:
            kid = me.kids[name] = Node('', me, name)
        kid.confirm()
        return kid

    def add(me, name, kid):
        """Link a ready-made node (of any Node class) as the child `name`; returns it."""
        kid.up, kid.name = me, name
        me.kids[name] = kid
        kid.confirm()
        return kid

    def nodes(me):
        """The live children, in the order they were made."""
        return [kid for kid in me.kids.values() if kid.live]

    def count(me):
        """The number of live children."""
        return len(me.nodes())

    def keys(me):
        """The names of the leaves."""
        return list(me.leaves)

    def __getattr__(me, name):
        if name.startswith('_'):
            raise AttributeError(name)
        if name in me.leaves:
            return me.leaves[name]
        if name not in me.kids:
            me.kids[name] = Node('', me, name, live=False)
        return me.kids[name]

    def __setattr__(me, name, value):
        if name in Node.__slots__:
            object.__setattr__(me, name, value)
        elif hasattr(type(me), name):
            raise AttributeError(f'"{name}" is a method name, not a leaf')
        else:
            me.kvw(name, value)

    __getitem__ = kvr
    __setitem__ = kvw

    def __repr__(me):
        parts = [f'{key}:{value!r}' for key, value in me.leaves.items()]
        return '{' + ', '.join(parts + [f'{kid.name}:{kid!r}' for kid in me.nodes()]) + '}'


def rec(**fields):
    """A record: a node holding the given fields; None values are left out. Records are the
    small flat groups that always travel together (a font, a line, a fill)."""
    record = Node()
    record.leaves.update({key: value for key, value in fields.items() if value is not None})
    return record
