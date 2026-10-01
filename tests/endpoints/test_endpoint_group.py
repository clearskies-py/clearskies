import clearskies
from clearskies import columns
from clearskies.contexts import Context
from clearskies.validators import Required, Unique
from tests.test_base import TestBase


class EndpointGroupTest(TestBase):
    def test_overview(self):
        class Company(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = columns.Uuid()
            name = columns.String(
                validators=[
                    Required(),
                    Unique(),
                ]
            )

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
            created_at = columns.Created()
            updated_at = columns.Updated()
            company_id = columns.BelongsToId(
                Company,
                readable_parent_columns=["id", "name"],
                validators=[Required()],
            )
            company = columns.BelongsToModel("company_id")

        readable_user_column_names = ["id", "name", "username", "age", "created_at", "updated_at", "company"]
        writeable_user_column_names = ["name", "username", "age", "company_id"]
        users_api = clearskies.EndpointGroup(
            [
                clearskies.endpoints.Update(
                    model_class=User,
                    url="/:id",
                    readable_column_names=readable_user_column_names,
                    writeable_column_names=writeable_user_column_names,
                ),
                clearskies.endpoints.Delete(
                    model_class=User,
                    url="/:id",
                ),
                clearskies.endpoints.Get(
                    model_class=User,
                    url="/:id",
                    readable_column_names=readable_user_column_names,
                ),
                clearskies.endpoints.Create(
                    model_class=User,
                    readable_column_names=readable_user_column_names,
                    writeable_column_names=writeable_user_column_names,
                ),
                clearskies.endpoints.SimpleSearch(
                    model_class=User,
                    readable_column_names=readable_user_column_names,
                    sortable_column_names=readable_user_column_names,
                    searchable_column_names=readable_user_column_names,
                    default_sort_column_name="name",
                ),
            ],
            url="users",
        )

        readable_company_column_names = ["id", "name"]
        writeable_company_column_names = ["name"]
        companies_api = clearskies.EndpointGroup(
            [
                clearskies.endpoints.Update(
                    model_class=Company,
                    url="/:id",
                    readable_column_names=readable_company_column_names,
                    writeable_column_names=writeable_company_column_names,
                ),
                clearskies.endpoints.Delete(
                    model_class=Company,
                    url="/:id",
                ),
                clearskies.endpoints.Get(
                    model_class=Company,
                    url="/:id",
                    readable_column_names=readable_company_column_names,
                ),
                clearskies.endpoints.Create(
                    model_class=Company,
                    readable_column_names=readable_company_column_names,
                    writeable_column_names=writeable_company_column_names,
                ),
                clearskies.endpoints.SimpleSearch(
                    model_class=Company,
                    readable_column_names=readable_company_column_names,
                    sortable_column_names=readable_company_column_names,
                    searchable_column_names=readable_company_column_names,
                    default_sort_column_name="name",
                ),
            ],
            url="companies",
        )

        context = clearskies.contexts.Context(clearskies.EndpointGroup([users_api, companies_api]))

        status, response_data, response_headers = context(
            url="/companies",
            request_method="POST",
            body={"name": "Box Store"},
        )
        assert response_data["data"]["name"] == "Box Store"
        company_id = response_data["data"]["id"]

        status, response_data, response_headers = context(
            url="/users",
            request_method="POST",
            body={"name": "Bob Brown", "username": "bobbrown", "age": 25, "company_id": company_id},
        )
        assert response_data["data"]["name"] == "Bob Brown"

        status, response_data, response_headers = context(
            url="/users",
            request_method="POST",
            body={"name": "Jane Doe", "username": "janedoe", "age": 32, "company_id": company_id},
        )
        assert response_data["data"]["name"] == "Jane Doe"

        status, response_data, response_headers = context(url="users")
        assert [user["username"] for user in response_data["data"]] == ["bobbrown", "janedoe"]
        assert [user["company"]["name"] for user in response_data["data"]] == ["Box Store", "Box Store"]

    def test_cors_preflight_bypasses_authentication(self):
        """OPTIONS preflight must return 200 with CORS headers even when the group has auth."""

        class Item(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()
            id = columns.Uuid()
            name = columns.String()

        group = clearskies.EndpointGroup(
            [
                clearskies.endpoints.SimpleSearch(
                    model_class=Item,
                    url="items",
                    readable_column_names=["id", "name"],
                    sortable_column_names=["name"],
                    searchable_column_names=["name"],
                    default_sort_column_name="name",
                    authentication=clearskies.authentication.SecretBearer(environment_key="MY_SECRET"),
                ),
            ],
            security_headers=[clearskies.security_headers.Cors(origin="https://example.com")],
        )
        context = Context(group)

        status, _, response_headers = context(url="/items", request_method="OPTIONS")
        assert status == 200
        assert response_headers.access_control_allow_origin == "https://example.com"

    def test_cors_preflight_on_group_with_auth_returns_404_for_unknown_url(self):
        """OPTIONS to an unknown URL should return 404, not bypass routing."""

        class Item(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()
            id = columns.Uuid()
            name = columns.String()

        group = clearskies.EndpointGroup(
            [
                clearskies.endpoints.SimpleSearch(
                    model_class=Item,
                    url="items",
                    readable_column_names=["id", "name"],
                    sortable_column_names=["name"],
                    searchable_column_names=["name"],
                    default_sort_column_name="name",
                    authentication=clearskies.authentication.SecretBearer(environment_key="MY_SECRET"),
                ),
            ],
            security_headers=[clearskies.security_headers.Cors(origin="https://example.com")],
        )
        context = Context(group)

        status, _, _ = context(url="/unknown", request_method="OPTIONS")
        assert status == 404

    def test_non_options_requests_still_require_authentication(self):
        """Normal requests through the group still go through authentication."""
        import os

        class Item(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()
            id = columns.Uuid()
            name = columns.String()

        os.environ["MY_SECRET"] = "supersecret"
        try:
            group = clearskies.EndpointGroup(
                [
                    clearskies.endpoints.SimpleSearch(
                        model_class=Item,
                        url="items",
                        readable_column_names=["id", "name"],
                        sortable_column_names=["name"],
                        searchable_column_names=["name"],
                        default_sort_column_name="name",
                        authentication=clearskies.authentication.SecretBearer(environment_key="MY_SECRET"),
                    ),
                ],
            )
            context = Context(group)

            status, _, _ = context(url="/items", request_method="GET")
            assert status == 401
        finally:
            del os.environ["MY_SECRET"]
