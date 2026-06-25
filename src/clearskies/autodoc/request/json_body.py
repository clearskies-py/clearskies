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
    ):
        super().__init__(definition=definition, description=description, required=required)
        self.content_type = content_type
