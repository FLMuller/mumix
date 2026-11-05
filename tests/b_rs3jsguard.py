r"""b_rs3jsguard.py -- tests and benchmarks for rs3jsguard: what a script of a doc block may say, and what is tried and
refused. The guard is not a proof (its header says why); this is the list of what it is known to stop.

Run from the project root:
    python tools/runbench.py b_rs3jsguard
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

SOURCES = ['rs3jsguard']
sys.path.insert(0, os.path.join(ROOT, 'tools', 'primary', 'rs3'))
from rs3jsguard import check, this_as

CLAUDE = os.path.dirname(ROOT)

ALLOWED_SCRIPTS = {
    'plain code': "var n = 0; function f(a, b){ return a + b; } [1, 2].forEach(function(x){ n += f(x, 1); });",
    'objects and keys': "var o = {a: 1, 'b': 2, c: function(){ return 3; }}; o.c();",
    'regex and division': "var r = /a\\/b[/]/g.test('a/b'); var half = 10 / 2 / 5;",
    'computed with a name, a number, a length': "var a = [1, 2, 3]; var i = 0; a[i]; a[i + 1]; a[a.length - 1]; a[0]; a['0'];",
    'the document is the box': "var e = document.getElementById('x'); var all = document.querySelectorAll('.k');",
    'a prototype read': "var s = Array.prototype.slice.call(document.querySelectorAll('x'));",
    'innerHTML of a plain literal': "var d = document.createElement('div'); d.innerHTML = '<b>x</b>';",
    'reading innerHTML': "var d = document.createElement('div'); var t = d.innerHTML;",
    'storage and location': "var k = localStorage.getItem('a'); var p = location.pathname; localStorage.setItem('a', JSON.stringify([1]));",
    'a timer with a function': "setTimeout(function(){ console.log(1); }, 10);",
    'try and catch': "try { JSON.parse('1'); } catch (e) { console.log(e.message); }",
    'for in': "var o = {a: 1}; for (var key in o) { o[key]; }",
    'the event listener of the box': "document.addEventListener('DOMContentLoaded', function(){ var n = 1; });",
}

REFUSED_SCRIPTS = {                  # script: a word the message holds
    'this': ("var f = function(){ return this; };", 'this is not allowed'),
    'an arrow function': ("var f = (x) => x;", 'arrow functions'),
    'the parent of the window': ("window.parent.document.body;", '.parent is not allowed'),
    'a name outside': ("fetch('/x');", 'the name fetch'),
    'XMLHttpRequest': ("new XMLHttpRequest();", 'the name XMLHttpRequest'),
    'WebSocket': ("new WebSocket('ws://x');", 'the name WebSocket'),
    'globalThis': ("globalThis.x = 1;", 'the name globalThis'),
    'self': ("self.x = 1;", 'the name self'),
    'top': ("top.location = 'x';", 'the name top'),
    'eval': ("eval('1');", 'eval is not allowed'),
    'Function': ("new Function('return 1')();", 'the name Function'),
    'constructor': ("var o = {}; o.constructor('return window')();", '.constructor is not allowed'),
    'constructor by a function': ("var f = function(){}; f.constructor('return window')();", '.constructor is not allowed'),
    '__proto__': ("var o = {}; o.__proto__.x = 1;", '.__proto__ is not allowed'),
    'a name joined at run time': ("var o = {}; o['con' + 'structor'];", '[ ]'),
    'a banned name as a string': ("var o = {}; o['constructor'];", '[ ]'),
    'getPrototypeOf': ("Object.getPrototypeOf(function(){}).x = 1;", '.getPrototypeOf is not allowed'),
    'defineProperty': ("Object.defineProperty({}, 'a', {});", '.defineProperty is not allowed'),
    'the parent node': ("var e = document.querySelector('x'); e.parentNode.removeChild(e);", '.parentNode is not allowed'),
    'the owner document': ("var e = document.querySelector('x'); e.ownerDocument.body;", '.ownerDocument is not allowed'),
    'the default view': ("var e = document.querySelector('x'); e.ownerDocument.defaultView;", '.ownerDocument is not allowed'),
    'closest': ("var e = document.querySelector('x'); e.closest('div');", '.closest is not allowed'),
    'the offset parent': ("var e = document.querySelector('x'); e.offsetParent;", '.offsetParent is not allowed'),
    'outerHTML': ("var e = document.querySelector('x'); e.outerHTML = '<b>';", '.outerHTML is not allowed'),
    'innerHTML of a variable': ("var d = document.createElement('div'); var h = 'x'; d.innerHTML = h;", '.innerHTML is assigned only'),
    'innerHTML with a joined string': ("var d = document.createElement('div'); d.innerHTML = '<b>' + 'x';", '.innerHTML is assigned only'),
    'innerHTML with a handler': ("var d = document.createElement('div'); d.innerHTML = '<img onerror=alert(1)>';", '.innerHTML is assigned only'),
    'innerHTML with a script': ("var d = document.createElement('div'); d.innerHTML = '<script>x</script>';", '.innerHTML is assigned only'),
    'insertAdjacentHTML': ("var d = document.createElement('div'); d.insertAdjacentHTML('beforeend', 'x');", '.insertAdjacentHTML is not allowed'),
    'document.write': ("document.write('x');", '.write is not allowed'),
    'setAttribute of a handler': ("var e = document.createElement('a'); e.setAttribute('onclick', 'x()');", 'setAttribute of an on'),
    'a string timer': ("setTimeout('x()', 1);", 'takes a function'),
    'a template with code': ("var s = `a${1}`;", 'template literal'),
    'a prototype assigned': ("Array.prototype.foo = 1;", 'assigning through .prototype'),
    'a prototype assigned deeper': ("Array.prototype.slice.foo = 1;", 'assigning through .prototype'),
    'with': ("with (document) { x; }", 'with is not allowed'),
    'class': ("class A {}", 'class is not allowed'),
    'import': ("import('x');", 'import is not allowed'),
    'destructuring': ("var {a} = {a: 1};", 'destructuring'),
    'a getter': ("var o = { get x(){ return 1; } };", 'accessors'),
    'arguments': ("function f(){ return arguments.callee; }", 'arguments is not allowed'),
    'alert': ("alert(1);", 'the name alert'),
    'Reflect': ("Reflect.ownKeys({});", 'the name Reflect'),
    'Proxy': ("new Proxy({}, {});", 'the name Proxy'),
    'an undeclared name': ("undeclared = 1;", 'the name undeclared'),
}


class b_rs3jsguard(bench):
    BenchName = 'rs3jsguard'
    BenchVersion = 'M1.0.1'          # runbench adds 1 to the last number on every run
    BenchHeader = 'what a script of a doc block may say, and what is tried and refused'
    sources = SOURCES

    def test_T1_these_scripts_are_inside_the_subset(self):
        for what, script in ALLOWED_SCRIPTS.items():
            self.assertEqual(check(script), [], what)

    def test_T2_each_of_these_is_refused_with_a_message_that_says_why(self):
        for what, (script, why) in REFUSED_SCRIPTS.items():
            found = check(script)
            self.assertTrue(found, what)
            self.assertTrue(any(why in message for message in found), f'{what}: {found}')

    def test_T3_a_message_names_the_line(self):
        found = check('var a = 1;\nvar b = 2;\nfetch("x");\n')
        self.assertEqual(found, ['line 3: the name fetch is not one this script declares or may use'])

    def test_T4_words_inside_strings_and_comments_are_not_code(self):
        script = "var s = 'this is eval and window.parent'; // this eval\n/* fetch(x) */ var t = \"constructor\";"
        self.assertEqual(check(script), [])

    def test_T5_the_names_a_script_declares_are_its_own(self):
        self.assertEqual(check('function go(a, b){ var c = a; return c + b; } go(1, 2);'), [])
        self.assertEqual(check('var a = 1, b = 2; a + b;'), [])
        self.assertTrue(check('var a = 1; a + c;'))
        self.assertEqual(check('try { 1; } catch (err) { err.message; }'), [])
        self.assertEqual(check('var o = {k: 1, v: [2]}; o.k + o.v[0];'), [])

    def test_T6_inline_handlers_are_checked_with_the_scripts_names_and_event(self):
        script = 'function go(v){ var n = v; }'
        self.assertEqual(check(script, ['go(aThis.value)', 'go(event.target.value)', 'go(this.value)']), [])
        found = check(script, ['go(this.parentNode)'])
        self.assertTrue(any('handler 1' in m and '.parentNode' in m for m in found), found)
        found = check(script, ['nope()'])
        self.assertTrue(any('handler 1' in m and 'nope' in m for m in found), found)

    def test_T7_this_as_writes_this_as_athis_but_not_inside_a_string_or_a_property(self):
        self.assertEqual(this_as("f(this.value, 'this', a.this, \"this\") // this"), "f(aThis.value, 'this', a.this, \"this\") // this")

    def test_T8_the_report_pages_of_this_project_that_hold_a_small_script_are_inside_the_subset(self):
        path = os.path.join(CLAUDE, 'code.py', 'results', 'b_str2int.html')
        if not os.path.isfile(path):
            self.skipTest('no such report here')
        import html
        import re
        text = open(path, encoding='utf-8').read()
        scripts = [m.group(1) for m in re.finditer(r'<script\b(?![^>]*\bsrc\s*=)[^>]*>(.*?)</script\s*>', text, re.S | re.I)]
        handlers = [html.unescape(m.group(2) if m.group(2) is not None else m.group(3))
                    for m in re.finditer(r'''\son([a-z]+)\s*=\s*(?:"([^"]*)"|'([^']*)')''', text)]
        self.assertEqual(check('\n'.join(scripts), handlers), [])

    def bench_check_a_small_report_script(self, timer):
        script = ALLOWED_SCRIPTS['plain code'] * 40
        with timer as test:
            while test.more:
                for _ in test.count:
                    check(script)
        return f'check of {len(script)} characters of script', 'guard'
