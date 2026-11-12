"""
b_compare.py -- xlw (compiled kv/tkv) and xlw4 (pure Python) side by side: the same calls, the same files.

Both packages are called xlw, so the old one is imported first and put aside under the name xlwold before
xlw4 is imported (its xlreader keeps the module it imported, so xlwold.open still reads with the old code).
The tests hold the two to the same results: the parts of one document written by each are the same XML,
and every sample file reads to the same cells. The benchmarks then time the same operation with each, one
row for xlw and one for xlw4 with the same group, so a pair is read straight across: the writes (per cell,
styled, a block), the whole-book rows (build, save, open for 10 000 and 100 000 numbers and for mixed
cells), reading a cell, and a book with charts. The files that are opened were written by xlw, so both read
the same bytes.

Run from the project root:
    python tools/runbench.py xlw4/tests/b_compare.py
"""

import os
import sys
import xml.etree.ElementTree as ET
import zipfile
from os.path import abspath, dirname, isdir, join


def findtools():                      # walk up to the folder that holds tools/
    here = dirname(abspath(__file__))
    while here != dirname(here) and not isdir(join(here, 'tools')):
        here = dirname(here)
    sys.path.insert(0, join(here, 'tools'))
    return here


ROOT = findtools()
from bench import bench


def import_old():
    """The old xlw module, put aside as xlwold, with its helper modules loaded while it is the one called xlw."""
    sys.path.insert(0, join(ROOT, 'xlw'))
    import xlw                                    # by the path: use.load would find xlw4's xlw first, as this suite sits in xlw4
    import xlreader, xlchart, xlsheet            # the ones the old xlw imports later: bound to the old module now
    old = sys.modules.pop('xlw')
    assert old.__file__.startswith(join(ROOT, 'xlw') + os.sep), old.__file__
    sys.modules['xlwold'] = old
    sys.path.remove(join(ROOT, 'xlw'))
    return old, xlchart, xlsheet


old_module, old_chart, old_sheet = import_old()
sys.path.insert(0, join(ROOT, 'xlw4'))
import xlw as new_module

SOURCES = ['xlw', 'xlbook', 'xlcells', 'xlformat', 'xlpack', 'xlscatter', 'xltext', 'xltree']
IMPLS = ('xlw', 'xlw4')
CLASS = {'xlw': old_module.xlw, 'xlw4': new_module.xlw}
OUTDIR = join(ROOT, 'results', 'b_compare')
FIXTURES = join(ROOT, 'tests', 'fixtures')
NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'


def new_book(impl, name, *sheets):
    """(writer, book node) of a new book of one package, its file in OUTDIR."""
    xl = CLASS[impl]()
    book = xl.newbook(join(OUTDIR, f'{impl}_{name}'), *sheets)
    return xl, book


def cells_of(impl, sheet):
    """{(row, col): (value, formula, style)} of a sheet of either package, styles with the border edges sorted."""
    found = {}
    if impl == 'xlw':
        entries = [(row, col) for row, col, _ in old_sheet.cell_list(sheet)]
        read = lambda row, col: (old_sheet.cell_value(sheet, row, col), old_sheet.cell_formula(sheet, row, col),
                                 old_sheet.cell_style(sheet, row, col))
    else:
        entries = sorted(sheet.kvr('cells').cells)
        read = lambda row, col: (sheet.cell(row, col), sheet.cell(row, col, 'formula'), sheet.cell(row, col, 'style'))
    for row, col in entries:
        value, formula, style = read(row, col)
        if 'border' in style:
            style = {**style, 'border': sorted(list(edge) for edge in style['border'])}
        found[row, col] = (value, formula, repr(sorted(style.items())))
    return found


