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
    tab.img(image, caption)                   image: a PIL image, or a path of an image file; embedded as jpeg (shrunk to 1300 px wide; shown at half the width of the page, a click opens it full size in a tab)
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
PAGE = os.path.join(HERE, "comments.html")      # (the book is now one file for each tab, in tabs/)
MAX_PAGE_BYTES = 7_500_000                      # the doc block takes at most 8 MB

__all__ = ["Book", "pdfcrop", "plain", "paper_line", "doi_of", "build", "main"]


def plain(text):
    """The text of the page's tables and notes unchanged: its formulas (between backslash-paren pairs) are set by MathJax, as in the main page."""
    return text


def doi_of(pdf):
    """The first doi found on page 1 (else page 2) of LIT/<pdf>, or None."""
    import pypdfium2
    doc = pypdfium2.PdfDocument(os.path.join(LIT, pdf))
    for number in range(min(2, len(doc))):
        found = re.search(r"10\.\d{4,9}/[^\s,;\"<>)\]\u27e9]+", doc[number].get_textpage().get_text_range())
        if found:
            return found.group(0).rstrip(".")
    return None


def paper_line(tab, pdfs, labels=None):
    """A line of the tab that leads to the papers: for each pdf of LIT/ the reference as a link that asks the server to open the pdf (and, if the file is not there, the doi), and the doi
    as a link of its own. labels: the reference text of each pdf (default: the file name without .pdf)."""
    parts = []
    for number, pdf in enumerate(pdfs):
        label = (labels[number] if labels and number < len(labels) else None) or pdf[:-4]
        doi = doi_of(pdf)
        parts.append("<a class=\"plink\" onclick=\"openpaper('%s', '%s')\" title=\"opens the pdf (./mumix/LIT/%s) through the server; the doi if the pdf is not found\">%s</a>%s" % (
            "./mumix/LIT/" + pdf, doi or "", html.escape(pdf, quote=True), label,
            " (<a href=\"https://doi.org/%s\" target=\"_blank\">doi:%s</a>)" % (doi, doi) if doi else " (no doi found on the first pages of the pdf)"))
    return tab.p("The paper: " + "<br>".join(parts))


def pdfcrop(pdf, page, box=(0, 0, 1, 1), scale=3.0):
    """A PIL image of the part `box` (fractions of the page, 0 at the top left) of page number `page` (1 is the first) of LIT/<pdf>."""
    import pypdfium2
    doc = pypdfium2.PdfDocument(os.path.join(LIT, pdf))
    image = doc[page - 1].render(scale=scale).to_pil()
    w, h = image.size
    return image.crop((int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h)))


