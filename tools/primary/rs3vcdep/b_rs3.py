r"""b_rs3.py -- tests and benchmarks for rs3, the report server's third build (pages of blocks).
Black box: the suite imports rs3 (which starts the server if it is not running), calls contactRS,
fetches pages with plain HTTP, and talks to the port as a page does (a websocket client that
sends an Origin). Nothing reaches under the bonnet. The signals between the blocks are played by
the pages' own selftest (add ?selftest=1 to a page's address; the title then holds the result).

Run from the project root:
    python tools/runbench.py b_rs3
"""
import atexit
import base64
import http.client
import json
import os
import re
import shutil
import socket
import struct
import sys
import threading
import time


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

SOURCES = ['rs3']
import rs3                          # starts the server if nothing answers

PORT = rs3.PORT
CLAUDE = os.path.dirname(ROOT)      # the folder that holds .claude and mumix


def rel_of(path):
    """The ./ path from the root of the server of a file."""
    return './' + os.path.relpath(os.path.abspath(path), CLAUDE).replace(os.sep, '/')


def web(method, path, body=None, headers=None):
    """(status, headers, body) of one plain request to the server."""
    conn = http.client.HTTPConnection('127.0.0.1', PORT, timeout=5)
    try:
        conn.request(method, path, body=body, headers=headers or {})
        got = conn.getresponse()
        return got.status, dict(got.getheaders()), got.read().decode('utf-8', 'replace')
    finally:
        conn.close()


class FakePage:
    """A page as the server sees it: a websocket client that sends an Origin, as a browser does.
    ask(obj) sends a message and returns the one reply. url is the address it says hello with."""

    def __init__(me, url=None):
        me.buf = bytearray()
        me.sock = socket.create_connection(('127.0.0.1', PORT), timeout=5)
        key = base64.b64encode(os.urandom(16)).decode()
        me.sock.sendall((f'GET / HTTP/1.1\r\nHost: 127.0.0.1:{PORT}\r\n'
                         f'Origin: http://127.0.0.1:{PORT}\r\nUpgrade: websocket\r\n'
                         f'Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n'
                         'Sec-WebSocket-Version: 13\r\n\r\n').encode())
        head = b''
        while b'\r\n\r\n' not in head:
            head += me.sock.recv(4096)
        head, _, rest = head.partition(b'\r\n\r\n')
        assert head.startswith(b'HTTP/1.1 101'), head
        me.buf += rest
        me.hello = me.ask({'do': 'hello', 'url': url}) if url else None
        me.hash = me.hello['hash'] if me.hello and me.hello.get('ok') else None

    def ask(me, obj):
        payload = json.dumps(obj).encode('utf-8')
        mask = os.urandom(4)
        n = len(payload)
        head = bytes([0x81, 0x80 | n]) if n < 126 else bytes([0x81, 0x80 | 126]) + struct.pack('>H', n)
        me.sock.sendall(head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))
        return me.read()

    def read(me):
        end = time.time() + 5
        while time.time() < end:
            buf = me.buf
            if len(buf) >= 2:
                n, at = buf[1] & 0x7F, 2
                if n == 126 and len(buf) >= 4:
                    n, at = struct.unpack('>H', bytes(buf[2:4]))[0], 4
                elif n == 127 and len(buf) >= 10:
                    n, at = struct.unpack('>Q', bytes(buf[2:10]))[0], 10
                if n < 126 or at > 2:
                    if len(buf) >= at + n:
                        data = bytes(buf[at:at + n])
                        del buf[:at + n]
                        return json.loads(data.decode('utf-8'))
            me.sock.settimeout(0.5)
            try:
                chunk = me.sock.recv(65536)
            except socket.timeout:
                continue
            if not chunk:
                break
            me.buf += chunk
        return {'ok': False, 'error': 'nothing came'}

    def close(me):
        me.sock.close()


