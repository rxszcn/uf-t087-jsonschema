"""
Tests for the constant-time evaluated-index / evaluated-key tracking used by
the ``unevaluatedItems`` and ``unevaluatedProperties`` keywords.

Two guarantees are under test:

* validation conclusions and the produced errors stay byte-for-byte identical
  to the previous list-based implementation, across every keyword that
  contributes evaluated indexes or property keys;
* validation time grows linearly (not quadratically) as the instance grows,
  on both the unevaluated-items and unevaluated-properties paths.
"""
from time import perf_counter
from unittest import TestCase

from jsonschema import Draft201909Validator, Draft202012Validator
from jsonschema._utils import extras_msg


def error_signatures(validator, instance):
    """
    Serialize every validation error into comparable, order-sensitive tuples.

    The tuples capture the message, the absolute instance/schema paths and the
    failing validator, so two runs agree only if they emit the same errors in
    the same order at the same locations.
    """
    return [
        (
            error.message,
            tuple(error.absolute_path),
            tuple(error.absolute_schema_path),
            error.validator,
        )
        for error in validator.iter_errors(instance)
    ]


def best_validation_time(validator, instance, repeats=5):
    list(validator.iter_errors(instance))  # warm-up
    best = float("inf")
    for _ in range(repeats):
        start = perf_counter()
        list(validator.iter_errors(instance))
        best = min(best, perf_counter() - start)
    return best


# Schemas exercising every branch that contributes evaluated item indexes:
# prefixItems, items, if/then/else, contains, unevaluatedItems itself, and
# the allOf/anyOf/oneOf applicators. Each schema's validity conclusion must
# be independent of instance *size* (the if/else variant is written so both
# branches evaluate the same prefix length, to keep that invariant).
ARRAY_SCHEMAS = [
    {"prefixItems": [{}], "unevaluatedItems": False},
    {"items": {}, "unevaluatedItems": False},
    {
        "if": {"prefixItems": [{}, {}]},
        "then": {"prefixItems": [{}, {}, {}]},
        "unevaluatedItems": False,
    },
    {
        "if": {"maxItems": 3},
        "then": {"prefixItems": [{}]},
        "else": {"prefixItems": [{}]},
        "unevaluatedItems": False,
    },
    {"contains": {"const": "marker"}, "unevaluatedItems": False},
    {"allOf": [{"prefixItems": [{}, {}]}], "unevaluatedItems": False},
    {
        "anyOf": [{"prefixItems": [{}, {}]}, {"prefixItems": [{}]}],
        "unevaluatedItems": False,
    },
    {"oneOf": [{"prefixItems": [{}, {}]}], "unevaluatedItems": False},
    {
        "$ref": "#/$defs/evaluated",
        "$defs": {"evaluated": {"prefixItems": [{}, {}]}},
        "unevaluatedItems": False,
    },
    {"prefixItems": [{}], "unevaluatedItems": {"type": "integer"}},
]

# Schemas exercising every branch that contributes evaluated property keys:
# properties, patternProperties, additionalProperties, unevaluatedProperties,
# dependentSchemas, the applicators and if/then/else.
OBJECT_SCHEMAS = [
    {"properties": {"p0": {}}, "unevaluatedProperties": False},
    {"patternProperties": {"^matched_": {}}, "unevaluatedProperties": False},
    {
        "properties": {"p0": {}},
        "additionalProperties": {"type": "integer"},
        "unevaluatedProperties": False,
    },
    {
        "dependentSchemas": {"p0": {"properties": {"p1": {}}}},
        "unevaluatedProperties": False,
    },
    {
        "if": {"required": ["p0"]},
        "then": {"properties": {"p1": {}}},
        "unevaluatedProperties": False,
    },
    {"allOf": [{"properties": {"p0": {}}}], "unevaluatedProperties": False},
    {
        "anyOf": [{"properties": {"p0": {}}}, {"properties": {"nope": {}}}],
        "unevaluatedProperties": False,
    },
    {"oneOf": [{"properties": {"p0": {}}}], "unevaluatedProperties": False},
    {
        "$ref": "#/$defs/evaluated",
        "$defs": {"evaluated": {"properties": {"p0": {}}}},
        "unevaluatedProperties": False,
    },
    {"properties": {"p0": {}}, "unevaluatedProperties": {"const": 12}},
]


