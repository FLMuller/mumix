r"""rs2.py -- the report server, second build: one port, a closed set of handlers, one function.

    import rs2                                # starts the server, hidden, if nothing answers a ping
    rs2.contactRS('ping')                     # {'ok': True, 'pong': 1}
    rs2.contactRS('config')                   # the shared page settings
    rs2.contactRS('config', {'size': 14})     # change some of them; the reply holds them all

contactRS is the only public name (__all__). It opens a websocket to the server, sends one
message and returns the one reply, a dict. It never raises: a failure is
{'ok': False, 'error': ...}, and "no answer in 3 s" is one of them. The one other answer is
None: snap and trigger name a page by its path (contactRS('snap', './mumix/results/x.result'))
and None says no page has that path loaded. The server is started by the import itself, once:
every program that imports rs2 shares the one server.

The server (what the daemon runs)
    One process, no threads, asleep in a selector until a byte arrives. It binds PORT on
    127.0.0.1 exclusively, so a second copy exits at once with code 3. Every request must
    name this server as its Host, and send no Origin (a program) or this server's own (a page).
    Websocket: a message is JSON {"do": VERB, ...fields} and the reply is a JSON object with
    "ok". HTTP: GET and POST only, one request per connection (rsfiles has the routes).
    Every verb and route is run by a handler: rscore, rsfiles and rsvcomment, named in
    HANDLERS, in the folder rs2/ beside this file. Each defines VERBS = {verb: function} with
    function(msg, S) -> dict, and may define ROUTES = {'GET': function, 'POST': function} with
    function(request, S) -> (code, bytes, type); S is the server's state. There is no list on
    disk and no loader: a verb or route claimed by two handlers stops the server at start.
    A verb may return {'relay': payload}: the server then sends the payload to every page
    connection (one that sent an Origin) and replies when a page answers {re: id, ...}.

Speed: a new connection and its upgrade cost about 10 ms here, the question itself about 1 ms,
so contactRS keeps one connection per process and reuses it (the server drops a silent one
after 120 s: contactRS then makes a new one, once, and carries on). It is not for several
threads at once. It connects with a bare socket, not socket.create_connection, whose name
lookup (getaddrinfo) cost 8 ms a call here against 0.2 ms for the connect (measured 2026-11-03).

Command line     python rs2.py [--serve] | --start --by NAME | --stop --by NAME | --status
Files            rs2/rs2.log (about 100 KB, then rs2.log.old), rs2/rs2.pid, rs2/rs2.config
Port             47652 while reportserver.py still runs on 47651.

VERSION  M1 m02.v01 (2026-11-03): HTTP GET and POST, the route table, the relay of commands to
         pages, the kept connection of contactRS.
         M1 m01.v01 (2026-11-03): first version: the transport, the dispatcher, contactRS, ping
         and config. From reportserver.py: the websocket framing, the handshake and the loop.
"""
import atexit
import base64
import hashlib
import http
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

__all__ = ['contactRS']

PORT = 47652
HOST = '127.0.0.1'
HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.join(HERE, 'rs2')                  # the handlers, and the server's own files
LOG_FILE = os.path.join(FOLDER, 'rs2.log')
PID_FILE = os.path.join(FOLDER, 'rs2.pid')
CONFIG_FILE = os.path.join(FOLDER, 'rs2.config')
HANDLERS = ('rscore', 'rsfiles', 'rsvcomment')      # hard-wired: no list on disk, no loader
GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
MAX_MSG = 65536                     # bytes of one message to the server (a question is short)
MAX_HEAD = 8192                     # bytes of the handshake
MAX_REPLY = 8 * 1024 * 1024
MAX_BODY = 8 * 1024 * 1024          # bytes of one POST body
RELAY_WAIT = 30                     # seconds the server waits for a page to answer a command
MAX_CONN = 8
IDLE = 120                          # seconds a connection may be silent
WAKE = 60                           # seconds the select sleeps at most
LOG_MAX = 100 * 1024
BY = re.compile(r'^[A-Za-z0-9 _.;:\-]{1,60}$')      # who started it: safe in a log line
OWN = (f'{HOST}:{PORT}', f'localhost:{PORT}')                   # the Host a request must name
ORIGINS = (None, f'http://{HOST}:{PORT}', f'http://localhost:{PORT}')   # None: a program
# what each verb takes after its name, in order: contactRS('snap', to, sel) is {do, to, sel}
SHAPES = {'ping': (), 'config': ('change',), 'tree': ('hash',), 'list': ('hash',),
          'open': ('hash', 'path', 'label'), 'check': ('hash', 'filename'),
          'update': ('**',), 'insert': ('**',),     # ('**',): one dict of fields
          'load': ('path', 'show'), 'snap': ('to', 'sel'), 'trigger': ('to', 'sel')}


