import unittest

from clearskies.backends.adapters.hal_json_response_adapter import HalJsonResponseAdapter


class HalJsonResponseAdapterTest(unittest.TestCase):
    def setUp(self):
        self.adapter = HalJsonResponseAdapter()

    # ── extract_records ────────────────────────────────────────────────────────

    def test_extract_records_bare_list(self):
        payload = [{"id": 1, "title": "Hello"}, {"id": 2, "title": "World"}]
        result = self.adapter.extract_records(payload)
        self.assertEqual(result, payload)

    def test_extract_records_bare_list_of_non_dicts_returns_none(self):
        self.assertIsNone(self.adapter.extract_records([1, 2, 3]))

    def test_extract_records_embedded_named_subresource(self):
        payload = {
            "_links": {"self": {"href": "/articles"}},
            "_embedded": {
                "articles": [
                    {"id": 1, "title": "Hello World", "_links": {"self": {"href": "/articles/1"}}},
                ]
            },
        }
        result = self.adapter.extract_records(payload)
        self.assertEqual(result, [{"id": 1, "title": "Hello World"}])

    def test_extract_records_named_list_container_keys(self):
        for key in ("items", "results", "records", "data", "content", "values", "paths"):
            payload = {key: [{"id": 1}]}
            result = self.adapter.extract_records(payload)
            self.assertEqual(result, [{"id": 1}], f"failed for key={key}")

    def test_extract_records_named_list_container_priority_over_key_map(self):
        # "items" should win even though the rest of the dict could look like a key->record map.
        payload = {"items": [{"id": 1}], "meta": {"count": 1}}
        result = self.adapter.extract_records(payload)
        self.assertEqual(result, [{"id": 1}])

    def test_extract_records_key_to_record_map_heuristic(self):
        payload = {
            "widgets": {"id": 1, "name": "Widget"},
            "gadgets": {"id": 2, "name": "Gadget"},
        }
        result = self.adapter.extract_records(payload)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        keys = {record["key"] for record in result}
        self.assertEqual(keys, {"widgets", "gadgets"})
        for record in result:
            self.assertIn("id", record)
            self.assertIn("name", record)

    def test_extract_records_key_to_record_map_excludes_hal_structural_keys(self):
        # A response with only _links/_embedded should NOT be misidentified as a key->record map.
        payload = {"_links": {"self": {"href": "/x"}}, "_embedded": {"items": [{"id": 1}]}}
        result = self.adapter.extract_records(payload)
        self.assertEqual(result, [{"id": 1}])

    def test_extract_records_recursive_fallback(self):
        # "count" is a scalar, so the key->record-map heuristic (step 3) doesn't apply at the top
        # level; the adapter must recurse into "nested" (step 4) to find the list.
        payload = {"count": 2, "nested": {"other_count": 3, "items": [{"id": 1}, {"id": 2}]}}
        result = self.adapter.extract_records(payload)
        self.assertEqual(result, [{"id": 1}, {"id": 2}])

    def test_extract_records_returns_none_when_nothing_found(self):
        self.assertIsNone(self.adapter.extract_records({"foo": "bar", "baz": 42}))

    def test_extract_records_returns_none_for_non_dict_non_list(self):
        self.assertIsNone(self.adapter.extract_records("a string"))
        self.assertIsNone(self.adapter.extract_records(None))
        self.assertIsNone(self.adapter.extract_records(42))

    def test_extract_records_strips_links_from_each_record(self):
        payload = {"items": [{"id": 1, "_links": {"self": {"href": "/x/1"}}}]}
        result = self.adapter.extract_records(payload)
        self.assertEqual(result, [{"id": 1}])

    # ── extract_record ──────────────────────────────────────────────────────────

    def test_extract_record_from_named_container_key(self):
        for key in ("item", "result", "record", "data"):
            payload = {key: {"id": 1, "_links": {}}}
            result = self.adapter.extract_record(payload)
            self.assertEqual(result, {"id": 1}, f"failed for key={key}")

    def test_extract_record_from_list_returns_first_dict(self):
        payload = [{"id": 1}, {"id": 2}]
        result = self.adapter.extract_record(payload)
        self.assertEqual(result, {"id": 1})

    def test_extract_record_from_list_with_no_dicts_returns_none(self):
        self.assertIsNone(self.adapter.extract_record([1, 2, 3]))

    def test_extract_record_from_embedded(self):
        payload = {"_embedded": {"article": {"id": 1, "title": "Hello", "_links": {}}}}
        result = self.adapter.extract_record(payload)
        self.assertEqual(result, {"id": 1, "title": "Hello"})

    def test_extract_record_bare_object_fallback(self):
        # No wrapper key at all -- the whole dict is treated as the record.
        payload = {"id": 1, "title": "Hello"}
        result = self.adapter.extract_record(payload)
        self.assertEqual(result, {"id": 1, "title": "Hello"})

    def test_extract_record_returns_none_for_non_dict_non_list(self):
        self.assertIsNone(self.adapter.extract_record("a string"))
        self.assertIsNone(self.adapter.extract_record(None))
        self.assertIsNone(self.adapter.extract_record(42))

    # ── _normalize_record ───────────────────────────────────────────────────────

    def test_normalize_record_strips_metadata_keys(self):
        record = {"id": 1, "_links": {"self": {"href": "/x/1"}}}
        result = self.adapter._normalize_record(record)
        self.assertEqual(result, {"id": 1})

    def test_normalize_record_promotes_embedded_without_overwriting(self):
        record = {
            "id": 1,
            "author": "top-level-author",
            "_embedded": {"author": "embedded-author", "publisher": "embedded-publisher"},
        }
        result = self.adapter._normalize_record(record)
        # existing top-level key wins
        self.assertEqual(result["author"], "top-level-author")
        # new key from _embedded gets promoted
        self.assertEqual(result["publisher"], "embedded-publisher")

    def test_normalize_record_custom_metadata_keys_subclass(self):
        class MyAdapter(HalJsonResponseAdapter):
            metadata_keys = HalJsonResponseAdapter.metadata_keys + ("_meta",)

        adapter = MyAdapter()
        record = {"id": 1, "_links": {}, "_meta": {"stale": True}}
        result = adapter._normalize_record(record)
        self.assertEqual(result, {"id": 1})

    def test_list_container_keys_extendable_via_subclass(self):
        class MyAdapter(HalJsonResponseAdapter):
            list_container_keys = HalJsonResponseAdapter.list_container_keys + ("entries",)

        adapter = MyAdapter()
        result = adapter.extract_records({"entries": [{"id": 1}]})
        self.assertEqual(result, [{"id": 1}])

    def test_record_container_keys_extendable_via_subclass(self):
        class MyAdapter(HalJsonResponseAdapter):
            record_container_keys = HalJsonResponseAdapter.record_container_keys + ("payload",)

        adapter = MyAdapter()
        result = adapter.extract_record({"payload": {"id": 1}})
        self.assertEqual(result, {"id": 1})


if __name__ == "__main__":
    unittest.main()
