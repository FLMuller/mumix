r"""rs3util.py -- the few helpers the blocks (pane_NAME.py) share.

    asset(file, ext) -> str     the text of a file that sits beside a block: asset(__file__, 'js')
                                reads pane_code.js for pane_code.py ('' if there is none)
    done(label, css, js, html)  the dict a block's write() returns: {label, css, js, html}
    split_package(html) -> (html, css, js)   a static page as the server takes it apart: every
                                <style> and <script> without a src comes out, in order, and
                                the rest is the html that goes in the block's place

A block is a Python function write(*data) -> {css, js, html}. Its css and js are labelled with the
block's name; a page that holds two blocks of one kind carries that css and js once.

VERSION  M1 m01.v01 (2026-11-03): first version.
"""
import os
import re

__all__ = ['asset', 'done', 'split_package']

STYLE = re.compile(r'<style\b[^>]*>(.*?)</style\s*>', re.S | re.I)
SCRIPT = re.compile(r'<script\b(?![^>]*\bsrc\s*=)[^>]*>(.*?)</script\s*>', re.S | re.I)


def asset(file, ext):
    """The text of the file beside `file` with the same name and the extension `ext`."""
    path = os.path.splitext(os.path.abspath(file))[0] + '.' + ext
    try:
        with open(path, encoding='utf-8') as f:
            return f.read()
    except OSError:
        return ''


def done(label, css='', js='', html=''):
    """What write() returns."""
    return {'label': label, 'css': css, 'js': js, 'html': html}


def split_package(html):
    """(html without them, all the css, all the js) of a page that carries its own <style> and
    <script> blocks, wherever they sit. The ideal package has one of each; more are joined in
    order. A script with a src is left where it is (it cannot be collated)."""
    css = '\n'.join(m.group(1).strip() for m in STYLE.finditer(html))
    js = '\n'.join(m.group(1).strip() for m in SCRIPT.finditer(html))
    return SCRIPT.sub('', STYLE.sub('', html)), css, js
