"""This module defines the handler for pages displaying the map."""
from __future__ import annotations

import json as _json
import typing as _typ

import django.core.handlers.wsgi as _dj_wsgi
from django.http import response as _dj_response

from . import _core, _ottm_handler
from .. import requests as _requests


class MapPageHandler(_ottm_handler.OTTMHandler):
    """Handler class for map pages."""
    VIEW = 'show'
    EDIT = 'edit'
    HISTORY = 'history'
    CONTRIBUTIONS = 'contributions'

    def __init__(self, request: _dj_wsgi.WSGIRequest, mode: str, username: str = None):
        """Create a handler for a map page.

        :param request: Client request.
        :param mode: Map display mode.
        :param username: If in contribution mode, the username of the user to display the contributions of.
        """
        super().__init__(request)
        self._mode = mode
        self._username = username

    def handle_request(self) -> _dj_response.HttpResponse:
        if self._mode == self.EDIT and not self._request_params.user.is_authenticated:
            return self.redirect('ottm:log_in', reverse=True, get_params={
                'return_to': self._request_params.request.path,
                'edit_warning': 1,
            })

        js_config = {
            'edit': self._mode == self.EDIT,
        }

        args = {'username': self._username} if self._mode == self.CONTRIBUTIONS else {}
        if self._mode != self.VIEW:
            tab_title = self.get_page_titles(page_id=self._mode, titles_args=args)[1]
        else:
            tab_title = None
        return self.render_page('ottm/map.html', MapPageContext(
            self._request_params,
            tab_title=tab_title,
            no_index=self._mode != self.VIEW,
            map_js_config=js_config,
        ))


class MapPageContext(_core.PageContext):
    """Context class for map pages."""

    def __init__(
            self,
            request_params: _requests.RequestParams,
            tab_title: str | None,
            no_index: bool,
            map_js_config: dict[str, _typ.Any],
    ):
        """Create a page context for a map page.

        :param request_params: Page request parameters.
        :param tab_title: Title of the browser’s tab.
        :param no_index: Whether to insert a noindex clause within the HTML page.
        :param map_js_config: Dict object containing map’s JS config.
            It is converted to a JSON object before being inserted in the HTML page.
        """
        super().__init__(
            request_params,
            tab_title=tab_title,
            title=None,
            no_index=no_index,
        )
        self._map_js_config = _json.dumps(map_js_config)

    @property
    def map_js_config(self) -> str:
        return self._map_js_config
