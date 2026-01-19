"""
QueryResult - A flexible result wrapper for backend and model operations.

This class wraps backend operation results (records, create, update, delete, count)
to provide a consistent interface with support for:

- Pagination metadata (total_count, total_pages, next_page_data)
- Count caching to avoid redundant API calls
- Generator and async access patterns
- Type-safe configuration via clearskies config descriptors

The primary motivation is to improve how record counts are communicated across backends.
When ``records()`` is called and the response contains count headers, the QueryResult
caches this information so that ``count()`` can return the cached value instead of making
a separate request.

Example usage:

```python
from clearskies.query.result import QueryResult

# Creating a QueryResult for a records query
result = QueryResult(
    data=[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
    success=True,
    total_count=100,
    total_pages=10,
    can_count=True,
    next_page_data={"start": 2},
)

# Iterating over records
for record in result:
    print(record["name"])

# Checking if count is available
if result.can_count:
    print(f"Total records: {result.get_count()}")

# Using as a generator for memory efficiency
for record in result.as_generator():
    process(record)
```
"""

from __future__ import annotations

from typing import Any as AnyType
from typing import Callable as CallableType
from typing import Generator, Iterator

from clearskies import configurable, decorators, loggable
from clearskies.configs import Any, Boolean, Callable, IntegerOrNone


class QueryResult(
    loggable.Loggable,
    configurable.Configurable,
):
    """
    A flexible result wrapper for backend and model operations.

    QueryResult wraps the results from backend operations (records, create, update, delete, count)
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
    from clearskies.query.result import QueryResult

    # Records result
    result = QueryResult(
        data=[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
    )
    for record in result:
        print(record["name"])

    # Single record result
    result = QueryResult(
        data={"id": 1, "name": "Alice"},
    )

    # Delete result
    result = QueryResult(data=True)
    ```
    """
    data = Any(default=None)

    """
    Boolean indicating whether the operation was successful.

    Defaults to ``True``. Set to ``False`` when the operation failed.
    Use ``FailedQueryResult`` to create an error result.

    ```python
    from clearskies.query.result import QueryResult, FailedQueryResult

    # Success result
    success_result = QueryResult(
        data=[{"id": 1}],
        success=True,
    )

    # Error result
    error_result = FailedQueryResult(error="Database connection failed")
    print(error_result.success)  # False
    ```
    """
    success = Boolean(default=True)

    """
    Error information if the operation failed.

    Can be a string, dictionary, exception, or any other error representation.
    Typically set when ``success`` is ``False``.

    ```python
    from clearskies.query.result import FailedQueryResult

    result = FailedQueryResult(error={
        "message": "Record not found",
        "code": 404
    })
    print(result.error_msg)  # {"message": "Record not found", "code": 404}
    ```
    """
    error = Any(default=None)

    """
    Total count of records available (not just those returned in this result).

    This is typically populated from API response headers like ``x-total-count``.
    When set along with ``can_count=True``, allows the model to return cached count
    information without making additional API calls.

    ```python
    from clearskies.query.result import QueryResult

    # API returned 10 records but indicated 100 total exist
    result = QueryResult(
        data=[{"id": i} for i in range(10)],
        total_count=100,
        can_count=True,
    )
    print(result.get_count())  # 100 (from cache, not len(data))
    ```
    """
    total_count = IntegerOrNone(default=None)

    """
    Total number of pages available.

    This is typically populated from API response headers like ``x-total-pages``.
    Useful for building pagination UI or determining how many requests are needed
    to fetch all data.

    ```python
    from clearskies.query.result import QueryResult

    result = QueryResult(
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
    from clearskies.query.result import QueryResult

    # Result with count info from headers
    result = QueryResult(
        data=[{"id": 1}],
        total_count=50,
        can_count=True,
    )

    if result.can_count:
        print(f"Total: {result.get_count()}")  # Uses cached count
    ```
    """
    can_count = Boolean(default=False)

    """
    Pagination data for fetching the next page of results.

    This dictionary contains the parameters needed to request the next page.
    The format depends on the backend's pagination style (offset, cursor, etc.).

    ```python
    from clearskies.query.result import QueryResult

    # Offset-based pagination
    result = QueryResult(
        data=[{"id": i} for i in range(10)],
        next_page_data={"start": 10},
    )

    if result.has_more_pages():
        # Use next_page_data to fetch more results
        print(result.next_page_data)  # {"start": 10}

    # Cursor-based pagination
    result = QueryResult(
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
    from clearskies.query.result import QueryResult

    def fetch_records_lazily():
        for i in range(1000):
            yield {"id": i, "name": f"Record {i}"}

    result = QueryResult(
        generator=fetch_records_lazily,
    )

    for record in result.as_generator():
        print(record["name"])  # Records fetched one at a time
    ```
    """
    generator: CallableType[[], Generator[AnyType, None, None]] | None = Callable(default=None)  # type: ignore[assignment]

    """
    Optional async function for asynchronous data access.

    When provided, ``as_async()`` will call this function to get data asynchronously.
    This is useful for async backends or when data needs to be fetched on-demand.

    ```python
    from clearskies.query.result import QueryResult
    import asyncio

    async def fetch_data_async():
        await asyncio.sleep(0.1)  # Simulate async operation
        return [{"id": 1}, {"id": 2}]

    result = QueryResult(
        async_data=fetch_data_async,
    )

    # In async context:
    # data = await result.as_async()
    ```
    """
    async_data: CallableType[[], AnyType] | None = Callable(default=None)  # type: ignore[assignment]

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
        """Initialize QueryResult with provided configuration values."""
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
        raise TypeError("QueryResult data is not iterable")

    def __repr__(self) -> str:
        """Return string representation of QueryResult."""
        data_preview = self.data
        if isinstance(self.data, list) and len(self.data) > 3:
            data_preview = f"[{len(self.data)} items]"
        return (
            f"QueryResult("
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
