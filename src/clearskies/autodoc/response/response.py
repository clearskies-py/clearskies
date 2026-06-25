class Response:
    status = None
    schema = None
    description = None
    headers = None
    links = None
    content = None

    def __init__(self, status, schema, description=None, headers=None, links=None, content=None):
        self.status = status
        self.schema = schema
        self.description = description if description is not None else ""
        self.headers = headers if headers is not None else {}
        self.links = links if links is not None else {}
        self.content = content if content is not None else {"application/json": {"schema": schema}}
