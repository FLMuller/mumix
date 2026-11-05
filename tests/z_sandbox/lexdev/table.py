import collections
import json
import os
import re
root = r'C:\Users\Frans PREFLM\OneDrive - University of Leeds\code\Claude\mumix'
data = [d for d in json.load(open(os.path.join(root, 'tests', 'z_sandbox', 'lexdev', 'corpus.json'))) if 'rows' in d]
JUNK = ('z_sandbox', 'oldsuite', 'rs3twolex', 'rs3vcdep', 'zprev')
kept = [d for d in data if not any(j in d['file'] for j in JUNK)]


def meanrow(d):
    return sum(r['score'] * r['size'] for r in d['rows']) / max(1, sum(r['size'] for r in d['rows']))


def findings(d, n=3):
    """The most telling non-green reasons of a file: file-level first, then the commonest row-level ones."""
    out = [w.split(' ', 1)[0] + ' ' + w.split(') ', 1)[-1] if ') ' in w else w for w in d['why'] if not w.endswith(': green')]
    count = collections.Counter()
    for r in d['rows']:
        for w in r['why']:
            if w.endswith(': green') or w.startswith(('docs', 'local', 'callers', 'usage', 'duplication')):
                continue
            count[w.split(':')[0] + ' ' + w.split(':')[1].split('(')[0].strip()] += 1
    return out[:2] + [f'{k} x{v}' for k, v in count.most_common(n)]


rows = []
for d in kept:
    suite = os.path.basename(d['file']).startswith('b_')
    c = collections.Counter(r['band'] or 'grey' for r in d['rows'])
    n = len(d['rows'])
    rows.append(dict(file=d['file'][2:], lines=d['lines'], suite=suite, band=d['band'] or 'grey', fscore=d['score'], rscore=round(meanrow(d), 1),
                     n=n, red=c['red'], orange=c['orange'], dots=sum(1 for r in d['rows'] if r['dot']), find=findings(d),
                     index=round((d['score'] + meanrow(d)) / 2 if n else d['score'], 1)))
prod = sorted([r for r in rows if not r['suite']], key=lambda r: r['index'])
suites = sorted([r for r in rows if r['suite']], key=lambda r: r['index'])
out = ['# spaghetti table of mumix', '',
       f'Judged by spaghettichk over {len(kept)} Python files of mumix (the folders z_sandbox, oldsuite, rs3twolex, rs3vcdep are old copies and are left out;'
       f' {len(data) - len(kept)} files). Index = the mean of the file score and the size-weighted mean score of its functions and classes'
       ' (0 worst, 100 best). Scope as agreed: the callers of a name are searched in the files of its own folder; the suites are b_<name>.py of the tests folder.', '',
       '## Production files, worst first', '',
       '| # | file | lines | band | file | rows | funcs | red | orange | dots | what stands out |', '|--:|:--|--:|:--|--:|--:|--:|--:|--:|--:|:--|']
for i, r in enumerate(prod, 1):
    out.append(f"| {i} | {r['file']} | {r['lines']} | {r['band']} | {r['fscore']:.0f} | {r['rscore']:.0f} | {r['n']} | {r['red']} | {r['orange']} | {r['dots']} | {'; '.join(r['find'])} |")
out += ['', '## Suites (b_*.py), worst first', '',
        '| # | file | lines | band | file | rows | funcs | red | what stands out |', '|--:|:--|--:|:--|--:|--:|--:|--:|:--|']
for i, r in enumerate(suites, 1):
    out.append(f"| {i} | {r['file']} | {r['lines']} | {r['band']} | {r['fscore']:.0f} | {r['rscore']:.0f} | {r['n']} | {r['red']} | {'; '.join(r['find'])} |")
open(os.path.join(root, 'spaghetti_table.md'), 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')
print(len(prod), 'production,', len(suites), 'suites')
for r in prod[:30]:
    print(f"{r['file']:58s} {r['band']:6s} f{r['fscore']:5.1f} r{r['rscore']:5.1f} n{r['n']:3d} red{r['red']:3d} or{r['orange']:3d} dots{r['dots']:2d} {r['lines']:4d}L | {'; '.join(r['find'])[:110]}")
print('...')
for r in prod[-14:]:
    print(f"{r['file']:58s} {r['band']:6s} f{r['fscore']:5.1f} r{r['rscore']:5.1f} n{r['n']:3d} red{r['red']:3d} or{r['orange']:3d} dots{r['dots']:2d} {r['lines']:4d}L")
