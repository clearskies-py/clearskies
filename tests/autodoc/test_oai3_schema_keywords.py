import unittest

from clearskies.autodoc.formats.oai3_json import OAI3SchemaResolver
from clearskies.autodoc.schema import AllOf, AnyOf, Array, Integer, Not, OneOf, String


class TestOai3SchemaKeywords(unittest.TestCase):
    def test_any_of_all_of_not_are_converted(self):
        resolver = OAI3SchemaResolver()

        any_of = AnyOf("value", [String("value"), Integer("value")])
        all_of = AllOf("value", [String("value"), String("value")])
        not_schema = Not("value", String("value"))

        self.assertIn("anyOf", resolver(any_of).convert())
        self.assertIn("allOf", resolver(all_of).convert())
        self.assertIn("not", resolver(not_schema).convert())

    def test_default_schema_keyword_constraints(self):
        resolver = OAI3SchemaResolver()
        schema = String("name")
        schema.min_length = 2
        schema.max_length = 20
        schema.pattern = "^[a-z]+$"
        schema.deprecated = True
        schema.nullable = True

        converted = resolver(schema).convert()
        self.assertEqual(converted["minLength"], 2)
        self.assertEqual(converted["maxLength"], 20)
        self.assertEqual(converted["pattern"], "^[a-z]+$")
        self.assertTrue(converted["deprecated"])
        self.assertTrue(converted["nullable"])

    def test_array_keyword_constraints(self):
        resolver = OAI3SchemaResolver()
        schema = Array("items", String("item"))
        schema.min_items = 1
        schema.max_items = 10
        schema.unique_items = True

        converted = resolver(schema).convert()
        self.assertEqual(converted["minItems"], 1)
        self.assertEqual(converted["maxItems"], 10)
        self.assertTrue(converted["uniqueItems"])

    def test_one_of_still_supported(self):
        resolver = OAI3SchemaResolver()
        schema = OneOf("value", [String("value"), Integer("value")])
        converted = resolver(schema).convert()
        self.assertIn("oneOf", converted)


if __name__ == "__main__":
    unittest.main()
