import unittest

from clearskies.autodoc.formats.oai3_json import OAI3SchemaResolver
from clearskies.autodoc.formats.oai3_json.parameter import Parameter as OAI3Parameter
from clearskies.autodoc.request import URLParameter
from clearskies.autodoc.schema import String


class TestOai3ParameterOptions(unittest.TestCase):
    def test_parameter_openapi_options_are_rendered(self):
        parameter = URLParameter(
            definition=String("q"),
            description="Search",
            required=False,
            style="form",
            explode=False,
            allow_reserved=True,
            deprecated=True,
            allow_empty_value=True,
        )

        formatted = OAI3Parameter(OAI3SchemaResolver())
        formatted.set_parameter(parameter)
        output = formatted.convert()

        self.assertEqual(output["style"], "form")
        self.assertFalse(output["explode"])
        self.assertTrue(output["allowReserved"])
        self.assertTrue(output["deprecated"])
        self.assertTrue(output["allowEmptyValue"])

    def test_parameter_example_and_examples_are_rendered(self):
        parameter = URLParameter(
            definition=String("q"),
            description="Search",
            required=False,
            example="hello",
            examples={
                "a": {
                    "summary": "A",
                    "value": "abc",
                }
            },
        )

        formatted = OAI3Parameter(OAI3SchemaResolver())
        formatted.set_parameter(parameter)
        output = formatted.convert()

        self.assertEqual(output["example"], "hello")
        self.assertIn("examples", output)
        self.assertIn("a", output["examples"])

    def test_parameter_content_is_rendered_instead_of_schema(self):
        parameter = URLParameter(
            definition=String("q"),
            description="Search",
            required=False,
            content={
                "application/json": {
                    "schema": {"type": "object"},
                }
            },
        )

        formatted = OAI3Parameter(OAI3SchemaResolver())
        formatted.set_parameter(parameter)
        output = formatted.convert()

        self.assertIn("content", output)
        self.assertNotIn("schema", output)


if __name__ == "__main__":
    unittest.main()
