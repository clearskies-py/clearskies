import unittest

from clearskies.input_outputs.wsgi import Wsgi


class WsgiTest(unittest.TestCase):
    def test_full_path_puts_script_name_first(self):
        wsgi = Wsgi({"REQUEST_METHOD": "GET", "SCRIPT_NAME": "/api", "PATH_INFO": "/users"}, lambda *args: None)
        assert wsgi.get_full_path() == "/api/users"
