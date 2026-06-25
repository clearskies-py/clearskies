from typing import Any


class Parameter:
    name: str = ""
    parameter: Any = None
    required: bool = False
    location_map = {
        "url_parameter": "query",
        "header": "header",
        "url_path": "path",
    }

    def __init__(self, oai3_schema_resolver):
        self.oai3_schema_resolver = oai3_schema_resolver

    def set_parameter(self, parameter):
        self.parameter = parameter
        self.name = self.parameter.definition.name
        self.required = self.parameter.required

    def convert(self):
        if self.parameter.location not in self.location_map:
            raise ValueError(
                f"Parameter of class {self.parameter.__class__} declares "
                + f"an unsupported location: '{self.parameter.location}'"
            )

        # In OpenAPI 3.0, description is recommended but not strictly required
        # Provide a default if missing
        description = self.parameter.description if self.parameter.description else ""

        output = {
            "name": self.parameter.definition.name,
            "description": description,
            "required": self.required,
            "in": self.location_map[self.parameter.location],
        }

        if self.parameter.content is not None:
            output["content"] = self.parameter.content
        else:
            output["schema"] = self.oai3_schema_resolver(self.parameter.definition).convert()

        if self.parameter.style is not None:
            output["style"] = self.parameter.style
        if self.parameter.explode is not None:
            output["explode"] = self.parameter.explode
        if self.parameter.allow_reserved is not None:
            output["allowReserved"] = self.parameter.allow_reserved
        if self.parameter.deprecated is not None:
            output["deprecated"] = self.parameter.deprecated
        if self.parameter.allow_empty_value is not None:
            output["allowEmptyValue"] = self.parameter.allow_empty_value
        if self.parameter.example is not None:
            output["example"] = self.parameter.example
        if self.parameter.examples is not None:
            output["examples"] = self.parameter.examples

        return output
