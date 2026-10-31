r"""
================================================================================
use.py — find project code by NAME, put it on the path, import it, run it, build
         it. A small dependency-free project loader. Port of MATLAB use.m/uses.m.
================================================================================

WHY
    In a multi-folder project you don't want brittle `sys.path.insert(...)` or
    `from ..pkg.sub import x` everywhere. `use` finds a file/folder by NAME with
    a bounded local search and wires it up for you. Five verbs, one search:

        use(...)      make a folder importable (path only — no side effects)
        load(...)     use() + import the public API into your namespace
        run(...)      execute a script/module fresh, WITHOUT importing it
        build(...)    (re)compile a folder's Cython .pyx into ./pyxfiles
        exclude(...)  add folder-name globs the search must never enter

QUICK START
    Put use.py at your project root, then from anywhere under it:

        import use
        use.load('primary')              # bind kv, tkv, ... ready to use
        d = kv()                         # ... now usable bare
        s = use.run('runbench','b_kv')   # run a script, get its result back
        use.use('plots')                 # just add ./plots to the path

────────────────────────────────────────────────────────────────────────────
use(*items[, 'silent']) -> (flds, ok)
────────────────────────────────────────────────────────────────────────────
  Search for each item and add the folder it lives in to sys.path. Binds NO
  names — it only makes things importable (it is also the plumbing load/run use).

    use('primary')              find primary/ (or primary.py) and add its folder
    use('kv')                   find kv.py -> add its folder (then `import kv` works)
    use('primary', 'tests')     several items
    use()                       no items -> the DEFAULTS constant
    use('plugins', '+subs')     add the found folder AND its sub-folders
    use('data', '+mkdir')       if not found, create ./data and add it
    use('.results')             CREATE ./results if missing — NOT added to path
    use('primary', 'silent')    suppress the report

  Per-item flags follow the item: '+subs' (recurse), '+mkdir' (create-if-missing
  + add), '+silent'. A leading '.' on the item (".results") just creates the
  folder (no path add). Returns (flds, ok): flds is a list of
  {item, full, status} with status added|created|subs|ok|skip; ok is True iff
  nothing was skipped.

────────────────────────────────────────────────────────────────────────────
load(*items[, silent=True]) -> dict {symbol: object}
────────────────────────────────────────────────────────────────────────────
  use() each item AND import its public API into the CALLER's namespace.

    from use import load
    load('primary')             kv, tkv, kv2, kvc2, ... now usable bare
    load('primary', '+subs')    ALSO import modules in primary's sub-folders
    load('kv')                  just kv's public API
    load('primary', 'tests')    several folders
    load()                      the DEFAULTS

  Per-item '+subs' (since 2.2): on a folder hit, also import every .py/.pyx in its
  sub-folders, no deeper than 2 levels below it (one tier past the search) — each
  sub-folder is added to the path and built/imported like the folder itself.

  What gets imported from a hit:
    * a folder  -> every .py module in it (skipping _private and setup.py),
                   plus every .pyx-backed compiled module;
    * a module  -> that one module.
  What gets BOUND from each module: its __all__ if declared, else the eponymous
  symbol (kv from kv.py), else the first class/function defined in the file.

  Dev loop: re-call load() after editing — pure-Python modules are unloaded and
  re-imported, so changes show with no restart. (Compiled .pyx are special — see
  COMPILED MODULES below.)

────────────────────────────────────────────────────────────────────────────
run(name, *args[, reload=True, silent=True]) -> result | module-namespace
────────────────────────────────────────────────────────────────────────────
  Run a script/module by NAME in a PRIVATE module — never registered in
  sys.modules, nothing injected into the caller. So `run('runbench')` does NOT
  leave runbench imported in your console.

    s = run('runbench','b_kv','','msg')  # -> runbench('b_kv','','msg') result
    run('smoke_kv')                       # top-level smoketest / figure script
    run('myscript', 5)                    # main(5) if a main() exists

  Entry point, in order: (1) main(*args); (2) the eponymous <name>(*args);
  (3) neither -> the top-level code WAS the work, and the module namespace is
  returned (s.fig, s.result, ...). Put runnable work in main() or at top level,
  NOT solely under `if __name__ == "__main__":` (that guard does not fire here).
  reload=True first drops project pure-Python modules from sys.modules, so edits
  to dependencies (bench.py, kv.py, ...) show on the next run.

────────────────────────────────────────────────────────────────────────────
build(item="primary") -> ok    |    exclude(*patterns) -> sorted skip list
────────────────────────────────────────────────────────────────────────────
  build  forces a full (re)compile of each item's .pyx into its pyxfiles subdir,
         with the CURRENT interpreter; no items -> the DEFAULTS (like use/load).
         (load builds on demand; this is the manual full rebuild.)
  exclude  adds folder-name GLOB patterns the search must never descend into —
         applies to use/load/run alike:   exclude('mani*', '*.venv', 'sandbox')

────────────────────────────────────────────────────────────────────────────
THE SEARCH  (_resolve)
────────────────────────────────────────────────────────────────────────────
  A bounded band around the current directory: up to MAX_UP parents, and from a
  root k levels up, down k+MAX_DOWN levels — so every root bottoms out at the
  SAME absolute depth (cwd + MAX_DOWN). With MAX_UP=MAX_DOWN=2 that is a tidy
  -2..+2 band. Climbing into parents is deliberate: it lets TOOLS that live
  PARALLEL to your code (sibling folders one or two levels up) be found.
    * CLOSEST to cwd wins; ties broken by NEWEST mtime.
    * The descent never enters a folder matching _SKIP (glob patterns: prev,
      site-packages, venv/.venv, .git, __pycache__, *.egg-info, build, dist, ...)
      nor any virtualenv (a dir containing pyvenv.cfg). Extend with exclude().
    * Absolute paths throughout; reports print '.'-relative (e.g. .\primary).
  This is what stops the search wandering into a sibling project's venv.

────────────────────────────────────────────────────────────────────────────
COMPILED MODULES  (.pyx -> .pyd, handled by load)
────────────────────────────────────────────────────────────────────────────
  .pyx are first-class. All build artefacts (.c, .pyd, temp) go to the pyxfiles/
  subdir, so the source folder shows only the .pyx; load adds pyxfiles/ to path.
    * load builds on demand: if there is no .pyd for THIS interpreter, or the
      .pyx is newer than the .pyd, it compiles (correct cpXY ABI tag) then imports.
    * A compiled module is NEVER reloaded — a live process cannot reload a C
      extension (the OS caches the shared library). If it is already imported,
      load WARNS and keeps the installed version; restart to pick up a rebuild.
    * Per-interpreter .pyd coexist (kvc.cp313-*.pyd and kvc.cp314-*.pyd), so the
      same source serves several Pythons.

BOOTSTRAP (once)
  `import use` only works if the folder that CONTAINS use.py is on sys.path
  (the list of folders Python searches for imports). If you're not sure how:
    * set the PYTHONPATH environment variable to include that folder, OR
    * run  sys.path.insert(0, r"C:\path\to\use_folder")  before importing use, OR
    * just start Python from that folder (its cwd is on the path).
  Only needed to import use itself; after that, use/load/run find everything else.

────────────────────────────────────────────────────────────────────────────
AUTO-BIND  (since 2.2)
────────────────────────────────────────────────────────────────────────────
  A bare `import use` self-binds use/load/run/build/exclude into the importer —
  no `from use import ...` needed. A `from use import x` is HONOURED (only x is
  bound). The names land in the importer's OWN namespace; in a REPL / PyCharm
  (pydev) console they also land in __main__ (where typed names resolve). A real
  module importing use binds into itself ALONE — nothing leaks to its caller or
  __main__. Each auto-bind prints one line: `use: auto-loaded ...`.

CHANGELOG
  (Full annotated history — incl. the MATLAB use.m/uses.m + folderpaths.m roots —
   lives in the "use loader" tab of port-log.html, recovered from chats/.)
  2.2  load() honours per-item '+subs' (recurse sub-folders for .py/.pyx, capped
       2 levels below the folder). Auto-bind on `import use` (see above).
  2.1  Cython .pyx support, bounded -2..+2 search band, create-only '.' items.
  pre  Port of MATLAB use.m/uses.m during the xlw.p port (2026-06). iuse.py
       indirection tried then dropped (cwd is always on the path); primary/setup.py
       folded in (self-contained cythonize); verbs settled (use/load/run/build/
       exclude). Pre-2.1 version numbers were never recorded.

VERSION: 2.2
"""

