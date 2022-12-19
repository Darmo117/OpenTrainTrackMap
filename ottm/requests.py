"""This modules defines the RequestParams class, which is a wrapper around a WSGIRequest object."""
import django.core.handlers.wsgi as dj_wsgi

from . import models, settings
from .api import auth, utils
from .api.wiki import constants as w_cons


class RequestParams:
    """Object containing the given request’s parameters."""

    MIN_RESULTS_PER_PAGE = 20
    MAX_RESULTS_PER_PAGE = 500
    DEFAULT_RESULTS_PER_PAGE = 50

    def __init__(self, request: dj_wsgi.WSGIRequest):
        get_params = request.GET
        self._request = request
        self._user = auth.get_user_from_request(request)
        self._language = self._get_page_language(request, self._user)
        self._dark_mode = self._get_dark_mode_status(request, self._user)
        self._return_to = get_params.get('return_to', '/')
        self._wiki_action = get_params.get('action', w_cons.ACTION_READ)
        if self._wiki_action not in w_cons.ACTIONS.values():
            self._wiki_action = w_cons.ACTION_READ
        self._results_per_page = self._get_results_per_page(get_params)
        self._page_index = self._get_page_index(get_params)
        self._get_params = get_params
        self._post_params = request.POST
        self._cookies = request.COOKIES

    @property
    def request(self) -> dj_wsgi.WSGIRequest:
        return self._request

    @property
    def user(self) -> models.User:
        return self._user

    @property
    def ui_language(self) -> settings.UILanguage:
        return self._language

    @property
    def dark_mode(self) -> bool:
        return self._dark_mode

    @property
    def return_to(self) -> str:
        return self._return_to

    @property
    def wiki_action(self) -> str:
        return self._wiki_action

    @property
    def results_per_page(self) -> int:
        return self._results_per_page

    @property
    def page_index(self) -> int:
        return self._page_index

    @property
    def get(self) -> dj_wsgi.QueryDict:
        return self._get_params

    @property
    def post(self) -> dj_wsgi.QueryDict:
        return self._post_params

    @property
    def cookies(self) -> dict[str, str]:
        return self._cookies

    @staticmethod
    def _get_page_language(request: dj_wsgi.WSGIRequest, user: models.User) -> settings.UILanguage:
        """Return the language for the page.

        :param request: Client request.
        :param user: Current user.
        :return: Page’s language.
        """
        # GET params have priority
        if (lang_code := request.GET.get('lang')) and lang_code in settings.LANGUAGES:
            return settings.LANGUAGES[lang_code]
        if (not user.is_authenticated  # Cookie only used for logged out users
                and (lang_code := request.COOKIES.get('language'))
                and lang_code in settings.LANGUAGES):
            return settings.LANGUAGES[lang_code]
        return user.preferred_language

    @staticmethod
    def _get_dark_mode_status(request: dj_wsgi.WSGIRequest, user: models.User) -> bool:
        """Return the dark mode status for the page.

        :param request: Client request.
        :param user: Current user.
        :return: True if the dark mode should be active, false otherwise.
        """
        # GET params have priority
        if (dark_mode := request.GET.get('dark_mode')) and dark_mode and dark_mode.isascii() and dark_mode.isnumeric():
            return bool(int(dark_mode))
        if not user.is_authenticated and 'dark_mode' in request.COOKIES:  # Cookie only used for logged out users
            return request.COOKIES['dark_mode'] == 'true'
        return user.uses_dark_mode

    @classmethod
    def _get_results_per_page(cls, get_params: dj_wsgi.QueryDict) -> int:
        if 'results_per_page' in get_params:
            try:
                return utils.clamp(int(get_params.get('results_per_page', cls.DEFAULT_RESULTS_PER_PAGE)),
                                   cls.MIN_RESULTS_PER_PAGE, cls.MAX_RESULTS_PER_PAGE)
            except ValueError:
                pass
        return cls.DEFAULT_RESULTS_PER_PAGE

    @staticmethod
    def _get_page_index(get_params: dj_wsgi.QueryDict) -> int:
        if 'page' in get_params:
            try:
                return utils.clamp(int(get_params.get('page', 1)), 1)
            except ValueError:
                pass
        return 1
