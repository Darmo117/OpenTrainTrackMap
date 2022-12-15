"""This module defines website’s forms."""
import typing as _typ

import django.contrib.auth.models as _dj_auth
import django.core.exceptions as _dj_exc
import django.core.validators as _dj_valid
import django.forms as _dj_forms

from . import models as _models
from .api.wiki import namespaces as w_ns


class _CustomForm(_dj_forms.Form):
    """Base class for all forms. Applies custom CSS styles to widgets."""

    def __init__(self, name: str, warn_unsaved_changes: bool, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._name = name
        self._warn_unsaved_changes = warn_unsaved_changes
        for field_name, field in self.fields.items():
            field.widget.attrs['id'] = f'{name.replace("_", "-")}-form-{field_name.replace("_", "-")}'
        for visible in self.visible_fields():
            if isinstance(visible.field.widget, _dj_forms.CheckboxInput):
                visible.field.widget.attrs['class'] = 'form-check-input'
            else:
                visible.field.widget.attrs['class'] = 'form-control'

    @property
    def name(self) -> str:
        return self._name

    @property
    def warn_unsaved_changes(self) -> bool:
        return self._warn_unsaved_changes


class ConfirmPasswordFormMixin:
    """Mixin for forms with a password confirmation field."""

    def clean_password_confirm(self):
        # noinspection PyUnresolvedReferences
        if not self.passwords_match():
            raise _dj_exc.ValidationError('passwords do not match', code='passwords_mismatch')

    def passwords_match(self) -> bool:
        """Check whether the passwords in the 'password' and 'password_confirm' fields match."""
        cleaned_data = getattr(self, 'cleaned_data')
        return cleaned_data['password'] == cleaned_data['password_confirm']


class SignUpForm(_CustomForm, ConfirmPasswordFormMixin):
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
        min_length=1,
        max_length=_dj_auth.AbstractUser._meta.get_field('username').max_length,
        strip=True,
        required=True,
        validators=[username_validator],
    )
    email = _dj_forms.CharField(
        label='email',
        widget=_dj_forms.EmailInput,
        strip=True,
        required=True,
        validators=[_dj_valid.validate_email],
    )
    password = _dj_forms.CharField(
        label='password',
        min_length=1,
        max_length=_dj_auth.AbstractUser._meta.get_field('password').max_length,
        strip=True,
        required=True,
        widget=_dj_forms.PasswordInput(),
    )
    password_confirm = _dj_forms.CharField(
        label='password_confirm',
        min_length=1,
        max_length=_dj_auth.AbstractUser._meta.get_field('password').max_length,
        strip=True,
        required=True,
        widget=_dj_forms.PasswordInput(),
    )


class SettingsForm(_CustomForm, ConfirmPasswordFormMixin):
    """User settings form."""

    def __init__(self, post=None, initial: dict[str, _typ.Any] = None):
        super().__init__('user_settings', True, post, initial=initial)

    username = _dj_forms.CharField(
        label='username',
        max_length=_dj_auth.AbstractUser._meta.get_field('username').max_length,
        validators=[SignUpForm.username_validator],
        required=True,
    )
    current_email = _dj_forms.CharField(
        label='current_email',
        widget=_dj_forms.EmailInput,
        validators=[_dj_valid.validate_email],
        required=True,
    )
    new_email = _dj_forms.CharField(
        label='new_email',
        widget=_dj_forms.EmailInput,
        validators=[_dj_valid.validate_email],
        required=True,
    )
    password = _dj_forms.CharField(
        label='password',
        max_length=_dj_auth.AbstractUser._meta.get_field('password').max_length,
        widget=_dj_forms.PasswordInput(),
        required=True,
    )
    password_confirm = _dj_forms.CharField(
        label='password_confirm',
        max_length=_dj_auth.AbstractUser._meta.get_field('password').max_length,
        widget=_dj_forms.PasswordInput(),
        required=True,
    )


class WikiForm(_CustomForm):
    """Base class for wiki forms."""

    def __init__(self, name: str, warn_unsaved_changes: bool, post=None, initial: dict[str, _typ.Any] = None):
        """Create a wiki form.

        :param name: Form’s name.
        :param warn_unsaved_changes: Whether to display a warning whenever a user quits
            the page without submitting this form.
        :param post: A POST dict to populate this form.
        :param initial: A dict object of initial field values.
        """
        super().__init__(name, warn_unsaved_changes, post, initial=initial)
        for field_name, field in self.fields.items():
            field.widget.attrs['id'] = f'wiki-{name.replace("_", "-")}-form-{field_name.replace("_", "-")}'


class WikiEditPageForm(WikiForm):
    """Form used to edit a wiki page."""
    content = _dj_forms.CharField(
        label='content',
        required=False,
        widget=_dj_forms.Textarea(attrs={'rows': 20})
    )
    comment = _dj_forms.CharField(
        label='comment',
        max_length=_models.PageRevision._meta.get_field('comment').max_length,
        strip=True,
        required=False
    )
    minor_edit = _dj_forms.BooleanField(
        label='minor_edit',
        required=False
    )
    follow_page = _dj_forms.BooleanField(
        label='follow_page',
        required=False
    )
    hidden_category = _dj_forms.BooleanField(
        label='hidden_category',
        required=False
    )
    # ID of the page section being edited (optional).
    section_id = _dj_forms.CharField(
        widget=_dj_forms.HiddenInput(),
        required=False
    )

    def __init__(self, user: _models.User = None, page: _models.Page = None, disabled: bool = False,
                 warn_unsaved_changes: bool = True, post=None, initial: dict[str, _typ.Any] = None):
        """Create a page edit form.

        :param user: The user to send the form to.
        :param page: The page this form will be associated to.
        :param disabled: If true, the content field will be disabled and all others will not be generated.
        :param warn_unsaved_changes: Whether to display a warning whenever a user quits
            the page without submitting this form.
        :param post: A POST dict to populate this form.
        :param initial: A dict object of initial field values.
        """
        super().__init__('edit', warn_unsaved_changes, post, initial)

        if user and user.is_anonymous:
            self.fields['follow_page'].widget.attrs['disabled'] = True
        if page and page.namespace != w_ns.NS_CATEGORY:
            self.fields['hidden_category'].widget.attrs['disabled'] = True
        if disabled:
            self.fields['content'].widget.attrs['disabled'] = True
