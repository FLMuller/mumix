"""
b_textscan -- sandbox: how should the fast scan take a text that sits in the cell itself?

Question
    A worksheet cell can hold its text in the cell (t="inlineStr", <is><t>..</t></is>) in place
    of an index into the shared strings. The grid stores a text as (TXT, position), so the scan
    must turn the characters into a position. Variants:
      key_bytes   the file's bytes go to the text kv as they are (the bytes key of kv M04)
      key_str     the bytes are decoded to a str first, the way xlsheet.text_id does it
      keep_raw    the cell keeps the raw bytes, no text table (an INL kind, not built yet)
    End to end, one sheet of 500 rows x 10 columns (a text column, nine number columns):
      scan_shared / scan_inline   xlsheetfun.scan_cells on the body, into fresh kv stores
      read_inline_fun / _python   xlsheet.xml_to_sheet on the same part, scan on and off

Hypothesis
    key_bytes is a little faster than key_str (it saves one decode and one encode per text
    cell); keep_raw is the fastest of the three (no lookup at all); an inline sheet read by the
    scan is close to the shared-string sheet and several times faster than the Python path.

Result
    One run, AC power, speed 166% (report results/textscan_2026.11.01_00;32.html), per op:
      text cell, bytes key              0.192 us    decode + str key    0.247 us   (bytes 22% less)
      text cell, keep the bytes         0.513 us    bytes key + cell    0.748 us   (keep 31% less)
      scan 5000 cells, shared strings   3.50 ms     inline text         3.58 ms    (+2%)
      xml_to_sheet, inline, Cython scan 3.67 ms     Python path        10.12 ms    (2.8x)
    The hypothesis holds on all three counts. Limits: 28 distinct texts, so nearly every lookup
    is a hit; the keep_raw and intern micros overwrite 500 cell keys, not new ones. One run.

Run
    python tools/runbench.py tests/z_sandbox/b_textscan.py -timeout=55 -name=textscan
"""

import os
import sys


def findtools():                      # walk up to the folder that holds tools/
    from os.path import abspath, dirname, isdir, join
    here = dirname(abspath(__file__))
    while here != dirname(here) and not isdir(join(here, 'tools')):
        here = dirname(here)
    sys.path.insert(0, join(here, 'tools'))
    return here


ROOT = findtools()
sys.path.insert(0, ROOT)
from use import load
from bench import bench
import mumix                                      # puts tools, xlw on sys.path

SOURCES = ['xlsheetfun']
load('xlw')
from kv import kv
import xlreader
import xlsheet

OUTDIR = os.path.join(ROOT, 'results', 'b_textscan')
HEAD = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="'
        'http://schemas.openxmlformats.org/spreadsheetml/2006/main">')
NROWS = 500
NDISTINCT = 28
TXT = 1                                           # the kind numbers of xlsheet
INL = 9                                           # keep_raw's stand-in kind


def label(row):
    return f'label {row % NDISTINCT}'


def cell_body(inline):
    """500 rows x 10 columns: column A text (shared index or inline), B-J numbers."""
    rows = []
    for row in range(1, NROWS + 1):
        cells = []
        for col, letter in enumerate('ABCDEFGHIJ'):
            ref = f'{letter}{row}'
            if col == 0 and inline:
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{label(row)}</t></is></c>')
            elif col == 0:
                cells.append(f'<c r="{ref}" t="s"><v>{row % NDISTINCT}</v></c>')
            else:
                cells.append(f'<c r="{ref}"><v>{row * 0.001 + col}</v></c>')
        rows.append(f'<row r="{row}">' + ''.join(cells) + '</row>')
    return ''.join(rows)


def part(inline):
    return (HEAD + '<sheetData>' + cell_body(inline) + '</sheetData></worksheet>').encode()


def no_entities(raw):
    raise AssertionError('the benchmark texts have no entities')


