r"""b_rs2.py -- tests and benchmarks for rs2, the report server's second build. Black box: the
suite only imports rs2 (which starts the server if it is not running) and calls contactRS, or
talks plain sockets to the port. Nothing reaches under the bonnet.

Run from the project root:
    python tools/runbench.py b_rs2
"""
import atexit
import base64
import hashlib
import http.client
import json
import os
import shutil
import socket
import struct
import sys
import tempfile
import threading
import time
from urllib.parse import quote


def hash_of(path):
    """The hash of a page: base64url of its full path and the time (the page's own formula)."""
    raw = f'{os.path.abspath(path)}|{int(time.time())}'.encode('utf-8')
    return base64.urlsafe_b64encode(raw).decode('ascii').rstrip('=')


def rel_of(path):
    """The ./ path of a file from the root of the server, the folder that holds mumix."""
    root = os.path.dirname(ROOT)
    return './' + os.path.relpath(os.path.abspath(path), root).replace(os.sep, '/')


def web(method, path, body=None, headers=None):
    """(status, headers, body) of one plain request to the server."""
    conn = http.client.HTTPConnection('127.0.0.1', rs2.PORT, timeout=5)
    try:
        conn.request(method, path, body=body, headers=headers or {})
        got = conn.getresponse()
        return got.status, dict(got.getheaders()), got.read()
    finally:
        conn.close()


