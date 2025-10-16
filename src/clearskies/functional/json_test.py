import pytest
from clearskies.functional.json import get_nested_attribute


def test_get_nested_attribute_with_dict():
    data = {"level1": {"level2": {"level3": "value"}}}
    assert get_nested_attribute(data, "level1.level2.level3") == "value"


def test_get_nested_attribute_with_json_string():
    json_string = '{"level1": {"level2": {"level3": "value"}}}'
    assert get_nested_attribute(json_string, "level1.level2.level3") == "value"


def test_get_nested_attribute_key_error():
    data = {"level1": {"level2": {}}}
    with pytest.raises(KeyError):
        get_nested_attribute(data, "level1.level2.level3")


def test_get_nested_attribute_value_error():
    invalid_json = "{not valid json}"
    with pytest.raises(ValueError):
        get_nested_attribute(invalid_json, "any.path")
