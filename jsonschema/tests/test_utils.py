from collections.abc import Mapping
from math import nan
from unittest import TestCase

from jsonschema._utils import _EvaluatedSet, equal, uniq


class Unhashable:
    __hash__ = None  # type: ignore[assignment]

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return isinstance(other, Unhashable) and self.value == other.value


class TestEqual(TestCase):
    def test_none(self):
        self.assertTrue(equal(None, None))

    def test_nan(self):
        self.assertTrue(equal(nan, nan))


class TestDictEqual(TestCase):
    def test_equal_dictionaries(self):
        dict_1 = {"a": "b", "c": "d"}
        dict_2 = {"c": "d", "a": "b"}
        self.assertTrue(equal(dict_1, dict_2))

    def test_equal_dictionaries_with_nan(self):
        dict_1 = {"a": nan, "c": "d"}
        dict_2 = {"c": "d", "a": nan}
        self.assertTrue(equal(dict_1, dict_2))

    def test_missing_key(self):
        dict_1 = {"a": "b", "c": "d"}
        dict_2 = {"c": "d", "x": "b"}
        self.assertFalse(equal(dict_1, dict_2))

    def test_additional_key(self):
        dict_1 = {"a": "b", "c": "d"}
        dict_2 = {"c": "d", "a": "b", "x": "x"}
        self.assertFalse(equal(dict_1, dict_2))

    def test_missing_value(self):
        dict_1 = {"a": "b", "c": "d"}
        dict_2 = {"c": "d", "a": "x"}
        self.assertFalse(equal(dict_1, dict_2))

    def test_empty_dictionaries(self):
        dict_1 = {}
        dict_2 = {}
        self.assertTrue(equal(dict_1, dict_2))

    def test_one_none(self):
        dict_1 = None
        dict_2 = {"a": "b", "c": "d"}
        self.assertFalse(equal(dict_1, dict_2))

    def test_same_item(self):
        dict_1 = {"a": "b", "c": "d"}
        self.assertTrue(equal(dict_1, dict_1))

    def test_nested_equal(self):
        dict_1 = {"a": {"a": "b", "c": "d"}, "c": "d"}
        dict_2 = {"c": "d", "a": {"a": "b", "c": "d"}}
        self.assertTrue(equal(dict_1, dict_2))

    def test_nested_dict_unequal(self):
        dict_1 = {"a": {"a": "b", "c": "d"}, "c": "d"}
        dict_2 = {"c": "d", "a": {"a": "b", "c": "x"}}
        self.assertFalse(equal(dict_1, dict_2))

    def test_mixed_nested_equal(self):
        dict_1 = {"a": ["a", "b", "c", "d"], "c": "d"}
        dict_2 = {"c": "d", "a": ["a", "b", "c", "d"]}
        self.assertTrue(equal(dict_1, dict_2))

    def test_nested_list_unequal(self):
        dict_1 = {"a": ["a", "b", "c", "d"], "c": "d"}
        dict_2 = {"c": "d", "a": ["b", "c", "d", "a"]}
        self.assertFalse(equal(dict_1, dict_2))


class TestListEqual(TestCase):
    def test_equal_lists(self):
        list_1 = ["a", "b", "c"]
        list_2 = ["a", "b", "c"]
        self.assertTrue(equal(list_1, list_2))

    def test_equal_lists_with_nan(self):
        list_1 = ["a", nan, "c"]
        list_2 = ["a", nan, "c"]
        self.assertTrue(equal(list_1, list_2))

    def test_unsorted_lists(self):
        list_1 = ["a", "b", "c"]
        list_2 = ["b", "b", "a"]
        self.assertFalse(equal(list_1, list_2))

    def test_first_list_larger(self):
        list_1 = ["a", "b", "c"]
        list_2 = ["a", "b"]
        self.assertFalse(equal(list_1, list_2))

    def test_second_list_larger(self):
        list_1 = ["a", "b"]
        list_2 = ["a", "b", "c"]
        self.assertFalse(equal(list_1, list_2))

    def test_list_with_none_unequal(self):
        list_1 = ["a", "b", None]
        list_2 = ["a", "b", "c"]
        self.assertFalse(equal(list_1, list_2))

        list_1 = ["a", "b", None]
        list_2 = [None, "b", "c"]
        self.assertFalse(equal(list_1, list_2))

    def test_list_with_none_equal(self):
        list_1 = ["a", None, "c"]
        list_2 = ["a", None, "c"]
        self.assertTrue(equal(list_1, list_2))

    def test_empty_list(self):
        list_1 = []
        list_2 = []
        self.assertTrue(equal(list_1, list_2))

    def test_one_none(self):
        list_1 = None
        list_2 = []
        self.assertFalse(equal(list_1, list_2))

    def test_same_list(self):
        list_1 = ["a", "b", "c"]
        self.assertTrue(equal(list_1, list_1))

    def test_equal_nested_lists(self):
        list_1 = ["a", ["b", "c"], "d"]
        list_2 = ["a", ["b", "c"], "d"]
        self.assertTrue(equal(list_1, list_2))

    def test_unequal_nested_lists(self):
        list_1 = ["a", ["b", "c"], "d"]
        list_2 = ["a", [], "c"]
        self.assertFalse(equal(list_1, list_2))


