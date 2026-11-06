# cython.mu -- how a Cython file is coloured

Chosen in colour_editor.html and saved from it (2026-10-29). Colours are hex RRGGBB, Back "-" is
none, Weight is 100 thin to 800 heavy (400 normal, 700 bold). The Id is what the programs
read; the Role text is for people. Load this file in the editor with the Load .mu button.

Page background #FFFFFF, font size 13px.

Files: .pyx .pxd .pxi

Extends: python (every Python rule and word list holds; these are added)

## Words

| List | Words |
|:--|:--|
| keyword | DEF ELIF ELSE IF cdef cimport cpdef ctypedef cython enum extern fused gil inline noexcept nogil packed public readonly sizeof struct typeof union |
| builtin | NULL Py_ssize_t bint bytearray bytes char complex const dict double float frozenset int int16_t int32_t int64_t int8_t list long object set short signed size_t str tuple uint16_t uint32_t uint64_t uint8_t unsigned void |
| C type | Py_ssize_t bint bytearray bytes char complex const dict double float frozenset int int16_t int32_t int64_t int8_t list long object set short signed size_t str tuple uint16_t uint32_t uint64_t uint8_t unsigned void |

## Rules

| Role | Id | Matches | Colour | Back | Weight | Italic | Underline |
|:--|:--|:--|:--|:--|:--|:--|:--|
| cdef, cpdef, nogil ... | ckeyword | `cdef nogil` | #0033B3 | - | 500 | no | no |
| C type | ctype | `int double` | #6F42C1 | - | 500 | no | no |
| object (any Python object) | cobject | `cdef object f(` | #FF00CC | - | 400 | no | no |
| NULL | cconst | `NULL` | #7A3E9D | - | 400 | no | no |
| cdef function name | cdefname | `cdef f(` | #C0198C | - | 600 | no | no |
| cdef class name | cdefclass | `cdef class C` | #FF00CC | - | 600 | no | no |
| struct, enum, fused name | cstruct | `struct P` | #C0198C | - | 600 | no | no |
| # cython: directive | directive | `# cython:` | #7A4B00 | #FFF4C2 | 600 | no | no |
| cython module | cymod | `cython.cfunc` | #7A3E9D | - | 600 | no | no |
| cython decorator | cydeco | `@cython.cfunc` | #5A6472 | - | 400 | no | no |
| cast | cast | `<int>` | #5A6472 | - | 400 | no | no |
| pointer, address | pointer | `* &` | #0000FF | - | 600 | no | no |
| memoryview | memview | `int[:]` | #808080 | - | 400 | no | no |
