class InvalidUsernameError(ValueError):
    pass


class DuplicateUsernameError(ValueError):
    pass


class InvalidPasswordError(ValueError):
    pass


class InvalidEmailError(ValueError):
    pass


class MissingPermissionError(RuntimeError):
    def __init__(self, *missing_perms: str):
        self._missing_perms = missing_perms

    @property
    def missing_perms(self) -> tuple[str]:
        return self._missing_perms


class ConcurrentWikiEditError(RuntimeError):
    pass
