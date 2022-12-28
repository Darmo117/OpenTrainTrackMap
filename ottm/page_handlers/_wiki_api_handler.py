"""This module defines a page handler class for the wiki API."""
import json as _json

from django.http import response as _dj_response

from . import _core
from ..api.wiki import pages as _pages, constants as _w_cons


class WikiAPIHandler(_core.PageHandler):
    """Handler for the wiki API."""

    def handle_request(self) -> _dj_response.HttpResponse:
        match self._request_params.get.get('action'):
            case 'query':
                return self._query_action()
            case action:
                return self._bad_request(f'invalid "action" parameter value: {action}')

    def _query_action(self) -> _dj_response.HttpResponse:
        """``action=query``"""
        match self._request_params.get.get('query'):
            case ('static' | 'gadget') as resource_type:
                return self._query_static_resource(resource_type)
            case action:
                return self._bad_request(f'invalid "query" parameter value: {action}')

    def _query_static_resource(self, resource_type: str) -> _dj_response.HttpResponse:
        """``action=query&query=(static|gadget)``"""
        page_title = self._request_params.get.get('title')
        if not page_title:
            return self._bad_request('missing "title" parameter')
        page = _pages.get_page(*_pages.split_title(page_title))
        if not page.exists:
            return self._not_found(f'page {page.full_title} does not exist')
        if resource_type == 'static':
            return self.response(page.cached_parsed_content, _w_cons.MIME_TYPES[page.content_type])
        # TODO assemble gadgets’ code
        return self.response(page.cached_parsed_content, _w_cons.MIME_TYPES[page.content_type])

    @staticmethod
    def _not_found(message: str) -> _dj_response.HttpResponseNotFound:
        return _dj_response.HttpResponseNotFound(
            _json.dumps({'error': message, 'error_type': 'not found'}),
            content_type='application/json',
        )

    @staticmethod
    def _bad_request(message: str) -> _dj_response.HttpResponseBadRequest:
        return _dj_response.HttpResponseBadRequest(
            _json.dumps({'error': message, 'error_type': 'bad request'}),
            content_type='application/json',
        )
