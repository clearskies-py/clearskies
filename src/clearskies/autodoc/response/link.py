class Link:
    operation_id = ""
    operation_ref = ""
    description = ""
    parameters = None

    def __init__(self, operation_id="", operation_ref="", description="", parameters=None):
        self.operation_id = operation_id
        self.operation_ref = operation_ref
        self.description = description
        self.parameters = parameters if parameters is not None else {}
