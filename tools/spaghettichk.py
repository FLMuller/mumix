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

    python tools/spaghettichk.py <verb> <path> [rule] [--only colour] [--rule rule] [--tests wildcard]
    main(argv)    the same from Python: the words after the script name; SystemExit(message) for a path outside a project

    scope   where a check on the path would look (project, area, suites, where the scan of the tree starts); nothing is read
    files   a line for each file: band, pie, score, milliseconds, its red rules and, after a |, its orange rules
    why     the reasons of each file, as isspaghetti gives them
    rows    each function, class and constant with band, pie, dot and reasons; --rule keeps the rows where that rule is not green
    rule    every place one rule is not green (its name after the path); --only picks another verdict, green too
    tally   how often each rule gave each verdict, for the files and for their rows
    A path is a file or one folder (its files, not its subfolders). It must lie below the folder that holds .claude, and the
    widest area a check looks at is the folder one below that (mumix): the Claude folder itself, a dot folder and anything
    outside are refused, and the scan of the tree around a module (importers, door, importclean) starts no higher than that
    folder. The lexer is found with use.load('rs3lex').

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
poke (a private member of another object), allsize, imports, foreign, suitepeek, locals, header (names and VERSION lines);
and from spaghetti_rules_v6.md: peek (a name of another module that its __all__ does not expose, reached through the module,
forced red), importers (how many modules of the folder use this one), door (a module that is not the folder's front door,
used from outside the folder, forced red), cycles (an import loop among the modules of the folder, forced red),
importclean (the names used / the names exposed must be exactly 1: siblings and subs for an internal module, the whole tree
for the front door), length (the median lines of a function), twin (a .pyx that stands for Python loops names the gain of each
function in a Speed section), constants (the same constant value in two modules), and allsize no longer exempts every Error name
(only a hierarchy under one base class).
The front door of a folder is the module named like it (xlw/xlw.py; a trailing version number is ignored, xlw2/xlw.py counts).
Not built: evolution (a version against the last one), the orange dot for functions no test run executed, the data attribute
of a class read from outside, the surface ratio of a package.

VERSION  M1 m01.v04 (2026-11-05): moved from tools/primary to tools/; main() and the verbs scope, files, why, rows, rule and tally;
         projectof and tree_top: the scan of the tree starts no higher than the folder one below the one that holds .claude (for a
         file in mumix/xlw it started at the Claude folder, and read all of it).
         M1 m01.v03 (2026-11-05): the v6 rules above; the weights of the new rules are in WEIGHTS and the bands of length in LENGTH.
         M1 m01.v02 (2026-11-04): constants and the __all__ line have a pie of their own; a file with no __all__ gets a red note row (key 0); the proof dot has four colours.
         M1 m01.v01 (2026-11-04): first version.
