import unittest

from clearskies.backends.adapters.body_count_adapter import BodyCountAdapter


class BodyCountAdapterTest(unittest.TestCase):
    # ── no data ────────────────────────────────────────────────────────────

    def test_returns_none_when_no_response_data(self):
        adapter = BodyCountAdapter(count_path="total")
        total, pages = adapter.extract_count(None, None)
        self.assertIsNone(total)
        self.assertIsNone(pages)

    # ── top-level path ─────────────────────────────────────────────────────

    def test_reads_top_level_count(self):
        adapter = BodyCountAdapter(count_path="total")
        total, pages = adapter.extract_count({"total": 42, "data": []}, None)
        self.assertEqual(total, 42)
        self.assertIsNone(pages)

    def test_reads_top_level_count_and_pages(self):
        adapter = BodyCountAdapter(count_path="total", pages_path="pages")
        total, pages = adapter.extract_count({"total": 100, "pages": 5}, None)
        self.assertEqual(total, 100)
        self.assertEqual(pages, 5)

    # ── nested dot-notation path ───────────────────────────────────────────

    def test_reads_nested_count(self):
        adapter = BodyCountAdapter(count_path="meta.total")
        data = {"data": [], "meta": {"total": 99}}
        total, pages = adapter.extract_count(data, None)
        self.assertEqual(total, 99)

    def test_reads_deeply_nested_count(self):
        adapter = BodyCountAdapter(
            count_path="meta.pagination.total",
            pages_path="meta.pagination.pages",
        )
        data = {
            "data": [],
            "meta": {
                "pagination": {
                    "total": 150,
                    "pages": 10,
                }
            },
        }
        total, pages = adapter.extract_count(data, None)
        self.assertEqual(total, 150)
        self.assertEqual(pages, 10)

    # ── missing paths ─────────────────────────────────────────────────────

    def test_returns_none_when_path_not_found(self):
        adapter = BodyCountAdapter(count_path="meta.total")
        total, pages = adapter.extract_count({"data": []}, None)
        self.assertIsNone(total)

    def test_returns_none_when_intermediate_key_missing(self):
        adapter = BodyCountAdapter(count_path="meta.pagination.total")
        total, pages = adapter.extract_count({"meta": {}}, None)
        self.assertIsNone(total)

    def test_returns_none_when_no_count_path_set(self):
        adapter = BodyCountAdapter()
        total, pages = adapter.extract_count({"total": 42}, None)
        self.assertIsNone(total)

    # ── invalid values ─────────────────────────────────────────────────────

    def test_ignores_non_integer_count(self):
        adapter = BodyCountAdapter(count_path="total")
        total, pages = adapter.extract_count({"total": "not-a-number"}, None)
        self.assertIsNone(total)

    def test_ignores_non_integer_pages(self):
        adapter = BodyCountAdapter(count_path="total", pages_path="pages")
        total, pages = adapter.extract_count({"total": 100, "pages": "bad"}, None)
        self.assertEqual(total, 100)
        self.assertIsNone(pages)

    # ── type coercion ──────────────────────────────────────────────────────

    def test_coerces_string_integer_count(self):
        adapter = BodyCountAdapter(count_path="total")
        total, pages = adapter.extract_count({"total": "42"}, None)
        self.assertEqual(total, 42)

    def test_coerces_float_count(self):
        adapter = BodyCountAdapter(count_path="total")
        total, pages = adapter.extract_count({"total": 42.9}, None)
        self.assertEqual(total, 42)

    # ── response headers ignored ───────────────────────────────────────────

    def test_response_headers_are_ignored(self):
        adapter = BodyCountAdapter(count_path="total")
        total, pages = adapter.extract_count(
            {"total": 10},
            {"X-Total-Count": "999"},
        )
        self.assertEqual(total, 10)

    # ── _resolve_path ──────────────────────────────────────────────────────

    def test_resolve_path_returns_none_for_non_dict(self):
        adapter = BodyCountAdapter()
        result = adapter._resolve_path([1, 2, 3], "total")
        self.assertIsNone(result)

    def test_resolve_path_empty_path_returns_none(self):
        adapter = BodyCountAdapter()
        result = adapter._resolve_path({"total": 1}, "")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
