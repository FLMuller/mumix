"""
cmp_xlw_xlw4.py -- xlw (compiled kv/tkv) against xlw4 (pure Python), the same operations.

Question  Is the pure-Python rebuild as fast as, or faster than, the package with the compiled
          stores, for the operations a caller pays for?
Variants  'old' = mumix/xlw (Cython kv, tkv, xlsheetfun built into xlw/pyxfiles), 'new' = mumix/xlw4.
          Each runs in its own process, because both packages are called xlw.
Method    each operation is repeated until about 0.4 s have passed and the best of three blocks
          is kept (the least disturbed one); the machine is the same for both. File sizes are read
          from the files each variant saved.
Result    printed by the driver, one row per operation: microseconds (or ms) and old/new.

Run:  python tests/z_sandbox/cmp_xlw_xlw4.py            (driver: runs both, prints the table)
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from os.path import abspath, dirname, join

HERE = dirname(abspath(__file__))
ROOT = dirname(dirname(HERE))
OUT = join(ROOT, 'results', 'cmp_xlw_xlw4')


def best(function, seconds=0.4, blocks=3):
    """Seconds per call: the best of `blocks` blocks of about `seconds` each."""
    function()
    result = []
    for _ in range(blocks):
        count, start = 0, time.perf_counter()
        while time.perf_counter() - start < seconds:
            function()
            count += 1
        result.append((time.perf_counter() - start) / count)
    return min(result)


def worker(which):
    """Time the operations with one package; returns {operation: seconds or bytes}."""
    sys.path.insert(0, join(ROOT, 'tools'))
    sys.path.insert(0, join(ROOT, 'xlw' if which == 'old' else 'xlw4'))
    from use import load
    if which == 'old':
        load('xlw')
    from xlw import xlw
    os.makedirs(OUT, exist_ok=True)
    table_10k = [[i * 0.001 + j for j in range(10)] for i in range(1000)]
    table_100k = [[i * 0.001 + j for j in range(10)] for i in range(10000)]
    mixed = [[f'row {i}', i, i * 0.5, i % 2 == 0, f'text {i % 50}'] for i in range(2000)]
    timings = {}

    def new_sheet():
        xl = xlw()
        xl.newbook(join(OUT, which + '_w'), 'W')
        return xl, xl.root.kvr('priv').kvr('cursor').kvr('W') if which == 'new' else xl.root.kvr('priv').kvr('cursor').kvr('W')

    def scalar_writes(node_form):
        xl = xlw()
        xl.newbook(join(OUT, which + '_w'), 'W')
        target = getattr(xl, which + '_w').W if node_form else xl
        for _ in range(1000):
            target.write(1.5)

    def styled_writes():
        xl = xlw()
        xl.newbook(join(OUT, which + '_w'), 'W')
        sheet = getattr(xl, which + '_w').W
        for _ in range(1000):
            sheet.write(1.5, 'Heading1')

    def build(table, name):
        xl = xlw()
        xl.newbook(join(OUT, which + '_' + name), 'Data')
        xl.write(table)
        return xl

    timings['write(1.5) x1000, xl.write'] = best(lambda: scalar_writes(False))
    timings['write(1.5) x1000, sheet.write'] = best(lambda: scalar_writes(True))
    timings["write(1.5,'Heading1') x1000"] = best(styled_writes)
    timings['build 10 000 numbers (block)'] = best(lambda: build(table_10k, 'b10'))
    timings['build 2 000 x 5 mixed cells (block)'] = best(lambda: build(mixed, 'bm'))
    for name, table in (('10k', table_10k), ('100k', table_100k)):
        xl = build(table, 's' + name)
        timings[f'save {name} numbers'] = best(xl.save, 0.4 if name == '10k' else 0.8, 2)
        fname = join(OUT, which + '_s' + name + '.xlsx')
        timings[f'size {name} numbers (bytes)'] = os.path.getsize(fname)
        timings[f'open {name} numbers'] = best(lambda: xlw().open(fname), 0.4 if name == '10k' else 0.8, 2)
    xl = build(mixed, 'sm')
    xl.save()
    fname = join(OUT, which + '_sm.xlsx')
    timings['save 2 000 x 5 mixed'] = best(xl.save)
    timings['open 2 000 x 5 mixed'] = best(lambda: xlw().open(fname))
    timings['size mixed (bytes)'] = os.path.getsize(fname)
    return timings


def driver():
    results = {}
    for which in ('old', 'new'):
        out = subprocess.run([sys.executable, abspath(__file__), which], capture_output=True, text=True)
        if out.returncode:
            print(out.stdout, out.stderr)
            raise SystemExit(f'{which} failed')
        results[which] = json.loads(out.stdout.strip().splitlines()[-1])
    print(f'{"operation":42s} {"old xlw":>12s} {"xlw4":>12s} {"old/new":>8s}')
    for name in results['old']:
        old, new = results['old'][name], results['new'][name]
        scale = (1, 'B') if 'bytes' in name else (1e6 if old < 1e-3 else 1e3, 'us' if old < 1e-3 else 'ms')
        shown = (f'{old:12.0f}', f'{new:12.0f}') if 'bytes' in name else (
            f'{old * scale[0]:9.1f} {scale[1]}', f'{new * scale[0]:9.1f} {scale[1]}')
        print(f'{name:42s} {shown[0]:>12s} {shown[1]:>12s} {old / new:8.2f}')


if __name__ == '__main__':
    if len(sys.argv) > 1:
        print(json.dumps(worker(sys.argv[1])))
    else:
        driver()
