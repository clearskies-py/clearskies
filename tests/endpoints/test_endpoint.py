import datetime

from dateutil.relativedelta import relativedelta  # type: ignore

import clearskies
from clearskies.contexts import Context
from tests.test_base import TestBase


class EndpointTest(TestBase):
    def test_response_headers(self):
        def custom_headers(query_parameters):
            some_value = "yes" if query_parameters.get("stuff") else "no"
            return [f"x-custom: {some_value}", "content-type: application/custom"]

        context = Context(
            clearskies.endpoints.Callable(
                lambda: {"hello": "world"},
                response_headers=custom_headers,
            )
        )
        status_code, response, headers = context()
        assert status_code == 200
        assert response["status"] == "success"
        assert response["data"] == {"hello": "world"}
        assert headers.content_type == "application/custom"
        assert headers.x_custom == "no"

        status_code, response, headers = context(query_parameters={"stuff": "1"})
        assert headers.x_custom == "yes"

    def test_routing_simple(self):
        context = Context(
            clearskies.endpoints.Callable(
                lambda: {"hello": "World"},
                url="/hello/world",
            )
        )

        status_code, response, headers = context(url="/hello/world")
        assert status_code == 200
        assert response["status"] == "success"
        assert response["data"] == {"hello": "World"}

        status_code, response, headers = context(url="/sup")
        assert status_code == 404
        assert response["status"] == "client_error"
        assert response["data"] == []

    def test_routing_data(self):
        context = Context(
            clearskies.endpoints.Callable(
                lambda first_name, last_name: {"hello": f"{first_name} {last_name}"},
                url="/hello/:first_name/{last_name}",
            )
        )

        status_code, response, headers = context(url="/hello/bob/brown")
        assert status_code == 200
        assert response["status"] == "success"
        assert response["data"] == {"hello": "bob brown"}

    def test_request_methods(self):
        context = Context(
            clearskies.endpoints.Callable(
                lambda: {"hello": "world"},
                request_methods=["POST"],
            )
        )

        status_code, response, headers = context(request_method="POST")
        assert status_code == 200
        assert response["data"] == {"hello": "world"}

        status_code, response, headers = context(request_method="GET")
        assert status_code == 404

    def test_output_map(self):
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
            output_map=user_to_json,
            output_schema=UserResponse,
            readable_column_names=["id", "name"],
            sortable_column_names=["id", "name", "dob"],
            default_sort_column_name="dob",
            default_sort_direction="DESC",
        )

        context = Context(
            list_users,
            classes=[User],
            bindings={
                "memory_backend_default_data": [
                    {
                        "model_class": User,
                        "records": [
                            {"id": "1-2-3-4", "name": "Bob", "dob": datetime.datetime(1990, 1, 1)},
                            {"id": "1-2-3-5", "name": "Jane", "dob": datetime.datetime(2020, 1, 1)},
                            {"id": "1-2-3-6", "name": "Greg", "dob": datetime.datetime(1980, 1, 1)},
                        ],
                    },
                ]
            },
        )
        status_code, response, response_headers = context(url="jane")

        assert status_code == 200
        this_year = datetime.datetime.now(datetime.timezone.utc).year
        assert response["data"] == [
            {"id": "1-2-3-5", "name": "Jane", "age": this_year - 2020, "is_special": True},
            {"id": "1-2-3-4", "name": "Bob", "age": this_year - 1990, "is_special": False},
            {"id": "1-2-3-6", "name": "Greg", "age": this_year - 1980, "is_special": False},
        ]

    def test_readable_column_names(self):
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

        context = Context(
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
                        ],
                    },
                ]
            },
        )

        status_code, response, response_headers = context()
        assert status_code == 200
        assert response["data"] == [
            {"id": "1-2-3-4", "name": "Bob"},
            {"id": "1-2-3-6", "name": "Greg"},
            {"id": "1-2-3-5", "name": "Jane"},
        ]

    def test_writeable_column_names(self):
        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()
            id = clearskies.columns.Uuid()
            name = clearskies.columns.String(validators=[clearskies.validators.Required()])
            date_of_birth = clearskies.columns.Date()

        context = Context(
            clearskies.endpoints.Callable(
                lambda request_data: request_data,
                request_methods=["GET", "POST"],
                writeable_column_names=["name", "date_of_birth"],
                model_class=User,
            )
        )

        status_code, response, response_headers = context(
            request_method="POST",
            body={"name": "Jane", "date_of_birth": "01/01/1990"},
        )
        assert status_code == 200
        assert response["data"] == {"name": "Jane", "date_of_birth": "01/01/1990"}

        status_code, response, response_headers = context(
            request_method="POST",
            body={"name": "", "date_of_birth": "this is not a date", "id": "hey"},
        )
        assert status_code == 200
        assert response["input_errors"] == {
            "name": "'name' is required.",
            "date_of_birth": "given value did not appear to be a valid date",
            "id": "Input column id is not an allowed input column.",
        }

    def test_input_validation_callable(self):
        def check_input(request_data):
            if not request_data:
                return {}
            if request_data.get("name"):
                return {"name": "This is a privacy-preserving system, so please don't tell us your name"}
            return {}

        context = Context(
            clearskies.endpoints.Callable(
                lambda request_data: request_data,
                request_methods=["GET", "POST"],
                input_validation_callable=check_input,
            )
        )

        status_code, response, response_headers = context(body={"name": "sup"})
        assert status_code == 200
        assert response["input_errors"] == {
            "name": "This is a privacy-preserving system, so please don't tell us your name",
        }

        status_code, response, response_headers = context(body={"hello": "world"})
        assert status_code == 200
        assert response["data"] == {"hello": "world"}

    def test_casing(self):
        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()
            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()
            date_of_birth = clearskies.columns.Date()

        thing = Context(
            clearskies.endpoints.Callable(
                lambda users: users.create({"name": "Example", "date_of_birth": datetime.datetime(2050, 1, 15)}),
                readable_column_names=["name", "date_of_birth"],
                internal_casing="snake_case",
                external_casing="TitleCase",
                model_class=User,
            ),
            classes=[User],
        )

        status_code, response, response_headers = thing()
        assert response == {
            "Status": "Success",
            "Error": "",
            "Data": {"Name": "Example", "DateOfBirth": "2050-01-15"},
            "Pagination": {},
            "InputErrors": {},
        }

    def test_security_headers(self):
        context = Context(
            clearskies.endpoints.Callable(
                lambda: {"hello": "world"},
                request_methods=["PATCH", "POST"],
                authentication=clearskies.authentication.SecretBearer(environment_key="MY_SECRET"),
                security_headers=[
                    clearskies.security_headers.Hsts(),
                    clearskies.security_headers.Cors(origin="https://example.com"),
                ],
            )
        )

        status_code, response, response_headers = context(request_method="OPTIONS")
        assert response_headers.access_control_allow_methods == "PATCH, POST"
        assert response_headers.access_control_allow_headers == "Authorization"
        assert response_headers.access_control_max_age == "5"
        assert response_headers.access_control_allow_origin == "https://example.com"
        assert response_headers.strict_transport_security == "max-age=31536000 ;"

    def test_route_from_request_data(self):
        """Test that route_from_request_data on Context populates routing data from request body."""
        context_without = Context(
            clearskies.endpoints.Callable(
                lambda routing_data: {"routing_data": routing_data},
                url="/groups/{group_id}/members",
                request_methods=["GET", "POST"],
            ),
            route_from_request_data=False,
        )

        # Without route_from_request_data, placeholder remains in routing_data
        status_code, response, headers = context_without(
            url="/groups/{group_id}/members",
            body={"group_id": "abc-123"},
        )
        assert status_code == 200
        assert response["data"]["routing_data"]["group_id"] == "{group_id}"

        # With route_from_request_data, placeholder is replaced from request body
        context_with = Context(
            clearskies.endpoints.Callable(
                lambda routing_data: {"routing_data": routing_data},
                url="/groups/{group_id}/members",
                request_methods=["GET", "POST"],
            ),
            route_from_request_data=True,
        )

        status_code, response, headers = context_with(
            url="/groups/{group_id}/members",
            body={"group_id": "abc-123"},
        )
        assert status_code == 200
        assert response["data"]["routing_data"]["group_id"] == "abc-123"

    def test_route_from_request_data_with_colon_syntax(self):
        """Test that route_from_request_data works with :param syntax too."""
        context = Context(
            clearskies.endpoints.Callable(
                lambda routing_data: {"routing_data": routing_data},
                url="/groups/:group_id/members/:member_id",
                request_methods=["GET", "POST"],
            ),
            route_from_request_data=True,
        )

        status_code, response, headers = context(
            url="/groups/:group_id/members/:member_id",
            body={"group_id": "group-456", "member_id": "member-789"},
        )
        assert status_code == 200
        assert response["data"]["routing_data"]["group_id"] == "group-456"
        assert response["data"]["routing_data"]["member_id"] == "member-789"

    def test_route_from_request_data_unpacks_body_params(self):
        """Test that route_from_request_data also unpacks request body params for callables."""

        def my_handler(group_id, request_data: dict = {}):
            """Return group_id from routing and page_data from body."""
            return {"group_id": group_id, "page_data": request_data["page_data"]}

        context = Context(
            clearskies.endpoints.Callable(
                my_handler,
                url="/groups/{group_id}/members",
                request_methods=["GET", "POST"],
            ),
            route_from_request_data=True,
        )

        status_code, response, headers = context(
            url="/groups/{group_id}/members",
            body={"group_id": "abc-123", "page_data": {"page": 2, "per_page": 50}},
        )
        assert status_code == 200
        assert response["data"]["group_id"] == "abc-123"
        assert response["data"]["page_data"] == {"page": 2, "per_page": 50}

    def test_route_from_request_data_with_key(self):
        """Test that route_from_request_data also unpacks request body params for callables."""

        def my_handler(group_id, request_data: dict = {}):
            """Return group_id from routing and page_data from body."""
            return {"group_id": group_id, "page_data": request_data["page_data"]}

        context = Context(
            clearskies.endpoints.Callable(
                my_handler,
                url="/groups/{group_id}/members",
                request_methods=["GET", "POST"],
            ),
            route_from_request_data=True,
            request_data_route_key="url",
        )

        status_code, response, headers = context(
            body={"url": "/groups/{group_id}/members", "group_id": "abc-123", "page_data": {"page": 2, "per_page": 50}},
        )
        print(response)
        assert status_code == 200
        assert response["data"]["group_id"] == "abc-123"
        assert response["data"]["page_data"] == {"page": 2, "per_page": 50}

    def test_route_from_request_data_does_not_override_routing_data(self):
        """Test that request body keys don't override routing_data or other core context keys."""

        def my_handler(routing_data, request_data):
            """Return both routing_data and request_data."""
            return {"routing_data": routing_data, "request_data": request_data}

        context = Context(
            clearskies.endpoints.Callable(
                my_handler,
                url="/groups/{group_id}/members",
                request_methods=["GET", "POST"],
            ),
            route_from_request_data=True,
        )

        # Try to override routing_data from body - should not work
        status_code, response, headers = context(
            url="/groups/{group_id}/members",
            body={
                "group_id": "abc-123",
                "routing_data": {"should": "not override"},
                "request_data": {"also": "should not override"},
            },
        )
        assert status_code == 200
        # routing_data should be the actual routing data, not the body's "routing_data"
        assert response["data"]["routing_data"]["group_id"] == "abc-123"
        # request_data should be the full body
        assert response["data"]["request_data"]["routing_data"] == {"should": "not override"}
