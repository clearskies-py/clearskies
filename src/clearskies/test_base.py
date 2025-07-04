import unittest


class TestBase(unittest.TestCase):
    def tearDown(self):
        import clearskies.backends.memory_backend

        clearskies.backends.memory_backend.MemoryBackend.clear_table_cache()
