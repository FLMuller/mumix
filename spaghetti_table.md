# spaghetti table of mumix

Judged by spaghettichk over 80 Python files of mumix (the folders z_sandbox, oldsuite, rs3twolex, rs3vcdep are old copies and are left out; 69 files). Index = the mean of the file score and the size-weighted mean score of its functions and classes (0 worst, 100 best). Scope as agreed: the callers of a name are searched in the files of its own folder; the suites are b_<name>.py of the tests folder.

## Production files, worst first

| # | file | lines | band | file | rows | funcs | red | orange | dots | what stands out |
|--:|:--|--:|:--|--:|--:|--:|--:|--:|--:|:--|
| 1 | mumix/xlw/xlsheet.py | 658 | red | 9 | 57 | 34 | 7 | 3 | 0 | imports: 5 standard, 4 other, 1 load/use; allsize: 30 name(s) in __all__; tangle grey x3; tangle red x2 |
| 2 | mumix/tools/primary/reportserver.py | 883 | red | 7 | 61 | 39 | 10 | 4 | 0 | imports: 18 standard, 1 other, 1 load/use, an automated import; allsize: 12 name(s) in __all__; tangle grey x6; tangle red x5; tested orange x2 |
| 3 | mumix/svgchart/svgchart.py | 708 | red | 12 | 62 | 27 | 5 | 1 | 0 | imports: 4 standard, 6 other, 0 load/use; allsize: 11 name(s) in __all__; tangle red x4; tangle grey x3 |
| 4 | mumix/xlw/tkv.pyx | 622 | red | 54 | 21 | 38 | 28 | 3 | 0 | allsize: 9 name(s) in __all__; header: header names 2 of 10 exposed, no VERSION lines; poke red x9; tangle red x9; tangle grey x1 |
| 5 | mumix/tools/primary/vcserver.py | 356 | red | 14 | 66 | 15 | 4 | 0 | 0 | imports: 8 standard, 3 other, 1 load/use; allsize: 7 name(s) in __all__; tangle grey x1; readsrc red x1; tangle red x1 |
| 6 | mumix/xlw/xlreader.py | 766 | orange | 23 | 58 | 25 | 6 | 3 | 0 | imports: 4 standard, 5 other, 0 load/use; allsize: 3 name(s) in __all__; tangle red x6; tangle grey x4; tangle orange x1 |
| 7 | mumix/xlw/kv.pyx | 457 | orange | 54 | 26 | 22 | 21 | 0 | 0 | allsize: 6 name(s) in __all__; header: header names 5 of 7 exposed, no VERSION lines |
| 8 | mumix/xlw/xlw.py | 587 | orange | 23 | 59 | 41 | 14 | 4 | 0 | imports: 2 standard, 10 other, 0 load/use; allsize: 5 name(s) in __all__; getattr orange x1; tangle grey x1; tangle red x1 |
| 9 | mumix/mumix.py | 492 | red | 25 | 59 | 16 | 3 | 0 | 0 | imports: 5 standard, 5 other, 2 load/use; allsize: 13 name(s) in __all__; getattr red x1; tangle grey x1 |
| 10 | mumix/tools/use.py | 889 | red | 36 | 51 | 41 | 16 | 1 | 7 | imports: 10 standard, 0 other, 1 load/use, an automated import; allsize: 7 name(s) in __all__; getattr red x9; readsrc red x5; tangle red x3 |
| 11 | mumix/tools/primary/use.py | 889 | red | 36 | 52 | 41 | 16 | 1 | 7 | imports: 10 standard, 0 other, 1 load/use, an automated import; allsize: 7 name(s) in __all__; getattr red x9; readsrc red x5; tangle red x3 |
| 12 | mumix/xlw/xlparts.py | 167 | red | 27 | 61 | 11 | 3 | 0 | 0 | allsize: 13 name(s) in __all__; foreign: a module with over 5 names in __all__: xlstyle |
| 13 | mumix/xlw/xlchart.py | 615 | red | 18 | 72 | 37 | 4 | 1 | 0 | allsize: 10 name(s) in __all__; foreign: a module with over 5 names in __all__: xlparts, xlstyle; tangle grey x4; tangle red x1 |
| 14 | mumix/tools/bench.py | 1116 | red | 46 | 45 | 62 | 16 | 7 | 16 | imports: 11 standard, 4 other, 3 load/use, an automated import; foreign: a module with over 5 names in __all__: use; classdata orange x4; getattr red x4; tangle red x3 |
| 15 | mumix/tools/primary/rs3/rs3util.py | 562 | red | 39 | 54 | 30 | 5 | 4 | 0 | allsize: 5 name(s) in __all__; foreign: a module with over 5 names in __all__: rs3layout; tangle red x4; tested orange x3; tangle grey x3 |
| 16 | mumix/xlw/xlstyle.py | 534 | red | 50 | 43 | 22 | 4 | 0 | 0 | allsize: 17 name(s) in __all__; locals: 7 local function(s), 0 class(es); tangle red x3; tangle grey x2 |
| 17 | mumix/tools/runbench.py | 1084 | orange | 46 | 52 | 48 | 16 | 0 | 0 | imports: 16 standard, 5 other, 2 load/use; foreign: a module with over 5 names in __all__: use; tangle red x8; getattr red x2; tangle grey x2 |
| 18 | mumix/tools/primary/rs3/rs3pages.py | 348 | red | 23 | 76 | 20 | 2 | 1 | 1 | imports: 9 standard, 2 other, 0 load/use, an automated import; allsize: 3 name(s) in __all__; readsrc red x1; tangle red x1; tangle grey x1 |
| 19 | mumix/tools/vcomment.py | 216 | red | 39 | 60 | 8 | 1 | 0 | 0 | imports: 6 standard, 5 other, 2 load/use; foreign: a module with over 5 names in __all__: use; tangle red x1; tangle grey x1 |
| 20 | mumix/htmlreport/report.py | 239 | red | 38 | 64 | 12 | 9 | 0 | 0 | allsize: 11 name(s) in __all__; header: header names 10 of 11 exposed, no VERSION lines; tangle grey x1 |
| 21 | mumix/odeproblem/odeproblem.py | 381 | grey | 59 | 46 | 23 | 7 | 1 | 0 | allsize: 4 name(s) in __all__; locals: 7 local function(s), 4 class(es); getattr red x1; classdata orange x1; tangle grey x1 |
| 22 | mumix/tests/gridcheck.py | 55 | red | 50 | 56 | 6 | 4 | 0 | 0 | allsize: no __all__; locals: 4 local function(s), 1 class(es) |
| 23 | mumix/tools/primary/codemark.py | 292 | grey | 59 | 47 | 8 | 3 | 0 | 2 | imports: 5 standard, 3 other, 1 load/use; foreign: a module with over 5 names in __all__: use; readsrc red x1; tangle red x1 |
| 24 | mumix/tools/primary/rs2/rscore.py | 134 | red | 32 | 76 | 7 | 0 | 1 | 0 | allsize: no __all__; foreign: imports rsfiles (no __all__); tangle grey x1 |
| 25 | mumix/tools/primary/spaghettichk.py | 341 | orange | 64 | 45 | 13 | 5 | 0 | 1 | foreign: a module with over 5 names in __all__: use; locals: 9 local function(s), 1 class(es); tangle red x5; tangle grey x1 |
| 26 | mumix/tools/primary/mdwriter.pyx | 138 | green | 86 | 22 | 4 | 4 | 0 | 4 | allsize: 4 name(s) in __all__; tangle grey x1 |
| 27 | mumix/tools/primary/rs2/rsvcomment.py | 73 | red | 32 | 81 | 5 | 0 | 4 | 0 | allsize: no __all__; foreign: imports rsfiles (no __all__) |
| 28 | mumix/xlw/xlsheetfun.pyx | 463 | green | 77 | 39 | 3 | 3 | 0 | 0 | allsize: 3 name(s) in __all__; header: header names 3 of 3 exposed, no VERSION lines; tangle red x2; tangle orange x1 |
| 29 | mumix/tools/primary/htmlwriter.py | 95 | grey | 59 | 58 | 6 | 5 | 0 | 5 | allsize: 5 name(s) in __all__; foreign: a module with over 5 names in __all__: use |
| 30 | mumix/tools/primary/vcode.py | 200 | grey | 59 | 59 | 9 | 1 | 1 | 2 | imports: 4 standard, 4 other, 1 load/use; foreign: a module with over 5 names in __all__: use, vclang; tangle red x1 |
| 31 | mumix/tools/primary/rs2/rsfiles.py | 247 | red | 54 | 70 | 14 | 1 | 2 | 0 | allsize: no __all__; locals: 14 local function(s), 0 class(es) |
| 32 | mumix/tools/primary/mdwriter.py | 137 | green | 86 | 39 | 6 | 6 | 0 | 4 | allsize: 4 name(s) in __all__; tangle red x2; tangle grey x1 |
| 33 | mumix/tools/primary/rs3/rs3table.py | 46 | green | 100 | 25 | 4 | 4 | 0 | 4 | classdata orange x1 |
| 34 | mumix/tools/primary/codelex.py | 611 | green | 77 | 49 | 17 | 4 | 1 | 4 | allsize: 4 name(s) in __all__; locals: 9 local function(s), 0 class(es); tangle red x4; tangle grey x2; tangle orange x1 |
| 35 | mumix/xlw/xlstore.py | 28 | green | 64 | 0 | 0 | 0 | 0 | 0 | foreign: a module with over 5 names in __all__: kv, tkv; header: header names 2 of 2 exposed, no VERSION lines |
| 36 | mumix/tests/chartcheck.py | 129 | green | 68 | 60 | 3 | 2 | 0 | 0 | allsize: 4 name(s) in __all__; header: header names 3 of 4 exposed, no VERSION lines; tangle red x1 |
| 37 | mumix/tools/primary/cumulette.py | 416 | green | 77 | 51 | 13 | 3 | 3 | 7 | allsize: 3 name(s) in __all__; locals: 5 local function(s), 5 class(es); tangle grey x1; getattr red x1; tangle red x1 |
| 38 | mumix/tools/primary/vclang.py | 544 | red | 64 | 65 | 21 | 2 | 0 | 0 | allsize: 8 name(s) in __all__; locals: 11 local function(s), 2 class(es); tangle grey x2; tangle red x2 |
| 39 | mumix/tools/primary/rs3/rs3layout.py | 340 | red | 68 | 66 | 23 | 3 | 1 | 9 | allsize: 8 name(s) in __all__; locals: 7 local function(s), 1 class(es); tangle red x3; tangle grey x1 |
| 40 | mumix/tools/primary/rs2.py | 801 | red | 79 | 60 | 38 | 5 | 6 | 0 | imports: 17 standard, 0 other, 0 load/use, an automated import; locals: 34 local function(s), 0 class(es); tangle red x3; getattr red x2; readsrc red x1 |
| 41 | mumix/tools/primary/rs3.py | 841 | red | 79 | 60 | 38 | 5 | 4 | 0 | imports: 17 standard, 1 other, 0 load/use, an automated import; locals: 34 local function(s), 0 class(es); tangle red x4; tangle grey x2; getattr red x1 |
| 42 | mumix/tools/primary/rs3/rs3comment.py | 480 | green | 82 | 57 | 28 | 5 | 4 | 0 | imports: 5 standard, 2 other, 3 load/use; locals: 24 local function(s), 0 class(es); tangle red x4; tangle grey x3; readsrc red x1 |
| 43 | mumix/tools/primary/rs3/rs3jsguard.py | 336 | green | 96 | 48 | 7 | 4 | 0 | 0 | locals: 5 local function(s), 0 class(es); tangle red x4; tangle grey x1 |
| 44 | mumix/tools/primary/rs3/rs3core.py | 232 | green | 82 | 71 | 15 | 0 | 2 | 0 | locals: 14 local function(s), 0 class(es); header: header names 0 of 1 exposed, VERSION lines; tangle grey x2 |
| 45 | mumix/odeproblem/fields.py | 71 | green | 91 | 62 | 3 | 2 | 0 | 0 | header: header names 1 of 1 exposed, no VERSION lines |
| 46 | mumix/tools/primary/marked.py | 743 | green | 91 | 64 | 20 | 7 | 1 | 1 | locals: 18 local function(s), 0 class(es); tangle red x6; tangle grey x1 |
| 47 | mumix/tools/primary/rs3/marked.py | 743 | green | 91 | 64 | 20 | 7 | 1 | 1 | locals: 18 local function(s), 0 class(es); tangle red x6; tangle grey x1 |
| 48 | mumix/tools/primary/rs3/panes/pane_doc.py | 174 | green | 96 | 61 | 8 | 2 | 2 | 1 | locals: 6 local function(s), 0 class(es); tangle red x1; tangle grey x1 |
| 49 | mumix/tools/primary/rs3/rs3lex.pyx | 1445 | green | 93 | 64 | 52 | 8 | 6 | 0 | locals: 32 local function(s), 4 class(es); tangle red x8; tangle grey x7; tested orange x3 |
| 50 | mumix/tools/primary/rs3/panes/pane_code.py | 59 | green | 100 | 57 | 1 | 1 | 0 | 1 |  |
| 51 | mumix/tools/primary/rs3/panes/pane_editbox.py | 46 | green | 100 | 57 | 1 | 1 | 0 | 1 |  |
| 52 | mumix/tools/primary/rs3/panes/pane_ftv.py | 47 | green | 100 | 57 | 1 | 1 | 0 | 1 |  |
| 53 | mumix/tools/primary/rs3/panes/pane_log.py | 36 | green | 100 | 57 | 1 | 1 | 0 | 1 |  |
| 54 | mumix/tools/primary/rs3/panes/pane_methods.py | 49 | green | 100 | 57 | 1 | 1 | 0 | 1 |  |
| 55 | mumix/tools/primary/rs3/panes/pane_options.py | 27 | green | 100 | 57 | 1 | 1 | 0 | 1 |  |
| 56 | mumix/tools/primary/rs3/panes/pane_search.py | 36 | green | 100 | 57 | 1 | 1 | 0 | 1 |  |
| 57 | mumix/tools/primary/rs3/panes/pane_serverstatus.py | 34 | green | 100 | 57 | 1 | 1 | 0 | 1 |  |
| 58 | mumix/tools/primary/rs3/panes/pane_statusbar.py | 74 | green | 100 | 57 | 1 | 1 | 0 | 1 |  |
| 59 | mumix/tools/primary/rs3/panes/pane_toptabs.py | 66 | green | 100 | 57 | 1 | 1 | 0 | 1 |  |
| 60 | mumix/tools/primary/marked.pyx | 744 | green | 100 | 59 | 2 | 1 | 0 | 1 |  |

