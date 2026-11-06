"""
b_fields.py -- tests and benchmarks for Fields, a dict whose keys are also attributes.

Fields is what ODEproblem hands to a model function, so v.VA, p.k and ddt.VA = ... read like
the maths. The tests cover construction, attribute and item access, nesting, the dict
behaviour that must not change, and the one documented trap: a key named like a dict
method reads back as the method.

Run from the project root:
    python tools/runbench.py tests/b_fields.py
"""

import sys


def findtools():                      # walk up to the folder that holds tools/
    from os.path import abspath, dirname, isdir, join
    here = dirname(abspath(__file__))
    while here != dirname(here) and not isdir(join(here, 'tools')):
        here = dirname(here)
    sys.path.insert(0, join(here, 'tools'))


findtools()
from use import load
from bench import bench

SOURCES = ['fields']
load('fields')          # Fields


class b_fields(bench):
    BenchName = 'fields'
    BenchVersion = 'M1.0.6'
    BenchHeader = ''
    sources = SOURCES

    @classmethod
    def setup_fixtures(cls):
        cls.record = Fields(a=1.0, b=dict(c=2.0), d=[1, 2, 3])

    # ---- construction ----------------------------------------------------------------
    def test_T01_construct_from_keywords_and_from_a_dict(self):
        self.assertEqual(Fields(a=1, b=2), {'a': 1, 'b': 2})
        self.assertEqual(Fields({'a': 1}, b=2), {'a': 1, 'b': 2})
        self.assertEqual(Fields(), {})

    def test_T02_a_fields_is_a_dict(self):
        record = Fields(a=1)
        self.assertIsInstance(record, dict)
        self.assertEqual(len(record), 1)
        self.assertIn('a', record)
        self.assertEqual(list(record), ['a'])
        self.assertEqual(record.get('z', 7), 7)

    def test_T03_nested_dicts_become_fields(self):
        record = Fields(a=dict(b=dict(c=5)))
        self.assertIsInstance(record.a, Fields)
        self.assertIsInstance(record.a.b, Fields)
        self.assertEqual(record.a.b.c, 5)

    # ---- attribute and item access -------------------------------------------------------
    def test_T04_attribute_read_equals_item_read(self):
        record = Fields(x=3.5)
        self.assertEqual(record.x, record['x'])

    def test_T05_attribute_write_is_item_write(self):
        record = Fields()
        record.x = 4
        self.assertEqual(record['x'], 4)
        record['y'] = 5
        self.assertEqual(record.y, 5)

    def test_T06_a_missing_attribute_raises_attribute_error(self):
        with self.assertRaises(AttributeError):
            Fields().missing

    def test_T07_attribute_delete(self):
        record = Fields(x=1)
        del record.x
        self.assertNotIn('x', record)
        with self.assertRaises(AttributeError):
            del record.x

    def test_T08_a_chain_of_attributes_assigns_into_a_nested_record(self):
        record = Fields(s=dict(a=1))
        record.s.a = 9
        record.s.b = 10
        self.assertEqual(record['s']['a'], 9)
        self.assertEqual(record.s.b, 10)

    # ---- values that are stored -------------------------------------------------------------
    def test_T09_setting_a_dict_converts_it(self):
        record = Fields()
        record.inner = {'k': 1}
        self.assertIsInstance(record.inner, Fields)
        record['other'] = {'k': 2}
        self.assertIsInstance(record.other, Fields)

    def test_T10_update_converts_nested_dicts_too(self):
        record = Fields()
        record.update({'a': {'b': 1}}, c={'d': 2})
        self.assertIsInstance(record.a, Fields)
        self.assertIsInstance(record.c, Fields)
        self.assertEqual(record.c.d, 2)

    def test_T11_other_values_pass_through_untouched(self):
        import numpy
        array = numpy.arange(3.0)
        items = [1, 2]
        record = Fields(array=array, items_list=items)
        self.assertIs(record.array, array)
        self.assertIs(record.items_list, items)
        inner = Fields(z=1)
        record.inner = inner
        self.assertIs(record.inner, inner)

    def test_T12_none_and_falsy_values_are_kept(self):
        record = Fields(zero=0, empty='', off=False, nothing=None)
        self.assertEqual(record.zero, 0)
        self.assertEqual(record.empty, '')
        self.assertIs(record.off, False)
        self.assertIsNone(record.nothing)
        self.assertIn('nothing', record)

    # ---- copy, repr, dir ---------------------------------------------------------------------
    def test_T13_copy_is_a_fields_with_the_same_content(self):
        record = Fields(a=1, b=dict(c=2))
        clone = record.copy()
        self.assertIsInstance(clone, Fields)
        self.assertEqual(clone, record)
        clone.a = 99
        self.assertEqual(record.a, 1)

    def test_T14_repr_names_the_class_and_shows_the_content(self):
        self.assertEqual(repr(Fields(a=1)), "Fields({'a': 1})")

    def test_T15_dir_lists_the_keys_and_the_dict_methods(self):
        names = dir(Fields(alpha=1, beta=2))
        self.assertIn('alpha', names)
        self.assertIn('beta', names)
        self.assertIn('items', names)
        self.assertEqual(names, sorted(names))

    # ---- the documented trap -------------------------------------------------------------------
    def test_T16_a_key_named_like_a_dict_method_reads_back_as_the_method(self):
        record = Fields()
        record.items = 5                       # allowed to write ...
        self.assertEqual(record['items'], 5)   # ... readable as an item ...
        self.assertTrue(callable(record.items))  # ... but the attribute is dict.items

    def test_T17_ordinary_names_do_not_clash(self):
        record = Fields(VA=1.0, nAA=2.0, Ai=3.0, t=4.0)
        self.assertEqual((record.VA, record.nAA, record.Ai, record.t), (1.0, 2.0, 3.0, 4.0))

    def test_T18_equality_and_json_like_use(self):
        self.assertEqual(Fields(a=Fields(b=1)), {'a': {'b': 1}})
        self.assertEqual(dict(Fields(a=1, b=2)), {'a': 1, 'b': 2})

    # ---- benchmarks -------------------------------------------------------------------------------
    def bench_attribute_read(self, timer):
        record = self.record
        with timer as test:
            while test.more:
                for i in test.count:
                    record.a
        return 'record.a', 'read'

    def bench_item_read(self, timer):
        record = self.record
        with timer as test:
            while test.more:
                for i in test.count:
                    record['a']
        return "record['a']", 'read'

    def bench_nested_attribute_read(self, timer):
        record = self.record
        with timer as test:
            while test.more:
                for i in test.count:
                    record.b.c
        return 'record.b.c', 'read'

    def bench_attribute_write(self, timer):
        record = self.record
        with timer as test:
            while test.more:
                for i in test.count:
                    record.a = 2.0
        return 'record.a = 2.0', 'write'

    def bench_write_a_dict(self, timer):
        record = Fields()
        value = {'k': 1}
        with timer as test:
            while test.more:
                for i in test.count:
                    record.inner = value
        return 'record.inner = {...}  (converts)', 'write'
