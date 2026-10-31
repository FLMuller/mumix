"""
b_xlwopen.py -- sandbox: where does xlw.open() spend its time, and inside read_cells?

Question 1 Opening costs 31-42 us a cell, about 3x saving. Which part of read_book is it?
Hypothesis 1 XML parsing and the per-cell work split it; shared strings play no part in a
           numeric file. Method: test_T2 runs cProfile over open() of a 5 000 cell workbook
           (a test may take 1 s; the proportions do not depend on the size) and writes the
           tables to results/b_xlwopen/profile.txt. Result: read_cells itself about 49%,
           iterparse about 25%, local() about 10%, reference decoding about 9%, styles 3%.
Question 2 Inside read_cells, what does each step cost? The bench rows "stage n" are a
           ladder: each stage is the previous one plus one more step, over the same 5 000
           cell sheet XML, so the difference of two rows is the marginal cost of a step. The
           last rows try cheap variants (no local(), end events only, cached column).
Question 3 How much does the shape of a cell cost? 5 000 cells with a value and one style
           leaf each, stored as: a tkv node with two leaves (today); a kv record held at the
           sparse key of the sheet; one kv per sheet with a tuple (value, style) at each
           sparse key; two sparse kvs (values, styles), no per-cell object at all.
Result 3   (see the bench rows 'shape: ...', AC)
Result 2   BATTERY run, ms per 5 000 cells, only 2-8 ops a row (rough): iterparse 31, +local
           and skeleton 16, +reference decode 19, +value 7, +style 0, +tkv node and leaf
           55 (the largest step, 42%), +clear and zip 4: read_cells 132. Variants: no
           local() 102, end events only 93, end only with column cache 73. Production
           xlreader is unchanged.

Run from the project root:
    python tools/runbench.py tests/z_sandbox/b_xlwopen.py
"""

import cProfile
import io
import os
import pstats
import re
import sys
import zipfile
import xml.etree.ElementTree as ET


def findtools():                      # walk up to the folder that holds tools/
    from os.path import abspath, dirname, isdir, join
    here = dirname(abspath(__file__))
    while here != dirname(here) and not isdir(join(here, 'tools')):
        here = dirname(here)
    sys.path.insert(0, join(here, 'tools'))
    return here


ROOT = findtools()
from use import load
from bench import bench

SOURCES = ['xlw', 'xlreader']
globals().update(load('xlw', into={}))
import xlreader
import xlchart
from xlstore import KV

OUTDIR = os.path.join(ROOT, 'results', 'b_xlwopen')
NS = xlreader.NS_MAIN
TAG_C = NS + 'c'
TAG_V = NS + 'v'
ROW_RE = re.compile(r'([A-Z]+)(\d+)')


class Quiet:
    def add(self, message):
        pass


# ---- the ladder: read_cells taken apart. Each stage = the one before + one step. ---------
def stage0(data):
    """iterparse with start and end events, empty body."""
    for event, element in ET.iterparse(io.BytesIO(data), events=('start', 'end')):
        pass


def stage1(data):
    """+ local(tag) and the start/end, depth skeleton."""
    depth = 0
    known = xlreader.SHEET_KNOWN
    for event, element in ET.iterparse(io.BytesIO(data), events=('start', 'end')):
        name = xlreader.local(element.tag)
        if event == 'start':
            depth += 1
            if depth == 2 and name not in known:
                pass
            if name == 'sheetView' and element.get('showGridLines') in ('0', 'false'):
                pass
            continue
        depth -= 1


def stage2(data):
    """+ for a closing <c>: the reference regex, letters2col, int(row)."""
    depth = 0
    known = xlreader.SHEET_KNOWN
    for event, element in ET.iterparse(io.BytesIO(data), events=('start', 'end')):
        name = xlreader.local(element.tag)
        if event == 'start':
            depth += 1
            if depth == 2 and name not in known:
                pass
            if name == 'sheetView' and element.get('showGridLines') in ('0', 'false'):
                pass
            continue
        depth -= 1
        if name == 'c':
            reference = ROW_RE.match(element.get('r'))
            col = xlchart.letters2col(reference.group(1))
            row = int(reference.group(2))


