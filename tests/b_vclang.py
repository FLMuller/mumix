r"""b_vclang.py -- tests and benchmarks for vclang, the languages of vcomment: which files it
opens, the comment triplet of each, the lexer for MATLAB, JavaScript and CSS, the function lists.

Run from the project root:
    python tools/runbench.py b_vclang
"""
import os
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

SOURCES = ['vclang']
import vclang


def roles(pieces, row):
    """The (role, text) pairs of one line (0-based row) without the plain spaces."""
    return [t for t in pieces[row][0] if t[1].strip()]


class b_vclang(bench):
    BenchName = 'vclang'
    BenchVersion = 'M1.0.10'          # runbench adds 1 to the last number on every run
    BenchHeader = 'the languages of vcomment: triplets, lexer, function lists'
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        cls.js = ['// line', 'function f(a) {', '  return a + `t ${a}`;', '}'] * 500

    # ---- which files, which comment ---------------------------------------------------------
    def test_T1_kind_of_each_extension(self):
        want = {'a.py': 'code', 'a.pyx': 'code', 'a.pxd': 'code', 'a.m': 'code', 'a.js': 'code',
                'a.css': 'code', 'a.md': 'md', 'a.txt': 'text', 'a.html': 'html',
                'a.htm': 'html', 'a.pyd': '', 'a.xlsx': '', 'a.cht': '', 'noext': ''}
        for name, kind in want.items():
            self.assertEqual(vclang.kind_of(name), kind, name)

    def test_T2_kind_ignores_case_of_extension(self):
        self.assertEqual(vclang.kind_of('A.PY'), 'code')
        self.assertEqual(vclang.kind_of('B.HTML'), 'html')

    def test_T3_triplet_of_each_language(self):
        want = {'a.py': ('###', ''), 'a.pyx': ('###', ''), 'a.m': ('%%%', ''),
                'a.js': ('///', ''), 'a.css': ('/***', '*/'), 'a.md': ('<!--###', '-->'),
                'a.txt': ('###', '')}
        for name, (open_, close) in want.items():
            spec = vclang.spec_for(name)
            self.assertEqual((spec.open, spec.close), (open_, close), name)

    def test_T4_no_spec_for_a_file_that_is_not_opened(self):
        self.assertIsNone(vclang.spec_for('a.html'))
        self.assertIsNone(vclang.spec_for('a.xlsx'))

    def test_T5_comment_lines_match_their_regex_and_carry_tag_and_text(self):
        for name in ('a.py', 'a.m', 'a.js', 'a.css', 'a.md', 'a.txt'):
            spec = vclang.spec_for(name)
            rx = vclang.comment_regex(spec)
            lines = vclang.comment_lines(spec, '    ', 'flm', 'why this?\n\nsecond')
            self.assertEqual(len(lines), 3, name)
            got = [rx.match(x) for x in lines]
            self.assertTrue(all(got), (name, lines))
            self.assertEqual([m.group(1) for m in got], ['flm'] * 3)
            self.assertEqual([m.group(2) or '' for m in got], ['why this?', '', 'second'], name)

    def test_T6_a_plain_comment_is_not_a_review_comment(self):
        cases = {'a.py': ['# note', '#### heading', 'x = 1  ###flm'],
                 'a.m': ['% note', '%% cell', 'x = 1; %%%flm'],
                 'a.js': ['// note', 'x = 1; ///flm'], 'a.css': ['/* note */', '/**flm x */'],
                 'a.md': ['<!-- note -->', '### heading']}
        for name, lines in cases.items():
            rx = vclang.comment_regex(vclang.spec_for(name))
            for line in lines:
                self.assertIsNone(rx.match(line), (name, line))

    def test_T7_separator_is_the_triplet_alone(self):
        sep = vclang.separator_regex(vclang.spec_for('a.py'))
        self.assertTrue(sep.match('###'))
        self.assertTrue(sep.match('  ########'))
        self.assertIsNone(sep.match('###flm'))
        sep = vclang.separator_regex(vclang.spec_for('a.m'))
        self.assertTrue(sep.match('%%%'))
        self.assertIsNone(sep.match('%%'))
        sep = vclang.separator_regex(vclang.spec_for('a.css'))
        self.assertTrue(sep.match('/*** */'))

    # ---- the lexer --------------------------------------------------------------------------
    def test_T8_matlab_comment_string_and_transpose(self):
        spec = vclang.spec_for('a.m')
        pieces = vclang.lexgen(["x = a' * b';  % note", "s = 'it''s'; t = \"dq\";"], spec)
        first = roles(pieces, 0)
        self.assertIn(('operator', "'"), first)                  # a' is a transpose
        self.assertEqual(first[-1][0], 'comment')
        self.assertEqual([t for t in roles(pieces, 1) if t[0] == 'string'],
                         [('string', "'it''s'"), ('string', '"dq"')])

    def test_T9_matlab_block_comment_alone_on_its_lines(self):
        spec = vclang.spec_for('a.m')
        pieces = vclang.lexgen(['a = 1;', '%{', 'inside = 2;', '%}', 'b = 3;'], spec)
        self.assertEqual([p[1] for p in pieces], [False, False, True, True, False])
        self.assertEqual(roles(pieces, 2)[0][0], 'lcomment')
        self.assertEqual(roles(pieces, 4)[0][0], 'default')

    def test_T10_matlab_continuation_is_a_comment(self):
        spec = vclang.spec_for('a.m')
        pieces = vclang.lexgen(['x = 1 + ... more'], spec)
        self.assertEqual(roles(pieces, 0)[-1][0], 'comment')

    def test_T11_javascript_words_comment_string_template_block(self):
        spec = vclang.spec_for('a.js')
        code = ['// c', 'const x = "s" + `a', 'b` /* c', 'd */ + 1;', 'this.f(x);']
        pieces = vclang.lexgen(code, spec)
        self.assertEqual(roles(pieces, 0), [('lcomment', '// c')])
        self.assertIn(('keyword', 'const'), roles(pieces, 1))
        self.assertIn(('string', '"s"'), roles(pieces, 1))
        self.assertTrue(pieces[2][0][0][0] == 'string')           # the template runs on
        self.assertTrue(pieces[3][1])                              # line 4 starts inside /* */
        self.assertIn(('number', '1'), roles(pieces, 3))
        self.assertFalse(pieces[4][1])
        self.assertIn(('self', 'this'), roles(pieces, 4))

    def test_T12_javascript_a_url_in_a_comment_is_marked(self):
        spec = vclang.spec_for('a.js')
        pieces = vclang.lexgen(['x(); // see https://x.org TODO'], spec)
        kinds = [r for r, t in pieces[0][0]]
        self.assertIn('url', kinds)
        self.assertIn('marker', kinds)

    def test_T13_css_selector_property_hex_and_block(self):
        spec = vclang.spec_for('a.css')
        code = ['.box #id { color: #fff; margin: 0 4px; }', '/* note', 'more */', '@media x {', '}']
        pieces = vclang.lexgen(code, spec)
        kinds = dict((t, r) for r, t in roles(pieces, 0))
        self.assertEqual(kinds['.box'], 'classname')
        self.assertEqual(kinds['#id'], 'classname')
        self.assertEqual(kinds['color'], 'attribute')
        self.assertEqual(kinds['#fff'], 'number')
        self.assertEqual(kinds['4px'], 'number')
        self.assertTrue(pieces[2][1])
        self.assertEqual(roles(pieces, 3)[0], ('keyword', '@media'))
        self.assertEqual(pieces[4][2], 1)                          # depth at the start of the }

    def test_T14_brackets_are_coloured_by_depth(self):
        spec = vclang.spec_for('a.js')
        pieces = vclang.lexgen(['f((a), [b])'], spec)
        found = [(r, t) for r, t in roles(pieces, 0) if t in '()[]']
        self.assertEqual([r for r, t in found], ['br0', 'br1', 'br1', 'br1', 'br1', 'br0'])

    def test_T15_unbalanced_close_bracket_is_invalid_and_state_recovers(self):
        spec = vclang.spec_for('a.js')
        pieces = vclang.lexgen([')', 'f(x)'], spec)
        self.assertEqual(roles(pieces, 0), [('invalid', ')')])
        self.assertEqual(roles(pieces, 1)[1][0], 'br0')

    # ---- functions --------------------------------------------------------------------------
    def test_T16_matlab_functions_and_classes(self):
        spec = vclang.spec_for('a.m')
        code = ['classdef Thing < handle', 'end', 'function out = first(a, b)', 'out = a;', 'end',
                'function second', 'end', '% function not_this']
        found = vclang.functions(code, spec, vclang.lexgen(code, spec))
        self.assertEqual([(n, f, k) for n, f, l, k in found],
                         [('Thing', 1, 'class'), ('first', 3, 'function'), ('second', 6, 'function')])
        self.assertEqual(found[1][2], 5)                           # ends where the next starts

    def test_T17_javascript_functions_arrows_and_classes(self):
        spec = vclang.spec_for('a.js')
        code = ['function a() {}', 'async function b() {}', 'const c = (x) => x;',
                'let d = function() {};', 'class E {}', 'const notfn = 3;', '/* function hidden() */']
        found = vclang.functions(code, spec, vclang.lexgen(code, spec))
        self.assertEqual([n for n, f, l, k in found], ['a', 'b', 'c', 'd', 'E'])

    def test_T18_css_rules_at_the_left_only(self):
        spec = vclang.spec_for('a.css')
        code = ['.a, .b {', '  color: red;', '}', '@media x {', '  .c {', '  }', '}', 'body {', '}']
        found = vclang.functions(code, spec, vclang.lexgen(code, spec))
        self.assertEqual([n for n, f, l, k in found], ['.a, .b', 'body'])

    def test_T19a_methods_are_named_with_their_class(self):
        spec = vclang.spec_for('a.py')
        code = ['class A:', '    def m(self):', '        pass', '    def n(self):', '        pass',
                'def free():', '    pass', 'class B:', '    def m(self):', '        pass']
        found = vclang.functions(code, spec, vclang.lexgen(code, spec))
        self.assertEqual([n for n, f, l, k in found],
                         ['A', 'A.m', 'A.n', 'free', 'B', 'B.m'])

    def test_T19_text_and_markdown_have_no_functions(self):
        for name in ('a.txt', 'a.md'):
            spec = vclang.spec_for(name)
            self.assertEqual(vclang.functions(['function x()'], spec), [])

    # ---- inside a block ---------------------------------------------------------------------
    def test_T20_inside_block_for_each_kind_of_block(self):
        js = vclang.spec_for('a.js')
        self.assertTrue(vclang.is_inside_block(['/* a', 'b', '*/'], js, 2))
        self.assertFalse(vclang.is_inside_block(['/* a', 'b', '*/'], js, 3 + 1))
        self.assertTrue(vclang.is_inside_block(['`a', 'b`'], js, 2))
        m = vclang.spec_for('a.m')
        self.assertTrue(vclang.is_inside_block(['%{', 'x', '%}'], m, 2))
        self.assertFalse(vclang.is_inside_block(['%{', 'x', '%}'], m, 4))
        self.assertFalse(vclang.is_inside_block(['x'], vclang.spec_for('a.txt'), 1))
        self.assertFalse(vclang.is_inside_block(['x', 'y'], vclang.spec_for('a.py'), 2))

    # ---- .mu as Markdown, VBA ---------------------------------------------------------------
    def test_T21_mu_files_open_as_markdown_and_vba_files_as_code(self):
        self.assertEqual(vclang.kind_of('lang/vba.mu'), 'md')
        self.assertEqual(vclang.spec_for('a.mu').open, '<!--###')
        for name in ('a.vba', 'a.vb', 'a.bas', 'a.cls', 'a.frm', 'A.BAS'):
            self.assertEqual(vclang.kind_of(name), 'code', name)
            self.assertEqual(vclang.spec_for(name).name, 'vba', name)

    def test_T22_vba_comment_is_three_quotes_and_a_plain_quote_is_not_a_review_comment(self):
        spec = vclang.spec_for('a.bas')
        self.assertEqual((spec.open, spec.close), ("'''", ''))
        rx = vclang.comment_regex(spec)
        lines = vclang.comment_lines(spec, '    ', 'flm', 'why?\nbecause')
        self.assertEqual(lines, ["    '''flm why?", "    '''flm because"])
        self.assertTrue(all(rx.match(x) for x in lines))
        for line in ("' note", "'' two", "x = 1 '''flm", "Rem note"):
            self.assertIsNone(rx.match(line), line)
        self.assertTrue(vclang.separator_regex(spec).match("'''"))

    def test_T23_vba_ignores_case_in_words_and_doubles_its_quotes(self):
        spec = vclang.spec_for('a.bas')
        pieces = vclang.lexgen(['DIM x AS Long \' note', 'dim s as string: s = "say ""hi"""',
                                'If Not IsNull(x) Then x = nothing'], spec)
        first = roles(pieces, 0)
        self.assertEqual([t for t in first if t[0] == 'keyword'], [('keyword', 'DIM'), ('keyword', 'AS')])
        self.assertIn(('builtin', 'Long'), first)
        self.assertEqual(first[-1][0], 'comment')
        second = roles(pieces, 1)
        self.assertEqual([t for t in second if t[0] == 'keyword'], [('keyword', 'dim'), ('keyword', 'as')])
        self.assertIn(('string', '"say ""hi"""'), second)
        third = roles(pieces, 2)
        self.assertIn(('keyword', 'If'), third)
        self.assertIn(('builtin', 'IsNull'), third)
        self.assertIn(('kwconst', 'nothing'), third)

    def test_T24_vba_functions_subs_properties_and_types(self):
        spec = vclang.spec_for('a.bas')
        code = ['Option Explicit', 'Public Function Area(w As Long) As Long', '  Area = w', 'End Function',
                'private sub Hide()', '  Exit Sub', 'End Sub', 'Property Get Size() As Long', 'End Property',
                'Public Type Point', '  x As Long', 'End Type', 'Declare Function Beep Lib "k" ()']
        found = vclang.functions(code, spec, vclang.lexgen(code, spec))
        self.assertEqual([(n, k) for n, f, l, k in found],
                         [('Area', 'function'), ('Hide', 'function'), ('Size', 'function'), ('Point', 'class')])

    # ---- text: notes, sections, key: value --------------------------------------------------
    def text(self, *lines):
        spec = vclang.spec_for('a.txt')
        return vclang.lexgen(list(lines), spec)

    def test_T25_text_a_note_line_starts_with_hash_percent_quote_or_semicolon(self):
        pieces = self.text('# whole', '  % indented', "'quoted note", '  ; ini note', 'plain words')
        for row in (0, 1, 2, 3):
            self.assertEqual(roles(pieces, row)[0][0], 'lcomment', row)
        self.assertEqual(roles(pieces, 4)[0][0], 'default')

    def test_T26_text_a_trailing_note_follows_a_space_and_is_followed_by_one(self):
        pieces = self.text('x = 1  # trailing', 'size 5 % of it', 'it is 50% done', "don't stop ; note",
                           'name: "a # b"  # real', 'tag#1 stays', "it's here ' not a note")
        self.assertEqual(roles(pieces, 0)[-1], ('comment', '# trailing'))
        self.assertEqual(roles(pieces, 1)[-1][0], 'comment')           # " % of it" is a note
        self.assertNotIn('comment', [r for r, t in roles(pieces, 2)])
        self.assertEqual(roles(pieces, 3)[-1], ('comment', '; note'))
        self.assertIn(('string', '"a # b"'), roles(pieces, 4))
        self.assertEqual(roles(pieces, 4)[-1], ('comment', '# real'))
        self.assertNotIn('comment', [r for r, t in roles(pieces, 5)])
        self.assertNotIn('comment', [r for r, t in roles(pieces, 6)])  # ' is a note at the front only

    def test_T27_text_keys_values_numbers_constants_sections_and_links(self):
        pieces = self.text('[Section A]', 'Settings:', 'rate = 3.5e-3', 'flag: true', 'name: Bob',
                           '  deep: 12 apples', 'url: https://x.org/a', 'C:\\path\\file', 'ratio==2')
        self.assertEqual(roles(pieces, 0), [('classname', '[Section A]')])
        self.assertEqual(roles(pieces, 1)[0], ('classname', 'Settings'))
        self.assertEqual(roles(pieces, 2), [('annotation', 'rate'), ('punct', '='), ('number', '3.5e-3')])
        self.assertEqual(roles(pieces, 3)[-1], ('kwconst', 'true'))
        self.assertEqual(roles(pieces, 4)[0], ('annotation', 'name'))
        self.assertEqual(roles(pieces, 5)[:2], [('annotation', 'deep'), ('punct', ':')])
        self.assertIn(('number', '12'), roles(pieces, 5))
        self.assertIn(('url', 'https://x.org/a'), roles(pieces, 6))
        self.assertNotIn('annotation', [r for r, t in roles(pieces, 7)])      # a drive letter is not a key
        self.assertNotIn('annotation', [r for r, t in roles(pieces, 8)])      # == is not a key

    def test_T28_text_the_pieces_always_make_up_the_line(self):
        lines = ['', '   ', '\tkey\t=\tvalue  # n', '[a] x', 'a: "open', "it's", '###flm x', '% 5 % 6 %',
                 'k:v:w', 'x = "a" "b" 1 2 true # end', 'é: ü']
        for line, piece in zip(lines, self.text(*lines)):
            self.assertEqual(''.join(t for r, t in piece[0]), line)

    def test_T29_text_sections_and_titles_are_listed_as_functions(self):
        spec = vclang.spec_for('a.txt')
        code = ['[A]', 'k: 1', 'Title:', 'x = 2', '  indented:', '[B]']
        found = vclang.functions(code, spec, vclang.lexgen(code, spec))
        self.assertEqual([n for n, f, l, k in found], ['A', 'Title', 'B'])

    def bench_lexgen_text_1000_lines(self, timer):
        lines = ['[s]', 'key = 12  # n', 'name: "q # r"', '# note', 'plain words 1 2 true'] * 200
        spec = vclang.spec_for('a.txt')
        with timer as test:
            while test.more:
                for _ in test.count:
                    vclang.lexgen(lines, spec)
        return 'lexgen text 1000 lines', 'lexer'

    def bench_lexgen_javascript_2000_lines(self, timer):
        with timer as test:
            spec = vclang.spec_for('a.js')
            while test.more:
                for _ in test.count:
                    vclang.lexgen(self.js, spec)
        return 'lexgen JS 2000 lines', 'lexer'

    def bench_functions_javascript_2000_lines(self, timer):
        with timer as test:
            spec = vclang.spec_for('a.js')
            pieces = vclang.lexgen(self.js, spec)
            while test.more:
                for _ in test.count:
                    vclang.functions(self.js, spec, pieces)
        return 'functions JS 2000 lines', 'lexer'
