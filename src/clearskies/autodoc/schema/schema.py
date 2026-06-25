class Schema:
    name: str
    required = False
    example = None
    value = None
    _type = "string"
    _format = ""
    minimum: float | int | None = None
    maximum: float | int | None = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    min_items: int | None = None
    max_items: int | None = None
    unique_items: bool | None = None
    nullable: bool | None = None
    deprecated: bool | None = None

    def __init__(self, name, example=None, value=None):
        self.name = name
        self.example = example
        self.value = value
