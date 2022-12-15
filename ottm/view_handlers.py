"""This module defines handlers for the different views."""
import typing as typ

from django.conf import settings as dj_settings
import django.contrib.auth.models as dj_auth_models

from . import forms, models, page_context, requests
from .api import permissions
from .api.wiki import namespaces as w_ns, pages as w_pages

VIEW_MAP = 'show'
EDIT_MAP = 'edit'
MAP_HISTORY = 'history'


def get_page_context(
        request_params: requests.RequestParams,
        page_id: str,
        no_index: bool = False,
        titles_args: dict[str, str] = None,
) -> page_context.PageContext:
    """Return a context object for the given page ID.

    :param request_params: Request parameters.
    :param page_id: Page’s ID.
    :param no_index: Whether to insert a noindex clause within the HTML page.
    :param titles_args: Dict object containing values to use in the page title translation.
    :return: A PageContext object.
    """
    return page_context.PageContext(
        request_params,
        **_get_title_args(request_params, page_id=page_id, titles_args=titles_args),
        no_index=no_index,
    )


def get_map_page_context(
        request_params: requests.RequestParams,
        action: str = VIEW_MAP,
        no_index: bool = False,
) -> page_context.MapPageContext:
    """Return a context object for the map page.

    :param request_params: Request parameters.
    :param action: Map action.
    :param no_index: Whether to insert a noindex clause within the HTML page.
    :return: A MapPageContext object.
    """
    translations_keys = [
        'map.controls.layers.standard',
        'map.controls.layers.black_and_white',
        'map.controls.layers.satellite_maptiler',
        'map.controls.layers.satellite_esri',
        'map.controls.zoom_in.tooltip',
        'map.controls.zoom_out.tooltip',
        'map.controls.search.tooltip',
        'map.controls.search.placeholder',
        'map.controls.google_maps_button.tooltip',
        'map.controls.ign_compare_button.label',
        'map.controls.ign_compare_button.tooltip',
        'map.controls.edit.new_marker.tooltip',
        'map.controls.edit.new_line.tooltip',
        'map.controls.edit.new_polygon.tooltip',
    ]
    js_config = {
        'trans': {},
        'static_path': dj_settings.STATIC_URL,
        'edit': 'true' if action == 'edit' else 'false',
    }

    for k in translations_keys:
        js_config['trans'][k] = request_params.ui_language.translate(k)

    return page_context.MapPageContext(
        request_params,
        **_get_title_args(request_params),
        no_index=no_index,
        map_js_config=js_config,
    )


def get_sign_up_page_context(
        request_params: requests.RequestParams,
        form: forms.SignUpForm = None,
) -> page_context.SignUpPageContext:
    """Return a context object for the sign up page.

    :param request_params: Request parameters.
    :param form: Sign up form.
    :return: A SignUpPageContext object.
    """
    return page_context.SignUpPageContext(
        request_params,
        **_get_title_args(request_params, page_id='sign_up'),
        no_index=False,
        form=form,
    )


def get_user_page_context(
        request_params: requests.RequestParams,
        target_user: models.User,
) -> page_context.UserPageContext:
    """Return a context object for the user profile page.

    :param request_params: Request parameters.
    :param target_user: User of the requested page.
    :return: A UserPageContext object.
    """
    titles_args = {'username': target_user.username}
    return page_context.UserPageContext(
        request_params,
        **_get_title_args(request_params, page_id='user_profile', titles_args=titles_args),
        target_user=target_user,
    )


def _get_title_args(
        request_params: requests.RequestParams,
        page_id: str = None,
        titles_args: dict[str, str] = None,
) -> dict[str, typ.Any]:
    """Return parameters common to all page context objects.

    :param request_params: Request parameters.
    :param page_id: ID of the page.
    :param titles_args: Dict object containing values to use in the page title translation.
    :return: A dict object containing context parameters.
    """
    language = request_params.ui_language
    if page_id:
        title = language.translate(f'page.{page_id}.title')
        tab_title = language.translate(f'page.{page_id}.tab_title')
        if titles_args:
            title = title.format(**titles_args)
            tab_title = tab_title.format(**titles_args)
    else:
        title = None
        tab_title = None
    return {
        'title': title,
        'tab_title': tab_title,
    }