class b_rs3(bench):
    BenchName = 'rs3'
    BenchVersion = 'M1.0.0'          # runbench adds 1 to the last number on every run
    BenchHeader = 'the third report server: pages of blocks, through contactRS, HTTP and a page'
    sources = SOURCES

    @classmethod
    def setUpClass(cls):
        super().setUpClass() if hasattr(super(), 'setUpClass') else None
        cls.folder = os.path.join(ROOT, 'tests', 'z_sandbox', 'rs3tmp')
        os.makedirs(cls.folder, exist_ok=True)
        atexit.register(shutil.rmtree, cls.folder, True)
        cls.sample = os.path.join(cls.folder, 'sample.py')
        with open(cls.sample, 'w', encoding='utf-8', newline='') as f:
            f.write('"""sample."""\n\n\nclass Thing:\n    def method(self):\n        return 1\n\n\n'
                    'def free():\n    return 2\n')
        cls.rel = rel_of(cls.sample)

    # ---- the server -----------------------------------------------------------------------------
    def test_T1_ping_gives_the_boot_and_the_time(self):
        got = rs3.contactRS('ping')
        self.assertEqual((got['ok'], got['pong']), (True, 1))
        self.assertRegex(got['boot'], r'^\d+-\d+$')
        self.assertLess(abs(got['time'] - time.time()), 5)

    def test_T2_config_changes_are_kept_and_bad_values_refused(self):
        was = rs3.contactRS('config')['config']['size']
        try:
            self.assertEqual(rs3.contactRS('config', {'size': 17})['config']['size'], 17)
        finally:
            rs3.contactRS('config', {'size': was})
        got = rs3.contactRS('config', {'size': 3})
        self.assertFalse(got['ok'])
        self.assertEqual(rs3.contactRS('config')['config']['size'], was)

    def test_T3_an_unknown_verb_is_refused_in_the_same_shape(self):
        got = rs3.contactRS('nosuchverb', 1)
        self.assertFalse(got['ok'])
        self.assertIn('unknown verb', got['error'])

    # ---- pages made of blocks ---------------------------------------------------------------------
    def test_T4_load_refuses_a_bad_layout_and_a_block_that_does_not_exist(self):
        for layout, blocks, word in (('[doc wxh', {}, 'layout'), ('[doc wxh ; doc wxh]', {}, 'twice'),
                                     ('[nosuch wxh]', {}, 'no block'),
                                     ('[doc wxh, doc2 wxh ; doc3 wxh]', {}, 'both')):
            got = rs3.contactRS('load', layout, blocks, 't', False)
            self.assertFalse(got['ok'], layout)
            self.assertIn(word, got['error'])

    def test_T5_a_page_of_blocks_has_one_style_and_one_script_and_the_html_in_its_place(self):
        got = rs3.contactRS('load', '[doc wxh]', {'doc': ['doc', 'var x = 1;', '.k{color:red}',
                                                          '<p id="mine">hello</p>']}, 'a page', False)
        self.assertTrue(got['ok'], got)
        status, head, text = web('GET', got['path'])
        self.assertEqual(status, 200)
        self.assertEqual((text.count('<style'), text.count('<script')), (1, 1))
        self.assertIn('<p id="mine">hello</p>', text)
        self.assertIn('.k{color:red}', text)
        self.assertIn('aDOM', text)                               # the doc script has its own element
        self.assertNotIn('@@', text)

    def test_T6_a_static_page_given_whole_is_taken_apart_and_its_parts_collated(self):
        whole = '<html><style>.a{x:1}</style><div>one</div><script>alert(1)</script></html>'
        got = rs3.contactRS('load', '[doc wxh]', {'doc': ['doc', '', '', whole]}, 'whole', False)
        text = web('GET', got['path'])[2]
        self.assertEqual((text.count('<style'), text.count('<script')), (1, 1))
        self.assertIn('.a{x:1}', text)
        self.assertIn('<div>one</div>', text)

    def test_T7_two_blocks_of_one_kind_carry_their_css_and_script_once(self):
        got = rs3.contactRS('load', '[methods 40xh, methods2 wxh]', {}, 'two', False)
        self.assertTrue(got['ok'], got)
        text = web('GET', got['path'])[2]
        self.assertEqual(text.count('/* block:methods */'), 2)    # one in the css, one in the js
        self.assertEqual(text.count("RS.pane('methods'"), 1)
        self.assertEqual(len(re.findall(r'data-loc="methods2?"', text)), 2)

    def test_T8_the_layout_sizes_and_draggable_edges_are_in_the_page(self):
        got = rs3.contactRS('load', '[doc 40dxh, doc2 wx25]', {}, 'sizes', False)
        text = web('GET', got['path'])[2]
        self.assertIn('flex:0 0 40mm', text)
        self.assertIn('class="drag v"', text)
        self.assertIn('class="group row"', text)

    def test_T9_a_page_that_is_not_there_is_not_found_and_outside_paths_are_refused(self):
        self.assertEqual(web('GET', '/page/000000000000.html')[0], 404)
        self.assertEqual(web('GET', '/code/../etc/passwd')[0], 404)
        self.assertEqual(web('GET', '/code/mumix/results')[0], 404)      # not a file
        self.assertEqual(web('GET', '/')[0], 403)

    # ---- the monitor and the viewer ---------------------------------------------------------------
    def test_T10_the_monitor_page_has_its_five_blocks(self):
        status, head, text = web('GET', '/reportserver')
        self.assertEqual(status, 200)
        found = re.findall(r'data-loc="(\w+)"', text)
        self.assertEqual(found, ['options', 'search', 'ftv', 'serverstatus', 'log'])
        self.assertEqual((text.count('<style'), text.count('<script')), (1, 1))

    def test_T11_view_makes_a_viewer_page_for_one_file_and_refuses_others(self):
        got = rs3.contactRS('view', self.rel, False)
        self.assertTrue(got['ok'], got)
        text = web('GET', got['path'])[2]
        self.assertEqual(re.findall(r'data-loc="(\w+)"', text),
                         ['options', 'search', 'methods', 'code', 'editbox'])
        self.assertIn(f'data-path="{self.rel}"', text)
        for bad in ('./no/such.py', '../x.py', 'C:/Windows/win.ini', './mumix/results'):
            self.assertFalse(rs3.contactRS('view', bad, False)['ok'], bad)

    # ---- a page talks to the server ----------------------------------------------------------------
    def test_T12_hello_by_address_gives_the_same_hash_each_time_and_a_program_may_not_say_it(self):
        one, two = FakePage('/reportserver'), FakePage('/reportserver')
        try:
            self.assertTrue(one.hello['ok'])
            self.assertEqual(one.hello['hash'], two.hello['hash'])
            self.assertEqual(one.hello['boot'], rs3.contactRS('ping')['boot'])
            self.assertFalse(one.ask({'do': 'hello', 'url': '/nowhere'})['ok'])
        finally:
            one.close()
            two.close()
        self.assertFalse(rs3.contactRS('hello', None, None, '/reportserver')['ok'])

    def test_T13_open_gives_the_lines_and_methods_the_names_with_their_classes(self):
        page = FakePage(rs3.contactRS('view', self.rel, False)['path'])
        try:
            lines = page.ask({'do': 'open', 'hash': page.hash, 'path': self.rel})
            self.assertTrue(lines['ok'], lines)
            self.assertGreaterEqual(lines['html'].count('class="ln'), 8)
            self.assertRegex(lines['base'], r'^[0-9a-f]{40}$')
            got = page.ask({'do': 'methods', 'hash': page.hash, 'path': self.rel})
            self.assertTrue(got['ok'], got)
            names = [m['name'] for m in got['methods']]
            self.assertIn('Thing', names)
            self.assertIn('free', names)
            for outside in ('./../x.py', './no/such.py', 'sample.py'):
                self.assertFalse(page.ask({'do': 'open', 'hash': page.hash, 'path': outside})['ok'], outside)
        finally:
            page.close()

    def test_T14_a_comment_is_inserted_changed_and_removed_and_nothing_else_changes(self):
        page = FakePage(rs3.contactRS('view', self.rel, False)['path'])
        with open(self.sample, 'rb') as f:
            before = f.read()
        try:
            base = page.ask({'do': 'open', 'hash': page.hash, 'path': self.rel})['base']
            got = page.ask({'do': 'insert', 'hash': page.hash, 'filename': self.rel, 'line': 4,
                            'base': base, 'tag': 'tst', 'text': 'why a class?'})
            self.assertTrue(got['ok'], got)
            with open(self.sample, 'rb') as f:
                self.assertIn(b'###tst', f.read())
            stale = page.ask({'do': 'insert', 'hash': page.hash, 'filename': self.rel, 'line': 1,
                              'base': base, 'tag': 'tst', 'text': 'stale'})     # the file moved on
            self.assertFalse(stale['ok'])
            got = page.ask({'do': 'update', 'hash': page.hash, 'filename': self.rel, 'first': got['first'],
                            'last': got['last'], 'base': got['base'], 'tag': 'tst', 'text': ''})
            self.assertTrue(got['ok'] and got['removed'], got)
            with open(self.sample, 'rb') as f:
                self.assertEqual(f.read(), before)
        finally:
            page.close()
            with open(self.sample, 'wb') as f:
                f.write(before)

    def test_T15_tree_lists_text_files_only_as_paths_from_the_root(self):
        page = FakePage('/reportserver')
        try:
            got = page.ask({'do': 'tree', 'hash': page.hash})
            self.assertTrue(got['ok'], got)
            kinds = {f['k'] for f in got['files']}
            self.assertLessEqual(kinds, {'code', 'md', 'text', 'html'})
            self.assertTrue(all(f['p'].startswith('./') for f in got['files']))
            self.assertIn('./mumix/tools/primary/rs3.py', [f['p'] for f in got['files']])
        finally:
            page.close()

    def test_T16_pulse_gives_the_status_and_the_log_lines_after_a_row(self):
        page = FakePage('/reportserver')
        try:
            got = page.ask({'do': 'pulse', 'since': 0})
            self.assertTrue(got['ok'], got)
            self.assertEqual(got['status']['port'], PORT)
            self.assertEqual(got['boot'], rs3.contactRS('ping')['boot'])
            self.assertGreater(len(got['rows']), 0)
            last = got['rows'][-1][0]
            again = page.ask({'do': 'pulse', 'since': last})
            self.assertTrue(all(r[0] > last for r in again['rows']))
        finally:
            page.close()

    def test_T16a_a_refusal_and_a_verb_are_in_the_log(self):
        page = FakePage('/reportserver')
        try:
            before = page.ask({'do': 'pulse', 'since': 0})['rows'][-1][0]
            self.assertFalse(page.ask({'do': 'open', 'hash': 'nothere', 'path': './x.py'})['ok'])
            text = ' '.join(r[2] for r in page.ask({'do': 'pulse', 'since': before})['rows'])
            self.assertIn('verb open', text)
            self.assertIn('refused', text)
        finally:
            page.close()

    def test_T17_only_a_program_or_the_monitor_page_may_stop_the_server(self):
        viewer = FakePage(rs3.contactRS('view', self.rel, False)['path'])
        try:
            for verb in ('stop', 'restart'):
                got = viewer.ask({'do': verb})
                self.assertFalse(got['ok'], verb)
                self.assertIn('monitor', got['error'])
        finally:
            viewer.close()
        self.assertTrue(rs3.contactRS('ping')['ok'])

    # ---- the pages' own checks of their signals (the title of a page with ?selftest=1) -------------
    def test_T18_every_page_serves_its_selftest_when_asked(self):
        for path in ('/reportserver', '/code' + self.rel[1:]):
            text = web('GET', path + '?selftest=1')[2]
            self.assertIn('RS.selftest()', text)
            self.assertNotIn('RS.selftest()', web('GET', path)[2])

    # ---- restart last: it ends this server and a new one takes the port --------------------------------
    def test_T99_restart_gives_a_new_boot_and_the_port_answers_again(self):
        was = rs3.contactRS('ping')['boot']
        self.assertTrue(rs3.contactRS('restart')['ok'])
        end = time.time() + 15
        now = was
        while time.time() < end and now == was:
            time.sleep(0.3)
            got = rs3.contactRS('ping', timeout=1.0)
            now = got.get('boot', was) if got.get('ok') else was
        self.assertNotEqual(now, was)

    def bench_ping(self, timer):
        with timer as test:
            while test.more:
                for _ in test.count:
                    rs3.contactRS('ping')
        return 'contactRS ping (kept connection)', 'client'

    def bench_monitor_page(self, timer):
        with timer as test:
            while test.more:
                for _ in test.count:
                    web('GET', '/reportserver')
        return 'GET the monitor page (built each time)', 'client'
