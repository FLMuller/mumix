r"""pane_editbox.py -- the comment box: write, change or remove the comment on lines of the file shown.

    write() -> {label, css, js, html}

Signals
    receives  onCommentline {path, base, line, where}    a comment above that line (a new one)
              onCommentselect {path, base, first, last, tag, text, where}   change that comment
              onClosefile {path, where}                  forget a comment of that file
              onWithconfig {}                            the settings changed: a new comment takes the new user id
    emits     saved {path, where}   the server wrote the file: the code and methods read it again
              notice {text, bad}    what the box says (saving, saved, a refusal): the status bar shows it
IN and OUT below are these names. The comment saves itself 600 ms after the typing stops (the Save
button and Ctrl+Enter do it at once): insert the first time, update after that, on the lines the
server answered; what is typed while a save runs is saved when that one is done. A save sends
insert or update (rs3comment) with the sha1 `base` the code read the file at, and keeps the base
of each answer; the server refuses an edit if the file has changed since. Remove sends update
with an empty text. The box only shows who the comment is from: the user id is the settings menu's
(`initials`, in the status bar's menu), and a new comment follows it when it changes; a comment
of Claude's (tag cld) or of another user is changed under its own tag. The row under the text is the
user id and what the box is doing (saving, saved, a refusal) on the left, and Save and Remove on the right.

VERSION  M1 m01.v04 (2026-11-04): its size is returned by write(): no module constant.
         M1 m01.v03 (2026-11-04): the user id is shown, not typed (the settings menu owns it); Save and
         Remove at the right; its own height, 42 mm, in a column.
         M1 m01.v02 (2026-11-03): the comment saves itself (as the old page's editor did).
         M1 m01.v01 (2026-11-03): first version.
"""
from rs3util import asset, done

__all__ = ['write']

IN = ['commentline', 'commentselect', 'closefile', 'withconfig']
OUT = ['saved', 'notice']


def write(S=None, page=None, loc=None):
    return done('editbox', asset(__file__, 'css'), asset(__file__, 'js'),
                '<div class="editbox"><div class="etarget">click the number of a line to write a '
                'comment on it, or a comment to change it (Markdown)</div>'
                '<textarea class="etext" placeholder="comment"></textarea>'
                '<div class="ebtn"><span class="euser" title="who the comment is from: the user id of the settings menu"></span>'
                '<span class="estate"></span><span class="gap"></span>'
                '<button class="esave">Save</button><button class="eremove">Remove</button></div></div>', height=42)
