import unittest
from unittest.mock import MagicMock, call

import clearskies
from clearskies.backends.mysql_backend import MysqlBackend
from clearskies.contexts import Context


class MysqlBackendTest(unittest.TestCase):
    """Tests for the MysqlBackend class."""

    def test_backend_uses_mysql_cursor(self):
        """Test that MysqlBackend uses mysql_cursor dependency."""
        # Verify the class has cursor configured to inject by name
        from clearskies.di import inject

        assert hasattr(MysqlBackend, "cursor")
        assert isinstance(MysqlBackend.cursor, inject.ByName)
        assert MysqlBackend.cursor.name == "mysql_cursor"

    def test_backend_supports_n_plus_one(self):
        """Test that MysqlBackend supports N+1 query optimization."""
        backend = MysqlBackend()
        assert backend.supports_n_plus_one is True

    def test_backend_with_model(self):
        """Test that MysqlBackend works with models and performs correct queries."""

        class Product(clearskies.Model):
            id_column_name = "id"
            backend = MysqlBackend(table_prefix="store_")
            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()

            @classmethod
            def destination_name(cls):
                return "products"

        # Mock cursor
        cursor = MagicMock()
        cursor.execute = MagicMock()
        cursor.execute.side_effect = [None, None]
        cursor.__iter__ = lambda self: [{"id": "abc-123", "name": "Widget"}].__iter__()

        uuid = MagicMock()
        uuid.uuid4 = MagicMock(return_value=["abc-123"])

        context = Context(
            clearskies.endpoints.Callable(
                lambda products: products.create({"name": "Widget"}).id,
            ),
            classes=[Product],
            bindings={
                "global_table_prefix": "shop_",
                "mysql_cursor": cursor,
                "uuid": uuid,
            },
        )

        (status_code, response, response_headers) = context()
        assert status_code == 200
        assert response["data"] == "abc-123"

        # Verify correct SQL queries were made (columns are sorted alphabetically)
        cursor.execute.assert_has_calls(
            [
                call("INSERT INTO `shop_store_products` (`name`, `id`) VALUES (%s, %s)", ("Widget", "['abc-123']")),
                call(
                    "SELECT `shop_store_products`.* FROM `shop_store_products` WHERE shop_store_products.id=%s",
                    ("['abc-123']",),
                ),
            ]
        )