def document(impl):
    """One document written with one package: text, numbers, styles, a block, a border, formulas, two charts."""
    xl, book = new_book(impl, 'doc', 'Data', 'Notes')
    xl.write('time', 'Heading1').write('a', 'Heading1').write('b', 'Heading1').writeln()
    xl.write([[0.0, 1.5, 10.0], [1.0, 2.25, 20.0], [2.0, 3.125, 40.0], [3.0, 0.0012, 80.0]])
    xl.writeln().write('total', 'Total').formula('=SUM(B2:B5)', cached=6.8762).formula('=A2*2', 'bold', True)
    xl.write(True).write(None).write('x & <y>', 'fill', 'yellow', 'color', 'red', 'border', 'all:thin', 'bcolor', '0000FF')
    xl.write(3, 'numfmt', '0.00%', 'halign', 'center', 'wrap', True, 'rotation', -30, 'indent', 2)
    xl.border([(9, 1), (9, 2)], 'n:medium,s:double', 'color', 'FF0000').gridlines(False)
    book.Notes.write('second sheet').writeln('with text')
    chart = book.Data.chart('conc')
    ref = old_chart.ref if impl == 'xlw' else chart.ref
    rec = old_chart.rec if impl == 'xlw' else chart.rec
    add = (lambda *a, **k: old_chart.add_series(chart, *a, **k)) if impl == 'xlw' else chart.add_series
    chart.title.text = 'Concentration'
    chart.xaxis.title.text = 'time (s)'
    chart.yaxis.log = 10
    chart.yaxis.crossesat = 5
    chart.legend.pos = 'b'
    chart.chartarea.fill = rec(color='F2F2F2')
    add(ref('Data', 2, 1, 5, 1), ref('Data', 2, 3, 5, 3), label='A', line=dict(color='C00000', width=2),
        marker=dict(symbol='square', size=7))
    second = add(ref('Data', 2, 1, 5, 1), [1, 2, 3, 4], labelref='Data!$B$1', axis=2, smooth=True)
    second.trend.fit = 'poly'
    second.trend.rsq = True
    second.yerr.mode = 'percentage'
    second.labels.showy = True
    chart.x2axis.visible = True
    (old_chart.place(chart, 5, 1, 8, 15) if impl == 'xlw' else chart.place(5, 1, 8, 15))
    xl.save()
    return book.kvr('priv').kvr('fname')


def canonical(text):
    """The XML of a part in canonical form, so <a/> and <a></a> are the same."""
    return ET.canonicalize(text)


class b_compare(bench):
    BenchName = 'xlw vs xlw4'
    BenchVersion = 'M1.0.6'
    BenchHeader = 'xlw (compiled kv/tkv) against xlw4 (pure Python): one row each, the same group, side by side'
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        os.makedirs(OUTDIR, exist_ok=True)
        cls.table_10k = [[i * 0.001 + j for j in range(10)] for i in range(1000)]
        cls.table_100k = [[i * 0.001 + j for j in range(10)] for i in range(10000)]
        cls.mixed = [[f'row {i}', i, i * 0.5, i % 2 == 0, f'text {i % 50}'] for i in range(2000)]
        cls.tables = {'10k': cls.table_10k, '100k': cls.table_100k, 'mixed': cls.mixed}
        cls.read_file, cls.saved = {}, {}
        for name, table in cls.tables.items():
            xl, book = new_book('xlw', 'src' + name, 'Data')
            xl.write(table)
            xl.save()
            cls.read_file[name] = book.kvr('priv').kvr('fname')       # written by xlw: both read these bytes
            for impl in IMPLS:
                writer, whole = new_book(impl, 'save' + name, 'Data')
                writer.write(table)
                cls.saved[impl, name] = writer
        for impl in IMPLS:
            xl, book = new_book(impl, 'cells', 'S1')
            for row in range(12):
                for col in range(12):
                    xl.write(row * 100.0 + col + 0.5, 'Heading1') if (row + col) % 5 == 3 else xl.write(row * 100.0 + col + 0.5)
                xl.writeln()
            setattr(cls, 'sheet_' + impl, book.S1)
        cls.coords = [(r, c) for r in range(1, 13) for c in range(1, 13)]

    # ---- the two hold the same results ---------------------------------------------------------
    def test_T1_the_parts_of_one_document_are_the_same_xml(self):
        files = {impl: document(impl) for impl in IMPLS}
        with zipfile.ZipFile(files['xlw']) as old, zipfile.ZipFile(files['xlw4']) as new:
            self.assertEqual(old.namelist(), new.namelist())
            for name in old.namelist():
                self.assertEqual(canonical(old.read(name).decode('utf-8')), canonical(new.read(name).decode('utf-8')), name)

    def test_T2_every_sample_file_reads_to_the_same_cells(self):
        for name in sorted(os.listdir(FIXTURES)):
            if not name.endswith('.xlsx'):
                continue
            books = {impl: CLASS[impl]().open(join(FIXTURES, name), 'cmp' + impl.replace('4', 'four')) for impl in IMPLS}
            keys = {impl: books[impl].kvr('priv').kvr('sheetkeys') for impl in IMPLS}
            self.assertEqual(keys['xlw'], keys['xlw4'], name)
            for key in keys['xlw']:
                self.assertEqual(cells_of('xlw', books['xlw'].kvr(key)), cells_of('xlw4', books['xlw4'].kvr(key)), name)

    def test_T3_a_file_the_old_package_wrote_reads_the_same_in_both(self):
        for name, path in self.read_file.items():
            if name == '100k':
                continue                              # opened twice it would pass the second a test may take
            books = {impl: CLASS[impl]().open(path) for impl in IMPLS}
            a, b = (cells_of(impl, books[impl].Data) for impl in IMPLS)
            self.assertEqual(len(a), len(b), name)
            self.assertEqual(a, b, name)

    def test_T4_charts_of_written_files_read_back_the_same(self):
        files = {impl: document(impl) for impl in IMPLS}
        charts = {}
        for impl in IMPLS:
            sheet = CLASS[impl]().open(files[impl]).Data
            charts[impl] = [self.dump(node) for node in sheet.kvr('priv').kvr('charts').nodes()]
        self.assertEqual(charts['xlw'], charts['xlw4'])

    def dump(self, node):
        """A chart node as plain data, for either package: leaves sorted, then children."""
        out = {}
        for key in sorted(node.keys()):
            value = node.kvr(key)
            out[key] = self.dump(value) if type(value).__name__ in ('tkv', 'kv', 'Node', 'Chart') else value
        if type(node).__name__ != 'kv':
            for kid in node.nodes():
                out[kid.name() if callable(kid.name) else kid.name] = self.dump(kid)
        return out

    # ---- the benchmarks, one pair for each operation --------------------------------------------
    def time_pair(self, timer, impl, label, group, run):
        """Time run(self, impl, test) for one package; the row is `label` for `impl`, in `group`."""
        with timer as test:
            while test.more:
                run(self, impl, test)
        return f'{label}  [{impl}]', group


