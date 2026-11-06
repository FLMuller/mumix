r"""b_rs3util.py -- tests and benchmarks for rs3util: pathof (one path either way, the files a pattern names, the ignore
rules, HOME) and address (a page as an address and back).

Run from the project root:
    python tools/runbench.py b_rs3util
"""
import atexit
import os
import shutil
import sys


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

SOURCES = ['rs3util']
sys.path.insert(0, os.path.join(ROOT, 'tools', 'rs_primary'))
import rs3util
from rs3util import address, pathof

CLAUDE = os.path.dirname(ROOT)              # the folder that holds .claude and mumix
TMP = os.path.join(ROOT, 'tests', 'z_sandbox', 'rs3utiltmp')


def put(path, text='x'):
    full = os.path.join(TMP, *path.split('/'))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8', newline='') as f:
        f.write(text)
    return full


class b_rs3util(bench):
    BenchName = 'rs3util'
    BenchVersion = 'M1.0.6'          # runbench adds 1 to the last number on every run
    BenchHeader = 'pathof (paths, patterns, ignore rules) and address (a page as an address)'
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        shutil.rmtree(TMP, True)
        atexit.register(shutil.rmtree, TMP, True)
        os.makedirs(os.path.join(TMP, '.git'))                # a repository: the root of everything under it
        put('a.py', 'a = 1')
        put('b.md', '# b')
        put('c.txt', 'c')
        put('pic.png', 'png')
        put('sub/d.py', 'd = 1')
        put('sub/deeper/e.py', 'e = 1')
        put('sub/deeper/f.js', 'f')
        put('build/gen.py', 'ignored by the folder rule')
        put('run.log', 'ignored by *.log')
        put('keep.log', 'taken back by !keep.log')
        put('rootonly.txt', 'ignored at the root only')
        put('sub/rootonly.txt', 'not ignored: the rule is anchored')
        put('zprev/old.py', 'zprev is never entered')
        put('.hidden/h.py', 'a dot folder is never entered')
        put('__pycache__/x.py', 'never entered')
        put('.claude/CLAUDE.md', 'the one dot folder that is shown')
        put('mine.ignore2', 'x')
        put('.ignore', 'only_me.py\n')
        put('only_me.py', 'ignored by .ignore')
        put('.gitignore', '# a comment\nbuild/\n*.log\n!keep.log\n/rootonly.txt\nnested/\n')
        put('nested/.git/HEAD', 'ref')
        put('nested/n.py', 'a repository of its own: listed though the outer one ignores nested/')
        put('nested/.gitignore', 'secret.py\n')
        put('nested/secret.py', 'ignored by its own repository')
        cls.big = os.path.join(TMP, 'many')
        for k in range(30):
            put(f'many/m{k:02d}.py', str(k))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TMP, True)

    # ---- HOME and one path ---------------------------------------------------------------------------------
    def test_T1_home_is_the_parent_of_the_repository_that_holds_rs3(self):
        self.assertEqual(os.path.normcase(rs3util.HOME), os.path.normcase(os.path.realpath(CLAUDE)))
        self.assertTrue(os.path.isdir(os.path.join(rs3util.HOME, '.claude')))
        self.assertTrue(os.path.isdir(os.path.join(rs3util.HOME, 'mumix', '.git')))

    def test_T2_a_short_path_is_made_long_and_a_long_one_short(self):
        real = pathof('./mumix/tools/reportserver.py')
        self.assertEqual(os.path.normcase(real), os.path.normcase(os.path.join(rs3util.HOME, 'mumix', 'tools', 'reportserver.py')))
        self.assertEqual(pathof(real), './mumix/tools/reportserver.py')
        self.assertEqual(pathof('mumix/tools/reportserver.py'), real)             # the ./ is not needed
        self.assertEqual(os.path.normcase(pathof('./')), os.path.normcase(rs3util.HOME))
        self.assertEqual(pathof('.'), pathof('./'))
        self.assertEqual(pathof(rs3util.HOME), '.')

    def test_T3_a_path_that_is_not_well_formed_is_none(self):
        for bad in ('../x', './a/../b', './a//b', './a/./b', './a\\b', 'C:x.py', './a:b', '', None, 5, './' + 'x' * 400):
            self.assertIsNone(pathof(bad), repr(bad)[:40])
        self.assertIsNone(pathof('C:/Windows/win.ini'))                       # a real path outside the root
        self.assertIsNone(pathof('./mumix/../../'))

    def test_T4_a_start_names_another_root_by_walking_up_to_a_repository(self):
        sub = os.path.join(TMP, 'sub', 'deeper')
        self.assertEqual(os.path.normcase(pathof('./', start=sub)), os.path.normcase(os.path.realpath(TMP)))
        self.assertEqual(os.path.normcase(pathof('./', start=os.path.join(TMP, 'a.py'))), os.path.normcase(os.path.realpath(TMP)))
        self.assertEqual(pathof(os.path.join(TMP, 'sub', 'd.py'), start=TMP), './sub/d.py')
        self.assertEqual(os.path.normcase(pathof('./sub/d.py', start=TMP)), os.path.normcase(os.path.realpath(os.path.join(TMP, 'sub', 'd.py'))))
        self.assertIsNone(pathof(os.path.join(CLAUDE, 'mumix', 'tools', 'bench.py'), start=TMP))   # outside that root
        self.assertEqual(os.path.normcase(pathof('./', start=os.path.join(CLAUDE, 'mumix', 'tools'))),
                         os.path.normcase(os.path.realpath(os.path.join(CLAUDE, 'mumix'))))      # the nearest .git, not HOME
        self.assertIsNone(pathof('./', start='C:\\'))                          # never the bare drive

    def test_T5_kinds_and_maxsize_ask_for_a_file_the_tree_could_show(self):
        s = {'start': TMP}
        self.assertIsNotNone(pathof('./a.py', kinds=('code',), **s))
        self.assertIsNone(pathof('./a.py', kinds=('md',), **s))                # not that kind
        self.assertIsNone(pathof('./pic.png', kinds=('code', 'md', 'text', 'html'), **s))     # no kind at all
        self.assertIsNone(pathof('./no/such.py', kinds=('code',), **s))        # must exist
        self.assertIsNotNone(pathof('./no/such.py', **s))                      # no kinds: a name only
        self.assertIsNone(pathof('./a.py', kinds=('code',), maxsize=2, **s))   # 5 bytes
        self.assertIsNone(pathof('./.hidden/h.py', kinds=('code',), **s))      # a folder the tree never shows
        self.assertIsNone(pathof('./__pycache__/x.py', kinds=('code',), **s))
        self.assertIsNotNone(pathof('./.hidden/h.py', **s))                    # but it can be named
        self.assertIsNotNone(pathof('./sub/deeper/f.js', kinds=('code',), **s))
        self.assertEqual(rs3util.kind_of('x.result'), 'html')

    # ---- patterns ------------------------------------------------------------------------------------------
    def test_T6_a_pattern_names_files_in_order_a_folders_files_before_its_folders(self):
        got = pathof('./**', start=TMP)
        self.assertEqual(got[:5], ['./.gitignore', './.ignore', './a.py', './b.md', './c.txt'])       # the root's files first
        self.assertLess(got.index('./c.txt'), got.index('./.claude/CLAUDE.md'))                      # then its folders
        self.assertLess(got.index('./sub/d.py'), got.index('./sub/deeper/e.py'))
        self.assertEqual(pathof('./sub/*.py', start=TMP), ['./sub/d.py'])
        self.assertEqual(pathof('./sub/**/*.py', start=TMP), ['./sub/d.py', './sub/deeper/e.py'])   # ** may be no folder
        self.assertEqual(pathof('./*/d.py', start=TMP), ['./sub/d.py'])        # a wildcard in a folder name
        self.assertEqual(pathof('./sub/deeper/?.js', start=TMP), ['./sub/deeper/f.js'])
        self.assertEqual(sorted(pathof('./sub/**', start=TMP)), ['./sub/d.py', './sub/deeper/e.py', './sub/deeper/f.js', './sub/rootonly.txt'])

    def test_T7_braces_pick_names_and_kinds_in_order(self):
        self.assertEqual(pathof('./{b.md,a.py}', start=TMP), ['./b.md', './a.py'])          # in the order written
        self.assertEqual(pathof('./sub/**/*.{py,js}', start=TMP), ['./sub/d.py', './sub/deeper/e.py', './sub/deeper/f.js'])
        self.assertEqual(pathof('./{a.py,nope.py}', start=TMP), ['./a.py', './nope.py'])    # a plain name is not looked up
        self.assertEqual(pathof('./*.{md,txt}', start=TMP, kinds=('md', 'text')), ['./b.md', './c.txt'])
        self.assertEqual(pathof('./sub/**/*.zzz', start=TMP), [])                          # nothing: an empty list

    def test_T8_the_ignore_rules_are_git_s_and_the_default_ones_are_added(self):
        got = pathof('./**', start=TMP)
        for gone in ('./build/gen.py', './run.log', './rootonly.txt', './only_me.py', './zprev/old.py', './.hidden/h.py',
                     './__pycache__/x.py', './nested/secret.py'):
            self.assertNotIn(gone, got)
        for kept in ('./keep.log', './sub/rootonly.txt', './.claude/CLAUDE.md', './nested/n.py', './mine.ignore2'):
            self.assertIn(kept, got)
        self.assertEqual(got.truncated, False)

    def test_T9_a_nested_repository_has_its_own_rules_not_the_outer_ones(self):
        got = pathof('./nested/**', start=TMP)
        self.assertEqual(sorted(got), ['./nested/.gitignore', './nested/n.py'])

    def test_T10_the_walk_stops_at_its_limit_and_says_so(self):
        got = pathof('./many/*.py', start=TMP, limit=10)
        self.assertEqual((len(got), got.truncated), (10, True))
        got = pathof('./many/*.py', start=TMP, limit=100)
        self.assertEqual((len(got), got.truncated), (30, False))
        self.assertEqual((got.kind[got[0]], got.size[got[0]]), ('code', 1))

    def test_T11_kinds_filter_a_walk_and_a_pattern_cannot_leave_the_root(self):
        self.assertEqual(pathof('./**', start=TMP, kinds=('md',)), ['./b.md', './.claude/CLAUDE.md'])
        self.assertEqual(pathof('./sub/../*.py', start=TMP), [])
        self.assertEqual(pathof('./../*.py', start=TMP), [])

    # ---- address -------------------------------------------------------------------------------------------
    def test_T12_an_address_is_short_and_makes_the_page_again(self):
        blocks = {'toptabs': ['toptabs', './mumix/tools/reportserver.py', './mumix/tools/rs_primary/rs3util.py', './mumix/tests/b_reportserver.py']}
        url = address('[ftv wdxh, [toptabs ; [methods wdxh, [code ; editbox wxhd]]]]', blocks,
                      sizes={'ftv': (75, None), 'methods': (55, None), 'editbox': (None, 42)})
        self.assertEqual(url, '/?layout=[ftv,[toptabs;[methods,[code;editbox]]]]&toptabs=mumix/{tools/reportserver.py,tools/rs_primary/rs3util.py,tests/b_reportserver.py}')
        layout, specs, title, selftest = address(url)
        self.assertEqual((layout, selftest), ('[ftv,[toptabs;[methods,[code;editbox]]]]', False))
        self.assertEqual(specs['toptabs'], ['toptabs', './mumix/{tools/reportserver.py,tools/rs_primary/rs3util.py,tests/b_reportserver.py}'])
        self.assertEqual(specs['ftv'], ['ftv'])
        self.assertEqual(pathof(specs['toptabs'][1], start=None).__class__.__name__, 'Paths')
        self.assertEqual(list(pathof(specs['toptabs'][1])), ['./mumix/tools/reportserver.py', './mumix/tools/rs_primary/rs3util.py',
                                                              './mumix/tests/b_reportserver.py'])

    def test_T13_a_size_that_is_not_the_blocks_own_stays_and_a_space_is_an_underscore(self):
        url = address('[ftv 100dxh, [code ; editbox wx30d]]', {}, title='my page', sizes={'ftv': (75, None), 'editbox': (None, 42)})
        self.assertEqual(url, '/?layout=[ftv_100dxh,[code;editbox_wx30d]]&title=my_page')
        self.assertEqual(address(url)[0], '[ftv 100dxh,[code;editbox wx30d]]')
        self.assertEqual(address(url)[2], 'my page')

    def test_T14_a_page_is_written_with_the_blocks_name_when_it_has_one_of_a_kind_and_the_short_name_when_several(self):
        url = address('[a,methods.2]', {'a': ['code', './x.py'], 'methods.2': ['methods']})
        self.assertEqual(url, '/?layout=[code,methods]&code=x.py')            # one of each: the blocks' names, and the data follows
        self.assertEqual(address(url)[1], {'code': ['code', './x.py'], 'methods': ['methods']})
        url = address('[code.1,cd.2,eb]', {'code.1': ['code', './a.py'], 'cd.2': ['code', './b.py'], 'eb': ['editbox']})
        self.assertEqual(url, '/?layout=[cd.1,cd.2,editbox]&cd.1=a.py&cd.2=b.py')       # two codes: short; one editbox: long
        self.assertEqual(address(url)[1], {'cd.1': ['code', './a.py'], 'cd.2': ['code', './b.py'], 'editbox': ['editbox']})

    def test_T14a_a_locator_that_names_no_kind_is_defined_at_the_end_of_the_layout(self):
        url = address('[cd3,cd4]', {'cd3': ['code', './a.py'], 'cd4': ['code', './b.py']})
        self.assertEqual(url, '/?layout=[cd3,cd4]{cd3=code,cd4=code}&cd3=a.py&cd4=b.py')
        layout, specs, _, _ = address(url)
        self.assertEqual((layout, specs['cd3'], specs['cd4']), ('[cd3,cd4]{cd3=code,cd4=code}', ['code', './a.py'], ['code', './b.py']))
        self.assertTrue(address('[ftv,cd3]{cd3=code}', {}).startswith('/?layout=[ftv,code]'))        # one of its kind: the name, no definition

    def test_T15_a_page_that_cannot_be_an_address_is_none(self):
        self.assertIsNone(address('[doc]', {'doc': ['doc', '', '', '<p>x</p>']}))             # html
        self.assertIsNone(address('[toptabs]', {'toptabs': ['toptabs', './a,b.py']}))            # a name with a comma
        self.assertIsNone(address('[toptabs]', {'toptabs': ['toptabs'] + [f'./mumix/d{k}/{__import__("hashlib").sha1(str(k).encode()).hexdigest()}.py' for k in range(300)]}))   # over 6000 characters
        with self.assertRaises(ValueError):
            address('/?title=x')
        with self.assertRaises(ValueError):
            address('/?layout=%5Bdoc')

    def test_T16_patterns_travel_in_an_address_as_written_and_name_the_same_files_when_read(self):
        patterns = ['./mumix/tools/rs_primary/**/*.{py,md}', './mumix/*.md']
        url = address('[toptabs]', {'toptabs': ['toptabs'] + patterns})
        self.assertIn('toptabs=', url)
        read = address(url)[1]['toptabs'][1:]
        want = []
        for pattern in patterns:
            want += [path for path in pathof(pattern) if path not in want]
        got = []
        for pattern in read:
            got += [path for path in pathof(pattern) if path not in got]
        self.assertEqual(got, want)
        self.assertIn('./mumix/tools/rs_primary/rs3util.py', got)

    # ---- speed ---------------------------------------------------------------------------------------------
    def test_T40_a_folder_named_in_INCLUDE_is_entered_although_the_rules_hide_it(self):
        folder = os.path.join(TMP, 'inc')
        rules = 'results_x/' + chr(10) + 'hidden_x/' + chr(10)
        for name, content in (('.gitignore', rules), ('keep.html', 'k'), ('results_x/r.html', 'r'),
                              ('hidden_x/h.html', 'h')):
            path = os.path.join(folder, *name.split('/'))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
        self.addCleanup(shutil.rmtree, folder, True)
        got = pathof('./inc/**/*.html', start=TMP)
        self.assertEqual(sorted(got), ['./inc/keep.html', './inc/results_x/r.html'])    # results_x matches result*; hidden_x does not

    def bench_pathof_the_whole_home_tree(self, timer):
        with timer as test:
            while test.more:
                for _ in test.count:
                    pathof('./**', kinds=('code', 'md', 'text', 'html'))
        return 'pathof(./**) over the Claude folder', 'pathof'

    def bench_pathof_a_pattern_of_one_folder(self, timer):
        with timer as test:
            while test.more:
                for _ in test.count:
                    pathof('./mumix/tools/rs_primary/panes/pane_*.{py,js}')
        return 'pathof of pane_*.{py,js}', 'pathof'

    def bench_pathof_one_path_either_way(self, timer):
        with timer as test:
            while test.more:
                for _ in test.count:
                    pathof(pathof('./mumix/tools/reportserver.py'))
        return 'a short path to a long one and back', 'pathof'

    def bench_address_written_and_read(self, timer):
        blocks = {'toptabs': ['toptabs'] + [f'./mumix/tools/rs_primary/panes/pane_{n}.{e}' for n in ('code', 'ftv', 'log') for e in ('css', 'js', 'py')]}
        with timer as test:
            while test.more:
                for _ in test.count:
                    address(address('[ftv wdxh, [toptabs ; code]]', blocks, sizes={'ftv': (75, None)}))
        return 'an address written and read back (9 files)', 'address'
