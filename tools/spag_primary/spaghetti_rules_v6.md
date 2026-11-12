# spaghettichk rules, proposed v6 (draft, not built)

Source: the user's edits (2026-11-05) of the proposal made after the xlw2 work. It
changes nothing in `spaghettichk.py` or in `spaghettichk_rules_v5.xlsx` yet.

## Why
A file can be made greener by splitting it. A split is only elegant when the new file
holds clear functionality that is reused. A module that one other module uses is a
satellite: the split moved code, it did not separate functionality.

## New and changed rules

| rule | level | verdict |
|---|---|---|
| importers | file | green: 4 or more other modules import it; grey: 3; orange: 2; red: 1 (a satellite); red: none (not used at all); n/a: an entry point (exported to users, or named in a suite) |
| cluster | scoring | a module with exactly one importer is scored together with that importer: its exports, local functions and imports are added to the parent's `allsize`, `locals`, `imports` |
| surface | package | names used by other modules of the parent folder / names exposed by the folder: green over 0.8, grey 0.5 to 0.8, orange 0.3 to 0.5, red under 0.3 |
| complexity | row | too little and too much are both penalised: green 11 to 18, grey 7 to 21, orange 5 to 30, red under 5 or over 30; the weight is larger than tangle's 4 |
| constants | row | the same literal or constant value defined in two modules (the `priv` contents are compared) counts under `duplication` |
| compiled twin | file | a .pyx whose only importer is the Python module it speeds up is allowed (not a satellite) when its header has a Speed section that names every `__all__` function with its measured gain over the Python loop; a function without a stated gain is orange, no Speed section is red |
| cycles | file | green: no module of the area imports one that imports it, directly or through others, at the top of the file or inside a function; red (forced): a cycle; orange: an import inside a function whose comment or name is a way round a cycle |
| peek | row | a module reaching a name of another module through an attribute (`module.name`, `name` not in that module's `__all__`) is red, forced (the band goes red), with a weight above `tangle`'s; it counts in the row that makes the access, and in the owning module's `poke`; green: none |
| importclean (siblings and subs) | file | the ratio below, counting only users in the module's own folder (its siblings) and in the subfolders of that folder (subs): exactly 1 is green; anything else is red, very heavy weight (above `peek`) |
| importclean (wide) | file | the same ratio, counting only users in the subfolders of the parent folder's parent (cousins, suites and callers elsewhere in the tree); exactly 1 is green; anything else is red, very heavy weight |
| (the ratio) | | distinct names called from the module (exposed or not) / names in its `__all__`. Under 1: an exposed name nobody in that scope uses. Over 1: a name used that is not exposed. Suites count as users and are not exempt |
| door | file | the module named like its folder (xlw/xlw.py; a trailing version number on the folder is ignored, so xlw2/xlw.py counts) is the folder's front door: its `__all__` is the folder's interface to the world, and it may be used from anywhere. Every other module of the folder is internal: only its siblings and the subfolders of its own folder (its suites included) may use it. Green: an internal module is used inside the folder only. Red, forced, very heavy weight: an internal module used from outside the folder (an import, `load`, or `module.name`). A folder with no module of its own name has no front door: every module in it is internal, which is red when anything outside uses one |
| errors | file | the `*Error` exemption in `allsize` goes, or applies only to a hierarchy with one base class |

## Read-out for xlw2 (importer counts, 2026-11-05)

| module | importers | band |
|---|---|---|
| xltext | 6 | green |
| xlchart, xlstore, xlstyle, xltables | 3 | grey |
| xlparts, xlsheetxml | 2 | orange |
| xlchartread, xlchartxml, xlsheet | 1 | red (satellite) |
| xlw, xlreader | 1 each (each imports the other) | n/a, entry points |
| kv, tkv | 1 (xlstore) | n/a if named in a suite (b_kv, b_tkv) |
| xlsheetfun | 1 (xltables) | allowed as a compiled twin: its header has the Speed section (done, 1.5x to 2.6x) |

## Open points
1. complexity: counted per function (the tangle count: 1 plus if, elif, for, while,
   except, and, or, case)? Then a 3-line helper is red. If that is not meant, the unit
   needs another definition (per file, or per function above N lines).
2. surface: "used by other modules" = imported by name, or any use?
3. (settled) xlw and xlreader imported each other; the cycle was removed in xlw2 and is the case the cycles rule is for.
6. importclean (both scopes): a name used through `load(..., into=)` counts as called when the bound name is used; `*` imports and `getattr` by string cannot be counted and are red on their own.
   Entry points no other module imports have nothing called: only their suites count.
5. cycles: is a cycle red for both modules, or for the one whose import closes it (the later one in the chain)?
4. (settled by the user) xlsheetfun: allowed, with the Speed annotation per exposed function.
7. importclean scopes: a name that only cousins use is under 1 for siblings and fine for wide; is that right,
   or must every exposed name be used in both scopes? An entry point has no sibling users: is its sibling
   ratio n/a (my reading) or red?

## Check of the door rule against the other rules

| rule | does it still hold | change needed |
|---|---|---|
| importers (v6) | its n/a for "an entry point (exported to users, or named in a suite)" is now sharper | entry point = the front door. A suite no longer makes a module an entry point |
| cluster (v6) | holds | a satellite is scored with the sibling that uses it; the front door has the world as importers, so it is never a satellite |
| callers (v5, row) | conflicts for the front door: its exports may have no sibling caller | n/a for front-door exports (the wide scope of importclean replaces it); for internal modules it counts siblings only, as now |
| tested (v5, row) | holds | an internal module's suite must live in the folder (a tests/ subfolder, as xlw2 has), not beside tools: otherwise the suite is a use from outside and is red under door |
| suitepeek (v5, file) | holds | same location rule: a suite of an internal module that sits outside the folder cannot be green |
| importclean, siblings and subs | applies to internal modules only | front door: n/a (nothing is called by siblings by design) |
| importclean, wide | applies to the front door only | internal modules have no legitimate wide users: any wide user is the door rule's red, so wide is n/a for them |
| peek (v6, row) | holds | an internal module's export reached from outside is `door`, a front door's non-exported name reached is still `peek` |
| allsize | holds | for the front door it is the size of the folder's interface; keep 1-2 green |
| surface (package, v6) | holds, simplified | names used from outside / names in the front door's `__all__` (internal modules add nothing to the folder's surface) |
| foreign (v5, file) | holds | importing from a front door of another folder is the normal case; importing an internal module of another folder is red under `door` |
| cycles (v6) | holds | a cycle between two folders' front doors is still a cycle |
| compiled twin (v6) | holds | the .pyx is internal to the folder, used by its Python sibling |
| header | holds | add: the front door's header says it is the folder's front door |

