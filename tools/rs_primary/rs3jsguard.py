r"""rs3jsguard.py -- what a script of a doc block may say: one function.

    check(script, handlers=()) -> [message, ...]     [] when the script (and the code of its inline handlers) is
                                                      inside the subset; else one message for each fault, with the line
    this_as(code) -> str                              a handler's code with `this` written aThis (see below)

A doc block (pane_doc) runs the script of a page it was given. The script is made safe in two layers. This is the first:
the script is read, as tokens, and refused unless it keeps to a small subset of JavaScript. The second layer is the run
time (pane_doc.js): the script runs inside a function whose names document, window, location and localStorage are the
box's own restricted objects (aDOM is the box), and whose names for the rest of the page's world are undefined.

The subset (ADsafe's way: say nothing the checker cannot follow)
    names        every name the script uses must be one it declares (var, let, const, function, a parameter, catch) or
                 be on ALLOWED (document, window, location, localStorage, JSON, Math, Date, Array, Object, String, Number,
                 Boolean, Set, Map, RegExp, Error, console, parseInt, parseFloat, isNaN, isFinite, encodeURIComponent,
                 decodeURIComponent, setTimeout, clearTimeout, setInterval, clearInterval, undefined, NaN, Infinity).
                 So window.parent is not written as parent, and fetch, eval, Function, XMLHttpRequest, WebSocket, Reflect,
                 Proxy, globalThis, self, top are not names the script may use.
    banned words this, with, class, super, yield, async, await, import, export, debugger, get and set accessors, arrow
                 functions (=>), template literals with ${ }, regular `new Function`.
    members      a.b is allowed unless b is on BAN_MEMBERS (innerHTML is read freely and assigned only a plain literal): constructor, __proto__ and every name that begins and ends with
                 __, the ways out of the box (parentNode, parentElement, ownerDocument, defaultView, getRootNode, closest,
                 offsetParent, contentWindow, contentDocument, opener, top, parent, frames) and the ways to run text as code
                 or markup (outerHTML, insertAdjacentHTML, srcdoc, write, writeln, createContextualFragment,
                 getPrototypeOf, setPrototypeOf, defineProperty, defineProperties, getOwnPropertyDescriptor(s),
                 setAttribute with an on... name, eval).
    a[b]         allowed when b is one number, one string that is not a banned name, one name, or names and numbers with
                 + - * / %; anything else (a string joined at run time could spell constructor) is refused.
    prototypes   .prototype is read, never assigned through (Array.prototype.foo = ... would change the page's Array).
    timers       setTimeout and setInterval take a function, never a string.
The names that stay out of ALLOWED and the members in BAN_MEMBERS are the whole of the wall; the list is short on purpose,
and a script that needs more says so (the error) and is read by a person.

Inline handlers. onclick="selTab('x')" in the html of a doc is a script too: pane_doc turns each into a function of the box,
and checks its code here, with the names of the script it goes with and `event`. `this` in such code is the element: this_as
writes it aThis, a parameter the box passes (the element), so it is the one place `this` is understood.

This is a guard against a page written without care, and a refusal that says why for one written with it. It is not a
proof against a script written to get out: JavaScript is too large a language for a checker this size. A sandboxed iframe
would be the wall; tests/b_rs3jsguard.py lists what is tried and refused.

VERSION  M1 m01.v01 (2026-11-04): first version.
"""
import re

__all__ = ['check', 'this_as']

KEYWORDS = {'var', 'let', 'const', 'function', 'return', 'if', 'else', 'for', 'while', 'do', 'break', 'continue',
            'switch', 'case', 'default', 'new', 'typeof', 'instanceof', 'in', 'of', 'delete', 'void', 'try', 'catch',
            'finally', 'throw', 'null', 'true', 'false'}
BANNED_WORDS = {'this': 'this', 'with': 'with', 'class': 'class', 'super': 'super', 'yield': 'yield', 'async': 'async',
                'await': 'await', 'import': 'import', 'export': 'export', 'debugger': 'debugger', 'extends': 'extends',
                'eval': 'eval', 'arguments': 'arguments'}
