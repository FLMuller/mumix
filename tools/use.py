r"""use2.py -- find project code by NAME, put its folder on the path, import it.

    use('vaults')          put the folder `vaults` on sys.path: `import slot` works
    use('slot')            put the folder that holds slot.py (or slot.pyx) on it
    use('vaults', '+subs') the folder and its subfolders (2 deep)
    use('data', '+mkdir')  create ./data if there is none, and put it on the path
    use('.results')        create ./results (not put on the path)
    load('slot')           use('slot'), build slot.pyx if it is stale, import it, and
                           bind the names of its __all__ in the caller: the same as
                           `from slot import *`
    load(asmodule=['slot'])  the same, but bind one name, `slot`, a namespace of the
                           __all__ names and of __name__, __file__, __doc__ and
                           __all__: `slot.f()` works, `slot._helper` does not
    locate('slot')         the file load('slot') would import, as a Path, or None

    use with no item means `primary`; load with nothing to load does nothing. Nothing
    is returned. A module to load needs an __all__ (no __all__ is an ImportError). The
    first item that cannot be found, built or imported raises (a failed build is a
    CompileError, an ImportError that carries the messages of the step that failed; a
    gcc that is not there fails as Python reports it). There is no into= and no
    'silent': a name that is neither a module nor a folder is not found.

    Importing use puts its own folder on sys.path, so a module imported after that
    can write `import use`. The first import still needs the folder on the path:
    the program that starts the process sees to that.

THE SEARCH  (the first step that has a match wins, then the shallowest match, then
a .pyx before a .py, then the newest)

    1  the CALLER's folder (the file that called use or load): its files, its
       `primary/` (1 deep), its subfolders (2 deep)
    2  each PARENT of the caller's folder, nearest first: files, `primary/`,
       subfolders (1 deep); a parent with more than BIG_PARENT entries is not
       scanned below
    3  the HOME folder (that of the script Python was started with; the current
       folder in a console or `python -c`), then its parent: the same
    4  the folders already on sys.path (not Python's own): their files only

    An item is `<name>.py`, `<name>.pyx` or a folder `<name>`. Never entered: SKIP,
    a folder with pyvenv.cfg, a bare drive.

TRAPS
    * Two copies of a name in reach: the nearest wins, so an old copy hides the
      new one.
    * A compiled module cannot be rebuilt while a process has it loaded: run again.
    * A module that imports a sibling needs it on the path: use() its folder, or
      load() the sibling first.
    * asmodule binds a namespace, a snapshot of the __all__ names as they were when
      load ran; it is not the module. A name the module rebinds later is not seen
      through it, and mock.patch must patch sys.modules['slot'], not the namespace.
    * load binds into the globals of the module that calls it: call it at the top
      of a module, not from a function that is meant to bind into its own caller.

VERSION  use2 3.1 (2026-11-05): load(*items, asmodule=()) binds the __all__ names of its
         items in the caller, and a namespace of them (with __name__, __file__,
         __doc__, __all__) for each asmodule item; caller() returns the places and
         the globals of the calling frame, the one frame read; units takes the places.
         use2 3.0 (2026-11-05): use and load rebuilt on one search (caller, closest)
         and one walk (units, the one generator). load imports, binds nothing,
         returns nothing and stops at the first error; compile is one private
         function and one gcc command. Gone: run, build, exclude, anchor, into=,
         reload=, Loading and the console features. Before: use 2.12
         (prev/use_current.py).
"""
import fnmatch
import importlib
import importlib.util
import os
import re
import subprocess
import sys
import sysconfig
import types
from pathlib import Path

__all__ = ['use', 'load', 'locate']

