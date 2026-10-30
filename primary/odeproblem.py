"""
ODEproblem  -  semantic ODE problems: write the model the way the maths reads

Why
    A solver wants one flat vector y and a function dy/dt = F(t, y). A human wants named
    variables, some of them arrays, with an equation each. ODEproblem sits between the two:
    you write the model with names (v.VA, v.conc.B, ddt.VA = ...), it packs and unpacks the
    flat vector for the scipy solver. Port of the core of MATLAB ODEproblem v.1 (2022);
    plotting and the figure vault are not ported.

Algorithm
    1. analyse   walk v once; every number or array becomes a Leaf (start, stop, shape)
                 in one flat vector; a nested dict becomes a nested layout.
    2. ode       each solver call: unpack y into a Fields with views of y (no copies),
                 build a zero ddt of the same shape, call f, pack ddt into dydt.
    3. solve     step the scipy solver class directly (BDF, RK45, ...), so a monitor can
                 stop a runaway run and the partial solution is kept.
    Cost per ode call is O(nODE) for packing plus one call of f; the packing walks the
    layout in Python, so for a few dozen variables it is small next to f itself.

Use
    from odeproblem import ODEproblem
    from fields import Fields

    p = dict(k=2.0, Racc=1e-6)                   # parameters (any names; see below)
    v = dict(A=1.0, x=[1.0, 2.0], s=dict(B=0.0)) # initial values: float, array or dict
    def f(v, p, ddt):
        ddt.A = -p.k * v.A                       # one equation per variable
        ddt.x = -v.x
        ddt.s.B = p.k * v.A
        return ddt                               # (returning nothing also works)
    prob = ODEproblem(p, v, f)

    t, tables = prob.solve(10)       # tspan 10 -> [0, 10]; [t0, t1] -> adaptive steps;
                                     # [t0, t1, t2, ...] -> output at those times only
    tables.A, tables.x, tables.s.B   # arrays, one row per time; x is (nt, 2)
    prob.t, prob.y                   # times (nt,) and the flat solution (nt, nODE)
    prob.report()                    # prints solver, steps, calls, time
    prob.stats()                     # the same numbers, as a dict (prob.solstats)

    ode, y0 = prob.create()          # for your own scipy call: ode(t, y) -> dydt
    prob.y0                          # initial values as a flat vector; assign to set
    prob.solver = 'ode15s'           # or 'ode45', 'BDF', 'Radau', 'LSODA', 'RK45', ...
    prob.clear()                     # forget the last solution

    Arguments of f:  v    current values (floats and views of y; read, do not write)
                          plus v.t, the time; v.t is not a state
                     p    the parameters
                     ddt  zeros shaped like v (no t); fill it, then return it
    Variable names:  not 'items', 'keys', 'values', 'get', 'copy', 'update', 'pop' or any
                     other dict method (Fields reads those as methods).
    Parameters p:    tspan (0, 1) | Racc 0.01 relative tolerance | Qo 1 typical size of y,
                     absolute tolerance is spacing(Qo) * 1000 | MaxStep None |
                     MaxFcalls 1000000 | solver 'ode15s' |
                     monitorfun(t, prob) -> True stops the run | scalefun(name, p, ys,
                     prob) -> (ys, label) rescales each table | title for report().
                     Any other name is yours; f reads it as p.name.
    Solver names:    ode15s -> BDF, ode23s -> Radau, ode45 -> RK45, ode23 -> RK23 (the
                     nearest scipy equivalents, not identical methods), or a scipy name.
    Errors:          ODEproblemError, for bad input, a NaN or Inf derivative (the message
                     names the variable), and a failed solver (partial results are kept).

Versions
    M01  m01.v01  2026-10-30  first version: the core of MATLAB ODEproblem on scipy.
                  Differences: time is v.t, not a state; arrays are C order; solve stops
                  the solver itself, so nfailed is not reported (scipy does not count it).
"""

import time

import numpy as np
from scipy.integrate import BDF, DOP853, LSODA, RK23, RK45, Radau

from fields import Fields

__all__ = ['ODEproblem', 'ODEproblemError', 'SOLVERS', 'ALIASES', 'DEFAULTS']

SOLVERS = {'BDF': BDF, 'Radau': Radau, 'LSODA': LSODA,
           'RK45': RK45, 'RK23': RK23, 'DOP853': DOP853}
ALIASES = {'': 'BDF', 'reset': 'BDF', 'ode15s': 'BDF', 'ode23s': 'Radau',
           'ode45': 'RK45', 'ode23': 'RK23'}
DEFAULTS = dict(tspan=(0.0, 1.0), Racc=0.01, Qo=1.0, MaxStep=None, MaxFcalls=1000000,
                solver='ode15s')


class ODEproblemError(Exception):
    """Bad input, a non-finite derivative, or a failed solver."""


class Leaf:
    """One number or array inside the flat vector: y[start:stop] reshaped to shape."""
    __slots__ = ('path', 'start', 'stop', 'shape')

    def __init__(me, path, start, shape):
        me.path = path
        me.start = start
        me.shape = shape
        me.stop = start + int(np.prod(shape))


