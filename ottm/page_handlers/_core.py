"""This module defines the base page handler and page context classes."""
from __future__ import annotations

import abc as _abc
import datetime as _dt
import json as _json
import typing as _typ
import urllib.parse as _url_parse

from django.conf import settings as _dj_settings
import django.core.handlers.wsgi as _dj_wsgi
import django.http.response as _dj_response
import django.shortcuts as _dj_scut
import pytz as _pytz

from .. import models as _models, requests as _requests, settings as _settings
from ..api import utils as _utils


class PageHandler(_abc.ABC):
    """Handles a specific WSGI request and returns a HttpResponse object."""

    def __init__(self, request: _dj_wsgi.WSGIRequest):
        """Create a page handler.

        :param request: The request to handle.
        """
        self._request_params = _requests.RequestParams(request)

    @_abc.abstractmethod
    def handle_request(self) -> _dj_response.HttpResponse:
        """Process the request."""
        pass

    # noinspection PyMethodMayBeStatic
    def redirect(self, url: str, /, *, reverse: bool = False, get_params: dict[str, _typ.Any] = None,
                 **kwargs) -> _dj_response.HttpResponseRedirect:
        """Return a HttpResponseRedirect object.

        :param url: URL to redirect to.
        :param reverse: If true, the url is parsed as a Django URL path name.
        :param get_params: Optional GET parameters.
        :param kwargs: Additional parameters for the URL reverse operation.
        :return: A HttpResponseRedirect object.
        """
        if reverse:
            url = _dj_scut.reverse(url, kwargs=kwargs)
        if get_params:
            url += '?' + _url_parse.urlencode(get_params)
        return _dj_response.HttpResponseRedirect(url)

    def render_page(self, template_name: str, context: PageContext, status: int = None,
                    kwargs: dict[str, _typ.Any] = None) -> _dj_response.HttpResponse:
        """Return a HttpResponse whose content is the rendered HTML of the given template.

        :param template_name: Name of the template to render.
        :param context: PageContext object to pass to the template.
        :param status: Status code.
        :param kwargs: Additonal parameters to pass to the template context.
        :return: A HttpResponse object.
        """
        return _dj_scut.render(
            self._request_params.request,
            template_name,
            context={'context': context, **(kwargs or {})},
            status=status,
        )

    # noinspection PyMethodMayBeStatic
    def response(self, content: str, content_type: str, status: int = 200):
        """Return a HttpResponse object.

        :param content: Response’s content.
        :param content_type: Response’s content type.
        :param status: Response’s status code.
        :return: A HttpResponse object.
        """
        return _dj_response.HttpResponse(content=content, content_type=content_type, status=status)


