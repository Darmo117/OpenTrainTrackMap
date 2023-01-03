"""This module defines all custom excetions."""


class InvalidUsernameError(ValueError):
    pass


class DuplicateUsernameError(ValueError):
    pass


class InvalidPasswordError(ValueError):
    pass


class InvalidEmailError(ValueError):
    pass


class PageDoesNotExistError(RuntimeError):
    pass


class TitleAlreadyExistsError(RuntimeError):
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


class EditSpecialPageError(RuntimeError):
    pass


class ProtectSpecialPageError(RuntimeError):
    pass


class DeleteSpecialPageError(RuntimeError):
    pass


class RenameSpecialPageError(RuntimeError):
    pass


class FollowSpecialPageError(RuntimeError):
    pass


class AnonymousFollowPageError(RuntimeError):
    pass


class NotACategoryPageError(RuntimeError):
    pass


class AnonymousEditGroupsError(RuntimeError):
    pass


class AnonymousMaskUsernameError(RuntimeError):
    pass


class EditGroupsError(RuntimeError):
    pass


class PastDateError(RuntimeError):
    pass


class CannotEditPageError(RuntimeError):
    pass
