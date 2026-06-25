from .schema import Schema


class AnyOf(Schema):
    options = None

    def __init__(self, name, options):
        super().__init__(name)
        self.options = options
