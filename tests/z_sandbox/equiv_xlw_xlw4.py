"""
equiv_xlw_xlw4.py -- does xlw4 write and read what xlw does?

Question  For the same calls, are the parts of the .xlsx the same, and for the same file, are the
          cells, styles and charts read the same?
Variants  'old' = mumix/xlw, 'new' = mumix/xlw4; each runs in its own process (both are 'xlw').
Method    WRITE: one document (text, numbers, a block, styles, a border, a formula, two charts with
          a secondary axis, a trendline, error bars, labels) is built by each and saved; the parts
          are compared text against text. READ: every .xlsx of tests/fixtures is opened by each;
          the cells (value, formula, style) and the charts are dumped to JSON and compared.
Result    printed: the parts that differ (with the first differing place) and the files whose
          dumps differ. Known, deliberate differences are listed in KNOWN and shown apart.

Run:  python tests/z_sandbox/equiv_xlw_xlw4.py
"""

import json
import os
import subprocess
import sys
import zipfile
from os.path import abspath, dirname, join

HERE = dirname(abspath(__file__))
ROOT = dirname(dirname(HERE))
OUT = join(ROOT, 'results', 'equiv_xlw_xlw4')
FIXTURES = join(ROOT, 'tests', 'fixtures')
KNOWN = {
    'repr': 'xlw4 writes a float as repr (exact); xlw as %.15g',
    'border order': 'xlw4 keeps border edges in the order n s e w; xlw kept the order given',
}


def build(which):
    """Make the document with one package and return the file name."""
    sys.path.insert(0, join(ROOT, 'tools'))
    sys.path.insert(0, join(ROOT, 'xlw' if which == 'old' else 'xlw4'))
    from use import load
    if which == 'old':
        load('xlw')
        import xlchart
    from xlw import xlw
    os.makedirs(OUT, exist_ok=True)
    xl = xlw()
    book = xl.newbook(join(OUT, which + '_doc'), 'Data', 'Notes')
    xl.write('time', 'Heading1').write('a', 'Heading1').write('b', 'Heading1').writeln()
    xl.write([[0.0, 1.5, 10.0], [1.0, 2.25, 20.0], [2.0, 3.125, 40.0], [3.0, 0.0012, 80.0]])
    xl.writeln().write('total', 'Total').formula('=SUM(B2:B5)', cached=6.8762).formula('=A2*2', 'bold', True)
    xl.write(True).write(None).write('x & <y>', 'fill', 'yellow', 'color', 'red', 'border', 'all:thin', 'bcolor', '0000FF')
    xl.write(3, 'numfmt', '0.00%', 'halign', 'center', 'wrap', True, 'rotation', -30, 'indent', 2)
    xl.border([(9, 1), (9, 2)], 'n:medium,s:double', 'color', 'FF0000')
    xl.gridlines(False)
    book.Notes.write('second sheet').writeln('with text')
    chart = book.Data.chart('conc')
    ref = xlchart.ref if which == 'old' else chart.ref
    add = (lambda *a, **k: xlchart.add_series(chart, *a, **k)) if which == 'old' else chart.add_series
    rec = xlchart.rec if which == 'old' else chart.rec
    chart.title.text = 'Concentration'
    chart.xaxis.title.text = 'time (s)'
    chart.yaxis.title.text = [('c', {}), ('2', {'baseline': -25})]
    chart.yaxis.log = 10
    chart.yaxis.min = 1
    chart.yaxis.crossesat = 5
    chart.legend.pos = 'b'
    chart.chartarea.fill = rec(color='F2F2F2')
    first = add(ref('Data', 2, 1, 5, 1), ref('Data', 2, 3, 5, 3), label='A', line=dict(color='C00000', width=2),
                marker=dict(symbol='square', size=7))
    second = add(ref('Data', 2, 1, 5, 1), [1, 2, 3, 4], labelref='Data!$B$1', axis=2, smooth=True)
    second.trend.fit = 'poly'
    second.trend.order = 3
    second.trend.rsq = True
    second.trend.eq = True
    second.yerr.mode = 'percentage'
    second.yerr.value = 5
    second.xerr.mode = 'custom'
    second.xerr.plus = [0.1, 0.2, 0.3, 0.4]
    second.labels.showy = True
    second.labels.pos = 'r'
    chart.x2axis.visible = True
    chart.y2axis.gridmajor = rec(color='EEEEEE', width=0.5)
    (xlchart.place(chart, 5, 1, 8, 15) if which == 'old' else chart.place(5, 1, 8, 15))
    other = book.Data.chart()
    (xlchart.add_series(other, [1, 2], [3, 4]) if which == 'old' else other.add_series([1, 2], [3, 4]))
    other.style = 'marker'
    xl.save('all')
    return xl.root.kvr('priv').kvr('cursor').kvr('priv').kvr('fname') if which == 'new' else \
        xl.root.kvr('priv').kvr('cursor').kvr('priv').kvr('fname')


def dump_node(node):
    """A chart node as plain data: leaves (records as dicts) and children, in sorted order."""
    out = {}
    for key in sorted(node.keys()):
        value = node.kvr(key)
        out[key] = dump_node(value) if hasattr(value, 'keys') and hasattr(value, 'nodes') else value
    for kid in node.nodes():
        out[kid.name() if callable(getattr(kid, 'name', None)) else kid.name] = dump_node(kid)
    return out


