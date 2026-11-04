r"""b_rs3.py -- tests and benchmarks for rs3, the report server's third build (pages of blocks).
Black box: the suite imports rs3 (which starts the server if it is not running), calls contactRS,
fetches pages with plain HTTP, and talks to the port as a page does (a websocket client that
sends an Origin). Nothing reaches under the bonnet. The signals between the blocks are played by
the pages' own selftest (add ?selftest=1 to a page's address; the title then holds the result).

Run from the project root:
    python tools/runbench.py b_rs3
"""
import ast
import atexit
import base64
import http.client
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import threading
import time
import urllib.parse


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

    def test_T5b_a_page_of_paths_has_an_address_that_makes_it_again_with_nothing_kept(self):
        layout = '[ftv wdxh, [toptabs ; [methods wdxh, [code ; edit wxhd]]]]'
        blocks = {'ftv': ['ftv'], 'toptabs': ['toptabs', './mumix/tools/primary/rs3.py', './mumix/tests/b_rs3.py'],
                  'methods': ['methods'], 'code': ['code'], 'edit': ['editbox']}
        got = rs3.contactRS('load', layout, blocks, '', False)
        self.assertTrue(got['ok'], got)
        self.assertTrue(got['path'].startswith('/?layout='), got['path'])
        self.assertEqual(got['path'].count('toptabs='), 1)                             # all of a block's paths in one value
        self.assertIn('toptabs=mumix/{tools/primary/rs3.py,tests/b_rs3.py}', got['path'])   # the common folder once
        many = {'toptabs': ['toptabs', './mumix/tools/primary/rs3.py', './mumix/tools/primary/rs3comment.py', './mumix/tools/primary/rs3files.py',
                            './mumix/tests/b_rs3.py']}
        folded = rs3.contactRS('load', '[toptabs wxh]', many, '', False)['path']
        self.assertEqual(folded.count('toptabs='), 1)
        self.assertEqual(folded.count('tools/primary'), 1)                             # the folder, and the stem rs3, written once
        self.assertLess(len(folded), 160)                                              # (four paths of ~35 characters)
        again = web('GET', folded)[2]
        self.assertIn('data-open="[&quot;./mumix/tools/primary/rs3.py&quot;, &quot;./mumix/tools/primary/rs3comment.py&quot;, '
                      '&quot;./mumix/tools/primary/rs3files.py&quot;, &quot;./mumix/tests/b_rs3.py&quot;]"', again)   # the paths as they were
        odd = rs3.contactRS('load', '[toptabs wxh]', {'toptabs': ['toptabs', './mumix/a,b.py', './mumix/c.py']}, '', False)
        self.assertTrue(odd['path'].startswith('/page/'), odd['path'])               # a path with a comma has no address form
        self.assertIn('block.edit=editbox', got['path'])                              # a block not named like its locator
        status, head, text = web('GET', got['path'])
        self.assertEqual(status, 200)
        self.assertEqual(re.findall(r'data-loc="(\w+)"', text), ['ftv', 'toptabs', 'methods', 'code', 'edit', 'statusbar'])
        self.assertIn('data-open="[&quot;./mumix/tools/primary/rs3.py&quot;', text)    # its data arrived
        self.assertIn('<title>ftv + toptabs + methods + code + edit - rs3.py</title>', text)   # a title from the address
        self.assertEqual(web('GET', '/?layout=%5Bdoc')[0], 500)                    # a layout that does not parse
        self.assertEqual(web('GET', '/?title=x')[0], 500)                               # no layout
        self.assertTrue(rs3.contactRS('load', '[doc wxh', {}, '', False)['ok'] is False)
        html = rs3.contactRS('load', '[doc wxh]', {'doc': ['doc', '', '', '<p>x</p>']}, 't', False)
        self.assertTrue(html['path'].startswith('/page/'), html['path'])             # html is not for an address: a kept page

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

    def test_T8b_a_draggable_bar_is_between_two_panes_even_for_the_last_one(self):
        def order(layout):
            got = rs3.contactRS('load', layout, {}, 'bars', False)
            return re.findall(r'class="(drag [vh](?: before)?)"|data-loc="(\w+)"', web('GET', got['path'])[2])
        flat = lambda found: [a or b for a, b in found]
        self.assertEqual(flat(order('[doc wxh ; doc2 wxhd]'))[:3], ['doc', 'drag h before', 'doc2'])   # the last: bar before it
        self.assertEqual(flat(order('[doc wdxh, doc2 wxh]'))[:3], ['doc', 'drag v', 'doc2'])           # not last: bar after it

    def test_T8a_a_pane_with_no_width_number_takes_its_blocks_width(self):
        def cells(layout):
            got = rs3.contactRS('load', layout, {'doc': ['doc', '', '', '<p>x</p>'], 'ftv': ['ftv'],
                                                 'methods': ['methods'], 'editbox': ['editbox']}, 'w', False)
            self.assertTrue(got['ok'], got)
            text = web('GET', got['path'])[2]
            return dict(re.findall(r'data-loc="(\w+)" style="([^"]*)"', text))
        got = cells('[ftv wdxh, [doc wxh ; methods wxh]]')
        self.assertIn('flex:0 0 75mm', got['ftv'])                       # no number: the block's own 75 mm
        self.assertIn('flex:1 1 0', got['doc'])                          # a block with none of its own fills
        self.assertIn('flex:0 0 70mm', cells('[ftv 70dxh, [doc wxh]]')['ftv'])    # a number is the layout's
        self.assertIn('flex:0 0 30mm', cells('[ftv 30xh, [doc wxh]]')['ftv'])
        self.assertIn('flex:1 1 0', cells('[doc wxh ; ftv wxh]')['ftv'])         # in a column there is no width to give
        self.assertIn('flex:0 0 42mm', cells('[doc wxh ; editbox wxhd]')['editbox'])   # a block's own height, in a column
        self.assertIn('flex:0 0 35mm', cells('[doc wxh ; editbox wx35d]')['editbox'])  # a number is the layout's

    def test_T9_a_page_that_is_not_there_is_not_found_and_outside_paths_are_refused(self):
        self.assertEqual(web('GET', '/page/000000000000.html')[0], 404)
        self.assertEqual(web('GET', '/code/../etc/passwd')[0], 404)
        self.assertEqual(web('GET', '/code/mumix/results')[0], 404)      # not a file
        self.assertEqual(web('GET', '/')[0], 403)

    # ---- the monitor and the viewer ---------------------------------------------------------------
    def test_T10_the_monitor_page_has_its_blocks_and_the_status_bar(self):
        status, head, text = web('GET', '/reportserver')
        self.assertEqual(status, 200)
        found = re.findall(r'data-loc="(\w+)"', text)
        self.assertEqual(found, ['ftv', 'serverstatus', 'log', 'statusbar'])
        self.assertEqual((text.count('<style'), text.count('<script')), (1, 1))

    def test_T10a_a_path_that_starts_with_reportserver_is_the_monitor_page(self):
        for tail in ('/reportserver', '/?reportserver', '/?reportserver=1', '/?reportserver&anything=at_all',
                     '/reportserver%20?layout=[ftv]', '/reportserver/anything', '/reportserverX'):
            status, head, text = web('GET', tail)                          # one load, the page itself: no redirect
            self.assertEqual(status, 200, tail)
            self.assertNotIn('Location', head)
            self.assertEqual(re.findall(r'data-loc="(\w+)"', text), ['ftv', 'serverstatus', 'log', 'statusbar'], tail)
            self.assertIn('"address": "/reportserver"', text.replace('":"', '": "'), tail)     # the same page, the same address
        before = rs3.contactRS('status')['status']['monitors']
        page = FakePage('/?reportserver=whatever')
        try:
            self.assertEqual(rs3.contactRS('status')['status']['monitors'], before + 1)     # and it is the admin page
        finally:
            page.close()

    def test_T5h_a_report_file_is_a_doc_block_in_a_layout_of_its_own_with_the_status_bar(self):
        path = os.path.join(self.folder, 'rep.html')
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write('<html><head><title>t</title><style>.k{color:red}</style></head><body><p class="k">hello report</p>'
                    '<script>var z = 1;</script></body></html>')
        status, head, text = web('GET', '/?layout=[doc]&doc=' + rel_of(path)[2:])
        self.assertEqual(status, 200)
        self.assertEqual(re.findall(r'data-loc="(\w+)"', text), ['doc', 'statusbar'])    # the status bar the raw file had not
        self.assertIn('hello report', text)
        self.assertIn('.k{color:red}', text)
        self.assertEqual(text.count('<style'), 1)                                          # its style is collated with the page's
        self.assertNotIn('<title>t</title>', text)
        self.assertEqual(web('GET', '/?layout=[doc]&doc=' + self.rel[2:])[0], 500)          # not a page: a source file
        self.assertEqual(web('GET', '/?layout=[doc]&doc=../x.html')[0], 500)

    def test_T5c_an_address_leaves_out_the_sizes_the_blocks_have_of_their_own(self):
        full = '[ftv wdxh, [toptabs ; [methods wdxh, [code ; editbox wxhd]]]]'
        got = rs3.contactRS('load', full, {'toptabs': ['toptabs', './mumix/tools/primary/rs3.py'], 'editbox': ['editbox']}, '', False)
        self.assertTrue(got['ok'], got)
        url = urllib.parse.unquote(got['url'])
        self.assertIn('layout=[ftv,[toptabs;[methods,[code;editbox]]]]', url)       # no wdxh, wxhd, wxh
        self.assertNotIn('wxh', url.split('&')[0])
        text = web('GET', got['path'])[2]
        again = web('GET', rs3.contactRS('load', '[ftv, [toptabs ; [methods, [code ; editbox]]]]', {'toptabs': ['toptabs', './mumix/tools/primary/rs3.py'], 'editbox': ['editbox']}, '', False)['path'])[2]
        self.assertEqual(re.findall(r'class="drag[^"]*"|flex:[^;"]*;', text), re.findall(r'class="drag[^"]*"|flex:[^;"]*;', again))
        sized = rs3.contactRS('load', '[ftv 70dxh, [doc wxh ; doc2 wx30d]]', {'doc': ['doc', '', '', '<p>a</p>']}, '', False)
        self.assertTrue(sized['ok'], sized)                                              # (html data: a hash page, nothing to shorten)
        kept = rs3.contactRS('load', '[ftv 70dxh, [code ; editbox wx30d]]', {}, '', False)['url']
        self.assertIn('ftv_70dxh', kept)                                                # a size that is not the default stays
        self.assertIn('editbox_wx30d', kept)

    def test_T5g_the_paths_of_an_address_start_at_the_root_without_a_dot_slash(self):
        got = rs3.contactRS('load', '[toptabs ; code]', {'toptabs': ['toptabs', './mumix/tools/primary/rs3.py']}, '', False)
        self.assertIn('toptabs=mumix/tools/primary/rs3.py', got['path'])
        self.assertNotIn('./', got['path'])
        for written in ('mumix/tools/primary/rs3.py', './mumix/tools/primary/rs3.py'):    # either is read
            text = web('GET', f'/?layout=[toptabs;code]&toptabs={written}')[2]
            self.assertIn('data-open="[&quot;./mumix/tools/primary/rs3.py&quot;]"', text)
            text = web('GET', f'/?layout=[toptabs;code]&toptabs={written}')[2]
            self.assertIn('data-open="[&quot;./mumix/tools/primary/rs3.py&quot;]"', text)
        mixed = rs3.contactRS('load', '[toptabs ; code]', {'toptabs': ['toptabs', './mumix/a,b.py', './mumix/c.py']}, '', False)
        self.assertTrue(mixed['ok'], mixed)

    def test_T5d_a_wildcard_in_a_file_name_opens_the_files_it_matches_when_the_page_is_built(self):
        panes = './mumix/tools/primary/rs3/panes/'
        got = rs3.contactRS('load', '[toptabs ; code]', {'toptabs': ['toptabs', panes + 'pane_s*.js', panes + 'pane_toptabs.?s*']}, '', False)
        self.assertTrue(got['ok'], got)
        self.assertIn('pane_s*.js', urllib.parse.unquote(got['url']))                  # the address keeps the wildcard
        text = web('GET', got['path'])[2]
        shown = re.search(r'data-open="([^"]*)"', text).group(1).replace('&quot;', '"')
        opened = json.loads(shown)
        self.assertEqual(opened, [panes + 'pane_search.js', panes + 'pane_serverstatus.js', panes + 'pane_statusbar.js',
                                  panes + 'pane_toptabs.css', panes + 'pane_toptabs.js'])                          # by name; ? and * both work
        none = rs3.contactRS('load', '[toptabs ; code]', {'toptabs': ['toptabs', panes + 'no_such_*.xyz']}, '', False)
        self.assertEqual(json.loads(re.search(r'data-open="([^"]*)"', web('GET', none['path'])[2]).group(1).replace('&quot;', '"')), [])
        out = rs3.contactRS('load', '[toptabs ; code]', {'toptabs': ['toptabs', './mumix/../*.py', './mumix/tools/*/.git*']}, '', False)
        self.assertTrue(out['ok'], out)                                                # nothing outside the root, or hidden, is matched

    def test_T10c_every_page_has_the_seven_dot_ring_in_orange_on_nothing_as_its_icon(self):
        for address in ('/reportserver', '/code/' + self.rel[2:]):
            text = web('GET', address)[2]
            found = re.search(r'<link rel="icon" type="image/svg\+xml" href="(data:image/svg\+xml,[^"]+)"', text)
            self.assertTrue(found, address)
            svg = urllib.parse.unquote(found.group(1).split(',', 1)[1])
            self.assertEqual(svg.count('<circle'), 7)
            self.assertIn('#d35400', svg)                                              # the deep orange of the footer's line
            self.assertNotIn('opacity', svg)                                           # all seven the same
            self.assertNotIn('<rect', svg)                                             # no background: it is transparent

    def test_T5e_double_star_goes_down_through_the_folders_and_a_folder_name_may_have_a_wildcard(self):
        base = './mumix/tools/primary/rs3'

        def opened(*patterns):
            got = rs3.contactRS('load', '[toptabs ; code]', {'toptabs': ['toptabs', *patterns]}, '', False)
            self.assertTrue(got['ok'], got)
            shown = re.search(r'data-open="([^"]*)"', web('GET', got['path'])[2]).group(1).replace('&quot;', '"')
            return json.loads(shown)
        deep = opened(base + '/**/*.js')
        self.assertIn(base + '/html/manager.js', deep)                                  # a folder below
        self.assertIn(base + '/panes/pane_log.js', deep)
        self.assertNotIn(base + '/rs3core.py', deep)                                    # not a .js
        every = opened(base + '/**')
        self.assertIn(base + '/rs3core.py', every)                                      # a trailing ** is every file below
        self.assertIn(base + '/panes/pane_log.css', every)
        self.assertFalse([path for path in every if '__pycache__' in path or path.endswith('.pyc')])
        self.assertLess(every.index(base + '/rs3core.py'), every.index(base + '/panes/pane_log.css'))   # a folder's files, then its folders
        among = opened(base + '/pa*/pane_log.*')
        self.assertEqual(among, [base + '/panes/pane_log.css', base + '/panes/pane_log.js', base + '/panes/pane_log.py'])
        self.assertEqual(opened(base + '/*/../*.py'), [])                               # no .. in a pattern

    def test_T5f_braces_in_a_wildcard_pick_the_kinds_of_file(self):
        base = './mumix/tools/primary/rs3'
        got = rs3.contactRS('load', '[toptabs ; code]', {'toptabs': ['toptabs', base + '/**/*.{py,md}']}, '', False)
        self.assertTrue(got['ok'], got)
        self.assertIn('/?layout=', got['url'])                                             # an address, not a kept page
        shown = re.search(r'data-open="([^"]*)"', web('GET', got['path'])[2]).group(1).replace('&quot;', '"')
        opened = json.loads(shown)
        self.assertIn(base + '/rs3core.py', opened)
        self.assertIn(base + '/SIGNALS.md', opened)
        self.assertEqual({path.rsplit('.', 1)[1] for path in opened}, {'py', 'md'})

    def test_T10b_status_counts_the_report_server_pages_with_a_live_socket_so_the_menu_link_can_leave_the_page_as_it_is(self):
        before = rs3.contactRS('status')['status']['monitors']
        page = FakePage('/reportserver')
        try:
            self.assertEqual(rs3.contactRS('status')['status']['monitors'], before + 1)
        finally:
            page.close()
        deadline = time.time() + 3
        while rs3.contactRS('status')['status']['monitors'] != before and time.time() < deadline:
            time.sleep(0.1)
        self.assertEqual(rs3.contactRS('status')['status']['monitors'], before)
        text = web('GET', '/reportserver')[2]
        self.assertIn('href="/reportserver" target="_blank"', text)          # the menu link opens a new tab

    def test_T11_view_makes_a_viewer_page_for_one_file_and_refuses_others(self):
        got = rs3.contactRS('view', self.rel, False)
        self.assertTrue(got['ok'], got)
        text = web('GET', got['path'])[2]
        self.assertEqual(re.findall(r'data-loc="(\w+)"', text),
                         ['methods', 'code', 'editbox', 'statusbar'])
        self.assertIn(f'data-path="{self.rel}"', text)
        for bad in ('./no/such.py', '../x.py', 'C:/Windows/win.ini', './mumix/results'):
            self.assertFalse(rs3.contactRS('view', bad, False)['ok'], bad)

    def test_T11a_every_page_has_exactly_one_status_bar_with_search_settings_and_the_pulse(self):
        layouts = ['[doc wxh]', '[ftv 70dxh, [toptabs ; [methods wxh, [code ; editbox wxh]]]]',
                   '[doc wxh ; statusbar wx9]']                    # one that names its own keeps that one
        for layout in layouts:
            got = rs3.contactRS('load', layout, {'doc': ['doc', '', '', '<p>x</p>']}, 'bar', False)
            self.assertTrue(got['ok'], (layout, got))
            text = web('GET', got['path'])[2]
            self.assertEqual(text.count('class="sbar"'), 1, layout)
            self.assertIn('class="cfgbtn"', text)                  # the menu button of the settings
            self.assertIn('class="sfind"', text)                   # the find box
            self.assertIn('class="slive"', text)                   # the pulse
            self.assertEqual(re.findall(r'data-loc="(\w+)"', text)[-1], 'statusbar')
        viewer = rs3.contactRS('view', self.rel, False)['path']
        for path in ('/reportserver', viewer):
            self.assertEqual(web('GET', path)[2].count('class="sbar"'), 1, path)

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
            self.assertIn('Thing.method', names)
            self.assertIn('free', names)
            for outside in ('./../x.py', './no/such.py', 'sample.py'):
                self.assertFalse(page.ask({'do': 'open', 'hash': page.hash, 'path': outside})['ok'], outside)
        finally:
            page.close()

    def test_T13c_a_markdown_file_is_in_numbered_blocks_with_coloured_code_and_its_comments_between(self):
        path = os.path.join(self.folder, 'doc.md')
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write('# Title\n\ntext **bold**\n\n```python\ndef f(a):\n    return a\n\n```\n\n<!--###tst a comment-->\n\n'
                    '| a | b |\n|---|---|\n| 1 | 2 |\n')
        rel = rel_of(path)
        page = FakePage(rs3.contactRS('view', rel, False)['path'])
        try:
            got = page.ask({'do': 'open', 'hash': page.hash, 'path': rel})
            self.assertTrue(got['ok'], got)
            text = got['html']
            self.assertIn('<h1>Title</h1>', text)
            self.assertIn('<strong>bold</strong>', text)
            self.assertRegex(text, r'id="L1" data-n="1"')
            self.assertRegex(text, r'id="L5" data-n="5"')                   # the fenced block (a blank line inside it)
            self.assertIn('<span class="r-keyword">def</span>', text)       # its code, coloured by the python lang file
            self.assertIn('class="cm"', text)                               # the comment thread between the blocks
            self.assertRegex(text, r'id="L13" data-n="13"')                 # the table, after the comment
            self.assertIn('<span class="r-number">1</span></td>', text)    # the numbers of its text have the number colour
            self.assertIn('<td align="center"><span class="r-number">2</span></td>', text)    # a column of numbers is centred
            self.assertNotIn('<h1><span', text)                             # (a heading keeps its own look)
        finally:
            page.close()

    def test_T13f_a_column_of_numbers_is_centred_unless_an_alignment_is_written_and_the_rest_is_left(self):
        path = os.path.join(self.folder, 'align.md')
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write('| name | n | w | mixed | blank |\n|:--|---|--:|---|---|\n| a | 10 | 7 | 5 | 1.5 |\n| b | 20 | 8 | x | |\n')
        rel = rel_of(path)
        page = FakePage(rs3.contactRS('view', rel, False)['path'])
        try:
            text = page.ask({'do': 'open', 'hash': page.hash, 'path': rel})['html']
            self.assertIn('<th align="center">n</th>', text)                  # a column of numbers: header and cells centred
            self.assertIn('<td align="center"><span class="r-number">10</span></td>', text)
            self.assertIn('<td align="right"><span class="r-number">7</span></td>', text)    # written --: kept
            self.assertIn('<td align="left">a</td>', text)                    # written :--: kept
            self.assertNotIn('align="center">x', text)                        # a column that is not all numbers: left
            self.assertNotIn('<th align="center">mixed', text)
            self.assertIn('<td align="center"><span class="r-number">1.5</span></td>', text)  # a blank cell does not count against
        finally:
            page.close()

    def test_T13d_yaml_front_matter_is_a_small_plain_block_and_not_a_heading(self):
        path = os.path.join(self.folder, 'front.md')
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write('---\nname: omem\ndescription: a long description of what it does\n---\n\n# Real heading\n\ntext\n')
        rel = rel_of(path)
        page = FakePage(rs3.contactRS('view', rel, False)['path'])
        try:
            text = page.ask({'do': 'open', 'hash': page.hash, 'path': rel})['html']
            self.assertIn('class="mdblock front"', text)
            self.assertIn('name: omem', text)
            self.assertNotIn('<h2>name', text)                              # (md2htm would make that a heading)
            self.assertIn('<h1>Real heading</h1>', text)
            self.assertRegex(text, r'id="L6" data-n="6"')                   # the heading, after the front matter
        finally:
            page.close()

    def test_T13e_every_heading_is_a_numbered_block_of_its_own(self):
        path = os.path.join(self.folder, 'heads.md')
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write('# One\ntext right under it\nmore text\n\n## Two\nbody\n')
        rel = rel_of(path)
        page = FakePage(rs3.contactRS('view', rel, False)['path'])
        try:
            text = page.ask({'do': 'open', 'hash': page.hash, 'path': rel})['html']
            for row in (1, 2, 5, 6):                                       # the headings (1, 5) and their text (2, 6)
                self.assertRegex(text, rf'id="L{row}" data-n="{row}"')
            self.assertNotRegex(text, r'id="L3" data-n="3"')               # the second text line shares row 2's block
        finally:
            page.close()

    def test_T5a_a_tab_strip_holds_the_sections_of_a_static_page_and_collates_their_style(self):
        sections = [['Summary', '<style>.sum{color:red}</style><p class="sum">all well</p>'], ['Failures', '<table><tr><td>x</td></tr></table>', True]]
        got = rs3.contactRS('load', '[toptabs wxh]', {'toptabs': ['toptabs', *sections]}, 'report', False)
        self.assertTrue(got['ok'], got)
        text = web('GET', got['path'])[2]
        self.assertEqual((text.count('<style'), text.count('<script')), (1, 1))      # still one of each
        self.assertIn('.sum{color:red}', text)                                       # the section's style, collated
        self.assertEqual(text.count('<template class="ttsec"'), 2)
        self.assertIn('data-title="Summary">', text)
        self.assertIn('data-title="Failures" data-bad="1">', text)                   # the red one
        self.assertIn('<p class="sum">all well</p>', text)
        self.assertNotIn('<style>.sum', text.split('<template', 1)[1])               # (taken out of the section itself)

    def test_T13a_a_markdown_file_is_shown_as_md2htm_formats_it_headings_and_tables(self):
        rel = './mumix/tools/primary/rs3/SIGNALS.md'
        page = FakePage(rs3.contactRS('view', rel, False)['path'])
        try:
            got = page.ask({'do': 'open', 'hash': page.hash, 'path': rel})
            self.assertTrue(got['ok'], got)
            self.assertIn('<table class="grid">', got['html'])        # md2htm's page: real tables ...
            self.assertRegex(got['html'], r'<h[12]>')                  # ... and headings
            self.assertIn('Signals added while', got['html'])
            self.assertNotIn('| ---', got['html'])                     # not the markup
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

    def test_T14a_a_comment_inside_a_docstring_is_refused_with_its_reason_and_nothing_is_written(self):
        path = os.path.join(self.folder, 'doc.py')
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write('"""head\nmore text\n"""\n\n\ndef f():\n    return 1\n')
        rel = rel_of(path)
        page = FakePage(rs3.contactRS('view', rel, False)['path'])
        try:
            base = page.ask({'do': 'open', 'hash': page.hash, 'path': rel})['base']
            got = page.ask({'do': 'insert', 'hash': page.hash, 'filename': rel, 'line': 2,
                            'base': base, 'tag': 'tst', 'text': 'inside'})
            self.assertFalse(got['ok'], got)
            self.assertRegex(got['error'], r'string|more than comments')
            with open(path, 'rb') as f:
                self.assertNotIn(b'###', f.read())
            ok = page.ask({'do': 'insert', 'hash': page.hash, 'filename': rel, 'line': 6,
                           'base': base, 'tag': 'tst', 'text': 'above the function'})
            self.assertTrue(ok['ok'], ok)                      # a comment between the code is fine
        finally:
            page.close()

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

    def test_T15a_rs3_imports_only_the_standard_library_and_its_own_folder(self):
        folder = os.path.join(ROOT, 'tools', 'primary', 'rs3')
        folders = [folder, os.path.join(folder, 'panes')]
        own = {os.path.splitext(n)[0] for f in folders for n in os.listdir(f) if n.endswith('.py')}
        files = [os.path.join(f, n) for f in folders for n in sorted(os.listdir(f)) if n.endswith('.py')]
        files.append(os.path.join(ROOT, 'tools', 'primary', 'rs3.py'))
        outside = []
        for path in files:
            with open(path, encoding='utf-8') as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                         else [node.module] if isinstance(node, ast.ImportFrom) and node.level == 0 else [])
                for name in names:
                    top = name.split('.')[0]
                    if top not in sys.stdlib_module_names and top not in own and top not in ('rs3', 'use'):   # use: tools/use.py loads rs3lex.pyx
                        outside.append((os.path.basename(path), name))
        self.assertEqual(outside, [])

    def test_T15b_each_blocks_signals_are_the_ones_its_script_handles_and_emits(self):
        folder = os.path.join(ROOT, 'tools', 'primary', 'rs3', 'panes')
        declared_in, declared_out, emitted_by_blocks = {}, {}, set()
        problems = []
        for name in sorted(os.listdir(folder)):
            if not (name.startswith('pane_') and name.endswith('.py')):
                continue
            block = name[5:-3]
            with open(os.path.join(folder, name), encoding='utf-8') as f:
                tree = ast.parse(f.read())
            lists = {t.id: [e.value for e in node.value.elts] for node in tree.body
                     if isinstance(node, ast.Assign) and isinstance(node.value, ast.List)
                     for t in node.targets if isinstance(t, ast.Name) and t.id in ('IN', 'OUT')}
            declared_in[block], declared_out[block] = set(lists.get('IN', [])), set(lists.get('OUT', []))
            js_path = os.path.join(folder, f'pane_{block}.js')
            text = ''
            if os.path.isfile(js_path):
                with open(js_path, encoding='utf-8') as f:
                    text = f.read()
            handled = {m[0].lower() + m[1:] for m in re.findall(r"\bon([A-Z]\w*)\b", text)}
            sent = set(re.findall(r"ctx\.emit\('(\w+)'", text))
            if 'RS.doors(' in text:
                sent.add('showpane')
            if block == 'toptabs':
                sent = set()                          # its code panes emit, with its number
            if handled != declared_in[block]:
                problems.append((block, 'IN', sorted(handled ^ declared_in[block])))
            if block != 'toptabs' and sent != declared_out[block]:
                problems.append((block, 'OUT', sorted(sent ^ declared_out[block])))
        manager_in = {'closemaintab', 'showpane', 'openfile', 'closefile', 'withlineno', 'withwrap', 'withconfig'}
        manager_out = {'status', 'log', 'newtabopened', 'closingmaintab', 'busy'}
        every_in = set().union(*declared_in.values()) | manager_in
        every_out = set().union(*declared_out.values()) | manager_out
        gaps = {'newtabopened', 'closingmaintab', 'closemaintab'}     # SIGNALS.md: no receiver yet, no sender yet
        problems += [('no receiver', sorted(every_out - every_in - gaps)),
                     ('no sender', sorted(every_in - every_out - gaps))]
        self.assertEqual([p for p in problems if p[-1]], [])

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
    def test_T99_restart_gives_a_new_boot_and_the_port_answers_again_and_a_loaded_page_survives_it(self):
        made = rs3.contactRS('load', '[doc wxh]', {'doc': ['doc', '', '', '<p>it survives</p>']}, 'a survivor', False)
        self.assertTrue(made['ok'], made)
        was = rs3.contactRS('ping')['boot']
        self.assertTrue(rs3.contactRS('restart')['ok'])
        end = time.time() + 15
        now = was
        while time.time() < end and now == was:
            time.sleep(0.3)
            got = rs3.contactRS('ping', timeout=1.0)
            now = got.get('boot', was) if got.get('ok') else was
        self.assertNotEqual(now, was)
        status, head, text = web('GET', made['path'])                  # the new server builds the page again from its kept spec
        self.assertEqual(status, 200)
        self.assertIn('it survives', text)
        self.assertIn('a survivor', text)

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
