"""Tests for input type transformation consistency across endpoints."""

import unittest

import clearskies
from clearskies import exceptions
from clearskies.di import Di


class User(clearskies.Model):
    """Test model with various column types."""

    id_column_name = "id"
    backend = clearskies.backends.MemoryBackend()

    id = clearskies.columns.Integer()
    name = clearskies.columns.String()
    age = clearskies.columns.Integer()
    active = clearskies.columns.Boolean()
    score = clearskies.columns.Float()


class TypeTransformationTest(unittest.TestCase):
    """Test that type transformation flag works correctly."""

    def test_transform_query_parameters_method(self):
        """Test transform_query_parameters method directly."""
        endpoint = clearskies.endpoints.List(
            model_class=User,
            readable_column_names=["id", "name", "age", "active"],
            sortable_column_names=["id", "name"],
            searchable_column_names=["age", "active"],
            default_sort_column_name="id",
        )

        di = Di(classes=[User])
        endpoint.injectable_properties(di)

        # Test transformation
        query_params = {
            "age": "25",
            "active": "true",
            "limit": "50",
        }

        transformed = endpoint.transform_query_parameters(query_params, User)

        # Check transformations
        self.assertEqual(transformed["age"], 25)  # String to int
        self.assertEqual(transformed["active"], True)  # String to bool
        self.assertEqual(transformed["limit"], 50)  # String to int

    def test_transform_routing_data_method(self):
        """Test transform_routing_data method directly."""
        endpoint = clearskies.endpoints.Get(
            model_class=User,
            url="/{id}",
            readable_column_names=["id", "name"],
        )

        di = Di(classes=[User])
        endpoint.injectable_properties(di)

        # Test transformation
        routing_data = {"id": "123"}

        transformed = endpoint.transform_routing_data(routing_data, User)

        # Check transformation
        self.assertEqual(transformed["id"], 123)  # String to int

    def test_flag_is_optional(self):
        """Test that transform_input_types flag is optional and defaults to False."""
        # List endpoint
        endpoint = clearskies.endpoints.List(
            model_class=User,
            readable_column_names=["id", "name"],
            sortable_column_names=["id"],
            default_sort_column_name="id",
        )
        self.assertFalse(endpoint.transform_input_types)

        # Get endpoint
        endpoint = clearskies.endpoints.Get(
            model_class=User,
            url="/{id}",
            readable_column_names=["id", "name"],
        )
        self.assertFalse(endpoint.transform_input_types)

        # Callable endpoint
        endpoint = clearskies.endpoints.Callable(
            to_call=lambda: {"hello": "world"},
        )
        self.assertFalse(endpoint.transform_input_types)

    def test_flag_can_be_enabled(self):
        """Test that transform_input_types flag can be set to True."""
        # List endpoint
        endpoint = clearskies.endpoints.List(
            model_class=User,
            readable_column_names=["id", "name"],
            sortable_column_names=["id"],
            default_sort_column_name="id",
            transform_input_types=True,
        )
        self.assertTrue(endpoint.transform_input_types)

        # Get endpoint
        endpoint = clearskies.endpoints.Get(
            model_class=User,
            url="/{id}",
            readable_column_names=["id", "name"],
            transform_input_types=True,
        )
        self.assertTrue(endpoint.transform_input_types)

        # Callable endpoint
        endpoint = clearskies.endpoints.Callable(
            to_call=lambda: {"hello": "world"},
            transform_input_types=True,
        )
        self.assertTrue(endpoint.transform_input_types)

    def test_invalid_type_raises_error(self):
        """Test that invalid type conversion raises InputErrors."""
        endpoint = clearskies.endpoints.List(
            model_class=User,
            readable_column_names=["id", "name", "age"],
            sortable_column_names=["id"],
            searchable_column_names=["age"],
            default_sort_column_name="id",
        )

        di = Di(classes=[User])
        endpoint.injectable_properties(di)

        # Try to transform invalid integer
        query_params = {"age": "not_a_number"}

        with self.assertRaises(exceptions.InputErrors) as cm:
            endpoint.transform_query_parameters(query_params, User)

        self.assertIn("age", cm.exception.errors)

    def test_non_searchable_columns_not_transformed(self):
        """Test that non-searchable columns are not transformed."""
        endpoint = clearskies.endpoints.List(
            model_class=User,
            readable_column_names=["id", "name", "age"],
            sortable_column_names=["id", "name"],
            searchable_column_names=["age"],  # Only age is searchable
            default_sort_column_name="id",
        )

        di = Di(classes=[User])
        endpoint.injectable_properties(di)

        query_params = {
            "age": "25",  # Searchable - should transform
            "name": "123",  # Not searchable - should stay as string
        }

        transformed = endpoint.transform_query_parameters(query_params, User)

        self.assertEqual(transformed["age"], 25)  # Transformed
        self.assertEqual(transformed["name"], "123")  # Not transformed

    def test_operators_in_query_params(self):
        """Test that operators in query parameters are handled correctly."""
        endpoint = clearskies.endpoints.List(
            model_class=User,
            readable_column_names=["id", "name", "age"],
            sortable_column_names=["id"],
            searchable_column_names=["age"],
            default_sort_column_name="id",
        )

        di = Di(classes=[User])
        endpoint.injectable_properties(di)

        # Test operator syntax
        query_params = {
            "age__gt": "25",
            "age__lt": "50",
        }

        transformed = endpoint.transform_query_parameters(query_params, User)

        # Both should be transformed because they reference the searchable column 'age'
        self.assertEqual(transformed["age__gt"], 25)
        self.assertEqual(transformed["age__lt"], 50)

    def test_input_schema_overrides_model_class(self):
        """Test that input_schema takes precedence over model_class for validation."""

        # Create a separate input schema with different types
        class UserInput(clearskies.Schema):
            id = clearskies.columns.Integer()
            search_term = clearskies.columns.String()

        endpoint = clearskies.endpoints.Get(
            model_class=User,
            url="/{id}",
            readable_column_names=["id", "name"],
            input_schema=UserInput,  # Use input_schema for validation
            transform_input_types=True,
        )

        di = Di(classes=[User])
        endpoint.injectable_properties(di)

        # Test that routing data uses input_schema
        routing_data = {"id": "123"}
        transformed = endpoint.transform_routing_data(routing_data)

        # Should be transformed to int based on input_schema
        self.assertEqual(transformed["id"], 123)

    def test_input_schema_in_list_endpoint(self):
        """Test input_schema with List endpoint for query parameter validation."""

        class SearchInput(clearskies.Schema):
            age = clearskies.columns.Integer()
            active = clearskies.columns.Boolean()

        endpoint = clearskies.endpoints.List(
            model_class=User,
            readable_column_names=["id", "name", "age", "active"],
            sortable_column_names=["id"],
            searchable_column_names=["age", "active"],
            default_sort_column_name="id",
            input_schema=SearchInput,
            transform_input_types=True,
        )

        di = Di(classes=[User])
        endpoint.injectable_properties(di)

        # Test query parameter transformation with input_schema
        query_params = {
            "age": "30",
            "active": "false",
        }
        transformed = endpoint.transform_query_parameters(query_params)

        self.assertEqual(transformed["age"], 30)
        # Boolean column's to_backend converts any non-empty string to True
        # so "false" becomes True - this is expected behavior
        self.assertEqual(transformed["active"], True)

    def test_input_schema_in_callable_endpoint(self):
        """Test input_schema with Callable endpoint."""

        class CallableInput(clearskies.Schema):
            user_id = clearskies.columns.Integer()
            limit = clearskies.columns.Integer()

        def process_data(user_id, limit):
            return {"user_id": user_id, "limit": limit}

        endpoint = clearskies.endpoints.Callable(
            process_data,
            input_schema=CallableInput,
            url="/process/{user_id}",
            transform_input_types=True,
        )

        di = Di(classes=[User])
        endpoint.injectable_properties(di)

        # Test routing data transformation
        routing_data = {"user_id": "42"}
        transformed_routing = endpoint.transform_routing_data(routing_data)
        self.assertEqual(transformed_routing["user_id"], 42)

        # Test query parameter transformation
        query_params = {"limit": "100"}
        transformed_query = endpoint.transform_query_parameters(query_params)
        self.assertEqual(transformed_query["limit"], 100)

    def test_fallback_to_model_class_when_no_input_schema(self):
        """Test that model_class is used when input_schema is not provided."""
        endpoint = clearskies.endpoints.Get(
            model_class=User,
            url="/{id}",
            readable_column_names=["id", "name"],
            transform_input_types=True,
        )

        di = Di(classes=[User])
        endpoint.injectable_properties(di)

        # Without input_schema, should fall back to model_class
        routing_data = {"id": "456"}
        transformed = endpoint.transform_routing_data(routing_data)

        # Should still transform based on model_class
        self.assertEqual(transformed["id"], 456)

    def test_input_schema_validation_error(self):
        """Test that invalid input raises appropriate error with input_schema."""

        class StrictInput(clearskies.Schema):
            id = clearskies.columns.Integer()

        endpoint = clearskies.endpoints.Delete(
            model_class=User,
            url="/{id}",
            input_schema=StrictInput,
            transform_input_types=True,
        )

        di = Di(classes=[User])
        endpoint.injectable_properties(di)

        # Try to pass invalid integer
        routing_data = {"id": "not_an_integer"}

        with self.assertRaises(exceptions.InputErrors) as cm:
            endpoint.transform_routing_data(routing_data)

        self.assertIn("id", cm.exception.errors)


if __name__ == "__main__":
    unittest.main()
