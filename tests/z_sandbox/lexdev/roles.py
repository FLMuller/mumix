import os, sys, collections
root = r'C:\Users\Frans PREFLM\OneDrive - University of Leeds\code\Claude\mumix'
for p in ('tools', 'tools/primary', 'tools/primary/rs3'):
    sys.path.insert(0, os.path.join(root, p))
from use import load
load('rs3lex')
src = Source.read(os.path.join(root, 'tools/primary/rs3/rs3util.py'))
roles = collections.Counter()
ex = {}
for toks, inb, d in src.lexed():
    for r, t in toks:
        roles[r] += 1
        ex.setdefault(r, t)
for r, n in roles.most_common():
    print(r, n, repr(ex[r]))
