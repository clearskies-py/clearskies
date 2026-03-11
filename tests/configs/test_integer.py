import unittest

import clearskies.decorators
from clearskies import Configurable, configs


class HasInteger(Configurable):
    _descriptor_config_map = None
    my_int = configs.Integer(default=10)

    @clearskies.decorators.parameters_to_properties
    def __init__(self, my_int=None):
        self.finalize_and_validate_configuration()


class HasIntegerRequired(Configurable):
    _descriptor_config_map = None
    my_int = configs.Integer(required=True)

    @clearskies.decorators.parameters_to_properties
    def __init__(self, my_int=None):
        self.finalize_and_validate_configuration()


class HasIntegerMinMax(Configurable):
    _descriptor_config_map = None
    my_int = configs.Integer(default=50, min=10, max=100)

    @clearskies.decorators.parameters_to_properties
    def __init__(self, my_int=None):
        self.finalize_and_validate_configuration()


class HasIntegerMinOnly(Configurable):
    _descriptor_config_map = None
    my_int = configs.Integer(min=0)

    @clearskies.decorators.parameters_to_properties
    def __init__(self, my_int=None):
        self.finalize_and_validate_configuration()


class HasIntegerMaxOnly(Configurable):
    _descriptor_config_map = None
    my_int = configs.Integer(max=100)

    @clearskies.decorators.parameters_to_properties
    def __init__(self, my_int=None):
        self.finalize_and_validate_configuration()


class IntegerTest(unittest.TestCase):
    def test_allow(self):
        has_configs = HasInteger(42)
        assert has_configs.my_int == 42

    def test_raise_wrong_type(self):
        with self.assertRaises(TypeError) as context:
            HasInteger("not_an_int")
        assert "attempt to set a value of type 'str' to parameter that requires an integer" in str(context.exception)

    def test_default(self):
        has_configs = HasInteger()
        assert has_configs.my_int == 10

    def test_required(self):
        with self.assertRaises(ValueError) as context:
            HasIntegerRequired()
        assert "Missing required configuration property 'my_int'" in str(context.exception)


class IntegerMinMaxTest(unittest.TestCase):
    def test_value_within_range(self):
        has_configs = HasIntegerMinMax(50)
        assert has_configs.my_int == 50

    def test_value_at_min_boundary(self):
        has_configs = HasIntegerMinMax(10)
        assert has_configs.my_int == 10

    def test_value_at_max_boundary(self):
        has_configs = HasIntegerMinMax(100)
        assert has_configs.my_int == 100

    def test_value_below_min(self):
        with self.assertRaises(ValueError) as context:
            HasIntegerMinMax(9)
        assert "less than the minimum allowed 10" in str(context.exception)

    def test_value_above_max(self):
        with self.assertRaises(ValueError) as context:
            HasIntegerMinMax(101)
        assert "greater than the maximum allowed 100" in str(context.exception)

    def test_default_within_range(self):
        has_configs = HasIntegerMinMax()
        assert has_configs.my_int == 50

    def test_wrong_type_with_min_max(self):
        with self.assertRaises(TypeError) as context:
            HasIntegerMinMax("not_an_int")
        assert "attempt to set a value of type 'str' to parameter that requires an integer" in str(context.exception)

    def test_min_only(self):
        has_configs = HasIntegerMinOnly(0)
        assert has_configs.my_int == 0

    def test_min_only_rejects_below(self):
        with self.assertRaises(ValueError) as context:
            HasIntegerMinOnly(-1)
        assert "less than the minimum allowed 0" in str(context.exception)

    def test_min_only_allows_large_values(self):
        has_configs = HasIntegerMinOnly(999999)
        assert has_configs.my_int == 999999

    def test_max_only(self):
        has_configs = HasIntegerMaxOnly(100)
        assert has_configs.my_int == 100

    def test_max_only_rejects_above(self):
        with self.assertRaises(ValueError) as context:
            HasIntegerMaxOnly(101)
        assert "greater than the maximum allowed 100" in str(context.exception)

    def test_max_only_allows_negative_values(self):
        has_configs = HasIntegerMaxOnly(-999)
        assert has_configs.my_int == -999

    def test_no_min_max_allows_any_integer(self):
        """Integer without min/max should accept any integer (backward compatible)."""
        has_configs = HasInteger(0)
        assert has_configs.my_int == 0
        has_configs = HasInteger(-999999)
        assert has_configs.my_int == -999999
        has_configs = HasInteger(999999)
        assert has_configs.my_int == 999999


if __name__ == "__main__":
    unittest.main()
