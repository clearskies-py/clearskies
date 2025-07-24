import unittest
from unittest.mock import MagicMock

import clearskies.decorators
from clearskies import Configurable, configs

from .. import validator


class FakeValidator(validator.Validator):
    def check(self, data):  # type: ignore
        pass


class HasConfigs(Configurable):
    validators = configs.Validators()

    @clearskies.decorators.parameters_to_properties
    def __init__(self, validators):
        self.finalize_and_validate_configuration()


class ValidatorsTest(unittest.TestCase):
    def test_allow(self):
        fake_validator = FakeValidator()

        has_configs = HasConfigs(fake_validator)
        assert has_configs.validators == [fake_validator]

    def test_raise_non_validator(self):
        with self.assertRaises(TypeError) as context:
            fake_validator = FakeValidator()
            has_configs = HasConfigs([fake_validator, "sup"])
        assert (
            "Error with 'HasConfigs.validators': attempt to set a value of type 'str' for item #2 when a Validator is required"
            == str(context.exception)
        )
