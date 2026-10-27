import threading
import unittest

import clearskies
from clearskies.di import Di
from clearskies.input_outputs import InputOutput


class RequestIsolationTest(unittest.TestCase):
    def test_interleaved_requests_see_their_own_input_output(self):
        a_started = threading.Event()
        b_done = threading.Event()
        seen = {}

        def application(di: Di, input_output: InputOutput):
            user = input_output.request_headers.get("x-user")
            if user == "alice":
                a_started.set()
                b_done.wait(5)
            # read again after the other request has replaced the shared Di binding
            seen[user] = (
                di.build("input_output", cache=True).request_headers.get("x-user"),
                di.build_class_from_type_hint("input_output", InputOutput).request_headers.get("x-user"),
            )
            return user

        context = clearskies.contexts.Context(application)

        def request_a():
            context(request_headers={"x-user": "alice"})

        thread = threading.Thread(target=request_a)
        thread.start()
        a_started.wait(5)
        context(request_headers={"x-user": "bob"})
        b_done.set()
        thread.join(5)

        assert seen == {"alice": ("alice", "alice"), "bob": ("bob", "bob")}

    def test_endpoint_groups_do_not_grow_across_requests(self):
        context = clearskies.contexts.Context(
            clearskies.EndpointGroup(
                [
                    clearskies.endpoints.Callable(
                        lambda endpoint_groups: {"count": len(endpoint_groups)},
                        url="count",
                    ),
                ]
            )
        )

        for _ in range(3):
            (status_code, response, _headers) = context(url="count")
            assert status_code == 200
            assert response["data"] == {"count": 1}

    def test_cors_preflight_does_not_change_the_configured_header(self):
        cors = clearskies.security_headers.Cors(origin="*", methods=["PUT"])
        context = clearskies.contexts.Context(
            clearskies.endpoints.Callable(
                lambda: {},
                url="thing",
                request_methods=["GET"],
                security_headers=[cors],
            )
        )

        (status_code, _response, headers) = context(url="thing", request_method="OPTIONS")

        assert status_code == 200
        assert headers.get("access-control-allow-methods") == "GET"
        assert cors.methods == ["PUT"]