def make(label, group, run):
    """The two bench methods (xlw, xlw4) of one operation."""
    def one(impl):
        def method(self, timer):
            return self.time_pair(timer, impl, label, group, run)
        return method
    return {impl: one(impl) for impl in IMPLS}


def run_write_xl(self, impl, test):
    xl, book = new_book(impl, 'w', 'W')
    for i in test.count:
        xl.write(1.5)


def run_write_node(self, impl, test):
    xl, book = new_book(impl, 'w', 'W')
    sheet = book.W
    for i in test.count:
        sheet.write(1.5)


def run_write_styled(self, impl, test):
    xl, book = new_book(impl, 'w', 'W')
    sheet = book.W
    for i in test.count:
        sheet.write(1.5, 'Heading1')


def run_read_cell(self, impl, test):
    coords = self.coords
    size = len(coords)
    sheet = getattr(self, 'sheet_' + impl)
    read = (lambda r, c: old_sheet.cell_value(sheet, r, c)) if impl == 'xlw' else sheet.cell
    for i in test.count:
        read(*coords[i % size])


def run_build(name):
    def run(self, impl, test):
        table = self.tables[name]
        for i in test.count:
            xl, book = new_book(impl, 'b' + name, 'Data')
            xl.write(table)
    return run


def run_save(name):
    def run(self, impl, test):
        writer = self.saved[impl, name]
        for i in test.count:
            writer.save()
    return run


def run_open(name):
    def run(self, impl, test):
        path = self.read_file[name]
        for i in test.count:
            CLASS[impl]().open(path)
    return run


def run_chart_save(self, impl, test):
    xl, book = new_book(impl, 'chart', 'Data')
    xl.write([[float(i), i * 0.5] for i in range(200)])
    chart = book.Data.chart('c')
    ref = old_chart.ref if impl == 'xlw' else chart.ref
    (old_chart.add_series(chart, ref('Data', 1, 1, 200, 1), ref('Data', 1, 2, 200, 2), label='y')
     if impl == 'xlw' else chart.add_series(ref('Data', 1, 1, 200, 1), ref('Data', 1, 2, 200, 2), label='y'))
    for i in test.count:
        xl.save()


OPERATIONS = [
    ('write', 'xl.write(1.5)', 'cell', run_write_xl),
    ('write', 'sheet.write(1.5)', 'cell', run_write_node),
    ('write', "sheet.write(1.5, 'Heading1')", 'cell', run_write_styled),
    ('read', 'read one cell', 'cell', run_read_cell),
    ('build', 'build 10 000 numbers, one block', 'book', run_build('10k')),
    ('build', 'build 100 000 numbers, one block', 'book', run_build('100k')),
    ('build', 'build 2 000 x 5 mixed cells', 'book', run_build('mixed')),
    ('save', 'save 10 000 numbers', 'book', run_save('10k')),
    ('save', 'save 100 000 numbers', 'book', run_save('100k')),
    ('save', 'save 2 000 x 5 mixed cells', 'book', run_save('mixed')),
    ('open', 'open 10 000 numbers', 'book', run_open('10k')),
    ('open', 'open 100 000 numbers', 'book', run_open('100k')),
    ('open', 'open 2 000 x 5 mixed cells', 'book', run_open('mixed')),
    ('chart', 'save a book with a chart of 200 points', 'book', run_chart_save),
]
for number, (kind, label, unit, run) in enumerate(OPERATIONS):
    for impl, method in make(label, f'{number:02d} {kind}: {label}', run).items():
        setattr(b_compare, f'bench_{number:02d}_{kind}_{impl.replace("4", "four")}', method)
