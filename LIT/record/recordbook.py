r"""recordbook.py  The recording book: the way from each paper to the data of the page, written step by step, one tab a paper.

    python recordbook.py [--no-open]       write comments.html (in this folder) and show it through the report server

What it makes. comments.html is one page for the report server (layout [doc;editbox]): a tab for the summary (the table of all the tube
data that the model uses) and a tab for each paper. A tab is a list of numbered lines (a heading, a paragraph, a figure, a table is one line each).
Click a line: the edit box at the bottom takes your comment for that line and saves it to comments.notes (the report server's rs3microDB:
one json line {code, file, line, text, who, ts} per comment, `file` the tab, `line` the number you clicked). Your notes show under their lines
(click a note to change it, empty it to remove it). A guess of ours is written in RED, with what was guessed and why; every tab lists
its guesses at the top and the summary tab lists them all.

For the author of a tab (recordtabs.py)
    tab = Book.tab(id, title)                 a new tab; id is its short name (the `file` of its comments)
    tab.h(text)                               a step heading
    tab.p(html)                               a paragraph (html: &lt; for <, entities, <b>, <i>, <sub>, <sup>)
    tab.math(latex)                           a display formula, LaTeX (texhtml.py shows it with sub/superscripts, Greek, stacked fractions, square roots)
    tab.eq(text)                              a line of working in plain monospace text
    tab.table(head, rows, caption=None)       head: list of text, rows: lists of html text
    tab.img(image, caption)                   image: a PIL image, or a path of an image file; embedded as jpeg (shrunk to 1000 px wide)
    tab.guess(what, why)                      returns the html of a red guess, to be put into a paragraph; registers it in the tab's list
    pdfcrop(pdf, page, box)                   a PIL image of the part of a page of a pdf of LIT/: box = (x0, y0, x1, y1) as fractions of the page, 0 at top left
Line numbers follow the order the lines are added, from 1: do not insert lines in the middle of a tab that has comments (add at the end,
or add a new tab): a comment is tied to its number. The line the comment was written on is kept in the .notes file with the text, so a
shifted comment can still be read and moved.

The page script is written inside the subset of the report server's script guard (rs3jsguard): no this, no arrow functions, no parentNode.

VERSION  M1 m01.v01 (2026-11-12): first version.
"""
import base64
import html
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import texhtml   # noqa: E402
LIT = os.path.dirname(HERE)
ANALYSIS = os.path.join(LIT, "analysis")
PAGE = os.path.join(HERE, "comments.html")
MAX_PAGE_BYTES = 7_500_000                      # the doc block takes at most 8 MB

__all__ = ["Book", "pdfcrop", "plain", "build", "main"]


def plain(text):
    """The text of the page's tables and notes unchanged: its formulas (between backslash-paren pairs) are set by MathJax, as in the main page."""
    return text


def pdfcrop(pdf, page, box=(0, 0, 1, 1), scale=3.0):
    """A PIL image of the part `box` (fractions of the page, 0 at the top left) of page number `page` (1 is the first) of LIT/<pdf>."""
    import pypdfium2
    doc = pypdfium2.PdfDocument(os.path.join(LIT, pdf))
    image = doc[page - 1].render(scale=scale).to_pil()
    w, h = image.size
    return image.crop((int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h)))


def data_uri(image, width=1000, quality=72):
    """A jpeg data URI of the image (a PIL image or a file), shrunk to `width` pixels when wider."""
    from PIL import Image
    if isinstance(image, str):
        image = Image.open(image if os.path.isabs(image) else os.path.join(ANALYSIS, image))
    image = image.convert("RGB")
    if image.width > width:
        image = image.resize((width, max(1, round(image.height * width / image.width))))
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=quality, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


