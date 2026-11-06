"""
xlerrors -- the errors xlw4 raises, as one family under XlwError.

Why
    A caller catches XlwError for anything the writer refuses, or one subclass for the kind of
    refusal. The classes live apart from the model that raises them (xlbook) and the door that
    re-exports them (xlw), so neither imports the other for a name.

Use
    XlwNoBook    a verb needs a book and none exists (newbook first), or a book name is unknown
    XlwNoSheet   a book with no sheet was saved
    XlwBadArg    a bad argument: a dict to write, an unknown move direction, a name already taken,
                 a book or sheet named like a method
    All are caught by  except XlwError.

VERSION  M01 m01.v01 (2026-11-06): first version; the four classes of xlw's xlw.py.
"""

__all__ = ['XlwError', 'XlwNoBook', 'XlwNoSheet', 'XlwBadArg']


class XlwError(Exception):
    """Any refusal by xlw4; catch this one for all of them."""


class XlwNoBook(XlwError):
    """A verb needs a book and none exists, or a book name is unknown."""


class XlwNoSheet(XlwError):
    """A book with no sheet was saved."""


class XlwBadArg(XlwError):
    """A bad argument: a dict to write, an unknown direction, a name already taken."""
