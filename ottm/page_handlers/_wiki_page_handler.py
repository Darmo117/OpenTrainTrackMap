"""This module defines the page handler and page context classes for wiki pages."""
from __future__ import annotations

import abc as _abc
import dataclasses as _dataclasses
import datetime as _dt
import re as _re
import typing as _typ

import django.contrib.auth.models as _dj_auth_models
import django.core.handlers.wsgi as _dj_wsgi
import django.core.paginator as _dj_paginator
import django.db.models as _dj_models
import django.forms as _dj_forms
from django.http import response as _dj_response

from . import _core, _ottm_handler, _wiki_base_form
from .. import models as _models, requests as _requests, settings as _settings
from ..api import errors as _errors, permissions as _permissions, utils as _utils
from ..api.wiki import (constants as _w_cons, namespaces as _w_ns, pages as _w_pages, special_pages as _w_sp)


class WikiPageHandler(_ottm_handler.OTTMHandler):
    """Handler for wiki pages."""

    def __init__(self, request: _dj_wsgi.WSGIRequest, raw_page_title: str):
        """Create a handler for the given wiki page.

        :param request: Client request.
        :param raw_page_title: Raw wiki page title.
        """
        super().__init__(request)
        self._raw_page_title = raw_page_title

    def _parse_page_title(self) -> _dj_response.HttpResponse | tuple[_w_ns.Namespace, str]:
        """Parse the page title and return the title as a tuple
        or a HttpResponse object if it is invalid or not well formatted.

        :return: A HttpResponse object or a tuple containing the page’s namespace and title.
        """
        # Redirect to wiki’s main page if title is empty
        if not self._raw_page_title:
            return self.redirect(
                'ottm:wiki_page',
                reverse=True,
                get_params=self._request_params.GET,
                raw_page_title=_w_pages.url_encode_page_title(_w_pages.MAIN_PAGE_TITLE),
            )

        # Remove all trailing '/'
        if match := _re.search('/+$', self._raw_page_title):
            return self.redirect(
                'ottm:wiki_page',
                reverse=True,
                get_params=self._request_params.GET,
                raw_page_title=self._raw_page_title[:-len(match.group(0))],
            )

        ns, title = _w_pages.split_title(_w_pages.get_correct_title(self._raw_page_title))
        # Check if title is empty
        if not title:
            page = _models.Page(namespace_id=_w_ns.NS_SPECIAL.id, title=title)
            js_config = _w_pages.get_js_config(self._request_params, page)
            return self.render_page(
                'ottm/wiki/page.html',
                self._page_error_context(page, js_config, empty_title=True),
                status=400,
                kwargs={
                    **_w_cons.__dict__,
                    **_w_ns.NAMESPACES_DICT,
                    'MAIN_PAGE_TITLE': _w_pages.MAIN_PAGE_TITLE,
                })

        # Check if title is invalid
        if m := _settings.INVALID_TITLE_REGEX.search(title):
            page = _w_pages.get_page(_w_ns.NS_SPECIAL, title)
            js_config = _w_pages.get_js_config(self._request_params, page)
            return self.render_page(
                'ottm/wiki/page.html',
                self._page_error_context(page, js_config, char=m.group(1)),
                status=400,
                kwargs={
                    **_w_cons.__dict__,
                    **_w_ns.NAMESPACES_DICT,
                    'MAIN_PAGE_TITLE': _w_pages.MAIN_PAGE_TITLE,
                })

        # Redirect to well-formatted page title if necessary
        if self._raw_page_title != (t := _w_pages.url_encode_page_title(ns.get_full_page_title(title))):
            return self.redirect(
                'ottm:wiki_page',
                reverse=True,
                get_params=self._request_params.GET,
                raw_page_title=t,
            )

        return ns, title

    def handle_request(self) -> _dj_response.HttpResponse:
        result = self._parse_page_title()
        if isinstance(result, _dj_response.HttpResponse):
            return result

        ns, title = result
        page = _w_pages.get_page(ns, title)
        if ns == _w_ns.NS_SPECIAL:
            res = self._handle_special_page(page)
        else:
            res = self._handle_normal_page(page)
        if not isinstance(res, tuple):
            return res
        context, status = res

        return self.render_page('ottm/wiki/page.html', context, status=status, kwargs={
            **{k: v for k, v in _w_cons.__dict__.items() if k.startswith('ACTION_') or k.startswith('CT_')},
            **_w_ns.NAMESPACES_DICT,
            'MAIN_PAGE_TITLE': _w_pages.MAIN_PAGE_TITLE,
        })

    def _handle_special_page(self, page: _models.Page) \
            -> tuple[WikiSpecialPageContext, int] | _dj_response.HttpResponseRedirect:
        """Handle the given special page.

        :param page: Dummy Page object representing the special page.
        :return: A tuple containing a PageContext object and a status code, or a HttpResponseRedirect object.
        """
        special_page = _w_sp.SPECIAL_PAGES.get(page.base_name)
        if special_page is None:
            context = WikiSpecialPageContext(
                self._request_params,
                page=page,
                page_exists=False,
                forbidden=False,
                js_config=_w_pages.get_js_config(self._request_params, page),
            )
            status = 404
        elif not special_page.can_user_access(self._request_params.user):
            context = WikiSpecialPageContext(
                self._request_params,
                page=page,
                page_exists=True,
                forbidden=True,
                js_config=_w_pages.get_js_config(self._request_params, page),
                required_perms=special_page.permissions_required,
            )
            status = 403
        else:
            data = special_page.process_request(self._request_params, page.title)
            if isinstance(data, _w_sp.Redirect):
                args = {k: v for k, v in self._request_params.GET.items()}
                # Replace False and None values by an empty strings
                args.update({k: '' if v is False or v is None else v for k, v in data.args.items()})
                return self.redirect(
                    'ottm:wiki_page',
                    reverse=True,
                    get_params=args,
                    raw_page_title=_w_pages.url_encode_page_title(data.page_title),
                )
            context = WikiSpecialPageContext(
                self._request_params,
                page=page,
                page_exists=True,
                forbidden=False,
                js_config=_w_pages.get_js_config(self._request_params, page, data),
                required_perms=special_page.permissions_required,
                kwargs=data,
            )
            status = 200
        return context, status

    def _handle_normal_page(self, page: _models.Page) \
            -> tuple[WikiPageContext, int] | _dj_response.HttpResponseRedirect:
        """Handle the given page.

        :param page: A Page object.
        :return: A tuple containing a PageContext object and a status code, or a HttpResponseRedirect object.
        """
        revid: str | None = self._request_params.GET.get('revid')
        if revid and revid.isascii() and revid.isnumeric():
            revision_id = int(revid)
        else:
            revision_id = None
        js_config = _w_pages.get_js_config(self._request_params, page, revision_id=revision_id)

        match self._request_params.wiki_action:
            case _w_cons.ACTION_RAW:
                return self.response(
                    content=page.get_content(),
                    content_type=_w_cons.MIME_TYPES[page.content_type],
                    status=200 if page.exists else 404,
                )
            case _w_cons.ACTION_EDIT:
                context = self._page_edit_context(page, revision_id, js_config)
            case _w_cons.ACTION_SUBMIT:
                res = self._handle_submit_action(page, revision_id, js_config)
                if not isinstance(res, WikiPageContext):
                    return res
                context = res
            case _w_cons.ACTION_HISTORY:
                res = self._handle_history_action(page, js_config)
                if not isinstance(res, WikiPageContext):
                    return res
                context = res
            case _w_cons.ACTION_TALK:
                context = self._page_talk_context(page, js_config)
            case _w_cons.ACTION_INFO:
                context = self._page_info_context(page, js_config)
            case _:
                context = self._page_read_context(page, revision_id, js_config)
        status = 200 if context.page.exists else 404
        return context, status

    def _handle_submit_action(self, page: _models.Page, revision_id: int, js_config: dict[str, _typ.Any]) \
            -> WikiPageEditActionContext | _dj_response.HttpResponseRedirect:
        """Handle the submit action.

        :param page: A page object.
        :param revision_id: The page’s revision.
        :param js_config: The JS config dict object.
        :return: A PageContext or a HttpResponseRedirect object.
        """
        form = WikiEditPageForm(post=self._request_params.request.POST)
        if not form.is_valid():
            return self._page_edit_context(page, revision_id, js_config, form=form)
        try:
            _w_pages.edit_page(
                self._request_params.user,
                page,
                form.cleaned_data['content'],
                form.cleaned_data['comment'],
                form.cleaned_data['minor_edit'],
                form.cleaned_data['follow_page'],
                form.cleaned_data['hidden_category'],
                form.cleaned_data['section_id']
            )
        except _errors.MissingPermissionError:
            return self._page_edit_context(page, revision_id, js_config)
        except _errors.ConcurrentWikiEditError:
            # TODO textarea containing concurrent page content
            return self._page_edit_context(page, revision_id, js_config, concurrent_edit_error=True)
        # Redirect to normal view
        return self.redirect(
            'ottm:wiki_page',
            reverse=True,
            raw_page_title=_w_pages.url_encode_page_title(page.full_title),
        )

    def _handle_history_action(self, page: _models.Page, js_config: dict[str, _typ.Any]) \
            -> WikiPageHistoryActionContext | _dj_response.HttpResponseRedirect:
        """Handle the history action.

        :param page: A page object.
        :param js_config: The JS config dict object.
        :return: A PageContext or a HttpResponseRedirect object.
        """
        form = WikiHistoryFilterForm()
        global_errors = {form.name: []}
        revisions = _dj_auth_models.EmptyManager(_models.PageRevision).all()
        if self._request_params.POST:
            form = WikiHistoryFilterForm(post=self._request_params.POST)
            if form.is_valid():
                if (not form.cleaned_data['start_date'] or not form.cleaned_data['end_date']
                        or form.cleaned_data['start_date'] <= form.cleaned_data['end_date']):
                    return self.redirect(
                        'ottm:wiki_page',
                        reverse=True,
                        raw_page_title=_w_pages.url_encode_page_title(page.full_title),
                        get_params={
                            'action': 'history',
                            'hidden_revisions_only': form.cleaned_data['hidden_revisions_only'],
                            'page_creations_only': form.cleaned_data['page_creations_only'],
                            'mask_minor_edits': form.cleaned_data['mask_minor_edits'],
                            'start_date': form.cleaned_data['start_date'],
                            'end_date': form.cleaned_data['end_date'],
                        }
                    )
                global_errors[form.name].append('invalid_dates')
        else:
            form = WikiHistoryFilterForm(post=self._request_params.GET)
            if page.exists:
                query_set = page.revisions
                if self._request_params.user.has_permission(_permissions.PERM_MASK):
                    revisions = query_set.all()
                else:
                    revisions = query_set.filter(hidden=False)
                if form.is_valid():
                    if form.cleaned_data['hidden_revisions_only']:
                        revisions = revisions.filter(hidden=True)
                    if form.cleaned_data['page_creations_only']:
                        revisions = revisions.filter(page_creation=True)
                    if form.cleaned_data['mask_minor_edits']:
                        revisions = revisions.filter(is_minor=False)
                    if start_date := form.cleaned_data['start_date']:
                        revisions = revisions.filter(date__gte=start_date)
                    if end_date := form.cleaned_data['end_date']:
                        revisions = revisions.filter(date__lte=end_date)
        return self._page_history_context(page, js_config, revisions, form, global_errors)

    def _page_error_context(
            self,
            page: _models.Page,
            js_config: dict,
            char: str = None,
            empty_title: bool = False,
    ) -> WikiPageErrorContext:
        """Create a wiki pagcontexte error context object.

        :param page: Page object.
        :param js_config: Dict object containing JS config values.
        :param empty_title: Whether the page’s title is empty.
        :return: A WikiPageContext object.
        :param char: The invalid character.
        """
        return WikiPageErrorContext(
            self._request_params,
            page,
            js_config,
            char=char,
            empty_title=empty_title,
        )

    def _page_read_context(self, page: _models.Page, revision_id: int | None, js_config: dict) \
            -> WikiPageReadActionContext:
        """Create a wiki page read context object.

        :param page: Page object.
        :param revision_id: Page revision ID.
        :param js_config: Dict object containing JS config values.
        :return: A WikiPageContext object.
        """
        language = self._request_params.ui_language
        no_index = not page.exists
        cat_subcategories = []
        cat_pages = []
        archived = False
        if revision_id is None or not page.exists:
            if page.content_type != _w_cons.CT_WIKIPAGE:
                # Return non-minified content
                revision = page.revisions.latest() if page.exists else None
                content = revision.content if revision else None
                cache_metadata = None
            else:
                content = page.cached_parsed_content
                cache_metadata = CacheMetadata(
                    parse_duration=page.parse_time,
                    parse_date=page.parse_date,
                    size_before=page.size_before_parse,
                    size_after=page.size_after_parse,
                    cached_parsed_revision_id=page.cached_parsed_revision_id,
                    cache_expiry_date=page.cache_expiry_date,
                )
                revision = page.revisions.latest() if page.exists else None
            if page.namespace == _w_ns.NS_CATEGORY:
                cat_subcategories = list(_models.PageCategory.subcategories_for_category(page.full_title))
                cat_pages = list(_models.PageCategory.pages_for_category(page.full_title))
        else:
            try:
                revision = page.revisions.get(id=revision_id)
            except _models.PageRevision.DoesNotExist:
                revision = page.revisions.latest()
            else:
                if revision.hidden and not self._request_params.user.has_permission(_permissions.PERM_MASK):
                    revision = page.revisions.latest()
                else:
                    archived = True
            content, parse_metadata = _w_pages.render_wikicode(revision.content, page, revision)
            cache_metadata = CacheMetadata(
                parse_duration=parse_metadata.parse_duration,
                parse_date=parse_metadata.parse_date,
                size_before=parse_metadata.size_before,
                size_after=parse_metadata.size_after,
            )
        if not page.exists:
            no_page_notice = _w_pages.get_no_page_notice(language)
        else:
            no_page_notice = None
        return WikiPageReadActionContext(
            self._request_params,
            page=page,
            no_index=no_index,
            js_config=js_config,
            content=content,
            cache_metadata=cache_metadata,
            revision=revision,
            archived=archived,
            cat_subcategories=cat_subcategories,
            cat_pages=cat_pages,
            no_page_notice=no_page_notice,
        )

    def _page_info_context(self, page: _models.Page, js_config: dict) -> WikiPageInfoActionContext:
        """Create a wiki page info context object.

        :param page: Page object.
        :param js_config: Dict object containing JS config values.
        :return: A WikiPageContext object.
        """
        statuses = _models.PageFollowStatus.objects.filter(page_namespace_id=page.namespace_id, page_title=page.title)
        return WikiPageInfoActionContext(
            self._request_params,
            page=page,
            js_config=js_config,
            revisions=page.revisions.all() if page.exists else _dj_auth_models.EmptyManager(_models.PageRevision),
            followers_nb=statuses.count(),
            redirects_nb=page.get_redirects().count(),
            subpages_nb=page.get_subpages().count(),
            protection=page.get_edit_protection(),
        )

    def _page_edit_context(
            self,
            page: _models.Page,
            revision_id: int | None,
            js_config: dict,
            form: WikiEditPageForm = None,
            concurrent_edit_error: bool = False,
    ) -> WikiPageEditActionContext:
        """Create a wiki page editing context object.

        :param page: Page object.
        :param revision_id: Page revision ID.
        :param js_config: Dict object containing JS config values.
        :param form: Edit form object.
        :param concurrent_edit_error: Whether another edit was made before submitting.
        :return: A WikiPageContext object.
        """
        archived = False
        if revision_id is None or not page.exists:
            revision = page.revisions.latest() if page.exists else None
        else:
            try:
                revision = page.revisions.get(id=revision_id)
            except _models.PageRevision.DoesNotExist:
                revision = page.revisions.latest()
            else:
                archived = True
        user = self._request_params.user
        language = self._request_params.ui_language
        follow = (page.is_user_following(user)
                  or user.add_modified_pages_to_follow_list
                  or (not page.exists and user.add_created_pages_to_follow_list))
        deletion_log_entry = None
        if page.deleted:
            try:
                deletion_log_entry = _models.PageDeletionLog.objects.filter(page=page).latest()
            except _models.PageDeletionLog.DoesNotExist:
                pass
        form = form or WikiEditPageForm(
            user=user,
            page=page,
            disabled=not page.can_user_edit(user),
            warn_unsaved_changes=True,
            initial={
                'content': revision.content if revision else '',
                'follow_page': follow,
                'hidden_category': page.is_category_hidden,
                'minor_edit': user.mark_all_wiki_edits_as_minor,
            },
        )
        return WikiPageEditActionContext(
            self._request_params,
            page=page,
            js_config=js_config,
            revision=revision,
            archived=archived,
            edit_form=form,
            edit_notice=_w_pages.get_edit_notice(language, page),
            new_page_notice=_w_pages.get_new_page_notice(language, page) if not page.exists else None,
            perm_error=not page.can_user_edit(user),
            concurrent_edit_error=concurrent_edit_error,
            edit_protection_log_entry=_w_pages.get_page_protection_log_entry(page),
            deletion_log_entry=deletion_log_entry,
        )

    def _page_talk_context(self, page: _models.Page, js_config: dict) -> WikiPageTalkActionContext:
        """Create a wiki page talk context object.

        :param page: Page object.
        :param js_config: Dict object containing JS config values.
        :return: A WikiPageContext object.
        """
        user = self._request_params.user
        if page.exists:
            if user.has_permission(_permissions.PERM_MASK):
                topics = page.topics.all()
            else:
                topics = page.topics.filter(deleted=False)
        else:
            topics = _dj_auth_models.EmptyManager(_models.TopicRevision)
        if (pp := page.get_edit_protection()) and pp.protect_talks:
            log_entry = _w_pages.get_page_protection_log_entry(page)
        else:
            log_entry = None
        return WikiPageTalkActionContext(
            self._request_params,
            page=page,
            js_config=js_config,
            topics=topics.order_by('-date'),
            edit_protection_log_entry=log_entry,
        )

    def _page_history_context(
            self,
            page: _models.Page,
            js_config: dict,
            revisions: _dj_models.QuerySet[_models.PageRevision],
            form: WikiHistoryFilterForm,
            global_errors: dict[str, list[str]],
    ) -> WikiPageHistoryActionContext:
        """Create a wiki page history context object.

        :param page: Page object.
        :param js_config: Dict object containing JS config values.
        :param revisions: List of revisions.
        :param form: The filter form.
        :param global_errors: Global errors.
        :return: A WikiPageContext object.
        """
        return WikiPageHistoryActionContext(
            self._request_params,
            page=page,
            js_config=js_config,
            revisions=revisions.order_by('-date'),
            form=form,
            global_errors=global_errors,
        )


