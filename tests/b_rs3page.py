r"""b_rs3page.py -- tests for the code that runs in the browser pages of rs3: who gets a signal (html/manager.js), the filter language of
the table engine (html/table.js) and the pie of the methods block (panes/pane_methods.js). No Node and no browser driver, and nothing
added to the server. One stand-alone page, tests/jstest.html (the js test manager), is kept open in its own tab of the default browser
and carries its own access to the server (hello, open, and the answers to trigger and snap). A run is:

    the suite writes a bundle, tests/z_sandbox/jstest/testfile.txt: the code to be tested, the test code (b_rs3page.js) and the cases;
    it presses #get in the page (trigger); the page asks the server for the file (open), unpacks it, runs it, writes the results into
    #out; the suite reads #state and #out (snap) and judges the results here.

The tab is opened the first time (an address no page answers for) and reused after that. When no page answers within 25 seconds
(nobody is there), the tests are skipped, not failed.

Run from the project root:
    python tools/runbench.py b_rs3page
"""
import atexit
import json
import os
import shutil
import sys
import time
import uuid
import webbrowser


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

CLAUDE = os.path.dirname(ROOT)      # the folder that holds .claude and mumix
RS3 = os.path.join(ROOT, 'tools', 'rs_primary')
WAIT = 25                           # seconds to wait for the page to say hello


def text_of(*parts):
    with open(os.path.join(*parts), encoding='utf-8') as f:
        return f.read()


def panes(layout, kinds=None, to=None, **flags):
    """The panes of a layout the way build writes them: {loc, block, at, to, ...}; kinds {loc: block}, to {loc: [locs]}."""
    tree = rs3layout.parse(layout)
    at = rs3layout.places(tree)
    return [{'loc': loc, 'block': (kinds or {}).get(loc, loc), 'at': at[loc], 'to': (to or {}).get(loc, []),
             'takes': False, 'holds': None, 'hosted': False, **flags.get(loc, {})} for loc in rs3layout.names(tree)]


def cases():
    """{filter, pie, route}: the cases the page runs; what each must give is judged by the tests below."""
    same = {'cd0': 'cd', 'cd1': 'cd', 'cd2': 'cd', 'cd3': 'cd'}
    listen = {loc: ['commentline'] for loc in same}

    def near(layout, sender, to=None):
        return {'panes': panes(layout, same, to), 'listens': listen,
                'steps': [{'from': sender, 'name': 'commentline', 'data': {'path': 'p'}}]}
    kinds = {'cd1': 'code', 'cd2': 'code', 'ml1': 'methods', 'ml2': 'methods', 'eb': 'editbox'}
    kind = '[ml1,[cd1;[ml2,cd2,eb]]]'
    take = {'takes': True}
    both = panes('[ftv,[tt;cd]]', {'ftv': 'ftv', 'tt': 'toptabs', 'cd': 'code'}, tt={'takes': True, 'holds': 'code'},
                 cd={'takes': True, 'hosted': True})
    lone = panes('[ftv,[cd1;cd2]]', {'cd1': 'code', 'cd2': 'code'}, cd1=take, cd2=take)
    taker = {'tt': ['showfile'], 'cd1': ['showfile'], 'cd2': ['showfile']}

    def show(layout, data, listens=taker):
        return {'panes': layout, 'listens': listens, 'steps': [{'from': 'ftv', 'name': 'mngshowfile', 'data': data}]}
    return {
        'filter': [['>3 & <6.3', True, '4'], ['>3 & <6.3', True, '7'], ['<3 | >6', True, '9'], ['3..6', True, '6'], ['6..3', True, '4'],
                   ['>=2', True, '14.4k'], ['3', True, '3'], ['', True, 'x'], ['pane*', False, 'pane_code'], ['pane*', False, 'my_pane'],
                   ['[ane]', False, 'pane_code'], ['{a b}', False, 'x a b y'], ['[p - s]', False, 'rs3'], ['[p - s]', False, 'zed'],
                   ['!pane*', False, 'pane_code'], ['blank', False, ''], ['*', False, 'anything'], ['a | b', False, 'b'],
                   ['>3 &', True, '4'], ['[a', False, 'a'], ['pa?e', False, 'page']],
        'pie': [[[100, 0, 0, 0], ''], [[50, 0, 50, 0], ''], [[60, 20, 10, 10], 'red'], [[0, 0, 0, 0], ''], [[0, 100, 0, 0], 'green']],
        'route': [
            near('[cd1,[cd2,eb]]', 'eb'),                                                    # 0 the group [cd2,eb] is the nearest
            near('[[eb,cd1,cd2],cd3]', 'eb'),                                                # 1 one group: the first after eb
            near('[[cd0,eb,cd1,cd2],cd3]', 'eb'),                                            # 2 the same: cd1, not cd0
            near('[cd0,eb]', 'eb'),                                                          # 3 none after: round the end
            near('[[cd0,eb,cd1,cd2],cd3]', 'eb', {'eb': ['cd2']}),                           # 4 a list in the layout string
            near('[[cd0,eb,cd1,cd2],cd3]', 'eb', {'eb': ['cd0', 'cd2']}),                    # 5 ... of two
            {'panes': panes(kind, kinds), 'listens': {'cd1': ['saved'], 'cd2': ['saved'], 'ml1': ['saved'], 'ml2': ['saved']},
             'steps': [{'from': 'eb', 'name': 'saved', 'data': {'path': 'p'}}]},             # 6 the nearest of each kind
            {'panes': panes(kind, kinds), 'listens': {'cd1': ['selectfunk'], 'cd2': ['selectfunk']},
             'steps': [{'from': 'ml2', 'name': 'selectfunk', 'data': {'lineno': 3, 'to': ['cd1']}}]},    # 7 addressed
            {'panes': panes(kind, kinds), 'listens': {'cd1': ['selectfunk'], 'cd2': ['selectfunk']},
             'steps': [{'from': 'ml2', 'name': 'selectfunk', 'data': {'lineno': 3}}]},        # 8 everyone
            show(both, {'path': './a.py', 'show': True}),                                    # 9 the container, not the code
            show(lone, {'path': './a.py', 'show': True}),                                    # 10 the first lone block
            show(lone, {'path': './a.py', 'show': True, 'to': ['cd2']}),                     # 11 addressed
            show(panes('[ftv,log]'), {'path': './a.py', 'show': True}, {}),                  # 12 nothing takes it: a tab
            show(both, {'path': './r.html', 'show': True, 'to': 'tab'}),                     # 13 html: a tab
            {'panes': both, 'listens': taker,
             'steps': [{'from': 'tt', 'name': 'showcode', 'data': {'path': './a.py', 'loc': 'tt', 'on': True}},
                       {'from': 'ftv', 'name': 'mngshowfile', 'data': {'path': './a.py', 'show': False}}]},   # 14 closed where shown
            show(panes('[ftv{cd2},[cd1;cd2]]', {'cd1': 'code', 'cd2': 'code'}, to={'ftv': ['cd2']}, cd1=take, cd2=take),
                 {'path': './a.py', 'show': True}),                                          # 15 ftv{cd2}
            {'panes': panes('[a,b]'), 'listens': {'a': ['mngshowfile'], 'b': ['mngshowfile']},
             'steps': [{'from': 'a', 'name': 'mngshowfile', 'data': {'path': './x.py', 'show': True}}]},   # 16 a name of mng is the manager's
        ]}


