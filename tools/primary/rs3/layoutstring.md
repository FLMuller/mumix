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

A group uses one separator kind: `,` or `;`, never both. A name that is not a group is a **block**:
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

A locator is a block name; digits at the end tell two of a kind apart: `code`, `code2`. The block is the name
without the digits (`code2` is a `code` block). A locator that is not a block's name says which with
`&block.NAME=block`, e.g. `&block.edit=editbox`.

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
(draggable). One value alone is the width: `50` is `50xh`. A dot may stand for the `x`: `w50d.h`.

**Along or across.** In a **row** the width is the size along the row (the *main* size) and the height is the size
across it; in a **column** the height is the main size. The main size does the work: a number is fixed, `w`/`h` shares
what is left. The across size fills unless it is a number. The `d` of either value makes the **main** edge draggable.

**The bar.** A draggable edge has a 1 mm bar. It goes *after* the item, and *before* the item when that is the last
of its group (`editbox` under the code), so the bar sits between two items and dragging resizes the item that has the `d`
(dragging up makes the last item taller).

## 4. Defaults: what you need not write

A block can have a size of its own: `ftv` 75 mm wide, `methods` 50 mm wide, `editbox` 42 mm high, `serverstatus` 62 mm
high (`WIDTH` or `HEIGHT` at the top of `panes/pane_NAME.py`). Where the layout gives that size no number, the block
takes its own, and that edge is **draggable without a `d`**. So `ftv` means what `ftv 75dxh` would, and
`[ftv wdxh, ...]` is just `[ftv, ...]`.

A number in the layout always wins: `ftv 100dxh` is 100 mm. A block with no size of its own (`toptabs`, `code`, `log`,
`doc`) fills and shares what is left with its neighbours.

When an address is made (`load`), every size the blocks' defaults make needless is left out of the string, and the spaces
after `,` and `;` are too. That is why the address above has no sizes.

## 5. The data of a block

A block takes data from a parameter named like its locator: `&toptabs=...` is the data of `toptabs`. A block with no
parameter (ftv, methods, code, editbox) finds what it shows at run time (the file tree, the file of the open tab).

For `toptabs` the data is **files**, as paths from the root of the server (the folder the tree starts at):

| Written | Means |
|---|---|
| `mumix/tools/primary/rs3.py` | one file (the `./` of `./mumix/...` is optional, always understood) |
| `a/{x,y}.py` | shell braces: `a/x.py` and `a/y.py`; they nest: `a/{x,b/{y,z}}.py` |
| `a/*.py`, `a/pane_?.js` | `*` any characters, `?` one, in a file name or a folder name (`mumix/*/b_*.py`) |
| `a/**/*.js` | `**` goes down through any number of folders |
| `a/**` | every file below `a` |
| `a/**/*.{py,md}` | braces and wildcards together: the `.py` and `.md` files |

Wildcards are opened **when the page is built** (each time the address is opened), by name, a folder's files first,
then its folders. Only files the tree would show are matched: not `.git`, `__pycache__`, an environment or a compiled
file; nothing outside the root; at most 500 per block. A pattern that matches nothing gives nothing. A file added later
appears when the page is opened again, not in a page that is already open.

All of a block's paths go in **one value**, so many files stay short: the common folder once, then braces.

## 6. Writing the address

- Start with `/?layout=`.
- In the layout, a space is written `_` where one is needed (`ftv_100dxh`); there is none after `,` or `;`.
- Characters kept as they are: `/ [ ] ; , ( ) { } *`. Others are percent-encoded (a space in a *file name* is `%20`).
- `&title=my_page` gives the page a title (`_` is a space there too); `&selftest=1` runs the page's self test.
- A path that has a comma, a brace, `&`, `=`, `#` or `%` in a name, a block whose data is html (`doc`), or an address
  over 6000 characters cannot be written this way: the page is then kept by the server (`/page/KEY.html`, the last 50, as
  specifications in `rs3/pages/`) and a restart builds it again from there.
- `/?reportserver` (any text after it is ignored) is the report server page, the same as
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
