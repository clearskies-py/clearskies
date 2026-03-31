import clearskies
from tests.test_base import TestBase


class FloatTest(TestBase):
    def test_default(self):
        class MyModel(clearskies.Model):
            backend = clearskies.backends.MemoryBackend()
            id_column_name = "id"

            id = clearskies.columns.Uuid()
            score = clearskies.columns.Float()

        context = clearskies.contexts.Context(
            clearskies.endpoints.Create(
                MyModel,
                writeable_column_names=["score"],
                readable_column_names=["id", "score"],
            ),
            classes=[MyModel],
        )

        status_code, response_data, response_headers = context(request_method="POST", body={"score": 15.2})
        assert response_data["data"]["score"] == 15.2

        status_code, response_data, response_headers = context(request_method="POST", body={"score": "15.2"})
        assert "score" not in response_data["data"]
        assert "score" in response_data["input_errors"]

    def test_float_returns_none_for_null_backend_value(self):
        class Product(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            amount = clearskies.columns.Float()

        context = clearskies.contexts.Context(
            clearskies.endpoints.List(
                Product,
                readable_column_names=["id", "amount"],
                sortable_column_names=["id"],
                default_sort_column_name="id",
            ),
            classes=[Product],
            bindings={
                "memory_backend_default_data": [
                    {
                        "model_class": Product,
                        "records": [
                            {"id": "product-1", "amount": None},
                        ],
                    },
                ],
            },
        )
        status_code, response, response_headers = context()
        assert status_code == 200
        assert len(response["data"]) == 1
        product_data = response["data"][0]
        assert product_data["amount"] is None
