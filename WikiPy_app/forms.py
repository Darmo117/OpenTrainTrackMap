import django.core.exceptions as dj_exc
import django.core.validators as dj_valid

from . import settings


def username_validator(value, anonymous: bool = False):
    # Avoid circular imports
    from . import api

    if (not anonymous and value.startswith('Anonymous-')
            or '/' in value
            or settings.INVALID_TITLE_REGEX.search(value)):
        raise dj_exc.ValidationError('invalid username', code='invalid')
    if api.user_exists(value):
        raise dj_exc.ValidationError('username already exists', code='duplicate')


def email_validator(value):
    dj_valid.EmailValidator()(value)
