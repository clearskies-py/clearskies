from __future__ import annotations

from typing import Any


class CallableResponse:
    """
    Return value for a Callable endpoint that needs to control the status code or headers of a single response.

    The `data` is handled exactly like any other return value of the callable: it is wrapped in the standard
    clearskies response (with models converted via `readable_column_names`) unless `return_standard_response`
    is `False`.  The `status_code` overrides the endpoint's `status_code` setting, and `headers` are added to
    the response:

    ```python
    import clearskies


    def create_widget(request_data):
        return clearskies.endpoints.CallableResponse(
            {"id": "123", "name": request_data["name"]},
            status_code=201,
            headers={"location": "/widgets/123"},
        )


    clearskies.contexts.WsgiRef(
        clearskies.endpoints.Callable(create_widget, request_methods=["POST"]),
    )()
    ```
    """

    def __init__(self, data: Any, status_code: int = 200, headers: dict[str, str] | None = None):
        if not isinstance(status_code, int):
            raise TypeError(
                f"CallableResponse requires an integer status_code, but I was given a '{status_code.__class__.__name__}'."
            )
        self.data = data
        self.status_code = status_code
        self.headers = headers or {}
