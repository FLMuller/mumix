# RETIRED 2026-11-05: the suite of use 2.12 (tools/prev/use_current.py), which had compile, CompileError and into=. use.py 3.x is tested by tests/b_use.py. Kept for history, not run, not imported.
r"""b_use.py -- tests for use.compile: a .pyx becomes a module, through Cython and two gcc
commands that use.py runs itself, with no console window.

Black box: the suite uses only what use lists in __all__ (compile, CompileError,
locate). build() is not tested here: it names a folder of the project, and a scratch
folder in the project is held by OneDrive. Every build is made once in setup_fixtures, in a scratch folder; the tests then
read what happened. The built modules are imported in a hidden child process, so nothing
is loaded here and no .pyd stays locked. Not tested: that no console window appears (look
at the screen once), and the refusal of a Cygwin gcc (there is none here).

Run from the project root:
    python tools/runbench.py b_use -timeout=120
"""
import atexit
import glob
import os
import shutil
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace

from bench import bench
from use import load

SOURCES = ['use']
use = SimpleNamespace(**load('use', into={}))

GOOD = 'def add(int a, int b):\n    return a + b\n'
BAD_SYNTAX = 'def bad(:\n'
BAD_C = 'cdef extern from "no_such_header_anywhere.h":\n    pass\ndef f():\n    return 1\n'
NUMPY = 'cimport numpy as cnp\ncnp.import_array()\ndef one():\n    return 1\n'


def wipe(folder):
    """Remove a scratch folder (a scanner may hold a file for a moment: try a few times)."""
    for _ in range(6):
        shutil.rmtree(folder, True)
        if not os.path.exists(folder):
            return
        time.sleep(0.5)


def attempt(call):
    """What a call gives: ('ok', value), or ('error', the CompileError or ValueError)."""
    try:
        return 'ok', call()
    except (use.CompileError, ValueError) as error:
        return 'error', error


def imported(folder, name, call):
    """What `name.call` says in a fresh, hidden Python that imports the build of <folder>."""
    code = (f'import sys; sys.path.insert(0, {os.path.join(folder, "pyxfiles")!r}); '
            f'import {name}; print({name}.{call})')
    done = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True,
                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    return done.returncode, done.stdout.strip(), done.stderr.strip()[-300:]


class b_use(bench):
    BenchName = 'use'
    BenchVersion = 'M1.0.13'          # runbench adds 1 to the last number on every run
    BenchHeader = 'use.compile: a .pyx to a module with gcc, hidden'
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        cls.folder = tempfile.mkdtemp(prefix='b_use_')       # the system temp: not in OneDrive
        atexit.register(wipe, cls.folder)

        def pyx(name, text):
            path = os.path.join(cls.folder, name + '.pyx')
            with open(path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(text)
            return path
        cls.paths = {name: pyx(name, text) for name, text in
                     (('good', GOOD), ('good_pair', GOOD), ('bad', BAD_SYNTAX),
                      ('badc', BAD_C), ('uses_numpy', NUMPY))}
        cls.good = attempt(lambda: use.compile(cls.paths['good']))
        cls.pair = attempt(lambda: use.compile([cls.paths['bad'], cls.paths['good_pair']]))
        cls.badc = attempt(lambda: use.compile(cls.paths['badc']))
        cls.numpy = attempt(lambda: use.compile(cls.paths['uses_numpy']))
        cls.missing = attempt(lambda: use.compile(os.path.join(cls.folder, 'nothing.pyx')))
        path = os.environ.get('PATH', '')
        os.environ['PATH'] = ''                  # no gcc to be found: only for this one call
        try:
            cls.nogcc = attempt(lambda: use.compile(cls.paths['good']))
        finally:
            os.environ['PATH'] = path

    def pyd(self, name):
        return glob.glob(os.path.join(self.folder, 'pyxfiles', name + '.*pyd'))

    def test_T1_a_good_pyx_gives_0_and_a_module_that_works(self):
        self.assertEqual(self.good, ('ok', 0))
        self.assertEqual(len(self.pyd('good')), 1)
        self.assertEqual(imported(self.folder, 'good', 'add(2, 3)')[:2], (0, '5'))

    def test_T2_every_file_of_a_list_is_tried_and_one_failure_does_not_stop_the_other(self):
        kind, error = self.pair
        self.assertEqual(kind, 'error')
        self.assertIsInstance(error, use.CompileError)
        self.assertIn('bad.pyx', str(error))
        self.assertEqual(len(self.pyd('good_pair')), 1)          # built although bad.pyx came first

    def test_T3_a_syntax_error_names_the_file_and_cython_with_a_code(self):
        kind, error = self.pair
        self.assertIn('Cython found', str(error))
        self.assertEqual(error.code, 1)

    def test_T4_a_c_error_names_the_compile_step_and_gccs_return_code(self):
        kind, error = self.badc
        self.assertEqual(kind, 'error')
        self.assertIn('the compile step failed', str(error))
        self.assertIn('no_such_header_anywhere.h', str(error))
        self.assertNotEqual(error.code, 0)

    def test_T6_a_missing_file_is_a_CompileError_that_says_so(self):
        kind, error = self.missing
        self.assertEqual(kind, 'error')
        self.assertIsInstance(error, use.CompileError)
        self.assertIn('is not there', str(error))

    def test_T7_no_gcc_on_the_path_is_a_CompileError_with_code_127(self):
        kind, error = self.nogcc
        self.assertEqual(kind, 'error')
        self.assertEqual(error.code, 127)
        self.assertIn('gcc was not found on PATH', str(error))

    def test_T8_a_pyx_that_cimports_numpy_gets_the_numpy_headers(self):
        try:
            import numpy  # noqa: F401
        except ImportError:
            self.skipTest('numpy is not installed')
        self.assertEqual(self.numpy, ('ok', 0))

    def bench_locate_a_pyx_by_name(self, timer):
        with timer as test:
            while test.more:
                for _ in test.count:
                    use.locate('good', self.folder)
        return 'locate a .pyx of a folder by name', 'use'
