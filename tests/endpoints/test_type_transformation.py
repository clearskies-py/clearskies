"""Tests for input type forcing and validation across endpoints."""

import clearskies
from tests.test_base import TestBase

# ──────────────────────────────────────────────────────────────────────────────
# 1. Column-level force_value_from_input() tests
# ──────────────────────────────────────────────────────────────────────────────


class ForceValueFromInputTest(TestBase):
    """Test force_value_from_input() on Integer, Float, Boolean columns."""

    # ── Integer ────────────────────────────────────────────────────────────

    def test_integer_forces_string_to_int(self):
        col = clearskies.columns.Integer()
        assert col.force_value_from_input("25") == 25

    def test_integer_forces_negative_string(self):
        col = clearskies.columns.Integer()
        assert col.force_value_from_input("-3") == -3

    def test_integer_passes_through_native_int(self):
        col = clearskies.columns.Integer()
        assert col.force_value_from_input(25) == 25

    def test_integer_returns_original_on_invalid_string(self):
        col = clearskies.columns.Integer()
        assert col.force_value_from_input("abc") == "abc"

    def test_integer_returns_original_on_empty_string(self):
        col = clearskies.columns.Integer()
        assert col.force_value_from_input("") == ""

    def test_integer_does_not_treat_bool_as_int(self):
        col = clearskies.columns.Integer()
        assert col.force_value_from_input(True) is True
        assert col.force_value_from_input(False) is False

    # ── Float ──────────────────────────────────────────────────────────────

    def test_float_forces_string_to_float(self):
        col = clearskies.columns.Float()
        assert col.force_value_from_input("3.14") == 3.14

    def test_float_forces_integer_to_float(self):
        col = clearskies.columns.Float()
        assert col.force_value_from_input(5) == 5.0
        assert isinstance(col.force_value_from_input(5), float)

    def test_float_forces_integer_string_to_float(self):
        col = clearskies.columns.Float()
        assert col.force_value_from_input("42") == 42.0

    def test_float_passes_through_native_float(self):
        col = clearskies.columns.Float()
        assert col.force_value_from_input(3.14) == 3.14

    def test_float_returns_original_on_invalid_string(self):
        col = clearskies.columns.Float()
        assert col.force_value_from_input("abc") == "abc"

    def test_float_does_not_treat_bool_as_int(self):
        col = clearskies.columns.Float()
        assert col.force_value_from_input(True) is True
        assert col.force_value_from_input(False) is False

    # ── Boolean ────────────────────────────────────────────────────────────

    def test_boolean_forces_string_true(self):
        col = clearskies.columns.Boolean()
        assert col.force_value_from_input("true") is True
        assert col.force_value_from_input("True") is True
        assert col.force_value_from_input("TRUE") is True

    def test_boolean_forces_string_false(self):
        col = clearskies.columns.Boolean()
        assert col.force_value_from_input("false") is False
        assert col.force_value_from_input("False") is False
        assert col.force_value_from_input("FALSE") is False

    def test_boolean_forces_string_1_and_0(self):
        col = clearskies.columns.Boolean()
        assert col.force_value_from_input("1") is True
        assert col.force_value_from_input("0") is False

    def test_boolean_forces_yes_no(self):
        col = clearskies.columns.Boolean()
        assert col.force_value_from_input("yes") is True
        assert col.force_value_from_input("no") is False

    def test_boolean_forces_empty_string_to_false(self):
        col = clearskies.columns.Boolean()
        assert col.force_value_from_input("") is False

    def test_boolean_passes_through_native_bool(self):
        col = clearskies.columns.Boolean()
        assert col.force_value_from_input(True) is True
        assert col.force_value_from_input(False) is False

    def test_boolean_returns_original_on_invalid_string(self):
        col = clearskies.columns.Boolean()
        result = col.force_value_from_input("maybe")
        assert result == "maybe"

    # ── String (no-op) ─────────────────────────────────────────────────────

    def test_string_column_returns_value_unchanged(self):
        col = clearskies.columns.String()
        assert col.force_value_from_input("hello") == "hello"
        assert col.force_value_from_input(42) == 42

    # ── Timestamp ─────────────────────────────────────────────────────────

    def test_timestamp_forces_string_to_int(self):
        col = clearskies.columns.Timestamp()
        assert col.force_value_from_input("1234567890") == 1234567890

    def test_timestamp_passes_through_native_int(self):
        col = clearskies.columns.Timestamp()
        assert col.force_value_from_input(1234567890) == 1234567890

    def test_timestamp_returns_original_on_invalid_string(self):
        col = clearskies.columns.Timestamp()
        assert col.force_value_from_input("not_a_timestamp") == "not_a_timestamp"

    def test_timestamp_does_not_treat_bool_as_int(self):
        col = clearskies.columns.Timestamp()
        assert col.force_value_from_input(True) is True
        assert col.force_value_from_input(False) is False


