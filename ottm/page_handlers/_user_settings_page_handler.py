"""This module defines the handler for user settings pages."""
from __future__ import annotations

import django.contrib.auth.models as _dj_auth
import django.core.validators as _dj_valid
import django.forms as _dj_forms
from django.http import response as _dj_response

from . import _ottm_handler, _user_page_context
from .. import forms as _forms, models as _models, requests as _requests
from ..api import utils as _utils


class UserSettingsPageHandler(_ottm_handler.OTTMHandler):
    """Handler for user settings pages."""

    def handle_request(self) -> _dj_response.HttpResponse:
        if not self._request_params.user.is_authenticated:
            return self.redirect('ottm:map', reverse=True)

        user = self._request_params.user
        title, tab_title = self.get_page_titles(page_id='user_settings')
        form = UserSettingsForm(user=user)
        return self.render_page(f'ottm/user-settings.html', UserSettingsPageContext(
            self._request_params,
            title,
            tab_title,
            target_user=self._request_params.user,
            form=form,
        ))


class UserSettingsForm(_forms.CustomForm, _forms.ConfirmPasswordFormMixin):
    """User settings form."""

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
    prefered_language = _dj_forms.ChoiceField(
        label='prefered_language',
        required=True,
        choices=(),  # Set in __init__
    )
    email = _dj_forms.CharField(
        label='email',
        widget=_dj_forms.EmailInput(),
        validators=[_dj_valid.validate_email],
        required=True,
        help_text=True,
    )
    users_can_send_emails = _dj_forms.BooleanField(
        label='users_can_send_emails',
        required=False,
    )
    new_users_can_send_emails = _dj_forms.BooleanField(
        label='new_users_can_send_emails',
        required=False,
    )
    send_copy_of_sent_emails = _dj_forms.BooleanField(
        label='send_copy_of_sent_emails',
        required=False,
    )
    email_user_blacklist = _dj_forms.CharField(
        label='email_user_blacklist',
        widget=_dj_forms.Textarea(attrs={'rows': 2}),
        required=False,
        help_text=True,
    )
    dark_mode = _dj_forms.BooleanField(
        label='dark_mode',
        required=False,
    )
    prefered_datetime_format = _dj_forms.ChoiceField(
        label='prefered_datetime_format',
        required=True,
        choices=(),  # Set in __init__()
    )

    def __init__(self, post=None, user: _models.User = None):
        if user:
            initial = {
                'prefered_language': user.prefered_language.code,
                'email': user.email,
                'dark_mode': user.uses_dark_mode,
                'prefered_datetime_format': user.internal_object.prefered_datetime_format.id,
            }
        else:
            initial = {}

        sections = {
            'personal_info': {
                'basic_info': ['password', 'password_confirm', ],
                'localization': ['prefered_language', ],
                'email': ['email', 'users_can_send_emails', 'new_users_can_send_emails', 'send_copy_of_sent_emails',
                          'email_user_blacklist', ],
            },
            'appearence': {
                'skins': ['dark_mode', ],
                'date_and_time': ['prefered_datetime_format', ],
                'files': [],
                'diffs': [],
                'appearence_advanced': [],
            },
            'editing': {
                'editor': [],
                'preview': [],
                'talks': [],
            },
            'recent_changes': {
                'rc_display': [],
                'rc_mask': [],
            },
            'follow_list': {
                'modify': [],
                'fl_display': [],
                'fl_mask': [],
                'followed_pages': [],
            },
            'search': {
                'general': [],
                'advanced_search': [],
            },
            'gadgets': {
                # TODO
            },
            'notifications': {
                'email_options': [],
                'events': [],
                'blocked_users': [],
                'blocked_pages': [],
            },
        }

        super().__init__('user_settings', True, sections, post=post, initial=initial)

        self.fields['prefered_language'].choices = tuple(
            (language.code, language.name)
            for language in _models.Language.objects.order_by('name')
        )
        now = _utils.now()
        self.fields['prefered_datetime_format'].choices = tuple(
            (dtf.id, user.prefered_language.format_datetime(now, dtf.format))
            for dtf in _models.DateTimeFormat.objects.all()
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
