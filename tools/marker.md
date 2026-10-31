# marker.md -- the markup

Markdown in, HTML out: `md2htm(md)` (marked.py). Written with `mdwrite`, `mdwriteln`, `mdappend`
(mdwriter.py); HTML is written with `htmwrite`, `htmwriteln`, `htmappend` and put in a template with
`htmtemplate` (htmlwriter.py). `md` and `htm` are bytes (a bytearray).

## Writing

| Call | Does |
|:--|:--|
| `mdwrite(md, *args)` | args joined by a space; no line end |
| `mdwriteln(md, *args)` | args joined by a space; a new line |
| `mdappend(md, *args)` | args joined by nothing; no line end |
| `md2str(md, 'utf8' or 'ascii')` | the text; ascii spells accents, Greek letters (` mu `), named characters; `_` for the rest |

- `md` is `None`, an int, or the bytearray of an earlier call. Every call returns it.
- Args are columns: a list is one row per item, a single value repeats on every row. Lists of
  different lengths raise `ValueError`. An empty list writes nothing.
- Numbers are written as mformat does (4 significant figures; 143.50k, 1.20M, 1.34e-3).
- A `|` in text that goes in a table cell: write `\|`.

```python
mdwriteln(md, '| name | r |')
mdwriteln(md, '|:--|--:|')
mdwriteln(md, '|', names, '|', values, '|')       # one row per name
```

## Markdown

| Write | Get |
|:--|:--|
| `# Title` to `######` | headings; or underline with `=====` / `-----` |
| blank line | ends a paragraph |
| `---` `***` `___` | rule |
| `> text` | quote |
| `- a` `* a` `+ a`, `1. a` `1) a` | lists; 2 spaces nest; blank line between items: loose |
| `- [x] a` `- [ ] a` | task list |
| ` ``` ` or `~~~` fence, or 4 spaces | code block |
| `[name]: url "title"` | link definition |
| `*em*` `_em_`, `**strong**`, `~~gone~~`, `` `code` `` | inline |
| `[text](url "title")`, `[text][name]`, `![alt](src)`, `<url>`, bare `http://` `www.` | links, images |
| two spaces or `\` at the line end | line break |
| `\*` | the character itself |

Raw HTML is shown as text. `javascript:` links are dropped. No footnotes, math or HTML blocks.

### Tables

```
| a | b |
|:--|--:|
| x | 1 |
```

`:--` left, `:-:` centre, `--:` right. A table is `<table class="grid">`: the page gives every
column that has more than one value a star (sort) and a hamburger (filter).
A row whose first cell starts `{.name}` gets that class on its `<tr>`: `| {.bad}x | 1 |`.

## Markers

A marker is a line of its own, nothing else on it. Names may not contain `_\` or `/_`.

| Marker | Does |
|:--|:--|
| `_\section:name/_` | closes every open div and starts a section. Sections do not nest. |
| `_\name/_` | opens a `<div class="mk">` |
| `_\type:name/_` | opens a div of that type: `<div class="mk mk-type">` (`tab`, `flex`, any word) |
| `_\type:name {a b}/_` | the same with the classes `a` and `b` |
| `_\next:name/_` | closes the innermost div and opens another of its type |
| `_\|/_` | closes the innermost div |

- Every div gets `id="mk<call>.<n>"` (unique on a page) and `data-name="name"`.
- What is open at the end of the Markdown is closed.
- Text before the first section marker is the section `_\main/_`. The HTML always starts with
  `<!--SECTION name-->`.
- A colon in a name needs a type: `_\tab:Run: 3/_`.
- A `flex` div: each line that starts `|` is an item (`<div class="mk-item">`); lines under it
  belong to it until the next `|` line, a blank line or a marker. `_\|/_` ends the flex. A flex
  with no name gets no useful `data-name`. Class `cards` makes big figures.

```
_\flex:machine/_
| power AC
| clock 4.4 GHz
_\|/_
```

## Templates

`htmtemplate(filename, htm, **keys) -> bytearray`

- The template has places `{{name}}`. A section fills `{{section}}` (the default one: `{{_\main/_}}`).
  A key fills `{{KEY}}`; the keys `css` and `js` are the names of files whose text is put in.
- A place with nothing to fill it raises `KeyError`; a section or key no place uses raises `ValueError`.
- A value that holds `{{x}}` leaves it in the page, for the next program to fill.
- `htmsave(htm, filename)` writes a new file; `FileExistsError` if it exists.

## Page conventions (runbench.html, bench.html)

- A tab is a div with class `mk-tab` and `data-name`. Inside a tab, divs of class `mk-tab` are
  its sub-tabs. The page script makes the buttons. Class `bad` on a tab makes it red.
- A link `[name](#tab_name)` opens that tab.
- Bench pages hold no css or js: they are in runbench.css and runbench.js.

## The code tab (codemark.py)

`codemark(path) -> (functions, code)`: HTML for a .py or .pyx file.

- A comment is a run of full-line `#` lines, or (Python) a stand-alone string over 5 lines. Its
  text is Markdown. `[xx] text` is the user xx's (orange circle in the margin); the rest is
  Claude's (blue).
- A click on a line's margin writes a comment on it; on a comment's margin, changes it. Every
  edit is saved by the report server: only comments may differ in the file afterwards.
- Function list: green `test_` and `bench_`; red under 5 lines or called from one place or none.
