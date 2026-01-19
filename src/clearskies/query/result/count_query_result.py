"""CountQueryResult - A QueryResult specialized for count() operations."""

from __future__ import annotations

from clearskies.query.result.query_result import QueryResult


class CountQueryResult(QueryResult):
    """
    A QueryResult specialized for count() operations.

    This subclass provides a clearer API for operations that return a count value.

    Example usage:

    ```python
    from clearskies.query.result import CountQueryResult

    # Create a count result
    result = CountQueryResult(count=42)

    print(result.count)  # 42
    print(int(result))  # 42
    print(bool(result))  # True (count > 0)

    # Zero count
    empty = CountQueryResult(count=0)
    print(bool(empty))  # False (count == 0)
    ```
    """

    _count_value: int  # Store locally to avoid descriptor recursion in __bool__

    def __init__(
        self,
        count: int,
    ) -> None:
        """
        Initialize CountQueryResult.

        Args:
            count: The count value returned by the query.
        """
        # Store locally first to avoid recursion in __bool__
        self._count_value = count
        # Set properties directly without calling super().__init__ to avoid decorator recursion
        self.data = count
        self.success = True
        self.error = None
        self.total_count = count
        self.total_pages = None
        self.can_count = True
        self.next_page_data = None
        self.generator = None
        self.async_data = None
        self.finalize_and_validate_configuration()

    @property
    def count(self) -> int:
        """Return the count value."""
        return self._count_value

    def __int__(self) -> int:
        """Allow conversion to int."""
        return self._count_value

    def __bool__(self) -> bool:
        """Return True if count > 0, False otherwise."""
        return self._count_value > 0

    def __repr__(self) -> str:
        """Return string representation of CountQueryResult."""
        return f"CountQueryResult(count={self._count_value})"
