"""This module defines all page view handlers."""
import typing as typ

import django.core.handlers.wsgi as dj_wsgi
import django.http.response as dj_response
import django.shortcuts as dj_scut
import requests
from django.conf import settings as dj_settings

from . import forms, models, page_context, settings, wiki_special_pages
from .api import auth, errors, permissions
from .api.wiki import constants as w_cons, namespaces as w_ns, pages as w_pages

VIEW_MAP = 'show'
EDIT_MAP = 'edit'
MAP_HISTORY = 'history'


def get_tile(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    """API view that handles map tile querying.

    Expected GET parameters:
        - provider (str): Name of the tile provider.
        - x (int): Tile’s x position.
        - y (int): Tile’s y position.
        - z (int): Zoom value.
    """
    try:
        x = int(request.GET.get('x'))
        y = int(request.GET.get('y'))
        z = int(request.GET.get('z'))
    except ValueError:
        return dj_response.HttpResponseBadRequest()
    provider = request.GET.get('provider')
    if provider == 'maptiler':
        url = f'https://api.maptiler.com/tiles/satellite/{z}/{x}/{y}.jpg?key=5PelNcEc4zGc3OEutmIG'
        response = requests.get(url)
        # Remove Connection header as it may cause issues with Django
        del response.headers['Connection']
        return dj_response.HttpResponse(response.content, status=response.status_code, headers=response.headers)
    return dj_response.HttpResponseNotFound(f'invalid provider {provider}')


def map_page(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    """OTTM map page handler."""
    user = auth.get_user_from_request(request)
    language = _get_page_language(request, user)

    return dj_scut.render(request, 'ottm/map.html', context={
        'context': _get_map_page_context(request, user, auth.get_ip(request))
    })


# TODO redirect to login page with alert-warning if user not logged in
def edit_page(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    """OTTM map editing page handler."""
    user = auth.get_user_from_request(request)

    return dj_scut.render(request, 'ottm/map.html', context={
        'context': _get_map_page_context(request, user, action=EDIT_MAP, no_index=True)
    })


def history_page(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    """OTTM map history page handler."""
    user = auth.get_user_from_request(request)

    return dj_scut.render(request, 'ottm/map.html', context={
        'context': _get_map_page_context(request, user, action=MAP_HISTORY, no_index=True)
    })


def page_handler(page_name: str) -> typ.Callable[[dj_wsgi.WSGIRequest], dj_response.HttpResponse]:
    """Generate a page view handler for the given page name.

    :param page_name: Page’s name.
    :return: The view function.
    """

    def handler(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
        user = auth.get_user_from_request(request)
        return dj_scut.render(request, f'ottm/{page_name}.html', context={
            'context': _get_page_context(request, user, page_name)
        })

    return handler


def signup_page(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    """Sign-up page handler."""
    pass  # TODO


def login_page(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    """Login page handler."""
    pass  # TODO


def logout_page(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    """Logout page handler."""
    if auth.get_user_from_request(request).is_authenticated:
        auth.log_out(request)
    return dj_response.HttpResponseRedirect(_get_referer_url(request))


def user_profile(request: dj_wsgi.WSGIRequest, username: str) -> dj_response.HttpResponse:
    """User profile page handler."""
    user = auth.get_user_from_request(request)
    target_user = auth.get_user_from_name(username)
    return dj_scut.render(request, 'ottm/user-profile.html', context={
        'context': _get_user_page_context(request, user, target_user)
    })


def user_settings(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    """User settings page handler."""
    user = auth.get_user_from_request(request)

    if not user.is_authenticated:
        return dj_response.HttpResponseRedirect(dj_scut.reverse('ottm:map'))

    return dj_scut.render(request, 'ottm/user-settings.html', context={
        'context': _get_page_context(request, user, 'user_settings')
    })


def user_contributions(request: dj_wsgi.WSGIRequest, username: str) -> dj_response.HttpResponse:
    """User OTTM contributions page handler."""
    user = auth.get_user_from_request(request)
    target_user = auth.get_user_from_name(username)

    return dj_scut.render(request, 'ottm/map.html', context={
        'context': _get_map_page_context(request, user, action=MAP_HISTORY)
    })


def user_notes(request: dj_wsgi.WSGIRequest, username: str) -> dj_response.HttpResponse:
    """User notes page handler."""
    user = auth.get_user_from_request(request)
    target_user = auth.get_user_from_name(username)

    return dj_scut.render(request, 'ottm/user-notes.html', context={
        'context': _get_page_context(request, user, 'notes', no_index=True)
    })


def wiki_page(request: dj_wsgi.WSGIRequest, raw_page_title: str = '') -> dj_response.HttpResponse:
    """Wiki page handler.

    :param request: Client request.
    :param raw_page_title: Page title extracted from the URL.
    """
    if not raw_page_title:
        return dj_response.HttpResponseRedirect(dj_scut.reverse('ottm:wiki_page', kwargs={
            'raw_page_title': w_pages.url_encode_page_title(w_pages.MAIN_PAGE_TITLE)
        }))
    site_name = settings.SITE_NAME
    kwargs = request.GET
    user = auth.get_user_from_request(request)
    language = _get_page_language(request, user)
    dark_mode = _get_dark_mode_status(request, user)
    page_title = w_pages.get_correct_title(raw_page_title)
    ns, title = w_pages.split_title(page_title)
    action = kwargs.get('action', w_cons.ACTION_READ)
    page = w_pages.get_page(ns, title)
    js_config = w_pages.get_js_config(page, action)
    results_per_page = kwargs.get('results_per_page', 20)
    page_index = kwargs.get('page', 1)

    if ns == w_ns.NS_SPECIAL:
        special_page = wiki_special_pages.SPECIAL_PAGES.get(title)
        if special_page is None:
            context = page_context.WikiSpecialPageContext(
                site_name=site_name,
                page=page,
                user=user,
                language=language,
                dark_mode=dark_mode,
                page_exists=False,
                js_config=js_config,
            )
            status = 404
        elif not special_page.can_user_access(user):
            context = page_context.WikiSpecialPageContext(
                site_name=site_name,
                page=page,
                user=user,
                language=language,
                dark_mode=dark_mode,
                page_exists=True,
                js_config=js_config,
                required_perms=special_page.permissions_required,
            )
            status = 403
        else:
            data = special_page.process_request(request, title, **kwargs)
            context = page_context.WikiSpecialPageContext(
                site_name=site_name,
                page=page,
                user=user,
                language=language,
                dark_mode=dark_mode,
                page_exists=True,
                js_config=js_config,
                **data,
            )
            status = 200

    else:
        revid: str | None = kwargs.get('revid')
        if revid and revid.isascii() and revid.isnumeric():
            revision_id = int(revid)
        else:
            revision_id = None

        match action:
            case w_cons.ACTION_RAW:
                return dj_response.HttpResponse(
                    content=page.get_content(),
                    content_type=w_cons.MIME_TYPES[page.content_type],
                    status=200 if page.exists else 404,
                )
            case w_cons.ACTION_EDIT:
                context = _wiki_page_edit_context(page, user, language, dark_mode, revision_id, js_config)
            case w_cons.ACTION_SUBMIT:
                form = forms.WikiEditPageForm(request.POST)
                if not form.is_valid():
                    context = _wiki_page_edit_context(page, user, language, dark_mode, revision_id, js_config,
                                                      form=form)
                else:
                    try:
                        w_pages.edit_page(request, user, page, form.content, form.comment, form.minor_edit,
                                          form.follow_page, form.section_id)
                    except errors.MissingPermissionError:
                        context = _wiki_page_edit_context(page, user, language, dark_mode, revision_id, js_config,
                                                          perm_error=True)
                    except errors.ConcurrentWikiEditError:
                        # TODO form containing concurrent page content
                        context = _wiki_page_edit_context(page, user, language, dark_mode, revision_id, js_config,
                                                          concurrent_edit_error=True)
                    else:
                        # Redirect to normal view
                        return dj_response.HttpResponseRedirect(dj_scut.reverse('ottm:wiki_page', kwargs={
                            'raw_page_title': page.full_title,
                        }))
            case w_cons.ACTION_HISTORY:
                context = _wiki_page_history_context(page, user, language, dark_mode, results_per_page, page_index,
                                                     js_config)
            case w_cons.ACTION_TALK:
                context = _wiki_page_talk_context(page, user, language, dark_mode, results_per_page, page_index,
                                                  js_config)
            case w_cons.ACTION_INFO:
                # TODO gather page info
                context = None
            case _:
                context = _show_wiki_page_context(page, user, language, dark_mode, revision_id, results_per_page,
                                                  page_index, js_config)
        status = 200 if context.page.exists else 404

    ctxt = {
        'context': context,
        **w_cons.__dict__,
        **w_ns.NAMESPACES_DICT,
    }
    return dj_scut.render(request, 'ottm/wiki/page.html', context=ctxt, status=status)


def handle404(request: dj_wsgi.WSGIRequest, _) -> dj_response.HttpResponse:
    """404 error page handler."""
    pass  # TODO 404


def handle500(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    """500 error page handler."""
    pass  # TODO 500


#####################
# Utility functions #
#####################


def _get_referer_url(request: dj_wsgi.WSGIRequest) -> str:
    """Return the value of 'return_to' GET parameter or '/' if it is undefined."""
    return request.GET.get('return_to', '/')


def _get_page_language(request: dj_wsgi.WSGIRequest, user: models.User) -> settings.UILanguage:
    """Return the language for the page.

    :param request: Client request.
    :param user: Current user.
    :return: Page’s language.
    """
    if (lang_code := request.GET.get('lang')) and lang_code in settings.LANGUAGES:
        return settings.LANGUAGES[lang_code]
    elif (lang_code := request.COOKIES.get('language')) and lang_code in settings.LANGUAGES:
        return settings.LANGUAGES[lang_code]
    else:
        return user.prefered_language


def _get_dark_mode_status(request: dj_wsgi.WSGIRequest, user: models.User) -> bool:
    """Return the dark mode status for the page.

    :param request: Client request.
    :param user: Current user.
    :return: True if the dark mode is active, false otherwise.
    """
    if 'dark_mode' in request.GET:
        return bool(request.GET['dark_mode'])
    if 'dark_mode' in request.COOKIES:
        return request.COOKIES['dark_mode'] == 'true'
    else:
        return user.uses_dark_mode


def _get_page_context(
        request: dj_wsgi.WSGIRequest,
        user: models.User,
        page_id: str,
        no_index: bool = False,
        titles_args: dict[str, str] = None,
) -> page_context.PageContext:
    """Return a context object for the given page ID.

    :param user: Current user.
    :param page_id: Page’s ID.
    :param no_index: Whether to insert a noindex clause within the HTML page.
    :param titles_args: Dict object containing values to use in the page title translation.
    :return: A PageContext object.
    """
    kwargs = _get_base_context_args(request, user, page_id=page_id, titles_args=titles_args, no_index=no_index)
    return page_context.PageContext(**kwargs)


def _get_map_page_context(
        request: dj_wsgi.WSGIRequest,
        user: models.User,
        action: str = VIEW_MAP,
        no_index: bool = False,
) -> page_context.MapPageContext:
    """Return a context object for the map page.

    :param user: Current user.
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
        js_config['trans'][k] = _get_page_language(request, user).translate(k)

    kwargs = _get_base_context_args(request, user, no_index=no_index)
    return page_context.MapPageContext(**kwargs, map_js_config=js_config)


def _get_user_page_context(
        request: dj_wsgi.WSGIRequest,
        user: models.User,
        target_user: models.User,
) -> page_context.UserPageContext:
    """Return a context object for the user profile page.

    :param user: Current user.
    :param target_user: User of the requested page.
    :return: A UserPageContext object.
    """
    titles_rags = {'username': target_user.username}
    kwargs = _get_base_context_args(request, user, page_id='user_profile', titles_args=titles_rags)
    return page_context.UserPageContext(**kwargs, target_user=target_user)


def _get_base_context_args(
        request: dj_wsgi.WSGIRequest,
        user: models.User,
        page_id: str = None,
        titles_args: dict[str, str] = None,
        no_index: bool = False,
) -> dict[str, typ.Any]:
    """Return parameters common to all page context objects.

    :param user: Current user.
    :param page_id: Page ID.
    :param titles_args: Dict object containing values to use in the page title translation.
    :param no_index: Whether to insert a noindex clause within the HTML page.
    :return: A dict object containing context parameters.
    """
    language = _get_page_language(request, user)
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
        'no_index': no_index,
        'user': user,
        'language': language,
        'dark_mode': _get_dark_mode_status(request, user),
    }


def _show_wiki_page_context(
        page: models.Page,
        user: models.User,
        language: settings.UILanguage,
        dark_mode: bool,
        revision_id: int | None,
        results_per_page: int,
        page_index: int,
        js_config: dict,
) -> page_context.WikiPageShowActionContext:
    """Create a wiki page context object.

    :param page: Page object.
    :param user: Current user.
    :param language: Page’s language.
    :param dark_mode: Whether to activate the dark mode.
    :param revision_id: Page revision ID.
    :param results_per_page: Number of results to display per page. Used only for category pages.
    :param page_index: Index of current page. Used only for category pages.
    :param js_config: Dict object containing JS config values.
    :return: A WikiPageContext object.
    """
    no_index = not page.exists
    content = w_pages.render_wikicode(page.get_content(), user, language)
    cat_subcategories = []
    cat_pages = []
    if revision_id is None:
        revision = page.revisions.latest() if page.exists else None
        archived = False
        if page.namespace == w_ns.NS_CATEGORY:
            cat_subcategories = list(models.PageCategory.subcategories_for_category(page.full_title))
            cat_pages = list(models.PageCategory.pages_for_category(page.full_title))
    else:
        revision = page.revisions.get(id=revision_id)
        archived = True
    return page_context.WikiPageShowActionContext(
        page=page,
        no_index=no_index,
        user=user,
        language=language,
        dark_mode=dark_mode,
        js_config=js_config,
        content=content,
        revision=revision,
        archived=archived,
        cat_subcategories=cat_subcategories,
        cat_pages=cat_pages,
        cat_results_per_page=results_per_page,
        cat_page_index=page_index,
    )


def _wiki_page_edit_context(
        page: models.Page,
        user: models.User,
        language: settings.UILanguage,
        dark_mode: bool,
        revision_id: int | None,
        js_config: dict,
        form: forms.WikiEditPageForm = None,
        perm_error: bool = False,
        concurrent_edit_error: bool = False,
) -> page_context.WikiPageEditActionContext:
    """Create a wiki page editing context object.

    :param page: Page object.
    :param user: Current user.
    :param language: Page’s language.
    :param dark_mode: Whether to activate the dark mode.
    :param revision_id: Page revision ID.
    :param js_config: Dict object containing JS config values.
    :param form: Edit form object.
    :param perm_error: Whether the user lacks the permission to edit wiki pages.
    :param concurrent_edit_error: Whether another edit was made before submitting.
    :return: A WikiPageContext object.
    """
    if revision_id is None:
        revision = page.revisions.latest() if page.exists else None
        archived = False
    else:
        revision = page.revisions.get(id=revision_id)
        archived = True
    form = form or forms.WikiEditPageForm(
        user=user,
        language=language,
        disabled=not page.can_user_edit(user),
        warn_unsaved_changes=True,
        initial={
            'content': page.get_content(),
            'follow_page': page.is_user_following(user),
        },
    )
    return page_context.WikiPageEditActionContext(
        page=page,
        user=user,
        language=language,
        dark_mode=dark_mode,
        js_config=js_config,
        revision=revision,
        archived=archived,
        edit_form=form,
        edit_notice=w_pages.get_edit_notice(user, language),
        new_page_notice=w_pages.get_new_page_notice(user, language) if not page.exists else None,
        perm_error=perm_error,
        concurrent_edit_error=concurrent_edit_error,
        edit_protection_log_entry=w_pages.get_page_protection_log_entry(page),
    )


def _wiki_page_talk_context(
        page: models.Page,
        user: models.User,
        language: settings.UILanguage,
        dark_mode: bool,
        results_per_page: int,
        page_index: int,
        js_config: dict,
) -> page_context.WikiPageTalkActionContext:
    """Create a wiki page talk context object.

    :param page: Page object.
    :param user: Current user.
    :param language: Page’s language.
    :param dark_mode: Whether to activate the dark mode.
    :param results_per_page: Number of topics to display per page.
    :param page_index: Index of current page.
    :param js_config: Dict object containing JS config values.
    :return: A WikiPageContext object.
    """
    if page.exists:
        if user.has_permission(permissions.PERM_WIKI_MASK):
            topics = page.topics.all()
        else:
            topics = page.topics.filter(deleted=False)
    else:
        topics = []
    return page_context.WikiPageTalkActionContext(
        page=page,
        user=user,
        language=language,
        dark_mode=dark_mode,
        js_config=js_config,
        topics=topics,
        topics_per_page=results_per_page,
        page_index=page_index,
    )


def _wiki_page_history_context(
        page: models.Page,
        user: models.User,
        language: settings.UILanguage,
        dark_mode: bool,
        results_per_page: int,
        page_index: int,
        js_config: dict,
) -> page_context.WikiPageHistoryActionContext:
    """Create a wiki page history context object.

    :param page: Page object.
    :param user: Current user.
    :param language: Page’s language.
    :param dark_mode: Whether to activate the dark mode.
    :param results_per_page: Number of revisions to display per page.
    :param page_index: Index of current page.
    :param js_config: Dict object containing JS config values.
    :return: A WikiPageContext object.
    """
    if page.exists:
        if user.has_permission(permissions.PERM_WIKI_MASK):
            revisions = page.revisions.all()
        else:
            revisions = page.revisions.filter(hidden=False)
    else:
        revisions = []
    return page_context.WikiPageHistoryActionContext(
        page=page,
        user=user,
        language=language,
        dark_mode=dark_mode,
        js_config=js_config,
        revisions=revisions,
        revisions_per_page=results_per_page,
        page_index=page_index,
    )