class Priv:
    """Private state of an ODEproblem (slots: attribute access is much faster)."""
    __slots__ = ('f', 'layout', 'leaves', 'nODE', 'ncalls', 'solver')


# ---------------------------------------------------------------------------------------
# Layout helpers: a layout is a dict name -> Leaf or nested layout, in the order of v.
# They are plain functions because ODEproblem uses several of them.

def analyse(me, tree, path, start):
    """Walk tree; return (layout, normalised copy of the values, next free index)."""
    layout = {}
    values = Fields()
    for name, val in tree.items():
        if hasattr(dict, name):
            raise ODEproblemError(f"variable name '{name}' is a dict method: rename it")
        label = path + name
        if isinstance(val, dict):
            layout[name], values[name], start = analyse(me, val, label + '.', start)
            continue
        try:
            arr = np.array(val, dtype=float)       # a copy, so later edits cannot leak in
        except (TypeError, ValueError):
            raise ODEproblemError(f"variable '{label}' is not numeric") from None
        leaf = Leaf(label, start, arr.shape)
        me.priv.leaves.append(leaf)
        layout[name] = leaf
        values[name] = float(arr) if arr.shape == () else arr
        start = leaf.stop
    return layout, values, start


def unpack(layout, y):
    """Flat vector y -> Fields of floats and views of y (nothing is copied)."""
    out = Fields()
    for name, node in layout.items():
        if isinstance(node, Leaf):
            if node.shape == ():
                out[name] = y[node.start]
            else:
                out[name] = y[node.start:node.stop].reshape(node.shape)
        else:
            out[name] = unpack(node, y)
    return out


def zeros(layout):
    """A Fields shaped like the layout, all zero: the empty ddt handed to f."""
    out = Fields()
    for name, node in layout.items():
        if isinstance(node, Leaf):
            out[name] = 0.0 if node.shape == () else np.zeros(node.shape)
        else:
            out[name] = zeros(node)
    return out


def pack(layout, tree, flat):
    """Fields (or dict) shaped like the layout -> flat vector, written into flat."""
    for name, node in layout.items():
        if isinstance(node, Leaf):
            arr = np.asarray(tree[name], dtype=float)
            if arr.size == node.stop - node.start:
                flat[node.start:node.stop] = arr.reshape(-1)
            elif arr.size == 1:                    # a scalar fills a whole array
                flat[node.start:node.stop] = arr.reshape(())
            else:
                raise ODEproblemError(f"'{node.path}' has {arr.size} elements, "
                                      f"expected {node.stop - node.start}")
        else:
            pack(node, tree[name], flat)


def diagnose(me, dydt):
    """One line per variable whose derivative is NaN or Inf."""
    lines = []
    for leaf in me.priv.leaves:
        seg = dydt[leaf.start:leaf.stop]
        bad = ~np.isfinite(seg)
        if bad.any():
            lines.append(f"{leaf.path}: {int(bad.sum())} of {seg.size} not finite "
                         f"(first {seg[bad][0]})")
    return lines


def timespan(tspan):
    """Scalar -> [0, tspan]; otherwise a float vector of at least two increasing times."""
    ts = np.atleast_1d(np.array(tspan, dtype=float))
    if ts.size == 1:
        ts = np.array([0.0, ts[0]])
    if ts.size < 2 or np.any(np.diff(ts) <= 0):
        raise ODEproblemError("tspan must be a final time or increasing times [t0, ...]")
    return ts


def maketables(me):
    """The solution as a Fields shaped like v: each leaf an array of (nt,) + shape."""
    scale = me.p.get('scalefun')
    nt = me.y.shape[0]

    def walk(layout):
        out = Fields()
        for name, node in layout.items():
            if isinstance(node, Leaf):
                ys = me.y[:, node.start:node.stop].reshape((nt,) + node.shape)
                if scale is not None:
                    ys, label = scale(node.path, me.p, ys, me)
                out[name] = ys
            else:
                out[name] = walk(node)
        return out
    return walk(me.priv.layout)


# ---------------------------------------------------------------------------------------

