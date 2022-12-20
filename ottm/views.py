"""This module defines all page view handlers."""
import typing as _typ

import django.core.handlers.wsgi as _dj_wsgi
import django.http.response as _dj_response
import requests as _requests

from . import page_handlers as _ph


def get_tile(request: _dj_wsgi.WSGIRequest) -> _dj_response.HttpResponse:
    """API view that handles map tile querying.

    Expected GET parameters:
        - provider (str): Name of the tile provider.
        - x (int): Tile’s x position.
        - y (int): Tile’s y position.
        - z (int): Zoom value.
    """
    try:
        x = int(request.GET.get('x'))
        y = int(request.GET.get('y'))
        z = int(request.GET.get('z'))
    except ValueError:
        return _dj_response.HttpResponseBadRequest()
    provider = request.GET.get('provider')
    if provider == 'maptiler':
        url = f'https://api.maptiler.com/tiles/satellite/{z}/{x}/{y}.jpg?key=5PelNcEc4zGc3OEutmIG'
        response = _requests.get(url)
        # Remove Connection header as it may cause issues with Django
        del response.headers['Connection']
        return _dj_response.HttpResponse(response.content, status=response.status_code, headers=response.headers)
    return _dj_response.HttpResponseNotFound(f'invalid provider {provider}')


def map_page(request: _dj_wsgi.WSGIRequest) -> _dj_response.HttpResponse:
    """View for the map."""
    return _ph.MapPageHandler(request, mode=_ph.MapPageHandler.VIEW).handle_request()


def edit_page(request: _dj_wsgi.WSGIRequest) -> _dj_response.HttpResponse:
    """View for the map in edit mode."""
    return _ph.MapPageHandler(request, mode=_ph.MapPageHandler.EDIT).handle_request()


def history_page(request: _dj_wsgi.WSGIRequest) -> _dj_response.HttpResponse:
    """View for the map in history mode."""
    return _ph.MapPageHandler(request, mode=_ph.MapPageHandler.HISTORY).handle_request()


def get_page_handler(page_name: str) -> _typ.Callable[[_dj_wsgi.WSGIRequest], _dj_response.HttpResponse]:
    """Generate a view handler for the given page name.

    :param page_name: Page’s name.
    :return: The view function.
    """
    return lambda request: _ph.DefaultPageHandler(request, page_name).handle_request()


def signup_page(request: _dj_wsgi.WSGIRequest) -> _dj_response.HttpResponse:
    """View for the sign-up page."""
    return _ph.SignUpPageHandler(request).handle_request()


def login_page(request: _dj_wsgi.WSGIRequest) -> _dj_response.HttpResponse:
    """View for the login page."""
    return _ph.LoginPageHandler(request).handle_request()


def logout_page(request: _dj_wsgi.WSGIRequest) -> _dj_response.HttpResponse:
    """View for the logout page."""
    return _ph.LogoutPageHandler(request).handle_request()


def user_profile(request: _dj_wsgi.WSGIRequest, username: str) -> _dj_response.HttpResponse:
    """View for a user’s profile.

    :param request: Client request.
    :param username: Username of the user.
    """
    return _ph.UserProfilePageHandler(request, username).handle_request()


def user_settings(request: _dj_wsgi.WSGIRequest) -> _dj_response.HttpResponse:
    """View for a user’s account settings."""
    return _ph.UserSettingsPageHandler(request).handle_request()


def user_contributions(request: _dj_wsgi.WSGIRequest, username: str) -> _dj_response.HttpResponse:
    """View for a user’s map contributions.

    :param request: Client request.
    :param username: Username of the user.
    """
    return _ph.MapPageHandler(request, mode=_ph.MapPageHandler.CONTRIBUTIONS, username=username).handle_request()


def user_notes(request: _dj_wsgi.WSGIRequest, username: str) -> _dj_response.HttpResponse:
    """View for a user’s notes.

    :param request: Client request.
    :param username: Username of the user.
    """
    return _ph.UserNotesPageHandler(request, username).handle_request()


def wiki_page(request: _dj_wsgi.WSGIRequest, raw_page_title: str = '') -> _dj_response.HttpResponse:
    """View for a wiki page.

    :param request: Client request.
    :param raw_page_title: Title of the wiki page.
    """
    return _ph.WikiPageHandler(request, raw_page_title).handle_request()


def api(request: _dj_wsgi.WSGIRequest):
    """Entry point for the map API."""
    return _dj_response.HttpResponseNotFound()  # TODO


def wiki_api(request: _dj_wsgi.WSGIRequest):
    """Entry point for the wiki API."""
    return _ph.WikiAPIHandler(request).handle_request()


# Parameter 'exception' must have this exact name
# noinspection PyUnusedLocal
def handle404(request: _dj_wsgi.WSGIRequest, exception: Exception) -> _dj_response.HttpResponse:
    """404 error page handler."""
    return _ph.E404Handler(request).handle_request()
