class Default:
    def __init__(self, schema):
        self.schema = schema

    def convert(self):
        schema = {"type": self.schema._type}

        if self.schema._format:
            schema["format"] = self.schema._format

        # Add description if available
        if hasattr(self.schema, "description") and self.schema.description:
            schema["description"] = self.schema.description

        # Add example if available (prefer 'example' over 'value')
        if hasattr(self.schema, "example") and self.schema.example:
            schema["example"] = self.schema.example
        elif hasattr(self.schema, "value") and self.schema.value:
            schema["example"] = self.schema.value

        # Add nullable if the schema supports it
        if hasattr(self.schema, "nullable") and self.schema.nullable:
            schema["nullable"] = True

        return schema