def fail(why):
    return {'ok': False, 'error': why}


# ---- the client: contactRS ------------------------------------------------------------------
def accept_key(key):
    return base64.b64encode(hashlib.sha1((key + GUID).encode()).digest()).decode()


def client_frame(payload):
    """A masked text frame: a client must mask what it sends."""
    n = len(payload)
    head = bytes([0x81])
    if n < 126:
        head += bytes([0x80 | n])
    elif n < 65536:
        head += bytes([0x80 | 126]) + struct.pack('>H', n)
    else:
        head += bytes([0x80 | 127]) + struct.pack('>Q', n)
    mask = os.urandom(4)
    return head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload))


def server_frame(buf):
    """Take one whole frame out of the bytearray buf: (opcode, payload), or None while more is
    to come. A server frame is never masked."""
    if len(buf) < 2:
        return None
    opcode = buf[0] & 0x0F
    n = buf[1] & 0x7F
    at = 2
    if n == 126:
        if len(buf) < 4:
            return None
        n = struct.unpack('>H', bytes(buf[2:4]))[0]
        at = 4
    elif n == 127:
        if len(buf) < 10:
            return None
        n = struct.unpack('>Q', bytes(buf[2:10]))[0]
        at = 10
    if n > MAX_REPLY:
        raise ValueError('the reply is too large')
    if len(buf) < at + n:
        return None
    payload = bytes(buf[at:at + n])
    del buf[:at + n]
    return opcode, payload


def client_handshake(sock, deadline):
    """Upgrade the connection; the bytes that came after the head, which belong to frames."""
    key = base64.b64encode(os.urandom(16)).decode()
    sock.sendall((f'GET / HTTP/1.1\r\nHost: {HOST}:{PORT}\r\nUpgrade: websocket\r\n'
                  f'Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n'
                  'Sec-WebSocket-Version: 13\r\n\r\n').encode())
    buf = bytearray()
    while b'\r\n\r\n' not in buf:
        sock.settimeout(max(0.05, deadline - time.time()))
        chunk = sock.recv(4096)
        if not chunk:
            raise ValueError('the server closed the connection')
        buf += chunk
        if len(buf) > MAX_HEAD:
            raise ValueError('the server sent a bad reply')
    head, _, rest = bytes(buf).partition(b'\r\n\r\n')
    if not head.startswith(b'HTTP/1.1 101') or accept_key(key).encode() not in head:
        raise ValueError('the server refused the connection')
    return bytearray(rest)


def client_read(sock, buf, deadline):
    """The text of the next text frame from the server."""
    while True:
        got = server_frame(buf)
        if got is None:
            sock.settimeout(max(0.05, deadline - time.time()))
            chunk = sock.recv(65536)
            if not chunk:
                raise ValueError('the server closed the connection')
            buf += chunk
            continue
        opcode, payload = got
        if opcode == 1:
            return payload.decode('utf-8')
        if opcode == 8:
            raise ValueError('the server closed the connection')


LINK = {'sock': None, 'buf': None}      # the one connection this process keeps to the server


def hang_up():
    """Drop the kept connection; the next question makes a new one."""
    sock = LINK['sock']
    LINK['sock'] = None
    LINK['buf'] = None
    if sock is not None:
        try:
            sock.close()
        except OSError:
            pass


def ask(msg, timeout):
    """One question and its answer (text) over the kept connection, made first if there is
    none. Raises OSError or ValueError: contactRS turns them into a reply."""
    deadline = time.time() + timeout
    if LINK['sock'] is None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        LINK['sock'] = sock                     # kept at once, so a failure below hangs it up
        sock.settimeout(timeout)
        sock.connect((HOST, PORT))              # not create_connection: see the header
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        LINK['buf'] = client_handshake(sock, deadline)
    sock = LINK['sock']
    sock.settimeout(max(0.05, deadline - time.time()))
    sock.sendall(client_frame(json.dumps(msg).encode('utf-8')))
    return client_read(sock, LINK['buf'], deadline)


