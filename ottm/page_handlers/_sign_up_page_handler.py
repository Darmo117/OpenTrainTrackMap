"""This module defines the handler for the sign up page."""
from __future__ import annotations

import typing as _typ

import django.contrib.auth.models as _dj_auth
import django.core.exceptions as _dj_exc
import django.core.validators as _dj_valid
import django.forms as _dj_forms
from django.http import response as _dj_response

from . import _core, _ottm_handler
from .. import forms as _forms, models as _models, requests as _requests
from ..api import auth as _auth


class SignUpPageHandler(_ottm_handler.OTTMHandler):
    """Handler for the sign up page."""

    def handle_request(self) -> _dj_response.HttpResponse:
        if not self._request_params.user.is_authenticated:
            if self._request_params.post:
                form = SignUpForm(post=self._request_params.post)
                if form.is_valid():
                    # All errors should have been handled by the form already
                    user = _auth.create_user(
                        form.cleaned_data['username'],
                        form.cleaned_data['email'],
                        form.cleaned_data['password'],
                    )
                    if user:
                        _auth.log_in(self._request_params.request,
                                     form.cleaned_data['username'],
                                     form.cleaned_data['password'])
                        return self.redirect('ottm:help', reverse=True)
            else:
                form = SignUpForm()
        else:
            form = None
        title, tab_title = self.get_page_titles(page_id='sign_up')
        return self.render_page('ottm/sign-up.html', SignUpPageContext(
            self._request_params,
            title,
            tab_title,
            form=form,
        ))


class SignUpForm(_forms.CustomForm, _forms.ConfirmPasswordFormMixin):
    """Sign up form."""

    def __init__(self, post=None, initial: dict[str, _typ.Any] = None):
        super().__init__('sign_up', False, post, initial=initial)

    @staticmethod
    def username_validator(value: str):
        """Validate the given username. Checks if it is valid and not already taken.

        :param value: Username to validate.
        """
        _models.username_validator(value)
        if value.startswith('Anonymous-'):
            raise _dj_exc.ValidationError('invalid username', code='invalid')
        if _models.CustomUser.objects.filter(username=value).exists():
            raise _dj_exc.ValidationError('duplicate username', code='duplicate')

    username = _dj_forms.CharField(
        label='username',
        max_length=_dj_auth.AbstractUser._meta.get_field('username').max_length,
        strip=True,
        required=True,
        validators=[username_validator],
        help_text=True,
    )
    email = _dj_forms.CharField(
        label='email',
        widget=_dj_forms.EmailInput,
        strip=True,
        required=True,
        validators=[_dj_valid.validate_email],
        help_text=True,
    )
    password = _dj_forms.CharField(
        label='password',
        max_length=_dj_auth.AbstractUser._meta.get_field('password').max_length,
        strip=True,
        required=True,
        widget=_dj_forms.PasswordInput(),
    )
    password_confirm = _dj_forms.CharField(
        label='password_confirm',
        max_length=_dj_auth.AbstractUser._meta.get_field('password').max_length,
        strip=True,
        required=True,
        widget=_dj_forms.PasswordInput(),
    )


class SignUpPageContext(_core.PageContext):
    """Context class for the sign up page."""

    def __init__(
            self,
            request_params: _requests.RequestParams,
            tab_title: str,
            title: str,
            form: SignUpForm = None,
    ):
        """Create a page context for the sign up page.

        :param request_params: Page request parameters.
        :param tab_title: Title of the browser’s tab.
        :param title: Page’s title.
        :param form: The sign up form.
        """
        super().__init__(
            request_params,
            tab_title=tab_title,
            title=title,
            no_index=False,
        )
        self._form = form

    @property
    def sign_up_form(self) -> SignUpForm | None:
        return self._form