from __future__ import annotations

import fnmatch
import os
import re
import sys
from pathlib import Path

__all__ = ["use", "load", "run", "build", "exclude"]

from warnings import catch_warnings

ROOT = Path(__file__).resolve().parent              # this file marks the project root
DEFAULTS = ('.primary',"primary")                   # use()/load() with no items
MAX_UP   = 2        # search climbs at most this many parents above cwd
MAX_DOWN = 2        # ...and descends this many levels; an ancestor k levels up is
                    # searched (k + MAX_DOWN) deep, so every root bottoms out at the
                    # SAME absolute level (cwd + MAX_DOWN) — a band of -MAX_UP..+MAX_DOWN.
_SEG_OK = re.compile(r"^[A-Za-z0-9_\-.()\[\]{};& ]+$")
PYXOUT = "pyxfiles"     # .pyx build artefacts (.c, .pyd, temp) live in <folder>/pyxfiles
                        # so the source folder shows only the .pyx; load adds it to path
_SKIP = {"prev", "__pycache__", ".git", ".hg", ".svn", ".idea", ".vscode",
         ".tox", "node_modules", "site-packages", "venv", ".venv", "env",
         ".env", "build", "dist", "*.egg-info", "*.dist-info"}
# folder-name GLOB patterns the search never enters; extend with exclude().


