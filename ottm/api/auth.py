"""This module declares functions related to user authentication."""
import django.contrib.auth as dj_auth
import django.core.handlers.wsgi as dj_wsgi

from .. import models


def log_in(request: dj_wsgi.WSGIRequest, username: str, password: str) -> bool:
    if (user := dj_auth.authenticate(request, username=username, password=password)) is not None:
        dj_auth.login(request, user)
        return True
    return False


def log_out(request: dj_wsgi.WSGIRequest):
    dj_auth.logout(request)


def get_user_from_request(request: dj_wsgi.WSGIRequest) -> models.User:
    return dj_auth.get_user(request)


def get_user_from_name(username: str) -> models.User | None:
    try:
        return dj_auth.get_user_model().objects.get(username__iexact=username)
    except dj_auth.get_user_model().DoesNotExist:
        return None


def user_exists(username: str) -> bool:
    return dj_auth.get_user_model().objects.filter(username=username).exists()
