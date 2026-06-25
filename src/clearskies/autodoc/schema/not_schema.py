from .schema import Schema


class Not(Schema):
    option = None

    def __init__(self, name, option):
        super().__init__(name)
        self.option = option
