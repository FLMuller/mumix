"""
mumix -- a phenomenological micromixing model for a fed batch (F. Muller).

Why
    A feed of concentration Bo is added to a vessel of A, with Ao much smaller than Bo, and
    A + B -> P is fast. Whether the reaction follows the kinetics or the mixing depends on
    how A and B are segregated. The model follows two volumes, A (the vessel) and B (the
    fresh feed), and the interface between them, which turbulent eddies stretch and fold.
    See "A phenomenological model for micromixing.docx" in this folder.

Algorithm
    State: VA, VB (volumes), Ai (interface area), nAA, nBA, nAB, nBB (moles of species A and
    B in volume A and B: n<species><volume>) and nP (product).
    Each period tau_mu, eddies of diameter d_mu form within one diameter of the interface,
    at the rate G = (2 Ai d_mu / Vtot) (N_mu / tau_mu), and process the volume
    K = G (pi/4) d_mu^2 lam_mu each second. An eddy formed with a fraction x of B has the
    linear mixture  c(x) = (1 - x) cA + x cB  after molecular mixing, and x is uniform on
    [0, 1]. Its volume joins
        B   when  [B](x) >= Blmt        x in [xB, 1]       fraction fB = 1 - xB
        A   when  it is neither               x in [xr, xB]     fraction fA = xB - xr
        r   when  [B](x) is within dCr of [B]A  x in [0, xr]    fraction fr = xr
    with xB = (Blmt - [B]A) / ([B]B - [B]A) and xr = dCr / ([B]B - [B]A), both clipped so
    that 0 <= xr <= xB <= 1 (the ordering condition of the review). Eddies that return to
    bulk (r) join volume A, so
        dVB/dt = 1/2 K (fB - fA - fr) + Qf        dVA/dt = 1/2 K (fA + fr - fB)
        d(nXA)/dt = K (X_mu-A + X_mu-r - 1/2 [X]A) - reaction
        d(nXB)/dt = K (X_mu-B - 1/2 [X]B)          - reaction      (+ Qf Bo for B)
    where X_mu-r, X_mu-A, X_mu-B are the integrals of c(x) over the three ranges of x (they
    sum to 1/2 ([X]A + [X]B), so the exchange conserves each species). The interface area
        dAi/dt = meso + G [ (1 - fr) dA_mu + fr dA_r ]     dA_mu = 1/2 (pi - 1) d_mu lam_mu,
                                                           dA_r = - d_mu lam_mu
    shrinks only when fr > dA_mu / (dA_mu + d_mu lam_mu), about 0.52. 'meso' is the
    mesomixing term of the document, switched off unless Nmezo > 0.

Open closures (the document leaves them open; each is a named parameter, see PARAMETERS
and the Parameters sheet of the workbook, where the column 'source' says which is which)
    C1  reaction: A and B react, rate kAB [A][B], in each bulk volume with its mean
        concentrations, after the eddy contents have joined it. Segregation therefore acts
        through K and the thresholds, as in the document, and not inside an eddy.
    C2  eddies: space filling, N_mu = fill / Veddy per unit volume with the eddy volume
        Veddy = pi/4 d_mu^2 lam_mu and lam_mu = 10 d_mu, so that K = fill 2 Ai d_mu / tau_mu:
        the interface zone (volume 2 Ai d_mu) is processed once per tau_mu. N_mu = 1/d_mu^3
        would make the eddies overlap (lam_mu > d_mu) and mix faster than one eddy lifetime.
    C3  interface area is limited above by Amax = min(Vtot / (2 d_mu), 2 VB / d_mu): a layer
        of B thinner than one eddy is already mixed, and the interface zone cannot be larger
        than the vessel. Without this limit the area grows without bound while fr < 0.52.
        With it the volume of B present settles near Qf tau_mu / 1.6, feed rate times a
        few eddy lifetimes. From below the area is limited by that of a sphere of volume
        VB, Amin = (36 pi)^(1/3) VB^(2/3): a volume cannot have less surface. Without this
        floor a slow feed lets Ai collapse to zero, where exponential growth cannot start
        again. The model is only meaningful while VB exceeds about one eddy volume.
    C4  Blmt = 0.9 Bo, dCr = 1 mol/m3, Ai(0) = area of a 1 mm feed jet, VB(0) = 1 uL.
    Change any of them through run(name=value).

Use
    import mumix
    result = mumix.run()                          # defaults, 1 h feed
    result.t, result.tables.nAA                   # times (s), state tables
    result.derived.beta                           # accumulation [B]A / Ao
    result.balances                               # relative residuals of the three balances
    mumix.write_xlsx(result, 'out/mumix.xlsx')    # workbook with charts (needs xlw)
    xl, book = mumix.build_workbook(result, 'out/mumix.xlsx'); xl.save()
    mumix.write_report(result, book, 'out')       # out/mumix.html + one svg per chart
    python mumix.py                               # writes results/mumix/ (xlsx, html, svg)
    mumix.result_table(result)                    # (headers, units, rows) of the Results sheet

Versions
    M01  m01.v01  2026-10-31  first version: the equations of the document as corrected in
                              the review, closures C1-C4.
         m01.v02  2026-10-31  the HTML report (write_report); crosses='min' on the log
                              axes of the charts; main() writes the xlsx, html and svgs.
"""

