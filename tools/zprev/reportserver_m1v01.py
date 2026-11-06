r"""reportserver.py -- the report server: a small websocket daemon that lets an open report list
and load the other reports of its series. One process, no threads, asleep until a byte arrives.

    from reportserver import ensure, start, stop, status, running, token
    running()                  # 'ours', 'other' (the port is used by something else) or None
    ensure('runbench')         # what a program calls: nothing if it runs, else the bat opens
    print(start('claude 2026-11-03-01;43;12'))   # 'report server: started (pid 123)' or 'running'
    python reportserver.py     # run the server itself, in this process (the daemon runs this)
    python reportserver.py --start --by BY | --stop --by BY | --status | --register FOLDER
                               # start the daemon (one only) | stop it | say how it is |
                               # let it read the reports in FOLDER

Who. Every start and stop says who asked, BY, and the server's log keeps it: "started, pid 123,
    port 47651, by claude 2026-11-03-01;43;12" and "stop requested by ...". BY is 1 to 60 of
    letters, digits, space and . _ - : ; (the bat's own label is a name and its opening time).
    The server cannot log its own death (Windows ends it at once), so stop() logs first.
The bat. The one way a person meets the server is .claude/vscripts/reportserver.bat: a window
    with the status, a prompt and the log beside it. A program that needs the server calls
    ensure(by): nothing is done if it runs, else the bat is opened (os.startfile, a window the
    user can see) with --by BY --start, which starts the daemon. ensure(by, visible=False) runs
    the bat with --hidden instead: no window at all. A port or files that are not the default
    ones (a test) start the daemon directly. bat_path() says where the bat is, '' if missing.

The daemon
    start() launches the server detached and without a window (pythonw), at below-normal
    priority. There is only ever one: it binds PORT on 127.0.0.1 exclusively, and a second
    copy exits at once with code 3, whoever started it. A software error in the server's loop
    is logged and the loop starts again after 3 s, on the same bound port. The files it keeps
    are in the folder reportserver/ beside this file (override with --roots, --log, --pid):
    reportserver.roots (the folders it may read, one a line, added by register()),
    reportserver.log (kept to about 100 KB; the one before it is reportserver.log.old) and
    reportserver.pid.

What a page may ask (a websocket to ws://127.0.0.1:PORT, one JSON text message each)
    {"hash": TOKEN}                    the other reports of its series: [{"file", "when"}],
                                       newest first
    {"hash": TOKEN, "filename": NAME}  {"file": NAME, "title": ..., "html": the tabs of NAME}
    Anything else, and any refusal, is the reply []; the reason goes only to the log.
    TOKEN is token(name, time) of the asking page's own file, made by htmlwriter.save. It is
    accepted if the asker's time is under a day old by the server's clock, its name and its
    time agree to within a day, and the file is in a registered folder. NAME is a bare file name
    that must be in the directory listing of that folder and have the asker's series name; it
    may be of any age.

Extension verbs (2026-11-01, for vcomment): reportserver.handlers, beside reportserver.roots,
names modules (one a line, importable from this folder) that each define
handler(S, msg, root, name, log) -> reply text or None. They are asked after the settings and
before the report verbs; None leaves the message to the report server. vcserver.py is one.

register(folder) adds a folder to reportserver.roots (once). prepare(folder) does that and returns
bat_path(), which the pages show when the server is not running.

status(...) -> {state, pid, since, port, roots, last}: state 'ours', 'other' or None; pid from the
pid file and since its time (the server writes it when it starts); roots the number of
registered folders; last the last line of the log.

VERSION  M1 m01.v01 (2026-11-03): who asked (BY) in the log, status(), ensure() and the bat in
         .claude/vscripts instead of the two bats this module used to write (write_bats is gone).
"""
import atexit
import ast
import base64
import hashlib
import html
import importlib
import json
import os
import re
import selectors
import signal
import socket
import struct
import subprocess
import sys
import time
import traceback

# the daemon starts as a script with only this folder on its path: tools/ (use.py) is added
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from use import load

load('marked')                       # md2htm, compiled: use finds marked.pyx beside this file

__all__ = ['PORT', 'token', 'unpack', 'running', 'start', 'stop', 'status', 'ensure',
           'bat_path', 'register', 'prepare', 'main']