class WikiEditPageForm(_wiki_base_form.WikiForm):
    """Form used to edit a wiki page."""
    content = _dj_forms.CharField(
        label='content',
        required=False,
        widget=_dj_forms.Textarea(attrs={'rows': 20})
    )
    comment = _dj_forms.CharField(
        label='comment',
        max_length=_models.PageRevision._meta.get_field('comment').max_length,
        strip=True,
        required=False
    )
    minor_edit = _dj_forms.BooleanField(
        label='minor_edit',
        required=False
    )
    follow_page = _dj_forms.BooleanField(
        label='follow_page',
        required=False
    )
    hidden_category = _dj_forms.BooleanField(
        label='hidden_category',
        required=False
    )
    # ID of the page section being edited (optional).
    section_id = _dj_forms.CharField(
        widget=_dj_forms.HiddenInput(),
        required=False
    )

    def __init__(self, user: _models.User = None, page: _models.Page = None, disabled: bool = False,
                 warn_unsaved_changes: bool = True, post=None, initial: dict[str, _typ.Any] = None):
        """Create a page edit form.

        :param user: The user to send the form to.
        :param page: The page this form will be associated to.
        :param disabled: If true, the content field will be disabled and all others will not be generated.
        :param warn_unsaved_changes: Whether to display a warning whenever a user quits
            the page without submitting this form.
        :param post: A POST dict to populate this form.
        :param initial: A dict object of initial field values.
        """
        super().__init__('edit', warn_unsaved_changes, post=post, initial=initial)

        if user and not user.is_authenticated:
            self.fields['follow_page'].widget.attrs['disabled'] = True
        if page and page.namespace != _w_ns.NS_CATEGORY:
            self.fields['hidden_category'].widget.attrs['disabled'] = True
        if disabled:
            self.fields['content'].widget.attrs['disabled'] = True


