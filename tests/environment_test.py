import os
import unittest
from unittest.mock import MagicMock, call

from clearskies.di import Di
from clearskies.environment import Environment


class EnvironmentTest(unittest.TestCase):
    def setUp(self):
        self.secrets = type("", (), {"get": MagicMock(return_value="my_secret")})()
        self.os_environ = {
            "env_in_environment": "yup",
            "also": "secret:///another/secret/path",
            "an_integer": 5,
        }
        self.environment = Environment("")
        di = Di(bindings={"secrets": self.secrets, "os.environ": self.os_environ})
        self.environment.injectable_properties(di)

    def test_get_from_env(self):
        self.assertEqual("yup", self.environment.get("env_in_environment"))

    def test_get_from_env_resolve_secret(self):
        self.assertEqual("my_secret", self.environment.get("also"))
        self.secrets.get.assert_called_with("/another/secret/path")  # type: ignore

    def test_no_crash_for_ints(self):
        self.assertEqual(5, self.environment.get("an_integer"))
