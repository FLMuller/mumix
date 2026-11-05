r"""b_use2.py -- tests for use2: use, load and locate.

Black box: the suite calls only what use2 lists in __all__ (use, load, locate) and looks only
at what they do: sys.path, sys.modules, the files of a build, what is raised or printed.
The fixtures are written by setup_fixtures into folders u2_* beside this file's
fixtures/ folder, so that the search from this file finds them (a folder one level below
the caller's, the files of a folder two levels below). Nothing is deleted: a file is
rewritten only when its text changed, so a built .pyx stays built between runs.

Not tested: that no console window shows during a build (look at the screen once), and
use() with no item (it means the `primary` folder of whoever calls).

Run from the project root:
    python tools/runbench.py b_use2 -timeout=180
"""
import contextlib
import io
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

from bench import bench
from use import load

SOURCES = ['use2']
use2 = SimpleNamespace(**load('use2', into={}))          # use, load, locate

FIXTURES = Path(__file__).resolve().parent / 'fixtures'
PURE = "def f():\n    return {!r}\n"
ADD = "def add(int a, int b):\n    return a + b\n"
FILES = {
    'u2_flat/u2_pure_a.py': PURE.format('a'),
    'u2_flat/u2_pure_b.py': PURE.format('b'),
    'u2_flat/u2_pure_c.py': PURE.format('c'),
    'u2_flat/u2_boom.py': "raise RuntimeError('boom')\n",
    'u2_flat/u2_both.py': PURE.format('py'),
    'u2_flat/u2_both.pyx': ADD,
    'u2_flat/u2_comp.pyx': ADD,
    'u2_flat/u2_bad.pyx': "def bad(:\n",
    'u2_flat/u2_cbad.pyx': 'cdef extern from "no_such_header_anywhere.h":\n    pass\n',
    'u2_flat/u2_nogcc.pyx': ADD,
    'u2_tree/u2_one.py': PURE.format('one'),
    'u2_tree/u2_two.py': PURE.format('two'),
    'u2_tree/_u2_hidden.py': PURE.format('hidden'),
    'u2_tree/setup.py': PURE.format('setup'),
    'u2_tree/inner/u2_inner.py': PURE.format('inner'),
    'u2_dupa/u2_dup.py': PURE.format('dupa'),
    'u2_dupb/u2_dup.py': PURE.format('dupb'),
    'u2_q&r s/u2_amp.pyx': ADD,
    'u2_p%PATH%q/u2_pct.pyx': ADD,
}


def attempt(call):
    """What a call does: ('ok', None), or ('error', the exception)."""
    try:
        call()
        return 'ok', None
    except Exception as error:
        return 'error', error


def imported_from(name):
    """The folder a module was imported from (a build's pyxfiles folder counts as its parent)."""
    there = Path(sys.modules[name].__file__).parent
    return there.parent if there.name == 'pyxfiles' else there