def _excluded(name):
    return any(fnmatch.fnmatch(name, pat) for pat in _SKIP)   # case-insensitive on Windows


def exclude(*patterns):
    # Add folder-name glob patterns the search must never descend into — applies
    # to use / load / run. Wildcards allowed:  exclude('mani*', '*.venv').
    _SKIP.update(str(p) for p in patterns)
    return sorted(_SKIP)


# ════════════════════════════════════════════════════════════════
# The search — find where a named library/module/folder lives
# ════════════════════════════════════════════════════════════════
def _search_roots(start):
    # cwd, then up to MAX_UP parents (never above the filesystem root). _resolve
    # pairs root index i with a descent budget i + MAX_DOWN, so the search spans a
    # band of -MAX_UP..+MAX_DOWN levels around cwd. Climbing INTO parents is
    # deliberate — it lets tools that live PARALLEL to the code (sibling folders a
    # level or two up) be found; _SKIP/exclude keep venvs & junk out of descent.
    if len(start.parts) < 3:
        raise ValueError(
            f'use: working directory too shallow: "{start}" — need at least '
            f'3 path elements (e.g. C:{os.sep}code{os.sep}myproj).')
    roots, cur = [start], start
    for _ in range(MAX_UP):
        nxt = cur.parent
        if nxt == cur:
            break
        cur = nxt
        roots.append(cur)
    return roots


def _candidates(root, name, maxdepth, suffix=".py", want_dir=True):
    # <name><suffix> files (and, if want_dir, <name>/ dirs) at/under `root`, no
    # deeper than maxdepth levels. Descent prunes _SKIP patterns and virtualenvs.
    out, root = [], str(root)
    for dp, dirs, files in os.walk(root):
        rel = os.path.relpath(dp, root)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        dirs[:] = [d for d in dirs
                   if not _excluded(d)
                   and not os.path.isfile(os.path.join(dp, d, "pyvenv.cfg"))]  # venv root
        if name + suffix in files:
            out.append(Path(dp) / (name + suffix))
        if want_dir and depth < maxdepth and name in dirs:
            out.append(Path(dp) / name)
        if depth >= maxdepth:
            dirs[:] = []                            # stop descending past the band
    return out


def _resolve(name):
    # Closest-wins search. Returns (dirs_to_add, modname): for a <name>.py hit,
    # the dir containing it + modname; for a <name>/ folder, the folder (+ its
    # primary/ subdir if present) + modname None. (None, None) if nothing found.
    start = Path.cwd()
    for i, root in enumerate(_search_roots(start)):
        cands = _candidates(root, name, i + MAX_DOWN)
        if not cands:
            continue
        # closest = shallowest under this root, then newest mtime
        cands.sort(key=lambda p: (len(p.relative_to(root).parts), -p.stat().st_mtime))
        best = cands[0]
        if best.is_dir():
            dirs = [best] + ([best / "primary"] if (best / "primary").is_dir() else [])
            return dirs, None
        return [best.parent], name
    return None, None


