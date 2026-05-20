import json

import clearskies
from tests.test_base import TestBase


class ListFromBackendTest(TestBase):
    """Unit tests for List.from_backend — exercises type coercion and value_type validation."""

    def _col(self, **kwargs):
        """Create a configured List column, optionally with value_type."""
        col = clearskies.columns.List(**kwargs)
        col.name = "items"
        return col

    # --- None / falsy inputs ---

    def test_none_returns_none(self):
        assert self._col().from_backend(None) is None

    def test_empty_string_returns_none(self):
        assert self._col().from_backend("") is None

    # --- Already-parsed list ---

    def test_list_passthrough_no_type(self):
        assert self._col().from_backend([1, 2, 3]) == [1, 2, 3]

    def test_empty_list_passthrough(self):
        assert self._col().from_backend([]) == []

    def test_list_correct_value_type_passes(self):
        assert self._col(value_type=str).from_backend(["a", "b"]) == ["a", "b"]

    def test_list_wrong_value_type_returns_none(self):
        assert self._col(value_type=str).from_backend([1, 2]) is None

    def test_list_partial_wrong_value_type_returns_none(self):
        assert self._col(value_type=str).from_backend(["a", 1]) is None

    def test_list_tuple_value_type_valid(self):
        assert self._col(value_type=(str, int)).from_backend(["a", 1]) == ["a", 1]

    def test_list_tuple_value_type_invalid(self):
        assert self._col(value_type=(str, int)).from_backend(["a", 1.5]) is None

    # --- JSON string inputs ---

    def test_json_string_becomes_list(self):
        assert self._col().from_backend("[1, 2, 3]") == [1, 2, 3]

    def test_json_string_empty_list(self):
        assert self._col().from_backend("[]") == []

    def test_json_string_list_of_dicts(self):
        assert self._col().from_backend('[{"a": 1}]') == [{"a": 1}]

    def test_invalid_json_returns_none(self):
        assert self._col().from_backend("{not valid json}") is None

    def test_json_dict_not_list_returns_none(self):
        assert self._col().from_backend('{"key": "value"}') is None

    def test_json_string_wrong_value_type_returns_none(self):
        assert self._col(value_type=str).from_backend("[1, 2, 3]") is None

    def test_json_string_correct_value_type_passes(self):
        assert self._col(value_type=str).from_backend('["a", "b"]') == ["a", "b"]

    def test_json_string_tuple_value_type_valid(self):
        result = self._col(value_type=(str, int)).from_backend('["hello", 42]')
        assert result == ["hello", 42]

    def test_json_string_tuple_value_type_invalid(self):
        assert self._col(value_type=(str, int)).from_backend("[1.5, 2.5]") is None


class ListToBackendTest(TestBase):
    """Unit tests for List.to_backend — serialisation to JSON string."""

    def _col(self, **kwargs):
        col = clearskies.columns.List(**kwargs)
        col.name = "items"
        return col

    def test_list_serialised_to_json_string(self):
        result = self._col().to_backend({"items": [1, 2, 3]})
        assert result["items"] == "[1, 2, 3]"

    def test_list_of_dicts_serialised(self):
        result = self._col().to_backend({"items": [{"a": 1}]})
        assert json.loads(result["items"]) == [{"a": 1}]

    def test_empty_list_serialised(self):
        result = self._col().to_backend({"items": []})
        assert result["items"] == "[]"

    def test_none_value_passed_through(self):
        result = self._col().to_backend({"items": None})
        assert result["items"] is None

    def test_missing_key_passed_through(self):
        result = self._col().to_backend({"other": "value"})
        assert "items" not in result

    def test_already_a_string_idempotent(self):
        # If the value arrives as a serialised string (e.g. from a raw backend read),
        # to_backend should leave it untouched.
        result = self._col().to_backend({"items": "[1, 2, 3]"})
        assert result["items"] == "[1, 2, 3]"


class ListForceValueFromInputTest(TestBase):
    """Unit tests for List.force_value_from_input — JSON-string coercion at the API boundary."""

    def _col(self):
        col = clearskies.columns.List()
        col.name = "items"
        return col

    def test_list_returned_unchanged(self):
        assert self._col().force_value_from_input([1, 2]) == [1, 2]

    def test_json_string_becomes_list(self):
        assert self._col().force_value_from_input("[1, 2, 3]") == [1, 2, 3]

    def test_json_string_empty_list(self):
        assert self._col().force_value_from_input("[]") == []

    def test_invalid_json_string_unchanged(self):
        assert self._col().force_value_from_input("{bad json}") == "{bad json}"

    def test_json_string_that_is_dict_unchanged(self):
        # A valid JSON string but not a list — return original so validation can reject it.
        original = '{"key": "val"}'
        assert self._col().force_value_from_input(original) == original

    def test_non_string_non_list_unchanged(self):
        assert self._col().force_value_from_input(42) == 42


