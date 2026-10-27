import unittest
from unittest.mock import MagicMock

from clearskies.cursors.from_environment.mysql import Mysql
from clearskies.cursors.from_environment.postgresql import Postgresql
from clearskies.cursors.postgresql import Postgresql as PostgresqlBase


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


class PostgresqlTest(unittest.TestCase):
    def test_connection_kwargs_are_valid_libpq_options(self):
        cursor = PostgresqlBase(database="appdb", cert_path="/path/to/ca.pem")
        cursor._factory = MagicMock()
        kwargs = cursor.build_connection_kwargs()
        self.assertEqual(kwargs["dbname"], "appdb")
        self.assertEqual(kwargs["sslrootcert"], "/path/to/ca.pem")
        self.assertEqual(kwargs["sslmode"], "verify-ca")
        for invalid in ["database", "ssl_ca", "sslcert"]:
            self.assertNotIn(invalid, kwargs)
        self.assertEqual(cursor.column_escape_character, '"')
        self.assertEqual(cursor.table_escape_character, '"')

    def test_from_environment(self):
        kwargs = build_kwargs(Postgresql, {**BASE_ENV, "DATABASE_CERT_PATH": "/path/to/ca.pem"})
        self.assertEqual(kwargs["dbname"], "appdb")
        self.assertEqual(kwargs["sslrootcert"], "/path/to/ca.pem")
        self.assertEqual(kwargs["sslmode"], "verify-ca")
        self.assertTrue(kwargs["autocommit"])
        self.assertNotIn("database", kwargs)

    def test_no_cert_leaves_sslmode_to_libpq(self):
        cursor = PostgresqlBase(database="appdb")
        cursor._factory = MagicMock()
        self.assertNotIn("sslmode", cursor.build_connection_kwargs())
        self.assertNotIn("sslmode", build_kwargs(Postgresql, BASE_ENV))
