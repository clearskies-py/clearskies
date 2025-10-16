from typing import Any, cast


def get_nested_attribute(data: dict[str, Any] | str, attr_path: str) -> Any:
    """
    Extract a nested attribute from JSON data using dot notation.

    This function navigates through a nested JSON structure using a dot-separated path
    to retrieve a specific attribute. If the input is a string, it will attempt to parse
    it as JSON first.

    Example:
    ```
    data = {"database": {"credentials": {"username": "admin", "password": "secret"}}}
    username = get_nested_attribute(data, "database.credentials.username")
    # Returns "admin"
    ```

    Args:
        data: The JSON data as a dictionary or a JSON string
        attr_path: The path to the attribute using dot notation (e.g., "database.username")

    Returns:
        The value at the specified path

    Raises:
        ValueError: If the data cannot be parsed as JSON
        KeyError: If the attribute path doesn't exist in the data
    """
    keys = attr_path.split(".", 1)
    if not isinstance(data, dict):
        try:
            import json

            data = json.loads(data)
        except Exception:
            raise ValueError(f"Could not parse data as JSON to get attribute '{attr_path}'")

    # At this point, we know data is a dictionary
    data_dict = cast(dict[str, Any], data)  # Help type checker understand data is a dict

    if len(keys) == 1:
        if keys[0] not in data_dict:
            raise KeyError(f"Data does not contain attribute '{attr_path}'")
        return data_dict[keys[0]]

    return get_nested_attribute(data_dict[keys[0]], keys[1])