PORT = 47651
HOST = '127.0.0.1'
HERE = os.path.dirname(os.path.abspath(__file__))
GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
DAY = 86400
MAXAGE = 42 * DAY                                   # a page older than this may not edit a file
MAX_MSG = 65536                     # bytes of one message from a page (a comment is text)
MAX_HEAD = 8192                     # bytes of the handshake
MAX_REPLY = 8 * 1024 * 1024
MAX_CONN = 8
IDLE = 120                          # seconds a connection may be silent
WAKE = 60                           # seconds the select sleeps at most
LOG_MAX = 100 * 1024
NAME = re.compile(r'^(?P<stem>[A-Za-z0-9_.\-]{1,60})_(?P<when>\d{4}\.\d\d\.\d\d_\d\d;\d\d'
                  r'(?:\.\d\d)?[a-z]{0,2})\.html$')           # the minute, seconds, then a, b ... zz
BY = re.compile(r'^[A-Za-z0-9 _.;:\-]{1,60}$')       # who asked: safe in a log line and a command
SHELL = re.compile(r'<!--SHELL:BEGIN-->(.*?)<!--SHELL:END-->', re.S)
TITLE = re.compile(r'<title>(.*?)</title>', re.S)


# ---- the token ------------------------------------------------------------------------------
def token(name, now=None):
    """The packed token of a page: its own file name and the time it was written."""
    raw = f'{name}|{int(time.time() if now is None else now)}'.encode('utf-8')
    return base64.urlsafe_b64encode(raw).decode('ascii').rstrip('=')


def unpack(packed):
    """(name, epoch) from a token, or None if it is not one."""
    try:
        raw = base64.urlsafe_b64decode(packed + '=' * (-len(packed) % 4)).decode('utf-8')
        name, epoch = raw.rsplit('|', 1)
        return name, int(epoch)
    except (ValueError, TypeError, AttributeError, UnicodeError):
        return None


def stamp_epoch(when):
    """Seconds since the epoch of the stamp in a file name, in local time."""
    base = when[:16]
    return time.mktime(time.strptime(base, '%Y.%m.%d_%H;%M'))


# ---- the log, the folders, the replies ------------------------------------------------------
def log(S, text):
    path = S['log']
    try:
        if os.path.isfile(path) and os.path.getsize(path) > LOG_MAX:
            os.replace(path, path + '.old')
        with open(path, 'a', encoding='utf-8') as f:
            f.write(time.strftime('%Y-%m-%d %H:%M:%S ') + text.replace('\n', '\n    ') + '\n')
    except OSError:
        pass


def roots(S):
    """The registered folders that exist; the file is read again when it changes."""
    try:
        stamp = os.path.getmtime(S['roots_file'])
    except OSError:
        return []
    if stamp != S['roots_stamp']:
        with open(S['roots_file'], encoding='utf-8') as f:
            S['roots_list'] = [line.strip() for line in f if line.strip()]
        S['roots_stamp'] = stamp
    return [p for p in S['roots_list'] if os.path.isdir(p)]


def refuse(S, why):
    log(S, 'refused: ' + why)
    return '[]'


HANDLERS = []                                       # see handlers()


def handlers(S):
    """The extension verbs: functions handler(S, msg, root, name, log) -> reply text, or None
    when the message is not theirs. They come from the modules named in the .handlers file beside
    the roots file (one module name a line, importable from this folder; the file is read again
    when it changes). A page of another program (vcomment) is answered by its own module, after
    the settings and before the report verbs; a module that fails to load is logged and left out."""
    path = os.path.splitext(S['roots_file'])[0] + '.handlers'
    try:
        stamp = os.path.getmtime(path)
    except OSError:
        stamp = None
    if stamp != S.get('handlers_stamp'):
        S['handlers_stamp'] = stamp
        HANDLERS.clear()
        if stamp is not None:
            with open(path, encoding='utf-8') as f:
                for line in f:
                    name = line.strip()
                    try:
                        if name:
                            HANDLERS.append(importlib.import_module(name).handler)
                    except Exception:
                        log(S, f'handler module {name} failed to load:\n' + traceback.format_exc())
    return HANDLERS


# ---- the settings and the comment editor -----------------------------------------------------
DEFAULTS = {'font': 'Consolas', 'size': 12, 'initials': 'user', 'linenos': True, 'tabwidth': 4,
            'wrap': False, 'color': '#e8650f'}
COMMENT = re.compile(r'^\s*###(\w{1,8})(?: (.*))?$')      # ###tag text: a line of a comment by tag
EDITABLE = ('.py', '.pyx', '.pxd', '.pxi')