def _addpath(folder, subs=False):
    # Prepend folder (and, if subs, its sub-folders, skipping prev) to sys.path.
    folder = str(folder)
    if not subs:
        roots = [folder]
    else:
        roots = []
        for dp, dnames, _f in os.walk(folder):
            if "prev" in Path(dp).parts:
                dnames[:] = []                       # never descend into prev/
                continue
            if os.path.basename(dp) == PYXOUT:       # a .pyx build dir (pyxfiles/)
                dnames[:] = []                       # nothing importable below it (_tmp ...)
                # Only expose a build dir that sits NEXT TO its source: the parent
                # must still hold a .pyx. An orphan pyxfiles/ (source moved/removed)
                # is skipped, so a raw `import mod` can't bind a stale .pyd. A parent
                # WITH a .pyx still exposes its build — a user with a C compiler
                # rebuilds from the .c as before.
                parent = os.path.dirname(dp)
                try:
                    if not any(f.endswith(".pyx") for f in os.listdir(parent)):
                        continue                     # orphan build dir -> do not add
                except OSError:
                    continue
            roots.append(dp)
    added = False
    for r in roots:
        if r not in sys.path:
            sys.path.insert(0, r)
            added = True
    return added


# ════════════════════════════════════════════════════════════════
# Pretty printing — a simplified tree2str (no dependency on tree2str)
# ════════════════════════════════════════════════════════════════
def _rel(p):
    # Path relative to cwd, anchored with '.', so long absolute folders read as
    # ".\primary". Falls back to the absolute path across drives (no relpath).
    try:
        r = os.path.relpath(str(p), os.getcwd())
    except ValueError:
        return str(p)
    if r == "." or r.startswith("." + os.sep) or r.startswith(".." + os.sep):
        return r
    return "." + os.sep + r


def _tree(title, rows):
    # title with '|__' children. Rows may be strings or column-tuples; columns
    # are left-padded to a common width so they line up (tabbed). ASCII only
    # (the Windows console codec can't encode the Unicode box glyphs).
    cells = [r if isinstance(r, (list, tuple)) else (r,) for r in rows]
    ncol = max((len(c) for c in cells), default=0)
    width = [max((len(str(c[i])) for c in cells if i < len(c)), default=0)
             for i in range(ncol)]
    out = [title]
    for c in cells:
        line = "  ".join(str(c[i]).ljust(width[i]) for i in range(len(c)))
        out.append("   |__ " + line.rstrip())
    return "\n".join(out)


def _use_rows(flds):
    return [(f"[{f['status']}]", f["item"],
             "(file/folder not found)" if f["status"] == "skip" else _rel(f["full"]))
            for f in flds]


class _Folds(list):                 # use() result: list of {item,full,status}
    def __repr__(self):
        return _tree("use", _use_rows(self))


class _Loaded(dict):                # load() result: a dict with a tree repr
    _summary = ""
    def __repr__(self):
        return self._summary or dict.__repr__(self)


class _UseResult(tuple):            # use() result: (flds, ok) that echoes as ONE
    # tree (not a duplicated print + tuple echo). Still unpacks: flds, ok = use().
    def __new__(cls, flds, ok, silent=False):
        self = super().__new__(cls, (flds, ok))
        self._silent = silent
        return self
    def __repr__(self):
        return "" if self._silent else repr(self[0])


# ════════════════════════════════════════════════════════════════
# use — search each item, add its folder to the path
# ════════════════════════════════════════════════════════════════
def use(*args):
    # Parse items + per-item flags (+subs/+mkdir/+silent) + global 'silent'.
    entries, global_silent = [], False            # entry: [item, subs, mkdir, silent]
    for tok in args:
        tok = str(tok)
        if tok.lower() == "silent":
            global_silent = True
        elif tok.startswith("+"):
            if not entries:
                raise ValueError(f'use: flag "{tok}" appears before any item.')
            flag = tok.lower()
            if   flag == "+subs":   entries[-1][1] = True
            elif flag == "+mkdir":  entries[-1][2] = True
            elif flag == "+silent": entries[-1][3] = True
            else: raise ValueError(f'use: unknown flag "{tok}".')
        else:
            entries.append([tok, False, False, False])

    if not entries:
        entries = [[n, False, False, False] for n in DEFAULTS]

    flds, ok = [], True
    for item, subs, mkdir, ent_silent in entries:
        silent = global_silent or ent_silent

        # leading '.' -> CREATE ./item (no path add). New feature.
        if item[:1] == ".":
            rel = item[1:]
            _validate_create(rel)
            full = Path.cwd() / rel
            full.mkdir(parents=True, exist_ok=True)
            status = "created"
        else:
            dirs, _mod = _resolve(item)
            if dirs is None:
                if mkdir:                          # not found -> create under cwd + add
                    _validate_create(item)
                    full = Path.cwd() / item
                    full.mkdir(parents=True, exist_ok=True)
                    _addpath(full, subs)
                    status = "created"
                else:
                    full = item; status = "skip"; ok = False
            else:
                full = dirs[0]
                hit = any(_addpath(d, subs) for d in dirs)
                status = ("subs" if subs else "added") if hit else "ok"

        flds.append({"item": item, "full": str(full), "status": status})

    return _UseResult(_Folds(flds), ok, global_silent)   # echoes as one tree