## Suites (b_*.py), worst first

| # | file | lines | band | file | rows | funcs | red | what stands out |
|--:|:--|--:|:--|--:|--:|--:|--:|:--|
| 1 | mumix/tests/b_svgchart.py | 532 | orange | 0 | 42 | 53 | 3 | imports: 5 standard, 5 other, 3 load/use; getattr red x3; tangle orange x1 |
| 2 | mumix/tests/b_rs3.py | 1047 | orange | 0 | 42 | 73 | 5 | imports: 16 standard, 3 other, 0 load/use; readsrc red x4; tangle red x3; classdata orange x2 |
| 3 | mumix/tests/b_xlw.py | 840 | orange | 0 | 45 | 102 | 2 | imports: 6 standard, 5 other, 2 load/use; tangle grey x2; getattr orange x2; tripwire red x2 |
| 4 | mumix/tests/b_reportserver.py | 309 | orange | 0 | 45 | 30 | 3 | imports: 12 standard, 2 other, 0 load/use; getattr red x2; rewire red x2; classdata orange x1 |
| 5 | mumix/tests/b_mumix.py | 381 | orange | 0 | 46 | 43 | 0 | imports: 7 standard, 8 other, 0 load/use; classdata orange x1 |
| 6 | mumix/tests/b_vcserver.py | 522 | orange | 0 | 46 | 62 | 0 | imports: 10 standard, 4 other, 0 load/use; classdata orange x1 |
| 7 | mumix/tests/b_rs3util.py | 262 | red | 0 | 47 | 26 | 2 | imports: 5 standard, 3 other, 0 load/use, an automated import; readsrc red x2; classdata orange x1 |
| 8 | mumix/tests/b_rs2.py | 428 | orange | 0 | 47 | 41 | 0 | imports: 15 standard, 2 other, 0 load/use; classdata orange x2 |
| 9 | mumix/tests/b_xlsheet.py | 830 | orange | 0 | 47 | 68 | 5 | imports: 9 standard, 10 other, 1 load/use; rewire red x4; getattr red x2; classdata orange x1 |
| 10 | mumix/tests/b_vcomment.py | 235 | orange | 0 | 47 | 29 | 0 | imports: 11 standard, 3 other, 0 load/use; classdata orange x1 |
| 11 | mumix/tests/b_xlreader.py | 492 | orange | 0 | 49 | 40 | 0 | imports: 7 standard, 6 other, 3 load/use; tangle grey x1; classdata orange x1 |
| 12 | mumix/tests/b_rs3lex.py | 321 | red | 0 | 50 | 29 | 3 | imports: 8 standard, 2 other, 1 load/use, an automated import; readsrc red x3; tangle grey x1 |
| 13 | mumix/tests/b_kv.py | 1150 | grey | 50 | 45 | 136 | 4 | imports: 3 standard, 3 other, 1 load/use; getattr red x3; poke red x2; classdata orange x1 |
| 14 | mumix/tests/b_fields.py | 200 | grey | 50 | 45 | 26 | 0 | imports: 2 standard, 3 other, 1 load/use; classdata orange x1 |
| 15 | mumix/tests/b_odeproblem.py | 304 | grey | 50 | 46 | 42 | 4 | imports: 4 standard, 4 other, 2 load/use; getattr red x4; classdata orange x1 |
| 16 | mumix/tests/b_report.py | 323 | grey | 50 | 46 | 31 | 0 | imports: 5 standard, 4 other, 3 load/use; classdata orange x1; tangle grey x1 |
| 17 | mumix/tests/b_xlchart.py | 522 | grey | 50 | 47 | 50 | 0 | imports: 6 standard, 4 other, 2 load/use; classdata orange x1 |
| 18 | mumix/tests/b_tkv.py | 602 | green | 100 | 43 | 102 | 2 | poke red x2; classdata orange x1 |
| 19 | mumix/tests/b_vclang.py | 332 | green | 100 | 47 | 38 | 0 | classdata orange x1 |
| 20 | mumix/tests/b_rs3jsguard.py | 155 | green | 100 | 47 | 11 | 0 |  |

