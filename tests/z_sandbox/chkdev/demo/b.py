"""b -- loops back. Exposes bee. VERSION  M1 m01.v01 (2026-11-05): first."""
import a

__all__ = ['bee']


def bee(x):
    return a.two(x)
