"""
Tests to verify OpenAPI 3.0 specification compliance for generated documentation.

This test suite validates the generated OpenAPI 3.0 JSON against the official specification
and ensures all required fields and structures are correct.
"""

import json
import unittest
from unittest.mock import Mock

from clearskies.autodoc.formats.oai3_json import Oai3Json, OAI3SchemaResolver
from clearskies.autodoc.request import JSONBody, Request, URLParameter
from clearskies.autodoc.response import Response
from clearskies.autodoc.schema import (
    Array,
    Enum,
    Integer,
    Object,
    String,
)


class TestOAI3Compliance(unittest.TestCase):
    """Test OpenAPI 3.0 compliance."""

    def setUp(self):
        """Set up common test fixtures."""
        self.oai3_schema_resolver = OAI3SchemaResolver()
        self.oai3_json = Oai3Json(self.oai3_schema_resolver)

    def test_basic_structure_required_fields(self):
        """Test that the basic OpenAPI 3.0 structure has all required fields."""
        # Create a minimal request
        response = Response(
            schema=String("message", example="Success"),
            status=200,
            description="Successful response",
        )
        test_request = Request(
            description="Test endpoint",
            responses=[response],
            relative_path="/test",
            request_methods=["GET"],
        )

        self.oai3_json.set_requests([test_request])
        output = json.loads(self.oai3_json.compact())

        # Verify required top-level fields
        self.assertIn("openapi", output)
        self.assertEqual(output["openapi"], "3.0.0")
        self.assertIn("paths", output)
        self.assertIsInstance(output["paths"], dict)

    def test_operation_has_required_fields(self):
        """Test that operations have required fields including operationId."""
        response = Response(
            schema=Object("result", [String("status")]),
            status=200,
            description="Success",
        )
        test_request = Request(
            description="Health check endpoint",
            responses=[response],
            relative_path="/health",
            request_methods=["GET"],
        )

        self.oai3_json.set_requests([test_request])
        output = json.loads(self.oai3_json.compact())

        operation = output["paths"]["/health"]["get"]

        # Verify required operation fields
        self.assertIn("operationId", operation)
        self.assertIn("summary", operation)
        self.assertIn("responses", operation)

        # Verify operationId follows proper naming convention
        self.assertEqual(operation["operationId"], "getHealth")

    def test_operation_id_generation(self):
        """Test that operationId is generated correctly for various paths."""
        test_cases = [
            ("/health", "GET", "getHealth"),
            ("/v3/api/users", "GET", "getV3ApiUsers"),
            ("/v3/api/users/{id}", "GET", "getV3ApiUsersById"),
            ("/v3/api/users", "POST", "postV3ApiUsers"),
            ("/users/{userId}/posts/{postId}", "PUT", "putUsersByUserIdPostsByPostId"),
        ]

        for path, method, expected_operation_id in test_cases:
            response = Response(
                schema=String("message"),
                status=200,
                description="Response",
            )
            test_request = Request(
                description="Test",
                responses=[response],
                relative_path=path,
                request_methods=[method],
            )

            oai3_json = Oai3Json(self.oai3_schema_resolver)
            oai3_json.set_requests([test_request])
            output = json.loads(oai3_json.compact())

            operation = output["paths"][path][method.lower()]
            self.assertEqual(
                operation["operationId"],
                expected_operation_id,
                f"Failed for {method} {path}",
            )

    def test_invalid_http_methods_excluded(self):
        """Test that invalid HTTP methods (like 'query') are excluded."""
        response = Response(
            schema=String("message"),
            status=200,
            description="Response",
        )
        test_request = Request(
            description="Test endpoint",
            responses=[response],
            relative_path="/test",
            request_methods=["GET", "QUERY"],  # QUERY is invalid
        )

        self.oai3_json.set_requests([test_request])
        output = json.loads(self.oai3_json.compact())

        path_obj = output["paths"]["/test"]

        # GET should be present
        self.assertIn("get", path_obj)
        # QUERY should be excluded
        self.assertNotIn("query", path_obj)

    def test_response_required_description(self):
        """Test that responses always have a description field."""
        response_with_desc = Response(
            schema=String("message"),
            status=200,
            description="Successful operation",
        )

        response_without_desc = Response(
            schema=String("message"),
            status=204,
            description="",  # Empty description
        )

        test_request = Request(
            description="Test",
            responses=[response_with_desc, response_without_desc],
            relative_path="/test",
            request_methods=["GET"],
        )

        self.oai3_json.set_requests([test_request])
        output = json.loads(self.oai3_json.compact())

        operation = output["paths"]["/test"]["get"]

        # Both responses should have description
        self.assertIn("description", operation["responses"]["200"])
        self.assertEqual(operation["responses"]["200"]["description"], "Successful operation")

        self.assertIn("description", operation["responses"]["204"])
        # Empty descriptions should default to "Response"
        self.assertEqual(operation["responses"]["204"]["description"], "Response")

    def test_enum_nullable_without_null_in_values(self):
        """Test that enum schemas use nullable: true instead of including null in enum values."""
        from clearskies.autodoc.formats.oai3_json.schema import Enum as OAI3Enum

        enum_schema = Enum(
            name="status",
            values=["active", "inactive", "pending"],
            value_type=String("status"),
        )

        oai3_enum = OAI3Enum(enum_schema, self.oai3_schema_resolver)
        converted = oai3_enum.convert()

        # Verify nullable is true
        self.assertTrue(converted.get("nullable"))

        # Verify null is NOT in the enum values
        self.assertNotIn(None, converted["enum"])
        self.assertListEqual(converted["enum"], ["active", "inactive", "pending"])

    def test_object_with_ref_only(self):
        """Test that objects with model_name use only $ref without other properties."""
        object_with_model = Object(
            name="user",
            children=[String("name"), Integer("age")],
            model_name="User",
        )

        from clearskies.autodoc.formats.oai3_json.schema import Object as OAI3Object

        oai3_object = OAI3Object(object_with_model, self.oai3_schema_resolver)
        converted = oai3_object.convert()

        # When model_name is present, should ONLY have $ref
        self.assertIn("$ref", converted)
        self.assertEqual(converted["$ref"], "#/components/schemas/User")
        self.assertNotIn("type", converted)
        self.assertNotIn("properties", converted)

    def test_object_without_ref_has_properties(self):
        """Test that objects without model_name have properties."""
        object_without_model = Object(
            name="inline_object",
            children=[String("field1"), Integer("field2")],
        )

        from clearskies.autodoc.formats.oai3_json.schema import Object as OAI3Object

        oai3_object = OAI3Object(object_without_model, self.oai3_schema_resolver)
        converted = oai3_object.convert()

        # Without model_name, should have type and properties
        self.assertEqual(converted["type"], "object")
        self.assertIn("properties", converted)
        self.assertNotIn("$ref", converted)
        self.assertIn("field1", converted["properties"])
        self.assertIn("field2", converted["properties"])

    def test_parameter_has_schema(self):
        """Test that parameters always have a schema object."""
        url_param = URLParameter(
            definition=Integer("page"),
            description="Page number",
            required=False,
        )

        from clearskies.autodoc.formats.oai3_json.parameter import Parameter as OAI3Parameter

        oai3_param = OAI3Parameter(self.oai3_schema_resolver)
        oai3_param.set_parameter(url_param)
        converted = oai3_param.convert()

        # Verify parameter structure
        self.assertIn("name", converted)
        self.assertIn("in", converted)
        self.assertIn("required", converted)
        self.assertIn("schema", converted)
        self.assertIsInstance(converted["schema"], dict)
        self.assertEqual(converted["schema"]["type"], "integer")

    def test_components_only_when_not_empty(self):
        """Test that components object is only included when it has content."""
        response = Response(
            schema=String("message"),
            status=200,
            description="Success",
        )
        test_request = Request(
            description="Test",
            responses=[response],
            relative_path="/test",
            request_methods=["GET"],
        )

        self.oai3_json.set_requests([test_request])
        output = json.loads(self.oai3_json.compact())

        # Without models or security schemes, components should not be present
        # or should be empty
        if "components" in output:
            self.assertEqual(len(output["components"]), 0)

    def test_components_with_schemas(self):
        """Test that components are included when models are present."""
        user_model = Object(
            name="User",
            children=[
                String("name"),
                String("email"),
                Integer("age"),
            ],
        )

        self.oai3_json.set_components({"models": {"User": user_model}})

        response = Response(
            schema=String("message"),
            status=200,
            description="Success",
        )
        test_request = Request(
            description="Test",
            responses=[response],
            relative_path="/test",
            request_methods=["GET"],
        )

        self.oai3_json.set_requests([test_request])
        output = json.loads(self.oai3_json.compact())

        # Components should be present with schemas
        self.assertIn("components", output)
        self.assertIn("schemas", output["components"])
        self.assertIn("User", output["components"]["schemas"])

    def test_array_schema(self):
        """Test that array schemas are properly formatted."""
        array_schema = Array(
            name="items",
            item_definition=String("item"),
        )

        from clearskies.autodoc.formats.oai3_json.schema import Array as OAI3Array

        oai3_array = OAI3Array(array_schema, self.oai3_schema_resolver)
        converted = oai3_array.convert()

        self.assertEqual(converted["type"], "array")
        self.assertIn("items", converted)
        self.assertIsInstance(converted["items"], dict)
        self.assertEqual(converted["items"]["type"], "string")

    def test_schema_nullable_support(self):
        """Test that schemas properly support nullable field."""
        from clearskies.autodoc.formats.oai3_json.schema import Default

        # Create a mock schema with nullable
        mock_schema = Mock()
        mock_schema._type = "string"
        mock_schema._format = None
        mock_schema.nullable = True

        default_schema = Default(mock_schema)
        converted = default_schema.convert()

        self.assertTrue(converted.get("nullable"))

    def test_request_body_structure(self):
        """Test that request bodies are properly structured."""
        json_body = JSONBody(
            definition=Object(
                "request",
                [
                    String("name", example="John"),
                    Integer("age", example=30),
                ],
            ),
            description="User data",
            required=True,
        )

        response = Response(
            schema=String("message"),
            status=201,
            description="Created",
        )

        test_request = Request(
            description="Create user",
            responses=[response],
            relative_path="/users",
            request_methods=["POST"],
            parameters=[json_body],
        )

        self.oai3_json.set_requests([test_request])
        output = json.loads(self.oai3_json.compact())

        operation = output["paths"]["/users"]["post"]

        self.assertIn("requestBody", operation)
        request_body = operation["requestBody"]

        self.assertIn("description", request_body)
        self.assertIn("required", request_body)
        self.assertIn("content", request_body)
        self.assertIn("application/json", request_body["content"])
        self.assertIn("schema", request_body["content"]["application/json"])

    def test_multiple_operations_same_path(self):
        """Test that multiple HTTP methods on the same path are handled correctly."""
        get_response = Response(
            schema=Object("user", [String("name")]),
            status=200,
            description="Get user",
        )

        post_response = Response(
            schema=Object("user", [String("name")]),
            status=201,
            description="Created user",
        )

        get_request = Request(
            description="Get user",
            responses=[get_response],
            relative_path="/users/{id}",
            request_methods=["GET"],
        )

        post_request = Request(
            description="Update user",
            responses=[post_response],
            relative_path="/users/{id}",
            request_methods=["PUT"],
        )

        self.oai3_json.set_requests([get_request, post_request])
        output = json.loads(self.oai3_json.compact())

        path_obj = output["paths"]["/users/{id}"]

        self.assertIn("get", path_obj)
        self.assertIn("put", path_obj)
        self.assertEqual(path_obj["get"]["operationId"], "getUsersById")
        self.assertEqual(path_obj["put"]["operationId"], "putUsersById")


if __name__ == "__main__":
    unittest.main()