## How to read it

The table ranks the 60 production files by their index, worst first; the 20 suites are ranked apart because they are judged by
fewer rules (a suite has no `__all__` to expose). `dots` counts the names in `__all__` that no suite names (the red dot).
"What stands out" lists the file-level findings first, then the commonest function-level ones.

## Nature and severity, as I see it

**1. Giant state machines.** The worst *functions* are tokenisers: `rs3lex.scan` (complexity 213, 354 lines), `codelex.lex_line`
(125), `vclang.lexline` (77), `codemark.codemark` (68), `marked.inline` (65) and `marked.lex` (57). A tokeniser is a state machine, so
some branching is natural, but nothing about these is easy to read or test in pieces. Severity: high, and the biggest single
maintenance risk. My own new `spaghettichk.verdicts_row` (77) and `verdicts_file` (84) land on the same list: a rule checker with one
function per kind of item has the same shape. The checker marks its own file orange.

**2. The xlw family.** `xlw/xlsheet.py` (30 names in `__all__`, five very complex functions), `xlw.py`, `xlreader.py`, `xlstyle.py`
and `xlparts.py` are the worst *group*: mean index 42 against 66 for `tools/primary`. They expose too much (`xlsheet` 30 names,
`xlstyle` 17, `xlparts` 13), import widely from each other (`xlparts`, `xlchart` import from modules with long export lists) and
carry the tangled functions. `svgchart.py` (708 lines, four red-tangle functions) and `reportserver.py` (883 lines, an
automated import, 12 exported names, six red functions) are the other two files near the bottom. Severity: high for `xlsheet`,
`reportserver`, `svgchart`; medium for the rest.

