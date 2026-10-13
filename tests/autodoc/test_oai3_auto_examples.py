import json
import unittest

from clearskies.autodoc import schema as autodoc_schema
from clearskies.autodoc.formats.oai3_json import Oai3Json, OAI3SchemaResolver
from clearskies.autodoc.request import JSONBody, Request, URLParameter
from clearskies.autodoc.response import Response


class TestOai3AutoExamples(unittest.TestCase):
    def test_auto_examples_for_request_body_and_response(self):
        request = Request(
            description="Create",
            relative_path="/items",
            request_methods=["POST"],
            parameters=[
                JSONBody(
                    definition=autodoc_schema.String("name"),
                    required=True,
                )
            ],
            responses=[
                Response(
                    status=200,
                    schema=autodoc_schema.Object(
                        "body",
                        [
                            autodoc_schema.String("email"),
                            autodoc_schema.Integer("count"),
                            autodoc_schema.Boolean("enabled"),
                        ],
                    ),
                    description="Ok",
                )
            ],
        )

        oai3_json = Oai3Json(OAI3SchemaResolver())
        oai3_json.set_requests([request])
        output = json.loads(oai3_json.compact())

        request_example = output["paths"]["/items"]["post"]["requestBody"]["content"]["application/json"]["example"]
        self.assertIn("name", request_example)

        response_example = output["paths"]["/items"]["post"]["responses"]["200"]["content"]["application/json"][
            "example"
        ]
        self.assertEqual(response_example["email"], "user@example.com")
        self.assertEqual(response_example["count"], 1)
        self.assertTrue(response_example["enabled"])

    def test_override_examples_for_request_body_parameter(self):
        request = Request(
            description="Create",
            relative_path="/items",
            request_methods=["POST"],
            parameters=[
                JSONBody(
                    definition=autodoc_schema.String("name"),
                    required=True,
                    documentation_example={"name": "override"},
                    documentation_examples={"sample": {"value": {"name": "sample"}}},
                )
            ],
            responses=[
                Response(status=200, schema=autodoc_schema.String("message"), description="Ok"),
            ],
        )

        oai3_json = Oai3Json(OAI3SchemaResolver())
        oai3_json.set_requests([request])
        output = json.loads(oai3_json.compact())
        request_content = output["paths"]["/items"]["post"]["requestBody"]["content"]["application/json"]
        self.assertEqual(request_content["example"], {"name": "override"})
        self.assertIn("examples", request_content)

    def test_override_examples_for_parameter_and_response(self):
        request = Request(
            description="Get",
            relative_path="/items",
            request_methods=["GET"],
            parameters=[
                URLParameter(
                    definition=autodoc_schema.String("q"),
                    documentation_example="override-q",
                )
            ],
            responses=[
                Response(
                    status=200,
                    schema=autodoc_schema.String("message"),
                    description="Ok",
                    documentation_example="override-message",
                    documentation_examples={"sample": {"value": "sample-message"}},
                )
            ],
        )

        oai3_json = Oai3Json(OAI3SchemaResolver())
        oai3_json.set_requests([request])
        output = json.loads(oai3_json.compact())

        parameter = output["paths"]["/items"]["get"]["parameters"][0]
        self.assertEqual(parameter["example"], "override-q")

        response_content = output["paths"]["/items"]["get"]["responses"]["200"]["content"]["application/json"]
        self.assertEqual(response_content["example"], "override-message")
        self.assertIn("examples", response_content)


if __name__ == "__main__":
    unittest.main()
