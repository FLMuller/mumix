r"""pane_serverstatus.py -- the state of the server, and its Restart and Stop buttons.

    write() -> {label, css, js, html}

Signals
    receives  onStatus {...}   the manager's word on the server, about once a second: the status
                               (boot, pid, port, started, uptime, pages, connections, by, known,
                               version), or {stopped: 'stop'} when the server was stopped, or
                               {lost: true, restarting} when the link dropped
    emits     nothing
Stop and Restart are verbs (rs3core); the server accepts them from this page only when the page
is the monitor (/reportserver). After a stop the page says so, and how to open the server again.
IN and OUT below are these names.

VERSION  M1 m01.v01 (2026-11-03): first version.
"""
from rs3util import asset, done

__all__ = ['write']

IN = ['status']
OUT = []

ROWS = ('port', 'pid', 'boot', 'started by', 'up for', 'pages open', 'connections', 'pages known',
        'version', 'time')


def write(S=None, page=None, loc=None):
    rows = ''.join(f'<tr><th>{name}</th><td data-k="{name}">-</td></tr>' for name in ROWS)
    return done('serverstatus', asset(__file__, 'css'), asset(__file__, 'js'),
                f'<div class="srv"><table>{rows}</table><div class="srvbtn">'
                '<button class="restart">Restart</button><button class="stop">Stop</button></div>'
                '<div class="srvmsg">connecting...</div></div>')
