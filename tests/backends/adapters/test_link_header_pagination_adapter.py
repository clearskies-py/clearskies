import unittest
from unittest.mock import MagicMock

from clearskies.backends.adapters.link_header_pagination_adapter import LinkHeaderPaginationAdapter


class LinkHeaderPaginationAdapterTest(unittest.TestCase):
    def setUp(self):
        self.adapter = LinkHeaderPaginationAdapter(pagination_parameter_name="start")
        self.query = MagicMock()

    def _make_response(self, link_header=None):
        response = MagicMock()
        headers = {}
        if link_header is not None:
            headers["link"] = link_header
        response.headers = headers
        return response

    def test_returns_empty_when_no_link_header(self):
        response = self._make_response()
        result = self.adapter.extract_next_page_data(response, self.query)
        self.assertEqual(result, {})

    def test_returns_empty_when_no_rel_next(self):
        response = self._make_response('<https://api.example.com/users?start=0>; rel="prev"')
        result = self.adapter.extract_next_page_data(response, self.query)
        self.assertEqual(result, {})

    def test_extracts_pagination_param_from_next_link(self):
        response = self._make_response('<https://api.example.com/users?start=50>; rel="next"')
        result = self.adapter.extract_next_page_data(response, self.query)
        self.assertEqual(result, {"start": "50"})

    def test_extracts_from_multi_link_header(self):
        response = self._make_response(
            '<https://api.example.com/users?start=0>; rel="prev", <https://api.example.com/users?start=50>; rel="next"'
        )
        result = self.adapter.extract_next_page_data(response, self.query)
        self.assertEqual(result, {"start": "50"})

    def test_custom_pagination_parameter_name(self):
        adapter = LinkHeaderPaginationAdapter(pagination_parameter_name="page")
        response = self._make_response('<https://api.example.com/users?page=3>; rel="next"')
        result = adapter.extract_next_page_data(response, self.query)
        self.assertEqual(result, {"page": "3"})

    def test_raises_when_param_not_in_next_link(self):
        response = self._make_response('<https://api.example.com/users?cursor=abc>; rel="next"')
        with self.assertRaises(ValueError) as ctx:
            self.adapter.extract_next_page_data(response, self.query)
        self.assertIn("start", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
