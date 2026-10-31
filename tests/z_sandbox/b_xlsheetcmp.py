"""
b_xlsheetcmp.py -- sandbox: the new worksheet codec against the old sheet_data / read_cells.

Question   How much do the style cache, the inlined cell text and the regex scanner of
           xlsheet (pure Python, phase 2) save over xlw.sheet_data and xlreader.read_cells?
Hypothesis Emit: the style cache removes the style_key + kv lookup per cell, about 30% of
           the emit. Scan: the regex scan removes the 4 parser events, local() and the
           reference regex per cell, about 2x on the read of a sheet.
Method     Two 5 000 cell sheets: 'num' (500 x 10 numbers) and 'mix' (numbers, text with
           repeats, booleans). One op = one emit, or one read of the part into a fresh
           sheet. The old read opens the part from an in-memory zip, the new one reads the
           bytes from the same zip first, so both pay for the decompression.
Result     AC power, ms per 5 000 cells (old -> new): emit num 18.0 -> 13.0, emit mix 14.2 ->
           11.4 (about -25%); scan num 35.6 -> 16.8, scan mix 34.9 -> 16.5 (2.1x). What is
           left is mostly tkv: cell.entries() per cell on the way out, sheet.node() and the
           leaf writes on the way in. A Cython xlsheet alone would gain little more; the
           next step is a tkv2 with a bulk cell read and a bulk node insert.

Run from the project root:
    python tools/runbench.py tests/z_sandbox/b_xlsheetcmp.py
"""

import io
import os
import shutil
import sys
import zipfile


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

SOURCES = ['xlsheet', 'xlw', 'xlreader']
globals().update(load('xlw', into={}))
import xlw as xlwmodule
import xlreader
import xlsheet

OUTDIR = os.path.join(ROOT, 'results', 'b_xlsheetcmp')
REFERENCE = os.path.join(ROOT, 'results', 'reference')
REAL = {'isotherm': 'Theophylline Isotherm.xlsx', 'solubility': 'SB Solubility vs temperature.xlsx',
        'xrd': 'Theopylline As recieved.xlsx'}


class NewCodec:
    """While active, xlw reads worksheets with xlsheet.xml_to_sheet and writes them with
    xlsheet.sheet_to_xml; leaving restores the original functions."""

    def __enter__(me):
        me.read = xlreader.read_cells
        me.write = xlwmodule.sheet_data

        def read_cells(archive, path, sheet, strings, deltas, report):
            return xlsheet.xml_to_sheet(archive.read(path), sheet, strings, deltas, report)
        xlreader.read_cells = read_cells
        xlwmodule.sheet_data = xlsheet.sheet_to_xml
        return me

    def __exit__(me, *exc):
        xlreader.read_cells = me.read
        xlwmodule.sheet_data = me.write


class Quiet:
    def add(self, message):
        pass


HEAD = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="'
        'http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>')


def formula_part(nstrings, number_formulas, text_formulas, only_last_row=False):
    """A worksheet part as bytes, 500 rows x 10 columns: column A shared text, B-D numbers,
    column E a numeric formula, F-G numbers, H a text formula, I-J numbers. The formula
    columns are present only where asked, otherwise numbers fill them; with only_last_row
    a formula appears in the last row alone (the worst case for an all-or-nothing scan)."""
    rows = []
    for row in range(1, 501):
        cells = []
        for col, letter in enumerate('ABCDEFGHIJ'):
            ref = f'{letter}{row}'
            formula = (not only_last_row) or row == 500
            if col == 0:
                cells.append(f'<c r="{ref}" t="s"><v>{row % nstrings}</v></c>')
            elif col == 4 and number_formulas and formula:
                cells.append(f'<c r="{ref}"><f>SUM(B{row}:D{row})</f><v>{row * 0.003}</v></c>')
            elif col == 7 and text_formulas and formula:
                cells.append(f'<c r="{ref}" t="str"><f>A{row}&amp;"x"</f><v>text {row}</v></c>')
            else:
                cells.append(f'<c r="{ref}"><v>{row * 0.001 + col}</v></c>')
        rows.append(f'<row r="{row}">' + ''.join(cells) + '</row>')
    return (HEAD + ''.join(rows) + '</sheetData></worksheet>').encode('utf-8')


