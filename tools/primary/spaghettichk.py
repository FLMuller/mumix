r"""spaghettichk.py -- how tangled, hidden and untested the code of a file is, as a pie of four verdicts.

    colour = isspaghetti(source, area='', testarea='')

    source    a Source of rs3lex (the file, read once and kept by the server's process); its facts() are what is judged
    area      a wildcard of the files that may use it (rs3util.pathof: './mumix/tools/primary/rs3/*.py'); the files of the
              same folder in the way rs3comment calls it
    testarea  a wildcard of the suites ('./mumix/tests/b_*.py'); a suite of a file is b_<its name>.py
    colour    a str, the band: 'green', '' (grey, the middle), 'orange' or 'red'; '' too for a file that is not Python. It
              carries colour.why (the reasons), colour.pie (percent of green, grey, orange, red, summing to 100),
              colour.score (green + half the grey, 0 to 100), colour.dot (the proof dot of an item in __all__, '' for the
              others: 'red' no suite names it, 'orange' some of it is named, 'grey' all named but the functions under it
              are not shown to be reached, 'green' all named and nothing under it left unreached)
              and colour.rows {first line of a function or class: its own colour}: the colour of the file is the colour of
              the file-level rules, and its rows are the items.

How it judges (one pass, three stages): the facts of the file and of its neighbours are read from the Source cache (a changed
file is read again by Source, so a renewed file is judged anew); every rule of ROWS (for each function and class) and FILES
(for the file) looks at the facts and gives a verdict, green, grey, orange or red, or none when it does not apply; the grade
adds the weights of the rules by verdict, scales them to 100 (the pie) and chooses the band: red when the red share is 15% or
more, or a rule marked force says red; else orange when orange and red make 35% or more; else green at 50% or more; else
grey. Every leading-underscore name of a class (not a dunder, not the backing name of a property) adds 1% of red to that
class, at most 25%. The weights, the limits and the bands are the workbook spaghettichk_rules_v4.xlsx, which says what each
rule means and which are not built.

A rule that finds nothing wrong (getattr, readsrc, rewire, tripwire, poke) gives no verdict instead of a green one: it is
not an achievement, and counting it would dilute every pie with green.

Built: tested, callers, usage, getattr, readsrc, rewire, tripwire, tangle, local, duplication (a signature twin), docs, classdata,
poke (a private member of another object), allsize, imports, foreign, suitepeek, locals, header (names and VERSION lines).
Not built: a body that matches another, the orange dot for functions no test run executed, the data attribute of a class read
from outside, the constants hygiene of header.

VERSION  M1 m01.v02 (2026-11-04): constants and the __all__ line have a pie of their own; a file with no __all__ gets a red note row (key 0); the proof dot has four colours.
         M1 m01.v01 (2026-11-04): first version.
"""
import os
import re
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # tools/: the one use.py
from use import load

pathof = load('rs3util', into={})['pathof']

__all__ = ['isspaghetti']

BANDS = {'red': 15, 'orange': 35, 'green': 50, 'grey': 0.5, 'private': 1, 'cap': 25}
KINDS = ('green', 'grey', 'orange', 'red')
REASON = re.compile(r'\b(because|so that|why|instead|since|in order to|to avoid|chosen|rationale|rather than)\b', re.I)
TRIPWIRE = re.compile(r'shim|compat|legacy|wrapper|hack|adapter|patch|_old$|_new$', re.I)
NUMBERED = re.compile(r'^(.+?)_?\d+$')                        # foo2 and foo_2 say a second foo: a tripwire when a foo is in the file
VERSION = re.compile(r'^\s*VERSION\s+M\d+\s+m\d+\.v\d+\s+\(\d{4}-\d\d-\d\d\)', re.M)
HEADER = re.compile(r'\s*(?:#[^\n]*\n\s*)*[rRuU]?("""|\'\'\')(.*?)\1', re.S)
SELF = {'self', 'me', 'cls'}
REFLECT = {'getattr', 'setattr', 'delattr', 'hasattr'}
READS = ('eval', 'exec', '__import__', 'ast.parse', 'inspect.getsource', 'importlib.')
PLAIN = {'NamedTuple', 'Enum', 'TypedDict', 'IntEnum', 'Flag'}
CALLED = re.compile(r'^(test_|bench_|setUp|tearDown|setup_fixtures|main$)')      # names a framework calls: no caller in the code


