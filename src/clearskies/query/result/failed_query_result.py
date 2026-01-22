"""FailedQueryResult - A QueryResult specialized for failed operations."""

from __future__ import annotations

from typing import Any as AnyType

from clearskies.query.result.query_result import QueryResult


class FailedQueryResult(QueryResult):
    """
    A QueryResult specialized for failed operations.

    This subclass provides a clearer API for operations that failed with an error.

    Example usage:

    ```python
    from clearskies.query.result import FailedQueryResult

    # Create a failed result
    result = FailedQueryResult(error="Database connection failed")

    print(result.success)  # False
    print(result.error_msg)  # "Database connection failed"

    # Check for failure using .success (not bool()):
    if not result.success:
        print("Operation failed!")
    ```

    Note: Due to descriptor implementation details, all QueryResult subclasses
    must return True from __bool__ to avoid recursion. Check .success instead.
    """

    _error_value: AnyType  # Store locally to avoid descriptor recursion

    def __init__(
        self,
        error: AnyType,
    ) -> None:
        """Initialize FailedQueryResult."""
        # Store locally first to avoid recursion
        self._error_value = error
        self.success = False
        self.error = error
        self.finalize_and_validate_configuration()

    @property
    def error_msg(self) -> AnyType:
        """Return the error value without triggering descriptor recursion."""
        return self._error_value

    def __bool__(self) -> bool:
        """Prevent recursion - use .success to check for failure."""
        return True

    def __repr__(self) -> str:
        """Return string representation of FailedQueryResult."""
        return f"FailedQueryResult(error={self._error_value!r})"