# Private to use2.py: nothing outside it reads these.
priv = types.SimpleNamespace(
    PRIMARY='primary',              # the home of the self-sufficient tools, and
                                    # the place when no item is given
    MYPARENT=Path(__file__).resolve().parent,   # the folder of this file
    PYXOUT='pyxfiles',              # <folder>/pyxfiles holds the builds
    CALLER_SUBS=2,                  # levels below the caller's folder
    PARENT_SUBS=1,                  # levels below a parent of the caller
    HOME_SUBS=2,                    # levels below the home folder
    PRIMARY_DEPTH=1,                # levels searched inside a primary/
    BIG_PARENT=176,                 # entries: a parent with more is not scanned
    SEG_OK=re.compile(r'^[A-Za-z0-9_\-.()\[\]{};& ]+$'),    # a folder name to create
    SKIP={'.py', 'pyxfiles', 'prev', 'zprev', '__pycache__', '.git', '.hg', '.svn',
          '.idea', '.vscode', '.tox', 'node_modules', 'site-packages', 'venv',
          '.venv', 'env', '.env', 'build', 'dist', '*.egg-info',
          '*.dist-info'},           # folder-name globs the search never enters
    # What a .pyx takes from its own folder: `cimport x` / `from x cimport y`
    # (x.pxd) and `include "f"`. Cython's own declarations are not there.
    NEEDS=re.compile(r'''^[ \t]*(?:from[ \t]+([\w.]+)[ \t]+cimport|'''
                     r'''cimport[ \t]+([\w., \t]+)|'''
                     r'''include[ \t]+['"]([^'"\n]+)['"])''', re.M),
    # Why we run gcc ourselves: setuptools ran the same commands three layers
    # down, where they could not be given CREATE_NO_WINDOW, so a server
    # (pythonw.exe, no console) showed a window for each gcc. Here it is started
    # hidden. Windows and a MinGW gcc on PATH only; a .pyd that a process has
    # loaded is locked.
    COMPILER='gcc',                 # found through PATH
    NO_WINDOW=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
    # The flags of the one gcc command (it compiles and links):
    #   -shared  the output is a library (a DLL), not a program.
    #   -O1      light optimisation for speed. On the lexer (z_sandbox/b_optlevel)
    #            -O0 took 15.8 ms, -O1 11.2, -O2 11.6, -O3 11.2: the time is in
    #            calls into Python.
    #   -w       no warnings: Cython's C draws notes nobody can act on. Errors
    #            still stop the build.
    #   -s       strip the symbol table: a smaller file at the same speed; a
    #            crash in the C shows addresses, not names.
    GCC_FLAGS=['-shared', '-O1', '-w', '-s'])


class CompileError(ImportError):
    """A .pyx that did not become a module: names the file, the step and the
    messages of that step."""


# ---- where a search looks ---------------------------------------------------
def caller(here=None):
    """(places, scope) for the file that called use, load or locate. places: where
    the search looks, [(folder, depth)] in order, the caller's own folder first. That
    folder is the first frame above this module with a file of its own outside
    Python's installation (none in a console, python -c or stdin; a `here` given
    replaces the frame). For each folder met: its own files (depth 0), its primary/,
    then its subfolders (the depth that folder gets); each folder once, a bare drive
    and a missing one not at all. A big parent (BIG_PARENT entries) gives its own
    files and primary/ only. Last, the folders already on sys.path. scope: the
    globals of the first frame above this module that is not Python's own (a console
    has no file but has scope), which is where load binds names; None when `here` is
    given. This is the one frame read: the caller does not pass its own location, so
    no call site has to."""
    python = os.path.abspath(sys.base_prefix).lower() + os.sep
    frame = sys._getframe(1) if here is None else None
    scope = None
    while frame is not None:
        name = frame.f_globals.get('__name__', '')
        file = frame.f_globals.get('__file__')
        own = not file or not os.path.abspath(file).lower().startswith(python)
        if own and name != __name__ and 'importlib' not in name:
            scope = scope or frame.f_globals
            if file:
                here = Path(os.path.abspath(file)).parent
                break
        frame = frame.f_back
    # The home folder: that of the script Python was started with (sys.argv[0]), or
    # the current folder in a console, python -c or stdin, or when the script is
    # part of Python itself.
    script = sys.argv[0] if sys.argv else ''
    home = Path.cwd()
    if script.endswith('.py') and os.path.isfile(script):
        if not os.path.abspath(script).lower().startswith(python):
            home = Path(os.path.abspath(script)).parent
    folders = [(home, priv.HOME_SUBS), (home.parent, priv.PARENT_SUBS)]
    parents = {home.parent}
    if here is not None:
        up = [(parent, priv.PARENT_SUBS) for parent in here.parents]
        folders = [(here, priv.CALLER_SUBS), *up, *folders]
        parents |= set(here.parents)
    seen, places = set(), []
    for root, depth in folders:
        if root in seen or len(root.parts) < 2 or not root.is_dir():
            continue
        seen.add(root)
        places += [(root, 0), (root / priv.PRIMARY, priv.PRIMARY_DEPTH)]
        if (root not in parents or root in (here, home)
                or len(os.listdir(root)) <= priv.BIG_PARENT):
            places.append((root, depth))
    for entry in sys.path:
        root = Path(os.path.abspath(entry or '.'))
        if (root not in seen and len(root.parts) >= 2 and root.is_dir()
                and not str(root).lower().startswith(python)):
            seen.add(root)
            places.append((root, 0))
    return places, scope