import math
import os
import sys
import warnings

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
for folder in ('tools', 'xlw', 'svgchart', 'htmlreport'):
    sys.path.insert(0, os.path.join(HERE, folder))
from use import load

load(asmodule=['odeproblem', 'fields'])
ODEproblem = odeproblem.ODEproblem
FIELDS = fields.Fields

__all__ = ['PARAMETERS', 'parameters', 'initial', 'rates', 'thresholds', 'segment_mean',
           'run', 'write_xlsx', 'kolmogorov', 'result_table', 'build_workbook',
           'write_report', 'main']

TINY = 1e-18                      # smallest volume used in a division (m3)
SPHERE = (36.0 * math.pi)**(1.0 / 3.0)    # area of a sphere = SPHERE * volume^(2/3)

# name: (default, unit, meaning, source). source: 'document' = the document states or implies
# it, 'assumed' = my choice, to be replaced.
PARAMETERS = {
    'Ao': (100.0, 'mol/m3', 'A concentration in the vessel at the start', 'assumed'),
    'Bo': (1000.0, 'mol/m3', 'B concentration of the feed (Bo = 10 Ao)', 'document'),
    'V0': (1.0e-3, 'm3', 'volume of the A solution at the start', 'assumed'),
    'tf': (3600.0, 's', 'feed time (1 h)', 'document'),
    'kAB': (1.0, 'm3/(mol s)', 'rate constant; tau_rxn = 1/(kAB Bo) = 1 ms', 'assumed'),
    'dmu': (50e-6, 'm', 'diameter of the micromixing (Kolmogorov) eddy', 'document'),
    'taumu': (2.5e-3, 's', 'lifetime of that eddy (Kolmogorov time at dmu = 50 um)',
              'assumed'),
    'lammu': (5.0e-4, 'm', 'effective length of the eddy, 10 dmu', 'assumed'),
    'fill': (1.0, '-', 'fraction of the interface zone renewed each tau_mu (1 = space '
             'filling eddies)', 'assumed'),
    'D': (1.0e-9, 'm2/s', 'molecular diffusivity', 'document'),
    'Blmt': (900.0, 'mol/m3', 'eddies with [B] above this join volume B (0.9 Bo)', 'assumed'),
    'dCr': (1.0, 'mol/m3', 'eddies within this of [B]A return to bulk', 'assumed'),
    'Ai0': (7.85e-7, 'm2', 'interface area at the start (1 mm feed jet)', 'assumed'),
    'VB0': (1.0e-9, 'm3', 'volume of B at the start (1 uL)', 'assumed'),
    'Nmezo': (0.0, '1/m3', 'mesoscale eddies per unit volume per tau_mezo (0 = off)',
              'assumed'),
    'de': (5.0e-3, 'm', 'mesoscale eddy diameter', 'assumed'),
    'taumezo': (0.3, 's', 'mesomixing time', 'document'),
    'l_over_de': (2.0, '-', 'spiral length over eddy diameter', 'assumed'),
    'lame': (2.0e-2, 'm', 'effective length of the mesoscale eddy', 'assumed'),
    'nout': (241, '-', 'number of output times from 0 to tf', 'assumed'),
}


