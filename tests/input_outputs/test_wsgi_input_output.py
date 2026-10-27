import unittest

from clearskies.input_outputs.wsgi import Wsgi


class WsgiTest(unittest.TestCase):
    def test_full_path_puts_script_name_first(self):
        wsgi = Wsgi({"REQUEST_METHOD": "GET", "SCRIPT_NAME": "/api", "PATH_INFO": "/users"}, lambda *args: None)
        assert wsgi.get_full_path() == "/api/users"

    def test_accepts_put_query_and_head(self):
        for method in ["PUT", "QUERY", "HEAD"]:
            assert Wsgi({"REQUEST_METHOD": method}, lambda *args: None).request_method == method
