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


class Wsgi(Context):
    """
    Connect your application to a WSGI server.

    The Wsgi context is used to connect a clearskies application to a WSGI server of your choice.  As with all
    contexts, you first create it and pass in the application (a callable, endpoint, or endpoint group) as well
    as any dependency injection parameters.  Then, you call the context from inside of the function invoked by
    your WSGI server, passing along the `environment` and `start_response` variables, and returning the response
    from the context.  Here's a simple example:

    ```
    import clearskies

    def hello_world():
        return "Hello World!"

    wsgi = clearskies.contexts.Wsgi(hello_world)

    def application(environment, start_response):
        return wsgi(environment, start_response)
    ```

    You would then launch your WSGI server.  For instance, here's how to launch it with uwsgi, which automatically
    looks for a function called `application` and treats that as the WSGI starting point:

    ```
    uwsgi --http :9090 --wsgi-file test.py
    ```

    You could then:

    ```
    curl 'http://localhost:9090'
    ```

    And see the response from this "hello world" app.  Note than in the above example I create the context outside
    of the application function.  Of course, you can do the opposite:

    ```
    import clearskies

    def hello_world():
        return "Hello World!"

    def application(environment, start_response):
        wsgi = clearskies.contexts.Wsgi(hello_world)
        return wsgi(environment, start_response)
    ```

    The difference is that most wsgi servers will cache any objects created outside of the handler function (e.g. `application`
    in this case).  When you first create the context clearskies will configure and validate any endpoints attached.
    Also, it will create an instance of the dependency injection container and cache it.  If the context object is created
    outside of the handler, and the server caches objects in this csae, then this validation will only happen once and
    the DI cache will store objects in between HTTP calls.  If you create your context inside the handler function, then
    you'll end up with an empty cache everytime and you'll have slower responses because of clearskies checking the
    application configuration everytime.  Note that the DI system for clearskies grants you full cache control, so
    by and large it's normal and expected that you'll persist the cache between requests by creating the context outside
    of any handler functions.

    """

    def __call__(self, env, start_response):  # type: ignore
        return self.execute_application(WsgiInputOutput(env, start_response))
