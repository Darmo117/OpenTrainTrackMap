"""This module defines the user mute special page."""
import typing as _typ

import django.contrib.auth.models as _dj_auth_models
import django.forms as _dj_forms

from . import _core
from .. import namespaces as _w_ns
from ... import auth as _auth
from .... import forms as _forms, models as _models, page_handlers as _ph, requests as _requests


class MuteSpecialPage(_core.SpecialPage):
    """This special page lets users mute other users.

    Args: ``/<username:str>``
        - ``username``: the username of the user to mute.
    """

    def __init__(self):
        super().__init__('Mute', category=_core.Section.USERS)

    def _process_request(self, params: _requests.RequestParams, args: list[str]) \
            -> dict[str, _typ.Any] | _core.Redirect:
        user = _auth.get_user_from_request(params.request)
        target_user = None
        form = _Form()
        global_errors = {form.name: []}
        if params.post:
            form = _Form(params.post)
            if form.is_valid():
                target_user = _auth.get_user_from_name(form.cleaned_data['username'])
                username = target_user.username
                if user.is_authenticated:
                    email_bl = list(user.email_user_blacklist)
                    if form.cleaned_data['mute_emails']:
                        email_bl.append(username)
                    elif username in email_bl:
                        email_bl.remove(username)
                    user.email_user_blacklist = email_bl
                    notif_bl = list(user.user_notification_blacklist)
                    if form.cleaned_data['mute_notifications']:
                        notif_bl.append(username)
                    elif username in notif_bl:
                        notif_bl.remove(username)
                    user.user_notification_blacklist = notif_bl
                    user.internal_object.save()
                    return _core.Redirect(
                        f'{_w_ns.NS_SPECIAL.get_full_page_title(self.name)}/{form.cleaned_data["username"]}',
                        args={'done': True}
                    )
                else:
                    global_errors[form.name].append('anonymous_user')
        elif args:
            target_user = _auth.get_user_from_name(args[0])
            if not target_user:
                global_errors[form.name].append('user_does_not_exist')
                form = _Form(initial={'username': args[0]})
            else:
                form = _Form(initial={
                    'username': target_user.username,
                    'mute_emails': target_user.username in user.email_user_blacklist,
                    'mute_notifications': target_user.username in user.user_notification_blacklist,
                })
        return {
            'title_key': 'title_user' if target_user else 'title',
            'title_value': target_user.username if target_user else None,
            'target_user': target_user,
            'form': form,
            'global_errors': global_errors,
            'done': params.get.get('done'),
        }


class _Form(_ph.WikiForm):
    username = _dj_forms.CharField(
        label='username',
        max_length=_dj_auth_models.AbstractUser._meta.get_field('username').max_length,
        required=True,
        strip=True,
        validators=[_models.username_validator, _forms.user_exists_validator],
    )
    mute_emails = _dj_forms.BooleanField(
        label='mute_emails',
        required=False,
    )
    mute_notifications = _dj_forms.BooleanField(
        label='mute_notifications',
        required=False,
    )

    def __init__(self, post=None, initial=None):
        super().__init__('mute_user', False, post=post, initial=initial)
