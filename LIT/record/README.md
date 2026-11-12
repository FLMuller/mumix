# The recording book (LIT/record)

From each paper to the numbers of the data table of the page, one tab a paper, with screenshots of the paper's pages, the working step by step, and our guesses in red.

## Use

    python recordbook.py            (in this folder) make tabs/*.html and open the page in the report server
    python recordbook.py --no-open  make the files only

The page is `[toptabs;editbox]`: the tab strip stays at the top, the box at the bottom takes your comments.
Click a line (or the picture on it: that also opens the picture at full size in a browser tab of its own) and write the comment in the box; it saves itself.
Click a blue note under a line to change it; empty it and save to remove it.

## Files

| file | what |
|---|---|
| `recordbook.py` | the engine: tabs, lines, the page script, the html of each tab, `main` (writes `tabs/*.html`, loads the page) |
| `recordtabs.py` | the summary tab (the data table), the generic tab of every source (its rows, the conversion chain, a worked example), the list of all guesses |
| `pdftabs.py` | the four pdf sources (Tanahashi 2001 and 2004, Das 2006, Pirozzoli 2012): the figure, the digitising, the fits (made again at every build: `summary_pdfs.main`), grid and detection |
| `srctabs.py` | the page cut-outs (table or figure) of the other sources, found by their captions in the pdfs of `LIT/` |
| `texhtml.py` | a LaTeX-to-html converter written first and not used: the doc block now sets the formulas with MathJax (`document.typeset()`) |
| `tabs/NAME.html` | one tab (made by `recordbook.py`) |
| `tabs/NAME.notes` | the comments of that tab: jsonl, one record `{code, file, line, text, who, ts}` a line, appended by the report server (`rs3microDB`) |
| `comments.html`, `comments.notes` | the index of the tabs; the notes file is a test note of the build and can be deleted |

## Rules of the book

- A line is numbered in the order it was added: add to the end of a tab, do not insert, or the comments lose their line. The comment keeps its text, so a shifted one can be moved.
- A guess is made with `tab.guess(what, why)`: red in the line, in the list at the top of the tab, and in the list at the end of the summary tab.
- Equations: `tab.math(latex)`; inline `\( ... \)` in any text.
- Pictures: `tab.img(PIL image or file, caption)`; shown at half width, shrunk to 1300 px; a click opens the full picture in a tab.
- A tab is at most 8 MB (the doc block's limit, `MAX_PAGE` in `pane_doc.py`); the largest is 0.7 MB.

## The report server side (tools/)

`rs_primary/rs3microDB.py` (verbs `note_add`, `note_list`): the notes file of a page is the page's html file with `.notes` in place of `.html`; the message names the html file (`source`), and the server only accepts one the page was made from.
`pane_editbox` (type note: `noteline`, `noteselect` in, `notesaved` out) and `pane_doc` (`document.noteline`, `document.noteselect`, `document.notes`, `document.onnotesaved`, `document.typeset`, `document.opentab`, and `data-source` on the box) carry it; the code-comment path of the edit box is unchanged.
