import os
import sys
root = r'C:\Users\Frans PREFLM\OneDrive - University of Leeds\code\Claude\mumix'
for p in ('tools', 'tools/primary', 'tools/primary/rs3'):
    sys.path.insert(0, os.path.join(root, p))
from use import load
load('rs3lex')

target = sys.argv[1] if len(sys.argv) > 1 else None
text = '''"""Module doc.
more
"""
import os, sys as system
from a.b import c, d as e
from use import load
load('rs3util')
__all__ = ['f',
           'G']
LIMIT = 5


@property
def f(a, b=1,
      *args, **kw):
    """Doc."""
    x = getattr(a, 'y')
    obj._hidden = 3
    mod.attr = 4
    try:
        import zz
    except (ImportError, ValueError):
        pass
    if a and b or x:
        return a, b
    self.count = 1


class G(Base, object):
    size = 3

    def m(me):
        me._x = 1
        return me
'''
folder = os.path.join(root, 'tests', 'z_sandbox', 'lexdev')
path = os.path.join(folder, 'facttmp.py')
open(path, 'w', encoding='utf-8', newline='').write(text)
try:
    src = Source.read(target or path)
    f = src.facts()
    for d in f.defs:
        print(d.dotted, d.kind, d.top, d.first, d.last, d.params, d.decorators, d.bases, d.docs, d.parent, repr(d.owner), d.doc[:20])
    for n, items in sorted(f.lines.items()):
        print(n, items)
    print('exports', f.exports, 'consts', f.consts, 'imports', f.imports, 'doc', f.doc)
    print('words', dict(list(f.words.items())[:12]))
finally:
    os.remove(path)