def kolmogorov(eps, nu=1.0e-6):
    """Kolmogorov length (m) and time (s) for a dissipation eps (W/kg) and viscosity nu
    (m2/s): d = (nu^3 / eps)^(1/4), tau = (nu / eps)^(1/2)."""
    return (nu**3 / eps)**0.25, (nu / eps)**0.5


def parameters(**overrides):
    """The parameter Fields: every PARAMETERS default, the solver settings, then the
    overrides. Qf, tspan and the derived values are filled in here."""
    p = FIELDS()
    for name, (value, unit, meaning, source) in PARAMETERS.items():
        p[name] = value
    p.update(overrides)
    unknown = sorted(set(overrides) - set(PARAMETERS) - {'Racc', 'solver', 'Qo', 'title',
                                                         'MaxStep', 'monitorfun'})
    if unknown:
        raise KeyError(f'unknown parameter(s): {unknown}')
    p.setdefault('Racc', 1e-6)
    p.setdefault('solver', 'ode15s')
    p.setdefault('title', 'mumix fed batch')
    p.Vfeed = p.V0 * p.Ao / p.Bo                     # overall A:B of 1:1
    p.Qf = p.Vfeed / p.tf                            # feed rate (m3/s)
    p.Veddy = math.pi / 4 * p.dmu**2 * p.lammu       # volume of one eddy
    p.Nvol = p.fill / p.Veddy                        # space-filling eddies per unit volume
    p.Lmix = math.sqrt(p.D * p.taumu)                # diffusion length in an eddy lifetime
    p.dAmu = 0.5 * (math.pi - 1) * p.dmu * p.lammu   # area gained by an eddy kept apart
    p.dAr = -p.dmu * p.lammu                         # area lost by an eddy that returns
    p.dAmeso = 2 * (p.l_over_de - 1) * p.de * p.lame
    p.tspan = np.linspace(0.0, p.tf, int(p.nout))
    return p


def initial(p):
    """Initial state: the vessel holds A at Ao, a microlitre of B sits at the feed."""
    return dict(VA=p.V0, VB=p.VB0, Ai=p.Ai0, nAA=p.Ao * p.V0, nBA=0.0, nAB=0.0,
                nBB=p.Bo * p.VB0, nP=0.0)


def thresholds(cBA, cBB, Blmt, dCr):
    """(xB, xr): the x of the eddy whose mixed [B] equals Blmt, and the x whose [B] is
    within dCr of [B]A, clipped to 0 <= xr <= xB <= 1. When the two volumes have the same
    [B] no eddy can be told apart: everything returns to bulk."""
    spread = cBB - cBA
    if spread <= 1e-12 * max(abs(cBB), 1.0):
        return 1.0, 1.0
    xB = min(max((Blmt - cBA) / spread, 0.0), 1.0)
    xr = min(max(dCr / spread, 0.0), xB)
    return xB, xr


def segment_mean(cA, cB, x1, x2):
    """The integral of c(x) = (1 - x) cA + x cB over x from x1 to x2, per unit eddy volume:
    cA (x2 - x1) + 1/2 (x2^2 - x1^2) (cB - cA)."""
    return cA * (x2 - x1) + 0.5 * (x2 * x2 - x1 * x1) * (cB - cA)


