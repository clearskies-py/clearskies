import clearskies
from tests.test_base import TestBase


class ListTest(TestBase):
    def test_overview(self):
        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()
            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()

        list_users = clearskies.endpoints.List(
            model_class=User,
            readable_column_names=["id", "name"],
            sortable_column_names=["id", "name"],
            default_sort_column_name="name",
        )

        context = clearskies.contexts.Context(
            list_users,
            classes=[User],
            bindings={
                "memory_backend_default_data": [
                    {
                        "model_class": User,
                        "records": [
                            {"id": "1-2-3-4", "name": "Bob"},
                            {"id": "1-2-3-5", "name": "Jane"},
                            {"id": "1-2-3-6", "name": "Greg"},
                        ],
                    },
                ]
            },
        )
        status_code, response_data, response_headers = context()

        assert response_data["data"] == [
            {"id": "1-2-3-4", "name": "Bob"},
            {"id": "1-2-3-6", "name": "Greg"},
            {"id": "1-2-3-5", "name": "Jane"},
        ]

    def test_join(self):
        class Student(clearskies.Model):
            backend = clearskies.backends.MemoryBackend()
            id_column_name = "id"

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()
            grade = clearskies.columns.Integer()
            will_graduate = clearskies.columns.Boolean()

        class PastRecord(clearskies.Model):
            backend = clearskies.backends.MemoryBackend()
            id_column_name = "id"

            id = clearskies.columns.Uuid()
            student_id = clearskies.columns.BelongsToId(Student)
            school_name = clearskies.columns.String()

        context = clearskies.contexts.Context(
            clearskies.endpoints.List(
                Student,
                readable_column_names=["id", "name", "grade"],
                sortable_column_names=["name", "grade"],
                default_sort_column_name="name",
                joins=["INNER JOIN past_records ON past_records.student_id=students.id"],
            ),
            bindings={
                "memory_backend_default_data": [
                    {
                        "model_class": Student,
                        "records": [
                            {"id": "1-2-3-4", "name": "Bob", "grade": 5, "will_graduate": True},
                            {"id": "1-2-3-5", "name": "Jane", "grade": 3, "will_graduate": True},
                            {"id": "1-2-3-6", "name": "Greg", "grade": 3, "will_graduate": False},
                            {"id": "1-2-3-7", "name": "Bob", "grade": 2, "will_graduate": True},
                            {"id": "1-2-3-8", "name": "Ann", "grade": 12, "will_graduate": True},
                        ],
                    },
                    {
                        "model_class": PastRecord,
                        "records": [
                            {"id": "5-2-3-4", "student_id": "1-2-3-4", "school_name": "Best Academy"},
                            {"id": "5-2-3-5", "student_id": "1-2-3-5", "school_name": "Awesome School"},
                        ],
                    },
                ],
            },
        )
        status_code, response_data, response_headers = context()

        assert response_data["data"] == [
            {"id": "1-2-3-4", "name": "Bob", "grade": 5},
            {"id": "1-2-3-5", "name": "Jane", "grade": 3},
        ]

    def test_limit_without_searchable_columns(self):
        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()
            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()

        context = clearskies.contexts.Context(
            clearskies.endpoints.List(
                model_class=User,
                readable_column_names=["id", "name"],
                sortable_column_names=["name"],
                default_sort_column_name="name",
            ),
            bindings={
                "memory_backend_default_data": [
                    {
                        "model_class": User,
                        "records": [
                            {"id": "1", "name": "Ann"},
                            {"id": "2", "name": "Bob"},
                            {"id": "3", "name": "Cat"},
                        ],
                    },
                ]
            },
        )
        status_code, response_data, response_headers = context(query_parameters={"limit": "2"})

        assert status_code == 200
        assert ["Ann", "Bob"] == [record["name"] for record in response_data["data"]]

    def test_sort_from_request(self):
        class Student(clearskies.Model):
            backend = clearskies.backends.MemoryBackend()
            id_column_name = "id"

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()
            grade = clearskies.columns.Integer()

        context = clearskies.contexts.Context(
            clearskies.endpoints.List(
                Student,
                readable_column_names=["id", "name", "grade"],
                sortable_column_names=["name", "grade"],
                default_sort_column_name="name",
            ),
            bindings={
                "memory_backend_default_data": [
                    {
                        "model_class": Student,
                        "records": [
                            {"id": "1", "name": "Ann", "grade": 3},
                            {"id": "2", "name": "Bob", "grade": 12},
                            {"id": "3", "name": "Cat", "grade": 7},
                        ],
                    },
                ],
            },
        )
        status_code, response_data, response_headers = context(query_parameters={"sort": "grade", "direction": "desc"})

        assert [12, 7, 3] == [record["grade"] for record in response_data["data"]]