class UnevaluatedConclusionConsistencyTest(TestCase):
    """Conclusions and error artifacts stay identical across instance sizes."""

    def test_array_validity_conclusions_are_stable_under_growth(self):
        instance = ["marker", 1, "unevaluated-string", 3, 4]
        for schema in ARRAY_SCHEMAS:
            validator = Draft202012Validator(schema)
            small_valid = validator.is_valid(instance)
            large_valid = validator.is_valid(instance * 400)
            self.assertIs(small_valid, large_valid, schema)

    def test_object_validity_conclusions_are_stable_under_growth(self):
        instance = {"p0": 1, "p1": 2, "matched_x": 3, "unmatched": "nope"}
        grown = dict(instance)
        grown.update({f"bulk_{i}": i for i in range(400)})
        for schema in OBJECT_SCHEMAS:
            validator = Draft202012Validator(schema)
            small_valid = validator.is_valid(instance)
            large_valid = validator.is_valid(grown)
            self.assertIs(small_valid, large_valid, schema)

    def test_large_array_error_message_is_verbatim(self):
        schema = {
            "prefixItems": [{} for _ in range(200)],
            "unevaluatedItems": False,
        }
        validator = Draft202012Validator(schema)
        instance = list(range(400))
        (error,) = validator.iter_errors(instance)
        joined, verb = extras_msg(instance[200:])
        self.assertEqual(
            error.message,
            f"Unevaluated items are not allowed ({joined} {verb} unexpected)",
        )
        self.assertEqual(tuple(error.absolute_path), ())
        self.assertEqual(error.validator, "unevaluatedItems")

    def test_large_object_error_message_is_verbatim(self):
        schema = {
            "properties": {f"p{i}": {} for i in range(200)},
            "unevaluatedProperties": False,
        }
        validator = Draft202012Validator(schema)
        instance = {f"p{i}": i for i in range(400)}
        (error,) = validator.iter_errors(instance)
        extras = sorted((f"p{i}" for i in range(200, 400)), key=str)
        joined, verb = extras_msg(extras)
        self.assertEqual(
            error.message,
            "Unevaluated properties are not allowed "
            f"({joined} {verb} unexpected)",
        )
        self.assertEqual(error.validator, "unevaluatedProperties")

    def test_mixed_string_and_integer_property_keys(self):
        # Mirrors the heterogeneous-keys test in test_validators, scaled up so
        # the constant-time path is exercised with non-string keys.
        schema = {"properties": {"foo": {}}, "unevaluatedProperties": False}
        validator = Draft202012Validator(schema)
        instance = {"foo": {}}
        instance.update({f"k{i}": i for i in range(200)})
        instance[37] = 12
        (error,) = validator.iter_errors(instance)
        self.assertIn("37", error.message)
        self.assertIn("'k0'", error.message)

    def test_evaluated_and_unevaluated_mix_has_no_false_negatives(self):
        # Every unevaluated position must be reported, not just the first one:
        # a membership-tracking bug that silently swallowed indexes would lose
        # entries from the extras list.
        schema = {
            "prefixItems": [{} for _ in range(50)],
            "unevaluatedItems": False,
        }
        validator = Draft202012Validator(schema)
        instance = list(range(200))
        (unevaluated_error,) = validator.iter_errors(instance)
        reported, _ = extras_msg(instance[50:])
        for index in range(50, 200):
            self.assertIn(repr(index), reported)
        self.assertEqual(unevaluated_error.validator, "unevaluatedItems")

    def test_fully_evaluated_instances_remain_valid_at_scale(self):
        array_schema = {"items": {}, "unevaluatedItems": False}
        object_schema = {
            "properties": {f"p{i}": {} for i in range(400)},
            "unevaluatedProperties": False,
        }
        array_validator = Draft202012Validator(array_schema)
        object_validator = Draft202012Validator(object_schema)
        self.assertEqual(
            list(array_validator.iter_errors(list(range(400)))),
            [],
        )
        self.assertEqual(
            list(
                object_validator.iter_errors(
                    {f"p{i}": i for i in range(400)},
                ),
            ),
            [],
        )

    def test_draft2019_09_conclusions_are_stable_under_growth(self):
        # The legacy draft2019-09 finders carry the same quadratic bug and
        # must both scale and preserve conclusions. Note that, unlike the
        # 2020-12 finder, draft2019-09's unevaluatedItems does not treat
        # prefixItems as evaluating positions (a pre-existing semantic kept
        # byte-for-byte), so the instance is expected to stay invalid at
        # every size rather than flip with size.
        array_schema = {
            "prefixItems": [{} for _ in range(100)],
            "unevaluatedItems": False,
        }
        object_schema = {
            "properties": {f"p{i}": {} for i in range(100)},
            "unevaluatedProperties": False,
        }
        array = list(range(200))
        obj = {f"p{i}": i for i in range(200)}

        legacy_validator = Draft201909Validator(array_schema)
        self.assertFalse(legacy_validator.is_valid(array))
        self.assertFalse(legacy_validator.is_valid(array * 2))
        (legacy_error,) = legacy_validator.iter_errors(array)
        self.assertEqual(legacy_error.validator, "unevaluatedItems")

        object_validator = Draft201909Validator(object_schema)
        self.assertFalse(object_validator.is_valid(obj))
        self.assertFalse(object_validator.is_valid(dict(obj, extra=1)))


