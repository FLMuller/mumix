# The report server: addresses and commands

The server runs on this machine only, `127.0.0.1`, port **47653**. There are three ways to talk to it: an address in a browser,
a message from a program, and the command line. The page grammar (layout string, sizes, locators) is in `layoutstring.md`;
the signals between the blocks of a page are in `SIGNALS.md`.

## 1. Addresses (a browser, HTTP GET)

| Address | What it serves |
|---|---|
| `/reportserver` | the monitor page: file tree, server status, log, stop and restart. Any path that starts with `reportserver`, or `/?reportserver...`, is the same page |
| `/?layout=LAYOUT&...` | **the layout command**: a page made by its address, of the blocks the layout names (section 2) |
| `/code/PATH` | the viewer of one file: methods list, code, comment box (`[methods,[code;editbox]]`). PATH is the file from the Claude folder without the `./`, for example `/code/mumix/tools/use.py`. A code, markdown or text file inside that folder; anything else is a 404 |
| `/page/KEY.html` | a page made by a program (`load`, section 3) that was too long to be an address; the last 50 are kept, and a restarted server builds them again |

Anything else is a 404, and `/` alone is a 403.

Examples (the first opens the viewer of a file, the second a page of the file tree and tabs):

```
http://127.0.0.1:47653/code/mumix/tests/b_rs3jsguard.py
http://127.0.0.1:47653/?layout=[ftv,[toptabs;[methods,[code;editbox]]]]&toptabs=mumix/tools/{reportserver.py,rs_primary/**}
```

## 2. The layout command: `/?layout=...`

The address *is* the page: the same address always makes the same page, nothing is kept, and a page is a link you can paste.

| Part | Meaning |
|---|---|
| `layout=LAYOUT` | the blocks and where they sit: `[a,b]` a row, `[a;b]` a column, nested to any depth. A name is a block (`ftv`, `toptabs`, `methods`, `code`, `editbox`, `log`, `doc`, ...) |
| `&LOCATOR=DATA` | the data of a block, named like its locator: `&toptabs=mumix/tools/**.py`, `&doc=mumix/results/x.html` |
| `&title=my_page` | the page's title (`_` is a space) |
| `&selftest=1` | runs the page's own self test |

Writing the address: no spaces after `,` or `;` (a needed space is `_`); `/ [ ] ; , ( ) { } *` are written as they are, other characters
are percent-encoded (a space in a file name is `%20`). A page whose data cannot be written this way (a comma or brace in a path, a
block whose data is html, an address over 6000 characters) is made by `load` instead and lives at `/page/KEY.html`.

Paths in data are from the Claude folder (`./` optional); `*`, `?`, `**` and `{a,b}` open to the files they name when the page is built.

### A report file

`/?layout=[doc]&doc=FILE` shows an html file (a report) in a box that its script and css cannot get out of. A page whose script
says more than the box allows is served as the file itself, its own page with no panes. In a doc:

- `{{layout=[mt,[cd;eb]],./path/to/file.py}}` in the html becomes the **panes of that file** (methods, code, comment box) in that place:
  several may be in one page, each with its own locators.
- `toptabs` takes `[title, html-or-./path.html, bad]` sections, each a doc of its own.

## 3. Messages from a program: `contactRS`

```python
from reportserver import contactRS, ReportServerError
got = contactRS('load', '[ftv,[toptabs;[methods,[code;editbox]]]]', {'toptabs': ['toptabs', './mumix/tools/use.py']}, 'my title', True)
```

`contactRS(verb, *fields)` raises `ReportServerError` (`.reply` is the server's answer) when the server does not carry the request out.
One message to the server is at most **64 KB**: a long page is given by the `./` paths of files, not by its html.

| Verb | Fields | Answer / what it does |
|---|---|---|
| `ping` | | `{pong, boot, time}`: is it awake; `boot` says which start |
| `status` | | boot, pid, port, start time, uptime, pages, connections |
| `load` | `layout, blocks, title, show, selftest` | makes a page of blocks: `{hash, url, path}`. `show` true opens it in the default browser, false only answers |
| `view` | `path, show` | opens one file as a commentable page (`/code/...`) |
| `monitor` | | opens the monitor page unless one is open |
| `config` | `change` | the settings the pages share (font, size, initials, line numbers, wrap, tab width, colour); a change that is not allowed changes nothing |
| `tree` | `hash` | the files of a page's root (the file tree block) |
| `open` | `hash, path` | one file as numbered lines with its comments |
| `methods` | `hash, path` | the functions, classes and constants of a file, with their colours |
| `check` | `hash, filename` | may comments be added to that file |
| `update`, `insert` | one dict | change, remove or add a comment on lines |
| `hello`, `pulse` | | what a page says to be known, and the monitor's once-a-second look at status and log |
| `stop`, `restart` | | the server ends (restart: a new one takes the port over, and open pages reconnect) |
| `snap`, `trigger` | `to, sel` | ask an open page to post a picture of itself, or press a button |

`hash` is the page's own id (a page says which one it is with `hello`); the verbs on files use the root of that page.

## 4. The command line

```
python mumix/tools/reportserver.py --status
python mumix/tools/reportserver.py --start --by NAME      start (a label for the log)
python mumix/tools/reportserver.py --stop --by NAME
python mumix/tools/reportserver.py --restart --by NAME    close, start a new one; pages reconnect, no page is opened
python mumix/tools/reportserver.py --show [FILE ...]      start if need be, show the server page unless one is open, open the files
```

`.claude/vscripts/reportserver.bat` does the same by double click or with words: no word (start and show the page), `FILE ...`
(open these through the server), `restart`, `close` (or `stop`), and for a program `--by NAME --start [--hidden]`.
