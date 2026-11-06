# BROKEN 2026-11-05: use.compile has no optimisation argument any more (-O1 only) - the experiment is done, its result is in the docstring and in use.compile; run it only against prev/usesetuptools.py
r"""b_optlevel.py -- experiment: does gcc -O2 make the compiled lexer faster than -O1?

Question: use.compile now builds with -O2 (setuptools built with -O1). Is that worth it?
Variants: the same source, rs3lex.pyx, copied four times (lexo0.pyx .. lexo3.pyx: a
module's file name is its name) and built with use.compile(..., optimisation='O0' .. 'O3')
into tests/z_sandbox/optlevel/. -O0 is there to show that the flag does anything at all. Each variant lexes the same file (tools/use.py) with its
own lex(lines, lang): no cache is involved, so every call does the work.
Hypothesis: -O2 is a few per cent faster at most, since the lexer spends its time in
Python's own machinery (strings, lists, calls) and not in loops that gcc can tighten.
The folder is kept between runs (OneDrive may hold files in it, so it is not deleted);
the suite only rewrites what it needs. Compare r only between rows of one report, and
runs only at a similar speed % (BATTERY and THROTTLED runs are slower).

Result: (filled in after the run, see the report and the docstring of use.compile).

Result (2026-11-05, power AC, one run): -O0 15.75 ms, -O1 11.17, -O2 11.56, -O3 11.24 (se 0.6-1.2%).
The flag matters from -O0 to -O1 (30%); beyond that nothing is gained. Chosen: -O1.

Run from the project root:
    python tools/runbench.py tests/z_sandbox/b_optlevel.py -timeout=300
"""
import importlib
import os
import shutil
import sys
from types import SimpleNamespace

from bench import bench
from use import load

SOURCES = ['use']
load(asmodule=['use'])

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
RS3 = os.path.join(ROOT, 'tools', 'primary', 'rs3')
FOLDER = os.path.join(HERE, 'optlevel')
SAMPLE = os.path.join(ROOT, 'tools', 'use.py')           # the file the variants lex
LEVELS = (('lexo0', 'O0'), ('lexo1', 'O1'), ('lexo2', 'O2'), ('lexo3', 'O3'))


class b_optlevel(bench):
    BenchName = 'optlevel'
    BenchVersion = 'M1.0.2'          # runbench adds 1 to the last number on every run
    BenchHeader = 'rs3lex.lex built with -O1 and with -O2, on the same file'
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        os.makedirs(FOLDER, exist_ok=True)
        if not os.path.isdir(os.path.join(FOLDER, 'lang')):        # the module reads its lang folder
            shutil.copytree(os.path.join(RS3, 'lang'), os.path.join(FOLDER, 'lang'))
        cls.mods = {}
        for name, level in LEVELS:
            shutil.copyfile(os.path.join(RS3, 'rs3lex.pyx'), os.path.join(FOLDER, name + '.pyx'))
            use.compile(os.path.join(FOLDER, name + '.pyx'), optimisation=level)
        sys.path.insert(0, os.path.join(FOLDER, 'pyxfiles'))
        importlib.invalidate_caches()
        for name, level in LEVELS:
            cls.mods[name] = importlib.import_module(name)
        with open(SAMPLE, encoding='utf-8') as f:
            cls.lines = f.read().split('\n')
        cls.lang = cls.mods['lexo1'].language(SAMPLE)

    def test_T1_every_build_lexes_the_file_to_the_same_pieces(self):
        first = None
        for name, level in LEVELS:
            mod = self.mods[name]
            got = mod.lex(self.lines, mod.language(SAMPLE))
            self.assertGreater(len(got), 500)
            first = first or got
            self.assertEqual(got, first, level)

    def bench_lex_built_with_O0(self, timer):
        return self.timed(timer, 'lexo0', 'O0')

    def bench_lex_built_with_O1(self, timer):
        return self.timed(timer, 'lexo1', 'O1')

    def bench_lex_built_with_O2(self, timer):
        return self.timed(timer, 'lexo2', 'O2')

    def bench_lex_built_with_O3(self, timer):
        return self.timed(timer, 'lexo3', 'O3')

    def timed(self, timer, name, level):
        mod = self.mods[name]
        lang = mod.language(SAMPLE)
        with timer as test:
            while test.more:
                for _ in test.count:
                    mod.lex(self.lines, lang)
        return f'lex of use.py ({len(self.lines)} lines), -{level}', 'optlevel'
