r"""b_vcserver.py -- tests and benchmarks for vcserver (the live verbs of vcomment), vcode (a file as
a tab) and the extension hook of reportserver that carries them.

Everything is done on a repository made in a temporary folder, with a .claude folder above it
(the reach). The handler is called as the report server calls it; reportserver.reply_for is
called for the end to end tests, with a roots file and a handlers file of its own.

Run from the project root:
    python tools/runbench.py b_vcserver
"""
import atexit
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time


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

SOURCES = ['vcserver', 'vcode', 'reportserver']
import reportserver
import vcode
import vcserver

PY = ('"""doc"""\ndef f(x):\n    return x + 1\n\n\ns = """\ninside string\n"""\n')
M = "x = 1;\n%{\nblock\n%}\ny = x';\n"
JS = 'function f() {\n  return 1;\n}\n/* block\n   text */\nvar t = `a\nb`;\n'
CSS = '.a {\n  color: red;\n}\n/* block\n   more */\n'
MD = '# Title\n\ntext\n'
TXT = 'plain\ntext\n'
FILES = {'a.py': PY, 'b.m': M, 'c.js': JS, 'd.css': CSS, 'e.md': MD, 'f.txt': TXT,
         'crlf.py': 'def g():\r\n    return 1\r\n'}
# where a comment goes and what it looks like in each language
WHERE = {'a.py': (3, '    ###flm hello'), 'b.m': (5, '%%%flm hello'), 'c.js': (2, '  ///flm hello'),
         'd.css': (2, '  /***flm hello */'), 'e.md': (3, '<!--###flm hello -->'),
         'f.txt': (2, '###flm hello')}


def sha(path):
    with open(path, 'rb') as f:
        return hashlib.sha1(f.read()).hexdigest()


def text_of(path):
    with open(path, 'rb') as f:
        return f.read().decode('utf-8')