class Colour(str):
    """The band of an item. The pie, the score, the dot, the reasons and (for a file) the colours of its rows ride along."""

    def __new__(cls, band, why=(), pie=(0, 0, 0, 0), score=0.0, dot='', rows=None):
        me = str.__new__(cls, band)
        me.why = list(why)
        me.pie = tuple(pie)
        me.score = score
        me.dot = dot
        me.rows = rows or {}
        return me


def ladder(n, cuts):
    """green, grey, orange or red by how many cuts n has passed: cuts are the last values of green, grey and orange."""
    return KINDS[sum(1 for cut in cuts if n > cut)]


def private(name):
    return name.startswith('_') and not (name.startswith('__') and name.endswith('__'))


def sources(expr, reader):
    """The Sources of the files a wildcard names (unreadable and unknown kinds are left out)."""
    out = []
    for short in (pathof(expr) if expr else []):
        try:
            out.append(reader.read(pathof(short)))
        except (OSError, ValueError, TypeError):
            pass
    return out


def summary(src):
    """What the rules read of one file, found once from its facts and kept with the Source: per def its metrics, per file the
    words, the exports and the imports. None when the file is not Python."""
    facts = src.facts()
    if facts is None:
        return None
    stem = os.path.splitext(os.path.basename(src.real))[0]
    items = [SimpleNamespace(d=d, branch=0, depth=0, glob=False, calls=[], dots=[], sets=[], excepts=[], returns=[])
             for d in facts.defs]
    for n, line in facts.lines.items():
        at = facts.scope[n] if n < len(facts.scope) else -1
        while at != -1:
            it = items[at]
            it.branch += line.get('branch', 0)
            it.glob = it.glob or line.get('global', False)
            it.calls += line.get('calls', [])
            it.dots += line.get('dots', [])
            if 'sets' in line:
                it.sets.append(line['sets'])
            it.excepts += line.get('except', [])
            if 'returns' in line:
                it.returns.append(tuple(line['returns']))
            if 'block' in line:
                it.depth = max(it.depth, (facts.indent[n - 1] - it.d.indent) // 4)
            at = it.d.parent
    exports = set(facts.exports) if facts.exports is not None else None
    return SimpleNamespace(src=src, stem=stem, facts=facts, items=items, exports=exports, words=facts.words,
                           aliases={clause[2] for clause in facts.imports if clause[2]},
                           text=src.text)


def exposure(me):
    """The set of line numbers of the items that are in __all__: a top-level function or class by name, a public method of one."""
    out = set()
    if me.exports is None:
        return out
    for it in me.items:
        d = it.d
        if d.parent == -1 and d.name in me.exports:
            out.add(d.first)
        elif d.owner and d.parent != -1 and me.items[d.parent].d.first in out and not d.name.startswith('_'):
            out.add(d.first)
    return out


def proof(c, it):
    """The proof dot of an item in __all__: red when no suite names it (or there is no suite), orange when only some of it is
    named (a class and its public methods), grey when all is named but it has local functions under it whose reach no test
    run has shown, green when all is named and nothing is under it. The reach of the functions under an item (a call
    closure over the local functions of the file) waits for a traced test run: until then it is grey."""
    me, d = c.me, it.d
    group = [it]
    if d.kind == 'class':
        group += [x for x in me.items if x.d.parent == me.items.index(it) and x.d.first in c.exposed]
    named = [any(re.search(r'\b' + re.escape(x.d.name) + r'\b', s.text) for s in c.suites) for x in group]
    if not any(named):
        return 'red'
    if not all(named):
        return 'orange'
    local = {x.d.name: x for x in me.items if x.d.first not in c.exposed and x.d.kind == 'def'}
    seen, todo = set(), [it]
    while todo:
        for call in todo.pop().calls:
            name = call[0].rsplit('.', 1)[-1]
            if name in local and name not in seen and local[name] is not it:
                seen.add(name)
                todo.append(local[name])
    return 'grey' if seen else 'green'


def verdicts_row(c, it, exposed):
    """[(id, weight, force, verdict, reason)] of the rules that apply to one function or class."""
    d, got = it.d, []
    suite = c.me.stem.startswith('b_')

    def add(rule, weight, verdict, reason, force=False):
        if verdict:
            got.append((rule, weight, force and verdict == 'red', verdict, reason))
    size, klass = d.last - d.first + 1, d.kind == 'class'
    others = sum(1 for s in c.sibs if s.words.get(d.name, 0))
    uses = c.me.words.get(d.name, 0)
    if exposed:
        if c.suites:
            named = any(re.search(r'\b' + re.escape(d.name) + r'\b', s.text) for s in c.suites)
            add('tested', 5, 'green' if named else 'orange', 'a suite names it' if named else 'a suite exists, none names it')
        if c.sibs or c.area:
            verdict = ('green' if others >= 3 else 'grey' if others == 2 or (others == 1 and uses) else 'orange' if uses or others
                       else 'red')
            add('callers', 3, verdict, f'{others} other module(s) and {uses} own use(s)', True)
    elif not d.name.startswith('__') and not klass and not suite and not CALLED.match(d.name):
        uses += others if d.owner and not d.name.startswith('_') else 0          # a public method may be called from another file
        add('usage', 3, 'green' if uses > 2 else 'grey' if uses == 2 else 'orange' if uses == 1 else 'red',
            f'used {uses} time(s)', True)
    me = d.params[0] if d.params else ''
    reflect = [call for call in it.calls if call[0] in REFLECT]
    if reflect:
        mine = all(call[1] in SELF or call[1] == me for call in reflect)
        add('getattr', 6, 'orange' if mine else 'red', 'getattr/setattr on ' + ('me/self' if mine else 'another object'), True)
    reads = [call[0] for call in it.calls if call[0] in READS or call[0].startswith(READS[3:])]
    if reads:
        add('readsrc', 3, 'red', 'reads or parses code: ' + ', '.join(reads[:3]))
    wired = 'ImportError' in it.excepts or 'ModuleNotFoundError' in it.excepts or any(obj in c.me.aliases for obj, attr in it.sets)
    if wired:
        add('rewire', 3, 'red', 'an ImportError fallback or an imported module patched')
    twin = NUMBERED.match(d.name)
    if TRIPWIRE.search(d.name) or (twin and twin.group(1) in c.names):
        add('tripwire', 2, 'red', 'a name that says fix')
    if not klass:
        complexity = 1 + it.branch
        passed = (complexity > 10) + (it.depth > 4) + (size > 80) + it.glob
        add('tangle', 4, 'red' if passed > 2 or complexity > 15 else ladder(passed, (0, 1, 2)),
            f'complexity {complexity}, nesting {it.depth}, {size} lines')
    if not exposed and not klass and not suite:
        by_size = 'green' if size >= 12 else 'grey' if size >= 5 else 'orange' if size >= 2 else 'red'
        if private(d.name):
            by_size = {'green': 'grey', 'grey': 'orange'}.get(by_size, by_size)
        add('local', 2, by_size, f'{size} lines' + (', an underscore name' if private(d.name) else ''))
    if c.sibs or c.area:
        twin = [other for other in c.twins.get(c.key(it), []) if other is not it]
        if c.key(it)[0] and twin:
            add('duplication', 4, 'orange', 'the same parameters and returned names as ' + twin[0].d.name)
        elif not twin:
            add('duplication', 4, 'green', 'no signature twin')
    if (exposed or klass) and not suite:
        add('docs', 3, 'red' if not d.docs else 'orange' if d.docs > 60 else 'green' if d.docs >= 3 and REASON.search(d.doc) else 'grey',
            'no docstring' if not d.docs else f'{d.docs} docstring line(s)')
    pokes = [(obj, attr) for obj, attr in it.dots if private(attr) and obj not in SELF and obj != me]
    if pokes:
        add('poke', 3, 'red', f'reaches {pokes[0][0]}.{pokes[0][1]}')
    return got


def class_notes(c, it):
    """(verdicts of the class data rule, how many private names, why) for a class row."""
    d = it.d
    members = [x for x in c.me.items if x.d.parent == c.me.items.index(it)]
    props = {x.d.name for x in members if 'property' in x.d.decorators}
    me = {x.d.params[0] for x in members if x.d.params}
    attrs = {attr for x in members for obj, attr in x.sets if obj in me}
    names = {x.d.name for x in members if private(x.d.name)} | {a for a in attrs if private(a)}
    names = {n for n in names if n.lstrip('_') not in props}
    public = sorted(a for a in attrs if not a.startswith('_') and a not in props)
    plain = any(b in PLAIN for b in d.bases) or any(x.startswith('dataclass') for x in d.decorators)
    return public, sorted(names), plain


def allsize(me):
    """(verdict, reason) of the size of __all__: 1-2 names green, 3-5 grey, 6-7 orange, more or none red (an Error class does not count)."""
    n = 0 if me.exports is None else len([x for x in me.exports if not x.endswith('Error')])
    return ('red' if me.exports is None or n > 7 else 'orange' if n > 5 else 'grey' if n > 2 else 'green',
            'no __all__' if me.exports is None else f'{n} name(s) in __all__')


def const_verdict(c, name, literal):
    """(verdict, reason) of a module-level constant, one colour for the whole pie: orange when it is in __all__ (a constant should not be
    exposed), red when other modules use it though it is not exposed, orange when it has too few capitals (a literal that is not a
    CONSTANT name) or is never used, green when it is all capitals and used inside the module only, grey when only its first
    three letters are capitals."""
    me = c.me
    outside = sum(1 for s in c.sibs if s.words.get(name, 0))
    if me.exports is not None and name in me.exports:
        return 'orange', 'a constant in __all__'
    if outside:
        return 'red', f'used by {outside} other module(s), not in __all__'
    if literal:
        return 'orange', 'a literal with too few capitals'
    if me.words.get(name, 0) < 2:
        return 'orange', 'never used'
    return ('green', 'all capitals, private to the module') if name == name.upper() else ('grey', 'only the first three letters are capitals')


def verdicts_file(c):
    """[(id, weight, force, verdict, reason)] of the rules of the file."""
    me, got = c.me, []

    def add(rule, weight, verdict, reason):
        got.append((rule, weight, False, verdict, reason))
    std = sys.stdlib_module_names
    clauses = me.facts.imports
    plain = [x for x in clauses if x[0].split('.')[0] in std]
    other = [x for x in clauses if x[0].split('.')[0] not in std]
    loads = [call for line in me.facts.lines.values() for call in line.get('calls', []) if call[0] in ('load', 'use')]
    auto = any(call[0].startswith(('importlib', '__import__')) for line in me.facts.lines.values()
               for call in line.get('calls', []))
    total = len(clauses) + len(loads)
    add('imports', 2, 'red' if auto else 'orange' if total > 12 else 'grey' if len(plain) > 7 or len(other) + len(loads) > 3
        else 'green', f'{len(plain)} standard, {len(other)} other, {len(loads)} load/use' + (', an automated import' if auto else ''))
    if me.stem.startswith('b_'):                      # a suite has no __all__ and nothing to expose: only its imports count
        return got
    add('allsize', 3, *allsize(me))
    if c.sibs:
        by = {s.stem: s for s in c.sibs}
        wrong = []
        many = []
        for module, names, alias, line in clauses:
            sib = by.get(module.split('.')[0])
            if sib is None:
                continue
            if sib.exports is None:
                wrong.append(module + ' (no __all__)')
            else:
                wrong += [f'{module}.{x}' for x in names if x not in sib.exports]
                if len(sib.exports) > 5:
                    many.append(module)
        for call in loads:
            sib = by.get(call[1].strip('\'"'))
            if sib is not None and sib.exports and len(sib.exports) > 5:
                many.append(sib.stem)
        add('foreign', 3, 'red' if wrong else 'orange' if many else 'green',
            'imports ' + ', '.join(wrong[:3]) if wrong else 'a module with over 5 names in __all__: ' + ', '.join(many[:2]) if many else 'none')
    if c.suites:
        peeks = set()
        for suite in c.suites:
            f = suite.facts()
            if f is None or me.exports is None:
                continue
            alias = {x[2] for x in f.imports if x[0].split('.')[0] == me.stem}
            for module, names, a, line in f.imports:
                if module.split('.')[0] == me.stem:
                    peeks |= {x for x in names if x not in me.exports and not x.startswith('__')}
            for line in f.lines.values():
                for obj, attr in line.get('dots', []):
                    if obj in alias and attr not in me.exports and not attr.startswith('__'):
                        peeks.add(attr)
        if peeks:
            add('suitepeek', 3, 'red', 'a suite reaches ' + ', '.join(sorted(peeks)[:4]))
        else:
            only = [x for x in sorted(me.exports or ()) if not any(s.words.get(x) for s in c.sibs) and not me.words.get(x)]
            add('suitepeek', 3, 'orange' if only else 'green',
                'exposed for the tests only: ' + ', '.join(only[:3]) if only else 'the suite reaches only what is exposed')
    funcs = [x for x in me.items if x.d.parent == -1 and x.d.kind == 'def' and x.d.first not in c.exposed]
    classes = [x for x in me.items if x.d.parent == -1 and x.d.kind == 'class']
    worst = max(KINDS.index(ladder(len(funcs), (3, 7, 12))), KINDS.index(ladder(len(classes), (2, 3, 4))))
    add('locals', 1, KINDS[worst], f'{len(funcs)} local function(s), {len(classes)} class(es)')
    match = HEADER.match(me.text)
    head = match.group(2) if match else ''
    names = [x for x in (me.exports or ()) if re.search(r'\b' + re.escape(x) + r'\b', head)]
    listed = me.exports is not None and len(names) == len(me.exports)
    versions = bool(VERSION.search(head))
    add('header', 2, 'red' if not head else 'green' if listed and versions else 'grey' if listed or versions
        else 'orange' if names else 'red', f'header names {len(names)} of {len(me.exports or ())} exposed' + (', VERSION lines' if versions else ', no VERSION lines'))
    return got


def grade(hits, extra=0, dot=''):
    """The Colour of a list of hits [(id, weight, force, verdict, reason)], and `extra` percent of red added."""
    total = sum(h[1] for h in hits)
    if not total:
        return Colour('', pie=(0, 0, 0, 0), dot=dot)
    share = [100.0 * sum(h[1] for h in hits if h[3] == k) / total for k in KINDS]
    red = min(100.0, share[3] + extra)
    scale = 0 if share[3] >= 100 else (100 - red) / (100 - share[3])
    share = [share[0] * scale, share[1] * scale, share[2] * scale, red]
    pie = [int(x) for x in share]
    for k in sorted(range(4), key=lambda i: share[i] - pie[i], reverse=True)[:100 - sum(pie)]:
        pie[k] += 1
    forced = any(h[2] for h in hits)
    band = ('red' if forced or share[3] >= BANDS['red'] else 'orange' if share[2] + share[3] >= BANDS['orange']
            else 'green' if share[0] >= BANDS['green'] else '')
    why = [f'{h[0]}: {h[3]} ({h[1]}) {h[4]}' for h in hits if h[3] != 'green'] + [f'{h[0]}: green' for h in hits if h[3] == 'green']
    return Colour(band, why, pie, share[0] + BANDS['grey'] * share[1], dot)


def isspaghetti(source, area='', testarea=''):
    """The Colour of a file, with the Colour of each of its functions and classes in .rows: see the module header."""
    me = summary(source)
    if me is None:
        return Colour('')
    c = SimpleNamespace(me=me, area=area, exposed=set())
    c.sibs = [s for s in (summary(x) for x in sources(area, source)) if s is not None and s.src.real != source.real]
    stem = me.stem
    c.suites = [s for s in sources(testarea, source) if os.path.splitext(os.path.basename(s.real))[0] == 'b_' + stem]
    c.exposed = exposure(me)
    c.names = {it.d.name for it in me.items}
    c.twins = {}
    c.key = lambda it: (tuple(it.d.params), tuple(sorted({n for r in it.returns for n in r}))) if len(it.d.params) > 1 else ((), ())
    for s in c.sibs + [me]:
        for it in s.items:
            if it.d.params and it.returns:
                c.twins.setdefault(c.key(it), []).append(it)
    rows = {}
    for i, it in enumerate(me.items):
        exposed = it.d.first in c.exposed
        hits = verdicts_row(c, it, exposed)
        extra = 0
        dot = proof(c, it) if exposed and testarea else ''
        if it.d.kind == 'class':
            public, names, plain = class_notes(c, it)
            if public and not plain:
                hits.append(('classdata', 2, False, 'orange', 'public data attributes: ' + ', '.join(public[:3])))
            elif exposed:
                hits.append(('classdata', 2, False, 'green', 'none'))
            extra = min(BANDS['cap'], BANDS['private'] * len(names))
        rows[it.d.first] = grade(hits, extra, dot)
    for name, first, last in me.facts.consts:         # the __all__ line has the pie of its size: too many names is red
        if name == '__all__':
            if me.exports is not None:
                rows[first] = grade([('allsize', 3, False) + allsize(me)])
        else:
            rows[first] = grade([('constant', 3, False) + const_verdict(c, name, False)])
    for name, first, last in me.facts.literals:
        rows[first] = grade([('constant', 3, False) + const_verdict(c, name, True)])
    if me.exports is None and not me.stem.startswith('b_'):          # no __all__: a note row (key 0), red, since nothing is exposed
        rows[0] = grade([('allsize', 3, False) + allsize(me)])
    whole = grade(verdicts_file(c))
    whole.rows = rows
    return whole
