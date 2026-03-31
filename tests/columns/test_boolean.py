import clearskies
from tests.test_base import TestBase


class BooleanTest(TestBase):
    def test_boolean_returns_false_for_null_backend_value(self):
        class Pet(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            is_active = clearskies.columns.Boolean()

        context = clearskies.contexts.Context(
            clearskies.endpoints.List(
                Pet,
                readable_column_names=["id", "is_active"],
                sortable_column_names=["id"],
                default_sort_column_name="id",
            ),
            classes=[Pet],
            bindings={
                "memory_backend_default_data": [
                    {
                        "model_class": Pet,
                        "records": [
                            {"id": "pet-1", "is_active": None},
                        ],
                    },
                ],
            },
        )
        status_code, response, response_headers = context()
        assert status_code == 200
        assert len(response["data"]) == 1
        pet_data = response["data"][0]
        assert pet_data["is_active"] is False

    def test_boolean_returns_false_for_zero_string(self):
        class Pet(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            is_active = clearskies.columns.Boolean()

        context = clearskies.contexts.Context(
            clearskies.endpoints.List(
                Pet,
                readable_column_names=["id", "is_active"],
                sortable_column_names=["id"],
                default_sort_column_name="id",
            ),
            classes=[Pet],
            bindings={
                "memory_backend_default_data": [
                    {
                        "model_class": Pet,
                        "records": [
                            {"id": "pet-1", "is_active": "0"},
                        ],
                    },
                ],
            },
        )
        status_code, response, response_headers = context()
        assert status_code == 200
        assert len(response["data"]) == 1
        pet_data = response["data"][0]
        assert pet_data["is_active"] is False

    def test_boolean_returns_true_for_truthy_value(self):
        class Pet(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            is_active = clearskies.columns.Boolean()

        context = clearskies.contexts.Context(
            clearskies.endpoints.List(
                Pet,
                readable_column_names=["id", "is_active"],
                sortable_column_names=["id"],
                default_sort_column_name="id",
            ),
            classes=[Pet],
            bindings={
                "memory_backend_default_data": [
                    {
                        "model_class": Pet,
                        "records": [
                            {"id": "pet-1", "is_active": 1},
                        ],
                    },
                ],
            },
        )
        status_code, response, response_headers = context()
        assert status_code == 200
        assert len(response["data"]) == 1
        pet_data = response["data"][0]
        assert pet_data["is_active"] is True