class b_textscan(bench):
    BenchName = "textscan"
    BenchVersion = "M1.0.7"
    BenchHeader = ""
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        os.makedirs(OUTDIR, exist_ok=True)
        cls.body_shared = cell_body(False).encode()
        cls.body_inline = cell_body(True).encode()
        cls.part_shared = part(False)
        cls.part_inline = part(True)
        cls.slices = [label(row).encode() for row in range(1, NROWS + 1)]
        cls.xfs = [{}]
        cls.scan = staticmethod(xlsheet.FUN['scan_cells'])
        xl = xlw()
        xl.newbook(os.path.join(OUTDIR, 'book'), 'S')
        cls.sheet = xl.book.S
        cls.strings = [label(i) for i in range(NDISTINCT)]
        cls.remap = xlsheet.fill_tables(xlsheet.tables_of(cls.sheet), cls.strings, [{}])
        cls.report = xlreader.Collector()

    # ---- the cells the variants make --------------------------------------------------------
    def scanned(self, body, texts):
        cells = kv()
        count = self.scan(body, cells, self.xfs, self.remap, texts, no_entities)
        return count, cells

    def test_T01_the_scan_reads_inline_text_into_the_text_table(self):
        texts = kv()
        count, cells = self.scanned(self.body_inline, texts)
        self.assertEqual(count, NROWS * 10)
        self.assertEqual(len(texts), NDISTINCT)
        first = cells.kvr((1, 1))
        self.assertEqual((first[0], texts.at(first[1])), (TXT, 'label 1'))

    def test_T02_inline_and_shared_text_give_the_same_cells(self):
        texts = kv()
        for text in self.strings:
            texts.kvw(text, len(texts))
        _, inline = self.scanned(self.body_inline, texts)
        shared_cells = kv()
        self.scan(self.body_shared, shared_cells, self.xfs, None, texts, no_entities)
        self.assertEqual(inline.indici(), shared_cells.indici())
        self.assertEqual([inline.kvr(key) for key in inline.indici()],
                         [shared_cells.kvr(key) for key in shared_cells.indici()])

    def test_T03_a_bytes_key_and_its_str_are_one_text(self):
        texts = kv()
        texts.kvw(b'label 1', 0)
        self.assertEqual(texts.kvr('label 1'), 0)

    def test_T04_python_and_scan_paths_read_the_inline_part_alike(self):
        tables = xlsheet.tables_of(self.sheet)
        results = []
        for fun in (xlsheet.FUN, None):
            saved = xlsheet.FUN
            xlsheet.FUN = fun
            try:
                xl = xlw()
                xl.newbook(os.path.join(OUTDIR, 'alike'), 'S')
                sheet = xl.alike.S
                xlsheet.xml_to_sheet(self.part_inline, sheet, xlreader.Collector(), None)
                results.append([(xlsheet.cell_value(sheet, row, 1)) for row in range(1, 6)])
            finally:
                xlsheet.FUN = saved
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0][0], 'label 1')

    # ---- the key, one text cell per op -----------------------------------------------------
    def bench_key_bytes(self, timer):
        slices = self.slices
        n = len(slices)
        texts = kv()
        with timer as test:
            while test.more:
                for i in test.count:
                    raw = slices[i % n]
                    found = texts.kvr(raw)
                    if found is None:
                        texts.kvw(raw, len(texts))
        return "text cell: bytes key", "key"

    def bench_key_str(self, timer):
        slices = self.slices
        n = len(slices)
        texts = kv()
        with timer as test:
            while test.more:
                for i in test.count:
                    text = slices[i % n].decode('utf-8')
                    found = texts.kvr(text)
                    if found is None:
                        texts.kvw(text, len(texts))
        return "text cell: decode, str key", "key"

    def bench_keep_raw(self, timer):
        slices = self.slices
        n = len(slices)
        cells = kv()
        with timer as test:
            while test.more:
                for i in test.count:
                    cells[(i % n, 1)] = (INL, slices[i % n], 0)
        return "text cell: keep the bytes, no table", "key"

    def bench_intern_bytes(self, timer):
        slices = self.slices
        n = len(slices)
        cells = kv()
        texts = kv()
        with timer as test:
            while test.more:
                for i in test.count:
                    raw = slices[i % n]
                    found = texts.kvr(raw)
                    if found is None:
                        found = len(texts)
                        texts.kvw(raw, found)
                    cells[(i % n, 1)] = (TXT, found, 0)
        return "text cell: bytes key and the cell write", "key"

    # ---- a whole sheet per op ---------------------------------------------------------------
    def bench_scan_shared(self, timer):
        body = self.body_shared
        with timer as test:
            while test.more:
                for i in test.count:
                    self.scan(body, kv(), self.xfs, self.remap, kv(), no_entities)
        return "scan 5000 cells, shared strings", "sheet"

    def bench_scan_inline(self, timer):
        body = self.body_inline
        with timer as test:
            while test.more:
                for i in test.count:
                    self.scan(body, kv(), self.xfs, self.remap, kv(), no_entities)
        return "scan 5000 cells, inline text", "sheet"

    def read(self, data, fun):
        saved = xlsheet.FUN
        xlsheet.FUN = fun
        try:
            xlsheet.xml_to_sheet(data, self.sheet, self.report, self.remap)
        finally:
            xlsheet.FUN = saved

    def bench_read_inline_fun(self, timer):
        data = self.part_inline
        fun = xlsheet.FUN
        with timer as test:
            while test.more:
                for i in test.count:
                    self.read(data, fun)
        return "xml_to_sheet, inline text, Cython scan", "sheet"

    def bench_read_inline_python(self, timer):
        data = self.part_inline
        with timer as test:
            while test.more:
                for i in test.count:
                    self.read(data, None)
        return "xml_to_sheet, inline text, Python path", "sheet"


if __name__ == "__main__":
    from runbench import runbench
    name = os.path.splitext(os.path.basename(__file__))[0]
    sys.exit(runbench([name], timeout=55))
