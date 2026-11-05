r"""b_lexparts.py -- experiment: where does the compiled lexer (rs3lex.pyd) spend its time?

Question: the lexer costs about 11 ms for the 1044 lines of tools/use.py, and -O2 against
-O1 made no difference (b_optlevel): the time is in what the code does, not in how gcc
compiles it. Which of its routines is the expensive one?
Variants: one bench_ method per routine of the compiled module, all on the same file, each
with the work of one pass over it: survey (the names of the file), scan (every line, one
state carried across), lex (survey + scan + the loop), functions and build_facts (on the
lexed rows). Read them as parts of lex: lex - survey - scan is the loop and state cost.
Hypothesis: scan, a 355-line function of per-character tests, is most of lex; survey is
small; build_facts costs as much as lex because it walks every token again.
The module is built once as lexparts.pyx (-O2, the default of use.compile) in
tests/z_sandbox/lexparts/, kept between runs (OneDrive may hold files in it).

Result (2026-11-05, power AC, one run): lex 10.9 ms = survey 1.1 + scan 9.8 (89%), the loop
costs nothing; build_facts 5.4 ms (half of lex, not as much as lex); functions 0.6 ms. scan, at
about 9 us a line, is the routine to work on; survey and functions are small.

Run from the project root:
    python tools/runbench.py tests/z_sandbox/b_lexparts.py -timeout=180
"""
import importlib
import os
import shutil
import sys
from types import SimpleNamespace

from bench import bench
from use import load

SOURCES = ['use']
use = SimpleNamespace(**load('use', into={}))

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
RS3 = os.path.join(ROOT, 'tools', 'primary', 'rs3')
FOLDER = os.path.join(HERE, 'lexparts')
SAMPLE = os.path.join(ROOT, 'tools', 'use.py')           # the file every routine works on


class b_lexparts(bench):
    BenchName = 'lexparts'
    BenchVersion = 'M1.0.2'          # runbench adds 1 to the last number on every run
    BenchHeader = 'the routines of the compiled lexer, each on tools/use.py'
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        os.makedirs(FOLDER, exist_ok=True)
        if not os.path.isdir(os.path.join(FOLDER, 'lang')):        # the module reads its lang folder
            shutil.copytree(os.path.join(RS3, 'lang'), os.path.join(FOLDER, 'lang'))
        shutil.copyfile(os.path.join(RS3, 'rs3lex.pyx'), os.path.join(FOLDER, 'lexparts.pyx'))
        use.compile(os.path.join(FOLDER, 'lexparts.pyx'))
        sys.path.insert(0, os.path.join(FOLDER, 'pyxfiles'))
        importlib.invalidate_caches()
        cls.mod = importlib.import_module('lexparts')
        with open(SAMPLE, encoding='utf-8') as f:
            cls.lines = f.read().split('\n')
        cls.lang = cls.mod.language(SAMPLE)
        cls.rows = cls.mod.lex(cls.lines, cls.lang)
        cls.ctx = cls.mod.survey(cls.lines)
        cls.ctx.lang = cls.lang

    def test_T1_the_parts_agree_with_the_whole(self):
        mod = self.mod
        st = mod.new_state()
        rows = []
        for line in self.lines:
            start = (bool(st.block or st.tpl or st.tri), st.depth)
            rows.append((mod.scan(line, st, self.ctx), start[0], start[1]))
        self.assertEqual(len(rows), len(self.rows))
        self.assertGreater(len(vars(mod.build_facts(self.lines, self.rows))), 0)    # a namespace of facts
        self.assertGreater(len(mod.functions(self.lines, self.lang, self.rows)), 5)

    def bench_survey(self, timer):
        survey, lines = self.mod.survey, self.lines
        with timer as test:
            while test.more:
                for _ in test.count:
                    survey(lines)
        return f'survey of use.py ({len(lines)} lines)', 'lexparts'

    def bench_scan_every_line(self, timer):
        mod, lines, ctx = self.mod, self.lines, self.ctx
        with timer as test:
            while test.more:
                for _ in test.count:
                    st = mod.new_state()
                    for line in lines:
                        mod.scan(line, st, ctx)
        return 'scan of every line, one state carried across', 'lexparts'

    def bench_lex_the_whole(self, timer):
        mod, lines, lang = self.mod, self.lines, self.lang
        with timer as test:
            while test.more:
                for _ in test.count:
                    mod.lex(lines, lang)
        return 'lex: survey + scan + the loop', 'lexparts'

    def bench_functions_of_lexed_rows(self, timer):
        mod, lines, lang, rows = self.mod, self.lines, self.lang, self.rows
        with timer as test:
            while test.more:
                for _ in test.count:
                    mod.functions(lines, lang, rows)
        return 'functions, given the lexed rows', 'lexparts'

    def bench_facts_of_lexed_rows(self, timer):
        mod, lines, rows = self.mod, self.lines, self.rows
        with timer as test:
            while test.more:
                for _ in test.count:
                    mod.build_facts(lines, rows)
        return 'build_facts, given the lexed rows', 'lexparts'
