import clearskies
from clearskies.columns.boolean import Boolean
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

    def test_condition_value_to_backend_returns_python_bools(self):
        """condition_value_to_backend coerces string inputs to Python booleans.

        The API backend layer (conditions_to_request_parameters) is responsible for
        converting Python bools to lowercase strings before URL encoding.
        """
        column = Boolean()
        assert column.condition_value_to_backend(True) is True
        assert column.condition_value_to_backend(False) is False
        # string inputs (common when conditions are parsed from raw where-clauses)
        assert column.condition_value_to_backend("true") is True
        assert column.condition_value_to_backend("false") is False
        assert column.condition_value_to_backend("1") is True
        assert column.condition_value_to_backend("0") is False
