from __future__ import annotations

from typing import Any


def schema_example(schema: Any) -> Any:
    if schema is None:
        return None

    example = getattr(schema, "example", None)
    if example is not None:
        return example

    value = getattr(schema, "value", None)
    if value is not None:
        return value

    schema_type = getattr(schema, "_type", "")
    schema_format = getattr(schema, "_format", "")
    name = getattr(schema, "name", "value")

    if schema_type == "object":
        children = getattr(schema, "children", None) or []
        return {child.name: schema_example(child) for child in children}

    if schema_type == "array":
        item = getattr(schema, "item_definition", None)
        return [schema_example(item)]

    options = getattr(schema, "options", None)
    if options:
        return schema_example(options[0])

    option = getattr(schema, "option", None)
    if option is not None:
        return schema_example(option)

    values = getattr(schema, "values", None)
    if values:
        return values[0]

    if schema_type == "boolean":
        return True
    if schema_type == "integer":
        return 1
    if schema_type == "number":
        return 1.5
    if schema_type == "string":
        lowered_name = str(name).lower()
        if schema_format == "date-time":
            return "2026-01-01T00:00:00Z"
        if schema_format == "date":
            return "2026-01-01"
        if schema_format == "password":
            return "example-password"
        if "email" in lowered_name:
            return "user@example.com"
        if "phone" in lowered_name:
            return "+12025550123"
        if lowered_name in ("id", "uuid") or lowered_name.endswith("_id"):
            return "00000000-0000-0000-0000-000000000001"
        return "example-text"

    return "example-value"