def rates(v, p, ddt):
    """The ODE function for ODEproblem (v state and time, p parameters, ddt to fill)."""
    VA = max(v.VA, TINY)
    VB = max(v.VB, TINY)
    Vtot = VA + VB
    cAA = v.nAA / VA
    cBA = v.nBA / VA
    cAB = v.nAB / VB
    cBB = v.nBB / VB

    xB, xr = thresholds(cBA, cBB, p.Blmt, p.dCr)
    fr = xr
    fA = xB - xr
    fB = 1.0 - xB

    # eddy contents per unit eddy volume, over the three ranges of x
    Aur = segment_mean(cAA, cAB, 0.0, xr)
    AuA = segment_mean(cAA, cAB, xr, xB)
    AuB = segment_mean(cAA, cAB, xB, 1.0)
    Bur = segment_mean(cBA, cBB, 0.0, xr)
    BuA = segment_mean(cBA, cBB, xr, xB)
    BuB = segment_mean(cBA, cBB, xB, 1.0)

    Ai = max(v.Ai, 0.0)
    G = 2.0 * Ai * p.dmu * p.Nvol / p.taumu                # eddy formations per second
    K = G * p.Veddy                                        # volume processed per second

    rA = p.kAB * max(cAA, 0.0) * max(cBA, 0.0)             # reaction in volume A
    rB = p.kAB * max(cAB, 0.0) * max(cBB, 0.0)             # reaction in volume B
    Qf = p.Qf if v.t <= p.tf else 0.0

    ddt.VB = 0.5 * K * (fB - fA - fr) + Qf
    ddt.VA = 0.5 * K * (fA + fr - fB)
    ddt.nAA = K * (AuA + Aur - 0.5 * cAA) - rA * VA
    ddt.nBA = K * (BuA + Bur - 0.5 * cBA) - rA * VA
    ddt.nAB = K * (AuB - 0.5 * cAB) - rB * VB
    ddt.nBB = K * (BuB - 0.5 * cBB) + Qf * p.Bo - rB * VB
    ddt.nP = rA * VA + rB * VB

    growth = G * ((1.0 - fr) * p.dAmu + fr * p.dAr)
    if p.Nmezo > 0.0:
        growth += 2.0 * Ai * p.de * p.Nmezo / p.taumezo * p.dAmeso
    Amin = SPHERE * VB**(2.0 / 3.0)                        # closure C3, lower limit
    Amax = max(Amin, min(Vtot / (2.0 * p.dmu), 2.0 * VB / p.dmu))     # and upper limit
    if growth > 0.0:
        growth *= max(0.0, 1.0 - Ai / Amax)
    ddt.Ai = growth - max(0.0, Ai - Amax) / p.taumu + max(0.0, Amin - Ai) / p.taumu
    return ddt


def derive(p, t, tables):
    """Concentrations, fractions and balances from the state tables."""
    VA = np.maximum(tables.VA, TINY)
    VB = np.maximum(tables.VB, TINY)
    d = FIELDS()
    d.cAA = tables.nAA / VA
    d.cBA = tables.nBA / VA
    d.cAB = tables.nAB / VB
    d.cBB = tables.nBB / VB
    d.beta = np.maximum(d.cBA, 1e-30) / p.Ao                 # accumulation of B in volume A
    d.conversion = tables.nP / (p.Ao * p.V0)
    d.xB = np.zeros(t.size)
    d.xr = np.zeros(t.size)
    for i in range(t.size):
        d.xB[i], d.xr[i] = thresholds(d.cBA[i], d.cBB[i], p.Blmt, p.dCr)
    d.fr = d.xr
    d.fA = d.xB - d.xr
    d.fB = 1.0 - d.xB
    G = 2.0 * tables.Ai * p.dmu * p.Nvol / p.taumu
    d.K = G * p.Veddy
    return d


