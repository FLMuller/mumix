r"""wsserve.py -- a small websocket server for pages on this machine: one process, no threads,
asleep in a selector until a byte arrives. It speaks only to 127.0.0.1 and gives one reply to
each text message the page sends. What the reply says is the caller's: a function.

    from wsserve import bind, serve, probe
    listener = bind(47652)                      # None if the port is taken
    serve(listener, reply, 47652, 'vcserver', log)   # runs until an exception ends it
    probe(47652, 'vcserver')                    # 'ours', 'other' or None: is it up?

reply(text) -> str
    Called with the text of each message (a page sends JSON); returns the text to send back. An
    exception in reply is logged and drops that one connection, never the server.
log(text)
    Where the server writes what it refuses and what fails. Never raises.

What it checks, before reply is ever called
    The handshake must be a GET / upgrade with Host 127.0.0.1:PORT or localhost:PORT and an Origin
    that is absent, `null` (a page opened from a file) or this host: a page from a web site is
    refused with 403. Frames must be masked (the client's), without reserved bits, and at most
    MAX_MSG bytes; at most MAX_CONN connections at once; a silent connection is dropped after IDLE
    seconds. Replies up to MAX_REPLY bytes.

This is the design of reportserver.py (which keeps its own copy of it, tied to its report series)
with the handler passed in, so that another server need not copy the loop.

VERSION  M1 m01.v01 (2026-11-01): first version, for vcomment.
"""
import base64
import hashlib
import selectors
import socket
import struct
import time
import traceback

__all__ = ['bind', 'serve', 'probe', 'frame', 'frames']

HOST = '127.0.0.1'
GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
MAX_MSG = 65536                     # bytes of one message from a page (a comment is text)
MAX_HEAD = 8192                     # bytes of the handshake
MAX_REPLY = 8 * 1024 * 1024
MAX_CONN = 8
IDLE = 120                          # seconds a connection may be silent
WAKE = 60                           # seconds the select sleeps at most


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


def probe(port, name):
    """'ours' if a server called `name` answers on the port, 'other' if something else does,
    else None. It sends a handshake and reads the Server header of the answer."""
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
        return 'ours' if f'Server: {name}/'.encode() in answer else 'other'
    except OSError:
        return 'other'
    finally:
        sock.close()


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
    port = S['port']
    ok = (lines[0].startswith('GET / ') and head.get('upgrade', '').lower() == 'websocket'
          and 'upgrade' in head.get('connection', '').lower() and 'sec-websocket-key' in head
          and head.get('sec-websocket-version') == '13'
          and head.get('host') in (f'{HOST}:{port}', f'localhost:{port}')
          and head.get('origin') in (None, 'null', f'http://{HOST}:{port}',
                                     f'http://localhost:{port}'))
    if not ok:
        S['log'](f'refused handshake from {conn["peer"]}: {lines[0][:60]!r} origin '
                 f'{head.get("origin")!r} host {head.get("host")!r}')
        conn['out'] += (f'HTTP/1.1 403 Forbidden\r\nServer: {S["name"]}/1\r\n'
                        'Content-Length: 0\r\nConnection: close\r\n\r\n').encode()
        conn['closing'] = True
        return True
    conn['out'] += ('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n'
                    f'Connection: Upgrade\r\nServer: {S["name"]}/1\r\n'
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
                answer = S['reply'](text).encode('utf-8')
                if len(answer) > MAX_REPLY:
                    answer = b'[]'
                conn['out'] += frame(answer)
        elif opcode != 10:
            raise ValueError('unsupported opcode')
    return True


def serve(listener, reply, port, name, log):
    """Sleep in the selector and serve what comes, until an exception ends it."""
    S = {'port': port, 'name': name, 'reply': reply, 'log': log}
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
                        data = conn['sock'].recv(65536)
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
            for conn in [c for c in conns.values() if now - c['last'] > IDLE]:
                drop(conn)
    finally:
        for conn in list(conns.values()):
            drop(conn)
        sel.close()
