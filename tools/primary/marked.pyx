# cython: language_level=3
r"""marked.pyx -- Markdown to HTML. One public function.

    from marked import md2htm
    htm = md2htm(md)        # md: bytes of Markdown (or a str); htm: a new bytearray of HTML

md2htm(md) -> bytearray
    md      bytes, bytearray or memoryview of UTF-8 Markdown, or a str. Input that is not
            UTF-8 is repaired (the bad bytes become a replacement character).
    The HTML holds <p>, <h1>-<h6>, <pre><code>, <hr>, <blockquote>, <ul>, <ol>, <li> and
    <table class="grid">, inline emphasis, strong, ~~strike~~, `code`, [links](url "title"),
    ![images](src), <autolinks>, bare http:// and www. addresses, [reference][links], hard
    breaks. Raw HTML in the Markdown is shown as text (escaped); javascript: links are dropped.
    The language and the markers for sections, tabs and other divs are in marker.md.

The HTML always starts with a section comment, <!--SECTION name-->: the first section is
named _\main/_ when the Markdown does not start with a section marker. htmlwriter.htmtemplate
splits the HTML at these comments.

VERSION  M2 m02.v01 (2026-10-28): rebuilt as md2htm(md): no byte-array header, no data-md, no
         column arguments (mdwriter has them); section markers; a bare name is a div; ids
         are numbered by call and marker.
         M1 (2026-10-28): marked.py with md2html(b, *md): see zprev/marked.py.
"""
import re

__all__ = ['md2htm']

CALLS = [0]                                 # md2htm calls so far: makes ids unique on a page

ESCAPABLE = '\\`*_{}[]()#+-.!|~<>"\'&:;/=?@$%^,'
FENCE = re.compile(r'^( {0,3})(`{3,}|~{3,})[ \t]*([^\n]*)$')
ATX = re.compile(r'^ {0,3}(#{1,6})(?:[ \t]+(.*?))?[ \t]*$')
HR = re.compile(r'^ {0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$')
QUOTE = re.compile(r'^ {0,3}> ?(.*)$')
LIST = re.compile(r'^( {0,3})([*+-]|\d{1,9}[.)])( +|$)(.*)$')
SETEXT = re.compile(r'^ {0,3}(=+|-+)[ \t]*$')
DELIM = re.compile(r'^ {0,3}\|?[ \t]*:?-+:?[ \t]*(?:\|[ \t]*:?-+:?[ \t]*)*\|?[ \t]*$')
DEFINITION = re.compile(r'^ {0,3}\[([^\]\n]+)\]:[ \t]*<?([^\s>]+)>?'
                        r'(?:[ \t]+["\'(](.*?)["\')])?[ \t]*$')
TASK = re.compile(r'^\[([ xX])\][ \t]+')
URL = re.compile(r'(?:https?://|www\.)[^\s<]+')
AUTOLINK = re.compile(r'<([A-Za-z][A-Za-z0-9+.\-]{1,31}:[^\s<>]*)>')
AUTOMAIL = re.compile(r'<([^\s<>@]+@[^\s<>]+)>')
ENTITY = re.compile(r'&(?!(?:#\d+|#[xX][0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]*);)')
UNSAFE = re.compile(r'^\s*(?:javascript|vbscript):', re.I)
MARK = re.compile(r'^ {0,3}_\\(.+?)/_[ \t]*$')
MARKEND = re.compile(r'^ {0,3}_\\\|/_[ \t]*$')
MARKBODY = re.compile(r'(?:([A-Za-z][A-Za-z0-9-]*):)?(.*?)(?:[ \t]*\{([^{}]*)\})?[ \t]*')
ITEM = re.compile(r'^ {0,3}\|[ \t]?(.*)$')
ROWCLASS = re.compile(r'^\{\.([\w -]+)\}[ \t]*')


