import clearskies
from tests.test_base import TestBase


class SimpleSearchTest(TestBase):
    def test_overview(self):
        class Student(clearskies.Model):
            backend = clearskies.backends.MemoryBackend()
            id_column_name = "id"

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()
            grade = clearskies.columns.Integer()

        context = clearskies.contexts.Context(
            clearskies.endpoints.SimpleSearch(
                Student,
                readable_column_names=["id", "name", "grade"],
                sortable_column_names=["name", "grade"],
                searchable_column_names=["name", "grade"],
                default_sort_column_name="name",
            ),
            bindings={
                "memory_backend_default_data": [
                    {
                        "model_class": Student,
                        "records": [
                            {"id": "1-2-3-4", "name": "Bob", "grade": 5},
                            {"id": "1-2-3-5", "name": "Jane", "grade": 3},
                            {"id": "1-2-3-6", "name": "Greg", "grade": 3},
                            {"id": "1-2-3-7", "name": "Bob", "grade": 2},
                        ],
                    },
                ],
            },
        )

        status_code, response_data, response_headers = context()
        assert response_data["data"] == [
            {"id": "1-2-3-4", "name": "Bob", "grade": 5},
            {"id": "1-2-3-7", "name": "Bob", "grade": 2},
            {"id": "1-2-3-6", "name": "Greg", "grade": 3},
            {"id": "1-2-3-5", "name": "Jane", "grade": 3},
        ]

        status_code, response_data, response_headers = context(query_parameters={"name": "Bob"})
        assert response_data["data"] == [
            {"id": "1-2-3-4", "name": "Bob", "grade": 5},
            {"id": "1-2-3-7", "name": "Bob", "grade": 2},
        ]

        status_code, response_data, response_headers = context(query_parameters={"name": "Bob", "grade": "2"})
        assert response_data["data"] == [
            {"id": "1-2-3-7", "name": "Bob", "grade": 2},
        ]

        status_code, response_data, response_headers = context(
            query_parameters={"sort": "grade", "direction": "desc", "limit": "2"}
        )
        assert response_data["data"] == [
            {"id": "1-2-3-4", "name": "Bob", "grade": 5},
            {"id": "1-2-3-5", "name": "Jane", "grade": 3},
        ]
        assert response_data["pagination"] == {"number_results": 4, "limit": 2, "next_page": {"start": 2}}

        status_code, response_data, response_headers = context(
            query_parameters={"sort": "grade", "direction": "desc", "limit": "2", "start": "2"}
        )
        assert response_data["data"] == [
            {"id": "1-2-3-6", "name": "Greg", "grade": 3},
            {"id": "1-2-3-7", "name": "Bob", "grade": 2},
        ]
        assert response_data["pagination"] == {"number_results": 4, "limit": 2, "next_page": {}}

    def test_search_on_related_column(self):
        class Category(clearskies.Model):
            backend = clearskies.backends.MemoryBackend()
            id_column_name = "id"

            id = clearskies.columns.String()
            name = clearskies.columns.String()

        class Product(clearskies.Model):
            backend = clearskies.backends.MemoryBackend()
            id_column_name = "id"

            id = clearskies.columns.String()
            name = clearskies.columns.String()
            category_id = clearskies.columns.BelongsToId(Category, readable_parent_columns=["id", "name"])
            category = clearskies.columns.BelongsToModel("category_id")

        context = clearskies.contexts.Context(
            clearskies.endpoints.SimpleSearch(
                Product,
                readable_column_names=["id", "name"],
                sortable_column_names=["name"],
                searchable_column_names=["name", "category.name"],
                default_sort_column_name="name",
            ),
            classes=[Category, Product],
            bindings={
                "memory_backend_default_data": [
                    {"model_class": Category, "records": [{"id": "c1", "name": "Toys"}, {"id": "c2", "name": "Auto"}]},
                    {
                        "model_class": Product,
                        "records": [
                            {"id": "p1", "name": "Ball", "category_id": "c1"},
                            {"id": "p2", "name": "Tire", "category_id": "c2"},
                            {"id": "p3", "name": "Kite", "category_id": "c1"},
                        ],
                    },
                ],
            },
        )

        status_code, response_data, response_headers = context(query_parameters={"category.name": "Toys"})
        assert status_code == 200
        assert response_data["data"] == [{"id": "p1", "name": "Ball"}, {"id": "p3", "name": "Kite"}]
