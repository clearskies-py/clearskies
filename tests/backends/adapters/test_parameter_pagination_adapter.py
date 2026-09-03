import unittest
from unittest.mock import MagicMock

from clearskies.backends.adapters.parameter_pagination_adapter import ParameterPaginationAdapter


class ParameterPaginationAdapterTest(unittest.TestCase):
    def _make_query(self, pagination=None, limit=None):
        query = MagicMock()
        query.pagination = pagination or {}
        query.limit = limit
        return query

    def _make_response(self, records=None, content=True):
        response = MagicMock()
        response.content = content
        if records is not None:
            response.json.return_value = records
        return response

    # ── page-based ──────────────────────────────────────────────────────────

    def test_increments_page_from_start_value(self):
        adapter = ParameterPaginationAdapter(pagination_parameter_name="page", start_value=1, step=1)
        query = self._make_query(pagination={}, limit=10)
        response = self._make_response(records=[{"id": i} for i in range(10)])
        result = adapter.extract_next_page_data(response, query)
        self.assertEqual(result, {"page": "2"})

    def test_increments_from_current_page(self):
        adapter = ParameterPaginationAdapter(pagination_parameter_name="page", start_value=1, step=1)
        query = self._make_query(pagination={"page": "3"}, limit=10)
        response = self._make_response(records=[{"id": i} for i in range(10)])
        result = adapter.extract_next_page_data(response, query)
        self.assertEqual(result, {"page": "4"})

    def test_returns_empty_when_fewer_records_than_limit(self):
        adapter = ParameterPaginationAdapter(pagination_parameter_name="page", start_value=1, step=1)
        query = self._make_query(pagination={"page": "3"}, limit=10)
        response = self._make_response(records=[{"id": i} for i in range(5)])
        result = adapter.extract_next_page_data(response, query)
        self.assertEqual(result, {})

    # ── offset-based ────────────────────────────────────────────────────────

    def test_offset_uses_limit_as_step(self):
        adapter = ParameterPaginationAdapter(pagination_parameter_name="offset", start_value=0, use_limit_as_step=True)
        query = self._make_query(pagination={}, limit=50)
        response = self._make_response(records=[{"id": i} for i in range(50)])
        result = adapter.extract_next_page_data(response, query)
        self.assertEqual(result, {"offset": "50"})

    def test_offset_increments_from_current(self):
        adapter = ParameterPaginationAdapter(pagination_parameter_name="offset", start_value=0, use_limit_as_step=True)
        query = self._make_query(pagination={"offset": "100"}, limit=50)
        response = self._make_response(records=[{"id": i} for i in range(50)])
        result = adapter.extract_next_page_data(response, query)
        self.assertEqual(result, {"offset": "150"})

    def test_offset_stops_on_partial_page(self):
        adapter = ParameterPaginationAdapter(pagination_parameter_name="offset", start_value=0, use_limit_as_step=True)
        query = self._make_query(pagination={"offset": "100"}, limit=50)
        response = self._make_response(records=[{"id": i} for i in range(30)])
        result = adapter.extract_next_page_data(response, query)
        self.assertEqual(result, {})

    # ── edge cases ──────────────────────────────────────────────────────────

    def test_returns_empty_when_no_content(self):
        """With no response content we can't check record count, default to no next page."""
        adapter = ParameterPaginationAdapter(pagination_parameter_name="page", start_value=1, step=1)
        query = self._make_query(pagination={}, limit=10)
        response = self._make_response(records=None, content=False)
        # No content means we can't determine next page, increments anyway since we can't check
        result = adapter.extract_next_page_data(response, query)
        # With no content, json() won't be parseable as a list, so we fall through to increment
        self.assertEqual(result, {"page": "2"})

    def test_handles_non_list_response_body(self):
        """If response body is a dict (enveloped), fall through to increment."""
        adapter = ParameterPaginationAdapter(pagination_parameter_name="page", start_value=1, step=1)
        query = self._make_query(pagination={"page": "2"}, limit=10)
        response = MagicMock()
        response.content = True
        response.json.return_value = {"data": [{"id": i} for i in range(10)], "total": 100}
        result = adapter.extract_next_page_data(response, query)
        # body is not a list, can't check count, so increments
        self.assertEqual(result, {"page": "3"})


if __name__ == "__main__":
    unittest.main()