def wiki_page_read_context(
        request_params: requests.RequestParams,
        page: models.Page,
        revision_id: int | None,
        js_config: dict,
) -> page_context.WikiPageReadActionContext:
    """Create a wiki page context object.

    :param request_params: Request parameters.
    :param page: Page object.
    :param revision_id: Page revision ID.
    :param js_config: Dict object containing JS config values.
    :return: A WikiPageContext object.
    """
    user = request_params.user
    language = request_params.ui_language
    no_index = not page.exists
    cat_subcategories = []
    cat_pages = []
    if revision_id is None:
        content = w_pages.render_wikicode(page.get_content(), user, language)
        revision = page.revisions.latest() if page.exists else None
        archived = False
        if page.namespace == w_ns.NS_CATEGORY:
            cat_subcategories = list(models.PageCategory.subcategories_for_category(page.full_title))
            cat_pages = list(models.PageCategory.pages_for_category(page.full_title))
    else:
        revision = page.revisions.get(id=revision_id)
        content = w_pages.render_wikicode(revision.content, user, language)
        archived = True
    if not page.exists:
        no_page_notice = w_pages.get_no_page_notice(user, language)
    else:
        no_page_notice = None
    return page_context.WikiPageReadActionContext(
        request_params,
        page=page,
        no_index=no_index,
        js_config=js_config,
        content=content,
        revision=revision,
        archived=archived,
        cat_subcategories=cat_subcategories,
        cat_pages=cat_pages,
        no_page_notice=no_page_notice,
    )


def wiki_page_info_context(request_params: requests.RequestParams, page: models.Page, js_config: dict) \
        -> page_context.WikiPageInfoActionContext:
    """Create a wiki page info context object.

    :param request_params: Request parameters.
    :param page: Page object.
    :param js_config: Dict object containing JS config values.
    :return: A WikiPageContext object.
    """
    statuses = models.PageFollowStatus.objects.filter(page_namespace_id=page.namespace_id, page_title=page.title)
    return page_context.WikiPageInfoActionContext(
        request_params,
        page=page,
        js_config=js_config,
        revisions=page.revisions.all() if page.exists else dj_auth_models.EmptyManager(models.PageRevision),
        followers_nb=statuses.count(),
        redirects_nb=page.get_redirects().count(),
        subpages_nb=page.get_subpages().count(),
        protection=page.get_edit_protection(),
    )


def wiki_page_edit_context(
        request_params: requests.RequestParams,
        page: models.Page,
        revision_id: int | None,
        js_config: dict,
        form: forms.WikiEditPageForm = None,
        concurrent_edit_error: bool = False,
) -> page_context.WikiPageEditActionContext:
    """Create a wiki page editing context object.

    :param request_params: Request parameters.
    :param page: Page object.
    :param revision_id: Page revision ID.
    :param js_config: Dict object containing JS config values.
    :param form: Edit form object.
    :param concurrent_edit_error: Whether another edit was made before submitting.
    :return: A WikiPageContext object.
    """
    if revision_id is None:
        revision = page.revisions.latest() if page.exists else None
        archived = False
    else:
        revision = page.revisions.get(id=revision_id)
        archived = True
    user = request_params.user
    language = request_params.ui_language
    form = form or forms.WikiEditPageForm(
        user=user,
        page=page,
        disabled=not page.can_user_edit(user),
        warn_unsaved_changes=True,
        initial={
            'content': revision.content if revision else '',
            'follow_page': page.is_user_following(user),
            'hidden_category': page.is_category_hidden,
        },
    )
    return page_context.WikiPageEditActionContext(
        request_params,
        page=page,
        js_config=js_config,
        revision=revision,
        archived=archived,
        edit_form=form,
        edit_notice=w_pages.get_edit_notice(user, language, page),
        new_page_notice=w_pages.get_new_page_notice(user, language, page) if not page.exists else None,
        perm_error=not page.can_user_edit(user),
        concurrent_edit_error=concurrent_edit_error,
        edit_protection_log_entry=w_pages.get_page_protection_log_entry(page),
    )


def wiki_page_talk_context(request_params: requests.RequestParams, page: models.Page, js_config: dict) \
        -> page_context.WikiPageTalkActionContext:
    """Create a wiki page talk context object.

    :param request_params: Request parameters.
    :param page: Page object.
    :param js_config: Dict object containing JS config values.
    :return: A WikiPageContext object.
    """
    user = request_params.user
    if page.exists:
        if user.has_permission(permissions.PERM_WIKI_MASK):
            topics = page.topics.all()
        else:
            topics = page.topics.filter(deleted=False)
    else:
        topics = dj_auth_models.EmptyManager(models.TopicRevision)
    return page_context.WikiPageTalkActionContext(
        request_params,
        page=page,
        js_config=js_config,
        topics=topics.order_by('-date'),
    )


def wiki_page_history_context(request_params: requests.RequestParams, page: models.Page, js_config: dict) \
        -> page_context.WikiPageHistoryActionContext:
    """Create a wiki page history context object.

    :param request_params: Request parameters.
    :param page: Page object.
    :param js_config: Dict object containing JS config values.
    :return: A WikiPageContext object.
    """
    user = request_params.user
    if page.exists:
        if user.has_permission(permissions.PERM_WIKI_MASK):
            revisions = page.revisions.all()
        else:
            revisions = page.revisions.filter(hidden=False)
    else:
        revisions = dj_auth_models.EmptyManager(models.PageRevision)
    return page_context.WikiPageHistoryActionContext(
        request_params,
        page=page,
        js_config=js_config,
        revisions=revisions.order_by('-date'),
    )