class Tab:
    """One tab: a list of lines (the html of each) and the guesses made on it."""

    def __init__(me, id, title):
        me.id, me.title = id, title
        me.lines = []                               # (kind, html)
        me.guesses = []                             # (guess id, what, why)

    def add(me, kind, markup):
        me.lines.append((kind, markup))
        return len(me.lines)

    def h(me, text):
        return me.add("h", html.escape(text) if "<" not in text and "&" not in text else text)

    def p(me, markup):
        return me.add("p", markup)

    def eq(me, text):
        """A line of working in monospace (plain text)."""
        return me.add("w", html.escape(text))

    def math(me, latex):
        """A display formula (LaTeX, converted by texhtml): its own line, centred."""
        return me.add("eq", "$$%s$$" % latex)

    def table(me, head, rows, caption=None):
        body = "<div class=\"tablebox\"><table class=\"dt\"><thead><tr>" + "".join("<th>%s</th>" % c for c in head) + "</tr></thead><tbody>"
        body += "".join("<tr>" + "".join("<td>%s</td>" % c for c in row) + "</tr>" for row in rows) + "</tbody></table></div>"
        return me.add("t", ("<div class=\"cap\">%s</div>" % caption if caption else "") + body)

    def img(me, image, caption=""):
        return me.add("i", "<img src=\"%s\" class=\"pic\"/>%s" % (data_uri(image), "<div class=\"cap\">%s</div>" % caption if caption else ""))

    def guess(me, what, why):
        gid = "g-%s-%d" % (me.id, len(me.guesses) + 1)
        me.guesses.append((gid, what, why))
        return "<span class=\"guess\" id=\"%s\">[GUESS: %s &mdash; because %s]</span>" % (gid, what, why)

    def html(me, with_summary=False, all_tabs=None):
        out = ["<div class=\"rpanel\" id=\"p-%s\" hidden>" % me.id]
        if me.guesses:
            out.append("<div class=\"gindex\"><b>Guesses in this tab (%d)</b>: %s</div>" % (len(me.guesses), " ".join(
                "<a class=\"glink\" onclick=\"jump('%s')\">%d</a>" % (gid, k) for k, (gid, what, why) in enumerate(me.guesses, 1))))
        for number, (kind, markup) in enumerate(me.lines, 1):
            out.append("<div class=\"ln k-%s\" id=\"L-%s-%d\" data-file=\"%s\" data-line=\"%d\" onclick=\"pick(this)\"><span class=\"no\">%d</span><div class=\"body\">%s</div></div>"
                       "<div class=\"nt\" id=\"nt-%s-%d\"></div>" % (kind, me.id, number, me.id, number, number, markup, me.id, number))
        out.append("</div>")
        return "\n".join(out)


class BookClass:
    def __init__(me):
        me.tabs = []
        me.summary_intro = ""
        me.summary_table = ""

    def tab(me, id, title):
        t = Tab(id, title)
        me.tabs.append(t)
        return t


Book = BookClass()

MATHJAX = ("<script>window.MathJax = { tex: { inlineMath: [['\\(', '\\)']], displayMath: [['$$', '$$']] }, svg: { fontCache: 'global' } };</script>"
           "<script src=\"https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.2/es5/tex-svg.js\"></script>")      # the main page's way

CSS = """
.rbar{display:flex;flex-wrap:wrap;gap:4px;padding:6px 8px;border-bottom:1px solid #ccc}
.rtab{border:1px solid #bbb;border-radius:4px;padding:2px 9px;cursor:pointer;font:12px Verdana,Arial,sans-serif;background:#f4f1ec}
.rtab.on{background:#e8650f;color:#fff;border-color:#c25400}
.rtab.hasnotes{border-color:#06c;border-width:2px}
.rpanel{padding:6px 10px 40px 10px;font:13px Verdana,Arial,sans-serif;max-width:1100px}
.ln{display:flex;gap:8px;padding:3px 4px;cursor:pointer;border-radius:3px}
.ln:hover{background:#fdeedd}
.ln.sel{outline:2px solid #e8650f}
.ln .no{flex:0 0 34px;text-align:right;color:#999;font-size:10px;padding-top:3px;user-select:none}
.ln .body{flex:1;min-width:0}
.k-h .body{font-weight:bold;font-size:15px;margin-top:10px;border-bottom:1px solid #ddd}
.k-w .body{font-family:Consolas,monospace;font-size:12px;white-space:pre-wrap}
.k-eq .body{text-align:center;padding:4px 0;overflow-x:auto}
.k-p .body{line-height:1.45}
.pic{max-width:100%;border:1px solid #ccc}
.cap{font-size:11px;color:#555;padding:2px 0}
.guess{color:#c00;font-weight:bold}
.gindex{padding:4px 6px;margin-bottom:6px;color:#c00;font-size:12px}
.glink{display:inline-block;min-width:16px;text-align:center;border:1px solid #c00;color:#c00;border-radius:3px;margin:0 2px;cursor:pointer}
.tablebox{overflow-x:auto;max-width:100%}
table.dt{border-collapse:collapse;font-size:11px}
table.dt th,table.dt td{border:1px solid #ccc;padding:2px 5px;text-align:left;vertical-align:top}
table.dt th{background:#eee}
.nt{margin-left:48px}
.note{border-left:3px solid #06c;margin:2px 0 4px 0;padding:2px 8px;font-size:12px;color:#134;cursor:pointer;white-space:pre-wrap;background:#eef5ff}
.note .who{color:#06c;font-weight:bold;margin-right:6px}
"""

