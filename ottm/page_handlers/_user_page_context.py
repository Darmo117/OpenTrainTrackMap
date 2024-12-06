"""This module defines the bage page context class for user pages."""
from . import _core
from .. import data_model as _models, requests as _requests


class UserPageContext(_core.PageContext):
    """Base class for user page context classes."""

    def __init__(
            self,
            request_params: _requests.RequestParams,
            tab_title: str | None,
            title: str | None,
            target_user: _models.User,
    ):
        """Create a page context for a user’s page.

        :param request_params: Page request parameters.
        :param tab_title: Title of the browser’s tab.
        :param title: Page’s title.
        :param target_user: User of the requested page.
        """
        super().__init__(
            request_params,
            tab_title=tab_title,
            title=title,
            no_index=False,
        )
        self._target_user = target_user

    @property
    def target_user(self) -> _models.User:
        return self._target_user