def contactRS(*args, timeout=3.0):
    """Send one message to the report server and return its one reply as a dict. The first
    argument is the verb, the rest are that verb's fields (see SHAPES): contactRS('ping'),
    contactRS('config', {'size': 14}). Never raises: a failure is {'ok': False, 'error': ...}."""
    if not args or not isinstance(args[0], str):
        return fail('contactRS needs a verb, for example contactRS("ping")')
    fields = SHAPES.get(args[0])
    if fields == ('**',):
        if len(args) != 2 or not isinstance(args[1], dict):
            return fail(f'{args[0]} takes one dict of fields')
        msg = {**args[1], 'do': args[0]}
    elif fields is None:
        msg = {'do': args[0], 'args': list(args[1:])}
    elif len(args) - 1 > len(fields):
        return fail(f'{args[0]} takes {len(fields)} field(s) after its name: {", ".join(fields)}')
    else:
        msg = {'do': args[0], **dict(zip(fields, args[1:]))}
    for attempt in (0, 1):
        reused = LINK['sock'] is not None
        try:
            text = ask(msg, timeout)
            break
        except ConnectionRefusedError:
            hang_up()
            return fail('the report server is not running')
        except (TimeoutError, socket.timeout):
            hang_up()                       # a late reply must not answer the next question
            return fail(f'no answer in {timeout:g} s')
        except (OSError, ValueError, TypeError) as error:
            hang_up()
            if reused and attempt == 0:     # the kept connection had gone stale: once more, new
                continue
            return fail(str(error))
    try:
        got = json.loads(text)
    except ValueError:
        return fail('the reply was not json')
    if not isinstance(got, dict):
        return fail('the reply was not an object')
    return None if got.get('loaded') is False else got      # None: that page is not loaded


# ---- the log, the dispatcher ----------------------------------------------------------------
def log(text):
    try:
        if os.path.isfile(LOG_FILE) and os.path.getsize(LOG_FILE) > LOG_MAX:
            os.replace(LOG_FILE, LOG_FILE + '.old')
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(time.strftime('%Y-%m-%d %H:%M:%S ') + text.replace('\n', '\n    ') + '\n')
    except OSError:
        pass


def load_handlers(S):
    """Fill S['verbs'] from the handlers named in HANDLERS. Their folder is put on the path
    here, in the daemon only, so that importing rs2 as a client loads none of them. A verb
    claimed twice, or a handler that will not load, stops the server."""
    sys.path.insert(0, FOLDER)
    for name in HANDLERS:
        module = importlib.import_module(name)
        for verb, function in module.VERBS.items():
            if verb in S['verbs']:
                raise RuntimeError(f'the verb {verb} is claimed twice ({name})')
            S['verbs'][verb] = function
        for method, function in getattr(module, 'ROUTES', {}).items():
            if method in S['routes']:
                raise RuntimeError(f'the {method} route is claimed twice ({name})')
            S['routes'][method] = function


def pages_of(S):
    """The page connections: the upgraded ones that sent an Origin (a browser always does,
    a program never does)."""
    return [c for c in S['conns'].values() if c['upgraded'] and c['origin'] is not None]


def send(conn, reply):
    conn['out'] += frame(json.dumps(reply).encode('utf-8'))


def relay(S, conn, payload, key):
    """Pass a command on to the pages that said (hello) they show the page with hash `key`
    and wait for one to answer:
    the reply to conn is sent when a page answers {re: id, ...} (or when RELAY_WAIT passes),
    so there is nothing to send now (None). No such page is an answer at once, and
    contactRS turns it into None."""
    pages = [c for c in pages_of(S) if c['hash'] == key]
    if not pages:
        return {'ok': False, 'loaded': False}
    rid = f'r{S["next_rid"]}'
    S['next_rid'] += 1
    S['pending'][rid] = {'conn': conn, 'deadline': time.time() + RELAY_WAIT}
    for page in pages:
        send(page, {**payload, 'id': rid})
    return None


def answered(S, conn, msg):
    """A page's answer to a relayed command: {re: id, ...} goes to the program waiting."""
    waiting = S['pending'].get(msg.get('re'))
    if waiting is None or conn['origin'] is None:       # only a page answers, and only once
        return
    del S['pending'][msg['re']]
    send(waiting['conn'], {**{k: v for k, v in msg.items() if k != 're'}, 'ok': msg.get('ok', True)})


