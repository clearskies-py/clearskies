import clearskies.configs
from clearskies import decorators
from clearskies.cursors.port_forwarding import port_forwarder


class SshPrivateKey(port_forwarder.PortForwarder):
    """
    Port forwarder using SSH with a private key for authentication.

    This class sets up a local port forwarding tunnel to a remote host using SSH and a private key file.

    ### Configuration

    - `ssh_user` (str): SSH username (default: "ec2-user")
    - `private_key_path` (str): Path to the SSH private key file (required)
    - `local_host` (str): Local host to bind (default: "127.0.0.1")
    - `local_port` (int): Local port to bind (default: 0, auto-select)

    ### Example

    ```python
    forwarder = SSHPrivateKey(ssh_user="ec2-user", private_key_path="/path/to/id_rsa")
    local_host, local_port = forwarder.setup("db.internal", 3306)
    # Use local_host and local_port for DB connection
    forwarder.teardown()
    ```
    """

    """
    SSH username for authentication (default: "root").
    """
    ssh_user = clearskies.configs.String(default="root")

    """
    Path to the SSH private key file used for authentication.
    """
    private_key_path = clearskies.configs.String()

    """
    Local host to bind for the forwarding tunnel (default: "127.0.0.1").
    """
    local_host = clearskies.configs.String(default="127.0.0.1")

    """
    Local port to bind for the forwarding tunnel (default: 0, auto-selects a free port).
    """
    local_port = clearskies.configs.Integer(default=0)

    @decorators.parameters_to_properties
    def __init__(
        self,
        ssh_user: str | None = "root",
        private_key_path: str | None = None,
        local_host: str | None = "127.0.0.1",
        local_port: int | None = 0,
    ):
        self._proc = None
        self.finalize_and_validate_configuration()

    def setup(self, original_host: str, original_port: int) -> tuple[str, int]:
        """
        Establish the port forwarding tunnel and return the local endpoint.

        This method is called by the `Cursor` before it connects to the database. Starts the SSH tunnel
        and returns the host and port that the database driver should connect to on the local machine.

        Args:
            original_host: The target database hostname that the cursor is configured with.
            original_port: The target database port that the cursor is configured with.

        Returns:
            A tuple containing the local host and local port to connect to (e.g., ("localhost", 12345)).

        Raises:
            Exception: If the tunnel cannot be established, this method should raise an exception.
        """
        # Pick a free local port if not specified
        if self.local_port == 0:
            self.local_port = self.pick_free_port(self.local_host)

        # Check if the tunnel is already open
        if self.is_port_open(self.local_host, self.local_port):
            return self.local_host, self.local_port

        ssh_cmd = [
            "ssh",
            "-i",
            self.private_key_path,
            "-N",
            "-L",
            f"{self.local_host}:{self.local_port}:{original_host}:{original_port}",
            f"{self.ssh_user}@{original_host}",
        ]
        self._proc = self.subprocess.Popen(ssh_cmd, stdout=self.subprocess.PIPE, stderr=self.subprocess.PIPE)

        # Wait for the local port to be open (max 10s)
        import time

        start = time.time()
        while True:
            try:
                test_sock = self.socket.socket(self.socket.AF_INET, self.socket.SOCK_STREAM)
                test_sock.settimeout(0.2)
                test_sock.connect((self.local_host, self.local_port))
                test_sock.close()
                break
            except Exception:
                if self._proc is not None and self._proc.poll() is not None:
                    raise RuntimeError("SSH process exited unexpectedly")
                if time.time() - start > 10:
                    raise TimeoutError(f"Timeout waiting for port {self.local_port} to open")
                time.sleep(0.1)

        return self.local_host, self.local_port

    def teardown(self):
        if self._proc:
            self._proc.terminate()
            self._proc.wait()
            self._proc = None