def config_reply(S, change):
    """The settings of the pages {font, size, initials, linenos, tabwidth, wrap, color}, after
    a change (a dict of some of them) is applied; refused if any value is not allowed."""
    path = S['config_file']
    try:
        with open(path, encoding='utf-8') as f:
            have = {**DEFAULTS, **json.load(f)}
    except (OSError, ValueError):
        have = dict(DEFAULTS)
    if isinstance(change, dict):
        for key, value in change.items():
            number = isinstance(value, int) and not isinstance(value, bool)
            ok = key in DEFAULTS and (
                (key == 'font' and isinstance(value, str) and re.fullmatch(r"[\w .\-]{1,60}", value))
                or (key == 'size' and number and 6 <= value <= 40)
                or (key == 'tabwidth' and number and 1 <= value <= 16)
                or (key == 'initials' and isinstance(value, str) and re.fullmatch(r'\w{1,8}', value))
                or (key in ('linenos', 'wrap') and isinstance(value, bool))
                or (key == 'color' and isinstance(value, str)
                    and re.fullmatch(r'#[0-9a-fA-F]{6}', value)))
            if not ok:
                return refuse(S, f'config: {key!r} is not allowed that value')
            have[key] = value
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(have, f)
        os.replace(tmp, path)
    return json.dumps(have)


def tree_of(folder):
    """What the editor may reach from a report in folder: up from it to the first folder that
    holds .git, or to the first folder below the drive, whichever comes first."""
    here = os.path.abspath(folder)
    while True:
        parent = os.path.dirname(here)
        if os.path.isdir(os.path.join(here, '.git')) or os.path.dirname(parent) == parent:
            return here
        here = parent


def skeleton(text, ext):
    """What must not change when comments change: for Python the syntax tree (comments are not
    in it, a ### line pushed into a string is); for the rest, the lines that are not comments."""
    if ext == '.py':
        return ast.dump(ast.parse(text))
    return [x.rstrip() for x in text.split('\n') if not COMMENT.match(x)]


def comment_lines(text, indent, tag):
    """The lines of one comment: ###tag then the text; a blank line keeps its tag and space."""
    return [indent + '###' + tag + ' ' + x for x in text.rstrip('\n').split('\n')]


WRITTEN = {}                                        # real path -> its mtime after this server's own last edit


def reachable(path, root):
    """The real path of a source file the editor may reach from a report in root, else None."""
    top = os.path.realpath(tree_of(root))
    real = os.path.realpath(path)
    try:
        inside = os.path.commonpath([real, top]) == top
    except ValueError:                              # another drive
        inside = False
    if not inside or os.path.splitext(real)[1].lower() not in EDITABLE or not os.path.isfile(real) \
            or os.path.getsize(real) > 4 * 1024 * 1024:
        return None
    return real


def outdated(root, name, real):
    """Why a page may not edit a file, or '' when it may: its report (the file called name in
    root) is over 42 days old, or the file was changed after the report was made. A change this
    server made itself does not count, or a page could not edit twice."""
    made = os.path.getmtime(os.path.join(root, name))
    if time.time() - made > MAXAGE:
        return 'These results are too old (over 42 days) to edit the code: run the tests again for a new report.'
    changed = os.path.getmtime(real)
    if changed > made + 1 and changed != WRITTEN.get(real):
        return 'These results are outdated: the file changed after this report was made. Run the tests again for a new report.'
    return ''


def stale(S, why):
    log(S, 'refused: ' + why)
    return json.dumps({'ok': False, 'outdated': why})


def check_reply(S, msg, root, name):
    """May this page edit that file? {check: true, filename} -> {ok: true} or the outdated reply."""
    real = reachable(msg.get('filename'), root) if isinstance(msg.get('filename'), str) else None
    if real is None:
        return refuse(S, 'check: not a source file inside the tree')
    why = outdated(root, name, real)
    return stale(S, why) if why else '{"ok": true}'


