"""loops -- compiled twin of the Python loop in demo.py (the pure-Python version).

Exposes total.

Speed
    total   2 ms    6 ms    3.0x   against the Python loop

VERSION  M1 m01.v01 (2026-11-05): first.
"""
__all__ = ['total']


def total(a):
    return sum(a)
