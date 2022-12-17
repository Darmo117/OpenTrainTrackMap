"""This module defines the handler for pages displaying the map."""
from __future__ import annotations

import json as _json
import typing as _typ

from django.conf import settings as _dj_settings
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

        translations_keys = [
            'map.controls.layers.standard',
            'map.controls.layers.black_and_white',
            'map.controls.layers.satellite_maptiler',
            'map.controls.layers.satellite_esri',
            'map.controls.zoom_in.tooltip',
            'map.controls.zoom_out.tooltip',
            'map.controls.search.tooltip',
            'map.controls.search.placeholder',
            'map.controls.google_maps_button.tooltip',
            'map.controls.ign_compare_button.label',
            'map.controls.ign_compare_button.tooltip',
            'map.controls.edit.new_marker.tooltip',
            'map.controls.edit.new_line.tooltip',
            'map.controls.edit.new_polygon.tooltip',
        ]
        js_config = {
            'trans': {},
            'static_path': _dj_settings.STATIC_URL,
            'edit': 'true' if self._mode == self.EDIT else 'false',
        }

        for k in translations_keys:
            js_config['trans'][k] = self._request_params.ui_language.translate(k)

        args = {'username': self._username} if self._mode == self.CONTRIBUTIONS else {}
        tab_title = self.get_page_titles(page_id=self._mode, titles_args=args)[1]
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
