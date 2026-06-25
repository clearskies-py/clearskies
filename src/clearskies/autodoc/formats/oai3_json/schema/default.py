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

        if hasattr(self.schema, "examples") and self.schema.examples is not None:
            schema["examples"] = self.schema.examples

        # Add nullable if the schema supports it
        if hasattr(self.schema, "nullable") and self.schema.nullable:
            schema["nullable"] = True

        if hasattr(self.schema, "minimum") and self.schema.minimum is not None:
            schema["minimum"] = self.schema.minimum
        if hasattr(self.schema, "maximum") and self.schema.maximum is not None:
            schema["maximum"] = self.schema.maximum
        if hasattr(self.schema, "exclusive_minimum") and self.schema.exclusive_minimum is not None:
            schema["exclusiveMinimum"] = self.schema.exclusive_minimum
        if hasattr(self.schema, "exclusive_maximum") and self.schema.exclusive_maximum is not None:
            schema["exclusiveMaximum"] = self.schema.exclusive_maximum
        if hasattr(self.schema, "multiple_of") and self.schema.multiple_of is not None:
            schema["multipleOf"] = self.schema.multiple_of
        if hasattr(self.schema, "min_length") and self.schema.min_length is not None:
            schema["minLength"] = self.schema.min_length
        if hasattr(self.schema, "max_length") and self.schema.max_length is not None:
            schema["maxLength"] = self.schema.max_length
        if hasattr(self.schema, "pattern") and self.schema.pattern:
            schema["pattern"] = self.schema.pattern
        if hasattr(self.schema, "min_properties") and self.schema.min_properties is not None:
            schema["minProperties"] = self.schema.min_properties
        if hasattr(self.schema, "max_properties") and self.schema.max_properties is not None:
            schema["maxProperties"] = self.schema.max_properties
        if hasattr(self.schema, "additional_properties") and self.schema.additional_properties is not None:
            schema["additionalProperties"] = self.schema.additional_properties
        if hasattr(self.schema, "deprecated") and self.schema.deprecated is not None:
            schema["deprecated"] = self.schema.deprecated
        if hasattr(self.schema, "read_only") and self.schema.read_only is not None:
            schema["readOnly"] = self.schema.read_only
        if hasattr(self.schema, "write_only") and self.schema.write_only is not None:
            schema["writeOnly"] = self.schema.write_only
        if hasattr(self.schema, "discriminator") and self.schema.discriminator is not None:
            schema["discriminator"] = self.schema.discriminator
        if hasattr(self.schema, "xml") and self.schema.xml is not None:
            schema["xml"] = self.schema.xml
        if hasattr(self.schema, "external_docs") and self.schema.external_docs is not None:
            schema["externalDocs"] = self.schema.external_docs

        return schema
