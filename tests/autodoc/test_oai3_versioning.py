import json
import unittest

from clearskies.autodoc.formats.oai3_json import Oai3Json, OAI3SchemaResolver
from clearskies.autodoc.request import Request
from clearskies.autodoc.response import Response
from clearskies.autodoc.schema import String


class TestOai3Versioning(unittest.TestCase):
    def test_default_openapi_version(self):
        oai3_json = Oai3Json(OAI3SchemaResolver())
        response = Response(schema=String("message"), status=200, description="Ok")
        request = Request(description="Test", responses=[response], relative_path="/test", request_methods=["GET"])
        oai3_json.set_requests([request])
        output = json.loads(oai3_json.compact())
        self.assertEqual(output["openapi"], "3.0.0")

    def test_custom_openapi_version(self):
        oai3_json = Oai3Json(OAI3SchemaResolver(), openapi_version="3.1.0")
        response = Response(schema=String("message"), status=200, description="Ok")
        request = Request(description="Test", responses=[response], relative_path="/test", request_methods=["GET"])
        oai3_json.set_requests([request])
        output = json.loads(oai3_json.compact())
        self.assertEqual(output["openapi"], "3.1.0")


if __name__ == "__main__":
    unittest.main()
