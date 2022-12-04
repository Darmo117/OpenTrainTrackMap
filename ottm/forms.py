import django.contrib.auth.models as dj_auth
import django.core.exceptions as dj_exc
import django.core.validators as dj_valid
import django.forms as dj_forms

from . import models


class _CustomForm(dj_forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'


class ConfirmPasswordFormMixin:
    def passwords_match(self) -> bool:
        cleaned_data = getattr(self, 'cleaned_data')
        return cleaned_data['password'] == cleaned_data['password_confirm']


class SettingsForm(_CustomForm, ConfirmPasswordFormMixin):
    @staticmethod
    def username_validator(value: str, anonymous: bool = False):
        models.username_validator(value)
        if not anonymous and value.startswith('Anonymous-'):
            raise dj_exc.ValidationError('invalid username', code='invalid')

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
