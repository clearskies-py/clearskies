"""
QueryResponse - A flexible response wrapper for backend and model operations.

This class wraps backend operation results (records, create, update, delete, count)
to provide a consistent interface with support for:

- Pagination metadata (total_count, total_pages, next_page_data)
- Count caching to avoid redundant API calls
- Generator and async access patterns
- Type-safe configuration via clearskies config descriptors

The primary motivation is to improve how record counts are communicated across backends.
When ``records()`` is called and the response contains count headers, the QueryResponse
caches this information so that ``count()`` can return the cached value instead of making
a separate request.

Example usage:

```python
import clearskies

# Creating a QueryResponse for a records query
response = clearskies.QueryResponse(
    data=[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
    success=True,
    total_count=100,
    total_pages=10,
    can_count=True,
    next_page_data={"start": 2},
)

# Iterating over records
for record in response:
    print(record["name"])

# Checking if count is available
if response.can_count:
    print(f"Total records: {response.get_count()}")

# Using as a generator for memory efficiency
for record in response.as_generator():
    process(record)
```
"""

from __future__ import annotations

from typing import Any as AnyType
from typing import Callable as CallableType
from typing import Generator, Iterator

from clearskies import configurable, decorators, loggable
from clearskies.configs import Any, Boolean, Callable, IntegerOrNone


