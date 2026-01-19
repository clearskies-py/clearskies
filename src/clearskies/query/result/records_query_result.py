"""RecordsQueryResult - A QueryResult specialized for records() operations."""

from __future__ import annotations

from typing import Any as AnyType
from typing import Callable as CallableType
from typing import Generator

from clearskies.query.result.query_result import QueryResult


class RecordsQueryResult(QueryResult):
    """
    A QueryResult specialized for records() operations.

    This subclass provides a clearer API for operations that return a list of records
    with optional pagination information.

    Example usage:

    ```python
    from clearskies.query.result import RecordsQueryResult

    # Create a records result
    result = RecordsQueryResult(
        records=[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
        total_count=100,
        total_pages=10,
        next_page_data={"start": 2},
    )

    # Iterate over records
    for record in result:
        print(record["name"])

    # Check pagination
    if result.has_more_pages():
        print(f"More pages available: {result.next_page_data}")
    ```
    """

    def __init__(
        self,
        records: list[dict[str, AnyType]] | None = None,
        total_count: int | None = None,
        total_pages: int | None = None,
        next_page_data: AnyType = None,
        generator: CallableType[[], Generator[AnyType, None, None]] | None = None,
        async_data: CallableType[[], AnyType] | None = None,
    ) -> None:
        """Initialize RecordsQueryResult."""
        self.data = records or []
        self.total_count = total_count
        self.total_pages = total_pages
        self.can_count = total_count is not None
        self.next_page_data = next_page_data
        self.generator = generator
        self.async_data = async_data
        self.finalize_and_validate_configuration()

    @property
    def records(self) -> list[dict[str, AnyType]]:
        """Return the list of records."""
        return self.data if isinstance(self.data, list) else []

    def __bool__(self) -> bool:
        """Prevent recursion - RecordsQueryResult is always truthy."""
        return True

    def __len__(self) -> int:
        """Return the number of records in this result."""
        return len(self.records)

    def __repr__(self) -> str:
        """Return string representation of RecordsQueryResult."""
        return (
            f"RecordsQueryResult("
            f"records=[{len(self.records)} items], "
            f"total_count={self.total_count}, "
            f"next_page={self.has_more_pages()})"
        )
