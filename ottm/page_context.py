import typing as _typ

from . import models as _models


class PageContext:
    def __init__(self, site_name: str, tab_title: str | None, title: str | None, no_index: bool, user: _models.User):
        self._site_name = site_name
        self._tab_title = tab_title
        self._title = title
        self._no_index = no_index
        self._user = user
        self._language = self.user.prefered_language
        self._context = None

    @property
    def site_name(self) -> str:
        return self._site_name

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
        return self._user

    @property
    def language(self):
        return self._language


class MapPageContext(PageContext):
    def __init__(self, site_name: str, tab_title: str | None, title: str | None, no_index: bool, user: _models.User,
                 js_config: dict[str, _typ.Any]):
        super().__init__(site_name=site_name, tab_title=tab_title, title=title, no_index=no_index, user=user)
        self._js_config = '{' + ','.join(f'{k!r}: {v!r}' for k, v in js_config.items()) + '}'

    @property
    def js_config(self) -> str:
        return self._js_config


class UserPageContext(PageContext):
    def __init__(self, site_name: str, tab_title: str | None, title: str | None, no_index: bool, user: _models.User,
                 target_user: _models.User):
        super().__init__(site_name=site_name, tab_title=tab_title, title=title, no_index=no_index, user=user)
        self._target_user = target_user

    @property
    def target_user(self) -> _models.User:
        return self._target_user