def data_uri(image, width=1300, quality=70):
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
        out = ["<div class=\"rpanel\" id=\"p-%s\"><div id=\"nterr\" class=\"nterr\"></div>" % me.id]
        if me.guesses:
            out.append("<div class=\"gindex\"><b>Guesses in this tab (%d)</b>: %s</div>" % (len(me.guesses), " ".join(
                "<a class=\"glink\" onclick=\"jump('%s')\">%d</a>" % (gid, k) for k, (gid, what, why) in enumerate(me.guesses, 1))))
        for number, (kind, markup) in enumerate(me.lines, 1):
            out.append("<div class=\"ln k-%s\" id=\"L-%s-%d\" data-file=\"%s\" data-line=\"%d\" onclick=\"pick(this, event)\"><span class=\"no\">%d</span><div class=\"body\">%s</div></div>"
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
.pic{max-width:50%;border:1px solid #ccc;cursor:zoom-in}
.cap{font-size:11px;color:#555;padding:2px 0}
.guess{color:#c00;font-weight:bold}
.gindex{padding:4px 6px;margin-bottom:6px;color:#c00;font-size:12px}
.glink{display:inline-block;min-width:16px;text-align:center;border:1px solid #c00;color:#c00;border-radius:3px;margin:0 2px;cursor:pointer}
.tablebox{overflow-x:auto;max-width:100%}
table.dt{border-collapse:collapse;font-size:11px}
table.dt th,table.dt td{border:1px solid #ccc;padding:2px 5px;text-align:left;vertical-align:top}
table.dt th{background:#eee}
.nt{margin-left:48px}
.nterr{color:#c00;font-size:12px}
.path{font-family:Consolas,monospace;font-size:11px;color:#555}
.plink{color:#06c;cursor:pointer;text-decoration:underline}
.note{border-left:3px solid #06c;margin:2px 0 4px 0;padding:2px 8px;font-size:12px;color:#134;cursor:pointer;white-space:pre-wrap;background:#eef5ff}
.note .who{color:#06c;font-weight:bold;margin-right:6px}
"""

SCRIPT = """
function pick(el, e){
  if (e && e.target && e.target.tagName === 'IMG' && document.opentab){ document.opentab(e.target.getAttribute('src')); }      // a click on a picture: it opens at full size in a tab of its own
  var old = document.querySelectorAll('.ln.sel'), i;
  for (i = 0; i < old.length; i++) old[i].classList.remove('sel');
  el.classList.add('sel');
  document.noteline(el.getAttribute('data-file'), el.getAttribute('data-line'));
}
function openpaper(path, doi){
  if (!document.openfile){ return; }
  document.openfile(path, doi).then(function(why){ var box = document.getElementById('nterr'); if (box) box.textContent = why ? 'the pdf was not opened: ' + why : ''; });
}
function jump(id){
  var el = document.getElementById(id);
  if (el) el.scrollIntoView({block: 'center'});
}
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
  var boxes = document.querySelectorAll('.nt'), i, k, box;
  for (i = 0; i < boxes.length; i++) boxes[i].textContent = '';
  for (k = 0; k < list.length; k++){
    box = document.getElementById('nt-' + list[k].file + '-' + list[k].line);
    if (box) addNote(box, list[k]);
  }
}
function reload(){
  document.notes(TAB, function(list, err){
    var box = document.getElementById('nterr');
    if (err){ if (box){ box.textContent = 'the notes of this tab could not be read: ' + err; } return; }
    if (box) box.textContent = '';
    showNotes(list);
  });
}
document.addEventListener('DOMContentLoaded', function(){
  reload();
  if (document.typeset) document.typeset();         // the formulas (the report server loads MathJax for the box)
});
document.onnotesaved(reload);
"""

TABS_DIR = os.path.join(HERE, "tabs")


def tab_file(tab):
    """The html of one tab as a file of its own (a section of the page's toptabs): its css, the lines, its script."""
    return ("<!doctype html><html><head><meta charset=\"utf-8\"><title>%s</title>%s<style>%s</style></head><body>\n%s\n<script>var TAB = '%s';\n%s</script></body></html>" % (
        tab.title, MATHJAX, CSS, tab.html(), tab.id, SCRIPT))


def build(book=None):
    """Make every tab's file in tabs/ and return [(title, ./ path)] in the order of the tabs."""
    book = book or Book
    import recordtabs
    recordtabs.fill(book)
    os.makedirs(TABS_DIR, exist_ok=True)
    out = []
    for tab in book.tabs:
        text = tab_file(tab)
        size = len(text.encode("utf-8"))
        if size > MAX_PAGE_BYTES:
            raise ValueError("the tab %s is %d bytes: the doc block takes at most 8 MB" % (tab.id, size))
        path = os.path.join(TABS_DIR, tab.id + ".html")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        out.append((tab.title, "./mumix/LIT/record/tabs/%s.html" % tab.id, size))
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    made = build()
    index = "<!doctype html><html><head><meta charset=\"utf-8\"><title>Recording book</title></head><body><h3>The recording book</h3><p>The book is one html file for each tab, in the folder tabs/, shown as the sections of a toptabs page by the report server. Run <code>python recordbook.py</code> (in this folder) to make the files and open the page. The comments of each tab are in tabs/NAME.notes.</p><ul>%s</ul></body></html>" % "".join("<li>%s: %s</li>" % (m[0], m[1]) for m in made)
    with open(PAGE, "w", encoding="utf-8", newline=chr(10)) as f:
        f.write(index)
    print("wrote %d tab files in %s (%.2f MB in all; the largest %.2f MB)" % (len(made), TABS_DIR, sum(m[2] for m in made) / 1e6, max(m[2] for m in made) / 1e6))
    if "--no-open" not in argv:
        sys.path.insert(0, os.path.join(os.path.dirname(LIT), "tools"))
        import reportserver
        items = ["toptabs"] + [[title, path] for title, path, size in made]
        reply = reportserver.contactRS("load", "[toptabs;editbox]", {"toptabs": items}, "Recording book", timeout=30.0)
        print("shown:", reply.get("url"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
