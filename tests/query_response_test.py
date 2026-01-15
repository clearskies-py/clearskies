"""Tests for QueryResponse class."""

import unittest
from pytest import raises  # type: ignore

from clearskies import QueryResponse


class QueryResponseTest(unittest.TestCase):
    """Test suite for QueryResponse class."""

    def test_basic_initialization(self):
        """Test basic QueryResponse initialization with defaults."""
        response = QueryResponse()

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
        """Test QueryResponse initialization with data."""
        data = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        response = QueryResponse(
            data=data, success=True, total_count=100, total_pages=10, can_count=True, next_page_data={"start": 2}
        )

        assert response.data == data
        assert response.success is True
        assert response.total_count == 100
        assert response.total_pages == 10
        assert response.can_count is True
        assert response.next_page_data == {"start": 2}

    def test_from_error_factory(self):
        """Test QueryResponse.from_error factory method."""
        error = {"message": "Something went wrong", "code": 500}
        response = QueryResponse.from_error(error)

        assert response.data is None
        assert response.success is False
        assert response.error == error

    def test_iteration(self):
        """Test iterating over QueryResponse."""
        data = [{"id": 1}, {"id": 2}, {"id": 3}]
        response = QueryResponse(data=data)

        result = [item["id"] for item in response]
        assert result == [1, 2, 3]

    def test_iteration_error_on_non_iterable(self):
        """Test that iterating over non-iterable data raises TypeError."""
        response = QueryResponse(data="not a list")

        with raises(TypeError) as exc_info:
            list(response)
        assert "not iterable" in str(exc_info.value)

    def test_as_generator(self):
        """Test as_generator method."""
        data = [{"id": 1}, {"id": 2}]
        response = QueryResponse(data=data)

        gen = response.as_generator()
        result = list(gen)
        assert result == data

    def test_as_generator_with_custom_generator(self):
        """Test as_generator with custom generator function."""

        def custom_gen():
            yield {"id": 1}
            yield {"id": 2}

        response = QueryResponse(data=None, generator=custom_gen)

        gen = response.as_generator()
        result = list(gen)
        assert result == [{"id": 1}, {"id": 2}]

    def test_as_generator_error_on_non_list(self):
        """Test as_generator raises error when no generator available for non-list."""
        response = QueryResponse(data=42)

        with raises(NotImplementedError) as exc_info:
            response.as_generator()
        assert "No generator available" in str(exc_info.value)

    def test_get_count_with_can_count(self):
        """Test get_count returns total_count when can_count is True."""
        response = QueryResponse(data=[{"id": 1}], total_count=50, can_count=True)

        assert response.get_count() == 50

    def test_get_count_from_data_length(self):
        """Test get_count returns data length when can_count is False."""
        data = [{"id": 1}, {"id": 2}, {"id": 3}]
        response = QueryResponse(data=data, can_count=False)

        assert response.get_count() == 3

    def test_get_count_none_when_unavailable(self):
        """Test get_count returns None when count cannot be determined."""
        response = QueryResponse(data="non-list", can_count=False)

        assert response.get_count() is None

    def test_has_more_pages(self):
        """Test has_more_pages method."""
        with_more_pages = QueryResponse(next_page_data={"start": 10})
        without_more_pages = QueryResponse(next_page_data=None)
        empty_next_page = QueryResponse(next_page_data={})

        assert with_more_pages.has_more_pages() is True
        assert without_more_pages.has_more_pages() is False
        assert empty_next_page.has_more_pages() is False

    def test_repr(self):
        """Test __repr__ provides useful string representation."""
        response = QueryResponse(data=[{"id": 1}], success=True, total_count=10, can_count=True)

        repr_str = repr(response)
        assert "QueryResponse" in repr_str
        assert "success=True" in repr_str
        assert "total_count=10" in repr_str
        assert "can_count=True" in repr_str

    def test_repr_with_large_data(self):
        """Test __repr__ shows item count for large data lists."""
        data = [{"id": i} for i in range(10)]
        response = QueryResponse(data=data)

        repr_str = repr(response)
        assert "[10 items]" in repr_str

    def test_type_validation_success(self):
        """Test that Boolean config validates types."""
        # These should work
        response = QueryResponse(success=True)
        assert response.success is True

        response = QueryResponse(success=False)
        assert response.success is False

    def test_type_validation_total_count(self):
        """Test that Integer config validates types for total_count."""
        response = QueryResponse(total_count=100)
        assert response.total_count == 100

    def test_error_response_pattern(self):
        """Test typical error response pattern."""
        error_message = "Database connection failed"
        response = QueryResponse.from_error(error_message)

        if not response.success:
            # Handle error case
            assert response.error == error_message
            assert response.data is None

    def test_pagination_response_pattern(self):
        """Test typical pagination response pattern."""
        page_1 = QueryResponse(
            data=[{"id": 1}, {"id": 2}], total_count=5, total_pages=3, can_count=True, next_page_data={"start": 2}
        )

        assert page_1.get_count() == 5  # Total count, not current page size
        assert len(list(page_1)) == 2  # Actual items in this page
        assert page_1.has_more_pages() is True

    def test_empty_response(self):
        """Test empty response handling."""
        response = QueryResponse(data=[], total_count=0, can_count=True)

        assert response.get_count() == 0
        assert list(response) == []
        assert response.success is True  # Operation still succeeded


if __name__ == "__main__":
    unittest.main()
