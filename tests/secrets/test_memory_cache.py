import datetime
import unittest

from clearskies.di import Di
from clearskies.secrets.cache_storage import MemoryCache


class MemoryCacheTest(unittest.TestCase):
    def setUp(self):
        """Set up a DI container and inject it into the cache."""
        self.di = Di()
        self.current_time = datetime.datetime(2024, 1, 1, 12, 0, 0)
        self.di.set_now(self.current_time)

    def _create_cache(self, default_ttl: int | None = None) -> MemoryCache:
        """Create a MemoryCache with DI injected."""
        cache = MemoryCache(default_ttl=default_ttl)
        cache.injectable_properties(di=self.di)
        return cache

    def _advance_time(self, seconds: int) -> None:
        """Advance the mock time by the given number of seconds."""
        self.current_time = self.current_time + datetime.timedelta(seconds=seconds)
        self.di.set_now(self.current_time)

    def test_get_returns_none_for_missing_key(self):
        """Test that get returns None for keys not in cache."""
        cache = self._create_cache()
        result = cache.get("/path/to/secret")
        self.assertIsNone(result)

    def test_set_and_get(self):
        """Test basic set and get functionality."""
        cache = self._create_cache()
        cache.set("/path/to/secret", "secret-value")
        result = cache.get("/path/to/secret")
        self.assertEqual(result, "secret-value")

    def test_set_overwrites_existing(self):
        """Test that set overwrites existing values."""
        cache = self._create_cache()
        cache.set("/path/to/secret", "old-value")
        cache.set("/path/to/secret", "new-value")
        result = cache.get("/path/to/secret")
        self.assertEqual(result, "new-value")

    def test_delete_removes_entry(self):
        """Test that delete removes an entry from cache."""
        cache = self._create_cache()
        cache.set("/path/to/secret", "secret-value")
        cache.delete("/path/to/secret")
        result = cache.get("/path/to/secret")
        self.assertIsNone(result)

    def test_delete_nonexistent_key_does_not_raise(self):
        """Test that deleting a nonexistent key doesn't raise."""
        cache = self._create_cache()
        # Should not raise
        cache.delete("/nonexistent/path")

    def test_clear_removes_all_entries(self):
        """Test that clear removes all entries from cache."""
        cache = self._create_cache()
        cache.set("/path/one", "value-one")
        cache.set("/path/two", "value-two")
        cache.clear()
        self.assertIsNone(cache.get("/path/one"))
        self.assertIsNone(cache.get("/path/two"))
        self.assertEqual(cache.size, 0)

    def test_size_property(self):
        """Test the size property returns correct count."""
        cache = self._create_cache()
        self.assertEqual(cache.size, 0)
        cache.set("/path/one", "value-one")
        self.assertEqual(cache.size, 1)
        cache.set("/path/two", "value-two")
        self.assertEqual(cache.size, 2)
        cache.delete("/path/one")
        self.assertEqual(cache.size, 1)


class MemoryCacheTTLTest(unittest.TestCase):
    def setUp(self):
        """Set up a DI container and inject it into the cache."""
        self.di = Di()
        self.current_time = datetime.datetime(2024, 1, 1, 12, 0, 0)
        self.di.set_now(self.current_time)

    def _create_cache(self, default_ttl: int | None = None) -> MemoryCache:
        """Create a MemoryCache with DI injected."""
        cache = MemoryCache(default_ttl=default_ttl)
        cache.injectable_properties(di=self.di)
        return cache

    def _advance_time(self, seconds: int) -> None:
        """Advance the mock time by the given number of seconds."""
        self.current_time = self.current_time + datetime.timedelta(seconds=seconds)
        self.di.set_now(self.current_time)

    def test_default_ttl_applied(self):
        """Test that default_ttl is applied to entries."""
        cache = self._create_cache(default_ttl=60)
        cache.set("/path/to/secret", "secret-value")

        # Should be available immediately
        self.assertEqual(cache.get("/path/to/secret"), "secret-value")

        # Advance time past TTL
        self._advance_time(61)

        # Should be expired now
        self.assertIsNone(cache.get("/path/to/secret"))

    def test_explicit_ttl_overrides_default(self):
        """Test that explicit TTL overrides default_ttl."""
        cache = self._create_cache(default_ttl=600)
        cache.set("/path/to/secret", "secret-value", ttl=60)

        # Should be available immediately
        self.assertEqual(cache.get("/path/to/secret"), "secret-value")

        # Advance time past explicit TTL but not default
        self._advance_time(61)

        # Should be expired now
        self.assertIsNone(cache.get("/path/to/secret"))

    def test_no_ttl_never_expires(self):
        """Test that entries without TTL never expire."""
        cache = self._create_cache()  # No default_ttl
        cache.set("/path/to/secret", "secret-value")

        # Entry should not have an expiration
        entry = cache._cache["/path/to/secret"]
        self.assertIsNone(entry.expires_at)
        self.assertFalse(entry.is_expired(self.current_time))

        # Even after a long time, should still be available
        self._advance_time(86400 * 365)  # 1 year
        self.assertEqual(cache.get("/path/to/secret"), "secret-value")

    def test_cleanup_expired_removes_expired_entries(self):
        """Test that cleanup_expired removes all expired entries."""
        cache = self._create_cache()
        cache.set("/path/one", "value-one", ttl=60)
        cache.set("/path/two", "value-two")  # No TTL, never expires

        # Advance time past first entry's TTL
        self._advance_time(61)

        # Cleanup should remove 1 entry
        removed = cache.cleanup_expired()
        self.assertEqual(removed, 1)
        self.assertEqual(cache.size, 1)
        self.assertIsNone(cache.get("/path/one"))
        self.assertEqual(cache.get("/path/two"), "value-two")

    def test_get_removes_expired_entry(self):
        """Test that get() lazily removes expired entries."""
        cache = self._create_cache()
        cache.set("/path/to/secret", "secret-value", ttl=60)

        # Entry exists
        self.assertEqual(cache.size, 1)

        # Advance time past TTL
        self._advance_time(61)

        # Get should return None and remove the entry
        result = cache.get("/path/to/secret")
        self.assertIsNone(result)
        self.assertEqual(cache.size, 0)


if __name__ == "__main__":
    unittest.main()