def balances(p, t, tables):
    """Relative residuals of the species A and B balances and of the volume balance: all
    should be zero to the solver tolerance."""
    fed = p.Qf * np.minimum(t, p.tf)
    a_total = p.Ao * p.V0
    b_total = p.Bo * (p.VB0 + fed)
    out = FIELDS()
    out.A = (tables.nAA + tables.nAB + tables.nP - a_total) / a_total
    out.B = (tables.nBA + tables.nBB + tables.nP - b_total) / np.maximum(b_total, TINY)
    out.volume = (tables.VA + tables.VB - (p.V0 + p.VB0 + fed)) / (p.V0 + p.VB0)
    return out


def run(**overrides):
    """Solve the model; returns Fields with p, t, tables, derived, balances, problem."""
    p = parameters(**overrides)
    problem = ODEproblem(p, initial(p), rates)
    with warnings.catch_warnings():
        # nP (the product) feeds nothing back, so its column of scipy's finite-difference
        # Jacobian is zero and scipy multiplies that column's step by 10 at every Jacobian
        # until it overflows (long runs only). Harmless: the balances close to 1e-13.
        warnings.filterwarnings('ignore', message='overflow encountered in multiply',
                                category=RuntimeWarning)
        t, tables = problem.solve(p.tspan)
    result = FIELDS()
    result.p = p
    result.t = t
    result.tables = tables
    result.derived = derive(p, t, tables)
    result.balances = balances(p, t, tables)
    result.problem = problem
    return result


# ------------------------------------------------------------------------ output ---------
COLUMNS = (('t', 's', lambda r: r.t),
           ('VA', 'mL', lambda r: r.tables.VA * 1e6),
           ('VB', 'uL', lambda r: r.tables.VB * 1e9),
           ('Ai', 'cm2', lambda r: r.tables.Ai * 1e4),
           ('[A] in A', 'mol/m3', lambda r: r.derived.cAA),
           ('[B] in A', 'mol/m3', lambda r: r.derived.cBA),
           ('[A] in B', 'mol/m3', lambda r: r.derived.cAB),
           ('[B] in B', 'mol/m3', lambda r: r.derived.cBB),
           ('beta', '-', lambda r: r.derived.beta),
           ('conversion of A', '-', lambda r: r.derived.conversion),
           ('fB', '-', lambda r: r.derived.fB),
           ('fA', '-', lambda r: r.derived.fA),
           ('fr', '-', lambda r: r.derived.fr),
           ('K', 'mL/s', lambda r: r.derived.K * 1e6))


def result_table(result):
    """(headers, units, rows): the output columns of the Results sheet as plain lists."""
    columns = [function(result) for name, unit, function in COLUMNS]
    headers = [name for name, unit, function in COLUMNS]
    units = [unit for name, unit, function in COLUMNS]
    rows = [[float(column[i]) for column in columns] for i in range(len(result.t))]
    return headers, units, rows