**3. Whole files duplicated.** `tools/use.py` and `tools/primary/use.py` (889 lines each) are the same file, as are the two
`marked.py`, and the sandbox and `rs3twolex` / `rs3vcdep` folders hold more copies. The checker cannot see this yet (a body match
is not built), but it is the clearest duplication in the project. Severity: medium (it is a maintenance trap, not a defect).

**4. Reflection that is on purpose.** `use.py` is the loader: nine `getattr` calls on other objects, `sys._getframe`, five code
reads. It is flagged red, and a loader is the one place such code is justified. The rules cannot tell "on purpose" from "by
habit" (see the changes below). `bench.py` (1116 lines, 62 functions, 16 untested names in `__all__`) and `runbench.py` (1084 lines,
eight very complex functions) are the largest files in the project and both orange or red.

**5. Exposure without proof.** Of 134 names in `__all__` across the production files, 87 are named by no suite (65%). Only 39 have a
suite that mentions them. The red dots are densest in `bench.py` (16), `use.py` (7 in each copy), `mdwriter` and `htmlwriter`.

**6. What is good.** `tools/primary` as a group (39 files, mean 66): the new rs3 files, `rs3lex.pyx`, `marked.pyx`, `mdwriter.pyx` are
green at file level. Small files with a short, named `__all__` and a header with `VERSION` lines get green quickly. The panes
(`pane_*.py`) are green by file and each has one red-dot row (`write` has no suite naming it), which is a limit of black-box
suites that test through the server.

