class DSLError(Exception):
    pass


class DSLParseError(DSLError):
    def __init__(self, message: str, line: int | None = None, column: int | None = None) -> None:
        self.line = line
        self.column = column
        if line is not None and column is not None:
            msg = f"line {line}, col {column}: {message}"
        elif line is not None:
            msg = f"line {line}: {message}"
        else:
            msg = message
        super().__init__(msg)


class DSLValidationError(DSLError):
    pass
