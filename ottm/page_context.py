from __future__ import annotations

import dataclasses
import typing as typ

from . import models, forms


@dataclasses.dataclass
class PageContext:
    site_name: str
    tab_title: typ.Optional[str]
    title: typ.Optional[str]
    noindex: bool
    user: models.User

    def __post_init__(self):
        self._context = None
        self.lang = self.user.prefered_language

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
    log_in_form: forms.LogInForm
    global_errors: typ.List[str]

    def __init__(self, context: PageContext, /, form: forms.LogInForm, global_errors: typ.List[str]):
        self._context = context
        self.log_in_form = form
        self.global_errors = global_errors


@dataclasses.dataclass(init=False)
class UserPageContext(PageContext):
    target_user: models.User

    def __init__(self, context: PageContext, /, target_user: models.User):
        self._context = context
        self.target_user = target_user
