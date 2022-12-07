import json as _json
import typing as _typ

import django.core.paginator as dj_paginator

from . import models as _models, settings, forms
from .api.wiki import constants as w_cons, pages


class PageContext:
    def __init__(
            self,
            site_name: str,
            tab_title: str | None,
            title: str | None,
            no_index: bool,
            user: _models.User,
            language: settings.Language,
    ):
        self._site_name = site_name
        self._tab_title = tab_title
        self._title = title
        self._no_index = no_index
        self._user = user
        self._language = language

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
    def __init__(
            self,
            site_name: str,
            tab_title: str | None,
            title: str | None,
            no_index: bool,
            user: _models.User,
            language: settings.Language,
            map_js_config: dict[str, _typ.Any]
    ):
        super().__init__(
            site_name=site_name,
            tab_title=tab_title,
            title=title,
            no_index=no_index,
            user=user,
            language=language,
        )
        self._map_js_config = _json.dumps(map_js_config)

    @property
    def map_js_config(self) -> str:
        return self._map_js_config


class UserPageContext(PageContext):
    def __init__(
            self,
            site_name: str,
            tab_title: str | None,
            title: str | None,
            no_index: bool,
            user: _models.User,
            language: settings.Language,
            target_user: _models.User
    ):
        super().__init__(
            site_name=site_name,
            tab_title=tab_title,
            title=title,
            no_index=no_index,
            user=user,
            language=language,
        )
        self._target_user = target_user

    @property
    def target_user(self) -> _models.User:
        return self._target_user


class WikiPageContext(PageContext):  # TODO parent pages
    def __init__(
            self,
            site_name: str,
            page: _models.Page,
            no_index: bool,
            user: _models.User,
            language: settings.Language,
            action: str,
            show_title: bool,
            page_exists: bool,
            js_config: dict[str, _typ.Any]
    ):
        super().__init__(
            site_name=site_name,
            tab_title=page.title,
            title=page.title,
            no_index=no_index,
            user=user,
            language=language,
        )
        self._page = page
        self._action = action
        self._show_title = show_title
        self._page_exists = page_exists
        self._js_config = _json.dumps(js_config)

    @property
    def page(self) -> _models.Page:
        return self._page

    @property
    def action(self) -> str:
        return self._action

    @property
    def show_title(self) -> bool:
        return self._show_title

    @property
    def page_exists(self) -> bool:
        return self._page_exists

    @property
    def can_user_edit(self) -> bool:
        return self.page.can_user_edit(self.user)

    @property
    def wiki_js_config(self) -> str:
        return self._js_config


class WikiPageShowActionContext(WikiPageContext):
    def __init__(
            self,
            site_name: str,
            page: _models.Page,
            no_index: bool,
            user: _models.User,
            language: settings.Language,
            js_config: dict[str, _typ.Any],
            content: str,
            revision: _models.PageRevision | None,
            archived: bool,
            cat_subcategories: list[_models.Page] = None,
            cat_pages: list[_models.Page] = None,
            cat_page_index: int = 1,
            cat_results_per_page: int = 20,
    ):
        show_title = page.full_title != pages.MAIN_PAGE_TITLE
        super().__init__(
            site_name=site_name,
            page=page,
            no_index=no_index,
            user=user,
            language=language,
            action=w_cons.ACTION_SHOW,
            show_title=show_title,
            page_exists=page.exists,
            js_config=js_config,
        )
        self._content = content
        self._revision = revision
        self._archived = archived
        self._cat_subcategories = dj_paginator.Paginator(cat_subcategories or [], cat_results_per_page)
        self._cat_pages = dj_paginator.Paginator(cat_pages or [], cat_results_per_page)
        self._cat_page_index = cat_page_index

    @property
    def rendered_page_content(self) -> str:
        return self._content

    @property
    def archived(self) -> bool:
        return self._archived

    @property
    def revision(self) -> _models.PageRevision | None:
        return self._revision

    @property
    def cat_subcategories(self) -> dj_paginator.Paginator:
        return self._cat_subcategories

    @property
    def cat_pages(self) -> dj_paginator.Paginator:
        return self._cat_pages

    @property
    def cat_page_index(self) -> int:
        return self._cat_page_index


