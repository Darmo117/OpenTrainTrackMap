"""This module defines a default page handler."""
from __future__ import annotations

import django.core.handlers.wsgi as _dj_wsgi
from django.http import response as _dj_response

from . import _core, _ottm_handler


class DefaultPageHandler(_ottm_handler.OTTMHandler):
    """Default page handler. Does nothing more than rendering the given page template."""

    def __init__(self, request: _dj_wsgi.WSGIRequest, page_id: str):
        """Create a handler for the given page.

        :param request: Client request.
        :param page_id: ID of the page to handle.
        """
        super().__init__(request)
        self._page_id = page_id

    def handle_request(self) -> _dj_response.HttpResponse:
        title, tab_title = self.get_page_titles(page_id=self._page_id)
        return self.render_page(f'ottm/{self._page_id}.html', _core.PageContext(
            self._request_params,
            title,
            tab_title,
            no_index=False,
        ))
