import clearskies
from clearskies.autodoc.schema import Object as AutoDocObject
from tests.test_base import TestBase


class HasOneTest(TestBase):
    def test_has_one_get(self):
        """Test that HasOne.__get__ returns a single model record."""

        class ProjectSetting(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            gitlab_project_id = clearskies.columns.String()
            visibility = clearskies.columns.String()
            merge_method = clearskies.columns.String()

        class Project(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()
            settings = clearskies.columns.HasOne(
                ProjectSetting,
                foreign_column_name="gitlab_project_id",
                readable_child_column_names=["visibility", "merge_method"],
            )

        def test_has_one(projects: Project, project_settings: ProjectSetting):
            project = projects.create({"name": "My Project"})
            project_settings.create(
                {
                    "gitlab_project_id": project.id,
                    "visibility": "private",
                    "merge_method": "merge",
                }
            )

            settings = project.settings
            return {"visibility": settings.visibility, "merge_method": settings.merge_method}

        context = clearskies.contexts.Context(
            clearskies.endpoints.Callable(
                test_has_one,
            ),
            classes=[Project, ProjectSetting],
        )
        status_code, response_data, response_headers = context()
        assert response_data["data"]["visibility"] == "private"
        assert response_data["data"]["merge_method"] == "merge"

    def test_has_one_to_json(self):
        """Test that HasOne.to_json returns a dict (not a list) for a single child."""

        class ProjectSetting(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            gitlab_project_id = clearskies.columns.String()
            visibility = clearskies.columns.String()
            merge_method = clearskies.columns.String()

        class Project(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()
            settings = clearskies.columns.HasOne(
                ProjectSetting,
                foreign_column_name="gitlab_project_id",
                readable_child_column_names=["visibility", "merge_method"],
            )

        def test_has_one_json(projects: Project, project_settings: ProjectSetting):
            project = projects.create({"name": "My Project"})
            setting = project_settings.create(
                {
                    "gitlab_project_id": project.id,
                    "visibility": "private",
                    "merge_method": "merge",
                }
            )

            return project

        context = clearskies.contexts.Context(
            clearskies.endpoints.Callable(
                test_has_one_json,
                model_class=Project,
                readable_column_names=["id", "name", "settings"],
            ),
            classes=[Project, ProjectSetting],
        )
        status_code, response_data, response_headers = context()
        assert response_data["status"] == "success"
        data = response_data["data"]
        # settings should be a dict, not a list
        assert isinstance(data["settings"], dict)
        assert data["settings"]["visibility"] == "private"
        assert data["settings"]["merge_method"] == "merge"

    def test_has_one_to_json_no_child(self):
        """Test that HasOne.to_json returns None when there is no child."""

        class ProjectSetting(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            gitlab_project_id = clearskies.columns.String()
            visibility = clearskies.columns.String()

        class Project(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()
            settings = clearskies.columns.HasOne(
                ProjectSetting,
                foreign_column_name="gitlab_project_id",
                readable_child_column_names=["visibility"],
            )

        def test_has_one_no_child(projects: Project):
            project = projects.create({"name": "My Project"})
            return project

        context = clearskies.contexts.Context(
            clearskies.endpoints.Callable(
                test_has_one_no_child,
                model_class=Project,
                readable_column_names=["id", "name", "settings"],
            ),
            classes=[Project, ProjectSetting],
        )
        status_code, response_data, response_headers = context()
        assert response_data["status"] == "success"
        data = response_data["data"]
        assert data["settings"] is None

    def test_has_one_with_restful_api_get(self):
        """Test HasOne serialization through a Get endpoint.

        This reproduces the bug where HasOne inherited to_json from HasMany, which tried
        to iterate over a single model record (causing a ValueError about querying an individual record).
        """

        class ProjectSetting(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            project_id = clearskies.columns.String()
            visibility = clearskies.columns.String()
            merge_method = clearskies.columns.String()

        class Project(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()
            settings = clearskies.columns.HasOne(
                ProjectSetting,
                foreign_column_name="project_id",
                readable_child_column_names=["visibility", "merge_method"],
            )

        def setup_data(projects: Project, project_settings: ProjectSetting):
            project = projects.create({"name": "Test Project"})
            project_settings.create(
                {
                    "project_id": project.id,
                    "visibility": "internal",
                    "merge_method": "rebase_merge",
                }
            )
            return project.id

        # First create the data
        setup_context = clearskies.contexts.Context(
            clearskies.endpoints.Callable(setup_data),
            classes=[Project, ProjectSetting],
        )
        _, setup_response, _ = setup_context()
        project_id = setup_response["data"]

        # Now test the Get endpoint via URL routing
        context = clearskies.contexts.Context(
            clearskies.endpoints.Get(
                url="/{id}",
                model_class=Project,
                readable_column_names=["id", "name", "settings"],
            ),
            classes=[Project, ProjectSetting],
        )
        status_code, response_data, response_headers = context(
            url=f"/{project_id}",
        )
        assert status_code == 200
        assert response_data["status"] == "success"
        data = response_data["data"]
        assert isinstance(data["settings"], dict)
        assert data["settings"]["visibility"] == "internal"
        assert data["settings"]["merge_method"] == "rebase_merge"

    def test_has_one_set_raises_error(self):
        """Test that setting a HasOne column raises a ValueError with correct message."""

        class ProjectSetting(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            project_id = clearskies.columns.String()
            visibility = clearskies.columns.String()

        class Project(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()
            settings = clearskies.columns.HasOne(
                ProjectSetting,
                foreign_column_name="project_id",
            )

        def attempt_set(projects: Project):
            project = projects.create({"name": "Test"})
            project.settings = "something"

        context = clearskies.contexts.Context(
            clearskies.endpoints.Callable(attempt_set),
            classes=[Project, ProjectSetting],
        )
        with self.assertRaises(ValueError) as cm:
            context()
        assert "HasOne" in str(cm.exception)
        assert "HasMany" not in str(cm.exception)

    def test_has_one_with_where_conditions(self):
        """Test HasOne with additional where conditions to filter the child."""

        class ProjectSetting(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            project_id = clearskies.columns.String()
            visibility = clearskies.columns.String()
            is_active = clearskies.columns.Boolean()

        class Project(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()
            active_setting = clearskies.columns.HasOne(
                ProjectSetting,
                foreign_column_name="project_id",
                readable_child_column_names=["visibility", "is_active"],
                where="is_active=1",
            )

        def test_where(projects: Project, project_settings: ProjectSetting):
            project = projects.create({"name": "My Project"})
            # Create an inactive setting
            project_settings.create(
                {
                    "project_id": project.id,
                    "visibility": "private",
                    "is_active": False,
                }
            )
            # Create an active setting
            project_settings.create(
                {
                    "project_id": project.id,
                    "visibility": "public",
                    "is_active": True,
                }
            )

            setting = project.active_setting
            return {"visibility": setting.visibility, "is_active": setting.is_active}

        context = clearskies.contexts.Context(
            clearskies.endpoints.Callable(test_where),
            classes=[Project, ProjectSetting],
        )
        status_code, response_data, response_headers = context()
        assert response_data["status"] == "success"
        assert response_data["data"]["visibility"] == "public"
        assert response_data["data"]["is_active"] is True

    def test_has_one_documentation_returns_object_not_array(self):
        """Test that HasOne.documentation() returns an AutoDocObject, not an AutoDocArray."""

        class ProjectSetting(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            project_id = clearskies.columns.String()
            visibility = clearskies.columns.String()

        class Project(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()
            settings = clearskies.columns.HasOne(
                ProjectSetting,
                foreign_column_name="project_id",
                readable_child_column_names=["visibility"],
            )

        # Trigger column finalization
        columns = Project.get_columns()
        settings_column = columns["settings"]

        docs = settings_column.documentation()
        assert len(docs) == 1
        assert isinstance(docs[0], AutoDocObject)
        assert docs[0].name == "settings"