def answer(S, conn, text):
    """The reply, a dict, to one message, a str: the handler of its verb runs it. None when
    there is no reply now: a page's answer to a relayed command (passed on), or a command
    that was relayed (its reply comes when a page answers)."""
    try:
        msg = json.loads(text)
    except ValueError:
        return fail('not json')
    if not isinstance(msg, dict):
        return fail('not an object')
    if 're' in msg and 'do' not in msg:
        answered(S, conn, msg)
        return None
    verb = msg.get('do')
    function = S['verbs'].get(verb) if isinstance(verb, str) else None
    if function is None:
        return fail(f'unknown verb {verb!r}')
    S['conn'] = conn                                    # the sender, during this call only
    try:
        got = function(msg, S)
    except Exception:
        log(f'the verb {verb} failed:\n' + traceback.format_exc())
        return fail(f'the verb {verb} failed (see the log)')
    finally:
        S['conn'] = None
    if not isinstance(got, dict):
        return fail(f'the verb {verb} gave no reply')
    if 'relay' in got:
        return relay(S, conn, got['relay'], got.get('to_hash'))
    got.setdefault('ok', True)
    return got


# ---- websocket ------------------------------------------------------------------------------
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
        n = second & 0x7F
        at = 2
        if n == 126:
            if len(buf) < 4:
                break
            n = struct.unpack('>H', bytes(buf[2:4]))[0]
            at = 4
        elif n == 127:
            if len(buf) < 10:
                break
            n = struct.unpack('>Q', bytes(buf[2:10]))[0]
            at = 10
        if n > MAX_MSG:
            raise ValueError('frame too long')
        if len(buf) < at + 4 + n:
            break
        mask = buf[at:at + 4]
        data = bytes(b ^ mask[i % 4] for i, b in enumerate(buf[at + 4:at + 4 + n]))
        out.append((bool(first & 0x80), first & 0x0F, data))
        del buf[:at + 4 + n]
    return out


def read_head(conn):
    """The parsed head of the request in conn['buf'] once it is whole, else None. ValueError
    if it is too big, is not a request, repeats Content-Length or has a chunked body."""
    buf = conn['buf']
    end = buf.find(b'\r\n\r\n')
    if end < 0:
        if len(buf) > MAX_HEAD:
            raise ValueError('request head too large')
        return None
    lines = bytes(buf[:end]).decode('latin-1').split('\r\n')
    del buf[:end + 4]
    parts = lines[0].split(' ')
    if len(parts) != 3 or not parts[2].startswith('HTTP/'):
        raise ValueError('bad request line')
    headers = {}
    seen = {}
    for line in lines[1:]:
        key, colon, value = line.partition(':')
        if colon:
            name = key.strip().lower()
            headers[name] = value.strip()
            seen[name] = seen.get(name, 0) + 1
    if seen.get('content-length', 0) > 1 or 'transfer-encoding' in headers:
        raise ValueError('a repeated Content-Length or a chunked body is not taken')
    return {'method': parts[0], 'target': parts[1], 'headers': headers, 'line': lines[0]}


def reply(conn, code, data=b'', kind=None):
    """One HTTP response, then the connection closes: one request per connection."""
    head = f'HTTP/1.1 {code} {http.HTTPStatus(code).phrase}\r\nServer: rs2/1\r\n'
    if kind:
        head += f'Content-Type: {kind}\r\n'
    head += (f'Content-Length: {len(data)}\r\nCache-Control: no-store\r\n'
             'X-Content-Type-Options: nosniff\r\nConnection: close\r\n\r\n')
    conn['out'] += head.encode('latin-1') + data
    conn['closing'] = True


def upgrade(conn, head):
    """Answer a websocket upgrade; a request that is not a proper one is refused."""
    h = head['headers']
    ok = (head['line'].startswith('GET / ') and h.get('upgrade', '').lower() == 'websocket'
          and 'upgrade' in h.get('connection', '').lower() and 'sec-websocket-key' in h
          and h.get('sec-websocket-version') == '13')
    if not ok:
        reply(conn, 400)
        return
    conn['out'] += ('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n'
                    'Connection: Upgrade\r\nServer: rs2/1\r\n'
                    f'Sec-WebSocket-Accept: {accept_key(h["sec-websocket-key"])}\r\n\r\n'
                    ).encode()
    conn['upgraded'] = True
    conn['origin'] = h.get('origin')