def build_workbook(result, filename):
    """The xlw object holding the Results and Parameters sheets and the charts."""
    from xlw import xlw
    import xlchart
    xl = xlw()
    base = os.path.splitext(os.path.basename(filename))[0]
    xl.newbook(filename, 'Results', 'Parameters')
    book = getattr(xl, base)
    headers, units, rows = result_table(result)
    xl.write(headers, 'Heading_3', 'halign', 'center').nl()
    xl.write(units, 'Explanatory_Text', 'halign', 'center').nl()
    xl.write(rows)
    n = len(rows)
    last = 2 + n
    first_data = 3

    def column(name):
        return headers.index(name) + 1

    def rng(name, first=first_data):
        return xlchart.ref('Results', first, column(name), last, column(name))

    sheet = book.Results
    # chart 1: the A volume, [A] left and [B] right
    c1 = sheet.chart('concentrations')
    c1.title.text = 'Concentrations in volume A'
    c1.xaxis.title.text = 'time (s)'
    c1.yaxis.title.text = '[A] in A  (mol/m3)'
    c1.y2axis.title.text = '[B] in A  (mol/m3)'
    c1.legend.pos = 'b'
    xlchart.add_series(c1, rng('t'), rng('[A] in A'), label='[A] in A',
                       line=dict(color='4472C4', width=2.25), marker=dict(symbol='none'))
    xlchart.add_series(c1, rng('t'), rng('[B] in A'), label='[B] in A', axis=2,
                       line=dict(color='ED7D31', width=2.25), marker=dict(symbol='none'))
    xlchart.place(c1, col=len(headers) + 1, row=1, ncols=9, nrows=18)
    # chart 2: accumulation on a log axis (the first row, beta = 0, is left out)
    c2 = sheet.chart('accumulation')
    c2.title.text = 'Accumulation of B in volume A'
    c2.xaxis.title.text = 'time (s)'
    c2.yaxis.title.text = [('beta = [B]', {}), ('A', {'baseline': -25}), (' / A', {}),
                           ('o', {'baseline': -25})]
    c2.yaxis.log = 10
    c2.yaxis.crosses = 'min'            # the x axis at the bottom: autoZero on a log axis is 1
    c2.yaxis.gridminor = xlchart.rec(color='EEEEEE', width=0.5)
    xlchart.add_series(c2, rng('t', first_data + 1), rng('beta', first_data + 1),
                       label='beta', line=dict(color='C00000', width=2.25),
                       marker=dict(symbol='none'))
    xlchart.place(c2, col=len(headers) + 1, row=20, ncols=9, nrows=18)
    # chart 3: interface area and B volume, both on log axes
    c3 = sheet.chart('interface')
    c3.title.text = 'Interface area and volume of B'
    c3.xaxis.title.text = 'time (s)'
    c3.yaxis.title.text = 'Ai (cm2)'
    c3.y2axis.title.text = 'VB (uL)'
    c3.yaxis.log = 10
    c3.yaxis.crosses = 'min'
    c3.y2axis.log = 10
    c3.legend.pos = 'b'
    xlchart.add_series(c3, rng('t', first_data + 1), rng('Ai', first_data + 1), label='Ai',
                       line=dict(color='70AD47', width=2.25), marker=dict(symbol='none'))
    xlchart.add_series(c3, rng('t', first_data + 1), rng('VB', first_data + 1), label='VB',
                       axis=2, line=dict(color='5B9BD5', width=2.25, dash='dash'),
                       marker=dict(symbol='none'))
    xlchart.place(c3, col=len(headers) + 1, row=39, ncols=9, nrows=18)

    # the parameters, with where each value comes from
    xl.activate(book.Parameters)
    xl.move('home')
    xl.write(['name', 'value', 'unit', 'meaning', 'source'], 'Heading_3').nl()
    for name, (default, unit, meaning, source) in PARAMETERS.items():
        value = result.p[name]
        xl.write([name, float(value), unit, meaning, source])
        xl.nl()
    xl.write(['derived', '', '', '', ''], 'Heading_3').nl()
    for name, unit, meaning in DERIVED:
        xl.write([name, float(result.p[name]), unit, meaning, 'derived']).nl()
    xl.activate(book.Results)
    return xl, book


def write_xlsx(result, filename):
    """Write the workbook (Results, Parameters, three charts) and return the path."""
    xl, book = build_workbook(result, filename)
    xl.save()
    return book.kvr('priv').kvr('fname')


REPORT_COLUMNS = ('t', 'VA', 'VB', 'Ai', '[A] in A', '[B] in A', 'beta', 'conversion of A',
                  'fB', 'fA', 'fr')
REPORT_ROWS = 15
DERIVED = (('Vfeed', 'm3', 'feed volume: V0 Ao / Bo (overall A:B = 1:1)'),
           ('Qf', 'm3/s', 'feed rate Vfeed / tf'),
           ('Lmix', 'm', 'sqrt(D taumu), diffusion length in one eddy lifetime'),
           ('Veddy', 'm3', 'pi/4 dmu^2 lammu'))
