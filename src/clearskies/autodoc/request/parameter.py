class Parameter:
    location = ""
    in_body = False

    def __init__(
        self,
        definition,
        description="",
        required=False,
        style=None,
        explode=None,
        allow_reserved=None,
        deprecated=None,
        allow_empty_value=None,
        example=None,
        examples=None,
        content=None,
    ):
        self.definition = definition
        self.description = description
        self.required = required
        self.style = style
        self.explode = explode
        self.allow_reserved = allow_reserved
        self.deprecated = deprecated
        self.allow_empty_value = allow_empty_value
        self.example = example
        self.examples = examples
        self.content = content
