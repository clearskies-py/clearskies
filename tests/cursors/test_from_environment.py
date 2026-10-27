import unittest
from unittest.mock import MagicMock

from clearskies.cursors.from_environment.mysql import Mysql


class FakeEnvironment:
    def __init__(self, values):
        self.values = values

    def get(self, name, silent=False):
        if name not in self.values and not silent:
            raise KeyError(name)
        return self.values.get(name)


BASE_ENV = {
    "DATABASE_HOST": "db.example.com",
    "DATABASE_USERNAME": "example-user",
    "DATABASE_PASSWORD": "REPLACE_ME",
    "DATABASE_NAME": "appdb",
}


def build_kwargs(cursor_class, env):
    class TestCursor(cursor_class):
        environment = FakeEnvironment(env)

    cursor = TestCursor()
    cursor._factory = MagicMock()
    return cursor.build_connection_kwargs()


class MysqlFromEnvironmentTest(unittest.TestCase):
    def test_autocommit_defaults_to_true_when_unset(self):
        self.assertTrue(build_kwargs(Mysql, BASE_ENV)["autocommit"])

    def test_autocommit_parses_env_value(self):
        self.assertFalse(build_kwargs(Mysql, {**BASE_ENV, "DATABASE_AUTOCOMMIT": "false"})["autocommit"])
        self.assertFalse(build_kwargs(Mysql, {**BASE_ENV, "DATABASE_AUTOCOMMIT": "0"})["autocommit"])
        self.assertFalse(build_kwargs(Mysql, {**BASE_ENV, "DATABASE_AUTOCOMMIT": False})["autocommit"])
        self.assertTrue(build_kwargs(Mysql, {**BASE_ENV, "DATABASE_AUTOCOMMIT": "true"})["autocommit"])
