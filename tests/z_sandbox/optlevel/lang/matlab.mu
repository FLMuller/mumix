# matlab.mu -- how a MATLAB file is coloured and commented

Made from python.mu (the same roles, ids and colours) and then adjusted. The header lines below the title are read by vclang.py:

- Comment: the triplet a reviewer's comment starts with, and (after a space) what closes it. The server writes `<triplet><tag> text` lines and nothing else.
- Line comment, Block comment, Quotes, Escape, Transpose, Continuation: how the lexer reads it.
- Function, Class: regular expressions whose first group is the name, for the function list.

Files: .m
Mode: code
Comment: %%%
Line comment: %
Block comment: %{ %}
Block alone: yes
Continuation: ...
Quotes: ' "
Transpose: yes
Escape: double
Function: ^\s*function\b[^=\n(]*?=?\s*(\w+)\s*(?:\(|$)
Class: ^\s*classdef\s+(?:\([^)]*\)\s*)?(\w+)

## Words

| List | Words |
|:--|:--|
| keyword | arguments break case catch classdef continue else elseif end enumeration events for function global if import methods otherwise parfor persistent properties return spmd switch try while |
| keyword constant | true false Inf NaN pi eps |
| builtin | abs all any angle arrayfun asin acos atan atan2 cat ceil cell cellfun char class conj cos cosh cumprod cumsum det diag disp eig error eval exist exp eye feval fieldnames figure find fix floor fminsearch fprintf func2str fzero grid hold horzcat imag inputParser interp1 inv isa iscell ischar isempty isfield isinf islogical isnan isnumeric isreal isstruct legend length linspace log log10 log2 logspace max mean median min mod nargin nargout ndims norm num2str numel ode15s ode45 ones plot polyfit polyval prod rand randi randn rank real regexp regexprep rem repmat reshape rmfield round size sin sinh sort sprintf sqrt std str2double str2func str2num strcat strcmp strcmpi strfind strjoin strrep strsplit struct structfun subplot sum svd tan tanh tic title toc trace transpose tril triu upper lower var varargin varargout vertcat warning while xlabel ylabel zeros assert axis |
| self |  |

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
| string | string | `"text"` | #1F2328 | #FFFEFA | 400 | no | no |
| format code | format | `%4.1f !r :>5` | #808080 | - | 600 | no | no |
| escape | escape | `\n {{ }}` | #808080 | - | 400 | no | no |
| docstring | docstring | `"""Doc."""` | #0A7D0A | #D1E5F0 | 400 | yes | no |
| other triple string | triple | `'''text'''` | #1F2328 | #FFFEFA | 400 | no | no |
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
