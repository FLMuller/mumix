"""
xlstore -- loads the two Cython stores once, for the whole xlw package.

kv    hash map for text and sparse keys (xlw/kv.pyx)
tkv   typed tree on the same store design  (xlw/tkv.pyx)

Use
    from xlstore import KV, TKV
    table = KV()                  # dedup tables, the zip part list
    root = TKV(['root', 'book'])  # a typed tree

    use() builds the .pyx files into xlw/pyxfiles on the first load. It needs
    tools/use.py on sys.path, which every mumix script and suite arranges first.

Versions
    M01  m01.v01  2026-10-31  first version.
"""

from use import load

__all__ = ['KV', 'TKV']

kvnames = load('kv', into={})
tkvnames = load('tkv', into={})
KV = kvnames['kv']
TKV = tkvnames['tkv']
