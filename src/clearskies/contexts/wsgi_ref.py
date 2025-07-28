import datetime
from types import ModuleType
from typing import Any, Callable
from wsgiref.simple_server import make_server
from wsgiref.util import setup_testing_defaults

import clearskies.endpoint
import clearskies.endpoint_group
from clearskies.contexts.context import Context
from clearskies.di import AdditionalConfig
from clearskies.input_outputs import Wsgi as WsgiInputOutput


class WsgiRef(Context):
    """
    Use a built in WSGI server (for development purposes only).

    This context will launch a built-in HTTP server for you, so you can run applications locally
    without having to install extra dependencies.  Note that this server is not intended for production
    usage, so this is best used for simple tests/demonstration purposes.  Unlike the WSGI context, where
    you define the application handler and invoke the context from inside of it (passing along the
    environment and start_response variables), in this case you simply directly invoke the context to
    launch the server.  The default port is 8080:

    ```
    #!/usr/bin/env python
    import clearskies

    def hello_world(name):
        return f"Hello {name}!"

    wsgi = clearskies.contexts.WsgiRef(
        clearskies.endpoints.Callable(
            hello_world,
            url="/hello/:name",
        )
    )
    wsgi()
    ```

    And to invoke it:

    ```
    curl 'http://localhost:8080/hello/Friend'
    ```
    """

    port: int = 8080

    def __init__(
        self,
        application: Callable | clearskies.endpoint.Endpoint | clearskies.endpoint_group.EndpointGroup,
        port: int = 8080,
        classes: type | list[type] = [],
        modules: ModuleType | list[ModuleType] = [],
        bindings: dict[str, Any] = {},
        additional_configs: AdditionalConfig | list[AdditionalConfig] = [],
        class_overrides: dict[type, type] = {},
        overrides: dict[str, type] = {},
        now: datetime.datetime | None = None,
        utcnow: datetime.datetime | None = None,
    ):
        super().__init__(
            application,
            classes=classes,
            modules=modules,
            bindings=bindings,
            additional_configs=additional_configs,
            class_overrides=class_overrides,
            overrides=overrides,
            now=now,
            utcnow=utcnow,
        )
        self.port = port

    def __call__(self):  # type: ignore
        with make_server("", self.port, self.handler) as httpd:
            print(f"Starting WSGI server on port {self.port}.  This is NOT intended for production usage.")
            httpd.serve_forever()

    def handler(self, environment, start_response):
        return self.execute_application(WsgiInputOutput(environment, start_response))
