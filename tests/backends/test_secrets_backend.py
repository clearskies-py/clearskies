import pytest

import clearskies
from clearskies.contexts import Context


class FakeSecrets:
    def __init__(self):
        self.store: dict[str, str] = {}

    def list_secrets(self, path):
        return [name for name in self.store if name.startswith(path)]

    def get(self, path):
        return self.store.get(path)

    def upsert(self, path, value):
        self.store[path] = str(value)

    def delete(self, path):
        del self.store[path]
        return True


class ApiKey(clearskies.Model):
    id_column_name = "id"
    backend = clearskies.backends.SecretsBackend()

    id = clearskies.columns.String()
    owner = clearskies.columns.String()
    api_key = clearskies.columns.String()

    @classmethod
    def destination_name(cls):
        return "api-keys"


def build():
    secrets = FakeSecrets()
    api_keys = Context(lambda: None, classes=[ApiKey], bindings={"secrets": secrets}).build(ApiKey)
    return api_keys, secrets


def test_create_find_update_delete():
    api_keys, secrets = build()

    api_keys.create({"id": "key-1", "owner": "alice", "api_key": "REPLACE_ME"})
    assert secrets.store == {"api-keys/key-1/owner": "alice", "api-keys/key-1/api_key": "REPLACE_ME"}

    record = api_keys.find("id=key-1")
    assert (record.id, record.owner, record.api_key) == ("key-1", "alice", "REPLACE_ME")

    record.save({"api_key": "NEW_VALUE"})
    assert api_keys.find("id=key-1").api_key == "NEW_VALUE"

    record.delete()
    assert secrets.store == {}
    assert not api_keys.find("id=key-1")


def test_missing_record_and_other_conditions():
    api_keys, secrets = build()
    api_keys.create({"id": "key-1", "owner": "alice", "api_key": "REPLACE_ME"})

    assert not api_keys.find("id=key-2")
    assert api_keys.where("id=key-1").where("owner=alice").first().id == "key-1"
    assert not api_keys.where("id=key-1").where("owner=bob").first()


@pytest.mark.parametrize("bad_id", ["a/../b", "..", "", "x/y"])
def test_id_cannot_escape_the_folder(bad_id):
    api_keys, secrets = build()
    with pytest.raises(ValueError):
        api_keys.backend.records(api_keys.where(f"id={bad_id}").get_query())
