import logging
import typing as typ

import django.contrib.auth as dj_auth
import django.core.exceptions as dj_exc
import django.core.handlers.wsgi as dj_wsgi

import WikiPy_app.forms as wpy_forms
from . import _errors
from .. import models, settings

#########
# Users #
#########

username_validator = wpy_forms.username_validator

email_validator = wpy_forms.email_validator


def log_in_username_validator(value):
    if not user_exists(value):
        raise dj_exc.ValidationError('Username does not exist.', code='not_exists')


def create_user(username: str, email: str = None, password: str = None, ignore_email: bool = False,
                lang_code: str = settings.DEFAULT_LANGUAGE, is_admin: bool = False) -> models.User:
    username = username.strip()
    if password is not None:
        password = password.strip()

    try:
        username_validator(username)
    except dj_exc.ValidationError as e:
        if e.code == 'invalid':
            raise _errors.InvalidUsernameError(username)
        elif e.code == 'duplicate':
            raise _errors.DuplicateUsernameError(username)
        else:  # Should not occur
            raise ValueError(e)

    if not ignore_email:
        try:
            email_validator(email)
        except dj_exc.ValidationError:
            raise _errors.InvalidEmailError(email)
    elif password is None or password == '':
        raise _errors.InvalidPasswordError(password)

    dj_user = dj_auth.get_user_model().objects.create_user(username, email=email, password=password)
    dj_user.save()

    data = _create_user_info(dj_user, lang_code, is_admin)
    user = models.User(dj_user, data)
    logging.info(f'Created user {username}')

    return user


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
        user_data = _get_user_info(dj_user)
        return models.User(dj_user, user_data)
    except dj_auth.get_user_model().DoesNotExist:
        return None


def user_exists(username: str) -> bool:
    return dj_auth.get_user_model().objects.filter(username=username).count() != 0


def _create_user_info(user, lang_code: str = settings.DEFAULT_LANGUAGE, is_admin: bool = False):
    data = models.UserInfo(
        user=user,
        lang_code=lang_code,
        is_admin=is_admin
    )
    data.save()
    return data


def _get_user_info(user):
    try:
        return models.UserInfo.objects.get(user=user)
    except models.UserInfo.DoesNotExist:
        return _create_user_info(user)
