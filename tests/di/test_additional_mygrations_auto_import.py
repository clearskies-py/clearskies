import os
import tempfile
import unittest
from pathlib import Path

from clearskies.di import AdditionalMygrationsAutoImport, Di


class TestAdditionalMygrationsAutoImport(unittest.TestCase):
    # -------------------------------------------------------------------------
    # Base class sql_paths() behaviour
    # -------------------------------------------------------------------------

    def test_sql_paths_returns_empty_when_default_sql_folder_missing(self):
        """Default sql_dir=["sql"] resolves relative to the subclass module file, skips if missing."""

        class MyMigrations(AdditionalMygrationsAutoImport):
            pass

        instance = MyMigrations()
        # The subclass is defined HERE in this test file, so abs path is this dir / "sql"
        # which almost certainly does not exist.
        paths = instance.sql_paths()
        assert paths == []

    def test_sql_paths_returns_path_when_folder_exists(self):
        """sql_dir resolves to subclass dir/sql when that dir exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = os.path.join(tmpdir, "sql")
            os.makedirs(target_dir)

            # sql_paths() resolves relative to the module file of self.__class__
            # which is THIS file.  So we test with an absolute path instead.
            instance = AdditionalMygrationsAutoImport(sql_dir=[target_dir])
            assert instance.sql_paths() == [target_dir]

    def test_sql_paths_resolves_absolute_paths_unchanged(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            instance = AdditionalMygrationsAutoImport(sql_dir=[tmpdir])
            assert instance.sql_paths() == [tmpdir]

    def test_sql_paths_silently_skips_nonexistent(self):
        instance = AdditionalMygrationsAutoImport(sql_dir=["/this/path/absolutely/does/not/exist"])
        assert instance.sql_paths() == []

    # -------------------------------------------------------------------------
    # get_base_dir() behaviour
    # -------------------------------------------------------------------------

    def test_get_base_dir_defaults_to_module_file_parent(self):
        """Without explicit base_dir, get_base_dir() returns the directory of this test file."""

        class MyMigrations(AdditionalMygrationsAutoImport):
            pass

        instance = MyMigrations()
        expected = Path(__file__).parent
        assert instance.get_base_dir() == expected

    def test_get_base_dir_uses_explicit_base_dir(self):
        """When base_dir is provided, get_base_dir() returns it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            instance = AdditionalMygrationsAutoImport(base_dir=Path(tmpdir))
            assert instance.get_base_dir() == Path(tmpdir)

    def test_sql_paths_resolves_relative_against_explicit_base_dir(self):
        """Relative sql_dir entries resolve against explicit base_dir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sql_folder = os.path.join(tmpdir, "sql")
            os.makedirs(sql_folder)

            instance = AdditionalMygrationsAutoImport(base_dir=Path(tmpdir))
            # Default sql_dir is ["sql"], and tmpdir/sql exists
            paths = instance.sql_paths()
            assert paths == [sql_folder]

    # -------------------------------------------------------------------------
    # Di.add_modules() discovery
    # -------------------------------------------------------------------------

    def test_add_modules_discovers_subclass(self):
        import tests.di.mygrations_module as mygrations_module

        di = Di()
        di.add_modules([mygrations_module])
        # MigrationsWithDefaultSql has no existing sql folder so paths is [] but the
        # config object is still registered.  MigrationsWithCustomSql points at a real dir.
        discovered = di._mygrations_configs
        class_names = [c.__class__.__name__ for c in discovered]
        assert "MigrationsWithCustomSql" in class_names

    def test_add_modules_does_not_instantiate_base_class(self):
        import tests.di.mygrations_module as mygrations_module

        di = Di()
        di.add_modules([mygrations_module])
        for config in di._mygrations_configs:
            assert type(config) is not AdditionalMygrationsAutoImport

    def test_add_modules_raises_for_required_constructor_args(self):
        """A subclass with required constructor args must raise at discovery time."""
        import types

        # Build a synthetic module that contains only the bad class.
        bad_module = types.ModuleType("bad_module")
        bad_module.__file__ = __file__  # give it a real __file__ so Di doesn't skip it

        class BadMigrations(AdditionalMygrationsAutoImport):
            def __init__(self, required_arg):
                pass

        bad_module.__dict__["BadMigrations"] = BadMigrations

        di = Di()
        with self.assertRaises(ValueError) as context:
            di.add_modules([bad_module])
        assert "auto imported mygrations configs can only have keyword arguments" in str(context.exception)

    # -------------------------------------------------------------------------
    # get_mygrations_sql_paths() dedup and ordering
    # -------------------------------------------------------------------------

    def test_get_mygrations_sql_paths_returns_discovered_paths(self):
        import tests.di.mygrations_module as mygrations_module
        from tests.di.mygrations_module import _custom_sql_dir

        di = Di()
        di.add_modules([mygrations_module])
        paths = di.get_mygrations_sql_paths()
        assert _custom_sql_dir in paths

    def test_get_mygrations_sql_paths_deduplicates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            first = AdditionalMygrationsAutoImport(sql_dir=[tmpdir])
            second = AdditionalMygrationsAutoImport(sql_dir=[tmpdir])

            di = Di()
            di._mygrations_configs = [first, second]
            paths = di.get_mygrations_sql_paths()
            assert paths.count(tmpdir) == 1

    def test_get_mygrations_sql_paths_preserves_order(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_a = os.path.join(tmpdir, "a")
            dir_b = os.path.join(tmpdir, "b")
            os.makedirs(dir_a)
            os.makedirs(dir_b)

            first = AdditionalMygrationsAutoImport(sql_dir=[dir_a])
            second = AdditionalMygrationsAutoImport(sql_dir=[dir_b])

            di = Di()
            di._mygrations_configs = [first, second]
            paths = di.get_mygrations_sql_paths()
            assert paths == [dir_a, dir_b]

    def test_get_mygrations_sql_paths_returns_empty_when_no_configs(self):
        di = Di()
        assert di.get_mygrations_sql_paths() == []

    # -------------------------------------------------------------------------
    # Mygrations endpoint merge behaviour (unit level via Di directly)
    # -------------------------------------------------------------------------

    def test_explicit_sql_wins_dedup_over_auto_import(self):
        """An auto-imported path that is also in the explicit sql list is dropped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_a = os.path.join(tmpdir, "a")
            dir_b = os.path.join(tmpdir, "b")
            os.makedirs(dir_a)
            os.makedirs(dir_b)

            auto = AdditionalMygrationsAutoImport(sql_dir=[dir_a])

            di = Di()
            di._mygrations_configs = [auto]

            auto_paths = di.get_mygrations_sql_paths()
            explicit_sql = [dir_a, dir_b]  # explicit list includes dir_a

            seen: set[str] = set(explicit_sql)
            merged: list[str] = []
            for path in auto_paths:
                if path not in seen:
                    seen.add(path)
                    merged.append(path)
            merged.extend(explicit_sql)

            # dir_a appears only once (in the explicit section at the end)
            assert merged.count(dir_a) == 1
            # dir_a is NOT in the auto-prepend section
            assert merged.index(dir_a) >= len(merged) - len(explicit_sql)

    def test_auto_paths_prepend_before_explicit(self):
        """Unique auto-imported paths appear before the explicit sql list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_auto = os.path.join(tmpdir, "auto")
            dir_explicit = os.path.join(tmpdir, "explicit")
            os.makedirs(dir_auto)
            os.makedirs(dir_explicit)

            auto = AdditionalMygrationsAutoImport(sql_dir=[dir_auto])

            di = Di()
            di._mygrations_configs = [auto]

            auto_paths = di.get_mygrations_sql_paths()
            explicit_sql = [dir_explicit]

            seen: set[str] = set(explicit_sql)
            merged: list[str] = []
            for path in auto_paths:
                if path not in seen:
                    seen.add(path)
                    merged.append(path)
            merged.extend(explicit_sql)

            assert merged == [dir_auto, dir_explicit]

    # -------------------------------------------------------------------------
    # get_mygrations_sql_paths() class name filtering
    # -------------------------------------------------------------------------

    def test_filter_by_class_name_includes_matching(self):
        """Only configs whose class name is in the allow-list contribute paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_a = os.path.join(tmpdir, "a")
            dir_b = os.path.join(tmpdir, "b")
            os.makedirs(dir_a)
            os.makedirs(dir_b)

            class AlphaMigrations(AdditionalMygrationsAutoImport):
                def __init__(self):
                    super().__init__(sql_dir=[dir_a])

            class BetaMigrations(AdditionalMygrationsAutoImport):
                def __init__(self):
                    super().__init__(sql_dir=[dir_b])

            di = Di()
            di._mygrations_configs = [AlphaMigrations(), BetaMigrations()]

            # Only include AlphaMigrations
            paths = di.get_mygrations_sql_paths(["AlphaMigrations"])
            assert paths == [dir_a]

    def test_filter_by_class_name_excludes_non_matching(self):
        """Configs not in the allow-list are excluded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_a = os.path.join(tmpdir, "a")
            os.makedirs(dir_a)

            class AlphaMigrations(AdditionalMygrationsAutoImport):
                def __init__(self):
                    super().__init__(sql_dir=[dir_a])

            di = Di()
            di._mygrations_configs = [AlphaMigrations()]

            paths = di.get_mygrations_sql_paths(["NonExistentClass"])
            assert paths == []

    def test_filter_empty_list_returns_all(self):
        """An empty allow-list means no filtering — all configs contribute."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_a = os.path.join(tmpdir, "a")
            dir_b = os.path.join(tmpdir, "b")
            os.makedirs(dir_a)
            os.makedirs(dir_b)

            class AlphaMigrations(AdditionalMygrationsAutoImport):
                def __init__(self):
                    super().__init__(sql_dir=[dir_a])

            class BetaMigrations(AdditionalMygrationsAutoImport):
                def __init__(self):
                    super().__init__(sql_dir=[dir_b])

            di = Di()
            di._mygrations_configs = [AlphaMigrations(), BetaMigrations()]

            paths = di.get_mygrations_sql_paths([])
            assert paths == [dir_a, dir_b]

    def test_filter_none_returns_all(self):
        """None as allow-list means no filtering — all configs contribute."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_a = os.path.join(tmpdir, "a")
            os.makedirs(dir_a)

            class AlphaMigrations(AdditionalMygrationsAutoImport):
                def __init__(self):
                    super().__init__(sql_dir=[dir_a])

            di = Di()
            di._mygrations_configs = [AlphaMigrations()]

            paths = di.get_mygrations_sql_paths(None)
            assert paths == [dir_a]
