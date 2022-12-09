"""This package defines the wiki’s special pages.
Special pages are pages that are not stored in the database.
They are used to manage the wiki and may require specific permissions.
"""
import abc
import importlib
import os.path
import pathlib
import typing as typ

import django.core.handlers.wsgi as dj_wsgi

from .. import models


class SpecialPage(abc.ABC):
    """Base class for special pages."""

    def __init__(self, name: str, *requires_perms: str, has_custom_css: bool = False, has_custom_js: bool = False,
                 accesskey: str = None):
        """Create a special page.

        :param name: Page’s name.
        :param requires_perms: List of permissions required to access this page.
        :param has_custom_css: Whether this page has custom CSS.
        :param has_custom_js: Whether this page has custom JS.
        :param accesskey: The access key for menu links that point to this page.
        """
        self._name = name
        self._has_custom_css = has_custom_css
        self._has_custom_js = has_custom_js
        self._perms_required = requires_perms
        self._accesskey = accesskey

    @property
    def name(self) -> str:
        """This page’s name."""
        return self._name

    @property
    def has_custom_css(self) -> bool:
        """Whether this page has custom CSS."""
        return self._has_custom_css

    @property
    def has_custom_js(self) -> bool:
        """Whether this page has custom JS."""
        return self._has_custom_js

    @property
    def permissions_required(self) -> tuple[str, ...]:
        """The permissions required to access this page."""
        return self._perms_required

    @property
    def access_key(self) -> str | None:
        """The access key for menu links that point to this page."""
        return self._accesskey

    def can_user_access(self, user: models.User) -> bool:
        """Check whether the given user can access this page."""
        return all(user.has_permission(p) for p in self.permissions_required)

    def process_request(self, request: dj_wsgi.WSGIRequest, title: str, **kwargs: str) -> dict[str, typ.Any]:
        """Process the given client request.

        :param request: The client request.
        :param title: Page’s full title. The title will be split around '/'.
        :param kwargs: Page’s GET parameters.
        :return: A dict object containing parameters to pass to the page context object.
        """
        return {
            'has_custom_css': self.has_custom_css,
            'has_custom_js': self.has_custom_js,
            **self._process_request(request, *title.split('/'), **kwargs),
        }

    @abc.abstractmethod
    def _process_request(self, request: dj_wsgi.WSGIRequest, *args: str, **kwargs: str) -> dict[str, typ.Any]:
        """Process the given client request.

        :param request: The client request.
        :param args: Page’s arguments.
        :param kwargs: Page’s GET parameters.
        :return: A dict object containing parameters to pass to the page context object.
        """
        pass


SPECIAL_PAGES: dict[str, SpecialPage] = {}
"""Collection of all loaded special pages."""


def init():
    """Load and initialize all special pages from this package."""
    # Import all special pages from this package
    for f in pathlib.Path(__file__).parent.glob('_*.py'):
        if f.is_file() and f.name != '__init__.py':
            module = importlib.import_module('.' + os.path.splitext(f.name)[0], package=__name__)
            for k, v in module.__dict__.items():
                if k[0] != '_' and isinstance(v, type) and issubclass(v, SpecialPage):
                    # noinspection PyArgumentList
                    sp = v()
                    SPECIAL_PAGES[sp.name] = sp


init()
