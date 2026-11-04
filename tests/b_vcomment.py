r"""b_vcomment.py -- tests and benchmarks for vcomment, the launcher: which project a path or -repo
means, the command words, the page it writes. The report server is never touched (server=False).

Run from the project root:
    python tools/runbench.py b_vcomment
"""
import atexit
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile


def findtools():                      # walk up to the folder that holds tools/
    from os.path import abspath, dirname, isdir, join
    here = dirname(abspath(__file__))
    while here != dirname(here) and not isdir(join(here, 'tools')):
        here = dirname(here)
    sys.path.insert(0, join(here, 'tools'))
    sys.path.insert(0, join(here, 'tools', 'primary'))
    return here


ROOT = findtools()
from bench import bench

SOURCES = ['vcomment']
import reportserver
import vcomment


def said(fn, *args, **kwargs):
    """(result, what it printed) of a call; a SystemExit is returned as the result."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        try:
            got = fn(*args, **kwargs)
        except SystemExit as stop:
            got = stop
    return got, out.getvalue()


class b_vcomment(bench):
    BenchName = 'vcomment'
    BenchVersion = 'M1.0.7'          # runbench adds 1 to the last number on every run
    BenchHeader = 'the launcher: the project, the command words, the page'
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        cls.tmp = os.path.realpath(tempfile.mkdtemp(prefix='vcl_'))
        atexit.register(shutil.rmtree, cls.tmp, True)
        cls.top = os.path.join(cls.tmp, 'claude')              # holds .claude: the Claude root
        cls.proj = os.path.join(cls.top, 'proj')
        cls.plain = os.path.join(cls.top, 'plain')
        cls.results = os.path.join(cls.tmp, 'results')
        os.makedirs(os.path.join(cls.top, '.claude'))
        subprocess.run(['git', 'init', '-q', cls.proj], check=True)
        for rel, text in (('proj/a.py', 'x = 1\n'), ('proj/sub/deep/same.py', 'x = 2\n'),
                          ('proj/same.py', 'x = 3\n'), ('proj/notes.md', '# n\n'),
                          ('plain/sub/b.m', 'x = 1;\n')):
            path = os.path.join(cls.top, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)

    def make(self, **kwargs):
        """vcomment() with the fixture's Claude root and results, and no report server."""
        kwargs.setdefault('claude_root', self.top)
        kwargs.setdefault('results', self.results)
        kwargs['server'] = False
        return said(vcomment.vcomment, **kwargs)

    def page_of(self, path):
        with open(path, encoding='utf-8') as f:
            return f.read()

    # ---- the project ------------------------------------------------------------------------
    def test_T1_a_path_in_a_repository_means_that_repository(self):
        for path in (self.proj, os.path.join(self.proj, 'sub', 'deep'),
                     os.path.join(self.proj, 'sub', 'deep', 'same.py')):
            self.assertEqual(vcomment.choose_root(path, '', self.top), (self.proj, ''))

    def test_T2_a_path_with_no_repository_means_the_top_folder_under_the_claude_root(self):
        got = vcomment.choose_root(os.path.join(self.plain, 'sub', 'b.m'), '', self.top)
        self.assertEqual(got, (self.plain, ''))

    def test_T3_repo_names_a_folder_of_the_claude_root(self):
        self.assertEqual(vcomment.choose_root('', 'plain', self.top), (self.plain, ''))
        self.assertEqual(vcomment.choose_root('ignored', 'proj', self.top), (self.proj, ''))

    def test_T4_repo_must_be_a_plain_name_of_an_existing_folder(self):
        for name in ('..', '.', 'a/b', 'a\\b', 'nothere', 'C:'):
            root, why = vcomment.choose_root('', name, self.top)
            self.assertIsNone(root, name)
            self.assertIn('-repo', why)

    def test_T5_the_drive_root_is_no_project(self):
        drive = os.path.splitdrive(self.tmp)[0] + os.sep
        root, why = vcomment.choose_root(drive, '', self.top)
        self.assertIsNone(root)
        self.assertIn('outside', why)

    # ---- the words --------------------------------------------------------------------------
    def test_T6_words_take_every_option(self):
        got = vcomment.words(['some/path', '-title', 'why it is open', '-repo', 'mumix',
                              '-files', 'a.py', 'b/c.m', '-open', '-nostart'])
        self.assertEqual(got, {'path': 'some/path', 'title': 'why it is open', 'repo': 'mumix',
                               'files': ['a.py', 'b/c.m'], 'open_page': True, 'start': False})

    def test_T7_files_end_at_the_next_option_and_may_come_before_the_path(self):
        self.assertEqual(vcomment.words(['-files', 'a.py', 'b.py', '-open', 'where']),
                         {'files': ['a.py', 'b.py'], 'open_page': True, 'path': 'where'})
        self.assertEqual(vcomment.words([]), {})

    def test_T8_a_word_it_does_not_know_prints_the_use_and_exits_with_2(self):
        for words in (['-nonsense'], ['-title'], ['-repo'], ['one', 'two']):
            got, out = said(vcomment.words, words)
            self.assertIsInstance(got, SystemExit, words)
            self.assertEqual(got.code, 2)
            self.assertIn('Use:', out)

    # ---- the page name ----------------------------------------------------------------------
    def test_T9_page_names_are_the_series_name_and_the_minute_then_seconds_then_letters(self):
        folder = os.path.join(self.tmp, 'names')
        os.makedirs(folder)
        seen = []
        for _ in range(4):
            name = vcomment.page_name(folder, 'review-x', 1762000000.0)
            seen.append(name)
            open(os.path.join(folder, name), 'w').close()
        self.assertEqual(len(set(seen)), 4)
        rx = re.compile(r'^review-x_\d{4}\.\d\d\.\d\d_\d\d;\d\d(\.\d\d[a-z]{0,2})?\.html$')
        self.assertTrue(all(rx.match(n) for n in seen), seen)
        self.assertTrue(seen[1].endswith('.html') and '.' in seen[1].split('_')[-1][:-5])

    def test_T10_the_report_server_reads_the_name_of_a_page(self):
        name = vcomment.page_name(self.tmp, 'review-proj', 1762000000.0)
        self.assertTrue(reportserver.NAME.match(name), name)

    # ---- the page ---------------------------------------------------------------------------
    def test_T11_a_page_is_made_in_results_for_the_project(self):
        out, said_ = self.make(path=self.proj)
        self.assertTrue(os.path.isfile(out))
        self.assertEqual(os.path.dirname(out), self.results)
        self.assertIn('project: ' + self.proj, said_)
        self.assertIn('page: ' + out, said_)
        page = self.page_of(out)
        self.assertTrue(page.startswith('<!DOCTYPE html>'))
        self.assertIn('<title>vcomment: proj</title>', page)

    def test_T12_the_page_carries_the_tree_the_tabs_and_the_scripts(self):
        page = self.page_of(self.make(path=self.proj)[0])
        for needle in ('id="vctree"', 'id="vcfiles"', 'id="tabStrip"', 'function buildTabs',
                       'function vcLoadTree', '.vcwrap{', '.r-keyword{'):
            self.assertIn(needle, page, needle)

    def test_T13_no_place_of_the_template_is_left_unfilled(self):
        page = self.page_of(self.make(path=self.proj)[0])
        for place in ('TITLE', 'STEM', 'RUNS', 'NAME', 'TOKEN', 'PORT', 'BAT', 'VC', 'css', 'js',
                      'rolecss', 'vccss', 'vcjs', '_\\main/_'):
            self.assertNotIn('{{' + place + '}}', page, place)

    def test_T14_the_token_names_the_page_file(self):
        out = self.make(path=self.proj)[0]
        page = self.page_of(out)
        token = json.loads(re.search(r'TOKEN = (".*?")', page).group(1))
        self.assertEqual(reportserver.unpack(token)[0], os.path.basename(out))
        self.assertIn('SELF = ' + json.dumps(os.path.basename(out)), page)

    def test_T15_without_the_report_server_the_page_has_no_port(self):
        page = self.page_of(self.make(path=self.proj)[0])
        self.assertIn('PORT = 0,', page)
        self.assertIn('BAT = ""', page)

    def test_T16_title_goes_in_the_heading_the_window_title_and_the_start_tab(self):
        out = self.make(path=self.proj, title='why: the <b>review</b> & more')[0]
        page = self.page_of(out)
        self.assertIn('<title>vcomment: proj - why: the &lt;b&gt;review&lt;/b&gt; &amp; more</title>', page)
        self.assertIn('<h1>vcomment: proj - why: the &lt;b&gt;review&lt;/b&gt;', page)
        self.assertNotIn('<b>review</b>', page.split('<script>')[0])
        self.assertIn('"title": "vcomment: proj - why: the <b>review<\\/b> & more"', page)

    def test_T17_files_are_found_nearest_the_root_and_listed_for_opening(self):
        out, said_ = self.make(path=self.proj, files=['same.py', 'a.py', 'notes.md', 'gone.py'])
        vc = json.loads(re.search(r'var VC = (\{.*?\});', self.page_of(out)).group(1))
        self.assertEqual(vc['open'], ['same.py', 'a.py', 'notes.md'])    # same.py: not sub/deep/
        self.assertEqual(vc['root'], self.proj)
        self.assertIn('not found under ' + self.proj + ': gone.py', said_)

    def test_T18_the_start_tab_names_the_files_found_and_not_found(self):
        page = self.page_of(self.make(path=self.proj, files=['a.py', 'gone.py'])[0])
        start = page.split('data-name="Start"')[1].split('<!--SHELL:END-->')[0]
        self.assertIn('Opened at the start', start)
        self.assertIn('Not found', start)
        self.assertIn(self.proj, start)

    def test_T19_every_run_is_a_new_page(self):
        first = self.make(path=self.proj)[0]
        second = self.make(path=self.proj)[0]
        self.assertNotEqual(first, second)
        self.assertTrue(os.path.isfile(first) and os.path.isfile(second))

    def test_T20_repo_and_a_path_outside_the_reach_are_refused_with_2(self):
        got, out = self.make(repo='nothere')
        self.assertIsInstance(got, SystemExit)
        self.assertEqual(got.code, 2)
        self.assertIn('-repo', out)
        drive = os.path.splitdrive(self.tmp)[0] + os.sep
        got, out = self.make(path=drive)
        self.assertEqual(got.code, 2)

    def test_T21_the_project_of_repo_is_a_folder_of_the_claude_root(self):
        out = self.make(repo='plain')[0]
        self.assertIn('<title>vcomment: plain</title>', self.page_of(out))

    def test_T22_nothing_is_written_outside_results(self):
        before = sorted(os.listdir(self.proj))
        self.make(path=self.proj, files=['a.py'])
        self.assertEqual(sorted(os.listdir(self.proj)), before)

    def bench_make_a_page(self, timer):
        with timer as test:
            while test.more:
                for _ in test.count:
                    out = io.StringIO()
                    with contextlib.redirect_stdout(out):
                        os.remove(vcomment.vcomment(path=self.proj, claude_root=self.top,
                                                    results=self.results, server=False))
        return 'make a page (no server)', 'page'
