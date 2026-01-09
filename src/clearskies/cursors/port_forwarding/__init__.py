"""
Port forwarding support for database cursors.

This module provides an abstract base class for implementing port forwarding
to remote databases through various protocols (SSM, SSH, etc.).

The base PortForwarder class can be extended to create custom port forwarding
implementations. Concrete implementations (like SSMPortForwarder) typically
live in separate packages (e.g., clearskies-aws).

Usage:
    from clearskies.cursors.port_forwarding import PortForwarder, SSHCertPort, SSHPrivateKey

    class MyPortForwarder(PortForwarder):
        def setup(self, original_host: str, original_port: int) -> tuple[str, int]:
            # Establish tunnel
            return ("localhost", 12345)

        def teardown(self) -> None:
            # Clean up
            pass

    forwarder = MyPortForwarder()
    # Use with a cursor:
    # cursor = clearskies.cursors.Mysql(port_forwarding=forwarder, ...)

"""

from clearskies.cursors.port_forwarding.port_forwarder import PortForwarder
from clearskies.cursors.port_forwarding.ssh_cert import SshCert
from clearskies.cursors.port_forwarding.ssh_private_key import SshPrivateKey

__all__ = ["PortForwarder", "SshCert", "SshPrivateKey"]
