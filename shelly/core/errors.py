class ParseError(Exception):
    """Raised when a line can't be understood. The message is meant for humans."""

    def __init__(self, message: str, line_number: int | None = None):
        super().__init__(message)
        self.message = message
        self.line_number = line_number

    def __str__(self) -> str:
        if self.line_number is not None:
            return f"Line {self.line_number}: {self.message}"
        return self.message
