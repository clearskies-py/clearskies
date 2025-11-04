import unittest

import clearskies.cursors
from clearskies.di import Di


class PostgresqlConfigTest(unittest.TestCase):
    """Tests for the PostgresqlConfig AdditionalConfig class."""

    def test_backend_type(self):
        def my_function(cursor_backend_type: str):
            return cursor_backend_type

        di = Di(additional_configs=[clearskies.cursors.PostgresqlConfig()])

        assert di.call_function(my_function) == "postgresql"