class b_vcserver(bench):
    BenchName = 'vcserver'
    BenchVersion = 'M1.0.10'          # runbench adds 1 to the last number on every run
    BenchHeader = 'live verbs of vcomment: reach, tree, open, comment-only edits, the hook'
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        cls.tmp = os.path.realpath(tempfile.mkdtemp(prefix='vc_'))
        atexit.register(shutil.rmtree, cls.tmp, True)
        cls.top = os.path.join(cls.tmp, 'claude')              # the reach: holds .claude
        cls.proj = os.path.join(cls.top, 'proj')               # a repository
        cls.plain = os.path.join(cls.top, 'plain', 'sub')      # no .git anywhere
        for folder in (os.path.join(cls.top, '.claude'), cls.proj, cls.plain):
            os.makedirs(folder)
        subprocess.run(['git', '-C', cls.proj, 'init', '-q'], check=True)
        cls.write('proj/.gitignore', 'ignored.txt\n')
        for name, text in FILES.items():
            cls.write('proj/' + name, text)
        for name in ('sub/deep/g.m', '__pycache__/x.pyc', 'venv/lib.py', '.hidden/h.py',
                     'sub2/.claude/rules.md', 'ignored.txt', 'data.xlsx', 'page.html', 'thing.tmp'):
            cls.write('proj/' + name, 'x\n')
        cls.write('plain/sub/x.py', 'x = 1\n')
        cls.server = os.path.join(cls.tmp, 'rs')                # the report server's folder
        cls.results = os.path.join(cls.tmp, 'results')
        os.makedirs(cls.server)
        os.makedirs(cls.results)
        cls.page = 'review-proj_' + time.strftime('%Y.%m.%d_%H;%M') + '.html'
        cls.report = 'suite_' + time.strftime('%Y.%m.%d_%H;%M') + '.html'
        for name in (cls.page, cls.report):
            cls.write('results/' + name, '<html></html>')
        cls.S = {'roots_file': os.path.join(cls.server, 'reportserver.roots')}
        vcserver.register(cls.page, cls.proj, cls.server)

    @classmethod
    def write(cls, rel, text):
        path = os.path.join(cls.tmp if rel.split('/')[0] in ('results', 'rs') else cls.top, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(text.encode('utf-8'))
        return path

    def setUp(self):
        self.logs = []
        for extra in ('m.py', 'tests', 'test', 'n1', 'n2', 'n3', 'huge.py', 'link.py'):
            path = os.path.join(self.proj, extra)                 # what an earlier test left
            if os.path.isdir(path):
                shutil.rmtree(path)
            elif os.path.lexists(path):
                os.remove(path)
        for name, text in FILES.items():                       # every test starts from the same files
            self.write('proj/' + name, text)

    def ask(self, **msg):
        """The handler's reply to a message of the registered page: parsed, or None / '[]'."""
        got = vcserver.handler(self.S, msg, self.results, self.page, self.logs.append)
        return json.loads(got) if got not in (None, '[]') else got

    def edit(self, name, **msg):
        path = os.path.join(self.proj, name)
        msg.setdefault('filename', path)
        msg.setdefault('base', sha(path))
        msg.setdefault('tag', 'flm')
        return self.ask(**msg)

    # ---- reach ------------------------------------------------------------------------------
    def test_T1_reach_is_the_first_folder_with_claude(self):
        self.assertEqual(vcserver.reach_limit(os.path.join(self.proj, 'sub')), self.top)
        self.assertEqual(vcserver.reach_limit(os.path.join(self.proj, 'a.py')), self.top)

    def test_T2_reach_is_one_name_below_the_drive_when_nothing_has_claude(self):
        drive = os.path.splitdrive(self.tmp)[0] + os.sep
        got = vcserver.reach_limit(os.path.join(drive, 'Windows', 'System32', 'x.dll'))
        self.assertEqual(got.lower(), os.path.join(drive, 'Windows').lower())

    def test_T3_find_root_is_the_repository_else_the_top_folder_under_the_reach(self):
        self.assertEqual(vcserver.find_root(os.path.join(self.proj, 'sub', 'deep')), self.proj)
        self.assertEqual(vcserver.find_root(os.path.join(self.proj, 'a.py')), self.proj)
        self.assertEqual(vcserver.find_root(self.plain), os.path.join(self.top, 'plain'))
        self.assertEqual(vcserver.find_root(self.top), self.top)

    def test_T4_find_root_never_reads_the_drive_root(self):
        drive = os.path.splitdrive(self.tmp)[0] + os.sep
        self.assertIsNone(vcserver.find_root(drive))
        self.assertIsNone(vcserver.find_root(drive + '..'))

    # ---- find_files -------------------------------------------------------------------------
    def test_T5_find_files_nearest_to_the_root_then_newest(self):
        for rel, age in (('n1/x.py', 100), ('n2/x.py', 0), ('n3/n4/x.py', -100)):
            path = self.write('proj/' + rel, 'x = 1\n')
            os.utime(path, (time.time() - age, time.time() - age))
        got = dict(vcserver.find_files(self.proj, ['x.py', 'n4/x.py', 'missing.py', 'F.TXT']))
        self.assertEqual(got['x.py'], 'n2/x.py')                # depth 1, and newer than n1
        self.assertEqual(got['n4/x.py'], 'n3/n4/x.py')          # the end of a path
        self.assertIsNone(got['missing.py'])
        self.assertEqual(got['F.TXT'], 'f.txt')                 # case does not matter
        shutil.rmtree(os.path.join(self.proj, 'n1'))
        shutil.rmtree(os.path.join(self.proj, 'n2'))
        shutil.rmtree(os.path.join(self.proj, 'n3'))

    # ---- the tree ---------------------------------------------------------------------------
    def test_T6_tree_shows_files_and_hides_junk(self):
        got = self.ask(tree=True)
        shown = {x['p']: x['k'] for x in got['files']}
        want = {'.gitignore': 'other', 'a.py': 'code', 'b.m': 'code', 'c.js': 'code',
                'crlf.py': 'code', 'd.css': 'code', 'e.md': 'md', 'f.txt': 'text',
                'data.xlsx': 'other', 'page.html': 'html', 'sub/deep/g.m': 'code',
                'sub2/.claude/rules.md': 'md'}
        self.assertEqual(shown, want)
        self.assertEqual(got['root'], self.proj)
        self.assertEqual(got['name'], 'proj')
        self.assertTrue(got['base'].startswith('file:///'))

    def test_T7_tree_sizes_are_the_bytes(self):
        sizes = {x['p']: x['s'] for x in self.ask(tree=True)['files']}
        self.assertEqual(sizes['f.txt'], len(TXT))

    def test_T8_a_file_too_large_to_open_is_listed_as_big(self):
        path = self.write('proj/huge.py', 'x' * (vcserver.MAX_BYTES + 1))
        shown = {x['p']: x['k'] for x in self.ask(tree=True)['files']}
        os.remove(path)
        self.assertEqual(shown['huge.py'], 'big')

    # ---- who is answered --------------------------------------------------------------------
    def test_T9_a_page_that_is_not_registered_is_left_to_the_report_server(self):
        got = vcserver.handler(self.S, {'tree': True}, self.results, self.report, self.logs.append)
        self.assertIsNone(got)

    def test_T10_a_report_verb_of_a_registered_page_is_left_to_the_report_server(self):
        for msg in ({}, {'config': True}, {'filename': 'x'}):
            self.assertIsNone(vcserver.handler(self.S, msg, self.results, self.page, self.logs.append))

    # ---- reachable --------------------------------------------------------------------------
    def test_T11_open_refuses_what_is_not_inside_or_not_shown_or_not_opened(self):
        outside = self.write('plain/sub/x.py', 'x = 1\n')
        bad = ['../plain/sub/x.py', outside, 'nothing.py', 'data.xlsx', 'page.html',
               '__pycache__/x.pyc', 'venv/lib.py', '.hidden/h.py', 'sub']
        for name in bad:
            self.assertEqual(self.ask(open=name), '[]', name)
        self.assertEqual(self.logs[0][:8], 'refused:')

    def test_T12_no_dotdot_even_when_it_comes_back_inside(self):
        self.assertEqual(self.ask(open='sub/../a.py'), '[]')
        self.assertEqual(self.ask(check=True, filename=os.path.join(self.proj, 'sub', '..', 'a.py')), '[]')

    def test_T13_a_link_out_of_the_repository_is_not_followed(self):
        link = os.path.join(self.proj, 'link.py')
        try:
            os.symlink(os.path.join(self.top, 'plain', 'sub', 'x.py'), link)
        except OSError:
            return                                               # no right to make links here
        try:
            self.assertEqual(self.ask(open='link.py'), '[]')
        finally:
            os.remove(link)

    # ---- open -------------------------------------------------------------------------------
    def test_T14_open_gives_the_tab_of_each_kind_of_file(self):
        for name in ('a.py', 'b.m', 'c.js', 'd.css', 'e.md', 'f.txt', 'sub/deep/g.m', 'sub2/.claude/rules.md'):
            got = self.ask(open=name, label='L')
            self.assertTrue(got['ok'], name)
            html = got['html']
            self.assertIn('data-name="L"', html, name)
            self.assertIn(f'data-rel="{name}"', html, name)
            self.assertIn('class="codepane"', html, name)
            self.assertIn('class="clines" data-base="', html, name)

    def test_T15_a_markdown_tab_has_a_rendered_view_and_the_source(self):
        html = self.ask(open='e.md')['html']
        self.assertIn('data-name="Rendered"', html)
        self.assertIn('data-name="Source"', html)
        self.assertIn('<h1', html)
        self.assertEqual(html.count('class="codepane"'), 1)

    def test_T16_the_path_shown_is_relative_to_the_repository(self):
        for name in ('a.py', 'b.m', 'sub/deep/g.m'):
            html = self.ask(open=name)['html']
            self.assertIn(f'>{name}</span><button class="cprev"', html)

    def test_T17_a_python_file_gets_its_function_list_and_others_theirs(self):
        self.assertIn('data-line="2">f</a>', self.ask(open='a.py')['html'])
        self.assertIn('data-line="1">f</a>', self.ask(open='c.js')['html'])
        self.assertIn('no functions', self.ask(open='f.txt')['html'])

    def test_T18_existing_comments_show_as_threads_not_as_code(self):
        self.write('proj/c.js', JS.replace('  return 1;', '  ///flm look\n  ///flm here\n  ///cld ok\n  return 1;'))
        html = self.ask(open='c.js')['html']
        self.assertEqual(html.count('class="cm"'), 2)            # two runs: flm (two lines) and cld
        self.assertIn('data-first="2" data-last="3"', html)
        self.assertIn('data-who="claude"', html)
        self.assertNotIn('///flm', html)

    def test_T19_label_is_the_file_name_by_default(self):
        self.assertIn('data-name="a.py"', self.ask(open='a.py')['html'])

    # ---- check ------------------------------------------------------------------------------
    def test_T20_check_agrees_for_every_language_and_refuses_the_rest(self):
        for name in ('a.py', 'b.m', 'c.js', 'd.css', 'e.md', 'f.txt'):
            self.assertEqual(self.ask(check=True, filename=os.path.join(self.proj, name)), {'ok': True})
        self.assertEqual(self.ask(check=True, filename=os.path.join(self.proj, 'data.xlsx')), '[]')
        self.assertEqual(self.ask(check=True, filename=5), '[]')

    # ---- edit -------------------------------------------------------------------------------
    def test_T21_a_comment_is_written_with_the_marker_of_the_language(self):
        for name, (line, expect) in WHERE.items():
            path = os.path.join(self.proj, name)
            old = text_of(path).split('\n')
            got = self.edit(name, insert=True, line=line, text='hello')
            self.assertTrue(got['ok'], name)
            self.assertEqual(text_of(path).split('\n'), old[:line - 1] + [expect] + old[line - 1:], name)
            self.assertEqual((got['first'], got['last'], got['delta'], got['removed']), (line, line, 1, False))
            self.assertEqual(got['base'], sha(path))

    def test_T22_the_marker_comes_from_the_file_not_from_the_page(self):
        got = self.edit('b.m', insert=True, line=1, text='x', triplet='###', opener='###', marker='///')
        self.assertTrue(got['ok'])
        self.assertTrue(text_of(os.path.join(self.proj, 'b.m')).startswith('%%%flm x\n'))

    def test_T23_removing_a_comment_gives_back_the_same_bytes(self):
        for name, (line, expect) in WHERE.items():
            path = os.path.join(self.proj, name)
            before = open(path, 'rb').read()
            self.edit(name, insert=True, line=line, text='hello')
            got = self.edit(name, update=True, first=line, last=line, text='')
            self.assertTrue(got['removed'], name)
            self.assertEqual(open(path, 'rb').read(), before, name)

    def test_T24_a_comment_of_several_lines_and_a_change_of_its_text(self):
        path = os.path.join(self.proj, 'c.js')
        got = self.edit('c.js', insert=True, line=2, text='one\n\nthree')
        self.assertEqual((got['first'], got['last'], got['delta']), (2, 4, 3))
        self.assertEqual(text_of(path).split('\n')[1:4], ['  ///flm one', '  ///flm ', '  ///flm three'])
        got = self.edit('c.js', update=True, first=2, last=4, text='short')
        self.assertEqual((got['first'], got['last'], got['delta']), (2, 2, -2))
        self.assertEqual(text_of(path).split('\n')[1:3], ['  ///flm short', '  return 1;'])

    def test_T25_the_reply_carries_the_comment_as_html(self):
        got = self.edit('e.md', insert=True, line=3, text='**bold** thought')
        self.assertIn('<strong>bold</strong>', got['html'])

    def test_T26_a_file_that_was_opened_shows_the_comment_after_it(self):
        self.edit('b.m', insert=True, line=5, text='why transpose?')
        html = self.ask(open='b.m')['html']
        self.assertIn('data-first="5" data-last="5"', html)
        self.assertIn('data-initials="flm"', html)
        self.assertIn('why transpose?', html)

    def test_T27_the_line_ends_of_the_file_are_kept(self):
        path = os.path.join(self.proj, 'crlf.py')
        self.edit('crlf.py', insert=True, line=2, text='a\nb')
        self.assertEqual(open(path, 'rb').read(),
                         b'def g():\r\n    ###flm a\r\n    ###flm b\r\n    return 1\r\n')

    def test_T28_an_edit_made_since_the_file_was_read_is_refused(self):
        stale = sha(os.path.join(self.proj, 'a.py'))
        self.write('proj/a.py', PY + '# changed\n')
        before = text_of(os.path.join(self.proj, 'a.py'))
        self.assertEqual(self.edit('a.py', insert=True, line=3, text='x', base=stale), '[]')
        self.assertEqual(text_of(os.path.join(self.proj, 'a.py')), before)

    def test_T29_a_file_newer_than_the_page_is_no_reason_to_refuse(self):
        # the report verbs refuse this ('these results are outdated'): a vcomment page holds no copy
        path = os.path.join(self.proj, 'b.m')
        os.utime(path, (time.time() + 60, time.time() + 60))
        self.assertTrue(self.edit('b.m', insert=True, line=1, text='x')['ok'])

    def test_T30_a_comment_inside_a_python_string_is_refused(self):
        before = text_of(os.path.join(self.proj, 'a.py'))
        self.assertEqual(self.edit('a.py', insert=True, line=7, text='x'), '[]')
        self.assertEqual(text_of(os.path.join(self.proj, 'a.py')), before)
        self.assertIn('more than comments', self.logs[-1])

    def test_T31_a_comment_inside_a_block_comment_or_a_template_is_refused(self):
        cases = [('c.js', 5), ('c.js', 7), ('d.css', 5), ('b.m', 3)]
        for name, line in cases:
            before = text_of(os.path.join(self.proj, name))
            self.assertEqual(self.edit(name, insert=True, line=line, text='x'), '[]', (name, line))
            self.assertEqual(text_of(os.path.join(self.proj, name)), before)
            self.assertIn('inside a block', self.logs[-1])
        self.assertTrue(self.edit('c.js', insert=True, line=4, text='fine')['ok'])    # before /* */
        self.assertTrue(self.edit('b.m', insert=True, line=6, text='at the end')['ok'])

    def test_T32_text_that_would_end_the_comment_is_refused(self):
        self.assertEqual(self.edit('d.css', insert=True, line=2, text='breaks */ out'), '[]')
        self.assertEqual(self.edit('e.md', insert=True, line=3, text='breaks --> out'), '[]')
        self.assertTrue(self.edit('a.py', insert=True, line=3, text='*/ and --> are fine here')['ok'])

    def test_T33_bad_requests_are_refused(self):
        path = os.path.join(self.proj, 'a.py')
        before = text_of(path)
        bad = [dict(insert=True, line=99, text='x'), dict(insert=True, line=0, text='x'),
               dict(insert=True, line='x', text='x'), dict(update=True, first=1, last=2, text='x'),
               dict(update=True, first=3, last=2, text='x'), dict(insert=True, line=3, text='x', tag='toolongtag1'),
               dict(insert=True, line=3, text='x', tag='a b'), dict(insert=True, line=3, text='x\x00y'),
               dict(insert=True, line=3, text='x' * 30001), dict(insert=True, line=3, text=5), dict(insert=True, line=3, text='x', base=5),
               dict(insert=True, line=3, text='x', filename=os.path.join(self.plain, 'x.py'))]
        for msg in bad:
            self.assertEqual(self.edit('a.py', **msg), '[]', msg)
        self.assertEqual(text_of(path), before)

    def test_T34_an_update_must_cover_comment_lines_only(self):
        self.edit('f.txt', insert=True, line=1, text='note')
        path = os.path.join(self.proj, 'f.txt')
        before = text_of(path)
        self.assertEqual(self.edit('f.txt', update=True, first=1, last=2, text='x'), '[]')
        self.assertEqual(text_of(path), before)

    def test_T35_insert_at_the_end_of_the_file(self):
        path = os.path.join(self.proj, 'f.txt')
        self.assertTrue(self.edit('f.txt', insert=True, line=3, text='end')['ok'])
        self.assertEqual(text_of(path), 'plain\ntext\n###flm end\n')

    # ---- the report server's hook -----------------------------------------------------------
    def serverstate(self, handlers):
        """The report server's state dict for a run of reply_for, with a handlers file."""
        S = {'port': 0, 'roots_file': self.S['roots_file'], 'roots_stamp': None, 'roots_list': [],
             'log': os.path.join(self.server, 'reportserver.log'),
             'config_file': os.path.join(self.server, 'reportserver.config')}
        with open(S['roots_file'], 'w', encoding='utf-8') as f:
            f.write(self.results + '\n')
        path = os.path.splitext(S['roots_file'])[0] + '.handlers'
        if handlers is None:
            if os.path.exists(path):
                os.remove(path)
        else:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(handlers)
        reportserver.HANDLERS.clear()
        return S

    def say(self, S, name, **msg):
        msg['hash'] = reportserver.token(name)
        return reportserver.reply_for(S, json.dumps(msg))

    def test_T36_through_the_report_server_a_page_gets_the_live_verbs(self):
        S = self.serverstate('vcserver\n')
        got = json.loads(self.say(S, self.page, tree=True))
        self.assertEqual(got['name'], 'proj')
        got = json.loads(self.say(S, self.page, open='b.m'))
        self.assertTrue(got['ok'])
        path = os.path.join(self.proj, 'b.m')
        got = json.loads(self.say(S, self.page, insert=True, line=1, text='hi', tag='flm',
                                  filename=path, base=sha(path)))
        self.assertTrue(got['ok'])
        self.assertTrue(text_of(path).startswith('%%%flm hi\n'))

    def test_T37_a_report_page_is_answered_as_before(self):
        S = self.serverstate('vcserver\n')
        path = os.path.join(self.proj, 'b.m')
        # the report verb refuses a .m file, and a tree is not a report verb: the series list
        self.assertEqual(self.say(S, self.report, check=True, filename=path), '[]')
        self.assertEqual(self.say(S, self.report, tree=True), '[]')
        self.assertEqual(self.say(S, self.page, config=True)[:1], '{')           # settings: shared
        self.assertEqual(json.loads(self.say(S, self.report, config=True))['size'], 12)

    def test_T38_the_list_question_of_the_page_goes_to_the_report_server(self):
        S = self.serverstate('vcserver\n')
        self.assertIsInstance(json.loads(self.say(S, self.page)), list)

    def test_T39_without_a_handlers_file_nothing_changes(self):
        S = self.serverstate(None)
        self.assertEqual(self.say(S, self.page, tree=True), '[]')
        self.assertEqual(reportserver.HANDLERS, [])

    def test_T40_a_handler_that_cannot_be_loaded_is_logged_and_left_out(self):
        S = self.serverstate('nosuchmodule\nvcserver\n')
        self.assertEqual(json.loads(self.say(S, self.page, tree=True))['name'], 'proj')
        self.assertIn('nosuchmodule failed to load', text_of(S['log']))

    def test_T41_a_handler_that_raises_is_logged_and_answered_with_nothing(self):
        S = self.serverstate('vcserver\n')
        self.say(S, self.page)                                 # loads the handlers
        reportserver.HANDLERS.insert(0, lambda *a: 1 / 0)
        self.assertEqual(self.say(S, self.page, tree=True), '[]')
        self.assertIn('handler failed', text_of(S['log']))

    def test_T42_the_handlers_file_is_read_again_when_it_changes(self):
        S = self.serverstate(None)
        self.assertEqual(self.say(S, self.page, tree=True), '[]')
        path = os.path.splitext(S['roots_file'])[0] + '.handlers'
        time.sleep(0.05)
        with open(path, 'w', encoding='utf-8') as f:
            f.write('vcserver\n')
        os.utime(path, (time.time() + 5, time.time() + 5))
        self.assertEqual(json.loads(self.say(S, self.page, tree=True))['name'], 'proj')

    # ---- register ---------------------------------------------------------------------------
    def test_T43_register_replaces_the_line_of_a_page_and_keeps_the_others(self):
        folder = os.path.join(self.tmp, 'reg')
        os.makedirs(folder)
        vcserver.register('one.html', self.proj, folder)
        vcserver.register('two.html', self.top, folder)
        vcserver.register('one.html', self.top, folder)
        S = {'roots_file': os.path.join(folder, 'reportserver.roots')}
        self.assertEqual(vcserver.lookup(S, 'one.html'), self.top)
        self.assertEqual(vcserver.lookup(S, 'two.html'), self.top)
        self.assertIsNone(vcserver.lookup(S, 'three.html'))

    def test_T44_a_page_whose_repository_is_gone_is_not_answered(self):
        folder = os.path.join(self.tmp, 'reg2')
        os.makedirs(folder)
        vcserver.register('gone.html', os.path.join(self.tmp, 'nowhere'), folder)
        self.assertIsNone(vcserver.lookup({'roots_file': os.path.join(folder, 'reportserver.roots')}, 'gone.html'))

    # ---- vcode ------------------------------------------------------------------------------
    def test_T45_vctab_refuses_what_it_does_not_open(self):
        for name in ('data.xlsx', 'page.html'):
            with self.assertRaises(ValueError):
                vcode.vctab(os.path.join(self.proj, name), self.proj)

    def test_T46_find_tests_looks_in_test_and_tests(self):
        self.write('proj/tests/b_a.py', 'x = 1\n')
        self.write('proj/test/b_c.py', 'x = 1\n')
        self.assertEqual(vcode.find_tests(self.proj, os.path.join(self.proj, 'a.py')),
                         [os.path.join(self.proj, 'tests', 'b_a.py')])
        self.assertEqual(vcode.find_tests(self.proj, os.path.join(self.proj, 'c.js')),
                         [os.path.join(self.proj, 'test', 'b_c.py')])
        self.assertEqual(vcode.find_tests(self.proj, os.path.join(self.proj, 'tests', 'b_a.py')), [])
        shutil.rmtree(os.path.join(self.proj, 'tests'))
        shutil.rmtree(os.path.join(self.proj, 'test'))

    def test_T47_a_python_function_is_green_when_a_suite_names_it(self):
        self.write('proj/m.py', '__all__ = ["f", "g"]\n\n\ndef f(x):\n    return x\n\n\ndef g(x):\n    return x\n')
        self.write('proj/tests/b_m.py', 'm.f(1)\n')
        html = vcode.vctab(os.path.join(self.proj, 'm.py'), self.proj)
        shown = bytes(html).decode('utf-8')
        self.assertIn('<td class="l green"><a href="#" data-line="4">f</a>', shown)
        self.assertNotIn('green"><a href="#" data-line="8">g</a>', shown)
        shutil.rmtree(os.path.join(self.proj, 'tests'))

    def test_T48_a_comment_line_is_never_shown_as_a_code_line(self):
        self.edit('d.css', insert=True, line=2, text='about color')
        shown = bytes(vcode.vctab(os.path.join(self.proj, 'd.css'), self.proj)).decode('utf-8')
        self.assertEqual(shown.count('class="cm"'), 1)
        self.assertNotIn('/***flm', shown)
        self.assertEqual(shown.count('class="ln'), 5)            # the 5 code lines, not the comment

    def bench_listing_of_a_small_repository(self, timer):
        with timer as test:
            while test.more:
                for _ in test.count:
                    vcserver.listing(self.proj)
        return 'listing (git ls-files + stat)', 'tree'

    def bench_open_a_python_file(self, timer):
        path = os.path.join(ROOT, 'tools', 'primary', 'vcode.py')
        with timer as test:
            while test.more:
                for _ in test.count:
                    vcode.vctab(path, ROOT)
        return 'vctab of vcode.py (codemark)', 'tab'

    def bench_open_a_javascript_file(self, timer):
        path = os.path.join(ROOT, 'tools', 'primary', 'html', 'vcomment.js')
        with timer as test:
            while test.more:
                for _ in test.count:
                    vcode.vctab(path, ROOT)
        return 'vctab of vcomment.js (vclang)', 'tab'
