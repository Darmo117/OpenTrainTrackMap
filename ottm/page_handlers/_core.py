"""This module defines the base page handler and page context classes."""
from __future__ import annotations

import abc as _abc
import typing as _typ
import urllib.parse

import django.core.handlers.wsgi as _dj_wsgi
import django.http.response as _dj_response
import django.shortcuts as _dj_scut

from .. import models as _models, requests as _requests, settings as _settings


class PageHandler(_abc.ABC):
    """Handles a specific WSGI request and returns a HttpResponse object."""

    def __init__(self, request: _dj_wsgi.WSGIRequest):
        """Create a page handler.

        :param request: The request to handle.
        """
        self._request_params = _requests.RequestParams(request)

    @_abc.abstractmethod
    def handle_request(self) -> _dj_response.HttpResponse:
        """Process the request."""
        pass

    # noinspection PyMethodMayBeStatic
    def redirect(self, url: str, /, *, reverse: bool = False, get_params: dict[str, _typ.Any] = None,
                 **kwargs) -> _dj_response.HttpResponseRedirect:
        """Return a HttpResponseRedirect object.

        :param url: URL to redirect to.
        :param reverse: If true, the url is parsed as a Django URL path name.
        :param get_params: Optional GET parameters.
        :param kwargs: Additional parameters for the URL reverse operation.
        :return: A HttpResponseRedirect object.
        """
        if reverse:
            url = _dj_scut.reverse(url, kwargs=kwargs)
        if get_params:
            url += '?' + urllib.parse.urlencode(get_params)
        return _dj_response.HttpResponseRedirect(url)

    def render_page(self, template_name: str, context: PageContext, status: int = None,
                    kwargs: dict[str, _typ.Any] = None) -> _dj_response.HttpResponse:
        """Return a HttpResponse whose content is the rendered HTML of the given template.

        :param template_name: Name of the template to render.
        :param context: PageContext object to pass to the template.
        :param status: Status code.
        :param kwargs: Additonal parameters to pass to the template context.
        :return: A HttpResponse object.
        """
        return _dj_scut.render(
            self._request_params.request,
            template_name,
            context={'context': context, **(kwargs or {})},
            status=status,
        )

    # noinspection PyMethodMayBeStatic
    def response(self, content: str, content_type: str, status: int):
        """Return a HttpResponse object.

        :param content: Response’s content.
        :param content_type: Response’s content type.
        :param status: Response’s status code.
        :return: A HttpResponse object.
        """
        return _dj_response.HttpResponse(content=content, content_type=content_type, status=status)


class PageContext:
    """A page context object contains values meant to be used within HTML templates."""

    def __init__(
            self,
            request_params: _requests.RequestParams,
            tab_title: str | None,
            title: str | None,
            no_index: bool,
            max_page_index: int = None,
    ):
        """Create a generic page context.

        :param request_params: Page request parameters.
        :param tab_title: Title of the browser’s tab.
        :param title: Page’s title.
        :param no_index: Whether to insert a noindex clause within the HTML page.
        :param max_page_index: Maximum page index. May be None if the page does not have pagination.
        """
        self._request_params = request_params
        self._tab_title = tab_title
        self._title = title
        self._no_index = no_index
        self._max_page_index = max_page_index

    @property
    def request_params(self) -> _requests.RequestParams:
        return self._request_params

    @property
    def site_name(self) -> str:
        return _settings.SITE_NAME

    @property
    def tab_title(self) -> str:
        return self._tab_title

    @property
    def title(self) -> str:
        return self._title

    @property
    def no_index(self) -> bool:
        return self._no_index

    @property
    def user(self) -> _models.User:
        return self._request_params.user

    @property
    def language(self) -> _settings.UILanguage:
        return self._request_params.ui_language

    @property
    def ui_languages(self) -> list[_settings.UILanguage]:
        return list(_settings.LANGUAGES.values())

    @property
    def dark_mode(self) -> bool:
        return self._request_params.dark_mode

    @property
    def results_per_page(self) -> int:
        return self._request_params.results_per_page

    @property
    def page_index(self) -> int:
        if self._max_page_index:
            return min(self._request_params.page_index, self._max_page_index)
        return self._request_params.page_index
