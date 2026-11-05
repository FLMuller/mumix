import os
import sys
root = r'C:\Users\Frans PREFLM\OneDrive - University of Leeds\code\Claude\mumix'
for p in ('tools', 'tools/primary', 'tools/primary/rs3'):
    sys.path.insert(0, os.path.join(root, p))
from use import load
Source = load('rs3lex', into={})['Source']
src = Source.read(os.path.join(root, 'tools', 'use.py'))
for i, row in enumerate(src.lexed(), 1):
    if 553 <= i <= 572:
        toks, inb, depth = row
        print(i, inb, depth, [(r, t[:24]) for r, t in toks if t.strip()][:6])
