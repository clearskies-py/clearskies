from __future__ import annotations

import inspect
import urllib.parse
from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Callable, Optional

from clearskies import autodoc, column, configs, configurable, decorators, di, end, exceptions
from clearskies.authentication import Authentication, Authorization, Public
from clearskies.autodoc import schema
from clearskies.autodoc.request import Parameter, Request
from clearskies.autodoc.response import Response
from clearskies.functional import routing, string

if TYPE_CHECKING:
    from clearskies import Column, Model, SecurityHeader
    from clearskies.input_outputs import InputOutput
    from clearskies.schema import Schema
    from clearskies.security_headers import Cors


class Endpoint(
    end.End,  # type: ignore
    configurable.Configurable,
    di.InjectableProperties,
):
    """
    Automating drudgery.

    With clearskies, endpoints exist to offload some drudgery and make your life easier, but they can also
    get out of your way when you don't need them.  Think of them as pre-built endpoints that can execute
    common functionality needed for web applications/APIs.  Instead of defining a function that fetches
    records from your backend and returns them to the end user, you can let the list endpoint do this for you
    with a minimal amount of configuration.  Instead of making an endpoint that creates records, just deploy
    a create endpoint.  While this gives clearskies some helpful capabiltiies for automation, it also has
    the Callable endpoint which simply calls a developer-defined function, and therefore allows clearskies to
    act like a much more typical framework.
    """

    """
    The dependency injection container
    """
    di = di.inject.Di()

    """
    Whether or not this endpoint can handle CORS
    """
    has_cors = False

    """
    The actual CORS header
    """
    cors_header: Optional[Cors] = None

    """
    Set some response headers that should be returned for this endpoint.

    Provide a list of response headers to return to the caller when this endpoint is executed.
    This should be given a list containing a combination of strings or callables that return a list of strings.
    The strings in question should be headers formatted as "key: value".  If you attach a callable, it can accept
    any of the standard dependencies or context-specific values like any other callable in a clearskies
    application:

    ```python
    def custom_headers(query_parameters):
        some_value = "yes" if query_parameters.get("stuff") else "no"
        return [f"x-custom: {some_value}", "content-type: application/custom"]

    endpoint = clearskies.endpoints.Callable(
        lambda: {"hello": "world"},
        response_headers=custom_headers,
    )

    wsgi = clearskies.contexts.WsgiRef(endpoint)
    wsgi()
    ```
    """
    response_headers = configs.StringListOrCallable(default=[])

    """
    Set the URL for the endpoint

    When an endpoint is attached directly to a context, then the endpoint's URL becomes the exact URL
    to invoke the endpoint.  If it is instead attached to an endpoint group, then the URL of the endpoint
    becomes a suffix on the URL of the group.  This is described in more detail in the documentation for endpoint
    groups, so here's an example of attaching endpoints directly and setting the URL:

    ```python
    import clearskies

    endpoint = clearskies.endpoints.Callable(
        lambda: {"hello": "World"},
        url="/hello/world",
    )

    wsgi = clearskies.contexts.WsgiRef(endpoint)
    wsgi()
    ```

    Which then acts as expected:

    ```bash
    $ curl 'http://localhost:8080/hello/asdf' | jq
    {
        "status": "client_error",
        "error": "Not Found",
        "data": [],
        "pagination": {},
        "input_errors": {}
    }

    $ curl 'http://localhost:8080/hello/world' | jq
    {
        "status": "success",
        "error": "",
        "data": {
            "hello": "world"
        },
        "pagination": {},
        "input_errors": {}
    }
    ```

    Some endpoints allow or require the use of named routing parameters.  Named routing paths are created using either the
    `/{name}/` syntax or `/:name/`.  These parameters can be injected into any callable via the `routing_data`
    dependency injection name, as well as via their name:

    ```python
    import clearskies

    endpoint = clearskies.endpoints.Callable(
        lambda first_name, last_name: {"hello": f"{first_name} {last_name}"},
        url="/hello/:first_name/{last_name}",
    )

    wsgi = clearskies.contexts.WsgiRef(endpoint)
    wsgi()
    ```

    Which you can then invoke in the usual way:

    ```bash
    $ curl 'http://localhost:8080/hello/bob/brown' | jq
    {
        "status": "success",
        "error": "",
        "data": {
            "hello": "bob brown"
        },
        "pagination": {},
        "input_errors": {}
    }

    ```

    """
    url = configs.Url(default="")

    """
    The allowed request methods for this endpoint.

    By default, only GET is allowed.

    ```python
    import clearskies

    endpoint = clearskies.endpoints.Callable(
        lambda: {"hello": "world"},
        request_methods=["POST"],
    )

    wsgi = clearskies.contexts.WsgiRef(endpoint)
    wsgi()
    ```

    And to execute:

    ```bash
    $ curl 'http://localhost:8080/' -X POST | jq
    {
        "status": "success",
        "error": "",
        "data": {
            "hello": "world"
        },
        "pagination": {},
        "input_errors": {}
    }

    $ curl 'http://localhost:8080/' -X GET | jq
    {
        "status": "client_error",
        "error": "Not Found",
        "data": [],
        "pagination": {},
        "input_errors": {}
    }
    ```
    """
    request_methods = configs.SelectList(
        allowed_values=["GET", "POST", "PUT", "DELETE", "PATCH", "QUERY"], default=["GET"]
    )

    """
    The authentication for this endpoint (default is public)

    Use this to attach an instance of `clearskies.authentication.Authentication` to an endpoint, which enforces authentication.
    For more details, see the dedicated documentation section on authentication and authorization. By default, all endpoints are public.
    """
    authentication = configs.Authentication(default=Public())

    """
    The authorization rules for this endpoint

    Use this to attach an instance of `clearskies.authentication.Authorization` to an endpoint, which enforces authorization.
    For more details, see the dedicated documentation section on authentication and authorization. By default, no authorization is enforced.
    """
    authorization = configs.Authorization(default=Authorization())

    """
    An override of the default model-to-json mapping for endpoints that auto-convert models to json.

    Many endpoints allow you to return a model which is then automatically converted into a JSON response.  When this is the case,
    you can provide a callable in the `output_map` parameter which will be called instead of following the usual method for
    JSON conversion.  Note that if you use this method, you should also specify `output_schema`, which the autodocumentation
    will then use to document the endpoint.

    Your function can request any named dependency injection parameter as well as the standard context parameters for the request.

    ```python
    import clearskies
    import datetime
    from dateutil.relativedelta import relativedelta

    class User(clearskies.Model):
        id_column_name = "id"
        backend = clearskies.backends.MemoryBackend()
        id = clearskies.columns.Uuid()
        name = clearskies.columns.String()
        dob = clearskies.columns.Datetime()

    class UserResponse(clearskies.Schema):
        id = clearskies.columns.String()
        name = clearskies.columns.String()
        age = clearskies.columns.Integer()
        is_special = clearskies.columns.Boolean()

    def user_to_json(model: User, utcnow: datetime.datetime, special_person: str):
        return {
            "id": model.id,
            "name": model.name,
            "age": relativedelta(utcnow, model.dob).years,
            "is_special": model.name.lower() == special_person.lower(),
        }

    list_users = clearskies.endpoints.List(
        model_class=User,
        url="/{special_person}",
        output_map = user_to_json,
        output_schema = UserResponse,
        readable_column_names=["id", "name"],
        sortable_column_names=["id", "name", "dob"],
        default_sort_column_name="dob",
        default_sort_direction="DESC",
    )

    wsgi = clearskies.contexts.WsgiRef(
        list_users,
        classes=[User],
        bindings={
            "special_person": "jane",
            "memory_backend_default_data": [
                {
                    "model_class": User,
                    "records": [
                        {"id": "1-2-3-4", "name": "Bob", "dob": datetime.datetime(1990, 1, 1)},
                        {"id": "1-2-3-5", "name": "Jane", "dob": datetime.datetime(2020, 1, 1)},
                        {"id": "1-2-3-6", "name": "Greg", "dob": datetime.datetime(1980, 1, 1)},
                    ]
                },
            ]
        }
    )
    wsgi()
    ```

    Which gives:

    ```bash
    $ curl 'http://localhost:8080/jane' | jq
    {
        "status": "success",
        "error": "",
        "data": [
            {
                "id": "1-2-3-5",
                "name": "Jane",
                "age": 5,
                "is_special": true
            }
            {
                "id": "1-2-3-4",
                "name": "Bob",
                "age": 35,
                "is_special": false
            },
            {
                "id": "1-2-3-6",
                "name": "Greg",
                "age": 45,
                "is_special": false
            },
        ],
        "pagination": {
            "number_results": 3,
            "limit": 50,
            "next_page": {}
        },
        "input_errors": {}
    }

    ```

    """
    output_map = configs.Callable(default=None)

    """
    A schema that describes the expected output to the client.

    This is used to build the auto-documentation.  See the documentation for clearskies.endpoint.output_map for examples.
    Note that this is typically not required - when returning models and relying on clearskies to auto-convert to JSON,
    it will also automatically generate your documentation.
    """
    output_schema = configs.Schema(default=None)

    """
    The model class used by this endpoint.

    The endpoint will use this to fetch/save/validate incoming data as needed.
    """
    model_class = configs.ModelClass(default=None)

    """
    A schema that describes the expected input from the client.

    Use this to define input validation for query parameters, URL path parameters, and request bodies
    when you don't want to use a full Model with a backend, or when you need to validate inputs
    differently than your model schema.

    This is particularly useful for validating query parameters and URL path parameters in
    endpoints like Get, List, and Delete, where you want to ensure that URL parameters like
    `/users/{id}` are validated as the correct type (e.g., Integer instead of string).

    ## Basic Usage

    ```python
    import clearskies

    class User(clearskies.Model):
        id_column_name = "id"
        backend = clearskies.backends.MemoryBackend()
        id = clearskies.columns.Integer()
        name = clearskies.columns.String()
        email = clearskies.columns.String()

    class UserLookup(clearskies.Schema):
        id = clearskies.columns.Integer()

    get_user = clearskies.endpoints.Get(
        model_class=User,
        input_schema=UserLookup,  # Validates routing_data["id"] as Integer
        transform_input_types=True,
        readable_column_names=["id", "name", "email"],
    )

    wsgi = clearskies.contexts.WsgiRef(get_user, classes=[User])
    wsgi()
    ```

    In this example:
    - `model_class=User` defines the data source (backend operations)
    - `input_schema=UserLookup` defines input validation for path parameters
    - Request `/users/abc` raises `InputError("id must be an integer")`
    - Request `/users/123` validates and transforms to `{"id": 123}` (int)

    ## When to Use input_schema vs model_class

    ### Use input_schema when:

    1. **Validating URL path parameters**: Ensure `/users/{id}` has proper type validation
    2. **Validating query parameters**: Ensure `?age=25` is validated as Integer
    3. **Input schema differs from model schema**: Admin endpoints may need different validation
    4. **No backend needed**: Pure validation without database operations

    ### model_class vs input_schema precedence:

    When both are provided:
    - `model_class` → Used for backend operations (fetch/save)
    - `input_schema` → Used for input validation (routing_data, query_parameters, request_data when set)
    - If `input_schema` is not set, `model_class` is used for both operations and validation

    ## Common Patterns

    ### Pattern 1: URL Path Validation

    ```python
    import clearskies

    class UserLookup(clearskies.Schema):
        id = clearskies.columns.Integer()

    delete_user = clearskies.endpoints.Delete(
        model_class=User,
        input_schema=UserLookup,
        transform_input_types=True,
    )
    ```

    URL `/users/abc` → `InputError("id must be an integer")`
    URL `/users/123` → Validates and deletes user with id=123

    ### Pattern 2: Query Parameter Validation

    ```python
    import clearskies

    class UserFilters(clearskies.Schema):
        age = clearskies.columns.Integer()
        active = clearskies.columns.Boolean()

    list_users = clearskies.endpoints.List(
        model_class=User,
        input_schema=UserFilters,
        transform_input_types=True,
        searchable_column_names=["age", "active"],
        readable_column_names=["id", "name", "age", "active"],
    )
    ```

    Query `?age=abc` → `InputError("age must be an integer")`
    Query `?age=25&active=true` → Validates and transforms to `{age: 25, active: True}`

    ### Pattern 3: Combined Input Validation

    ```python
    import clearskies

    class UserInput(clearskies.Schema):
        id = clearskies.columns.Integer()
        name = clearskies.columns.String(validators=[clearskies.validators.Required()])
        age = clearskies.columns.Integer(validators=[clearskies.validators.MinimumValue(0)])

    update_user = clearskies.endpoints.Update(
        model_class=User,
        input_schema=UserInput,
        transform_input_types=True,
        writeable_column_names=["name", "age"],
        readable_column_names=["id", "name", "age"],
    )
    ```

    This validates:
    - Path parameter: `/users/abc` → Error
    - Request body: `{"name": "", "age": -5}` → Errors for both fields

    ## See Also

    - `model_class`: Defines the data model and backend
    - `transform_input_types`: Enables type transformation for all inputs
    - `writeable_column_names`: Defines which columns can be set in request bodies
    """
    input_schema = configs.Schema(default=None)

    """
    Columns from the model class that should be returned to the client.

    Most endpoints use a model to build the return response to the user.  In this case, `readable_column_names`
    instructs the model what columns should be sent back to the user.  This information is similarly used when generating
    the documentation for the endpoint.

    ```python
    import clearskies

    class User(clearskies.Model):
        id_column_name = "id"
        backend = clearskies.backends.MemoryBackend()
        id = clearskies.columns.Uuid()
        name = clearskies.columns.String()
        secret = clearskies.columns.String()

    list_users = clearskies.endpoints.List(
        model_class=User,
        readable_column_names=["id", "name"],
        sortable_column_names=["id", "name"],
        default_sort_column_name="name",
    )

    wsgi = clearskies.contexts.WsgiRef(
        list_users,
        classes=[User],
        bindings={
            "memory_backend_default_data": [
                {
                    "model_class": User,
                    "records": [
                        {"id": "1-2-3-4", "name": "Bob", "secret": "Awesome dude"},
                        {"id": "1-2-3-5", "name": "Jane", "secret": "Gets things done"},
                        {"id": "1-2-3-6", "name": "Greg", "secret": "Loves chocolate"},
                    ]
                },
            ]
        }
    )
    wsgi()
    ```

    And then:

    ```bash
    $ curl 'http://localhost:8080'
    {
        "status": "success",
        "error": "",
        "data": [
            {
                "id": "1-2-3-4",
                "name": "Bob"
            },
            {
                "id": "1-2-3-6",
                "name": "Greg"
            },
            {
                "id": "1-2-3-5",
                "name": "Jane"
            }
        ],
        "pagination": {
            "number_results": 3,
            "limit": 50,
            "next_page": {}
        },
        "input_errors": {}
    }

    ```
    """
    readable_column_names = configs.ReadableModelColumns("model_class", default=[])

    """
    Specifies which columns from a model class can be set by the client.

    Many endpoints allow or require input from the client.  The most common way to provide input validation
    is by setting the model class and using `writeable_column_names` to specify which columns the end client can
    set.  Clearskies will then use the model schema to validate the input and also auto-generate documentation
    for the endpoint.

    ```python
    import clearskies

    class User(clearskies.Model):
        id_column_name = "id"
        backend = clearskies.backends.MemoryBackend()
        id = clearskies.columns.Uuid()
        name = clearskies.columns.String(validators=[clearskies.validators.Required()])
        date_of_birth = clearskies.columns.Date()

    send_user = clearskies.endpoints.Callable(
        lambda request_data: request_data,
        request_methods=["GET","POST"],
        writeable_column_names=["name", "date_of_birth"],
        model_class=User,
    )

    wsgi = clearskies.contexts.WsgiRef(send_user)
    wsgi()
    ```

    If we send a valid payload:

    ```bash
    $ curl 'http://localhost:8080' -d '{"name":"Jane","date_of_birth":"01/01/1990"}' | jq
    {
        "status": "success",
        "error": "",
        "data": {
            "name": "Jane",
            "date_of_birth": "01/01/1990"
        },
        "pagination": {},
        "input_errors": {}
    }
    ```

    And we can see the automatic input validation by sending some incorrect data:

    ```bash
    $ curl 'http://localhost:8080' -d '{"name":"","date_of_birth":"this is not a date","id":"hey"}' | jq
    {
        "status": "input_errors",
        "error": "",
        "data": [],
        "pagination": {},
        "input_errors": {
            "name": "'name' is required.",
            "date_of_birth": "given value did not appear to be a valid date",
            "other_column": "Input column other_column is not an allowed input column."
        }
    }
    ```

    """
    writeable_column_names = configs.WriteableModelColumns("model_class", default=[])

    """
    Columns from the model class that can be searched by the client.

    Sets which columns the client is allowed to search (for endpoints that support searching).
    """
    searchable_column_names = configs.SearchableModelColumns("model_class", default=[])

    """
    A function to call to add custom input validation logic.

    Typically, input validation happens by choosing the appropriate column in your schema and adding validators where necessary.  You
    can also create custom columns with their own input validation logic.  However, if desired, endpoints that accept user input also
    allow you to add callables for custom validation logic.  These functions should return a dictionary where the key name
    represents the name of the column that has invalid input, and the value is a human-readable error message.  If no input errors are
    found, then the callable should return an empty dictionary.  As usual, the callable can request any standard dependencies configured
    in the dependency injection container or proivded by input_output.get_context_for_callables.

    Note that most endpoints (such as Create and Update) explicitly require input.  As a result, if a request comes in without input
    from the end user, it will be rejected before calling your input validator.  In these cases you can depend on request_data always
    being a dictionary.  The Callable endpoint, however, only requires input if `writeable_column_names` is set.  If it's not set,
    and the end-user doesn't provide a request body, then request_data will be None.

    ```python
    import clearskies

    def check_input(request_data):
        if not request_data:
            return {}
        if request_data.get("name"):
            return {"name":"This is a privacy-preserving system, so please don't tell us your name"}
        return {}

    send_user = clearskies.endpoints.Callable(
        lambda request_data: request_data,
        request_methods=["GET", "POST"],
        input_validation_callable=check_input,
    )

    wsgi = clearskies.contexts.WsgiRef(send_user)
    wsgi()
    ```

    And when invoked:

    ```bash
    $ curl http://localhost:8080 -d '{"name":"sup"}' | jq
    {
        "status": "input_errors",
        "error": "",
        "data": [],
        "pagination": {},
        "input_errors": {
            "name": "This is a privacy-preserving system, so please don't tell us your name"
        }
    }

    $ curl http://localhost:8080 -d '{"hello":"world"}' | jq
    {
        "status": "success",
        "error": "",
        "data": {
            "hello": "world"
        },
        "pagination": {},
        "input_errors": {}
    }
    ```

    """
    input_validation_callable = configs.Callable(default=None)

    """
    A dictionary with columns that should override columns in the model.

    This is typically used to change column definitions on specific endpoints to adjust behavior: for intstance a model might use a `created_by_*`
    column to auto-populate some data, but an admin endpoint may need to override that behavior so the user can set it directly.

    This should be a dictionary with the column name as a key and the column itself as the value.  Note that you cannot use this to remove
    columns from the model.  In general, if you want a column not to be exposed through an endpoint, then all you have to do is remove
    that column from the list of writeable columns.

    ```python
    import clearskies

    endpoint = clearskies.Endpoint(
        column_overrides = {
            "name": clearskies.columns.String(validators=clearskies.validators.Required()),
        }
    )
    ```
    """
    column_overrides = configs.Columns(default={})

    """
    Used in conjunction with external_casing to change the casing of the key names in the outputted JSON of the endpoint.

    To use these, set internal_casing to the casing scheme used in your model, and then set external_casing to the casing
    scheme you want for your API endpoints.  clearskies will then automatically convert all output key names accordingly.
    Note that for callables, this only works when you return a model and set `readable_columns`.  If you set `writeable_columns`,
    it will also map the incoming data.

    The allowed casing schemas are:

     1. `snake_case`
     2. `camelCase`
     3. `TitleCase`

    By default internal_casing and external_casing are both set to 'snake_case', which means that no conversion happens.

    ```python
    import clearskies
    import datetime

    class User(clearskies.Model):
        id_column_name = "id"
        backend = clearskies.backends.MemoryBackend()
        id = clearskies.columns.Uuid()
        name = clearskies.columns.String()
        date_of_birth = clearskies.columns.Date()

    send_user = clearskies.endpoints.Callable(
        lambda users: users.create({"name":"Example","date_of_birth": datetime.datetime(2050, 1, 15)}),
        readable_column_names=["name", "date_of_birth"],
        internal_casing="snake_case",
        external_casing="TitleCase",
        model_class=User,
    )

    # because we're using name-based injection in our lambda callable (instead of type hinting) we have to explicitly
    # add the user model to the dependency injection container
    wsgi = clearskies.contexts.WsgiRef(send_user, classes=[User])
    wsgi()
    ```

    And then when called:

    ```bash
    $ curl http://localhost:8080  | jq
    {
        "Status": "Success",
        "Error": "",
        "Data": {
            "Name": "Example",
            "DateOfBirth": "2050-01-15"
        },
        "Pagination": {},
        "InputErrors": {}
    }
    ```
    """
    internal_casing = configs.Select(["snake_case", "camelCase", "TitleCase"], default="snake_case")

    """
    Used in conjunction with internal_casing to change the casing of the key names in the outputted JSON of the endpoint.

    See the docs for `internal_casing` for more details and usage examples.
    """
    external_casing = configs.Select(["snake_case", "camelCase", "TitleCase"], default="snake_case")

    """
    Enable transformation of input types for query parameters and routing data.

    By default (False), query parameters and URL path routing data remain as strings. When enabled (True),
    these values will be converted to their proper Python types based on the schema's column definitions,
    matching the behavior of request body transformation.

    ## Overview

    Clearskies automatically transforms string inputs from JSON request bodies into proper Python types
    (e.g., `{"age": "25"}` becomes `{"age": 25}`). However, query parameters and URL path parameters
    arrive as strings and by default remain as strings. This flag enables consistent type transformation
    across all input sources.

    ## What Gets Transformed

    When `transform_input_types=True`, values are converted based on their column types:

    - Request Body: Always transformed (default behavior)
    - Query Parameters: Transformed when flag is True
    - URL Path Parameters: Transformed when flag is True

    ## Supported Column Types

    The following column types support automatic type transformation:

    - **Integer**: `"25"` → `25`
    - **Float**: `"3.14"` → `3.14`
    - **Boolean**: `"true"` / `"false"` → `True` / `False`
    - **Date**: `"2025-01-15"` → `datetime.date(2025, 1, 15)`
    - **Datetime**: `"2025-01-15T10:30:00"` → `datetime.datetime(2025, 1, 15, 10, 30)`
    - **String**: No transformation (remains string)
    - **UUID**: No transformation (remains string, validated by column)

    ## Error Handling

    Invalid type conversions raise `InputErrors` with clear error messages:

    ```python
    # Query: ?age=abc
    # Result: InputError("age must be an integer")

    # Query: ?active=maybe
    # Result: InputError("active must be a boolean (true/false)")
    ```

    ## Usage by Endpoint Type

    ### List Endpoint

    Transforms query parameters used for filtering and searching:

    ```python
    import clearskies

    class User(clearskies.Model):
        id_column_name = "id"
        backend = clearskies.backends.MemoryBackend()
        id = clearskies.columns.Integer()
        name = clearskies.columns.String()
        age = clearskies.columns.Integer()
        active = clearskies.columns.Boolean()

    list_users = clearskies.endpoints.List(
        model_class=User,
        transform_input_types=True,
        searchable_column_names=["age", "active", "name"],
        sortable_column_names=["id", "name", "age"],
        readable_column_names=["id", "name", "age", "active"],
    )

    wsgi = clearskies.contexts.WsgiRef(list_users, classes=[User])
    wsgi()
    ```

    Query example:

    ```bash
    # Query: GET /users?age=25&active=true
    # Without flag: query_parameters = {"age": "25", "active": "true"}
    # With flag:    query_parameters = {"age": 25, "active": True}
    ```

    ### Get/Delete Endpoints

    Transforms URL path parameters used for record lookup:

    ```python
    import clearskies

    class User(clearskies.Model):
        id_column_name = "id"
        backend = clearskies.backends.MemoryBackend()
        id = clearskies.columns.Integer()
        name = clearskies.columns.String()

    get_user = clearskies.endpoints.Get(
        model_class=User,
        transform_input_types=True,
        readable_column_names=["id", "name"],
    )

    wsgi = clearskies.contexts.WsgiRef(get_user, classes=[User])
    wsgi()
    ```

    Path parameter example:

    ```bash
    # Request: GET /users/123
    # Without flag: routing_data = {"id": "123"}
    # With flag:    routing_data = {"id": 123}
    ```

    ### Update Endpoint

    Transforms both request body (always) and routing data (when flag enabled):

    ```python
    import clearskies

    class User(clearskies.Model):
        id_column_name = "id"
        backend = clearskies.backends.MemoryBackend()
        id = clearskies.columns.Integer()
        name = clearskies.columns.String()
        age = clearskies.columns.Integer()

    update_user = clearskies.endpoints.Update(
        model_class=User,
        transform_input_types=True,
        writeable_column_names=["name", "age"],
        readable_column_names=["id", "name", "age"],
    )

    wsgi = clearskies.contexts.WsgiRef(update_user, classes=[User])
    wsgi()
    ```

    Example:

    ```bash
    # Request: PATCH /users/123
    #          {"name": "Jane", "age": "30"}
    # Without flag: routing_data = {"id": "123"}, request_data = {"name": "Jane", "age": 30}
    # With flag:    routing_data = {"id": 123}, request_data = {"name": "Jane", "age": 30}
    ```

    ### Callable Endpoint

    Transforms query parameters and routing data (when flag enabled and schema provided):

    ```python
    import clearskies

    class UserSchema(clearskies.Schema):
        user_id = clearskies.columns.Integer()
        limit = clearskies.columns.Integer()

    def process_user(user_id, limit):
        # Both parameters are already integers
        return {"user_id": user_id, "limit": limit, "type": type(user_id).__name__}

    process = clearskies.endpoints.Callable(
        process_user,
        model_class=UserSchema,
        transform_input_types=True,
        url="/process/{user_id}",
    )

    wsgi = clearskies.contexts.WsgiRef(process)
    wsgi()
    ```

    Example:

    ```bash
    # Request: GET /process/123?limit=50
    # Without flag: user_id="123", limit="50"
    # With flag:    user_id=123, limit=50

    $ curl 'http://localhost:8080/process/123?limit=50' | jq
    {
        "status": "success",
        "error": "",
        "data": {
            "user_id": 123,
            "limit": 50,
            "type": "int"
        },
        "pagination": {},
        "input_errors": {}
    }
    ```

    ## Advanced: Search Operators

    The List endpoint supports search operators in query parameters. Type transformation applies to
    the values when the flag is enabled:

    ```python
    # Query: GET /users?age__gt=25&age__lt=50&active=true
    # Without flag: {"age__gt": "25", "age__lt": "50", "active": "true"}
    # With flag:    {"age__gt": 25, "age__lt": 50, "active": True}
    ```

    The operator suffix (e.g., `__gt`, `__lt`) is preserved, and the column name is extracted
    to determine the appropriate type transformation.

    ## Migration Guide

    If you have existing code that manually converts types, you can simplify it with this flag:

    ```python
    # Old code (manual conversion)
    def process(query_parameters, routing_data):
        age = int(query_parameters.get("age", "0"))
        user_id = int(routing_data["id"])
        active = query_parameters.get("active", "false") == "true"
        return {"age": age, "user_id": user_id, "active": active}

    # New code (with transform_input_types=True)
    def process(query_parameters, routing_data):
        age = query_parameters.get("age", 0)
        user_id = routing_data["id"]
        active = query_parameters.get("active", False)
        return {"age": age, "user_id": user_id, "active": active}
    ```

    ## Edge Cases

    ### Empty Values

    Empty query parameters are treated as `None`:

    ```python
    # Query: ?age=
    # Result: {"age": None}
    ```

    ### Multiple Values

    Lists of values are not transformed (remain as list of strings):

    ```python
    # Query: ?tags=python&tags=flask
    # Result: {"tags": ["python", "flask"]}
    ```

    ### Invalid Columns

    Parameters not matching model columns are left as-is:

    ```python
    # Query: ?age=25&unknown=value
    # Result: {"age": 25, "unknown": "value"}  # age transformed, unknown left as string
    ```

    ## Backward Compatibility

    This flag defaults to `False` for backward compatibility. Code that depends on query parameters
    or routing data being strings will continue to work. Enable it only when you're ready to handle
    properly typed values.

    In a future major version (v3.0), this may become the default behavior.

    ## See Also

    - `writeable_column_names`: Defines which columns can be set in request bodies
    - `searchable_column_names`: Defines which columns can be filtered in List endpoints
    - `readable_column_names`: Defines which columns are returned to the client
    """
    transform_input_types = configs.Boolean(default=False)

    """
    Configure standard security headers to be sent along in the response from this endpoint.

    Note that, with CORS, you generally only have to specify the origin.  The routing system will automatically add
    in the appropriate HTTP verbs, and the authorization classes will add in the appropriate headers.

    ```python
    import clearskies

    hello_world = clearskies.endpoints.Callable(
        lambda: {"hello": "world"},
        request_methods=["PATCH", "POST"],
        authentication=clearskies.authentication.SecretBearer(environment_key="MY_SECRET"),
        security_headers=[
            clearskies.security_headers.Hsts(),
            clearskies.security_headers.Cors(origin="https://example.com"),
        ],
    )

    wsgi = clearskies.contexts.WsgiRef(hello_world)
    wsgi()
    ```

    And then execute the options endpoint to see all the security headers:

    ```bash
    $ curl -v http://localhost:8080 -X OPTIONS
    * Host localhost:8080 was resolved.
    < HTTP/1.0 200 Ok
    < Server: WSGIServer/0.2 CPython/3.11.6
    < ACCESS-CONTROL-ALLOW-METHODS: PATCH, POST
    < ACCESS-CONTROL-ALLOW-HEADERS: Authorization
    < ACCESS-CONTROL-MAX-AGE: 5
    < ACCESS-CONTROL-ALLOW-ORIGIN: https://example.com
    < STRICT-TRANSPORT-SECURITY: max-age=31536000 ;
    < CONTENT-TYPE: application/json; charset=UTF-8
    < Content-Length: 0
    <
    * Closing connection
    ```

    """
    security_headers = configs.SecurityHeaders(default=[])

    """
    A description for this endpoint.  This is added to any auto-documentation
    """
    description = configs.String(default="")

    """
    Whether or not the routing data should also be persisted to the model.  Defaults to False.

    Note: this is only relevant for handlers that accept request data
    """
    include_routing_data_in_request_data = configs.Boolean(default=False)

    """
    Additional conditions to always add to the results.

    where should be a single item or a list of items containing one of three things:

      1. Conditions expressed as a string (e.g. `"name=example"`, `"age>5"`)
      2. Queries built with a column (e.g. `SomeModel.name.equals("example")`, `SomeModel.age.greater_than(5)`)
      3. A callable which accepts and returns the mode (e.g. `lambda model: model.where("name=example")`)

    Here's an example:

    ```python
    import clearskies

    class Student(clearskies.Model):
        backend = clearskies.backends.MemoryBackend()
        id_column_name = "id"

        id = clearskies.columns.Uuid()
        name = clearskies.columns.String()
        grade = clearskies.columns.Integer()
        will_graduate = clearskies.columns.Boolean()

    wsgi = clearskies.contexts.WsgiRef(
        clearskies.endpoints.List(
            Student,
            readable_column_names=["id", "name", "grade"],
            sortable_column_names=["name", "grade"],
            default_sort_column_name="name",
            where=["grade<10", Student.will_graduate.equals(True)],
        ),
        bindings={
            "memory_backend_default_data": [
                {
                    "model_class": Student,
                    "records": [
                        {"id": "1-2-3-4", "name": "Bob", "grade": 5, "will_graduate": True},
                        {"id": "1-2-3-5", "name": "Jane", "grade": 3, "will_graduate": True},
                        {"id": "1-2-3-6", "name": "Greg", "grade": 3, "will_graduate": False},
                        {"id": "1-2-3-7", "name": "Bob", "grade": 2, "will_graduate": True},
                        {"id": "1-2-3-8", "name": "Ann", "grade": 12, "will_graduate": True},
                    ],
                },
            ],
        },
    )
    wsgi()
    ```

    Which you can invoke:

    ```bash
    $ curl 'http://localhost:8080/' | jq
    {
        "status": "success",
        "error": "",
        "data": [
            {
                "id": "1-2-3-4",
                "name": "Bob",
                "grade": 5
            },
            {
                "id": "1-2-3-7",
                "name": "Bob",
                "grade": 2
            },
            {
                "id": "1-2-3-5",
                "name": "Jane",
                "grade": 3
            }
        ],
        "pagination": {},
        "input_errors": {}
    }
    ```
    and note that neither Greg nor Ann are returned.  Ann because she doesn't make the grade criteria, and Greg because
    he won't graduate.
    """
    where = configs.Conditions(default=[])

    """
    Additional joins to always add to the query.

    ```python
    import clearskies

    class Student(clearskies.Model):
        backend = clearskies.backends.MemoryBackend()
        id_column_name = "id"

        id = clearskies.columns.Uuid()
        name = clearskies.columns.String()
        grade = clearskies.columns.Integer()
        will_graduate = clearskies.columns.Boolean()

    class PastRecord(clearskies.Model):
        backend = clearskies.backends.MemoryBackend()
        id_column_name = "id"

        id = clearskies.columns.Uuid()
        student_id = clearskies.columns.BelongsToId(Student)
        school_name = clearskies.columns.String()

    wsgi = clearskies.contexts.WsgiRef(
        clearskies.endpoints.List(
            Student,
            readable_column_names=["id", "name", "grade"],
            sortable_column_names=["name", "grade"],
            default_sort_column_name="name",
            joins=["INNER JOIN past_records ON past_records.student_id=students.id"],
        ),
        bindings={
            "memory_backend_default_data": [
                {
                    "model_class": Student,
                    "records": [
                        {"id": "1-2-3-4", "name": "Bob", "grade": 5, "will_graduate": True},
                        {"id": "1-2-3-5", "name": "Jane", "grade": 3, "will_graduate": True},
                        {"id": "1-2-3-6", "name": "Greg", "grade": 3, "will_graduate": False},
                        {"id": "1-2-3-7", "name": "Bob", "grade": 2, "will_graduate": True},
                        {"id": "1-2-3-8", "name": "Ann", "grade": 12, "will_graduate": True},
                    ],
                },
                {
                    "model_class": PastRecord,
                    "records": [
                        {"id": "5-2-3-4", "student_id": "1-2-3-4", "school_name": "Best Academy"},
                        {"id": "5-2-3-5", "student_id": "1-2-3-5", "school_name": "Awesome School"},
                    ],
                },
            ],
        },
    )
    wsgi()
    ```

    Which when invoked:

    ```bash
    $ curl 'http://localhost:8080/' | jq
    {
        "status": "success",
        "error": "",
        "data": [
            {
                "id": "1-2-3-4",
                "name": "Bob",
                "grade": 5
            },
            {
                "id": "1-2-3-5",
                "name": "Jane",
                "grade": 3
            }
        ],
        "pagination": {},
        "input_errors": {}
    }
    ```

    e.g., the inner join reomves all the students that don't have an entry in the PastRecord model.

    """
    joins = configs.Joins(default=[])

    cors_header: Cors = None  # type: ignore
    _model: Model = None  # type: ignore
    _columns: dict[str, column.Column] = None  # type: ignore
    _readable_columns: dict[str, column.Column] = None  # type: ignore
    _writeable_columns: dict[str, column.Column] = None  # type: ignore
    _searchable_columns: dict[str, column.Column] = None  # type: ignore
    _sortable_columns: dict[str, column.Column] = None  # type: ignore
    _as_json_map: dict[str, column.Column] = None  # type: ignore

    @decorators.parameters_to_properties
    def __init__(
        self,
        url: str = "",
        request_methods: list[str] = ["GET"],
        response_headers: list[str | Callable[..., list[str]]] = [],
        output_map: Callable[..., dict[str, Any]] | None = None,
        input_schema: Schema | type[Schema] | None = None,
        column_overrides: dict[str, Column] = {},
        internal_casing: str = "snake_case",
        external_casing: str = "snake_case",
        security_headers: list[SecurityHeader] = [],
        description: str = "",
        authentication: Authentication = Public(),
        authorization: Authorization = Authorization(),
    ):
        self.finalize_and_validate_configuration()
        for security_header in self.security_headers:
            if not security_header.is_cors:
                continue
            self.cors_header = security_header  # type: ignore
            self.has_cors = True
            break

    @property
    def model(self) -> Model:
        if self._model is None:
            self._model = self.di.build(self.model_class)
        return self._model

    @property
    def columns(self) -> dict[str, Column]:
        if self._columns is None:
            self._columns = self.model.get_columns()
        return self._columns

    @property
    def readable_columns(self) -> dict[str, Column]:
        if self._readable_columns is None:
            self._readable_columns = {name: self.columns[name] for name in self.readable_column_names}
        return self._readable_columns

    @property
    def writeable_columns(self) -> dict[str, Column]:
        if self._writeable_columns is None:
            self._writeable_columns = {name: self.columns[name] for name in self.writeable_column_names}
        return self._writeable_columns

    @property
    def searchable_columns(self) -> dict[str, Column]:
        if self._searchable_columns is None:
            self._searchable_columns = {name: self._columns[name] for name in self.sortable_column_names}
        return self._searchable_columns

    @property
    def sortable_columns(self) -> dict[str, Column]:
        if self._sortable_columns is None:
            self._sortable_columns = {name: self._columns[name] for name in self.sortable_column_names}
        return self._sortable_columns

    def get_request_data(self, input_output: InputOutput, required=True) -> dict[str, Any]:
        if not input_output.request_data:
            if input_output.has_body():
                raise exceptions.ClientError("Request body was not valid JSON")
            raise exceptions.ClientError("Missing required JSON body")
        if not isinstance(input_output.request_data, dict):
            raise exceptions.ClientError("Request body was not a JSON dictionary.")

        return {
            **input_output.request_data,  # type: ignore
            **(input_output.routing_data if self.include_routing_data_in_request_data else {}),
        }

    def fetch_model_with_base_query(self, input_output: InputOutput) -> Model:
        model = self.model
        for join in self.joins:
            if callable(join):
                model = self.di.call_function(join, model=model, **input_output.get_context_for_callables())
            else:
                model = model.join(join)
        for where in self.where:
            if callable(where):
                model = self.di.call_function(where, model=model, **input_output.get_context_for_callables())
            else:
                model = model.where(where)
        model = model.where_for_request_all(
            model,
            input_output,
            input_output.routing_data,
            input_output.authorization_data,
            overrides=self.column_overrides,
        )
        return self.authorization.filter_model(model, input_output.authorization_data, input_output)

    def matches_request(self, input_output: InputOutput, allow_partial=False) -> bool:
        """Whether or not we can handle an incoming request based on URL and request method."""
        # soo..... this excessively duplicates the logic in populate_routing_data, but I'm being lazy right now
        # and not fixing it.
        if input_output.supports_request_method:
            request_method = input_output.request_method.upper()
            if request_method == "OPTIONS":
                return True
            if request_method not in self.request_methods:
                return False
        if input_output.supports_url:
            expected_url = self.url.strip("/")
            incoming_url = input_output.get_full_path().strip("/")
            if not expected_url and not incoming_url:
                return True

            matches, routing_data = routing.match_route(expected_url, incoming_url, allow_partial=allow_partial)
            return matches
        return True

    def populate_routing_data(self, input_output: InputOutput) -> Any:
        # matches_request is only checked by the endpoint group, not by the context.  As a result, we need to check our
        # route.  However we always have to check our route anyway because the full routing data can only be figured
        # out at the endpoint level, so calling out to routing.mattch_route is unavoidable.
        if input_output.supports_request_method:
            request_method = input_output.request_method.upper()
            if request_method == "OPTIONS":
                return self.cors(input_output)
            if request_method not in self.request_methods:
                return self.error(input_output, "Not Found", 404)
        if input_output.supports_url:
            expected_url = self.url.strip("/")
            incoming_url = input_output.get_full_path().strip("/")
            if expected_url or incoming_url:
                matches, routing_data = routing.match_route(expected_url, incoming_url, allow_partial=False)
                if not matches:
                    return self.error(input_output, "Not Found", 404)

                input_output.routing_data = routing_data

    def failure(self, input_output: InputOutput) -> Any:
        return self.respond_json(input_output, {"status": "failure"}, 500)

    def redirect(self, input_output: InputOutput, location: str, status_code: int) -> Any:
        """Return a redirect."""
        input_output.response_headers.add("content-type", "text/html")
        input_output.response_headers.add("location", location)
        return self.respond(
            input_output,
            '<meta http-equiv="refresh" content="0; url=' + urllib.parse.quote(location) + '">Redirecting',
            status_code,
        )

    def success(
        self,
        input_output: InputOutput,
        data: dict[str, Any] | list[Any],
        number_results: int | None = None,
        limit: int | None = None,
        next_page: Any = None,
    ) -> Any:
        """Return a successful response."""
        response_data = {"status": "success", "data": data, "pagination": {}}

        if next_page or number_results:
            if number_results is not None:
                for value in [number_results, limit]:
                    if value is not None and type(value) != int:
                        raise ValueError("number_results and limit must all be integers")

            response_data["pagination"] = {
                "number_results": number_results,
                "limit": limit,
                "next_page": next_page,
            }

        return self.respond_json(input_output, response_data, 200)

    def model_as_json(self, model: Model, input_output: InputOutput) -> dict[str, Any]:
        if self.output_map:
            return self.di.call_function(self.output_map, model=model, **input_output.get_context_for_callables())

        if self._as_json_map is None:
            self._as_json_map = self._build_as_json_map(model)

        json = OrderedDict()
        for output_name, column in self._as_json_map.items():
            column_data = column.to_json(model)
            if len(column_data) == 1:
                json[output_name] = list(column_data.values())[0]
            else:
                for key, value in column_data.items():
                    json[self.auto_case_column_name(key, True)] = value
        return json

    def _build_as_json_map(self, model: Model) -> dict[str, column.Column]:
        conversion_map = {}
        if not self.readable_column_names:
            raise ValueError(
                "I was asked to convert a model to JSON but I wasn't provided with `readable_column_names'"
            )
        for column in self.readable_columns.values():
            conversion_map[self.auto_case_column_name(column.name, True)] = column
        return conversion_map

    def validate_input_against_schema(
        self, request_data: dict[str, Any], input_output: InputOutput, schema: Schema | type[Schema]
    ) -> None:
        if not self.writeable_column_names:
            raise ValueError(
                f"I was asked to validate input against a schema, but no writeable columns are defined, so I can't :(  This is probably a bug in the endpoint class - {self.__class__.__name__}."
            )
        request_data = self.map_request_data_external_to_internal(request_data)
        self.find_input_errors(request_data, input_output, schema)

    def transform_request_data(
        self, request_data: dict[str, Any], schema: Schema | type[Schema] | None = None
    ) -> dict[str, Any]:
        """
        Transform request data to proper types using the schema's column definitions.

        After validation passes, this method converts string values (or other input types)
        to their proper Python types as defined by the schema columns. For example:
        - "25" becomes int(25) for Integer columns
        - "true" becomes bool(True) for Boolean columns
        - "2024-12-31" becomes a date object for Date columns

        If no schema is provided, the request_data is returned unchanged.
        """
        if not request_data or not schema:
            return request_data

        columns = schema.get_columns()
        transformed_data = {}

        for key, value in request_data.items():
            if key in columns and value is not None:
                # Use the column's to_backend method to convert types
                # This is the same method used when saving to a model
                column_data = columns[key].to_backend({key: value})
                transformed_data[key] = column_data.get(key, value)
            else:
                transformed_data[key] = value

        return transformed_data

    def transform_query_parameters(
        self, query_params: dict[str, Any], schema: Schema | type[Schema] | None = None
    ) -> dict[str, Any]:
        """
        Transform query parameters to proper types based on searchable columns.

        This method is only applied when transform_input_types=True. It transforms string query
        parameters to their proper Python types using the schema's column definitions.

        Handles:
        - Simple filters: ?age=25 -> {"age": 25}
        - Operators: ?age__gt=25 -> {"age__gt": 25} (validates value against column type)
        - Pagination: ?limit=50 -> {"limit": 50}

        Args:
            query_params: Raw query parameters from the request (typically all strings)
            schema: The model class or schema to use for type conversion (optional, defaults to input_schema or model_class)

        Returns:
            Dictionary with values transformed to proper Python types
        """
        # Prefer input_schema over model_class for validation
        if schema is None:
            schema = self.input_schema if self.input_schema else self.model_class

        if not query_params or not schema:
            return query_params

        transformed = {}
        columns = schema.get_columns()

        for key, value in query_params.items():
            # Handle operators like age__gt, age__lt, etc.
            column_name = key.split("__")[0] if "__" in key else key

            # Transform searchable column values
            if column_name in self.searchable_column_names and column_name in columns:
                column = columns[column_name]
                try:
                    # Use to_backend to transform the value
                    column_data = column.to_backend({column_name: value})
                    transformed[key] = column_data.get(column_name, value)
                except (ValueError, TypeError):
                    # If transformation fails, raise an input error
                    raise exceptions.InputErrors(
                        {key: f"Invalid value for {column_name}: expected {column.__class__.__name__} type"}
                    )
            # Transform pagination parameters
            elif key in ["limit", "start"]:
                try:
                    transformed[key] = int(value) if value is not None else value
                except (ValueError, TypeError):
                    raise exceptions.InputErrors({key: f"{key} must be an integer"})
            else:
                # Keep other parameters as-is (like sort_by, sort_direction)
                transformed[key] = value

        return transformed

    def transform_routing_data(
        self, routing_data: dict[str, Any], schema: Schema | type[Schema] | None = None
    ) -> dict[str, Any]:
        """
        Transform URL path parameters to proper types.

        This method is only applied when transform_input_types=True. It transforms string URL
        path parameters to their proper Python types using the schema's column definitions.

        Examples:
        - /users/123 with Integer id column: {"id": "123"} -> {"id": 123}
        - /users/a-b-c-d with UUID id column: {"id": "a-b-c-d"} -> {"id": "a-b-c-d"} (stays string)
        - /users/{user_id}/posts/{post_id}: Both IDs transformed based on their column types

        Args:
            routing_data: Raw routing data from URL path (typically all strings)
            schema: The model class or schema to use for type conversion (optional, defaults to input_schema or model_class)

        Returns:
            Dictionary with values transformed to proper Python types
        """
        # Prefer input_schema over model_class for validation
        if schema is None:
            schema = self.input_schema if self.input_schema else self.model_class

        if not routing_data or not schema:
            return routing_data

        transformed = {}
        columns = schema.get_columns()

        for key, value in routing_data.items():
            # Only transform if the key exists in the schema columns
            if key in columns:
                column = columns[key]
                try:
                    # Use to_backend to transform the value
                    column_data = column.to_backend({key: value})
                    transformed[key] = column_data.get(key, value)
                except (ValueError, TypeError):
                    # If transformation fails, raise an input error
                    raise exceptions.InputErrors(
                        {key: f"Invalid value for {key}: expected {column.__class__.__name__} type"}
                    )
            else:
                # Keep parameters that aren't in the schema as-is
                transformed[key] = value

        return transformed

    def map_request_data_external_to_internal(self, request_data, required=True):
        # we have to map from internal names to external names, because case mapping
        # isn't always one-to-one, so we want to do it exactly the same way that the documentation
        # is built.
        key_map = {self.auto_case_column_name(key, True): key for key in self.writeable_column_names}

        # and make sure we don't drop any data along the way, because the input validation
        # needs to return an error for unexpected data.
        return {key_map.get(key, key): value for (key, value) in request_data.items()}

    def find_input_errors(
        self, request_data: dict[str, Any], input_output: InputOutput, schema: Schema | type[Schema]
    ) -> None:
        input_errors: dict[str, str] = {}
        columns = schema.get_columns()
        model = self.di.build(schema) if inspect.isclass(schema) else schema
        for column_name in self.writeable_column_names:
            column = columns[column_name]
            input_errors = {
                **input_errors,
                **column.input_errors(model, request_data),  # type: ignore
            }
        input_errors = {
            **input_errors,
            **self.find_input_errors_from_callable(request_data, input_output),
        }
        for extra_column_name in set(request_data.keys()) - set(self.writeable_column_names):
            external_column_name = self.auto_case_column_name(extra_column_name, False)
            input_errors[external_column_name] = f"Input column {external_column_name} is not an allowed input column."
        if input_errors:
            raise exceptions.InputErrors(input_errors)

    def find_input_errors_from_callable(
        self, request_data: dict[str, Any] | list[Any] | None, input_output: InputOutput
    ) -> dict[str, str]:
        if not self.input_validation_callable:
            return {}

        more_input_errors = self.di.call_function(
            self.input_validation_callable, **input_output.get_context_for_callables()
        )
        if not isinstance(more_input_errors, dict):
            raise ValueError("The input error callable did not return a dictionary as required")
        return more_input_errors

    def cors(self, input_output: InputOutput):
        cors_header = self.cors_header if self.cors_header else Cors()
        for method in self.request_methods:
            cors_header.add_method(method)
        if self.authentication:
            self.authentication.set_headers_for_cors(cors_header)
        cors_header.set_headers_for_input_output(input_output)
        for security_header in self.security_headers:
            if security_header.is_cors:
                continue
            security_header.set_headers_for_input_output(input_output)
        return input_output.respond("", 200)

    def documentation(self) -> list[Request]:
        return []

    def documentation_components(self) -> dict[str, Any]:
        return {
            "models": self.documentation_models(),
            "securitySchemes": self.documentation_security_schemes(),
        }

    def documentation_security_schemes(self) -> dict[str, Any]:
        if not self.authentication or not self.authentication.documentation_security_scheme_name():
            return {}

        return {
            self.authentication.documentation_security_scheme_name(): (
                self.authentication.documentation_security_scheme()
            ),
        }

    def documentation_models(self) -> dict[str, schema.Schema]:
        return {}

    def documentation_pagination_response(self, include_pagination=True) -> schema.Schema:
        if not include_pagination:
            return schema.Object(self.auto_case_internal_column_name("pagination"), [], value={})
        model = self.di.build(self.model_class)
        return schema.Object(
            self.auto_case_internal_column_name("pagination"),
            [
                schema.Integer(self.auto_case_internal_column_name("number_results"), example=10),
                schema.Integer(self.auto_case_internal_column_name("limit"), example=100),
                schema.Object(
                    self.auto_case_internal_column_name("next_page"),
                    model.documentation_pagination_next_page_response(self.auto_case_internal_column_name),
                    model.documentation_pagination_next_page_example(self.auto_case_internal_column_name),
                ),
            ],
        )

    def documentation_success_response(
        self, data_schema: schema.Object | schema.Array, description: str = "", include_pagination: bool = False
    ) -> Response:
        return Response(
            200,
            schema.Object(
                "body",
                [
                    schema.String(self.auto_case_internal_column_name("status"), value="success"),
                    data_schema,
                    self.documentation_pagination_response(include_pagination=include_pagination),
                    schema.String(self.auto_case_internal_column_name("error"), value=""),
                    schema.Object(self.auto_case_internal_column_name("input_errors"), [], value={}),
                ],
            ),
            description=description,
        )

    def documentation_generic_error_response(self, description="Invalid Call", status=400) -> Response:
        return Response(
            status,
            schema.Object(
                "body",
                [
                    schema.String(self.auto_case_internal_column_name("status"), value="error"),
                    schema.Object(self.auto_case_internal_column_name("data"), [], value={}),
                    self.documentation_pagination_response(include_pagination=False),
                    schema.String(self.auto_case_internal_column_name("error"), example="User readable error message"),
                    schema.Object(self.auto_case_internal_column_name("input_errors"), [], value={}),
                ],
            ),
            description=description,
        )

    def documentation_input_error_response(self, description="Invalid client-side input") -> Response:
        email_example = self.auto_case_internal_column_name("email")
        return Response(
            200,
            schema.Object(
                "body",
                [
                    schema.String(self.auto_case_internal_column_name("status"), value="input_errors"),
                    schema.Object(self.auto_case_internal_column_name("data"), [], value={}),
                    self.documentation_pagination_response(include_pagination=False),
                    schema.String(self.auto_case_internal_column_name("error"), value=""),
                    schema.Object(
                        self.auto_case_internal_column_name("input_errors"),
                        [schema.String("[COLUMN_NAME]", example="User friendly error message")],
                        example={email_example: f"{email_example} was not a valid email address"},
                    ),
                ],
            ),
            description=description,
        )

    def documentation_access_denied_response(self) -> Response:
        return self.documentation_generic_error_response(description="Access Denied", status=401)

    def documentation_unauthorized_response(self) -> Response:
        return self.documentation_generic_error_response(description="Unauthorized", status=403)

    def documentation_not_found(self) -> Response:
        return self.documentation_generic_error_response(description="Not Found", status=404)

    def documentation_request_security(self):
        authentication = self.authentication
        name = authentication.documentation_security_scheme_name()
        return [{name: []}] if name else []

    def documentation_data_schema(
        self, schema: type[Schema] | None = None, column_names: list[str] = []
    ) -> list[schema.Schema]:
        if schema is None:
            schema = self.model_class
        readable_column_names = [*column_names]
        if not readable_column_names and self.readable_column_names:
            readable_column_names: list[str] = self.readable_column_names  # type: ignore
        properties = []

        columns = schema.get_columns()
        for column_name in readable_column_names:
            column = columns[column_name]
            for doc in column.documentation():
                doc.name = self.auto_case_internal_column_name(doc.name)
                properties.append(doc)

        return properties

    def standard_json_request_parameters(
        self, schema: type[Schema] | None = None, column_names: list[str] = []
    ) -> list[Parameter]:
        if not column_names:
            if not self.writeable_column_names:
                return []
            column_names = self.writeable_column_names

        if not schema:
            if not self.model_class:
                return []
            schema = self.model_class

        model_name = string.camel_case_to_snake_case(schema.__name__)
        columns = schema.get_columns()
        parameters = []
        for column_name in column_names:
            columns[column_name].injectable_properties(self.di)
            parameters.append(
                autodoc.request.JSONBody(
                    columns[column_name].documentation(name=self.auto_case_column_name(column_name, True)),
                    description=f"Set '{column_name}' for the {model_name}",
                    required=columns[column_name].is_required,
                )
            )
        return parameters  # type: ignore

    def documentation_url_parameters(self) -> list[Parameter]:
        parameter_names = routing.extract_url_parameter_name_map(self.url.strip("/"))
        return [
            autodoc.request.URLPath(
                autodoc.schema.String(parameter_name),
                description=f"The {parameter_name}.",
                required=True,
            )
            for parameter_name in parameter_names.keys()
        ]
