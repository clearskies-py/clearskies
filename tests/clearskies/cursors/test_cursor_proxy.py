"""Tests for the cursor proxy implementation."""

import sqlite3

import pytest

from clearskies.cursors.base_cursor import CursorProxy


class TestCursorProxy:
    """Test the CursorProxy class."""

    def test_proxy_iteration(self):
        """Test that the proxy can be iterated over."""
        # Create a real SQLite cursor with test data
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'Alice')")
        conn.execute("INSERT INTO test VALUES (2, 'Bob')")
        conn.commit()

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM test")

        # Create a proxy with a passthrough format function
        def passthrough_format(sql, params):
            return sql, params

        proxy = CursorProxy(cursor, passthrough_format)

        # Test iteration
        results = [row for row in proxy]
        assert len(results) == 2
        assert results[0] == (1, "Alice")
        assert results[1] == (2, "Bob")

        conn.close()

    def test_proxy_execute_with_formatting(self):
        """Test that the proxy formats SQL parameters correctly."""
        # Create a real SQLite cursor
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
        conn.commit()

        cursor = conn.cursor()

        # Create a format function that converts %s to ?
        def qmark_format(sql, params):
            formatted_sql = sql.replace("%s", "?")
            return formatted_sql, params

        proxy = CursorProxy(cursor, qmark_format)

        # Execute with %s style parameters
        proxy.execute("INSERT INTO test VALUES (%s, %s)", (1, "Alice"))
        conn.commit()

        # Verify the data was inserted
        cursor.execute("SELECT * FROM test")
        result = cursor.fetchone()
        assert result == (1, "Alice")

        conn.close()

    def test_proxy_attribute_delegation(self):
        """Test that cursor attributes are delegated correctly."""
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'Alice')")
        conn.commit()

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM test")

        def passthrough_format(sql, params):
            return sql, params

        proxy = CursorProxy(cursor, passthrough_format)

        # Test description attribute
        assert proxy.description is not None
        assert len(proxy.description) == 2  # Two columns

        # Test fetchone method
        row = proxy.fetchone()
        assert row == (1, "Alice")

        conn.close()

    def test_proxy_fetchall(self):
        """Test that fetchall works correctly."""
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'Alice')")
        conn.execute("INSERT INTO test VALUES (2, 'Bob')")
        conn.commit()

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM test")

        def passthrough_format(sql, params):
            return sql, params

        proxy = CursorProxy(cursor, passthrough_format)

        # Test fetchall
        results = proxy.fetchall()
        assert len(results) == 2
        assert results[0] == (1, "Alice")
        assert results[1] == (2, "Bob")

        conn.close()

    def test_proxy_rowcount(self):
        """Test that rowcount is accessible."""
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
        conn.commit()

        cursor = conn.cursor()

        def passthrough_format(sql, params):
            return sql, params

        proxy = CursorProxy(cursor, passthrough_format)

        proxy.execute("INSERT INTO test VALUES (?, ?)", (1, "Alice"))
        conn.commit()

        # Test rowcount
        assert proxy.rowcount == 1

        conn.close()

    def test_proxy_execute_without_params(self):
        """Test execute without parameters."""
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()

        def passthrough_format(sql, params):
            return sql, params

        proxy = CursorProxy(cursor, passthrough_format)

        # Execute without parameters
        proxy.execute("CREATE TABLE test (id INTEGER, name TEXT)")
        conn.commit()

        # Verify table was created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test'")
        result = cursor.fetchone()
        assert result is not None
        assert result[0] == "test"

        conn.close()

    def test_proxy_close(self):
        """Test that close is delegated correctly."""
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()

        def passthrough_format(sql, params):
            return sql, params

        proxy = CursorProxy(cursor, passthrough_format)

        # Close the proxy
        proxy.close()

        # The cursor should be closed
        with pytest.raises(sqlite3.ProgrammingError):
            cursor.execute("SELECT 1")

        conn.close()

    def test_sqlite_cursor_direct_usage(self):
        """Test that SqliteCursor can be used directly as a cursor."""
        from clearskies.cursors.sqlite_cursor import SqliteCursor

        # Create cursor config
        cursor_config = SqliteCursor(database_name=":memory:", autocommit=True)

        # Create table using direct execute
        cursor_config.execute("CREATE TABLE test (id INTEGER, name TEXT)", None)

        # Insert data using direct execute
        cursor_config.execute("INSERT INTO test VALUES (?, ?)", (1, "Alice"))
        cursor_config.execute("INSERT INTO test VALUES (?, ?)", (2, "Bob"))

        # Query and iterate directly
        cursor_config.execute("SELECT * FROM test", None)
        results = [row for row in cursor_config]

        assert len(results) == 2
        assert results[0]["id"] == 1
        assert results[0]["name"] == "Alice"
        assert results[1]["id"] == 2
        assert results[1]["name"] == "Bob"

        # Test fetchall via delegation
        cursor_config.execute("SELECT * FROM test WHERE id=?", (1,))
        result = cursor_config.fetchone()
        assert result["id"] == 1
        assert result["name"] == "Alice"
