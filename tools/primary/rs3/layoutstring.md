# The layout string and the page address

A page of rs3 is **blocks** (ftv, toptabs, methods, code, editbox, log, ...) placed by a **layout string**.
The same string is the address of the page, so a page is a link you can paste:

```
http://127.0.0.1:47653/?layout=[ftv,[toptabs;[methods,[code;editbox]]]]&toptabs=mumix/tools/primary/{rs3.py,rs3/**}
```

Code: `rs3layout.py` (the grammar, `parse`, `plain`, `render`), `rs3pages.py` (the address, `page_url`, `query_page`,
`wild`). Tests: `tests/b_rs3.py` (T5 to T8, T10).

## 1. Groups, rows and columns

| Written | Meaning |
|---|---|
| `[a,b,c]` | a **row**: a, b and c side by side |
| `[a;b;c]` | a **column**: a, b and c one under the other |
| `[ ]` inside `[ ]` | groups nest, to any depth |

A group uses one separator kind: `,` or `;`, never both. A name may be followed by `{locators}`: `editbox{cd.2}`
(see section 2a). A name that is not a group is a **block**:
`ftv`, `toptabs`, `methods`, `code`, `editbox`, `log`, `serverstatus`, `doc`, ...

`[ftv,[toptabs;[methods,[code;editbox]]]]` is:

```
+-----+---------------------------------+
|     |  toptabs                        |
| ftv +---------+-----------------------+
|     | methods |  code                 |
|     |         +-----------------------+
|     |         |  editbox              |
+-----+---------+-----------------------+
| statusbar                             |
+---------------------------------------+
```

The server always adds the **status bar** as the last row (`statusbar wx7`, 7 mm high): no layout can lose it.

## 2. Two of a kind

A locator is the kind of block it is, then an optional `.suffix` that tells two of a kind apart: `eb`, `eb.1`,
`eb.notes`, `cd.2`, `ftv.py`. The kind is the block's name or its short name:

| Short | Block | | Short | Block |
|---|---|---|---|---|
| `tt` | toptabs | | `cd` | code |
| `mt` | methods | | `eb` | editbox |

`ftv`, `log` and `doc` are short already. Nobody writes `serverstatus`, `statusbar`, `options` or `search`: the monitor and
the status bar have them. Digits with no `.` are not a suffix: `cd3` is no kind, so it is defined at the end of the layout,
`[ftv,[cd.1,cd3]]{cd3=code}` (`{a=code,b=methods}` for several).

An address is written the short way when a page has several blocks of a kind (`[cd.1,cd.2,editbox]`) and with the
block's own name when it has one (`code`): `cd`, `code` and `code.1` are the same block on a page with one code block, and
the address says `code`. The data of a block is the parameter of its locator: `&cd.1=src/a.py`.

## 2a. Who a block sends to: `blk{a,b}`

Some signals of a block go to one pane, not to all (SIGNALS.md): a comment click of a code pane goes to an editbox, the
`saved` of an editbox to a code pane and a methods block, a click in ftv sends the file to a pane that takes it. Without a
list the manager picks, for each kind of block that listens, the one **nearest** in the layout: the one that shares most
groups `[...]` with the sender, and of those the first after the sender (round the end). So `[cd1,[cd2,eb]]`
gives cd2 to eb, `[[eb,cd1,cd2],cd3]` gives cd1.

`eb{cd2}` names the receivers instead: `[[cd0,eb{cd2},cd1,cd2],cd3]` sends eb's to cd2; `eb{cd0,cd2}` to both. Every
name must be in the layout, not the block itself, and take what the block sends (a code block takes `saved`, a block that
takes files takes the file of `ftv{...}`); a list that fails is refused with the reason. A file clicked in ftv goes to
a container (toptabs) before a lone code block, else to a new browser tab; an html report always to a new tab.

## 3. Sizes: `wxh`

A size follows a name (or a group) after a space: `ftv 75dxh`. It is **width x height**, written
`WIDTH` `x` `HEIGHT`. Each of the two values is one of:

| Value | Means |
|---|---|
| `w` (width) or `h` (height) | **fill**: take what is left (this is where "wxh" comes from: w = fill the width, h = fill the height) |
| a number, `75` | that many **millimetres** |
| `75d` or `wd` | the same, and the edge on that side is **draggable** (`d`) |
| `2f` | a **share** of what is left: `2f` gets twice as much as `w` (= `1f`) |

So `wxh` is fill both ways, `75dxh` is 75 mm wide (draggable) and full height, `wx42d` is full width and 42 mm high
(draggable). One value alone is the width: `50` is `50xh`.

**Along or across.** In a **row** the width is the size along the row (the *main* size) and the height is the size
across it; in a **column** the height is the main size. The main size does the work: a number is fixed, `w`/`h` shares
what is left. The across size fills unless it is a number. The `d` of either value makes the **main** edge draggable.

**The bar.** A draggable edge has a 1 mm bar. It goes *after* the item, and *before* the item when that is the last
of its group (`editbox` under the code), so the bar sits between two items and dragging resizes the item that has the `d`
(dragging up makes the last item taller).

## 4. Defaults: what you need not write

