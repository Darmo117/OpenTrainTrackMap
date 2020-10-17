import typing as typ

import django.core.handlers.wsgi as dj_wsgi
import django.http.response as dj_response
import django.shortcuts as dj_scut

from OpenTrainTrackMap import settings as g_settings
from . import api, page_context, models, settings, forms


def map_page(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    user = api.get_user_from_request(request)

    return dj_scut.render(request, 'main_app/map.html', context={
        'context': _get_map_page_context(user, no_index=False)
    })


# TODO rediriger vers log-in (avec alert-warning) si pas connecté
def edit_page(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    user = api.get_user_from_request(request)

    return dj_scut.render(request, 'main_app/map.html', context={
        'context': _get_map_page_context(user, no_index=True, action='edit')
    })


def history_page(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    user = api.get_user_from_request(request)

    return dj_scut.render(request, 'main_app/map.html', context={
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

        return dj_scut.render(request, f'main_app/{page_name}.html', context={
            'context': _get_base_context(user, page_name, no_index=False)
        })

    return handler


def login_page(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    user = api.get_user_from_request(request)
    args = {
        'form': None,
    }

    if not user.is_logged_in:
        if request.method == 'POST':
            form = forms.LogInForm(request.POST)
            args['form'] = form
            if form.is_valid():
                if api.log_in(request, form.cleaned_data['username'], form.cleaned_data['password']):
                    return dj_scut.HttpResponseRedirect(_get_referer_url(request))
                else:
                    pass  # TODO handle
        else:
            args['form'] = forms.LogInForm()

    return dj_scut.render(request, 'main_app/log-in.html', context={
        'context': _get_login_page_context(user, **args)
    })


def logout_page(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    if api.get_user_from_request(request).is_logged_in:
        api.log_out(request)

    return dj_scut.HttpResponseRedirect(_get_referer_url(request))


def sign_up_page(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    user = api.get_user_from_request(request)
    args = {
        'form': None,
    }

    if not user.is_logged_in:
        if request.method == 'POST':
            form = forms.SignUpForm(request.POST)
            args['form'] = form
            if form.is_valid():
                username = form.cleaned_data['username']
                password = form.cleaned_data['email']
                api.create_user(username, password, form.cleaned_data['password'])
                return dj_scut.HttpResponseRedirect(dj_scut.reverse('main_app:log_in'))
        else:
            args['form'] = forms.SignUpForm()

    return dj_scut.render(request, 'main_app/sign-up.html', context={
        'context': _get_sign_up_page_context(user, **args)
    })


def user_profile(request: dj_wsgi.WSGIRequest, username: str) -> dj_response.HttpResponse:
    user = api.get_user_from_request(request)
    target_user = api.get_user_from_name(username)

    return dj_scut.render(request, 'main_app/user-profile.html', context={
        'context': _get_base_context(user, 'user', no_index=False)
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


def _get_base_context(user: models.User, page_id: typ.Optional[str], no_index: bool) -> page_context.PageContext:
    return page_context.PageContext(
        title=user.prefered_language.translate(f'page.{page_id}.title') if page_id is not None else None,
        tab_title=user.prefered_language.translate(f'page.{page_id}.tab_title') if page_id is not None else None,
        site_name=settings.SITE_NAME,
        noindex=no_index,
        user=user
    )


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
        'edit': int(action == 'edit'),  # To avoid False and True in the JavaScript code.
    }
    for t in translations_keys:
        js_config['trans'][t] = user.prefered_language.translate(t)

    context = _get_base_context(user, None, no_index)
    return page_context.MapPageContext(context, js_config)


def _get_login_page_context(user: models.User, form: forms.LogInForm) -> page_context.LoginPageContext:
    context = _get_base_context(user, 'log_in', no_index=True)
    return page_context.LoginPageContext(context, form)


def _get_sign_up_page_context(user: models.User, form: forms.SignUpForm) -> page_context.SignUpPageContext:
    context = _get_base_context(user, 'sign_up', no_index=True)
    return page_context.SignUpPageContext(context, form)
