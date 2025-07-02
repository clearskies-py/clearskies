import unittest
from unittest.mock import MagicMock

from .maximum_value import MaximumValue


class MaximumValueTest(unittest.TestCase):
    def setUp(self):
        self.maximum_value = MaximumValue(10)

    def test_check_length(self):
        error = self.maximum_value.check("model", "age", {"age": "10"})  # type: ignore
        self.assertEqual("", error)
        error = self.maximum_value.check("model", "age", {"age": 10})  # type: ignore
        self.assertEqual("", error)
        error = self.maximum_value.check("model", "age", {"age": ""})  # type: ignore
        self.assertEqual("age must be an integer or float", error)
        error = self.maximum_value.check("model", "age", {})  # type: ignore
        self.assertEqual("", error)
        error = self.maximum_value.check("model", "age", {"age": -5})  # type: ignore
        self.assertEqual("", error)
        error = self.maximum_value.check("model", "age", {"age": 11})  # type: ignore
        self.assertEqual("'age' must be at most 10.", error)
