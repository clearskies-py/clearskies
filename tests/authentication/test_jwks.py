import base64
import datetime
import json
import types
import unittest
from types import SimpleNamespace
from typing import Any, Callable, cast
from unittest.mock import MagicMock, patch

import clearskies
from clearskies.di.di import Di
from clearskies.exceptions import ClientError


class FakeJWException(Exception):
    pass


class FakeJWKSet:
    def import_keyset(self, raw_json: str) -> None:
        self.keyset = json.loads(raw_json)


class FakeJWT:
    """
    Minimal stand-in for jwcrypto.jwt.JWT.

    Mirrors the real class closely enough for unit tests:
    - accepts ``algs`` in the constructor (as the real JWT does)
    - ``deserialize`` parses the header from the raw token and stores it as a
      JSON string on ``self.header``, exactly as jwcrypto does
    - ``validate`` always succeeds so tests can focus on our own logic
    """

    def __init__(self, algs: list[str] | None = None) -> None:
        self.algs = algs
        self.header: str = "{}"
        self.claims_data: dict[str, Any] = {
            "iss": "https://issuer.example.com",
            "aud": ["https://audience.example.com"],
            "scope": "read",
        }

    def deserialize(self, raw_jwt: str) -> None:
        parts = raw_jwt.split(".")
        if len(parts) == 3:
            encoded = parts[0] + "=" * (-len(parts[0]) % 4)
            header_dict = json.loads(base64.urlsafe_b64decode(encoded))
            self.header = json.dumps(header_dict)
        else:
            self.header = "{}"
        self.claims = json.dumps(self.claims_data)

    def validate(self, _keys: FakeJWKSet) -> None:
        return None


def _build_jwt(header: dict[str, str], payload: dict[str, str] | None = None) -> str:
    payload = payload or {"sub": "example-user"}
    encoded_header = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    encoded_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"{encoded_header}.{encoded_payload}.signature"


def _mock_jwcrypto_modules(claims_data: dict[str, Any] | None = None) -> dict[str, types.ModuleType]:
    """Return mocked jwcrypto modules.  Pass ``claims_data`` to override the decoded JWT payload."""
    effective_claims = (
        claims_data
        if claims_data is not None
        else {
            "iss": "https://issuer.example.com",
            "aud": ["https://audience.example.com"],
            "scope": "read",
        }
    )

    class _JWT(FakeJWT):
        def __init__(self, algs: list[str] | None = None) -> None:
            super().__init__(algs)
            self.claims_data = dict(effective_claims)

    jwk_module = types.ModuleType("jwcrypto.jwk")
    setattr(jwk_module, "JWKSet", FakeJWKSet)

    jwt_module = types.ModuleType("jwcrypto.jwt")
    setattr(jwt_module, "JWT", _JWT)

    common_module = types.ModuleType("jwcrypto.common")
    setattr(common_module, "JWException", FakeJWException)

    jwcrypto_module = types.ModuleType("jwcrypto")
    setattr(jwcrypto_module, "jwk", jwk_module)
    setattr(jwcrypto_module, "jwt", jwt_module)

    return {
        "jwcrypto": jwcrypto_module,
        "jwcrypto.jwk": jwk_module,
        "jwcrypto.jwt": jwt_module,
        "jwcrypto.common": common_module,
    }


_DEFAULT_JWKS = {"keys": [{"kid": "key-1", "alg": "RS256", "kty": "RSA", "n": "abc", "e": "AQAB"}]}
_DEFAULT_RAW_JWT = _build_jwt({"alg": "RS256", "kid": "key-1"})