"""
import argparse
import os
import re
import sys
import time
from types import SimpleNamespace

from use import load

load('rs3util')
from rs3util import pathof

__all__ = ['isspaghetti', 'main']

BANDS = {'red': 15, 'orange': 35, 'green': 50, 'grey': 0.5, 'private': 1, 'cap': 25}
WEIGHTS = {'peek': 8, 'importers': 3, 'door': 8, 'cycles': 6, 'importclean': 10, 'length': 6, 'twin': 3, 'constants': 4}
LENGTH = (11, 18, 7, 21, 5, 30)                     # the median lines of a function: green from..to, grey from..to, orange from..to
SKIP = {'results', 'z_sandbox', 'zprev', '__pycache__', 'pyxfiles', 'node_modules', 'fixtures', 'golden', 'build'}
USERHOME = os.path.expanduser('~')                  # its .claude is Claude Code's own settings: no project is below it
SCAN = 6000                                         # the most files looked at around a folder
LISTED = 10                                         # seconds a listing of the files around a folder is kept
TREE = {}                                           # top folder: (time, paths)
INDEX = {}                                          # path: (mtime, size, words)
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


def folder_of(real):
    """The name of the folder of a file without a trailing version number: xlw2 is xlw."""
    return re.sub(r'\d+$', '', os.path.basename(os.path.dirname(real)))


def imports_of(s, stem):
    """True when the file summarised by s imports or loads the module stem."""
    return (any(clause[0].split('.')[0] == stem for clause in s.facts.imports)
            or re.search(r'^[ \t]*(?:from|import)[ \t]+' + re.escape(stem) + r'\b', s.text, re.M) is not None
            or re.search(r'\bload\([^)]*[\'"]' + re.escape(stem) + r'[\'"]', s.text) is not None)


def user_names(s, stem, exports):
    """(the exposed names of the module stem that the file s uses, the names of it that s reaches without them being exposed)."""
    used = {x for x in exports if s.words.get(x) or re.search(r'[\[(][ ]*[\'"]' + re.escape(x) + r'[\'"]', s.text)}   # a key of what load() gives counts
    alias ={clause[2] or clause[0].split('.')[0] for clause in s.facts.imports if clause[0].split('.')[0] == stem}
    reached = set()
    for clause in s.facts.imports:
        if clause[0].split('.')[0] == stem:
            reached |= {x for x in clause[1] if x not in exports and x != '*' and not x.startswith('__')}
    for line in s.facts.lines.values():
        reached |= {attr for obj, attr in line.get('dots', []) if obj in alias and attr not in exports and not attr.startswith('__')}
    return used, reached


def userhome(path):
    """True for the user's home folder, whose .claude holds Claude Code's own settings and is no project."""
    try:
        return os.path.samefile(path, USERHOME)
    except OSError:
        return False


def projectof(real):
    """The widest folder a check may look at: the folder one below the nearest folder that holds .claude, on
    the way up from real (the user's home folder does not count). '' when real is that folder or above it, a
    file straight in it, outside any such folder, or in a dot folder (.claude, .git): a check never works on
    the whole Claude area."""
    here = os.path.abspath(real)
    below = ''
    while here != os.path.dirname(here):
        if os.path.isdir(os.path.join(here, '.claude')) and not userhome(here):
            return below if os.path.isdir(below) and not os.path.basename(below).startswith('.') else ''
        below = here
        here = os.path.dirname(here)
    return ''


def tree_top(folder, project):
    """The folder the scan of the tree around a module starts from: two folders above its own, never above
    its project (both are folders on the way up from the module, so the longer path is the lower one)."""
    return max(os.path.dirname(os.path.dirname(folder)), project, key=len)


def listing(top):
    """The paths of the Python and Cython files under top (not the folders of SKIP), listed again after LISTED seconds."""
    got = TREE.get(top)
    if got and time.time() - got[0] < LISTED:
        return got[1]
    paths = []
    for root, dirs, files in os.walk(top):
        dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith('.')]
        paths += [os.path.join(root, name) for name in files if name.endswith(('.py', '.pyx'))]
        if len(paths) > SCAN:
            break
    TREE[top] = (time.time(), paths)
    return paths


def words_of(path):
    """The set of the words of a file, read once and again only when the file changes (size and time)."""
    try:
        stat = os.stat(path)
    except OSError:
        return frozenset()
    hit = INDEX.get(path)
    if hit and hit[0] == stat.st_mtime and hit[1] == stat.st_size:
        return hit[2]
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            found = frozenset(re.findall(r'\w+', f.read()))
    except OSError:
        found = frozenset()
    INDEX[path] = (stat.st_mtime, stat.st_size, found)
    return found


def tree_users(me, reader):
    """(inside, outside): summaries of the files that use this module in the tree around its folder, the folder and its
    subfolders (inside) and the rest of what lies under the folder's parent's parent (outside), never above the project (projectof). A file whose own folder holds a
    module of the same name is left out: it means that one."""
    folder = os.path.normcase(os.path.abspath(os.path.dirname(me.src.real)))
    project = os.path.normcase(projectof(me.src.real))
    if not project:                                   # not inside a project: no tree is looked at
        return [], []
    top = tree_top(folder, project)
    mine = os.path.normcase(os.path.abspath(me.src.real))
    inside, outside = [], []
    for path in listing(top):
        full = os.path.normcase(os.path.abspath(path))
        if full == mine or me.stem not in words_of(path):
            continue
        here = os.path.dirname(full)
        within = here == folder or here.startswith(folder + os.sep)
        if not within and any(os.path.exists(os.path.join(os.path.dirname(path), me.stem + ext)) for ext in ('.py', '.pyx')):
            continue
        try:
            src = type(me.src).read(path)
        except (OSError, ValueError, TypeError):
            continue
        s = summary(src)
        if s is not None and imports_of(s, me.stem):
            (inside if within else outside).append(s)
    return inside, outside


def cycle_of(me, sibs):
    """The loop of imports among the modules of the folder that this module is in, as 'a > b > a', or ''."""
    mods = {s.stem: s for s in sibs}
    mods[me.stem] = me
    edges = {stem: [other for other in mods if other != stem and imports_of(s, other)] for stem, s in mods.items()}
    stack = [(me.stem, [me.stem])]
    seen = set()
    while stack:
        at, path = stack.pop()
        for nxt in edges.get(at, ()):
            if nxt == me.stem:
                return ' > '.join(path + [nxt])
            if nxt not in seen:
                seen.add(nxt)
                stack.append((nxt, path + [nxt]))
    return ''


def code_lines(me, it):
    """The lines of a function that carry code: not blank, not a comment, not the docstring; a ; counts as a new line."""
    d = it.d
    body = me.text.split('\n')[d.first - 1:d.last]
    n = 0
    for line in body:
        s = line.strip()
        if s and not s.startswith('#'):
            n += 1 + (s.count(';') if '"' not in s and "'" not in s else 0)
    return max(1, n - d.docs)


def split_top(text):
    """The pieces of text at the commas that are not inside brackets or quotes."""
    out, depth, quote, start = [], 0, '', 0
    for i, ch in enumerate(text):
        if quote:
            quote = '' if ch == quote else quote
        elif ch in '"\'':
            quote = ch
        elif ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        elif ch == ',' and depth == 0:
            out.append(text[start:i])
            start = i + 1
    out.append(text[start:])
    return out


def constant_values(s):
    """{name: normalised value} of the constants of a file that are long enough to be a value worth copying: the module-level
    ones and the NAME=value entries of a priv namespace."""
    if hasattr(s, 'values'):
        return s.values
    out, lines = {}, s.text.split('\n')
    for name, first, last in s.facts.consts + s.facts.literals:
        rhs = ' '.join(x.strip() for x in lines[first - 1:last]).split('=', 1)[-1].strip()
        if name != '__all__' and len(rhs) >= 12:
            out[name] = re.sub(r'\s+', '', rhs)
    block = re.search(r'^priv\s*=\s*[\w.]*SimpleNamespace\(', s.text, re.M)
    if block:
        depth, i = 1, block.end()
        while i < len(s.text) and depth:
            depth += {'(': 1, ')': -1}.get(s.text[i], 0)
            i += 1
        for piece in split_top(re.sub(r'#[^\n]*', '', s.text[block.end():i - 1])):
            name, _, rhs = piece.partition('=')
            name, rhs = name.strip(), re.sub(r'\s+', '', rhs)
            if name.isupper() and len(rhs) >= 12:
                out[name] = rhs
    s.values = out
    return out


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
        if c.suites and not suite:
            named = any(re.search(r'\b' + re.escape(d.name) + r'\b', s.text) for s in c.suites)
            add('tested', 5, 'green' if named else 'orange', 'a suite names it' if named else 'a suite exists, none names it')
        if (c.sibs or c.area) and not c.door:
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
    peeks = [(obj, attr) for obj, attr in it.dots if obj in c.modmap and c.modmap[obj].exports is not None
             and attr not in c.modmap[obj].exports and not attr.startswith('__') and not private(attr)]
    if peeks:
        add('peek', WEIGHTS['peek'], 'red', f'reaches {peeks[0][0]}.{peeks[0][1]}, which {c.modmap[peeks[0][0]].stem} does not expose', True)
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
    """(verdict, reason) of the size of __all__: 1-2 names green, 3-5 grey, 6-7 orange, more or none red (the Error classes of
    one hierarchy under one base class count as that base)."""
    errors = {x for x in (me.exports or ()) if x.endswith('Error')}
    bases = {it.d.name: set(it.d.bases) for it in me.items if it.d.kind == 'class' and it.d.name in errors}
    one = len([x for x in errors if not bases.get(x, set()) & errors]) == 1          # a hierarchy under one base class
    n = 0 if me.exports is None else len(me.exports) - (len(errors) - 1 if one else 0)
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

    def add(rule, weight, verdict, reason, force=False):
        got.append((rule, weight, force and verdict == 'red', verdict, reason))
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
    tree_rules(c, add)
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


def tree_rules(c, add):
    """The rules of spaghetti_rules_v6.md that look at the folder and the tree around it: importers, door, cycles, importclean,
    length, twin and constants. add(rule, weight, verdict, reason, force) records a verdict."""
    me = c.me
    head = HEADER.match(me.text)
    head = head.group(2) if head else ''
    twin = me.src.real.endswith('.pyx') and re.search(r'pure-Python|Python (loop|version)', head) is not None
    users = [s for s in c.sibs if imports_of(s, me.stem)]
    if not c.door and not twin and c.area:
        n = len(users)
        add('importers', WEIGHTS['importers'], 'green' if n >= 4 else 'grey' if n == 3 else 'orange' if n == 2 else 'red',
            f'{n} other module(s) of the folder use it' + (' (a satellite)' if n == 1 else ''))
        if c.outside:
            add('door', WEIGHTS['door'], 'red', 'used from outside its folder: ' + ', '.join(
                sorted({os.path.basename(s.src.real) for s in c.outside})[:3]), True)
        else:
            add('door', WEIGHTS['door'], 'green', 'used inside its folder only')
    loop = cycle_of(me, c.sibs) if c.sibs else ''
    add('cycles', WEIGHTS['cycles'], 'red' if loop else 'green', ('an import loop: ' + loop) if loop else 'no import loop', True)
    if me.exports:
        mine = c.outside + c.inside if c.door else c.inside + [s for s in c.sibs if s.src.real not in {x.src.real for x in c.inside}]
        got = set()
        reached = set()
        for s in mine:
            used, reach = user_names(s, me.stem, me.exports)
            got |= used
            reached |= reach
        unused = sorted(set(me.exports) - got)
        if not (c.door and not mine and not me.words):
            bad = bool(unused or reached)
            add('importclean', WEIGHTS['importclean'], 'red' if bad else 'green',
                f'{len(got)} of {len(me.exports)} exposed names used by the ' + ('tree' if c.door else 'folder')
                + ('; unused: ' + ', '.join(unused[:3]) if unused else '') + ('; not exposed: ' + ', '.join(sorted(reached)[:3]) if reached else ''))
    sizes = sorted(code_lines(me, it) for it in me.items if it.d.kind == 'def')
    if sizes:
        m = (sizes[len(sizes) // 2] + sizes[(len(sizes) - 1) // 2]) / 2
        g0, g1, y0, y1, o0, o1 = LENGTH
        add('length', WEIGHTS['length'], 'green' if g0 <= m <= g1 else 'grey' if y0 <= m <= y1 else 'orange' if o0 <= m <= o1 else 'red',
            f'the median function is {m:g} lines (of {len(sizes)})')
    if twin and me.exports:
        found = re.search(r'\nSpeed\n((?:[ \t]+[^\n]*\n|\n(?=[ \t]))*)', head + '\n')
        section = found.group(1).split('\n') if found else []
        named = [x for x in me.exports if any(x in line and re.search(r'\d(?:\.\d+)?\s*x\b', line) for line in section)]
        add('twin', WEIGHTS['twin'], 'red' if not found else 'green' if len(named) == len(me.exports) else 'orange',
            'no Speed section in the header' if not found else f'the Speed section gives the gain of {len(named)} of {len(me.exports)} functions')
    if c.sibs:
        mine = constant_values(me)
        same = [f'{name} = {s.stem}.{other}' for s in c.sibs for other, value in constant_values(s).items()
                for name, mine_value in mine.items() if value == mine_value]
        add('constants', WEIGHTS['constants'], 'orange' if same else 'green', ('the same value as ' + same[0]) if same else 'no copied constant')


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
    same = os.path.normcase(os.path.abspath(source.real))
    c.sibs = [s for s in (summary(x) for x in sources(area, source))
              if s is not None and os.path.normcase(os.path.abspath(s.src.real)) != same]
    stem = me.stem
    c.suites = [s for s in sources(testarea, source) if os.path.splitext(os.path.basename(s.real))[0] == 'b_' + stem]
    c.exposed = exposure(me)
    c.door = me.stem == folder_of(me.src.real)
    c.inside, c.outside = ([], [])
    if area and not me.stem.startswith('b_'):
        c.inside, c.outside = tree_users(me, source)
    by = {s.stem: s for s in c.sibs}
    c.modmap = {(clause[2] or clause[0].split('.')[0]): by[clause[0].split('.')[0]] for clause in me.facts.imports
                if clause[0].split('.')[0] in by and by[clause[0].split('.')[0]].exports is not None}
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


# ---- the command line: python tools/spaghettichk.py <verb> <path> ---------------------------------------------
VERDICT = re.compile(r'^(\w+): (green|grey|orange|red)\b')        # a reason of Colour.why: 'rule: verdict ...'


def target(text):
    """(the real path, its project folder) of a path given on the command line. SystemExit with a message when it
    names nothing or is not inside a project (see projectof)."""
    real = os.path.abspath(text) if os.path.exists(text) else (pathof(text) or '')
    project = projectof(real) if real and os.path.exists(real) else ''
    if not project:
        sys.exit(f'spaghettichk: {text!r} is not a path inside a project. Give a file or a folder below the folder '
                 'that holds .claude; the widest area a check looks at is the folder one below it.')
    return real, project


def files_of(real):
    """The Python and Cython files a path names: itself, or those straight in the folder (no subfolder)."""
    if os.path.isfile(real):
        return [real]
    names = sorted(name for name in os.listdir(real) if name.endswith(('.py', '.pyx')))
    return [os.path.join(real, name) for name in names]


def areas(real, project, tests):
    """(area, testarea) for isspaghetti: the Python files of the folder, and the suites of the project
    (test/ or tests/ b_*.py) unless a wildcard is given."""
    folder = real if os.path.isdir(real) else os.path.dirname(real)
    here, home = pathof(folder), pathof(project)
    return (here + '/*.{py,pyx}' if here else ''), tests or (home + '/{test,tests}/b_*.py' if home else '')


def judged(args):
    """[(path, Source, Colour, milliseconds)] of the files the command names."""
    out = []
    for path in files_of(args.real):
        began = time.time()
        src = args.Source.read(path)
        colour = isspaghetti(src, args.area, args.testarea)
        out.append((path, src, colour, 1000 * (time.time() - began)))
    return out


def band_of(colour):
    return str(colour) or 'grey'


def pie_of(colour):
    return '/'.join(str(share) for share in colour.pie)


def reasons_of(item, rule=''):
    """The reasons of a Colour that are not green; only those of one rule when it is given."""
    return [why for why in item.why if not why.endswith(': green') and (not rule or why.startswith(rule + ':'))]


def rules_of(colour, verdict):
    """The names of the rules of a Colour with this verdict."""
    found = [VERDICT.match(why) for why in colour.why]
    return [got.group(1) for got in found if got and got.group(2) == verdict]


def names_of(src):
    """{first line: name} of the rows a Colour carries: functions and classes, constants, and the __all__ note (0)."""
    facts = src.facts()
    names = {d.first: d.dotted for d in facts.defs}
    names.update({first: name for name, first, last in facts.consts + facts.literals})
    names[0] = '(no __all__)'
    return names


def do_scope(args):
    """scope: where a check on this path would look, and nothing read."""
    folder = os.path.abspath(args.real if os.path.isdir(args.real) else os.path.dirname(args.real))
    names = [os.path.basename(path) for path in files_of(args.real)]
    print(f'path     {args.real}')
    print(f'project  {args.project}   (the widest area a check looks at)')
    print(f'area     {args.area or "(none)"}')
    print(f'suites   {args.testarea or "(none)"}')
    print(f'scan     {tree_top(folder, args.project)}   (where the scan of the tree starts)')
    print(f'files    {len(names)}: {", ".join(names)}')


def do_files(args):
    """files: a line for each file: band, pie, score, time, then its red rules and, after |, its orange ones."""
    for path, src, colour, ms in judged(args):
        if args.only in ('', band_of(colour)):
            orange = rules_of(colour, 'orange')
            print(f'{os.path.basename(path):18s}{band_of(colour):8s}{pie_of(colour):14s}{colour.score:6.1f}'
                  f'{ms:8.0f} ms  {" ".join(rules_of(colour, "red"))}' + (f'  | {" ".join(orange)}' if orange else ''))


def do_why(args):
    """why: the reasons of each file, as isspaghetti gives them."""
    for path, src, colour, ms in judged(args):
        print(f'{os.path.basename(path)}  {band_of(colour)}  {pie_of(colour)}  score {colour.score:.1f}')
        for why in colour.why:
            print('   ' + why)


def do_rows(args):
    """rows: each function, class and constant of each file with band, pie, dot and its reasons that are not green."""
    for path, src, colour, ms in judged(args):
        names = names_of(src)
        print(os.path.basename(path))
        for line, row in sorted(colour.rows.items()):
            got = reasons_of(row, args.rule)
            if args.only in ('', band_of(row)) and (got or not args.rule):
                print(f'  {line:5d} {band_of(row):7s}{names.get(line, ""):24.24s} {pie_of(row):13s}{row.dot:7s}'
                      f'{"; ".join(got)[:160]}')


def do_rule(args):
    """rule: every place one rule is not green, or has the verdict --only gives."""
    for path, src, colour, ms in judged(args):
        names = names_of(src)
        base = os.path.basename(path)
        places = [(base, '', colour)] + [(f'{base}:{line}', names.get(line, ''), row) for line, row in sorted(colour.rows.items())]
        for place, name, item in places:
            for why in item.why:
                found = VERDICT.match(why)
                if found and found.group(1) == args.word and (found.group(2) == args.only if args.only else found.group(2) != 'green'):
                    print(f'{place:24s}{name:24.24s} {why}')


def do_tally(args):
    """tally: how often each rule gave each verdict, for the files and for their rows (the most red first)."""
    counts = {'file': {}, 'row': {}}
    for path, src, colour, ms in judged(args):
        for level, item in [('file', colour)] + [('row', row) for row in colour.rows.values()]:
            for why in item.why:
                found = VERDICT.match(why)
                if found:
                    counts[level].setdefault(found.group(1), dict.fromkeys(KINDS, 0))[found.group(2)] += 1
    for level, rules in counts.items():
        print(f'{level} rules          green  grey  orange  red')
        for rule, got in sorted(rules.items(), key=lambda pair: (-pair[1]['red'], -pair[1]['orange'], pair[0])):
            print(f'  {rule:14s}{got["green"]:7d}{got["grey"]:6d}{got["orange"]:8d}{got["red"]:5d}')


VERBS = {'scope': do_scope, 'files': do_files, 'why': do_why, 'rows': do_rows, 'rule': do_rule, 'tally': do_tally}


def main(argv=None):
    """The command line: <verb> <path> [rule] [--only colour] [--rule rule] [--tests wildcard], the words after
    the script name (see the module header). SystemExit(message) for a path outside a project."""
    parser = argparse.ArgumentParser(prog='spaghettichk', description='How tangled, hidden and untested a file is.',
                                     epilog='\n'.join(f'  {name:6s} {fun.__doc__.split(": ", 1)[1]}' for name, fun in VERBS.items()),
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('verb', choices=list(VERBS))
    parser.add_argument('path', help='a file, or a folder (its files, not its subfolders), below the folder that holds .claude')
    parser.add_argument('word', nargs='?', default='', help='rule: the name of the rule')
    parser.add_argument('--only', default='', choices=KINDS, help='keep only this colour (rule: this verdict)')
    parser.add_argument('--rule', default='', help='rows: keep the rows where this rule is not green')
    parser.add_argument('--tests', default='', help='a wildcard of the suites (default: the project\'s tests/b_*.py)')
    args = parser.parse_args(argv)
    if args.verb == 'rule' and not args.word:
        parser.error('rule needs the name of a rule after the path')
    args.real, args.project = target(args.path)
    load('rs3lex')
    from rs3lex import Source
    args.Source = Source
    args.area, args.testarea = areas(args.real, args.project, args.tests)
    VERBS[args.verb](args)


if __name__ == '__main__':
    main()
