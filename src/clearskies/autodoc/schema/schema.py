class Schema:
    name: str
    required = False
    example = None
    value = None
    _type = "string"
    _format = ""
    minimum: float | int | None = None
    maximum: float | int | None = None
    exclusive_minimum: float | int | bool | None = None
    exclusive_maximum: float | int | bool | None = None
    multiple_of: float | int | None = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    min_properties: int | None = None
    max_properties: int | None = None
    additional_properties: bool | dict | None = None
    min_items: int | None = None
    max_items: int | None = None
    unique_items: bool | None = None
    nullable: bool | None = None
    deprecated: bool | None = None
    read_only: bool | None = None
    write_only: bool | None = None
    discriminator: dict | None = None
    xml: dict | None = None
    external_docs: dict | None = None
    examples: dict | list | None = None

    def __init__(self, name, example=None, value=None):
        self.name = name
        self.example = example
        self.value = value