## What the door rule finds in the xlw folder today (2026-11-05)
- xlw/xlw.py has no problem: it is the front door of the folder.
- svgchart/svgchart.py and mumix.py use xlchart, an internal module of xlw/: red under door.
  The rule only reports it. Files stay in their project folder; what to do about the use is the user's decision.
- tests/b_xlreader.py, b_xlsheet.py, b_xlw.py, b_xlstyle (and gridcheck.py) use xlreader, xlsheet, xlstyle and xlstore, all
  internal: red under door while the suites sit in mumix/tests. In xlw2 they sit in xlw2/tests, inside the folder, which passes.
- kv.pyx and tkv.pyx are tested by suites outside xlw/: red under door for the same reason. They stay where they are.
- xlw2/xlw.py is the front door of xlw2 (the trailing version number of the folder name is ignored).

## New open points
8. A suite of a front door sits outside (mumix/tests today). Is that allowed, as the door is for the world, while the suites of internal modules must sit in the folder?
9. A file never moves out of its project folder (user rule): the checker reports a door violation and does not suggest relocating the file.

## Proposed: evolution (a file or cluster against its previous version)

Aim: reward the change that gives the same functionality with a better algorithm, and do not reward
moving code about. Innovation itself cannot be read from source; this rule scores what an
innovative change leaves behind when compared with the previous version.

Inputs. The previous version is the file at the last commit whose header had a lower VERSION, or the
snapshot named in the header (the snapshot section of CLAUDE.md already asks for one). The unit
compared is the cluster (the module with the siblings only it uses), so a split changes nothing.
Function bodies are matched by similarity of their normal form (below), not by a hash of the text:
a body that is 85% or more the same, as a tree, is "moved" and counts as no change.

### Normal form and counting (so that comments, names and layout cannot move a score)
Every function is reduced to its syntax tree and printed back in one fixed layout before it is
compared or counted:
1. comments, docstrings and blank lines are gone (they are not in the tree)
2. one statement per line: `a; b` and `if x: y` are expanded; line wraps and joins disappear
3. every local name and argument is renamed by order of first use (v1, v2, ...), so long or short
   names make no difference; names of other modules, attributes and exported names are kept
