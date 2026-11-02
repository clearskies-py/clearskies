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

    def _users_context(self, url: str = "users"):
        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()
            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()

        context = clearskies.contexts.Context(
            clearskies.endpoints.List(
                model_class=User,
                url=url,
                readable_column_names=["id", "name"],
                sortable_column_names=["name"],
                searchable_column_names=["name"],
                default_sort_column_name="name",
            ),
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
        return context

    def test_link_header_points_to_next_page(self):
        context = self._users_context()
        status_code, response_data, response_headers = context(
            url="users", query_parameters={"limit": "2", "sort": "name", "direction": "desc"}
        )

        assert response_data["pagination"]["next_page"] == {"start": 2}
        assert response_headers["link"] == '<?limit=2&sort=name&direction=desc&start=2>; rel="next"'

        status_code, response_data, response_headers = context(
            url="users", query_parameters={"limit": "2", "start": "2"}
        )
        assert response_data["data"] == [{"id": "1-2-3-5", "name": "Jane"}]
        assert "link" not in response_headers

    def test_no_link_header_for_post(self):
        context = self._users_context()
        status_code, response_data, response_headers = context(url="users", request_method="POST", body={"limit": 2})
        assert "link" not in response_headers

    def test_api_backend_pages_through_list_with_link_header(self):
        from unittest.mock import MagicMock
        from urllib.parse import parse_qsl, urlparse

        server = self._users_context()
        # Render both pages up front: running the server context inside the mocked request would swap the client's DI.
        pages = {}
        for query in ({"limit": "2"}, {"limit": "2", "start": "2"}):
            status_code, body, headers = server(url="users", query_parameters=dict(query))
            pages[tuple(sorted(query.items()))] = (body, {k.lower(): v for k, v in headers.items()})

        def request(method, url, **kwargs):
            body, headers = pages[tuple(sorted(parse_qsl(urlparse(url).query)))]
            response = MagicMock(ok=True, status_code=200, headers=headers)
            response.json.return_value = body
            return response

        class RemoteUser(clearskies.Model):
            id_column_name = "id"
            # No pagination adapter configured: ApiBackend defaults to following Link headers.
            backend = clearskies.backends.ApiBackend(
                base_url="https://api.example.com",
                response_adapter=lambda response: response.get("data"),
            )
            id = clearskies.columns.String()
            name = clearskies.columns.String()

            @classmethod
            def destination_name(cls):
                return "users"

        requests = MagicMock()
        requests.request.side_effect = request
        found = {}

        def application(remote_users: RemoteUser):
            found["names"] = [user.name for user in remote_users.limit(2).paginate_all()]

        clearskies.contexts.Context(application, classes=[RemoteUser], bindings={"requests": requests})()

        assert found["names"] == ["Bob", "Greg", "Jane"]
        assert requests.request.call_count == 2