def tree(root, depth):
    """[(path, dirs, files)] of the folder and its subfolders `depth` levels down,
    one pruned walk, for the search and for '+subs'. Never entered: the SKIP
    folders and a virtual environment (a folder with pyvenv.cfg)."""
    found = []
    for path, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs
                   if not os.path.isfile(os.path.join(path, d, 'pyvenv.cfg'))
                   and not any(fnmatch.fnmatch(d, p) for p in priv.SKIP)]
        found.append((Path(path), list(dirs), files))
        if len(Path(path).relative_to(root).parts) >= depth:
            dirs[:] = []
    return found


def closest(name, places, folders=True):
    """The best match for `name`: a <name>.py, a <name>.pyx and, if `folders`, a
    folder <name>. The first of `places` (from caller(), made once) that has any
    wins, then the shallowest below its root, then a .pyx, then the newest. None
    if there is none."""
    for root, depth in places:
        found = []
        for path, dirs, files in tree(root, depth):
            found += [path / (name + ext) for ext in ('.py', '.pyx')
                      if name + ext in files]
            level = len(path.relative_to(root).parts)
            if folders and level < depth and name in dirs:
                found.append(path / name)
        if found:
            return min(found, key=lambda p: (len(p.relative_to(root).parts),
                                             p.suffix != '.pyx',
                                             -p.stat().st_mtime, str(p)))
    return None


def locate(name, here=None):
    """The file load('name') would import (the .pyx when there is one, else the
    .py), found by the same search, or None. `here` is the folder to search from;
    the default is the folder of the caller."""
    return closest(name, caller(None if here is None else Path(here))[0], folders=False)


# ---- the walk both verbs make -----------------------------------------------
def addpath(folder):
    """Put a folder first on sys.path unless it is there."""
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))


addpath(priv.MYPARENT)            # the first import of use makes it importable


def create(path):
    """Create ./path under the current folder (clean segments only); return it."""
    for segment in re.split(r'[/\\]', path):
        if segment in ('', '.', '..') or not priv.SEG_OK.match(segment):
            raise ValueError(f'use: cannot create "{path}" (bad segment '
                             f'"{segment}").')
    full = Path.cwd() / path
    full.mkdir(parents=True, exist_ok=True)
    return full


def flags(items):
    """[[item, subs, mkdir]] from the arguments of use and load: a '+subs' or
    '+mkdir' flag belongs to the item before it. No item means `primary`."""
    entries = []
    for token in map(str, items or [priv.PRIMARY]):
        if token.startswith('+'):
            if not entries or token.lower() not in ('+subs', '+mkdir'):
                raise ValueError(f'use: flag "{token}" must be +subs or +mkdir, '
                                 f'after an item.')
            entries[-1][1 if token.lower() == '+subs' else 2] = True
        else:
            entries.append([token, False, False])
    return entries


