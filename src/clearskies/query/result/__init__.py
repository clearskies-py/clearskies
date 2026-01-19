"""Query result classes for backend operations."""

from clearskies.query.result.query_result import QueryResult
from clearskies.query.result.record_query_result import RecordQueryResult
from clearskies.query.result.records_query_result import RecordsQueryResult
from clearskies.query.result.count_query_result import CountQueryResult
from clearskies.query.result.success_query_result import SuccessQueryResult
from clearskies.query.result.failed_query_result import FailedQueryResult

__all__ = [
    "QueryResult",
    "RecordQueryResult",
    "RecordsQueryResult",
    "CountQueryResult",
    "SuccessQueryResult",
    "FailedQueryResult",
]