## Where the rules misjudge (found by running them on everything)

| What | Evidence | Change |
|---|---|---|
| `usage` red for names a framework calls | 1246 forced reds before the fix, mostly `test_*` and `bench_*` methods | done: those names are exempt; public methods also count calls from other files |
| `tripwire` on any trailing digit | `y0`, `test_T49_..._100`, `b_rs3` were all flagged | done: only when a name without the digit exists in the file |
| a suite is judged like a library | every `b_*.py` got "no `__all__`" | done: a suite is judged by its imports and its functions only |
| `foreign` orange for importing from any module with more than 5 exports | 13 files, all because of `use` (7 names) | drop it; the size of an export list is already `allsize` |
| a class takes every finding of its methods | `b_rs3` and the other suite classes are red because one method reads code | make a class row hold its own findings (private names, data attributes, docs) and show its methods' share |
| `callers` counts only the files of the same folder | `rs3util.asset` shows "1 other module" though every pane uses it | search the folder and its subfolders for callers |
| `poke` on deliberate privates | `sys._getframe`, `d._note` in a test of that very name | a short list of allowed names; the suite's own reach is `suitepeek` |
| `readsrc`, `rewire` in suites | the policy tests read code on purpose | leave out of suites |
| `.pyx` is judged by the same patterns | a Cython `cdef` function with typed parameters has no parameter list in the facts | read the typed parameters |

