from clearskies.configurable import Configurable


class SecurityHeader(Configurable):
    """
    Attach all the various security headers to endpoints.

    The security header classes can be attached directly to both endpoints and endpoint groups and
    are used to set all the various security headers.
    """

    is_cors = False

    def set_headers_for_input_output(self, input_output):
        raise NotImplementedError()
