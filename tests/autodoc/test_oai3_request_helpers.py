import json
import unittest

import clearskies
from clearskies import columns
from clearskies.autodoc import schema as autodoc_schema
from clearskies.autodoc.formats.oai3_json import Oai3Json, OAI3SchemaResolver
from clearskies.autodoc.request import Request
from clearskies.autodoc.response import Response


class PayloadSchema(clearskies.Schema):
    count = columns.Integer()
    ratio = columns.Float()
    enabled = columns.Boolean()
    metadata = columns.Json()
    name = columns.String()
    email = columns.Email()
    phone = columns.Phone()
    id = columns.Uuid()
    created_at = columns.Date()

    @classmethod
    def destination_name(cls):
        return ""


class TestOai3RequestBodySchema(unittest.TestCase):
    def test_string_or_schema_object_uses_existing_conversion(self):
        string_option = autodoc_schema.String("payload")
        setattr(string_option, "description", "Serialized JSON payload")

        output = autodoc_schema.OneOf(
            "payload",
            [
                string_option,
                autodoc_schema.Object(
                    "payload",
                    [doc for column in PayloadSchema.get_columns().values() for doc in column.documentation()],
                ),
            ],
        )

        converted = OAI3SchemaResolver()(output).convert()
        self.assertIn("oneOf", converted)

        string_shape = converted["oneOf"][0]
        self.assertEqual(string_shape["type"], "string")
        self.assertEqual(string_shape["description"], "Serialized JSON payload")

        object_shape = converted["oneOf"][1]
        self.assertEqual(object_shape["type"], "object")
        self.assertEqual(object_shape["properties"]["count"], {"type": "integer", "format": "int32"})
        self.assertEqual(object_shape["properties"]["ratio"], {"type": "number", "format": "float"})
        self.assertEqual(object_shape["properties"]["enabled"], {"type": "boolean"})
        self.assertEqual(
            object_shape["properties"]["metadata"],
            {
                "oneOf": [
                    {"type": "object", "properties": {}},
                    {"type": "array", "items": {"type": "string"}},
                ]
            },
        )
        self.assertEqual(object_shape["properties"]["name"], {"type": "string"})
        self.assertEqual(object_shape["properties"]["email"], {"type": "string"})
        self.assertEqual(object_shape["properties"]["phone"], {"type": "string"})
        self.assertEqual(object_shape["properties"]["id"], {"type": "string"})
        self.assertEqual(object_shape["properties"]["created_at"], {"type": "string", "format": "date-time"})

    def test_request_root_properties_request_body_rendering(self):
        string_option = autodoc_schema.String("payload")
        setattr(string_option, "description", "Serialized JSON payload")

        payload_property = autodoc_schema.OneOf(
            "payload",
            [
                string_option,
                autodoc_schema.Object(
                    "payload",
                    [doc for column in PayloadSchema.get_columns().values() for doc in column.documentation()],
                ),
            ],
        )

        request_root_properties = {
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": autodoc_schema.Object("body", [payload_property]),
                    },
                },
            },
        }
        request_root_properties["requestBody"]["content"]["application/json"]["schema"].children[0].required = True

        response = Response(schema=autodoc_schema.String("message"), status=200, description="Ok")
        request = Request(
            description="Create",
            responses=[response],
            relative_path="/schema-hints",
            request_methods=["POST"],
            root_properties=request_root_properties,
        )

        oai3_json = Oai3Json(OAI3SchemaResolver())
        oai3_json.set_requests([request])

        output = json.loads(oai3_json.compact())
        request_body = output["paths"]["/schema-hints"]["post"]["requestBody"]
        schema = request_body["content"]["application/json"]["schema"]

        self.assertTrue(request_body["required"])
        self.assertEqual(schema["type"], "object")
        self.assertEqual(schema["required"], ["payload"])
        self.assertIn("payload", schema["properties"])
        self.assertIn("oneOf", schema["properties"]["payload"])


if __name__ == "__main__":
    unittest.main()
