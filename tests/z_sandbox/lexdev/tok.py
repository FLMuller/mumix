import os
import sys
root = r'C:\Users\Frans PREFLM\OneDrive - University of Leeds\code\Claude\mumix'
for p in ('tools', 'tools/primary', 'tools/primary/rs3'):
    sys.path.insert(0, os.path.join(root, p))
from use import load
Source = load('rs3lex', into={})['Source']

text = '''"""Module doc.
more
"""
import os, sys as system
from a.b import c, d as e
from use import load
load('rs3util', into={})
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
folder = os.path.join(root, 'tests', 'z_sandbox')
os.makedirs(folder, exist_ok=True)
path = os.path.join(folder, 'toktmp.py')
open(path, 'w', encoding='utf-8', newline='').write(text)
try:
    src = Source.read(path)
    for i, row in enumerate(src.lexed(), 1):
        toks, inb, depth = row
        print(i, inb, depth, [(r, t) for r, t in toks if t.strip()][:14])
    print(src.functions())
finally:
    os.remove(path)
