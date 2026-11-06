r"""b_use.py -- tests for use: use, load and locate (use.py, 3.x). It replaces the suite of use 2.12,
which is in zprev/b_use_2_12.py.

Black box: the suite calls only what use lists in __all__ (use, load, locate) and looks only
at what they do: sys.path, sys.modules, the globals of the caller, the files of a build, what
is raised or printed. load binds the names of an item's __all__ in the caller, and
load(asmodule=[...]) binds one namespace for each item: T7 and T20 to T29.
The fixtures are written by setup_fixtures into folders u2_* beside this file's
fixtures/ folder, so that the search from this file finds them (a folder one level below
the caller's, the files of a folder two levels below). Nothing is deleted: a file is
rewritten only when its text changed, so a built .pyx stays built between runs.

Not tested: that no console window shows during a build (look at the screen once), and
use() with no item (it means the `primary` folder of whoever calls).

Run from the project root:
    python tools/runbench.py b_use -timeout=180
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

SOURCES = ['use']
load(asmodule=['use'])                                   # the namespace use: use, load, locate

FIXTURES = Path(__file__).resolve().parent / 'fixtures'
PURE = "__all__ = ['f']\n\n\ndef f():\n    return {!r}\n"
ADD = "__all__ = ['add']\n\n\ndef add(int a, int b):\n    return a + b\n"
NAMES = ('"""u2_names doc"""\n__all__ = [\'shown\', \'twin\']\nHIDDEN = 1\n_private = 2\n\n\n'
         "def shown():\n    return 'shown'\n\n\ndef twin():\n    return 'twin'\n")
FILES = {
    'u2_flat/u2_names.py': NAMES,
    'u2_flat/u2_noall.py': "def lone():\n    return 1\n",
    'u2_flat/u2_ghost.py': "__all__ = ['real', 'ghost']\n\n\ndef real():\n    return 1\n",
    'u2_pair/u2_pa.py': PURE.format('pa'),
    'u2_pair/u2_pb.py': PURE.format('pb'),
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


class b_use(bench):
    BenchName = 'use'
    BenchVersion = 'M1.1.5'          # runbench adds 1 to the last number on every run
    BenchHeader = 'use: use, load and locate'
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        for relative, text in FILES.items():
            path = FIXTURES / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.is_file() or path.read_text(encoding='utf-8') != text:
                path.write_text(text, encoding='utf-8')
        (FIXTURES / 'u2_work').mkdir(exist_ok=True)
        cls.built = attempt(lambda: use.load('u2_comp'))
        cls.bad = attempt(lambda: use.load('u2_bad'))
        cls.cbad = attempt(lambda: use.load('u2_cbad'))
        cls.amp = attempt(lambda: use.load('u2_amp'))
        cls.pct = attempt(lambda: use.load('u2_pct'))
        path = os.environ.get('PATH', '')
        os.environ['PATH'] = ''                  # no gcc to be found: for this one call
        try:
            cls.nogcc = attempt(lambda: use.load('u2_nogcc'))
        finally:
            os.environ['PATH'] = path

    # ---- use -----------------------------------------------------------------------------------
    def test_T1_use_puts_the_folder_of_an_item_on_sys_path_once(self):
        use.use('u2_flat')
        use.use('u2_flat')
        self.assertEqual(sys.path.count(str(FIXTURES / 'u2_flat')), 1)

    def test_T2_use_of_a_module_puts_the_folder_that_holds_it_on_sys_path(self):
        use.use('u2_one')
        self.assertIn(str(FIXTURES / 'u2_tree'), sys.path)
        self.assertNotIn('u2_one', sys.modules)           # use imports nothing

    def test_T3_plus_subs_adds_the_subfolders_too(self):
        use.use('u2_tree', '+subs')
        self.assertIn(str(FIXTURES / 'u2_tree' / 'inner'), sys.path)

    def test_T4_use_creates_the_folders_asked_for(self):
        here = os.getcwd()
        os.chdir(FIXTURES / 'u2_work')
        try:
            use.use('.results')                           # created, not put on the path
            use.use('data', '+mkdir')                     # created and put on the path
        finally:
            os.chdir(here)
        self.assertTrue((FIXTURES / 'u2_work' / 'results').is_dir())
        self.assertTrue((FIXTURES / 'u2_work' / 'data').is_dir())
        self.assertNotIn(str(FIXTURES / 'u2_work' / 'results'), sys.path)
        self.assertIn(str(FIXTURES / 'u2_work' / 'data'), sys.path)

    def test_T5_a_bad_flag_or_a_bad_folder_name_is_a_ValueError(self):
        with self.assertRaises(ValueError):
            use.use('u2_flat', '+nope')
        with self.assertRaises(ValueError):
            use.use('+subs')                              # a flag before any item
        with self.assertRaises(ValueError):
            use.use('.bad..name/../x')

    def test_T6_an_item_that_is_not_there_is_an_ImportError_naming_it(self):
        with self.assertRaises(ImportError) as caught:
            use.use('no_such_item_zz')
        self.assertIn('no_such_item_zz', str(caught.exception))

    # ---- load: pure python ------------------------------------------------------------------------
    def test_T7_load_imports_the_module_and_binds_its_all_names_here_and_returns_nothing(self):
        self.addCleanup(globals().pop, 'f', None)
        got = use.load('u2_pure_a')
        self.assertIsNone(got)
        self.assertIn('u2_pure_a', sys.modules)
        self.assertEqual(sys.modules['u2_pure_a'].f(), 'a')
        self.assertEqual(globals()['f'](), 'a')            # the name of its __all__ is bound here

    def test_T8_load_of_a_folder_imports_its_modules_but_not_private_ones_or_setup(self):
        use.load('u2_tree')
        self.assertEqual(sys.modules['u2_one'].f(), 'one')
        self.assertEqual(sys.modules['u2_two'].f(), 'two')
        self.assertNotIn('_u2_hidden', sys.modules)
        self.assertNotIn('setup', sys.modules)

    def test_T9_load_stops_at_the_first_failure(self):
        with self.assertRaises(RuntimeError):              # the module's own error
            use.load('u2_boom', 'u2_pure_b')
        self.assertNotIn('u2_pure_b', sys.modules)

    def test_T10_a_name_already_imported_from_another_folder_is_said_so(self):
        use.load('u2_dupa')
        said = io.StringIO()
        with contextlib.redirect_stdout(said):
            use.load('u2_dupb')
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
                use.load('u2_comp')
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

    # ---- load: what it binds in the caller -----------------------------------------------------------
    def test_T20_load_binds_the_names_of_all_and_no_other_name_and_no_dunder(self):
        for name in ('shown', 'twin'):
            self.addCleanup(globals().pop, name, None)
        before = (globals()['__name__'], globals().get('__doc__'), globals().get('__all__'))
        self.assertIsNone(use.load('u2_names'))
        self.assertEqual((globals()['shown'](), globals()['twin']()), ('shown', 'twin'))
        self.assertNotIn('HIDDEN', globals())
        self.assertNotIn('_private', globals())
        self.assertEqual((globals()['__name__'], globals().get('__doc__'), globals().get('__all__')), before)

    def test_T21_asmodule_binds_one_namespace_of_the_all_names_with_name_file_doc_and_all(self):
        self.addCleanup(globals().pop, 'u2_names', None)
        use.load(asmodule=['u2_names'])
        space = globals()['u2_names']
        self.assertIsInstance(space, SimpleNamespace)
        self.assertEqual((space.shown(), space.twin()), ('shown', 'twin'))
        for private in ('HIDDEN', '_private'):
            self.assertFalse(hasattr(space, private), private)      # the interface only
        self.assertEqual(space.__name__, 'u2_names')
        self.assertEqual(Path(space.__file__), FIXTURES / 'u2_flat' / 'u2_names.py')
        self.assertEqual(space.__doc__, 'u2_names doc')
        self.assertEqual(space.__all__, ['shown', 'twin'])
        self.assertNotIn('shown', globals())                        # no other name is bound here

    def test_T22_a_module_with_no_all_is_an_ImportError_that_says_so(self):
        for call in (lambda: use.load('u2_noall'), lambda: use.load(asmodule=['u2_noall'])):
            with self.assertRaises(ImportError) as caught:
                call()
            self.assertIn('no __all__', str(caught.exception))

    def test_T23_a_name_in_all_that_the_module_does_not_define_is_an_ImportError_naming_it(self):
        with self.assertRaises(ImportError) as caught:
            use.load('u2_ghost')
        self.assertIn('ghost', str(caught.exception))

    def test_T24_asmodule_of_a_folder_binds_a_namespace_for_each_of_its_modules(self):
        for name in ('u2_pa', 'u2_pb'):                  # u2_pair is these tests' own folder: u2_tree is
            self.addCleanup(globals().pop, name, None)   # left for T2 and T8, which look at what is imported
        use.load(asmodule=['u2_pair'])
        self.assertEqual((globals()['u2_pa'].f(), globals()['u2_pb'].f()), ('pa', 'pb'))

    def test_T25_items_and_asmodule_in_one_call(self):
        for name in ('shown', 'twin', 'u2_pa', 'u2_pb'):
            self.addCleanup(globals().pop, name, None)
        use.load('u2_names', asmodule=['u2_pair'])
        self.assertEqual(globals()['shown'](), 'shown')
        self.assertEqual(globals()['u2_pa'].f(), 'pa')

    def test_T26_there_is_no_into_and_no_silent(self):
        with self.assertRaises(TypeError):
            use.load('u2_names', into={})
        for call in (use.use, use.load):
            with self.assertRaises(ImportError) as caught:
                call('silent')
            self.assertIn('not found', str(caught.exception))

    def test_T27_load_with_nothing_to_load_loads_nothing(self):
        before = set(sys.modules)
        self.assertIsNone(use.load())
        self.assertIsNone(use.load(asmodule=[]))
        self.assertEqual(set(sys.modules), before)          # an empty list is not `primary`

    def test_T28_names_are_bound_in_the_module_that_calls_even_from_inside_a_function(self):
        for name in ('shown', 'twin'):
            self.addCleanup(globals().pop, name, None)

        def inner():
            use.load('u2_names')
        inner()
        self.assertIn('shown', globals())

    def test_T29_a_pyx_namespace_names_the_built_pyd_as_its_file(self):
        self.addCleanup(globals().pop, 'u2_comp', None)
        self.addCleanup(globals().pop, 'add', None)
        self.assertEqual(self.built, ('ok', None))
        use.load(asmodule=['u2_comp'])
        space = globals()['u2_comp']
        self.assertEqual(space.add(2, 3), 5)
        self.assertTrue(space.__file__.endswith('.pyd'), space.__file__)

    # ---- locate ----------------------------------------------------------------------------------
    def test_T17_locate_gives_the_file_load_would_import_and_a_pyx_beats_a_py(self):
        self.assertEqual(use.locate('u2_pure_a'), FIXTURES / 'u2_flat' / 'u2_pure_a.py')
        self.assertEqual(use.locate('u2_both'), FIXTURES / 'u2_flat' / 'u2_both.pyx')

    def test_T18_locate_of_a_name_that_is_not_there_is_None_and_imports_nothing(self):
        self.assertIsNone(use.locate('no_such_item_zz'))
        self.assertIsNone(sys.modules.get('u2_pure_c'))
        self.assertEqual(use.locate('u2_pure_c'), FIXTURES / 'u2_flat' / 'u2_pure_c.py')
        self.assertIsNone(sys.modules.get('u2_pure_c'))    # still not imported

    def test_T19_locate_searches_from_the_folder_given(self):
        self.assertEqual(use.locate('u2_inner', FIXTURES / 'u2_tree'),
                         FIXTURES / 'u2_tree' / 'inner' / 'u2_inner.py')

    # ---- timing ----------------------------------------------------------------------------------
    def bench_locate_a_module(self, timer):
        with timer as test:
            while test.more:
                for _ in test.count:
                    use.locate('u2_pure_a')
        return 'locate a module two levels below the caller', 'use'

    def bench_load_a_module_already_imported(self, timer):
        use.load('u2_pure_a')
        with timer as test:
            while test.more:
                for _ in test.count:
                    use.load('u2_pure_a')
        return 'load a module that is already imported', 'use'
