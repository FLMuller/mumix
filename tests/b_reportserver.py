r"""b_reportserver.py -- tests and benchmarks for reportserver: who asked (BY) in the log,
status(), stop() logging before the kill, ensure() and the bat's place. A fake listener stands
in for a running server, so nothing real is started or stopped except one throwaway daemon on a
free port in a temp folder (test_T11).

Run from the project root:
    python tools/runbench.py b_reportserver
"""
import atexit
import contextlib
import io
import os
import shutil
import socket
import subprocess
import sys
import tempfile
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

SOURCES = ['reportserver']
import reportserver


class Fake:
    """A listener on a free port. ours=True answers the report server's handshake the way the
    real one does; ours=False answers like some other program."""

    def __init__(me, ours=True):
        me.sock = socket.socket()
        me.sock.bind(('127.0.0.1', 0))
        me.sock.listen(8)
        me.port = me.sock.getsockname()[1]
        me.ours = ours
        threading.Thread(target=me.loop, daemon=True).start()

    def loop(me):
        reply = (b'HTTP/1.1 101 Switching\r\nServer: reportserver/1\r\n\r\n' if me.ours
                 else b'HTTP/1.1 200 OK\r\n\r\n')
        while True:
            try:
                conn, _ = me.sock.accept()
            except OSError:
                return
            with conn:
                conn.settimeout(1)
                try:
                    conn.recv(512)
                    conn.sendall(reply)
                except OSError:
                    pass

    def close(me):
        me.sock.close()


