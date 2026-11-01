"""
b_odeproblem.py -- tests and benchmarks for ODEproblem, semantic ODE problems on scipy.

The model is written with names (v.VA, ddt.VA = ...); ODEproblem packs those into the flat
vector a solver wants. The tests check the packing (scalars, arrays, matrices, nested
records), the solver (a stiff problem against a tight scipy reference, every solver name),
the guards (non-finite derivatives, size mismatches, bad names, runaway runs), and the
reporting. The benchmarks time one call of the ode function, which is what every solver
step pays for.

Run from the project root:
    python tools/runbench.py tests/b_odeproblem.py
"""

import contextlib
import io
import sys

import numpy as np
from scipy.integrate import solve_ivp


def findtools():                      # walk up to the folder that holds tools/
    from os.path import abspath, dirname, isdir, join
    here = dirname(abspath(__file__))
    while here != dirname(here) and not isdir(join(here, 'tools')):
        here = dirname(here)
    sys.path.insert(0, join(here, 'tools'))


findtools()
from use import load
from bench import bench

SOURCES = ['odeproblem', 'fields']
globals().update(load('odeproblem', into={}))      # ODEproblem, ODEproblemError, SOLVERS ...
globals().update(load('fields', into={}))          # Fields


def robertson(v, p, ddt):
    ddt.A = -p.k1 * v.A + p.k3 * v.B * v.C
    ddt.B = p.k1 * v.A - p.k3 * v.B * v.C - p.k2 * v.B**2
    ddt.C = p.k2 * v.B**2
    return ddt


def decay(v, p, ddt):
    ddt.x = -p.k * v.x
    ddt.s.a = -v.s.a
    ddt.s.M = -2 * v.s.M


def grow(v, p, ddt):
    ddt.a = v.a


