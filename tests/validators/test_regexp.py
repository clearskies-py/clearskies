import unittest

import clearskies
from clearskies.validators.regexp import Regexp


class RegepxTest(unittest.TestCase):
    def setUp(self):
        self.regexp = Regexp(f"\d\.\d+\.\d+")
        clearskies.backends.MemoryBackend.clear_table_cache()

    def test_check_regexp(self):
        error = self.regexp.check("model", "version", {"version": "1.0.0"})  # type: ignore
        self.assertEqual("", error)
        error = self.regexp.check("model", "version", {"version": "1.20.340"})  # type: ignore
        self.assertEqual("", error)
        error = self.regexp.check("model", "version", {"version": "a.b.c"})  # type: ignore
        self.assertEqual("Does not match the required pattern.", error)

        regexp = Regexp(f"\d\.\d+\.\d+", include_regexp_in_error=True)
        error = regexp.check("model", "version", {"version": "a.b.c"})  # type: ignore
        self.assertEqual("Does not match the required pattern, '\d\.\d+\.\d+'.", error)

    def test_example(self):
        class MyModel(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            version = clearskies.columns.String(validators=[clearskies.validators.Regexp(r"\d+\.\d+\.\d+")])

        context = clearskies.contexts.Context(
            clearskies.endpoints.Create(
                MyModel,
                readable_column_names=["id", "version"],
                writeable_column_names=["version"],
            ),
        )

        (status, response, headers) = context(body={"version": "1.2.3"}, request_method="POST")
        assert status == 200
        assert response["status"] == "success"

        (status, response, headers) = context(body={"version": "1.a.3"}, request_method="POST")
        assert status == 200
        assert response["status"] == "input_errors"
        assert response["input_errors"] == {"version": "Does not match the required pattern."}
