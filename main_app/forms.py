import django.contrib.auth.models as dj_auth
import django.forms as dj_forms

from . import api


class _CustomForm(dj_forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'


class SignUpForm(_CustomForm):
    username = dj_forms.CharField(
        label='username',
        min_length=1,
        max_length=dj_auth.User._meta.get_field('username').max_length,
        help_text=True,
        validators=[api.username_validator],
        required=True
    )
    email = dj_forms.CharField(
        label='email',
        help_text=True,
        required=True,
        widget=dj_forms.EmailInput,
        validators=[api.email_validator]
    )
    password = dj_forms.CharField(
        label='password',
        min_length=1,
        max_length=dj_auth.User._meta.get_field('password').max_length,
        help_text=True,
        required=True,
        widget=dj_forms.PasswordInput()
    )


class LogInForm(_CustomForm):
    username = dj_forms.CharField(
        label='username',
        required=True,
        validators=[api.log_in_username_validator]
    )
    password = dj_forms.CharField(
        label='password',
        required=True,
        widget=dj_forms.PasswordInput()
    )
