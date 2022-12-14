"""This module defines all page context classes."""
import abc
import datetime
import json as _json
import typing as _typ

import django.core.paginator as dj_paginator
import django.db.models as dj_models

from . import forms, models as _models, settings, requests
from .api import utils
from .api.wiki import constants as w_cons, pages


class PageContext:
    """A page context object contains values meant to be used within HTML templates."""

    def __init__(
            self,
            request_params: requests.RequestParams,
            tab_title: str | None,
            title: str | None,
            no_index: bool,
            max_page_index: int = None,
    ):
        """Create a generic page context.

        :param request_params: Page request parameters.
        :param tab_title: Title of the browser’s tab.
        :param title: Page’s title.
        :param no_index: Whether to insert a noindex clause within the HTML page.
        :param max_page_index: Maximum page index. May be None if the page does not have pagination.
        """
        self._request_params = request_params
        self._tab_title = tab_title
        self._title = title
        self._no_index = no_index
        self._max_page_index = max_page_index

    @property
    def request_params(self) -> requests.RequestParams:
        return self._request_params

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
        return self._request_params.user

    @property
    def language(self) -> settings.UILanguage:
        return self._request_params.ui_language

    @property
    def ui_languages(self) -> list[settings.UILanguage]:
        return list(settings.LANGUAGES.values())

    @property
    def dark_mode(self) -> bool:
        return self._request_params.dark_mode

    @property
    def results_per_page(self) -> int:
        return self._request_params.results_per_page

    @property
    def page_index(self) -> int:
        if self._max_page_index:
            return min(self._request_params.page_index, self._max_page_index)
        return self._request_params.page_index


class MapPageContext(PageContext):
    def __init__(
            self,
            request_params: requests.RequestParams,
            tab_title: str | None,
            title: str | None,
            no_index: bool,
            map_js_config: dict[str, _typ.Any],
    ):
        """Create a page context for map pages.

        :param request_params: Page request parameters.
        :param tab_title: Title of the browser’s tab.
        :param title: Page’s title.
        :param no_index: Whether to insert a noindex clause within the HTML page.
        :param map_js_config: Dict object containing map’s JS config.
         It is converted to a JSON object before being inserted in the HTML page.
        """
        super().__init__(
            request_params,
            tab_title=tab_title,
            title=title,
            no_index=no_index,
        )
        self._map_js_config = _json.dumps(map_js_config)

    @property
    def map_js_config(self) -> str:
        return self._map_js_config


class UserPageContext(PageContext):
    def __init__(
            self,
            request_params: requests.RequestParams,
            tab_title: str | None,
            title: str | None,
            no_index: bool,
            target_user: _models.User,
    ):
        """Create a page context for user pages.

        :param request_params: Page request parameters.
        :param tab_title: Title of the browser’s tab.
        :param title: Page’s title.
        :param no_index: Whether to insert a noindex clause within the HTML page.
        :param target_user: User of the requested page.
        """
        super().__init__(
            request_params,
            tab_title=tab_title,
            title=title,
            no_index=no_index,
        )
        self._target_user = target_user

    @property
    def target_user(self) -> _models.User:
        return self._target_user


class WikiPageContext(PageContext, abc.ABC):  # TODO parent pages
    def __init__(
            self,
            request_params: requests.RequestParams,
            page: _models.Page,
            no_index: bool,
            show_title: bool,
            page_exists: bool,
            js_config: dict[str, _typ.Any],
            max_page_index: int = None,
    ):
        """Create a page context for wiki pages.

        :param request_params: Page request parameters.
        :param page: Wiki page object.
        :param no_index: Whether to insert a noindex clause within the HTML page.
        :param show_title: Whether the page title should be displayed.
        :param page_exists: Whether the page exists.
        :param js_config: Dict object containing the wiki’s JS config.
            It is converted to a JSON object before being inserted in the HTML page.
        :param max_page_index: Maximum page index. May be None if the page does not have pagination.
        """
        super().__init__(
            request_params,
            tab_title=page.title,
            title=page.title,
            no_index=no_index,
            max_page_index=max_page_index,
        )
        self._page = page
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
        return self._request_params.wiki_action

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


