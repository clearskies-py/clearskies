"""Adapters for backends."""

from clearskies.backends.adapters.adapter import Adapter
from clearskies.backends.adapters.count_adapter import CountAdapter
from clearskies.backends.adapters.header_count_adapter import HeaderCountAdapter
from clearskies.backends.adapters.body_count_adapter import BodyCountAdapter
from clearskies.backends.adapters.response_adapter import ResponseAdapter
from clearskies.backends.adapters.url_adapter import UrlAdapter
from clearskies.backends.adapters.pagination_adapter import PaginationAdapter
from clearskies.backends.adapters.link_header_pagination_adapter import LinkHeaderPaginationAdapter
from clearskies.backends.adapters.parameter_pagination_adapter import ParameterPaginationAdapter
from clearskies.backends.adapters.hal_json_response_adapter import HalJsonResponseAdapter
from clearskies.backends.adapters.json_api_response_adapter import JsonApiResponseAdapter

__all__ = [
    "Adapter",
    "CountAdapter",
    "HeaderCountAdapter",
    "BodyCountAdapter",
    "ResponseAdapter",
    "UrlAdapter",
    "PaginationAdapter",
    "LinkHeaderPaginationAdapter",
    "ParameterPaginationAdapter",
    "HalJsonResponseAdapter",
    "JsonApiResponseAdapter",
]