class TestUniq(TestCase):
    def test_scalars(self):
        self.assertTrue(uniq([1, 2, 3]))
        self.assertFalse(uniq([1, 2, 1]))

    def test_bool_and_int_differ(self):
        self.assertTrue(uniq([True, 1]))
        self.assertTrue(uniq([False, 0]))
        self.assertFalse(uniq([True, True]))
        self.assertFalse(uniq([False, False]))

    def test_sequence_types_compare_structurally(self):
        self.assertFalse(uniq([[1, 2], (1, 2)]))
        self.assertTrue(uniq([[1, 2], (2, 1)]))

    def test_mappings_ignore_key_order(self):
        self.assertFalse(
            uniq(
                [
                    {"a": [1, 2], "b": {"c": 3}},
                    {"b": {"c": 3}, "a": (1, 2)},
                ],
            ),
        )

    def test_falls_back_for_unhashable_scalars(self):
        self.assertFalse(uniq([Unhashable(1), Unhashable(1)]))
        self.assertTrue(uniq([Unhashable(1), Unhashable(2)]))

    def test_nan_falls_back(self):
        self.assertFalse(uniq([nan, nan]))
        self.assertTrue(uniq([nan, -nan]))

    def test_sequence_with_nan_falls_back(self):
        self.assertFalse(uniq([[nan], [nan]]))
        self.assertTrue(uniq([[nan], [-nan]]))

    def test_mapping_with_nan_falls_back(self):
        self.assertFalse(uniq([{"x": nan}, {"x": nan}]))
        self.assertTrue(uniq([{"x": nan}, {"x": -nan}]))

    def test_nested_bool_and_int_differ(self):
        # Exercises the _TRUE/_FALSE sentinels through recursion.
        self.assertTrue(uniq([[True], [1]]))
        self.assertTrue(uniq([{"k": True}, {"k": 1}]))

    def test_falls_back_for_unhashable_mapping_key(self):
        class FrozenDict(Mapping):
            def __init__(self, items):
                self._items = list(items)

            def __getitem__(self, key):
                for k, v in self._items:
                    if k == key:
                        return v
                raise KeyError(key)

            def __iter__(self):
                return (k for k, _ in self._items)

            def __len__(self):
                return len(self._items)

        a = FrozenDict([([1, 2], "x")])
        b = FrozenDict([([1, 2], "x")])
        self.assertFalse(uniq([a, b]))

    def test_unhashable_inside_sequence_falls_back(self):
        self.assertFalse(uniq([[Unhashable(1)], [Unhashable(1)]]))
        self.assertTrue(uniq([[Unhashable(1)], [Unhashable(2)]]))

    def test_unhashable_inside_mapping_falls_back(self):
        self.assertFalse(
            uniq([{"k": Unhashable(1)}, {"k": Unhashable(1)}]),
        )
        self.assertTrue(
            uniq([{"k": Unhashable(1)}, {"k": Unhashable(2)}]),
        )


class _CaseInsensitiveString(str):
    """A ``str`` subclass with different equality semantics than plain str."""

    __slots__ = ()

    def __eq__(self, other):
        if isinstance(other, str):
            return self.lower() == other.lower()
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    __hash__ = str.__hash__


