from __future__ import annotations

from typing import Any

from . import ResponseAdapter


class HalJsonResponseAdapter(ResponseAdapter):
    """
    Unwrap `HAL+JSON <https://stateless.group/hal_specification.html>`_ response envelopes for ``ApiBackend``.

    HAL (Hypertext Application Language) is a widely-adopted convention for embedding hypermedia
    controls in JSON APIs.  A typical HAL list response looks like this:

    ```json
    {
        "_links": {"self": {"href": "/articles"}},
        "_embedded": {
            "articles": [
                {
                    "id": 1,
                    "title": "Hello World",
                    "_links": {"self": {"href": "/articles/1"}}
                }
            ]
        }
    }
    ```

    Without an adapter, ``ApiBackend`` has no way to know that the real records are buried inside
    ``_embedded.articles``.  ``HalJsonResponseAdapter`` navigates that nesting automatically and
    delivers a clean list of plain dicts to the model's column-mapping layer:

    ```json
    [{"id": 1, "title": "Hello World"}]
    ```

    ## Supported envelope shapes

    The adapter handles a broad range of real-world payload shapes in priority order:

    1. **Idiomatic HAL** — ``_embedded`` wrapping a list or a named sub-resource.
    2. **Named list containers** — top-level keys such as ``"items"``, ``"results"``, ``"data"``
       (see :attr:`list_container_keys`).
    3. **Bare list** — a JSON array at the root is returned as-is.
    4. **Key→record map** — a dict whose non-metadata values are all dicts is treated as a named
       record collection; the key is injected as ``"key"`` into each record.
    5. **Recursive fallback** — any nested value that contains a list is unwrapped.

    For single-record extraction the adapter checks :attr:`record_container_keys` first, then
    ``_embedded``, and finally returns the entire response dict as a last resort (useful for APIs
    that return a bare object with no wrapper key).

    ## Normalisation

    :meth:`_normalize_record` removes keys listed in :attr:`metadata_keys` (``"_links"`` by
    default) and promotes ``_embedded`` sub-resources from each record to the top level.  Existing
    top-level keys are never overwritten by embedded content.

    Note that ``_links`` is only stripped from **individual record objects** inside the list, not
    from the top-level response envelope.  ``ApiBackend`` drives pagination from HTTP response
    headers (the ``Link`` header and ``X-Total-Count``), so the top-level ``_links`` body field is
    never needed by the framework.  If you subclass ``ApiBackend`` and override
    ``get_next_page_data_from_response`` to read ``_links`` from the JSON body, that data is
    still available on the raw ``response.json()`` call — the adapter does not touch it.

    ## Full working example

    Define a backend subclass that points at the upstream HAL service and attach the adapter,
    then wire it into a model and expose it through a list endpoint:

    ```python
    import clearskies


    class ArticleBackend(clearskies.backends.ApiBackend):
        def __init__(self):
            super().__init__(
                base_url="https://hal.example.com",
                response_adapter=clearskies.backends.adapters.HalJsonResponseAdapter(),
            )


    class Article(clearskies.Model):
        id_column_name = "id"
        backend = ArticleBackend()

        id = clearskies.columns.Integer()
        title = clearskies.columns.String()


    wsgi = clearskies.contexts.WsgiRef(
        clearskies.endpoints.List(
            model_class=Article,
            readable_column_names=["id", "title"],
            sortable_column_names=["id"],
            default_sort_column_name=None,
            default_limit=10,
        ),
        classes=[Article],
    )
    wsgi()
    ```

    Assuming ``https://hal.example.com/articles`` returns a HAL envelope, the endpoint unwraps
    it transparently:

    ```bash
    $ curl 'http://localhost:8080/' | jq
    {
        "status": "success",
        "error": "",
        "data": [
            {"id": 1, "title": "Hello"},
            {"id": 2, "title": "World"}
        ],
        "pagination": {"number_results": 2, "limit": 10, "next_page": {}},
        "input_errors": {}
    }
    ```

    ## Customising the adapter

    All lookup keys are defined as class attributes so that subclasses can extend or replace them
    without overriding any logic:

    ```python
    from clearskies.backends.adapters import HalJsonResponseAdapter


    class MyHalAdapter(HalJsonResponseAdapter):
        # Add "entries" as an additional list container key.
        list_container_keys = HalJsonResponseAdapter.list_container_keys + ("entries",)

        # Also strip "_meta" from each normalised record.
        metadata_keys = HalJsonResponseAdapter.metadata_keys + ("_meta",)
    ```

    ## Binding the adapter via DI

    You can register the adapter in the dependency injection container instead of setting it on
    the backend instance:

    ```python
    context = clearskies.contexts.WsgiRef(
        clearskies.endpoints.List(model_class=Article, ...),
        bindings={"response_adapter": HalJsonResponseAdapter()},
    )
    ```

    An adapter set directly on the backend always takes precedence over one registered via DI.
    """

    """
    Top-level dict keys that indicate the value is a list of records.

    The adapter checks these keys in order and recurses into the first match.  Extend this tuple
    in a subclass to support additional envelope conventions without overriding any logic:

    ```python
    from clearskies.backends.adapters import HalJsonResponseAdapter

    class MyAdapter(HalJsonResponseAdapter):
        list_container_keys = HalJsonResponseAdapter.list_container_keys + ("entries", "rows")
    ```
    """
    list_container_keys = ("items", "results", "records", "data", "content", "values", "paths")

    """
    Top-level dict keys that indicate the value is a single record.

    Checked in order inside :meth:`_find_record`.  The first key whose value is a dict is
    returned as the record.  Extend in a subclass to add custom key names:

    ```python
    from clearskies.backends.adapters import HalJsonResponseAdapter

    class MyAdapter(HalJsonResponseAdapter):
        record_container_keys = HalJsonResponseAdapter.record_container_keys + ("payload",)
    ```
    """
    record_container_keys = ("item", "result", "record", "data")

    """
    Keys that carry HAL metadata and should be stripped from normalised records.

    By default only ``"_links"`` is removed.  Override in a subclass to also strip ``"_meta"``,
    ``"_curies"``, or any other envelope-level key:

    ```python
    from clearskies.backends.adapters import HalJsonResponseAdapter

    class MyAdapter(HalJsonResponseAdapter):
        metadata_keys = ("_links", "_meta", "_curies")
    ```
    """
    metadata_keys = ("_links",)

    # Keys that are structurally part of HAL and are excluded from the key→record-map heuristic.
    # This prevents a response like {"_links": {"self": {...}}, "_embedded": {...}} from being
    # misidentified as a named record collection.
    _hal_structural_keys = frozenset(("_links", "_embedded", "_meta", "_curies", "_page"))

    def extract_records(self, response_data: Any) -> list[dict[str, Any]] | None:
        """Return a normalised list of records located anywhere inside the HAL payload.

        Returns ``None`` to hand control back to the built-in ``ApiBackend`` extraction logic when
        no list of dicts can be found.
        """
        records = self._find_records(response_data)
        if records is None:
            return None
        return [self._normalize_record(record) for record in records]

    def extract_record(self, response_data: Any) -> dict[str, Any] | None:
        """Return a single normalised record located anywhere inside the HAL payload.

        Returns ``None`` to hand control back to the built-in ``ApiBackend`` extraction logic when
        no suitable dict can be found.
        """
        record = self._find_record(response_data)
        if record is None:
            return None
        return self._normalize_record(record)

    def _find_records(self, response_data: Any) -> list[dict[str, Any]] | None:
        """Locate the list of raw record dicts inside *response_data*.

        Checks in order: bare list, ``_embedded``, :attr:`list_container_keys`, key→record-map
        heuristic (non-structural dict values that are all dicts), then a recursive depth-first
        scan of remaining values.  Returns ``None`` if no list of dicts is found.
        """
        if isinstance(response_data, list):
            if all(isinstance(item, dict) for item in response_data):
                return response_data
            return None

        if not isinstance(response_data, dict):
            return None

        # 1. Idiomatic HAL: _embedded → first list-valued entry.
        embedded = response_data.get("_embedded")
        if isinstance(embedded, dict):
            for value in embedded.values():
                found = self._find_records(value)
                if found is not None:
                    return found

        # 2. Named list containers (items, results, data, …).
        for key in self.list_container_keys:
            if key in response_data:
                found = self._find_records(response_data[key])
                if found is not None:
                    return found

        # 3. Key→record-map heuristic: every *non-structural* value is a dict.
        #    Structural HAL keys (_links, _embedded, …) are excluded so that a
        #    response like {"_links": {"self": {…}}, "_embedded": {…}} is NOT
        #    misidentified as a named record collection.
        non_structural = {k: v for k, v in response_data.items() if k not in self._hal_structural_keys}
        if non_structural and all(isinstance(v, dict) for v in non_structural.values()):
            dict_records: list[dict[str, Any]] = []
            for key, value in non_structural.items():
                record = {**value}
                record.setdefault("key", key)
                dict_records.append(record)
            return dict_records

        # 4. Recursive fallback: scan remaining values depth-first.
        for value in response_data.values():
            found = self._find_records(value)
            if found is not None:
                return found

        return None

    def _find_record(self, response_data: Any) -> dict[str, Any] | None:
        """Locate a single raw record dict inside *response_data*.

        Checks in order: first dict in a list, :attr:`record_container_keys`, ``_embedded``, and
        finally the entire response dict as a last resort for bare-object APIs.
        """
        if isinstance(response_data, list):
            for item in response_data:
                if isinstance(item, dict):
                    return item
            return None

        if not isinstance(response_data, dict):
            return None

        # Named record containers take priority.
        for key in self.record_container_keys:
            value = response_data.get(key)
            if isinstance(value, dict):
                return value

        # HAL _embedded single-record shape.
        embedded = response_data.get("_embedded")
        if isinstance(embedded, dict):
            for value in embedded.values():
                record = self._find_record(value)
                if record:
                    return record

        return response_data

    def _normalize_record(self, record: dict[str, Any]) -> dict[str, Any]:
        """Strip HAL metadata keys and promote ``_embedded`` sub-resources to the top level.

        Keys listed in :attr:`metadata_keys` (``"_links"`` by default) are removed.  Any keys
        found inside ``_embedded`` are merged in at the top level; existing top-level keys are
        not overwritten.
        """
        normalized = {key: value for key, value in record.items() if key not in self.metadata_keys}

        embedded = record.get("_embedded")
        if isinstance(embedded, dict):
            for key, value in embedded.items():
                if key not in normalized:
                    normalized[key] = value

        return normalized