# ---- escaping -----------------------------------------------------------------------------
cdef object esc(text):
    """Text for an HTML attribute or code: every & < > " is escaped."""
    return (text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;'))


cdef object esctext(text):
    """Text between tags: & < > are escaped, an entity such as &amp; is left alone."""
    return ENTITY.sub('&amp;', text).replace('<', '&lt;').replace('>', '&gt;')


# ---- block pass ---------------------------------------------------------------------------
cdef object indent(line):
    return len(line) - len(line.lstrip(' '))


cdef object startsblock(line):
    """True if the line would begin a block that interrupts a paragraph."""
    if FENCE.match(line) or ATX.match(line) or HR.match(line) or QUOTE.match(line):
        return True
    if marker(line) is not None:
        return True
    m = LIST.match(line)
    return bool(m and m.group(4).strip() and (not m.group(2)[0].isdigit()
                                              or m.group(2)[:-1] == '1'))


cdef object marker(line):
    r"""The marker a line is, or None: {'kind': 'end'}, {'kind': 'section', 'name'}, or
    {'kind': 'open' | 'next', 'type', 'name', 'cls'}. A name with _\ or /_ inside is not one."""
    if MARKEND.match(line):
        return {'kind': 'end', 'type': '', 'name': '', 'cls': []}
    m = MARK.match(line)
    if not m or '_\\' in m.group(1) or '/_' in m.group(1):
        return None
    kind, name, cls = MARKBODY.fullmatch(m.group(1)).groups()
    name = name.strip()
    cls = (cls or '').split()
    if kind == 'section':
        return {'kind': 'section', 'type': '', 'name': name, 'cls': []} if name else None
    if kind == 'next':
        return {'kind': 'next', 'type': '', 'name': name, 'cls': cls}
    if not name and kind != 'flex':
        return None
    return {'kind': 'open', 'type': kind or '', 'name': name, 'cls': cls}


cdef object cells(line):
    s = line.strip()
    if s.startswith('|'):
        s = s[1:]
    if s.endswith('|') and not s.endswith('\\|'):
        s = s[:-1]
    return [p.strip().replace('\\|', '|') for p in re.split(r'(?<!\\)\|', s)]


cdef object istable(lines, i, n):
    if i + 1 >= n or '|' not in lines[i]:
        return False
    nxt = lines[i + 1]
    return bool(DELIM.match(nxt) and ('|' in nxt or ':' in nxt)
                and len(cells(lines[i])) == len(cells(nxt)))


cdef object lex(lines, defs, top=False):
    """Blocks of a list of lines: tokens {t, first, last, ...}, first/last as indexes of
    the lines (last excluded). Link definitions go into defs. top: the lines are the
    document's own, so markers count (and the items of a flex)."""
    out = []
    i, n = 0, len(lines)
    flex = False                                    # inside a flex: lines with | are items
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if top:
            mark = marker(line)
            if mark is not None:
                mark.update(t='mark', first=i, last=i + 1)
                out.append(mark)
                flex = mark['kind'] == 'open' and mark['type'] == 'flex'
                i += 1
                continue
            m = ITEM.match(line) if flex else None
            if m:
                j = i + 1
                body = [m.group(1)]
                while (j < n and lines[j].strip() and not ITEM.match(lines[j])
                       and marker(lines[j]) is None):
                    body.append(lines[j])
                    j += 1
                out.append({'t': 'item', 'first': i, 'last': j, 'tokens': lex(body, defs)})
                i = j
                continue
        m = FENCE.match(line)
        if m and not (m.group(2)[0] == '`' and '`' in m.group(3)):
            ch, size, pad = m.group(2)[0], len(m.group(2)), len(m.group(1))
            close = re.compile(r'^ {0,3}' + re.escape(ch) + '{' + str(size) + r',}[ \t]*$')
            j = i + 1
            body = []
            while j < n and not close.match(lines[j]):
                body.append(lines[j][min(pad, indent(lines[j])):])
                j += 1
            out.append({'t': 'code', 'first': i, 'last': min(j + 1, n),
                        'lang': m.group(3).strip().split(' ')[0], 'text': '\n'.join(body)})
            i = min(j + 1, n)
            continue
        if indent(line) >= 4:
            j = i
            body = []
            while j < n and (indent(lines[j]) >= 4 or not lines[j].strip()):
                body.append(lines[j][4:])
                j += 1
            while body and not body[-1].strip():
                body.pop()
                j -= 1
            out.append({'t': 'code', 'first': i, 'last': j, 'lang': '', 'text': '\n'.join(body)})
            i = j
            continue
        m = ATX.match(line)
        if m:
            text = m.group(2) or ''
            text = '' if re.fullmatch(r'#+', text) else re.sub(r'[ \t]+#+$', '', text)
            out.append({'t': 'h', 'first': i, 'last': i + 1, 'depth': len(m.group(1)),
                        'text': text.strip()})
            i += 1
            continue
        if HR.match(line):
            out.append({'t': 'hr', 'first': i, 'last': i + 1})
            i += 1
            continue
        if QUOTE.match(line):
            j = i
            inner = []
            while j < n:
                q = QUOTE.match(lines[j])
                if q:
                    inner.append(q.group(1))
                elif (lines[j].strip() and inner and inner[-1].strip()
                      and not startsblock(lines[j])):
                    inner.append(lines[j])
                else:
                    break
                j += 1
            out.append({'t': 'quote', 'first': i, 'last': j, 'tokens': lex(inner, defs)})
            i = j
            continue
        m = LIST.match(line)
        if m and not HR.match(line):
            token, i = lexlist(lines, i, n, defs)
            out.append(token)
            continue
        m = DEFINITION.match(line)
        if m:
            defs.setdefault(m.group(1).strip().lower(), (m.group(2), m.group(3) or ''))
            i += 1
            continue
        if istable(lines, i, n):
            align = []
            for c in cells(lines[i + 1]):
                align.append('center' if c.startswith(':') and c.endswith(':') else
                             'right' if c.endswith(':') else 'left' if c.startswith(':') else '')
            head = cells(line)
            body = []
            rowcls = []
            j = i + 2
            while j < n and lines[j].strip() and not startsblock(lines[j]):
                row = cells(lines[j])[:len(head)]
                row += [''] * (len(head) - len(row))
                found = ROWCLASS.match(row[0])      # {.bad} first in the row: a class of the row
                rowcls.append(found.group(1) if found else '')
                if found:
                    row[0] = row[0][found.end():]
                body.append(row)
                j += 1
            out.append({'t': 'table', 'first': i, 'last': j, 'head': head,
                        'align': align, 'rows': body, 'rowcls': rowcls})
            i = j
            continue
        j = i + 1                                   # a paragraph, or a setext heading
        depth = 0
        while j < n and lines[j].strip():
            s = SETEXT.match(lines[j])
            if s:
                depth = 1 if s.group(1)[0] == '=' else 2
                break
            if startsblock(lines[j]) or istable(lines, j, n):
                break
            j += 1
        text = '\n'.join(x.lstrip() for x in lines[i:j]).rstrip()   # two trailing spaces break
        if depth:
            out.append({'t': 'h', 'first': i, 'last': j + 1, 'depth': depth, 'text': text})
            i = j + 1
        else:
            out.append({'t': 'p', 'first': i, 'last': j, 'text': text})
            i = j
    return out


cdef object lexlist(lines, i, n, defs):
    """One list from line i: (token, the line after it)."""
    m = LIST.match(lines[i])
    ordered = m.group(2)[0].isdigit()
    delim = m.group(2)[-1] if ordered else m.group(2)
    start = int(m.group(2)[:-1]) if ordered else 0
    items = []
    loose = False
    j = i
    while j < n:
        m = LIST.match(lines[j])
        if not m or HR.match(lines[j]):
            break
        mark = m.group(2)
        if mark[0].isdigit() != ordered or (mark[-1] if ordered else mark) != delim:
            break
        pad = len(m.group(1)) + len(mark)
        spaces = len(m.group(3))
        rest = m.group(4)
        if not rest.strip():
            width, first = pad + 1, ''
        elif spaces > 4:
            width, first = pad + 1, ' ' * (spaces - 1) + rest
        else:
            width, first = pad + spaces, rest
        body = [first]
        k = j + 1
        while k < n:
            line = lines[k]
            if not line.strip():
                look = k + 1
                while look < n and not lines[look].strip():
                    look += 1
                if look < n and indent(lines[look]) >= width and body[0].strip():
                    body += [''] * (look - k)
                    k = look
                    continue
                break
            if indent(line) >= width:
                body.append(line[width:])
            elif body[-1].strip() and not startsblock(line) and not LIST.match(line):
                body.append(line.lstrip())
            else:
                break
            k += 1
        end = k
        while end > j + 1 and not lines[end - 1].strip():
            end -= 1
        task = None
        t = TASK.match(body[0])
        if t:
            task = t.group(1) != ' '
            body[0] = body[0][t.end():]
        tokens = lex(body, defs)
        if any(a['last'] < b['first'] for a, b in zip(tokens, tokens[1:])):
            loose = True
        items.append({'first': j, 'last': end, 'tokens': tokens, 'task': task})
        j = k
        look = j
        while look < n and not lines[look].strip():
            look += 1
        nxt = LIST.match(lines[look]) if look < n else None
        if (not nxt or HR.match(lines[look]) or nxt.group(2)[0].isdigit() != ordered
                or (nxt.group(2)[-1] if ordered else nxt.group(2)) != delim):
            break                                   # the list ends; blanks after it are not a gap
        if look > j:
            loose = True                            # a blank line between two items
        j = look
    last = items[-1]['last']
    return {'t': 'list', 'first': i, 'last': last, 'ordered': ordered, 'start': start,
            'loose': loose, 'items': items}, last


# ---- inline pass --------------------------------------------------------------------------
cdef object punct(c):
    return bool(c) and not (c.isalnum() or c.isspace())


cdef object bracket(text, i):
    """Index of the ] that matches the [ at i, or -1."""
    depth = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == '\\':
            i += 1
        elif c == '`':
            k = 1
            while i + k < n and text[i + k] == '`':
                k += 1
            end = text.find('`' * k, i + k)
            if end > 0:
                i = end + k - 1
        elif c == '[':
            depth += 1
        elif c == ']':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


cdef object destination(text, i):
    """Parse (url "title") from the ( at i: (url, title, index after the )) or None."""
    n = len(text)
    i += 1
    while i < n and text[i] in ' \n':
        i += 1
    if i < n and text[i] == '<':
        end = text.find('>', i)
        if end < 0:
            return None
        url, i = text[i + 1:end], end + 1
    else:
        depth, k = 0, i
        while k < n and not text[k].isspace():
            if text[k] == '\\':
                k += 1
            elif text[k] == '(':
                depth += 1
            elif text[k] == ')':
                if depth == 0:
                    break
                depth -= 1
            k += 1
        url, i = text[i:k], k
    while i < n and text[i] in ' \n':
        i += 1
    title = ''
    if i < n and text[i] in '"\'(':
        close = ')' if text[i] == '(' else text[i]
        end = text.find(close, i + 1)
        if end < 0:
            return None
        title, i = text[i + 1:end], end + 1
        while i < n and text[i] in ' \n':
            i += 1
    if i < n and text[i] == ')':
        return url, title, i + 1
    return None


cdef object link(url, title, inner, image):
    if UNSAFE.match(url):
        return inner
    url = re.sub(r'\\([!-/:-@\[-`{-~])', r'\1', url)
    t = f' title="{esc(title)}"' if title else ''
    if image:
        alt = esc(re.sub(r'<[^>]*>', '', inner))
        return f'<img src="{esc(url)}" alt="{alt}"{t}>'
    return f'<a href="{esc(url)}"{t}>{inner}</a>'


cdef object textof(node):
    return node if isinstance(node, str) else node['ch'] * node['n']


cdef object emphasis(nodes):
    """Resolve delimiter runs into <em>, <strong> and <del> (the CommonMark rules)."""
    out = []
    stack = []
    for node in nodes:
        if isinstance(node, str):
            out.append(node)
            continue
        if node['close']:
            k = len(stack) - 1
            while k >= 0 and node['n'] > 0:
                at = stack[k]
                o = out[at]
                if o['ch'] != node['ch'] or not o['open'] or o['n'] == 0:
                    k -= 1
                    continue
                if ((o['close'] or node['open']) and (o['orig'] + node['orig']) % 3 == 0
                        and not (o['orig'] % 3 == 0 and node['orig'] % 3 == 0)):
                    k -= 1
                    continue
                use = min(o['n'], node['n'], 2) if node['ch'] == '~' else (
                    2 if o['n'] >= 2 and node['n'] >= 2 else 1)
                tag = 'del' if node['ch'] == '~' else ('strong' if use == 2 else 'em')
                inner = ''.join(textof(x) for x in out[at + 1:])
                del stack[k + 1:]
                o['n'] -= use
                node['n'] -= use
                out[at + 1:] = [f'<{tag}>{inner}</{tag}>']
                if o['n'] == 0:
                    stack.pop(k)
                k = len(stack) - 1
        if node['n'] > 0:
            out.append(node)
            if node['open']:
                stack.append(len(out) - 1)
    return ''.join(textof(x) for x in out)


cdef object inline(text, defs):
    """The HTML of the text of a block."""
    nodes = []
    pending = []

    def flush():
        if pending:
            nodes.append(esctext(''.join(pending)))
            pending.clear()

    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '\\' and i + 1 < n and text[i + 1] in ESCAPABLE:
            flush()
            nodes.append(esc(text[i + 1]))
            i += 2
        elif c == '\\' and i + 1 < n and text[i + 1] == '\n':
            flush()
            nodes.append('<br>\n')
            i += 2
        elif c == '`':
            k = 1
            while i + k < n and text[i + k] == '`':
                k += 1
            end = i + k
            while True:
                end = text.find('`' * k, end)
                if end < 0 or text[end + k:end + k + 1] != '`':
                    break
                while end < n and text[end] == '`':
                    end += 1
            if end < 0:
                pending.append('`' * k)
                i += k
            else:
                code = text[i + k:end].replace('\n', ' ')
                if code.startswith(' ') and code.endswith(' ') and code.strip():
                    code = code[1:-1]
                flush()
                nodes.append(f'<code>{esc(code)}</code>')
                i = end + k
        elif c == '<':
            m = AUTOLINK.match(text, i) or AUTOMAIL.match(text, i)
            if m:
                flush()
                url = m.group(1)
                shown = esc(url)
                if m.re is AUTOMAIL:
                    url = 'mailto:' + url
                nodes.append(link(url, '', shown, False))
                i = m.end()
            else:
                pending.append('<')
                i += 1
        elif c in '[!' and (c == '[' or text[i + 1:i + 2] == '['):
            image = c == '!'
            open_ = i + (1 if image else 0)
            close = bracket(text, open_)
            done = None
            if close > 0:
                label = text[open_ + 1:close]
                after = close + 1
                if text[after:after + 1] == '(':
                    d = destination(text, after)
                    if d:
                        done = (d[0], d[1], d[2])
                else:
                    ref = label
                    if text[after:after + 1] == '[':
                        end = text.find(']', after)
                        if end > 0:
                            ref = text[after + 1:end] or label
                            after = end + 1
                    found = defs.get(ref.strip().lower())
                    if found:
                        done = (found[0], found[1], after)
            if done:
                flush()
                inner = inline(label, defs)
                nodes.append(link(done[0], done[1], inner, image))
                i = done[2]
            else:
                pending.append(c)
                i += 1
        elif c in '*_~':
            k = 1
            while i + k < n and text[i + k] == c:
                k += 1
            if c == '~' and k > 2:
                pending.append(c * k)
                i += k
                continue
            before = text[i - 1] if i else ' '
            after = text[i + k] if i + k < n else ' '
            left = not after.isspace() and (not punct(after) or before.isspace() or punct(before))
            right = not before.isspace() and (not punct(before) or after.isspace() or punct(after))
            if c == '_':
                can_open = left and (not right or punct(before))
                can_close = right and (not left or punct(after))
            else:
                can_open, can_close = left, right
            flush()
            nodes.append({'ch': c, 'n': k, 'orig': k, 'open': can_open, 'close': can_close})
            i += k
        elif c == '\n':
            spaces = len(''.join(pending)) - len(''.join(pending).rstrip(' '))
            if pending:
                pending[:] = [''.join(pending).rstrip(' ')]
            flush()
            nodes.append('<br>\n' if spaces >= 2 else '\n')
            i += 1
            while i < n and text[i] == ' ':
                i += 1
        elif c in 'hw' and (i == 0 or not text[i - 1].isalnum()) and URL.match(text, i):
            m = URL.match(text, i)
            url = m.group(0).rstrip('.,:;!?)*_~\'"')
            flush()
            nodes.append(link(url if url.startswith('http') else 'http://' + url, '', esc(url),
                              False))
            i += len(url)
        else:
            pending.append(c)
            i += 1
    flush()
    return emphasis(nodes)


# ---- the HTML ----------------------------------------------------------------------------
cdef object render(b, tokens, defs, ctx, tight=False):
    """Write the HTML of the tokens into the list b."""
    for at, tok in enumerate(tokens):
        t = tok['t']
        if t == 'mark':
            mark(b, ctx, tok)
            continue
        if t == 'item':
            b.append('<div class="mk-item">\n')
            render(b, tok['tokens'], defs, ctx, True)
            b.append('\n</div>\n')
            continue
        if t == 'p':
            body = inline(tok['text'], defs)
            if not tight:
                b.append(f'<p>{body}</p>\n')
            else:
                b.append(body + ('\n' if at < len(tokens) - 1 else ''))
        elif t == 'h':
            d = tok['depth']
            b.append(f'<h{d}>{inline(tok["text"], defs)}</h{d}>\n')
        elif t == 'code':
            cls = f' class="language-{esc(tok["lang"])}"' if tok['lang'] else ''
            b.append(f'<pre><code{cls}>{esc(tok["text"])}'
                   f'{chr(10) if tok["text"] else ""}</code></pre>\n')
        elif t == 'hr':
            b.append(f'<hr>\n')
        elif t == 'quote':
            b.append(f'<blockquote>\n')
            render(b, tok['tokens'], defs, ctx)
            b.append('</blockquote>\n')
        elif t == 'list':
            tag = 'ol' if tok['ordered'] else 'ul'
            start = f' start="{tok["start"]}"' if tok['ordered'] and tok['start'] != 1 else ''
            b.append(f'<{tag}{start}>\n')
            for item in tok['items']:
                box = ''
                if item['task'] is not None:
                    box = ('<input ' + ('checked="" ' if item['task'] else '')
                           + 'disabled="" type="checkbox"> ')
                b.append(f'<li>{box}')
                render(b, item['tokens'], defs, ctx, not tok['loose'])
                b.append('</li>\n')
            b.append(f'</{tag}>\n')
        elif t == 'table':
            b.append(f'<table class="grid">\n<thead>\n<tr>\n')
            for k, c in enumerate(tok['head']):
                a = f' align="{tok["align"][k]}"' if tok['align'][k] else ''
                b.append(f'<th{a}>{inline(c, defs)}</th>\n')
            b.append('</tr>\n</thead>\n')
            if tok['rows']:
                b.append('<tbody>\n')
                for r, row in enumerate(tok['rows']):
                    rc = tok['rowcls'][r]
                    b.append(f'<tr class="{esc(rc)}">\n' if rc else '<tr>\n')
                    for k, c in enumerate(row):
                        a = f' align="{tok["align"][k]}"' if tok['align'][k] else ''
                        b.append(f'<td{a}>{inline(c, defs)}</td>\n')
                    b.append('</tr>\n')
                b.append('</tbody>\n')
            b.append('</table>\n')


cdef object mark(b, ctx, tok):
    """Write what a marker does: a section starts, a div closes, a div opens."""
    stack = ctx['stack']
    kind, type_ = tok['kind'], tok['type']
    if kind == 'section':
        b.append('</div>\n' * len(stack))
        stack.clear()
        b.append('<!--SECTION ' + tok['name'].replace('-->', '--').replace('\n', ' ') + '-->\n')
        return
    if kind in ('end', 'next'):
        if stack:
            b.append('</div>\n')
            type_ = stack.pop()
        if kind == 'end':
            return
    ctx['n'] += 1
    classes = ' '.join(['mk'] + (['mk-' + type_] if type_ else []) + tok['cls'])
    b.append(f'<div class="{classes}" id="mk{ctx["call"]}.{ctx["n"]}" '
             f'data-name="{esc(tok["name"])}">\n')
    stack.append(type_)


def md2htm(md):
    """Convert Markdown (bytes, or a str) to HTML. See the module header."""
    if isinstance(md, str):
        text = md
    elif isinstance(md, (bytes, bytearray, memoryview)):
        text = bytes(md).decode('utf-8', 'replace')
    else:
        raise TypeError('md2htm: md is bytes, a bytearray, a memoryview or a str')
    lines = [x.expandtabs(4) for x in text.replace('\r\n', '\n').replace('\r', '\n').split('\n')]
    defs = {}
    tokens = lex(lines, defs, True)
    CALLS[0] += 1
    ctx = {'stack': [], 'n': 0, 'call': CALLS[0]}
    b = []
    if not (tokens and tokens[0]['t'] == 'mark' and tokens[0]['kind'] == 'section'):
        b.append('<!--SECTION _\\main/_-->\n')
    render(b, tokens, defs, ctx)
    b.append('</div>\n' * len(ctx['stack']))
    return bytearray(''.join(b).encode('utf-8'))


# ---- licence and credits ------------------------------------------------------------------
# marked.py and marked.pyx: Copyright (c) Frans L. Muller. MIT licence (the text below).
#
# Adapted from marked, https://github.com/markedjs/marked : the block and inline rules from
# https://github.com/markedjs/marked/blob/master/src/rules.ts , the table, list, emphasis and
# link handling from .../src/Tokenizer.ts , the order the rules are tried in from
# .../src/Lexer.ts and the HTML forms from .../src/Renderer.ts . The two-pass design (blocks,
# then the inline text of each block) was checked against Markdig,
# https://github.com/xoofx/markdig/tree/master/src/Markdig/Parsers
#
# Copyright (c) 2018+, MarkedJS (https://github.com/markedjs/)
# Copyright (c) 2011-2018, Christopher Jeffrey (https://github.com/chjj/)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons
# to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or
# substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE
# FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
#
# marked carries this notice for the Markdown language it implements:
# Copyright (c) 2004, John Gruber, http://daringfireball.net/ . All rights reserved.
# Redistribution and use in source and binary forms, with or without modification, are
# permitted provided that the following conditions are met:
#   * Redistributions of source code must retain the above copyright notice, this list of
#     conditions and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice, this list of
#     conditions and the following disclaimer in the documentation and/or other materials
#     provided with the distribution.
#   * Neither the name "Markdown" nor the names of its contributors may be used to endorse
#     or promote products derived from this software without specific prior written
#     permission.
# This software is provided by the copyright holders and contributors "as is" and any
# express or implied warranties, including, but not limited to, the implied warranties of
# merchantability and fitness for a particular purpose are disclaimed. In no event shall the
# copyright owner or contributors be liable for any direct, indirect, incidental, special,
# exemplary, or consequential damages (including, but not limited to, procurement of
# substitute goods or services; loss of use, data, or profits; or business interruption)
# however caused and on any theory of liability, whether in contract, strict liability, or
# tort (including negligence or otherwise) arising in any way out of the use of this software,
# even if advised of the possibility of such damage.
#
# Markdig, Copyright (c) 2016-2026, Alexandre Mutel. All rights reserved. BSD 2-Clause:
# Redistributions of source code must retain the above copyright notice, this list of
# conditions and the following disclaimer. Redistributions in binary form must reproduce the
# above copyright notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution. THIS SOFTWARE IS
# PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED; IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DAMAGES ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE.
