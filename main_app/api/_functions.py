import typing as typ

import django.contrib.auth as dj_auth
import django.core.exceptions as dj_exc
import django.core.handlers.wsgi as dj_wsgi

import WikiPy_app.api as wpy_api
import WikiPy_app.forms as wpy_forms
import WikiPy_app.settings as wpy_settings
from .. import models, settings

#########
# Users #
#########

username_validator = wpy_forms.username_validator

email_validator = wpy_forms.email_validator


def log_in(request: dj_wsgi.WSGIRequest, username: str, password: str) -> bool:
    user = dj_auth.authenticate(request, username=username, password=password)
    if user is not None:
        dj_auth.login(request, user)
        return True
    return False


def log_out(request: dj_wsgi.WSGIRequest):
    dj_auth.logout(request)


def get_user_from_request(request: dj_wsgi.WSGIRequest) -> models.User:
    dj_user = dj_auth.get_user(request)

    if not dj_user.is_anonymous:
        user_data = _get_user_info(dj_user)
    else:
        user_data = None

    return models.User(dj_user, user_data)


def get_user_from_name(username: str) -> typ.Optional[models.User]:
    try:
        dj_user = dj_auth.get_user_model().objects.get(username__iexact=username)
    except dj_auth.get_user_model().DoesNotExist:
        return None
    else:
        return models.User(dj_user, _get_user_info(dj_user))


def user_exists(username: str) -> bool:
    return dj_auth.get_user_model().objects.filter(username=username).count() != 0


def _get_user_info(user):
    try:
        return models.UserInfo.objects.get(user=user)
    except models.UserInfo.DoesNotExist:
        wpy_user = wpy_api.get_user_from_name(user.username)
        is_admin = (wpy_user.is_in_group(wpy_settings.GROUP_ADMINISTRATORS)
                    or wpy_user.is_in_group(wpy_settings.GROUP_RIGHTS_MANAGERS))
        return _create_user_info(user, is_admin=is_admin)


def _create_user_info(user, lang_code: str = settings.DEFAULT_LANGUAGE, is_admin: bool = False):
    data = models.UserInfo(
        user=user,
        lang_code=lang_code,
        is_admin=is_admin
    )
    data.save()
    return data
