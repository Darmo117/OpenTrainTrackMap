"""This module defines the handler for user settings pages."""
from __future__ import annotations

import typing as _typ

import django.contrib.auth.models as _dj_auth
import django.core.validators as _dj_valid
import django.forms as _dj_forms
from django.http import response as _dj_response

from . import _ottm_handler, _user_page_context
from .. import forms as _forms, models as _models, requests as _requests


class UserSettingsPageHandler(_ottm_handler.OTTMHandler):
    """Handler for user settings pages."""

    def handle_request(self) -> _dj_response.HttpResponse:
        if not self._request_params.user.is_authenticated:
            return self.redirect('ottm:map', reverse=True)

        user = self._request_params.user
        title, tab_title = self.get_page_titles(page_id='user_settings')
        form = UserSettingsForm(initial={
            'username': user.username,
            'current_email': user.email,
        })
        return self.render_page(f'ottm/user-settings.html', UserSettingsPageContext(
            self._request_params,
            title,
            tab_title,
            target_user=self._request_params.user,
            form=form,
        ))


class UserSettingsForm(_forms.CustomForm, _forms.ConfirmPasswordFormMixin):
    """User settings form."""

    def __init__(self, post=None, initial: dict[str, _typ.Any] = None):
        super().__init__('user_settings', True, post, initial=initial)

    current_email = _dj_forms.CharField(
        label='current_email',
        required=False,
        disabled=True,
    )
    new_email = _dj_forms.CharField(
        label='new_email',
        widget=_dj_forms.EmailInput,
        validators=[_dj_valid.validate_email],
        required=True,
        help_text=True,
    )
    password = _dj_forms.CharField(
        label='password',
        max_length=_dj_auth.AbstractUser._meta.get_field('password').max_length,
        widget=_dj_forms.PasswordInput(),
        required=False,
        help_text=True,
    )
    password_confirm = _dj_forms.CharField(
        label='password_confirm',
        max_length=_dj_auth.AbstractUser._meta.get_field('password').max_length,
        widget=_dj_forms.PasswordInput(),
        required=False,
    )


class UserSettingsPageContext(_user_page_context.UserPageContext):
    """Context class for user settings pages."""

    def __init__(
            self,
            request_params: _requests.RequestParams,
            tab_title: str | None,
            title: str | None,
            target_user: _models.User,
            form: UserSettingsForm,
    ):
        """Create a page context for a user’s settings page.

        :param request_params: Page request parameters.
        :param tab_title: Title of the browser’s tab.
        :param title: Page’s title.
        :param target_user: User of the requested page.
        :param form: Settings form.
        """
        super().__init__(
            request_params,
            tab_title=tab_title,
            title=title,
            target_user=target_user,
        )
        self._form = form

    @property
    def form(self) -> UserSettingsForm:
        return self._form