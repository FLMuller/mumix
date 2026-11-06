r"""b_spaghettichk.py -- tests and benchmarks for the command line of spaghettichk and for the limit on the area
it looks at.

The area. A check never works on the whole Claude area: a path must lie below the folder that holds .claude,
and the widest area is the folder one below it (mumix). The scan of the tree around a module, which finds the
modules that use it, starts no higher than that folder. The verbs (scope, files, why, rows, rule, tally) are
run through main() with the console captured, on two small files this suite writes into tests/z_sandbox.

Run from the project root:
    python tools/runbench.py b_spaghettichk
"""
import atexit
import contextlib
import io
import os
import shutil
import sys
import tempfile


def findtools():                      # walk up to the folder that holds tools/
    from os.path import abspath, dirname, isdir, join
    here = dirname(abspath(__file__))
    while here != dirname(here) and not isdir(join(here, 'tools')):
        here = dirname(here)
    sys.path.insert(0, join(here, 'tools'))
    return here


ROOT = findtools()
from bench import bench
from use import load

SOURCES = ['spaghettichk']
load(asmodule=['spaghettichk'])

CLAUDE = os.path.dirname(ROOT)                    # the folder that holds .claude
SAMPLE = os.path.join(ROOT, 'tests', 'z_sandbox', 'spagettitmp')
ALPHA = ('"""alpha.py -- a sample.\n\n    one(x)    gives x\n    two(x)    gives x + 1\n"""\n\n'
         "__all__ = ['one', 'two']\n\n\ndef one(x): return x\n\n\ndef two(x):\n    return x + 1\n")
BETA = ('"""beta.py -- uses alpha."""\nimport alpha\n\n__all__ = [\'three\']\n\n\n'
        'def three(x):\n    return alpha.two(x)\n')
BANDS = ('green', 'grey', 'orange', 'red')


def run(*words):
    """The console text of main(words)."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        spaghettichk.main(list(words))
    return out.getvalue()


def keyed(text):
    """{first word: the rest} of the lines of a scope listing."""
    return dict(line.split(None, 1) for line in text.splitlines() if len(line.split(None, 1)) == 2)


def same(path, other):
    return os.path.normcase(os.path.abspath(path)) == os.path.normcase(os.path.abspath(other))


class b_spaghettichk(bench):
    BenchName = 'spaghettichk'
    BenchVersion = 'M1.0.4'          # runbench adds 1 to the last number on every run
    BenchHeader = 'the command line of spaghettichk and the limit on the area it looks at'
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        os.makedirs(SAMPLE, exist_ok=True)
        atexit.register(shutil.rmtree, SAMPLE, True)
        for name, text in (('alpha.py', ALPHA), ('beta.py', BETA)):
            with open(os.path.join(SAMPLE, name), 'w', encoding='utf-8', newline='') as f:
                f.write(text)

    # ---- the limit on the area -----------------------------------------------------------------------
    def test_T1_scope_names_the_project_and_the_tree_scan_starts_no_higher_than_it(self):
        got = keyed(run('scope', os.path.join(ROOT, 'odeproblem')))
        self.assertTrue(same(got['project'].split('   ')[0].strip(), ROOT), got['project'])
        self.assertTrue(same(got['scan'].split('   ')[0].strip(), ROOT), got['scan'])      # two up is the Claude folder
        inside = keyed(run('scope', os.path.join(ROOT, 'tools', 'rs_primary', 'panes')))
        self.assertTrue(same(inside['scan'].split('   ')[0].strip(), os.path.join(ROOT, 'tools')), inside['scan'])   # kept

    def test_T2_a_path_outside_a_project_is_refused_before_anything_is_read(self):
        for path in (CLAUDE, os.path.join(CLAUDE, '.claude'), tempfile.gettempdir(), os.path.join(ROOT, 'nonesuch')):
            for verb in ('scope', 'files'):
                with self.assertRaises(SystemExit) as caught:
                    run(verb, path)
                self.assertIn('spaghettichk:', str(caught.exception.code), (verb, path))

    def test_T3_the_tree_scan_of_a_check_never_walks_above_the_project(self):
        walked = []
        real = os.walk

        def record(top, *args, **keywords):
            walked.append(os.path.normcase(os.path.abspath(top)))
            return real(top, *args, **keywords)
        os.walk = record
        self.addCleanup(setattr, os, 'walk', real)
        run('files', os.path.join(ROOT, 'odeproblem'))
        top = os.path.normcase(ROOT)
        self.assertTrue(walked)
        self.assertEqual([w for w in walked if not (w == top or w.startswith(top + os.sep))], [])

    # ---- the verbs ---------------------------------------------------------------------------------
    def test_T4_files_gives_a_line_for_each_file_and_only_keeps_one_colour(self):
        lines = run('files', SAMPLE).splitlines()
        self.assertEqual([line.split()[0] for line in lines], ['alpha.py', 'beta.py'])
        self.assertTrue(all(line.split()[1] in BANDS for line in lines), lines)
        for band in {line.split()[1] for line in lines}:
            kept = run('files', SAMPLE, '--only', band).splitlines()
            self.assertEqual([line.split()[:2] for line in kept], [line.split()[:2] for line in lines if line.split()[1] == band])

    def test_T5_why_lists_the_reasons_of_a_file_and_a_one_line_def_is_one_line_long(self):
        text = run('why', os.path.join(SAMPLE, 'alpha.py'))
        self.assertTrue(text.startswith('alpha.py'), text)
        for rule in ('importers', 'cycles', 'header', 'length'):
            self.assertIn(rule + ':', text)
        self.assertIn('the median function is 1.5 lines (of 2)', text)         # one() is 1 line, two() is 2

    def test_T6_rows_lists_the_functions_and_a_rule_keeps_the_rows_where_it_is_not_green(self):
        path = os.path.join(SAMPLE, 'alpha.py')
        names = [line.split()[2] for line in run('rows', path).splitlines() if len(line.split()) > 2]
        self.assertIn('one', names)
        self.assertIn('two', names)
        text = run('rows', path, '--rule', 'docs')
        self.assertEqual(sum('docs: red' in line for line in text.splitlines()), 2)
        self.assertNotIn('tangle', text)

    def test_T7_rule_lists_every_place_a_rule_is_not_green_and_only_picks_a_verdict(self):
        lines = run('rule', SAMPLE, 'docs').splitlines()
        places = [line.split()[0] for line in lines]
        self.assertEqual(places, ['alpha.py:10', 'alpha.py:13', 'beta.py:7'])
        self.assertEqual(run('rule', SAMPLE, 'docs', '--only', 'green'), '')

    def test_T8_tally_counts_the_verdicts_of_each_rule_for_the_file_and_for_its_rows(self):
        text = run('tally', SAMPLE)
        self.assertIn('file rules', text)
        self.assertIn('row rules', text)
        docs = [line.split() for line in text.splitlines() if line.split()[:1] == ['docs']]
        self.assertEqual(docs, [['docs', '0', '0', '0', '3']])                  # green grey orange red

    def test_T9_a_verb_that_does_not_exist_is_refused(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            run('nonsense', SAMPLE)
        self.assertEqual(caught.exception.code, 2)

    def bench_files_of_two_small_files(self, timer):
        with timer as test:
            while test.more:
                for _ in test.count:
                    run('files', SAMPLE)
        return 'files verb on 2 files', 'verbs'
