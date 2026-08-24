from __future__ import annotations

from typing import Any

from . import ResponseAdapter


class JsonApiResponseAdapter(ResponseAdapter):
    """
    Unwrap strict `JSON:API <https://jsonapi.org>`_ response envelopes for ``ApiBackend``.

    Many public APIs follow the JSON:API specification, which wraps every response in a well-defined
    envelope.  A list response looks like this:

    ```json
    {
        "data": [
            {"id": "1", "type": "articles", "attributes": {"title": "Hello", "body": "World"}},
            {"id": "2", "type": "articles", "attributes": {"title": "Bye",   "body": "Now"}}
        ]
    }
    ```

    And a single-resource response like this:

    ```json
    {
        "data": {"id": "42", "type": "articles", "attributes": {"title": "Hello", "body": "World"}}
    }
    ```

    Without an adapter, ``ApiBackend`` sees the outer ``{"data": [...]}`` shell and tries to map it
    directly to your model columns — which never works.  ``JsonApiResponseAdapter`` peels that shell
    away and flattens each resource object so that clearskies sees a plain dictionary:

    ```json
    {"id": "1", "type": "articles", "title": "Hello", "body": "World"}
    ```

    ## Normalisation rules

    Each JSON:API resource object is transformed as follows:

    1. All fields inside ``attributes`` are promoted to the top level.
    2. The resource-level ``id`` and ``type`` are preserved and **always take precedence** over
       any field of the same name that may exist inside ``attributes``.
    3. ``relationships``, ``links``, and ``meta`` are **dropped** — they are not part of the
       flat column mapping layer.

    ## Full working example

    Define a backend subclass that points at the upstream JSON:API service and attach the adapter,
    then wire it into a model and expose it through a list endpoint:

    ```python
    import clearskies


    class ArticleBackend(clearskies.backends.ApiBackend):
        def __init__(self):
            super().__init__(
                base_url="https://jsonapi.example.com",
                response_adapter=clearskies.backends.adapters.JsonApiResponseAdapter(),
            )


    class Article(clearskies.Model):
        id_column_name = "id"
        backend = ArticleBackend()

        id = clearskies.columns.String()
        title = clearskies.columns.String()
        body = clearskies.columns.String()


    wsgi = clearskies.contexts.WsgiRef(
        clearskies.endpoints.List(
            model_class=Article,
            readable_column_names=["id", "title", "body"],
            sortable_column_names=["id"],
            default_sort_column_name=None,
            default_limit=10,
        ),
        classes=[Article],
    )
    wsgi()
    ```

    Assuming ``https://jsonapi.example.com/articles`` returns a JSON:API envelope, the endpoint
    unwraps it transparently:

    ```bash
    $ curl 'http://localhost:8080/' | jq
    {
        "status": "success",
        "error": "",
        "data": [
            {"id": "1", "title": "Hello", "body": "World"},
            {"id": "2", "title": "Bye",   "body": "Now"}
        ],
        "pagination": {"number_results": 2, "limit": 10, "next_page": {}},
        "input_errors": {}
    }
    ```

    ## Binding the adapter via DI

    You can also register the adapter in the dependency injection container rather than setting it
    on the backend instance directly.  The ``ApiBackend`` will pick it up automatically:

    ```python
    context = clearskies.contexts.WsgiRef(
        clearskies.endpoints.List(model_class=Article, ...),
        bindings={"response_adapter": JsonApiResponseAdapter()},
    )
    ```

    Note that an adapter set directly on the backend always wins over one registered via DI.
    """

    def extract_records(self, response_data: Any) -> list[dict[str, Any]] | None:
        """
        Return a flattened list of records from a JSON:API ``data`` array.

        Returns ``None`` for every other shape, handing control back to the built-in
        ``ApiBackend`` extraction logic.
        """
        if not isinstance(response_data, dict):
            return None

        data = response_data.get("data")
        if isinstance(data, list):
            return [self._normalize_record(item) for item in data]
        return None

    def extract_record(self, response_data: Any) -> dict[str, Any] | None:
        """
        Return a single flattened record from a JSON:API ``data`` object.

        Also handles bare resource objects (``"attributes"`` at the top level) as a convenience
        fallback for APIs that strip the outer envelope.  Returns ``None`` for every other shape.
        """
        if not isinstance(response_data, dict):
            return None

        data = response_data.get("data")
        if isinstance(data, dict):
            return self._normalize_record(data)

        # Convenience fallback: payload was already stripped or wrapped differently.
        if "attributes" in response_data:
            return self._normalize_record(response_data)
        return None

    def _normalize_record(self, data_block: dict[str, Any]) -> dict[str, Any]:
        """
        Flatten a single JSON:API resource object into a plain dict.

        ``attributes`` fields are spread to the top level first.  The resource-level ``id`` and
        ``type`` are then written on top so they always take precedence over any identically-named
        attribute — matching the JSON:API specification's intent that ``id`` is a resource
        identifier, not a mutable attribute.  ``relationships``, ``links``, and ``meta`` are
        intentionally excluded; their mapping is left to the model's column layer.
        """
        # Unpack attributes first so root-level id/type can safely overwrite.
        attributes = data_block.get("attributes", {})
        normalized: dict[str, Any] = dict(attributes) if isinstance(attributes, dict) else {}

        # Root resource identifiers always take precedence over same-named attributes.
        if "id" in data_block:
            normalized["id"] = data_block["id"]
        if "type" in data_block:
            normalized["type"] = data_block["type"]

        return normalized
