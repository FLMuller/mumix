r"""rs3microDB.py -- a small text database of the comments of a page that is an html file: the verbs note_add and note_list.

Verbs (websocket; each takes the page's hash, as every verb of rs3)
    note_add   {do: 'note_add', hash, file, line, text, code?}  -> {ok, code}
               write a comment. `file` is the name the page gives to the part of itself the comment is on (a tab), `line` the
               number of its line. Without `code` the comment is new and the server makes its code; with the code of an
               earlier comment this one replaces it (the file is appended to, never rewritten: the last record of a code
               is the comment). An empty text removes the comment.
    note_list  {do: 'note_list', hash, file?}  -> {ok, notes: [{code, file, line, text, who, ts}]}
               the comments now standing, oldest first; only those of `file` when it is given.

Where it is written. A comment goes to ONE file, found from the page and never from the message: the page's doc file
(`&doc=./mumix/x/comments.html`) with its extension changed to `.notes`, in the same folder (comments.html ->
comments.notes). The server makes the file when the first comment is written. A page that is not an html file has no
notes file: both verbs refuse it. Nothing else on disk is read or written.

The file is jsonl, one record a line: {"code", "file", "line", "text", "who", "ts"}.
    code  the id of a comment: the time to the microsecond, YYYYMMDDTHHMMSS.ffffff, a minus sign and the first six
          hex digits of the sha1 of (time, file, line, text): unique in practice, and sorting by it is sorting by time.
    ts    the same time as ISO 8601 (local); who is the user id the box sent (the settings menu's initials).
A record of a code with an empty text is a removal.

Limits: a text of at most 30000 characters, a file name of at most 200, a line number of at most 10 million, a notes
file of at most 8 MB (writing refuses after that).

VERSION  M1 m01.v01 (2026-11-12): first version.
"""
import hashlib
import json
import os
import time

from rs3util import address, pathof

__all__ = ['VERBS']

MAX_TEXT = 30000
MAX_FILE = 200
MAX_LINE = 10_000_000
MAX_BYTES = 8 * 1024 * 1024


def refuse(why):
    return {'ok': False, 'error': why}


def notes_file(S, msg):
    """(path of the notes file, None) of the page of msg's hash, or (None, {ok: false, error}) when the page has none:
    the page must have been made from one doc file, an .html inside the root of the page."""
    page, why = S['pages'].known(msg.get('hash'))
    if page is None:
        return None, refuse(why)
    source = page.get('path') or ''
    if not source.startswith('/?'):
        return None, refuse('this page is not an html file: it has no notes file')
    try:
        specs = address(source)[1]
        doc = specs.get('doc', [])[1:]
    except (ValueError, TypeError, KeyError):
        return None, refuse('this page is not an html file: it has no notes file')
    if len(doc) != 1 or not isinstance(doc[0], str) or doc[0].startswith('/') or not doc[0].endswith('.html'):
        return None, refuse('this page is not an html file: it has no notes file')
    real = pathof(doc[0] if doc[0].startswith('./') else './' + doc[0], kinds=('html',))
    if real is None:
        return None, refuse('the html file of this page is not readable')
    return os.path.splitext(real)[0] + '.notes', None


def read_notes(path):
    """The records of the file as written, in order (a damaged line is skipped)."""
    records = []
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            for row in f:
                row = row.strip()
                if not row:
                    continue
                try:
                    one = json.loads(row)
                except ValueError:
                    continue
                if isinstance(one, dict) and 'code' in one:
                    records.append(one)
    return records


def standing(records):
    """The comments that stand: the last record of each code, a removal (empty text) taken out, oldest code first."""
    last = {}
    for one in records:
        last[one['code']] = one
    return sorted((one for one in last.values() if str(one.get('text', '')).strip()), key=lambda one: one['code'])


def make_code(file, line, text):
    now = time.time()
    stamp = time.strftime('%Y%m%dT%H%M%S', time.localtime(now)) + '.%06d' % int((now % 1) * 1_000_000)
    digest = hashlib.sha1(f'{stamp}|{file}|{line}|{text}'.encode('utf-8')).hexdigest()[:6]
    return f'{stamp}-{digest}', time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(now))


def note_add(msg, S):
    path, why = notes_file(S, msg)
    if why:
        return why
    file, line, text = msg.get('file'), msg.get('line'), msg.get('text')
    if not isinstance(file, str) or not file or len(file) > MAX_FILE:
        return refuse('file must be a short name')
    if not isinstance(line, int) or isinstance(line, bool) or not 0 <= line <= MAX_LINE:
        return refuse('line must be a whole number')
    if not isinstance(text, str) or len(text) > MAX_TEXT:
        return refuse(f'text must be a string of at most {MAX_TEXT} characters')
    if os.path.exists(path) and os.path.getsize(path) > MAX_BYTES:
        return refuse('the notes file is full')
    code = msg.get('code')
    code_new, stamp = make_code(file, line, text)
    if code is None:
        code = code_new
    elif not isinstance(code, str) or len(code) > 40 or not code.replace('-', '').replace('.', '').replace('T', '').isalnum():
        return refuse('code is not the code of a comment')
    row = {'code': code, 'file': file, 'line': line, 'text': text, 'who': str(msg.get('who', ''))[:40], 'ts': stamp}
    with open(path, 'a', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')
    return {'ok': True, 'code': code}


def note_list(msg, S):
    path, why = notes_file(S, msg)
    if why:
        return why
    file = msg.get('file')
    notes = [one for one in standing(read_notes(path)) if file is None or one.get('file') == file]
    return {'ok': True, 'notes': notes}


VERBS = {'note_add': note_add, 'note_list': note_list}
