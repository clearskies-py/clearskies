import datetime

import clearskies
from clearskies import columns, validators
from tests.test_base import TestBase


class CreateTest(TestBase):
    def test_overview(self):
        class MyAwesomeModel(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = columns.Uuid()
            name = clearskies.columns.String(
                validators=[
                    validators.Required(),
                    validators.MaximumLength(50),
                ]
            )
            email = columns.Email(validators=[validators.Unique()])
            some_number = columns.Integer()
            expires_at = columns.Date()
            created_at = columns.Created()

        utcnow = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)

        context = clearskies.contexts.Context(
            clearskies.endpoints.Create(
                MyAwesomeModel,
                readable_column_names=["id", "name", "email", "some_number", "expires_at", "created_at"],
                writeable_column_names=["name", "email", "some_number", "expires_at"],
            ),
            utcnow=utcnow,
        )
        status_code, response_data, response_headers = context(
            request_method="POST",
            body={"name": "Example", "email": "test@example.com", "some_number": 5, "expires_at": "2024-12-31"},
        )

        assert len(response_data["data"]["id"]) == 36
        assert response_data["data"]["name"] == "Example"
        assert response_data["data"]["email"] == "test@example.com"
        assert response_data["data"]["some_number"] == 5
        assert response_data["data"]["expires_at"] == "2024-12-31"
        assert response_data["data"]["created_at"] == utcnow.isoformat()

    def test_external_casing(self):
        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()
            id = clearskies.columns.Uuid()
            first_name = clearskies.columns.String(validators=[clearskies.validators.Required()])

        context = clearskies.contexts.Context(
            clearskies.endpoints.Create(
                model_class=User,
                readable_column_names=["id", "first_name"],
                writeable_column_names=["first_name"],
                external_casing="camelCase",
            ),
        )

        status_code, response_data, response_headers = context(request_method="POST", body={"firstName": "zed"})
        assert status_code == 200
        assert response_data["data"]["firstName"] == "zed"

        status_code, response_data, response_headers = context(request_method="POST", body={"firstName": ""})
        assert "first_name" in response_data["inputErrors"]
