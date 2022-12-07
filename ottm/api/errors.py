"""This module defines all custom excetions."""


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
        """Create a permission error.

        :param missing_perms: List of permissions the user is missing.
        """
        self._missing_perms = missing_perms

    @property
    def missing_perms(self) -> tuple[str]:
        """List of permissions the user is missing."""
        return self._missing_perms


class ConcurrentWikiEditError(RuntimeError):
    pass
