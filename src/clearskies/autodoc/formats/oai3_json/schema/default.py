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

        if hasattr(self.schema, "minimum") and self.schema.minimum is not None:
            schema["minimum"] = self.schema.minimum
        if hasattr(self.schema, "maximum") and self.schema.maximum is not None:
            schema["maximum"] = self.schema.maximum
        if hasattr(self.schema, "min_length") and self.schema.min_length is not None:
            schema["minLength"] = self.schema.min_length
        if hasattr(self.schema, "max_length") and self.schema.max_length is not None:
            schema["maxLength"] = self.schema.max_length
        if hasattr(self.schema, "pattern") and self.schema.pattern:
            schema["pattern"] = self.schema.pattern
        if hasattr(self.schema, "deprecated") and self.schema.deprecated is not None:
            schema["deprecated"] = self.schema.deprecated

        return schema