class ListInputErrorForValueTest(TestBase):
    """Unit tests for List.input_error_for_value — API-level validation (400 boundary)."""

    def _col(self, **kwargs):
        col = clearskies.columns.List(**kwargs)
        col.name = "items"
        return col

    def test_non_list_string_returns_error(self):
        error = self._col().input_error_for_value("not a list")
        assert error == "value must be a list"

    def test_non_list_dict_returns_error(self):
        error = self._col().input_error_for_value({"key": "val"})
        assert error == "value must be a list"

    def test_valid_list_no_type_restriction(self):
        assert self._col().input_error_for_value([1, "two", 3.0]) == ""

    def test_empty_list_no_type_restriction(self):
        assert self._col().input_error_for_value([]) == ""

    def test_empty_list_with_value_type(self):
        # No items to check — always valid.
        assert self._col(value_type=str).input_error_for_value([]) == ""

    def test_correct_value_type_no_error(self):
        assert self._col(value_type=str).input_error_for_value(["a", "b", "c"]) == ""

    def test_wrong_value_type_returns_error(self):
        error = self._col(value_type=str).input_error_for_value([1, 2])
        assert "str" in error
        assert "int" in error

    def test_partial_wrong_value_type_first_bad_item_reported(self):
        error = self._col(value_type=str).input_error_for_value(["ok", 42])
        assert error != ""

    def test_tuple_value_type_valid(self):
        assert self._col(value_type=(str, int)).input_error_for_value(["hello", 42]) == ""

    def test_tuple_value_type_invalid(self):
        error = self._col(value_type=(str, int)).input_error_for_value(["hello", 1.5])
        assert "str | int" in error
        assert "float" in error


class ListTypeNameTest(TestBase):
    """Unit tests for List._type_name — human-readable type label for error messages."""

    def _col(self, **kwargs):
        col = clearskies.columns.List(**kwargs)
        col.name = "items"
        return col

    def test_single_type(self):
        assert self._col(value_type=str)._type_name() == "str"

    def test_single_type_int(self):
        assert self._col(value_type=int)._type_name() == "int"

    def test_tuple_two_types(self):
        assert self._col(value_type=(str, int))._type_name() == "str | int"

    def test_tuple_three_types(self):
        assert self._col(value_type=(str, int, float))._type_name() == "str | int | float"


class ListContextTest(TestBase):
    """End-to-end tests for the List column through a full clearskies Context + endpoint."""

    def _make_context(self, column):
        class MyModel(clearskies.Model):
            backend = clearskies.backends.MemoryBackend()
            id_column_name = "id"

            id = clearskies.columns.Uuid()
            items = column

        return clearskies.contexts.Context(
            clearskies.endpoints.Create(
                MyModel,
                writeable_column_names=["items"],
                readable_column_names=["id", "items"],
            ),
            classes=[MyModel],
        )

    # --- Untyped List column ---

    def test_create_with_list_of_mixed_types(self):
        context = self._make_context(clearskies.columns.List())
        _, response, _ = context(request_method="POST", body={"items": [1, "two", {"three": 3}]})
        assert response["data"]["items"] == [1, "two", {"three": 3}]

    def test_create_with_empty_list(self):
        context = self._make_context(clearskies.columns.List())
        _, response, _ = context(request_method="POST", body={"items": []})
        assert response["data"]["items"] == []

    def test_create_with_non_list_dict_returns_input_error(self):
        context = self._make_context(clearskies.columns.List())
        _, response, _ = context(request_method="POST", body={"items": {"key": "value"}})
        assert response["status"] == "input_errors"
        assert "items" in response["input_errors"]

    def test_create_with_string_returns_input_error(self):
        context = self._make_context(clearskies.columns.List())
        _, response, _ = context(request_method="POST", body={"items": "not a list"})
        assert response["status"] == "input_errors"
        assert "items" in response["input_errors"]

    # --- value_type=str ---

    def test_create_list_of_strings_valid(self):
        context = self._make_context(clearskies.columns.List(value_type=str))
        _, response, _ = context(request_method="POST", body={"items": ["alpha", "beta"]})
        assert response["data"]["items"] == ["alpha", "beta"]

    def test_create_wrong_item_type_returns_input_error(self):
        context = self._make_context(clearskies.columns.List(value_type=str))
        _, response, _ = context(request_method="POST", body={"items": [1, 2, 3]})
        assert response["status"] == "input_errors"
        assert "items" in response["input_errors"]
        assert "str" in response["input_errors"]["items"]

    def test_create_partial_wrong_item_type_returns_input_error(self):
        context = self._make_context(clearskies.columns.List(value_type=str))
        _, response, _ = context(request_method="POST", body={"items": ["valid", 42]})
        assert response["status"] == "input_errors"
        assert "items" in response["input_errors"]

    # --- value_type=(str, int) ---

    def test_create_tuple_value_type_valid(self):
        context = self._make_context(clearskies.columns.List(value_type=(str, int)))
        _, response, _ = context(request_method="POST", body={"items": ["hello", 42]})
        assert response["data"]["items"] == ["hello", 42]

    def test_create_tuple_value_type_invalid_item_returns_error(self):
        context = self._make_context(clearskies.columns.List(value_type=(str, int)))
        _, response, _ = context(request_method="POST", body={"items": ["hello", 3.14]})
        assert response["status"] == "input_errors"
        assert "items" in response["input_errors"]
        assert "str | int" in response["input_errors"]["items"]

    # --- value_type=int ---

    def test_create_list_of_ints_valid(self):
        context = self._make_context(clearskies.columns.List(value_type=int))
        _, response, _ = context(request_method="POST", body={"items": [10, 20, 30]})
        assert response["data"]["items"] == [10, 20, 30]

    def test_create_list_of_ints_with_string_returns_error(self):
        context = self._make_context(clearskies.columns.List(value_type=int))
        _, response, _ = context(request_method="POST", body={"items": [10, "twenty"]})
        assert response["status"] == "input_errors"
        assert "items" in response["input_errors"]
