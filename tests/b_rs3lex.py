r"""b_rs3lex.py -- tests and benchmarks for rs3lex, the one lexer of rs3 (colouring, the comment marker, the
functions, the inside test), against the two lexers it replaced.

The reference is primary/rs3twolex/rs3/: codelex.py and vclang.py exactly as rs3 had them before rs3lex. They
are loaded from there by path under other names (ref_codelex, ref_vclang), so nothing here depends on what else
is on the path. A test that compares compares the pieces of every line with adjacent pieces of one role merged.

Run from the project root:
    python tools/runbench.py b_rs3lex
"""
import atexit
import importlib.util
import os
import shutil
import sys
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

SOURCES = ['rs3lex']          # (the .pyx)
RS3 = os.path.join(ROOT, 'tools', 'primary', 'rs3')
REF = os.path.join(ROOT, 'tools', 'primary', 'rs3twolex', 'rs3')
sys.path.insert(0, RS3)
from use import load

load('rs3lex', into={})                                  # rs3lex.pyx, built into rs3/pyxfiles when need be
rs3lex = sys.modules['rs3lex']                           # its own functions, which its __all__ (Source, css) does not export: this suite tests them

CLAUDE = os.path.dirname(ROOT)


def load_ref(name):
    """The old module of rs3twolex/rs3, by path, under the name ref_<name>; None if the folder is not there."""
    path = os.path.join(REF, name + '.py')
    if not os.path.isfile(path):
        return None
    spec = importlib.util.spec_from_file_location('ref_' + name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules['ref_' + name] = module
    spec.loader.exec_module(module)
    return module


CODELEX, VCLANG = load_ref('codelex'), load_ref('vclang')


def merged(tokens):
    """The pieces of a line with neighbours of one role joined: [(role, text)]."""
    out = []
    for role, text in tokens:
        if out and out[-1][0] == role:
            out[-1] = (role, out[-1][1] + text)
        else:
            out.append((role, text))
    return out


def old_lex(path, lines):
    """The reference: [[(role, text)]] by codelex (Python, Cython) or vclang (the rest)."""
    name, words = CODELEX.language(path)
    if name:
        return CODELEX.lex('\n'.join(lines), name == 'cython', words)
    return [got[0] for got in VCLANG.lexgen(lines, VCLANG.spec_for(path))]


def read_lines(path):
    with open(path, 'rb') as f:
        text = f.read().decode('utf-8', 'replace')
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    return lines


def corpus():
    """Real files: the rs3 folder, tests/ and tools/, and some of each of the other kinds from the whole tree."""
    found = []
    for folder in (RS3, os.path.join(ROOT, 'tests'), os.path.join(ROOT, 'tools'), os.path.join(ROOT, 'tools', 'primary')):
        for top, dirs, names in os.walk(folder):
            dirs[:] = [d for d in dirs if d not in ('__pycache__', 'zprev', 'rs3twolex', 'rs3vcdep', 'z_sandbox', 'logs')]
            found += [os.path.join(top, n) for n in sorted(names) if n.endswith(('.py', '.pyx', '.js', '.css', '.md', '.mu', '.txt'))]
    more = {'.m': 25, '.txt': 10, '.md': 10, '.js': 10, '.css': 10}
    for top, dirs, names in os.walk(CLAUDE):
        dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__', 'zprev', 'rs3twolex', 'rs3vcdep', 'node_modules')]
        for n in sorted(names):
            ext = os.path.splitext(n)[1].lower()
            if more.get(ext):
                more[ext] -= 1
                found.append(os.path.join(top, n))
    return sorted(set(found))


SAMPLES = {
    'x.bas': ["Attribute VB_Name = \"Module1\"", "Option Explicit", "' a note TODO", "Public Function Add(a As Long) As Long",
              "    Dim s As String: s = \"say \"\"hi\"\"\"", "    Add = a + 1.5e3  ' trailing", "End Function",
              "Private Type Pt", "    X As Double", "End Type"],
    'x.css': ["/* head */", "@media (min-width: 10px) {", "  .a, #b > p:hover { color: #ff0; margin: -2px 3% }", "}",
              "/* open", "   still */ a { content: \"x\" }"],
    'x.js': ["// line", "/* block", "   more */ const a = `t", "u`; class K { m(x) { return x.y(1) + this.z } }",
             "export default async function f(a, b) { return a === b ? null : [a, 0x1F] }"],
    'x.m': ["%% cell", "function y = f(x)", "%{", "block", "%}", "y = x' + [1 2 3]'; s = 'it''s'; z = a.^2 ... cont", "end",
            "classdef Foo", "  methods", "    function r = m(o)", "    end", "  end", "end"],
    'x.txt': ["# a note", "[section]", "name: value 12 true \"quoted\" # trailing", "key = https://x.org ; end", "plain words 3.5"],
    'x.md': ["# Title", "", "text **bold** `code` [l](http://x.org) 12", "| a | b |", "|---|---|", "", "```", "code", "```"],
    'x.py': ["\"\"\"doc", "more\"\"\"", "import os, re as rx", "from a.b import (c,", "    d)", "__all__ = ['f', 'K']", "",
             "@dec", "class K(Base):", "    \"\"\"d\"\"\"", "    def f(self, a: int = 1, *b) -> 'K':",
             "        return f'{a!r:>{b}} {self.x.y(1)} %s' % (a,) # tail", "def g(): pass",
             "x = re.compile(r'^(\\d+)[a-z]*$')", "y = {'k': [1, 2.5e3, 0xFF]}  # end"],
    'x.pyx': ["# cython: language_level=3", "cdef int n = <int>x", "cdef class C:", "    cdef double* p", "cpdef f(int a, bint b=0):",
              "    return cython.cast(int, a) & b"],
}


def compare(self, path, lines):
    """Assert that rs3lex and the reference give the same pieces for every line; names the first that differ."""
    old = old_lex(path, lines)
    new = [got[0] for got in rs3lex.lex(lines, rs3lex.language(path))]
    self.assertEqual(len(old), len(new), path)
    bad = [k for k in range(len(lines)) if merged(old[k]) != merged(new[k])]
    if bad:
        k = bad[0]
        self.fail(f'{path}: {len(bad)} of {len(lines)} lines differ, the first is line {k + 1}: {lines[k]!r}\n'
                  f'   old {merged(old[k])}\n   new {merged(new[k])}')


class b_rs3lex(bench):
    BenchName = 'rs3lex'
    BenchVersion = 'M1.0.0'          # runbench adds 1 to the last number on every run
    BenchHeader = 'the one lexer of rs3, against codelex and vclang'
    sources = SOURCES

    # ---- the language of a file ------------------------------------------------------------------
    def test_T0_the_lexer_is_the_compiled_one(self):
        import sys
        self.assertTrue(sys.modules['rs3lex'].__file__.endswith('.pyd'), sys.modules['rs3lex'].__file__)

    def test_T1_a_file_has_the_language_of_its_extension_and_an_unknown_one_is_an_error(self):
        for name, language, mode in (('a.py', 'python', 'python'), ('a.PYX', 'cython', 'python'), ('a.js', 'javascript', 'code'),
                                     ('a.css', 'css', 'css'), ('a.m', 'matlab', 'code'), ('a.bas', 'vba', 'code'),
                                     ('a.txt', 'text', 'text'), ('a.md', 'markdown', 'markdown'), ('a.mu', 'markdown', 'markdown')):
            got = rs3lex.language(name)
            self.assertEqual((got.name, got.mode), (language, mode), name)
        for name in ('a.zzz', 'noext', 'a.json'):
            with self.assertRaises(rs3lex.NoLanguage) as raised:
                rs3lex.language(name)
            self.assertIn(os.path.basename(name), str(raised.exception))

    # ---- the pieces ----------------------------------------------------------------------------------
    def test_T2_the_pieces_of_every_line_join_back_to_the_line_and_every_role_has_a_colour(self):
        styled = {line.split('{')[0][3:] for line in rs3lex.css().splitlines() if line.startswith('.r-')}
        roles = set()
        for path in corpus():
            lines = read_lines(path)
            for k, (tokens, block, depth) in enumerate(rs3lex.lex(lines, rs3lex.language(path))):
                self.assertEqual(''.join(t for r, t in tokens), lines[k], f'{path} line {k + 1}')
                roles |= {r for r, t in tokens}
        self.assertEqual(sorted(roles - styled - {'default'}), [])

    def test_T3_a_digit_that_is_not_0_to_9_does_not_crash_the_scan(self):
        for name in ('a.py', 'a.js', 'a.md', 'a.m'):
            got = rs3lex.lex(['cells² and ٣ x'], rs3lex.language(name))
            self.assertEqual(''.join(t for r, t in got[0][0]), 'cells² and ٣ x')

    # ---- the same pieces as the lexers it replaced -------------------------------------------------------
    @classmethod
    def requires_reference(cls):
        return CODELEX is not None and VCLANG is not None

    def test_T4_the_pieces_are_those_of_codelex_and_vclang_on_real_files(self):
        if CODELEX is None:
            self.skipTest('rs3twolex/rs3 is not there')
        for path in corpus():
            if os.path.getsize(path) > 300000:
                continue
            compare(self, path, read_lines(path))

    def test_T5_the_pieces_are_those_of_codelex_and_vclang_on_samples_of_every_language(self):
        if CODELEX is None:
            self.skipTest('rs3twolex/rs3 is not there')
        for name, lines in SAMPLES.items():
            compare(self, name, lines)

    def test_T6_the_colours_are_those_of_codelex(self):
        if CODELEX is None:
            self.skipTest('rs3twolex/rs3 is not there')
        new = set(rs3lex.css().splitlines())
        self.assertEqual(sorted(set(CODELEX.css().splitlines()) - new), [])

    # ---- the comment marker, inside, and the functions -----------------------------------------------------
    def test_T7_a_comment_is_written_and_read_back_in_every_language(self):
        for name, marker in (('a.py', '###'), ('a.m', '%%%'), ('a.js', '///'), ('a.css', '/***'), ('a.md', '<!--###'),
                             ('a.bas', "'''"), ('a.txt', '###')):
            mark = rs3lex.review(rs3lex.language(name))
            lines = mark.write('    ', 'flm', 'one\ntwo')
            self.assertEqual(len(lines), 2, name)
            for line, word in zip(lines, ('one', 'two')):
                self.assertTrue(line.startswith('    ' + marker + 'flm'), (name, line))
                got = mark.match(line)
                self.assertEqual((got.group(1), got.group(2)), ('flm', word), (name, line))
            self.assertFalse(mark.match('x = 1'))
        py = rs3lex.review(rs3lex.language('a.py'))
        self.assertTrue(py.separator.match('  ####'))
        self.assertFalse(py.separator.match('###flm text'))

    def test_T8_a_row_inside_a_string_or_block_comment_is_inside_and_the_rest_is_not(self):
        doc = ['x = 1', '"""docstring', 'second line', '"""', 'y = 2']
        py = rs3lex.language('a.py')
        self.assertEqual([rs3lex.inside(doc, py, row) for row in range(1, 6)], [False, False, True, True, False])
        js = ['a();', '/* open', 'mid', '*/ b();', 'c = `t', 'u`;', 'd();']
        got = [rs3lex.inside(js, rs3lex.language('a.js'), row) for row in range(1, 8)]
        self.assertEqual(got, [False, False, True, True, False, True, False])
        self.assertFalse(rs3lex.inside(['# a', 'b: c'], rs3lex.language('a.txt'), 2))

    def test_T9_the_functions_are_those_of_vclang_and_a_method_is_Class_method(self):
        if VCLANG is None:
            self.skipTest('rs3twolex/rs3 is not there')
        for name, lines in SAMPLES.items():
            if name in ('x.py', 'x.pyx'):
                continue                                     # Python's list is the syntax tree's (rs3comment)
            spec = VCLANG.spec_for(name)
            old = VCLANG.functions(lines, spec, VCLANG.lexgen(lines, spec))
            self.assertEqual(rs3lex.functions(lines, rs3lex.language(name)), old, name)
        names = [f[0] for f in rs3lex.functions(SAMPLES['x.py'], rs3lex.language('x.py'))]
        self.assertEqual(names, ['K', 'K.f', 'g'])

    # ---- speed -----------------------------------------------------------------------------------------
    # ---- Source: the file read once, with its tokens, comment runs and functions -------------------------------
    def sample(self, name, text):
        folder = os.path.join(ROOT, 'tests', 'z_sandbox', 'rs3lextmp')
        if not os.path.isdir(folder):
            os.makedirs(folder)
            atexit.register(shutil.rmtree, folder, True)
        path = os.path.join(folder, name)
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(text)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        return path

    def test_T20_source_reads_a_file_once_and_keeps_it_while_it_is_unchanged(self):
        path = self.sample('a.py', 'x = 1\n')
        first = rs3lex.Source.read(path)
        self.assertIs(rs3lex.Source.read(path), first)
        self.assertEqual(first.base, __import__('hashlib').sha1(b'x = 1\n').hexdigest())
        self.assertEqual((first.lines, first.raw), (['x = 1'], b'x = 1\n'))
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write('x = 12\n')                           # the size changes: a new Source
        self.assertIsNot(rs3lex.Source.read(path), first)

    def test_T21_tokens_join_back_to_the_lines_and_comments_are_runs_of_one_tag(self):
        text = 'def f(a):\n    ###fm one\n    ###fm two\n    ###cl reply\n    return a + 1  # not a comment of ours\n'
        src = rs3lex.Source.read(self.sample('b.py', text))
        self.assertEqual([''.join(t for _, t in line) for line in src.tokens()], src.lines)
        self.assertEqual(src.comments(), {2: [2, 3, 'fm'], 4: [4, 4, 'cl']})
        self.assertEqual([x[0] for x in src.functions()], ['f'])
        self.assertFalse(src.inside(2))

    def test_T22_a_file_no_lang_file_describes_is_a_ValueError_with_its_extension(self):
        with self.assertRaises(ValueError) as caught:
            rs3lex.Source.read(self.sample('c.zzz', 'x'))
        self.assertIn('zzz', str(caught.exception))

    def test_T23_coloured_gives_the_pieces_of_some_text_for_an_extension_and_none_for_an_unknown_one(self):
        got = rs3lex.Source.coloured('py', 'x = 1\ny = "s"')
        self.assertEqual([''.join(t for _, t in line) for line in got], ['x = 1', 'y = "s"'])
        self.assertIsNone(rs3lex.Source.coloured('zzz', 'x'))

    def test_T24_inside_says_a_row_in_a_triple_string_cannot_take_a_comment(self):
        src = rs3lex.Source.read(self.sample('d.py', 'a = """\nline\n"""\nb = 2\n'))
        self.assertTrue(src.inside(2))
        self.assertFalse(src.inside(4))

    def bench_lex_python_file(self, timer):
        path = os.path.join(RS3, 'rs3lex.py')
        lines, lang = read_lines(path), rs3lex.language(path)
        with timer as test:
            while test.more:
                for _ in test.count:
                    rs3lex.lex(lines, lang)
        return f'rs3lex.lex of rs3lex.py ({len(lines)} lines)', 'python'

    def bench_codelex_python_file(self, timer):
        path = os.path.join(RS3, 'rs3lex.py')
        lines = read_lines(path)
        name, words = CODELEX.language(path)
        text = '\n'.join(lines)
        with timer as test:
            while test.more:
                for _ in test.count:
                    CODELEX.lex(text, name == 'cython', words)
        return f'codelex.lex of the same file', 'python'

    def bench_lex_javascript_file(self, timer):
        path = os.path.join(RS3, 'html', 'manager.js')
        lines, lang = read_lines(path), rs3lex.language(path)
        with timer as test:
            while test.more:
                for _ in test.count:
                    rs3lex.lex(lines, lang)
        return f'rs3lex.lex of manager.js ({len(lines)} lines)', 'javascript'

    def bench_vclang_javascript_file(self, timer):
        path = os.path.join(RS3, 'html', 'manager.js')
        lines = read_lines(path)
        spec = VCLANG.spec_for(path)
        with timer as test:
            while test.more:
                for _ in test.count:
                    VCLANG.lexgen(lines, spec)
        return 'vclang.lexgen of the same file', 'javascript'
