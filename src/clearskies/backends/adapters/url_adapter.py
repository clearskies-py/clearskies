"""URL routing adapter for ApiBackend."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from clearskies import configs, decorators
from clearskies.backends.adapters.adapter import Adapter
from clearskies.functional import routing

if TYPE_CHECKING:
    from clearskies import Model
    from clearskies.query import Query


class UrlAdapter(Adapter["UrlAdapter"]):
    """
    Pluggable URL routing strategy for ``ApiBackend``.

    Sits between the high-level CRUD methods (``create``, ``update``, ``delete``, ``records``)
    and the actual HTTP request.  Its sole responsibility is answering the *structural* question —
    **what URL should this request go to, and which data keys were consumed as routing parameters?**

    Every URL method returns a tuple of ``(url, used_routing_parameters)``.  The second element is a
    list of parameter names that were absorbed into the URL path.  These parameters are then removed from
    the request body before sending to the API, preventing them from being sent in both the URL path and
    the request body.

    ## Default behavior

    The default implementation generates standard REST-style URLs:

    - ``GET    /resource``         — via ``records_url``
    - ``POST   /resource``         — via ``create_url``
    - ``PATCH  /resource/{id}``    — via ``update_url``
    - ``DELETE /resource/{id}``    — via ``delete_url``

    It also supports URL parameter substitution using ``{param}`` or ``:param`` syntax in the ``base_url``.
    For instance, with a base URL of ``/api/v1/{tenant_id}``, query conditions like
    ``model.where("tenant_id=abc")`` will fill in the parameter automatically.

    ## Implementing a custom adapter

    Subclass ``UrlAdapter`` and override the methods you need.  Each method receives different
    arguments depending on the operation:

    ```python
    import clearskies


    class VersionedUrlAdapter(clearskies.backends.adapters.UrlAdapter):
        def records_url(self, query):
            name = query.model_class.destination_name()
            return (f"/api/v2/{name}", [])

        def create_url(self, data, model):
            return (f"/api/v2/{model.destination_name()}", [])

        def update_url(self, id, data, model):
            return (f"/api/v2/{model.destination_name()}/{id}", [])

        def delete_url(self, id, model):
            return (f"/api/v2/{model.destination_name()}/{id}", [])
    ```

    Attach it to an ``ApiBackend``:

    ```python
    backend = clearskies.backends.ApiBackend(
        base_url="https://api.example.com",
        url_adapter=VersionedUrlAdapter(),
    )
    ```

    ## Reporting consumed routing parameters

    If your URL absorbs parameters from the save data, return them in the second element of the tuple
    so they are stripped from the request body:

    ```python
    class TenantUrlAdapter(clearskies.backends.adapters.UrlAdapter):
        def create_url(self, data, model):
            tenant_id = data["tenant_id"]
            url = f"/api/v1/tenants/{tenant_id}/{model.destination_name()}"
            return (url, ["tenant_id"])
    ```

    Without reporting ``["tenant_id"]``, the ``tenant_id`` key would be sent in both the URL path
    and the JSON request body.
    """

    """
    Prepended to all generated URLs (e.g. ``"https://api.example.com/api/v1"``).
    Supports ``{param}`` and ``:param`` routing parameter syntax.
    """
    base_url = configs.String(default="")

    """
    Appended to all generated URLs (e.g. ``".json"``).
    """
    url_suffix = configs.String(default="")

    @decorators.parameters_to_properties
    def __init__(self, base_url: str = "", url_suffix: str = ""):
        """
        Initialize URL adapter.

        ``base_url`` is prepended to all generated URLs (e.g. ``"https://api.example.com/api/v1"``).
        It supports ``{param}`` and ``:param`` routing parameter syntax.

        ``url_suffix`` is appended to all generated URLs (e.g. ``".json"``).
        """
        self.finalize_and_validate_configuration()

    def finalize_url(
        self,
        url: str,
        available_routing_data: Mapping[str, str | int],
        operation: str,
    ) -> tuple[str, list[str]]:
        """
        Core URL finalization: prepend ``base_url``, append ``url_suffix``, and fill in routing parameters.

        Given a URL, this will build the full URL from ``base_url + url + url_suffix``, then scan for
        routing parameters (``{param}`` or ``:param`` syntax) and fill them in from ``available_routing_data``.
        Returns both the final URL and the list of parameter names that were consumed.

        For example, consider a base URL of ``/my/api/{record_id}/:other_id`` and then this is called as:

        ```python
        (url, used_routing_params) = adapter.finalize_url(
            "entries",
            {
                "record_id": "1-2-3-4",
                "other_id": "a-s-d-f",
                "more_things": "qwerty",
            },
            "records",
        )
        ```

        The returned url would be ``/my/api/1-2-3-4/a-s-d-f/entries``, and ``used_routing_params`` would
        be ``["record_id", "other_id"]``.  The ``more_things`` key was not consumed because it didn't
        match any routing parameter in the URL template.

        Raises a ``ValueError`` if a routing parameter in the URL template cannot be found in
        ``available_routing_data``, or if a routing parameter value is not a string or integer.
        """
        base = self.base_url.strip("/") + "/" if self.base_url.strip("/") else ""
        suffix = "/" + self.url_suffix.strip("/") if self.url_suffix.strip("/") else ""
        full_url = base + url + suffix

        routing_parameters = routing.extract_url_parameter_name_map(full_url)
        if not routing_parameters:
            return (full_url, [])

        parts = full_url.split("/")
        used_routing_parameters = []
        for parameter_name, index in routing_parameters.items():
            if parameter_name not in available_routing_data:
                a = "an" if operation == "update" else "a"
                raise ValueError(
                    f"Failed to generate URL for {a} {operation}. URL {full_url} has parameter "
                    f"'{parameter_name}' that I couldn't find in the request data."
                )
            value = available_routing_data[parameter_name]
            if not isinstance(value, (str, int)):
                parameter_type = value.__class__.__name__
                raise ValueError(
                    f"I was filling in a routing parameter named {parameter_name} but the value I was given has a type "
                    f"of {parameter_type}.  Routing parameters can only be strings or integers."
                )
            parts[index] = str(value)
            used_routing_parameters.append(parameter_name)

        return ("/".join(parts), used_routing_parameters)

    def records_url(self, query: Query) -> tuple[str, list[str]]:
        """
        Generate the URL for listing records (GET).

        Collects all equality conditions from the query and uses them as available routing data
        to fill in any URL template parameters.  For example, if the base URL contains
        ``{tenant_id}`` and the query has ``model.where("tenant_id=abc")``, the ``tenant_id``
        condition will be used to fill in the URL and will be reported as a used routing parameter.
        """
        available_routing_data = {}
        for condition in query.conditions:
            if condition.operator != "=":
                continue
            available_routing_data[condition.column_name] = condition.values[0]

        return self.finalize_url(
            query.model_class.destination_name(),
            available_routing_data,
            "records",
        )

    def create_url(self, data: dict[str, Any], model: Model) -> tuple[str, list[str]]:
        """
        Generate the URL for creating a record (POST).

        Uses the save data dictionary as available routing data to fill in URL template parameters.
        Any keys in ``data`` that match routing parameters in the URL will be consumed and reported
        in the returned ``used_routing_parameters`` list so they can be stripped from the request body.
        """
        return self.finalize_url(
            model.destination_name(),
            data,
            "create",
        )

    def update_url(self, id: int | str, data: dict[str, Any], model: Model) -> tuple[str, list[str]]:
        """
        Generate the URL for updating a record (PATCH).

        Merges the record ID, the model's existing raw data, and the new save data into a single
        routing data dictionary.  The save data takes precedence over the model's raw data, ensuring
        that any updated routing values are used in the URL.
        """
        available_routing_data = {"id": id, **model.get_raw_data(), **data}

        base = model.destination_name().strip("/") + "/" if model.destination_name() else ""
        return self.finalize_url(
            f"{base}{id}",
            available_routing_data,
            "update",
        )

    def delete_url(self, id: int | str, model: Model) -> tuple[str, list[str]]:
        """
        Generate the URL for deleting a record (DELETE).

        Uses the record ID and the model's existing raw data as available routing data to fill
        in any URL template parameters.
        """
        available_routing_data = {"id": id, **model.get_raw_data()}

        base = model.destination_name().strip("/") + "/" if model.destination_name() else ""
        return self.finalize_url(
            f"{base}{id}",
            available_routing_data,
            "delete",
        )
