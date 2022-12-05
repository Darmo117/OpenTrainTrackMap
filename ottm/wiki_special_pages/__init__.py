import abc
import importlib
import pathlib
import typing as typ

import django.core.handlers.wsgi as dj_wsgi

from .. import models


class SpecialPage(abc.ABC):
    def __init__(self, name: str, *requires_perms: str, has_custom_css: bool = False, has_custom_js: bool = False):
        self._name = name
        self._has_custom_css = has_custom_css
        self._has_custom_js = has_custom_js
        self._perms_required = requires_perms

    @property
    def name(self) -> str:
        return self._name

    @property
    def has_custom_css(self) -> bool:
        return self._has_custom_css

    @property
    def has_custom_js(self) -> bool:
        return self._has_custom_js

    @property
    def permissions_required(self) -> tuple[str, ...]:
        return self._perms_required

    def can_user_access(self, user: models.User) -> bool:
        return all(user.has_permission(p) for p in self.permissions_required)

    def process_request(self, request: dj_wsgi.WSGIRequest, title: str, **kwargs: str) -> dict[str, typ.Any]:
        return {
            'has_custom_css': self.has_custom_css,
            'has_custom_js': self.has_custom_js,
            **self._process_request(request, *title.split('/'), **kwargs),
        }

    @abc.abstractmethod
    def _process_request(self, request: dj_wsgi.WSGIRequest, *args: str, **kwargs: str) -> dict[str, typ.Any]:
        pass


SPECIAL_PAGES: dict[str, SpecialPage] = {}


def init():
    # Import all special pages from this package
    for f in pathlib.Path(__file__).parent.glob('_*.py'):
        if f.is_file() and f.name != '__init__.py':
            module = importlib.import_module('.' + f.name, package=str(pathlib.Path(__file__).parent))
            for k, v in module.__dict__.items():
                if issubclass(v, SpecialPage):
                    # noinspection PyArgumentList
                    sp = v()
                    SPECIAL_PAGES[sp.name] = sp
