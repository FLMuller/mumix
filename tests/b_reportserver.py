r"""b_reportserver.py -- tests and benchmarks for rs3, the report server's third build (pages of blocks).
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

SOURCES = ['reportserver']
import reportserver                          # starts the server if nothing answers
sys.path.insert(0, os.path.join(ROOT, 'tools', 'rs_primary'))
import rs3layout

PORT = reportserver.PORT
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
    BenchName = 'reportserver'
    BenchVersion = 'M1.0.18'          # runbench adds 1 to the last number on every run
    BenchHeader = 'the third report server: pages of blocks, through contactRS, HTTP and a page'
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
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
        got = reportserver.contactRS('ping')
        self.assertEqual((got['ok'], got['pong']), (True, 1))
        self.assertRegex(got['boot'], r'^\d+-\d+$')
        self.assertLess(abs(got['time'] - time.time()), 5)

    def test_T2_config_changes_are_kept_and_bad_values_refused(self):
        was = reportserver.contactRS('config')['config']['size']
        try:
            self.assertEqual(reportserver.contactRS('config', {'size': 17})['config']['size'], 17)
        finally:
            reportserver.contactRS('config', {'size': was})
        with self.assertRaises(reportserver.ReportServerError) as caught:
            reportserver.contactRS('config', {'size': 3})
        self.assertFalse(caught.exception.reply['ok'])
        self.assertEqual(reportserver.contactRS('config')['config']['size'], was)

    def test_T3_an_unknown_verb_raises_ReportServerError_with_the_reason_and_the_reply_in_the_same_shape(self):
        with self.assertRaises(reportserver.ReportServerError) as caught:
            reportserver.contactRS('nosuchverb', 1)
        self.assertIn('unknown verb', str(caught.exception))
        self.assertFalse(caught.exception.reply['ok'])
        self.assertEqual(caught.exception.reply['error'], str(caught.exception))

    def test_T3a_the_error_is_public_and_has_no_reply_when_the_server_gave_none(self):
        self.assertEqual(reportserver.__all__, ['contactRS', 'ReportServerError'])
        self.assertTrue(issubclass(reportserver.ReportServerError, Exception))
        self.assertIsNone(reportserver.ReportServerError('no answer in 3 s').reply)
        self.assertIsNone(reportserver.contactRS('snap', '/no/such/page', '#x'))      # None, not an error: no page has that path

    # ---- pages made of blocks ---------------------------------------------------------------------
    def test_T4_load_refuses_a_bad_layout_and_a_block_that_does_not_exist(self):
        for layout, blocks, word in (('[doc wxh', {}, 'layout'), ('[doc wxh ; doc wxh]', {}, 'twice'),
                                     ('[nosuch wxh]', {}, 'no block'),
                                     ('[doc wxh, doc.2 wxh ; doc.3 wxh]', {}, 'both'),
                                     ('[doc wxh, cd3 wxh]', {}, 'define it'),            # cd3 is no kind: it needs {cd3=code}
                                     ('[doc wxh, cd3 wxh]{cd4=code}', {}, 'definition')):
            with self.assertRaises(reportserver.ReportServerError, msg=layout) as caught:
                reportserver.contactRS('load', layout, blocks, 't', False)
            self.assertIn(word, str(caught.exception))

    def test_T5_a_page_of_blocks_has_one_style_and_one_script_and_the_html_in_its_place(self):
        got = reportserver.contactRS('load', '[doc wxh]', {'doc': ['doc', 'var x = 1;', '.k{color:red}',
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
        blocks = {'ftv': ['ftv'], 'toptabs': ['toptabs', './mumix/tools/reportserver.py', './mumix/tests/b_reportserver.py'],
                  'methods': ['methods'], 'code': ['code'], 'edit': ['editbox']}            # (edit is an editbox by this page's say)
        got = reportserver.contactRS('load', layout, blocks, '', False)
        self.assertTrue(got['ok'], got)
        self.assertTrue(got['path'].startswith('/?layout='), got['path'])
        self.assertEqual(got['path'].count('toptabs='), 1)                             # all of a block's paths in one value
        self.assertIn('toptabs=mumix/{tools/reportserver.py,tests/b_reportserver.py}', got['path'])   # the common folder once
        many = {'toptabs': ['toptabs', './mumix/tools/reportserver.py', './mumix/tools/primary/rs3comment.py', './mumix/tools/primary/rs3files.py',
                            './mumix/tests/b_reportserver.py']}
        folded = reportserver.contactRS('load', '[toptabs wxh]', many, '', False)['path']
        self.assertEqual(folded.count('toptabs='), 1)
        self.assertEqual(folded.count('tools/primary'), 1)                             # the folder, and the stem rs3, written once
        self.assertLess(len(folded), 160)                                              # (four paths of ~35 characters)
        again = web('GET', folded)[2]
        self.assertIn('data-open="[&quot;./mumix/tools/reportserver.py&quot;, &quot;./mumix/tools/primary/rs3comment.py&quot;, '
                      '&quot;./mumix/tools/primary/rs3files.py&quot;, &quot;./mumix/tests/b_reportserver.py&quot;]"', again)   # the paths as they were
        odd = reportserver.contactRS('load', '[toptabs wxh]', {'toptabs': ['toptabs', './mumix/a,b.py', './mumix/c.py']}, '', False)
        self.assertTrue(odd['path'].startswith('/page/'), odd['path'])               # a path with a comma has no address form
        self.assertNotIn('block.', got['path'])                                      # one editbox: written with its block's name
        self.assertIn('[ftv,[toptabs;[methods,[code;editbox]]]]', got['path'])
        status, head, text = web('GET', got['path'])
        self.assertEqual(status, 200)
        self.assertEqual(re.findall(r'data-loc="([\w.]+)"', text), ['ftv', 'toptabs', 'methods', 'code', 'editbox', 'statusbar'])
        self.assertIn('data-open="[&quot;./mumix/tools/reportserver.py&quot;', text)    # its data arrived
        self.assertIn('<title>ftv + toptabs + methods + code + editbox - reportserver.py</title>', text)   # a title from the address
        self.assertEqual(web('GET', '/?layout=%5Bdoc')[0], 500)                    # a layout that does not parse
        self.assertEqual(web('GET', '/?title=x')[0], 500)                               # no layout
        with self.assertRaises(reportserver.ReportServerError):
            reportserver.contactRS('load', '[doc wxh', {}, '', False)
        html = reportserver.contactRS('load', '[doc wxh]', {'doc': ['doc', '', '', '<p>x</p>']}, 't', False)
        self.assertTrue(html['path'].startswith('/page/'), html['path'])             # html is not for an address: a kept page

    def test_T6_a_static_page_given_whole_is_taken_apart_and_its_parts_collated(self):
        whole = '<html><style>.a{x:1}</style><div>one</div><script>var n = 1;</script></html>'
        got = reportserver.contactRS('load', '[doc wxh]', {'doc': ['doc', '', '', whole]}, 'whole', False)
        text = web('GET', got['path'])[2]
        self.assertEqual((text.count('<style'), text.count('<script')), (1, 1))
        self.assertIn('[data-doc="doc"] .a{x:1}', text)                  # its rule is a rule of the box
        self.assertIn('<div>one</div>', text)
        self.assertIn("(RS.docs = RS.docs || {})['doc'] = function(aDOM, document, window", text)    # its script is the box's

    def test_T6a_a_script_that_says_more_than_a_doc_may_is_refused_and_the_box_says_why(self):
        for script, why in (('window.parent.x = 1;', '.parent is not allowed'), ('fetch("/x");', 'the name fetch'),
                            ('var f = function(){ return this; };', 'this is not allowed'),
                            ('var o = {}; o.constructor("return 1")();', '.constructor is not allowed')):
            got = reportserver.contactRS('load', '[doc wxh]', {'doc': ['doc', '', '', f'<p>x</p><script>{script}</script>']}, 'bad', False)
            text = web('GET', got['path'])[2]
            self.assertIn('this page cannot be shown', text, script)
            self.assertIn(why, text, script)
            self.assertNotIn('(RS.docs = RS.docs', text, script)          # nothing of it runs

    def test_T6b_inline_handlers_become_functions_of_the_box_and_javascript_links_are_refused(self):
        page = '<p>t</p><button onclick="go(this.value)" id="b">x</button><script>function go(v){ var n = v; }</script>'
        got = reportserver.contactRS('load', '[doc wxh]', {'doc': ['doc', '', '', page]}, 'handler', False)
        text = web('GET', got['path'])[2]
        self.assertIn('data-aon-click="0"', text)
        self.assertNotIn('onclick=', text)
        self.assertIn('aDOM.on(["click"], [function(event, aThis){\naThis.value', text.replace('go(aThis.value)', 'aThis.value'))
        got = reportserver.contactRS('load', '[doc wxh]', {'doc': ['doc', '', '', '<a href="javascript:alert(1)">x</a>']}, 'link', False)
        self.assertIn('this page cannot be shown', web('GET', got['path'])[2])

    def test_T11b_a_block_says_what_it_can_search_and_the_status_bar_offers_that(self):
        text = web('GET', '/reportserver')[2]
        found = {m.group(1): m.group(2) for m in re.finditer(r'"block": "(\w+)", "at": \[[\d, ]*\], "to": \[[^\]]*\], "takes": \w+, "holds": [^,]+, "hosted": \w+, "search": (null|"\w+")', text)}
        self.assertEqual(found.get('ftv'), '"files"')
        self.assertEqual(found.get('log'), '"log"')
        self.assertEqual(found.get('serverstatus'), 'null')
        text = web('GET', '/?layout=[doc]&title=t')[2]
        self.assertIn('"search": "text"', text)                           # a doc answers a text search
        self.assertIn('class="sortbtn shome"', text)                      # one star, as in the tables, for next, previous, back
        self.assertNotIn('sprev', text)                                   # ... so no buttons of their own
        self.assertNotIn('snext', text)

    def test_T7_two_blocks_of_one_kind_carry_their_css_and_script_once(self):
        got = reportserver.contactRS('load', '[methods 40xh, methods.2 wxh]', {}, 'two', False)
        self.assertTrue(got['ok'], got)
        text = web('GET', got['path'])[2]
        self.assertEqual(text.count('/* block:methods */'), 2)    # one in the css, one in the js
        self.assertEqual(text.count("RS.pane('methods'"), 1)
        self.assertEqual(re.findall(r'data-loc="(mt(?:\.2)?)"', text), ['mt', 'mt.2'])        # several of a kind: the short name

    def test_T8_the_layout_sizes_and_draggable_edges_are_in_the_page(self):
        got = reportserver.contactRS('load', '[doc 40dxh, doc.2 wx25]', {}, 'sizes', False)
        text = web('GET', got['path'])[2]
        self.assertIn('flex:0 0 40mm', text)
        self.assertIn('class="drag v"', text)
        self.assertIn('class="group row"', text)

    def test_T8b_a_draggable_bar_is_between_two_panes_even_for_the_last_one(self):
        def order(layout):
            got = reportserver.contactRS('load', layout, {}, 'bars', False)
            return re.findall(r'class="(drag [vh](?: before)?)"|data-loc="([\w.]+)"', web('GET', got['path'])[2])
        flat = lambda found: [a or b for a, b in found]
        self.assertEqual(flat(order('[doc wxh ; doc.2 wxhd]'))[:3], ['doc', 'drag h before', 'doc.2'])   # the last: bar before it
        self.assertEqual(flat(order('[doc wdxh, doc.2 wxh]'))[:3], ['doc', 'drag v', 'doc.2'])           # not last: bar after it

    def test_T8a_a_pane_with_no_width_number_takes_its_blocks_width(self):
        def cells(layout):
            got = reportserver.contactRS('load', layout, {'doc': ['doc', '', '', '<p>x</p>'], 'ftv': ['ftv'],
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
        before = reportserver.contactRS('status')['status']['monitors']
        page = FakePage('/?reportserver=whatever')
        try:
            self.assertEqual(reportserver.contactRS('status')['status']['monitors'], before + 1)     # and it is the admin page
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
        got = reportserver.contactRS('load', full, {'toptabs': ['toptabs', './mumix/tools/reportserver.py'], 'editbox': ['editbox']}, '', False)
        self.assertTrue(got['ok'], got)
        url = urllib.parse.unquote(got['url'])
        self.assertIn('layout=[ftv,[toptabs;[methods,[code;editbox]]]]', url)       # no wdxh, wxhd, wxh
        self.assertNotIn('wxh', url.split('&')[0])
        text = web('GET', got['path'])[2]
        again = web('GET', reportserver.contactRS('load', '[ftv, [toptabs ; [methods, [code ; editbox]]]]', {'toptabs': ['toptabs', './mumix/tools/reportserver.py'], 'editbox': ['editbox']}, '', False)['path'])[2]
        self.assertEqual(re.findall(r'class="drag[^"]*"|flex:[^;"]*;', text), re.findall(r'class="drag[^"]*"|flex:[^;"]*;', again))
        sized = reportserver.contactRS('load', '[ftv 70dxh, [doc wxh ; doc.2 wx30d]]', {'doc': ['doc', '', '', '<p>a</p>']}, '', False)
        self.assertTrue(sized['ok'], sized)                                              # (html data: a hash page, nothing to shorten)
        kept = reportserver.contactRS('load', '[ftv 70dxh, [code ; editbox wx30d]]', {}, '', False)['url']
        self.assertIn('ftv_70dxh', kept)                                                # a size that is not the default stays
        self.assertIn('editbox_wx30d', kept)

    def test_T5g_the_paths_of_an_address_start_at_the_root_without_a_dot_slash(self):
        got = reportserver.contactRS('load', '[toptabs ; code]', {'toptabs': ['toptabs', './mumix/tools/reportserver.py']}, '', False)
        self.assertIn('toptabs=mumix/tools/reportserver.py', got['path'])
        self.assertNotIn('./', got['path'])
        for written in ('mumix/tools/reportserver.py', './mumix/tools/reportserver.py'):    # either is read
            text = web('GET', f'/?layout=[toptabs;code]&toptabs={written}')[2]
            self.assertIn('data-open="[&quot;./mumix/tools/reportserver.py&quot;]"', text)
            text = web('GET', f'/?layout=[toptabs;code]&toptabs={written}')[2]
            self.assertIn('data-open="[&quot;./mumix/tools/reportserver.py&quot;]"', text)
        mixed = reportserver.contactRS('load', '[toptabs ; code]', {'toptabs': ['toptabs', './mumix/a,b.py', './mumix/c.py']}, '', False)
        self.assertTrue(mixed['ok'], mixed)

    def test_T5d_a_wildcard_in_a_file_name_opens_the_files_it_matches_when_the_page_is_built(self):
        panes = './mumix/tools/rs_primary/panes/'
        got = reportserver.contactRS('load', '[toptabs ; code]', {'toptabs': ['toptabs', panes + 'pane_s*.js', panes + 'pane_toptabs.?s*']}, '', False)
        self.assertTrue(got['ok'], got)
        self.assertIn('pane_s*.js', urllib.parse.unquote(got['url']))                  # the address keeps the wildcard
        text = web('GET', got['path'])[2]
        shown = re.search(r'data-open="([^"]*)"', text).group(1).replace('&quot;', '"')
        opened = json.loads(shown)
        self.assertEqual(opened, [panes + 'pane_search.js', panes + 'pane_serverstatus.js', panes + 'pane_statusbar.js',
                                  panes + 'pane_toptabs.css', panes + 'pane_toptabs.js'])                          # by name; ? and * both work
        none = reportserver.contactRS('load', '[toptabs ; code]', {'toptabs': ['toptabs', panes + 'no_such_*.xyz']}, '', False)
        self.assertEqual(json.loads(re.search(r'data-open="([^"]*)"', web('GET', none['path'])[2]).group(1).replace('&quot;', '"')), [])
        out = reportserver.contactRS('load', '[toptabs ; code]', {'toptabs': ['toptabs', './mumix/../*.py', './mumix/tools/*/.git*']}, '', False)
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
        base = './mumix/tools/rs_primary'

        def opened(*patterns):
            got = reportserver.contactRS('load', '[toptabs ; code]', {'toptabs': ['toptabs', *patterns]}, '', False)
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
        base = './mumix/tools/rs_primary'
        got = reportserver.contactRS('load', '[toptabs ; code]', {'toptabs': ['toptabs', base + '/**/*.{py,md}']}, '', False)
        self.assertTrue(got['ok'], got)
        self.assertIn('/?layout=', got['url'])                                             # an address, not a kept page
        shown = re.search(r'data-open="([^"]*)"', web('GET', got['path'])[2]).group(1).replace('&quot;', '"')
        opened = json.loads(shown)
        self.assertIn(base + '/rs3core.py', opened)
        self.assertIn(base + '/SIGNALS.md', opened)
        self.assertEqual({path.rsplit('.', 1)[1] for path in opened}, {'py', 'md'})

    def test_T10b_status_counts_the_report_server_pages_with_a_live_socket_so_the_menu_link_can_leave_the_page_as_it_is(self):
        before = reportserver.contactRS('status')['status']['monitors']
        page = FakePage('/reportserver')
        try:
            self.assertEqual(reportserver.contactRS('status')['status']['monitors'], before + 1)
        finally:
            page.close()
        deadline = time.time() + 3
        while reportserver.contactRS('status')['status']['monitors'] != before and time.time() < deadline:
            time.sleep(0.1)
        self.assertEqual(reportserver.contactRS('status')['status']['monitors'], before)
        text = web('GET', '/reportserver')[2]
        self.assertIn('href="/reportserver" target="_blank"', text)          # the menu link opens a new tab

    def test_T10d_the_monitor_verb_opens_nothing_when_a_monitor_page_is_open_and_show_says_what_it_could_not_open(self):
        import subprocess
        page = FakePage('/reportserver')                      # a monitor page with a live socket: the server has its page
        try:
            got = reportserver.contactRS('monitor')
            self.assertIs(got['opened'], False)
            self.assertTrue(got['url'].endswith('/reportserver'), got['url'])
            script = os.path.join(ROOT, 'tools', 'reportserver.py')
            missing = os.path.join(ROOT, 'no_such_file_zz.py')
            done = subprocess.run([sys.executable, script, '--show', missing], capture_output=True, text=True, timeout=30)
            self.assertEqual(done.returncode, 1, done.stdout + done.stderr)                 # the file could not be opened
            self.assertIn('page already open', done.stdout)                                  # and the page was not opened again
            self.assertIn('no_such_file_zz.py', done.stdout)
        finally:
            page.close()

    def test_T11_view_makes_a_viewer_page_for_one_file_and_refuses_others(self):
        got = reportserver.contactRS('view', self.rel, False)
        self.assertTrue(got['ok'], got)
        text = web('GET', got['path'])[2]
        self.assertEqual(re.findall(r'data-loc="(\w+)"', text),
                         ['methods', 'code', 'editbox', 'statusbar'])
        self.assertIn(f'data-path="{self.rel}"', text)
        for bad in ('./no/such.py', '../x.py', 'C:/Windows/win.ini', './mumix/results'):
            with self.assertRaises(reportserver.ReportServerError, msg=bad):
                reportserver.contactRS('view', bad, False)

    def test_T11a_every_page_has_exactly_one_status_bar_with_search_settings_and_the_pulse(self):
        layouts = ['[doc wxh]', '[ftv 70dxh, [toptabs ; [methods wxh, [code ; editbox wxh]]]]',
                   '[doc wxh ; statusbar wx9]']                    # one that names its own keeps that one
        for layout in layouts:
            got = reportserver.contactRS('load', layout, {'doc': ['doc', '', '', '<p>x</p>']}, 'bar', False)
            self.assertTrue(got['ok'], (layout, got))
            text = web('GET', got['path'])[2]
            self.assertEqual(text.count('class="sbar"'), 1, layout)
            self.assertIn('class="cfgbtn"', text)                  # the menu button of the settings
            self.assertIn('class="sfind"', text)                   # the find box
            self.assertIn('class="slive"', text)                   # the pulse
            self.assertEqual(re.findall(r'data-loc="(\w+)"', text)[-1], 'statusbar')
        viewer = reportserver.contactRS('view', self.rel, False)['path']
        for path in ('/reportserver', viewer):
            self.assertEqual(web('GET', path)[2].count('class="sbar"'), 1, path)

    # ---- a page talks to the server ----------------------------------------------------------------
    def test_T12_hello_by_address_gives_the_same_hash_each_time_and_a_program_may_not_say_it(self):
        one, two = FakePage('/reportserver'), FakePage('/reportserver')
        try:
            self.assertTrue(one.hello['ok'])
            self.assertEqual(one.hello['hash'], two.hello['hash'])
            self.assertEqual(one.hello['boot'], reportserver.contactRS('ping')['boot'])
            self.assertFalse(one.ask({'do': 'hello', 'url': '/nowhere'})['ok'])
        finally:
            one.close()
            two.close()
        with self.assertRaises(reportserver.ReportServerError):
            reportserver.contactRS('hello', None, None, '/reportserver')

    def test_T13_open_gives_the_lines_and_methods_the_rows_with_their_owner_kind_and_lines(self):
        page = FakePage(reportserver.contactRS('view', self.rel, False)['path'])
        try:
            lines = page.ask({'do': 'open', 'hash': page.hash, 'path': self.rel})
            self.assertTrue(lines['ok'], lines)
            self.assertGreaterEqual(lines['html'].count('class="ln'), 8)
            self.assertRegex(lines['base'], r'^[0-9a-f]{40}$')
            got = page.ask({'do': 'methods', 'hash': page.hash, 'path': self.rel})
            self.assertTrue(got['ok'], got)
            rows = {(m['owner'], m['name'], m['kind']): m for m in got['methods']}
            self.assertEqual(sorted(rows), [('Thing', 'method', 'def'), ('sample', 'Thing', 'class'), ('sample', '__all__', 'const'), ('sample', 'free', 'def')])   # the note row: no __all__
            thing, method = rows[('sample', 'Thing', 'class')], rows[('Thing', 'method', 'def')]
            self.assertEqual((thing['line'], thing['top'], thing['last']), (4, 4, 6))          # a class runs to the end of its methods
            self.assertEqual((method['line'], method['text']), (5, 'def method(self):'))
            path = os.path.join(self.folder, 'consts.py')
            with open(path, 'w', encoding='utf-8', newline='') as f:
                f.write("__all__ = ['f']\nLIMIT = 5\nmax = 3\nNAME: str = 'x'\n\n\n@dec\ndef f():\n    return LIMIT\n")
            more = page.ask({'do': 'methods', 'hash': page.hash, 'path': rel_of(path)})['methods']
            self.assertEqual([(m['name'], m['kind'], m['line']) for m in more],
                             [('__all__', 'const', 1), ('LIMIT', 'const', 2), ('max', 'const', 3), ('NAME', 'const', 4), ('f', 'def', 8)])   # three capitals, __all__, or a literal with too few
            self.assertEqual((more[4]['top'], more[4]['last']), (7, 9))                          # the decorator is part of it
            self.assertEqual(more[1]['text'], 'LIMIT = 5')
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
        page = FakePage(reportserver.contactRS('view', rel, False)['path'])
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
        page = FakePage(reportserver.contactRS('view', rel, False)['path'])
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
        page = FakePage(reportserver.contactRS('view', rel, False)['path'])
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
        page = FakePage(reportserver.contactRS('view', rel, False)['path'])
        try:
            text = page.ask({'do': 'open', 'hash': page.hash, 'path': rel})['html']
            for row in (1, 2, 5, 6):                                       # the headings (1, 5) and their text (2, 6)
                self.assertRegex(text, rf'id="L{row}" data-n="{row}"')
            self.assertNotRegex(text, r'id="L3" data-n="3"')               # the second text line shares row 2's block
        finally:
            page.close()

    def test_T5a_a_tab_strip_holds_the_sections_of_a_static_page_as_docs_and_collates_their_style(self):
        sections = [['Summary', '<style>.sum{color:red}</style><p class="sum">all well</p>'], ['Failures', '<table><tr><td>x</td></tr></table>', True]]
        got = reportserver.contactRS('load', '[toptabs wxh]', {'toptabs': ['toptabs', *sections]}, 'report', False)
        self.assertTrue(got['ok'], got)
        text = web('GET', got['path'])[2]
        self.assertEqual((text.count('<style'), text.count('<script')), (1, 1))      # still one of each
        self.assertIn('.sum{color:red}', text)                                       # the section's style, collated
        self.assertEqual(text.count('<template class="ttsec"'), 2)
        self.assertIn('data-title="Summary" data-doc="toptabs.s1">', text)            # each section is a doc of its own
        self.assertIn('data-title="Failures" data-doc="toptabs.s2" data-bad="1">', text)   # the red one
        self.assertIn('<div class="doc" data-doc="toptabs.s1">', text)
        self.assertIn('<p class="sum">all well</p>', text)
        self.assertNotIn('<style>.sum', text.split('<template', 1)[1])               # (taken out of the section itself)

    def test_T5j_a_layout_token_in_a_tab_becomes_panes_of_its_own_with_their_own_locators(self):
        one = '<p>one</p>{{layout=[mt,[cd;eb]],./mumix/tools/use.py}}'
        two = '<p>two</p>{{layout=[mt,[cd;eb]],./mumix/tools/bench.py}}'
        got = reportserver.contactRS('load', '[toptabs]', {'toptabs': ['toptabs', ['One', one], ['Two', two]]}, 'tokens', False)
        self.assertTrue(got['ok'], got)
        text = web('GET', got['path'])[2]
        self.assertEqual((text.count('class="rslayout"'), text.count('{{layout=')), (2, 0))      # a place for each, no token left
        info = json.loads(re.search(r'var PAGE = (\{.*?\});', text, re.S).group(1))
        panes = {p['loc']: p for p in info['panes']}
        for loc in ('mt.c1', 'cd.c1', 'eb.c1', 'mt.c2', 'cd.c2', 'eb.c2'):
            self.assertIn(loc, panes)
        self.assertFalse(panes['cd.c1']['hosted'])                    # a tab strip does not make a container's code pane its place
        self.assertEqual(panes['cd.c1']['at'][:-2], panes['eb.c1']['at'][:-2])      # one container: the same path down to its own group
        self.assertNotEqual(panes['cd.c1']['at'][:-2], panes['cd.c2']['at'][:-2])   # two containers: not the same

    def test_T13a_a_markdown_file_is_shown_as_md2htm_formats_it_headings_and_tables(self):
        rel = './mumix/tools/rs_primary/SIGNALS.md'
        page = FakePage(reportserver.contactRS('view', rel, False)['path'])
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
        page = FakePage(reportserver.contactRS('view', self.rel, False)['path'])
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

    def test_T14a_a_comment_may_go_inside_a_docstring_or_a_string_and_is_a_line_of_its_text_with_a_note(self):
        path = os.path.join(self.folder, 'doc.py')
        original = '"""head\nmore text\n"""\n\n\ndef f():\n    x = """a\n    b"""\n    return x\n'
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(original)
        rel = rel_of(path)
        page = FakePage(reportserver.contactRS('view', rel, False)['path'])
        try:
            base = page.ask({'do': 'open', 'hash': page.hash, 'path': rel})['base']
            got = page.ask({'do': 'insert', 'hash': page.hash, 'filename': rel, 'line': 2,
                            'base': base, 'tag': 'tst', 'text': 'inside the docstring'})
            self.assertTrue(got['ok'] is not False and 'error' not in got, got)
            self.assertIn('note', got)                                         # it says the comment is a line of the string
            with open(path, encoding='utf-8') as f:
                self.assertEqual(f.read().split('\n')[:4], ['"""head', '###tst inside the docstring', 'more text', '"""'])
            data = page.ask({'do': 'insert', 'hash': page.hash, 'filename': rel, 'line': 9,
                             'base': got['base'], 'tag': 'tst', 'text': 'inside data'})
            self.assertNotIn('error', data)                                    # a string that is data: the user's say
            self.assertIn('note', data)
            shown = page.ask({'do': 'open', 'hash': page.hash, 'path': rel})
            self.assertEqual(len(re.findall(r'class="cm[ "]', shown['html'])), 2)              # both are comment threads in the page
            ok = page.ask({'do': 'insert', 'hash': page.hash, 'filename': rel, 'line': 6,
                           'base': data['base'], 'tag': 'tst', 'text': 'above the function'})
            self.assertNotIn('note', ok)                                       # between the code: no note
            self.assertNotIn('error', ok)
            for first in (11, 8, 2):                                           # take them out again, last first
                with open(path, encoding='utf-8') as f:
                    lines = f.read().split('\n')
                at = next(i + 1 for i, line in enumerate(lines) if line.lstrip().startswith('###tst') and i + 1 <= first + 2 and i + 1 >= first - 2)
                base = page.ask({'do': 'open', 'hash': page.hash, 'path': rel})['base']
                gone = page.ask({'do': 'update', 'hash': page.hash, 'filename': rel, 'first': at, 'last': at, 'base': base, 'tag': 'tst', 'text': ''})
                self.assertTrue(gone.get('removed'), gone)
            with open(path, encoding='utf-8') as f:
                self.assertEqual(f.read(), original)                           # nothing else ever changed
            with open(path, 'wb') as f:
                f.write(b'x = 1\n')
            stale = page.ask({'do': 'insert', 'hash': page.hash, 'filename': rel, 'line': 1,
                              'base': 'stale', 'tag': 'tst', 'text': 'x'})
            self.assertIn('error', stale)
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
            self.assertIn('./mumix/tools/reportserver.py', [f['p'] for f in got['files']])
        finally:
            page.close()

    def test_T15c_each_module_exports_only_what_another_unit_uses(self):
        rs3dir = os.path.join(ROOT, 'tools', 'rs_primary')
        want = {'rs3util.py': {'asset', 'done', 'split_package', 'pathof', 'address'}, 'rs3core.py': {'VERBS'},
                'rs3pages.py': {'VERBS', 'ROUTES', 'register_url'}, 'rs3comment.py': {'VERBS'}, 'rs3table.py': {'Pages'},
                'rs3jsguard.py': {'check', 'this_as'}, 'rs3layout.py': {'parse', 'names', 'places', 'receivers', 'blocks', 'normal', 'render', 'plain', 'LayoutError'}}
        for name in os.listdir(os.path.join(rs3dir, 'panes')):
            if name.endswith('.py'):
                want[os.path.join('panes', name)] = {'write'}
        for name, names in want.items():
            tree = ast.parse(open(os.path.join(rs3dir, name), encoding='utf-8').read())
            found = [n for n in tree.body if isinstance(n, ast.Assign) and any(getattr(t, 'id', '') == '__all__' for t in n.targets)]
            self.assertEqual(len(found), 1, name)
            self.assertEqual({e.value for e in found[0].value.elts}, names, name)
        for gone in ('rs3files.py', 'rs3source.py'):
            self.assertFalse(os.path.exists(os.path.join(rs3dir, gone)), gone)

    def test_T15a_rs3_imports_only_the_standard_library_and_its_own_folder(self):
        folder = os.path.join(ROOT, 'tools', 'rs_primary')
        folders = [folder, os.path.join(folder, 'panes')]
        own = {os.path.splitext(n)[0] for f in folders for n in os.listdir(f) if n.endswith('.py')}
        files = [os.path.join(f, n) for f in folders for n in sorted(os.listdir(f)) if n.endswith('.py')]
        files.append(os.path.join(ROOT, 'tools', 'reportserver.py'))
        outside = []
        for path in files:
            with open(path, encoding='utf-8') as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                         else [node.module] if isinstance(node, ast.ImportFrom) and node.level == 0 else [])
                for name in names:
                    top = name.split('.')[0]
                    if top not in sys.stdlib_module_names and top not in own and top not in ('reportserver', 'use'):   # use: tools/use.py loads rs3lex.pyx
                        outside.append((os.path.basename(path), name))
        self.assertEqual(outside, [])

    def test_T15b_each_blocks_signals_are_the_ones_its_script_handles_and_emits(self):
        folder = os.path.join(ROOT, 'tools', 'rs_primary', 'panes')
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
                sent = set()                          # its code panes emit, as this block
            if handled != declared_in[block]:
                problems.append((block, 'IN', sorted(handled ^ declared_in[block])))
            if block != 'toptabs' and sent != declared_out[block]:
                problems.append((block, 'OUT', sorted(sent ^ declared_out[block])))
        manager_in = {'closemaintab', 'showpane', 'mngshowfile', 'withlineno', 'withwrap', 'withconfig'}
        manager_out = {'status', 'log', 'newtabopened', 'closingmaintab', 'busy', 'showfile', 'showcode'}
        self.assertEqual([n for names in declared_in.values() for n in names if n.startswith('mng')], [])   # no block listens to one
        every_in = set().union(*declared_in.values()) | manager_in
        every_out = set().union(*declared_out.values()) | manager_out
        gaps = {'newtabopened', 'closingmaintab', 'closemaintab'}     # SIGNALS.md: no receiver yet, no sender yet
        problems += [('no receiver', sorted(every_out - every_in - gaps)),
                     ('no sender', sorted(every_in - every_out - gaps))]
        self.assertEqual([p for p in problems if p[-1]], [])



    # ---- the layout lists of who receives; the routing itself is tested in the page: tests/b_rs3page.py ----
    def test_T20_a_layout_lists_who_receives_and_says_where_each_block_sits(self):
        tree = rs3layout.parse('[cd0,ed{cd2},cd1,cd2]')
        self.assertEqual(rs3layout.receivers(tree), {'ed': ['cd2']})
        self.assertEqual(rs3layout.places(rs3layout.parse('[ftv,[toptabs;[methods,[code;editbox]]]]')),
                         {'ftv': [0], 'toptabs': [1, 0], 'methods': [1, 1, 0], 'code': [1, 1, 1, 0], 'editbox': [1, 1, 1, 1]})
        self.assertEqual(rs3layout.plain(rs3layout.parse('[a,b{a,c} 30xh,c]'), lambda loc, way: False), '[a,b{a,c} 30xh,c]')
        self.assertEqual(rs3layout.receivers(rs3layout.parse('[a{b,c} , b , c]')), {'a': ['b', 'c']})
        self.assertEqual(rs3layout.names(rs3layout.parse('[ftv.py,[cd.1,cd3,eb.notes w50dxh]]{cd3=code}')), ['ftv.py', 'cd.1', 'cd3', 'eb.notes'])
        self.assertEqual(rs3layout.blocks(rs3layout.parse('[ftv.py,[cd.1,cd3,eb.notes]]{cd3=code}')),
                         {'ftv.py': 'ftv', 'cd.1': 'code', 'cd3': 'code', 'eb.notes': 'editbox'})
        tree, new = rs3layout.normal(rs3layout.parse('[mt,mt.2,[code.x,cd.y],eb]'))                # several: short; one: the name
        self.assertEqual(rs3layout.plain(tree, lambda loc, way: False), '[mt,mt.2,[cd.x,cd.y],editbox]')
        self.assertEqual(new['eb'], 'editbox')
        for bad in ('[a,b{c}]', '[a{a},b]', '[a{b,},b]', '[a{b][b]', '[a{B},b]', '[a w50d.h]', '[a]{b=code}', '[a]{a=}'):
            with self.assertRaises(rs3layout.LayoutError, msg=bad):
                rs3layout.parse(bad)

    def test_T20a_a_page_says_where_its_blocks_sit_and_what_they_take_and_hold(self):
        got = reportserver.contactRS('load', '[ftv,[toptabs;[methods,[code;editbox{toptabs}]]]]', {}, 'routes', False)
        self.assertTrue(got['ok'], got)
        text = web('GET', got['path'])[2]
        info = json.loads(re.search(r'var PAGE = (\{.*?\});\n', text, re.S).group(1)) if 'var PAGE = ' in text else None
        panes = {p['loc']: p for p in info['panes']}
        self.assertEqual(panes['editbox']['to'], ['toptabs'])
        self.assertEqual(panes['code']['hosted'], True)               # the tabs hold it
        self.assertEqual((panes['toptabs']['takes'], panes['toptabs']['holds']), (True, 'code'))
        self.assertEqual(panes['ftv']['takes'], False)
        self.assertEqual(panes['editbox']['at'], [0, 1, 1, 1, 1])      # the status bar's row is the outer group
        self.assertEqual(info['routed'], ['commentline', 'commentselect', 'saved', 'showcode'])
        for layout in ('[ftv{methods},code]', '[ftv,editbox{log},log]', '[log{ftv},ftv]'):      # a list must name blocks that take what is sent
            with self.assertRaises(reportserver.ReportServerError, msg=layout):
                reportserver.contactRS('load', layout, {}, 'bad', False)

    def test_T22a_a_name_that_starts_with_mng_is_for_the_manager_only(self):
        folder = os.path.join(ROOT, 'tools', 'rs_primary', 'panes')
        for name in sorted(os.listdir(folder)):
            if name.startswith('pane_') and name.endswith('.js'):
                with open(os.path.join(folder, name), encoding='utf-8') as f:
                    self.assertEqual(re.findall(r'\bonMng\w*', f.read()), [], name)       # no block listens to one

    def test_T5i_a_report_that_does_not_keep_the_rules_of_the_box_is_its_own_page_with_no_rs3_around_it(self):
        path = os.path.join(self.folder, 'old.html')
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write('<html><head><title>old</title></head><body><p>old report</p>'
                    '<script>var s = new WebSocket("ws://127.0.0.1:1/"); document.body.parentNode;</script></body></html>')
        status, head, text = web('GET', '/?layout=[doc]&doc=' + rel_of(path)[2:])
        self.assertEqual(status, 200)
        self.assertIn('new WebSocket', text)                          # the file as it is
        self.assertNotIn('data-loc=', text)                           # no layout, no manager, no status bar
        self.assertNotIn('this page cannot be shown', text)
        inside = web('GET', '/?layout=[doc]&doc=' + rel_of(path)[2:] + '&title=x')
        self.assertEqual(inside[0], 200)
        mixed = reportserver.contactRS('load', '[doc,log]', {'doc': ['doc', './' + rel_of(path)[2:]]}, 'mixed', False)
        self.assertIn('this page cannot be shown', web('GET', mixed['path'])[2])     # in a page of blocks it is still refused there


    def test_T23a_a_page_carries_the_table_engine_and_the_methods_block_is_a_table_with_a_status_pie(self):
        text = web('GET', '/code/' + self.rel[2:])[2]
        self.assertIn('RS.table = (function()', text)
        self.assertIn('button.sortbtn', text)                                  # the css of the star
        self.assertIn('RS.table.make(t, {initial: byName', text)
        self.assertIn('function pie(shares, dot)', text)                       # the pie of an item, drawn as svg
        self.assertNotIn('.methods.band-red{border-color', text)               # no frame round the pane
        self.assertIn('.methods.band-red .mhead{background', text)             # the header takes a pale colour of the file's band
        self.assertIn('class="fscore"', text)                                  # ... with the score of the file before its pie
        self.assertIn('RS.pane(\'methods\'', text)


    def test_T30_the_methods_of_a_file_carry_a_pie_a_dot_and_reasons_from_spaghettichk_and_a_changed_file_is_judged_again(self):
        proj = os.path.join(self.folder, 'proj')
        for sub in ('tools', 'tests'):
            os.makedirs(os.path.join(proj, sub), exist_ok=True)
        mod = os.path.join(proj, 'tools', 'mod.py')
        good = ('"""mod -- a demo.\n\nExposes alpha and Beta.\n\nVERSION  M1 m01.v01 (2026-11-04): first version.\n"""\n'
                '__all__ = [\'alpha\', \'Beta\']\n\n\n'
                'def alpha(x, y):\n    """Add them because a sum is what the callers need.\n\n    More lines.\n    """\n    return x + y\n\n\n'
                'def untested(v):\n    return getattr(other, \'a\')\n\n\n'
                'class Beta:\n    def __init__(me):\n        me.size = 1\n        me._hidden = 2\n\n    def run(me):\n        return 1\n')
        with open(mod, 'w', encoding='utf-8', newline='') as f:
            f.write(good)
        with open(os.path.join(proj, 'tools', 'bare.py'), 'w', encoding='utf-8', newline='') as f:
            f.write('__all__ = [\'only\']\n\n\ndef only(a):\n    return a\n')
        with open(os.path.join(proj, 'tools', 'consts.py'), 'w', encoding='utf-8', newline='') as f:
            f.write("__all__ = ['SHOWN']\nSHOWN = 1\nLIMIT = 5\nINNER = 2\nLimit = 3\nSTYLEsheet = 4\nUNUSED = 9\n\n\n"
                    "def f():\n    return INNER + STYLEsheet + SHOWN + Limit\n")
        with open(os.path.join(proj, 'tools', 'user.py'), 'w', encoding='utf-8', newline='') as f:
            f.write('x = LIMIT\n')
        with open(os.path.join(proj, 'tools', 'noall.py'), 'w', encoding='utf-8', newline='') as f:
            f.write('def x():\n    return 1\n')
        with open(os.path.join(proj, 'tests', 'b_mod.py'), 'w', encoding='utf-8', newline='') as f:
            f.write('from mod import alpha, untested\n\n\nclass b_mod:\n    def test_alpha(self):\n        assert alpha(1, 2) == 3\n')
        page = FakePage(reportserver.contactRS('view', rel_of(mod), False)['path'])
        try:
            got = page.ask({'do': 'methods', 'hash': page.hash, 'path': rel_of(mod)})
            self.assertTrue(got['ok'], got)
            rows = {m['name']: m for m in got['methods']}
            for row in rows.values():
                if row['kind'] != 'const':
                    self.assertEqual(sum(row['pie']), 100 if any(row['pie']) else 0, row)           # the pie is percent
            self.assertEqual((rows['__all__']['band'], rows['__all__']['pie']), ('green', [100, 0, 0, 0]))   # two names in __all__: green
            many = os.path.join(proj, 'tools', 'many.py')
            with open(many, 'w', encoding='utf-8', newline='') as f:
                f.write('__all__ = [' + ', '.join(f"'n{k}'" for k in range(9)) + ']\n')
            big = page.ask({'do': 'methods', 'hash': page.hash, 'path': rel_of(many)})
            self.assertEqual([(m['band'], m['pie']) for m in big['methods']], [('red', [0, 0, 0, 100])])       # nine names: too many, red
            self.assertGreater(rows['alpha']['pie'][0], 50)                                          # tested, documented: mostly green
            self.assertEqual(rows['alpha']['dot'], 'green')                                          # a suite names it, nothing under it: green
            self.assertEqual(rows['untested']['dot'], '')                                            # not in __all__: no dot
            self.assertEqual(rows['Beta']['dot'], 'red')                                             # in __all__, no suite names it
            self.assertTrue(any(w.startswith('tested: green') for w in rows['alpha']['why']), rows['alpha']['why'])
            self.assertEqual(rows['untested']['band'], 'red')                                        # getattr on another object forces red
            self.assertTrue(any('getattr' in w and 'another object' in w for w in rows['untested']['why']), rows['untested']['why'])
            self.assertTrue(any(w.startswith('tested: orange') for w in rows['Beta']['why']), rows['Beta']['why'])   # a suite, none names it
            self.assertGreaterEqual(rows['Beta']['pie'][3], 1)                                       # a private name of a class: red
            self.assertEqual(got['file']['band'], 'red')                                             # the suite reaches `untested`, not in __all__
            self.assertTrue(any(w.startswith('suitepeek: red') and 'untested' in w for w in got['file']['why']), got['file']['why'])
            consts = page.ask({'do': 'methods', 'hash': page.hash, 'path': rel_of(os.path.join(proj, 'tools', 'consts.py'))})
            by = {m['name']: m for m in consts['methods'] if m['kind'] == 'const'}
            self.assertEqual({k: (v['band'], v['pie']) for k, v in by.items() if k != '__all__'},
                             {'SHOWN': ('orange', [0, 0, 100, 0]),                                   # in __all__: a constant should not be exposed
                              'LIMIT': ('red', [0, 0, 0, 100]),                                      # used by another module, not exposed
                              'INNER': ('green', [100, 0, 0, 0]),                                    # all capitals, private to the module
                              'Limit': ('orange', [0, 0, 100, 0]),                                   # a literal with too few capitals
                              'STYLEsheet': ('', [0, 100, 0, 0]),                                    # only the first three letters
                              'UNUSED': ('orange', [0, 0, 100, 0])})                                 # never used
            noall = page.ask({'do': 'methods', 'hash': page.hash, 'path': rel_of(os.path.join(proj, 'tools', 'noall.py'))})
            note = [m for m in noall['methods'] if m['name'] == '__all__']
            self.assertEqual([(m['band'], m['pie'], m['line']) for m in note], [('red', [0, 0, 0, 100], 1)])      # a note row, red
            self.assertIn('no __all__', note[0]['text'])
            bare = page.ask({'do': 'methods', 'hash': page.hash, 'path': rel_of(os.path.join(proj, 'tools', 'bare.py'))})
            self.assertEqual({m['name']: m['dot'] for m in bare['methods'] if m['kind'] != 'const'}, {'only': 'red'})      # in __all__, and no suite
            with open(mod, 'w', encoding='utf-8', newline='') as f:
                f.write(good.replace('def alpha(x, y):\n    """Add them because a sum is what the callers need.\n\n    More lines.\n    """\n',
                                     'def alpha(x, y):\n'))
            again = page.ask({'do': 'methods', 'hash': page.hash, 'path': rel_of(mod)})
            rows = {m['name']: m for m in again['methods']}
            self.assertTrue(any(w.startswith('docs: red') for w in rows['alpha']['why']), rows['alpha']['why'])   # the new text was read
        finally:
            page.close()


    def test_T16_pulse_gives_the_status_and_the_log_lines_after_a_row(self):
        page = FakePage('/reportserver')
        try:
            got = page.ask({'do': 'pulse', 'since': 0})
            self.assertTrue(got['ok'], got)
            self.assertEqual(got['status']['port'], PORT)
            self.assertEqual(got['boot'], reportserver.contactRS('ping')['boot'])
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
        viewer = FakePage(reportserver.contactRS('view', self.rel, False)['path'])
        try:
            for verb in ('stop', 'restart'):
                got = viewer.ask({'do': verb})
                self.assertFalse(got['ok'], verb)
                self.assertIn('monitor', got['error'])
        finally:
            viewer.close()
        self.assertTrue(reportserver.contactRS('ping')['ok'])

    # ---- the pages' own checks of their signals (the title of a page with ?selftest=1) -------------
    def test_T18_every_page_serves_its_selftest_when_asked(self):
        for path in ('/reportserver', '/code' + self.rel[1:]):
            text = web('GET', path + '?selftest=1')[2]
            self.assertIn('RS.selftest()', text)
            self.assertNotIn('RS.selftest()', web('GET', path)[2])

    # ---- restart last: it ends this server and a new one takes the port --------------------------------
    def test_T99_restart_gives_a_new_boot_and_the_port_answers_again_and_a_loaded_page_survives_it(self):
        made = reportserver.contactRS('load', '[doc wxh]', {'doc': ['doc', '', '', '<p>it survives</p>']}, 'a survivor', False)
        self.assertTrue(made['ok'], made)
        was = reportserver.contactRS('ping')['boot']
        self.assertTrue(reportserver.contactRS('restart')['ok'])
        end = time.time() + 15
        now = was
        while time.time() < end and now == was:
            time.sleep(0.3)
            try:
                now = reportserver.contactRS('ping', timeout=1.0).get('boot', was)
            except reportserver.ReportServerError:                    # the old one has gone and the new one is not up yet
                now = was
        self.assertNotEqual(now, was)
        status, head, text = web('GET', made['path'])                  # the new server builds the page again from its kept spec
        self.assertEqual(status, 200)
        self.assertIn('it survives', text)
        self.assertIn('a survivor', text)

    def test_T99a_the_command_line_restart_gives_a_new_boot_and_opens_no_page(self):
        import subprocess
        was = reportserver.contactRS('ping')['boot']
        script = os.path.join(ROOT, 'tools', 'reportserver.py')
        done = subprocess.run([sys.executable, script, '--restart', '--by', 'suite'], capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn('restarted', done.stdout)
        self.assertNotIn('page', done.stdout)                                           # nothing was opened
        self.assertNotEqual(reportserver.contactRS('ping')['boot'], was)

    def bench_ping(self, timer):
        with timer as test:
            while test.more:
                for _ in test.count:
                    reportserver.contactRS('ping')
        return 'contactRS ping (kept connection)', 'client'

    def bench_monitor_page(self, timer):
        with timer as test:
            while test.more:
                for _ in test.count:
                    web('GET', '/reportserver')
        return 'GET the monitor page (built each time)', 'client'
