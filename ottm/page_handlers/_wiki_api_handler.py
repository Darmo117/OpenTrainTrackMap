"""This module defines a page handler class for the wiki API."""

from django.http import response as _dj_response

from . import _core
from ..api import auth
from ..api.wiki import pages as _pages, constants as _w_cons


class WikiAPIHandler(_core.PageHandler):
    """Handler for the wiki API."""

    def handle_request(self) -> _dj_response.HttpResponse:
        match self._request_params.GET.get('action'):
            case 'query':
                return self._query_action()
            case action:
                return self._bad_request(f'invalid "action" parameter value: {action}')

    def _query_action(self) -> _dj_response.HttpResponse:
        """``action=query``"""
        match self._request_params.GET.get('query'):
            case 'static':
                return self._query_static_resource()
            case 'gadgets':
                return self._query_user_gadgets()
            case 'gadget':
                return self._query_gadget()
            case action:
                return self._bad_request(f'invalid "query" parameter value: {action}')

    def _query_static_resource(self) -> _dj_response.HttpResponse:
        """``action=query&query=static``"""
        page_title = self._request_params.GET.get('title')
        if not page_title:
            return self._bad_request('missing "title" parameter')
        page = _pages.get_page(*_pages.split_title(page_title))
        if not page.exists:
            return self._not_found(f'page {page.full_title} does not exist')
        return self.response(page.cached_parsed_content, _w_cons.MIME_TYPES[page.content_type])

    def _query_user_gadgets(self):
        """``action=query&query=gadgets``"""
        username = self._request_params.GET.get('username')
        if not auth.user_exists(username):
            return _dj_response.JsonResponse(
                {'error': f'no user with name "{username}"'},
                status=404
            )
        gadget_names = []  # TODO query names of all gadgets activated by the user
        return _dj_response.JsonResponse({'gadget_names': gadget_names})

    def _query_gadget(self):
        # TODO assemble gadget code
        return _dj_response.JsonResponse(
            {'error': 'no implemented'},
            status=501
        )

    @staticmethod
    def _not_found(message: str) -> _dj_response.HttpResponse:
        return _dj_response.JsonResponse(
            {'error': message},
            status=404
        )

    @staticmethod
    def _bad_request(message: str) -> _dj_response.HttpResponse:
        return _dj_response.JsonResponse(
            {'error': message},
            status=400
        )
