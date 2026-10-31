r"""b_<unit>.py -- tests and benchmarks for <unit>.   (benchtest suite template)

Fill in: SOURCES, the import line, setup_fixtures, one test_* per behaviour, one bench_* per
key action. A suite is the unit's contract (test_*) and its timing (bench_*): the tests run
first, and the benchmarks run only if every test passed.

Run from the project root:
    python tools/runbench.py b_<unit>
"""

import sys


def findtools():                      # walk up to the folder that holds tools/
    from os.path import abspath, dirname, isdir, join
    here = dirname(abspath(__file__))
    while here != dirname(here) and not isdir(join(here, 'tools')):
        here = dirname(here)
    sys.path.insert(0, join(here, 'tools'))


findtools()
from bench import bench
from use import use

use('primary', 'silent')
SOURCES = ['<unit>']             # the modules this suite tests: the report shows the code that ran
from <unit> import <Unit>, <UnitError>


class b_<unit>(bench):
    BenchName = '<unit>'
    BenchVersion = 'M1.0.0'          # runbench adds 1 to the last number on every run
    BenchHeader = ''
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        cls.data = [1, 2, 3]

    def test_T1_bad_input_raises(self):
        with self.assertRaises(<UnitError>):
            <Unit>(None)

    def test_T2_happy_path(self):
        self.assertEqual(<Unit>(self.data), self.data)

    def bench_key_action(self, timer):
        with timer as test:
            while test.more:
                # prepare: not timed
                for _ in test.count:
                    <Unit>(self.data)
        return 'key action', 'group'

