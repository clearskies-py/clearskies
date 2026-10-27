import datetime

import clearskies
from tests.test_base import TestBase


class DateTest(TestBase):
    def test_default(self):
        class MyModel(clearskies.Model):
            backend = clearskies.backends.MemoryBackend()
            id_column_name = "id"

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()
            my_datetime = clearskies.columns.Datetime()

        context = clearskies.contexts.Context(
            clearskies.endpoints.Create(
                MyModel,
                writeable_column_names=["name", "my_datetime"],
                readable_column_names=["id", "name", "my_datetime"],
            ),
            classes=[MyModel],
        )

        status_code, response_data, response_headers = context(
            request_method="POST", body={"name": "Bob", "my_datetime": "May 13th 2025 15:35:03UTC"}
        )
        assert response_data["data"]["my_datetime"] == "2025-05-13T15:35:03+00:00"

        status_code, response_data, response_headers = context(
            request_method="POST", body={"name": "Bob", "my_datetime": "2025-05-13 15:35:03+00:00"}
        )
        assert response_data["data"]["my_datetime"] == "2025-05-13T15:35:03+00:00"

        status_code, response_data, response_headers = context(
            request_method="POST", body={"name": "Bob", "my_datetime": "not a date"}
        )
        assert "my_datetime" not in response_data["data"]
        assert "my_datetime" in response_data["input_errors"]

    def test_round_trip_converts_timezone(self):
        class MyModel(clearskies.Model):
            backend = clearskies.backends.MemoryBackend()
            id_column_name = "id"

            id = clearskies.columns.Uuid()
            my_datetime = clearskies.columns.Datetime()

        column = MyModel.get_columns()["my_datetime"]
        value = datetime.datetime(2026, 1, 1, 10, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=2)))
        stored = column.to_backend({"my_datetime": value})["my_datetime"]
        assert stored == "2026-01-01 08:00:00"
        assert column.from_backend(stored) == value
