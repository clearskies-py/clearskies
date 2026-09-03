from __future__ import annotations

import urllib.parse
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from requests import Response as RequestsResponse

from clearskies import columns, configs, decorators
from clearskies.autodoc.schema import Integer as AutoDocInteger
from clearskies.autodoc.schema import Schema as AutoDocSchema
from clearskies.autodoc.schema import String as AutoDocString
from clearskies.backends.adapters import (
    CountAdapter,
    HeaderCountAdapter,
    LinkHeaderPaginationAdapter,
    PaginationAdapter,
    ResponseAdapter,
    UrlAdapter,
)
from clearskies.backends.backend import Backend
from clearskies.di import InjectableProperties, inject
from clearskies.exceptions import MissingDependency
from clearskies.functional import json as json_functional
from clearskies.functional import string
from clearskies.query.result import (
    CountQueryResult,
    RecordQueryResult,
    RecordsQueryResult,
    SuccessQueryResult,
)

if TYPE_CHECKING:
    from clearskies import Column, Model
    from clearskies.authentication import Authentication
    from clearskies.query import Query


class NotModelData(Exception):
    pass


class ApiBackend(Backend, InjectableProperties):
    """
    Fetch and store data from an API endpoint.

    The ApiBackend gives developers a way to quickly build SDKs to connect a clearskies applications
    to arbitrary API endpoints.  The backend has some built in flexibility to make it easy to connect it to
    **most** APIs, as well as behavioral hooks so that you can override small sections of the logic to accommodate
    APIs that don't work in the expected way.  This allows you to interact with APIs using the standard model
    methods, just like every other backend, and also means that you can attach such models to endpoints to
    quickly enable all kinds of pre-defined behaviors.

    ## Usage

    Configuring the API backend is pretty easy:

     1. Provide the `base_url` to the constructor, or extend it and set it in the `__init__` for the new backend.
     2. Provide a `clearskies.authentication.Authentication` object, assuming it isn't a public API.
     3. Match your model class name to the path of the API (or set `model.destination_name()` appropriately)
     4. Use the resulting model like you would any other model!

    It's important to understand how the Api Backend will map queries and saves to the API in question.  The rules
    are fairly simple:

      1. The API backend only supports searching with the equals operator (e.g. `models.where("column=value")`).
      2. To specify routing parameters, use the `{parameter_name}` or `:parameter_name` syntax in either the url
         or in the destination name of your model.  In order to query the model, you then **must** provide a value
         for any routing parameters, using a matching search condition: (e.g.
         `models.where("routing_parameter_name=value")`)
      3. Any search clauses that don't correspond to routing parameters will be translated into query parameters.
         So, if your destination_name is `https://example.com/:categoy_id/products` and you executed a
         model query: `models.where("category_id=10").where("on_sale=1")` then this would result in fetching
         a URL of `https://example.com/10/products?on_sale=1`
      4. When you specifically search on the id column for the model, the id will be appended to the end
         of the URL rather than as a query parameter.  So, with a destination name of `https://example.com/products`,
         querying for `models.find("id=10")` will result in fetching `https://example.com/products/10`.
      5. Delete and Update operations will similarly append the id to the URL, and also set the appropriate
         response method (e.g. `DELETE` or `PATCH` by default).
      6. When processing the response, the backend will attempt to automatically discover the results by looking
         for dictionaries that contain the expected column names (as determined from the model schema and the mapping
         rules).
      7. The backend will check for a response header called `link` and parse this to find pagination information
         so it can iterate through records.

    NOTE: The API backend doesn't support joins or group_by clauses.  This limitation, as well as the fact that it only
    supports seaching with the equals operator, isn't a limitation in the API backend itself, but simply reflects the behavior
    of most API endoints.  If you want to support an API that has more flexibility (for instance, perhaps it allows for more search
    operations than just `=`), then you can extend the appropritae methods, discussed below, to map a model query to an API request.

    Here's an example of how to use the API Backend to integrate with the Github API:

    ```python
    import clearskies


    class GithubPublicBackend(clearskies.backends.ApiBackend):
        def __init__(
            self,
            # This varies from endpoint to endpoint, so we want to be able to set it for each model
            pagination_parameter_name: str = "since",
        ):
            # these are fixed for all gitlab API parameters, so there's no need to make them setable
            # from the constructor
            self.base_url = "https://api.github.com"
            self.limit_parameter_name = "per_page"
            self.pagination_parameter_name = pagination_parameter_name
            self.finalize_and_validate_configuration()


    class UserRepo(clearskies.Model):
        # Corresponding API Docs: https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#list-repositories-for-a-user
        id_column_name = "full_name"
        backend = GithubPublicBackend(pagination_parameter_name="page")

        @classmethod
        def destination_name(cls) -> str:
            return "users/:login/repos"

        id = clearskies.columns.Integer()
        full_name = clearskies.columns.String()
        type = clearskies.columns.Select(["all", "owner", "member"])
        url = clearskies.columns.String()
        html_url = clearskies.columns.String()
        created_at = clearskies.columns.Datetime()
        updated_at = clearskies.columns.Datetime()

        # The API endpoint won't return "login" (e.g. username), so it may not seem like a column, but we need to search by it
        # because it's a URL parameter for this API endpoint.  Clearskies uses strict validation and won't let us search by
        # a column that doesn't exist in the model: therefore, we have to add the login column.
        login = clearskies.columns.String(is_searchable=True, is_readable=False)

        # The API endpoint let's us sort by `created`/`updated`.  Note that the names of the columns (based on the data returned
        # by the API endpoint) are `created_at`/`updated_at`.  As above, clearskies strictly validates data, so we need columns
        # named created/updated so that we can sort by them.  We can set some flags to (hopefully) avoid confusion
        updated = clearskies.columns.Datetime(
            is_searchable=False, is_readable=False, is_writeable=False
        )
        created = clearskies.columns.Datetime(
            is_searchable=False, is_readable=False, is_writeable=False
        )


    class User(clearskies.Model):
        # Corresponding API docs: https://docs.github.com/en/rest/users/users?apiVersion=2022-11-28#list-users

        # github has two columns that are both effecitvely id columns: id and login.
        # We use the login column for id_column_name because that is the column that gets
        # used in the API to fetch an individual record
        id_column_name = "login"
        backend = GithubPublicBackend()

        id = clearskies.columns.Integer()
        login = clearskies.columns.String()
        gravatar_id = clearskies.columns.String()
        avatar_url = clearskies.columns.String()
        html_url = clearskies.columns.String()
        repos_url = clearskies.columns.String()

        # We can hook up relationships between models just like we would if we were using an SQL-like
        # database.  The whole point of the backend system is that the model queries work regardless of
        # backend, so clearskies can issue API calls to fetch related records just like it would be able
        # to fetch children from a related database table.
        repos = clearskies.columns.HasMany(
            UserRepo,
            foreign_column_name="login",
            readable_child_columns=["id", "full_name", "html_url"],
        )


    def fetch_user(users: User, user_repos: UserRepo):
        # If we execute this models query:
        some_repos = (
            user_repos.where("login=cmancone")
            .sort_by("created", "desc")
            .where("type=owner")
            .pagination(page=2)
            .limit(5)
        )
        # the API backend will fetch this url:
        # https://api.github.com/users/cmancone/repos?type=owner&sort=created&direction=desc&per_page=5&page=2
        # and we can use the results like always
        repo_names = [repo.full_name for repo in some_repos]

        # For the below case, the backend will fetch this url:
        # https://api.github.com/users/cmancone
        # in addition, the readable column names on the callable endpoint includes "repos", which references our has_many
        # column.  This means that when converting the user model to JSON, it will also grab a page of repositories for that user.
        # To do that, it will fetch this URL:
        # https://api.github.com/users/cmancone/repos
        return users.find("login=cmancone")


    wsgi = clearskies.contexts.WsgiRef(
        clearskies.endpoints.Callable(
            fetch_user,
            model_class=User,
            readable_column_names=["id", "login", "html_url", "repos"],
        ),
        classes=[User, UserRepo],
    )

    if __name__ == "__main__":
        wsgi()
    ```

    The following example demonstrates how models using this backend can be used in other clearskies endpoints, just like any
    other model.  Note that the following example is re-using the above models and backend, I have just omitted them for the sake
    of brevity:

    ```python
    wsgi = clearskies.contexts.WsgiRef(
        clearskies.endpoints.List(
            model_class=User,
            readable_column_names=["id", "login", "html_url"],
            sortable_column_names=["id"],
            default_sort_column_name=None,
            default_limit=10,
        ),
        classes=[User],
    )

    if __name__ == "__main__":
        wsgi()
    ```

    And if you invoke it:

    ```bash
    $ curl 'http://localhost:8080' | jq
    {
        "status": "success",
        "error": "",
        "data": [
            {
                "id": 1,
                "login": "mojombo",
                "html_url": "https://github.com/mojombo"
            },
            {
                "id": 2,
                "login": "defunkt",
                "html_url": "https://github.com/defunkt"
            },
            {
                "id": 3,
                "login": "pjhyett",
                "html_url": "https://github.com/pjhyett"
            },
            {
                "id": 4,
                "login": "wycats",
                "html_url": "https://github.com/wycats"
            },
            {
                "id": 5,
                "login": "ezmobius",
                "html_url": "https://github.com/ezmobius"
            },
            {
                "id": 6,
                "login": "ivey",
                "html_url": "https://github.com/ivey"
            },
            {
                "id": 7,
                "login": "evanphx",
                "html_url": "https://github.com/evanphx"
            },
            {
                "id": 17,
                "login": "vanpelt",
                "html_url": "https://github.com/vanpelt"
            },
            {
                "id": 18,
                "login": "wayneeseguin",
                "html_url": "https://github.com/wayneeseguin"
            },
            {
                "id": 19,
                "login": "brynary",
                "html_url": "https://github.com/brynary"
            }
        ],
        "pagination": {
            "number_results": null,
            "limit": 10,
            "next_page": {
                "since": "19"
            }
        },
        "input_errors": {}
    }
    ```

    In essence, we now have an endpoint that lists results but, instead of pulling its data from a database, it
    makes API calls.  It also tracks pagination as expected, so you can use the data in `pagination.next_page` to
    fetch the next set of results, just as you would if this were backed by a database, e.g.:

    ```bash
    $ curl http://localhost:8080?since=19
    ```

    ## Mapping from Queries to API calls

    The process of mapping a model query into an API request involves a few different methods which can be
    overwritten to fully control the process.  This is necessary in cases where an API behaves differently
    than expected by the API backend.  This table outlines the method involved and how they are used:

    | Method                           | Description                                                                                           |
    |----------------------------------|-------------------------------------------------------------------------------------------------------|
    | records_url                      | Return the absolute URL to fetch, as well as any columns that were used to fill in routing parameters |
    | records_method                   | Reurn the HTTP request method to use for the API call                                                 |
    | conditions_to_request_parameters | Translate the query conditions into URL fragments, query parameters, or JSON body parameters          |
    | pagination_to_request_parameters | Translate the pagination data into URL fragments, query parameters, or JSON body parameters           |
    | sorts_to_request_parameters      | Translate the sort directive(s) into URL fragments, query parameters, or JSON body parameters         |
    | map_records_response             | Take the response from the API and return a list of dictionaries with the resulting records           |

    In short, the details of the query are stored in a clearskies.query.Query object which is passed around to these
    various methods.  They use that information to adjust the URL, add query parameters, or add parameters into the
    JSON body.  The API Backend will then execute an API call with those final details, and use the map_record_response
    method to pull the returned records out of the response from the API endpoint.

    """

    """
    Whether this backend supports count operations via ``len(model)`` and ``bool(model)``.

    When ``can_count`` is ``True``, calling ``len()`` or ``bool()`` on a model will issue a lightweight
    ``HEAD`` request to the records URL and extract the count from response headers (e.g.
    ``X-Total-Count``) via the ``count_adapter``.  A ``HEAD`` request returns only headers — no
    response body — so this is much cheaper than fetching all records.

    Additionally, count information is always extracted from response headers when fetching records
    via ``records()``, so after iterating over a model the count is cached and available without
    an additional request.

    When ``can_count`` is ``False`` (the default), ``len()`` and ``bool()`` on models will raise
    ``NotImplementedError``, and endpoints won't include ``number_results`` in the pagination response.

    ```python
    backend = clearskies.backends.ApiBackend(
        base_url="https://api.example.com",
        can_count=True,
    )
    ```
    """
    can_count = configs.Boolean(default=False)

    """
    The Base URL for the requests - will be prepended to the destination_name() from the model.

    Note: this is treated as a 'folder' path: if set, it becomes the URL prefix and is followed with a '/'
    """
    base_url = configs.String(default="")

    """
    A suffix to append to the end of the URL.

    Note: this is treated as a 'folder' path: if set, it becomes the URL suffix and is prefixed with a '/'
    """
    url_suffix = configs.String(default="")

    """
    An instance of clearskies.authentication.Authentication that handles authentication to the API.

    The following example is a modification of the Github Backends used above that shows how to setup authentication.
    Github, like many APIs, uses an API key attached to the request via the authorization header.  The SecretBearer
    authentication class in clearskies is designed for this common use case, and pulls the secret key out of either
    an environment variable or the secret manager (I use the former in this case, because it's hard to have a
    self-contained example with a secret manager).  Of course, any authentication method can be attached to your
    API backend - SecretBearer authentication is used here simply because it's a common approach.

    Note that, when used in conjunction with a secret manager, the API Backend and the SecretBearer class will work
    together to check for a new secret in the event of an authentication failure from the API endpoint (specifically,
    a 401 error).  This allows you to automate credential rotation: create a new API key, put it in the secret manager,
    and then revoke the old API key.  The next time an API call is made, the SecretBearer will provide the old key from
    it's cache and the request will fail.  The API backend will detect this and try the request again, but this time
    will tell the SecretBearer class to refresh it's cache with a fresh copy of the key from the secrets manager.
    Therefore, as long as you put the new key in your secret manager **before** disabling the old key, this second
    request will succeed and the service will continue to operate successfully with only a slight delay in response time
    caused by refreshing the cache.

    ```python
    import clearskies

    class GithubBackend(clearskies.backends.ApiBackend):
        def __init__(
            self,
            pagination_parameter_name: str = "page",
            authentication: clearskies.authentication.Authentication | None = None,
        ):
            self.base_url = "https://api.github.com"
            self.limit_parameter_name = "per_page"
            self.pagination_parameter_name = pagination_parameter_name
            self.authentication = clearskies.authentication.SecretBearer(
                environment_key="GITHUB_API_KEY",
                header_prefix="Bearer ", # Because github expects a header of 'Authorization: Bearer API_KEY'
            )
            self.finalize_and_validate_configuration()

    class Repo(clearskies.Model):
        id_column_name = "login"
        backend = GithubBackend()

        @classmethod
        def destination_name(cls):
            return "/user/repos"

        id = clearskies.columns.Integer()
        name = clearskies.columns.String()
        full_name = clearskies.columns.String()
        html_url = clearskies.columns.String()
        visibility = clearskies.columns.Select(["all", "public", "private"])

    wsgi = clearskies.contexts.WsgiRef(
        clearskies.endpoints.List(
            model_class=Repo,
            readable_column_names=["id", "name", "full_name", "html_url"],
            sortable_column_names=["full_name"],
            default_sort_column_name="full_name",
            default_limit=10,
            where=["visibility=private"],
        ),
        classes=[Repo],
    )

    if __name__ == "__main__":
        wsgi()

    ```
    """
    authentication = configs.Authentication(default=None)

    """
    A dictionary of headers to attach to all outgoing API requests
    """
    headers = configs.StringDict(default={})

    """
    A dictionary of headers to attach to record fetch requests (GET). If not set, falls back to headers.
    """
    record_headers = configs.StringDict(default=None)

    """
    A dictionary of headers to attach to create requests (POST). If not set, falls back to headers.
    """
    create_headers = configs.StringDict(default=None)

    """
    A dictionary of headers to attach to update requests (PATCH/PUT). If not set, falls back to headers.
    """
    update_headers = configs.StringDict(default=None)

    """
    A dictionary of headers to attach to delete requests (DELETE). If not set, falls back to headers.
    """
    delete_headers = configs.StringDict(default=None)

    """
    A dictionary of headers to attach to count requests. If not set, falls back to headers.
    """
    count_headers = configs.StringDict(default=None)

    """
    The casing used in the model (snake_case, camelCase, TitleCase)

    This is used in conjunction with api_casing to tell the processing layer when you and the API are using
    different casing standards.  The API backend will then automatically covnert the casing style of the API
    to match your model.  This can be helpful when you have a standard naming convention in your own code which
    some external API doesn't follow, that way you can at least standardize things in your code.  In the following
    example, these parameters are used to convert from the snake_casing native to the Github API into the
    TitleCasing used in the model class:

    ```python
    import clearskies

    class User(clearskies.Model):
        id_column_name = "login"
        backend = clearskies.backends.ApiBackend(
            base_url="https://api.github.com",
            limit_parameter_name="per_page",
            pagination_parameter_name="since",
            model_casing="TitleCase",
            api_casing="snake_case",
        )

        Id = clearskies.columns.Integer()
        Login = clearskies.columns.String()
        GravatarId = clearskies.columns.String()
        AvatarUrl = clearskies.columns.String()
        HtmlUrl = clearskies.columns.String()
        ReposUrl = clearskies.columns.String()

    wsgi = clearskies.contexts.WsgiRef(
        clearskies.endpoints.List(
            model_class=User,
            readable_column_names=["Login", "AvatarUrl", "HtmlUrl", "ReposUrl"],
            sortable_column_names=["Id"],
            default_sort_column_name=None,
            default_limit=2,
            internal_casing="TitleCase",
            external_casing="TitleCase",
        ),
        classes=[User],
    )

    if __name__ == "__main__":
        wsgi()
    ```

    and when executed:

    ```bash
    $ curl http://localhost:8080 | jq
    {
        "Status": "Success",
        "Error": "",
        "Data": [
            {
                "Login": "mojombo",
                "AvatarUrl": "https://avatars.githubusercontent.com/u/1?v=4",
                "HtmlUrl": "https://github.com/mojombo",
                "ReposUrl": "https://api.github.com/users/mojombo/repos"
            },
            {
                "Login": "defunkt",
                "AvatarUrl": "https://avatars.githubusercontent.com/u/2?v=4",
                "HtmlUrl": "https://github.com/defunkt",
                "ReposUrl": "https://api.github.com/users/defunkt/repos"
            }
        ],
        "Pagination": {
            "NumberResults": null,
            "Limit": 2,
            "NextPage": {
                "Since": "2"
            }
        },
        "InputErrors": {}
    }
    ```
    """
    model_casing = configs.Select(["snake_case", "camelCase", "TitleCase"], default="snake_case")

    """
    The casing used by the API response (snake_case, camelCase, TitleCase)

    See model_casing for details and usage.
    """
    api_casing = configs.Select(["snake_case", "camelCase", "TitleCase"], default="snake_case")

    """
    A mapping from the data keys returned by the API to the data keys expected in the model

    This comes into play when you want your model columns to use different names than what is returned by the
    API itself.  Provide a dictionary where the key is the name of a piece of data from the API, and the value
    is the name of the column in the model.  The API Backend will use this to match the API data to your model.
    In the example below, `html_url` from the API has been mapped to `profile_url` in the model:

    ```python
    import clearskies

    class User(clearskies.Model):
        id_column_name = "login"
        backend = clearskies.backends.ApiBackend(
            base_url="https://api.github.com",
            limit_parameter_name="per_page",
            pagination_parameter_name="since",
            api_to_model_map={"html_url": "profile_url"},
        )

        id = clearskies.columns.Integer()
        login = clearskies.columns.String()
        profile_url = clearskies.columns.String()

    wsgi = clearskies.contexts.WsgiRef(
        clearskies.endpoints.List(
            model_class=User,
            readable_column_names=["login", "profile_url"],
            sortable_column_names=["id"],
            default_sort_column_name=None,
            default_limit=2,
        ),
        classes=[User],
    )

    if __name__ == "__main__":
        wsgi()
    ```

    And if you invoke it:

    ```bash
    $ curl http://localhost:8080 | jq
    {
        "status": "success",
        "error": "",
        "data": [
            {
                "login": "mojombo",
                "profile_url": "https://github.com/mojombo"
            },
            {
                "login": "defunkt",
                "profile_url": "https://github.com/defunkt"
            }
        ],
        "pagination": {
            "number_results": null,
            "limit": 2,
            "next_page": {
                "since": "2"
            }
        },
        "input_errors": {}
    }
    ```
    """
    api_to_model_map = configs.AnyDict(default={})

    """
    A :class:`~clearskies.backends.ResponseAdapter` that handles extracting records and single
    records from the raw API response **before** the model-mapping pipeline runs.

    The adapter answers the structural question — *where is the data inside the envelope?* —
    while ``api_to_model_map`` and ``map_to_model`` continue to answer the field-level question
    (*what are the fields called?*) as before.

    Provide a :class:`~clearskies.backends.ResponseAdapter` subclass for full control, or a
    plain callable ``(response_data: Any) -> list | dict | None`` for simple unwrapping::

        # Full adapter — different logic per operation:
        backend = clearskies.backends.ApiBackend(
            base_url="https://api.example.com",
            response_adapter=MyHalJsonResponseAdapter(),
        )

        # Callable — same extractor for both list and single-record responses:
        backend = clearskies.backends.ApiBackend(
            base_url="https://api.example.com",
            response_adapter=lambda data: data.get("items"),
        )

    Return ``None`` from either the adapter method or the callable to fall through to the
    built-in ``ApiBackend`` extraction logic.

    If not provided, clearskies checks DI for a dependency named
    ``response_adapter`` and uses it when available.
    """
    response_adapter = configs.ResponseAdapter(default=None)

    """
    Dependency name used to lazily resolve a response adapter from DI when
    ``response_adapter`` is not explicitly configured.
    """
    response_adapter_dependency_name = configs.String(default="response_adapter")

    """
    Pluggable URL routing adapter for controlling how URLs are generated for API requests.

    By default, the backend generates standard REST-style URLs using the model's destination name
    (e.g. ``/users``, ``/users/123``), combined with the ``base_url`` and ``url_suffix`` settings.
    You can override this behavior by providing a :class:`~clearskies.backends.adapters.UrlAdapter`
    subclass for full control, or a plain callable for simple cases.

    When providing a callable, it will be called with different arguments depending on the operation
    (see the individual URL methods for details).  The callable can return either:

    1. A plain URL string — in this case, no routing parameters are reported as consumed, so all
       data keys remain in the request body.
    2. A tuple of ``(url, used_routing_parameters)`` — the second element is a list of parameter
       names that were absorbed into the URL.  These parameters will be removed from the request
       body before sending to the API, preventing them from being sent in both the URL path and
       the request body.

    This matters because clearskies uses the ``used_routing_parameters`` list to strip routing data
    out of the request body.  For example, if your URL template is ``/tenants/{tenant_id}/users``
    and the save data contains ``{"tenant_id": "abc", "name": "Jane"}``, the routing parameter
    ``tenant_id`` will be filled into the URL and then removed from the request body so only
    ``{"name": "Jane"}`` is sent.

    Provide a :class:`~clearskies.backends.adapters.UrlAdapter` subclass for full control, or a
    plain callable for simple URL generation::

        # Full adapter — override individual URL methods:
        class VersionedUrlAdapter(clearskies.backends.adapters.UrlAdapter):
            def records_url(self, query):
                return (f"/api/v2/{query.model_class.destination_name()}", [])

            def create_url(self, data, model):
                return (f"/api/v2/{model.destination_name()}", [])

        backend = clearskies.backends.ApiBackend(
            base_url="https://api.example.com",
            url_adapter=VersionedUrlAdapter(),
        )

        # Callable — return just a URL string (simple case, no routing params consumed):
        backend = clearskies.backends.ApiBackend(
            base_url="https://api.example.com",
            url_adapter=lambda data, model: f"/api/v2/{model.destination_name()}",
        )

        # Callable — return a tuple to report consumed routing parameters:
        backend = clearskies.backends.ApiBackend(
            base_url="https://api.example.com",
            url_adapter=lambda data, model: (
                f"/api/v2/tenants/{data['tenant_id']}/users",
                ["tenant_id"],
            ),
        )
    """
    url_adapter = configs.AdapterOrCallable[UrlAdapter](adapter_type="UrlAdapter", default=None)

    """
    Dependency name used to lazily resolve a URL adapter from DI when
    ``url_adapter`` is not explicitly configured.
    """
    url_adapter_dependency_name = configs.String(default="url_adapter")

    """
    Pluggable pagination adapter for controlling how next-page data is extracted from API responses.

    Responsible for answering one question: **how do I fetch the next page of records?**  For total
    count extraction, see ``count_adapter``.

    clearskies ships with two built-in implementations:

    - :class:`~clearskies.backends.adapters.LinkHeaderPaginationAdapter` — parses RFC 5988 ``Link``
      headers with ``rel="next"`` (the **default**)
    - :class:`~clearskies.backends.adapters.ParameterPaginationAdapter` — reads the next page value
      from a response header (e.g. ``X-Next-Page``) or response body field (e.g. ``next_page``)

    You can also provide a custom :class:`~clearskies.backends.adapters.PaginationAdapter` subclass
    or a plain callable.

    Use the default Link header adapter (this is what happens when no ``pagination_adapter`` is set)::

        backend = clearskies.backends.ApiBackend(
            base_url="https://api.example.com",
            pagination_adapter=clearskies.backends.adapters.LinkHeaderPaginationAdapter(
                pagination_parameter_name="page",
            ),
        )

    Use the parameter adapter to read next-page from a response header::

        backend = clearskies.backends.ApiBackend(
            base_url="https://api.example.com",
            pagination_adapter=clearskies.backends.adapters.ParameterPaginationAdapter(
                pagination_parameter_name="page",
                next_page_header="X-Next-Page",
            ),
        )

    Or from the response body::

        backend = clearskies.backends.ApiBackend(
            base_url="https://api.example.com",
            pagination_adapter=clearskies.backends.adapters.ParameterPaginationAdapter(
                pagination_parameter_name="page",
                next_page_body_key="next_page",
            ),
        )

    Write a custom adapter for cursor-based pagination::

        class CursorPaginationAdapter(clearskies.backends.adapters.PaginationAdapter):
            def extract_next_page_data(self, response, query):
                data = response.json()
                if cursor := data.get("meta", {}).get("next_cursor"):
                    return {"cursor": cursor}
                return {}

        backend = clearskies.backends.ApiBackend(
            base_url="https://api.example.com",
            pagination_adapter=CursorPaginationAdapter(),
        )

    Or use a callable for simple cases::

        backend = clearskies.backends.ApiBackend(
            base_url="https://api.example.com",
            pagination_adapter=lambda response, query: (
                {"page": response.json()["next_page"]}
                if response.json().get("next_page")
                else {}
            ),
        )
    """
    pagination_adapter = configs.AdapterOrCallable[PaginationAdapter](adapter_type="PaginationAdapter", default=None)

    """
    Dependency name used to lazily resolve a pagination adapter from DI when
    ``pagination_adapter`` is not explicitly configured.
    """
    pagination_adapter_dependency_name = configs.String(default="pagination_adapter")

    """
    Pluggable count extraction adapter for controlling how total record counts are extracted from API responses.

    clearskies ships with two built-in implementations:

    - :class:`~clearskies.backends.adapters.HeaderCountAdapter` — reads ``X-Total-Count``,
      ``X-Total``, and ``X-Total-Pages`` response headers (the **default**)
    - :class:`~clearskies.backends.adapters.BodyCountAdapter` — navigates a dot-notation path
      in the response body (e.g. ``"meta.pagination.total"``)

    You can also provide a custom :class:`~clearskies.backends.adapters.CountAdapter` subclass
    or a plain callable.

    Use the default header adapter (this is what happens when no ``count_adapter`` is set)::

        backend = clearskies.backends.ApiBackend(
            base_url="https://api.example.com",
            count_adapter=clearskies.backends.adapters.HeaderCountAdapter(),
        )

    Use the body adapter for APIs that return counts in the response body::

        backend = clearskies.backends.ApiBackend(
            base_url="https://api.example.com",
            count_adapter=clearskies.backends.adapters.BodyCountAdapter(
                count_path="meta.pagination.total",
                pages_path="meta.pagination.pages",
            ),
        )

    Or use a callable that receives ``(response_headers, response_data)`` and returns
    ``(total_count, total_pages)``::

        backend = clearskies.backends.ApiBackend(
            base_url="https://api.example.com",
            count_adapter=lambda headers, data: (
                int(headers["X-My-Total"]) if headers and "X-My-Total" in headers else None,
                None,
            ),
        )
    """
    count_adapter = configs.AdapterOrCallable[CountAdapter](adapter_type="CountAdapter", default=None)

    """
    Dependency name used to lazily resolve a count adapter from DI when
    ``count_adapter`` is not explicitly configured.
    """
    count_adapter_dependency_name = configs.String(default="count_adapter")

    """
    The name of the pagination parameter
    """
    pagination_parameter_name = configs.String(default="start")

    """
    The expected 'type' of the pagination parameter: must be either 'int' or 'str'

    Note: this is set as a literal string, not as a type.
    """
    pagination_parameter_type = configs.Select(["int", "str"], default="str")

    """
    The name of the parameter that sets the number of records per page (if empty, setting the page size will not be allowed)
    """
    limit_parameter_name = configs.String(default="limit")

    """
    The requests instance.
    """
    requests = inject.Requests()

    """
    The dependency injection container (so we can pass it along to the Authentication object)
    """
    di = inject.Di()

    _auth_injected = False
    _response_to_model_map: dict[str, str] | None = None
    _resolved_response_adapter: ResponseAdapter | Callable | None = None

    @decorators.parameters_to_properties
    def __init__(
        self,
        base_url: str,
        authentication: Authentication | None = None,
        headers: dict[str, str] = {},
        record_headers: dict[str, str] | None = None,
        create_headers: dict[str, str] | None = None,
        update_headers: dict[str, str] | None = None,
        delete_headers: dict[str, str] | None = None,
        count_headers: dict[str, str] | None = None,
        model_casing: str = "snake_case",
        api_casing: str = "snake_case",
        api_to_model_map: dict[str, str | list[str]] = {},
        pagination_parameter_name: str = "start",
        pagination_parameter_type: str = "str",
        limit_parameter_name: str = "limit",
        can_create: bool | None = True,
        can_update: bool | None = True,
        can_delete: bool | None = True,
        can_query: bool | None = True,
        can_count: bool | None = False,
        response_adapter: ResponseAdapter | Callable | None = None,
        response_adapter_dependency_name: str = "response_adapter",
        url_adapter: UrlAdapter | Callable | None = None,
        url_adapter_dependency_name: str = "url_adapter",
        pagination_adapter: PaginationAdapter | Callable | None = None,
        pagination_adapter_dependency_name: str = "pagination_adapter",
        count_adapter: CountAdapter | Callable | None = None,
        count_adapter_dependency_name: str = "count_adapter",
        url_suffix: str = "",
    ):
        self.finalize_and_validate_configuration()

    @property
    def url_adapter_instance(self) -> UrlAdapter | Callable[..., Any]:
        """
        Lazy-resolve UrlAdapter from config param, DI, or default.

        Resolution order:
        1. Direct param (self.url_adapter)
        2. DI binding (via url_adapter_dependency_name)
        3. Default UrlAdapter (with base_url, url_suffix)

        Note: Checks on every access for consistency with get_response_adapter pattern.
        If url_adapter config is mutated after first use, the new value will be used.
        """
        # Always check direct param first (it may have changed)
        if self.url_adapter is not None:
            return self.url_adapter

        # Check cache
        if hasattr(self, "_url_adapter_instance_cached"):
            return self._url_adapter_instance_cached

        # Resolve from DI or create default
        try:
            self._url_adapter_instance_cached: UrlAdapter = self.di.build(self.url_adapter_dependency_name)
        except MissingDependency:
            self._url_adapter_instance_cached = UrlAdapter(
                base_url=self.base_url,
                url_suffix=self.url_suffix,
            )
        return self._url_adapter_instance_cached

    @property
    def pagination_adapter_instance(self) -> PaginationAdapter | Callable[..., Any]:
        """
        Lazy-resolve PaginationAdapter from config param, DI, or default.

        Resolution order:
        1. Direct param (self.pagination_adapter)
        2. DI binding (via pagination_adapter_dependency_name)
        3. Default PaginationAdapter (with pagination_parameter_name)

        Note: Checks on every access for consistency with get_response_adapter pattern.
        If pagination_adapter config is mutated after first use, the new value will be used.
        """
        # Always check direct param first (it may have changed)
        if self.pagination_adapter is not None:
            return self.pagination_adapter

        # Check cache
        if hasattr(self, "_pagination_adapter_instance_cached"):
            return self._pagination_adapter_instance_cached

        # Resolve from DI or create default
        try:
            self._pagination_adapter_instance_cached: PaginationAdapter = self.di.build(
                self.pagination_adapter_dependency_name
            )
        except MissingDependency:
            self._pagination_adapter_instance_cached = LinkHeaderPaginationAdapter(
                pagination_parameter_name=self.pagination_parameter_name,
            )
        return self._pagination_adapter_instance_cached

    @property
    def count_adapter_instance(self) -> CountAdapter | Callable[..., Any]:
        """
        Lazy-resolve CountAdapter from config param, DI, or default.

        Resolution order:
        1. Direct param (self.count_adapter)
        2. DI binding (via count_adapter_dependency_name)
        3. Default CountAdapter

        Note: Checks on every access for consistency with get_response_adapter pattern.
        If count_adapter config is mutated after first use, the new value will be used.
        """
        # Always check direct param first (it may have changed)
        if self.count_adapter is not None:
            return self.count_adapter

        # Check cache
        if hasattr(self, "_count_adapter_instance_cached"):
            return self._count_adapter_instance_cached

        # Resolve from DI or create default
        try:
            self._count_adapter_instance_cached: CountAdapter = self.di.build(self.count_adapter_dependency_name)
        except MissingDependency:
            self._count_adapter_instance_cached = HeaderCountAdapter()
        return self._count_adapter_instance_cached

    def finalize_url(
        self, url: str, available_routing_data: dict[str, str | int], operation: str
    ) -> tuple[str, list[str]]:
        """
        Delegate to URL adapter for finalization.

        Given a URL, this will append the base URL, fill in any routing data, and also return any used routing parameters.

        For example, consider a base URL of `/my/api/{record_id}/:other_id` and then this is called as so:

        ```python
        (url, used_routing_parameters) = api_backend.finalize_url(
            "entries",
            {
                "record_id": "1-2-3-4",
                "other_id": "a-s-d-f",
                "more_things": "qwerty",
            },
        )
        ```

        The returned url would be `/my/api/1-2-3-4/a-s-d-f/entries`, and used_routing_parameters would be ["record_id", "other_id"].
        The latter is returned so you can understand what parameters were absorbed into the URL.  Often, when some piece of data
        becomes a routing parameter, it needs to be ignored in the rest of the request.  `used_routing_parameters` helps with that.
        """
        url_adapter = self.url_adapter_instance
        if isinstance(url_adapter, UrlAdapter):
            return url_adapter.finalize_url(url, available_routing_data, operation)
        # Callable url_adapters don't participate in finalize_url — they replace
        # the higher-level methods (create_url, records_url, etc.) instead.
        # Fall back to a default UrlAdapter for the core URL-template logic.
        return UrlAdapter(
            base_url=self.base_url,
            url_suffix=self.url_suffix,
        ).finalize_url(url, available_routing_data, operation)

    def finalize_url_from_data(self, url: str, data: dict[str, Any], operation: str) -> tuple[str, list[str]]:
        """
        Create the final URL using a data dictionary to fill in any URL parameters.

        See finalize_url for more details about the return value.
        """
        return self.finalize_url(url, data, operation)

    def finalize_url_from_query(self, query: Query, operation: str) -> tuple[str, list[str]]:
        """
        Create the URL using a query to fill in any URL parameters.

        See finalize_url for more details about the return value.
        """
        available_routing_data: dict[str, str | int] = {}
        for condition in query.conditions:
            if condition.operator != "=":
                continue
            available_routing_data[condition.column_name] = condition.values[0]
        return self.finalize_url(query.model_class.destination_name(), available_routing_data, operation)

    def create_url(self, data: dict[str, Any], model: Model) -> tuple[str, list[str]]:
        """
        Calculate the URL to use for a create request.  Also, return the list of any data parameters used to construct the URL.

        See finalize_url for more details on the return value.

        When a callable is provided as the ``url_adapter``, it receives ``(data, model)`` and can return either a plain
        URL string or a tuple of ``(url, used_routing_parameters)``.  If it returns just a URL string, no routing
        parameters are reported as consumed, so all data keys remain in the request body.  If it returns a tuple, the
        second element lists the parameter names that were absorbed into the URL and should be removed from the request
        body before sending the API request::

            # Simple callable — just return a URL string:
            url_adapter = lambda data, model: f"/api/v2/{model.destination_name()}"

            # Callable with routing parameter reporting:
            url_adapter = lambda data, model: (
                f"/api/v2/tenants/{data['tenant_id']}/{model.destination_name()}",
                ["tenant_id"],
            )
        """
        url_adapter = self.url_adapter_instance
        if callable(url_adapter) and not isinstance(url_adapter, UrlAdapter):
            # A callable url_adapter receives (data, model) and can return either a plain URL string
            # or a tuple of (url, used_routing_parameters).  When it returns just a string, we assume
            # no routing parameters were consumed from the data, so nothing is stripped from the request body.
            result = url_adapter(data, model)
            if isinstance(result, tuple):
                return result
            return (result, [])
        return url_adapter.create_url(data, model)

    def create_method(self, data: dict[str, Any], model: Model) -> str:
        """Return the request method to use with a create request."""
        return "POST"

    def records_url(self, query: Query) -> tuple[str, list[str]]:
        """
        Calculate the URL to use for a records request.  Also, return the list of any query parameters used to construct the URL.

        See finalize_url for more details on the return value.

        When a callable is provided as the ``url_adapter``, it receives ``(query)`` and can return either a plain
        URL string or a tuple of ``(url, used_routing_parameters)``.  If it returns just a URL string, no routing
        parameters are reported as consumed, so all query conditions are translated into query parameters.  If it
        returns a tuple, the second element lists the condition column names that were absorbed into the URL and
        should be excluded from query parameters::

            # Simple callable — just return a URL string:
            url_adapter = lambda query: f"/api/v2/{query.model_class.destination_name()}"

            # Callable with routing parameter reporting:
            url_adapter = lambda query: (
                f"/api/v2/tenants/{next(c.values[0] for c in query.conditions if c.column_name == 'tenant_id')}/{query.model_class.destination_name()}",
                ["tenant_id"],
            )
        """
        url_adapter = self.url_adapter_instance
        if callable(url_adapter) and not isinstance(url_adapter, UrlAdapter):
            # A callable url_adapter receives (query) and can return either a plain URL string or a tuple
            # of (url, used_routing_parameters).  When it returns just a string, we assume no query conditions
            # were consumed as routing parameters.
            result = url_adapter(query)
            if isinstance(result, tuple):
                return result
            return (result, [])
        return url_adapter.records_url(query)

    def records_method(self, query: Query) -> str:
        """Return the request method to use when fetching records from the API."""
        return "GET"

    def count_url(self, query: Query) -> tuple[str, list[str]]:
        """
        Calculate the URL to use for a request to get a record count..  Also, return the list of any query parameters used to construct the URL.

        See finalize_url for more details on the return value.
        """
        return self.records_url(query)

    def count_method(self, query: Query) -> str:
        """
        Return the request method to use when making a request for a record count.

        Defaults to ``HEAD`` because it's lightweight — the server returns only headers (no body),
        which is sufficient when count information comes from headers like ``X-Total-Count``.
        Override this to return ``GET`` if your API doesn't support ``HEAD`` requests or if the
        count comes from the response body.
        """
        return "HEAD"

    def delete_url(self, id: int | str, model: Model) -> tuple[str, list[str]]:
        """
        Calculate the URL to use for a delete request.  Also, return the list of any query parameters used to construct the URL.

        See finalize_url for more details on the return value.

        When a callable is provided as the ``url_adapter``, it receives ``(model, id)`` and can return either a plain
        URL string or a tuple of ``(url, used_routing_parameters)``::

            # Simple callable — just return a URL string:
            url_adapter = lambda model, id: f"/api/v2/{model.destination_name()}/{id}"

            # Callable with routing parameter reporting:
            url_adapter = lambda model, id: (
                f"/api/v2/tenants/{model.tenant_id}/{model.destination_name()}/{id}",
                ["tenant_id"],
            )
        """
        url_adapter = self.url_adapter_instance
        if callable(url_adapter) and not isinstance(url_adapter, UrlAdapter):
            # A callable url_adapter receives (model, id) and can return either a plain URL string or a tuple
            # of (url, used_routing_parameters).  When it returns just a string, we assume no routing parameters
            # were consumed from the model data.
            result = url_adapter(model, id)
            if isinstance(result, tuple):
                return result
            return (result, [])
        return url_adapter.delete_url(id, model)

    def delete_method(self, id: int | str, model: Model) -> str:
        """Return the request method to use when deleting records via the API."""
        return "DELETE"

    def update_url(self, id: int | str, data: dict[str, Any], model: Model) -> tuple[str, list[str]]:
        """
        Calculate the URL to use for an update request.  Also, return the list of any query parameters used to construct the URL.

        See finalize_url for more details on the return value.

        When a callable is provided as the ``url_adapter``, it receives ``(model, id, data)`` and can return either
        a plain URL string or a tuple of ``(url, used_routing_parameters)``.  If it returns just a URL string, no
        routing parameters are reported as consumed, so all data keys remain in the request body.  If it returns a
        tuple, the second element lists the parameter names that were absorbed into the URL and should be removed
        from the request body before sending the API request::

            # Simple callable — just return a URL string:
            url_adapter = lambda model, id, data: f"/api/v2/{model.destination_name()}/{id}"

            # Callable with routing parameter reporting:
            url_adapter = lambda model, id, data: (
                f"/api/v2/tenants/{data['tenant_id']}/{model.destination_name()}/{id}",
                ["tenant_id"],
            )
        """
        url_adapter = self.url_adapter_instance
        if callable(url_adapter) and not isinstance(url_adapter, UrlAdapter):
            # A callable url_adapter receives (model, id, data) and can return either a plain URL string or a tuple
            # of (url, used_routing_parameters).  When it returns just a string, we assume no routing parameters
            # were consumed from the data, so nothing is stripped from the request body.
            result = url_adapter(model, id, data)
            if isinstance(result, tuple):
                return result
            return (result, [])
        return url_adapter.update_url(id, data, model)

    def update_method(self, id: int | str, data: dict[str, Any], model: Model) -> str:
        """Return the request method to use for an update request."""
        return "PATCH"

    def get_record_headers(self) -> dict[str, str]:
        """
        Return headers to use for record fetch requests.

        Uses record_headers if set, otherwise falls back to headers.
        """
        return self.record_headers if self.record_headers is not None else self.headers

    def get_create_headers(self) -> dict[str, str]:
        """
        Return headers to use for create requests.

        Uses create_headers if set, otherwise falls back to headers.
        """
        return self.create_headers if self.create_headers is not None else self.headers

    def get_update_headers(self) -> dict[str, str]:
        """
        Return headers to use for update requests.

        Uses update_headers if set, otherwise falls back to headers.
        """
        return self.update_headers if self.update_headers is not None else self.headers

    def get_delete_headers(self) -> dict[str, str]:
        """
        Return headers to use for delete requests.

        Uses delete_headers if set, otherwise falls back to headers.
        """
        return self.delete_headers if self.delete_headers is not None else self.headers

    def get_count_headers(self) -> dict[str, str]:
        """
        Return headers to use for count requests.

        Uses count_headers if set, otherwise falls back to headers.
        """
        return self.count_headers if self.count_headers is not None else self.headers

    def update(self, id: int | str, data: dict[str, Any], model: Model) -> RecordQueryResult:
        """Update a record."""
        data = {**data}
        url, used_routing_parameters = self.update_url(id, data, model)
        request_method = self.update_method(id, data, model)
        for parameter in used_routing_parameters:
            del data[parameter]

        response = self.execute_request(
            url, request_method, json=self.map_update_request(id, data, model), headers=self.get_update_headers()
        )
        json_response = response.json() if response.content else {}
        new_record = {**model.get_raw_data(), **data}
        if response.content:
            new_record = {**new_record, **self.map_update_response(response.json(), model)}
        return RecordQueryResult(record=new_record)

    def map_update_request(self, id: int | str, data: dict[str, Any], model: Model) -> dict[str, Any]:
        """
        Take the data for an update request and figure out where it should go in the API request (e.g. URL parameters vs. query parameters vs. body).

        See self.map_record_response for goals/motiviation
        """
        return data

    def map_update_response(self, response_data: dict[str, Any], model: Model) -> dict[str, Any]:
        """
        Take the response from the API endpoint for an update request and figure out where the data lives/return it to build a new model.

        See self.map_record_response for goals/motiviation
        """
        return self.map_record_response(response_data, model.get_columns(), "update")

    def create(self, data: dict[str, Any], model: Model) -> RecordQueryResult:
        """Create a record."""
        data = {**data}
        url, used_routing_parameters = self.create_url(data, model)
        request_method = self.create_method(data, model)

        for parameter in used_routing_parameters:
            del data[parameter]

        response = self.execute_request(
            url, request_method, json=self.map_create_request(data, model), headers=self.get_create_headers()
        )
        json_response = response.json() if response.content else {}
        if response.content:
            record = self.map_create_response(response.json(), model)
            return RecordQueryResult(record=record)
        return RecordQueryResult(record={})

    def map_create_request(self, data: dict[str, Any], model: Model) -> dict[str, Any]:
        """
        Take the data for a create request and figure out where it should go in the API request (e.g. URL parameters vs. query parameters vs. body).

        The default implementation just returns the data as-is, but you can overwrite this if you need to massage the data in some way before it's sent to the API endpoint.  For example, maybe your model has a column named `full_name` but the API expects this to be sent as `fullName` - in this case, you could overwrite this method to convert from snake_case to camelCase before sending the data to the API endpoint.
        """
        return data

    def map_create_response(self, response_data: dict[str, Any], model: Model) -> dict[str, Any]:
        return self.map_record_response(response_data, model.get_columns(), "create")

    def delete(self, id: int | str, model: Model) -> SuccessQueryResult:
        (url, used_routing_parameters) = self.delete_url(id, model)
        request_method = self.delete_method(id, model)

        response = self.execute_request(url, request_method, headers=self.get_delete_headers())
        return SuccessQueryResult()

    def records(self, query: Query) -> RecordsQueryResult:
        self.check_query(query)
        (url, method, body, headers) = self.build_records_request(query)
        response = self.execute_request(url, method, json=body, headers=headers)
        response_data = response.json()
        records = self.map_records_response(response_data, query)
        response_next_page_data = self.get_next_page_data_from_response(query, response)

        # Extract count info via the count adapter.  Both the headers and the parsed body are
        # provided so that either header-based or body-based count adapters can find the count.
        total_count, total_pages = self.extract_count_from_response(dict(response.headers), response_data)

        return RecordsQueryResult(
            records=records,
            next_page_data=response_next_page_data if response_next_page_data else None,
            total_count=total_count,
            total_pages=total_pages,
        )

    def build_records_request(self, query: Query) -> tuple[str, str, dict[str, Any], dict[str, str]]:
        url, used_routing_parameters = self.records_url(query)

        condition_route_id, condition_url_parameters, condition_body_parameters = self.conditions_to_request_parameters(
            query, used_routing_parameters
        )
        pagination_url_parameters, pagination_body_parameters = self.pagination_to_request_parameters(query)
        sort_url_parameters, sort_body_parameters = self.sorts_to_request_parameters(query)

        url_parameters = {
            **condition_url_parameters,
            **pagination_url_parameters,
            **sort_url_parameters,
        }

        body_parameters = {
            **condition_body_parameters,
            **pagination_body_parameters,
            **sort_body_parameters,
        }

        if condition_route_id:
            url = url.rstrip("/") + "/" + condition_route_id
        if url_parameters:
            url = url + "?" + urllib.parse.urlencode(url_parameters)

        return (
            url,
            self.records_method(query),
            body_parameters,
            self.get_record_headers(),
        )

    def conditions_to_request_parameters(
        self, query: Query, used_routing_parameters: list[str]
    ) -> tuple[str, dict[str, str], dict[str, Any]]:
        route_id = ""

        url_parameters = {}
        for condition in query.conditions:
            if condition.column_name in used_routing_parameters:
                continue
            if condition.operator != "=":
                raise ValueError(
                    f"I'm not very smart and only know how to search with the equals operator, but I received a condition of {condition.parsed}.  If you need to support this, you'll have to extend the ApiBackend and overwrite the build_records_request method."
                )
            if condition.column_name == query.model_class.id_column_name:
                route_id = condition.values[0]
                continue
            url_parameters[string.swap_casing(condition.column_name, self.model_casing, self.api_casing)] = (
                condition.values[0]
            )

        return (route_id, url_parameters, {})

    def pagination_to_request_parameters(self, query: Query) -> tuple[dict[str, str], dict[str, Any]]:
        url_parameters = {}
        if query.limit:
            if not self.limit_parameter_name:
                raise ValueError(
                    "The records query attempted to change the limit (the number of results per page) but the backend does not support it.  If it actually does support this, then set an appropriate value for backend.limit_parameter_name"
                )
            url_parameters[self.limit_parameter_name] = str(query.limit)

        if query.pagination.get(self.pagination_parameter_name):
            url_parameters[self.pagination_parameter_name] = str(query.pagination.get(self.pagination_parameter_name))

        return (url_parameters, {})

    def sorts_to_request_parameters(self, query: Query) -> tuple[dict[str, str], dict[str, Any]]:
        if not query.sorts:
            return ({}, {})

        if len(query.sorts) > 1:
            raise ValueError(
                "I received a query with two sort directives, but I can only handle one.  Sorry!  If you need o support two sort directions, you'll have to extend the ApiBackend and overwrite the build_records_request method."
            )

        return (
            {"sort": query.sorts[0].column_name, "direction": query.sorts[0].direction.lower()},
            {},
        )

    def map_records_response(
        self, response_data: Any, query: Query, query_data: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Take the response from an API endpoint that returns a list of records and find the actual list of records."""
        columns = query.model_class.get_columns()
        # turn all of our conditions into record data and inject these into the results.  We do this to keep around
        # any query parameters.  This is especially important for any URL parameters, wihch aren't always returned in
        # the data, but which we are likely to need again if we go to update/delete the record.
        if query_data is None:
            query_data = {}
            for condition in query.conditions:
                if condition.operator != "=":
                    continue
                query_data[condition.column_name] = condition.values[0]

        # Allow the response_adapter to pre-process the raw response data before the standard mapping
        # logic runs.  A non-None return value replaces response_data; None means "pass through".
        adapter = self.get_response_adapter()
        if adapter is not None:
            extracted = (
                adapter(response_data)
                if callable(adapter) and not isinstance(adapter, ResponseAdapter)
                else adapter.extract_records(response_data)
            )
            if extracted is None:
                raise ValueError(
                    "A response adapter was configured, but it did not extract records from the API response.  Please update your adapter to return the records list for this response shape."
                )
            response_data = extracted

        # if our response is actually a list, then presumably the problem is solved.  If the response is a list
        # and the individual items aren't model results though... well, then I'm very confused
        if isinstance(response_data, list):
            if not response_data:
                return []
            try:
                response = self.map_to_model(response_data[0], columns, strict=True)
            except NotModelData:
                raise ValueError(
                    "The response from a records request returned a list, but the records in the list didn't look anything like the model class.  Please check your model class and mapping settings in the API Backend.  If those are correct, then you'll have to override the map_records_response method, because the API you are interacting with is returning data in an unexpected way that I can't automatically figure out."
                )
            return [self.map_to_model(record, columns, query_data) for record in response_data]

        if not isinstance(response_data, dict):
            raise ValueError(
                f"The response from a records request returned a variable of type {response_data.__class__.__name__}, which is just confusing.  To do automatic introspection, I need a list or a dictionary.  I'm afraid you'll have to extend the API backend and override the map_record_response method to deal with this."
            )

        # a records request may only return a single record, so before we fail, let's check for that
        record = self.check_dict_and_map_to_model(response_data, columns, query_data, strict=True)
        if record is not None:
            return [record]

        for key, value in response_data.items():
            if not isinstance(value, list):
                continue
            return self.map_records_response(value, query, query_data)

        raise ValueError(
            "The response from a records request returned a dictionary, but none of the items in the dictionary was a list, so I don't know where to find the records.  I only ever check one level deep in dictionaries.  I'm afraid you'll have to extend the API backend and override the map_records_response method to deal with this."
        )

    def map_record_response(
        self,
        response_data: dict[str, Any],
        columns: dict[str, Column],
        operation: str,
    ) -> dict[str, Any]:
        """
        Take the response from an API endpoint that returns a single record (typically update and create requests) and return the data for a new model.

        The goal of this method is to try to use the model schema to automatically understand the response from the
        the API endpoint.  The goal is for the backend to work out-of-the-box with most APIs.  In general, it works
        by iterating over the response, looking for a dictionary with keys that match the expected model columns.

        Occassionally the automatic introspection may not be able to make sense of the response from an API
        endoint.  If this happens, you have to make a new API backend, override the map_record_response method
        to manage the mapping yourself, and then attach this new backend to your models.
        """
        # Allow the response_adapter to pre-process the raw response data before the standard mapping
        # logic runs.  A non-None return value replaces response_data; None means "pass through".
        adapter = self.get_response_adapter()
        if adapter is not None:
            extracted = (
                adapter(response_data)
                if callable(adapter) and not isinstance(adapter, ResponseAdapter)
                else adapter.extract_record(response_data)
            )
            if extracted is None:
                raise ValueError(
                    f"A response adapter was configured, but it did not extract a record from the API response for {operation}.  Please update your adapter to return the record dictionary for this response shape."
                )
            response_data = extracted

        an = "a" if operation == "create" else "an"
        if not isinstance(response_data, dict):
            raise ValueError(
                f"The response from {an} {operation} request returned a variable of type {response_data.__class__.__name__}, which is just confusing.  To do automatic introspection, I need a dictionary.  I'm afraid you'll have to build your own API backend and override the map_record_response method to deal with this."
            )

        response = self.check_dict_and_map_to_model(response_data, columns)
        if response is None:
            raise ValueError(
                f"I was not able to automatically interpret the response from {an} {operation} request.  This could be a sign of a response that is structured in a very unusual way, or may be a sign that the casing settings and/or columns on your model to properly reflect the API response.  For the former, you will hvae to build your own API backend and override the map_record_response to deal with this."
            )

        return response

    def get_response_adapter(self) -> ResponseAdapter | Callable | None:
        """Return the active response adapter."""
        if self.response_adapter is not None:
            return self.response_adapter

        if self._resolved_response_adapter is not None:
            return self._resolved_response_adapter

        try:
            self._resolved_response_adapter = self.di.build(self.response_adapter_dependency_name)
        except MissingDependency:
            self._resolved_response_adapter = None

        return self._resolved_response_adapter

    def map_to_model(
        self,
        response_data: dict[str, Any],
        columns: dict[str, Column],
        query_data: dict[str, Any] = {},
        strict: bool = False,
    ) -> dict[str, Any]:
        """
        Map a response dictionary to a model record.

        If strict is False (the default) then any extra keys in the dictionary will automatically
        be added to the response.  This is convenient when processing the actual data, because it's
        fairly common (in practice) to have an API return data that doesn't have corresponding columns.
        However, there are times when we want this behavior off.  In particular, when we're trying to
        decide if some part of a response actually corresponds to model data.  In this case, including
        all extra columns in the response is detrimental because the logic of the automated mapping process
        figures out when it has found the data because data gets returned: if we just include anything,
        we'll think that we've found a match with the first dictionary we find.

        Therefore, we want to be strict when we're looking for the data, and we want to be lax when
        we're transforming the data afterwards (which is exactly how this flag is used - see the
        `map_records_response` method.
        """
        response_to_model_map = self.build_response_to_model_map(columns)
        response_keys = set(response_data.keys())
        map_keys = set(response_to_model_map.keys())
        matching = response_keys.intersection(map_keys)

        mapped = {response_to_model_map[key]: response_data[key] for key in matching}

        for api_key, column_name in self.api_to_model_map.items():
            if "." not in api_key:
                continue
            try:
                value = json_functional.get_nested_attribute(response_data, api_key)
            except KeyError:
                continue
            if value is None:
                continue
            if isinstance(column_name, list):
                for column in column_name:
                    mapped[column] = value
            else:
                mapped[column_name] = value

        if not strict:
            for key in response_keys.difference(map_keys):
                mapped[string.swap_casing(key, self.api_casing, self.model_casing)] = response_data[key]

        # if we didn't map anything at the top level, recurse into child dictionaries
        if not mapped:
            for value in response_data.values():
                if not isinstance(value, dict):
                    continue
                try:
                    return {**query_data, **self.map_to_model(value, columns)}
                except NotModelData:
                    pass

            raise NotModelData("Input was not valid model data")

        return {**query_data, **mapped}

    def check_dict_and_map_to_model(
        self,
        response_data: dict[str, Any],
        columns: dict[str, Column],
        query_data: dict[str, Any] = {},
        strict: bool = False,
    ) -> dict[str, Any] | None:
        """
        Check a dictionary in the response to decide if it contains the data for a record.

        If not, it will search the keys for something that looks like a record.
        """
        try:
            return self.map_to_model(response_data, columns, query_data, strict=strict)
        except NotModelData:
            return None

    def build_response_to_model_map(self, columns: dict[str, Column]) -> dict[str, str]:
        if self._response_to_model_map is not None:
            return self._response_to_model_map

        self._response_to_model_map = {}
        for column_name in columns:
            self._response_to_model_map[string.swap_casing(column_name, self.model_casing, self.api_casing)] = (
                column_name
            )
        self._response_to_model_map = {**self._response_to_model_map, **self.api_to_model_map}

        return self._response_to_model_map

    def get_next_page_data_from_response(
        self,
        query: Query,
        response: RequestsResponse,
    ) -> dict[str, Any]:
        """
        Extract pagination data from the API response via adapter.

        This method has a very important job, which is to inform clearskies about how to make another API call to fetch the next
        page of records.  It returns a dictionary with whatever pagination information is necessary.

        Returns:
            A dictionary containing pagination data (e.g., cursor, page number, total counts).
            Returns an empty dict if there is no next page.
        """
        pagination_adapter = self.pagination_adapter_instance
        if callable(pagination_adapter) and not isinstance(pagination_adapter, PaginationAdapter):
            next_page_data = pagination_adapter(response, query)
            return next_page_data if isinstance(next_page_data, dict) else {}
        return pagination_adapter.extract_next_page_data(response, query)

    def extract_count_from_response(
        self,
        response_headers: dict[str, str] | None = None,
        response_data: Any = None,
    ) -> tuple[int | None, int | None]:
        """
        Extract count information from API response via the count adapter.

        Delegates to the configured ``count_adapter`` to extract total record count and total page
        count from the API response.  The default ``CountAdapter`` checks for common count headers
        used by REST APIs:

        - ``X-Total-Count`` or ``X-Total`` for total record count
        - ``X-Total-Pages`` for total pages

        You can customize this by providing a ``count_adapter`` when configuring the backend, or by
        overriding this method in a subclass:

        ```python
        def extract_count_from_response(
            self,
            response_headers: dict[str, str] | None = None,
            response_data: Any = None,
        ) -> tuple[int | None, int | None]:
            if not response_headers:
                return (None, None)
            # Custom header names for your API
            total = response_headers.get("X-My-Api-Total")
            pages = response_headers.get("X-My-Api-Pages")
            if total is not None:
                return (int(total), int(pages) if pages else None)
            return (None, None)
        ```
        """
        count_adapter = self.count_adapter_instance
        if callable(count_adapter) and not isinstance(count_adapter, CountAdapter):
            result = count_adapter(response_headers, response_data)
            return result if isinstance(result, tuple) and len(result) == 2 else (None, None)
        return count_adapter.extract_count(response_data, response_headers)

    def count(self, query: Query) -> CountQueryResult:
        """
        Count the number of records matching the query.

        When ``can_count`` is ``True``, this attempts a lightweight ``HEAD`` request to the records URL
        and uses the ``count_adapter`` to extract the total count from the response headers (e.g.
        ``X-Total-Count``).  A ``HEAD`` request returns only headers — no response body — so this is
        much cheaper than fetching all records just to count them.

        If the ``HEAD`` request doesn't return count headers, the count will be ``0``.  For APIs that
        don't support ``HEAD`` requests or don't return count headers, you can override ``count_method``
        to use ``GET`` instead, or override this method entirely.

        When ``can_count`` is ``False`` (the default), this raises ``NotImplementedError``.

        ```python
        backend = clearskies.backends.ApiBackend(
            base_url="https://api.example.com",
            can_count=True,
        )
        ```
        """
        if not self.can_count:
            raise NotImplementedError(
                f"The {self.__class__.__name__} backend does not support count operations.  "
                f"Set can_count=True to enable count via HEAD request with response headers."
            )

        self.check_query(query)
        url, used_routing_parameters = self.count_url(query)
        method = self.count_method(query)
        condition_route_id, condition_url_parameters, condition_body_parameters = self.conditions_to_request_parameters(
            query, used_routing_parameters
        )

        if condition_route_id:
            url = url.rstrip("/") + "/" + str(condition_route_id)

        if condition_url_parameters:
            url = url + "?" + urllib.parse.urlencode(condition_url_parameters)

        response = self.execute_request(url, method, headers=self.get_count_headers())
        total_count, total_pages = self.extract_count_from_response(
            dict(response.headers),
            response.json() if response.content else None,
        )

        return CountQueryResult(count=total_count or 0)

    def execute_request(
        self,
        url: str,
        method: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> RequestsResponse:
        """
        Execute the actual API request and returns the response object.

        We don't directly call the requests library to support retries in the event of failed authentication.  The goal
        is to support short-lived credentials, and our authentication classes denote if they support this feature.  If
        they do, and the requests fails, then we'll ask the authentication method to refresh its credentials and we
        will retry the request.
        """
        if json is None:
            json = {}
        if headers is None:
            headers = {}

        self.logger.debug(f"Executing {method} request to {url} with headers {headers} and json {json}")

        if self.authentication:
            if not self._auth_injected:
                self._auth_injected = True
                if isinstance(self.authentication, InjectableProperties):
                    self.authentication.injectable_properties(self.di)
        # the requests library seems to build a slightly different request if you specify the json parameter,
        # even if it is null, and this causes trouble for some picky servers
        if not json:
            response = self.requests.request(
                method,
                url,
                headers=headers,
                auth=self.authentication if self.authentication else None,
            )
        else:
            response = self.requests.request(
                method,
                url,
                headers=headers,
                json=json,
                auth=self.authentication if self.authentication else None,
            )

        if not response.ok:
            raise ValueError(
                f"Failed request.  Status code: {response.status_code}, message: " + response.content.decode("utf-8")
            )

        return response

    def check_query(self, query: Query) -> None:
        for key in ["joins", "group_by", "selects"]:
            if getattr(query, key):
                raise ValueError(f"{self.__class__.__name__} does not support queries with {key}")

        for condition in query.conditions:
            if condition.operator != "=":
                raise ValueError(
                    f"{self.__class__.__name__} only supports searching with the '=' operator, but I found a search with the {condition.operator} operator"
                )

    def validate_pagination_data(self, data: dict[str, Any], case_mapping: Callable) -> str:
        extra_keys = set(data.keys()) - set(self.allowed_pagination_keys())
        if len(extra_keys):
            key_name = case_mapping(self.pagination_parameter_name)
            return "Invalid pagination key(s): '" + "','".join(extra_keys) + f"'.  Only '{key_name}' is allowed"
        if self.pagination_parameter_name not in data:
            key_name = case_mapping(self.pagination_parameter_name)
            return f"You must specify '{key_name}' when setting pagination"
        value = data[self.pagination_parameter_name]
        try:
            if self.pagination_parameter_type == "int":
                converted = int(value)
        except:
            key_name = case_mapping(self.pagination_parameter_name)
            return f"Invalid pagination data: '{key_name}' must be a number"
        return ""

    def allowed_pagination_keys(self) -> list[str]:
        return [self.pagination_parameter_name]

    def documentation_pagination_next_page_response(self, case_mapping: Callable) -> list[Any]:
        if self.pagination_parameter_type == "int":
            return [AutoDocInteger(case_mapping(self.pagination_parameter_name), example=0)]
        else:
            return [AutoDocString(case_mapping(self.pagination_parameter_name), example="")]

    def documentation_pagination_next_page_example(self, case_mapping: Callable) -> dict[str, Any]:
        return {case_mapping(self.pagination_parameter_name): 0 if self.pagination_parameter_type == "int" else ""}

    def documentation_pagination_parameters(self, case_mapping: Callable) -> list[tuple[AutoDocSchema, str]]:
        return [
            (
                AutoDocInteger(
                    case_mapping(self.pagination_parameter_name),
                    example=0 if self.pagination_parameter_type == "int" else "",
                ),
                "The next record",
            )
        ]

    def column_from_backend(self, column: Column, value: Any) -> Any:
        """We have a couple columns we want to override transformations for."""
        # most importantly, there's no need to transform a JSON column in either direction
        if isinstance(column, columns.json.Json):
            return value
        return super().column_from_backend(column, value)

    def column_to_backend(self, column: Column, backend_data: dict[str, Any]) -> dict[str, Any]:
        """We have a couple columns we want to override transformations for."""
        # most importantly, there's no need to transform a JSON column in either direction
        if isinstance(column, columns.json.Json):
            return backend_data
        # also, APIs tend to have a different format for dates than SQL
        if isinstance(column, columns.date.Date) and column.name in backend_data:
            as_date = (
                backend_data[column.name].isoformat()
                if type(backend_data[column.name]) != str
                else backend_data[column.name]
            )
            return {**backend_data, **{column.name: as_date}}
        return column.to_backend(backend_data)
