"""RecordQueryResult - A QueryResult specialized for single record operations."""

from __future__ import annotations

from typing import Any as AnyType

from clearskies.query.result.query_result import QueryResult


class RecordQueryResult(QueryResult):
    """
    A QueryResult specialized for create() and update() operations.

    This subclass provides a clearer API for operations that return a single record
    dictionary (as opposed to a list of records).

    Example usage:

    ```python
    from clearskies.query.result import RecordQueryResult

    # Create a single record result
    result = RecordQueryResult(
        record={"id": 1, "name": "Alice", "email": "alice@example.com"},
    )

    # Access the record directly
    print(result.record["name"])  # "Alice"

    # Access individual fields
    print(result.id)  # 1 (if id_column_name is "id")
    ```
    """

    # Store the record data in a private attribute to avoid descriptor recursion
    _record_data: dict[str, AnyType]

    def __init__(
        self,
        record: dict[str, AnyType] | None = None,
    ) -> None:
        """
        Initialize RecordQueryResult.

        Args:
            record: The record dictionary returned by the create/update operation.
        """
        # Store in private attribute first to avoid recursion in __bool__
        self._record_data = record or {}
        # Set properties directly without calling super().__init__ to avoid decorator recursion
        self.data = self._record_data
        self.success = True
        self.error = None
        self.total_count = None
        self.total_pages = None
        self.can_count = False
        self.next_page_data = None
        self.generator = None
        self.async_data = None
        self.finalize_and_validate_configuration()

    @property
    def record(self) -> dict[str, AnyType]:
        """Return the record dictionary."""
        # Use private attribute to avoid descriptor recursion
        return self._record_data

    def get(self, key: str, default: AnyType = None) -> AnyType:
        """Get a value from the record by key."""
        return self._record_data.get(key, default)

    def __getitem__(self, key: str) -> AnyType:
        """Allow dict-like access to record fields."""
        return self._record_data[key]

    def __contains__(self, key: str) -> bool:
        """Check if a key exists in the record."""
        return key in self._record_data

    def __bool__(self) -> bool:
        """RecordQueryResult is truthy if it has a non-empty record."""
        # Use private attribute to avoid descriptor recursion
        return bool(self._record_data)

    def __repr__(self) -> str:
        """Return string representation of RecordQueryResult."""
        return f"RecordQueryResult(record={self._record_data})"