# ──────────────────────────────────────────────────────────────────────────────
# Helper: isolated model factory to avoid MemoryBackend cross-test pollution
# ──────────────────────────────────────────────────────────────────────────────


def _make_user_model():
    """Create an isolated model class to avoid MemoryBackend cross-test pollution."""

    class User(clearskies.Model):
        id_column_name = "id"
        backend = clearskies.backends.MemoryBackend()
        id = clearskies.columns.Uuid()
        name = clearskies.columns.String()
        age = clearskies.columns.Integer()
        active = clearskies.columns.Boolean()
        score = clearskies.columns.Float()

    return User


def _make_integer_id_model():
    """Create a model with an integer id column."""

    class IntegerIdModel(clearskies.Model):
        id_column_name = "id"
        backend = clearskies.backends.MemoryBackend()
        id = clearskies.columns.Integer()
        name = clearskies.columns.String()

    return IntegerIdModel


# ──────────────────────────────────────────────────────────────────────────────
# 2. Force-then-validate flow tests (Create endpoint with body data)
# ──────────────────────────────────────────────────────────────────────────────


class ForceBeforeValidateTest(TestBase):
    """Test that forcing happens before validation in the Create endpoint."""

    def test_string_age_forced_to_int_passes_validation(self):
        """String '25' → forced to int(25) → passes Integer validation."""
        User = _make_user_model()
        context = clearskies.contexts.Context(
            clearskies.endpoints.Create(
                model_class=User,
                writeable_column_names=["name", "age"],
                readable_column_names=["id", "name", "age"],
                transform_input_types=True,
            ),
        )
        status_code, response_data, _ = context(
            request_method="POST",
            body={"name": "Alice", "age": "25"},
        )
        assert status_code == 200
        assert response_data["status"] == "success"
        assert response_data["data"]["age"] == 25

    def test_invalid_string_age_fails_validation(self):
        """String 'abc' → stays 'abc' → fails Integer validation."""
        User = _make_user_model()
        context = clearskies.contexts.Context(
            clearskies.endpoints.Create(
                model_class=User,
                writeable_column_names=["name", "age"],
                readable_column_names=["id", "name", "age"],
                transform_input_types=True,
            ),
        )
        status_code, response_data, _ = context(
            request_method="POST",
            body={"name": "Alice", "age": "abc"},
        )
        assert response_data["status"] == "input_errors"
        assert "age" in response_data["input_errors"]

    def test_string_boolean_forced_to_bool_passes_validation(self):
        """String 'false' → forced to bool(False) → passes Boolean validation."""
        User = _make_user_model()
        context = clearskies.contexts.Context(
            clearskies.endpoints.Create(
                model_class=User,
                writeable_column_names=["name", "active"],
                readable_column_names=["id", "name", "active"],
                transform_input_types=True,
            ),
        )
        status_code, response_data, _ = context(
            request_method="POST",
            body={"name": "Alice", "active": "false"},
        )
        assert status_code == 200
        assert response_data["status"] == "success"
        assert response_data["data"]["active"] is False

    def test_invalid_boolean_string_fails_validation(self):
        """String 'maybe' → stays 'maybe' → fails Boolean validation."""
        User = _make_user_model()
        context = clearskies.contexts.Context(
            clearskies.endpoints.Create(
                model_class=User,
                writeable_column_names=["name", "active"],
                readable_column_names=["id", "name", "active"],
                transform_input_types=True,
            ),
        )
        status_code, response_data, _ = context(
            request_method="POST",
            body={"name": "Alice", "active": "maybe"},
        )
        assert response_data["status"] == "input_errors"
        assert "active" in response_data["input_errors"]

    def test_string_float_forced_to_float_passes_validation(self):
        """String '3.14' → forced to float(3.14) → passes Float validation."""
        User = _make_user_model()
        context = clearskies.contexts.Context(
            clearskies.endpoints.Create(
                model_class=User,
                writeable_column_names=["name", "score"],
                readable_column_names=["id", "name", "score"],
                transform_input_types=True,
            ),
        )
        status_code, response_data, _ = context(
            request_method="POST",
            body={"name": "Alice", "score": "3.14"},
        )
        assert status_code == 200
        assert response_data["status"] == "success"
        assert response_data["data"]["score"] == 3.14


