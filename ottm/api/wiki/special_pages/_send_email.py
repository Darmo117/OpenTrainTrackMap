"""This module defines the email special page."""
import typing as _typ

import django.contrib.auth.models as _dj_auth_models
import django.forms as _dj_forms

from . import _core
from .. import namespaces as _w_ns
from ... import auth as _auth, emails as _emails
from .... import forms as _forms, data_model as _models, page_handlers as _ph, requests as _requests


class SendEmailSpecialPage(_core.SpecialPage):
    """This special page lets users send emails to others.

    Args: ``/<username:str>``
        - ``username``: the username of the user to send the email to.
    """

    def __init__(self):
        super().__init__('SendEmail', category=_core.Section.USERS)

    def _process_request(self, params: _requests.RequestParams, args: list[str]) \
            -> dict[str, _typ.Any] | _core.Redirect:
        user = _auth.get_user_from_request(params.request)
        if args:
            target_user = _auth.get_user_from_name(args[0])
        else:
            target_user = None
        form = _Form(user)
        global_errors = {form.name: []}
        if params.POST:
            form = _Form(user, post=params.POST)
            if form.is_valid():
                target_user = _auth.get_user_from_name(form.cleaned_data['username'])
                sent, error_message = _emails.user_send_email(
                    target_user,
                    form.cleaned_data['subject'],
                    form.cleaned_data['content'],
                    user,
                    is_copy=False)
                if error_message:
                    global_errors[form.name].append(error_message)
                if sent and form.cleaned_data['send_copy']:
                    copy_sent, copy_error_message = _emails.user_send_email(
                        target_user,
                        form.cleaned_data['subject'],
                        form.cleaned_data['content'],
                        user,
                        is_copy=True
                    )
                    if copy_error_message:
                        global_errors[form.name].append(copy_error_message)
                else:
                    copy_sent = None
                if sent:
                    kwargs = {'done': True}
                    if copy_sent is not None:
                        kwargs['copy-sent'] = copy_sent
                    return _core.Redirect(
                        f'{_w_ns.NS_SPECIAL.get_full_page_title(self.name)}/{target_user.username}',
                        args=kwargs
                    )
        elif args:
            if not target_user:
                global_errors[form.name].append('user_does_not_exist')
                form = _Form(user, initial={'username': args[0]})
            else:
                form = _Form(user, initial={'username': target_user.username})
        return {
            'title_key': 'title_user' if target_user else 'title',
            'title_value': target_user.username if target_user else None,
            'target_user': target_user,
            'form': form,
            'global_errors': global_errors,
            'done': params.GET.get('done'),
            'copy_sent': params.GET.get('copy-sent'),
        }


class _Form(_ph.WikiForm):
    username = _dj_forms.CharField(
        label='username',
        max_length=_dj_auth_models.AbstractUser._meta.get_field('username').max_length,
        required=True,
        strip=True,
        validators=[_models.username_validator, _forms.user_exists_validator],
    )
    subject = _dj_forms.CharField(
        label='subject',
        max_length=200,
        required=True,
        strip=True,
    )
    content = _dj_forms.CharField(
        label='content',
        widget=_dj_forms.Textarea(attrs={'rows': 20}),
        required=True,
        strip=True,
    )
    send_copy = _dj_forms.BooleanField(
        label='send_copy',
        required=False,
    )

    def __init__(self, user: _models.User, post=None, initial=None):
        if not initial:
            initial = {}
        initial.update({
            'subject': _emails.DEFAULT_SUBJECT,
            'send_copy': user.send_copy_of_sent_emails,
        })
        super().__init__('send_email', False, post=post, initial=initial)
