import pytest

from clearskies.backends.memory_backend import MemoryBackend


@pytest.fixture(autouse=True)
def clear_memory_backend_tables():
    MemoryBackend.clear_table_cache()
    yield
    MemoryBackend.clear_table_cache()