# ──────────────────────────────────────────────────────────────────────────────
# 3. _body_as_json is updated after forcing
# ──────────────────────────────────────────────────────────────────────────────


class BodyAsJsonUpdateTest(TestBase):
    """Verify that _body_as_json on input_output is updated with forced data."""

    def test_body_as_json_updated_after_forcing(self):
        """After forcing, the callable receives forced values via request_data."""
        User = _make_user_model()
        received = {}

        def capture_request_data(request_data):
            received.update(request_data)
            return request_data

        context = clearskies.contexts.Context(
            clearskies.endpoints.Callable(
                capture_request_data,
                model_class=User,
                writeable_column_names=["name", "age"],
                request_methods=["POST"],
                transform_input_types=True,
            ),
        )
        status_code, response_data, _ = context(
            request_method="POST",
            body={"name": "Alice", "age": "25"},
        )
        assert status_code == 200
        # The callable received forced values (int, not string)
        assert received["age"] == 25
        assert isinstance(received["age"], int)


# ──────────────────────────────────────────────────────────────────────────────
# 4. Routing data validation (Get, Update, Delete)
# ──────────────────────────────────────────────────────────────────────────────


class RoutingDataValidationTest(TestBase):
    """Test that routing data is forced and written back to input_output."""

    def test_get_with_valid_uuid_routing(self):
        """Valid UUID routing data passes validation and fetches record."""
        User = _make_user_model()
        context = clearskies.contexts.Context(
            clearskies.endpoints.Get(
                model_class=User,
                url="/{id}",
                readable_column_names=["id", "name"],
                transform_input_types=True,
            ),
            bindings={
                "memory_backend_default_data": [
                    {
                        "model_class": User,
                        "records": [
                            {"id": "1-2-3-4", "name": "Alice", "age": 30, "active": True, "score": 4.5},
                        ],
                    },
                ],
            },
        )
        status_code, response_data, _ = context(url="/1-2-3-4")
        assert status_code == 200
        assert response_data["data"]["id"] == "1-2-3-4"
        assert response_data["data"]["name"] == "Alice"

    def test_get_invalid_routing_data_returns_not_found(self):
        """Non-existent id fails with 404."""
        User = _make_user_model()
        context = clearskies.contexts.Context(
            clearskies.endpoints.Get(
                model_class=User,
                url="/{id}",
                readable_column_names=["id", "name"],
                transform_input_types=True,
            ),
            bindings={
                "memory_backend_default_data": [
                    {
                        "model_class": User,
                        "records": [
                            {"id": "1-2-3-4", "name": "Alice"},
                        ],
                    },
                ],
            },
        )
        status_code, response_data, _ = context(url="/nonexistent")
        assert status_code == 404

    def test_delete_with_valid_uuid_routing(self):
        User = _make_user_model()
        context = clearskies.contexts.Context(
            clearskies.endpoints.Delete(
                model_class=User,
                url="/{id}",
                transform_input_types=True,
            ),
            bindings={
                "memory_backend_default_data": [
                    {
                        "model_class": User,
                        "records": [
                            {"id": "1-2-3-4", "name": "Alice", "age": 30, "active": True, "score": 4.5},
                        ],
                    },
                ],
            },
        )
        status_code, response_data, _ = context(url="/1-2-3-4", request_method="DELETE")
        assert status_code == 200
        assert response_data["status"] == "success"

    def test_update_forces_body_data_with_routing(self):
        """Update forces body data types while routing stays as strings."""
        User = _make_user_model()
        context = clearskies.contexts.Context(
            clearskies.endpoints.Update(
                model_class=User,
                url="/{id}",
                writeable_column_names=["name", "age"],
                readable_column_names=["id", "name", "age"],
                transform_input_types=True,
            ),
            bindings={
                "memory_backend_default_data": [
                    {
                        "model_class": User,
                        "records": [
                            {"id": "1-2-3-4", "name": "Alice", "age": 30, "active": True, "score": 4.5},
                        ],
                    },
                ],
            },
        )
        status_code, response_data, _ = context(
            url="/1-2-3-4",
            request_method="PATCH",
            body={"name": "Bob", "age": "35"},
        )
        assert status_code == 200
        assert response_data["data"]["name"] == "Bob"
        assert response_data["data"]["age"] == 35


