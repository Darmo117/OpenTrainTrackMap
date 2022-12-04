"""This middleware replaces the default django.contrib.auth.models.AnonymousUser class by a custom one."""
import importlib

import django.contrib.auth as dj_auth
import django.contrib.auth.middleware as dj_middleware
import django.utils.functional as dj_func
from django.conf import settings as dj_settings

module, class_name = dj_settings.AUTH_ANONYMOUS_MODEL.rsplit('.', 1)
AnonymousUser = getattr(importlib.import_module(module + '.models'), class_name)


def get_cached_user(request):
    """Set request._cached_user to a new instance of this app’s custom AnonymousUser class
    if the request’s user is anonymous."""
    if not hasattr(request, '_cached_user'):
        user = dj_auth.get_user(request)
        if user.is_anonymous:
            user = AnonymousUser(request)
        request._cached_user = user
    # noinspection PyProtectedMember
    return request._cached_user


class AuthenticationMiddleware(dj_middleware.AuthenticationMiddleware):
    """Custom auth middleware that uses this app’s custom AnonymousUser class instead of Django’s."""

    def process_request(self, request):
        super().process_request(request)  # Call to super to handle potential errors
        request.user = dj_func.SimpleLazyObject(lambda: get_cached_user(request))