def stage3(data):
    """+ the value: type attribute, find <v>, find <f>, float()."""
    depth = 0
    known = xlreader.SHEET_KNOWN
    formulas = 0
    for event, element in ET.iterparse(io.BytesIO(data), events=('start', 'end')):
        name = xlreader.local(element.tag)
        if event == 'start':
            depth += 1
            if depth == 2 and name not in known:
                pass
            if name == 'sheetView' and element.get('showGridLines') in ('0', 'false'):
                pass
            continue
        depth -= 1
        if name == 'c':
            reference = ROW_RE.match(element.get('r'))
            col = xlchart.letters2col(reference.group(1))
            row = int(reference.group(2))
            kind = element.get('t')
            raw = element.find(NS + 'v')
            if element.find(NS + 'f') is not None:
                formulas += 1
            if raw is None or raw.text is None:
                value = None
            else:
                value = float(raw.text)


def stage4(data):
    """+ the style lookup: int(get('s')), deltas[style]."""
    depth = 0
    known = xlreader.SHEET_KNOWN
    formulas = 0
    deltas = [{}]
    for event, element in ET.iterparse(io.BytesIO(data), events=('start', 'end')):
        name = xlreader.local(element.tag)
        if event == 'start':
            depth += 1
            if depth == 2 and name not in known:
                pass
            if name == 'sheetView' and element.get('showGridLines') in ('0', 'false'):
                pass
            continue
        depth -= 1
        if name == 'c':
            reference = ROW_RE.match(element.get('r'))
            col = xlchart.letters2col(reference.group(1))
            row = int(reference.group(2))
            kind = element.get('t')
            raw = element.find(NS + 'v')
            if element.find(NS + 'f') is not None:
                formulas += 1
            if raw is None or raw.text is None:
                value = None
            else:
                value = float(raw.text)
            style = int(element.get('s', 0))
            delta = deltas[style] if style < len(deltas) else {}


def stage5(data, sheet):
    """+ the node and its value leaf in a fresh sheet (all of read_cells but clear())."""
    depth = 0
    known = xlreader.SHEET_KNOWN
    formulas = 0
    deltas = [{}]
    for event, element in ET.iterparse(io.BytesIO(data), events=('start', 'end')):
        name = xlreader.local(element.tag)
        if event == 'start':
            depth += 1
            if depth == 2 and name not in known:
                pass
            if name == 'sheetView' and element.get('showGridLines') in ('0', 'false'):
                pass
            continue
        depth -= 1
        if name == 'c':
            reference = ROW_RE.match(element.get('r'))
            col = xlchart.letters2col(reference.group(1))
            row = int(reference.group(2))
            kind = element.get('t')
            raw = element.find(NS + 'v')
            if element.find(NS + 'f') is not None:
                formulas += 1
            if raw is None or raw.text is None:
                value = None
            else:
                value = float(raw.text)
            style = int(element.get('s', 0))
            delta = deltas[style] if style < len(deltas) else {}
            if value is not None or delta:
                cell = sheet.node(row, col)
                cell['val'] = xlreader.xlw_blank(value)
                for prop, setting in delta.items():
                    cell[prop] = setting


# ---- the cheap variants ----------------------------------------------------------------
def variant_no_local(data, sheet):
    """stage 5 + clear(), tags compared directly: no local(), no per-event rsplit."""
    depth = 0
    deltas = [{}]
    for event, element in ET.iterparse(io.BytesIO(data), events=('start', 'end')):
        if event == 'start':
            depth += 1
            continue
        depth -= 1
        if element.tag == TAG_C:
            reference = ROW_RE.match(element.get('r'))
            col = xlchart.letters2col(reference.group(1))
            row = int(reference.group(2))
            raw = element.find(TAG_V)
            value = None if raw is None or raw.text is None else float(raw.text)
            style = int(element.get('s', 0))
            delta = deltas[style] if style < len(deltas) else {}
            if value is not None or delta:
                cell = sheet.node(row, col)
                cell['val'] = xlreader.xlw_blank(value)
                for prop, setting in delta.items():
                    cell[prop] = setting
            element.clear()


def variant_end_only(data, sheet):
    """End events only, tags compared directly (the start-event checks would be made once
    on the top-level elements instead)."""
    deltas = [{}]
    for event, element in ET.iterparse(io.BytesIO(data), events=('end',)):
        if element.tag == TAG_C:
            reference = ROW_RE.match(element.get('r'))
            col = xlchart.letters2col(reference.group(1))
            row = int(reference.group(2))
            raw = element.find(TAG_V)
            value = None if raw is None or raw.text is None else float(raw.text)
            style = int(element.get('s', 0))
            delta = deltas[style] if style < len(deltas) else {}
            if value is not None or delta:
                cell = sheet.node(row, col)
                cell['val'] = xlreader.xlw_blank(value)
                for prop, setting in delta.items():
                    cell[prop] = setting
            element.clear()