# ──────────────────────────────────────────────────────────────────────────────
# 5. Routing data validation with Integer id model
# ──────────────────────────────────────────────────────────────────────────────


class RoutingIntegerValidationTest(TestBase):
    """Test that routing data is validated against integer columns."""

    def test_routing_validates_integer_id_rejects_non_numeric(self):
        """Non-numeric id string is rejected by validate_routing_data."""
        IntegerIdModel = _make_integer_id_model()
        context = clearskies.contexts.Context(
            clearskies.endpoints.Get(
                model_class=IntegerIdModel,
                url="/{id}",
                readable_column_names=["id", "name"],
                transform_input_types=True,
            ),
        )
        status_code, response_data, _ = context(url="/not_a_number")
        assert response_data["status"] == "input_errors"
        assert "id" in response_data["input_errors"]

    def test_routing_validates_integer_id_accepts_numeric(self):
        """Numeric id string passes validation."""
        IntegerIdModel = _make_integer_id_model()
        context = clearskies.contexts.Context(
            clearskies.endpoints.Get(
                model_class=IntegerIdModel,
                url="/{id}",
                readable_column_names=["id", "name"],
                transform_input_types=True,
            ),
            bindings={
                "memory_backend_default_data": [
                    {
                        "model_class": IntegerIdModel,
                        "records": [
                            {"id": 42, "name": "Alice"},
                        ],
                    },
                ],
            },
        )
        status_code, response_data, _ = context(url="/42")
        assert status_code == 200
        assert response_data["data"]["name"] == "Alice"


# ──────────────────────────────────────────────────────────────────────────────
# 6. List endpoint forcing
# ──────────────────────────────────────────────────────────────────────────────


class ListForcingTest(TestBase):
    """Test that the List endpoint forces query parameters via force_query_parameters."""

    def test_limit_forced_to_int(self):
        User = _make_user_model()
        context = clearskies.contexts.Context(
            clearskies.endpoints.List(
                model_class=User,
                readable_column_names=["id", "name"],
                sortable_column_names=["id", "name"],
                searchable_column_names=[],
                default_sort_column_name="id",
                transform_input_types=True,
            ),
            bindings={
                "memory_backend_default_data": [
                    {
                        "model_class": User,
                        "records": [
                            {"id": "1-2-3-4", "name": "Alice", "age": 30, "active": True, "score": 4.5},
                            {"id": "1-2-3-5", "name": "Bob", "age": 25, "active": False, "score": 3.2},
                            {"id": "1-2-3-6", "name": "Carol", "age": 35, "active": True, "score": 4.8},
                        ],
                    },
                ],
            },
        )
        status_code, response_data, _ = context(
            query_parameters={"limit": "2"},
        )
        assert status_code == 200
        assert len(response_data["data"]) == 2
        assert response_data["pagination"]["limit"] == 2

    def test_invalid_limit_raises_error(self):
        User = _make_user_model()
        context = clearskies.contexts.Context(
            clearskies.endpoints.List(
                model_class=User,
                readable_column_names=["id", "name"],
                sortable_column_names=["id", "name"],
                searchable_column_names=[],
                default_sort_column_name="id",
                transform_input_types=True,
            ),
        )
        status_code, response_data, _ = context(
            query_parameters={"limit": "abc"},
        )
        assert status_code == 400 or response_data.get("status") in ("client_error", "input_errors")


# ──────────────────────────────────────────────────────────────────────────────
# 7. Flag behavior (defaults, enabling)
# ──────────────────────────────────────────────────────────────────────────────


