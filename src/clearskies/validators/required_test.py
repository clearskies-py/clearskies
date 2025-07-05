import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from .required import Required


class RequiredTest(unittest.TestCase):
    def setUp(self):
        self.required = Required()

    def test_create(self):
        error = self.required.check(False, "name", {})  # type: ignore
        self.assertEqual("'name' is required.", error)
        error = self.required.check(False, "name", {"name": " "})  # type: ignore
        self.assertEqual("'name' is required.", error)
        error = self.required.check(False, "name", {"name": 0})  # type: ignore
        self.assertEqual("'name' is required.", error)

        error = self.required.check(False, "name", {"name": "sup"})  # type: ignore
        self.assertEqual("", error)
        error = self.required.check(False, "name", {"name": 5})  # type: ignore
        self.assertEqual("", error)

    def test_update(self):
        # The database already has a value for the required field
        exists = SimpleNamespace(name="sup")
        error = self.required.check(exists, "name", {"name": "  "})  # type: ignore
        self.assertEqual("'name' is required.", error)
        error = self.required.check(exists, "name", {"name": "hey"})  # type: ignore
        self.assertEqual("", error)
        error = self.required.check(exists, "name", {})  # type: ignore
        self.assertEqual("", error)

        # The database does not have a value for the required field
        exists_no_value = SimpleNamespace(name="")
        error = self.required.check(exists_no_value, "name", {"name": "   "})  # type: ignore
        self.assertEqual("'name' is required.", error)
        error = self.required.check(exists_no_value, "name", {})  # type: ignore
        self.assertEqual("'name' is required.", error)
        error = self.required.check(exists_no_value, "name", {"name": "okay"})  # type: ignore
        self.assertEqual("", error)
