import unittest

from clearskies.backends.adapters.json_api_response_adapter import JsonApiResponseAdapter


class JsonApiResponseAdapterTest(unittest.TestCase):
    def setUp(self):
        self.adapter = JsonApiResponseAdapter()

    # ── extract_records ────────────────────────────────────────────────────────

    def test_extract_records_returns_flattened_list(self):
        payload = {
            "data": [
                {"id": "1", "type": "articles", "attributes": {"title": "Hello", "body": "World"}},
                {"id": "2", "type": "articles", "attributes": {"title": "Bye", "body": "Now"}},
            ]
        }
        result = self.adapter.extract_records(payload)
        self.assertEqual(
            result,
            [
                {"id": "1", "type": "articles", "title": "Hello", "body": "World"},
                {"id": "2", "type": "articles", "title": "Bye", "body": "Now"},
            ],
        )

    def test_extract_records_empty_data_list(self):
        result = self.adapter.extract_records({"data": []})
        self.assertEqual(result, [])

    def test_extract_records_returns_none_when_data_is_not_list(self):
        # data is a dict → single-resource shape, not a list
        payload = {"data": {"id": "1", "type": "articles", "attributes": {}}}
        result = self.adapter.extract_records(payload)
        self.assertIsNone(result)

    def test_extract_records_returns_none_when_data_key_missing(self):
        result = self.adapter.extract_records({"other": [{"id": "1"}]})
        self.assertIsNone(result)

    def test_extract_records_returns_none_for_non_dict(self):
        self.assertIsNone(self.adapter.extract_records([{"id": "1"}]))
        self.assertIsNone(self.adapter.extract_records("string"))
        self.assertIsNone(self.adapter.extract_records(None))

    def test_extract_records_no_attributes_key(self):
        # Resource objects without attributes are still normalised
        payload = {"data": [{"id": "3", "type": "tags"}]}
        result = self.adapter.extract_records(payload)
        self.assertEqual(result, [{"id": "3", "type": "tags"}])

    # ── extract_record ─────────────────────────────────────────────────────────

    def test_extract_record_from_data_dict(self):
        payload = {"data": {"id": "42", "type": "articles", "attributes": {"title": "Hello", "body": "World"}}}
        result = self.adapter.extract_record(payload)
        self.assertEqual(result, {"id": "42", "type": "articles", "title": "Hello", "body": "World"})

    def test_extract_record_returns_none_when_data_is_list(self):
        # list under data → single-record extraction cannot apply
        payload = {"data": [{"id": "1", "type": "x", "attributes": {}}]}
        result = self.adapter.extract_record(payload)
        self.assertIsNone(result)

    def test_extract_record_fallback_bare_attributes(self):
        # Payload already stripped of the outer "data" wrapper
        payload = {"id": "5", "type": "users", "attributes": {"name": "Alice"}}
        result = self.adapter.extract_record(payload)
        self.assertEqual(result, {"id": "5", "type": "users", "name": "Alice"})

    def test_extract_record_returns_none_for_non_dict(self):
        self.assertIsNone(self.adapter.extract_record([]))
        self.assertIsNone(self.adapter.extract_record("string"))
        self.assertIsNone(self.adapter.extract_record(42))

    def test_extract_record_returns_none_when_no_data_or_attributes(self):
        result = self.adapter.extract_record({"other": "stuff"})
        self.assertIsNone(result)

    # ── _normalize_record ──────────────────────────────────────────────────────

    def test_normalize_record_id_wins_over_attribute_id(self):
        # JSON:API spec: resource-level id is the canonical identifier.
        # An attribute named "id" must not shadow it.
        data_block = {
            "id": "canonical-id",
            "type": "widgets",
            "attributes": {"id": "attribute-id", "name": "Thing"},
        }
        result = self.adapter._normalize_record(data_block)
        self.assertEqual(result["id"], "canonical-id")
        self.assertEqual(result["name"], "Thing")

    def test_normalize_record_type_wins_over_attribute_type(self):
        data_block = {
            "id": "1",
            "type": "canonical-type",
            "attributes": {"type": "attribute-type"},
        }
        result = self.adapter._normalize_record(data_block)
        self.assertEqual(result["type"], "canonical-type")

    def test_normalize_record_attributes_spread_to_top(self):
        data_block = {"id": "1", "attributes": {"foo": "bar", "baz": 42}}
        result = self.adapter._normalize_record(data_block)
        self.assertIn("foo", result)
        self.assertIn("baz", result)

    def test_normalize_record_no_attributes_key(self):
        data_block = {"id": "7", "type": "empty"}
        result = self.adapter._normalize_record(data_block)
        self.assertEqual(result, {"id": "7", "type": "empty"})

    def test_normalize_record_relationships_not_included(self):
        data_block = {
            "id": "1",
            "type": "posts",
            "attributes": {"title": "Hi"},
            "relationships": {"author": {"data": {"id": "2", "type": "users"}}},
        }
        result = self.adapter._normalize_record(data_block)
        self.assertNotIn("relationships", result)

    def test_normalize_record_links_not_included(self):
        data_block = {
            "id": "1",
            "type": "posts",
            "attributes": {"title": "Hi"},
            "links": {"self": "/posts/1"},
        }
        result = self.adapter._normalize_record(data_block)
        self.assertNotIn("links", result)

    def test_normalize_record_non_dict_attributes_treated_as_empty(self):
        data_block = {"id": "1", "attributes": "bad-value"}
        result = self.adapter._normalize_record(data_block)
        self.assertEqual(result, {"id": "1"})


if __name__ == "__main__":
    unittest.main()