class PageContext:
    """A page context object contains values meant to be used within HTML templates."""

    def __init__(
            self,
            request_params: _requests.RequestParams,
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
        self._now = _utils.now()
        self._js_config = {
            'config': {
                'debug': _dj_settings.DEBUG,
                'apiPath': _dj_scut.reverse('ottm:api'),
                'serverHost': f'//{request_params.request.get_host()}',
                'staticPath': _dj_settings.STATIC_URL,
                'siteName': self.site_name,
                'serverTimezone': _dj_settings.TIME_ZONE,
            },
            'page': {
                'language': self.language.code,
                'darkMode': self.dark_mode,
            },
            'user': {
                'isAnonymous': not self.user.is_authenticated,
                'username': self.user.username,
                'hideUsername': self.user.hide_username,
                'id': self.user.internal_object.id if self.user.is_authenticated else 0,
                'preferredLanguage': self.user.preferred_language.code,
                'gender': self.user.gender.label,
                'usesDarkMode': self.user.uses_dark_mode,
                'preferredDatetimeFormat': self.user.preferred_datetime_format,
                'preferredTimezone': self.user.preferred_timezone.zone,
                'isBot': self.user.is_bot,
                'registrationTimestamp':
                    int(self.user.internal_object.date_joined.timestamp()) if self.user.is_authenticated else None,
                'groups': [g.label for g in self.user.get_groups().order_by('label')],
                'permissions': [p for g in self.user.get_groups().order_by('label') for p in g.permissions],
                'editCount': self.user.edits_count(),
                'wikiEditCount': self.user.wiki_edits_count(),
                'usersCanSendEmails': self.user.users_can_send_emails,
                'newUsersCanSendEmails': self.user.new_users_can_send_emails,
                'maxFilePreviewSize': self.user.max_file_preview_size,
                'thumbnailsSize': self.user.thumbnails_size,
                'showPageContentInDiffs': self.user.show_page_content_in_diffs,
                'showDiffAfterRevert': self.user.show_diff_after_revert,
                'showHiddenCategories': self.user.show_hidden_categories,
                'askRevertConfirmation': self.user.ask_revert_confirmation,
                'useEditorSyntaxHighlighting': self.user.uses_editor_syntax_highlighting,
                'markAllWikiEditsAsMinor': self.user.mark_all_wiki_edits_as_minor,
                'warnWhenNoWikiEditComment': self.user.warn_when_no_wiki_edit_comment,
                'warnWhenWikiEditNotPublished': self.user.warn_when_wiki_edit_not_published,
                'showPreviewAboveEditForm': self.user.show_preview_above_edit_form,
                'showPreviewWithoutReload': self.user.show_preview_without_reload,
                'defaultDaysNbWikiEditLists': self.user.default_days_nb_in_wiki_edit_lists,
                'defaultEditsNbWikiEditLists': self.user.default_edits_nb_in_wiki_edit_lists,
                'groupEditsPerPage': self.user.group_edits_per_page,
                'maskWikiMinorEdits': self.user.mask_wiki_minor_edits,
                'maskWikiBotEdits': self.user.mask_wiki_bot_edits,
                'maskWikiOwnEdits': self.user.mask_wiki_own_edits,
                'maskWikiAnonymousEdits': self.user.mask_wiki_anonymous_edits,
                'maskWikiAuthenticatedEdits': self.user.mask_wiki_authenticated_edits,
                'maskWikiCategorizationEdits': self.user.mask_wiki_categorization_edits,
                'maskWikiPatrolledEdits': self.user.mask_wiki_patrolled_edits,
                'addCreatedPagesToFL': self.user.add_created_pages_to_follow_list,
                'addModifiedPagesToFL': self.user.add_modified_pages_to_follow_list,
                'addRenamedPagesToFL': self.user.add_renamed_pages_to_follow_list,
                'addDeletedPagesToFL': self.user.add_deleted_pages_to_follow_list,
                'addRevertedPagesToFL': self.user.add_reverted_pages_to_follow_list,
                'addCreatedTopicsToFL': self.user.add_created_topics_to_follow_list,
                'addRepliedToTopicsToFL': self.user.add_replied_to_topics_to_follow_list,
                'searchDefaultResultsNb': self.user.search_default_results_nb,
                'searchMode': self.user.search_mode.value,
            },
            'languages': [self._lang_to_json(lang) for lang in _settings.LANGUAGES.values()],
            'translations': self.language.js_mappings,
        }

    @property
    def request_params(self) -> _requests.RequestParams:
        return self._request_params

    @property
    def now(self) -> _dt.datetime:
        return self._now

    @property
    def server_timezone(self) -> _dt.tzinfo:
        return _pytz.timezone(_dj_settings.TIME_ZONE)

    @property
    def site_name(self) -> str:
        return _settings.SITE_NAME

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
    def language(self) -> _settings.UILanguage:
        return self._request_params.ui_language

    @property
    def ui_languages(self) -> list[_settings.UILanguage]:
        return sorted(_settings.LANGUAGES.values(), key=lambda lang: lang.name)

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

    @property
    def js_config(self) -> str:
        return _json.dumps(self._js_config)

    @staticmethod
    def _lang_to_json(lang: _settings.UILanguage) -> dict[str, _typ.Any]:
        return {
            'code': lang.code,
            'name': lang.name,
            'writingDirection': lang.writing_direction,
            'comma': lang.comma,
            'and': lang.and_word,
            'dayNames': lang.day_names,
            'abbrDayNames': lang.abbr_day_names,
            'monthNames': lang.month_names,
            'abbrMonthNames': lang.abbr_month_names,
            'ampm': lang.am_pm,
            'decimalSep': lang.decimal_separator,
            'thousandsSep': lang.thousands_separator,
        }