class b_xlsheetcmp(bench):
    BenchName = 'xlsheetcmp'
    BenchVersion = 'M1.0.6'
    BenchHeader = ''
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        os.makedirs(OUTDIR, exist_ok=True)
        xl = xlw()
        xl.newbook(os.path.join(OUTDIR, 'cmp'), 'num', 'mix')
        book = xl.cmp
        book.num.write([[row * 0.001 + col for col in range(10)] for row in range(500)])
        mixed = []
        for row in range(500):
            line = []
            for col in range(10):
                if col % 3 == 0:
                    line.append(f'label {col} {row % 7}')
                elif col % 5 == 1:
                    line.append(row % 2 == 0)
                else:
                    line.append(row * 0.001 + col)
            mixed.append(line)
        book.mix.write(mixed)
        xl.save()
        cls.book = book
        cls.sheets = {'num': book.num, 'mix': book.mix}
        with zipfile.ZipFile(os.path.join(OUTDIR, 'cmp.xlsx')) as archive:
            cls.strings = xlreader.read_strings(archive)
            cls.deltas = xlreader.read_styles(archive, Quiet())
            cls.parts = {'num': archive.read('xl/worksheets/sheet1.xml'),
                         'mix': archive.read('xl/worksheets/sheet2.xml')}
        count = len(cls.strings)
        cls.parts['fx1'] = formula_part(count, True, False, only_last_row=True)
        cls.parts['fx20'] = formula_part(count, True, True)
        cls.archives = {}
        for name, data in cls.parts.items():
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('p.xml', data)
            cls.archives[name] = zipfile.ZipFile(buffer)
        cls.real = {}
        for key, name in REAL.items():
            source = os.path.join(REFERENCE, name)
            if not os.path.isfile(source):
                continue
            local = os.path.join(OUTDIR, name)
            shutil.copyfile(source, local)
            xl = xlw()
            book = xl.open(local)
            cells = 0
            for sheetkey in book.kvr('priv').kvr('sheetkeys'):
                cells += len(xlsheet.sheet_cells(book.kvr(sheetkey)))
            cls.real[key] = (local, xl, cells)
        cls.target = xlw()
        cls.target.newbook(os.path.join(OUTDIR, 'target'), 'W')
        cls.serial = 0

    def fresh(self):
        type(self).serial += 1
        return self.target.newsheet(f's{self.serial}')

    def test_T1_emit_is_identical_for_both_sheets(self):
        for name, sheet in self.sheets.items():
            old = xlwmodule.SaveState()
            new = xlwmodule.SaveState()
            self.assertEqual(xlsheet.sheet_to_xml(sheet, new),
                             xlwmodule.sheet_data(sheet, old), name)
            self.assertEqual(new.styles, old.styles)
            self.assertEqual(new.strings, old.strings)

    def test_T2_scan_reads_the_same_cells_without_falling_back(self):
        for name in self.parts:
            tables = []
            for which in (0, 1):
                sheet = self.fresh()
                if which == 0:
                    xlreader.read_cells(self.archives[name], 'p.xml', sheet,
                                        list(self.strings), list(self.deltas), Quiet())
                else:
                    xlsheet.xml_to_sheet(self.parts[name], sheet, list(self.strings),
                                         list(self.deltas), Quiet())
                tables.append({n: [(k, v) for k, v in c.entries()]
                               for n, c in zip(sheet.names(), sheet.nodes())})
            self.assertEqual(tables[0], tables[1], name)

    # ---- the real workbooks: one op = open the whole file, or save the opened book -------
    def read_real(self, timer, key, new):
        if key not in self.real:
            self.skipTest('no reference workbook in results/reference')
        local = self.real[key][0]
        if new:
            with NewCodec():
                with timer as test:
                    while test.more:
                        for i in test.count:
                            xlw().open(local)
        else:
            with timer as test:
                while test.more:
                    for i in test.count:
                        xlw().open(local)
        cells = self.real[key][2]
        return f'{"new" if new else "old"} open', f'read {key}: {cells} cells'

    def write_real(self, timer, key, new):
        if key not in self.real:
            self.skipTest('no reference workbook in results/reference')
        xl = self.real[key][1]
        if new:
            with NewCodec():
                with timer as test:
                    while test.more:
                        for i in test.count:
                            xl.save()
        else:
            with timer as test:
                while test.more:
                    for i in test.count:
                        xl.save()
        cells = self.real[key][2]
        return f'{"new" if new else "old"} save', f'write {key}: {cells} cells'

    def bench_real_xrd_read_old(self, timer):
        return self.read_real(timer, 'xrd', False)

    def bench_real_xrd_read_new(self, timer):
        return self.read_real(timer, 'xrd', True)

    def bench_real_xrd_write_old(self, timer):
        return self.write_real(timer, 'xrd', False)

    def bench_real_xrd_write_new(self, timer):
        return self.write_real(timer, 'xrd', True)

    def bench_real_solubility_read_old(self, timer):
        return self.read_real(timer, 'solubility', False)

    def bench_real_solubility_read_new(self, timer):
        return self.read_real(timer, 'solubility', True)

    def bench_real_solubility_write_old(self, timer):
        return self.write_real(timer, 'solubility', False)

    def bench_real_solubility_write_new(self, timer):
        return self.write_real(timer, 'solubility', True)

    def bench_real_isotherm_read_old(self, timer):
        return self.read_real(timer, 'isotherm', False)

    def bench_real_isotherm_read_new(self, timer):
        return self.read_real(timer, 'isotherm', True)

    def bench_real_isotherm_write_old(self, timer):
        return self.write_real(timer, 'isotherm', False)

    def bench_real_isotherm_write_new(self, timer):
        return self.write_real(timer, 'isotherm', True)

    # ---- emit: one op = the sheetData of 5 000 cells --------------------------------------
    def bench_emit_old_num(self, timer):
        sheet = self.sheets['num']
        old = xlwmodule.sheet_data
        with timer as test:
            while test.more:
                for i in test.count:
                    old(sheet, xlwmodule.SaveState())
        return 'old sheet_data', 'emit num 5 000 cells'

    def bench_emit_new_num(self, timer):
        sheet = self.sheets['num']
        new = xlsheet.sheet_to_xml
        with timer as test:
            while test.more:
                for i in test.count:
                    new(sheet, xlwmodule.SaveState())
        return 'xlsheet.sheet_to_xml', 'emit num 5 000 cells'

    def bench_emit_old_mix(self, timer):
        sheet = self.sheets['mix']
        old = xlwmodule.sheet_data
        with timer as test:
            while test.more:
                for i in test.count:
                    old(sheet, xlwmodule.SaveState())
        return 'old sheet_data', 'emit mix 5 000 cells'

    def bench_emit_new_mix(self, timer):
        sheet = self.sheets['mix']
        new = xlsheet.sheet_to_xml
        with timer as test:
            while test.more:
                for i in test.count:
                    new(sheet, xlwmodule.SaveState())
        return 'xlsheet.sheet_to_xml', 'emit mix 5 000 cells'

    # ---- scan: one op = the part of 5 000 cells read into a fresh sheet --------------------
    def bench_scan_old_num(self, timer):
        archive = self.archives['num']
        strings = self.strings
        deltas = self.deltas
        old = xlreader.read_cells
        with timer as test:
            while test.more:
                for i in test.count:
                    old(archive, 'p.xml', self.fresh(), strings, deltas, Quiet())
        return 'old read_cells', 'scan num 5 000 cells'

    def bench_scan_new_num(self, timer):
        archive = self.archives['num']
        strings = self.strings
        deltas = self.deltas
        new = xlsheet.xml_to_sheet
        with timer as test:
            while test.more:
                for i in test.count:
                    new(archive.read('p.xml'), self.fresh(), strings, deltas, Quiet())
        return 'xlsheet.xml_to_sheet', 'scan num 5 000 cells'

    # ---- formulas: fx1 = one formula cell in 5 000, fx20 = 20% formula cells ------------------
    def bench_scan_old_fx1(self, timer):
        archive = self.archives['fx1']
        strings = self.strings
        deltas = self.deltas
        old = xlreader.read_cells
        with timer as test:
            while test.more:
                for i in test.count:
                    old(archive, 'p.xml', self.fresh(), strings, deltas, Quiet())
        return 'old read_cells', 'scan fx1: 1 formula in 5 000 cells'

    def bench_scan_new_fx1(self, timer):
        archive = self.archives['fx1']
        strings = self.strings
        deltas = self.deltas
        new = xlsheet.xml_to_sheet
        with timer as test:
            while test.more:
                for i in test.count:
                    new(archive.read('p.xml'), self.fresh(), strings, deltas, Quiet())
        return 'xlsheet.xml_to_sheet', 'scan fx1: 1 formula in 5 000 cells'

    def bench_scan_old_fx20(self, timer):
        archive = self.archives['fx20']
        strings = self.strings
        deltas = self.deltas
        old = xlreader.read_cells
        with timer as test:
            while test.more:
                for i in test.count:
                    old(archive, 'p.xml', self.fresh(), strings, deltas, Quiet())
        return 'old read_cells', 'scan fx20: 20% formula cells, text and numbers'

    def bench_scan_new_fx20(self, timer):
        archive = self.archives['fx20']
        strings = self.strings
        deltas = self.deltas
        new = xlsheet.xml_to_sheet
        with timer as test:
            while test.more:
                for i in test.count:
                    new(archive.read('p.xml'), self.fresh(), strings, deltas, Quiet())
        return 'xlsheet.xml_to_sheet', 'scan fx20: 20% formula cells, text and numbers'

    def bench_scan_old_mix(self, timer):
        archive = self.archives['mix']
        strings = self.strings
        deltas = self.deltas
        old = xlreader.read_cells
        with timer as test:
            while test.more:
                for i in test.count:
                    old(archive, 'p.xml', self.fresh(), strings, deltas, Quiet())
        return 'old read_cells', 'scan mix 5 000 cells'

    def bench_scan_new_mix(self, timer):
        archive = self.archives['mix']
        strings = self.strings
        deltas = self.deltas
        new = xlsheet.xml_to_sheet
        with timer as test:
            while test.more:
                for i in test.count:
                    new(archive.read('p.xml'), self.fresh(), strings, deltas, Quiet())
        return 'xlsheet.xml_to_sheet', 'scan mix 5 000 cells'
