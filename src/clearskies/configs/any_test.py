import unittest
from unittest.mock import MagicMock
import clearskies.decorators

from clearskies import Configurable, configs


class HasConfigs(Configurable):
    anything = configs.Any()

    @clearskies.decorators.parameters_to_properties
    def __init__(self, anything):
        self.finalize_and_validate_configuration()


class AnyTest(unittest.TestCase):
    def test_allow(self):
        has_configs = HasConfigs("blahblahblah")
        assert has_configs.anything == "blahblahblah"

        more_configs = HasConfigs(5)
        assert more_configs.anything == 5