class WikiPageReadActionContext(WikiPageContext):
    def __init__(
            self,
            request_params: requests.RequestParams,
            page: _models.Page,
            no_index: bool,
            js_config: dict[str, _typ.Any],
            content: str,
            revision: _models.PageRevision | None,
            archived: bool,
            cat_subcategories: list[_models.Page] = None,
            cat_pages: list[_models.Page] = None,
            no_page_notice: str = None,
    ):
        """Create a page context for wiki pages.

        :param request_params: Page request parameters.
        :param page: Wiki page object.
        :param no_index: Whether to insert a noindex clause within the HTML page.
        :param js_config: Dict object containing the wiki’s JS config.
         It is converted to a JSON object before being inserted in the HTML page.
        :param content: Rendered page’s content.
        :param revision: A revision of the page. May be None.
        :param archived: Whether the revision is not the current one.
        :param cat_subcategories: The list of subcategories of the category represented by the page.
         Only used if the page is a category.
        :param cat_pages: The list of pages within the category represented by the page.
         Only used if the page is a category.
        :param no_page_notice: The rendered notice if the page does not exist.
        """
        self._cat_pages = dj_paginator.Paginator(cat_pages or [], request_params.results_per_page)
        show_title = page.full_title != pages.MAIN_PAGE_TITLE
        super().__init__(
            request_params,
            page=page,
            no_index=no_index,
            show_title=show_title,
            page_exists=page.exists,
            js_config=js_config,
            max_page_index=self._cat_pages.num_pages,
        )
        self._content = content
        self._revision = revision
        self._archived = archived
        self._cat_subcategories = cat_subcategories or []
        self._no_page_notice = no_page_notice

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
    def cat_subcategories(self) -> list[_models.Page]:
        return self._cat_subcategories

    @property
    def cat_pages(self) -> dj_paginator.Paginator:
        return self._cat_pages

    @property
    def no_page_notice(self) -> str | None:
        return self._no_page_notice


class WikiPageInfoActionContext(WikiPageContext):
    def __init__(
            self,
            request_params: requests.RequestParams,
            page: _models.Page,
            js_config: dict[str, _typ.Any],
            revisions: dj_models.QuerySet[_models.PageRevision],
            followers_nb: int,
            redirects_nb: int,
            subpages_nb: int,
            protection: _models.PageProtection | None,
    ):
        """Create a page info context for wiki pages.

        :param request_params: Page request parameters.
        :param page: Wiki page object.
        :param js_config: Dict object containing the wiki’s JS config.
         It is converted to a JSON object before being inserted in the HTML page.
        :param revisions: List of revisions for the page.
        :param followers_nb: Number of users that follow the page.
        :param redirects_nb: Number of redirects to this page.
        :param subpages_nb: Number of subpages of this page.
        :param protection: Protection status of the page.
        """
        super().__init__(
            request_params,
            page=page,
            no_index=True,
            show_title=True,
            page_exists=page.exists,
            js_config=js_config,
        )
        self._revisions = revisions
        self._recent_revisions = revisions.filter(date__gte=utils.now() - datetime.timedelta(days=self.recent_range))
        self._recent_editors_nb = self._recent_revisions.aggregate(
            dj_models.Count('author', distinct=True))['author__count']
        self._followers_nb = followers_nb
        self._redirects_nb = redirects_nb
        self._subpages_nb = subpages_nb
        self._protection = protection

    @property
    def recent_range(self) -> int:
        return 30

    @property
    def revisions(self) -> dj_models.QuerySet[_models.PageRevision]:
        return self._revisions

    @property
    def recent_revisions(self) -> dj_models.QuerySet[_models.PageRevision]:
        return self._recent_revisions

    @property
    def recent_editors_nb(self) -> int:
        return self._recent_editors_nb

    @property
    def last_revision(self) -> _models.PageRevision:
        return self._revisions[len(self._revisions) - 1]

    @property
    def first_revision(self) -> _models.PageRevision:
        return self._revisions[0]

    @property
    def followers_nb(self) -> int:
        return self._followers_nb

    @property
    def redirects_nb(self) -> int:
        return self._redirects_nb

    @property
    def subpages_nb(self) -> int:
        return self._subpages_nb

    @property
    def protection(self) -> _models.PageProtection | None:
        return self._protection


