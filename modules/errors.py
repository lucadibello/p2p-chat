type ErrorFields = list[tuple[str, str]]


class ValidationError(Exception):
    def __init__(self, message: str, fields: ErrorFields = []):
        self.message = message
        self.fields = fields
        super().__init__(self.message)
