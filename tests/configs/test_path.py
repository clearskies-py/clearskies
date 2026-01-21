import tempfile
import unittest
from pathlib import Path

import clearskies.decorators
from clearskies import Configurable, configs


class HasConfigs(Configurable):
    my_path = configs.Path(default=".")

    @clearskies.decorators.parameters_to_properties
    def __init__(self, my_path=None):
        self.finalize_and_validate_configuration()


class HasConfigsRequired(Configurable):
    my_path = configs.Path(required=True)

    @clearskies.decorators.parameters_to_properties
    def __init__(self, my_path=None):
        self.finalize_and_validate_configuration()


class HasConfigsNoExistenceCheck(Configurable):
    my_path = configs.Path(check_for_existence=False)

    @clearskies.decorators.parameters_to_properties
    def __init__(self, my_path=None):
        self.finalize_and_validate_configuration()


class PathTest(unittest.TestCase):
    def test_allow_string(self):
        has_configs = HasConfigs(".")
        assert has_configs.my_path == Path(".")

    def test_allow_path_object(self):
        has_configs = HasConfigs(Path("."))
        assert has_configs.my_path == Path(".")

    def test_converts_string_to_path(self):
        has_configs = HasConfigs(".")
        assert isinstance(has_configs.my_path, Path)

    def test_raise_wrong_type(self):
        with self.assertRaises(TypeError) as context:
            has_configs = HasConfigs(5)
        assert (
            "Error with 'HasConfigs.my_path': attempt to set a value of type 'int' to a parameter that requires a Path."
            == str(context.exception)
        )

    def test_default(self):
        has_configs = HasConfigs()
        assert has_configs.my_path == Path(".")

    def test_required(self):
        with self.assertRaises(ValueError) as context:
            has_configs = HasConfigsRequired()
        assert "Missing required configuration property 'my_path' for class 'HasConfigsRequired'" == str(
            context.exception
        )

    def test_raises_for_nonexistent_path(self):
        with self.assertRaises(ValueError) as context:
            has_configs = HasConfigs("/this/path/does/not/exist/at/all")
        assert "path '/this/path/does/not/exist/at/all' does not exist" in str(context.exception)

    def test_skip_existence_check(self):
        has_configs = HasConfigsNoExistenceCheck("/this/path/does/not/exist/at/all")
        assert has_configs.my_path == Path("/this/path/does/not/exist/at/all")

    def test_with_temp_file(self):
        with tempfile.NamedTemporaryFile() as temp_file:
            has_configs = HasConfigs(temp_file.name)
            assert has_configs.my_path == Path(temp_file.name)
