import json
import unittest

import pytest

openapi_spec_validator = pytest.importorskip("openapi_spec_validator")
validate = openapi_spec_validator.validate

from clearskies.autodoc import schema as autodoc_schema
from clearskies.autodoc.formats.oai3_json import Oai3Json, OAI3SchemaResolver
from clearskies.autodoc.request import JSONBody, Request, URLParameter
from clearskies.autodoc.response import Response


class TestOai3ExternalValidation(unittest.TestCase):
    def test_generated_spec_validates_against_openapi_spec(self):
        list_response = Response(
            schema=autodoc_schema.Object(
                "result",
                [
                    autodoc_schema.Array(
                        "items",
                        autodoc_schema.Object(
                            "item",
                            [
                                autodoc_schema.String("id"),
                                autodoc_schema.OneOf(
                                    "payload",
                                    [
                                        autodoc_schema.String("payload"),
                                        autodoc_schema.Object("payload", [autodoc_schema.Integer("count")]),
                                    ],
                                ),
                            ],
                        ),
                    )
                ],
            ),
            status=200,
            description="List items",
        )

        list_request = Request(
            description="List items",
            responses=[list_response],
            relative_path="/items",
            request_methods=["GET"],
            parameters=[
                URLParameter(
                    definition=autodoc_schema.Integer("page"),
                    description="Page",
                    required=False,
                    style="form",
                    explode=True,
                )
            ],
        )

        create_response = Response(
            schema=autodoc_schema.String("message"),
            status=201,
            description="Created",
        )

        create_request = Request(
            description="Create item",
            responses=[create_response],
            relative_path="/items",
            request_methods=["POST"],
            parameters=[
                JSONBody(
                    definition=autodoc_schema.Object("request", [autodoc_schema.String("name")]),
                    required=True,
                    content_type="application/json",
                ),
                JSONBody(
                    definition=autodoc_schema.Object("request", [autodoc_schema.String("name")]),
                    required=False,
                    content_type="application/x-www-form-urlencoded",
                ),
            ],
        )

        oai3_json = Oai3Json(OAI3SchemaResolver())
        oai3_json.set_requests([list_request, create_request])

        spec = json.loads(
            oai3_json.compact(
                root_properties={
                    "info": {
                        "title": "Example API",
                        "version": "1.0.0",
                    },
                    "servers": [{"url": "https://api.example.com", "description": "Production"}],
                }
            )
        )

        validate(spec)


if __name__ == "__main__":
    unittest.main()