def dump_book(path, which):
    """Cells and charts of a file as plain data."""
    sys.path.insert(0, join(ROOT, 'tools'))
    sys.path.insert(0, join(ROOT, 'xlw' if which == 'old' else 'xlw4'))
    from use import load
    if which == 'old':
        load('xlw')
        import xlsheet
    from xlw import xlw
    book = xlw().open(path, 'dump_' + which)
    priv = book.kvr('priv')
    result = {'sheets': priv.kvr('sheets'), 'unmapped': priv.kvr('unmapped'), 'cells': {}, 'charts': {}}
    for name, key in zip(priv.kvr('sheets'), priv.kvr('sheetkeys')):
        sheet = book.kvr(key)
        cells = {}
        if which == 'old':
            for row, col, cell in xlsheet.cell_list(sheet):
                style = xlsheet.cell_style(sheet, row, col)
                cells[f'{row},{col}'] = [xlsheet.cell_value(sheet, row, col), xlsheet.cell_formula(sheet, row, col),
                                         json.dumps(norm_style(style), sort_keys=True, default=str)]
        else:
            grid = sheet.kvr('cells')
            for (row, col) in sorted(grid.cells):
                cells[f'{row},{col}'] = [sheet.cell(row, col), sheet.cell(row, col, 'formula'),
                                         json.dumps(norm_style(sheet.cell(row, col, 'style')), sort_keys=True, default=str)]
        result['cells'][name] = cells
        charts = sheet.kvr('priv').kvr('charts')
        result['charts'][name] = [dump_chart(chart, which) for chart in (charts.nodes() if charts is not None else [])]
    return result


def norm_style(style):
    """A style dict with the border edges sorted (the known difference) and blank cells' default valign dropped."""
    style = {key: value for key, value in style.items()}
    if 'border' in style:
        style['border'] = sorted([list(edge) for edge in style['border']])
    return style


def dump_chart(chart, which):
    return dump_any(chart)


def dump_any(node):
    """A tree or record as plain data (leaves sorted, then children); old kv, old tkv, Node and Chart alike."""
    containers = ('tkv', 'kv', 'Node', 'Chart')
    out = {}
    for key in sorted(node.keys()):
        value = node.kvr(key)
        out[key] = dump_any(value) if type(value).__name__ in containers else value
    if type(node).__name__ != 'kv':
        for kid in node.nodes():
            name = kid.name() if callable(kid.name) else kid.name
            out[name] = dump_any(kid)
    return out


def first_difference(a, b, path=''):
    """The first place two plain data trees differ, as text; '' when they are equal."""
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            if key not in a or key not in b:
                return f'{path}/{key}: only in {"old" if key in a else "new"}'
            found = first_difference(a[key], b[key], f'{path}/{key}')
            if found:
                return found
        return ''
    return '' if a == b else f'{path}: {str(a)[:60]} != {str(b)[:60]}'


def compare_parts(old_file, new_file):
    """Print the parts of the two files that differ, and where."""
    with zipfile.ZipFile(old_file) as old, zipfile.ZipFile(new_file) as new:
        print(f'parts: old {len(old.namelist())}, new {len(new.namelist())}; only in old: '
              f'{sorted(set(old.namelist()) - set(new.namelist()))}; only in new: {sorted(set(new.namelist()) - set(old.namelist()))}')
        for name in old.namelist():
            if name not in new.namelist():
                continue
            a, b = old.read(name).decode('utf-8'), new.read(name).decode('utf-8')
            if a == b:
                print(f'  same       {name}')
                continue
            at = next((i for i in range(min(len(a), len(b))) if a[i] != b[i]), min(len(a), len(b)))
            print(f'  DIFFERENT  {name} at {at}: old ...{a[max(0, at - 40):at + 60]!r}')
            print(f'{"":14s} new ...{b[max(0, at - 40):at + 60]!r}')


def driver():
    files = {}
    for which in ('old', 'new'):
        out = subprocess.run([sys.executable, abspath(__file__), 'build', which], capture_output=True, text=True)
        if out.returncode:
            raise SystemExit(out.stderr[-1500:])
        files[which] = out.stdout.strip().splitlines()[-1]
    print('== WRITE: the parts of the same document')
    compare_parts(files['old'], files['new'])
    print('\n== READ: every fixture, cells and charts')
    charted = [join(ROOT, 'results', *name.split('/')) for name in (
        'b_xlchart/many.xlsx', 'b_xlchart/quoted.xlsx', 'b_xlchart/rich.xlsx', 'b_mumix/mumix.xlsx',
        'b_xlreader/orig.xlsx')]                       # files with charts, left by the xlw suites
    for path in [join(FIXTURES, name) for name in sorted(os.listdir(FIXTURES)) if name.endswith('.xlsx')] + charted:
        name = os.path.basename(path)
        if not os.path.isfile(path):
            continue
        dumps = {}
        for which in ('old', 'new'):
            out = subprocess.run([sys.executable, abspath(__file__), 'dump', which, path],
                                 capture_output=True, text=True)
            if out.returncode:
                dumps[which] = {'error': out.stderr[-300:]}
            else:
                dumps[which] = json.loads(out.stdout.strip().splitlines()[-1])
        found = first_difference(dumps['old'], dumps['new'])
        cells = sum(len(v) for v in dumps['new'].get('cells', {}).values())
        charts = sum(len(v) for v in dumps['new'].get('charts', {}).values())
        print(f'  {"same     " if not found else "DIFFERENT"} {name:24s} {cells:6d} cells {charts} charts  {found}')


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == 'build':
        print(build(sys.argv[2]))
    elif len(sys.argv) > 3 and sys.argv[1] == 'dump':
        print(json.dumps(dump_book(sys.argv[3], sys.argv[2]), default=str))
    else:
        driver()
