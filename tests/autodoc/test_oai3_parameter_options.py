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


if __name__ == "__main__":
    unittest.main()
