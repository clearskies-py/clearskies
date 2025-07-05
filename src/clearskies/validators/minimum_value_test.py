import unittest
from unittest.mock import MagicMock

from .minimum_value import MinimumValue


class MinimumValueTest(unittest.TestCase):
    def setUp(self):
        self.minimum_value = MinimumValue(10)

    def test_check_length(self):
        error = self.minimum_value.check("model", "age", {"age": "10"})  # type: ignore
        self.assertEqual("", error)
        error = self.minimum_value.check("model", "age", {"age": 10})  # type: ignore
        self.assertEqual("", error)
        error = self.minimum_value.check("model", "age", {"age": ""})  # type: ignore
        self.assertEqual("age must be an integer or float", error)
        error = self.minimum_value.check("model", "age", {})  # type: ignore
        self.assertEqual("", error)
        error = self.minimum_value.check("model", "age", {"age": -1})  # type: ignore
        self.assertEqual("'age' must be at least 10.", error)