def _validate_create(rel):
    # Light guard on a folder we are about to CREATE (no '..', clean segments).
    for seg in re.split(r"[/\\]", rel):
        if seg in ("", ".", "..") or not _SEG_OK.match(seg):
            raise ValueError(f'use: cannot create "{rel}" (bad segment "{seg}").')


# ════════════════════════════════════════════════════════════════
# load — use() each item AND import its public API into the caller
# ════════════════════════════════════════════════════════════════
def load(*items, silent=True, _into=None):
    if _into is None:
        _into = sys._getframe(1).f_globals          # the caller's module globals
    if not items:
        items = DEFAULTS

    import importlib
    loaded, skipped, built = {}, [], set()

    def _inject(m, name):
        for sym in _public_api(m, name):
            obj = getattr(m, sym, None)
            if obj is not None:
                _into[sym] = obj
                loaded[sym] = obj

    # Parse a per-item '+subs' flag (mirrors use()). On a FOLDER hit it widens
    # discovery to the folder's sub-folders — but only 2 levels below it, so it
    # reaches exactly one tier deeper than the search that FOUND the folder. Other
    # '+' flags are not meaningful to load and are ignored here.
    entries = []                                    # (item, subs) in call order
    for tok in items:
        t = str(tok)
        if t.startswith("+"):
            if t.lower() == "+subs" and entries:
                entries[-1] = (entries[-1][0], True)
            continue
        entries.append((t, False))

    def _modnames(folder):
        # importable .py and .pyx in one folder (skip _private + the setup script).
        fns = sorted(os.listdir(folder))
        py  = [f[:-3] for f in fns if f.endswith(".py")  and not f.startswith("_")
               and f != "setup.py"]                 # build script, not a library
        pyx = [f[:-4] for f in fns if f.endswith(".pyx") and not f.startswith("_")]
        return py, pyx

    def _walk_units(folder, maxdepth=2):
        # (folder, py_names, pyx_names) for `folder` (depth 0) and every sub-folder
        # no deeper than maxdepth levels below it. Prunes _SKIP, pyxfiles, prev and
        # virtualenvs — the same descent rules the main search uses.
        units, folder = [], str(folder)
        for dp, dnames, _f in os.walk(folder):
            rel   = os.path.relpath(dp, folder)
            depth = 0 if rel == "." else rel.count(os.sep) + 1
            dnames[:] = [d for d in dnames
                         if not _excluded(d) and d != PYXOUT
                         and not os.path.isfile(os.path.join(dp, d, "pyvenv.cfg"))]
            py, pyx = _modnames(dp)
            if py or pyx:
                units.append((dp, py, pyx))
            if depth >= maxdepth:
                dnames[:] = []                       # stop descending past the cap
        return units

    def _process_unit(folder, py_names, pyx_names):
        # Import one folder's modules into the caller (the path-add + py + pyx
        # machinery, factored out so '+subs' can run it per sub-folder).
        folder = str(folder)
        _addpath(folder)

        # pure-Python: reloadable — unload (dev loop) then import.
        for name in py_names:
            sys.modules.pop(name, None)
        for name in py_names:
            try:
                _inject(importlib.import_module(name), name)
            except Exception as e:                  # a bad module must not abort the rest
                skipped.append(f"{name} ({type(e).__name__}: {e})")

        if pyx_names:                               # .pyd lives in the pyxfiles subdir
            _addpath(os.path.join(folder, PYXOUT))

        # compiled (.pyx): NOT reloadable. Rebuild the folder once if any
        # NOT-loaded module is stale (no .pyd for this interpreter, or .pyx newer
        # than .pyd); loaded modules are locked, so they are never rebuilt.
        if (folder not in built
                and any(name not in sys.modules and _pyx_stale(folder, name)
                        for name in pyx_names)):
            built.add(folder)
            okb, msg = _build_ext(folder)
            if not okb:
                skipped.append(f"{folder} (build failed: {msg})")

        for name in pyx_names:
            if name in sys.modules:                  # already imported -> can't reload
                print(f"  use.load: WARNING '{name}' is already imported — a compiled "
                      f"extension cannot be reloaded in a live process; keeping the "
                      f"installed version (restart the interpreter to pick up a rebuild).")
                _inject(sys.modules[name], name)
                continue
            try:
                m = importlib.import_module(name)
            except Exception as e:
                skipped.append(f"{name} ({type(e).__name__}: {e})")
                continue
            _inject(m, name)

    for item, subs in entries:
        if item[:1] == "." or str(item).lower() == "silent":
            use(item, "silent")                     # create-only / token: path side only
            continue
        dirs, mod = _resolve(item)
        if dirs is not None:
            for d in dirs:
                _addpath(d)
            folder = str(dirs[0])
            if mod is not None:                     # a single .py module
                units = [(folder, [mod], [])]
            elif subs:                              # folder + sub-folders (<= 2 levels)
                units = _walk_units(folder, 2)
            else:                                   # the folder's own .py AND .pyx
                py, pyx = _modnames(folder)
                units = [(folder, py, pyx)]
        else:                                       # maybe a pyx-only single module
            pyx = _find_pyx(item)
            if pyx is None:
                skipped.append(f"{item} (not found)")
                continue
            units = [(str(pyx.parent), [], [item])]

        for unit in units:
            _process_unit(*unit)

    result = _Loaded(loaded)
    rows = []                                       # one aligned row per symbol
    for sym, obj in loaded.items():
        mod = sys.modules.get(getattr(obj, "__module__", "?"))
        f = _rel(mod.__file__) if mod and getattr(mod, "__file__", None) else ""
        rows.append((sym, f))
    if skipped:
        rows.append(("skipped", "; ".join(skipped)))
    result._summary = _tree("use.load", rows)
    if not silent:
        print(result._summary)
    return result


