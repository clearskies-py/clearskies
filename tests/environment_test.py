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


class EnvironmentWithRealOsEnvironTest(unittest.TestCase):
    """Tests that verify Environment works with real os.environ via build_standard_lib."""

    def test_os_environ_resolved_via_build_standard_lib(self):
        """Test that os.environ is correctly resolved via ByStandardLib('os.environ')."""
        # Set a test environment variable
        test_key = "CLEARSKIES_TEST_ENV_VAR_12345"
        test_value = "test_value_from_os_environ"
        os.environ[test_key] = test_value

        try:
            environment = Environment("")
            environment._env_file_config = {}
            # Don't mock os.environ - let it be resolved via build_standard_lib
            di = Di()
            environment.injectable_properties(di)

            # The environment should be able to read from the real os.environ
            result = environment.get(test_key)
            self.assertEqual(test_value, result)
        finally:
            # Clean up
            del os.environ[test_key]

    def test_os_environ_is_actual_os_environ(self):
        """Test that the resolved os.environ is the actual os.environ object."""
        environment = Environment("")
        environment._env_file_config = {}
        di = Di()
        environment.injectable_properties(di)

        # The os_environ property should be the actual os.environ
        self.assertIs(environment.os_environ, os.environ)

    def test_set_overrides_real_os_environ(self):
        """Test that set() overrides values from real os.environ."""
        test_key = "CLEARSKIES_TEST_OVERRIDE_VAR"
        os.environ[test_key] = "original_value"

        try:
            environment = Environment("")
            environment._env_file_config = {}
            di = Di()
            environment.injectable_properties(di)

            # Verify original value is accessible
            self.assertEqual("original_value", environment.get(test_key))

            # Override with set()
            environment.set(test_key, "overridden_value")
            self.assertEqual("overridden_value", environment.get(test_key))
        finally:
            del os.environ[test_key]

    def test_silent_get_returns_none_for_missing_key(self):
        """Test that get() with silent=True returns None for missing keys."""
        environment = Environment("")
        environment._env_file_config = {}
        di = Di()
        environment.injectable_properties(di)

        result = environment.get("NONEXISTENT_KEY_XYZ_12345", silent=True)
        self.assertIsNone(result)

    def test_environment_built_via_di_has_injectable_properties(self):
        """Test that Environment built via di.build() has injectable properties initialized."""
        test_key = "CLEARSKIES_TEST_DI_BUILD_VAR"
        test_value = "test_value_from_di_build"
        os.environ[test_key] = test_value

        try:
            di = Di()
            # Build environment via DI - this should call inject_properties automatically
            environment = di.build("environment", cache=True)
            environment._env_file_config = {}

            # The environment should be able to read from os.environ without raising
            # "injectable hasn't been properly initialized" error
            result = environment.get(test_key)
            self.assertEqual(test_value, result)
        finally:
            del os.environ[test_key]