4. size is counted in operations (calls, operators, subscripts, branches, literals, returns), not
   in lines and not in names, so a one-line giant table is not "one line" and a temporary variable
   adds nothing; lines of the fixed layout are reported beside it for the reader
5. a name assigned once and used once is inlined before counting (splitting an expression into steps
   changes nothing); `pass`, bare constants and `x = x` are dropped (a no-op cannot make a body new)

Tricks this has to catch, and the answer to each:
- hide branches in a comprehension, a ternary, `and`/`or`, a lambda or a chained comparison: all
  count as branches, and a lambda counts as a function
- hide branches in a dispatch dict of functions or a table of lambdas: the table counts the
  branches of what it holds
- lower a function's complexity by a helper with one caller: the helper is counted into its caller
  (single-use callees are inlined for the measure); complexity is also reported for the cluster
- move code to another file, or into a .pyx, a data file or a config that drives logic: cluster
  scoring, and any file the code reads at run time (json, yaml, a pattern file) counts with it
- hide logic in a string: `exec`, `eval`, `getattr` by name, `__import__`, and a long regular
  expression (counted by its alternations and groups) are counted as the logic they stand for
- hide it in indirection: decorators, metaclasses, `__getattr__`, a registry filled at import time
  count as one branch each at least, and as a `getattr` finding
- split a function in many tiny ones: the complexity band has a lower end, and the count of defs
  is reported
- delete functionality or tests to look smaller: the suite's test count and the assertions per
  exported name may not fall; golden files may not change
- version bump with no change in the tree: n/a, no credit
- rename back and forth: renames are invisible to the normal form, so they change nothing

Measures, on the changed (not moved) code, current against previous:
1. complexity: total tangle count of the cluster, and the largest single function
2. size: lines and number of defs of the cluster
3. generalisation: defs removed against callers gained by the defs that stayed (one function now
   does what several did)
4. data against branches: the share of table literals (dict, tuple, list of pairs) in the
   cluster against its if/elif chains
5. evidence: the header's VERSION line names the algorithm change, and a bench of the snapshot
   against the current file exists (the b_ suite has both as bench_ methods)
6. behaviour: the suite passes, the golden files are unchanged, `__all__` is the same or smaller,
   no test was edited to pass (tripwire 5)

Verdict (a row of the file pie, heavy weight, n/a for a first version or a version with no body change):
- green: behaviour kept (6) and complexity down 15% or more (1), or a measured gain of 10% or more in
  the bench (5), and the header says what changed
- grey: behaviour kept, no measurable change either way
- orange: behaviour kept, complexity or size up with no new exported name; or the header claims an
  algorithm change that the diff cannot show
- red, forced: the suite had to be edited to pass; or an "algorithm" change that only moved or
  renamed bodies; or a bench shows a regression the header does not explain

Open points
10. The header word that marks an algorithm change (an `algo:` tag in the VERSION line?).
11. Cost: the checker would call `git show` for the previous version; cached by commit hash.
12. Measure 4 rewards tables over branches; the user to say if that is the right direction.

## Built in tools/primary/spaghettichk.py (m01.v03, 2026-11-05), and how the open points were read
Built: peek, importers, door, cycles, importclean (siblings and subs for an internal module, the whole tree for the
front door), length, twin (compiled twin), constants, and the Error exemption of allsize limited to one hierarchy.
Weights are in WEIGHTS, the length bands in LENGTH (11-18 green, 7-21 grey, 5-30 orange, outside red).
Not built: evolution, surface, the orange function-level-import case of cycles.

Readings I took, to be corrected where wrong:
- "complexity 11-18 / 7-21 / 5-30" is built as the median number of lines of a function in the file (code lines,
  no blank, comment or docstring lines), not the tangle count, which has its own limits (15 is red).
- importclean counts a name as used when it is a word of the user's code or a quoted key (FUN['write_rows']).
- "wide" is everything under the parent of the folder's parent (here the Claude root), skipping results, z_sandbox,
  zprev, fixtures, golden, pyxfiles, build; a file whose own folder holds a module of the same name is left out.
- A compiled twin is a .pyx whose header says "pure-Python" or "Python loop/version"; it is not a satellite and must
  have a Speed section that gives each exported function a gain as "N x".
- cycles is the import graph among the modules of the folder, including imports inside functions.
- Known noise: the suites in mumix/tests import the modules of xlw, xlw2 and xlw3 by the same names, so each folder
  looks used from outside; and an exposed base class of the used exceptions (XlwError) counts as unused.
