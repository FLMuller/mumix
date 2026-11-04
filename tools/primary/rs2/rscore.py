r"""rscore.py -- the verbs about the server itself, run for rs2.py.

    ping                  {do: 'ping'}                  -> {ok, pong: 1}
    config                {do: 'config', change?: {...}} -> {ok, config: {...}}
                          the settings the pages share, after a change (a dict of some of
                          them) is applied; refused, and nothing changed, if any value is
                          not allowed: font, size 6-40, initials 1-8 letters or digits,
                          linenos and wrap true or false, tabwidth 1-16, color #rrggbb

    load                  {do: 'load', path, show?}     -> {ok, hash, url, id}
                          open a page in the default browser (show false: only answer)
    snap                  {do: 'snap', to, sel?}        -> what the page answers
    trigger               {do: 'trigger', to, sel}      -> what the page answers
                          `to` is a page's hash. snap asks that page to post an SVG of itself
                          and answer with its path; trigger asks it to press the button `sel`.
                          The server only carries them: it sends the command to every page
                          connection (those that sent an Origin), the page it names answers
                          {re: id, ...}, and that answer is the reply. A page may not give
                          them, only a program; no page connected is an answer at once.

This module holds no state of its own: rs2.py hands each verb the server's state, S (S['conn']
is the connection the message came from, during the call), and the settings file is
S['config_file'].

VERSION  M1 m02.v01 (2026-11-03): load, snap and trigger.
         M1 m01.v01 (2026-11-03): first version: ping and config (config as in reportserver.py).
"""
import json
import os
import re
import webbrowser
from urllib.parse import quote

import time

from rsfiles import path_hash, register

HOST = '127.0.0.1'
DEFAULTS = {'font': 'Consolas', 'size': 12, 'initials': 'user', 'linenos': True,
            'tabwidth': 4, 'wrap': False, 'color': '#e8650f'}


def ping(msg, S):
    """Awake? The id of this start (boot) and the server's time say which server it is."""
    return {'pong': 1, 'boot': S['boot'], 'time': time.time()}


def hello(msg, S):
    """A page says which path it shows, so commands can be sent to it by that path. It says
    so again after every reconnect, and gets the same hash: a restart loses nothing."""
    conn = S['conn']
    if conn['origin'] is None:
        return {'ok': False, 'error': 'hello comes from a page, not from a program'}
    page = register(S, msg.get('path'))
    if page is None:
        return {'ok': False, 'error': 'not a path a page may show'}
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


def config(msg, S):
    path = S['config_file']
    try:
        with open(path, encoding='utf-8') as f:
            have = {**DEFAULTS, **json.load(f)}
    except (OSError, ValueError):
        have = dict(DEFAULTS)
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


def load(msg, S):
    """Open a page in the default browser: {do: 'load', path, show?} -> {hash, url, id}. The
    path is ./ from the root. show false only answers (a test uses it)."""
    page = register(S, msg.get('path'))
    if page is None:
        return {'ok': False, 'error': 'not a path a page may show'}
    url = f'http://{HOST}:{S["port"]}/' + quote(page['path'][2:], safe='/')
    if msg.get('show', True):
        try:
            webbrowser.open(url)
        except Exception as error:
            S['say'](f'load: the browser would not open {url}: {error!r}')
    return {'hash': page['hash'], 'url': url, 'id': page['id'], 'path': page['path']}


def command(verb):
    """A verb that is carried out by a page: sent to the connections that said (hello) they
    show the path `to`, and answered by one of them. Only a program may give one, never a page
    (a browser sends an Origin). A path nothing has loaded gives {ok: false, loaded: false},
    which contactRS turns into None."""
    def run(msg, S):
        if S['conn']['origin'] is not None:
            return {'ok': False, 'error': f'{verb} comes from a program, not from a page'}
        path = msg.get('to')
        if not isinstance(path, str) or not path.startswith('./'):
            return {'ok': False, 'loaded': False}
        return {'relay': {'do': verb, 'to': path, 'sel': msg.get('sel')},
                'to_hash': path_hash(path)}      # no file lookup: an unknown spelling is not loaded
    return run


VERBS = {'ping': ping, 'hello': hello, 'config': config, 'load': load,
         'snap': command('snap'), 'trigger': command('trigger')}