class TestJwks(unittest.TestCase):
    def _authentication(
        self,
        claims: list[str] | Callable[..., Any] | None = None,
        algorithms: list[str] = ["RS256"],
        issuer: str = "https://issuer.example.com",
        audience: str = "https://audience.example.com",
    ) -> clearskies.authentication.Jwks:
        authentication = clearskies.authentication.Jwks(
            jwks_url="https://example.com/.well-known/jwks.json",
            issuer=issuer,
            audience=audience,
            claims=claims,
            algorithms=algorithms,
        )
        authentication.injectable_properties(Di())
        return authentication

    # --- authenticate ---

    def test_authenticate_rejects_missing_authorization_header(self):
        authentication = self._authentication()
        io = SimpleNamespace(request_headers={})
        with self.assertRaisesRegex(ClientError, "Missing 'Authorization' header in request"):
            authentication.authenticate(cast(Any, io))

    def test_authenticate_rejects_wrong_header_prefix(self):
        authentication = self._authentication()
        io = SimpleNamespace(request_headers={"authorization": "Token abc123"})
        with self.assertRaisesRegex(ClientError, "Missing 'Bearer ' prefix in authorization header"):
            authentication.authenticate(cast(Any, io))

    def test_authenticate_sets_authorization_data_on_success(self):
        authentication = self._authentication()
        setattr(authentication, "_get_jwks", lambda: _DEFAULT_JWKS)
        io = SimpleNamespace(request_headers={"authorization": f"Bearer {_DEFAULT_RAW_JWT}"}, authorization_data=None)
        with patch.dict("sys.modules", _mock_jwcrypto_modules()):
            result = authentication.authenticate(cast(Any, io))
        self.assertTrue(result)
        self.assertEqual("https://issuer.example.com", io.authorization_data.get("iss"))

    # --- Format validation: uses real jwcrypto, no JWKS call needed ---

    def test_validate_jwt_rejects_malformed_token(self):
        authentication = self._authentication()
        with self.assertRaises(ClientError):
            authentication.validate_jwt("only.two")

    # --- Issuer validation ---

    def test_validate_jwt_rejects_wrong_issuer(self):
        authentication = self._authentication()
        setattr(authentication, "_get_jwks", lambda: _DEFAULT_JWKS)
        with patch.dict(
            "sys.modules",
            _mock_jwcrypto_modules(
                claims_data={"iss": "https://wrong.example.com", "aud": ["https://audience.example.com"]}
            ),
        ):
            with self.assertRaisesRegex(ClientError, "Issuer does not match"):
                authentication.validate_jwt(_DEFAULT_RAW_JWT)

    def test_validate_jwt_accepts_matching_issuer(self):
        authentication = self._authentication()
        setattr(authentication, "_get_jwks", lambda: _DEFAULT_JWKS)
        with patch.dict("sys.modules", _mock_jwcrypto_modules()):
            self.assertTrue(authentication.validate_jwt(_DEFAULT_RAW_JWT))

    # --- Audience validation ---

    def test_validate_jwt_rejects_when_aud_claim_missing(self):
        authentication = self._authentication()
        setattr(authentication, "_get_jwks", lambda: _DEFAULT_JWKS)
        with patch.dict("sys.modules", _mock_jwcrypto_modules(claims_data={"iss": "https://issuer.example.com"})):
            with self.assertRaisesRegex(ClientError, "Audience required, but missing in JWT"):
                authentication.validate_jwt(_DEFAULT_RAW_JWT)

    def test_validate_jwt_rejects_wrong_audience(self):
        authentication = self._authentication()
        setattr(authentication, "_get_jwks", lambda: _DEFAULT_JWKS)
        with patch.dict(
            "sys.modules",
            _mock_jwcrypto_modules(
                claims_data={"iss": "https://issuer.example.com", "aud": ["https://other.example.com"]}
            ),
        ):
            with self.assertRaisesRegex(ClientError, "Audience does not match"):
                authentication.validate_jwt(_DEFAULT_RAW_JWT)

    def test_validate_jwt_accepts_audience_as_string(self):
        authentication = self._authentication()
        setattr(authentication, "_get_jwks", lambda: _DEFAULT_JWKS)
        with patch.dict(
            "sys.modules",
            _mock_jwcrypto_modules(
                claims_data={"iss": "https://issuer.example.com", "aud": "https://audience.example.com"}
            ),
        ):
            self.assertTrue(authentication.validate_jwt(_DEFAULT_RAW_JWT))

    def test_validate_jwt_accepts_audience_in_list(self):
        authentication = self._authentication()
        setattr(authentication, "_get_jwks", lambda: _DEFAULT_JWKS)
        with patch.dict("sys.modules", _mock_jwcrypto_modules()):
            self.assertTrue(authentication.validate_jwt(_DEFAULT_RAW_JWT))

    # --- claims validation ---

    def test_validate_jwt_accepts_token_when_no_claims_configured(self):
        authentication = self._authentication()
        setattr(authentication, "_get_jwks", lambda: _DEFAULT_JWKS)
        with patch.dict("sys.modules", _mock_jwcrypto_modules()):
            self.assertTrue(authentication.validate_jwt(_DEFAULT_RAW_JWT))

    def test_validate_jwt_rejects_missing_required_claim_from_list(self):
        authentication = self._authentication(claims=["role"])
        setattr(authentication, "_get_jwks", lambda: _DEFAULT_JWKS)
        with patch.dict("sys.modules", _mock_jwcrypto_modules()):
            with self.assertRaisesRegex(ClientError, "Required claim missing: role"):
                authentication.validate_jwt(_DEFAULT_RAW_JWT)

    def test_validate_jwt_accepts_token_when_all_required_claims_present(self):
        authentication = self._authentication(claims=["iss", "scope"])
        setattr(authentication, "_get_jwks", lambda: _DEFAULT_JWKS)
        with patch.dict("sys.modules", _mock_jwcrypto_modules()):
            self.assertTrue(authentication.validate_jwt(_DEFAULT_RAW_JWT))

    def test_validate_jwt_callable_returning_true_accepts_token(self):
        def check_claims(jwt_claims: dict[str, Any]) -> bool:
            return "forbidden" not in jwt_claims

        authentication = self._authentication(claims=check_claims)
        setattr(authentication, "_get_jwks", lambda: _DEFAULT_JWKS)
        with patch.dict("sys.modules", _mock_jwcrypto_modules()):
            self.assertTrue(authentication.validate_jwt(_DEFAULT_RAW_JWT))

    def test_validate_jwt_callable_returning_none_accepts_token(self):
        def check_claims(jwt_claims: dict[str, Any]) -> None:
            return None

        authentication = self._authentication(claims=check_claims)
        setattr(authentication, "_get_jwks", lambda: _DEFAULT_JWKS)
        with patch.dict("sys.modules", _mock_jwcrypto_modules()):
            self.assertTrue(authentication.validate_jwt(_DEFAULT_RAW_JWT))

    def test_validate_jwt_callable_returning_false_rejects_token(self):
        def check_claims(jwt_claims: dict[str, Any]) -> bool:
            return "scope" not in jwt_claims

        authentication = self._authentication(claims=check_claims)
        setattr(authentication, "_get_jwks", lambda: _DEFAULT_JWKS)
        with patch.dict("sys.modules", _mock_jwcrypto_modules()):
            with self.assertRaisesRegex(ClientError, "JWT claims failed custom validation"):
                authentication.validate_jwt(_DEFAULT_RAW_JWT)

    def test_validate_jwt_callable_returning_list_enforces_those_claims(self):
        def check_claims(jwt_claims: dict[str, Any]) -> list[str]:
            return ["role"]  # always require 'role', which is absent from FakeJWT claims

        authentication = self._authentication(claims=check_claims)
        setattr(authentication, "_get_jwks", lambda: _DEFAULT_JWKS)
        with patch.dict("sys.modules", _mock_jwcrypto_modules()):
            with self.assertRaisesRegex(ClientError, "Required claim missing: role"):
                authentication.validate_jwt(_DEFAULT_RAW_JWT)

    # --- _get_jwks caching ---

    def test_get_jwks_fetches_from_url(self):
        authentication = self._authentication()
        requests_mock = MagicMock()
        requests_mock.get.return_value.json.return_value = _DEFAULT_JWKS
        setattr(authentication, "requests", requests_mock)
        setattr(authentication, "now", datetime.datetime(2024, 1, 1))

        result = authentication._get_jwks()

        requests_mock.get.assert_called_once_with("https://example.com/.well-known/jwks.json")
        self.assertEqual(_DEFAULT_JWKS, result)
        self.assertEqual(_DEFAULT_JWKS, authentication._jwks)

    def test_get_jwks_returns_cached_result_within_cache_time(self):
        authentication = self._authentication()
        requests_mock = MagicMock()
        setattr(authentication, "requests", requests_mock)
        setattr(authentication, "now", datetime.datetime(2024, 1, 1, 12, 0, 0))
        authentication._jwks = _DEFAULT_JWKS
        authentication._jwks_fetched = datetime.datetime(2024, 1, 1, 11, 0, 0)  # 1 hour ago, within 24h

        result = authentication._get_jwks()

        requests_mock.get.assert_not_called()
        self.assertEqual(_DEFAULT_JWKS, result)

    def test_get_jwks_refetches_after_cache_expiry(self):
        authentication = self._authentication()
        fresh_jwks = {"keys": [{"kid": "key-2", "alg": "RS256"}]}
        requests_mock = MagicMock()
        requests_mock.get.return_value.json.return_value = fresh_jwks
        setattr(authentication, "requests", requests_mock)
        setattr(authentication, "now", datetime.datetime(2024, 1, 2, 12, 0, 0))
        authentication._jwks = _DEFAULT_JWKS
        authentication._jwks_fetched = datetime.datetime(2024, 1, 1, 11, 0, 0)  # 25 hours ago

        result = authentication._get_jwks()

        requests_mock.get.assert_called_once()
        self.assertEqual(fresh_jwks, result)

    # --- documentation helpers ---

    def test_documentation_security_scheme_returns_oauth2_structure(self):
        authentication = clearskies.authentication.Jwks(
            jwks_url="https://example.com/.well-known/jwks.json",
            authorization_url="https://auth.example.com/authorize",
        )
        scheme = authentication.documentation_security_scheme()
        self.assertEqual("oauth2", scheme["type"])
        self.assertEqual("https://auth.example.com/authorize", scheme["flows"]["implicit"]["authorizationUrl"])

    def test_documentation_security_scheme_name_defaults_to_jwt(self):
        authentication = clearskies.authentication.Jwks(jwks_url="https://example.com/.well-known/jwks.json")
        self.assertEqual("jwt", authentication.documentation_security_scheme_name())

    def test_documentation_security_scheme_name_respects_override(self):
        authentication = clearskies.authentication.Jwks(
            jwks_url="https://example.com/.well-known/jwks.json",
            documentation_security_name="my_scheme",
        )
        self.assertEqual("my_scheme", authentication.documentation_security_scheme_name())

    def test_set_headers_for_cors_adds_authorization(self):
        authentication = self._authentication()
        cors_mock = MagicMock()
        authentication.set_headers_for_cors(cors_mock)
        cors_mock.add_header.assert_called_once_with("Authorization")
