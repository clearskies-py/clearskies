import unittest
from unittest.mock import MagicMock

from clearskies import configs
from clearskies.cursors.cursor import Cursor
from clearskies.cursors.port_forwarding import PortForwarder
from clearskies.di import Di


class MockPortForwarder(PortForwarder):
    def __init__(self, local_host="localhost", local_port=12345):
        super().__init__()
        self.local_host = local_host
        self.local_port = local_port
        self.setup_called = False
        self.teardown_called = False
        self.setup_args = None

    def setup(self, original_host: str, original_port: int) -> tuple[str, int]:
        self.setup_called = True
        self.setup_args = (original_host, original_port)
        return (self.local_host, self.local_port)

    def teardown(self) -> None:
        self.teardown_called = True


class CursorTest(unittest.TestCase):
    def setUp(self):
        self.di = Di()
        self.factory_mock = MagicMock()
        self.connection_mock = MagicMock()
        self.cursor_mock = MagicMock()
        self.factory_mock.connect.return_value = self.connection_mock
        self.connection_mock.cursor.return_value = self.cursor_mock

    def test_port_forwarding_lifecycle(self):
        class TestCursor(Cursor):
            hostname = configs.String(default="original-host")
            port = configs.Integer(default=3306)

            @property
            def factory(self):
                return self._factory

            def build_connection_kwargs(self):
                return {"host": self.hostname, "port": self.port, **super().build_connection_kwargs()}

        port_forwarder = MockPortForwarder()
        cursor = TestCursor()
        cursor.hostname = "remote-db"
        cursor.port = 5432
        cursor.port_forwarding = port_forwarder
        cursor.finalize_and_validate_configuration()
        cursor._factory = self.factory_mock

        # Trigger connection
        _ = cursor.cursor

        # Verify setup was called
        self.assertTrue(port_forwarder.setup_called)
        self.assertEqual(port_forwarder.setup_args, ("remote-db", 5432))

        # Verify connection was made with forwarded details
        self.factory_mock.connect.assert_called_with(
            host="localhost", port=12345, database="example", autocommit=True, connect_timeout=2
        )

        # Verify teardown on close
        cursor.close()
        self.assertTrue(port_forwarder.teardown_called)

    def test_invalid_port_forwarder(self):
        class TestCursor(Cursor):
            hostname = configs.String(default="original-host")
            port = configs.Integer(default=3306)

            @property
            def factory(self):
                return self._factory

            def build_connection_kwargs(self):
                return {"host": self.hostname, "port": self.port, **super().build_connection_kwargs()}

        cursor = TestCursor()
        cursor.port_forwarding = "not-a-forwarder"
        cursor.finalize_and_validate_configuration()
        with self.assertRaises(TypeError):
            _ = cursor.cursor

    def test_no_port_forwarding(self):
        class TestCursor(Cursor):
            hostname = configs.String(default="original-host")
            port = configs.Integer(default=3306)

            @property
            def factory(self):
                return self._factory

            def build_connection_kwargs(self):
                return {"host": self.hostname, "port": self.port, **super().build_connection_kwargs()}

        cursor = TestCursor()
        cursor.hostname = "remote-db"
        cursor.port = 5432
        cursor._factory = self.factory_mock
        cursor.finalize_and_validate_configuration()

        _ = cursor.cursor

        self.factory_mock.connect.assert_called_with(
            host="remote-db", port=5432, database="example", autocommit=True, connect_timeout=2
        )
