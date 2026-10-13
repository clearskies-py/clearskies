import clearskies
from clearskies.contexts import Context
from tests.test_base import TestBase


class RedirectTest(TestBase):
    def test_exception_str_is_location(self):
        for exception_class in [clearskies.exceptions.MovedPermanently, clearskies.exceptions.MovedTemporarily]:
            exception = exception_class("https://example.com/new")
            assert str(exception) == "https://example.com/new"
            assert exception.location == "https://example.com/new"

    def test_endpoint(self):
        for exception_class, expected_status in [
            (clearskies.exceptions.MovedPermanently, 301),
            (clearskies.exceptions.MovedTemporarily, 307),
        ]:

            def redirect(exception_class=exception_class):
                raise exception_class("https://example.com/new")

            context = Context(clearskies.endpoints.Callable(redirect))
            status_code, response, response_headers = context()
            assert status_code == expected_status
            assert response_headers["location"] == "https://example.com/new"

    def test_endpoint_group(self):
        for exception_class, expected_status in [
            (clearskies.exceptions.MovedPermanently, 301),
            (clearskies.exceptions.MovedTemporarily, 307),
        ]:

            class RedirectingAuthentication(clearskies.authentication.Authentication):
                def authenticate(self, input_output, exception_class=exception_class):
                    raise exception_class("https://example.com/login")

            context = Context(
                clearskies.EndpointGroup(
                    [clearskies.endpoints.Callable(lambda: {"hello": "world"})],
                    authentication=RedirectingAuthentication(),
                )
            )
            status_code, response, response_headers = context()
            assert status_code == expected_status
            assert response_headers["location"] == "https://example.com/login"

    def test_bare_callable(self):
        for exception_class, expected_status in [
            (clearskies.exceptions.MovedPermanently, 301),
            (clearskies.exceptions.MovedTemporarily, 307),
        ]:

            def redirect(exception_class=exception_class):
                raise exception_class("https://example.com/new")

            context = Context(redirect)
            status_code, response, response_headers = context()
            assert status_code == expected_status
            assert response == "https://example.com/new"
            assert response_headers["location"] == "https://example.com/new"