class b_odeproblem(bench):
    BenchName = 'odeproblem'
    BenchVersion = 'M1.0.3'
    BenchHeader = ''
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        cls.params = dict(k1=0.04, k2=3e7, k3=1e4, Racc=1e-6, title='Robertson')
        cls.state = dict(A=1.0, B=0.0, C=0.0)
        cls.small = ODEproblem(dict(k=3.0), dict(x=[1.0, 2.0], s=dict(a=1.0, M=np.ones((2, 2)))),
                               decay)
        cls.ode, cls.y0 = cls.small.create()

    def quiet(self, function, *args):
        """Run function while capturing what it prints; returns the text."""
        text = io.StringIO()
        with contextlib.redirect_stdout(text):
            function(*args)
        return text.getvalue()

    # ---- the solver ---------------------------------------------------------------------
    def test_T01_stiff_robertson_matches_a_tight_scipy_reference(self):
        problem = ODEproblem(self.params, self.state, robertson)
        t, tables = problem.solve(1000)
        reference = solve_ivp(
            lambda t, y: [-0.04 * y[0] + 1e4 * y[1] * y[2],
                          0.04 * y[0] - 1e4 * y[1] * y[2] - 3e7 * y[1]**2, 3e7 * y[1]**2],
            (0, 1000), [1, 0, 0], method='Radau', rtol=1e-11, atol=1e-14)
        self.assertAlmostEqual(tables.A[-1], reference.y[0, -1], delta=1e-4 * reference.y[0, -1])
        self.assertAlmostEqual(tables.A[-1] + tables.B[-1] + tables.C[-1], 1.0, places=8)
        self.assertTrue(problem.stats()['ok'])
        self.assertGreater(problem.stats()['nsteps'], 5)

    def test_T02_tspan_forms(self):
        problem = ODEproblem(dict(k=1.0, Racc=1e-9), dict(a=1.0), lambda v, p, ddt: setattr(
            ddt, 'a', -p.k * v.a))
        t, tables = problem.solve(2)                       # a final time
        self.assertEqual((t[0], t[-1]), (0.0, 2.0))
        t, tables = problem.solve([1, 3])                  # [t0, t1]: adaptive steps
        self.assertEqual((t[0], t[-1]), (1.0, 3.0))
        self.assertGreater(len(t), 2)
        t, tables = problem.solve([0, 0.5, 1, 2])          # output at those times only
        np.testing.assert_allclose(t, [0, 0.5, 1, 2])
        np.testing.assert_allclose(tables.a, np.exp(-t), rtol=1e-5)

    def test_T03_bad_tspan_is_refused(self):
        problem = ODEproblem({}, dict(a=1.0), grow)
        for bad in ([2, 1], [0, 1, 1], []):
            with self.assertRaises(ODEproblemError):
                problem.solve(bad)

    def test_T04_every_solver_name_gives_the_same_answer(self):
        for name in ('ode15s', 'ode23s', 'ode45', 'ode23', 'BDF', 'Radau', 'LSODA', 'RK45',
                     'RK23', 'DOP853', 'dop853'):
            problem = ODEproblem(dict(solver=name, Racc=1e-8), dict(a=1.0), grow)
            t, tables = problem.solve(1)
            self.assertAlmostEqual(tables.a[-1], np.e, delta=1e-4 * np.e, msg=name)
            self.assertIn(problem.solver, SOLVERS)

    def test_T05_aliases_map_to_scipy_solvers(self):
        for alias, expected in (('ode15s', 'BDF'), ('ode23s', 'Radau'), ('ode45', 'RK45'),
                                ('ode23', 'RK23')):
            self.assertEqual(ODEproblem(dict(solver=alias), dict(a=1.0), grow).solver, expected)

    def test_T06_unknown_solver_is_refused(self):
        with self.assertRaises(ODEproblemError):
            ODEproblem(dict(solver='nope'), dict(a=1.0), grow)
        problem = ODEproblem({}, dict(a=1.0), grow)
        with self.assertRaises(ODEproblemError):
            problem.solver = 'nope'

    def test_T07_time_is_v_t_and_not_a_state(self):
        def clock(v, p, ddt):
            ddt.a = v.t
        problem = ODEproblem(dict(Racc=1e-9), dict(a=0.0), clock)
        t, tables = problem.solve(3)
        self.assertAlmostEqual(tables.a[-1], 4.5, places=6)
        self.assertEqual(problem.nODE, 1)

    def test_T08_a_start_time_given_as_t(self):
        problem = ODEproblem(dict(tspan=[2, 4], Racc=1e-9), dict(t=2.0, a=0.0),
                             lambda v, p, ddt: setattr(ddt, 'a', 1.0))
        t, tables = problem.solve()
        self.assertEqual(t[0], 2.0)
        self.assertAlmostEqual(tables.a[-1], 2.0, places=6)

    # ---- packing -----------------------------------------------------------------------------
    def test_T09_arrays_matrices_and_nested_records(self):
        problem = ODEproblem(dict(k=3.0, Racc=1e-9),
                             dict(x=[1.0, 2.0], s=dict(a=1.0, M=np.ones((2, 2)))), decay)
        t, tables = problem.solve([0, 1])
        self.assertEqual(tables.x.shape, (len(t), 2))
        self.assertEqual(tables.s.M.shape, (len(t), 2, 2))
        self.assertEqual(tables.s.a.shape, (len(t),))
        np.testing.assert_allclose(tables.x[-1], np.array([1, 2]) * np.exp(-3), rtol=1e-6)
        np.testing.assert_allclose(tables.s.M[-1], np.exp(-2), rtol=1e-6)
        self.assertEqual(problem.nODE, 2 + 1 + 4)

    def test_T10_y0_get_and_set(self):
        problem = ODEproblem(dict(k=3.0), dict(x=[1.0, 2.0], s=dict(a=1.0, M=np.ones((2, 2)))),
                             decay)
        np.testing.assert_allclose(problem.y0, [1, 2, 1, 1, 1, 1, 1])
        problem.y0 = np.arange(7.0)
        self.assertEqual(problem.v.s.a, 2.0)
        np.testing.assert_allclose(problem.v.s.M, [[3, 4], [5, 6]])
        self.assertFalse(problem.solved)

    def test_T11_y0_of_the_wrong_size_is_refused(self):
        problem = ODEproblem({}, dict(a=1.0, b=2.0), grow)
        with self.assertRaises(ODEproblemError):
            problem.y0 = [1.0, 2.0, 3.0]

    def test_T12_a_scalar_derivative_fills_an_array(self):
        problem = ODEproblem(dict(Racc=1e-9), dict(x=[0.0, 0.0, 0.0]),
                             lambda v, p, ddt: setattr(ddt, 'x', 1.0))
        t, tables = problem.solve(2)
        np.testing.assert_allclose(tables.x[-1], [2, 2, 2], rtol=1e-6)

    def test_T13_the_input_values_are_copied(self):
        values = dict(x=np.array([1.0, 2.0]))
        problem = ODEproblem({}, values, grow if False else (lambda v, p, ddt: None))
        values['x'][0] = 99.0
        self.assertEqual(problem.v.x[0], 1.0)

    # ---- guards -----------------------------------------------------------------------------------
    def test_T14_a_non_finite_derivative_names_the_variable(self):
        def bad(v, p, ddt):
            with np.errstate(all='ignore'):
                ddt.a = np.log(v.a)
                ddt.b = 0.0
        with self.assertRaises(ODEproblemError) as caught:
            ODEproblem({}, dict(a=0.0, b=1.0), bad).solve(1)
        self.assertIn('a:', str(caught.exception))
        self.assertNotIn('b:', str(caught.exception))

    def test_T15_a_derivative_of_the_wrong_size_is_refused(self):
        def wrong(v, p, ddt):
            ddt.x = np.zeros(3)
        with self.assertRaises(ODEproblemError) as caught:
            ODEproblem({}, dict(x=[1.0, 2.0]), wrong).solve(1)
        self.assertIn("'x'", str(caught.exception))

    def test_T16_names_that_are_dict_methods_and_non_numbers_are_refused(self):
        for bad in (dict(items=1.0), dict(keys=1.0), dict(s='text'), dict(s=[1, 'a'])):
            with self.assertRaises(ODEproblemError):
                ODEproblem({}, bad, lambda v, p, ddt: ddt)

    def test_T17_the_monitor_stops_a_run_and_the_partial_result_is_kept(self):
        problem = ODEproblem(dict(monitorfun=lambda t, prob: t > 0.3, Racc=1e-6),
                             dict(a=1.0), grow)
        t, tables = problem.solve(10)
        self.assertEqual(problem.stats()['status'], 'stopped by monitor')
        self.assertFalse(problem.stats()['ok'])
        self.assertTrue(0.3 < t[-1] < 10)
        self.assertEqual(len(tables.a), len(t))

    def test_T18_the_call_limit_stops_a_runaway(self):
        problem = ODEproblem(dict(MaxFcalls=1, Racc=1e-6), dict(a=1.0), grow)
        t, tables = problem.solve(1e6)
        self.assertEqual(problem.stats()['status'], 'stopped by monitor')
        self.assertLess(t[-1], 1e6)

    def test_T19_a_failing_solver_raises_and_keeps_the_partial_result(self):
        def blowup(v, p, ddt):
            ddt.a = v.a**2                          # reaches infinity at t = 1
        problem = ODEproblem(dict(solver='RK45', Racc=1e-10), dict(a=1.0), blowup)
        with self.assertRaises(ODEproblemError):
            problem.solve(2)
        self.assertGreater(len(problem.t), 1)

    # ---- the rest of the interface -----------------------------------------------------------------
    def test_T20_scalefun_rescales_each_table(self):
        def scale(name, p, ys, prob):
            return ys * 1000, name
        problem = ODEproblem(dict(scalefun=scale, Racc=1e-9), dict(a=1.0), grow)
        t, tables = problem.solve(1)
        self.assertAlmostEqual(tables.a[-1], 1000 * np.e, delta=1.0)
        self.assertAlmostEqual(problem.y[-1, 0], np.e, delta=1e-3)    # raw y is unscaled

    def test_T21_create_returns_a_function_for_any_scipy_solver(self):
        problem = ODEproblem({}, dict(a=1.0), grow)
        ode, y0 = problem.create()
        self.assertTrue(callable(ode))
        np.testing.assert_allclose(ode(0.0, y0), [1.0])
        result = solve_ivp(ode, (0, 1), y0, rtol=1e-9)
        self.assertAlmostEqual(result.y[0, -1], np.e, places=6)

    def test_T22_stats_before_solve_is_refused(self):
        with self.assertRaises(ODEproblemError):
            ODEproblem({}, dict(a=1.0), grow).stats()

    def test_T23_stats_and_report_after_a_solve(self):
        problem = ODEproblem(dict(title='growth', Racc=1e-8), dict(a=1.0), grow)
        problem.solve(1)
        stats = problem.stats()
        for key in ('solver', 'nsteps', 'ncalls', 'nfev', 'deltat', 'ok', 'status'):
            self.assertIn(key, stats)
        self.assertIs(stats, problem.solstats)
        text = self.quiet(problem.report)
        self.assertIn('growth', text)
        self.assertIn('steps', text)
        self.assertNotIn('NOT FINISHED', text)

    def test_T24_clear_forgets_the_solution(self):
        problem = ODEproblem({}, dict(a=1.0), grow)
        problem.solve(1)
        problem.clear()
        self.assertFalse(problem.solved)
        self.assertEqual(len(problem.t), 0)
        with self.assertRaises(ODEproblemError):
            problem.stats()

    def test_T25_the_function_may_return_ddt_or_nothing(self):
        def returns(v, p, ddt):
            ddt.a = -v.a
            return ddt

        def nothing(v, p, ddt):
            ddt.a = -v.a
        for function in (returns, nothing):
            t, tables = ODEproblem(dict(Racc=1e-9), dict(a=1.0), function).solve(1)
            self.assertAlmostEqual(tables.a[-1], np.exp(-1), places=6)

    def test_T26_the_defaults_are_published(self):
        self.assertEqual(DEFAULTS['Racc'], 0.01)
        self.assertEqual(DEFAULTS['solver'], 'ode15s')
        self.assertIn('BDF', SOLVERS)
        self.assertEqual(ALIASES['ode45'], 'RK45')

    # ---- benchmarks ---------------------------------------------------------------------------------
    def bench_ode_call_small(self, timer):
        ode = self.ode
        y0 = self.y0
        with timer as test:
            while test.more:
                for i in test.count:
                    ode(0.0, y0)
        return 'ode(t, y): 7 states (array, matrix, record)', 'ode call'

    def bench_ode_call_scalars(self, timer):
        problem = ODEproblem(self.params, self.state, robertson)
        ode, y0 = problem.create()
        with timer as test:
            while test.more:
                for i in test.count:
                    ode(0.0, y0)
        return 'ode(t, y): 3 scalar states (Robertson)', 'ode call'