class WikiPageEditActionContext(WikiPageContext):
    def __init__(
            self,
            request_params: requests.RequestParams,
            page: _models.Page,
            js_config: dict[str, _typ.Any],
            revision: _models.PageRevision | None,
            archived: bool,
            edit_form: forms.WikiEditPageForm,
            edit_notice: str = None,
            new_page_notice: str = None,
            perm_error: bool = False,
            concurrent_edit_error: bool = False,
            edit_protection_log_entry: _models.PageProtectionLog = None,
    ):
        """Create a page context for wiki pages.

        :param request_params: Page request parameters.
        :param page: Wiki page object.
        :param js_config: Dict object containing the wiki’s JS config.
            It is converted to a JSON object before being inserted in the HTML page.
        :param revision: A revision of the page. May be None.
        :param archived: Whether the revision is not the current one.
        :param edit_form: Editing form.
        :param edit_notice: Rendered edit notice. May be None.
        :param new_page_notice: Rendered new page notice. May be None.
        :param perm_error: Whether the user lacks the permission to edit wiki pages.
        :param concurrent_edit_error: Whether another edit was made before submitting.
        :param edit_protection_log_entry: The page’s PageProtectionLog entry if it exists.
        """
        super().__init__(
            request_params,
            page=page,
            no_index=True,
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
        self._edit_protection_log_entry = edit_protection_log_entry

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

    @property
    def edit_protection_log_entry(self) -> _models.PageProtectionLog | None:
        return self._edit_protection_log_entry


class WikiPageTalkActionContext(WikiPageContext):
    def __init__(
            self,
            request_params: requests.RequestParams,
            page: _models.Page,
            js_config: dict[str, _typ.Any],
            topics: list[_models.Topic],
    ):
        """Create a page context for wiki pages’ history.

        :param request_params: Page request parameters.
        :param page: Wiki page object.
        :param js_config: Dict object containing the wiki’s JS config.
         It is converted to a JSON object before being inserted in the HTML page.
        :param topics: List of page talk topics.
        """
        self._topics = dj_paginator.Paginator(topics, request_params.results_per_page)
        super().__init__(
            request_params,
            page=page,
            no_index=True,
            show_title=True,
            page_exists=page.exists,
            js_config=js_config,
            max_page_index=self._topics.num_pages,
        )

    @property
    def topics(self) -> dj_paginator.Paginator:
        return self._topics


class WikiPageHistoryActionContext(WikiPageContext):
    def __init__(
            self,
            request_params: requests.RequestParams,
            page: _models.Page,
            js_config: dict[str, _typ.Any],
            revisions: list[_models.PageRevision],
    ):
        """Create a page context for wiki pages’ history.

        :param request_params: Page request parameters.
        :param page: Wiki page object.
        :param js_config: Dict object containing the wiki’s JS config.
         It is converted to a JSON object before being inserted in the HTML page.
        :param revisions: List of page revisions.
        """
        self._revisions = dj_paginator.Paginator(revisions, request_params.results_per_page)
        super().__init__(
            request_params,
            page=page,
            no_index=True,
            show_title=True,
            page_exists=page.exists,
            js_config=js_config,
            max_page_index=self._revisions.num_pages,
        )

    @property
    def revisions(self) -> dj_paginator.Paginator:
        return self._revisions


class WikiPageTalkContext(WikiPageContext):
    def __init__(
            self,
            request_params: requests.RequestParams,
            page: _models.Page,
            js_config: dict[str, _typ.Any],
            topics: dict[_models.Topic, list[_models.Message]],
    ):
        """Create a page context for wiki talk pages.

        :param request_params: Page request parameters.
        :param page: Wiki page object.
        :param js_config: Dict object containing the wiki’s JS config.
            It is converted to a JSON object before being inserted in the HTML page.
        :param topics: Dict of topics with their associated messages.
        """
        super().__init__(
            request_params,
            page=page,
            no_index=True,
            show_title=True,
            page_exists=page.exists,
            js_config=js_config,
            max_page_index=1,  # TODO paginate topics
        )
        self._topics = topics
        self._can_user_post_messages = page.can_user_post_messages(request_params.user)

    @property
    def topics(self) -> dict[_models.Topic, list[_models.Message]]:
        return self._topics

    @property
    def can_user_post_messages(self) -> bool:
        return self._can_user_post_messages


class WikiSpecialPageContext(WikiPageContext):
    def __init__(
            self,
            request_params: requests.RequestParams,
            page: _models.Page,
            page_exists: bool,
            js_config: dict[str, _typ.Any],
            required_perms: tuple[str, ...] = (),
            kwargs: dict[str, _typ.Any] = None,
    ):
        """Create a page context for special pages.

        :param request_params: Page request parameters.
        :param page: Wiki page object.
        :param page_exists: Whether the page exists.
        :param js_config: Dict object containing the wiki’s JS config.
            It is converted to a JSON object before being inserted in the HTML page.
        :param required_perms: Tuple of all permissions required to access the special page.
        :param kwargs: Special page’s additional parameters.
        """
        if kwargs is None:
            kwargs = {}
        super().__init__(
            request_params,
            page=page,
            no_index=True,
            show_title=True,
            page_exists=page_exists,
            js_config=js_config,
            max_page_index=kwargs.get('max_page_index', 1),
        )
        self._required_perms = required_perms
        self._data = kwargs

    @property
    def required_perms(self) -> tuple[str, ...]:
        return self._required_perms

    @property
    def can_user_read(self) -> bool:
        return all(self.user.has_permission(p) for p in self._required_perms)

    def __getattr__(self, item: str) -> _typ.Any:
        return self._data.get(item)