SCRIPT = """
var GRAB = '';
function showTab(id){
  var buttons = document.querySelectorAll('.rtab'), panels = document.querySelectorAll('.rpanel'), i;
  for (i = 0; i < buttons.length; i++){
    if (buttons[i].getAttribute('data-go') === id) buttons[i].classList.add('on'); else buttons[i].classList.remove('on');
  }
  for (i = 0; i < panels.length; i++) panels[i].hidden = panels[i].id !== 'p-' + id;
  try { localStorage.setItem('tab', id); } catch (e) {}
  reload();
}
function pick(el){
  var old = document.querySelectorAll('.ln.sel'), i;
  for (i = 0; i < old.length; i++) old[i].classList.remove('sel');
  el.classList.add('sel');
  document.noteline(el.getAttribute('data-file'), el.getAttribute('data-line'));
}
function jump(id){
  var el = document.getElementById(id);
  if (el) el.scrollIntoView({block: 'center'});
}
function jumptab(tab, id){ showTab(tab); jump(id); }
function addNote(box, n){
  var div = document.createElement('div'), who = document.createElement('span'), text = document.createElement('span');
  div.className = 'note'; who.className = 'who';
  who.textContent = (n.who || 'user') + ' ' + String(n.ts || '').slice(5, 16).replace('T', ' ');
  text.textContent = n.text;
  div.appendChild(who); div.appendChild(text);
  div.addEventListener('click', function(e){ e.stopPropagation(); document.noteselect(n); });
  box.appendChild(div);
}
function showNotes(list){
  var boxes = document.querySelectorAll('.nt'), buttons = document.querySelectorAll('.rtab'), i, k, box, count = {};
  for (i = 0; i < boxes.length; i++) boxes[i].textContent = '';
  for (k = 0; k < list.length; k++){
    box = document.getElementById('nt-' + list[k].file + '-' + list[k].line);
    if (box) addNote(box, list[k]);
    var f = list[k].file;
    count[f] = (count[f] || 0) + 1;
  }
  for (i = 0; i < buttons.length; i++){
    var key = buttons[i].getAttribute('data-go');
    if (count[key]) buttons[i].classList.add('hasnotes'); else buttons[i].classList.remove('hasnotes');
  }
}
function reload(){ document.notes(undefined, function(list, err){ if (!err) showNotes(list); }); }
document.addEventListener('DOMContentLoaded', function(){
  var first = 'summary', saved = null;
  try { saved = localStorage.getItem('tab'); } catch (e) {}
  if (saved && document.getElementById('p-' + saved)) first = saved;
  showTab(first);
  reload();
  if (document.typeset) document.typeset();         // the formulas (the report server loads MathJax for the box)
});
document.onnotesaved(reload);
"""


def summary_table():
    """The table of all the tube data of the model (the 'data' table of the page), as plain text headers."""
    sys.path.insert(0, ANALYSIS)
    import build_data_sections as bds
    table = bds.model_input_table()
    return plain(table)


def build(book=None):
    """The html of the book (a string)."""
    book = book or Book
    import recordtabs
    recordtabs.fill(book)
    buttons = "".join("<span class=\"rtab\" data-go=\"%s\" onclick=\"showTab('%s')\">%s</span>" % (t.id, t.id, t.title) for t in book.tabs)
    panels = "\n".join(t.html() for t in book.tabs)
    page = ("<!doctype html><html><head><meta charset=\"utf-8\"><title>Recording book: from paper to data</title>%s<style>%s</style></head><body>"
            "<div class=\"rbar\">%s</div>\n%s\n<script>%s</script></body></html>" % (MATHJAX, CSS, buttons, panels, SCRIPT))
    size = len(page.encode("utf-8"))
    if size > MAX_PAGE_BYTES:
        raise ValueError("the book is %d bytes: the doc block takes at most 8 MB" % size)
    return page


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    text = build()
    with open(PAGE, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("wrote %s (%.2f MB, %d tabs)" % (PAGE, len(text.encode("utf-8")) / 1e6, len(Book.tabs)))
    if "--no-open" not in argv:
        sys.path.insert(0, os.path.join(os.path.dirname(LIT), "tools"))
        import reportserver
        reply = reportserver.contactRS("load", "[doc;editbox]", {"doc": ["doc", "./mumix/LIT/record/comments.html"]}, "Recording book")
        print("shown:", reply.get("url"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
