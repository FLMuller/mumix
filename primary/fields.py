"""
Fields  -  a dict whose keys are also attributes (the Python form of a MATLAB struct)

Why
    The semantic ODE model of ODEproblem is written the way the maths reads:
    v.VA, p.Vtot, ddt.VA = ...  A plain dict needs v['VA'] everywhere, which hides the
    equations. Fields is a dict, so it can be passed anywhere a dict is wanted, with the
    attribute spelling added on top.

Use
    from fields import Fields
    s = Fields(a=1.0, b=dict(c=2.0))     # nested dicts become Fields
    s.a                                  # 1.0           (same as s['a'])
    s.b.c                                # 2.0
    s.d = 3.0                            # same as s['d'] = 3.0
    s.update(e=4.0)                      # like dict.update; nested dicts converted too
    'a' in s, list(s), s.get('z', 0)     # dict behaviour is unchanged

    A key that is also a dict method (items, keys, values, get, copy, update, pop, ...)
    can be written s.items = 1, but read back only as s['items']: the method wins on
    attribute reads. ODEproblem refuses such variable names.

Versions
    M01  m01.v01  2026-10-30  first version, for the mumix ODEproblem.
"""

__all__ = ['Fields']


class Fields(dict):
    """dict with attribute access; plain dicts stored in it become Fields (recursively)."""

    def __init__(me, *args, **kwargs):
        dict.__init__(me)
        me.update(*args, **kwargs)

    def __setitem__(me, key, val):
        # Only a bare dict is converted: arrays, floats and Fields pass through untouched.
        if type(val) is dict:
            val = Fields(val)
        dict.__setitem__(me, key, val)

    def update(me, *args, **kwargs):
        # dict.update bypasses __setitem__, so route each pair through it.
        for key, val in dict(*args, **kwargs).items():
            me[key] = val

    def __getattr__(me, name):
        # Called only when normal lookup fails, so dict methods and real attributes win.
        try:
            return me[name]
        except KeyError:
            raise AttributeError(name) from None

    def __setattr__(me, name, val):
        me[name] = val

    def __delattr__(me, name):
        try:
            del me[name]
        except KeyError:
            raise AttributeError(name) from None

    def __dir__(me):
        return sorted(set(dir(dict)) | set(map(str, me.keys())))

    def copy(me):
        return Fields(me)

    def __repr__(me):
        return 'Fields(' + dict.__repr__(me) + ')'