def edit_reply(S, msg, root, name):
    """Add, change or remove one comment of a source file: {update: true, first, last} or
    {insert: true, line}, with filename, tag (who wrote it: 1-8 letters or digits), text (empty
    removes) and base (the fingerprint of the file as the page read it). The comment is written
    as ###tag lines; insert may go one past the last line. Only comments may differ afterwards,
    else nothing is written. A report over 42 days old, or older than the file's last change,
    gets {ok: false, outdated: why} and nothing is written."""
    path, text, base, tag = msg.get('filename'), msg.get('text'), msg.get('base'), msg.get('tag')
    if not (isinstance(path, str) and isinstance(text, str) and isinstance(base, str)):
        return refuse(S, 'edit: filename, text and base are strings')
    if not (isinstance(tag, str) and re.fullmatch(r'\w{1,8}', tag)):
        return refuse(S, 'edit: the tag is 1 to 8 letters or digits')
    if '\x00' in text or len(text) > 30000:
        return refuse(S, 'edit: that text')
    real = reachable(path, root)
    if real is None:
        return refuse(S, f'edit: {path} is not a source file inside {os.path.realpath(tree_of(root))}')
    why = outdated(root, name, real)
    if why:
        return stale(S, why)
    ext = os.path.splitext(real)[1].lower()
    with open(real, 'rb') as f:
        raw = f.read()
    if hashlib.sha1(raw).hexdigest() != base:
        return refuse(S, 'edit: the file has changed since the page read it')
    eol = '\r\n' if b'\r\n' in raw else '\n'
    old = raw.decode('utf-8').replace('\r\n', '\n')
    lines = old.split('\n')
    try:
        if msg.get('update'):
            first, last = int(msg['first']), int(msg['last'])
            block = lines[first - 1:last]
            comment = bool(block) and all(COMMENT.match(x) for x in block)
            if not 1 <= first <= last <= len(lines) or not comment:
                return refuse(S, 'edit: those lines are not a comment')
            indent = re.match(r'\s*', lines[first - 1]).group(0)
        elif msg.get('insert'):
            first = int(msg['line'])
            if not 1 <= first <= len(lines) + 1:
                return refuse(S, 'edit: no such line')
            indent = re.match(r'\s*', lines[min(first, len(lines)) - 1]).group(0)
            last = first - 1                        # nothing is replaced: it goes in before
        else:
            return refuse(S, 'edit: neither update nor insert')
    except (KeyError, TypeError, ValueError):
        return refuse(S, 'edit: the lines are not numbers')
    new = comment_lines(text, indent, tag) if text.strip() else []
    after = lines[:first - 1] + new + lines[last:]
    try:
        if skeleton('\n'.join(after), ext) != skeleton(old, ext):
            return refuse(S, 'edit: more than comments would change')
    except SyntaxError:
        return refuse(S, 'edit: the result is not Python')
    data = eol.join(after).encode('utf-8')
    tmp = real + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(data)
    os.replace(tmp, real)
    WRITTEN[real] = os.path.getmtime(real)
    log(S, f'edit: {real} lines {first}-{last} now {len(new)} lines')
    shown = bytes(md2htm(text)).split(b'-->\n', 1)[1].decode('utf-8')
    return json.dumps({'ok': True, 'base': hashlib.sha1(data).hexdigest(), 'first': first,
                       'last': first + len(new) - 1, 'delta': len(new) - (last - first + 1),
                       'html': shown, 'removed': not new})


def reply_for(S, text):
    """The reply to one message of a page (a str): see the module header."""
    try:
        msg = json.loads(text)
    except ValueError:
        return refuse(S, 'not json')
    if not isinstance(msg, dict):
        return refuse(S, 'not an object')
    if msg.get('ping') == 1:                        # a page asking if we are awake: no files
        return '{"pong": 1}'
    got =unpack(msg.get('hash')) if isinstance(msg.get('hash'), str) else None
    if got is None:
        return refuse(S, 'no usable hash')
    name, epoch = got
    m = NAME.match(name)
    now = time.time()
    if m is None:
        return refuse(S, 'the asker has no report name')
    editing = msg.get('check') or msg.get('update') or msg.get('insert')
    if editing and now - epoch >= MAXAGE:             # told why, not just refused
        return stale(S, 'These results are too old (over 42 days) to edit the code: run the tests again for a new report.')
    if not -3600 <= now - epoch < MAXAGE:
        return refuse(S, 'the asker is more than 42 days old')
    if abs(stamp_epoch(m.group('when')) - epoch) > DAY:
        return refuse(S, 'the asker\'s name and time disagree')
    root = next((r for r in roots(S) if name in os.listdir(r)), None)
    if root is None:
        return refuse(S, 'the asker is in no registered folder')
    if 'config' in msg:
        return config_reply(S, msg['config'])
    for handler in handlers(S):
        try:
            answer = handler(S, msg, root, name, lambda text: log(S, text))
        except Exception:
            log(S, 'handler failed:\n' + traceback.format_exc())
            return '[]'
        if answer is not None:
            return answer
    if msg.get('check'):
        return check_reply(S, msg, root, name)
    if msg.get('update') or msg.get('insert'):
        return edit_reply(S, msg, root, name)
    series = []
    for other in os.listdir(root):
        o = NAME.match(other)
        if o and o.group('stem') == m.group('stem'):
            series.append((o.group('when'), other))
    series.sort(reverse=True)                       # 09;50.07 after 09;50: by time
    want = msg.get('filename')
    if want is None:
        return json.dumps([{'file': f, 'when': w} for w, f in series if f != name])
    if not isinstance(want, str) or want not in {f for w, f in series}:
        return refuse(S, 'not a file of the series')
    with open(os.path.join(root, want), encoding='utf-8') as f:
        page = f.read()
    shell = SHELL.search(page)
    if shell is None:
        return refuse(S, 'the file has no tabs to give')
    title = TITLE.search(page)
    out = json.dumps({'file': want, 'title': html.unescape(title.group(1)) if title else '',
                      'html': shell.group(1)})
    return out if len(out) <= MAX_REPLY else refuse(S, 'the reply is too large')


