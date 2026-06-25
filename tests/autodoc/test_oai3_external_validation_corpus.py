import json
import unittest

import pytest

openapi_spec_validator = pytest.importorskip("openapi_spec_validator")
validate = openapi_spec_validator.validate

from clearskies.autodoc import schema as autodoc_schema
from clearskies.autodoc.formats.oai3_json import Oai3Json, OAI3SchemaResolver
from clearskies.autodoc.request import JSONBody, Request, URLParameter, URLPath
from clearskies.autodoc.response import Link, Response


class TestOai3ExternalValidationCorpus(unittest.TestCase):
    def _validate(self, requests, components=None, root_properties=None, openapi_version="3.0.0"):
        oai3_json = Oai3Json(OAI3SchemaResolver(), openapi_version=openapi_version)
        oai3_json.set_requests(requests)
        if components:
            oai3_json.set_components(components)
        spec = json.loads(oai3_json.compact(root_properties=root_properties))
        validate(spec)

    def test_external_validation_corpus(self):
        request_1 = Request(
            description="List users",
            responses=[
                Response(
                    status=200,
                    schema=autodoc_schema.Array("users", autodoc_schema.Object("user", [autodoc_schema.String("id")])),
                    description="Success",
                )
            ],
            relative_path="/users/{tenant}",
            request_methods=["GET"],
            parameters=[
                URLParameter(definition=autodoc_schema.Integer("page"), required=False, style="form", explode=True),
                URLPath(definition=autodoc_schema.String("tenant"), required=True),
            ],
            tags=["users"],
            servers=[{"url": "https://api.example.com", "description": "Prod"}],
        )

        request_2 = Request(
            description="Create user",
            responses=[
                Response(
                    status=201,
                    schema=autodoc_schema.String("message"),
                    description="Created",
                    headers={"X-Trace-Id": {"schema": {"type": "string"}}},
                    links={"next": Link(operation_id="getUser")},
                    content={
                        "application/json": {"schema": autodoc_schema.String("message")},
                        "text/plain": {"schema": autodoc_schema.String("message")},
                    },
                )
            ],
            relative_path="/users",
            request_methods=["POST"],
            parameters=[
                JSONBody(definition=autodoc_schema.Object("body", [autodoc_schema.String("name")]), required=True),
                JSONBody(
                    definition=autodoc_schema.Object("body", [autodoc_schema.String("name")]),
                    required=False,
                    content_type="application/x-www-form-urlencoded",
                ),
            ],
            security=[{"bearerAuth": []}],
        )

        request_3 = Request(
            description="Get profile",
            responses=[
                Response(
                    status=200,
                    schema=autodoc_schema.OneOf(
                        "profile",
                        [
                            autodoc_schema.String("profile"),
                            autodoc_schema.Object("profile", [autodoc_schema.Integer("id")]),
                        ],
                    ),
                    description="Ok",
                )
            ],
            relative_path="/profile/{id}",
            request_methods=["GET"],
            parameters=[URLPath(definition=autodoc_schema.Integer("id"), required=True)],
        )

        components = {
            "models": {
                "User": autodoc_schema.Object("User", [autodoc_schema.String("id")]),
            },
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                }
            },
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
                "CreateUser": {
                    "required": True,
                    "content": {"application/json": {"schema": {"type": "object", "properties": {}}}},
                }
            },
            "headers": {
                "RateLimit": {
                    "description": "Rate limit",
                    "schema": {"type": "integer"},
                }
            },
            "examples": {
                "Sample": {
                    "summary": "Sample",
                    "value": {"name": "alice"},
                }
            },
            "links": {
                "GetUser": {
                    "operationId": "getUser",
                }
            },
            "callbacks": {
                "onEvent": {
                    "{$request.body#/callbackUrl}": {
                        "post": {
                            "requestBody": {
                                "content": {"application/json": {"schema": {"type": "object", "properties": {}}}}
                            },
                            "responses": {"200": {"description": "ok"}},
                        }
                    }
                }
            },
        }

        root = {
            "info": {
                "title": "Validation Corpus",
                "version": "1.0.0",
            },
            "servers": [{"url": "https://api.example.com"}],
        }

        self._validate([request_1, request_2, request_3], components=components, root_properties=root)
        self._validate(
            [request_1, request_2, request_3], components=components, root_properties=root, openapi_version="3.1.0"
        )


if __name__ == "__main__":
    unittest.main()