A block can have a size of its own: `ftv` 75 mm wide, `methods` 50 mm wide, `editbox` 42 mm high, `serverstatus` 62 mm
high (the `width` or `height` its `write()` returns, `done(..., width=75)`, rs3util). Where the layout gives that size no number, the block
takes its own, and that edge is **draggable without a `d`**. So `ftv` means what `ftv 75dxh` would, and
`[ftv wdxh, ...]` is just `[ftv, ...]`.

A number in the layout always wins: `ftv 100dxh` is 100 mm. A block with no size of its own (`toptabs`, `code`, `log`,
`doc`) fills and shares what is left with its neighbours.

When an address is made (`load`), every size the blocks' defaults make needless is left out of the string, and the spaces
after `,` and `;` are too. That is why the address above has no sizes.

## 5. The data of a block

A block takes data from a parameter named like its locator: `&toptabs=...` is the data of `toptabs`. A block with no
parameter (ftv, methods, code, editbox) finds what it shows at run time (the file tree, the file of the open tab).

For `toptabs` the data is **files**, as paths from HOME, the parent of the repository that holds rs3 (the Claude folder;
rs3util.pathof is the one place that reads a path, either way, and `start=<path>` names another root, the nearest `.git`
or `.claude` above it). The server's own folder is no root:

| Written | Means |
|---|---|
| `mumix/tools/primary/rs3.py` | one file (the `./` of `./mumix/...` is optional, always understood) |
| `a/{x,y}.py` | shell braces: `a/x.py` and `a/y.py`; they nest: `a/{x,b/{y,z}}.py` |
| `a/*.py`, `a/pane_?.js` | `*` any characters, `?` one, in a file name or a folder name (`mumix/*/b_*.py`) |
| `a/**/*.js` | `**` goes down through any number of folders |
| `a/**` | every file below `a` |
| `a/**/*.{py,md}` | braces and wildcards together: the `.py` and `.md` files |

Wildcards are opened **when the page is built** (each time the address is opened), by name, a folder's files first,
then its folders. Only files the tree would show are matched: not in `.git`, `__pycache__`, `zprev`, an environment or
any folder with a dot (but `.claude`), not a compiled file, and not one that a `.gitignore` or `.ignore` on the way ignores
(its patterns as git reads them, a nested repository by its own); nothing outside the root; at most 500 per block. A
pattern that matches nothing gives nothing. A file added later appears when the page is opened again, not in a page that
is already open. The tree (ftv) is the same walk, stopping at 20000 files and saying so ("max files exceeded").

All of a block's paths go in **one value**, so many files stay short: the common folder once, then braces.

## 6. Writing the address

- Start with `/?layout=`.
- In the layout, a space is written `_` where one is needed (`ftv_100dxh`); there is none after `,` or `;`. A locator has
  no `_` in it (its suffix is `.`).
- Characters kept as they are: `/ [ ] ; , ( ) { } *`. Others are percent-encoded (a space in a *file name* is `%20`).
- `&title=my_page` gives the page a title (`_` is a space there too); `&selftest=1` runs the page's self test.
- A path that has a comma, a brace, `&`, `=`, `#` or `%` in a name, a block whose data is html (`doc`), or an address
  over 6000 characters cannot be written this way: the page is then kept by the server (`/page/KEY.html`, the last 50, as
  specifications in `rs3/pages/`) and a restart builds it again from there.
- `/?reportserver`, or any path that starts with `reportserver` (`/reportserver%20?x`, `/reportserver/y`), with any text after it ignored, is the report server page, the same as
  `/reportserver`.

## 7. From a program

```python
import rs3
rs3.contactRS('load', '[ftv,[toptabs;[methods,[code;editbox]]]]',
              {'toptabs': ['toptabs', './mumix/tools/primary/rs3.py', './mumix/tools/primary/rs3/**']},
              'my title')
```

`blocks` is `{locator: [block, *data]}`; a locator not in it takes the block of its own name. The answer is
`{ok, hash, url, path}`; the page opens in the browser unless `show` is false. The layout may be written with spaces and
sizes (`[ftv wdxh, [toptabs wxh ; ...]]`): the address made from it is the short form above.

## 8. Any html, and a report: the doc block

A report file whose script does not keep the rules below is not shown in a box: the address `/?layout=[doc]&doc=FILE` of
such a file is the file itself, its own page with no rs3 around it (no status bar, no manager). It may still call the
server the way the old reports do.

`[doc]&doc=code.py/results/b_str2int.html` is a report file; `{'doc': ['doc', js, css, html]}` is html given whole. The doc
shows it in a box it cannot get out of (pane_doc.py has the rules): its css is scoped to the box (`body{margin:20px}` is the
box's margin), its script runs with `document` meaning the box (`aDOM`, with `aDOM.currentdiv` the box element) and is
read first (rs3jsguard): no `this`, no arrow function, no `.constructor`, `.parentNode` or `.closest`, no computed names,
no names outside the script's own and a short list. A script that says more is not run; the box lists why. The status bar's
Find searches the text of a doc (every place marked, ▲ ▼ to step, ★ to go back to where it was).