def _find_pyx(name):
    # Closest-wins search for <name>.pyx (compiled-module source).
    start = Path.cwd()
    for i, root in enumerate(_search_roots(start)):
        cands = _candidates(root, name, i + MAX_DOWN, suffix=".pyx", want_dir=False)
        if cands:
            cands.sort(key=lambda p: (len(p.relative_to(root).parts), -p.stat().st_mtime))
            return cands[0]
    return None


def _pyx_stale(folder, name):
    # True if <name>.pyx needs (re)compiling: no compiled module for THIS
    # interpreter, or the .pyx source is newer than the .pyd build.
    import importlib.machinery
    pyx = os.path.join(folder, name + ".pyx")
    if not os.path.isfile(pyx):
        return False                                 # not a compiled module
    src = os.path.getmtime(pyx)
    for suf in importlib.machinery.EXTENSION_SUFFIXES:   # e.g. .cp313-win_amd64.pyd, .pyd
        pyd = os.path.join(folder, PYXOUT, name + suf)   # built into the pyxfiles subdir
        if os.path.isfile(pyd):
            return os.path.getmtime(pyd) < src       # stale iff build older than source
    return True                                      # no .pyd for this Python -> build


# Self-contained Cython build (no external setup.py needed): cythonize every
# *.pyx in a folder, sending ALL artefacts (.c, .pyd, temp objects) to the
# pyxfiles subdir so the source folder shows only the .pyx. Run in a SUBPROCESS
# so it is a fresh interpreter — the .pyd carries this Python's cpXY-<plat> ABI
# tag and no already-imported extension is locked in the current process.
_BUILD_SRC = r'''
import glob, os, sys
os.chdir(sys.argv[1])
out = sys.argv[2]
os.makedirs(out, exist_ok=True)
from setuptools import setup, Extension
from Cython.Build import cythonize
exts = [Extension(os.path.splitext(f)[0], [f]) for f in sorted(glob.glob("*.pyx"))]
setup(name="_use_cy",
      script_args=["build_ext", "--build-lib", out, "--build-temp", os.path.join(out, "_tmp")],
      ext_modules=cythonize(exts, language_level=3, annotate=False, build_dir=out))
'''


def build(*items):
    # Force a full (re)build of each item's .pyx into its pyxfiles subdir, with
    # the current interpreter. No items -> the DEFAULTS (same as use/load).
    # (load() builds on demand; this is the manual full rebuild.)
    if not items:
        items = DEFAULTS
    ok_all, seen = True, set()
    for item in items:
        if str(item)[:1] == ".":                    # create-only token, no .pyx
            continue
        dirs, _mod = _resolve(item)
        if dirs is not None:
            folder = str(dirs[0])
        else:
            pyx = _find_pyx(item)
            if pyx is None:
                print(f"  use.build: no .pyx found for '{item}'")
                ok_all = False
                continue
            folder = str(pyx.parent)
        if folder in seen:
            continue
        seen.add(folder)
        ok, msg = _build_ext(folder)
        print(f"  use.build: {item} " + ("done" if ok else "FAILED\n" + msg))
        ok_all = ok_all and ok
    return ok_all


