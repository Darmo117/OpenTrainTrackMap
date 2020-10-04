from __future__ import annotations

import dataclasses
import typing as typ

from . import models


@dataclasses.dataclass
class PageContext:
    site_name: str
    tab_title: typ.Optional[str]
    title: typ.Optional[str]
    noindex: bool
    user: models.User

    def __post_init__(self):
        self._context = None

    def __getattr__(self, item):
        if self._context:
            return getattr(self._context, item)
        raise AttributeError(item)


@dataclasses.dataclass(init=False)
class MapPageContext(PageContext):
    js_config: str

    def __init__(self, context: PageContext, /, js_config: dict):
        self._context = context
        self.js_config = self.__to_js(js_config)

    @staticmethod
    def __to_js(js_config: dict) -> str:
        def escape(s: str) -> str:
            return s.replace('"', r'\"').replace('\\', r'\\')

        js = [f'"{escape(k)}": {repr(v)}' for k, v in js_config.items()]

        return '{' + ','.join(js) + '}'


@dataclasses.dataclass(init=False)
class LoginPageContext(PageContext):
    login_invalid_credentials: bool
    login_username: str

    def __init__(self, context: PageContext, /, invalid_credentials: bool, username: str):
        self._context = context
        self.login_invalid_credentials = invalid_credentials
        self.login_username = username


@dataclasses.dataclass(init=False)
class SignUpPageContext(PageContext):
    sign_up_invalid_username: bool
    sign_up_invalid_password: bool
    sign_up_invalid_email: bool
    sign_up_username: str
    sign_up_email: str

    def __init__(self, context: PageContext, /, invalid_username: bool, invalid_password: bool, invalid_email: bool,
                 username: str, email: str):
        self._context = context
        self.sign_up_invalid_username = invalid_username
        self.sign_up_invalid_password = invalid_password
        self.sign_up_invalid_email = invalid_email
        self.sign_up_username = username
        self.sign_up_email = email