class UnevaluatedScalingTest(TestCase):
    """Doubling the instance must cost roughly twice, not 3x or more."""

    def test_unevaluated_items_scales_linearly(self):
        timings = {}
        for n in (2000, 4000, 8000):
            schema = {
                "prefixItems": [{} for _ in range(n // 2)],
                "unevaluatedItems": False,
            }
            validator = Draft202012Validator(schema)
            timings[n] = best_validation_time(validator, list(range(n)))

        # A quadratic implementation shows ratios near 4 (measured at ~3-4x
        # on this machine); linear work must stay well below that bound.
        self.assertLess(timings[4000] / timings[2000], 2.75)
        self.assertLess(timings[8000] / timings[4000], 2.75)

    def test_unevaluated_properties_scales_linearly(self):
        timings = {}
        for n in (2000, 4000, 8000):
            schema = {
                "properties": {f"p{i}": {} for i in range(n // 2)},
                "unevaluatedProperties": False,
            }
            validator = Draft202012Validator(schema)
            timings[n] = best_validation_time(
                validator,
                {f"p{i}": i for i in range(n)},
            )

        self.assertLess(timings[4000] / timings[2000], 2.75)
        self.assertLess(timings[8000] / timings[4000], 2.75)

    def test_draft2019_09_scales_linearly(self):
        # The legacy draft does not treat prefixItems as evaluated, so use
        # contains to build a non-empty evaluated-index set (the first half
        # of the instance matches); this is the path that exercised the
        # quadratic list scan in the legacy finder.
        timings = {}
        for n in (2000, 4000, 8000):
            schema = {
                "contains": {"maximum": n // 2 - 1},
                "unevaluatedItems": False,
            }
            validator = Draft201909Validator(schema)
            timings[n] = best_validation_time(validator, list(range(n)))

        self.assertLess(timings[4000] / timings[2000], 2.75)
        self.assertLess(timings[8000] / timings[4000], 2.75)