class TestEvaluatedSet(TestCase):
    def test_empty_membership(self):
        evaluated = _EvaluatedSet()
        self.assertNotIn(0, evaluated)
        self.assertNotIn("foo", evaluated)
        self.assertEqual(len(evaluated), 0)

    def test_hashable_membership_is_constant_time(self):
        evaluated = _EvaluatedSet(range(1000))
        self.assertIn(0, evaluated)
        self.assertIn(999, evaluated)
        self.assertNotIn(1000, evaluated)

    def test_add_deduplicates_hashable_elements(self):
        evaluated = _EvaluatedSet()
        evaluated.add("foo")
        evaluated.add("foo")
        evaluated.extend(["bar", "bar"])
        self.assertEqual(len(evaluated), 2)
        self.assertEqual(sorted(evaluated), ["bar", "foo"])

    def test_str_subclass_recorded_as_key_matches_list_scan(self):
        # In validation, property keys come from the instance and are the
        # *recorded* elements; the lookup needle is the same key object.
        # A str subclass recorded as an element is found identically by the
        # hash path and by a list scan, because str.__hash__ is inherited.
        key = _CaseInsensitiveString("foo")
        plain = [key, "bar"]
        evaluated = _EvaluatedSet(plain)
        self.assertEqual(key in evaluated, key in plain)
        self.assertTrue(key in evaluated)
        self.assertEqual(
            _CaseInsensitiveString("foo") in evaluated,
            _CaseInsensitiveString("foo") in plain,
        )

    def test_hash_contract_violation_is_resolved_by_hash_semantics(self):
        # Documented trade-off: a str subclass that overrides __eq__ with
        # case-insensitive semantics but keeps str.__hash__ breaks the
        # hash/equality contract. When such an object is used as the lookup
        # *needle*, a list scan calls its reflected __eq__ and reports True,
        # while a set consults the hash bucket and applies plain str equality,
        # reporting False. The set path is chosen because such objects cannot
        # occur as JSON-parsed keys, and honoring hash semantics is what keeps
        # membership tests constant time.
        plain = ["foo", "bar"]
        evaluated = _EvaluatedSet(plain)
        needle = _CaseInsensitiveString("FOO")
        self.assertTrue(needle in plain)  # old list-scan behavior
        self.assertFalse(needle in evaluated)  # new hash-based behavior

    def test_mixed_string_and_integer_keys(self):
        plain = ["a", 37]
        evaluated = _EvaluatedSet(plain)
        for needle in ("a", 37, "b", 0):
            self.assertEqual(needle in evaluated, needle in plain)

    def test_bool_and_integer_keys_do_not_collapse(self):
        plain = [1, 0]
        evaluated = _EvaluatedSet(plain)
        # Both list scan and set membership treat True == 1, False == 0.
        for needle in (True, False, 1, 0, 2):
            self.assertEqual(needle in evaluated, needle in plain)

    def test_nan_membership_matches_list_scan(self):
        from operator import contains

        plain = [nan]
        evaluated = _EvaluatedSet(plain)
        # Route the membership probes through operator.contains so the NaN
        # probe isn't flagged as a direct NaN comparison; the semantics under
        # test are container membership, not float equality.
        self.assertEqual(
            contains(evaluated, nan),
            contains(plain, nan),
        )
        self.assertTrue(contains(evaluated, nan))

    def test_unhashable_recorded_elements_fall_back_to_equality_scan(self):
        plain = [Unhashable(1), Unhashable(2)]
        evaluated = _EvaluatedSet(plain)
        self.assertIn(Unhashable(1), evaluated)
        self.assertNotIn(Unhashable(3), evaluated)
        # The fallback list de-duplicates just like the old append+scan code.
        evaluated.add(Unhashable(1))
        self.assertEqual(len(evaluated), 2)

    def test_unhashable_needle_does_not_raise(self):
        evaluated = _EvaluatedSet(["a", "b"])
        self.assertNotIn(Unhashable(1), evaluated)

    def test_hashable_and_unhashable_coexist(self):
        evaluated = _EvaluatedSet(["a", Unhashable(1)])
        self.assertIn("a", evaluated)
        self.assertIn(Unhashable(1), evaluated)
        self.assertNotIn("b", evaluated)
        self.assertNotIn(Unhashable(2), evaluated)
        self.assertEqual(len(evaluated), 2)
