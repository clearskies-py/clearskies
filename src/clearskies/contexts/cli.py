from clearskies.contexts.context import Context
from clearskies.input_outputs import Cli as CliInputOutput


class Cli(Context):
    """
    Run an application via a CLI command

    This context converts a clearskies application into a CLI command.  Here's a simple example:

    ```
    #!/usr/bin/env python
    import clearskies

    def my_function():
        return "Hello World!"

    cli = clearskies.contexts.Cli(my_function)
    cli()
    ```

    Which you can then run as expected:

    ```
    $ ./example.py
    Hello World!
    ```

    Routing is still supported, with routes and route parameters becoming CLI args:

    ```
    #!/usr/bin/env python
    import clearskies

    def my_function(name):
        return f"Hello {name}!"

    cli = clearskies.contexts.Cli(
        clearskies.endpoints.Callable(
            my_function,
            url="/hello/:name",
            return_standard_response=False,
        )
    )
    cli()
    ```

    With a url of `/hello/:name` you would invoke like so:

    ```
    ./example.py hello Bob
    Hello Bob!
    ```

    If the endpoint expects a request method you can provide it by setting the `-X` or `--request_method=`
    kwargs.  So for tihs example:

    ```
    #!/usr/bin/env python
    import clearskies

    def my_function(name):
        return f"Hello {name}!"

    cli = clearskies.contexts.Cli(
        clearskies.endpoints.Callable(
            my_function,
            url="/hello/:name",
            request_methods=["POST"],
        )
    )
    cli()
    ```

    And then calling it successfully:

    ```
    ./example.py hello Bob --request_method=POST

    ./example.py hello Bob -X POST
    ```

    You can pass data as a json string with the -d flag or set individual named arguments.  The following
    example just reflects the request data back to the client:

    ```
    #!/usr/bin/env python
    import clearskies

    def my_function(request_data):
        return request_data

    cli = clearskies.contexts.Cli(
        clearskies.endpoints.Callable(
            my_function,
        )
    )
    cli()
    ```

    And these three calls are identical:

    ```
    ./example.py -d '{"hello": "world"}'

    echo '{"hello": "world"}' | ./test.py

    ./test.py --hello=world
    ```

    Although note that the first two are going to be preferred over the third, simply because with the
    third there's simply no way to specify the type of a variable.  As a result, you may run into issues
    with strict type checking on endpoints.
    """

    def __call__(self):  # type: ignore
        return self.execute_application(CliInputOutput())
