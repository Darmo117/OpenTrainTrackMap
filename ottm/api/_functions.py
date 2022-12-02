import django.contrib.auth as dj_auth
import django.contrib.auth.models as dj_auth_models
import django.core.handlers.wsgi as dj_wsgi

import WikiPy.api.users as wpy_api_users
import WikiPy.settings as wpy_settings
from .. import models, settings

#########
# Users #
#########

username_validator = wpy_api_users.username_validator

email_validator = wpy_api_users.email_validator


def log_in(request: dj_wsgi.WSGIRequest, username: str, password: str) -> bool:
    if (user := dj_auth.authenticate(request, username=username, password=password)) is not None:
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


def get_user_from_name(username: str) -> models.User | None:
    try:
        dj_user = dj_auth.get_user_model().objects.get(username__iexact=username)
    except dj_auth.get_user_model().DoesNotExist:
        return None
    else:
        return models.User(dj_user, _get_user_info(dj_user))


def user_exists(username: str) -> bool:
    return dj_auth.get_user_model().objects.filter(username=username).count() != 0


def _get_user_info(user: dj_auth_models.AbstractUser) -> models.UserInfo:
    try:
        return models.UserInfo.objects.get(user=user)
    except models.UserInfo.DoesNotExist:
        wpy_user = wpy_api_users.get_user_from_name(user.username)
        is_admin = (wpy_user.is_in_group(wpy_settings.GROUP_ADMINISTRATORS)
                    or wpy_user.is_in_group(wpy_settings.GROUP_GROUPS_MANAGERS))
        return _create_user_info(user, is_admin=is_admin)


def _create_user_info(user: dj_auth_models.AbstractUser, lang_code: str = settings.DEFAULT_LANGUAGE,
                      is_admin: bool = False) -> models.UserInfo:
    data = models.UserInfo(
        user=user,
        language_code=lang_code,
        is_administrator=is_admin
    )
    data.save()
    return data