class TransformFlagTest(TestBase):
    """Test that transform_input_types defaults to False and can be enabled."""

    def test_flag_defaults_to_false(self):
        User = _make_user_model()

        endpoint = clearskies.endpoints.List(
            model_class=User,
            readable_column_names=["id", "name"],
            sortable_column_names=["id"],
            default_sort_column_name="id",
        )
        assert endpoint.transform_input_types is False

        endpoint = clearskies.endpoints.Get(
            model_class=User,
            url="/{id}",
            readable_column_names=["id", "name"],
        )
        assert endpoint.transform_input_types is False

        endpoint = clearskies.endpoints.Callable(
            to_call=lambda: {"hello": "world"},
        )
        assert endpoint.transform_input_types is False

    def test_flag_can_be_enabled(self):
        User = _make_user_model()

        endpoint = clearskies.endpoints.List(
            model_class=User,
            readable_column_names=["id", "name"],
            sortable_column_names=["id"],
            default_sort_column_name="id",
            transform_input_types=True,
        )
        assert endpoint.transform_input_types is True

        endpoint = clearskies.endpoints.Get(
            model_class=User,
            url="/{id}",
            readable_column_names=["id", "name"],
            transform_input_types=True,
        )
        assert endpoint.transform_input_types is True

        endpoint = clearskies.endpoints.Callable(
            to_call=lambda: {"hello": "world"},
            transform_input_types=True,
        )
        assert endpoint.transform_input_types is True

    def test_no_forcing_when_flag_is_false(self):
        """Without transform_input_types, native typed values still work."""
        User = _make_user_model()
        context = clearskies.contexts.Context(
            clearskies.endpoints.Create(
                model_class=User,
                writeable_column_names=["name", "age"],
                readable_column_names=["id", "name", "age"],
                transform_input_types=False,
            ),
        )
        status_code, response_data, _ = context(
            request_method="POST",
            body={"name": "Alice", "age": 25},
        )
        assert status_code == 200
        assert response_data["data"]["age"] == 25


# ──────────────────────────────────────────────────────────────────────────────
# 8. No input_schema on non-Callable endpoints
# ──────────────────────────────────────────────────────────────────────────────


class NoInputSchemaOnModelEndpointsTest(TestBase):
    """Verify input_schema is NOT accepted on Get/Delete/Create/Update/List endpoints."""

    def test_create_has_no_input_schema_parameter(self):
        import inspect

        sig = inspect.signature(clearskies.endpoints.Create.__init__)
        assert "input_schema" not in sig.parameters

    def test_update_has_no_input_schema_parameter(self):
        import inspect

        sig = inspect.signature(clearskies.endpoints.Update.__init__)
        assert "input_schema" not in sig.parameters

    def test_get_has_no_input_schema_parameter(self):
        import inspect

        sig = inspect.signature(clearskies.endpoints.Get.__init__)
        assert "input_schema" not in sig.parameters

    def test_delete_has_no_input_schema_parameter(self):
        import inspect

        sig = inspect.signature(clearskies.endpoints.Delete.__init__)
        assert "input_schema" not in sig.parameters

    def test_list_has_no_input_schema_parameter(self):
        import inspect

        sig = inspect.signature(clearskies.endpoints.List.__init__)
        assert "input_schema" not in sig.parameters

    def test_callable_still_has_input_schema(self):
        """Callable IS the only endpoint that supports input_schema."""
        import inspect

        sig = inspect.signature(clearskies.endpoints.Callable.__init__)
        assert "input_schema" in sig.parameters


# ──────────────────────────────────────────────────────────────────────────────
# 9. Callable endpoint with input_schema
# ──────────────────────────────────────────────────────────────────────────────


class CallableWithInputSchemaTest(TestBase):
    """Test the Callable endpoint with input_schema and type forcing."""

    def test_callable_forces_body_with_input_schema(self):
        class CallableInput(clearskies.Schema):
            user_id = clearskies.columns.Integer()
            limit = clearskies.columns.Integer()

        context = clearskies.contexts.Context(
            clearskies.endpoints.Callable(
                lambda request_data: request_data,
                input_schema=CallableInput,
                request_methods=["POST"],
                transform_input_types=True,
            ),
        )
        status_code, response_data, _ = context(
            request_method="POST",
            body={"user_id": "42", "limit": "100"},
        )
        assert status_code == 200
        assert response_data["data"]["user_id"] == 42
        assert response_data["data"]["limit"] == 100

    def test_callable_validates_routing_data_with_input_schema(self):
        """Routing data is validated (forced to proper types for validation).

        Invalid routing values are caught by validate_routing_data.
        """

        class CallableInput(clearskies.Schema):
            user_id = clearskies.columns.Integer()

        context = clearskies.contexts.Context(
            clearskies.endpoints.Callable(
                lambda routing_data: {"user_id": routing_data["user_id"]},
                input_schema=CallableInput,
                url="/{user_id}",
                request_methods=["POST"],
                transform_input_types=True,
            ),
        )
        # Invalid routing value
        status_code, response_data, _ = context(
            url="/not_a_number",
            request_method="POST",
            body={"user_id": "42"},
        )
        assert response_data["status"] == "input_errors"
        assert "user_id" in response_data["input_errors"]
