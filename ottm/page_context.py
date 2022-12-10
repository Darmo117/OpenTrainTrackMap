"""This module defines all page context classes."""
import abc
import json as _json
import typing as _typ

import django.core.paginator as dj_paginator

from . import forms, models as _models, settings
from .api.wiki import constants as w_cons, pages


class PageContext:
    """A page context object contains values meant to be used within HTML templates."""

    def __init__(
            self,
            tab_title: str | None,
            title: str | None,
            no_index: bool,
            user: _models.User,
            language: settings.UILanguage,
            dark_mode: bool,
    ):
        """Create a generic page context.

        :param tab_title: Title of the browser’s tab.
        :param title: Page’s title.
        :param no_index: Whether to insert a noindex clause within the HTML page.
        :param user: Current user.
        :param language: Page’s language.
        :param dark_mode: Whether to activate the dark mode.
        """
        self._tab_title = tab_title
        self._title = title
        self._no_index = no_index
        self._user = user
        self._language = language
        self._dark_mode = dark_mode

    @property
    def site_name(self) -> str:
        return settings.SITE_NAME

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
    def language(self) -> settings.UILanguage:
        return self._language

    @property
    def ui_languages(self) -> list[settings.UILanguage]:
        return list(settings.LANGUAGES.values())

    @property
    def dark_mode(self) -> bool:
        return self._dark_mode


class MapPageContext(PageContext):
    def __init__(
            self,
            tab_title: str | None,
            title: str | None,
            no_index: bool,
            user: _models.User,
            language: settings.UILanguage,
            dark_mode: bool,
            map_js_config: dict[str, _typ.Any],
    ):
        """Create a page context for map pages.

        :param tab_title: Title of the browser’s tab.
        :param title: Page’s title.
        :param no_index: Whether to insert a noindex clause within the HTML page.
        :param user: Current user.
        :param language: Page’s language.
        :param dark_mode: Whether to activate the dark mode.
        :param map_js_config: Dict object containing map’s JS config.
         It is converted to a JSON object before being inserted in the HTML page.
        """
        super().__init__(
            tab_title=tab_title,
            title=title,
            no_index=no_index,
            user=user,
            language=language,
            dark_mode=dark_mode,
        )
        self._map_js_config = _json.dumps(map_js_config)

    @property
    def map_js_config(self) -> str:
        return self._map_js_config


class UserPageContext(PageContext):
    def __init__(
            self,
            tab_title: str | None,
            title: str | None,
            no_index: bool,
            user: _models.User,
            language: settings.UILanguage,
            dark_mode: bool,
            target_user: _models.User,
    ):
        """Create a page context for user pages.

        :param tab_title: Title of the browser’s tab.
        :param title: Page’s title.
        :param no_index: Whether to insert a noindex clause within the HTML page.
        :param user: Current user.
        :param language: Page’s language.
        :param dark_mode: Whether to activate the dark mode.
        :param target_user: User of the requested page.
        """
        super().__init__(
            tab_title=tab_title,
            title=title,
            no_index=no_index,
            user=user,
            language=language,
            dark_mode=dark_mode,
        )
        self._target_user = target_user

    @property
    def target_user(self) -> _models.User:
        return self._target_user


