"""This module declares functions related to user authentication."""

import django.contrib.auth as dj_auth
import django.core.exceptions as dj_exc
import django.core.handlers.wsgi as dj_wsgi
import django.core.validators as dj_valid
import django.db.transaction as dj_db_trans

from .. import models
from ..api import errors, groups


def log_in(request: dj_wsgi.WSGIRequest, username: str, password: str) -> bool:
    if (user := dj_auth.authenticate(request, username=username, password=password)) is not None:
        dj_auth.login(request, user)
        return True
    return False


def log_out(request: dj_wsgi.WSGIRequest):
    dj_auth.logout(request)


def get_user_from_request(request: dj_wsgi.WSGIRequest) -> models.User:
    return models.User(dj_auth.get_user(request))


def get_user_from_name(username: str) -> models.User | None:
    try:
        return models.User(dj_auth.get_user_model().objects.get(username=username))
    except dj_auth.get_user_model().DoesNotExist:
        return None


def get_ip(request: dj_wsgi.WSGIRequest) -> str:
    # Client’s IP address is always at the last one in HTTP_X_FORWARDED_FOR on Heroku
    # https://stackoverflow.com/questions/18264304/get-clients-real-ip-address-on-heroku#answer-18517550
    if x_forwarded_for := request.META.get('HTTP_X_FORWARDED_FOR'):
        return x_forwarded_for[-1]
    return request.META.get('REMOTE_ADDR')


@dj_db_trans.atomic
def get_or_create_anonymous_account_from_request(request: dj_wsgi.WSGIRequest) -> models.User:
    ip = get_ip(request)

    try:
        latest_user = models.CustomUser.objects.latest("id")
    except models.CustomUser.DoesNotExist:
        nb = 0
    else:
        nb = latest_user.id

    try:
        dj_user = models.CustomUser.objects.get(ip=ip)
    except models.CustomUser.DoesNotExist:
        # Create temporary user account
        dj_user = models.CustomUser.objects.create_user(f'Anonymous-{nb + 1}', ip=ip)
        dj_user.save()
        dj_user.groups.add(models.UserGroup.objects.get(label='all'))

    return models.User(dj_user)


@dj_db_trans.atomic
def create_user(username: str, email: str = None, password: str = None, ignore_email: bool = False) -> models.User:
    try:
        models.username_validator(username)
    except dj_exc.ValidationError as e:
        match e.code:
            case 'invalid':
                raise errors.InvalidUsernameError(username)
            case 'duplicate':
                raise errors.DuplicateUsernameError(username)
            case _:
                raise e

    if email and not ignore_email:
        try:
            dj_valid.validate_email(email)
        except dj_exc.ValidationError:
            raise errors.InvalidEmailError(email)

    dj_user = models.CustomUser.objects.create_user(username, email=email, password=password)
    dj_user.save()
    dj_user.groups.add(models.UserGroup.objects.get(label=groups.GROUP_ALL))
    dj_user.groups.add(models.UserGroup.objects.get(label=groups.GROUP_USER))
    # TODO add to account creation log

    return models.User(dj_user)


def user_exists(username: str) -> bool:
    return dj_auth.get_user_model().objects.filter(username=username).exists()
