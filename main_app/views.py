import typing as typ

import django.shortcuts as dj_scut

from OpenTrainTrackMap import settings as g_settings
from . import api, page_context, models, settings


def map_page(request):
    user = api.get_user_from_request(request)

    return dj_scut.render(request, 'main_app/map.html', context={
        'context': _get_map_page_context(user, no_index=False)
    })


def edit_page(request):
    user = api.get_user_from_request(request)

    return dj_scut.render(request, 'main_app/map.html', context={
        'context': _get_map_page_context(user, no_index=True, action='edit')
    })


def history_page(request):
    user = api.get_user_from_request(request)

    return dj_scut.render(request, 'main_app/map.html', context={
        'context': _get_map_page_context(user, no_index=True, action='history')
    })


def copyright_page(request):
    user = api.get_user_from_request(request)

    return dj_scut.render(request, 'main_app/copyright.html', context={
        'context': _get_base_context(user, 'copyright', no_index=True)
    })


def help_page(request):
    user = api.get_user_from_request(request)

    return dj_scut.render(request, 'main_app/help.html', context={
        'context': _get_base_context(user, 'help', no_index=True)
    })


def about_page(request):
    user = api.get_user_from_request(request)

    return dj_scut.render(request, 'main_app/about.html', context={
        'context': _get_base_context(user, 'about', no_index=True)
    })


def login_page(request):
    user = api.get_user_from_request(request)
    args = {
        'invalid_credentials': False,
        'username': '',
    }

    referer = request.GET.get("return_to")

    if len(request.POST):
        try:
            username = request.POST['username']
            password = request.POST['password']
            args['username'] = username
        except KeyError:
            args['invalid_credentials'] = True
        else:
            if api.log_in(request, username, password):
                return dj_scut.HttpResponseRedirect(referer)

    return dj_scut.render(request, 'main_app/login.html', context={
        'context': _get_login_page_context(user, **args)
    })


def sign_up_page(request):
    user = api.get_user_from_request(request)
    args = {
        'invalid_username': False,
        'invalid_password': False,
        'invalid_email': False,
        'username': '',
        'email': '',
    }

    if len(request.POST):
        try:
            username = request.POST['username']
            password = request.POST['password']
            email = request.POST['email']
            args['username'] = username
            args['email'] = email
        except KeyError as e:
            message = str(e)
            args['invalid_username'] = 'username' in message
            args['invalid_password'] = 'password' in message
            args['invalid_email'] = 'email' in message
        else:
            try:
                api.create_user(username, email, password)
            except (api.InvalidUsernameError, api.DuplicateUsernameError):
                args['invalid_username'] = True
            except api.InvalidPasswordError:
                args['invalid_password'] = True
            except api.InvalidEmailError:
                args['invalid_email'] = True
            else:
                return dj_scut.HttpResponseRedirect('user', username)

    return dj_scut.render(request, 'main_app/login.html', context={
        'context': _get_sign_up_page_context(user, **args)
    })


def user_profile(request):
    user = api.get_user_from_request(request)

    return dj_scut.render(request, 'main_app/user-profile.html', context={
        'context': _get_base_context(user, 'user', no_index=False)
    })


# noinspection PyUnusedLocal
def handle404(request, exception):
    pass  # TODO 404


def handle500(request):
    pass  # TODO 500


def _get_base_context(user: models.User, page_id: typ.Optional[str], no_index: bool):
    return page_context.PageContext(
        title=user.prefered_language.translate(f'page.{page_id}.title') if page_id is not None else None,
        tab_title=user.prefered_language.translate(f'page.{page_id}.tab_title') if page_id is not None else None,
        site_name=settings.SITE_NAME,
        noindex=no_index,
        user=user
    )


def _get_map_page_context(user: models.User, no_index: bool, action: str = 'show'):
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
    ]
    js_config = {
        'trans': {},
        'static_path': g_settings.STATIC_URL,
    }
    for t in translations_keys:
        js_config['trans'][t] = user.prefered_language.translate(t)

    context = _get_base_context(user, None, no_index)
    return page_context.MapPageContext(context, js_config)


def _get_login_page_context(user: models.User, invalid_credentials: bool, username: str):
    context = _get_base_context(user, 'log_in', no_index=True)
    return page_context.LoginPageContext(context, invalid_credentials, username)


def _get_sign_up_page_context(user: models.User, invalid_username: bool, invalid_password: bool, invalid_email: bool,
                              username: str, email: str):
    context = _get_base_context(user, 'sign_up', no_index=True)
    return page_context.SignUpPageContext(context, invalid_username, invalid_password, invalid_email, username, email)