# ---- websocket ------------------------------------------------------------------------------
def accept_key(key):
    return base64.b64encode(hashlib.sha1((key + GUID).encode()).digest()).decode()


def frame(payload, opcode=1):
    """A server frame (never masked)."""
    n = len(payload)
    head = bytes([0x80 | opcode])
    if n < 126:
        head += bytes([n])
    elif n < 65536:
        head += bytes([126]) + struct.pack('>H', n)
    else:
        head += bytes([127]) + struct.pack('>Q', n)
    return head + payload


def frames(buf):
    """Take the whole client frames out of the bytearray buf: [(fin, opcode, payload)]. A frame
    that is not allowed (not masked, a reserved bit, too long) raises ValueError."""
    out = []
    while len(buf) >= 2:
        first, second = buf[0], buf[1]
        if first & 0x70 or not second & 0x80:
            raise ValueError('reserved bit or unmasked frame')
        n, at = second & 0x7F, 2
        if n == 126:
            if len(buf) < 4:
                break
            n, at = struct.unpack('>H', bytes(buf[2:4]))[0], 4
        elif n == 127:
            if len(buf) < 10:
                break
            n, at = struct.unpack('>Q', bytes(buf[2:10]))[0], 10
        if n > MAX_MSG:
            raise ValueError('frame too long')
        if len(buf) < at + 4 + n:
            break
        mask = buf[at:at + 4]
        data = bytes(b ^ mask[i % 4] for i, b in enumerate(buf[at + 4:at + 4 + n]))
        out.append((bool(first & 0x80), first & 0x0F, data))
        del buf[:at + 4 + n]
    return out


def handshake(S, conn):
    """Answer the upgrade request in conn['buf'] once it is whole. False to close."""
    buf = conn['buf']
    end = buf.find(b'\r\n\r\n')
    if end < 0:
        return len(buf) <= MAX_HEAD
    text = bytes(buf[:end]).decode('latin-1')
    del buf[:end + 4]
    lines = text.split('\r\n')
    head = {}
    for line in lines[1:]:
        key, _, value = line.partition(':')
        head[key.strip().lower()] = value.strip()
    own = (f'{HOST}:{S["port"]}', f'localhost:{S["port"]}')
    origins = (None, 'null', f'http://{HOST}:{S["port"]}', f'http://localhost:{S["port"]}')
    ok = (lines[0].startswith('GET / ') and head.get('upgrade', '').lower() == 'websocket'
          and 'upgrade' in head.get('connection', '').lower() and 'sec-websocket-key' in head
          and head.get('sec-websocket-version') == '13' and head.get('host') in own
          and head.get('origin') in origins)
    if not ok:
        log(S, f'refused handshake from {conn["peer"]}: {lines[0][:60]!r} origin '
               f'{head.get("origin")!r} host {head.get("host")!r}')
        conn['out'] += (b'HTTP/1.1 403 Forbidden\r\nServer: reportserver/1\r\n'
                        b'Content-Length: 0\r\nConnection: close\r\n\r\n')
        conn['closing'] = True
        return True
    conn['out'] += ('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n'
                    'Connection: Upgrade\r\nServer: reportserver/1\r\n'
                    f'Sec-WebSocket-Accept: {accept_key(head["sec-websocket-key"])}\r\n\r\n'
                    ).encode()
    conn['upgraded'] = True
    return True