class WikiHistoryFilterForm(_wiki_base_form.WikiForm):
    hidden_revisions_only = _dj_forms.BooleanField(
        label='hidden_revisions_only',
        required=False,
    )
    page_creations_only = _dj_forms.BooleanField(
        label='page_creations_only',
        required=False,
    )
    mask_minor_edits = _dj_forms.BooleanField(
        label='mask_minor_edits',
        required=False,
    )
    start_date = _dj_forms.DateField(
        label='start_date',
        widget=_dj_forms.DateInput(attrs={'type': 'date'}),
        required=False,
    )
    end_date = _dj_forms.DateField(
        label='end_date',
        widget=_dj_forms.DateInput(attrs={'type': 'date'}),
        required=False,
    )

    def __init__(self, post=None, initial=None):
        super().__init__('filter', False, post=post, initial=initial)


class WikiPageContext(_core.PageContext, _abc.ABC):
    """Base class for wiki page context classes."""

    def __init__(
            self,
            request_params: _requests.RequestParams,
            page: _models.Page,
            no_index: bool,
            show_title: bool,
            page_exists: bool,
            forbidden: bool,
            js_config: dict[str, _typ.Any],
            max_page_index: int = None,
    ):
        """Create a page context for a wiki page.

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
            tab_title=page.full_title,
            title=page.title,
            no_index=no_index,
            max_page_index=max_page_index,
        )
        self._page = page
        self._show_title = show_title
        self._page_exists = page_exists
        self._forbidden = forbidden
        if page.namespace.allows_subpages and '/' in page.title:
            self._parent_pages = page.get_parent_page_titles()
        else:
            self._parent_pages = []
        self._js_config['config'].update(js_config['config'])
        self._js_config['page'].update(js_config['page'])
        self._js_config['user'].update(js_config['user'])

    @property
    def invalid_title(self) -> bool:
        return False

    @property
    def main_page_full_title(self) -> str:
        return _w_pages.MAIN_PAGE_TITLE

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
    def forbidden(self) -> bool:
        return self._forbidden

    @property
    def can_user_edit(self) -> bool:
        return self.page.can_user_edit(self.user)

    @property
    def parent_pages(self) -> list[_models.Page]:
        return self._parent_pages


class WikiPageErrorContext(WikiPageContext):
    """Context class for page errors."""

    def __init__(
            self,
            request_params: _requests.RequestParams,
            page: _models.Page,
            js_config: dict[str, _typ.Any],
            char: str = None,
            empty_title: bool = False,
    ):
        """Create a page context for a wiki page with an invalid title.

        :param request_params: Page request parameters.
        :param page: Wiki page object.
        :param js_config: Dict object containing the wiki’s JS config.
            It is converted to a JSON object before being inserted in the HTML page.
        :param char: The invalid character.
        :param empty_title: Whether the page’s title is empty.
        """
        super().__init__(
            request_params,
            page=page,
            no_index=True,
            show_title=True,
            page_exists=False,
            forbidden=False,
            js_config=js_config,
        )
        self._char = char
        self._empty_title = empty_title

    @property
    def invalid_title(self) -> bool:
        return True

    @property
    def char(self) -> str | None:
        return self._char

    @property
    def empty_title(self) -> bool:
        return self._empty_title


@_dataclasses.dataclass(frozen=True)
class CacheMetadata:
    parse_duration: int
    parse_date: _dt.datetime
    size_before: int
    size_after: int
    cached_parsed_revision_id: int = None
    cache_expiry_date: _dt.datetime = None


class WikiPageReadActionContext(WikiPageContext):
    """Context class for the 'read' action."""

    def __init__(
            self,
            request_params: _requests.RequestParams,
            page: _models.Page,
            no_index: bool,
            js_config: dict[str, _typ.Any],
            content: str,
            cache_metadata: CacheMetadata | None,
            revision: _models.PageRevision | None,
            archived: bool,
            cat_subcategories: list[_models.Page] = None,
            cat_pages: list[_models.Page] = None,
            no_page_notice: str = None,
    ):
        """Create a page context for a wiki page with the 'read' action.

        :param request_params: Page request parameters.
        :param page: Wiki page object.
        :param no_index: Whether to insert a noindex clause within the HTML page.
        :param js_config: Dict object containing the wiki’s JS config.
            It is converted to a JSON object before being inserted in the HTML page.
        :param content: Rendered page’s content.
        :param cache_metadata: The metadata object for the page’s cache.
        :param revision: A revision of the page. May be None.
        :param archived: Whether the revision is not the current one.
        :param cat_subcategories: The list of subcategories of the category represented by the page.
            Only used if the page is a category.
        :param cat_pages: The list of pages within the category represented by the page.
            Only used if the page is a category.
        :param no_page_notice: The rendered notice if the page does not exist.
        """
        self._cat_pages = _dj_paginator.Paginator(cat_pages or [], request_params.results_per_page)
        show_title = page.full_title != _w_pages.MAIN_PAGE_TITLE
        super().__init__(
            request_params,
            page=page,
            no_index=no_index,
            show_title=show_title,
            page_exists=page.exists,
            forbidden=False,
            js_config=js_config,
            max_page_index=self._cat_pages.num_pages,
        )
        self._content = content
        self._cache_metadata = cache_metadata
        self._revision = revision
        self._archived = archived
        self._cat_subcategories = cat_subcategories or []
        self._no_page_notice = no_page_notice

    @property
    def page_content(self) -> str:
        return self._content

    @property
    def page_cache_metadata(self) -> CacheMetadata | None:
        return self._cache_metadata

    @property
    def page_language(self) -> str:
        return _w_cons.LANGUAGE_CODES[self.page.content_type]

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
    def cat_pages(self) -> _dj_paginator.Paginator:
        return self._cat_pages

    @property
    def no_page_notice(self) -> str | None:
        return self._no_page_notice


class WikiPageInfoActionContext(WikiPageContext):
    """Context class for the 'info' action."""

    def __init__(
            self,
            request_params: _requests.RequestParams,
            page: _models.Page,
            js_config: dict[str, _typ.Any],
            revisions: _dj_models.QuerySet[_models.PageRevision],
            followers_nb: int,
            redirects_nb: int,
            subpages_nb: int,
            protection: _models.PageProtection | None,
    ):
        """Create a page context for a wiki page with the 'info' action.

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
            forbidden=False,
            js_config=js_config,
        )
        self._revisions = revisions
        self._recent_revisions = revisions.filter(date__gte=_utils.now() - _dt.timedelta(days=self.recent_range))
        self._recent_editors_nb = self._recent_revisions.aggregate(
            _dj_models.Count('author', distinct=True))['author__count']
        self._followers_nb = followers_nb
        self._redirects_nb = redirects_nb
        self._subpages_nb = subpages_nb
        self._protection = protection

    @property
    def recent_range(self) -> int:
        return 30

    @property
    def revisions(self) -> _dj_models.QuerySet[_models.PageRevision]:
        return self._revisions

    @property
    def recent_revisions(self) -> _dj_models.QuerySet[_models.PageRevision]:
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
    """Context class for the 'edit' action."""

    def __init__(
            self,
            request_params: _requests.RequestParams,
            page: _models.Page,
            js_config: dict[str, _typ.Any],
            revision: _models.PageRevision | None,
            archived: bool,
            edit_form: WikiEditPageForm,
            edit_notice: str = None,
            new_page_notice: str = None,
            perm_error: bool = False,
            concurrent_edit_error: bool = False,
            edit_protection_log_entry: _models.PageProtectionLog = None,
            deletion_log_entry: _models.PageDeletionLog = None,
    ):
        """Create a page context for a wiki page with the 'edit' action.

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
        :param deletion_log_entry: The page’s latest PageDeletionLog entry if it has been deleted.
        """
        super().__init__(
            request_params,
            page=page,
            no_index=True,
            show_title=True,
            page_exists=page.exists,
            forbidden=False,
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
        self._deletion_log_entry = deletion_log_entry

    @property
    def archived(self) -> bool:
        return self._archived

    @property
    def revision(self) -> _models.PageRevision | None:
        return self._revision

    @property
    def edit_form(self) -> WikiEditPageForm:
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

    @property
    def deletion_log_entry(self) -> _models.PageDeletionLog | None:
        return self._deletion_log_entry


class WikiPageTalkActionContext(WikiPageContext):
    """Context class for the 'talk' action."""

    def __init__(
            self,
            request_params: _requests.RequestParams,
            page: _models.Page,
            js_config: dict[str, _typ.Any],
            topics: list[_models.Topic],
            edit_protection_log_entry: _models.PageProtectionLog = None,
    ):
        """Create a page context for a wiki page with the 'talk' action.

        :param request_params: Page request parameters.
        :param page: Wiki page object.
        :param js_config: Dict object containing the wiki’s JS config.
         It is converted to a JSON object before being inserted in the HTML page.
        :param topics: List of page talk topics.
        :param edit_protection_log_entry: The page’s PageProtectionLog entry if it exists.
        """
        self._topics = _dj_paginator.Paginator(topics, request_params.results_per_page)
        super().__init__(
            request_params,
            page=page,
            no_index=True,
            show_title=True,
            page_exists=page.exists,
            forbidden=False,
            js_config=js_config,
            max_page_index=self._topics.num_pages,
        )
        self._edit_protection_log_entry = edit_protection_log_entry

    @property
    def topics(self) -> _dj_paginator.Paginator:
        return self._topics

    @property
    def edit_protection_log_entry(self) -> _models.PageProtectionLog | None:
        return self._edit_protection_log_entry


class WikiPageHistoryActionContext(WikiPageContext):
    """Context class for the 'history' action."""

    def __init__(
            self,
            request_params: _requests.RequestParams,
            page: _models.Page,
            js_config: dict[str, _typ.Any],
            revisions: _dj_models.QuerySet[_models.PageRevision],
            form: WikiHistoryFilterForm,
            global_errors: dict[str, list[str]],
    ):
        """Create a page context for a wiki page with the 'history' action.

        :param request_params: Page request parameters.
        :param page: Wiki page object.
        :param js_config: Dict object containing the wiki’s JS config.
         It is converted to a JSON object before being inserted in the HTML page.
        :param revisions: List of page revisions.
        :param form: The filter form.
        :param global_errors: Global errors.
        """
        self._revisions = _dj_paginator.Paginator(revisions, request_params.results_per_page)
        super().__init__(
            request_params,
            page=page,
            no_index=True,
            show_title=True,
            page_exists=page.exists,
            forbidden=False,
            js_config=js_config,
            max_page_index=self._revisions.num_pages,
        )
        self._form = form
        self._global_errors = global_errors

    @property
    def revisions(self) -> _dj_paginator.Paginator:
        return self._revisions

    @property
    def form(self):
        return self._form

    @property
    def global_errors(self) -> dict[str, list[str]]:
        return self._global_errors


class WikiSpecialPageContext(WikiPageContext):
    """Context class for special pages."""

    def __init__(
            self,
            request_params: _requests.RequestParams,
            page: _models.Page,
            page_exists: bool,
            forbidden: bool,
            js_config: dict[str, _typ.Any],
            required_perms: tuple[str, ...] = (),
            kwargs: dict[str, _typ.Any] = None,
    ):
        """Create a page context for a special page.

        :param request_params: Page request parameters.
        :param page: Wiki page object.
        :param page_exists: Whether the page exists.
        :param forbidden: Whether the user is forbidden from reading the page.
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
            forbidden=forbidden,
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
