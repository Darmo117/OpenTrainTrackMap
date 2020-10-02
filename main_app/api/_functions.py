import logging
import re
import typing as typ

import django.contrib.auth as dj_auth
import django.contrib.auth.models as dj_models

from . import _errors
from .. import models


#########
# Users #
#########


def create_user(username: str, email: str = None, password: str = None, ignore_email: bool = False,
                lang_code: str = 'en', is_admin: bool = False) -> models.User:
    username = username.strip()

    # TODO disable usernames that are equal without considering case
    if username == '':
        raise _errors.InvalidUsernameError(username)
    if get_user_from_name(username):
        raise _errors.DuplicateUsernameError(username)

    if not ignore_email and not re.fullmatch(r'\w+([.-]\w+)*@\w+([.-]\w+)+', email):
        raise _errors.InvalidEmailError(email)
    elif password is None or password.strip() == '':
        raise _errors.InvalidPasswordError(password)

    if password is not None:
        password = password.strip()

    dj_user = dj_models.User.objects.create_user(username, email=email, password=password)
    dj_user.save()

    data = models.UserData(
        user=dj_user,
        lang_code=lang_code,
        is_admin=is_admin
    )
    data.save()
    user = models.User(dj_user, data)
    logging.info(f'Created user {username}')

    return user


def log_in(request, username: str, password: str) -> bool:
    user = dj_auth.authenticate(request, username=username, password=password)
    if user is not None:
        dj_auth.login(request, user)
        return True
    return False


def log_out(request):
    dj_auth.logout(request)


def get_user_from_request(request) -> models.User:
    dj_user = dj_auth.get_user(request)

    if not dj_user.is_anonymous:
        user_data = models.UserData.objects.get(user=dj_user)
    else:
        user_data = None

    return models.User(dj_user, user_data)


def get_user_from_name(username: str) -> typ.Optional[models.User]:
    try:
        dj_user = dj_models.User.objects.get(username__iexact=username)
        user_data = models.UserData.objects.get(user=dj_user)
        return models.User(dj_user, user_data)
    except dj_models.User.DoesNotExist:
        return None


def user_exists(username: str) -> bool:
    return dj_models.User.objects.filter(username=username).count() != 0
