# rs3 signals

A signal is a message from one block to another on the same page. The emitter writes `name`, a receiver
defines `onName`. The manager (manager.js) routes them; a handler can respond but cannot avoid, change
or hold a signal. `where` is the number of the pane a signal is for (the nth code/toptabs pane, the nth
methods pane, and so on; 0 is a new browser tab); a block with a number acts only on its own.
Each `pane_NAME.py` lists what it receives (`IN`) and what it emits (`OUT`).

| Block | Emits (OUT) | Receives (IN) |
|:--|:--|:--|
| manager | `newtabopened {path}`, `closingmaintab {path}`, `status {...}`, `log {rows\|reset}` | `closemaintab`, and `openfile`/`closefile` when no pane takes a file (it opens or closes a browser tab) |
| ftv | `openfile {path, where}`, `closefile {path, where}` | `onOpenfile`, `onClosefile`, `onSearchtext` (mode files) |
| code | `closefile` (its content is wiped or the pane removed), `openfile` (the pane became visible), `linenoClicked {lineno}`, `commentline {path, base, line}`, `commentselect {path, base, first, last, tag, text}`, `searchcount {index, total}` | `onOpenfile`, `onClosefile`, `onSelectfunk {lineno}`, `onWithlineno {on}`, `onWithwrap {on}`, `onSaved`, `onSearchtext`/`onSearchnext`/`onSearchprev` (mode text) |
| toptabs | none (its code panes emit) | `onOpenfile`, `onClosefile`, and the code ones, handed to the tab shown |
| methods | `selectfunk {lineno}` | `onOpenfile`, `onClosefile`, `onLinenoClicked`, `onSaved`, `onSearchtext` (mode names) |
| editbox | `saved {path}` | `onCommentline`, `onCommentselect`, `onClosefile` |
| options | `withlineno {on}`, `withwrap {on}` | none |
| search | `searchtext {text, mode}`, `searchnext {mode}`, `searchprev {mode}` | `onSearchcount` |
| serverstatus | none | `onStatus` |
| log | none | `onLog {rows\|reset}`, `onSearchtext` (mode log) |
| doc | none | none |

## Signals added while building (not in the design talk)
`commentline`, `commentselect` (code to editbox: which lines the user clicked), `saved` (editbox to
code, methods: the file changed, read it again), `searchtext`/`searchnext`/`searchprev`/`searchcount`
(the search block), `withwrap`, and the manager's `status` and `log` for the pulse. `openfile` also
comes from `code` when a tab switch makes its pane visible (so methods and ftv follow).

## Known gaps in the list
- `newtabopened` and `closingmaintab` have no receiver yet (a block that wants to show open tabs
  would take them).
- `closemaintab` has no emitter yet: the button that closes a tab is not built.
