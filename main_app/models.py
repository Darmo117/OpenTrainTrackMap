import typing as typ

import django.contrib.auth as dj_auth
import django.contrib.auth.models as dj_auth_models
import django.db.models as dj_models

from . import settings


class UserInfo(dj_models.Model):
    user = dj_models.OneToOneField(dj_auth.get_user_model(), on_delete=dj_models.CASCADE)
    lang_code = dj_models.CharField(max_length=3)
    is_admin = dj_models.BooleanField()

    @property
    def prefered_language(self) -> settings.Language:
        return settings.LANGUAGES[self.lang_code]


class User:
    """Simple wrapper class for Django users and associated user data."""

    def __init__(self, django_user: dj_auth_models.AbstractUser, data: typ.Optional[UserInfo]):
        self.__django_user = django_user
        self.__data = data

    @property
    def django_user(self) -> dj_auth_models.AbstractUser:
        return self.__django_user

    @property
    def data(self) -> typ.Optional[UserInfo]:
        return self.__data

    @property
    def username(self) -> str:
        return self.__django_user.username

    @property
    def is_logged_in(self) -> bool:
        return self.__django_user.is_authenticated

    @property
    def prefered_language(self) -> settings.Language:
        return self.__data.prefered_language if self.__data else settings.LANGUAGES[settings.DEFAULT_LANGUAGE]

    @property
    def is_admin(self) -> bool:
        return self.__data.is_admin if self.__data else False

    def __repr__(self):
        return f'User[django_user={self.__django_user.username},data={self.__data}]'
