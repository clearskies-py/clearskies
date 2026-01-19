"""SuccessQueryResult - A QueryResult specialized for success-only operations."""

from __future__ import annotations

from clearskies.query.result.query_result import QueryResult


class SuccessQueryResult(QueryResult):
    """
    A QueryResult specialized for delete() and other success-only operations.

    This subclass provides a clearer API for operations that simply indicate
    success without returning data. EmptyQueryResult is an alias for this class.

    Example usage:

    ```python
    from clearskies.query.result import SuccessQueryResult

    # Create a success result for delete operation
    result = SuccessQueryResult()

    print(result.success)  # True
    print(bool(result))  # True
    ```
    """

    def __init__(self) -> None:
        """Initialize SuccessQueryResult."""
        self.finalize_and_validate_configuration()

    def __bool__(self) -> bool:
        """Allow boolean check (always True for success)."""
        return True  # SuccessQueryResult is always truthy

    def __repr__(self) -> str:
        """Return string representation of SuccessQueryResult."""
        return "SuccessQueryResult(success=True)"