class FakePage:
    """A page as the server sees it: a websocket client that sends an Origin, as a browser
    does. A reader thread keeps what it was sent in .seen, and answers each command with
    answer(msg), a dict, as {re: id, ...} (no answer for None, or when there is no answer)."""

    def __init__(me, answer=None, path=None):
        me.answer = answer
        me.seen = []
        me.buf = bytearray()
        me.sock = socket.create_connection(('127.0.0.1', rs2.PORT), timeout=5)
        key = base64.b64encode(os.urandom(16)).decode()
        me.sock.sendall((f'GET / HTTP/1.1\r\nHost: 127.0.0.1:{rs2.PORT}\r\n'
                         f'Origin: http://127.0.0.1:{rs2.PORT}\r\nUpgrade: websocket\r\n'
                         f'Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n'
                         'Sec-WebSocket-Version: 13\r\n\r\n').encode())
        head = b''
        while b'\r\n\r\n' not in head:
            head += me.sock.recv(4096)
        head, _, rest = head.partition(b'\r\n\r\n')
        assert head.startswith(b'HTTP/1.1 101'), head
        me.buf += rest
        me.sock.settimeout(0.1)
        me.alive = True
        me.thread = threading.Thread(target=me.loop, daemon=True)
        me.thread.start()
        me.hello = None
        if path is not None:                      # say which path this page shows
            me.send({'do': 'hello', 'path': path})
            me.hello = me.wait()

    def send(me, obj):
        payload = json.dumps(obj).encode('utf-8')
        mask = os.urandom(4)
        n = len(payload)
        head = bytes([0x81, 0x80 | n]) if n < 126 else bytes([0x81, 0x80 | 126]) + struct.pack('>H', n)
        me.sock.sendall(head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def frame(me):
        """The text of the next whole text frame in the buffer, or None."""
        buf = me.buf
        if len(buf) < 2:
            return None
        n, at = buf[1] & 0x7F, 2
        if n == 126:
            if len(buf) < 4:
                return None
            n, at = struct.unpack('>H', bytes(buf[2:4]))[0], 4
        if len(buf) < at + n:
            return None
        data = bytes(buf[at:at + n])
        del buf[:at + n]
        return data.decode('utf-8')

    def loop(me):
        while me.alive:
            text = me.frame()
            if text is None:
                try:
                    chunk = me.sock.recv(65536)
                except socket.timeout:
                    continue
                except OSError:
                    return
                if not chunk:
                    return
                me.buf += chunk
                continue
            msg = json.loads(text)
            me.seen.append(msg)
            if 'do' in msg and me.answer is not None:
                reply = me.answer(msg)
                if reply is not None:
                    me.send({'re': msg['id'], **reply})

    def wait(me, seconds=3):
        """The next message the server sent that is not a command."""
        end = time.time() + seconds
        while time.time() < end:
            for msg in me.seen:
                if 'do' not in msg:
                    me.seen.remove(msg)
                    return msg
            time.sleep(0.02)
        return {'ok': False, 'error': 'nothing came'}

    def close(me):
        me.alive = False
        me.sock.close()
        me.thread.join(1)


def findtools():                      # walk up to the folder that holds tools/
    from os.path import abspath, dirname, isdir, join
    here = dirname(abspath(__file__))
    while here != dirname(here) and not isdir(join(here, 'tools')):
        here = dirname(here)
    sys.path.insert(0, join(here, 'tools'))
    sys.path.insert(0, join(here, 'tools', 'primary'))
    return here


ROOT = findtools()
from bench import bench

SOURCES = ['rs2']
import rs2                          # starts the server if nothing answers


class b_rs2(bench):
    BenchName = 'rs2'
    BenchVersion = 'M1.0.9'          # runbench adds 1 to the last number on every run
    BenchHeader = 'the second report server, through contactRS only'
    sources = SOURCES

    def test_T1_ping_is_answered_with_the_boot_and_the_time(self):
        got = rs2.contactRS('ping')
        self.assertEqual((got['ok'], got['pong']), (True, 1))
        self.assertRegex(got['boot'], r'^\d+-\d+$')
        self.assertLess(abs(got['time'] - time.time()), 5)
        self.assertEqual(rs2.contactRS('ping')['boot'], got['boot'])      # the same server

    def test_T2_config_gives_the_shared_settings(self):
        got = rs2.contactRS('config')
        self.assertTrue(got['ok'])
        self.assertEqual(sorted(got['config']),
                         ['color', 'font', 'initials', 'linenos', 'size', 'tabwidth', 'wrap'])

    def test_T3_config_changes_and_is_remembered(self):
        was = rs2.contactRS('config')['config']['size']
        try:
            self.assertEqual(rs2.contactRS('config', {'size': 17})['config']['size'], 17)
            self.assertEqual(rs2.contactRS('config')['config']['size'], 17)
        finally:
            rs2.contactRS('config', {'size': was})
        self.assertEqual(rs2.contactRS('config')['config']['size'], was)

    def test_T4_config_refuses_a_value_that_is_not_allowed(self):
        was = rs2.contactRS('config')['config']
        got = rs2.contactRS('config', {'size': 3, 'font': 'Consolas'})
        self.assertFalse(got['ok'])
        self.assertIn('size', got['error'])
        self.assertEqual(rs2.contactRS('config')['config'], was)         # nothing was applied

    def test_T5_an_unknown_verb_is_refused_in_the_same_shape(self):
        got = rs2.contactRS('nosuchverb', 1, 2)
        self.assertFalse(got['ok'])
        self.assertIn('unknown verb', got['error'])

    def test_T6_contactRS_without_a_verb_says_so(self):
        got = rs2.contactRS()
        self.assertFalse(got['ok'])
        self.assertIn('verb', got['error'])

    def test_T7_a_request_for_no_page_is_refused_or_not_found(self):
        for path, want in ((b'/', b'403'), (b'/index.html', b'404')):    # the root; a missing page
            with socket.create_connection(('127.0.0.1', rs2.PORT), timeout=3) as sock:
                sock.sendall(b'GET %s HTTP/1.1\r\nHost: 127.0.0.1:%d\r\n\r\n' % (path, rs2.PORT))
                self.assertTrue(sock.recv(200).startswith(b'HTTP/1.1 ' + want), path)

    def test_T8_only_contactRS_is_public(self):
        self.assertEqual(rs2.__all__, ['contactRS'])

    # ---- files: GET, POST, tree, list (the fixtures sit inside the project, the server's root)
    @classmethod
    def setup_fixtures(cls):
        cls.folder = os.path.join(ROOT, 'results', 'rs2_t')
        shutil.rmtree(cls.folder, True)
        os.makedirs(cls.folder)
        atexit.register(shutil.rmtree, cls.folder, True)
        cls.page = os.path.join(cls.folder, 'rs2t_2026.11.03_10;00.html')
        cls.older = os.path.join(cls.folder, 'rs2t_2026.11.03_09;00.html')
        cls.note = os.path.join(cls.folder, 'notes.txt')
        for path, text in ((cls.page, '<html><body>page one</body></html>'),
                           (cls.older, '<html><body>page zero</body></html>'),
                           (cls.note, 'not a page')):
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
        cls.sample = os.path.join(cls.folder, 'sample.py')
        with open(cls.sample, 'w', encoding='utf-8', newline='\n') as f:
            f.write('import os\n\n\ndef f(x):\n    return x + 1\n')
        cls.outside = os.path.join(tempfile.mkdtemp(prefix='rs2out_'), 'x.html')
        with open(cls.outside, 'w', encoding='utf-8') as f:
            f.write('<html>outside</html>')
        atexit.register(shutil.rmtree, os.path.dirname(cls.outside), True)
        cls.rel = rel_of(cls.page)
        cls.rel_older = rel_of(cls.older)
        cls.sample_rel = rel_of(cls.sample)
        cls.hash = rs2.contactRS('load', cls.rel, False)['hash']      # False: open no browser
        rs2.contactRS('load', cls.rel_older, False)

    def url(self, path):
        """The address a page is served at: its ./ path without the ./ (a URL cannot hold it)."""
        return '/' + quote(rel_of(path)[2:], safe='/')

    def test_T9_get_serves_a_page(self):
        code, head, body = web('GET', self.url(self.page))
        self.assertEqual(code, 200)
        self.assertIn('text/html', head['Content-Type'])
        self.assertEqual(body, b'<html><body>page one</body></html>')

    def test_T10_get_refuses_what_is_not_a_page_of_the_project(self):
        refused = [self.url(self.note),                      # not an .html or .result file
                   '/' + os.path.abspath(self.outside).replace('\\', '/'),   # absolute, a drive
                   self.url(self.outside),                   # up out of the root
                   self.url(self.page).replace('/rs2_t/', '/rs2_t/../rs2_t/')]   # a dot segment
        for path in refused:
            self.assertEqual(web('GET', path)[0], 403, path)

    def test_T11_post_keeps_an_svg_beside_the_page(self):
        svg = b'<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>'
        code, _, body = web('POST', '/post/snap1.svg', svg, {'X-Rs-Token': self.hash})
        got = json.loads(body)
        self.assertEqual(code, 200)
        self.assertTrue(got['ok'])
        final = os.path.join(self.folder, '.rsposts', 'snap1.svg')
        self.assertEqual(got['path'], rel_of(final))
        with open(final, 'rb') as f:
            self.assertEqual(f.read(), svg)
        self.assertEqual([n for n in os.listdir(os.path.dirname(final)) if n.endswith('.tmp')], [])

    def test_T12_post_refuses_a_bad_token_name_body_or_script(self):
        svg = b'<svg xmlns="http://www.w3.org/2000/svg"/>'
        cases = [('/post/a.svg', svg, {'X-Rs-Token': 'nonsense'}, 403),
                 ('/post/a.svg', b'plain text', {'X-Rs-Token': self.hash}, 400),
                 ('/post/a.svg', b'<svg><script>1</script></svg>', {'X-Rs-Token': self.hash}, 400),
                 ('/post/a.html', svg, {'X-Rs-Token': self.hash}, 400)]
        for path, body, headers, want in cases:
            self.assertEqual(web('POST', path, body, headers)[0], want, (path, body))

    def test_T13_tree_lists_the_files_of_the_pages_project(self):
        got = rs2.contactRS('tree', self.hash, timeout=10)
        self.assertTrue(got['ok'], got)
        self.assertEqual((got['name'], got['root']), ('mumix', './mumix'))
        self.assertIn('./mumix/tools/bench.py', [f['p'] for f in got['files']])

    def test_T14_list_gives_the_other_reports_of_the_series(self):
        got = rs2.contactRS('list', self.hash)
        self.assertEqual(got['reports'], [{'file': os.path.basename(self.older),
                                           'when': '2026.11.03_09;00'}])

    def test_T15_an_oversize_body_and_another_method_are_refused(self):
        with socket.create_connection(('127.0.0.1', rs2.PORT), timeout=3) as sock:
            sock.sendall(b'POST /post/a.svg HTTP/1.1\r\nHost: 127.0.0.1:%d\r\n'
                         b'Content-Length: 9000000\r\n\r\n' % rs2.PORT)
            self.assertTrue(sock.recv(100).startswith(b'HTTP/1.1 413'))
        self.assertEqual(web('DELETE', '/')[0], 405)

    # ---- vcomment: open a file, and the comment round trip
    def test_T16_open_gives_the_tab_of_a_file_and_check_says_where_comments_may_go(self):
        got = rs2.contactRS('open', self.hash, self.sample_rel, 'sample', timeout=10)
        self.assertTrue(got['ok'], got)
        self.assertIn('id="L5"', got['html'])                    # the file has five lines
        self.assertIn('class="r-defname">f<', got['html'])       # f is coloured as a def name
        self.assertIn(f'data-path="{self.sample_rel}"', got['html'])   # ./ path, not absolute
        self.assertTrue(rs2.contactRS('check', self.hash, self.sample_rel)['ok'])
        for bad in (os.path.abspath(self.sample), '../../../x.py', './no/such.py'):
            self.assertFalse(rs2.contactRS('check', self.hash, bad)['ok'], bad)
            self.assertFalse(rs2.contactRS('open', self.hash, bad)['ok'], bad)

    def test_T17_a_comment_is_inserted_changed_and_removed(self):
        def fields(**more):
            with open(self.sample, 'rb') as f:
                base = hashlib.sha1(f.read()).hexdigest()
            return {'hash': self.hash, 'filename': self.sample_rel, 'base': base, 'tag': 'tst',
                    **more}

        def lines():
            with open(self.sample, encoding='utf-8') as f:
                return f.read().split('\n')

        original = lines()
        put = rs2.contactRS('insert', fields(line=2, text='a note'))
        self.assertTrue(put['ok'], put)
        self.assertEqual(lines()[1], '###tst a note')
        changed = rs2.contactRS('update', fields(first=put['first'], last=put['last'],
                                                 text='changed'))
        self.assertTrue(changed['ok'], changed)
        self.assertEqual(lines()[1], '###tst changed')
        gone = rs2.contactRS('update', fields(first=changed['first'], last=changed['last'],
                                              text=''))
        self.assertTrue(gone['ok'] and gone['removed'], gone)
        self.assertEqual(lines(), original)

    def test_T18_an_edit_from_an_old_copy_is_refused_and_writes_nothing(self):
        with open(self.sample, 'rb') as f:
            before = f.read()
        got = rs2.contactRS('insert', {'hash': self.hash, 'filename': self.sample_rel, 'line': 1,
                                       'base': '0' * 40, 'tag': 'tst', 'text': 'x'})
        self.assertFalse(got['ok'])
        with open(self.sample, 'rb') as f:
            self.assertEqual(f.read(), before)

    # ---- load, and commands carried to a page (a fake page stands in for the browser)
    def test_T19_load_answers_with_the_hash_and_an_address_that_serves_the_page(self):
        got = rs2.contactRS('load', self.rel, False)                # False: do not open a browser
        self.assertTrue(got['ok'], got)
        self.assertEqual(got['hash'], self.hash)                    # the same path, the same hash
        self.assertEqual(web('GET', got['url'].split(str(rs2.PORT), 1)[1])[0], 200)
        self.assertTrue(rs2.contactRS('list', got['hash'])['ok'])
        for bad in (os.path.abspath(self.page), './no/such.html', '../x.html'):
            self.assertFalse(rs2.contactRS('load', bad, False)['ok'], bad)   # only ./ paths in the root

    def test_T20_a_path_nothing_has_loaded_gives_none(self):
        got = 'x'
        for _ in range(20):                       # let an earlier test's page finish leaving
            got = rs2.contactRS('snap', self.rel, timeout=0.3)
            if got is None:
                break
            time.sleep(0.05)
        self.assertIsNone(got)
        self.assertIsNone(rs2.contactRS('trigger', self.rel, '#a'))
        self.assertIsNone(rs2.contactRS('snap', './no/such/page.result'))
        self.assertIsNone(rs2.contactRS('snap', '../outside.html'))

    def test_T21_snap_and_trigger_name_a_page_by_its_path_and_its_answer_comes_back(self):
        page = FakePage(lambda msg: {'file': 'x.svg', 'sel': msg['sel']} if msg['do'] == 'snap'
                        else {'text': 'pressed'}, self.rel)
        try:
            self.assertEqual(rs2.contactRS('snap', self.rel, '#a', timeout=5),
                             {'ok': True, 'file': 'x.svg', 'sel': '#a'})
            self.assertEqual(rs2.contactRS('trigger', self.rel, '#b', timeout=5),
                             {'ok': True, 'text': 'pressed'})
            self.assertEqual([(m['do'], m['to'], m['sel']) for m in page.seen],
                             [('snap', self.rel, '#a'), ('trigger', self.rel, '#b')])
        finally:
            page.close()

    def test_T22_a_command_goes_only_to_the_page_with_that_path(self):
        mine = FakePage(lambda msg: {'who': 'mine'}, self.rel)
        other = FakePage(lambda msg: {'who': 'other'}, self.rel_older)
        try:
            self.assertEqual(rs2.contactRS('snap', self.rel, timeout=5)['who'], 'mine')
            self.assertEqual(rs2.contactRS('snap', self.rel_older, timeout=5)['who'], 'other')
            self.assertEqual([m['do'] for m in mine.seen], ['snap'])
            self.assertEqual([m['do'] for m in other.seen], ['snap'])
        finally:
            mine.close()
            other.close()

    def test_T23_a_page_that_does_not_answer_gives_a_timeout_and_the_next_call_is_clean(self):
        silent = FakePage(lambda msg: None, self.rel)
        try:
            got = rs2.contactRS('snap', self.rel, None, timeout=0.5)
            self.assertEqual(got, {'ok': False, 'error': 'no answer in 0.5 s'})
        finally:
            silent.close()
        page = FakePage(lambda msg: {'file': 'y.svg'}, self.rel)
        try:
            self.assertEqual(rs2.contactRS('snap', self.rel, None, timeout=5)['file'], 'y.svg')
        finally:
            page.close()

    def test_T24_a_page_may_not_give_a_command_and_a_program_may_not_say_hello(self):
        page = FakePage(None, self.rel)
        try:
            page.send({'do': 'snap', 'to': self.rel})
            got = page.wait()
            self.assertFalse(got['ok'])
            self.assertIn('program', got['error'])
        finally:
            page.close()
        got = rs2.contactRS('hello', self.rel)
        self.assertFalse(got['ok'])
        self.assertIn('page', got['error'])

    def test_T25_hello_gives_the_boot_and_the_time_and_refuses_a_bad_path(self):
        page = FakePage(None, self.rel)
        try:
            self.assertEqual((page.hello['path'], page.hello['hash']), (self.rel, self.hash))
            self.assertEqual(page.hello['boot'], rs2.contactRS('ping')['boot'])
            for bad in ('../x.py', os.path.abspath(self.page), './no/such.html', './a/../b.py'):
                page.send({'do': 'hello', 'path': bad})
                self.assertFalse(page.wait()['ok'], bad)
        finally:
            page.close()

    def bench_ping(self, timer):
        with timer as test:
            while test.more:
                for _ in test.count:
                    rs2.contactRS('ping')
        return 'contactRS ping (kept connection)', 'client'