ALLOWED = {'document', 'window', 'location', 'localStorage', 'JSON', 'Math', 'Date', 'Array', 'Object', 'String',
           'Number', 'Boolean', 'Set', 'Map', 'RegExp', 'Error', 'console', 'parseInt', 'parseFloat', 'isNaN',
           'isFinite', 'encodeURIComponent', 'decodeURIComponent', 'setTimeout', 'clearTimeout', 'setInterval',
           'clearInterval', 'undefined', 'NaN', 'Infinity'}
BAN_MEMBERS = {'constructor', 'parentNode', 'parentElement', 'ownerDocument', 'defaultView', 'getRootNode', 'closest',
               'offsetParent', 'contentWindow', 'contentDocument', 'opener', 'top', 'parent', 'frames',
               'outerHTML', 'insertAdjacentHTML', 'srcdoc', 'write', 'writeln', 'createContextualFragment',
               'getPrototypeOf', 'setPrototypeOf', 'defineProperty', 'defineProperties', 'getOwnPropertyDescriptor',
               'getOwnPropertyDescriptors', 'eval', 'globalThis', 'self', 'caller', 'callee'}
UNSAFE_MARKUP = re.compile(r'<\s*(?:script|iframe|object|embed|link|meta|base|style)|\son\w+\s*=|javascript:|srcdoc', re.I)
ASSIGN = {'=', '+=', '-=', '*=', '/=', '%=', '**=', '<<=', '>>=', '>>>=', '&=', '|=', '^=', '&&=', '||=', '??='}
PUNCT = ['>>>=', '...', '===', '!==', '**=', '<<=', '>>=', '>>>', '&&=', '||=', '??=', '=>', '==', '!=', '<=', '>=', '&&',
         '||', '??', '?.', '++', '--', '+=', '-=', '*=', '/=', '%=', '&=', '|=', '^=', '**', '<<', '>>']
IDENT = re.compile(r'[A-Za-z_$][\w$]*')
NUMBER = re.compile(r'0[xX][0-9a-fA-F]+|\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?')
REGEX_AFTER = {'(', ',', '=', ':', '[', '!', '&', '|', '?', '{', '}', ';', '+', '-', '*', '%', '<', '>', '~', '^'}
KEYWORD_BEFORE_REGEX = {'return', 'typeof', 'case', 'delete', 'void', 'in', 'of', 'else', 'do', 'new', 'throw'}


def tokens(text):
    """[(kind, text, line)] of a script: kind is ident, num, str, tmpl, regex or punct. Comments are left out."""
    out, i, n, line = [], 0, len(text), 1
    while i < n:
        c = text[i]
        if c == '\n':
            line += 1
            i += 1
        elif c in ' \t\r\f\v﻿ ':
            i += 1
        elif text.startswith('//', i):
            j = text.find('\n', i)
            i = n if j < 0 else j
        elif text.startswith('/*', i):
            j = text.find('*/', i + 2)
            j = n if j < 0 else j + 2
            line += text.count('\n', i, j)
            i = j
        elif c in '"\'':
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == '\\' else 1
                if j < n and text[j] == '\n':
                    break
            out.append(('str', text[i:j + 1], line))
            line += text.count('\n', i, j + 1)
            i = j + 1
        elif c == '`':
            j = i + 1
            while j < n and text[j] != '`':
                j += 2 if text[j] == '\\' else 1
            out.append(('tmpl', text[i:j + 1], line))
            line += text.count('\n', i, j + 1)
            i = j + 1
        elif c == '/' and regex_ok(out):
            j, in_class = i + 1, False
            while j < n and (text[j] != '/' or in_class) and text[j] != '\n':
                if text[j] == '\\':
                    j += 1
                elif text[j] == '[':
                    in_class = True
                elif text[j] == ']':
                    in_class = False
                j += 1
            j += 1
            while j < n and (text[j].isalpha()):
                j += 1
            out.append(('regex', text[i:j], line))
            i = j
        elif c.isdigit() or (c == '.' and i + 1 < n and text[i + 1].isdigit()):
            m = NUMBER.match(text, i)
            out.append(('num', m.group(0), line))
            i = m.end()
        elif c.isalpha() or c in '_$' or ord(c) > 127:
            m = IDENT.match(text, i)
            if m is None:
                m = re.compile(r'\w+').match(text, i)
            out.append(('ident', m.group(0), line))
            i = m.end()
        else:
            for p in PUNCT:
                if text.startswith(p, i):
                    out.append(('punct', p, line))
                    i += len(p)
                    break
            else:
                out.append(('punct', c, line))
                i += 1
    return out


