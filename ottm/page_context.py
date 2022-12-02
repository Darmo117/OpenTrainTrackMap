from __future__ import annotations

import dataclasses

from . import models


@dataclasses.dataclass
class PageContext:
    site_name: str
    tab_title: str | None
    title: str | None
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
        self.js_config = self._to_js(js_config)

    @staticmethod
    def _to_js(js_config: dict) -> str:
        def escape(s: str) -> str:
            return s.replace('"', r'\"').replace('\\', r'\\')

        js = (f'"{escape(k)}": {repr(v)}' for k, v in js_config.items())
        return '{' + ','.join(js) + '}'


@dataclasses.dataclass(init=False)
class UserPageContext(PageContext):
    target_user: models.User

    def __init__(self, context: PageContext, /, target_user: models.User):
        self._context = context
        self.target_user = target_user
