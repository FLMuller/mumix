"""corpus.py -- runs spaghettichk over every Python file of mumix (what pathof lists: no zprev, no ignored files), the way the
methods verb does (the files of the folder, the suites beside tools), and writes the rows to corpus.json for the table."""
import json
import os
import sys
import time
root = r'C:\Users\Frans PREFLM\OneDrive - University of Leeds\code\Claude\mumix'
for p in ('tools', 'tools/primary', 'tools/primary/rs3'):
    sys.path.insert(0, os.path.join(root, p))
from use import load
load('rs3lex')
load('spaghettichk')
load('rs3util')


def areas(real):
    here = os.path.dirname(real).replace('\\', '/')
    short = pathof(here)
    cut = (here + '/').find('/tools/')
    tests = pathof(here[:cut]) if cut > 0 else None
    return (short + '/*.{py,pyx}' if short else ''), (tests + '/{test,tests}/b_*.py' if tests else '')


files = list(pathof('./mumix/**/*.{py,pyx}'))
begin = time.time()
out = []
for short in files:
    real = pathof(short)
    try:
        src = Source.read(real)
        facts = src.facts()
        if facts is None:
            continue
        colour = isspaghetti(src, *areas(real))
    except Exception as error:
        out.append({'file': short, 'error': repr(error)[:120]})
        continue
    rows = []
    for d in facts.defs:
        row = colour.rows.get(d.first)
        rows.append({'name': d.dotted, 'kind': d.kind, 'line': d.first, 'size': d.last - d.first + 1, 'band': str(row),
                     'pie': list(row.pie), 'dot': row.dot, 'score': round(row.score, 1), 'why': row.why})
    out.append({'file': short, 'lines': len(src.lines), 'band': str(colour), 'pie': list(colour.pie), 'score': round(colour.score, 1),
                'why': colour.why, 'rows': rows})
json.dump(out, open(os.path.join(root, 'tests', 'z_sandbox', 'lexdev', 'corpus.json'), 'w'), indent=1)
print(len(files), 'files,', len(out), 'judged,', round(time.time() - begin, 1), 's')
