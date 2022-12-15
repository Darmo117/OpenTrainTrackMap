"""This module defines the handler for user notes pages."""
from __future__ import annotations

import django.core.handlers.wsgi as _dj_wsgi
from django.http import response as _dj_response

from . import _ottm_handler, _user_page_context
from .. import models as _models, requests as _requests
from ..api import auth as _auth


class UserNotesPageHandler(_ottm_handler.OTTMHandler):
    """Handler for user notes pages."""

    def __init__(self, request: _dj_wsgi.WSGIRequest, username: str):
        """Create a handler for the given user’s notes page.

        :param request: Client request.
        :param username: Username of the target user.
        """
        super().__init__(request)
        self._username = username

    def handle_request(self) -> _dj_response.HttpResponse:
        target_user = _auth.get_user_from_name(self._username)
        title, tab_title = self.get_page_titles(page_id='user_notes', titles_args={'username': target_user.username})
        return self.render_page(f'ottm/user-notes.html', UserNotesPageContext(
            self._request_params,
            title,
            tab_title,
            target_user=target_user,
        ))


class UserNotesPageContext(_user_page_context.UserPageContext):
    """Context class for user notes pages."""

    def __init__(
            self,
            request_params: _requests.RequestParams,
            tab_title: str,
            title: str,
            target_user: _models.User,
    ):
        """Create a page context for a user’s notes page.

        :param request_params: Page request parameters.
        :param tab_title: Title of the browser’s tab.
        :param title: Page’s title.
        :param target_user: User of the requested page.
        """
        super().__init__(
            request_params,
            tab_title=tab_title,
            title=title,
            target_user=target_user,
        )
