"""demo -- the front door of the demo folder.

Exposes run. VERSION  M1 m01.v01 (2026-11-05): first version.
"""
import a

__all__ = ['run']


def run(x):
    """Run it because the tests need it."""
    return a.one(x) + a.hidden(x)