BUNDLE = os.path.join(ROOT, 'tests', 'z_sandbox', 'jstest', 'testfile.txt')     # where the page looks (see PATH in jstest.html)
PAGE = os.path.join(ROOT, 'tests', 'jstest.html')
PAGE_VERSION = '1'                  # the version the page says (#ver): another one is an old tab, which is reloaded


def bundle(sources, test, data):
    """The text of a bundle for the js test manager: the source texts, the test code and the data, with an id for this run."""
    return json.dumps({'id': uuid.uuid4().hex, 'sources': sources, 'test': test, 'data': data}, indent=1)


def pieces():
    """The code to be tested, as text: the filter language of table.js and pie() of pane_methods.js."""
    table = text_of(RS3, 'html', 'table.js')
    methods = text_of(RS3, 'panes', 'pane_methods.js')
    return [table[table.index('// FILTER:BEGIN'):table.index('// FILTER:END')],
            methods[methods.index('var COLOURS'):methods.index('function frame()')]]


class b_rs3page(bench):
    BenchName = 'rs3page'
    BenchVersion = 'M1.0.16'          # runbench adds 1 to the last number on every run
    BenchHeader = 'the code of the rs3 pages (routing, the filter language, the pie), run in the js test manager through trigger and snap'
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        os.makedirs(os.path.dirname(BUNDLE), exist_ok=True)
        atexit.register(shutil.rmtree, os.path.dirname(BUNDLE), True)
        cls.address = '/?layout=[doc]&doc=' + os.path.relpath(PAGE, CLAUDE).replace(os.sep, '/')
        port = reportserver.contactRS('status')['status']['port']
        there = reportserver.contactRS('snap', cls.address, '#ver')
        if there and there.get('ok') and there.get('text') != PAGE_VERSION:      # an old tab: load the page again
            reportserver.contactRS('trigger', cls.address, '#reload')
            time.sleep(1.5)
        elif not (there and there.get('ok')):
            webbrowser.open(f'http://127.0.0.1:{port}{cls.address}')
        cls.alive = False
        end = time.time() + WAIT
        while time.time() < end and not cls.alive:
            got = reportserver.contactRS('snap', cls.address, '#alive')
            cls.alive = bool(got and got.get('ok') and got.get('text') == 'ready')
            time.sleep(0.5)
        cls.parts = (pieces(), text_of(ROOT, 'tests', 'b_rs3page.js'), {'CASES': cases(), 'MANAGER': text_of(RS3, 'html', 'manager.js')})
        cls.results = cls.run_bundle(*cls.parts) if cls.alive else None

    @classmethod
    def run_bundle(cls, sources, test, data):
        """The results of running a bundle in the page: write it, press #get, wait for #state, read #out."""
        text = bundle(sources, test, data)
        with open(BUNDLE, 'w', encoding='utf-8', newline='') as f:
            f.write(text)
        sent = reportserver.contactRS('trigger', cls.address, '#get')
        assert sent and sent.get('ok'), sent
        end = time.time() + WAIT
        while time.time() < end:
            state = reportserver.contactRS('snap', cls.address, '#state')
            if state and state.get('text') != 'running':
                break
            time.sleep(0.2)
        assert state and state.get('text') == 'done', state
        got = json.loads(reportserver.contactRS('snap', cls.address, '#out')['text'])
        assert got['id'] == json.loads(text)['id'], 'the page answered for another bundle'
        return got['results']

    def run_in_page(self, kind):
        """What the page gave for one kind of case."""
        if not self.alive:
            self.skipTest('no page answered: nobody is there to open the tab')
        return self.results[kind]

    def test_T1_the_filter_language_of_the_table_engine_reads_numbers_text_ranges_and_refuses_a_mistake(self):
        got = self.run_in_page('filter')
        want = [True, False, True, True, True, True, True, True, True, False, True, True, True, False, False, True, True, True]
        self.assertEqual(got[:len(want)], want)
        self.assertTrue(all(isinstance(x, str) and x.startswith('error') for x in got[len(want):-1]), got)    # '>3 &' and '[a' are refused
        self.assertIs(got[-1], True)                                                                        # ? is one character

    def test_T2_the_pie_of_an_item_is_svg_slices_clockwise_from_twelve_with_a_dot_a_pie_diameter_before_it(self):
        full, half, mixed, empty, grey = self.run_in_page('pie')
        self.assertEqual((full.count('<circle'), full.count('<path'), '#1a7f37' in full), (1, 0, True))     # one slice is a whole circle
        self.assertEqual((half.count('<path'), '#1a7f37' in half, '#d98200' in half, half.count('<circle')), (2, True, True, 0))
        self.assertIn('A7 7 0 0 1', half.split('<path')[1])                                                # a half is not the large arc ...
        self.assertEqual(mixed.count('<path'), 4)                                                          # ... four slices ...
        self.assertIn('A7 7 0 1 1', mixed.split('<path')[1])                                               # ... the first is over half
        self.assertEqual(mixed.count('<circle'), 1)                                                        # the proof dot: one small circle ...
        self.assertTrue(mixed.split('<circle')[1].startswith(' cx="-8" cy="8" r="2.6" fill="#c0392b"'), mixed)   # ... before the pie
        self.assertIn('stroke="#bbb"', empty)                                                              # nothing to judge: a ring
        self.assertEqual((grey.count('<circle'), '#1a7f37' in grey.split('<circle')[1], '#b0b0b0' in grey), (2, True, True))

    def test_T3_a_signal_for_one_block_goes_to_the_nearest_of_each_kind_or_to_the_list_or_to_all(self):
        got = self.run_in_page('route')
        who = [[row[0] for row in one['log']] for one in got]
        self.assertEqual(who[:6], [['cd2'], ['cd1'], ['cd1'], ['cd0'], ['cd2'], ['cd0', 'cd2']])
        self.assertEqual(sorted(who[6]), ['cd2', 'ml2'])                      # one code, one methods: those nearest eb
        self.assertEqual(who[7], ['cd1'])                                      # addressed
        self.assertEqual(sorted(who[8]), ['cd1', 'cd2'])                       # not routed, not addressed: everyone

    def test_T4_a_file_goes_to_the_container_before_a_lone_block_else_to_a_new_tab_and_closes_where_it_is_shown(self):
        got = self.run_in_page('route')
        self.assertEqual(got[9]['log'], [['tt', 'showfile', {'path': './a.py', 'show': True, 'to': ['tt']}]])     # the container
        self.assertEqual([row[0] for row in got[10]['log']], ['cd1'])                                           # the first lone block
        self.assertEqual([row[0] for row in got[11]['log']], ['cd2'])                                           # addressed
        self.assertEqual((got[12]['log'], len(got[12]['tabs'])), ([], 1))                                       # nothing takes it: a tab
        self.assertEqual((got[13]['log'], got[13]['tabs']), ([], ['/?layout=[doc]&doc=r.html']))                # html: a tab
        self.assertEqual(got[14]['log'], [['tt', 'showfile', {'path': './a.py', 'show': False, 'to': ['tt']}]])   # closed where shown
        self.assertEqual([row[0] for row in got[15]['log']], ['cd2'])                                           # ftv{cd2}
        self.assertEqual(len(got[16]['tabs']), 1)                                    # a name of mng is the manager's: it took it

    def bench_make_the_text_of_a_bundle(self, timer):          # (not a snap: every snap is a line of the server's log)
        with timer as test:
            while test.more:
                for _ in test.count:
                    bundle(*self.parts)
        return 'the text of a bundle: the code under test, the test code and the cases as JSON', 'bundle'