def take(S, conn):
    """What a connection has read: the handshake, then frames. False to close it."""
    if not conn['upgraded']:
        if not handshake(S, conn):
            return False
        if not conn['upgraded']:
            return True
    for fin, opcode, data in frames(conn['buf']):
        if opcode == 8:
            conn['out'] += frame(data[:2], 8)
            conn['closing'] = True
        elif opcode == 9:
            conn['out'] += frame(data, 10)
        elif opcode in (1, 0):
            conn['part'] += data
            if len(conn['part']) > MAX_MSG:
                raise ValueError('message too long')
            if fin:
                text, conn['part'] = bytes(conn['part']).decode('utf-8', 'replace'), bytearray()
                conn['out'] += frame(reply_for(S, text).encode('utf-8'))
        elif opcode != 10:
            raise ValueError('unsupported opcode')
    return True


# ---- the loop -------------------------------------------------------------------------------
def serve(S, listener):
    """Sleep in the selector and serve what comes, until an exception ends it."""
    sel = selectors.DefaultSelector()
    listener.setblocking(False)
    sel.register(listener, selectors.EVENT_READ, None)
    conns = {}

    def drop(conn):
        conns.pop(conn['sock'], None)
        try:
            sel.unregister(conn['sock'])
        except (KeyError, ValueError):
            pass
        conn['sock'].close()

    def flush(conn):
        if conn['out']:
            try:
                sent = conn['sock'].send(conn['out'])
            except BlockingIOError:
                sent = 0
            del conn['out'][:sent]
        wanted = selectors.EVENT_READ | (selectors.EVENT_WRITE if conn['out'] else 0)
        try:
            sel.modify(conn['sock'], wanted, conn)
        except (KeyError, ValueError):
            pass
        return not (conn['closing'] and not conn['out'])

    try:
        while True:
            for key, events in sel.select(timeout=WAKE):
                if key.data is None:
                    sock, peer = listener.accept()
                    if len(conns) >= MAX_CONN:
                        sock.close()
                        continue
                    sock.setblocking(False)
                    conn = {'sock': sock, 'peer': peer[0], 'buf': bytearray(),
                            'out': bytearray(), 'part': bytearray(), 'upgraded': False,
                            'closing': False, 'last': time.time()}
                    conns[sock] = conn
                    sel.register(sock, selectors.EVENT_READ, conn)
                    continue
                conn = key.data
                try:
                    alive = True
                    if events & selectors.EVENT_READ:
                        data = conn['sock'].recv(4096)
                        if not data:
                            alive = False
                        else:
                            conn['last'] = time.time()
                            conn['buf'] += data
                            alive = take(S, conn)
                    if alive:
                        alive = flush(conn)
                except (OSError, ValueError, UnicodeError) as error:
                    log(S, f'connection {conn["peer"]} dropped: {error!r}')
                    alive = False
                except Exception:
                    log(S, 'connection error:\n' + traceback.format_exc())
                    alive = False
                if not alive:
                    drop(conn)
            now = time.time()
            for conn in [c for c in conns.values() if now - c['last'] > IDLE]:
                drop(conn)
    finally:
        for conn in list(conns.values()):
            drop(conn)
        sel.close()


