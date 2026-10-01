import clearskies
from tests.test_base import TestBase


class IntegerTest(TestBase):
    def test_default(self):
        class MyModel(clearskies.Model):
            backend = clearskies.backends.MemoryBackend()
            id_column_name = "id"

            id = clearskies.columns.Uuid()
            age = clearskies.columns.Integer()

        context = clearskies.contexts.Context(
            clearskies.endpoints.Create(
                MyModel,
                writeable_column_names=["age"],
                readable_column_names=["id", "age"],
            ),
            classes=[MyModel],
        )

        status_code, response_data, response_headers = context(request_method="POST", body={"age": 20})
        assert response_data["data"]["age"] == 20

        status_code, response_data, response_headers = context(request_method="POST", body={"age": "asdf"})
        assert "age" not in response_data["data"]
        assert "age" in response_data["input_errors"]

    def test_input_error_for_value_non_primitive_returns_error_not_exception(self):
        """input_error_for_value returns a string for list/dict input rather than raising TypeError."""

        class MyModel(clearskies.Model):
            backend = clearskies.backends.MemoryBackend()
            id_column_name = "id"

            id = clearskies.columns.Uuid()
            count = clearskies.columns.Integer()

        MyModel().get_columns()
        column = MyModel.count
        assert column.input_error_for_value([1, 2]) != ""
        assert column.input_error_for_value({"a": 1}) != ""
        assert column.input_error_for_value(None) != ""