def web(S, conn, head):
    """A plain request: GET or POST only, and the route table of the handlers answers it.
    A POST waits here until its whole body (at most MAX_BODY) has come."""
    method = head['method']
    if method not in ('GET', 'POST'):
        reply(conn, 405)
        return
    need = 0
    if method == 'POST':
        try:
            need = int(head['headers'].get('content-length', ''))
        except ValueError:
            reply(conn, 411)
            return
        if not 0 <= need <= MAX_BODY:
            reply(conn, 413)
            return
    if len(conn['buf']) < need:
        return
    body = bytes(conn['buf'][:need])
    path, _, query = head['target'].partition('?')
    request = {'method': method, 'path': path, 'query': query, 'headers': head['headers'],
               'body': body}
    route = S['routes'].get(method)
    try:
        got = route(request, S) if route else None
    except Exception:
        log(f'the {method} route failed:\n' + traceback.format_exc())
        got = (500, b'', None)
    reply(conn, *(got or (404, b'', None)))


def begin(S, conn, head):
    """A head has come: the checks every request passes, then a websocket or a web request.
    Only a program (no Origin) or this server's own pages (its own Origin) are let in."""
    h = head['headers']
    if h.get('host') not in OWN or h.get('origin') not in ORIGINS:
        log(f'refused {head["line"][:60]!r} from {conn["peer"]}: origin '
            f'{h.get("origin")!r} host {h.get("host")!r}')
        reply(conn, 403)
    elif 'websocket' in h.get('upgrade', '').lower():
        upgrade(conn, head)
    else:
        web(S, conn, head)


def take(S, conn):
    """What a connection has read: the head, then a web request or websocket frames. False
    to close it."""
    if not conn['upgraded']:
        if conn['closing']:
            conn['buf'].clear()                 # a reply is on its way: nothing more is read
            return True
        if conn['head'] is None:
            conn['head'] = read_head(conn)
            if conn['head'] is None:
                return True
        begin(S, conn, conn['head'])
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
                text = bytes(conn['part']).decode('utf-8', 'replace')
                conn['part'] = bytearray()
                got = answer(S, conn, text)
                if got is not None:
                    reply = json.dumps(got).encode('utf-8')
                    if len(reply) > MAX_REPLY:
                        reply = json.dumps(fail('the reply is too large')).encode('utf-8')
                    conn['out'] += frame(reply)
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

    S['conns'] = conns

    def drop(conn):
        conns.pop(conn['sock'], None)
        for rid in [r for r, w in S['pending'].items() if w['conn'] is conn]:
            del S['pending'][rid]                       # nobody is left to answer to
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

    def wake():
        """Sleep at most WAKE, or until the nearest relay deadline."""
        due = [w['deadline'] - time.time() for w in S['pending'].values()]
        return max(0.01, min([WAKE] + due))

    try:
        while True:
            for key, events in sel.select(timeout=wake()):
                if key.data is None:
                    sock, peer = listener.accept()
                    if len(conns) >= MAX_CONN:
                        sock.close()
                        continue
                    sock.setblocking(False)
                    conn = {'sock': sock, 'peer': peer[0], 'buf': bytearray(),
                            'out': bytearray(), 'part': bytearray(), 'upgraded': False,
                            'closing': False, 'head': None, 'origin': None, 'hash': None,
                            'last': time.time()}
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
                    log(f'connection {conn["peer"]} dropped: {error!r}')
                    alive = False
                except Exception:
                    log('connection error:\n' + traceback.format_exc())
                    alive = False
                if not alive:
                    drop(conn)
            now = time.time()
            for rid, waiting in list(S['pending'].items()):     # a command no page answered
                if now > waiting['deadline']:
                    del S['pending'][rid]
                    send(waiting['conn'], fail(f'no page answered in {RELAY_WAIT} s'))
            for other in list(conns.values()):          # replies queued for a connection
                if other['out'] and not flush(other):   # that was not the one just read
                    drop(other)
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


def claude_root():
    """The folder that holds .claude, found upward from this file: what pages are served from
    and what a page's hash may name."""
    here = HERE
    while not os.path.isdir(os.path.join(here, '.claude')):
        if os.path.dirname(here) == here:
            raise RuntimeError(f'no folder holding .claude above {HERE}')
        here = os.path.dirname(here)
    return here


