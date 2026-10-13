class MovedTemporarily(Exception):
    def __init__(self, location):
        super().__init__(location)
        self.location = location
