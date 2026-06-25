import json
import unittest

from clearskies.autodoc import schema as autodoc_schema
from clearskies.autodoc.formats.oai3_json import Oai3Json, OAI3SchemaResolver
from clearskies.autodoc.request import Request
from clearskies.autodoc.response import Response


class TestOai3RootPropertiesNormalization(unittest.TestCase):
    def test_nested_schema_nodes_in_root_properties_are_converted(self):
        response = Response(schema=autodoc_schema.String("message"), status=200, description="Ok")
        request = Request(
            description="Create",
            responses=[response],
            relative_path="/items",
            request_methods=["POST"],
            root_properties={
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": autodoc_schema.Object(
                                "body",
                                [
                                    autodoc_schema.String("name"),
                                    autodoc_schema.OneOf(
                                        "payload",
                                        [
                                            autodoc_schema.String("payload"),
                                            autodoc_schema.Object("payload", [autodoc_schema.Integer("count")]),
                                        ],
                                    ),
                                ],
                            )
                        }
                    },
                }
            },
        )
        assert request.root_properties is not None
        root_schema = request.root_properties["requestBody"]["content"]["application/json"]["schema"]
        if root_schema and root_schema.children:
            root_schema.children[0].required = True

        oai3_json = Oai3Json(OAI3SchemaResolver())
        oai3_json.set_requests([request])

        output = json.loads(oai3_json.compact())
        schema = output["paths"]["/items"]["post"]["requestBody"]["content"]["application/json"]["schema"]

        self.assertEqual(schema["type"], "object")
        self.assertIn("required", schema)
        self.assertEqual(schema["required"], ["name"])
        self.assertIn("oneOf", schema["properties"]["payload"])


if __name__ == "__main__":
    unittest.main()
