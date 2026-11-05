import collections
import json
import os
import re
root = r'C:\Users\Frans PREFLM\OneDrive - University of Leeds\code\Claude\mumix'
data = [d for d in json.load(open(os.path.join(root, 'tests', 'z_sandbox', 'lexdev', 'corpus.json'))) if 'rows' in d]
errors = [d for d in json.load(open(os.path.join(root, 'tests', 'z_sandbox', 'lexdev', 'corpus.json'))) if 'error' in d]
print('files', len(data), 'errors', len(errors))
rule = collections.defaultdict(collections.Counter)
filerule = collections.defaultdict(collections.Counter)
bands = collections.Counter()
for d in data:
    bands[d['band']] += 1
    for w in d['why']:
        m = re.match(r'(\w+): (\w+)', w)
        filerule[m.group(1)][m.group(2)] += 1
    for r in d['rows']:
        for w in r['why']:
            m = re.match(r'(\w+): (\w+)', w)
            rule[m.group(1)][m.group(2)] += 1
print('file bands', dict(bands))
print('FILE RULES'); [print(' ', k, dict(v)) for k, v in sorted(filerule.items())]
print('ROW RULES'); [print(' ', k, dict(v)) for k, v in sorted(rule.items())]
rows = [(d['file'], r) for d in data for r in d['rows']]
rb = collections.Counter(r['band'] or 'grey' for f, r in rows)
print('rows', len(rows), dict(rb), 'dots', sum(1 for f, r in rows if r['dot']))
print('score hist', collections.Counter(int(r['score'] // 20) * 20 for f, r in rows))


def meanrow(d):
    return sum(r['score'] * r['size'] for r in d['rows']) / max(1, sum(r['size'] for r in d['rows']))


rank = sorted(data, key=lambda d: (d['score'] + meanrow(d)) / 2)
print('WORST 25')
for d in rank[:25]:
    c = collections.Counter(r['band'] or 'grey' for r in d['rows'])
    print(f"{d['file'][8:]:60s} {d['band'] or 'grey':7s} file {d['score']:5.1f} rows {meanrow(d):5.1f} n={len(d['rows']):3d} red={c['red']} or={c['orange']} dots={sum(1 for r in d['rows'] if r['dot'])} {d['lines']}L")
print('BEST 12')
for d in rank[-12:]:
    c = collections.Counter(r['band'] or 'grey' for r in d['rows'])
    print(f"{d['file'][8:]:60s} {d['band'] or 'grey':7s} file {d['score']:5.1f} rows {meanrow(d):5.1f} n={len(d['rows']):3d} red={c['red']} or={c['orange']} {d['lines']}L")
print('WORST FUNCTIONS (red, big)')
big = sorted([(f, r) for f, r in rows if r['band'] == 'red'], key=lambda p: -p[1]['size'])[:15]
for f, r in big:
    print(f"{f[8:50]:50s} {r['name']:28s} {r['size']:4d} L {[w for w in r['why'] if 'tangle' in w][:1]}")