def units(items, places):
    """The one walk, of use and load, over the `places` caller() found. For each
    item: find it, create it if asked, put its folder on sys.path, and yield
    (folder, module names): the one name of a module item, or the importable names
    of a folder (not _private, not setup.py; a .pyx and a .py of one name are one
    module). ImportError if not found."""
    for item, subs, mkdir in flags(items):
        if item.startswith('.'):               # create ./item, nothing on the path
            create(item[1:])
            continue
        best = closest(item, places) or (create(item) if mkdir else None)
        if best is None:
            raise ImportError(f"use: '{item}' not found from {places[0][0]}")
        if not best.is_dir():                       # a module: its folder, its name
            addpath(best.parent)
            yield best.parent, [item]
            continue
        if (best / priv.PRIMARY).is_dir():
            addpath(best / priv.PRIMARY)
        for path in [p for p, _, _ in tree(best, 2)] if subs else [best]:
            addpath(path)
            names = [n for n in sorted(os.listdir(path)) if not n.startswith('_')
                     and n != 'setup.py' and n.endswith(('.py', '.pyx'))]
            yield path, sorted({n.rsplit('.', 1)[0] for n in names})


def use(*items):
    """Put the folder of each item on sys.path (see the header); create the
    folders asked for."""
    list(units(items, caller()[0]))     # the walk does the work as it is iterated


def imported(items, places):
    """Each module the items name: found and put on the path (units), its .pyx built
    when it is stale, and imported. Warns when a module came from another folder
    than the one the search found."""
    for folder, names in units(items, places):
        for name in names:
            if (folder / (name + '.pyx')).is_file():
                if stale(folder, name):
                    compile(folder, name)
                addpath(folder / priv.PYXOUT)
            module = importlib.import_module(name)
            file = vars(module).get('__file__')
            there = Path(file).parent if file else folder
            there = there.parent if there.name == priv.PYXOUT else there
            if os.path.normcase(str(there)) != os.path.normcase(str(folder)):
                print(f'  use: WARNING {name} was imported from {there}, not from '
                      f'{folder}, which was found.')
            yield module


def load(*items, asmodule=()):
    """use() each item, bring its .pyx up to date, import its modules and bind them
    in the caller (see the header). An item binds the names of its __all__, as
    `from x import *` does; an asmodule item binds one name, x, a namespace of those
    names and of __name__, __file__, __doc__ and __all__. Returns nothing; the first
    failure raises (a failed build is a CompileError, an ImportError)."""
    places, scope = caller()
    for source, as_namespace in ((items, False), (asmodule, True)):
        if not source:                  # an empty list is nothing to load, not `primary`
            continue
        for module in imported(source, places):
            names = vars(module).get('__all__')
            if names is None:
                raise ImportError(f'use: {module.__name__} has no __all__')
            missing = [name for name in names if name not in vars(module)]
            if missing:
                raise ImportError(f'use: {module.__name__}.__all__ names {missing[0]}, '
                                  f'which the module does not define')
            got = {name: vars(module)[name] for name in names}
            if as_namespace:
                got.update(__name__=module.__name__,
                           __file__=vars(module).get('__file__'),
                           __doc__=module.__doc__, __all__=list(names))
                scope[module.__name__] = types.SimpleNamespace(**got)
            else:
                scope.update(got)


# ---- a .pyx becomes a module --------------------------------------------------
def stale(folder, name):
    """Does <name>.pyx need compiling: no build for THIS Python, or the build is
    older than the .pyx or than a file it is built from (its own .pxd, the .pxd of
    each module it cimports, the files it includes)."""
    pyx = folder / (name + '.pyx')
    needs = [pyx, folder / (name + '.pxd')]
    text = pyx.read_text(encoding='utf-8', errors='replace')
    for found in priv.NEEDS.finditer(text):
        for m in (found.group(2) or found.group(1) or '').split(','):
            if m.strip():
                m = m.split(' as ')[0].strip().replace('.', os.sep)
                needs.append(folder / (m + '.pxd'))
        needs += [folder / found.group(3)] if found.group(3) else []
    pyd = folder / priv.PYXOUT / (name + sysconfig.get_config_var('EXT_SUFFIX'))
    newest = max(p.stat().st_mtime for p in needs if p.is_file())
    return not pyd.is_file() or pyd.stat().st_mtime < newest


