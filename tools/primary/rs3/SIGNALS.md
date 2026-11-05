# rs3 signals

A signal is a message from one block to another on the same page. The emitter writes `name`, a receiver
defines `onName`. The manager (html/manager.js) routes them; a handler can respond but cannot avoid, change
or hold a signal. Each `pane_NAME.py` lists what it receives (`IN`) and what it emits (`OUT`). What a block can find for the status bar's Find
is what its `write()` returns as `search` (`files`, `text`, `names`, `log`): the bar offers those of the page's blocks.

## Who gets a signal
Three ways, and a signal's data or its sender's layout list may narrow it:

| Way | What | Signals |
|:--|:--|:--|
| everyone | every block with the handler | all not listed below |
| `to` | the data holds `to: [locators]`: only those blocks | `selectfunk` (methods sends it back to the code it follows), `showfile` (from the manager) |
| nearest | `PAGE.routed`: of each kind of block that listens, the one nearest the sender in the layout: the most groups `[...]` shared with it, then the first after the sender (round the end). The sender's `blk{a,b}` in the layout string names the receivers instead | `commentline`, `commentselect` (code to editbox), `saved` (editbox to code and methods) |

A name that starts with `mng` goes to the manager only: no block listens to one, and the manager decides who gets what.

## Files
`ftv` emits `mngshowfile {path, show, to?}` (`to: 'tab'` for a report page). The manager sends `showfile {path, show}`
to the blocks that take files (`takes` in what `write()` returns): the ones the layout list (`ftv{a,b}`) or `to` names, else a
container (`holds`: toptabs holds code, so a code block on its page is only the place its tabs show their file) before a lone
block, else a new browser tab. `show: false` closes: `showfile` goes to the panes that show the file (and the tab is closed).
A block that shows a file, or stops showing it (a tab switch too), says so with `showcode {path, loc, on}` to
everyone (the manager does it for a browser tab, `loc: 'tab'`): ftv marks the file, methods loads or blanks its list,
the editbox forgets a comment. methods follows the last `showcode` on and goes back to that pane with `selectfunk`.

| Block | Emits (OUT) | Receives (IN) |
|:--|:--|:--|
| manager | `showfile {path, show}`, `showcode {path, loc: 'tab', on}` (a browser tab), `newtabopened {path}`, `closingmaintab {path}`, `status {...}`, `busy {on}`, `log {rows\|reset}` | `closemaintab`, `showpane {block, on}` (it shuts or opens the pane to its strip), `withlineno {on}` and `withwrap {on}` (it sets the page's classes), `withconfig` (it sets the font, size, tab width and colour on the page), and `mngshowfile` (who gets the file) |
| ftv | `mngshowfile {path, show, to?}`, `showpane {block, on}`, `notice {text, bad}` (the tree stopped at its file limit) | `onShowcode`, `onSearchtext` (mode files) |
| code | `showcode {path, loc, on}`, `linenoClicked {lineno}`, `commentline {path, base, line}`, `commentselect {path, base, first, last, tag, text}`, `searchcount {index, total}` | `onShowfile {path, show}`, `onSelectfunk {lineno}`, `onShowmethods {path, ranges, focus}` (fold the file to those lines, or grey the rest), `onSaved`, `onSearchtext`/`onSearchnext`/`onSearchprev` (mode text) |
| toptabs | `mngshowfile` (the files its page was made with), and its code panes' (`showcode`, `linenoClicked`, `commentline`, `commentselect`, `searchcount`) as this block | `onShowfile`, and the code ones (`selectfunk`, `showmethods`, `saved`, search), handed to the tab shown |
| methods | `selectfunk {lineno, to}`, `showmethods {path, ranges, focus, to}` (the lines of the methods it shows or has picked, only while a filter is on or two rows are picked; `focus`: a double click), `showpane {block, on}` | `onShowcode`, `onLinenoClicked`, `onSaved`, `onSearchtext` (mode names) |
| editbox | `saved {path}`, `notice {text, bad}` | `onCommentline`, `onCommentselect`, `onShowcode` (off: forget the comment of that file), `onWithconfig` |
| options | `withlineno {on}`, `withwrap {on}`, `showpane {block, on}` | none |
| statusbar | `searchtext {text, mode}`, `searchnext {mode}`, `searchprev {mode}`, `searchhome {mode}` (the star: back to where the view was before the search), `withlineno {on}`, `withwrap {on}`, `withconfig` | `onSearchcount`, `onStatus`, `onBusy {on}`, `onNotice {text, bad}` |
| search | `searchtext {text, mode}`, `searchnext {mode}`, `searchprev {mode}` | `onSearchcount` |
| serverstatus | none | `onStatus` |
| log | none | `onLog {rows\|reset}`, `onSearchtext` (mode log) |
| doc | `searchcount {index, total}` | `onSearchtext`/`onSearchnext`/`onSearchprev`/`onSearchhome` (mode text) |

## Signals added while building (not in the design talk)
`commentline`, `commentselect` (code to editbox: which lines the user clicked), `saved` (editbox to
code, methods: the file changed, read it again), `searchtext`/`searchnext`/`searchprev`/`searchcount`
(the search block), `withwrap`, and the manager's `status` and `log` for the pulse. `showcode` also
comes from `code` when a tab switch brings its pane to the front or puts it behind (so methods and ftv follow).

## Known gaps in the list
- `newtabopened` and `closingmaintab` have no receiver yet (a block that wants to show open tabs
  would take them).
- `closemaintab` has no emitter yet: the button that closes a tab is not built.
