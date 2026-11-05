r"""use.py -- find project code by NAME, put it on the path, import it, run it, build it.

    It is tools/use.py rebuilt for pipe3: the search starts where the CALL is, not where the
    program was started, so a module finds its own neighbours however it is run. Rename it
    `use` when it replaces tools/use.py.

READ THIS FIRST -- what to write in a module

    from use import load, use

    use('vaults', 'silent')        # put the folder `vaults` on sys.path: `import slot`
    load('slotfun')                # build slotfun.pyx if need be, import it, bind its
                                   # public names (its __all__) into THIS module
    codec = load('attachment')     # the bound names, as a dict: codec['encode']
    load('slottable', into={})     # bind into a dict of your own, not into this module

    A single module that cannot be found, built or imported RAISES ImportError (with the
    compiler's last lines). A folder is loaded module by module: a bad one is printed and
    skipped, the rest are bound. `use` finds a folder or module and only makes it
    importable.

THE SEARCH  (what `use('x')` and `load('x')` look at, in this order; the first step that
has a match wins, and among the matches of one step the SHALLOWEST wins, then the NEWEST)

    1  the CALLER's folder: its own files; its `primary/` (1 deep); its subfolders (2 deep)
    2  each PARENT of the caller's folder, nearest first: its files; its `primary/` (1
       deep); its subfolders (1 deep)
    3  the folder of the SCRIPT Python was started with (sys.argv[0]; the current folder
       in a console, `python -c`, stdin, or `python -m ...`): files; `primary/`;
       subfolders (2 deep)
    4  the script folder's PARENT: files; `primary/`; subfolders (1 deep)
    5  the folders already on sys.path (not Python's own): their files only. So a script
       that has said use('pipe3', '+subs') can then load('cvault') from vaults/

    A name is `<name>.py` or `<name>.pyx` (a compiled module) or a folder `<name>`. Where both
    `.py` and `.pyx` of a name are met, the `.pyx` is the one: use loads one version of a name.
    * the CALLER is the file of the module that called use, load, run or build. In a
      console, `python -c` or stdin there is none, and the search begins at step 3.
    * a folder named `primary` is searched wherever it is met, 1 deep. It is the home of
      the self-sufficient tools; `use()` and `load()` with no item mean `primary`.
    * a folder that is the caller's own folder, or one of its parents, is never a match
      for a folder NAME (tests/pipe3 must not be taken for the pipe3 you asked for).
    * a PARENT (steps 2 and 4) holding more than 176 entries (BIG_PARENT) has only its own
      files and `primary/` searched, not its subfolders: scanning a crowd (the system temp
      folder has twenty thousand) takes seconds. Its own folder and the script's are not
      parents here and are always scanned.
    * a folder is searched only if it is at least one level below the bare drive: `C:\`
      is never searched, nor anything below it from there; `C:\code` is.
    * never entered: `.py` (the folder of non-Cython copies, whose files are `name.pyt`),
      `pyxfiles`, `prev`, `zprev`, `__pycache__`, `.git`, `venv`, `.venv`, `build`, `dist`,
      `site-packages`, and any folder that holds `pyvenv.cfg`. `exclude()` adds more.

use(*items) -> (folders, ok)
    Find each item and add the folder it lives in to sys.path. Binds no names.
        use('vaults')               a folder: add it (and its `primary/` if it has one)
        use('slot')                 a module: add the folder that holds slot.py
        use('vaults', '+subs')      the folder AND its subfolders (2 deep)
        use('data', '+mkdir')       if not found, create ./data and add it
        use('.results')             CREATE ./results (not added to the path)
        use('vaults', 'silent')     print nothing
    Returns (folders, ok): folders is a list of {item, full, status}, status one of
    added | ok (already on the path) | subs | created | skip (not found); ok is False if
    any was skipped. `use()` with no item is use('primary').

load(*items, silent=True, into=None, reload=None) -> dict {name: object}
    use() each item AND import it, binding its public names (__all__, else the eponymous
    name, else the first class or function it defines) into the caller's module
    namespace, or into the dict `into`. A folder item imports every module in it (not
    `_private`, not setup.py), `+subs` those of its subfolders too (2 deep). A
    pure-Python module is imported once; in a console (reload=None means reload when
    interactive; True or False forces it) a module whose file changed since it was
    last loaded is reloaded IN PLACE (importlib.reload: same module object, one stat
    per module, unchanged ones untouched) and named in a line. A reload makes new
    classes: an object made before the edit keeps the old class. One already imported
    from another folder is said so. In a console a bare `import use` also binds
    use, load, run, build, exclude (none replaced; no hook; a script is left alone).
    A .pyx is built on demand into <folder>/pyxfiles/ (ABI-tagged for this Python) when
    it has no build or is newer than its build, and is never reloaded: a process that
    has a stale build imported says so. A build that fails is a failure, even if an older build exists.

run(name, *args, reload=True, silent=True) -> result
    Run <name>.py in a private module (not put in sys.modules) and return main(*args),
    else the eponymous function's result, else the module namespace.

build(*items) -> ok
    Rebuild the .pyx of each item with the current Python: the one module when the item is a
    module, every .pyx of the folder when it is a folder.

compile(files) -> 0
    Compile .pyx file(s) (a path, or a list of paths) into <folder>/pyxfiles/ for this
    Python: Cython, then gcc to compile and link, every program started with no console
    window. Returns 0 when every file was built. Every file is tried; then CompileError is
    raised, its message naming each file, the step that failed (gcc missing or a Cygwin
    gcc, Cython, compile, link) and that step's messages, and its `.code` the return
    code of the first failure. The commands and the meaning of every option are
    written out at the head of `compile` in this file.

CompileError(message, code=1)
    The exception compile raises. build() and load() catch it: a build that fails is a
    failure.

locate(name, here=None) -> Path or None
    The file load('name') would run, found by the same search, without importing or
    building anything: the .pyx when there is one, else the .py. `here` is the folder the
    search starts from (default: the folder of the caller).

exclude(*patterns) -> list
    Add folder-name globs the search must never enter.

anchor() -> Path
    The folder step 3 starts from.

TRAPS  (each one has cost an afternoon)

    * Two copies of a name in reach: the nearest wins, so an old copy beside you hides
      the new one in a parent. Move strays; `prev/` and `.py/` are never searched.
    * The caller is the file that CALLS use: a helper function in another module that
      calls load() makes that module the caller.
    * A compiled module cannot be reloaded in a live process. After editing a .pyx, start
      a new process: load() then RAISES ImportError (use 2.7), saying to run again.
    * Two processes that start together may both find a stale build and both build it.
      Build once (use.build) before starting a crowd.
    * load() binds into a module's globals, so it must be called where the names are
      wanted (a module level), not inside a function whose caller is elsewhere.
    * A path is added with sys.path.insert(0, ...): the last use() wins an ordinary
      import of a name that exists in two folders on the path.
    * A module that defines no `__all__`, no function or class of its own and no name
      like its file binds nothing: give it an `__all__`.

VERSION  use 2.12 (2026-11-05): compile(files) and CompileError: a .pyx
         is built by Cython and by two gcc commands that this file runs itself, with no
         console window (setuptools, a second Python and BUILD_SRC are gone). The flags:
         -shared -O1 -w, then -shared -s (was -O1 -Wall; -O2 and -O3 timed no faster).
         Snapshot: prev/usesetuptools.py.
         use 2.10 (2026-10-31): locate(name, here): the file load would run, found without importing.
         use 2.9 (2026-10-30): a .pyx is stale also when a .pxd or an include of its own folder that it
         needs is newer than its build (needs): the modules that cimport a changed .pxd are
         rebuilt, and fail if already imported, like the .pyx itself.
         use 2.8 (2026-10-30): a build compiles only the .pyx asked for (the stale ones of a load, the
         one module of build('name')), not every .pyx of the folder: one that does not build
         cannot stop another. build('folder') still builds them all.
         use 2.7 (2026-10-30): load FAILS (ImportError) for a compiled module whose .pyx is newer
         than the build this process imported: it says to run again. It was a warning.
         use 2.6 (2026-10-30): a .pyx wins over a .py of the same name (one version of a name is
         loaded, in load of a name and of a folder); zprev is never entered.
         use 2.5 (2026-10-30): pipe3's use2.py is now tools/use.py: the name only, the code is
         the 2.4 below; the old use.py 2.2 is prev/use_m22.py.
         use 2.4 (2026-10-22): the reviewed useb (the first use is gone); the console
         loop is back: load() reloads changed pure modules in place (reload=), and a bare
         `import use` binds the verbs in a console; a parent holding more than 176
         entries is not scanned below.
         useb 2.3.1 (2026-10-22): use reviewed and formatted: the unused `+silent` flag
         is gone; a pure module already imported from another folder is said so; plain
         names for the throwaway variables.
         use 2.3 (2026-10-22): the search starts at the caller (see THE SEARCH);
         `primary/` is searched 1 deep wherever it is met; `.py` and `pyxfiles` are never
         entered; a bare drive is never searched; a folder match cannot be the caller's
         own folder or a parent; a single module that fails raises ImportError;
         pure-Python modules are imported once; no import hook; the
         helpers are module functions. Before: tools/use.py 2.2 (kept in
         tools/prev/use_m22.py).
"""
import contextlib
import fnmatch
import importlib
import importlib.machinery
import importlib.util
import inspect
import io
import os
import re
import subprocess
import sys
import sysconfig
from pathlib import Path