def compile(folder, name):
    """<folder>/<name>.pyx to <folder>/pyxfiles/<name><suffix>: Cython, then one gcc
    command, both run from a batch file written for this build. Raises CompileError
    with the messages of the step that failed, and ImportError if the module is
    already imported (a loaded .pyd cannot be replaced). The .c is removed after a
    good build, the .bat always."""
    pyx = folder / (name + '.pyx')
    out = folder / priv.PYXOUT
    pyd = out / (name + sysconfig.get_config_var('EXT_SUFFIX'))
    if name in sys.modules:
        raise ImportError(f'use: {name}.pyx is newer than the build this process '
                          f'imported: run again, to import the new build')
    out.mkdir(exist_ok=True)
    c_file = out / (name + '.c')
    bat = out / 'tmpcompile.bat'

    # gcc must be there, and not a Cygwin one (its binaries need cygwin1.dll).
    try:
        target = subprocess.check_output([priv.COMPILER, '-dumpmachine'], text=True,
                                         creationflags=priv.NO_WINDOW)
    except OSError as error:
        raise CompileError(f'{name}: gcc was not found ({error})') from error
    if target.strip().endswith('cygwin'):
        raise CompileError(f'{name}: gcc is a Cygwin build ({target.strip()}); '
                           f'a .pyd needs MinGW')

    # The gcc command: compiles name.c to machine code, with the calls into Python
    # left as blanks, and links it with the Python library into name.pyd, which
    # exports PyInit_<name>, the function Python calls on import. -I the header
    # folders (Python.h; numpy's too when numpy is installed, for a .pyx that
    # cimports it), -L the folders and -l the name of the Python library, -o the
    # output. No .o and no .def file are needed.
    includes = [sysconfig.get_paths()['include']]
    if importlib.util.find_spec('numpy'):
        import numpy
        includes.append(numpy.get_include())
    base = Path(sys.base_prefix)
    libs = [base / 'libs', base, base / 'PCbuild' / 'amd64']
    free = 't' if sysconfig.get_config_var('Py_GIL_DISABLED') else ''
    version = f'{sys.version_info.major}{sys.version_info.minor}{free}'
    gcc = [priv.COMPILER, *priv.GCC_FLAGS, *['-I' + str(d) for d in includes],
           str(c_file), *['-L' + str(d) for d in libs if d.is_dir()],
           f'-lpython{version}', '-o', str(pyd)]

    # Cython first: name.pyx -> name.c (a cimport is found in the .pyx's folder). The
    # console python (python.exe, not pythonw) gives both programs one hidden
    # console. In the batch file every argument is in double quotes, so that a space
    # or an & in a path is plain text, and each % is doubled (a batch file would read
    # %name% as a variable). The exit codes 11 and 12 tell the two steps apart.
    python = Path(sys.executable).with_name('python.exe')
    cython = [python, '-m', 'cython', '-3', '-I', folder, '-o', c_file, pyx]
    script = ['@echo off', 'chcp 65001 >nul']
    for code, command in enumerate([cython, gcc], 11):
        args = ['"' + str(a).replace('%', '%%') + '"' for a in command]
        script += [' '.join(args), f'if errorlevel 1 exit /b {code}']
    try:
        bat.write_text('\n'.join(script) + '\n', encoding='utf-8')
        done = subprocess.run(['cmd.exe', '/c', os.curdir + os.sep + bat.name],
                              cwd=out, capture_output=True, text=True,
                              encoding='utf-8', errors='replace',
                              creationflags=priv.NO_WINDOW)
    finally:
        bat.unlink(missing_ok=True)
    if done.returncode:
        step = {11: 'Cython', 12: 'gcc'}.get(done.returncode, 'cmd')
        raise CompileError(f'{name}.pyx: {step} failed (code {done.returncode})\n'
                           f'{(done.stderr or done.stdout)[-800:]}')
    c_file.unlink()
    importlib.invalidate_caches()           # the finders listed the folder before
