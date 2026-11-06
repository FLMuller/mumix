import os
import sys
root = r'C:\Users\Frans PREFLM\OneDrive - University of Leeds\code\Claude\mumix'
for p in ('tools', 'tools/primary', 'tools/primary/rs3'):
    sys.path.insert(0, os.path.join(root, p))
from use import load
load('rs3lex')
load('spaghettichk')
rel = sys.argv[1].replace('\\', '/')
real = os.path.join(root, rel)
folder = os.path.dirname(rel)
area = './mumix/' + folder + '/*.py'
c = isspaghetti(Source.read(real), area, './mumix/tests/b_*.py')
print('FILE', repr(str(c)), c.pie, round(c.score, 1), c.dot)
for w in c.why:
    print('   ', w)
for line, row in sorted(c.rows.items()):
    print(line, repr(str(row)), row.pie, row.dot, '|', '; '.join(w for w in row.why if not w.endswith(': green'))[:150])
