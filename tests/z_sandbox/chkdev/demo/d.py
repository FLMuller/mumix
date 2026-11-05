"""d -- copies a constant. Exposes dee. VERSION  M1 m01.v01 (2026-11-05): first."""
__all__ = ['dee']

COPY_TABLE = {'alpha': 1, 'beta': 2, 'gamma': 3}


def dee(x):
    return COPY_TABLE.get(x)
