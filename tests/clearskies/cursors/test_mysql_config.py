import unittest

import clearskies.cursors
from clearskies.di import Di


class MysqlConfigTest(unittest.TestCase):
    """Tests for the MysqlConfig AdditionalConfig class."""

    def test_backend_type(self):
        def my_function(cursor_backend_type: str):
            return cursor_backend_type

        di = Di(modules=[clearskies.cursors])

        assert di.call_function(my_function) == "mysql"