class QueryResponse(
    loggable.Loggable,
    configurable.Configurable,
):
    """
    A flexible response wrapper for backend and model operations.

    QueryResponse wraps the results from backend operations (records, create, update, delete, count)
    to provide a consistent interface for accessing data, pagination info, and count caching.
    This is particularly useful for API backends where count information may be returned in
    response headers alongside record data.
    """

    _descriptor_config_map = None

    """
    The primary data field containing the operation result.

    This can hold various types depending on the operation:
    - A list of dictionaries for ``records()`` operations
    - A single dictionary for ``create()`` or ``update()`` operations
    - A boolean for ``delete()`` operations
    - An integer for ``count()`` operations
    - None if the operation had no data to return

    ```python
    import clearskies

    # Records response
    response = clearskies.QueryResponse(
        data=[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
    )
    for record in response:
        print(record["name"])

    # Single record response
    response = clearskies.QueryResponse(
        data={"id": 1, "name": "Alice"},
    )

    # Delete response
    response = clearskies.QueryResponse(data=True)
    ```
    """
    data = Any(default=None)

    """
    Boolean indicating whether the operation was successful.

    Defaults to ``True``. Set to ``False`` when the operation failed.
    Use ``QueryResponse.from_error()`` to create an error response.

    ```python
    import clearskies

    # Success response
    success_response = clearskies.QueryResponse(
        data=[{"id": 1}],
        success=True,
    )

    # Error response
    error_response = clearskies.QueryResponse.from_error(
        "Database connection failed"
    )
    print(error_response.success)  # False
    ```
    """
    success = Boolean(default=True)

    """
    Error information if the operation failed.

    Can be a string, dictionary, exception, or any other error representation.
    Typically set when ``success`` is ``False``.

    ```python
    import clearskies

    response = clearskies.QueryResponse.from_error({
        "message": "Record not found",
        "code": 404
    })
    print(response.error)  # {"message": "Record not found", "code": 404}
    ```
    """
    error = Any(default=None)

    """
    Total count of records available (not just those returned in this response).

    This is typically populated from API response headers like ``x-total-count``.
    When set along with ``can_count=True``, allows the model to return cached count
    information without making additional API calls.

    ```python
    import clearskies

    # API returned 10 records but indicated 100 total exist
    response = clearskies.QueryResponse(
        data=[{"id": i} for i in range(10)],
        total_count=100,
        can_count=True,
    )
    print(response.get_count())  # 100 (from cache, not len(data))
    ```
    """
    total_count = IntegerOrNone(default=None)

    """
    Total number of pages available.

    This is typically populated from API response headers like ``x-total-pages``.
    Useful for building pagination UI or determining how many requests are needed
    to fetch all data.

    ```python
    import clearskies

    response = clearskies.QueryResponse(
        data=[{"id": i} for i in range(10)],
        total_count=100,
        total_pages=10,
        can_count=True,
    )
    ```
    """
    total_pages = IntegerOrNone(default=None)

    """
    Whether count information is available and reliable.

    When ``True``, indicates that ``total_count`` contains a valid count that can be
    used instead of making a separate count query. This is set when the backend
    extracts count information from response headers or body.

    ```python
    import clearskies

    # Response with count info from headers
    response = clearskies.QueryResponse(
        data=[{"id": 1}],
        total_count=50,
        can_count=True,
    )

    if response.can_count:
        print(f"Total: {response.get_count()}")  # Uses cached count
    ```
    """
    can_count = Boolean(default=False)

    """
    Pagination data for fetching the next page of results.

    This dictionary contains the parameters needed to request the next page.
    The format depends on the backend's pagination style (offset, cursor, etc.).

    ```python
    import clearskies

    # Offset-based pagination
    response = clearskies.QueryResponse(
        data=[{"id": i} for i in range(10)],
        next_page_data={"start": 10},
    )

    if response.has_more_pages():
        # Use next_page_data to fetch more results
        print(response.next_page_data)  # {"start": 10}

    # Cursor-based pagination
    response = clearskies.QueryResponse(
        data=[{"id": i} for i in range(10)],
        next_page_data={"cursor": "eyJpZCI6MTB9"},
    )
    ```
    """
    next_page_data = Any(default=None)

    """
    Optional generator function for lazy iteration over data.

    When provided, ``as_generator()`` will call this function to get a generator
    instead of iterating over ``data`` directly. This is useful for streaming
    large result sets without loading everything into memory.

    ```python
    import clearskies

    def fetch_records_lazily():
        for i in range(1000):
            yield {"id": i, "name": f"Record {i}"}

    response = clearskies.QueryResponse(
        generator=fetch_records_lazily,
    )

    for record in response.as_generator():
        print(record["name"])  # Records fetched one at a time
    ```
    """
    generator = Callable(default=None)

    """
    Optional async function for asynchronous data access.

    When provided, ``as_async()`` will call this function to get data asynchronously.
    This is useful for async backends or when data needs to be fetched on-demand.

    ```python
    import clearskies
    import asyncio

    async def fetch_data_async():
        await asyncio.sleep(0.1)  # Simulate async operation
        return [{"id": 1}, {"id": 2}]

    response = clearskies.QueryResponse(
        async_data=fetch_data_async,
    )

    # In async context:
    # data = await response.as_async()
    ```
    """
    async_data = Callable(default=None)

    @decorators.parameters_to_properties
    def __init__(
        self,
        data: AnyType = None,
        success: bool = True,
        error: AnyType = None,
        total_count: int | None = None,
        total_pages: int | None = None,
        can_count: bool = False,
        next_page_data: AnyType = None,
        generator: CallableType[[], Generator[AnyType, None, None]] | None = None,
        async_data: CallableType[[], AnyType] | None = None,
    ) -> None:
        """Initialize QueryResponse with provided configuration values."""
        self.finalize_and_validate_configuration()

    def as_generator(self) -> Generator[AnyType, None, None]:
        """Return data as a generator for lazy iteration."""
        if self.generator:
            return self.generator()
        if isinstance(self.data, (list, tuple)):
            return (item for item in self.data)
        raise NotImplementedError("No generator available for non-list data")

    async def as_async(self) -> AnyType:
        """Return data via async interface."""
        if self.async_data:
            return await self.async_data()
        raise NotImplementedError("No async data function available")

    def __iter__(self) -> Iterator[AnyType]:
        """Allow direct iteration over data."""
        if isinstance(self.data, (list, tuple)):
            return iter(self.data)
        raise TypeError("QueryResponse data is not iterable")

    def __repr__(self) -> str:
        """Return string representation of QueryResponse."""
        data_preview = self.data
        if isinstance(self.data, list) and len(self.data) > 3:
            data_preview = f"[{len(self.data)} items]"
        return (
            f"QueryResponse("
            f"data={data_preview}, "
            f"success={self.success}, "
            f"total_count={self.total_count}, "
            f"can_count={self.can_count})"
        )

    def get_count(self) -> int | None:
        """
        Get the count if available, otherwise return None.

        This is useful when you want to check if count is available
        before using it, without raising an exception.
        """
        if self.can_count:
            return self.total_count
        if isinstance(self.data, (list, tuple)):
            return len(self.data)
        return None

    def has_more_pages(self) -> bool:
        """Check if there are more pages of data available."""
        return self.next_page_data is not None and bool(self.next_page_data)

    @classmethod
    def from_error(cls, error: AnyType, **kwargs: AnyType) -> "QueryResponse":
        """Create a QueryResponse representing an error."""
        return cls(data=None, success=False, error=error, **kwargs)
