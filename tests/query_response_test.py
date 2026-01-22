"""Tests for QueryResult class."""

import unittest
from pytest import raises  # type: ignore

from clearskies.query.result import (
    QueryResult,
    RecordsQueryResult,
    CountQueryResult,
    SuccessQueryResult,
    FailedQueryResult,
)


class QueryResultTest(unittest.TestCase):
    """Test suite for QueryResult class."""

    def test_basic_initialization(self):
        """Test basic QueryResult initialization with defaults."""
        response = QueryResult()

        assert response.data is None
        assert response.success is True
        assert response.error is None
        assert response.total_count is None
        assert response.total_pages is None
        assert response.can_count is False
        assert response.next_page_data is None
        assert response.generator is None
        assert response.async_data is None

    def test_initialization_with_data(self):
        """Test QueryResult initialization with data."""
        data = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        response = QueryResult(
            data=data, success=True, total_count=100, total_pages=10, can_count=True, next_page_data={"start": 2}
        )

        assert response.data == data
        assert response.success is True
        assert response.total_count == 100
        assert response.total_pages == 10
        assert response.can_count is True
        assert response.next_page_data == {"start": 2}

    def test_iteration(self):
        """Test iterating over QueryResult."""
        data = [{"id": 1}, {"id": 2}, {"id": 3}]
        response = QueryResult(data=data)

        result = [item["id"] for item in response]
        assert result == [1, 2, 3]

    def test_iteration_error_on_non_iterable(self):
        """Test that iterating over non-iterable data raises TypeError."""
        response = QueryResult(data="not a list")

        with raises(TypeError) as exc_info:
            list(response)
        assert "not iterable" in str(exc_info.value)

    def test_as_generator(self):
        """Test as_generator method."""
        data = [{"id": 1}, {"id": 2}]
        response = QueryResult(data=data)

        gen = response.as_generator()
        result = list(gen)
        assert result == data

    def test_as_generator_with_custom_generator(self):
        """Test as_generator with custom generator function."""

        def custom_gen():
            yield {"id": 1}
            yield {"id": 2}

        response = QueryResult(data=None, generator=custom_gen)

        gen = response.as_generator()
        result = list(gen)
        assert result == [{"id": 1}, {"id": 2}]

    def test_as_generator_error_on_non_list(self):
        """Test as_generator raises error when no generator available for non-list."""
        response = QueryResult(data=42)

        with raises(NotImplementedError) as exc_info:
            response.as_generator()
        assert "No generator available" in str(exc_info.value)

    def test_get_count_with_can_count(self):
        """Test get_count returns total_count when can_count is True."""
        response = QueryResult(data=[{"id": 1}], total_count=50, can_count=True)

        assert response.get_count() == 50

    def test_get_count_from_data_length(self):
        """Test get_count returns data length when can_count is False."""
        data = [{"id": 1}, {"id": 2}, {"id": 3}]
        response = QueryResult(data=data, can_count=False)

        assert response.get_count() == 3

    def test_get_count_none_when_unavailable(self):
        """Test get_count returns None when count cannot be determined."""
        response = QueryResult(data="non-list", can_count=False)

        assert response.get_count() is None

    def test_has_more_pages(self):
        """Test has_more_pages method."""
        with_more_pages = QueryResult(next_page_data={"start": 10})
        without_more_pages = QueryResult(next_page_data=None)
        empty_next_page = QueryResult(next_page_data={})

        assert with_more_pages.has_more_pages() is True
        assert without_more_pages.has_more_pages() is False
        assert empty_next_page.has_more_pages() is False

    def test_repr(self):
        """Test __repr__ provides useful string representation."""
        response = QueryResult(data=[{"id": 1}], success=True, total_count=10, can_count=True)

        repr_str = repr(response)
        assert "QueryResult" in repr_str
        assert "success=True" in repr_str
        assert "total_count=10" in repr_str
        assert "can_count=True" in repr_str

    def test_repr_with_large_data(self):
        """Test __repr__ shows item count for large data lists."""
        data = [{"id": i} for i in range(10)]
        response = QueryResult(data=data)

        repr_str = repr(response)
        assert "[10 items]" in repr_str

    def test_type_validation_success(self):
        """Test that Boolean config validates types."""
        # These should work
        response = QueryResult(success=True)
        assert response.success is True

        response = QueryResult(success=False)
        assert response.success is False

    def test_type_validation_total_count(self):
        """Test that Integer config validates types for total_count."""
        response = QueryResult(total_count=100)
        assert response.total_count == 100

    def test_error_response_pattern(self):
        """Test typical error response pattern using FailedQueryResult."""
        error_message = "Database connection failed"
        response = FailedQueryResult(error=error_message)

        if not response.success:
            # Handle error case
            assert response.error_msg == error_message
            assert response.data is None

    def test_pagination_response_pattern(self):
        """Test typical pagination response pattern."""
        page_1 = QueryResult(
            data=[{"id": 1}, {"id": 2}], total_count=5, total_pages=3, can_count=True, next_page_data={"start": 2}
        )

        assert page_1.get_count() == 5  # Total count, not current page size
        assert len(list(page_1)) == 2  # Actual items in this page
        assert page_1.has_more_pages() is True

    def test_empty_response(self):
        """Test empty response handling."""
        response = QueryResult(data=[], total_count=0, can_count=True)

        assert response.get_count() == 0
        assert list(response) == []
        assert response.success is True  # Operation still succeeded


