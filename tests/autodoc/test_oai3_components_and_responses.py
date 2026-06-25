import json
import unittest

from clearskies.autodoc.formats.oai3_json import Oai3Json, OAI3SchemaResolver
from clearskies.autodoc.request import Request
from clearskies.autodoc.response import Link, Response
from clearskies.autodoc.schema import String


class TestOai3ComponentsAndResponses(unittest.TestCase):
    def test_response_headers_links_and_content_types(self):
        oai3_json = Oai3Json(OAI3SchemaResolver())
        response = Response(
            schema=String("message"),
            status=200,
            description="Ok",
            headers={
                "X-Trace-Id": {
                    "description": "Trace identifier",
                    "schema": {"type": "string"},
                }
            },
            links={
                "next": Link(operation_id="getNext", parameters={"id": "$response.body#/id"}),
            },
            content={
                "application/json": {"schema": String("message")},
                "text/plain": {"schema": String("message")},
            },
        )

        request = Request(
            description="Test",
            responses=[response],
            relative_path="/test",
            request_methods=["GET"],
        )
        oai3_json.set_requests([request])

        output = json.loads(oai3_json.compact())
        response_data = output["paths"]["/test"]["get"]["responses"]["200"]

        self.assertIn("headers", response_data)
        self.assertIn("X-Trace-Id", response_data["headers"])
        self.assertIn("links", response_data)
        self.assertIn("next", response_data["links"])
        self.assertIn("application/json", response_data["content"])
        self.assertIn("text/plain", response_data["content"])

    def test_components_extended_sections_are_emitted(self):
        oai3_json = Oai3Json(OAI3SchemaResolver())
        oai3_json.set_components(
            {
                "parameters": {
                    "Page": {
                        "name": "page",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "integer"},
                    }
                },
                "responses": {
                    "NotFound": {
                        "description": "Not found",
                    }
                },
                "requestBodies": {
                    "CreateThing": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {},
                                }
                            }
                        },
                    }
                },
            }
        )

        response = Response(schema=String("message"), status=200, description="Ok")
        request = Request(
            description="Test",
            responses=[response],
            relative_path="/test",
            request_methods=["GET"],
        )
        oai3_json.set_requests([request])

        output = json.loads(oai3_json.compact())
        self.assertIn("components", output)
        self.assertIn("parameters", output["components"])
        self.assertIn("responses", output["components"])
        self.assertIn("requestBodies", output["components"])


if __name__ == "__main__":
    unittest.main()
