import os, sys
root = r'C:\Users\Frans PREFLM\OneDrive - University of Leeds\code\Claude\mumix'
for p in ('tools', 'tools/primary', 'tools/primary/rs3'):
    sys.path.insert(0, os.path.join(root, p))
from use import load
load('rs3lex')
path = os.path.join(root, 'tests', 'z_sandbox', 'lexdev', 'rolestmp.py')
open(path, 'w', encoding='utf-8', newline='').write("SHOWN = 1\nSTYLEsheet = 4\nLimit = 3\nmax = 3\nname = 5\nUNUSED = 9\nTable = {'a': 1}\n")
try:
    for toks, inb, d in Source.read(path).lexed():
        print([(r, t) for r, t in toks if t.strip()][:3])
finally:
    os.remove(path)
