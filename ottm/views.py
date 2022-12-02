import typing as typ

import django.core.handlers.wsgi as dj_wsgi
import django.http.response as dj_response
import django.shortcuts as dj_scut

from OpenTrainTrackMap import settings as g_settings
from . import api, page_context, models, settings


def map_page(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    user = api.get_user_from_request(request)

    return dj_scut.render(request, 'ottm/map.html', context={
        'context': _get_map_page_context(user, no_index=False)
    })


# TODO rediriger vers log-in (avec alert-warning) si pas connecté
def edit_page(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    user = api.get_user_from_request(request)

    return dj_scut.render(request, 'ottm/map.html', context={
        'context': _get_map_page_context(user, no_index=True, action='edit')
    })


def history_page(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    user = api.get_user_from_request(request)

    return dj_scut.render(request, 'ottm/map.html', context={
        'context': _get_map_page_context(user, no_index=True, action='history')
    })


def page_handler(page_name: str) -> typ.Callable[[dj_wsgi.WSGIRequest], dj_response.HttpResponse]:
    """
    Generates a page handler for the given page name.
    :param page_name: Page’s name.
    :return: The handler function.
    """

    def handler(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
        user = api.get_user_from_request(request)

        return dj_scut.render(request, f'ottm/{page_name}.html', context={
            'context': _get_page_context(user, page_name, no_index=False)
        })

    return handler


def logout_page(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    if api.get_user_from_request(request).is_logged_in:
        api.log_out(request)
    return dj_scut.HttpResponseRedirect(_get_referer_url(request))


def user_profile(request: dj_wsgi.WSGIRequest, username: str) -> dj_response.HttpResponse:
    user = api.get_user_from_request(request)
    target_user = api.get_user_from_name(username)
    return dj_scut.render(request, 'ottm/user-profile.html', context={
        'context': _get_user_page_context(user, target_user)
    })


def user_settings(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    user = api.get_user_from_request(request)

    if not user.is_logged_in:
        return dj_scut.HttpResponseRedirect(dj_scut.reverse('ottm:map'))

    return dj_scut.render(request, 'ottm/user-settings.html', context={
        'context': _get_page_context(user, 'user_settings', no_index=False)
    })


def user_contributions(request: dj_wsgi.WSGIRequest, username: str) -> dj_response.HttpResponse:
    user = api.get_user_from_request(request)
    target_user = api.get_user_from_name(username)

    return dj_scut.render(request, 'ottm/map.html', context={
        'context': _get_map_page_context(user, no_index=False, action='history')
    })


def user_notes(request: dj_wsgi.WSGIRequest, username: str) -> dj_response.HttpResponse:
    user = api.get_user_from_request(request)
    target_user = api.get_user_from_name(username)

    return dj_scut.render(request, 'ottm/user-notes.html', context={
        'context': _get_page_context(user, 'notes', no_index=True)
    })


def handle404(request: dj_wsgi.WSGIRequest, _) -> dj_response.HttpResponse:
    pass  # TODO 404


def handle500(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    pass  # TODO 500


#####################
# Utility functions #
#####################


def _get_referer_url(request: dj_wsgi.WSGIRequest) -> str:
    return request.GET.get('return_to', '/')


def _get_page_context(user: models.User, page_id: str | None, no_index: bool,
                      titles_args: dict[str, str] = None) -> page_context.PageContext:
    return page_context.PageContext(**_get_base_context_args(user, page_id, no_index, titles_args))


def _get_map_page_context(user: models.User, no_index: bool, action: str = 'show') -> page_context.MapPageContext:
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

    kwargs = _get_base_context_args(user, None, no_index)
    return page_context.MapPageContext(**kwargs, js_config=js_config)


def _get_user_page_context(user: models.User, target_user: models.User) -> page_context.UserPageContext:
    titles_rags = {'username': target_user.username}
    kwargs = _get_base_context_args(user, 'user_profile', no_index=False, titles_args=titles_rags)
    return page_context.UserPageContext(**kwargs, target_user=target_user)


def _get_base_context_args(user: models.User, page_id: str | None, no_index: bool,
                           titles_args: dict[str, str] = None) -> dict[str, typ.Any]:
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