class b_use2(bench):
    BenchName = 'use2'
    BenchVersion = 'M1.0.13'          # runbench adds 1 to the last number on every run
    BenchHeader = 'use2: use, load and locate'
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        for relative, text in FILES.items():
            path = FIXTURES / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.is_file() or path.read_text(encoding='utf-8') != text:
                path.write_text(text, encoding='utf-8')
        (FIXTURES / 'u2_work').mkdir(exist_ok=True)
        cls.built = attempt(lambda: use2.load('u2_comp'))
        cls.bad = attempt(lambda: use2.load('u2_bad'))
        cls.cbad = attempt(lambda: use2.load('u2_cbad'))
        cls.amp = attempt(lambda: use2.load('u2_amp'))
        cls.pct = attempt(lambda: use2.load('u2_pct'))
        path = os.environ.get('PATH', '')
        os.environ['PATH'] = ''                  # no gcc to be found: for this one call
        try:
            cls.nogcc = attempt(lambda: use2.load('u2_nogcc'))
        finally:
            os.environ['PATH'] = path

    # ---- use -----------------------------------------------------------------------------------
    def test_T1_use_puts_the_folder_of_an_item_on_sys_path_once(self):
        use2.use('u2_flat')
        use2.use('u2_flat')
        self.assertEqual(sys.path.count(str(FIXTURES / 'u2_flat')), 1)

    def test_T2_use_of_a_module_puts_the_folder_that_holds_it_on_sys_path(self):
        use2.use('u2_one')
        self.assertIn(str(FIXTURES / 'u2_tree'), sys.path)
        self.assertNotIn('u2_one', sys.modules)           # use imports nothing

    def test_T3_plus_subs_adds_the_subfolders_too(self):
        use2.use('u2_tree', '+subs')
        self.assertIn(str(FIXTURES / 'u2_tree' / 'inner'), sys.path)

    def test_T4_use_creates_the_folders_asked_for(self):
        here = os.getcwd()
        os.chdir(FIXTURES / 'u2_work')
        try:
            use2.use('.results')                           # created, not put on the path
            use2.use('data', '+mkdir')                     # created and put on the path
        finally:
            os.chdir(here)
        self.assertTrue((FIXTURES / 'u2_work' / 'results').is_dir())
        self.assertTrue((FIXTURES / 'u2_work' / 'data').is_dir())
        self.assertNotIn(str(FIXTURES / 'u2_work' / 'results'), sys.path)
        self.assertIn(str(FIXTURES / 'u2_work' / 'data'), sys.path)

    def test_T5_a_bad_flag_or_a_bad_folder_name_is_a_ValueError(self):
        with self.assertRaises(ValueError):
            use2.use('u2_flat', '+nope')
        with self.assertRaises(ValueError):
            use2.use('+subs')                              # a flag before any item
        with self.assertRaises(ValueError):
            use2.use('.bad..name/../x')

    def test_T6_an_item_that_is_not_there_is_an_ImportError_naming_it(self):
        with self.assertRaises(ImportError) as caught:
            use2.use('no_such_item_zz')
        self.assertIn('no_such_item_zz', str(caught.exception))

    # ---- load: pure python ------------------------------------------------------------------------
    def test_T7_load_imports_the_module_and_binds_nothing_and_returns_nothing(self):
        before = set(globals())
        got = use2.load('u2_pure_a')
        self.assertIsNone(got)
        self.assertIn('u2_pure_a', sys.modules)
        self.assertEqual(sys.modules['u2_pure_a'].f(), 'a')
        self.assertEqual(set(globals()), before)           # no name bound here

    def test_T8_load_of_a_folder_imports_its_modules_but_not_private_ones_or_setup(self):
        use2.load('u2_tree')
        self.assertEqual(sys.modules['u2_one'].f(), 'one')
        self.assertEqual(sys.modules['u2_two'].f(), 'two')
        self.assertNotIn('_u2_hidden', sys.modules)
        self.assertNotIn('setup', sys.modules)

    def test_T9_load_stops_at_the_first_failure(self):
        with self.assertRaises(RuntimeError):              # the module's own error
            use2.load('u2_boom', 'u2_pure_b')
        self.assertNotIn('u2_pure_b', sys.modules)

    def test_T10_a_name_already_imported_from_another_folder_is_said_so(self):
        use2.load('u2_dupa')
        said = io.StringIO()
        with contextlib.redirect_stdout(said):
            use2.load('u2_dupb')
        self.assertEqual(imported_from('u2_dup'), FIXTURES / 'u2_dupa')
        self.assertIn('WARNING', said.getvalue())
        self.assertIn('u2_dupb', said.getvalue())

    # ---- load: a .pyx is built -------------------------------------------------------------------
    def test_T11_load_builds_a_pyx_and_imports_it_leaving_only_the_pyd(self):
        self.assertEqual(self.built, ('ok', None))
        self.assertEqual(sys.modules['u2_comp'].add(2, 3), 5)
        left = sorted(p.suffix for p in (FIXTURES / 'u2_flat' / 'pyxfiles').glob('u2_comp*'))
        self.assertEqual(left, ['.pyd'])                   # no .c, no .bat, no .o, no .def
        self.assertFalse(list((FIXTURES / 'u2_flat' / 'pyxfiles').glob('*.bat')))

    def test_T12_a_pyx_that_is_newer_than_the_build_in_use_says_to_run_again(self):
        pyx = FIXTURES / 'u2_flat' / 'u2_comp.pyx'
        old = pyx.stat().st_mtime
        os.utime(pyx, (old + 60, old + 60))
        try:
            with self.assertRaises(ImportError) as caught:
                use2.load('u2_comp')
            self.assertIn('run again', str(caught.exception))
        finally:
            os.utime(pyx, (old, old))

    def test_T13_a_pyx_with_a_syntax_error_is_an_ImportError_naming_cython(self):
        kind, error = self.bad
        self.assertEqual(kind, 'error')
        self.assertIsInstance(error, ImportError)
        self.assertIn('Cython failed', str(error))
        self.assertIn('u2_bad.pyx', str(error))

    def test_T14_a_c_error_names_gcc_and_carries_its_messages(self):
        kind, error = self.cbad
        self.assertEqual(kind, 'error')
        self.assertIsInstance(error, ImportError)
        self.assertIn('gcc failed', str(error))
        self.assertIn('no_such_header_anywhere.h', str(error))

    def test_T15_no_gcc_is_an_ImportError_that_says_so(self):
        kind, error = self.nogcc
        self.assertEqual(kind, 'error')
        self.assertIsInstance(error, ImportError)
        self.assertIn('gcc was not found', str(error))

    def test_T16_a_folder_with_an_ampersand_or_a_percent_in_its_name_builds(self):
        self.assertEqual(self.amp, ('ok', None))
        self.assertEqual(self.pct, ('ok', None))
        self.assertEqual(sys.modules['u2_amp'].add(1, 2), 3)
        self.assertEqual(sys.modules['u2_pct'].add(4, 5), 9)

    # ---- locate ----------------------------------------------------------------------------------
    def test_T17_locate_gives_the_file_load_would_import_and_a_pyx_beats_a_py(self):
        self.assertEqual(use2.locate('u2_pure_a'), FIXTURES / 'u2_flat' / 'u2_pure_a.py')
        self.assertEqual(use2.locate('u2_both'), FIXTURES / 'u2_flat' / 'u2_both.pyx')

    def test_T18_locate_of_a_name_that_is_not_there_is_None_and_imports_nothing(self):
        self.assertIsNone(use2.locate('no_such_item_zz'))
        self.assertIsNone(sys.modules.get('u2_pure_c'))
        self.assertEqual(use2.locate('u2_pure_c'), FIXTURES / 'u2_flat' / 'u2_pure_c.py')
        self.assertIsNone(sys.modules.get('u2_pure_c'))    # still not imported

    def test_T19_locate_searches_from_the_folder_given(self):
        self.assertEqual(use2.locate('u2_inner', FIXTURES / 'u2_tree'),
                         FIXTURES / 'u2_tree' / 'inner' / 'u2_inner.py')

    # ---- timing ----------------------------------------------------------------------------------
    def bench_locate_a_module(self, timer):
        with timer as test:
            while test.more:
                for _ in test.count:
                    use2.locate('u2_pure_a')
        return 'locate a module two levels below the caller', 'use2'

    def bench_load_a_module_already_imported(self, timer):
        use2.load('u2_pure_a')
        with timer as test:
            while test.more:
                for _ in test.count:
                    use2.load('u2_pure_a')
        return 'load a module that is already imported', 'use2'
