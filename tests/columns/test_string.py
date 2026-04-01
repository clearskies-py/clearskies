import clearskies
from tests.test_base import TestBase


class StringTest(TestBase):
    def test_default(self):
        class Pet(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()

        context = clearskies.contexts.Context(
            clearskies.endpoints.Create(
                Pet,
                writeable_column_names=["name"],
                readable_column_names=["id", "name"],
            ),
        )

        status_code, response_data, response_headers = context(
            request_method="POST",
            body={"name": "Spot"},
        )
        assert response_data["data"]["name"] == "Spot"

        status_code, response_data, response_headers = context(
            request_method="POST",
            body={"name": 25},
        )
        assert "name" not in response_data
        assert "name" in response_data["input_errors"]

    def test_string_returns_none_for_null_backend_value(self):
        class Pet(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()

        context = clearskies.contexts.Context(
            clearskies.endpoints.List(
                Pet,
                readable_column_names=["id", "name"],
                sortable_column_names=["id"],
                default_sort_column_name="id",
            ),
            classes=[Pet],
            bindings={
                "memory_backend_default_data": [
                    {
                        "model_class": Pet,
                        "records": [
                            {"id": "pet-1", "name": None},
                        ],
                    },
                ],
            },
        )
        status_code, response, response_headers = context()
        assert status_code == 200
        assert len(response["data"]) == 1
        pet_data = response["data"][0]
        assert pet_data["name"] is None
