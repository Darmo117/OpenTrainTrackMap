"""This module defines the handler for user profile pages."""
from __future__ import annotations

import django.core.handlers.wsgi as _dj_wsgi
from django.http import response as _dj_response

from . import _ottm_handler, _user_page_context
from ..api import auth as _auth


class UserProfilePageHandler(_ottm_handler.OTTMHandler):
    """Handler for user profile pages."""

    def __init__(self, request: _dj_wsgi.WSGIRequest, username: str):
        """Create a handler for the given user’s profile page.

        :param request: Client request.
        :param username: Username of the target user.
        """
        super().__init__(request)
        self._username = username

    def handle_request(self) -> _dj_response.HttpResponse:
        target_user = _auth.get_user_from_name(self._username)
        title, tab_title = self.get_page_titles(page_id='user_profile', titles_args={'username': target_user.username})
        return self.render_page(f'ottm/user-profile.html', _user_page_context.UserPageContext(
            self._request_params,
            tab_title,
            title,
            target_user=target_user,
        ))
