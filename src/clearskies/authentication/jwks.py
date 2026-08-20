from __future__ import annotations

import datetime
import json
from typing import TYPE_CHECKING, Any, Callable

from clearskies import configs, decorators, di
from clearskies.authentication.authentication import Authentication
from clearskies.exceptions import ClientError
from clearskies.security_headers.cors import Cors

if TYPE_CHECKING:
    from clearskies.input_outputs.input_output import InputOutput


class Jwks(Authentication, di.InjectableProperties):
    """
    Validate a JWT against a JWKS (JSON Web Key Set).

    This authentication class fetches a set of public keys from a remote JWKS endpoint and uses them
    to verify the signature of a Bearer token presented in the `Authorization` header.  It is the
    standard way to validate JWTs issued by OAuth 2.0 / OIDC providers such as Auth0, Azure Active
    Directory, or any provider that publishes a JWKS document.

    The minimum configuration is a `jwks_url`.  You will typically also want to set `audience` and
    `issuer` to ensure the token was issued for your application:

    ```python
    import clearskies

    wsgi = clearskies.contexts.WsgiRef(
        clearskies.endpoints.Callable(
            lambda authorization_data: authorization_data,
            authentication=clearskies.authentication.Jwks(
                jwks_url="https://auth.example.com/.well-known/jwks.json",
                audience="https://api.example.com/",
                issuer="https://auth.example.com/",
            ),
        )
    )
    wsgi()
    ```

    Calling the endpoint without a valid token returns a 401:

    ```bash
    $ curl http://localhost:8080 | jq
    {
        "status": "client_error",
        "error": "Not Authenticated",
        "data": [],
        "pagination": {},
        "input_errors": {}
    }
    ```

    With a valid Bearer token the decoded JWT payload is available via the `authorization_data`
    dependency:

    ```bash
    $ curl http://localhost:8080 -H "Authorization: Bearer <token>" | jq
    {
        "status": "success",
        "error": "",
        "data": {
            "sub": "example-user",
            "iss": "https://auth.example.com/",
            "aud": "https://api.example.com/"
        },
        "pagination": {},
        "input_errors": {}
    }
    ```
    """

    """
    The URL from which to fetch the JSON Web Key Set.

    clearskies fetches this URL to retrieve the public keys used to verify incoming JWTs.  The
    response must be a standard JWKS document — a JSON object with a `keys` array.  Key selection
    is performed automatically by matching the `kid` header of the incoming token against the keys
    in the set.

    The key set is cached for `jwks_cache_time` seconds (default one day) to avoid a remote fetch
    on every request.
    """
    jwks_url = configs.String(required=True)

    """
    The audience to accept JWTs for.

    If provided, JWTs will be rejected unless their `aud` claim contains this value.  You should
    always set this to the identifier of your own API to prevent tokens issued for other services
    from being accepted.  If you do not provide an audience then all audiences will be accepted.
    """
    audience = configs.String(default="")

    """
    The expected issuer of the JWTs.

    If provided, JWTs will be rejected unless their `iss` claim exactly matches this value.  Set
    this to the base URL of the authorization server that issues tokens for your application.  If
    you do not provide an issuer then any issuer will be accepted.
    """
    issuer = configs.String(default="")

    """
    The allowed signing algorithms.

    Passed directly to `jwcrypto.jwt.JWT(algs=...)`.  Any token whose `alg` header is not in this
    list is rejected before signature verification.  An empty list disables the restriction; any
    algorithm that is cryptographically compatible with the matched JWKS key is then accepted.
    """
    algorithms = configs.StringList(default=["RS256"])

    """
    The number of seconds for which the JWKS URL contents can be cached.

    Defaults to 86400 (one day).  Set to 0 to disable caching and always fetch fresh keys.
    """
    jwks_cache_time = configs.Integer(default=86400)

    """
    The authorization URL used in the auto-generated API documentation.

    This value is only used when generating OpenAPI documentation and has no effect on
    authentication behaviour at runtime.
    """
    authorization_url = configs.String()

    """
    Additional claim validation applied after the JWT signature is verified.

    Provide a list of claim names to require their presence in the decoded payload.  A 401
    is returned if any listed claim is missing:

    ```python
    import clearskies

    wsgi = clearskies.contexts.WsgiRef(
        clearskies.endpoints.Callable(
            lambda: {"hello": "world"},
            authentication=clearskies.authentication.Jwks(
                jwks_url="https://example.com/.well-known/jwks.json",
                claims=["role", "sub"],
            ),
        )
    )
    wsgi()
    ```

    For custom logic, provide a callable instead.  The clearskies DI system injects `jwt_claims`
    (the decoded payload as a dict) plus any other name resolvable from the DI container, so only
    declare the parameters your function actually needs.

    The callable may return `True` or `None` to accept the token, `False` to reject it with a 401,
    or a list of strings to dynamically specify which claims must be present:

    ```python
    import clearskies

    def no_blocked_users(jwt_claims):
        return "blocked" not in jwt_claims

    wsgi = clearskies.contexts.WsgiRef(
        clearskies.endpoints.Callable(
            lambda: {"hello": "world"},
            authentication=clearskies.authentication.Jwks(
                jwks_url="https://example.com/.well-known/jwks.json",
                claims=no_blocked_users,
            ),
        )
    )
    wsgi()
    ```

    You can also return a dynamic list of required claims based on the payload:

    ```python
    import clearskies

    def require_extra_claims_for_admins(jwt_claims):
        if jwt_claims.get("role") == "admin":
            return ["department", "employee_id"]
        return True

    wsgi = clearskies.contexts.WsgiRef(
        clearskies.endpoints.Callable(
            lambda: {"hello": "world"},
            authentication=clearskies.authentication.Jwks(
                jwks_url="https://example.com/.well-known/jwks.json",
                claims=require_extra_claims_for_admins,
            ),
        )
    )
    wsgi()
    ```
    """
    claims = configs.StringListOrCallable(default=[])

    """
    The name of the security scheme in the auto-generated API documentation.

    Defaults to `jwt`.  Override this if your documentation needs to distinguish between multiple
    JWT-based authentication schemes on the same set of endpoints.
    """
    documentation_security_name = configs.String(default="jwt")

    """
    The environment helper.
    """
    environment = di.inject.Environment()

    """
    The requests object.
    """
    requests = di.inject.Requests()

    """
    The current time.
    """
    now = di.inject.Now()

    """
    The dependency injection container.
    """
    di = di.inject.Di()

    """
    Local cache of the JWKS.
    """
    _jwks = None

    """
    The time when the JWKS was last fetched.
    """
    _jwks_fetched: datetime.datetime

    @decorators.parameters_to_properties
    def __init__(
        self,
        jwks_url: str,
        audience: str = "",
        issuer: str = "",
        algorithms: list[str] = ["RS256"],
        jwks_cache_time: int = 86400,
        authorization_url: str = "",
        claims: list[str] | Callable[..., list[str] | bool | None] | None = None,
        documentation_security_name: str = "jwt",
    ):
        self.finalize_and_validate_configuration()

    def authenticate(self, input_output: InputOutput) -> bool:
        auth_header = input_output.request_headers.get("authorization", None)
        if not auth_header:
            raise ClientError("Missing 'Authorization' header in request")
        if auth_header[:7].lower() != "bearer ":
            raise ClientError("Missing 'Bearer ' prefix in authorization header")
        self.validate_jwt(auth_header[7:])
        input_output.authorization_data = self.jwt_claims
        return True

    def validate_jwt(self, raw_jwt: str) -> bool:
        try:
            from jwcrypto import jwk, jwt
            from jwcrypto.common import JWException
        except ImportError:
            raise ValueError(
                "The JWKS authentication method requires the jwcrypto library to be installed.  This is an optional dependency of clearskies, so to include it do a `pip install 'clear-skies[jwcrypto]'`"
            )

        # Fail fast on malformed token before touching the JWKS endpoint.
        client_jwt = jwt.JWT(algs=self.algorithms or None)
        try:
            client_jwt.deserialize(raw_jwt)
        except Exception as e:
            raise ClientError(str(e))

        # kid-based key selection and cryptographic verification are handled by jwcrypto.
        # Passing the full JWKSet lets it pick the matching key by kid automatically.
        keys = jwk.JWKSet()
        keys.import_keyset(json.dumps(self._get_jwks()))

        try:
            client_jwt.validate(keys)
            self.jwt_claims = json.loads(client_jwt.claims)
        except JWException as e:
            raise ClientError(str(e))

        if self.issuer and self.jwt_claims.get("iss") != self.issuer:
            raise ClientError("Issuer does not match")

        if self.audience:
            jwt_audience = self.jwt_claims.get("aud")
            if not jwt_audience:
                raise ClientError("Audience required, but missing in JWT")
            if isinstance(jwt_audience, str):
                jwt_audiences = [jwt_audience]
            elif isinstance(jwt_audience, list):
                jwt_audiences = jwt_audience
            else:
                raise ClientError("Audience claim has invalid format")
            if self.audience not in jwt_audiences:
                raise ClientError("Audience does not match")

        self.validate_claims()

        return True

    def validate_claims(self) -> None:
        claims = self.claims
        if not claims:
            return

        if callable(claims):
            result = self.di.call_function(
                claims,
                jwt_claims=self.jwt_claims,
            )
            if result is None or result is True:
                return
            if result is False:
                raise ClientError("JWT claims failed custom validation")
            if not isinstance(result, list):
                raise TypeError("claims callable must return a list, bool, or None")
            claims = result

        if not claims:
            return

        for claim in claims:
            if claim not in self.jwt_claims:
                raise ClientError(f"Required claim missing: {claim}")

    def _get_jwks(self):
        if self._jwks is None or ((self.now - self._jwks_fetched).total_seconds() > self.jwks_cache_time):
            self._jwks = self.requests.get(self.jwks_url).json()
            self._jwks_fetched = self.now

        return self._jwks

    def documentation_security_scheme(self) -> dict[str, Any]:
        return {
            "type": "oauth2",
            "description": "JWT based authentication",
            "flows": {"implicit": {"authorizationUrl": self.authorization_url, "scopes": {}}},
        }

    def documentation_security_scheme_name(self) -> str:
        return self.documentation_security_name

    def set_headers_for_cors(self, cors: Cors):
        cors.add_header("Authorization")
