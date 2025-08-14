from __future__ import annotations

import inspect
from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Callable, Type

import clearskies.autodoc
import clearskies.configs
import clearskies.exceptions
from clearskies import authentication, autodoc, typing
from clearskies.authentication import Authentication, Authorization
from clearskies.endpoint import Endpoint
from clearskies.input_outputs import InputOutput

if TYPE_CHECKING:
    from clearskies import Column, SecurityHeader
    from clearskies.model import Model


class Schema(Endpoint):
    """
    An endpoint that automatically creates a swagger doc for the application

    The schema endpoint must always be attached to an endpoint group.  It will document all endpoints
    attached to its parent endpoint group.

    Keep in mind that the routing in the endpoint group is greedy and goes from top-down.  As a result,
    since the schema endpoint (typically) has a specific URL, it's usually best for it to be at the top
    of your endpoint list.  The following example builds an application with two endpoint groups, each
    of which has a schema endpoint:

    ```
    import clearskies
    from clearskies.validators import Required, Unique
    from clearskies import columns


    class User(clearskies.Model):
        id_column_name = "id"
        backend = clearskies.backends.MemoryBackend()

        id = columns.Uuid()
        name = columns.String(validators=[Required()])
        username = columns.String(
            validators=[
                Required(),
                Unique(),
            ]
        )
        age = columns.Integer(validators=[Required()])
        company_name = columns.String()
        created_at = columns.Created()
        updated_at = columns.Updated()


    readable_column_names = [
        "id",
        "name",
        "username",
        "age",
        "company_name",
        "created_at",
        "updated_at",
    ]
    writeable_user_column_names = ["name", "username", "age", "company_name"]
    users_api = clearskies.EndpointGroup(
        [
            clearskies.endpoints.Schema(url="schema"),
            clearskies.endpoints.RestfulApi(
                url="users",
                model_class=User,
                readable_column_names=readable_column_names,
                writeable_column_names=writeable_user_column_names,
                sortable_column_names=readable_column_names,
                searchable_column_names=readable_column_names,
                default_sort_column_name="name",
            )
        ],
        url="/users",
    )

    class SomeThing(clearskies.Model):
        id_column_name = "id"
        backend = clearskies.backends.MemoryBackend()

        id = clearskies.columns.Uuid()
        thing_1 = clearskies.columns.String(validators=[Required()])
        thing_2 = clearskies.columns.String(validators=[Unique()])

    more_endpoints = clearskies.EndpointGroup(
        [
            clearskies.endpoints.HealthCheck(url="health"),
            clearskies.endpoints.Schema(url="schema"),
            clearskies.endpoints.Callable(
                lambda request_data, some_things: some_things.create(request_data),
                model_class=SomeThing,
                readable_column_names=["id", "thing_1", "thing_2"],
                writeable_column_names=["thing_1", "thing_2"],
                request_methods=["POST"],
                url="some_thing",
            ),
            users_api,
        ]
    )

    wsgi = clearskies.contexts.WsgiRef(more_endpoints)
    wsgi()
    ```

    We attach the `more_endpoints` endpoint group to our context, and this contains 4 endpoints:

     1. A healthcheck
     2. A schema endpoint
     3. A callable endpoint
     4. The `users_api` endpoint group.

    The `users_api` endpoint group then contains it's own schema endpoint and a restful api endpoint
    with all our standard user CRUD operations.  As a result, we can fetch two different schema endpoints:

    ```
    curl 'http://localhost/schema'

    curl 'http://localhost/users/schema'
    ```

    The former documents all endpoints in the system.  The latter only documents the endpoints under the `/users`
    path provided by the `users_api` endpoint group.
    """

    """
    The doc builder class/format to use
    """
    schema_format = clearskies.configs.Any(default=clearskies.autodoc.formats.oai3_json.Oai3Json)

    """
    Addiional data to inject into the schema doc.

    This is typically used for setting info/server settings in the resultant swagger doc.  Anything
    in this dictionary is injected into the "root" of the generated documentation file.
    """
    schema_configuration = clearskies.configs.AnyDict(default={})

    @clearskies.decorators.parameters_to_properties
    def __init__(
        self,
        url: str,
        schema_format=clearskies.autodoc.formats.oai3_json.Oai3Json,
        request_methods: list[str] = ["GET"],
        response_headers: list[str | Callable[..., list[str]]] = [],
        security_headers: list[SecurityHeader] = [],
        schema_configuration: dict[str, Any] = {},
        authentication: Authentication = authentication.Public(),
    ):
        # we need to call the parent but don't have to pass along any of our kwargs.  They are all optional in our parent, and our parent class
        # just stores them in parameters, which we have already done.  However, the parent does do some extra initialization stuff that we need,
        # which is why we have to call the parent.
        super().__init__()

    def handle(self, input_output: InputOutput) -> Any:
        current_endpoint_groups = self.di.build_from_name("endpoint_groups", cache=True)
        if not current_endpoint_groups:
            raise ValueError(
                f"{self.__class__.__name__} endpoint was attached directly to the context, but it must be attached to an endpoint group (otherwise it has no application to document)."
            )

        # the endpoint group at the end of the list is the one that invoked us.  Let's grab it
        # if we don't hvae any endpoint groups then we've been attached directly to a context,
        # which is pointless - there's nothing for us to document.  So, treat it as an error.
        endpoint_group = current_endpoint_groups[-1]
        requests: list[Any] = []
        models: dict[str, Any] = {}
        security_schemes: dict[str, Any] = {}
        for endpoint in endpoint_group.all_endpoints():
            requests.extend(endpoint.documentation())
            models = {**models, **endpoint.documentation_models()}
            # if "user" in models:
            # print(models["user"].children)
            # print(endpoint.__class__.__name__)
            security_schemes = {**security_schemes, **endpoint.documentation_security_schemes()}
        # print(models["user"].children)

        schema = self.di.build(self.schema_format)
        schema.set_requests(requests)
        schema.set_components({"models": models, "securitySchemes": security_schemes})
        extra_schema_config = {**self.schema_configuration}
        if "info" not in extra_schema_config:
            extra_schema_config["info"] = {"title": "Auto generated by clearskies", "version": "1.0"}
        self.add_response_headers(input_output)
        return input_output.respond(schema.pretty(root_properties=extra_schema_config), 200)