class WikiPageContext(PageContext, abc.ABC):  # TODO parent pages
    def __init__(
            self,
            page: _models.Page,
            no_index: bool,
            user: _models.User,
            language: settings.UILanguage,
            dark_mode: bool,
            action: str,
            show_title: bool,
            page_exists: bool,
            js_config: dict[str, _typ.Any],
    ):
        """Create a page context for wiki pages.

        :param page: Wiki page object.
        :param no_index: Whether to insert a noindex clause within the HTML page.
        :param user: Current user.
        :param language: Page’s language.
        :param dark_mode: Whether to activate the dark mode.
        :param action: Page action.
        :param show_title: Whether the page title should be displayed.
        :param page_exists: Whether the page exists.
        :param js_config: Dict object containing the wiki’s JS config.
         It is converted to a JSON object before being inserted in the HTML page.
        """
        super().__init__(
            tab_title=page.title,
            title=page.title,
            no_index=no_index,
            user=user,
            language=language,
            dark_mode=dark_mode,
        )
        self._page = page
        self._action = action
        self._show_title = show_title
        self._page_exists = page_exists
        self._js_config = _json.dumps(js_config)

    @property
    def site_name(self) -> str:
        return self.language.translate('wiki.name', site_name=settings.SITE_NAME)

    @property
    def main_page_full_title(self) -> str:
        return pages.MAIN_PAGE_TITLE

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
            page: _models.Page,
            no_index: bool,
            user: _models.User,
            language: settings.UILanguage,
            dark_mode: bool,
            js_config: dict[str, _typ.Any],
            content: str,
            revision: _models.PageRevision | None,
            archived: bool,
            cat_subcategories: list[_models.Page] = None,
            cat_pages: list[_models.Page] = None,
            cat_page_index: int = 1,
            cat_results_per_page: int = 20,
    ):
        """Create a page context for wiki pages.

        :param page: Wiki page object.
        :param no_index: Whether to insert a noindex clause within the HTML page.
        :param user: Current user.
        :param language: Page’s language.
        :param dark_mode: Whether to activate the dark mode.
        :param js_config: Dict object containing the wiki’s JS config.
         It is converted to a JSON object before being inserted in the HTML page.
        :param content: Rendered page’s content.
        :param revision: A revision of the page. May be None.
        :param archived: Whether the revision is not the current one.
        :param cat_subcategories: The list of subcategories of the category represented by the page.
         Only used if the page is a category.
        :param cat_pages: The list of pages within the category represented by the page.
         Only used if the page is a category.
        :param cat_page_index: Current pagination index. Only used if the page is a category.
        :param cat_results_per_page: Number of pages per page to display. Only used if the page is a category.
        """
        show_title = page.full_title != pages.MAIN_PAGE_TITLE
        super().__init__(
            page=page,
            no_index=no_index,
            user=user,
            language=language,
            dark_mode=dark_mode,
            action=w_cons.ACTION_READ,
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
    def page_content(self) -> str:
        return self._content

    @property
    def page_language(self) -> str:
        return w_cons.LANGUAGE_CODES[self.page.content_type]

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
            page: _models.Page,
            user: _models.User,
            language: settings.UILanguage,
            dark_mode: bool,
            js_config: dict[str, _typ.Any],
            revision: _models.PageRevision | None,
            archived: bool,
            edit_form: forms.WikiEditPageForm,
            edit_notice: str = None,
            new_page_notice: str = None,
            perm_error: bool = False,
            concurrent_edit_error: bool = False,
    ):
        """Create a page context for wiki pages.

        :param page: Wiki page object.
        :param user: Current user.
        :param language: Page’s language.
        :param dark_mode: Whether to activate the dark mode.
        :param js_config: Dict object containing the wiki’s JS config.
         It is converted to a JSON object before being inserted in the HTML page.
        :param revision: A revision of the page. May be None.
        :param archived: Whether the revision is not the current one.
        :param edit_form: Editing form.
        :param edit_notice: Rendered edit notice. May be None.
        :param new_page_notice: Rendered new page notice. May be None.
        :param perm_error: Whether the user lacks the permission to edit wiki pages.
        :param concurrent_edit_error: Whether another edit was made before submitting.
        """
        super().__init__(
            page=page,
            no_index=True,
            user=user,
            language=language,
            dark_mode=dark_mode,
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


class WikiPageTalkActionContext(WikiPageContext):
    def __init__(
            self,
            page: _models.Page,
            user: _models.User,
            language: settings.UILanguage,
            dark_mode: bool,
            js_config: dict[str, _typ.Any],
            topics: list[_models.Topic],
            page_index: int = 1,
            topics_per_page: int = 20,
    ):
        """Create a page context for wiki pages’ history.

        :param page: Wiki page object.
        :param user: Current user.
        :param language: Page’s language.
        :param dark_mode: Whether to activate the dark mode.
        :param js_config: Dict object containing the wiki’s JS config.
         It is converted to a JSON object before being inserted in the HTML page.
        :param topics: List of page talk topics.
        :param page_index: Current pagination index.
        :param topics_per_page: Number of topics to display per page.
        """
        super().__init__(
            page=page,
            no_index=True,
            user=user,
            language=language,
            dark_mode=dark_mode,
            action=w_cons.ACTION_TALK,
            show_title=True,
            page_exists=page.exists,
            js_config=js_config,
        )
        self._topics = dj_paginator.Paginator(topics, topics_per_page)
        self._page_index = page_index
        self._topics_per_page = topics_per_page

    @property
    def topics(self) -> dj_paginator.Paginator:
        return self._topics

    @property
    def page_index(self) -> int:
        return self._page_index


class WikiPageHistoryActionContext(WikiPageContext):
    def __init__(
            self,
            page: _models.Page,
            user: _models.User,
            language: settings.UILanguage,
            dark_mode: bool,
            js_config: dict[str, _typ.Any],
            revisions: list[_models.PageRevision],
            page_index: int = 1,
            revisions_per_page: int = 20,
    ):
        """Create a page context for wiki pages’ history.

        :param page: Wiki page object.
        :param user: Current user.
        :param language: Page’s language.
        :param dark_mode: Whether to activate the dark mode.
        :param js_config: Dict object containing the wiki’s JS config.
         It is converted to a JSON object before being inserted in the HTML page.
        :param revisions: List of page revisions.
        :param page_index: Current pagination index.
        :param revisions_per_page: Number of revisions to display per page.
        """
        super().__init__(
            page=page,
            no_index=True,
            user=user,
            language=language,
            dark_mode=dark_mode,
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
            page: _models.Page,
            user: _models.User,
            language: settings.UILanguage,
            dark_mode: bool,
            js_config: dict[str, _typ.Any],
            topics: dict[_models.Topic, list[_models.Message]],
    ):
        """Create a page context for wiki talk pages.

        :param page: Wiki page object.
        :param user: Current user.
        :param language: Page’s language.
        :param dark_mode: Whether to activate the dark mode.
        :param js_config: Dict object containing the wiki’s JS config.
         It is converted to a JSON object before being inserted in the HTML page.
        :param topics: Dict of topics with their associated messages.
        """
        super().__init__(
            page=page,
            no_index=True,
            user=user,
            language=language,
            dark_mode=dark_mode,
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
            page: _models.Page,
            user: _models.User,
            language: settings.UILanguage,
            dark_mode: bool,
            page_exists: bool,
            js_config: dict[str, _typ.Any],
            **kwargs,
    ):
        """Create a page context for special pages.

        :param page: Wiki page object.
        :param user: Current user.
        :param language: Page’s language.
        :param dark_mode: Whether to activate the dark mode.
        :param page_exists: Whether the page exists.
        :param js_config: Dict object containing the wiki’s JS config.
         It is converted to a JSON object before being inserted in the HTML page.
        :param kwargs: Special page’s additional parameters.
        """
        super().__init__(
            page=page,
            no_index=True,
            user=user,
            language=language,
            dark_mode=dark_mode,
            action=w_cons.ACTION_READ,
            show_title=True,
            page_exists=page_exists,
            js_config=js_config
        )
        self._data = kwargs

    def __getattr__(self, item: str) -> _typ.Any:
        return self._data.get(item)