def variant_end_cached(data, sheet):
    """variant_end_only + the column letters looked up in a dict, and the reference split
    with one rstrip instead of a regex."""
    deltas = [{}]
    columns = {}
    for event, element in ET.iterparse(io.BytesIO(data), events=('end',)):
        if element.tag == TAG_C:
            reference = element.get('r')
            letters = reference.rstrip('0123456789')
            col = columns.get(letters)
            if col is None:
                col = columns[letters] = xlchart.letters2col(letters)
            row = int(reference[len(letters):])
            raw = element.find(TAG_V)
            value = None if raw is None or raw.text is None else float(raw.text)
            style = int(element.get('s', 0))
            delta = deltas[style] if style < len(deltas) else {}
            if value is not None or delta:
                cell = sheet.node(row, col)
                cell['val'] = xlreader.xlw_blank(value)
                for prop, setting in delta.items():
                    cell[prop] = setting
            element.clear()


class b_xlwopen(bench):
    BenchName = 'xlwopen'
    BenchVersion = 'M1.0.10'
    BenchHeader = ''
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        os.makedirs(OUTDIR, exist_ok=True)
        cls.filename = os.path.join(OUTDIR, 'open5k.xlsx')
        table = [[i * 0.001 + j for j in range(10)] for i in range(1000)]
        whole = xlw()
        whole.newbook(cls.filename, 'Data')
        whole.write(table[:500])
        whole.save()
        cls.whole = whole
        cls.table5k = table[:500]
        part = xlw()
        part.newbook(os.path.join(OUTDIR, 'open10k'), 'Data')
        part.write(table)
        part.save()
        with zipfile.ZipFile(cls.filename) as archive:
            cls.sheetxml = archive.read('xl/worksheets/sheet1.xml')
        cls.target = xlw()
        cls.target.newbook(os.path.join(OUTDIR, 'target'), 'W')
        cls.serial = 0

    def fresh(self):
        """A new empty sheet in the target book (a unique name each time)."""
        type(self).serial += 1
        return self.target.newsheet(f's{self.serial}')

    def test_T1_open_returns_every_cell(self):
        book = xlw().open(self.filename)
        self.assertEqual(book.Data[500, 10].kvr('val'), 499 * 0.001 + 9)

    def test_T2_profile_of_open(self):
        profiler = cProfile.Profile()
        profiler.enable()
        xlw().open(self.filename)
        profiler.disable()
        text = io.StringIO()
        for order in ('tottime', 'cumulative'):
            text.write(f'--- sorted by {order} ---\n')
            stats = pstats.Stats(profiler, stream=text)
            stats.strip_dirs().sort_stats(order).print_stats(28)
        with open(os.path.join(OUTDIR, 'profile.txt'), 'w', encoding='utf-8') as handle:
            handle.write(text.getvalue())

    def test_T3_variants_read_the_same_cells(self):
        reference = xlw().open(self.filename).Data
        expect = {}
        for name, node in zip(reference.names(), reference.nodes()):
            if name.startswith('('):
                expect[name] = node.kvr('val')
        for function in (stage5, variant_no_local, variant_end_only, variant_end_cached):
            sheet = self.fresh()
            function(self.sheetxml, sheet)
            got = {name: node.kvr('val') for name, node in zip(sheet.names(), sheet.nodes())
                   if name.startswith('(')}
            self.assertEqual(got, expect, function.__name__)

    # ---- one op = one pass over the 5 000 cell sheet -------------------------------------
    def bench_open_10k(self, timer):
        filename = os.path.join(OUTDIR, 'open10k.xlsx')
        with timer as test:
            while test.more:
                for i in test.count:
                    xlw().open(filename)
        return 'open 10 000 cells', 'whole book'

    # ---- like for like: create -> saved against opened -> read, 5 000 cells each way ------
    def bench_pipe_create_to_saved(self, timer):
        table = self.table5k
        with timer as test:
            while test.more:
                for i in test.count:
                    xl = xlw()
                    xl.newbook(os.path.join(OUTDIR, 'pipe'), 'W')
                    xl.write(table)
                    xl.save()
        return 'create to saved: xlw(), write(block), save()', 'pipeline'

    def bench_pipe_opened_to_read(self, timer):
        filename = self.filename
        with timer as test:
            while test.more:
                for i in test.count:
                    sheet = xlw().open(filename).Data
                    for row in range(1, 501):
                        for col in range(1, 11):
                            sheet[row, col].kvr('val')
        return 'opened to read: open(), then every cell value', 'pipeline'

    def bench_pipe_build_only(self, timer):
        table = self.table5k
        with timer as test:
            while test.more:
                for i in test.count:
                    xl = xlw()
                    xl.newbook(os.path.join(OUTDIR, 'pipe'), 'W')
                    xl.write(table)
        return 'create only: xlw(), write(block)', 'pipeline'

    def bench_pipe_save_only(self, timer):
        xl = self.whole
        with timer as test:
            while test.more:
                for i in test.count:
                    xl.save()
        return 'save only (book already built)', 'pipeline'

    def bench_pipe_open_only(self, timer):
        filename = self.filename
        with timer as test:
            while test.more:
                for i in test.count:
                    xlw().open(filename)
        return 'open only', 'pipeline'

    def bench_pipe_nodes_only(self, timer):
        rows = range(1, 501)
        cols = range(1, 11)
        with timer as test:
            while test.more:
                for i in test.count:
                    sheet = self.fresh()
                    for row in rows:
                        for col in cols:
                            sheet.node(row, col)['val'] = 1.5
        return 'nodes only: sheet.node(r, c)[val] = 1.5, 5 000 times', 'pipeline'

    # ---- the shape of a cell: one op = 5 000 cells, value + one style leaf each -------------
    def bench_shape_tkv_node(self, timer):
        rows = range(1, 501)
        cols = range(1, 11)
        with timer as test:
            while test.more:
                for i in test.count:
                    sheet = self.fresh()
                    for row in rows:
                        for col in cols:
                            cell = sheet.node(row, col)
                            cell['val'] = 1.5
                            cell['numfmt'] = '0.00'
        return 'tkv node, 2 leaves (today)', 'shape'

    def bench_shape_kv_record(self, timer):
        rows = range(1, 501)
        cols = range(1, 11)
        with timer as test:
            while test.more:
                for i in test.count:
                    sheet = self.fresh()
                    for row in rows:
                        for col in cols:
                            record = KV()
                            record.kvw('val', 1.5)
                            record.kvw('numfmt', '0.00')
                            sheet[row, col] = record
        return 'kv record at a sparse key of the sheet', 'shape'

    def bench_shape_kv_tuple(self, timer):
        rows = range(1, 501)
        cols = range(1, 11)
        with timer as test:
            while test.more:
                for i in test.count:
                    cells = KV()
                    for row in rows:
                        for col in cols:
                            cells[row, col] = (1.5, 3)
        return 'one kv, tuple (value, style) per sparse key', 'shape'

    def bench_shape_two_kvs(self, timer):
        rows = range(1, 501)
        cols = range(1, 11)
        with timer as test:
            while test.more:
                for i in test.count:
                    values = KV()
                    styles = KV()
                    for row in rows:
                        for col in cols:
                            values[row, col] = 1.5
                            styles[row, col] = 3
        return 'two sparse kvs (values, styles)', 'shape'

    # ---- the text table: text -> index, 5 000 lookups of 100 distinct texts ---------------
    def bench_text_kv(self, timer):
        texts = [f'label {i % 100} of the table' for i in range(5000)]
        index = KV()
        for number in range(100):
            index.kvw('s' + f'label {number} of the table', number)
        with timer as test:
            while test.more:
                for i in test.count:
                    for text in texts:
                        index.kvr('s' + text)
        return 'kv: kvr("s" + text)', 'text lookup'

    def bench_text_kv_bare(self, timer):
        texts = [f'label {i % 100} of the table' for i in range(5000)]
        index = KV()
        for number in range(100):
            index.kvw(f'label {number} of the table', number)
        with timer as test:
            while test.more:
                for i in test.count:
                    for text in texts:
                        index.kvr(text)
        return 'kv: kvr(text), no prefix (texts that start with ( would be refused)', \
            'text lookup'

    def bench_text_kv_hashed(self, timer):
        texts = [f'label {i % 100} of the table' for i in range(5000)]
        mask = 0xFFFFFFFFFFFFFFFF
        index = KV()
        for number in range(100):
            text = f'label {number} of the table'
            index.kvw(f'{hash(text) & mask:016x}', (number, text))
        with timer as test:
            while test.more:
                for i in test.count:
                    for text in texts:
                        entry = index.kvr(f'{hash(text) & mask:016x}')
                        if entry is None or entry[1] != text:
                            continue
        return 'kv: key = 16 hex of hash(text), value (n, text) verified', 'text lookup'

    def bench_text_kv_add(self, timer):
        names = [f'unique text number {i}' for i in range(1000)]
        with timer as test:
            while test.more:
                for i in test.count:
                    table = KV()
                    for number, text in enumerate(names):
                        table.kvw(text, number)
        return 'kv: add 1 000 new texts, kvw(text, n)', 'text add'

    def bench_text_dict_add(self, timer):
        names = [f'unique text number {i}' for i in range(1000)]
        with timer as test:
            while test.more:
                for i in test.count:
                    table = {}
                    order = []
                    for number, text in enumerate(names):
                        table[text] = number
                        order.append(text)
        return 'list + dict: add 1 000 new texts', 'text add'

    def bench_text_kv_order(self, timer):
        table = KV()
        for number in range(1000):
            table.kvw(f'unique text number {number}', number)
        with timer as test:
            while test.more:
                for i in test.count:
                    table.keys()
        return 'kv: keys() of 1 000 texts, the sharedStrings order', 'text in order'

    def bench_text_list_order(self, timer):
        order = [f'unique text number {number}' for number in range(1000)]
        with timer as test:
            while test.more:
                for i in test.count:
                    list(order)
        return 'list: copy of 1 000 texts', 'text in order'

    def bench_text_dict(self, timer):
        texts = [f'label {i % 100} of the table' for i in range(5000)]
        index = {f'label {number} of the table': number for number in range(100)}
        with timer as test:
            while test.more:
                for i in test.count:
                    for text in texts:
                        index.get(text)
        return 'dict: get(text)', 'text lookup'

    def bench_stage0(self, timer):
        data = self.sheetxml
        with timer as test:
            while test.more:
                for i in test.count:
                    stage0(data)
        return 'stage 0: iterparse, empty body', 'ladder'

    def bench_stage1(self, timer):
        data = self.sheetxml
        with timer as test:
            while test.more:
                for i in test.count:
                    stage1(data)
        return 'stage 1: + local(tag), depth skeleton', 'ladder'

    def bench_stage2(self, timer):
        data = self.sheetxml
        with timer as test:
            while test.more:
                for i in test.count:
                    stage2(data)
        return 'stage 2: + reference regex, letters2col', 'ladder'

    def bench_stage3(self, timer):
        data = self.sheetxml
        with timer as test:
            while test.more:
                for i in test.count:
                    stage3(data)
        return 'stage 3: + value (find v, f, float)', 'ladder'

    def bench_stage4(self, timer):
        data = self.sheetxml
        with timer as test:
            while test.more:
                for i in test.count:
                    stage4(data)
        return 'stage 4: + style lookup', 'ladder'

    def bench_stage5(self, timer):
        data = self.sheetxml
        with timer as test:
            while test.more:
                for i in test.count:
                    stage5(data, self.fresh())
        return 'stage 5: + tkv node and leaf (fresh sheet)', 'ladder'

    def bench_read_cells(self, timer):
        filename = self.filename
        with timer as test:
            while test.more:
                for i in test.count:
                    with zipfile.ZipFile(filename) as archive:
                        xlreader.read_cells(archive, 'xl/worksheets/sheet1.xml',
                                            self.fresh(), [], [{}], Quiet())
        return 'read_cells itself (zip open + clear)', 'ladder'

    def bench_variant_no_local(self, timer):
        data = self.sheetxml
        with timer as test:
            while test.more:
                for i in test.count:
                    variant_no_local(data, self.fresh())
        return 'variant: no local(), + clear()', 'variants'

    def bench_variant_end_only(self, timer):
        data = self.sheetxml
        with timer as test:
            while test.more:
                for i in test.count:
                    variant_end_only(data, self.fresh())
        return 'variant: end events only', 'variants'

    def bench_variant_end_cached(self, timer):
        data = self.sheetxml
        with timer as test:
            while test.more:
                for i in test.count:
                    variant_end_cached(data, self.fresh())
        return 'variant: end only + column cache, no regex', 'variants'