class ODEproblem:
    """A semantic ODE problem. ODEproblem(p, v, f); see the module header for the use."""

    def __init__(me, p, v, f):
        me.priv = Priv()
        me.priv.f = f
        me.priv.leaves = []
        me.priv.ncalls = 0
        me.p = Fields(DEFAULTS)
        me.p.update(p)
        values = dict(v)
        t0 = values.pop('t', None)                 # t is the time, never a state
        me.priv.layout, me.v, me.priv.nODE = analyse(me, values, '', 0)
        me.v.t = float(timespan(me.p.tspan)[0] if t0 is None else t0)
        me.priv.solver = None
        me.solver = me.p.solver
        me.t = np.zeros(0)
        me.y = np.zeros((0, me.nODE))
        me.tables = Fields()
        me.solstats = {}
        me.created = False
        me.solved = False

    @property
    def nODE(me):
        return me.priv.nODE

    @property
    def y0(me):
        """Initial values as a flat vector (assign a vector to set them)."""
        y = np.empty(me.nODE)
        pack(me.priv.layout, me.v, y)
        return y

    @y0.setter
    def y0(me, y):
        me.clear()
        y = np.array(y, dtype=float).reshape(-1)
        if y.size != me.nODE:
            raise ODEproblemError(f"y0 has {y.size} elements, expected {me.nODE}")
        t = me.v.t
        me.v = unpack(me.priv.layout, y)
        me.v.t = t

    @property
    def solver(me):
        """Solver name (a key of SOLVERS); assign 'ode15s', 'ode45', 'BDF', ..."""
        return me.priv.solver

    @solver.setter
    def solver(me, name):
        key = str(name).strip()
        key = ALIASES.get(key.lower(), key)
        match = [k for k in SOLVERS if k.lower() == key.lower()]
        if not match:
            raise ODEproblemError(f"unknown solver '{name}'; use one of "
                                  f"{sorted(SOLVERS)} or {sorted(ALIASES)[2:]}")
        me.priv.solver = match[0]

    def ode(me, t, y):
        """dy/dt for the solver: unpack, call f, pack, and check the numbers."""
        me.priv.ncalls += 1
        v = unpack(me.priv.layout, y)
        v.t = t
        ddt = zeros(me.priv.layout)
        out = me.priv.f(v, me.p, ddt)
        dydt = np.empty(me.nODE)
        pack(me.priv.layout, ddt if out is None else out, dydt)
        if not np.isfinite(dydt).all():
            raise ODEproblemError("ODE function returns numbers out of range:\n  "
                                  + "\n  ".join(diagnose(me, dydt)))
        return dydt

    def create(me):
        """Test f once and return (ode, y0): ode(t, y) is ready for any scipy solver."""
        me.clear()
        y0 = me.y0
        me.ode(me.v.t, y0)                         # an error in f shows here, with its line
        me.priv.ncalls = 0
        me.created = True
        return me.ode, y0

    def clear(me):
        """Forget the last solution."""
        me.t = np.zeros(0)
        me.y = np.zeros((0, me.nODE))
        me.tables = Fields()
        me.solstats = {}
        me.created = False
        me.solved = False

    def solve(me, tspan=None):
        """Integrate over tspan (or p.tspan); return (t, tables)."""
        if tspan is not None:
            me.p.tspan = timespan(tspan)
        ts = timespan(me.p.tspan)
        t0 = ts[0]
        tf = ts[-1]
        me.v.t = t0
        ode, y0 = me.create()

        atol = np.spacing(abs(float(me.p.Qo))) * 1000
        maxstep = np.inf if me.p.MaxStep is None else me.p.MaxStep
        solver = SOLVERS[me.solver](ode, t0, y0, tf, rtol=me.p.Racc, atol=atol,
                                    max_step=maxstep)
        monitor = me.p.get('monitorfun')
        limit = me.p.MaxFcalls * np.sqrt(-np.log(me.p.Racc))   # runaway guard

        t_out = [t0]
        y_out = [y0]
        t_eval = ts[1:] if ts.size > 2 else None
        k = 0                                      # next t_eval point still to report
        nsteps = 0
        stopped = False
        clock = time.perf_counter()
        while solver.status == 'running' and not stopped:
            solver.step()
            nsteps += 1
            if t_eval is None:
                t_out.append(solver.t)
                y_out.append(solver.y.copy())
            elif solver.status != 'failed':
                dense = solver.dense_output()      # interpolate inside the step just taken
                while k < t_eval.size and t_eval[k] <= solver.t:
                    t_out.append(t_eval[k])
                    y_out.append(dense(t_eval[k]))
                    k += 1
            if monitor is not None:
                stopped = bool(monitor(solver.t, me))
            else:
                stopped = me.priv.ncalls > limit
        elapsed = time.perf_counter() - clock

        me.t = np.array(t_out)
        me.y = np.vstack(y_out)
        me.tables = maketables(me)
        me.solved = True
        finished = solver.status == 'finished'
        me.solstats = dict(solver=me.solver, nsteps=nsteps, ncalls=me.priv.ncalls,
                           nfev=solver.nfev, njev=solver.njev, nlu=solver.nlu,
                           deltat=elapsed, ok=finished,
                           status='stopped by monitor' if stopped else solver.status)
        if solver.status == 'failed':
            raise ODEproblemError(f"{me.solver} failed at t = {solver.t:g} "
                                  f"({nsteps} steps; partial results kept in prob.t, "
                                  "prob.y)")
        return me.t, me.tables

    def stats(me):
        """The numbers of the last solve as a dict (also prob.solstats)."""
        if not me.solved:
            raise ODEproblemError("problem not solved: call solve() first")
        return me.solstats

    def report(me):
        """Print the stats of the last solve."""
        s = me.stats()
        title = me.p.get('title', 'ode problem')
        print(f"   solved: {title} ({s['solver']}) in {s['deltat']:.4g} s")
        print(f"            status: {s['status']}")
        print(f"             steps: {s['nsteps']}")
        print(f"    function calls: {s['ncalls']}")
        print(f"      jacobians/LU: {s['njev']} / {s['nlu']}")
        if not s['ok']:
            print("     !!NOT FINISHED!!")