def regex_ok(out):
    """May a / start a regular expression here? It may after an operator or an opening bracket or a keyword."""
    if not out:
        return True
    kind, text, _ = out[-1]
    if kind == 'punct':
        return text in REGEX_AFTER or text in ASSIGN or text in ('&&', '||', '??', '==', '===', '!=', '!==', '=>')
    return kind == 'ident' and text in KEYWORD_BEFORE_REGEX


def declared(tokens_):
    """The names a token list declares: var/let/const names, function names and parameters, catch parameters."""
    names, errors = set(), []
    depth, stack = 0, []
    decl = None                                     # the bracket depth of a var/let/const list being read
    expect = False
    i, n = 0, len(tokens_)
    while i < n:
        kind, text, line = tokens_[i]
        if kind == 'punct':
            if text in '([{':
                depth += 1
            elif text in ')]}':
                depth -= 1
            elif text == ';' and decl is not None and depth <= decl:
                decl, expect = None, False
            elif text == ',' and decl is not None and depth == decl:
                expect = True
            elif text == '=' and decl is not None and depth == decl:
                expect = False
            elif text in ('{', '[') and expect:
                errors.append(f'line {line}: destructuring is not allowed')
        if kind == 'ident':
            if text in ('var', 'let', 'const'):
                decl, expect = depth, True
                if i + 1 < n and tokens_[i + 1][1] in ('{', '['):
                    errors.append(f'line {line}: destructuring is not allowed')
            elif expect and decl is not None and depth == decl:
                names.add(text)
                expect = False
            elif text == 'function':
                j = i + 1
                if j < n and tokens_[j][0] == 'ident':
                    names.add(tokens_[j][1])
                    j += 1
                if j < n and tokens_[j][1] == '(':
                    j += 1
                    level, want = 0, True
                    while j < n and not (tokens_[j][1] == ')' and level == 0):
                        t = tokens_[j][1]
                        if t in '([{':
                            level += 1
                        elif t in ')]}':
                            level -= 1
                        elif t == ',' and level == 0:
                            want = True
                        elif t == '=' and level == 0:
                            want = False
                        elif tokens_[j][0] == 'ident' and want and level == 0:
                            names.add(t)
                            want = False
                        j += 1
            elif text == 'catch' and i + 2 < n and tokens_[i + 1][1] == '(' and tokens_[i + 2][0] == 'ident':
                names.add(tokens_[i + 2][1])
            elif text in ('for',) and i + 3 < n and tokens_[i + 1][1] == '(' and tokens_[i + 2][1] in ('var', 'let', 'const'):
                pass                                # the var inside is read as any var
        i += 1
    return names, errors


