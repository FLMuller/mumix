r"""rs3table.py -- the server's table of pages: one class.

    Pages()                    the table, S['pages']: a dict hash -> page, a page being
                               {id, hash, path, root, admin}
    pages.view(address, root=None, admin=False) -> page
                               put the page that is an address (made by the server, /reportserver, /code/mumix/x.py,
                               /?layout=...) in the table, or find it there. root is the real path of the root its
                               file lives in (None for a page with no file: its paths are from HOME, see rs3util)
    pages.known(hash) -> (page, None) | (None, why)
    Pages.hash_of(address) -> str   the hash of an address: sixteen hex digits of its sha1, the same every time, so a
                               restart loses nothing and a page that says hello again finds its place

A page is known by its hash. A page says hello after every reconnect (rs3core), and the server then sends commands to
the connections that said they are that page.

VERSION  M1 m01.v01 (2026-11-04): first version: entry, register_view and page_of of rs3files, as a class.
"""
import hashlib

__all__ = ['Pages']


class Pages(dict):
    def __init__(me):
        super().__init__()
        me.next_id = 1

    @staticmethod
    def hash_of(address):
        return hashlib.sha1(address.encode('utf-8')).hexdigest()[:16]

    def view(me, address, root=None, admin=False):
        key = me.hash_of(address)
        page = me.get(key)
        if page is None:
            page = {'id': me.next_id, 'hash': key}
            me.next_id += 1
            me[key] = page
        page['path'], page['root'], page['admin'] = address, root, admin
        return page

    def known(me, key):
        page = me.get(key) if isinstance(key, str) else None
        if page is None:
            return None, 'unknown page: it must say hello (or be loaded) first'
        return page, None
