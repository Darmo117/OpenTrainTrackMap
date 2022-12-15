"""This module defines the handler for the login page."""
from __future__ import annotations

import typing as _typ

import django.forms as _dj_forms
from django.http import response as _dj_response

from . import _core, _ottm_handler
from .. import forms as _forms, requests as _requests
from ..api import auth as _auth


class LoginPageHandler(_ottm_handler.OTTMHandler):
    """Handler for the login page."""

    def handle_request(self) -> _dj_response.HttpResponse:
        global_errors = []
        if not self._request_params.user.is_authenticated:
            if self._request_params.post:
                form = LoginForm(post=self._request_params.post)
                if form.is_valid():
                    # All errors should have been handled by the form already
                    if _auth.log_in(self._request_params.request,
                                    form.cleaned_data['username'],
                                    form.cleaned_data['password']):
                        return self.redirect(self._request_params.return_to)
                    global_errors.append('invalid_credentials')
            else:
                form = LoginForm()
        else:
            form = None
        title, tab_title = self.get_page_titles(page_id='log_in')
        return self.render_page('ottm/login.html', LoginPageContext(
            self._request_params,
            title,
            tab_title,
            edit_warning=bool(self._request_params.get.get('w')),
            form=form,
            global_errors=global_errors,
        ))


class LoginForm(_forms.CustomForm, _forms.ConfirmPasswordFormMixin):
    """Login form."""

    def __init__(self, post=None, initial: dict[str, _typ.Any] = None):
        """Create a login form.

        :param post: Optional POST dict.
        :param initial: Optional dict to pre-fill the form before render.
        """
        super().__init__('log_in', False, post, initial=initial)

    username = _dj_forms.CharField(
        label='username',
        strip=True,
        required=True,
    )
    password = _dj_forms.CharField(
        label='password',
        strip=True,
        required=True,
        widget=_dj_forms.PasswordInput(),
    )


class LoginPageContext(_core.PageContext):
    """Context class for the login page."""

    def __init__(
            self,
            request_params: _requests.RequestParams,
            tab_title: str,
            title: str,
            edit_warning: bool,
            form: LoginForm = None,
            global_errors: list[str] = None,
    ):
        """Create a page context for the login page.

        :param request_params: Page request parameters.
        :param tab_title: Title of the browser’s tab.
        :param title: Page’s title.
        :param form: The login form.
        :param global_errors: List of global form errors.
        """
        super().__init__(
            request_params,
            tab_title=tab_title,
            title=title,
            no_index=False,
        )
        self._edit_warning = edit_warning
        self._form = form
        self._global_errors = global_errors

    @property
    def edit_warning(self) -> bool:
        return self._edit_warning

    @property
    def login_form(self) -> LoginForm | None:
        return self._form

    @property
    def global_errors(self) -> list[str]:
        return self._global_errors
