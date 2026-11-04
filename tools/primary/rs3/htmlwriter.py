r"""htmlwriter.py -- write HTML into a byte array and fill a template with it. Plain functions:
`htm` is a bytearray that the writers append to and return.

    from htmlwriter import htmwrite, htmwriteln, htmappend, htmtemplate, htmsave
    htm = htmwriteln(None, '<p>', 'text', '</p>')          # the writers are mdwriter's
    page = htmtemplate('page.html', htm, TITLE='Report')   # the finished page, a bytearray
    htmsave(page, 'results/report.html')

htmwrite(htm, *args) -> htm      append the args, a space between them, no line end
htmwriteln(htm, *args) -> htm    the same, then a new line
htmappend(htm, *args) -> htm     append the args with nothing between them
    The arguments are as mdwriter's: lists are columns, numbers are written in engineering
    form, a None htm or an int starts a new bytearray.

htmtemplate(filename, htm, **keys) -> bytearray
    Fill the template file. A template has places written {{name}}; each is filled once, in
    one pass, so a value that holds {{x}} leaves a {{x}} in the page (a place for the next
    program to fill). A place is filled by
      a section of htm: marked (md2htm) starts one at each <!--SECTION name--> comment; the
                        text before the first comment is the section named _\main/_ ;
      a key:            htmtemplate(..., TITLE='x'): str, bytes or a number;
                        the keys css and js are the NAMES of files, whose text is put in.
    A place with nothing to fill it raises KeyError, and a section or key that no place
    uses raises ValueError: the page has no {{ }} left except those a value brought in.

htmsave(htm, filename) -> filename
    Write htm to a new file; FileExistsError if there is one (the caller picks another name).

VERSION  M2 m02.v01 (2026-10-28): rebuilt: the writers, htmtemplate and htmsave only. The tabs,
         the series names and the token moved to the page (js) and runbench3; the old module
         is zprev/htmlwriter.py.
"""
import re

from use import load

load('mdwriter')                     # mdappend, mdwrite, mdwriteln, compiled: use finds mdwriter.pyx beside this file

__all__ = ['htmwrite', 'htmwriteln', 'htmappend', 'htmtemplate', 'htmsave']

SECTION = re.compile(rb'<!--SECTION (.*?)-->\n?')
PLACE = re.compile(rb'\{\{([^{}\n]+)\}\}')
MAIN = '_\\main/_'
FILES = ('css', 'js')


def htmwrite(htm, *args):
    return mdwrite(htm, *args)


def htmwriteln(htm, *args):
    return mdwriteln(htm, *args)


def htmappend(htm, *args):
    return mdappend(htm, *args)


def htmtemplate(filename, htm, **keys):
    with open(filename, 'rb') as f:
        page = f.read()
    parts = SECTION.split(bytes(htm))
    found = {}
    if parts[0].strip():
        found[MAIN] = parts[0]
    for i in range(1, len(parts), 2):
        found[parts[i].decode('utf-8')] = parts[i + 1]
    for name in FILES:
        if name in keys:
            with open(keys[name], 'rb') as f:
                keys[name] = f.read()
    used = set()

    def fill(m):
        name = m.group(1).decode('utf-8')
        if name in found:
            used.add(name)
            return found[name]
        if name in keys:
            used.add(name)
            value = keys[name]
            return bytes(value) if isinstance(value, (bytes, bytearray)) else str(value).encode()
        raise KeyError(f'htmtemplate: {filename} has {{{{{name}}}}} and nothing to fill it')

    out = PLACE.sub(fill, page)
    spare = (set(found) | set(keys)) - used
    if spare:
        raise ValueError(f'htmtemplate: {filename} has no place for {sorted(spare)}')
    return bytearray(out)


def htmsave(htm, filename):
    with open(filename, 'xb') as f:
        f.write(htm)
    return filename
