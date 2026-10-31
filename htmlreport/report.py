"""
report -- a self-contained HTML report: tables, inline SVG charts, a link to the workbook.

Why
    The workbook holds every number and the charts Excel will draw; the report is the page
    to read first. It carries a sample of the results table, the parameters, the charts
    (drawn by svgchart from the very chart definitions that went into the workbook) and a
    link to the workbook for the rest. One HTML file, no scripts, no external files except
    the link and the standalone SVG of each chart.

Algorithm
    Nothing clever: the pieces are built as text. Tables are made from lists (a header row
    with units, then rows); numbers are written with a fixed number of significant figures;
    all text is escaped; charts are rendered once to SVG and embedded inline (the same text
    is also written as a file, for pasting into a document). The page is well-formed XML
    as well as HTML, which the tests rely on to check it with a standard parser.

Use
    import report
    body = report.table_html(headers, units, rows, caption='Results')
    sections = [('Run', report.facts_html([('final conversion', 0.999, '-')])),
                ('Results', body)]
    charts = report.book_charts(book)                    # [(sheet, key, title, svg), ...]
    sections.insert(1, ('Charts', report.charts_section(charts, 'mumix')))
    text = report.page('Title', sections, subtitle='...', workbook='mumix.xlsx')
    report.write_charts(folder, 'mumix', charts)         # mumix_<key>.svg beside the page
    report.write_page(folder, 'mumix.html', text)

    sig(value, digits=4)             number as text
    sample_rows(rows, count)         rows spread evenly, first and last kept
    table_html(headers, units, rows, caption=None, row_classes=None)
    facts_html(facts)                a list of (label, value, unit) as a small table
    list_html(items)                 bullet list of text items

Versions
    M01  m01.v01  2026-10-31  first version.
"""

import html
import os
from urllib.parse import quote

from svgchart import chart_svg, inline_svg
from xlw import book_values

__all__ = ['sig', 'sample_rows', 'table_html', 'facts_html', 'list_html', 'book_charts',
           'charts_section', 'page', 'write_charts', 'write_page', 'plain_title']

STYLE = """
:root { color-scheme: light dark; --ink: #1d2733; --muted: #5b6770; --rule: #d5dbe0;
        --page: #ffffff; --band: #f3f5f7; --accent: #1f5fa8; --flag: #fff4d6; }
@media (prefers-color-scheme: dark) {
  :root { --ink: #e6e9ec; --muted: #9aa5ae; --rule: #3a444d; --page: #14181c;
          --band: #1c2228; --accent: #7fb3ee; --flag: #3b3317; }
}
body { margin: 0; background: var(--page); color: var(--ink);
       font: 15px/1.5 "Segoe UI", Calibri, Arial, sans-serif; }
main { max-width: 1120px; margin: 0 auto; padding: 24px 16px 48px; }
h1 { font-size: 1.7rem; margin: 0 0 4px; }
h2 { font-size: 1.15rem; margin: 32px 0 8px; padding-bottom: 4px;
     border-bottom: 1px solid var(--rule); }
p.sub { color: var(--muted); margin: 0 0 8px; }
a { color: var(--accent); }
.charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
          gap: 16px; }
figure { margin: 0; background: #ffffff; border: 1px solid var(--rule); border-radius: 6px;
         padding: 8px; color: #1d2733; }
figure svg { display: block; }
figcaption { font-size: 0.85rem; padding: 4px 4px 0; }
figcaption a { color: #1f5fa8; }
.scroll { overflow-x: auto; }
table { border-collapse: collapse; font-variant-numeric: tabular-nums; font-size: 0.9rem; }
caption { text-align: left; color: var(--muted); padding: 0 0 6px; }
th, td { padding: 3px 10px; border-bottom: 1px solid var(--rule); }
th { background: var(--band); text-align: right; vertical-align: bottom; }
td.num { text-align: right; }
td.txt, th.txt { text-align: left; }
span.unit { color: var(--muted); font-weight: normal; font-size: 0.8rem; }
tr.flag td { background: var(--flag); }
table.facts th { text-align: left; background: none; font-weight: normal; }
ul { margin: 4px 0; padding-left: 22px; }
footer { color: var(--muted); font-size: 0.8rem; margin-top: 40px; }
@media print { main { max-width: none; } .charts { display: block; }
               figure { break-inside: avoid; margin-bottom: 12px; } }
"""


# ---------------------------------------------------------------------- small pieces -----
def esc(text):
    """Text safe to put inside HTML."""
    return html.escape(str(text), quote=True)


def sig(value, digits=4):
    """A number as text with `digits` significant figures; whole numbers as integers;
    None as an empty string; text unchanged."""
    if value is None:
        return ''
    if isinstance(value, (bool, str)):
        return str(value)
    if float(value).is_integer() and abs(value) < 1e9:
        return str(int(value))
    return '%.*g' % (digits, value)


def sample_rows(rows, count):
    """`count` rows spread evenly over the table, the first and the last always kept. A
    table with `count` rows or fewer is returned whole."""
    total = len(rows)
    if total <= count or count < 2:
        return list(rows)
    return [rows[round(i * (total - 1) / (count - 1))] for i in range(count)]


