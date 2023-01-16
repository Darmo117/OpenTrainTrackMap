class WikiScriptException(BaseException):
    def __init__(self, message: str, line: int, column: int):
        super().__init__(message)
        self._line = line
        self._column = column

    @property
    def line(self) -> int:
        return self._line

    @property
    def column(self) -> int:
        return self._column
