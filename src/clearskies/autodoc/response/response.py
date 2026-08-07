from clearskies.autodoc import examples


class Response:
    status = None
    schema = None
    description = None
    headers = None
    links = None
    content = None

    def __init__(
        self,
        status,
        schema,
        description=None,
        headers=None,
        links=None,
        content=None,
        documentation_example=None,
        documentation_examples=None,
    ):
        self.status = status
        self.schema = schema
        self.description = description if description is not None else ""
        self.headers = headers if headers is not None else {}
        self.links = links if links is not None else {}
        if content is None:
            content = {
                "application/json": {
                    "schema": schema,
                }
            }

        for media_type, media_data in content.items():
            if "example" not in media_data:
                if documentation_example is not None:
                    media_data["example"] = documentation_example
                else:
                    media_data["example"] = examples.schema_example(schema)
            if documentation_examples is not None and "examples" not in media_data:
                media_data["examples"] = documentation_examples

        self.content = content
