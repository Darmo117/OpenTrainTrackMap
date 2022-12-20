"""This module defines a page handler class for the 404 page."""
import django.core.handlers.wsgi as _dj_wsgi
from django.http import response as _dj_response

from . import _core, _ottm_handler
from .. import requests as _requests


class E404Handler(_ottm_handler.OTTMHandler):
    """Class for the 404 handler."""

    def __init__(self, request: _dj_wsgi.WSGIRequest):
        super().__init__(request)

    def handle_request(self) -> _dj_response.HttpResponse:
        return self.render_page('ottm/404.html', E404PageContext(self._request_params))


class E404PageContext(_core.PageContext):
    """Context class for the 404 page."""

    def __init__(self, request_params: _requests.RequestParams):
        """Create a page context for the 404 page.

        :param request_params: Page request parameters.
        """
        language = request_params.ui_language
        title = language.translate('page.error.404.title')
        tab_title = language.translate('page.error.404.tab_title')
        super().__init__(
            request_params,
            tab_title=tab_title,
            title=title,
            no_index=True,
        )
        self._path = request_params.request.path

    @property
    def path(self) -> str:
        return self._path
