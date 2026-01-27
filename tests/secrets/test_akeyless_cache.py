import unittest
from unittest.mock import MagicMock

from clearskies.secrets.akeyless import Akeyless
from clearskies.secrets.cache_storage import SecretCache


class MockSecretCache(SecretCache):
    """Mock implementation of SecretCache for testing."""

    def __init__(self):
        super().__init__()
        self._cache: dict[str, str] = {}
        self.get_calls: list[str] = []
        self.set_calls: list[tuple[str, str, int | None]] = []
        self.delete_calls: list[str] = []
        self.clear_calls: int = 0

    def get(self, path: str) -> str | None:
        self.get_calls.append(path)
        return self._cache.get(path)

    def set(self, path: str, value: str, ttl: int | None = None) -> None:
        self.set_calls.append((path, value, ttl))
        self._cache[path] = value

    def delete(self, path: str) -> None:
        self.delete_calls.append(path)
        if path in self._cache:
            del self._cache[path]

    def clear(self) -> None:
        self.clear_calls += 1
        self._cache.clear()


class AkeylessCacheStorageTest(unittest.TestCase):
    def setUp(self):
        self.mock_api = MagicMock()
        self.mock_akeyless_module = MagicMock()
        self.mock_akeyless_module.Configuration.return_value = MagicMock()
        self.mock_akeyless_module.ApiClient.return_value = MagicMock()
        self.mock_akeyless_module.V2Api.return_value = self.mock_api

        # Mock describe_permissions to always return read/write
        self.mock_api.describe_permissions.return_value = MagicMock(client_permissions=["read", "write", "list"])

        # Mock auth to return a token
        self.mock_api.auth.return_value = MagicMock(token="test-token")

    def _create_akeyless(self, cache_storage=None):
        """Create an Akeyless instance with mocked dependencies."""
        akeyless = Akeyless(
            access_id="p-test123",
            access_type="aws_iam",
            cache_storage=cache_storage,
        )
        akeyless.akeyless = self.mock_akeyless_module
        akeyless._api = self.mock_api
        # Pre-set a token to avoid authentication calls
        akeyless._token = "test-token"
        import datetime

        akeyless._token_refresh = datetime.datetime.now() + datetime.timedelta(hours=1)
        return akeyless

    def test_get_without_cache(self):
        """Test that get works without cache_storage configured."""
        akeyless = self._create_akeyless()

        # Mock the API response
        self.mock_api.get_secret_value.return_value = {"/path/to/secret": "secret-value"}

        result = akeyless.get("/path/to/secret")

        self.assertEqual(result, "secret-value")
        self.mock_api.get_secret_value.assert_called_once()

    def test_get_with_cache_miss(self):
        """Test that get fetches from API on cache miss and stores in cache."""
        cache = MockSecretCache()
        akeyless = self._create_akeyless(cache_storage=cache)

        # Mock the API response
        self.mock_api.get_secret_value.return_value = {"/path/to/secret": "secret-value"}

        result = akeyless.get("/path/to/secret")

        # Should have checked cache
        self.assertEqual(cache.get_calls, ["/path/to/secret"])
        # Should have fetched from API
        self.mock_api.get_secret_value.assert_called_once()
        # Should have stored in cache
        self.assertEqual(cache.set_calls, [("/path/to/secret", "secret-value", None)])
        # Should return the value
        self.assertEqual(result, "secret-value")

    def test_get_with_cache_hit(self):
        """Test that get returns cached value without calling API."""
        cache = MockSecretCache()
        cache._cache["/path/to/secret"] = "cached-value"
        akeyless = self._create_akeyless(cache_storage=cache)

        result = akeyless.get("/path/to/secret")

        # Should have checked cache
        self.assertEqual(cache.get_calls, ["/path/to/secret"])
        # Should NOT have fetched from API
        self.mock_api.get_secret_value.assert_not_called()
        # Should NOT have stored in cache (already there)
        self.assertEqual(cache.set_calls, [])
        # Should return the cached value
        self.assertEqual(result, "cached-value")

    def test_get_with_refresh_bypasses_cache(self):
        """Test that get with refresh=True bypasses cache and fetches from API."""
        cache = MockSecretCache()
        cache._cache["/path/to/secret"] = "cached-value"
        akeyless = self._create_akeyless(cache_storage=cache)

        # Mock the API response
        self.mock_api.get_secret_value.return_value = {"/path/to/secret": "fresh-value"}

        result = akeyless.get("/path/to/secret", refresh=True)

        # Should NOT have checked cache (refresh=True)
        self.assertEqual(cache.get_calls, [])
        # Should have fetched from API
        self.mock_api.get_secret_value.assert_called_once()
        # Should have stored new value in cache
        self.assertEqual(cache.set_calls, [("/path/to/secret", "fresh-value", None)])
        # Should return the fresh value
        self.assertEqual(result, "fresh-value")
        # Cache should now have the fresh value
        self.assertEqual(cache._cache["/path/to/secret"], "fresh-value")

    def test_update_updates_cache(self):
        """Test that update also updates the cache."""
        cache = MockSecretCache()
        akeyless = self._create_akeyless(cache_storage=cache)

        akeyless.update("/path/to/secret", "new-value")

        # Should have updated the API
        self.mock_api.update_secret_val.assert_called_once()
        # Should have updated the cache
        self.assertEqual(cache.set_calls, [("/path/to/secret", "new-value", None)])
        self.assertEqual(cache._cache["/path/to/secret"], "new-value")

    def test_upsert_updates_cache(self):
        """Test that upsert also updates the cache."""
        cache = MockSecretCache()
        akeyless = self._create_akeyless(cache_storage=cache)

        akeyless.upsert("/path/to/secret", "upserted-value")

        # Should have updated the cache
        # Note: upsert calls update which also sets cache, so we may have 2 set calls
        self.assertIn(("/path/to/secret", "upserted-value", None), cache.set_calls)
        self.assertEqual(cache._cache["/path/to/secret"], "upserted-value")


class SecretCacheConfigTest(unittest.TestCase):
    def test_cache_storage_accepts_secret_cache_instance(self):
        """Test that cache_storage config accepts SecretCache instances."""
        cache = MockSecretCache()

        # This should not raise
        akeyless = Akeyless.__new__(Akeyless)
        akeyless._config = {}
        akeyless.cache_storage = cache

        self.assertEqual(akeyless.cache_storage, cache)

    def test_cache_storage_rejects_invalid_type(self):
        """Test that cache_storage config rejects non-SecretCache values."""
        from clearskies.configs.secret_cache import SecretCache as SecretCacheConfig

        config = SecretCacheConfig()

        class MockInstance:
            _config = {}

            def _set_config(self, descriptor, value):
                self._config[descriptor] = value

            def _descriptor_to_name(self, descriptor):
                return "cache_storage"

        instance = MockInstance()

        # Should raise TypeError for invalid type
        with self.assertRaises(TypeError):
            config.__set__(instance, "not-a-cache")


if __name__ == "__main__":
    unittest.main()
