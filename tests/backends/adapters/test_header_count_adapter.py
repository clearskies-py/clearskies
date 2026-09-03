import unittest

from clearskies.backends.adapters.header_count_adapter import HeaderCountAdapter


class HeaderCountAdapterTest(unittest.TestCase):
    def setUp(self):
        self.adapter = HeaderCountAdapter()

    def test_returns_none_when_no_headers(self):
        total, pages = self.adapter.extract_count(None, None)
        self.assertIsNone(total)
        self.assertIsNone(pages)

    def test_returns_none_when_empty_headers(self):
        total, pages = self.adapter.extract_count(None, {})
        self.assertIsNone(total)
        self.assertIsNone(pages)

    def test_reads_x_total_count(self):
        total, pages = self.adapter.extract_count(None, {"X-Total-Count": "42"})
        self.assertEqual(total, 42)
        self.assertIsNone(pages)

    def test_reads_x_total_count_case_insensitive(self):
        total, pages = self.adapter.extract_count(None, {"x-total-count": "100"})
        self.assertEqual(total, 100)

    def test_reads_x_total_fallback(self):
        total, pages = self.adapter.extract_count(None, {"X-Total": "55"})
        self.assertEqual(total, 55)
        self.assertIsNone(pages)

    def test_x_total_count_takes_precedence_over_x_total(self):
        total, pages = self.adapter.extract_count(None, {"X-Total-Count": "10", "X-Total": "20"})
        self.assertEqual(total, 10)

    def test_reads_x_total_pages(self):
        total, pages = self.adapter.extract_count(None, {"X-Total-Count": "100", "X-Total-Pages": "5"})
        self.assertEqual(total, 100)
        self.assertEqual(pages, 5)

    def test_ignores_invalid_total_count(self):
        total, pages = self.adapter.extract_count(None, {"X-Total-Count": "not-a-number"})
        self.assertIsNone(total)

    def test_ignores_invalid_total_pages(self):
        total, pages = self.adapter.extract_count(None, {"X-Total-Count": "100", "X-Total-Pages": "not-a-number"})
        self.assertEqual(total, 100)
        self.assertIsNone(pages)

    def test_response_data_is_ignored(self):
        """HeaderCountAdapter reads headers only, not body."""
        total, pages = self.adapter.extract_count({"total": 999}, {"X-Total-Count": "10"})
        self.assertEqual(total, 10)


if __name__ == "__main__":
    unittest.main()
