# python.mu -- how a Python file is coloured

Chosen in colour_editor.html and saved from it (2026-10-29). Colours are hex RRGGBB, Back "-" is
none, Weight is 100 thin to 800 heavy (400 normal, 700 bold). The Id is what the programs
read; the Role text is for people. Load this file in the editor with the Load .mu button.

Page background #FFFFFF, font size 13px.

Files: .py

## Words

Words the tokenizer cannot tell from the text: the word lists. The rest of the roles come from
position (after def, after a dot, before an open bracket) and shape (UPPER_CASE, __dunder__).

| List | Words |
|:--|:--|
| keyword | False None True _ and as assert async await break case class continue def del elif else except finally for from global if import in is lambda match nonlocal not or pass raise return try type while with yield |
| keyword constant | True False None |
| builtin | False None True abs aiter all anext any ascii bin bool breakpoint bytearray bytes callable chr classmethod compile complex copyright credits delattr dict dir divmod enumerate eval exec exit filter float format frozenset getattr globals hasattr hash help hex id input int isinstance issubclass iter len license list locals map max memoryview min next object oct open ord pow print property quit range repr reversed round set setattr slice sorted staticmethod str sum super tuple type vars zip |
| self | self cls me |

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
