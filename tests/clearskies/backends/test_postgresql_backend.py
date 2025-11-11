import unittest
from unittest.mock import MagicMock, call

import clearskies
from clearskies.backends.postgesql_backend import PostgresqlBackend
from clearskies.contexts import Context


class PostgresqlBackendTest(unittest.TestCase):
    """Tests for the PostgresqlBackend class."""

    def test_backend_uses_postgresql_cursor(self):
        """Test that PostgresqlBackend uses postgresql_cursor dependency."""
        # Verify the class has cursor configured to inject by name
        from clearskies.di import inject

        assert hasattr(PostgresqlBackend, "cursor")
        assert isinstance(PostgresqlBackend.cursor, inject.ByName)
        assert PostgresqlBackend.cursor.name == "postgresql_cursor"

    def test_backend_supports_n_plus_one(self):
        """Test that PostgresqlBackend supports N+1 query optimization."""
        backend = PostgresqlBackend()
        assert backend.supports_n_plus_one is True

    def test_backend_with_model(self):
        """Test that PostgresqlBackend works with models and performs correct queries."""

        class Order(clearskies.Model):
            id_column_name = "id"
            backend = PostgresqlBackend(table_prefix="customer_")
            id = clearskies.columns.Uuid()
            status = clearskies.columns.String()

            @classmethod
            def destination_name(cls):
                return "orders"

        # Mock cursor
        cursor = MagicMock()
        cursor.execute = MagicMock()
        cursor.execute.side_effect = [None, None]
        cursor.__iter__ = lambda self: [{"id": "order-456", "status": "pending"}].__iter__()

        uuid = MagicMock()
        uuid.uuid4 = MagicMock(return_value=["order-456"])

        context = Context(
            clearskies.endpoints.Callable(
                lambda orders: orders.create({"status": "pending"}).id,
            ),
            classes=[Order],
            bindings={
                "global_table_prefix": "ecommerce_",
                "postgresql_cursor": cursor,
                "uuid": uuid,
            },
        )

        (status_code, response, response_headers) = context()
        assert status_code == 200
        assert response["data"] == "order-456"

        # Verify correct SQL queries were made (columns are sorted alphabetically)
        cursor.execute.assert_has_calls(
            [
                call(
                    "INSERT INTO `ecommerce_customer_orders` (`status`, `id`) VALUES (%s, %s)",
                    ("pending", "['order-456']"),
                ),
                call(
                    "SELECT `ecommerce_customer_orders`.* FROM `ecommerce_customer_orders` WHERE ecommerce_customer_orders.id=%s",
                    ("['order-456']",),
                ),
            ]
        )