## Rules I would add

1. **Duplicated file or body.** First the cheap one: two files in the area with the same text, or the same normalised function body (sha1 of the tokens without names), red. It
   finds `use.py` and `marked.py` at once. (small)
2. **Length.** A function over 150 lines is red whatever its complexity; a module over 800 lines is orange, over 1000 red. The lexers and `bench.py` would show.
3. **Many parameters.** More than 6 is orange, more than 9 red. (small)
4. **Swallowed errors.** A bare `except:`, or `except Exception:` whose body is only `pass`, red. (small)
5. **Import cycles between siblings.** A imports B and B imports A: red on both. (small, from the imports)
6. **Complexity per 100 lines**, as a second measure, so a long but flat table-driven function is judged fairly.
7. **Mutable module state.** `global` assignments and module-level lists or dicts that functions mutate: orange. (medium)
8. **Constants hygiene** (the header rule that is not built): numbers and strings inside functions other than 0, 1, -1 and empty text, against the
   constants defined: needs your definition of "embedded". (medium)
9. **Docstring bloat** and **comment density**: very long docstrings against short code. (small)
10. **Parallel names**: two functions in different files with the same parameters and returned names are already found as signature twins; widen to the whole
    folder tree. (small)

## Weights: what I would change from the first table

| rule | now | suggested | because |
|---|---|---|---|
| tangle | 4 | 6 | it is where the worst spaghetti is, and it is mostly diluted by the many small green rules |
| callers | 3 | 2 | the same-folder scope makes it noisy for shared infrastructure |
| local | 2 | 1 | 1100 verdicts, mostly grey or orange for underscore names; it should not swing a pie |
| usage | 3 | 3 | right; the forced red on never-called code is useful once the framework names are exempt |
| docs | 3 | 3 | 219 red (no docstring on an exposed name or class) is a fair finding |
| duplication | 4 | 6 | once whole-file and body duplicates exist, the pie should show them |
| getattr | 6 | 6 | keep; add the allowed-names list |
| header | 2 | 3 | the file's story is only as good as its header |

The thresholds for red and orange (15% and 35%) put 61 of 148 files in red and 18 in orange. With the weights above and the
class change I would expect roughly a third of the files red; the bands can be moved in the `Bands` sheet of the workbook.
