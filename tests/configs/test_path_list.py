import tempfile
import unittest
from pathlib import Path

import clearskies.decorators
from clearskies import Configurable, configs


class HasPathList(Configurable):
    my_paths = configs.PathList(default=[".", ".."])

    @clearskies.decorators.parameters_to_properties
    def __init__(self, my_paths=None):
        self.finalize_and_validate_configuration()


class HasPathListRequired(Configurable):
    my_paths = configs.PathList(required=True)

    @clearskies.decorators.parameters_to_properties
    def __init__(self, my_paths=None):
        self.finalize_and_validate_configuration()


class PathListTest(unittest.TestCase):
    def test_accepts_string_items(self):
        instance = HasPathList(["."])
        assert instance.my_paths == [Path(".")]

    def test_accepts_path_items(self):
        instance = HasPathList([Path(".")])
        assert instance.my_paths == [Path(".")]

    def test_converts_strings_to_paths(self):
        instance = HasPathList(["."])
        assert isinstance(instance.my_paths[0], Path)

    def test_raises_type_error_for_non_list(self):
        with self.assertRaises(TypeError) as context:
            HasPathList("not_a_list")
        assert "expected a list" in str(context.exception)

    def test_raises_type_error_for_invalid_item_type(self):
        with self.assertRaises(TypeError) as context:
            HasPathList([42])
        assert "item #1 must be a str or Path" in str(context.exception)

    def test_default_returns_existing_paths(self):
        instance = HasPathList()
        paths = instance.my_paths
        # "." and ".." both exist
        assert len(paths) == 2
        assert Path(".") in paths
        assert Path("..") in paths

    def test_silently_skips_nonexistent_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            existing = Path(tmpdir)
            nonexistent = Path(tmpdir) / "does_not_exist"

            instance = HasPathList([str(existing), str(nonexistent)])
            assert instance.my_paths == [existing]

    def test_returns_empty_list_when_all_missing(self):
        instance = HasPathList(["/this/does/not/exist/at/all"])
        assert instance.my_paths == []

    def test_accepts_mixed_str_and_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            instance = HasPathList([".", Path(tmpdir)])
            assert Path(".") in instance.my_paths
            assert Path(tmpdir) in instance.my_paths

    def test_required_raises_when_missing(self):
        with self.assertRaises(ValueError) as context:
            HasPathListRequired()
        assert "my_paths" in str(context.exception)