NOTES = ('Model: "A phenomenological model for micromixing" (the .docx in the project root), '
         'equations as corrected in the review.',
         'C1  A and B react at rate kAB [A][B] in each bulk volume, after the eddy contents '
         'have joined it.',
         'C2  Eddies fill space: N_mu = fill / Veddy per unit volume, so the interface zone '
         '(volume 2 Ai dmu) is renewed once per taumu.',
         'C3  The interface area is held between that of a sphere of volume VB and '
         'min(Vtot / (2 dmu), 2 VB / dmu).',
         'C4  Blmt, dCr, Ai0 and VB0 are chosen values.',
         'Rows marked in the parameter table are my choices, not stated in the document: '
         'replace them with measured values before drawing conclusions.')


def write_report(result, book, folder, stem='mumix', generated=None):
    """Write folder/stem.html and one stem_<chart>.svg per chart; returns the page path.
    The page holds the run summary, the charts (drawn from the chart nodes of `book`, the
    workbook of build_workbook), a sample of the results table, the parameters, the
    balances and the closures, and links to stem.xlsx for the full table."""
    import report
    p = result.p
    d = result.derived
    tables = result.tables
    headers, units, rows = result_table(result)
    pick = [headers.index(name) for name in REPORT_COLUMNS]
    shown = report.sample_rows(rows, REPORT_ROWS)
    results = report.table_html(
        [headers[j] for j in pick], [units[j] for j in pick],
        [[row[j] for j in pick] for row in shown],
        caption=f'{len(shown)} of {len(rows)} output times; the full table is the Results '
        f'sheet of {stem}.xlsx')
    mid = len(result.t) // 2
    facts = report.facts_html([
        ('feed time', p.tf, 's'),
        ('conversion of A at the end', d.conversion[-1], ''),
        ('accumulation beta at half the feed', d.beta[mid], ''),
        ('accumulation beta at the end', d.beta[-1], ''),
        ('volume of B at the end', tables.VB[-1] * 1e9, 'uL'),
        ('interface area at the end', tables.Ai[-1] * 1e4, 'cm2'),
        ('output times', len(result.t), '')])
    names = list(PARAMETERS)
    parameter_rows = [[name, float(p[name]), PARAMETERS[name][1], PARAMETERS[name][2],
                       PARAMETERS[name][3]] for name in names]
    parameter_rows += [[name, float(p[name]), unit, meaning, 'derived']
                       for name, unit, meaning in DERIVED]
    flags = ['flag' if row[4] == 'assumed' else None for row in parameter_rows]
    parameter_table = report.table_html(['name', 'value', 'unit', 'meaning', 'source'], None,
                                        parameter_rows, row_classes=flags)
    balance_table = report.table_html(
        ['balance', 'largest relative residual'], None,
        [[name, float(np.max(np.abs(result.balances[name])))]
         for name in ('A', 'B', 'volume')],
        caption='species A, species B and volume; zero up to the solver tolerance')
    charts = report.book_charts(book)
    sections = [('Run', facts),
                ('Charts', report.charts_section(charts, stem)),
                ('Results', results),
                ('Parameters', parameter_table),
                ('Balances', balance_table),
                ('Model notes', report.list_html(NOTES))]
    subtitle = (f'Fed batch, A + B -> P: {p.Ao:g} mol/m3 A in {p.V0 * 1e6:g} mL, '
                f'{p.Bo:g} mol/m3 B fed over {p.tf:g} s')
    text = report.page('Micromixing model', sections, subtitle=subtitle,
                       workbook=stem + '.xlsx', generated=generated)
    report.write_charts(folder, stem, charts)
    return report.write_page(folder, stem + '.html', text)


def main():
    """Run with the defaults and write results/mumix/ (mumix.xlsx, mumix.html and one svg
    per chart)."""
    import datetime
    result = run()
    folder = os.path.join(HERE, 'results', 'mumix')
    os.makedirs(folder, exist_ok=True)
    xl, book = build_workbook(result, os.path.join(folder, 'mumix.xlsx'))
    xl.save()
    print('wrote', book.kvr('priv').kvr('fname'))
    page = write_report(result, book, folder, generated=datetime.date.today().isoformat())
    print('wrote', page)
    return result


if __name__ == '__main__':
    main()
