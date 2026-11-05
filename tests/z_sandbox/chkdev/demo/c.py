"""c -- nobody uses it. Exposes cee. VERSION  M1 m01.v01 (2026-11-05): first."""
__all__ = ['cee']

PRIVATE_TABLE = {'alpha': 1, 'beta': 2, 'gamma': 3}


def cee(x):
    return PRIVATE_TABLE.get(x)
