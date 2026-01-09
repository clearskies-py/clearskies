from abc import ABC, abstractmethod

from clearskies import configurable, loggable
from clearskies.di import inject


class PortForwarder(ABC, configurable.Configurable, loggable.Loggable):
    """
    Abstract base class for port forwarding implementations.

    Port forwarders are responsible for establishing tunnels to remote databases through various protocols
    (e.g., AWS SSM, SSH). This allows `Cursor` objects to connect to databases that are not directly
    accessible from the local machine.

    To create a custom port forwarder, you must subclass `PortForwarder` and implement the `setup`
    and `teardown` methods.

    ### Example
    Here is a conceptual example of a custom port forwarder:

    ```python
    from clearskies.cursors.port_forwarding import PortForwarder


    class MyCustomForwarder(PortForwarder):
        def setup(self, original_host: str, original_port: int) -> tuple[str, int]:
            print(f"Setting up tunnel to {original_host}:{original_port}...")
            # In a real implementation, you would start a subprocess or thread
            # to establish the tunnel here.
            local_port = 12345
            print(f"Tunnel established on localhost:{local_port}")
            return ("localhost", local_port)

        def teardown(self) -> None:
            print("Tearing down tunnel...")
            # Clean up any resources (e.g., terminate subprocess).


    # This forwarder can then be passed to a cursor configuration:
    forwarder = MyCustomForwarder()
    # mysql_cursor = clearskies.cursors.Mysql(
    #     hostname="private-db.internal",
    #     port=3306,
    #     port_forwarding=forwarder,
    # )
    ```
    """

    socket = inject.Socket()
    subprocess = inject.Subprocess()

    def is_port_open(self, host: str, port: int, timeout: float = 0.2) -> bool:
        """
        Check if a TCP port is open on the given host.

        Args:
            host: Hostname or IP address.
            port: Port number.
            timeout: Timeout in seconds for the connection attempt.

        Returns:
            True if the port is open, False otherwise.
        """
        try:
            test_sock = self.socket.socket(self.socket.AF_INET, self.socket.SOCK_STREAM)
            test_sock.settimeout(timeout)
            test_sock.connect((host, port))
            test_sock.close()
            return True
        except Exception:
            return False

    def pick_free_port(self, host: str = "127.0.0.1") -> int:
        """
        Pick a free TCP port on the given host.

        Args:
            host: Hostname or IP address to bind to (default: "127.0.0.1").

        Returns:
            An available port number.
        """
        sock = self.socket.socket(self.socket.AF_INET, self.socket.SOCK_STREAM)
        sock.bind((host, 0))
        port = sock.getsockname()[1]
        sock.close()
        return port

    _descriptor_config_map = None

    @abstractmethod
    def setup(self, original_host: str, original_port: int) -> tuple[str, int]:
        """
        Establish the port forwarding tunnel and return the local endpoint.

        This method is called by the `Cursor` before it connects to the database. Your
        implementation should start the tunnel and return the host and port that the
        database driver should connect to on the local machine.

        Args:
            original_host: The target database hostname that the cursor is configured with.
            original_port: The target database port that the cursor is configured with.

        Returns:
            A tuple containing the local host and local port to connect to (e.g., `("localhost", 12345)`).

        Raises:
            Exception: If the tunnel cannot be established, this method should raise an exception.
        """
        pass

    @abstractmethod
    def teardown(self) -> None:
        """
        Clean up all resources associated with the port forwarding tunnel.

        This method is called when the `Cursor`'s `close()` method is invoked. It should
        terminate any running subprocesses, close network connections, and release any
        other resources that were allocated in `setup()`.

        Implementations should be idempotent, meaning it should be safe to call this
        method multiple times.
        """
        pass

    def __enter__(self):
        """
        Provide context manager support for the forwarder.

        This allows a forwarder to be used in a `with` statement, although it is not
        strictly necessary as the `Cursor` will manage the `setup` and `teardown`
        lifecycle automatically. Using it as a context manager can be useful for
        ensuring cleanup if the cursor is not explicitly closed.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure `teardown` is called when exiting a `with` block."""
        self.teardown()
        return False
