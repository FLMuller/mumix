r"""rs3core.py -- the verbs about the server itself, run for rs3.py.

    ping      {do: 'ping'}                   -> {ok, pong: 1, boot, time}
    hello     {do: 'hello', hash | path | url}  -> {hash, path, id, boot, time}
              a page says which page it is: a hash (from the page itself), a ./ file path, or the
              address it was served from (/reportserver, /code/...). The server then sends
              commands to that connection by the hash. It says so again after every reconnect.
    config    {do: 'config', change?: {...}} -> {ok, config: {...}}
              the settings the pages share, after a change (a dict of some of them) is applied;
              refused, and nothing changed, if any value is not allowed: font, size 6-40,
              initials 1-8 letters or digits, linenos and wrap true or false, tabwidth 1-16,
              color #rrggbb
    status    {do: 'status'}                 -> {ok, status: {...}}
              boot, pid, port, started, uptime, pages, connections, the program that started it
    pulse     {do: 'pulse', since}           -> {ok, boot, time, status, rows: [[row, time, text]]}
              the status and the log lines after row `since` (at most 500 a call): what the
              monitor page asks about once a second. A new boot id says the server restarted.
    stop      {do: 'stop'}                   -> {ok}
    restart   {do: 'restart'}                -> {ok}
              the server ends (restart: a new one is started that takes the port over) a moment
              after the reply; every page is told {bye: 'stop'|'restart'} first. Only a program
              or the monitor page (/reportserver) may ask.
    snap      {do: 'snap', to, sel?}         -> what the page answers
    trigger   {do: 'trigger', to, sel}       -> what the page answers
              `to` is a page's path; snap asks that page to post an SVG of itself and answer
              with its path; trigger asks it to press the button `sel`. The server only carries
              them: it sends the command to every page connection that said hello with that
              path's hash, and the answer {re: id, ...} is the reply. Only a program may give
              them. No such page is an answer at once.

This module holds no state of its own: rs3.py hands each verb the server's state, S (S['conn']
is the connection the message came from, during the call), and the settings file is
S['config_file'].

VERSION  M2 m01.v01 (2026-11-03): rs3: hello by hash or address, status, pulse, stop, restart.
         (rs2 rscore m02.v01: load, snap and trigger.)
"""
import json
import os
import re
import subprocess
import sys
import time

from rs3files import path_hash, register, scope_of

DEFAULTS = {'font': 'Consolas', 'size': 12, 'initials': 'user', 'linenos': True,
            'tabwidth': 4, 'wrap': False, 'color': '#e8650f'}
PULSE_ROWS = 500


def ping(msg, S):
    """Awake? The id of this start (boot) and the server's time say which server it is."""
    return {'pong': 1, 'boot': S['boot'], 'time': time.time()}


def hello(msg, S):
    """A page says which page it is. The reply's hash is the same after every reconnect."""
    import rs3pages
    conn = S['conn']
    if conn['origin'] is None:
        return {'ok': False, 'error': 'hello comes from a page, not from a program'}
    page = None
    if isinstance(msg.get('url'), str):
        page = rs3pages.register_url(S, msg['url'])
    elif isinstance(msg.get('path'), str):
        page = register(S, msg['path'])
    elif isinstance(msg.get('hash'), str):
        page = S['pages'].get(msg['hash'])
    if page is None:
        return {'ok': False, 'error': 'not a page this server knows'}
    conn['hash'] = page['hash']
    return {'hash': page['hash'], 'path': page['path'], 'id': page['id'], 'boot': S['boot'],
            'time': time.time()}


def allowed(key, value):
    """May the setting key take this value?"""
    number = isinstance(value, int) and not isinstance(value, bool)
    if key == 'font':
        return isinstance(value, str) and bool(re.fullmatch(r'[\w .\-]{1,60}', value))
    if key == 'size':
        return number and 6 <= value <= 40
    if key == 'tabwidth':
        return number and 1 <= value <= 16
    if key == 'initials':
        return isinstance(value, str) and bool(re.fullmatch(r'\w{1,8}', value))
    if key in ('linenos', 'wrap'):
        return isinstance(value, bool)
    if key == 'color':
        return isinstance(value, str) and bool(re.fullmatch(r'#[0-9a-fA-F]{6}', value))
    return False