def bind(port):
    """The listening socket on 127.0.0.1:port, exclusively; None if it is taken."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        sock.bind((HOST, port))
        sock.listen(8)
        return sock
    except OSError:
        sock.close()
        return None


def lower_priority():
    if os.name == 'nt':
        try:
            import ctypes
            ctypes.windll.kernel32.SetPriorityClass(
                ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)     # below normal
        except Exception:
            pass


def run(port, roots_file, log_file, pid_file, by='foreground'):
    """The server itself. Exit code 3 if the port is taken (one is running). by is who asked
    for it (start() says), and goes in the log."""
    listener = bind(port)
    if listener is None:
        return 3
    S = {'port': port, 'roots_file': roots_file, 'roots_stamp': None, 'roots_list': [],
         'log': log_file,
         'config_file': os.path.splitext(roots_file)[0] + '.config'}
    lower_priority()
    with open(pid_file, 'w') as f:
        f.write(str(os.getpid()))
    atexit.register(lambda: os.path.isfile(pid_file) and os.remove(pid_file))
    log(S, f'started, pid {os.getpid()}, port {port}, by {by}')
    while True:
        try:
            serve(S, listener)
        except KeyboardInterrupt:
            log(S, 'stopped')
            return 0
        except Exception:
            log(S, 'the loop failed, restarting in 3 s:\n' + traceback.format_exc())
            time.sleep(3)


# ---- starting, stopping, checking -----------------------------------------------------------
def running(port=PORT):
    """'ours' if our server answers on the port, 'other' if something else does, else None."""
    try:
        sock = socket.create_connection((HOST, port), timeout=0.7)
    except OSError:
        return None
    try:
        sock.settimeout(0.7)
        sock.sendall((f'GET / HTTP/1.1\r\nHost: {HOST}:{port}\r\nUpgrade: websocket\r\n'
                      'Connection: Upgrade\r\nSec-WebSocket-Version: 13\r\n'
                      'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n\r\n').encode())
        answer = sock.recv(512)
        return 'ours' if b'Server: reportserver/' in answer else 'other'
    except OSError:
        return 'other'
    finally:
        sock.close()


def files():
    """(roots file, log file, pid file): in the folder reportserver/ beside this file, which is
    made when it is missing (the config file is beside the roots file)."""
    folder = os.path.join(HERE, 'reportserver')
    os.makedirs(folder, exist_ok=True)
    return tuple(os.path.join(folder, 'reportserver.' + kind) for kind in ('roots', 'log', 'pid'))


def check_by(by):
    """The label of who asked, or ValueError: see BY."""
    if not isinstance(by, str) or not BY.match(by):
        raise ValueError(f'reportserver: by must be 1 to 60 of letters, digits, space and '
                         f'. _ - : ; (got {by!r})')
    return by


def start(by, port=PORT, roots_file=None, log_file=None, pid_file=None):
    """Start the daemon unless one is running. by is who asks (the log keeps it). Returns one
    line saying what happened."""
    check_by(by)
    state = running(port)
    if state == 'ours':
        return 'report server: running'
    if state == 'other':
        return f'report server: port {port} is used by another program; not started'
    default = files()
    args = [os.path.abspath(__file__), '--port', str(port), '--roots', roots_file or default[0],
            '--log', log_file or default[1], '--pid', pid_file or default[2], '--by', by]
    exe = sys.executable
    if os.name == 'nt':
        windowless = os.path.join(os.path.dirname(exe), 'pythonw.exe')
        flags = 0x00000008 | 0x00000200 | 0x08000000 | 0x00004000    # detached, own group,
        exe = windowless if os.path.isfile(windowless) else exe        # no window, low priority
    else:
        flags = 0
    try:
        proc = subprocess.Popen([exe] + args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, creationflags=flags, close_fds=True)
    except OSError as error:
        return f'report server: could not start ({error})'
    for _ in range(20):
        time.sleep(0.1)
        if running(port) == 'ours':
            return f'report server: started (pid {proc.pid})'
    return 'report server: started, but not answering yet (see reportserver.log)'


def stop(by, pid_file=None, port=PORT, log_file=None):
    """Stop the daemon named in the pid file. by is who asks: the log says so before the
    server goes, since Windows ends it at once and it cannot log its own death. Returns one
    line."""
    check_by(by)
    pid_file = pid_file or files()[2]
    try:
        with open(pid_file) as f:
            pid = int(f.read().strip())
    except (OSError, ValueError):
        return 'report server: no pid file, nothing to stop'
    if running(port) != 'ours':
        os.remove(pid_file)
        return 'report server: not running (stale pid file removed)'
    log({'log': log_file or files()[1]}, f'stop requested by {by}, pid {pid}')
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as error:
        return f'report server: could not stop pid {pid} ({error})'
    return f'report server: stopped (pid {pid})'


def register(folder, roots_file=None):
    """Add a folder to the list the server may read. True if it was not there."""
    roots_file = roots_file or files()[0]
    folder = os.path.abspath(folder)
    known = []
    if os.path.isfile(roots_file):
        with open(roots_file, encoding='utf-8') as f:
            known = [line.strip() for line in f if line.strip()]
    if folder in known:
        return False
    with open(roots_file, 'a', encoding='utf-8') as f:
        f.write(folder + '\n')
    return True


def bat_path():
    """The bat a person meets the server through: .claude/vscripts/reportserver.bat in the
    first folder up from here that has it; '' when there is none."""
    here = HERE
    while True:
        path = os.path.join(here, '.claude', 'vscripts', 'reportserver.bat')
        if os.path.isfile(path):
            return path
        if os.path.dirname(here) == here:
            return ''
        here = os.path.dirname(here)


def prepare(folder, roots_file=None):
    """Register the folder; the path of the bat, for a page to show when the server is down."""
    register(folder, roots_file)
    return bat_path()


def status(port=PORT, roots_file=None, log_file=None, pid_file=None):
    """How the server is: {state, pid, since, port, roots, last}. state is 'ours', 'other' or
    None (see running); pid and since (epoch seconds) come from the pid file, which the server
    writes when it starts, so they are None when there is none; roots counts the registered
    folders; last is the last line of the log ('' when there is none)."""
    default = files()
    roots_file, log_file = roots_file or default[0], log_file or default[1]
    pid_file = pid_file or default[2]
    pid = since = None
    try:
        with open(pid_file) as f:
            pid = int(f.read().strip())
        since = os.path.getmtime(pid_file)
    except (OSError, ValueError):
        pass
    try:
        with open(roots_file, encoding='utf-8') as f:
            roots = sum(1 for line in f if line.strip())
    except OSError:
        roots = 0
    last = ''
    try:
        with open(log_file, 'rb') as f:
            f.seek(max(0, os.path.getsize(log_file) - 2000))
            lines = f.read().decode('utf-8', 'replace').splitlines()
        last = next((x for x in reversed(lines) if x.strip()), '')
    except OSError:
        pass
    return {'state': running(port), 'pid': pid, 'since': since, 'port': port, 'roots': roots,
            'last': last}


def ensure(by, port=PORT, roots_file=None, log_file=None, pid_file=None, visible=True):
    """What a program calls when it needs the server. Nothing happens if it runs. Else, with
    the default port and files and a bat to open, the bat is opened for a person to see
    (visible) or run with no window at all (not visible); the bat starts the daemon. Any other
    port or files (a test) start the daemon itself. Returns one line, as start() does."""
    check_by(by)
    if running(port) == 'ours':
        return 'report server: running'
    bat = bat_path()
    default = files()
    ours = (port == PORT and roots_file in (None, default[0]) and log_file in (None, default[1])
            and pid_file in (None, default[2]))
    if not bat or not ours or os.name != 'nt':
        return start(by, port, roots_file, log_file, pid_file)
    if visible:
        os.startfile(bat, arguments=f'--by "{by}" --start')     # a window, like a double click
        for _ in range(50):
            time.sleep(0.2)
            if running(port) == 'ours':
                return 'report server: started in the bat window'
        return 'report server: the bat window was opened, not answering yet (see its window)'
    done = subprocess.run([bat, '--by', by, '--start', '--hidden'], capture_output=True,
                          text=True, creationflags=0x08000000, timeout=60)     # no window
    return (done.stdout.strip().splitlines() or ['report server: no answer'])[-1]


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    opts = {'--port': str(PORT)}
    default = files()
    opts.update({'--roots': default[0], '--log': default[1], '--pid': default[2], '--by': None})
    mode = 'run'
    folder = ''
    while args:
        word = args.pop(0)
        if word in ('--start', '--stop', '--status'):
            mode = word[2:]
        elif word == '--register' and args:
            mode, folder = 'register', args.pop(0)
        elif word in opts and args:
            opts[word] = args.pop(0)
        else:
            raise SystemExit(f'reportserver: unknown argument {word}')
    port = int(opts['--port'])
    by = opts['--by']
    if mode in ('start', 'stop') and by is None:
        raise SystemExit(f'reportserver: --{mode} needs --by NAME (who is asking)')
    if by is not None:
        try:
            check_by(by)
        except ValueError as error:
            raise SystemExit(str(error))
    if mode == 'start':
        print(start(by, port, opts['--roots'], opts['--log'], opts['--pid']))
        return 0
    if mode == 'stop':
        print(stop(by, opts['--pid'], port, opts['--log']))
        return 0
    if mode == 'register':
        if not os.path.isdir(folder):
            raise SystemExit(f'reportserver: no such folder {folder}')
        added = register(folder, opts['--roots'])
        print(f'report server: {"registered" if added else "already registered"} '
              f'{os.path.abspath(folder)}')
        return 0
    if mode == 'status':
        got = status(port, opts['--roots'], opts['--log'], opts['--pid'])
        got['state'] = got['state'] or 'none'
        for key, value in got.items():
            print(f'{key}={"" if value is None else value}')
        return 0
    return run(port, opts['--roots'], opts['--log'], opts['--pid'], by or 'foreground')


if __name__ == '__main__':
    raise SystemExit(main())
