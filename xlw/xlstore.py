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

###FLM why so complicated? just load 'kv','tkv' and creste the two stores?
###FLM or, as kv tkv are syblings, from kv import kv. simplify.
###cld Done: one load builds both when stale and binds a namespace for each, and KV and TKV are their classes.
###cld A plain load('kv', 'tkv') would bind kvr and kvw from both, the second over the first.
load(asmodule=['kv', 'tkv'])
KV = kv.kv
TKV = tkv.tkv
