from .parameter import Parameter


class JSONBody(Parameter):
    location = "json_body"
    in_body = True

    def __init__(
        self,
        definition,
        description="",
        required=False,
        content_type="application/json",
        documentation_example=None,
        documentation_examples=None,
    ):
        super().__init__(
            definition=definition,
            description=description,
            required=required,
            documentation_example=documentation_example,
            documentation_examples=documentation_examples,
        )
        self.content_type = content_type
