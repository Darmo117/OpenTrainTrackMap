import typing as typ

import django.core.handlers.wsgi as dj_wsgi
import django.http.response as dj_response
import django.shortcuts as dj_scut
from django.conf import settings as dj_settings

from . import forms, models, page_context, settings, wiki_special_pages
from .api import auth, errors, permissions
from .api.wiki import constants as w_cons, namespaces as w_ns, pages as w_pages

VIEW_MAP = 'show'
EDIT_MAP = 'edit'
MAP_HISTORY = 'history'


def map_page(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    user = auth.get_user_from_request(request)

    return dj_scut.render(request, 'ottm/map.html', context={
        'context': _get_map_page_context(user)
    })


# TODO redirect to login page with alert-warning if user not logged in
def edit_page(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    user = auth.get_user_from_request(request)

    return dj_scut.render(request, 'ottm/map.html', context={
        'context': _get_map_page_context(user, action=EDIT_MAP, no_index=True)
    })


def history_page(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    user = auth.get_user_from_request(request)

    return dj_scut.render(request, 'ottm/map.html', context={
        'context': _get_map_page_context(user, action=MAP_HISTORY, no_index=True)
    })


def page_handler(page_name: str) -> typ.Callable[[dj_wsgi.WSGIRequest], dj_response.HttpResponse]:
    """Generates a page handler for the given page name.

    :param page_name: Page’s name.
    :return: The handler function.
    """

    def handler(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
        user = auth.get_user_from_request(request)
        return dj_scut.render(request, f'ottm/{page_name}.html', context={
            'context': _get_page_context(user, page_name)
        })

    return handler


def signup_page(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    pass  # TODO


def login_page(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    pass  # TODO


def logout_page(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    if auth.get_user_from_request(request).is_authenticated:
        auth.log_out(request)
    return dj_scut.HttpResponseRedirect(_get_referer_url(request))


def user_profile(request: dj_wsgi.WSGIRequest, username: str) -> dj_response.HttpResponse:
    user = auth.get_user_from_request(request)
    target_user = auth.get_user_from_name(username)
    return dj_scut.render(request, 'ottm/user-profile.html', context={
        'context': _get_user_page_context(user, target_user)
    })


def user_settings(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    user = auth.get_user_from_request(request)

    if not user.is_authenticated:
        return dj_scut.HttpResponseRedirect(dj_scut.reverse('ottm:map'))

    return dj_scut.render(request, 'ottm/user-settings.html', context={
        'context': _get_page_context(user, 'user_settings')
    })


def user_contributions(request: dj_wsgi.WSGIRequest, username: str) -> dj_response.HttpResponse:
    user = auth.get_user_from_request(request)
    target_user = auth.get_user_from_name(username)

    return dj_scut.render(request, 'ottm/map.html', context={
        'context': _get_map_page_context(user, action=MAP_HISTORY)
    })


def user_notes(request: dj_wsgi.WSGIRequest, username: str) -> dj_response.HttpResponse:
    user = auth.get_user_from_request(request)
    target_user = auth.get_user_from_name(username)

    return dj_scut.render(request, 'ottm/user-notes.html', context={
        'context': _get_page_context(user, 'notes', no_index=True)
    })


def wiki_page(request: dj_wsgi.WSGIRequest, raw_page_title: str = '') -> dj_response.HttpResponse:
    if not raw_page_title:
        return dj_scut.HttpResponseRedirect(dj_scut.reverse('ottm:wiki_page', kwargs={
            'raw_page_title': w_pages.url_encode_page_title(w_pages.MAIN_PAGE_TITLE)
        }))
    site_name = settings.SITE_NAME
    kwargs = request.GET
    user = auth.get_user_from_request(request)
    if (lang_code := kwargs.get('lang')) and lang_code in settings.LANGUAGES:
        language = settings.LANGUAGES.get(lang_code)
    else:
        language = user.prefered_language
    page_title = w_pages.get_correct_title(raw_page_title)
    ns, title = w_pages.split_title(page_title)
    action = kwargs.get('action', w_cons.ACTION_SHOW)
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
                context = _wiki_page_edit_context(page, user, language, revision_id, js_config)
            case w_cons.ACTION_SUBMIT:
                form = forms.WikiEditPageForm(request.POST)
                if not form.is_valid():
                    context = _wiki_page_edit_context(page, user, language, revision_id, js_config, form=form)
                else:
                    try:
                        w_pages.edit_page(request, user, page, form.content, form.comment, form.minor_edit,
                                          form.follow_page, form.section_id)
                    except errors.MissingPermissionError:
                        context = _wiki_page_edit_context(page, user, language, revision_id, js_config, perm_error=True)
                    else:
                        # Redirect to normal view
                        return dj_scut.HttpResponseRedirect(dj_scut.reverse('ottm:wiki_page', kwargs={
                            'raw_page_title': page.full_title,
                        }))
            case w_cons.ACTION_HISTORY:
                context = _wiki_page_history_context(page, user, language, results_per_page, page_index, js_config)
            case w_cons.ACTION_TALK:
                # TODO get topics
                context = None
            case _:
                context = _show_wiki_page_context(page, user, language, revision_id, results_per_page, page_index,
                                                  js_config)
        status = 200 if context.page.exists else 404

    ctxt = {
        'context': context,
        **w_cons.ACTIONS,
        **w_ns.NAMESPACES_NAMES,
    }
    return dj_scut.render(request, 'ottm/wiki/page.html', context=ctxt, status=status)


def _show_wiki_page_context(
        page: models.Page,
        user: models.User,
        language: settings.Language,
        revision_id: int | None,
        results_per_page: int,
        page_index: int,
        js_config: dict,
):
    no_index = not page.exists
    content = w_pages.render_wikicode(page.get_content())
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
        site_name=settings.SITE_NAME,
        page=page,
        no_index=no_index,
        user=user,
        language=language,
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
        language: settings.Language,
        revision_id: int | None,
        js_config: dict,
        form: forms.WikiEditPageForm = None,
        perm_error: bool = False,
        concurrent_edit_error: bool = False,
):
    if revision_id is None:
        revision = page.revisions.latest() if page.exists else None
        archived = False
    else:
        revision = page.revisions.get(id=revision_id)
        archived = True
    form = form or forms.WikiEditPageForm(
        user=user,
        language=language,
        disabled=page.can_user_edit(user),
        warn_unsaved_changes=True,
        initial={
            'content': page.get_content(),
            'follow_page': page.is_user_following(user),
        },
    )
    return page_context.WikiPageEditActionContext(
        site_name=settings.SITE_NAME,
        page=page,
        user=user,
        language=language,
        js_config=js_config,
        revision=revision,
        archived=archived,
        edit_form=form,
        edit_notice=w_pages.get_edit_notice(),
        perm_error=perm_error,
        concurrent_edit_error=concurrent_edit_error,
    )


def _wiki_page_history_context(
        page: models.Page,
        user: models.User,
        language: settings.Language,
        results_per_page: int,
        page_index: int,
        js_config: dict,
):
    if user.has_permission(permissions.PERM_WIKI_MASK):
        revisions = page.revisions.all()
    else:
        revisions = page.revisions.filter(hidden=False)
    return page_context.WikiPageHistoryActionContext(
        site_name=settings.SITE_NAME,
        page=page,
        user=user,
        language=language,
        js_config=js_config,
        revisions=revisions,
        revisions_per_page=results_per_page,
        page_index=page_index,
    )


def handle404(request: dj_wsgi.WSGIRequest, _) -> dj_response.HttpResponse:
    pass  # TODO 404


def handle500(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    pass  # TODO 500


#####################
# Utility functions #
#####################


def _get_referer_url(request: dj_wsgi.WSGIRequest) -> str:
    return request.GET.get('return_to', '/')


def _get_page_context(user: models.User, page_id: str, no_index: bool = False,
                      titles_args: dict[str, str] = None) -> page_context.PageContext:
    kwargs = _get_base_context_args(user, page_id=page_id, titles_args=titles_args, no_index=no_index)
    return page_context.PageContext(**kwargs)


def _get_map_page_context(user: models.User, action: str = VIEW_MAP,
                          no_index: bool = False) -> page_context.MapPageContext:
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
        js_config['trans'][k] = user.prefered_language.translate(k)

    kwargs = _get_base_context_args(user, no_index=no_index)
    return page_context.MapPageContext(**kwargs, map_js_config=js_config)


def _get_user_page_context(user: models.User, target_user: models.User) -> page_context.UserPageContext:
    titles_rags = {'username': target_user.username}
    kwargs = _get_base_context_args(user, page_id='user_profile', titles_args=titles_rags)
    return page_context.UserPageContext(**kwargs, target_user=target_user)


def _get_base_context_args(user: models.User, page_id: str = None, titles_args: dict[str, str] = None,
                           no_index: bool = False) -> dict[str, typ.Any]:
    if page_id:
        title = user.prefered_language.translate(f'page.{page_id}.title')
        tab_title = user.prefered_language.translate(f'page.{page_id}.tab_title')
        if titles_args:
            title = title.format(**titles_args)
            tab_title = tab_title.format(**titles_args)
    else:
        title = None
        tab_title = None
    return {
        'title': title,
        'tab_title': tab_title,
        'site_name': settings.SITE_NAME,
        'no_index': no_index,
        'user': user,
        'language': user.prefered_language,
    }