def _build_ext(folder):
    # Build the folder's .pyx with THIS interpreter. Returns (ok, message-tail).
    import subprocess
    print(f"  use.load: building extensions in {_rel(folder)} for "
          f"Python {sys.version_info.major}.{sys.version_info.minor} ...")
    r = subprocess.run([sys.executable, "-c", _BUILD_SRC, str(folder), PYXOUT],
                       capture_output=True, text=True)
    return r.returncode == 0, (r.stderr or r.stdout or "")[-300:]


def _public_api(m, name):
    # __all__ if declared (the from-import-* list), else the eponymous symbol,
    # else the first class/function actually DEFINED in this module.
    import inspect
    if getattr(m, "__all__", None) is not None:
        return list(m.__all__)
    if hasattr(m, name):
        return [name]
    for sym, obj in vars(m).items():
        if (not sym.startswith("_")
                and (inspect.isclass(obj) or inspect.isfunction(obj))
                and getattr(obj, "__module__", None) == name):
            return [sym]
    return []


# ════════════════════════════════════════════════════════════════
# run — execute a script/module by name in a PRIVATE module, fresh
# ════════════════════════════════════════════════════════════════
def _reload_project():
    # Drop project pure-Python modules from sys.modules so the next import picks
    # up edits. Skip compiled extensions (.pyd/.so — cannot reload in a live
    # process), this module, and anything outside the project ROOT.
    root = str(ROOT)
    for nm in list(sys.modules):
        if nm == "use":
            continue
        m = sys.modules.get(nm)
        f = getattr(m, "__file__", None)
        if not f or not f.endswith(".py"):           # no source / compiled ext
            continue
        try:
            if os.path.commonpath([root, os.path.abspath(f)]) == root:
                del sys.modules[nm]
        except ValueError:
            pass                                     # different drive — not ours


def run(name, *args, reload=True, silent=True):
    # Locate <name>.py via the same search as use/load, load it into a PRIVATE
    # module (never registered in sys.modules), run it, and return the result.
    # Entry point: main(*args), else the eponymous <name>(*args), else (top-level
    # was the work) the module namespace. See the module docstring for details.
    import importlib.util

    dirs, mod = _resolve(name)
    if dirs is None or mod is None:
        raise FileNotFoundError(f'run: no script "{name}.py" found from {Path.cwd()}.')
    for d in dirs:
        _addpath(d)
    file = Path(dirs[0]) / (name + ".py")

    if reload:
        _reload_project()                            # so dependency edits show

    spec = importlib.util.spec_from_file_location(name, str(file))
    m = importlib.util.module_from_spec(spec)        # NOT inserted into sys.modules

    argv0 = sys.argv
    sys.argv = [str(file)] + [str(a) for a in args]  # so argv-driven scripts work
    try:
        spec.loader.exec_module(m)                   # runs the file's top level
        if callable(getattr(m, "main", None)):
            result = m.main(*args)
        elif callable(getattr(m, name, None)):
            result = getattr(m, name)(*args)
        else:
            result = m                               # top-level was the work
    finally:
        sys.argv = argv0

    if not silent:
        print(f"  use.run: {name}({', '.join(map(repr, args))})")
    return result


# ════════════════════════════════════════════════════════════════
# Auto-bind — every `import use` injects use's API into the importer
# ════════════════════════════════════════════════════════════════
# Goal: any module that does `import use` (or `from use import ...`) gets
# use/load/run/build/exclude bound bare in ITS namespace, with no `from use
# import *`. The module body runs only once per process (use is cached in
# sys.modules), so the body alone can only reach the FIRST importer. To fire on
# EVERY import we wrap builtins.__import__ — that IS called on every import
# statement, even for an already-cached module, and it is handed the importer's
# own globals. We inject there and otherwise defer entirely to the real import.

def _inject_api(g):
    # Bind use's public API into the mapping g (an importer's namespace). Skip any
    # name the importer ALREADY defined itself (guard against `g`, not use's own
    # globals). Returns the list of names actually bound, for the caller to report.
    if not isinstance(g, dict):
        return []
    added = []
    for k in __all__:
        if k not in g:                               # don't clobber the importer's own name
            g[k] = globals().get(k)
            added.append(k)
    return added



