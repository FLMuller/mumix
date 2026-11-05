"""a -- inner module. Exposes one, two. VERSION  M1 m01.v01 (2026-11-05): first."""
import b

__all__ = ['one', 'two']


def one(x):
    return b.bee(x)


def two(x):
    return x


def hidden(x):
    return x