def plain_title(chart):
    """The title of a chart node as plain text ('' when it has none); title runs are
    joined."""
    title = chart.kvr('title')
    text = None if title is None else title.kvr('text')
    if text is None:
        return ''
    if isinstance(text, str):
        return text
    return ''.join(item if isinstance(item, str) else item[0] for item in text)


# ------------------------------------------------------------------------- tables --------
def table_html(headers, units, rows, caption=None, row_classes=None):
    """A table. `headers` and `units` are lists (units may be None); a cell that is text is
    left-aligned, a number is right-aligned with 4 significant figures. `row_classes` is
    an optional list with one CSS class (or None) per row."""
    columns = len(headers)
    kinds = []
    for j in range(columns):
        text_column = any(isinstance(row[j], str) for row in rows) if rows else False
        kinds.append('txt' if text_column else 'num')
    out = ['<div class="scroll"><table>']
    if caption:
        out.append(f'<caption>{esc(caption)}</caption>')
    out.append('<thead><tr>')
    for j in range(columns):
        unit = '' if units is None or not units[j] else \
            f'<br/><span class="unit">{esc(units[j])}</span>'
        out.append(f'<th class="{kinds[j]}">{esc(headers[j])}{unit}</th>')
    out.append('</tr></thead><tbody>')
    for i, row in enumerate(rows):
        mark = '' if row_classes is None or row_classes[i] is None else \
            f' class="{esc(row_classes[i])}"'
        cells = ''.join(f'<td class="{kinds[j]}">{esc(sig(row[j]))}</td>'
                        for j in range(columns))
        out.append(f'<tr{mark}>{cells}</tr>')
    out.append('</tbody></table></div>')
    return ''.join(out)


def facts_html(facts):
    """A small two-column table from (label, value, unit) triples."""
    out = ['<div class="scroll"><table class="facts"><tbody>']
    for label, value, unit in facts:
        tail = f' <span class="unit">{esc(unit)}</span>' if unit else ''
        out.append(f'<tr><th>{esc(label)}</th><td class="num">{esc(sig(value))}{tail}</td>'
                   '</tr>')
    out.append('</tbody></table></div>')
    return ''.join(out)


def list_html(items):
    """A bullet list of text items."""
    return '<ul>' + ''.join(f'<li>{esc(item)}</li>' for item in items) + '</ul>'


# ------------------------------------------------------------------------- charts --------
def book_charts(book, width=640, height=400):
    """[(sheet name, chart key, title, svg text)] for every chart of a book, drawn with
    svgchart from the chart nodes. The svg is the standalone document; inline_svg() makes
    it embeddable."""
    values = book_values(book)
    bpriv = book.kvr('priv')
    found = []
    for name, key in zip(bpriv.kvr('sheets'), bpriv.kvr('sheetkeys')):
        charts = book.kvr(key).kvr('priv').kvr('charts')
        if charts is None:
            continue
        for chart_key, chart in zip(charts.names(), charts.nodes()):
            found.append((name, chart_key, plain_title(chart),
                          chart_svg(chart, values, width, height)))
    return found


def charts_section(charts, stem):
    """The charts as figures in a grid, each linking to its standalone file stem_key.svg."""
    out = ['<div class="charts">']
    for sheet, key, title, svg in charts:
        link = quote(f'{stem}_{key}.svg')
        out.append(f'<figure>{inline_svg(svg)}<figcaption>{esc(title or key)} '
                   f'(sheet {esc(sheet)}) <a href="{link}">svg</a></figcaption></figure>')
    out.append('</div>')
    return ''.join(out)


# --------------------------------------------------------------------------- page --------
def page(title, sections, subtitle=None, workbook=None, generated=None):
    """The whole HTML page. `sections` is a list of (heading, html) pairs; `workbook` is
    the file name of the workbook beside the page (linked at the top); `generated` is an
    optional date text for the footer."""
    out = ['<!DOCTYPE html>', '<html lang="en"><head><meta charset="utf-8"/>',
           '<meta name="viewport" content="width=device-width, initial-scale=1"/>',
           f'<title>{esc(title)}</title><style>{STYLE}</style></head><body><main>',
           f'<h1>{esc(title)}</h1>']
    if subtitle:
        out.append(f'<p class="sub">{esc(subtitle)}</p>')
    if workbook:
        out.append(f'<p class="sub">All numbers and the Excel charts: '
                   f'<a href="{quote(workbook)}">{esc(workbook)}</a></p>')
    for heading, body in sections:
        out.append(f'<section><h2>{esc(heading)}</h2>{body}</section>')
    if generated:
        out.append(f'<footer>generated {esc(generated)}</footer>')
    out.append('</main></body></html>')
    return '\n'.join(out)


def write_charts(folder, stem, charts):
    """Write each chart as folder/stem_key.svg; returns the paths."""
    paths = []
    for sheet, key, title, svg in charts:
        path = os.path.join(folder, f'{stem}_{key}.svg')
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(svg)
        paths.append(path)
    return paths


def write_page(folder, filename, text):
    """Write the page text as folder/filename (UTF-8); returns the path."""
    path = os.path.join(folder, filename)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)
    return path