__all__ = ['use', 'load', 'run', 'build', 'compile', 'CompileError', 'locate', 'exclude', 'anchor']

HERE = Path(__file__).resolve().parent              # the folder run() reloads code of
DEFAULTS = ('primary',)                             # use() and load() with no item
PRIMARY = 'primary'                                 # the home of the self-sufficient tools
PYXOUT = 'pyxfiles'                                 # <folder>/pyxfiles holds the builds
CALLER_SUBS = 2                                     # levels below the caller's folder
PARENT_SUBS = 1                                     # levels below a parent of the caller
SCRIPT_SUBS = 2                                     # levels below the script's folder
BIG_PARENT = int(42 * 4.2 // 1)                      # entries: a parent with more is not scanned
PRIMARY_DEPTH = 1                                   # levels searched inside a primary/
SEG_OK = re.compile(r'^[A-Za-z0-9_\-.()\[\]{};& ]+$')

#: Folder-name globs the search never enters. Extend with exclude().
SKIP = {'.py', PYXOUT, 'prev', 'zprev', '__pycache__', '.git', '.hg', '.svn', '.idea', '.vscode',
        '.tox', 'node_modules', 'site-packages', 'venv', '.venv', 'env', '.env', 'build',
        'dist', '*.egg-info', '*.dist-info'}


def exclude(*patterns):
    """Add folder-name globs the search must never descend into; returns the whole list."""
    SKIP.update(str(pattern) for pattern in patterns)
    return sorted(SKIP)


def barred(name):
    """Is a folder called `name` one the search never enters? (case-blind on Windows)"""
    return any(fnmatch.fnmatch(name, pattern) for pattern in SKIP)


def venv(path, name):
    """Is the folder `name` in `path` the root of a virtual environment?"""
    return os.path.isfile(os.path.join(path, name, 'pyvenv.cfg'))


# ---- where a search starts --------------------------------------------------------------
def anchor():
    """The folder of the script Python was started with (sys.argv[0]), so the result does
    not depend on where it was launched from. With no script (a console, python -c,
    stdin), or a script that is part of Python itself (python -m unittest), the current
    folder."""
    script = sys.argv[0] if sys.argv else ''
    if script.endswith('.py') and os.path.isfile(script):
        path = os.path.abspath(script)
        prefix = os.path.abspath(sys.base_prefix).lower() + os.sep
        if not path.lower().startswith(prefix):
            return Path(path).parent
    return Path.cwd()


def caller():
    """The folder of the module that called use, load, run or build: the first frame above
    this module that has a file of its own outside Python's installation. None in a
    console, python -c or stdin, where no file called."""
    prefix = os.path.abspath(sys.base_prefix).lower() + os.sep
    frame = sys._getframe(1)
    while frame is not None:
        name = frame.f_globals.get('__name__', '')
        file = frame.f_globals.get('__file__')
        if file and name != __name__ and 'importlib' not in name:
            path = os.path.abspath(file)
            if not path.lower().startswith(prefix):
                return Path(path).parent
        frame = frame.f_back
    return None


def allowed(folder):
    """May this folder be searched? Not a bare drive (C:\\ or /): at least one level
    below."""
    return len(folder.parts) >= 2


def crowded(folder):
    """Does a parent hold more than BIG_PARENT entries? Scanning below it costs seconds
    (the system temp folder has twenty thousand) for a match that is seldom there."""
    try:
        return len(os.listdir(folder)) > BIG_PARENT
    except OSError:
        return True


def steps(here):
    """[(root, depth)] in search order, for a caller in the folder `here` (or None). For
    each folder met: its own files (depth 0), its primary/ (1 deep), then its subfolders
    (the depth that folder gets). A folder is met once; a bare drive and a missing folder
    not at all."""
    folders = []
    if here is not None:
        folders.append((here, CALLER_SUBS))
        folders.extend((parent, PARENT_SUBS) for parent in here.parents)
    start = anchor()
    folders.append((start, SCRIPT_SUBS))
    folders.append((start.parent, PARENT_SUBS))
    parents = {*here.parents, start.parent} if here is not None else {start.parent}
    out = []
    seen = set()
    for root, depth in folders:
        if root in seen or not allowed(root) or not root.is_dir():
            continue
        seen.add(root)
        out.append((root, 0))
        out.append((root / PRIMARY, PRIMARY_DEPTH))
        if root in parents and root not in (here, start) and crowded(root):
            continue                                # too big to scan below: own files only
        out.append((root, depth))
    prefix = os.path.abspath(sys.base_prefix).lower() + os.sep
    for entry in sys.path:                          # step 5: what is on the path already
        root = Path(os.path.abspath(entry or '.'))
        if (root not in seen and allowed(root) and root.is_dir()
                and not str(root).lower().startswith(prefix)):
            seen.add(root)
            out.append((root, 0))
    return out


def candidates(root, name, maxdepth, suffix, want_dir):
    """<name><suffix> files (and, if want_dir, <name>/ folders) at or under `root`, no
    deeper than maxdepth levels. The descent skips the barred folders and virtual
    environments."""
    out = []
    root = str(root)
    if not os.path.isdir(root):
        return out
    for path, dirs, files in os.walk(root):
        rel_path = os.path.relpath(path, root)
        depth = 0 if rel_path == '.' else rel_path.count(os.sep) + 1
        dirs[:] = [d for d in dirs if not barred(d) and not venv(path, d)]
        if name + suffix in files:
            out.append(Path(path) / (name + suffix))
        if suffix == '.py' and name + '.pyx' in files:      # a module: its compiled form too
            out.append(Path(path) / (name + '.pyx'))
        if want_dir and depth < maxdepth and name in dirs:
            out.append(Path(path) / name)
        if depth >= maxdepth:
            dirs[:] = []                            # stop descending past the band
    return out


def closest(name, here, suffix='.py', want_dir=True):
    """The best match for `name`: the first step of the search that has any, then the
    shallowest below its root, then a .pyx before a .py of the same name, then the newest.
    None if there is none. A folder that is the caller's own, or one of its parents, never
    matches."""
    exempt = set() if here is None else {here, *here.parents}
    for root, depth in steps(here):
        found = [path for path in candidates(root, name, depth, suffix, want_dir)
                 if path not in exempt]
        if found:
            ranked = sorted((len(path.relative_to(root).parts), path.suffix != '.pyx',
                             -path.stat().st_mtime, str(path)) for path in found)
            return Path(ranked[0][3])
    return None


def locate(name, here=None):
    """The file `use` would load for the module `name`, as a Path: the same search as use and
    load (the shallowest match of the first step that has one, a .pyx before a .py, then the
    newest), but nothing is imported or built. None if there is none. `here` is the folder to
    search from; the default is the folder of the file that called locate. A report that
    shows the code that ran asks this."""
    return closest(name, caller() if here is None else Path(here), '.py', False)


def find(name, here):
    """(folders to add, module name) for `name`: a <name>.py gives its folder and the
    name; a folder <name>/ gives the folder (and its primary/ if it has one) and None;
    (None, None) if there is none."""
    best = closest(name, here)
    if best is None:
        return None, None
    if best.is_dir():
        return [best] + ([best / PRIMARY] if (best / PRIMARY).is_dir() else []), None
    return [best.parent], name


def addpath(folder, subs=False):
    """Put folder (and, if subs, its subfolders, 2 deep) first on sys.path, skipping the
    barred folders. A pyxfiles/ is never added by this: load adds the one that sits
    beside a .pyx. True if anything was added."""
    folder = str(folder)
    roots = [folder]
    if subs:
        roots = []
        for path, dirs, files in os.walk(folder):
            rel_path = os.path.relpath(path, folder)
            depth = 0 if rel_path == '.' else rel_path.count(os.sep) + 1
            dirs[:] = [d for d in dirs if not barred(d)]
            roots.append(path)
            if depth >= 2:
                dirs[:] = []
    added = False
    for root in roots:
        if root not in sys.path:
            sys.path.insert(0, root)
            added = True
    return added


# ---- printing -------------------------------------------------------------------------------
def rel(path):
    """A path relative to the current folder, anchored with '.', or absolute across
    drives."""
    try:
        relative = os.path.relpath(str(path), os.getcwd())
    except ValueError:
        return str(path)
    if relative == '.' or relative.startswith(('.' + os.sep, '..' + os.sep)):
        return relative
    return '.' + os.sep + relative


def tree(title, rows):
    """A title with `|__` children; the columns of a row line up."""
    cells = [row if isinstance(row, (list, tuple)) else (row,) for row in rows]
    ncol = max((len(cell) for cell in cells), default=0)
    width = [max((len(str(cell[i])) for cell in cells if i < len(cell)), default=0)
             for i in range(ncol)]
    out = [title]
    for cell in cells:
        line = '  '.join(str(cell[i]).ljust(width[i]) for i in range(len(cell)))
        out.append('   |__ ' + line.rstrip())
    return '\n'.join(out)


class Folders(list):
    """What use() found: a list of {item, full, status} that prints as a tree."""

    def __repr__(me):
        return tree('use', [(f"[{f['status']}]", f['item'],
                              '(file/folder not found)' if f['status'] == 'skip'
                              else rel(f['full'])) for f in me])


class Result(tuple):
    """(folders, ok) from use(); echoes as one tree unless silent. It still unpacks."""

    def __new__(cls, folders, ok, silent=False):
        me = super().__new__(cls, (folders, ok))
        me.silent = silent
        return me

    def __repr__(me):
        return '' if me.silent else repr(me[0])


class Loaded(dict):
    """What load() bound: {name: object}, printing as a tree of where each came from."""
    summary = ''

    def __repr__(me):
        return me.summary or dict.__repr__(me)


# ---- use -------------------------------------------------------------------------------------
def use(*args):
    """Find each item and add its folder to sys.path. See the module header."""
    here = caller()
    entries = []                                    # entry: [item, subs, mkdir]
    silent = False
    for token in args:
        token = str(token)
        if token.lower() == 'silent':
            silent = True
        elif token.startswith('+'):
            if not entries:
                raise ValueError(f'use: flag "{token}" appears before any item.')
            flag = token.lower()
            if flag == '+subs':
                entries[-1][1] = True
            elif flag == '+mkdir':
                entries[-1][2] = True
            else:
                raise ValueError(f'use: unknown flag "{token}".')
        else:
            entries.append([token, False, False])
    if not entries:
        entries = [[name, False, False] for name in DEFAULTS]

    folders = Folders()
    ok = True
    for item, subs, mkdir in entries:
        if item[:1] == '.':                         # create ./item, no path add
            check_segments(item[1:])
            full = Path.cwd() / item[1:]
            full.mkdir(parents=True, exist_ok=True)
            status = 'created'
        else:
            dirs, module = find(item, here)
            if dirs is None:
                if mkdir:                           # not found: create under cwd and add
                    check_segments(item)
                    full = Path.cwd() / item
                    full.mkdir(parents=True, exist_ok=True)
                    addpath(full, subs)
                    status = 'created'
                else:
                    full = item
                    status = 'skip'
                    ok = False
            else:
                full = dirs[0]
                hit = any([addpath(d, subs) for d in dirs])
                status = ('subs' if subs else 'added') if hit else 'ok'
        folders.append({'item': item, 'full': str(full), 'status': status})
    return Result(folders, ok, silent)


def check_segments(path):
    """A folder about to be created has clean segments (no '..', no odd characters)."""
    for segment in re.split(r'[/\\]', path):
        if segment in ('', '.', '..') or not SEG_OK.match(segment):
            raise ValueError(f'use: cannot create "{path}" (bad segment "{segment}").')


# ---- load ------------------------------------------------------------------------------------
def public_api(module, name):
    """The names load() binds from a module: its __all__, else the eponymous name, else
    the first class or function defined in it."""
    if getattr(module, '__all__', None) is not None:
        return list(module.__all__)
    if hasattr(module, name):
        return [name]
    for symbol, obj in vars(module).items():
        if (not symbol.startswith('_') and (inspect.isclass(obj) or inspect.isfunction(obj))
            and getattr(obj, '__module__', None) == name):
            return [symbol]
    return []


def modnames(folder):
    """(.py names, .pyx names) importable from one folder: not _private, not setup.py."""
    names = sorted(os.listdir(folder))
    py = [n[:-3] for n in names
          if n.endswith('.py') and not n.startswith('_') and n != 'setup.py']
    pyx = [n[:-4] for n in names if n.endswith('.pyx') and not n.startswith('_')]
    return [n for n in py if n not in pyx], pyx           # one version of a name: the .pyx


def walk_units(folder, maxdepth=2):
    """[(folder, py names, pyx names)] for the folder and its subfolders, maxdepth deep,
    skipping the barred folders."""
    units = []
    folder = str(folder)
    for path, dirs, files in os.walk(folder):
        rel_path = os.path.relpath(path, folder)
        depth = 0 if rel_path == '.' else rel_path.count(os.sep) + 1
        dirs[:] = [d for d in dirs if not barred(d) and not venv(path, d)]
        py, pyx = modnames(path)
        if py or pyx:
            units.append((path, py, pyx))
        if depth >= maxdepth:
            dirs[:] = []
    return units


#: What a .pyx takes from its own folder: `cimport x` / `from x cimport y` (x.pxd) and
#: `include "f"`. Cython's own and the standard declarations (cpython, libc) are not there.
NEEDS = re.compile(r'''^[ \t]*(?:from[ \t]+([\w.]+)[ \t]+cimport|cimport[ \t]+([\w., \t]+)|'''
                   r'''include[ \t]+['"]([^'"\n]+)['"])''', re.M)


def needs(folder, name):
    """The files of this folder a .pyx is built from besides itself: its own <name>.pxd, the
    .pxd of each module it cimports, the files it includes. Only those that exist."""
    wanted = [name + '.pxd']
    try:
        with open(os.path.join(folder, name + '.pyx'), encoding='utf-8', errors='replace') as f:
            text = f.read()
    except OSError:
        return []
    for found in NEEDS.finditer(text):
        if found.group(1):
            modules = [found.group(1)]
        elif found.group(2):
            modules = [m.split(' as ')[0].strip() for m in found.group(2).split(',')]
        else:
            modules = []
            wanted.append(found.group(3))
        wanted.extend(m.replace('.', os.sep) + '.pxd' for m in modules if m)
    return [os.path.join(folder, w) for w in dict.fromkeys(wanted)
            if os.path.isfile(os.path.join(folder, w))]


def pyx_stale(folder, name):
    """Does <name>.pyx need compiling: no build for THIS Python, or the build is older than
    the source or than a file it is built from (see needs): a changed .pxd makes every .pyx
    that cimports it stale, which is how its dependents are rebuilt."""
    pyx = os.path.join(folder, name + '.pyx')
    if not os.path.isfile(pyx):
        return False                                # not a compiled module
    source = max([os.path.getmtime(pyx)] + [os.path.getmtime(f) for f in needs(folder, name)])
    for suffix in importlib.machinery.EXTENSION_SUFFIXES:
        built = os.path.join(folder, PYXOUT, name + suffix)
        if os.path.isfile(built):
            return os.path.getmtime(built) < source
    return True


# ---- compile: a .pyx becomes a module -------------------------------------------
# Why we run gcc ourselves: setuptools ran the same commands three layers down, where
# they could not be given CREATE_NO_WINDOW, so a server (pythonw.exe, no console) showed
# a window for each gcc. Here every program is started hidden. Windows and a MinGW gcc
# on PATH only; a .pyd that a process has loaded is locked. Each step is explained where
# it runs, each flag where it is set.

COMPILER = 'gcc'                                    # found through PATH
# Compile step (name.c -> name.o):
#   -shared  the output is a library (a DLL), not a program.
#   -O1      light optimisation for speed. On the lexer (z_sandbox/b_optlevel) -O0 took
#            15.8 ms, -O1 11.2, -O2 11.6, -O3 11.2: the time is in calls into Python.
#   -w       no warnings: Cython's C draws notes nobody can act on. Errors still stop.
COMPILE_FLAGS = ['-shared', '-O1', '-w']
# Link step (name.o -> name.pyd): -s strips the symbol table (smaller file, same speed;
# a crash in the C shows addresses, not names).
LINK_FLAGS = ['-shared', '-s']
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
NUMPY = re.compile(r'^[ \t]*(?:cimport[ \t]+numpy|from[ \t]+numpy[ \t]+cimport)', re.M)


class CompileError(Exception):
    """A .pyx that did not become a module: names the file, the step and its messages;
    `code` is the step's return code (127: gcc or Cython missing)."""

    def __init__(me, message, code=1):
        super().__init__(message)
        me.code = code


def hidden(command):
    """Run a program with no window: (return code, messages); 127 if not started."""
    try:
        done = subprocess.run(command, capture_output=True, text=True,
                              creationflags=NO_WINDOW)
    except OSError as error:
        return 127, f'{command[0]}: {error}'
    return done.returncode, (done.stderr or '') + (done.stdout or '')


def compile_one(pyx):
    """One .pyx to <folder>/pyxfiles/<name><suffix>: Cython, compile, link (.c in
    pyxfiles, .o and .def in pyxfiles/_tmp). Raises CompileError."""
    pyx = os.path.abspath(pyx)
    folder, name = os.path.split(pyx)
    name = os.path.splitext(name)[0]
    if not os.path.isfile(pyx):
        raise CompileError(f'{name}: {pyx} is not there')
    out = os.path.join(folder, PYXOUT)
    os.makedirs(os.path.join(out, '_tmp'), exist_ok=True)
    c_file, obj = os.path.join(out, name + '.c'), os.path.join(out, '_tmp', name + '.o')
    symbols = os.path.join(out, '_tmp', name + '.def')
    pyd = os.path.join(out, name + sysconfig.get_config_var('EXT_SUFFIX'))

    # gcc must be there, and not a Cygwin one (its binaries need cygwin1.dll).
    code, text = hidden([COMPILER, '-dumpmachine'])
    if code == 127:
        raise CompileError(f'{name}: gcc was not found on PATH ({text.strip()})', 127)
    if text.strip().endswith('cygwin'):
        raise CompileError(f'{name}: gcc is a Cygwin build; a .pyd needs MinGW', code or 1)

    # Step 1, Cython: name.pyx -> name.c, here. A cimport is found in the .pyx's folder.
    try:
        from Cython.Compiler import Main
    except ImportError as error:
        raise CompileError(f'{name}: Cython is not installed ({error})', 127)
    messages = io.StringIO()
    with contextlib.redirect_stderr(messages):
        result = Main.compile(pyx, language_level=3, output_file=c_file,
                              include_path=[folder], full_module_name=name)
    if result.num_errors:
        raise CompileError(f'{name}.pyx: Cython found {result.num_errors} error(s)\n'
                           f'{messages.getvalue()[-800:]}', 1)

    # Step 2, compile: the C text becomes machine code; the calls into Python are left
    # as blanks. -I the header folders (numpy's too, for a .pyx that cimports it),
    # -c stop before linking, -o the output.
    includes = [sysconfig.get_paths()['include']]
    with open(pyx, encoding='utf-8', errors='replace') as f:
        if NUMPY.search(f.read()):
            import numpy
            includes.append(numpy.get_include())
    compiling = [COMPILER, *COMPILE_FLAGS, *['-I' + d for d in includes],
                 '-c', c_file, '-o', obj]

    # Step 3, link: fills the blanks from the Python library (-L its folders, -l its
    # name) and joins name.o and the .def file, which names the export PyInit_<name>,
    # the function Python calls on import, into name.pyd.
    with open(symbols, 'w', encoding='utf-8', newline='\n') as f:
        f.write(f'LIBRARY {os.path.basename(pyd)}\nEXPORTS\nPyInit_{name}\n')
    base = sys.base_prefix
    folders = [os.path.join(base, 'libs'), base, os.path.join(base, 'PCbuild', 'amd64')]
    free = 't' if sysconfig.get_config_var('Py_GIL_DISABLED') else ''
    linking = [COMPILER, *LINK_FLAGS, obj, symbols, *['-L' + d for d in folders if os.path.isdir(d)],
               f'-lpython{sys.version_info.major}{sys.version_info.minor}{free}', '-o', pyd]

    for step, command in (('compile', compiling), ('link', linking)):
        code, text = hidden(command)
        if code:
            raise CompileError(f'{name}.pyx: the {step} step failed (gcc returned '
                               f'{code})\n{text[-800:]}', code)


def compile(files):
    """Compile .pyx file(s) (a path or a list) into <folder>/pyxfiles/ for this Python.
    Returns 0 when all were built. Every file is tried; then CompileError names each
    failure, its `code` that of the first."""
    files = [str(f) for f in ([files] if isinstance(files, (str, os.PathLike)) else files)]
    print(f'  use: compiling {", ".join(os.path.basename(f) for f in files)} ...')
    failed, code = [], 0
    for pyx in files:
        try:
            compile_one(pyx)
        except CompileError as error:
            failed.append(str(error))
            code = code or error.code
    importlib.invalidate_caches()           # the finders listed the folder before
    if failed:
        raise CompileError('\n'.join(failed), code)
    return 0


STAMPS = {}                                         # module name -> (mtime_ns, size) imported


def stat_of(module):
    """(mtime_ns, size) of a module's source file, or None when it has none."""
    file = getattr(module, '__file__', None)
    try:
        info = os.stat(file)
    except (TypeError, OSError):
        return None
    return info.st_mtime_ns, info.st_size


def stamp(module, name):
    """Remember the source file's state the first time a module is seen; changed() renews
    it. A module imported before use saw it is checked against its .pyc, whose header
    holds the source's mtime and size at import: an edit made since is not lost. (With
    PYTHONDONTWRITEBYTECODE there is no .pyc and such a module is taken as current.)"""
    if name in STAMPS:
        return
    now = stat_of(module)
    cached = getattr(module, '__cached__', None)
    if now is not None and cached and name in sys.modules:
        try:
            with open(cached, 'rb') as handle:
                head = handle.read(16)
            seen = (int.from_bytes(head[8:12], 'little') * 1_000_000_000,
                    int.from_bytes(head[12:16], 'little'))
            if seen[1] != now[1] or seen[0] != now[0] // 1_000_000_000 * 1_000_000_000:
                STAMPS[name] = (0, 0)               # edited since import: changed() says so
                return
        except OSError:
            pass                                    # no .pyc: taken as current
    STAMPS[name] = now


def changed(module, name):
    """True when the source file differs from the state last stamped (O(1): one stat)."""
    now = stat_of(module)
    before = STAMPS.get(name)
    if now is not None and before is not None and now != before:
        STAMPS[name] = now
        return True
    return False


def interactive():
    """True in a console (python -i, IDLE, Spyder, IPython, Jupyter), where nothing
    restarts the process after an edit."""
    return hasattr(sys, 'ps1') or bool(sys.flags.interactive) or 'ipykernel' in sys.modules


class Loading:
    """The state of one load() call: where names go, what went, what could not."""

    def __init__(me, into, reload):
        me.into = into
        me.reload = reload
        me.reloaded = []                            # pure modules reloaded in this call
        me.loaded = {}
        me.skipped = []                             # everything that could not be loaded
        me.failed = []                              # ... of what was asked for by name
        me.built = set()                            # folders built in this call
        me.singles = set()                          # names asked for singly

    def inject(me, module, name):
        """Bind a module's public names into the destination."""
        for symbol in public_api(module, name):
            obj = getattr(module, symbol, None)
            if obj is not None:
                me.into[symbol] = obj
                me.loaded[symbol] = obj

    def fail(me, name, why, hard=False):
        """Note that `name` could not be loaded; a name asked for singly is a failure, and so is
        any one that hard says (a stale compiled module is never quietly used)."""
        text = f'{name} ({why})'
        me.skipped.append(text)
        if hard or name in me.singles:
            me.failed.append(text)

    def pure(me, folder, name):
        """Import the pure-Python module `name` and bind it. One already imported is
        reused, unless reload is on and its file changed since it was imported, when it
        is reloaded in place. One imported from another folder is said so."""
        module = sys.modules.get(name)
        try:
            if module is None:
                module = importlib.import_module(name)
            else:
                stamp(module, name)
                file = getattr(module, '__file__', None)
                there = os.path.dirname(os.path.abspath(file)) if file else ''
                if there and (os.path.normcase(there)
                              != os.path.normcase(os.path.abspath(folder))):
                    print(f'  use: WARNING {name} was imported from {rel(there)}, not '
                          f'from {rel(folder)}, which was found.')
                elif me.reload and changed(module, name):
                    stale = getattr(module, '__cached__', None)
                    if stale and os.path.exists(stale):         # a .pyc dates the source to the
                        os.unlink(stale)                        # second: an edit within the same
                    module = importlib.reload(module)           # second would be read as old
                    me.reloaded.append(name)
        except Exception as err:                    # one bad module must not stop the rest
            me.fail(name, f'{type(err).__name__}: {err}')
            return
        stamp(module, name)
        me.inject(module, name)

    def compiled(me, folder, pyx_names):
        """Build the folder's stale .pyx (once, in a fresh process), then import and bind
        the compiled modules. A stale build is not used if the rebuild failed."""
        addpath(os.path.join(folder, PYXOUT))
        stale = [name for name in pyx_names
                 if name not in sys.modules and pyx_stale(folder, name)]
        broken = set()
        if stale and folder not in me.built:
            me.built.add(folder)
            try:
                compile([os.path.join(folder, name + '.pyx') for name in stale])
            except CompileError as error:
                broken = set(stale)
                for name in stale:
                    me.fail(name, f'build failed: {str(error)[-600:]}')
        for name in pyx_names:
            if name in broken:
                continue
            if name in sys.modules:                 # imported: a compiled module cannot be reloaded
                if pyx_stale(folder, name):         # and a newer .pyx than the build in use is a failure
                    me.fail(name, f'{name}.pyx is newer than the build this process imported: '
                                  f'run again, so that the new build is imported', hard=True)
                    continue
                me.inject(sys.modules[name], name)
                continue
            try:
                module = importlib.import_module(name)
            except Exception as err:
                me.fail(name, f'{type(err).__name__}: {err}')
                continue
            me.inject(module, name)

    def unit(me, folder, py_names, pyx_names):
        """Import one folder's modules and bind their names."""
        folder = str(folder)
        addpath(folder)
        for name in py_names:
            me.pure(folder, name)
        if pyx_names:
            me.compiled(folder, pyx_names)


def load(*items, silent=True, into=None, reload=None):
    """use() each item and import it, binding its public names. See the module header."""
    here = caller()
    if reload is None:
        reload = interactive()
    state = Loading(into if into is not None else sys._getframe(1).f_globals, reload)
    entries = []                                    # (item, subs) in call order
    for token in items or DEFAULTS:
        token = str(token)
        if token.startswith('+'):
            if token.lower() == '+subs' and entries:
                entries[-1] = (entries[-1][0], True)
            continue
        entries.append((token, False))

    for item, subs in entries:
        if item[:1] == '.' or item.lower() == 'silent':
            use(item, 'silent')                     # create-only item, or the silent token
            continue
        dirs, module = find(item, here)
        if dirs is not None:
            for d in dirs:
                addpath(d)
            folder = str(dirs[0])
            if module is not None:                  # a single module: its .pyx if it has one
                state.singles.add(module)
                compiled = os.path.isfile(os.path.join(folder, module + '.pyx'))
                units = [(folder, [] if compiled else [module], [module] if compiled else [])]
            elif subs:                              # the folder and its subfolders
                units = walk_units(folder, 2)
            else:                                   # the folder's own .py and .pyx
                py, pyx = modnames(folder)
                units = [(folder, py, pyx)]
        else:                                       # maybe a compiled module alone
            state.singles.add(item)
            pyx = closest(item, here, '.pyx', False)
            if pyx is None:
                state.fail(item, f'not found from {here or anchor()}')
                continue
            units = [(str(pyx.parent), [], [item])]
        for unit in units:
            state.unit(*unit)

    result = Loaded(state.loaded)
    rows = []
    for symbol, obj in state.loaded.items():
        module = sys.modules.get(getattr(obj, '__module__', '?'))
        file = rel(module.__file__) if module and getattr(module, '__file__', None) else ''
        rows.append((symbol, file))
    if state.skipped:
        rows.append(('skipped', '; '.join(state.skipped)))
    result.summary = tree('use.load', rows)
    if state.failed:
        raise ImportError('use.load: ' + '; '.join(state.failed))
    if state.reloaded:
        print(f'  use.load: reloaded {", ".join(state.reloaded)}')
    if state.skipped:                               # a folder's bad modules: say so
        print(f'  use.load: skipped {"; ".join(state.skipped)}')
    if not silent:
        print(result.summary)
    return result


# ---- build, run ---------------------------------------------------------------------------
def build(*items):
    """Rebuild the .pyx of each item: the one module when the item names a module, every .pyx
    of the folder when it names a folder. True if all built."""
    here = caller()
    ok_all = True
    seen = set()
    for item in items or DEFAULTS:
        item = str(item)
        if item[:1] == '.':
            continue
        dirs, module = find(item, here)
        names = ()
        if dirs is not None:
            folder = str(dirs[0])
            if module is not None and os.path.isfile(os.path.join(folder, module + '.pyx')):
                names = (module,)
        else:
            pyx = closest(item, here, '.pyx', False)
            if pyx is None:
                print(f"  use.build: no .pyx found for '{item}'")
                ok_all = False
                continue
            folder = str(pyx.parent)
            names = (item,)
        if (folder, names) in seen:
            continue
        seen.add((folder, names))
        names = names or [os.path.splitext(f)[0] for f in sorted(os.listdir(folder))
                          if f.endswith('.pyx')]
        try:
            compile([os.path.join(folder, name + '.pyx') for name in names])
            print(f'  use.build: {item} done')
        except CompileError as error:
            print(f'  use.build: {item} FAILED\n{str(error)[-600:]}')
            ok_all = False
    return ok_all


def reload_project():
    """Drop the project's pure-Python modules from sys.modules so the next import sees
    edits: not compiled ones, not this one, nothing outside the folder of use."""
    root = str(HERE)
    for name in list(sys.modules):
        if name == __name__:
            continue
        file = getattr(sys.modules.get(name), '__file__', None)
        if not file or not file.endswith('.py'):
            continue
        try:
            if os.path.commonpath([root, os.path.abspath(file)]) == root:
                del sys.modules[name]
        except ValueError:
            pass                                    # a different drive: not ours


def run(name, *args, reload=True, silent=True):
    """Run <name>.py in a private module and return main(*args), else the eponymous
    function's result, else the module namespace. See the module header."""
    here = caller()
    dirs, module = find(name, here)
    if dirs is None or module is None:
        raise FileNotFoundError(f'run: no script "{name}.py" found from '
                                f'{here or anchor()}.')
    for d in dirs:
        addpath(d)
    file = Path(dirs[0]) / (name + '.py')
    if reload:
        reload_project()
    spec = importlib.util.spec_from_file_location(name, str(file))
    private = importlib.util.module_from_spec(spec)     # not put in sys.modules
    argv0 = sys.argv
    sys.argv = [str(file)] + [str(arg) for arg in args]
    try:
        spec.loader.exec_module(private)
        if callable(getattr(private, 'main', None)):
            result = private.main(*args)
        elif callable(getattr(private, name, None)):
            result = getattr(private, name)(*args)
        else:
            result = private
    finally:
        sys.argv = argv0
    if not silent:
        print(f"  use.run: {name}({', '.join(map(repr, args))})")
    return result


def bind_console():
    """In a console, a bare `import use` binds the verbs into the console (no hook, no
    output, nothing already there is replaced). A script is left alone."""
    main = sys.modules.get('__main__')
    if main is not None and not hasattr(main, '__file__') and interactive():
        for symbol in __all__:
            main.__dict__.setdefault(symbol, globals()[symbol])


bind_console()
