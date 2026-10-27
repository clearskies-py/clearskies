import clearskies
from tests.test_base import TestBase


class UpdateTest(TestBase):
    def test_overview(self):
        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()
            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()
            username = clearskies.columns.String(validators=[clearskies.validators.Required()])

        context = clearskies.contexts.Context(
            clearskies.endpoints.Update(
                model_class=User,
                url="/{id}",
                readable_column_names=["id", "name", "username"],
                writeable_column_names=["name", "username"],
            ),
            bindings={
                "memory_backend_default_data": [
                    {
                        "model_class": User,
                        "records": [
                            {"id": "1-2-3-4", "name": "Bob Brown", "username": "bobbrown"},
                            {"id": "1-2-3-5", "name": "Jane Doe", "username": "janedoe"},
                            {"id": "1-2-3-6", "name": "Greg", "username": "greg"},
                        ],
                    },
                ],
            },
        )

        status_code, response_data, response_headers = context(
            request_method="PATCH",
            body={"name": "Bobby Brown", "username": "bobbybrown"},
            url="/1-2-3-4",
        )
        assert response_data["data"] == {
            "id": "1-2-3-4",
            "name": "Bobby Brown",
            "username": "bobbybrown",
        }

        status_code, response_data, response_headers = context(
            request_method="PATCH",
            body={"name": 12345, "username": ""},
            url="/1-2-3-4",
        )
        assert "name" in response_data["input_errors"]
        assert "username" in response_data["input_errors"]

    def test_external_casing(self):
        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()
            id = clearskies.columns.Uuid()
            first_name = clearskies.columns.String()

        context = clearskies.contexts.Context(
            clearskies.endpoints.Update(
                model_class=User,
                url="/{id}",
                readable_column_names=["id", "first_name"],
                writeable_column_names=["first_name"],
                external_casing="camelCase",
            ),
            bindings={
                "memory_backend_default_data": [
                    {"model_class": User, "records": [{"id": "1-2-3-4", "first_name": "Bob"}]},
                ],
            },
        )

        status_code, response_data, response_headers = context(
            request_method="PATCH", body={"firstName": "zed"}, url="/1-2-3-4"
        )
        assert status_code == 200
        assert response_data["data"] == {"id": "1-2-3-4", "firstName": "zed"}
