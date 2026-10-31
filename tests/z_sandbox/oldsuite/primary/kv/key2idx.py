"""
key2idx.py — Normalise any key form to ONE canonical string storage key.
Python port of MATLAB key2idx.m.
VERSION: 1.0

    ck, nD = key2idx(k)

  ck : canonical str key (ALWAYS str) — all a READ needs. Index components are
       space-separated inside '(...)'; a component containing a space is
       single-quoted so the form round-trips unambiguously.
  nD : number of index components AND the sparse flag in one value —
         nD == 0  a plain/leaf name (str, incl. a literal '(r c)' transcribed
                  verbatim: parens are reserved, so it may only OVERWRITE an
                  existing sparse key)
         nD >  0  a genuine INDEX form -> a system-generated '(...)'.
       Writers gate on nD > 0 (== "is sparse"); readers just take ck.

  'foo' -> 'foo' 0      5     -> '(5)'   1      (3,7)     -> '(3 7)'   2
   str  -> name  0      [1,2] -> '(1 2)' 2      ('g',2)   -> '(g 2)'   2
  '(1 2)'->'(1 2)'0     (5,)  -> '(5)'   1      ('a b',7) -> "('a b' 7)" 2

Adaptation notes vs MATLAB:
  - MATLAB cell/numeric/string-array key forms collapse to Python str / int /
    float / tuple|list. A MATLAB scalar cell {x} maps to a 1-element list/tuple:
    {5}->(5,) is a 1-D index; {'foo'}->('foo',) is just the leaf name; {[1 2]}
    ->([1,2],) expands to a 2-D index — exactly the MATLAB branch behaviour.
  - string(double) -> f"{x:.15g}" (e.g. 5.0 -> '5', 1.5 -> '1.5').
"""

from __future__ import annotations


def _numstr(x):
    # MATLAB string(double): integer-valued -> no '.0'; else shortest %g.
    if isinstance(x, int):
        return str(x)
    return f"{x:.15g}"


def _components(comps):
    # Join index components into '(c1 c2 ...)'; quote any that contain a space.
    parts = []
    for c in comps:
        s = c if isinstance(c, str) else _numstr(c)
        if " " in s:
            s = "'" + s + "'"
        parts.append(s)
    return "(" + " ".join(parts) + ")", len(parts)


def key2idx(k):
    # --- plain name: str transcribed verbatim (incl. a literal '(r c)') ----
    if isinstance(k, str):
        return k, 0

    # --- scalar numeric: 1-D index -----------------------------------------
    if isinstance(k, (int, float)) and not isinstance(k, bool):
        return "(" + _numstr(k) + ")", 1

    # --- list/tuple: index form (MATLAB cell / numeric / string array) -----
    if isinstance(k, (list, tuple)):
        if len(k) == 1:                       # MATLAB scalar-cell {x}
            e = k[0]
            if isinstance(e, (list, tuple)):
                return _components(e)         # {[1 2]} -> '(1 2)'
            if isinstance(e, str):
                return e, 0                   # {'foo'} -> leaf name
            return "(" + _numstr(e) + ")", 1  # {5}     -> '(5)'
        return _components(k)

    # --- fallback: stringify, treat as a name ------------------------------
    return str(k), 0