class RecordsQueryResultTest(unittest.TestCase):
    """Test cases for the RecordsQueryResult subclass."""

    def test_basic_records(self):
        result = RecordsQueryResult(records=[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}])
        self.assertEqual([{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}], result.data)
        self.assertEqual([{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}], result.records)
        self.assertTrue(result.success)

    def test_is_subclass(self):
        result = RecordsQueryResult(records=[{"id": 1}])
        self.assertIsInstance(result, QueryResult)
        self.assertIsInstance(result, RecordsQueryResult)

    def test_with_pagination(self):
        result = RecordsQueryResult(
            records=[{"id": 1}],
            total_count=100,
            total_pages=10,
            next_page_data={"start": 1},
        )
        self.assertEqual(100, result.total_count)
        self.assertEqual(10, result.total_pages)
        self.assertTrue(result.can_count)
        self.assertTrue(result.has_more_pages())
        self.assertEqual({"start": 1}, result.next_page_data)

    def test_iteration(self):
        records = [{"id": 1}, {"id": 2}, {"id": 3}]
        result = RecordsQueryResult(records=records)
        iterated = list(result)
        self.assertEqual(records, iterated)

    def test_len(self):
        result = RecordsQueryResult(records=[{"id": 1}, {"id": 2}, {"id": 3}])
        self.assertEqual(3, len(result))

    def test_empty_records(self):
        result = RecordsQueryResult()
        self.assertEqual([], result.data)
        self.assertEqual([], result.records)
        self.assertEqual(0, len(result))

    def test_repr(self):
        result = RecordsQueryResult(
            records=[{"id": 1}, {"id": 2}],
            total_count=50,
            next_page_data={"start": 2},
        )
        repr_str = repr(result)
        self.assertIn("RecordsQueryResult", repr_str)
        self.assertIn("2 items", repr_str)
        self.assertIn("total_count=50", repr_str)


class CountQueryResultTest(unittest.TestCase):
    """Test cases for the CountQueryResult subclass."""

    def test_basic_count(self):
        result = CountQueryResult(count=42)
        self.assertEqual(42, result.data)
        self.assertEqual(42, result.count)
        self.assertEqual(42, result.get_count())
        self.assertTrue(result.success)
        self.assertTrue(result.can_count)

    def test_is_subclass(self):
        result = CountQueryResult(count=10)
        self.assertIsInstance(result, QueryResult)
        self.assertIsInstance(result, CountQueryResult)

    def test_zero_count(self):
        result = CountQueryResult(count=0)
        self.assertEqual(0, result.count)
        self.assertEqual(0, int(result))
        # bool(result) returns False when count is 0
        self.assertFalse(bool(result))

    def test_nonzero_count_is_truthy(self):
        result = CountQueryResult(count=42)
        self.assertTrue(bool(result))

    def test_int_conversion(self):
        result = CountQueryResult(count=42)
        self.assertEqual(42, int(result))

    def test_repr(self):
        result = CountQueryResult(count=100)
        self.assertEqual("CountQueryResult(count=100)", repr(result))


class SuccessQueryResultTest(unittest.TestCase):
    """Test cases for the SuccessQueryResult subclass."""

    def test_success(self):
        result = SuccessQueryResult()
        self.assertTrue(result.success)
        self.assertIsNone(result.data)

    def test_is_subclass(self):
        result = SuccessQueryResult()
        self.assertIsInstance(result, QueryResult)
        self.assertIsInstance(result, SuccessQueryResult)

    def test_bool(self):
        result = SuccessQueryResult()
        self.assertTrue(bool(result))

    def test_repr(self):
        result = SuccessQueryResult()
        self.assertEqual("SuccessQueryResult(success=True)", repr(result))


class FailedQueryResultTest(unittest.TestCase):
    """Test cases for the FailedQueryResult subclass."""

    def test_basic_error(self):
        result = FailedQueryResult(error="Database connection failed")
        # Use .success to check for failure (not bool())
        self.assertFalse(result.success)
        self.assertEqual("Database connection failed", result.error_msg)
        self.assertIsNone(result.data)

    def test_is_subclass(self):
        result = FailedQueryResult(error="Test error")
        self.assertIsInstance(result, QueryResult)
        self.assertIsInstance(result, FailedQueryResult)

    def test_dict_error(self):
        error = {"message": "Not found", "code": 404}
        result = FailedQueryResult(error=error)
        self.assertEqual(error, result.error_msg)

    def test_success_is_false(self):
        result = FailedQueryResult(error="Error")
        # Note: FailedQueryResult's bool is True to avoid descriptor recursion
        # Use .success to check for failure
        self.assertFalse(result.success)

    def test_repr(self):
        result = FailedQueryResult(error="Test error")
        repr_str = repr(result)
        self.assertIn("FailedQueryResult", repr_str)
        self.assertIn("Test error", repr_str)


if __name__ == "__main__":
    unittest.main()