def settings(S):
    """The settings the pages share: the defaults and what the settings file changes."""
    try:
        with open(S['config_file'], encoding='utf-8') as f:
            return {**DEFAULTS, **json.load(f)}
    except (OSError, ValueError):
        return dict(DEFAULTS)


def config(msg, S):
    path = S['config_file']
    have = settings(S)
    change = msg.get('change')
    if change is not None:
        if not isinstance(change, dict):
            return {'ok': False, 'error': 'change must be an object'}
        for key, value in change.items():
            if not allowed(key, value):
                return {'ok': False, 'error': f'config: {key!r} is not allowed that value'}
        have.update(change)
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(have, f)
        os.replace(tmp, path)
    return {'config': have}


def state(S):
    """What the monitor page shows of the server."""
    pages = [c for c in S['conns'].values() if c['upgraded'] and c['origin'] is not None]
    return {'boot': S['boot'], 'pid': os.getpid(), 'port': S['port'], 'started': S['started'],
            'uptime': time.time() - S['started'], 'pages': len(pages),
            'connections': len(S['conns']), 'by': S.get('by'), 'known': len(S['pages']),
            'version': 'rs3 M2 m01.v01'}


def status(msg, S):
    return {'status': state(S)}


def pulse(msg, S):
    since = msg.get('since')
    since = since if isinstance(since, int) and not isinstance(since, bool) else 0
    rows = [list(r) for r in S['log_ring']['rows'] if r[0] > since][:PULSE_ROWS]
    return {'boot': S['boot'], 'time': time.time(), 'status': state(S), 'rows': rows}


def may_stop(S):
    """A program may stop the server; a page only if it is the monitor page."""
    conn = S['conn']
    if conn['origin'] is None:
        return True
    page = S['pages'].get(conn.get('hash'))
    return bool(page and page.get('admin'))


def tell_pages(S, why):
    """Tell every page connection that the server is going: it shows 'stopped' and not 'lost'."""
    for conn in S['pages_of'](S):
        S['send'](conn, {'bye': why})


def stop(msg, S):
    if not may_stop(S):
        return {'ok': False, 'error': 'stop comes from a program or the monitor page'}
    S['say'](f'stop asked (by {"a program" if S["conn"]["origin"] is None else "the monitor page"})')
    tell_pages(S, 'stop')
    S['exit_at'] = time.time() + 0.4
    return {'stopping': True}


def restart(msg, S):
    if not may_stop(S):
        return {'ok': False, 'error': 'restart comes from a program or the monitor page'}
    S['say']('restart asked')
    flags = 0
    exe = sys.executable
    if os.name == 'nt':
        windowless = os.path.join(os.path.dirname(exe), 'pythonw.exe')
        exe = windowless if os.path.isfile(windowless) else exe
        flags = 0x00000008 | 0x00000200 | 0x08000000 | 0x00004000
    try:
        subprocess.Popen([exe, S['script'], '--serve', '--wait', '--by', 'restart'],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, creationflags=flags, close_fds=True)
    except OSError as error:
        return {'ok': False, 'error': f'could not start the new server: {error}'}
    tell_pages(S, 'restart')
    S['exit_at'] = time.time() + 0.4
    return {'restarting': True}


def command(verb):
    """A verb that is carried out by a page: sent to the connections that said (hello) they
    are the page `to`, and answered by one of them. Only a program may give one, never a page
    (a browser sends an Origin). A page nothing has loaded gives {ok: false, loaded: false},
    which contactRS turns into None."""
    def run(msg, S):
        if S['conn']['origin'] is not None:
            return {'ok': False, 'error': f'{verb} comes from a program, not from a page'}
        path = msg.get('to')
        if not isinstance(path, str) or not path.startswith(('./', '/')):
            return {'ok': False, 'loaded': False}
        return {'relay': {'do': verb, 'to': path, 'sel': msg.get('sel')},
                'to_hash': path_hash(path)}      # no file lookup: an unknown spelling is not loaded
    return run


VERBS = {'ping': ping, 'hello': hello, 'config': config, 'status': status, 'pulse': pulse,
         'stop': stop, 'restart': restart, 'snap': command('snap'),
         'trigger': command('trigger')}