def faults(tokens_, known):
    """The faults of a token list, given the names known to it."""
    out = []
    n = len(tokens_)
    for i, (kind, text, line) in enumerate(tokens_):
        prev = tokens_[i - 1] if i else ('', '', 0)
        nxt = tokens_[i + 1] if i + 1 < n else ('', '', 0)
        after_dot = prev[1] in ('.', '?.')
        if kind == 'punct' and text == '=>':
            out.append(f'line {line}: arrow functions are not allowed (write function(){{}})')
        elif kind == 'tmpl' and '${' in text:
            out.append(f'line {line}: a template literal with ${{ }} is not allowed')
        elif kind == 'ident' and after_dot:
            if text in BAN_MEMBERS or (text.startswith('__') and text.endswith('__')):
                out.append(f'line {line}: .{text} is not allowed')
            elif text == 'innerHTML' and nxt[1] in ('=', '+='):
                value = tokens_[i + 2] if i + 2 < n else ('', '', 0)
                after = tokens_[i + 3][1] if i + 3 < n else ';'
                if value[0] != 'str' or after in ('+', '.', '[') or UNSAFE_MARKUP.search(value[1]):
                    out.append(f'line {line}: .innerHTML is assigned only a plain literal of markup (no script, no on... handler)')
            elif text == 'setAttribute' and nxt[1] == '(' and i + 2 < n and tokens_[i + 2][0] == 'str' \
                    and re.match(r'''['"]on''', tokens_[i + 2][1], re.I):
                out.append(f'line {line}: setAttribute of an on... handler is not allowed')
            elif text == 'prototype':
                j = i + 1                           # .prototype.a.b = ... assigns through a prototype
                while j + 1 < n and tokens_[j][1] == '.' and tokens_[j + 1][0] == 'ident':
                    j += 2
                if j < n and tokens_[j][1] in ASSIGN:
                    out.append(f'line {line}: assigning through .prototype is not allowed')
        elif kind == 'ident':
            if text in BANNED_WORDS and not (nxt[1] == ':' and prev[1] in ('{', ',')):
                out.append(f'line {line}: {text} is not allowed')
            elif text in KEYWORDS or text in known or text in ALLOWED:
                pass
            elif nxt[1] == ':' and prev[1] in ('{', ',', ';'):
                pass                                # an object key or a label
            elif text in ('get', 'set') and nxt[0] == 'ident':
                out.append(f'line {line}: accessors ({text}) are not allowed')
            else:
                out.append(f'line {line}: the name {text} is not one this script declares or may use')
            if text in ('setTimeout', 'setInterval') and nxt[1] == '(' and i + 2 < n and tokens_[i + 2][0] in ('str', 'tmpl'):
                out.append(f'line {line}: {text} takes a function, not text')
        elif kind == 'punct' and text == '[' and prev[0] in ('ident', 'str', 'num') or (kind == 'punct' and text == '['
                                                                                        and prev[1] in (')', ']')):
            if prev[0] == 'ident' and prev[1] in KEYWORDS:
                continue                            # an array literal after return, in, of ...
            j, level, body = i + 1, 1, []
            while j < n and level:
                if tokens_[j][1] == '[':
                    level += 1
                elif tokens_[j][1] == ']':
                    level -= 1
                    if not level:
                        break
                body.append(tokens_[j])
                j += 1
            if not subscript_ok(body, known):
                out.append(f'line {line}: [ ] with anything but a number, a name or a literal is not allowed')
    return out


def subscript_ok(body, known):
    if not body:
        return False
    if len(body) == 1:
        kind, text, _ = body[0]
        if kind == 'num':
            return True
        if kind == 'str':
            name = text[1:-1]
            return name not in BAN_MEMBERS and not (name.startswith('__') and name.endswith('__'))
        return kind == 'ident' and (text in known or text in ALLOWED)
    for k, (kind, text, _) in enumerate(body):
        if kind == 'num' or (kind == 'punct' and text in ('+', '-', '*', '/', '%', '(', ')', '.')):
            continue
        after_dot = k > 0 and body[k - 1][1] == '.'
        if kind == 'ident' and after_dot and text not in BAN_MEMBERS and not text.startswith('__'):
            continue                                # v[v.length - 1]
        if kind == 'ident' and (text in known or text in ALLOWED) and text not in BAN_MEMBERS:
            continue
        return False
    return True


def this_as(code):
    """A handler's code with every `this` (the token, not the word in a string) written aThis."""
    result, i, n = [], 0, len(code)
    while i < n:
        c = code[i]
        if c in '"\'`':
            j = i + 1
            while j < n and code[j] != c:
                j += 2 if code[j] == '\\' else 1
            result.append(code[i:j + 1])
            i = j + 1
        elif code.startswith('//', i) or code.startswith('/*', i):
            end = code.find('\n' if code[i + 1] == '/' else '*/', i)
            j = n if end < 0 else end + (0 if code[i + 1] == '/' else 2)
            result.append(code[i:j])
            i = j
        elif c.isalpha() or c in '_$':
            m = IDENT.match(code, i)
            word = m.group(0)
            before = code[:i].rstrip()
            result.append('aThis' if word == 'this' and not before.endswith('.') else word)
            i = m.end()
        else:
            result.append(c)
            i += 1
    return ''.join(result)


def check(script, handlers=()):
    """See the module header: the faults of a script and of the code of its inline handlers."""
    main = tokens(script)
    known, errors = declared(main)
    out = list(errors) + faults(main, known)
    for k, code in enumerate(handlers):
        body = tokens(this_as(code))
        names, errs = declared(body)
        out += [f'handler {k + 1}: {e}' for e in errs]
        out += [f'handler {k + 1}: {e}' for e in faults(body, known | names | {'event', 'aThis'})]
    return out
