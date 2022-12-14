"""This module defines website’s forms."""
import typing as typ

import django.contrib.auth.models as dj_auth
import django.core.exceptions as dj_exc
import django.core.validators as dj_valid
import django.forms as dj_forms

from . import models
from .api.wiki.namespaces import *


class _CustomForm(dj_forms.Form):
    """Base class for all forms. Applies custom CSS styles to widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            if isinstance(visible.field.widget, dj_forms.CheckboxInput):
                visible.field.widget.attrs['class'] = 'form-check-input'
            else:
                visible.field.widget.attrs['class'] = 'form-control'


class ConfirmPasswordFormMixin:
    """Mixin for forms with a password confirmation field."""

    def passwords_match(self) -> bool:
        """Check whether the passwords in the 'password' and 'password_confirm' fields match."""
        cleaned_data = getattr(self, 'cleaned_data')
        return cleaned_data['password'] == cleaned_data['password_confirm']


class SettingsForm(_CustomForm, ConfirmPasswordFormMixin):
    """User settings form."""

    @staticmethod
    def username_validator(value: str, anonymous: bool = False):
        """Validate the given username. Checks if it is valid and not already taken.

        :param value: Username to validate.
        :param anonymous: Whether the username is for an anonymous user.
         If false, username cannot start with 'Anonymous-'.
        """
        models.username_validator(value)
        if not anonymous and value.startswith('Anonymous-'):
            raise dj_exc.ValidationError('invalid username', code='invalid')
        if models.CustomUser.objects.filter(username=value).exists():
            raise dj_exc.ValidationError('duplicate username', code='duplicate')

    username = dj_forms.CharField(
        label='username',
        min_length=1,
        max_length=dj_auth.User._meta.get_field('username').max_length,
        validators=[username_validator]
    )
    current_email = dj_forms.CharField(
        label='current_email',
        widget=dj_forms.EmailInput
    )
    new_email = dj_forms.CharField(
        label='new_email',
        widget=dj_forms.EmailInput,
        validators=[dj_valid.validate_email]
    )
    password = dj_forms.CharField(
        label='password',
        min_length=1,
        max_length=dj_auth.User._meta.get_field('password').max_length,
        widget=dj_forms.PasswordInput()
    )
    password_confirm = dj_forms.CharField(
        label='password_confirm',
        min_length=1,
        max_length=dj_auth.User._meta.get_field('password').max_length,
        widget=dj_forms.PasswordInput()
    )


class WikiForm(_CustomForm):
    """Base class for wiki forms."""

    def __init__(self, name: str, warn_unsaved_changes: bool, post=None, initial: dict[str, typ.Any] = None):
        """Create a wiki form.

        :param name: Form’s name.
        :param warn_unsaved_changes: Whether to display a warning whenever a user quits
            the page without submitting this form.
        :param post: A POST dict to populate this form.
        :param initial: A dict object of initial field values.
        """
        super().__init__(post, initial=initial)
        self._name = name
        self._warn_unsaved_changes = warn_unsaved_changes
        for field_name, field in self.fields.items():
            field.widget.attrs['id'] = f'wiki-{name}-form-{field_name.replace("_", "-")}'

    @property
    def name(self) -> str:
        return self._name

    @property
    def warn_unsaved_changes(self) -> bool:
        return self._warn_unsaved_changes


class WikiEditPageForm(WikiForm):
    """Form used to edit a wiki page."""
    content = dj_forms.CharField(
        label='content',
        required=False,
        widget=dj_forms.Textarea(attrs={'rows': 20})
    )
    comment = dj_forms.CharField(
        label='comment',
        max_length=200,
        required=False
    )
    minor_edit = dj_forms.BooleanField(
        label='minor_edit',
        required=False
    )
    follow_page = dj_forms.BooleanField(
        label='follow_page',
        required=False
    )
    hidden_category = dj_forms.BooleanField(
        label='hidden_category',
        required=False
    )
    # ID of the page section being edited (optional).
    section_id = dj_forms.CharField(
        widget=dj_forms.HiddenInput(),
        required=False
    )

    def __init__(self, user: models.User = None, page: models.Page = None, disabled: bool = False,
                 warn_unsaved_changes: bool = True, post=None, initial: dict[str, typ.Any] = None):
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
        if page and page.namespace != NS_CATEGORY:
            self.fields['hidden_category'].widget.attrs['disabled'] = True
        if disabled:
            self.fields['content'].widget.attrs['disabled'] = True
