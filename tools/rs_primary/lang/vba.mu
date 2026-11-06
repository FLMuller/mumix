# vba.mu -- how a VBA (and Visual Basic) file is coloured and commented

Made from matlab.mu (the same roles, ids and colours) and then adjusted. The header lines below the title are read by vclang.py:

- Comment: the triplet a reviewer's comment starts with. In VBA a line comment starts with one quote, so the triplet of three quotes is a comment the language ignores, and the server writes `<triplet><tag> text` lines and nothing else.
- Line comment, Quotes, Escape, Case: how the lexer reads it. VBA ignores case, so the word lists are lower case and the lexer folds each word.
- Function, Class: regular expressions whose first group is the name, for the function list.

Files: .vba .vb .bas .cls .frm
Mode: code
Comment: '''
Line comment: '
Quotes: "
Escape: double
Case: no
Function: (?i)^\s*(?:(?:Public|Private|Friend|Static)\s+)*(?:Function|Sub|Property\s+(?:Get|Let|Set))\s+(\w+)
Class: (?i)^\s*(?:(?:Public|Private)\s+)?(?:Type|Enum)\s+(\w+)

## Words

| List | Words |
|:--|:--|
| keyword | alias and as attribute byref byval call case class const declare dim do each else elseif end enum eqv event exit explicit for friend function get gosub goto if imp implements in is let lib like loop lset mod module new next not on option optional or paramarray preserve private property public raiseevent redim rem resume return rset select set static step stop sub then to type typeof until wend while with withevents xor |
| keyword constant | true false nothing empty null |
| builtin | abs array asc boolean byte cbool cbyte ccur cdate cdbl cdec chr cint clng clnglng csng cstr currency cvar date decimal dir doevents double err error format getobject hex inputbox instr instrrev int integer isarray isdate isempty iserror ismissing isnull isnumeric isobject join lbound lcase left len long longlong longptr mid msgbox now object oct replace right rnd round shell sgn single sqr string timer trim ubound ucase val variant weekday |
| self | me |

## Rules
| Role | Id | Matches | Colour | Back | Weight | Italic | Underline |
|:--|:--|:--|:--|:--|:--|:--|:--|
| default text | default | `name  value` | #1F2328 | - | 400 | no | no |
| file boundary line | fileline | `# ---- file ----` | #FFFFFF | #8A4B00 | 600 | no | no |
| keyword | keyword | `def if while` | #0000FF | - | 600 | no | no |
| keyword constant | kwconst | `True None` | #6A3D9A | - | 600 | no | no |
| imported module | module | `os np cython` | #4393C3 | - | 600 | no | no |
| imported function / class | imported | `sqrt Ordered` | #DE77AE | - | 600 | no | no |
| class use | classuse | `Shape(  Shape` | #FF00CC | - | 400 | no | no |
| def name | defname | `def parse(` | #C0198C | - | 600 | no | no |
| class name | classname | `class Shape` | #FF00CC | - | 600 | no | no |
| self / cls / me | self | `self.name` | #FF6037 | - | 600 | no | no |
| attribute | attribute | `.extra` | #1F2328 | - | 400 | no | no |
| method call | methodcall | `.append(` | #C0198C | - | 400 | no | no |
| call | call | `print(` | #1F2328 | - | 400 | no | no |
| call of a def in this file | localcall | `parse(` | #C0198C | - | 400 | no | no |
| builtin | builtin | `len range` | #7A3E9D | - | 600 | no | no |
| special name | special | `__init__` | #7A3E9D | - | 400 | no | no |
| exception | exception | `ValueError` | #FF355E | - | 600 | no | no |
| CONSTANT | constant | `MAX_ITEMS` | #5A6472 | - | 400 | no | no |
| decorator | decorator | `@property` | #9A6700 | - | 400 | yes | no |
| annotation | annotation | `x: int` | #6F42C1 | - | 400 | no | no |
| number | number | `0x1F 3.5e-3` | #0000FF | - | 400 | no | no |
| string | string | `"text"` | #1F2328 | - | 400 | no | no |
| format code | format | `%4.1f !r :>5` | #808080 | - | 600 | no | no |
| escape | escape | `\n {{ }}` | #808080 | - | 400 | no | no |
| docstring | docstring | `"""Doc."""` | #0A7D0A | #D1E5F0 | 400 | yes | no |
| other triple string | triple | `'''text'''` | #1F2328 | - | 400 | no | no |
| operator | operator | `+ == ->` | #1F2328 | - | 400 | no | no |
| punctuation | punct | `, ; : .` | #1F2328 | - | 400 | no | no |
| bracket, outer pair | br0 | `( )` | #5A6472 | - | 500 | no | no |
| bracket, level 1 (6, 11 ...) | br1 | `( )` | #7A1F1F | - | 500 | no | no |
| bracket, level 2 (7, 12 ...) | br2 | `( )` | #8A4B00 | - | 500 | no | no |
| bracket, level 3 (8 ...) | br3 | `( )` | #1F3FBF | - | 500 | no | no |
| bracket, level 4 (9 ...) | br4 | `( )` | #0B6B4F | - | 500 | no | no |
| bracket, level 5 (10 ...) | br5 | `( )` | #6B2F8A | - | 500 | no | no |
| comment, whole line | lcomment | `# note line` | #0A7D0A | #E8F3E8 | 400 | no | no |
| comment, inline (after code) | comment | `x = 1  # note` | #0A7D0A | - | 400 | no | no |
| comment marker | marker | `TODO FIXME` | #7A4B00 | #FFF4C2 | 600 | no | no |
| comment url | url | `https://x.org` | #0033B3 | - | 400 | no | yes |
| invalid | invalid | `$` | #FF0000 | - | 400 | no | yes |
