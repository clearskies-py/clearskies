import clearskies
from clearskies import columns
from clearskies.validators import Required, Unique
from tests.test_base import TestBase


class RestfulApiTest(TestBase):
    def test_overview(self):
        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = columns.Uuid()
            name = columns.String(validators=[Required()])
            username = columns.String(
                validators=[
                    Required(),
                    Unique(),
                ]
            )
            age = columns.Integer(validators=[Required()])
            created_at = columns.Created()
            updated_at = columns.Updated()

        context = clearskies.contexts.Context(
            clearskies.endpoints.RestfulApi(
                url="users",
                model_class=User,
                readable_column_names=["id", "name", "username", "age", "created_at", "updated_at"],
                writeable_column_names=["name", "username", "age"],
                sortable_column_names=["id", "name", "username", "age", "created_at", "updated_at"],
                searchable_column_names=["id", "name", "username", "age", "created_at", "updated_at"],
                default_sort_column_name="name",
            )
        )

        status_code, response_data, response_headers = context(
            request_method="POST",
            body={"name": "Bob", "username": "bob", "age": 25},
            url="users",
        )
        bob_id = response_data["data"]["id"]
        assert response_data["data"]["name"] == "Bob"
        assert response_data["data"]["age"] == 25

        status_code, response_data, response_headers = context(
            request_method="POST",
            body={"name": "Alice", "username": "alice", "age": 22},
            url="users",
        )
        assert response_data["data"]["name"] == "Alice"
        assert response_data["data"]["age"] == 22
        alice_id = response_data["data"]["id"]

        status_code, response_data, response_headers = context(
            url=f"users/{bob_id}",
        )
        assert response_data["data"]["name"] == "Bob"
        assert response_data["data"]["age"] == 25

        status_code, response_data, response_headers = context(
            request_method="PATCH",
            body={"name": "Alice Smith", "age": 23},
            url=f"users/{alice_id}",
        )
        assert response_data["data"]["name"] == "Alice Smith"
        assert response_data["data"]["age"] == 23

        status_code, response_data, response_headers = context(
            request_method="DELETE",
            url=f"users/{bob_id}",
        )
        assert not response_data["data"]
        assert response_data["status"] == "success"

        status_code, response_data, response_headers = context(
            url="users",
        )
        assert response_data["status"] == "success"
        assert [record["name"] for record in response_data["data"]] == ["Alice Smith"]

    def test_nested_resource_with_matching_primary_key(self):
        """
        Test that RestfulApi doesn't create duplicate URL parameters.

        When the base URL already contains a parameter that matches the model's primary key.

        Example: resources/:resource_id/setting should not become
        resources/:resource_id/setting/:resource_id
        """

        class ResourceSetting(clearskies.Model):
            # This model uses resource_id as its primary key (singleton per resource)
            id_column_name = "resource_id"
            backend = clearskies.backends.MemoryBackend()

            resource_id = columns.String(validators=[Required()])
            feature_enabled = columns.Boolean()
            max_users = columns.Integer()

        context = clearskies.contexts.Context(
            clearskies.endpoints.RestfulApi(
                url="resources/:resource_id/setting",
                model_class=ResourceSetting,
                readable_column_names=["resource_id", "feature_enabled", "max_users"],
                writeable_column_names=["resource_id", "feature_enabled", "max_users"],
                sortable_column_names=["resource_id"],
                searchable_column_names=["resource_id"],
                default_sort_column_name="resource_id",
            )
        )

        # Create a setting for resource "res-123"
        status_code, response_data, response_headers = context(
            request_method="POST",
            body={"resource_id": "res-123", "feature_enabled": True, "max_users": 100},
            url="resources/res-123/setting",
        )
        assert response_data["status"] == "success"
        assert response_data["data"]["resource_id"] == "res-123"
        assert response_data["data"]["feature_enabled"] is True

        # Get the setting for resource "res-123"
        # Should work at resources/res-123/setting, NOT resources/res-123/setting/res-123
        status_code, response_data, response_headers = context(
            request_method="GET",
            url="resources/res-123/setting",
        )
        assert response_data["status"] == "success"
        assert response_data["data"]["resource_id"] == "res-123"

        # Update the setting
        status_code, response_data, response_headers = context(
            request_method="PATCH",
            body={"max_users": 200},
            url="resources/res-123/setting",
        )
        assert response_data["status"] == "success"
        assert response_data["data"]["max_users"] == 200

        # Delete the setting
        status_code, response_data, response_headers = context(
            request_method="DELETE",
            url="resources/res-123/setting",
        )
        assert response_data["status"] == "success"