def _interactive():
    # True only at a REPL / the PyCharm (pydev) console — where __main__ is an
    # interactive session with NO source file. A script run (`python x.py`),
    # `python -m mod`, etc. all give __main__ a real __file__, so this is False.
    m = sys.modules.get("__main__")
    return not getattr(m, "__file__", None)


def _main_globals():
    # __main__'s dict — the namespace where typed names resolve in a REPL / pydev
    # console, even though the importer FRAME's f_globals is a pydev-internal dict.
    m = sys.modules.get("__main__")
    d = getattr(m, "__dict__", None)
    return d if isinstance(d, dict) else None


def _autobind(g):
    # Bind the API into the importer's OWN namespace g — and, ONLY in an
    # interactive session, also into __main__ (the console read namespace, which
    # pydev hides behind a scratch frame). A real module importing `use` therefore
    # binds into itself alone: nothing leaks into __main__ or any caller.
    targets = [g]
    if _interactive():
        targets.append(_main_globals())
    seen, added = set(), []
    for ns in targets:
        if isinstance(ns, dict) and id(ns) not in seen:
            seen.add(id(ns))
            for k in _inject_api(ns):
                if k not in added:
                    added.append(k)
    if added:                                        # report ONCE, the union bound
        print("use: auto-loaded " + ", ".join(added))


def _install_autoload_hook():
    # Wrap builtins.__import__ once so each `import use` injects the API into the
    # caller. Idempotent: a re-import/reload won't stack wrappers.
    import builtins
    if getattr(builtins.__import__, "_use_autoload", False):
        return
    _real_import = builtins.__import__

    def _import(name, globals=None, locals=None, fromlist=(), level=0):
        m = _real_import(name, globals, locals, fromlist, level)
        # Fire only for a BARE `import use` (fromlist is falsy). When the caller
        # wrote `from use import x` / `from use import *` they asked for specific
        # names — honour that and bind nothing extra. Never touch the thousands of
        # unrelated imports in a process.
        if (not fromlist
                and (name == "use" or name.split(".", 1)[0] == "use")):
            try:
                _autobind(globals)                   # importer ns (+ __main__ only if interactive)
            except Exception:
                pass                                 # auto-bind must never break an import
        return m


    _import._use_autoload = True
    builtins.__import__ = _import


def _importer_fromlist(frame):
    # The fromlist of the import statement currently running in `frame`: None for
    # a bare `import use`, a tuple for `from use import ...`. Read off the bytecode
    # — the frame is paused on IMPORT_NAME, whose fromlist operand was pushed by
    # the immediately preceding LOAD_CONST. Best-effort; on any doubt returns "?".
    import dis
    ins = list(dis.get_instructions(frame.f_code))
    cur = next((k for k, x in enumerate(ins) if x.offset == frame.f_lasti), None)
    if cur is None or ins[cur].opname != "IMPORT_NAME":
        return "?"
    for j in range(cur, -1, -1):
        if ins[j].opname == "LOAD_CONST":
            return ins[j].argval                     # None (plain) or a from-tuple
    return "?"


_install_autoload_hook()                             # covers all FUTURE `import use`

# The hook only fires on imports AFTER it is installed, so the bootstrap importer
# (whose `import use` ran this very body, under the un-wrapped __import__) is not
# covered by it. Reach that one importer directly via the call stack. We can only
# read the import form off the bytecode when the frame is parked on IMPORT_NAME
# (a plain top-level statement); a console / IPython / import_module() bootstrap
# runs use under exec, so the form is UNKNOWN ("?"). Rule: bind UNLESS we POSITIVELY
# see a `from use import ...` tuple — so the interactive case (where the user wants
# the names) self-binds, while a detectable from-import is still honoured.
for _depth in range(1, 40):
    try:
        _frame = sys._getframe(_depth)
    except ValueError:
        break
    _nm = _frame.f_globals.get("__name__", "")
    if _nm == "use" or "importlib" in _nm:           # our frame / (frozen) import machinery
        continue
    try:
        _fromlist = _importer_fromlist(_frame)       # None (plain) | tuple (from) | "?"
    except Exception:
        _fromlist = "?"                              # can't tell -> treat as interactive
    if not isinstance(_fromlist, tuple):             # plain or unknown -> self-bind
        _autobind(_frame.f_globals)                  # importer ns (+ __main__ only if interactive)
    break