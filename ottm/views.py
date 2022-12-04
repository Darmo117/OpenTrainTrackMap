import typing as typ

import django.core.handlers.wsgi as dj_wsgi
import django.http.response as dj_response
import django.shortcuts as dj_scut

from OpenTrainTrackMap import settings as g_settings
from . import page_context, models, settings, wiki_special_pages
from .api import auth, permissions
from .api.wiki import pages as w_pages, namespaces as w_ns, constants as w_cons

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
    user = auth.get_user_from_request(request)
    page_title = w_pages.get_correct_title(raw_page_title)
    ns, title = w_pages.split_title(page_title)
    kwargs = request.GET
    action = kwargs.get('action', w_cons.ACTION_SHOW)
    page = w_pages.get_page(ns, title)
    js_config = w_pages.get_js_config(page, action)
    site_name = settings.SITE_NAME

    if ns == w_ns.NS_SPECIAL:
        special_page = wiki_special_pages.SPECIAL_PAGES.get(title)
        if special_page is None:
            context = page_context.WikiSpecialPageContext(
                site_name=site_name,
                page=page,
                user=user,
                js_config=js_config,
            )
            status = 404
        elif not special_page.can_user_access(user):
            context = page_context.WikiSpecialPageContext(
                site_name=site_name,
                page=page,
                user=user,
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
                js_config=js_config,
                **data,
            )
            status = 200
        return dj_scut.render(request, 'ottm/wiki/special-page.html', context={'context': context}, status=status)

    else:
        page_exists = page.pk is not None
        match action:
            case w_cons.ACTION_RAW:
                return dj_response.HttpResponse(
                    content=page.get_content(),
                    content_type=w_cons.MIME_TYPES[page.content_type],
                    status=200 if page.exists else 404,
                )
            case w_cons.ACTION_EDIT:
                context = page_context.WikiPageEditActionContext(
                    site_name=site_name,
                    page=page,
                    user=user,
                    js_config=js_config,
                    code=page.get_content(),
                )
            case w_cons.ACTION_SUBMIT:
                # TODO edit
                context = None
            case w_cons.ACTION_HISTORY:
                revisions = page.revisions.all()
                if not user.has_permission(permissions.PERM_WIKI_MASK):
                    revisions = [r for r in revisions if not r.hidden]
                context = page_context.WikiPageHistoryActionContext(
                    site_name=site_name,
                    page=page,
                    user=user,
                    js_config=js_config,
                    revisions=revisions,
                )
            case w_cons.ACTION_DISCUSS:
                # TODO get topics
                context = None
            case _:
                no_index = not page_exists
                content = w_pages.render_wikicode(page.get_content())
                context = page_context.WikiPageShowActionContext(
                    site_name=site_name,
                    page=page,
                    no_index=no_index,
                    user=user,
                    js_config=js_config,
                    content=content,
                )

    status = 200 if context.page.exists else 404
    return dj_scut.render(request, 'ottm/wiki/page.html', context={'context': context}, status=status)


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
        'static_path': g_settings.STATIC_URL,
        'edit': 'true' if action == 'edit' else 'false',
    }

    for k in translations_keys:
        js_config['trans'][k] = user.prefered_language.translate(k)

    kwargs = _get_base_context_args(user, no_index=no_index)
    return page_context.MapPageContext(**kwargs, js_config=js_config)


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
    }
