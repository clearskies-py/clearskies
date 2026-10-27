import unittest

import clearskies
from clearskies import columns


class MemoryBackendTest(unittest.TestCase):
    def test_swap(self):
        class UserPreference(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.CursorBackend()
            id = clearskies.columns.Uuid()

        context = clearskies.contexts.Context(
            clearskies.endpoints.Callable(
                lambda user_preferences: user_preferences.create(no_data=True).id,
            ),
            classes=[UserPreference],
            class_overrides={
                clearskies.backends.CursorBackend: clearskies.backends.MemoryBackend(),
            },
        )
        status_code, response, response_headers = context()
        assert status_code == 200
        assert len(response["data"]) == 36

    def test_predefined_rows(self):
        class Owner(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()
            phone = clearskies.columns.Phone()

        class Pet(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()
            species = clearskies.columns.String()
            owner_id = clearskies.columns.BelongsToId(Owner, readable_parent_columns=["id", "name"])
            owner = clearskies.columns.BelongsToModel("owner_id")

        context = clearskies.contexts.Context(
            clearskies.endpoints.List(
                model_class=Pet,
                readable_column_names=["id", "name", "species", "owner"],
                sortable_column_names=["id", "name", "species"],
                default_sort_column_name="name",
            ),
            classes=[Owner, Pet],
            bindings={
                "memory_backend_default_data": [
                    {
                        "model_class": Owner,
                        "records": [
                            {"id": "1-2-3-4", "name": "John Doe", "phone": "555-123-4567"},
                            {"id": "5-6-7-8", "name": "Jane Doe", "phone": "555-321-0987"},
                        ],
                    },
                    {
                        "model_class": Pet,
                        "records": [
                            {"id": "a-b-c-d", "name": "Fido", "species": "Dog", "owner_id": "1-2-3-4"},
                            {"id": "e-f-g-h", "name": "Spot", "species": "Dog", "owner_id": "1-2-3-4"},
                            {"id": "i-j-k-l", "name": "Puss in Boots", "species": "Cat", "owner_id": "5-6-7-8"},
                        ],
                    },
                ],
            },
        )
        status_code, response, response_headers = context()
        assert response["data"] == [
            {"id": "a-b-c-d", "name": "Fido", "species": "Dog", "owner": {"id": "1-2-3-4", "name": "John Doe"}},
            {
                "id": "i-j-k-l",
                "name": "Puss in Boots",
                "species": "Cat",
                "owner": {"id": "5-6-7-8", "name": "Jane Doe"},
            },
            {"id": "e-f-g-h", "name": "Spot", "species": "Dog", "owner": {"id": "1-2-3-4", "name": "John Doe"}},
        ]

    def test_boolean_filter_false(self):
        """MemoryBackend must correctly filter by Boolean=False (deleted=0)."""

        class Item(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = columns.Uuid()
            name = columns.String()
            deleted = columns.Boolean()

        def run(items):
            items.create({"name": "active", "deleted": False})
            items.create({"name": "gone", "deleted": True})

            active = list(items.where("deleted=0"))
            gone = list(items.where("deleted=1"))

            return {
                "active_count": len(active),
                "active_name": active[0].name if active else "",
                "gone_count": len(gone),
                "gone_name": gone[0].name if gone else "",
            }

        context = clearskies.contexts.Context(run, classes=[Item])
        status_code, response, _ = context()

        assert status_code == 200
        assert response["active_count"] == 1
        assert response["active_name"] == "active"
        assert response["gone_count"] == 1
        assert response["gone_name"] == "gone"

    def _like_names(self, *conditions):
        class Person(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = columns.Uuid()
            name = columns.String()

        def run(persons):
            for name in ["Alice", "alfred", "Bob", "50% off", "a.c", "abc", None]:
                persons.create({"name": name})
            return [sorted(str(person.name) for person in persons.where(condition)) for condition in conditions]

        status_code, response, _ = clearskies.contexts.Context(run, classes=[Person])()
        assert status_code == 200
        return response

    def test_like_wildcards(self):
        assert self._like_names(
            "name like 'al%'",
            "name like '%b'",
            "name like '%L%'",
            "name like 'a_c'",
            "name like 'bob'",
            "name like 'bo'",
        ) == [
            ["Alice", "alfred"],
            ["Bob"],
            ["Alice", "alfred"],
            ["a.c", "abc"],
            ["Bob"],
            [],
        ]

    def test_like_escaping(self):
        assert self._like_names("name like 'a.c'", "name like '50\\% off'", "name like '%(%'") == [
            ["a.c"],
            ["50% off"],
            [],
        ]

    def test_not_like(self):
        # NULL matches neither LIKE nor NOT LIKE, as in SQL
        assert self._like_names("name not like 'a%'") == [["50% off", "Bob"]]

    def test_in_and_not_in(self):
        # NULL matches neither IN nor NOT IN, as in SQL
        assert self._like_names("name in ('Bob', 'abc')", "name not in ('Bob', 'abc', 'a.c')") == [
            ["Bob", "abc"],
            ["50% off", "Alice", "alfred"],
        ]

    def test_like_column_condition(self):
        class Person(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = columns.Uuid()
            name = columns.String()

        def run(persons):
            persons.create({"name": "Alice"})
            persons.create({"name": "Bob"})
            return [person.name for person in persons.where(Person.name.like("%LIC%"))]

        status_code, response, _ = clearskies.contexts.Context(run, classes=[Person])()
        assert response == ["Alice"]
