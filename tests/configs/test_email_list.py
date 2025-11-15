import unittest

import clearskies.decorators
from clearskies import Configurable, configs


class HasConfigs(Configurable):
    my_email = configs.EmailList(default=["test@example.com"])

    @clearskies.decorators.parameters_to_properties
    def __init__(self, my_email=None):
        self.finalize_and_validate_configuration()


class HasConfigsRequired(Configurable):
    my_email = configs.Email(required=True)

    @clearskies.decorators.parameters_to_properties
    def __init__(self, my_email=None):
        self.finalize_and_validate_configuration()


class EmailTest(unittest.TestCase):
    def test_allow(self):
        has_configs = HasConfigs(["test1@example.com"])
        assert has_configs.my_email == ["test1@example.com"]

    def test_raise_wrong_type(self):
        with self.assertRaises(TypeError) as context:
            has_configs = HasConfigs("test@example.com")
        assert (
            "Error with 'HasConfigs.my_email': attempt to set a value of type 'str' to a list of strings parameter."
            == str(context.exception)
        )

    def test_raise_wrong_format(self):
        with self.assertRaises(ValueError) as context:
            has_configs = HasConfigs(["not-an-email"])
        assert (
            "Error with 'HasConfigs.my_email': attempt to set a value of 'not-an-email' for item #1 but this does not match the required regexp: '(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$)'."
            == str(context.exception)
        )

    def test_default(self):
        has_configs = HasConfigs()
        assert has_configs.my_email == ["test@example.com"]

    def test_required(self):
        with self.assertRaises(ValueError) as context:
            has_configs = HasConfigsRequired()
        assert "Missing required configuration property 'my_email' for class 'HasConfigsRequired'" == str(
            context.exception
        )