class WikiPageEditActionContext(WikiPageContext):
    def __init__(
            self,
            site_name: str,
            page: _models.Page,
            user: _models.User,
            language: settings.Language,
            js_config: dict[str, _typ.Any],
            revision: _models.PageRevision | None,
            archived: bool,
            edit_form: forms.WikiEditPageForm,
            edit_notice: str = None,
            new_page_notice: str = None,
            perm_error: bool = False,
            concurrent_edit_error: bool = False,
    ):
        super().__init__(
            site_name=site_name,
            page=page,
            no_index=True,
            user=user,
            language=language,
            action=w_cons.ACTION_EDIT,
            show_title=True,
            page_exists=page.exists,
            js_config=js_config,
        )
        self._revision = revision
        self._archived = archived
        self._edit_form = edit_form
        self._edit_notice = edit_notice
        self._new_page_notice = new_page_notice
        self._perm_error = perm_error
        self._concurrent_edit_error = concurrent_edit_error

    @property
    def archived(self) -> bool:
        return self._archived

    @property
    def revision(self) -> _models.PageRevision | None:
        return self._revision

    @property
    def edit_form(self) -> forms.WikiEditPageForm:
        return self._edit_form

    @property
    def edit_notice(self) -> str | None:
        return self._edit_notice

    @property
    def new_page_notice(self) -> str | None:
        return self._new_page_notice

    @property
    def permission_error(self) -> bool:
        return self._perm_error

    @property
    def concurrent_edit_error(self) -> bool:
        return self._concurrent_edit_error


class WikiPageHistoryActionContext(WikiPageContext):
    def __init__(
            self,
            site_name: str,
            page: _models.Page,
            user: _models.User,
            language: settings.Language,
            js_config: dict[str, _typ.Any],
            revisions: list[_models.PageRevision],
            page_index: int = 1,
            revisions_per_page: int = 20,
    ):
        super().__init__(
            site_name=site_name,
            page=page,
            no_index=True,
            user=user,
            language=language,
            action=w_cons.ACTION_HISTORY,
            show_title=True,
            page_exists=page.exists,
            js_config=js_config,
        )
        self._revisions = dj_paginator.Paginator(revisions, revisions_per_page)
        self._page_index = page_index

    @property
    def revisions(self) -> dj_paginator.Paginator:
        return self._revisions

    @property
    def page_index(self) -> int:
        return self._page_index


class WikiPageTalkContext(WikiPageContext):
    def __init__(
            self,
            site_name: str,
            page: _models.Page,
            user: _models.User,
            language: settings.Language,
            js_config: dict[str, _typ.Any],
            topics: dict[_models.Topic, list[_models.Message]],
    ):
        super().__init__(
            site_name=site_name,
            page=page,
            no_index=True,
            user=user,
            language=language,
            action=w_cons.ACTION_TALK,
            show_title=True,
            page_exists=page.exists,
            js_config=js_config,
        )
        self._topics = topics
        self._can_user_post_messages = page.can_user_post_messages(user)

    @property
    def topics(self) -> dict[_models.Topic, list[_models.Message]]:
        return self._topics

    @property
    def can_user_post_messages(self) -> bool:
        return self._can_user_post_messages


class WikiSpecialPageContext(WikiPageContext):
    def __init__(
            self,
            site_name: str,
            page: _models.Page,
            user: _models.User,
            language: settings.Language,
            page_exists: bool,
            js_config: dict[str, _typ.Any],
            **kwargs,
    ):
        super().__init__(
            site_name=site_name,
            page=page,
            no_index=True,
            user=user,
            language=language,
            action=w_cons.ACTION_SHOW,
            show_title=True,
            page_exists=page_exists,
            js_config=js_config
        )
        self._data = kwargs

    def __getattr__(self, item: str) -> _typ.Any:
        return self._data[item]