def free_port():
    """A port nothing listens on now."""
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def said(fn, *args, **kwargs):
    """(result, what it printed) of a call; a SystemExit is returned as the result."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        try:
            got = fn(*args, **kwargs)
        except SystemExit as stop:
            got = stop
    return got, out.getvalue()


def text_of(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


class b_reportserver(bench):
    BenchName = 'reportserver'
    BenchVersion = 'M1.0.4'          # runbench adds 1 to the last number on every run
    BenchHeader = 'who asked in the log, status, stop, ensure, the bat'
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        cls.tmp = os.path.realpath(tempfile.mkdtemp(prefix='rs_'))
        atexit.register(shutil.rmtree, cls.tmp, True)
        cls.roots = os.path.join(cls.tmp, 'reportserver.roots')
        cls.log = os.path.join(cls.tmp, 'reportserver.log')
        cls.pid = os.path.join(cls.tmp, 'reportserver.pid')
        with open(cls.roots, 'w', encoding='utf-8') as f:
            f.write('C:\\one\nC:\\two\n\n')
        with open(cls.log, 'w', encoding='utf-8') as f:
            f.write('2026-11-03 01:00:00 first\n2026-11-03 01:00:01 last line\n\n')
        with open(cls.pid, 'w') as f:
            f.write('4242')

    def files(self, name):
        """A roots, log and pid file of their own, in a fresh folder."""
        folder = tempfile.mkdtemp(prefix=name + '_', dir=self.tmp)
        return tuple(os.path.join(folder, 'reportserver.' + kind) for kind in ('roots', 'log', 'pid'))

    # ---- the label of who asked ----
    def test_T1_by_accepts_a_name_and_a_time(self):
        for by in ('claude', 'claude 2026-11-03-01;43;12', 'user', 'a.b_c-d:e'):
            self.assertEqual(reportserver.check_by(by), by)

    def test_T2_by_refuses_what_a_log_or_a_command_cannot_hold(self):
        for by in ('', ' '.join(['x'] * 40), 'a"b', 'a&b', 'a|b', 'a%b', 'a^b', 'a\nb', None, 5):
            with self.assertRaises(ValueError, msg=repr(by)):
                reportserver.check_by(by)

    def test_T3_start_and_stop_need_by_on_the_command_line(self):
        for word in ('--start', '--stop'):
            got, _ = said(reportserver.main, [word])
            self.assertIsInstance(got, SystemExit)
            self.assertIn('--by', str(got))
        got, _ = said(reportserver.main, ['--start', '--by', 'a"b'])
        self.assertIsInstance(got, SystemExit)
        got, _ = said(reportserver.main, ['--zzz'])
        self.assertIn('unknown argument', str(got))

    # ---- status ----
    def test_T4_status_of_a_running_server(self):
        fake = Fake()
        try:
            got = reportserver.status(fake.port, self.roots, self.log, self.pid)
        finally:
            fake.close()
        self.assertEqual(got['state'], 'ours')
        self.assertEqual(got['pid'], 4242)
        self.assertEqual(got['roots'], 2)
        self.assertEqual(got['last'], '2026-11-03 01:00:01 last line')
        self.assertAlmostEqual(got['since'], os.path.getmtime(self.pid), places=3)
        self.assertEqual(got['port'], fake.port)

    def test_T5_status_when_nothing_runs_and_nothing_is_there(self):
        roots, log, pid = self.files('none')
        got = reportserver.status(free_port(), roots, log, pid)
        self.assertEqual(got, {'state': None, 'pid': None, 'since': None, 'port': got['port'],
                               'roots': 0, 'last': ''})

    def test_T6_status_tells_another_program_from_ours(self):
        fake = Fake(ours=False)
        try:
            got = reportserver.status(fake.port, self.roots, self.log, self.pid)
        finally:
            fake.close()
        self.assertEqual(got['state'], 'other')

    def test_T7_status_on_the_command_line_prints_key_value_lines(self):
        roots, log, pid = self.files('cli')
        got, out = said(reportserver.main, ['--status', '--port', str(free_port()),
                                            '--roots', roots, '--log', log, '--pid', pid])
        self.assertEqual(got, 0)
        self.assertIn('state=none', out.splitlines())
        self.assertIn('roots=0', out.splitlines())

    def test_T7b_register_on_the_command_line_adds_a_folder_once(self):
        roots, _, _ = self.files('reg')
        folder = os.path.join(self.tmp, 'toread')
        os.makedirs(folder)
        got, out = said(reportserver.main, ['--register', folder, '--roots', roots])
        self.assertEqual(got, 0)
        self.assertIn('registered', out)
        got, out = said(reportserver.main, ['--register', folder, '--roots', roots])
        self.assertIn('already registered', out)
        self.assertEqual(text_of(roots).split('\n').count(folder), 1)
        got, _ = said(reportserver.main, ['--register', os.path.join(self.tmp, 'nope'),
                                          '--roots', roots])
        self.assertIsInstance(got, SystemExit)

    # ---- stop ----
    def test_T8_stop_logs_who_before_it_kills(self):
        fake = Fake()
        roots, log, pid = self.files('stop')
        victim = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
        try:
            with open(pid, 'w') as f:
                f.write(str(victim.pid))
            line = reportserver.stop('claude 2026-11-03-01;43;12', pid, fake.port, log)
            victim.wait(timeout=10)
        finally:
            victim.kill()
            fake.close()
        self.assertIn(f'stopped (pid {victim.pid})', line)
        self.assertIn(f'stop requested by claude 2026-11-03-01;43;12, pid {victim.pid}',
                      text_of(log))

    def test_T9_stop_with_no_pid_file_or_a_stale_one_logs_nothing(self):
        roots, log, pid = self.files('nostop')
        self.assertIn('nothing to stop', reportserver.stop('claude', pid, free_port(), log))
        with open(pid, 'w') as f:
            f.write('4242')
        self.assertIn('stale pid file removed', reportserver.stop('claude', pid, free_port(), log))
        self.assertFalse(os.path.exists(pid))
        self.assertFalse(os.path.exists(log))

    def test_T10_stop_and_start_refuse_a_bad_by(self):
        with self.assertRaises(ValueError):
            reportserver.stop('a"b')
        with self.assertRaises(ValueError):
            reportserver.start('')

    # ---- start: one throwaway daemon ----
    def test_T11_a_started_daemon_logs_who_and_stop_logs_who(self):
        roots, log, pid = self.files('daemon')
        port = free_port()
        by = 'test 2026-11-03-01;50;00'
        try:
            first = reportserver.start(by, port, roots, log, pid)
            again = reportserver.start('someone else', port, roots, log, pid)
            self.assertIn('started', first)
            self.assertEqual(again, 'report server: running')
            self.assertIn(f'port {port}, by {by}', text_of(log))
        finally:
            reportserver.stop('test end', pid, port, log)
        self.assertIn('stop requested by test end', text_of(log))
        for _ in range(30):                                  # the port is let go once it ends
            if reportserver.running(port) is None:
                break
            time.sleep(0.1)
        self.assertIsNone(reportserver.running(port))

    def test_T12_start_leaves_another_programs_port_alone(self):
        fake = Fake(ours=False)
        try:
            line = reportserver.start('claude', fake.port, *self.files('other'))
        finally:
            fake.close()
        self.assertIn('used by another program', line)

    # ---- ensure ----
    def test_T13_ensure_does_nothing_when_the_server_runs(self):
        fake = Fake()
        try:
            self.assertEqual(reportserver.ensure('runbench', fake.port), 'report server: running')
        finally:
            fake.close()

    def test_T14_ensure_starts_the_daemon_itself_for_a_port_that_is_not_the_default(self):
        seen = []
        real = reportserver.start
        reportserver.start = lambda *args: seen.append(args) or 'started'
        try:
            files = self.files('ensure')
            got = reportserver.ensure('vcomment', free_port(), *files)
        finally:
            reportserver.start = real
        self.assertEqual(got, 'started')
        self.assertEqual(seen[0][0], 'vcomment')
        self.assertEqual(seen[0][2:], files)

    def test_T15_ensure_refuses_a_bad_by(self):
        with self.assertRaises(ValueError):
            reportserver.ensure('a"b')

    # ---- the bat and the folders ----
    def test_T16_the_bat_is_found_in_vscripts_or_not_at_all(self):
        path = reportserver.bat_path()
        if path:
            self.assertTrue(os.path.isfile(path))
            self.assertTrue(path.endswith(os.path.join('.claude', 'vscripts', 'reportserver.bat')))
        else:
            self.assertEqual(path, '')

    def test_T17_prepare_registers_the_folder_and_writes_no_bat(self):
        folder = os.path.join(self.tmp, 'results')
        os.makedirs(folder)
        roots, _, _ = self.files('prep')
        got = reportserver.prepare(folder, roots)
        self.assertEqual(got, reportserver.bat_path())
        self.assertIn(folder, text_of(roots).split('\n'))
        self.assertEqual(os.listdir(folder), [])
        self.assertFalse(hasattr(reportserver, 'write_bats'))

    def bench_check_by(self, timer):
        with timer as test:
            while test.more:
                for _ in test.count:
                    reportserver.check_by('claude 2026-11-03-01;43;12')
        return 'check_by', 'label'

    def bench_status_of_a_running_server(self, timer):
        fake = Fake()
        try:
            with timer as test:
                while test.more:
                    for _ in test.count:
                        reportserver.status(fake.port, self.roots, self.log, self.pid)
        finally:
            fake.close()
        return 'status (socket, 3 files)', 'status'
