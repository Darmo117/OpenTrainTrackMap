"""This module defines the handler for the logout page."""
from __future__ import annotations

from django.http import response as _dj_response

from . import _ottm_handler
from ..api import auth as _auth


class LogoutPageHandler(_ottm_handler.OTTMHandler):
    """Handler for the logout page."""

    def handle_request(self) -> _dj_response.HttpResponse:
        if _auth.get_user_from_request(self._request_params.request).is_authenticated:
            _auth.log_out(self._request_params.request)
        return self.redirect(self._request_params.return_to)
