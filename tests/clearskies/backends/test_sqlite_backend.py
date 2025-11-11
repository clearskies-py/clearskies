import unittest

import clearskies
from clearskies.backends.sqlite_backend import SqliteBackend
from clearskies.contexts import Context


class SqliteBackendTest(unittest.TestCase):
    """Tests for the SqliteBackend class."""

    def test_backend_uses_sqlite_cursor(self):
        """Test that SqliteBackend uses sqlite_cursor dependency."""
        # Verify the class has cursor configured to inject by name
        from clearskies.di import inject

        assert hasattr(SqliteBackend, "cursor")
        assert isinstance(SqliteBackend.cursor, inject.ByName)
        assert SqliteBackend.cursor.name == "sqlite_cursor"

    def test_backend_supports_n_plus_one(self):
        """Test that SqliteBackend supports N+1 query optimization."""
        backend = SqliteBackend()
        assert backend.supports_n_plus_one is True

    def test_backend_with_model_and_real_database(self):
        """Test that SqliteBackend works with models using actual in-memory database."""

        class Task(clearskies.Model):
            id_column_name = "id"
            backend = SqliteBackend(table_prefix="todo_")
            id = clearskies.columns.String()
            title = clearskies.columns.String()

            @classmethod
            def destination_name(cls):
                return "tasks"

        # Use real SQLite in-memory database
        cursor = clearskies.cursors.SqliteCursor(database_name=":memory:")

        # Create the table
        cursor.execute("CREATE TABLE app_todo_tasks (id TEXT PRIMARY KEY, title TEXT)", None)

        context = Context(
            clearskies.endpoints.Callable(
                lambda tasks: tasks.create({"id": "task-123", "title": "Do something"}).id,
            ),
            classes=[Task],
            bindings={
                "global_table_prefix": "app_",
                "sqlite_cursor": cursor,
            },
        )

        (status_code, response, response_headers) = context()
        assert status_code == 200
        assert response["data"] == "task-123"

        # Verify the record was actually saved to the database
        cursor.execute("SELECT * FROM app_todo_tasks WHERE id=?", ("task-123",))
        results = list(cursor)
        assert len(results) == 1
        assert results[0]["id"] == "task-123"
        assert results[0]["title"] == "Do something"

    def test_backend_with_real_memory_database(self):
        """Test basic cursor operations with actual in-memory database."""
        # Create a cursor directly with :memory: database
        cursor = clearskies.cursors.SqliteCursor(database_name=":memory:")

        # Test we can actually use the cursor
        cursor.execute("CREATE TABLE test (id INTEGER, name TEXT)", None)
        cursor.execute("INSERT INTO test VALUES (1, 'Alice')", None)
        cursor.execute("SELECT * FROM test", None)
        results = list(cursor)

        assert len(results) == 1
        assert results[0]["id"] == 1
        assert results[0]["name"] == "Alice"
