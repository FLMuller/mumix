r"""pane_editbox.py -- the comment box: write, change or remove the comment on lines of the file shown.

    write() -> {label, css, js, html}

Signals
    receives  onCommentline {path, base, line, where}    a comment above that line (a new one)
              onCommentselect {path, base, first, last, tag, text, where}   change that comment
              onClosefile {path, where}                  forget a comment of that file
    emits     saved {path, where}   the server wrote the file: the code and methods read it again
IN and OUT below are these names. Save sends insert or update (rs3vcomment) with the sha1 `base`
the code read the file at; the server refuses an edit if the file has changed since. Remove
sends update with an empty text. The tag is the user's initials (the config's `initials`); a
comment of Claude's (tag cld) is changed under its own tag.

VERSION  M1 m01.v01 (2026-11-03): first version.
"""
from rs3util import asset, done

__all__ = ['write']

IN = ['commentline', 'commentselect', 'closefile']
OUT = ['saved']


def write(S=None, page=None, loc=None):
    return done('editbox', asset(__file__, 'css'), asset(__file__, 'js'),
                '<div class="editbox"><div class="etarget">click the number of a line to write a '
                'comment on it, or a comment to change it (Markdown)</div>'
                '<textarea class="etext" placeholder="comment"></textarea>'
                '<div class="ebtn"><label>tag <input class="etag" size="6"></label>'
                '<button class="esave">Save</button><button class="eremove">Remove</button>'
                '<span class="estate"></span></div></div>')