def run(by):
    """The server itself. Exit code 3 if the port is taken (one is running), 4 if a handler
    will not load."""
    os.makedirs(FOLDER, exist_ok=True)
    listener = bind(PORT)
    if listener is None:
        return 3
    S = {'port': PORT, 'folder': FOLDER, 'config_file': CONFIG_FILE, 'verbs': {},
         'routes': {}, 'root': claude_root(), 'pages': {}, 'next_id': 1, 'pending': {},
         'next_rid': 1, 'conns': {}, 'conn': None, 'say': log,
         'boot': f'{os.getpid()}-{int(time.time())}'}       # which start this server is
    try:
        load_handlers(S)
    except Exception:
        log('a handler would not load, so the server did not start:\n'
            + traceback.format_exc())
        return 4
    lower_priority()
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    atexit.register(lambda: os.path.isfile(PID_FILE) and os.remove(PID_FILE))
    log(f'started, pid {os.getpid()}, port {PORT}, by {by}, verbs {sorted(S["verbs"])}')
    while True:
        try:
            serve(S, listener)
        except KeyboardInterrupt:
            log('stopped')
            return 0
        except Exception:
            log('the loop failed, restarting in 3 s:\n' + traceback.format_exc())
            time.sleep(3)


# ---- starting, stopping, checking -----------------------------------------------------------
def check_by(by):
    if not isinstance(by, str) or not BY.match(by):
        raise ValueError(f'by must be 1 to 60 of letters, digits, space and . _ - : ; '
                         f'(got {by!r})')
    return by


def start(by):
    """Start the daemon, hidden, unless one answers. One line saying what happened."""
    check_by(by)
    if contactRS('ping', timeout=1.0).get('ok'):
        return 'rs2: running'
    args = [os.path.abspath(__file__), '--serve', '--by', by]
    exe = sys.executable
    flags = 0
    if os.name == 'nt':
        windowless = os.path.join(os.path.dirname(exe), 'pythonw.exe')
        exe = windowless if os.path.isfile(windowless) else exe
        flags = 0x00000008 | 0x00000200 | 0x08000000 | 0x00004000   # detached, own group,
    try:                                                              # no window, low priority
        proc = subprocess.Popen([exe] + args, stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                creationflags=flags, close_fds=True)
    except OSError as error:
        return f'rs2: could not start ({error})'
    for _ in range(25):
        time.sleep(0.1)
        if contactRS('ping', timeout=1.0).get('ok'):
            return f'rs2: started (pid {proc.pid})'
    return 'rs2: started, but not answering yet (see rs2/rs2.log)'


def stop(by):
    """Stop the daemon named in the pid file; the log says who asked, before the server goes
    (Windows ends it at once). One line."""
    check_by(by)
    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
    except (OSError, ValueError):
        return 'rs2: no pid file, nothing to stop'
    if not contactRS('ping', timeout=1.0).get('ok'):
        os.remove(PID_FILE)
        return 'rs2: not running (stale pid file removed)'
    log(f'stop requested by {by}, pid {pid}')
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as error:
        return f'rs2: could not stop pid {pid} ({error})'
    return f'rs2: stopped (pid {pid})'


def status():
    """{running, pid, since, port}: pid and since (epoch seconds) from the pid file."""
    pid = since = None
    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        since = os.path.getmtime(PID_FILE)
    except (OSError, ValueError):
        pass
    return {'running': bool(contactRS('ping', timeout=1.0).get('ok')), 'pid': pid,
            'since': since, 'port': PORT}


def by_name():
    """Who is importing: the running program's name, the label the log keeps."""
    name = os.path.splitext(os.path.basename(sys.argv[0] or ''))[0]
    return name if BY.match(name) else 'python'


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    mode = 'serve'
    by = None
    while args:
        word = args.pop(0)
        if word in ('--serve', '--start', '--stop', '--status'):
            mode = word[2:]
        elif word == '--by' and args:
            by = args.pop(0)
        else:
            raise SystemExit(f'rs2: unknown argument {word}')
    if mode in ('start', 'stop') and by is None:
        raise SystemExit(f'rs2: --{mode} needs --by NAME (who is asking)')
    if by is not None:
        try:
            check_by(by)
        except ValueError as error:
            raise SystemExit(f'rs2: {error}')
    if mode == 'start':
        print(start(by))
        return 0
    if mode == 'stop':
        print(stop(by))
        return 0
    if mode == 'status':
        for key, value in status().items():
            print(f'{key}={"" if value is None else value}')
        return 0
    return run(by or 'foreground')


if __name__ == '__main__':
    raise SystemExit(main())
start(by_name())                    # importing starts the server, once: start() pings first
