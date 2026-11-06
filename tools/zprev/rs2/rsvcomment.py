r"""rsvcomment.py -- the vcomment verbs: open a file as a commentable tab, and the comments.

Verbs (websocket; each takes the page's hash, whose root is the scope of the page: rsfiles.
Paths are ./ from the root of the server, like every path in a message)
    open    {do: 'open', hash, path, label?}        -> {ok, html}
            the tab of one file under the page's root: colouring, comment threads, function
            list. The tab holds the file's ./ path (data-path), which a page sends back
    check   {do: 'check', hash, filename}           -> {ok}
            may comments be added to that file (a kind vcomment opens, inside the root)?
    update  {do: 'update', hash, filename, first, last, base, tag, text}
                                                    -> {ok, base, first, last, delta, html, removed}
            change the comment on lines first-last; empty text removes it
    insert  {do: 'insert', hash, filename, line, base, tag, text}   (the same reply)
            add a comment above a line
A refusal is {ok: false, error}. The same four verbs serve a report page and a vcomment page:
an edit is written only if the file's sha1 is `base` (what the page read), only comment lines
change, and the comment marker is the file's language's (vclang), whatever the page sends.

The work is vcserver.py's (with vclang.py and vcode.py), which stay where they are and are
imported here: this module turns ./ paths into the real ones they take, and their reply text
into dicts, and finds the root from the hash.

VERSION  M1 m02.v01 (2026-11-03): ./ paths in and out (the tab's data-path too).
         M1 m01.v01 (2026-11-03): first version: the four verbs over vcserver.
"""
import html
import json

import vcserver
from rsfiles import page_of, real_of, relative


def run(function, S, msg, shaped, path):
    """Call a vcserver function for the page of msg's hash. `path` is the ./ path the message
    names; shaped is the old-shaped message, which gets the real path where it needs one."""
    page, why = page_of(S, msg.get('hash'))
    if page is None:
        return {'ok': False, 'error': why}
    real = real_of(S, path)
    if real is None:
        return {'ok': False, 'error': f'{path!r} is not a ./ path inside the root'}
    got = json.loads(function(S['say'], shaped(real), page['root']))
    if not isinstance(got, dict):                 # vcserver refuses with [] and logs why
        return {'ok': False, 'error': f'{msg.get("do")} was refused (see the log)'}
    if 'html' in got:                             # the tab names its file: ./ from the root
        got['html'] = got['html'].replace(html.escape(real), relative(S, real))
    return got


def open_file(msg, S):
    path = msg.get('path')
    return run(vcserver.open_reply, S, msg, lambda real: {'open': real, 'label': msg.get('label')},
               path)


def check(msg, S):
    path = msg.get('filename')
    return run(vcserver.live_check, S, msg, lambda real: {'check': True, 'filename': real}, path)


def update(msg, S):
    path = msg.get('filename')
    return run(vcserver.live_edit, S, msg, lambda real: {**msg, 'filename': real, 'update': True},
               path)


def insert(msg, S):
    path = msg.get('filename')
    return run(vcserver.live_edit, S, msg, lambda real: {**msg, 'filename': real, 'insert': True},
               path)


VERBS = {'open': open_file, 'check': check, 'update': update, 'insert': insert}
