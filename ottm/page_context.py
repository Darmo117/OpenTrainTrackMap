import json as _json
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
        self._js_config = _json.dumps(js_config)

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


class WikiPageContext(PageContext):
    def __init__(self, site_name: str, page: _models.Page, no_index: bool, user: _models.User,
                 js_config: dict[str, _typ.Any]):
        super().__init__(site_name=site_name, tab_title=page.title, title=page.title, no_index=no_index, user=user)
        self._page = page
        self._js_config = _json.dumps(js_config)

    @property
    def page(self) -> _models.Page:
        return self._page

    @property
    def can_user_edit(self) -> bool:
        return self.page.can_user_edit(self.user)

    @property
    def js_config(self) -> str:
        return self._js_config


class WikiPageShowActionContext(WikiPageContext):
    def __init__(self, site_name: str, page: _models.Page, no_index: bool, user: _models.User,
                 js_config: dict[str, _typ.Any], content: str):
        super().__init__(site_name=site_name, page=page, no_index=no_index, user=user, js_config=js_config)
        self._content = content

    @property
    def content(self) -> str:
        return self._content


class WikiPageEditActionContext(WikiPageContext):
    def __init__(self, site_name: str, page: _models.Page, user: _models.User, js_config: dict[str, _typ.Any],
                 code: str):
        super().__init__(site_name=site_name, page=page, no_index=True, user=user, js_config=js_config)
        self._code = code

    @property
    def code(self) -> str:
        return self._code


class WikiPageHistoryActionContext(WikiPageContext):
    def __init__(self, site_name: str, page: _models.Page, user: _models.User, js_config: dict[str, _typ.Any],
                 revisions: list[_models.PageRevision]):
        super().__init__(site_name=site_name, page=page, no_index=True, user=user, js_config=js_config)
        self._revisions = revisions

    @property
    def revisions(self) -> list[_models.PageRevision]:
        return self._revisions


class WikiPageDiscussionContext(WikiPageContext):
    def __init__(self, site_name: str, page: _models.Page, user: _models.User, js_config: dict[str, _typ.Any],
                 topics: dict[_models.Topic, list[_models.Message]]):
        super().__init__(site_name=site_name, page=page, no_index=True, user=user, js_config=js_config)
        self._topics = topics

    @property
    def topics(self) -> dict[_models.Topic, list[_models.Message]]:
        return self._topics


class WikiSpecialPageContext(WikiPageContext):
    def __init__(self, site_name: str, page: _models.Page, user: _models.User, js_config: dict[str, _typ.Any],
                 **kwargs):
        super().__init__(site_name=site_name, page=page, no_index=True, user=user, js_config=js_config)
        self._data = kwargs

    def __getattr__(self, item: str) -> _typ.Any:
        return self._data[item]
