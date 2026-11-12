r"""pane_editbox.py -- the comment box: write, change or remove the comment on lines of the file shown.

    write() -> {label, css, js, html}

Signals
    receives  onCommentline {path, base, line}    a comment above that line (a new one)
              onCommentselect {path, base, first, last, tag, text}   change that comment
              onShowcode {path, loc, on}                 on false: forget a comment of that file
              onWithconfig {}                            the settings changed: a new comment takes the new user id
              onNoteline {file, line}                    a note on that line of a page (a new one)       -- type note
              onNoteselect {file, line, code, text, who} change that note                                 -- type note
    emits     saved {path}   the server wrote the file: every code pane and methods that shows it reads it again
              notesaved {file, line, code}   a note was written (type note): the doc that holds the page asks for its notes again
              notice {text, bad}    what the box says (saving, saved, a refusal): the status bar shows it
The box has two types. Type code (the default, everything above) comments the lines of a file through rs3comment. Type note
(the page is an html file, whose doc block sends noteline and noteselect) writes a record to the page's .notes file through
the verb note_add of rs3microDB; the box autosaves it the same way, the first save makes the note's code, later saves send it back.
IN and OUT below are these names. The comment saves itself 600 ms after the typing stops (the Save
button and Ctrl+Enter do it at once): insert the first time, update after that, on the lines the
server answered; what is typed while a save runs is saved when that one is done. A save sends
insert or update (rs3comment) with the sha1 `base` the code read the file at, and keeps the base
of each answer; the server refuses an edit if the file has changed since. Remove sends update
with an empty text. The box only shows who the comment is from: the user id is the settings menu's
(`initials`, in the status bar's menu), and a new comment follows it when it changes; a comment
of Claude's (tag cld) or of another user is changed under its own tag. The row under the text is the
user id and what the box is doing (saving, saved, a refusal) on the left, and Save and Remove on the right.

VERSION  M1 m01.v08 (2026-11-12): type note: noteline, noteselect in, notesaved out (the notes of an html page, rs3microDB); the code type is unchanged.
         M1 m01.v07 (2026-11-04): says the server's note after a save (a comment written inside a string).
         M1 m01.v06 (2026-11-04): the text has no border, no focus outline and an orange caret; data-keepsel keeps the code's chosen line (the insertion caret) while it is clicked.
         M1 m01.v05 (2026-11-04): showcode in (forgets the comment of a file that goes), no where.
         M1 m01.v04 (2026-11-04): its size is returned by write(): no module constant.
         M1 m01.v03 (2026-11-04): the user id is shown, not typed (the settings menu owns it); Save and
         Remove at the right; its own height, 42 mm, in a column.
         M1 m01.v02 (2026-11-03): the comment saves itself (as the old page's editor did).
         M1 m01.v01 (2026-11-03): first version.
"""
from rs3util import asset, done

__all__ = ['write']

IN = ['commentline', 'commentselect', 'noteline', 'noteselect', 'showcode', 'withconfig']
OUT = ['saved', 'notesaved', 'notice']


def write(S=None, page=None, loc=None):
    return done('editbox', asset(__file__, 'css'), asset(__file__, 'js'),
                '<div class="editbox" data-keepsel><div class="etarget">click the number of a line to write a '
                'comment on it, or a comment to change it (Markdown)</div>'
                '<textarea class="etext" placeholder="comment"></textarea>'
                '<div class="ebtn"><span class="euser" title="who the comment is from: the user id of the settings menu"></span>'
                '<span class="estate"></span><span class="gap"></span>'
                '<button class="esave">Save</button><button class="eremove">Remove</button></div></div>', height=42)
