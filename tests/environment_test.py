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
        # Pre-set _env_file_config to skip file loading in tests
        self.environment._env_file_config = {}
        di = Di(bindings={"secrets": self.secrets, "os.environ": self.os_environ})
        self.environment.injectable_properties(di)

    def test_get_from_env(self):
        self.assertEqual("yup", self.environment.get("env_in_environment"))

    def test_get_from_env_resolve_secret(self):
        self.assertEqual("my_secret", self.environment.get("also"))
        self.secrets.get.assert_called_with("/another/secret/path")  # type: ignore

    def test_no_crash_for_ints(self):
        self.assertEqual(5, self.environment.get("an_integer"))

    def test_set_value(self):
        self.environment.set("my_custom_key", "my_custom_value")
        self.assertEqual("my_custom_value", self.environment.get("my_custom_key"))

    def test_set_overrides_os_environ(self):
        # os_environ has env_in_environment = "yup"
        self.environment.set("env_in_environment", "overridden")
        self.assertEqual("overridden", self.environment.get("env_in_environment"))

    def test_set_with_secret_reference(self):
        self.environment.set("secret_key", "secret:///my/secret/path")
        self.assertEqual("my_secret", self.environment.get("secret_key"))
        self.secrets.get.assert_called_with("/my/secret/path")  # type: ignore
