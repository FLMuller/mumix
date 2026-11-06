"""
xltext -- the text conversions every part of xlw4 shares: XML out and in, numbers, names, columns.

Why
    Writers and readers all build or take apart small XML strings, quote text, turn numbers
    into text and columns into letters. One module holds them, so no codec carries its own copy.

Algorithm
    tag builds an element from a name, a body and keyword attributes, so a writer is a nest
    of calls that reads like the markup: tag('c:idx', val=3) is <c:idx val="3"/>. An attribute
    whose value is None is left out; a bool is 1 or 0; a number goes through xml_text; text is
    escaped. xml_text also deletes the control characters XML 1.0 cannot carry (Excel refuses a
    file holding one) and writes numbers as 11 and not 11.0, else as repr (exact on reading back).
    parse_xml reads a part with every namespace removed from tags and attribute names, so a
    reader writes 'ser' and 'id' and not '{...}ser'. safe_name makes a tree key from a name.
    column converts both ways, bijective base 26: 1 = A, 26 = Z, 27 = AA.
    Cost: O(length) per call.

Use
    tag('c:smooth', val=True)                 -> '<c:smooth val="1"/>'
    tag('a:t', xml_text(text))                -> '<a:t>text</a:t>'
    tag('c:ser', tag('c:idx', val=0), **{'r:id': 'rId1'})   # an attribute with a colon
    xml_text(0.1)  xml_text('a<b')            -> '0.1'  'a&lt;b'
    safe_name('my sheet')                     -> 'my_sheet'; a name that starts with a non-letter gets 's_'
    column(28) -> 'AB';  column('AB') -> 28   (also bytes, b'AB')
    parse_xml(bytes_or_text) -> the root element

VERSION  M01 m01.v01 (2026-11-06): first version, from the helpers of xlw's xlstyle, xlparts and xlchart.
"""

import xml.etree.ElementTree as ET

__all__ = ['tag', 'xml_text', 'parse_xml', 'safe_name', 'column']

# One table for both jobs, so a string is translated once: control characters go, five characters
# become entities.
TABLE = {**dict.fromkeys(list(range(0, 9)) + [11, 12] + list(range(14, 32))),
         **{ord(char): entity for char, entity in (('&', '&amp;'), ('<', '&lt;'), ('>', '&gt;'),
                                                   ('"', '&quot;'), ("'", '&apos;'))}}


def xml_text(value):
    """A value as XML text: a number as 11 not 11.0 and otherwise as the shortest text that reads
    back to the same float, a bool as 1 or 0, anything else escaped, with the control characters
    XML cannot carry removed."""
    if type(value) is str:
        return value.translate(TABLE)
    if isinstance(value, bool):
        return '1' if value else '0'
    if isinstance(value, int):
        return str(int(value))
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() and abs(value) < 1e15 else repr(value)
    return str(value).translate(TABLE)


def tag(element, /, *body, **attrs):
    """The element `element` with the attributes given (None leaves one out) and the body
    strings joined inside; with no body it is self-closing."""
    text = ''.join(f' {key}="{xml_text(value)}"' for key, value in attrs.items()
                   if value is not None)
    inner = ''.join(body)
    return f'<{element}{text}>{inner}</{element}>' if inner else f'<{element}{text}/>'


def parse_xml(data):
    """The root element of an XML part (bytes or text) with every namespace removed from tags
    and attribute names; an attribute 'r:id' becomes 'id'."""
    root = ET.fromstring(data)
    for element in root.iter():
        element.tag = element.tag.rsplit('}', 1)[-1]
        for key in [key for key in element.attrib if key.startswith('{')]:
            element.attrib[key.rsplit('}', 1)[-1]] = element.attrib.pop(key)
    return root


def safe_name(name):
    """A sheet or book name as a tree key: letters, digits and _, starting with a letter
    (a name that does not gets the prefix s_)."""
    text = ''.join(char if char.isascii() and char.isalnum() or char == '_' else '_'
                   for char in str(name))
    return text if text[:1].isascii() and text[:1].isalpha() else 's_' + text


def column(value):
    """A column number as letters, or letters (str or bytes) as the column number: bijective
    base 26, so 1 = A, 26 = Z and 27 = AA."""
    if isinstance(value, int):
        letters = ''
        while value > 0:
            value, rest = divmod(value - 1, 26)
            letters = chr(65 + rest) + letters
        return letters
    number = 0
    for char in value if isinstance(value, bytes) else value.encode():
        number = number * 26 + char - 64
    return number
