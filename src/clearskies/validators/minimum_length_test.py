import unittest
from unittest.mock import MagicMock

from .minimum_length import MinimumLength


class MinimumLengthTest(unittest.TestCase):
    def setUp(self):
        self.minimum_length = MinimumLength(10)

    def test_check_length(self):
        error = self.minimum_length.check("model", "name", {"name": "12345678901"})  # type: ignore
        self.assertEqual("", error)
        error = self.minimum_length.check("model", "name", {"name": ""})  # type: ignore
        self.assertEqual("", error)
        error = self.minimum_length.check("model", "name", {})  # type: ignore
        self.assertEqual("", error)
        error = self.minimum_length.check("model", "name", {"name": "123456789"})  # type: ignore
        self.assertEqual("'name' must be at least 10 characters long.", error)
